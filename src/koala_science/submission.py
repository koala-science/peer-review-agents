"""Explicit selection, read-only preview, and journaled sequential delivery."""

from __future__ import annotations

import asyncio
import json
import math
import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import Field

from .platform import PlatformClient, PlatformError, remote_identity, verify_paper
from .sources import check_evidence, read_source_async
from .types import Argument, ReviewResult, StrictModel
from .workspace import PaperWorkspace, digest, file_hash, read_json, write_json

ARTIFACTS = ("arguments.json", "sources.json", "manifest.json", "diagnostics.json")

AGENT_SETUP_GUIDE = """Set up platform submission:
1. Sign in to https://koala.science/dashboard with your human account.
2. Select an existing registered agent, or register an agent with its name and public audit repository.
   A local agent.yaml does not register an agent online. Keep the agent API key from registration private.
3. Set KOALA_AGENT_API_KEY in the shell that runs Koala, using that agent's API key, not a human access token.
   PowerShell (hidden input):
   $env:KOALA_AGENT_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'Koala agent API key' -AsSecureString)).Password
   Bash (hidden input):
   read -r -s -p 'Koala agent API key: ' KOALA_AGENT_API_KEY
   export KOALA_AGENT_API_KEY
4. Rerun koala submit to check the agent, then koala submit --send when ready.
Do not paste the key into chat, YAML, or Git. Koala does not load .env files.
"""


def check_submission_agent(api: PlatformClient, *, required: bool) -> dict | None:
    """Verify online registration using the agent key, or explain setup."""
    key = os.environ.get("KOALA_AGENT_API_KEY", "")
    if not key.strip():
        message = (
            "KOALA_AGENT_API_KEY is not set; platform agent not verified.\n"
            + AGENT_SETUP_GUIDE
        )
        if required:
            raise ValueError(message)
        print(message)
        return None
    if any(character.isspace() for character in key):
        raise ValueError(
            "KOALA_AGENT_API_KEY contains whitespace; set the exact agent key.\n"
            + AGENT_SETUP_GUIDE
        )
    try:
        profile = api.request("GET", "users/me", actor="agent")
    except PlatformError as exc:
        if exc.status in {401, 403}:
            raise PlatformError(
                "The platform rejected KOALA_AGENT_API_KEY. Check that the agent is active and its key is valid.\n"
                + AGENT_SETUP_GUIDE,
                status=exc.status,
            ) from exc
        raise PlatformError(
            "Could not verify the platform agent. Check the connection and platform availability, then rerun koala submit.",
            status=exc.status,
        ) from exc
    if (
        not isinstance(profile, dict)
        or profile.get("actor_type") != "agent"
        or not isinstance(profile.get("id"), str)
        or not profile["id"].strip()
    ):
        raise PlatformError(
            "The credential did not identify a registered agent. Use an agent API key, not a human access token.\n"
            + AGENT_SETUP_GUIDE
        )
    print("Registered platform agent verified with KOALA_AGENT_API_KEY.")
    return profile


class Selection(StrictModel):
    run: str
    run_id: str
    manuscript_hash: str
    artifact_hashes: dict[str, str]
    argument_ids: list[str] = Field(min_length=1)
    payload_hashes: dict[str, str]
    target: dict[str, Any]
    coverage: dict[str, Any]
    allow_partial: bool
    confirm_version: bool
    checksum: str = ""


def argument_payload(argument: Argument, result: ReviewResult) -> dict[str, str]:
    sources = {s.id: s for s in result.sources}
    lines = [f"Target: {argument.target}", f"Rationale: {argument.rationale}"]
    for evidence in argument.evidence:
        source = sources[evidence.source_id]
        locator = (
            f"physical page {evidence.page}"
            if evidence.page
            else f"lines {evidence.line_start}-{evidence.line_end}"
        )
        lines += [
            f"Source: {source.name}; SHA-256: {source.content_hash}; {locator}; span: {evidence.span_id}",
            f"Excerpt: {evidence.excerpt}",
        ]
    lines += [
        "Limitations: " + ("; ".join(argument.limitations) or "None recorded"),
        "Absence scope: " + (", ".join(argument.absence_scope) or "None"),
    ]
    payload = {
        "claim": argument.statement,
        "position": "positive" if argument.kind == "praise" else "negative",
        "evidence": "\n".join(lines),
    }
    if len(payload["claim"]) > 10000 or len(payload["evidence"]) > 10000:
        raise ValueError(
            "Selected claim or evidence exceeds 10,000 characters; no truncation is permitted"
        )
    return payload


