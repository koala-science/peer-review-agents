"""Located source snapshots and deterministic quote checks."""

import hashlib
import re
from pathlib import Path

from pypdf import PdfReader

from .types import Candidate, Source, Span


def normalize(text: str) -> str:
    """Collapse Unicode whitespace; preserve case, punctuation and spelling."""
    return " ".join(text.split())


def read_source(path: str | Path) -> Source:
    file = Path(path)
    if file.suffix.lower() not in {".pdf", ".md", ".txt"}:
        raise ValueError("Input must be PDF, Markdown, or text")
    if file.stat().st_size > 100 * 1024 * 1024:
        raise ValueError(
            "Input exceeds the 100 MiB extraction limit; supply a text version"
        )
    raw = file.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    source_id = "src-" + digest[:20]
    spans, gaps = [], []
    if file.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(file)
            for page_number, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                if not text.strip():
                    gaps.append(f"No text on physical page {page_number}")
                for offset in range(0, len(text), 1600):
                    chunk = text[offset : offset + 1600]
                    if chunk.strip():
                        spans.append(
                            Span(
                                id=f"{source_id}:p{page_number}:{offset}",
                                source_id=source_id,
                                text=chunk,
                                page=page_number,
                                section=f"page {page_number}",
                            )
                        )
        except Exception as exc:
            raise ValueError(
                "PDF extraction failed; supply a readable text input"
            ) from exc
    else:
        lines = raw.decode("utf-8-sig").splitlines()
        section = "document"
        for number, line in enumerate(lines, 1):
            if re.match(r"^#{1,6}\s", line):
                section = line.lstrip("# ")
            for offset in range(0, len(line), 1600):
                chunk = line[offset : offset + 1600]
                if chunk.strip():
                    spans.append(
                        Span(
                            id=f"{source_id}:l{number}:{offset}",
                            source_id=source_id,
                            text=chunk,
                            line_start=number,
                            line_end=number,
                            section=section,
                        )
                    )
    if not spans:
        raise ValueError(
            "No usable text; scanned PDFs need OCR or a supplied text input"
        )
    return Source(
        id=source_id, name=file.name, content_hash=digest, spans=spans, gaps=gaps
    )


def check_evidence(
    candidate: Candidate, spans: dict[str, Span], inspected: set[str]
) -> str | None:
    for evidence in candidate.evidence:
        span = spans.get(evidence.span_id)
        if span is None or span.source_id != evidence.source_id:
            return "Unknown source or span"
        if span.id not in inspected:
            return "Evidence references an unread span"
        if (span.page, span.line_start, span.line_end) != (
            evidence.page,
            evidence.line_start,
            evidence.line_end,
        ):
            return "Evidence locator does not match its span"
        if normalize(evidence.excerpt) not in normalize(span.text):
            return "Excerpt does not match the source"
    if not set(candidate.absence_scope).issubset(inspected):
        return "Absence scope includes unread spans"
    return None
