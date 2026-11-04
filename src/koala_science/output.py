"""Artifact serialization with staged replacement and an interruption journal."""

import html
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from .types import ReviewResult


def plain_text(text: str) -> str:
    """Escape active HTML and Markdown in untrusted model and source strings."""
    return re.sub(r"([\\`*_{}\[\]()#+.!|~-])", r"\\\1", html.escape(text, quote=False))


def markdown(result: ReviewResult) -> str:
    lines = [
        f"# Review: {plain_text(result.paper['name'])}",
        "",
        f"Status: {result.status}. Local checks are advisory.",
        "",
    ]
    for argument in result.arguments:
        lines += [
            f"## {plain_text(argument.id)}: {argument.kind}",
            "",
            plain_text(argument.statement),
            "",
            f"Target: {plain_text(argument.target)}",
            "",
            plain_text(argument.rationale),
            "",
        ]
        for evidence in argument.evidence:
            location = (
                f"physical page {evidence.page}"
                if evidence.page
                else f"lines {evidence.line_start}-{evidence.line_end}"
            )
            lines += [
                f"Source {plain_text(evidence.source_id)}, {location}, span {plain_text(evidence.span_id)}:",
                "",
                "> " + plain_text(evidence.excerpt).replace("\n", "\n> "),
                "",
            ]
        lines += [
            "Limitations: "
            + (plain_text("; ".join(argument.limitations)) or "None recorded."),
            "",
        ]
    if not result.arguments:
        lines += ["No arguments passed all local checks.", ""]
    return "\n".join(lines)


def save_result(result: ReviewResult, directory: str | Path) -> None:
    target = Path(directory).resolve()
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError("Output directory must be new or empty")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
    try:
        artifacts = {
            "arguments.json": result.model_dump(
                mode="json", exclude={"diagnostics", "manifest", "sources"}
            ),
            "diagnostics.json": result.diagnostics,
            "manifest.json": result.manifest,
            "sources.json": [
                source.model_dump(mode="json") for source in result.sources
            ],
        }
        for name, payload in artifacts.items():
            (stage / name).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        (stage / "arguments.md").write_text(markdown(result), encoding="utf-8")
        if target.exists():
            target.rmdir()
        os.replace(stage, target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