def load_review(workspace: PaperWorkspace, run: Path) -> ReviewResult:
    data = read_json(run / "arguments.json")
    result = ReviewResult.model_validate(
        {
            **data,
            "sources": read_json(run / "sources.json"),
            "manifest": read_json(run / "manifest.json"),
            "diagnostics": read_json(run / "diagnostics.json"),
        }
    )
    if result.status == "failed" or not result.arguments:
        raise ValueError("Run has no usable arguments")
    if (
        result.manifest.get("run_id") != result.run_id
        or result.manifest.get("status") != result.status
    ):
        raise ValueError("Run artifacts disagree")
    if result.paper.get("content_hash") != file_hash(workspace.manuscript):
        raise ValueError("Workspace manuscript differs from reviewed manuscript")
    paths = [workspace.manuscript, *workspace.sources]
    if len(paths) != len(result.sources):
        raise ValueError("Workspace supporting sources differ from review")

    # Re-extract under the same bounded reader before trusting stored excerpts.
    async def extract() -> list:
        return [await read_source_async(path, 30) for path in paths]

    actual = asyncio.run(extract())
    if [s.model_dump() for s in actual] != [s.model_dump() for s in result.sources]:
        raise ValueError("Source snapshots differ from workspace files")
    if result.manifest.get("sources") != {s.id: s.content_hash for s in result.sources}:
        raise ValueError("Source hashes disagree with manifest")
    coverage = result.manifest.get("coverage")
    if (
        not isinstance(coverage, dict)
        or not {"inspected_spans", "skipped_spans", "extraction_gaps"}
        <= coverage.keys()
    ):
        raise ValueError("Review coverage is unavailable")
    spans = {span.id: span for source in result.sources for span in source.spans}
    inspected = set(coverage["inspected_spans"])
    skipped = set(coverage["skipped_spans"])
    if inspected & skipped or inspected | skipped != set(spans):
        raise ValueError("Review coverage is inconsistent")
    if coverage["extraction_gaps"] != {s.id: s.gaps for s in result.sources}:
        raise ValueError("Extraction coverage is inconsistent")
    if len({a.id for a in result.arguments}) != len(result.arguments):
        raise ValueError("Duplicate local argument IDs")
    for argument in result.arguments:
        error = check_evidence(argument, spans, inspected)
        if error or any(
            argument.local_checks.get(k) != "passed"
            for k in (
                "schema",
                "source_resolution",
                "atomicity",
                "support",
                "duplicate",
            )
        ):
            raise ValueError("Saved argument failed evidence or local-check validation")
    return result


def _partial(result: ReviewResult) -> bool:
    coverage = result.manifest["coverage"]
    return (
        result.status == "partial"
        or bool(coverage["skipped_spans"])
        or any(coverage["extraction_gaps"].values())
    )


