"""Turn a locally checked argument into the platform's argument request body."""

from __future__ import annotations

from .types import Argument

MAX_FIELD_CHARS = 10000


def argument_payload(argument: Argument, paper_id: str) -> dict[str, str]:
    """Claim, position, and self-contained evidence: rationale plus located quotes.

    Raises instead of truncating, so a submitted argument always carries all of
    the evidence that passed the local checks.
    """
    lines = [argument.rationale, "", "From the paper:"]
    for evidence in argument.evidence:
        where = (
            f"Page {evidence.page}"
            if evidence.page
            else f"Lines {evidence.line_start}-{evidence.line_end}"
            if evidence.line_start
            else "Text"
        )
        lines.append(f'- {where}: "{" ".join(evidence.excerpt.split())}"')
    if argument.limitations:
        lines += ["", "Scope: " + " ".join(argument.limitations)]
    payload = {
        "paper_id": paper_id,
        "claim": argument.statement,
        "position": "positive" if argument.kind == "praise" else "negative",
        "evidence": "\n".join(lines),
    }
    if (
        len(payload["claim"]) > MAX_FIELD_CHARS
        or len(payload["evidence"]) > MAX_FIELD_CHARS
    ):
        raise ValueError(
            "Claim or evidence exceeds 10,000 characters; nothing truncated"
        )
    return payload
