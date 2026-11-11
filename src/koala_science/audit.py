"""Append-only logs and run state, laid out for the agent's public audit repository.

logs/
  arguments.jsonl         every submitted argument, then each outcome change
  state.json              reviewed and skipped papers, live arguments
  runs/<run>/run.json     configuration, instruction texts, start/end, summary
  runs/<run>/calls.jsonl  every platform request, download, and model call
  runs/<run>/selection.jsonl  candidates, filters, ranking, and reasons
  runs/<run>/papers/<id>/ review artifacts for each reviewed paper

The agent only writes these files. Publishing them is the user's job.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .types import ModelProvider, ModelRequest, ModelResponse


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_jsonl(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": now(), **entry}, ensure_ascii=False) + "\n")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(path.suffix + ".tmp")
    staged.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(staged, path)


class AuditLog:
    def __init__(self, root: Path, *, dry_run: bool = False) -> None:
        self.root = root
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.run_id = f"{stamp}-{uuid.uuid4().hex[:6]}" + ("-dry" if dry_run else "")
        self.run_dir = root / "runs" / self.run_id
        self.run_dir.mkdir(parents=True)
        self.dry_run = dry_run

    def call(self, entry: dict[str, Any]) -> None:
        append_jsonl(self.run_dir / "calls.jsonl", entry)

    def selection(self, entry: dict[str, Any]) -> None:
        append_jsonl(self.run_dir / "selection.jsonl", entry)

    def argument(self, entry: dict[str, Any]) -> None:
        # Dry-run arguments were never submitted, so they stay out of the summary.
        target = self.run_dir if self.dry_run else self.root
        append_jsonl(target / "arguments.jsonl", {"run": self.run_id, **entry})

    def paper_dir(self, paper_id: str) -> Path:
        return self.run_dir / "papers" / paper_id

    def run_record(self, data: dict[str, Any]) -> None:
        path = self.run_dir / "run.json"
        current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        write_json(path, {**current, **data})


class State:
    """What the agent already did, so restarts neither repeat nor forget work."""

    def __init__(self, path: Path | None, *, readonly: bool = False) -> None:
        self.path = path
        self.readonly = readonly
        data = (
            json.loads(path.read_text(encoding="utf-8"))
            if path is not None and path.exists()
            else {}
        )
        self.reviewed: dict[str, dict[str, Any]] = data.get("reviewed", {})
        self.skipped: dict[str, dict[str, Any]] = data.get("skipped", {})
        self.arguments: dict[str, dict[str, Any]] = data.get("arguments", {})

    def seen(self, paper_id: str) -> bool:
        return paper_id in self.reviewed or paper_id in self.skipped

    def live_on(self, paper_id: str) -> int:
        return sum(
            1
            for a in self.arguments.values()
            if a["paper_id"] == paper_id
            and a.get("state") in {None, "pending", "accepted"}
        )

    def pending(self) -> dict[str, list[str]]:
        papers: dict[str, list[str]] = {}
        for argument_id, a in self.arguments.items():
            if a.get("state") in {None, "pending"}:
                papers.setdefault(a["paper_id"], []).append(argument_id)
        return papers

    def save(self) -> None:
        if self.path is not None and not self.readonly:
            write_json(
                self.path,
                {
                    "reviewed": self.reviewed,
                    "skipped": self.skipped,
                    "arguments": self.arguments,
                },
            )


class LoggedProvider:
    """Record every model request and response in calls.jsonl."""

    def __init__(self, inner: ModelProvider, log: AuditLog, role: str) -> None:
        self.inner, self.log, self.role = inner, log, role

    async def generate(self, request: ModelRequest) -> ModelResponse:
        started = time.monotonic()
        entry: dict[str, Any] = {
            "kind": "model",
            "role": self.role,
            "model": request.model,
            "messages": [m.model_dump() for m in request.messages],
            "output_schema": request.output_schema.get("title"),
        }
        try:
            response = await self.inner.generate(request)
        except BaseException as exc:
            entry.update(error=type(exc).__name__, seconds=time.monotonic() - started)
            self.log.call(entry)
            raise
        entry.update(
            response=response.text,
            resolved_model=response.model,
            input_tokens=response.input_tokens,
            cached_input_tokens=response.cached_input_tokens,
            output_tokens=response.output_tokens,
            seconds=round(time.monotonic() - started, 3),
        )
        self.log.call(entry)
        return response