def prepare(
    workspace: PaperWorkspace,
    *,
    run: str | None,
    arguments: list[str],
    select: bool,
    allow_partial: bool,
    confirm_version: bool,
) -> tuple[Selection, ReviewResult]:
    if workspace.identity is None:
        raise ValueError(
            "Submission requires an arXiv identity in paper.yaml; local-only papers remain reviewable"
        )
    destination = workspace.state / "selection.json"
    fresh = select or bool(arguments) or run is not None or not destination.exists()
    saved = None if fresh else Selection.model_validate(read_json(destination))
    if saved and saved.checksum != digest(saved.model_dump(exclude={"checksum"})):
        raise ValueError("Saved selection changed; explicitly reselect with --select")
    run_path = (
        (workspace.root / run).resolve()
        if run
        else Path(saved.run)
        if saved
        else workspace.last_run()
    )
    result = load_review(workspace, run_path)
    coverage = result.manifest["coverage"]
    print(f"Run {result.run_id}: {result.status}; coverage: {json.dumps(coverage)}")
    for index, argument in enumerate(result.arguments, 1):
        print(f"{index}. [{argument.id}] {argument.kind}: {argument.statement}")
    if saved:
        selected = saved.argument_ids
        allow_partial = allow_partial or saved.allow_partial
        confirm_version = confirm_version or saved.confirm_version
    else:
        selected = arguments
        if not selected:
            if not sys.stdin.isatty():
                raise ValueError(
                    "Noninteractive submission requires repeatable --argument IDs or numbers"
                )
            selected = input(
                "Select argument numbers or IDs (comma separated): "
            ).split(",")
        selected = [value.strip() for value in selected]
        selected = [
            result.arguments[int(value) - 1].id
            if value.isdecimal() and 1 <= int(value) <= len(result.arguments)
            else value
            for value in selected
        ]
    if (
        not selected
        or len(set(selected)) != len(selected)
        or not set(selected) <= {a.id for a in result.arguments}
    ):
        raise ValueError("Choose distinct argument IDs or displayed numbers")
    if _partial(result) and not allow_partial:
        raise ValueError(
            "Partial coverage requires --allow-partial; missing coverage is shown above"
        )
    target = {
        "arxiv": workspace.identity[0],
        "version": workspace.identity[1],
        "configured_platform_paper_id": workspace.config.platform_paper_id,
        "platform_paper_id": saved.target["platform_paper_id"]
        if saved
        else workspace.config.platform_paper_id,
        "platform_version": saved.target.get("platform_version") if saved else None,
    }
    selection = Selection(
        run=str(run_path),
        run_id=result.run_id,
        manuscript_hash=file_hash(workspace.manuscript),
        artifact_hashes={name: file_hash(run_path / name) for name in ARTIFACTS},
        argument_ids=selected,
        payload_hashes={
            a.id: digest(argument_payload(a, result))
            for a in result.arguments
            if a.id in selected
        },
        target=target,
        coverage=coverage,
        allow_partial=allow_partial,
        confirm_version=confirm_version,
    )
    if saved:
        for key in (
            "run",
            "run_id",
            "manuscript_hash",
            "artifact_hashes",
            "argument_ids",
            "payload_hashes",
            "target",
            "coverage",
        ):
            if getattr(saved, key) != getattr(selection, key):
                raise ValueError(
                    "Saved selection or review changed; explicitly reselect with --select"
                )
    selection.checksum = digest(selection.model_dump(exclude={"checksum"}))
    write_json(destination, selection.model_dump())
    return selection, result


@contextmanager
def submission_lock(workspace: PaperWorkspace) -> Iterator[None]:
    workspace.state.mkdir(parents=True, exist_ok=True)
    path = workspace.state / "submit.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(
            "Submission lock exists; ensure no submit process is running before removing .koala/submit.lock"
        ) from exc
    os.close(fd)
    try:
        yield
    finally:
        path.unlink()


class Journal:
    def __init__(self, workspace: PaperWorkspace) -> None:
        self.path = workspace.state / "delivery.jsonl"
        self.events: list[dict] = []
        if self.path.exists():
            if self.path.stat().st_size > 32 * 1024 * 1024:
                raise ValueError("Delivery journal exceeds size limit")
            for line in self.path.read_text(encoding="utf-8").splitlines():
                self.events.append(json.loads(line))

    def append(self, event: dict) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.events.append(event)

    def latest(self, key: str) -> dict | None:
        return next(
            (event for event in reversed(self.events) if event.get("key") == key), None
        )


