"""The agent loop: select papers by strategy, review them, submit what clears the bar."""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import AuditLog, State, now
from .config import LoadedAgent
from .payload import argument_payload
from .platform import PlatformClient, PlatformError
from .providers import ProviderError
from .runner import Reviewer
from .selector import SLOTS_PER_PAPER, discover, rank
from .sources import read_source_async
from .types import ModelProvider, ReviewResult

MIN_MODEL_CREDIT_USD = 0.5


class StopRun(Exception):
    """Raised to end the run cleanly, with the reason recorded in run.json."""


class PaperRefused(Exception):
    """The platform refuses arguments on this paper (owner-authored or no slots)."""


class AgentLoop:
    def __init__(
        self,
        loaded: LoadedAgent,
        client: PlatformClient,
        providers: dict[str, ModelProvider],
        audit: AuditLog,
        state: State,
        *,
        dry_run: bool = False,
        cache_dir: Path | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        sleep: Callable[[float], None] = time.sleep,
        say: Callable[[str], None] = print,
    ) -> None:
        self.loaded, self.client, self.providers = loaded, client, providers
        self.audit, self.state = audit, state
        self.config = loaded.config
        self.dry_run = dry_run
        self.cache_dir = cache_dir or loaded.root / ".cache" / "papers"
        self.reviewer = Reviewer(loaded, providers)
        self.clock, self.sleep, self.say = clock, sleep, say
        self.profile: dict[str, Any] = {}
        self.submitted = 0
        self.papers = 0
        self.rounds = 0

    # -- stop rules -------------------------------------------------------

    def deadline(self) -> datetime | None:
        value = self.config.run.deadline
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    def stop_reason(self) -> str | None:
        rules = self.config.run
        if rules.max_arguments is not None and self.submitted >= rules.max_arguments:
            return f"submitted {self.submitted} arguments (max_arguments)"
        if rules.max_papers is not None and self.papers >= rules.max_papers:
            return f"reviewed {self.papers} papers (max_papers)"
        deadline = self.deadline()
        if deadline is not None and self.clock() >= deadline:
            return "deadline reached"
        budget = self.profile.get("budget")
        if not self.dry_run and isinstance(budget, int) and budget <= rules.min_budget:
            return f"owner budget {budget} is at or below min_budget {rules.min_budget}"
        credit = self.profile.get("model_credit_usd")
        uses_proxy = "koala_proxy" in {
            m.provider for m in (self.config.model, self.config.verifier_model) if m
        }
        if (
            uses_proxy
            and isinstance(credit, (int, float))
            and credit < MIN_MODEL_CREDIT_USD
        ):
            return f"Koala model credit ${credit:.2f} is nearly exhausted"
        return None

    # -- platform bookkeeping --------------------------------------------

    def refresh_profile(self) -> None:
        self.profile = self.client.me()

    def reconcile(self) -> None:
        """Adopt arguments the platform has but state.json lost, e.g. after a crash."""
        for argument in self.client.my_arguments(self.profile["id"]):
            if argument.get("author_id") not in {None, self.profile["id"]}:
                continue
            if argument["id"] not in self.state.arguments:
                self.state.arguments[argument["id"]] = {
                    "paper_id": argument["paper_id"],
                    "state": None,
                    "submitted_at": argument.get("created_at"),
                }
                self.audit.argument(
                    {
                        "event": "reconciled",
                        "argument_id": argument["id"],
                        "paper_id": argument["paper_id"],
                    }
                )
        self.state.save()

    def update_outcomes(self) -> None:
        """Record check results for arguments still pending."""
        for paper_id, ids in self.state.pending().items():
            visible = {a["id"]: a for a in self.client.paper_arguments(paper_id)}
            for argument_id in ids:
                argument = visible.get(argument_id)
                if argument is None:
                    # Arguments that fail moderation are withheld from the paper page.
                    new_state, checks = "withheld", None
                else:
                    new_state, checks = argument.get("state"), argument.get("checks")
                    if new_state == "pending":
                        continue
                self.state.arguments[argument_id]["state"] = new_state
                self.audit.argument(
                    {
                        "event": "outcome",
                        "argument_id": argument_id,
                        "paper_id": paper_id,
                        "state": new_state,
                        "checks": checks,
                    }
                )
                self.say(f"  outcome: {argument_id} on {paper_id} is {new_state}")
        self.state.save()

    # -- selection ---------------------------------------------------------

    def select(self) -> list[tuple[dict[str, Any], str]]:
        self.rounds += 1
        eligible, report = discover(
            self.client, self.config.discovery, self.state, now=self.clock()
        )
        shortlist = eligible[: self.config.discovery.shortlist]
        ranking = asyncio.run(
            rank(
                self.providers["selector"],
                self.config.model.name,
                self.loaded.strategy,
                shortlist,
                timeout_seconds=self.config.review.limits.request_timeout_seconds,
            )
        )
        by_id = {p["id"]: p for p in shortlist}
        chosen = [(by_id[r.paper_id], r.reason) for r in ranking.ranked]
        self.audit.selection(
            {
                "round": self.rounds,
                "discovery": self.config.discovery.model_dump(),
                **report,
                "shortlist": [
                    {"id": p["id"], "title": p.get("title")} for p in shortlist
                ],
                "ranked": [r.model_dump() for r in ranking.ranked],
                "not_selected": [
                    p["id"]
                    for p in shortlist
                    if p["id"] not in {r.paper_id for r in ranking.ranked}
                ],
            }
        )
        self.say(
            f"Round {self.rounds}: scanned {report['scanned']}, eligible {report['eligible']}, "
            f"shortlisted {len(shortlist)}, selected {len(chosen)}"
        )
        return chosen

    # -- one paper ---------------------------------------------------------

    def skip(self, paper_id: str, reason: str) -> None:
        self.state.skipped[paper_id] = {
            "at": now(),
            "run": self.audit.run_id,
            "reason": reason,
        }
        self.state.save()
        self.say(f"  skipped {paper_id}: {reason}")

    def review_paper(self, listed: dict[str, Any], reason: str) -> None:
        paper_id = listed["id"]
        self.say(f"Reviewing {paper_id}: {listed.get('title')}")
        paper = self.client.paper(paper_id)
        if not paper.get("pdf_url"):
            self.skip(paper_id, "no PDF")
            return
        pdf = (
            self.cache_dir / f"{hashlib.sha256(paper_id.encode()).hexdigest()[:24]}.pdf"
        )
        try:
            if not pdf.exists():
                self.client.download(paper["pdf_url"], pdf)
            source = asyncio.run(
                read_source_async(pdf, self.config.review.limits.max_run_seconds)
            )
        except (PlatformError, ValueError) as exc:
            self.skip(paper_id, f"paper text unavailable: {exc}")
            return
        existing = self.client.paper_arguments(paper_id)
        known = [
            {"id": a["id"], "claim": a["claim"], "position": a["position"]}
            for a in existing
            if a.get("state") != "rejected"
        ]
        own_live = {
            a["id"]
            for a in existing
            if a.get("author_id") == self.profile["id"] and a.get("state") != "rejected"
        }
        slots = SLOTS_PER_PAPER - max(len(own_live), self.state.live_on(paper_id))
        paper_dir = self.audit.paper_dir(paper_id)
        paper_dir.mkdir(parents=True)
        result: ReviewResult = asyncio.run(
            self.reviewer.review(
                source,
                paper=paper,
                known_arguments=known,
                journal=paper_dir / "journal.jsonl",
            )
        )
        result.save(paper_dir / "review")
        limit = min(self.config.review.max_arguments_per_paper, slots)
        if self.config.run.max_arguments is not None:
            limit = min(limit, self.config.run.max_arguments - self.submitted)
        submitted = []
        for argument in result.arguments[: max(0, limit)]:
            try:
                submitted.append(self.submit(paper_id, argument))
            except PaperRefused:
                break
        self.papers += 1
        self.state.reviewed[paper_id] = {
            "at": now(),
            "run": self.audit.run_id,
            "selection_reason": reason,
            "review_status": result.status,
            "passed_local_checks": len(result.arguments),
            "submitted": [s for s in submitted if s],
        }
        self.state.save()
        self.say(
            f"  {len(result.arguments)} argument(s) passed local checks; "
            f"{len([s for s in submitted if s])} {'would be ' if self.dry_run else ''}submitted"
        )

    def submit(self, paper_id: str, argument) -> str | None:
        try:
            payload = argument_payload(argument, paper_id)
        except ValueError as exc:
            self.audit.argument(
                {"event": "not_submitted", "paper_id": paper_id, "reason": str(exc)}
            )
            return None
        if self.dry_run:
            self.audit.argument(
                {"event": "dry_run", "paper_id": paper_id, "payload": payload}
            )
            self.submitted += 1
            return argument.id
        try:
            response = self.client.post_argument(payload)
        except PlatformError as exc:
            self.audit.argument(
                {
                    "event": "submit_failed",
                    "paper_id": paper_id,
                    "status": exc.status,
                    "detail": exc.detail,
                    "uncertain": exc.uncertain,
                    "payload": payload,
                }
            )
            if exc.status == 402:
                raise StopRun("owner budget is empty (HTTP 402)") from exc
            if exc.status in {403, 409}:
                raise PaperRefused from exc
            if exc.uncertain:
                # Never repeat a write that may have landed; reconcile on the next round.
                self.reconcile()
            return None
        self.state.arguments[response["id"]] = {
            "paper_id": paper_id,
            "state": response.get("state", "pending"),
            "submitted_at": now(),
        }
        self.state.save()
        self.submitted += 1
        self.audit.argument(
            {
                "event": "submitted",
                "argument_id": response["id"],
                "paper_id": paper_id,
                "payload": payload,
                "local_checks": argument.local_checks,
                "budget_remaining": response.get("budget_remaining"),
            }
        )
        if isinstance(response.get("budget_remaining"), int):
            self.profile["budget"] = response["budget_remaining"]
        return response["id"]

    # -- the loop ----------------------------------------------------------

    def run(self, *, once: bool = False) -> str:
        self.audit.run_record(
            {
                "run_id": self.audit.run_id,
                "started_at": now(),
                "dry_run": self.dry_run,
                "config": self.config.model_dump(mode="json"),
                "strategy": self.loaded.strategy,
                "reviewer": self.loaded.reviewer,
            }
        )
        reason = "stopped"
        try:
            self.refresh_profile()
            if not self.dry_run and not self.profile.get("github_repo"):
                raise StopRun(
                    "the agent profile has no github_repo; the platform requires a public audit repository"
                )
            self.reconcile()
            while True:
                try:
                    self.update_outcomes()
                    stop = self.stop_reason()
                    if stop:
                        reason = stop
                        break
                    chosen = self.select()
                    for paper, why in chosen:
                        stop = self.stop_reason()
                        if stop:
                            break
                        self.review_paper(paper, why)
                except StopRun:
                    raise
                except (PlatformError, ProviderError, ValueError) as exc:
                    # Transient trouble must not end a long run or mark papers as done.
                    self.audit.call({"kind": "round_error", "error": str(exc)})
                    self.say(f"Round failed: {exc}")
                    if once:
                        reason = f"round failed: {exc}"
                        break
                    self.sleep(min(self.config.run.idle_minutes * 60, 300))
                    self.refresh_profile()
                    continue
                if once:
                    reason = "finished one round (--once)"
                    break
                if not chosen:
                    if self.config.run.when_idle == "stop":
                        reason = "no eligible papers fit the strategy"
                        break
                    wait = self.config.run.idle_minutes * 60
                    deadline = self.deadline()
                    if deadline is not None:
                        wait = min(
                            wait, max(0, (deadline - self.clock()).total_seconds())
                        )
                    self.say(f"No eligible papers; sleeping {wait / 60:.0f} minutes")
                    self.sleep(wait)
                self.refresh_profile()
        except StopRun as exc:
            reason = str(exc)
        except KeyboardInterrupt:
            reason = "interrupted"
        finally:
            self.audit.run_record(
                {
                    "ended_at": now(),
                    "stop_reason": reason,
                    "papers_reviewed": self.papers,
                    "arguments_submitted": 0 if self.dry_run else self.submitted,
                    "arguments_dry_run": self.submitted if self.dry_run else 0,
                }
            )
        self.say(f"Stopped: {reason}")
        return reason
