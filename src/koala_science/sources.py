"""Located source snapshots and deterministic quote checks."""

import asyncio
import hashlib
import json
import re
import subprocess
import sys
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from .types import Candidate, Source, Span

MAX_INPUT_BYTES = 100 * 1024 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_SOURCE_SPANS = 10000
MAX_PDF_PAGES = 1000


async def read_source_async(path: str | Path, timeout: float) -> Source:
    """Isolate PDF parsing so the coordinator can terminate it at its deadline."""
    if timeout <= 0:
        raise ValueError("Input extraction exceeded the run deadline")
    if Path(path).suffix.lower() != ".pdf":
        return read_source(path)
    process = subprocess.Popen(  # noqa: ASYNC220 -- Windows selector loops need Popen; all waits run in a thread
        [
            sys.executable,
            "-I",
            "-m",
            "koala_science.extract_worker",
            str(Path(path).resolve()),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    communication = asyncio.create_task(asyncio.to_thread(process.communicate))
    try:
        stdout, _ = await asyncio.wait_for(asyncio.shield(communication), timeout)
    except (asyncio.TimeoutError, asyncio.CancelledError) as exc:
        if process.poll() is None:
            process.kill()
        await asyncio.shield(communication)
        if isinstance(exc, asyncio.CancelledError):
            raise
        raise ValueError(
            "PDF extraction exceeded the run deadline; supply a text input"
        ) from exc
    if process.returncode != 0:
        raise ValueError("PDF extraction failed; supply a readable text input")
    try:
        payload = json.loads(stdout)
        if "error" in payload:
            raise ValueError(payload["error"])
        return Source.model_validate(payload["source"])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("PDF extraction worker returned invalid output") from exc


def normalize(text: str) -> str:
    """Collapse Unicode whitespace; preserve case, punctuation and spelling."""
    return " ".join(text.split())


def read_source(path: str | Path) -> Source:
    file = Path(path)
    if file.suffix.lower() not in {".pdf", ".md", ".txt"}:
        raise ValueError("Input must be PDF, Markdown, or text")
    with file.open("rb") as handle:
        raw = handle.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(
            "Input exceeds the 100 MiB extraction limit; supply a text version"
        )
    digest = hashlib.sha256(raw).hexdigest()
    source_id = "src-" + digest[:20]
    spans, gaps = [], []
    text_bytes = 0

    def append_span(span: Span) -> None:
        nonlocal text_bytes
        text_bytes += len(span.text.encode("utf-8"))
        if text_bytes > MAX_TEXT_BYTES or len(spans) >= MAX_SOURCE_SPANS:
            raise ValueError(
                "Extracted source exceeds text or span limit; supply a smaller input"
            )
        spans.append(span)

    if file.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(BytesIO(raw))
            if len(reader.pages) > MAX_PDF_PAGES:
                raise ValueError("PDF exceeds page limit; supply a smaller input")
            for page_number, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                if not text.strip():
                    gaps.append(f"No text on physical page {page_number}")
                for offset in range(0, len(text), 1600):
                    chunk = text[offset : offset + 1600]
                    if chunk.strip():
                        append_span(
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
        if len(raw) > MAX_TEXT_BYTES:
            raise ValueError(
                "Text input exceeds extraction size limit; supply a smaller input"
            )
        lines = raw.decode("utf-8-sig").splitlines()
        section = "document"
        for number, line in enumerate(lines, 1):
            if re.match(r"^#{1,6}\s", line):
                section = line.lstrip("# ")
            for offset in range(0, len(line), 1600):
                chunk = line[offset : offset + 1600]
                if chunk.strip():
                    append_span(
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