@contextmanager
def preserve_outcomes(journal: Journal, enabled: bool) -> Iterator[None]:
    """Keep mixed or unresolved delivery distinct from a preflight failure."""
    start = len(journal.events)
    try:
        yield
    except PlatformError as exc:
        latest = {event["key"]: event["status"] for event in journal.events}
        current = {event["key"]: event["status"] for event in journal.events[start:]}
        if enabled and (
            any(
                status in {"intent", "uncertain", "conflict"}
                for status in latest.values()
            )
            or "receipt" in current.values()
        ):
            exc.uncertain = True
        raise


def _matching(existing: list[dict], payload: dict, agent_id: str) -> dict | None:
    same = [
        a
        for a in existing
        if a.get("author_id") == agent_id and a.get("claim") == payload["claim"]
    ]
    if len(same) > 1:
        raise ValueError("Ambiguous existing argument")
    if same and any(same[0].get(k) != v for k, v in payload.items()):
        raise ValueError(
            "An immutable argument with this claim has different evidence or position"
        )
    return same[0] if same else None


def resolve_import(
    api: PlatformClient,
    workspace: PaperWorkspace,
    selection: Selection,
    journal: Journal,
) -> dict:
    identity = workspace.identity
    key = "import:" + identity[0]
    previous = journal.latest(key)
    found = api.find_paper(
        identity[0], workspace.config.title, selection.target["platform_paper_id"]
    )
    if found:
        if previous and previous["status"] in {"intent", "uncertain", "conflict"}:
            journal.append(
                {
                    "key": key,
                    "status": "receipt",
                    "paper_id": found["id"],
                    "reconciled": True,
                }
            )
        return found
    if previous and previous["status"] in {
        "intent",
        "uncertain",
        "conflict",
        "receipt",
    }:
        raise PlatformError(
            "Prior import is unresolved or inaccessible; no repeat import will be attempted",
            uncertain=True,
        )
    owner = api.request("GET", "users/me", actor="owner")
    if (
        owner.get("actor_type") != "human"
        or not isinstance(owner.get("papers_available"), int)
        or owner["papers_available"] < 1
    ):
        raise PlatformError(
            "Import requires a human account with paper allowance; check the owner dashboard"
        )
    # Repeat immediately before creating: lookup failures never authorize a POST.
    found = api.find_paper(identity[0], workspace.config.title)
    if found:
        return found
    url = (
        "https://arxiv.org/abs/"
        + identity[0]
        + (f"v{identity[1]}" if identity[1] else "")
    )
    journal.append({"key": key, "status": "intent", "url": url})
    try:
        found = api.request("POST", "papers/arxiv", actor="owner", payload={"url": url})
        if not isinstance(found, dict) or not isinstance(found.get("id"), str):
            raise PlatformError("Import returned no paper ID", uncertain=True)
    except PlatformError as exc:
        status = (
            "conflict"
            if exc.status == 409
            else "uncertain"
            if exc.uncertain
            else "failed"
        )
        journal.append({"key": key, "status": status, "http_status": exc.status})
        if exc.uncertain or exc.status == 409:
            try:
                found = api.find_paper(identity[0], workspace.config.title)
            except (PlatformError, ValueError) as lookup_error:
                raise PlatformError(
                    "Import reconciliation failed; delivery remains unresolved",
                    uncertain=True,
                ) from lookup_error
            if not found:
                raise PlatformError(
                    "Import delivery unresolved or duplicate inaccessible; do not repeat upload",
                    uncertain=True,
                ) from exc
        else:
            raise
    # Persist the server identifier before version validation or argument requests.
    journal.append({"key": key, "status": "receipt", "paper_id": found["id"]})
    return found


def pin_paper(workspace: PaperWorkspace, selection: Selection, paper: dict) -> None:
    verify_paper(paper, workspace.identity, selection.confirm_version)
    version = remote_identity(paper)[1]
    previous_version = selection.target.get("platform_version")
    if previous_version is not None and previous_version != version:
        raise ValueError(
            "Platform version changed since selection; inspect it and reselect"
        )
    selection.target.update(platform_paper_id=paper["id"], platform_version=version)
    selection.checksum = digest(selection.model_dump(exclude={"checksum"}))
    write_json(workspace.state / "selection.json", selection.model_dump())


def revalidate(
    workspace: PaperWorkspace, selection: Selection, result: ReviewResult
) -> None:
    if read_json(workspace.state / "selection.json") != selection.model_dump():
        raise ValueError("Selection changed during submission")
    if any(
        file_hash(Path(selection.run) / name) != value
        for name, value in selection.artifact_hashes.items()
    ):
        raise ValueError("Review artifacts changed during submission")
    for path, source in zip(
        [workspace.manuscript, *workspace.sources], result.sources, strict=True
    ):
        if file_hash(path) != source.content_hash:
            raise ValueError("Source changed during submission")


def export_payloads(
    workspace: PaperWorkspace,
    selection: Selection,
    selected: dict[str, dict],
    paper_id: str,
) -> None:
    """Save the exact request objects separately from review artifacts."""
    try:
        UUID(paper_id)
    except ValueError as exc:
        raise ValueError("Platform export requires a valid paper UUID") from exc
    payloads = [
        {**selected[aid], "paper_id": paper_id} for aid in selection.argument_ids
    ]
    destination = workspace.state / "exports" / selection.checksum / "arguments.json"
    if destination.exists():
        if read_json(destination) != payloads:
            raise ValueError("Existing platform export changed; refusing to overwrite")
    else:
        write_json(destination, payloads)
    print(f"Platform payload export: {destination}")


def submit(
    workspace: PaperWorkspace,
    *,
    send: bool = False,
    run: str | None = None,
    arguments: list[str] | None = None,
    select: bool = False,
    allow_partial: bool = False,
    confirm_version: bool = False,
    wait: float = 0,
) -> int:
    if not 0 <= wait <= 300:
        raise ValueError("--wait must be between 0 and 300 seconds")
    with submission_lock(workspace):
        selection, result = prepare(
            workspace,
            run=run,
            arguments=arguments or [],
            select=select,
            allow_partial=allow_partial,
            confirm_version=confirm_version,
        )
        journal = Journal(workspace)
        initial_events = len(journal.events)
        with PlatformClient() as api, preserve_outcomes(journal, send):
            profile = check_submission_agent(api, required=send)
            if send and not profile.get("github_repo"):
                raise ValueError(
                    "Add a public audit repository to the registered agent at https://koala.science/dashboard; "
                    "include prompts, code, and interaction logs before submission"
                )
            found = api.find_paper(
                workspace.identity[0],
                workspace.config.title,
                selection.target["platform_paper_id"],
            )
            if found:
                pin_paper(workspace, selection, found)
                print(f"Use existing paper {found['id']}")
            else:
                prior_import = journal.latest("import:" + workspace.identity[0])
                if prior_import and prior_import["status"] in {
                    "intent",
                    "uncertain",
                    "conflict",
                    "receipt",
                }:
                    raise PlatformError(
                        "Prior import remains unresolved or inaccessible; no repeat upload is permitted",
                        uncertain=True,
                    )
                print(
                    f"Import arXiv {workspace.identity[0]} using human paper allowance, then submit selected arguments"
                )
            selected = {
                a.id: argument_payload(a, result)
                for a in result.arguments
                if a.id in selection.argument_ids
            }
            print(json.dumps(selected, ensure_ascii=False, indent=2))
            if found:
                export_payloads(workspace, selection, selected, found["id"])
            else:
                print("Platform payload export pending paper ID resolution")
            if not send:
                print("Preview saved. No papers or arguments were created.")
                return 0
            assert profile is not None
            if workspace.identity[1] is None and not selection.confirm_version:
                raise ValueError(
                    "Reviewed arXiv version unavailable; inspect it and pass --confirm-version"
                )
            agent_id = profile["id"]
            existing = api.arguments(found["id"], agent_id) if found else []
            remaining = (
                sum(
                    _matching(existing, {**p, "paper_id": found["id"]}, agent_id)
                    is None
                    for p in selected.values()
                )
                if found
                else len(selected)
            )
            budget = profile.get("budget")
            if (
                type(budget) not in {int, float}
                or not math.isfinite(budget)
                or budget < remaining
            ):
                raise PlatformError(
                    "Insufficient agent submission budget; check the owner dashboard"
                )
            revalidate(workspace, selection, result)
            found = resolve_import(api, workspace, selection, journal)
            revalidate(workspace, selection, result)
            pin_paper(workspace, selection, found)
            paper_id = found["id"]
            export_payloads(workspace, selection, selected, paper_id)
            # Revalidate local artifacts after network preflight, before sending.
            load_review(workspace, Path(selection.run))
            confirmed: list[dict] = []
            for argument_id in selection.argument_ids:
                payload = {**selected[argument_id], "paper_id": paper_id}
                key = "argument:" + digest([agent_id, paper_id, payload["claim"]])
                existing = api.arguments(paper_id, agent_id)
                receipt = _matching(existing, payload, agent_id)
                previous = journal.latest(key)
                if receipt:
                    journal.append(
                        {
                            "key": key,
                            "status": "receipt",
                            "receipt": receipt,
                            "reconciled": True,
                        }
                    )
                elif previous and previous["status"] in {
                    "intent",
                    "uncertain",
                    "receipt",
                    "conflict",
                }:
                    print(
                        "Prior argument delivery remains unresolved; no repost was attempted"
                    )
                    return 4
                else:
                    revalidate(workspace, selection, result)
                    verify_paper(
                        api.paper(paper_id),
                        workspace.identity,
                        selection.confirm_version,
                    )
                    journal.append(
                        {
                            "key": key,
                            "status": "intent",
                            "argument_id": argument_id,
                            "selection": selection.checksum,
                            "payload": payload,
                            "payload_hash": digest(payload),
                        }
                    )
                    try:
                        receipt = api.request(
                            "POST", "arguments/", actor="agent", payload=payload
                        )
                        if (
                            not isinstance(receipt, dict)
                            or not isinstance(receipt.get("id"), str)
                            or receipt.get("author_id") != agent_id
                            or any(receipt.get(k) != v for k, v in payload.items())
                        ):
                            raise PlatformError(
                                "Argument receipt could not be verified", uncertain=True
                            )
                    except PlatformError as exc:
                        journal.append(
                            {
                                "key": key,
                                "status": "conflict"
                                if exc.status == 409
                                else "uncertain"
                                if exc.uncertain
                                else "failed",
                                "http_status": exc.status,
                            }
                        )
                        if exc.uncertain or exc.status == 409:
                            try:
                                receipt = _matching(
                                    api.arguments(paper_id, agent_id), payload, agent_id
                                )
                            except (PlatformError, ValueError) as lookup_error:
                                raise PlatformError(
                                    "Argument reconciliation failed; delivery remains unresolved",
                                    uncertain=True,
                                ) from lookup_error
                            if receipt is None:
                                print(
                                    "Argument delivery unresolved; rerun to reconcile, never automatically repost"
                                )
                                return 4
                        else:
                            print(str(exc))
                            delivered = confirmed or any(
                                event["status"] == "receipt"
                                for event in journal.events[initial_events:]
                            )
                            return 4 if delivered else 3
                    journal.append(
                        {"key": key, "status": "receipt", "receipt": receipt}
                    )
                confirmed.append(receipt)
                print(
                    f"Receipt {receipt['id']}: {receipt.get('state', 'unknown')}; receipt does not imply acceptance"
                )
            if wait:
                deadline = time.monotonic() + wait
                api.deadline = deadline
                while True:
                    rows = api.pages(f"papers/{paper_id}/arguments")
                    states = {r["id"]: r.get("state", "unknown") for r in rows}
                    current = {
                        r["id"]: states.get(r["id"], "unknown") for r in confirmed
                    }
                    print("Platform checks: " + json.dumps(current))
                    if all(
                        state in {"accepted", "rejected"} for state in current.values()
                    ):
                        return (
                            0
                            if all(state == "accepted" for state in current.values())
                            else 4
                        )
                    if time.monotonic() >= deadline:
                        return 4
                    time.sleep(min(2, max(0, deadline - time.monotonic())))
            return 0
