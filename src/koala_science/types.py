"""Versioned public contracts for local reviews."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, strict=True, allow_inf_nan=False
    )


class Message(StrictModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ModelRequest(StrictModel):
    model: str
    messages: list[Message]
    output_schema: dict[str, Any]
    max_output_tokens: int
    timeout_seconds: float


class ModelResponse(StrictModel):
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...


class Limits(StrictModel):
    max_arguments: int = Field(8, ge=1)
    max_concurrency: int = Field(2, ge=1)
    max_model_calls: int = Field(24, ge=1)
    max_tasks: int = Field(12, ge=1)
    max_candidates_per_task: int = Field(4, ge=1)
    max_input_tokens_per_call: int = Field(16000, ge=256)
    max_output_tokens_per_call: int = Field(2000, ge=1)
    max_run_seconds: float = Field(600, gt=0)
    request_timeout_seconds: float = Field(60, gt=0)


class Span(StrictModel):
    id: str
    source_id: str
    text: str
    section: str = "document"
    page: int | None = Field(None, ge=1)
    line_start: int | None = Field(None, ge=1)
    line_end: int | None = Field(None, ge=1)


class Source(StrictModel):
    id: str
    name: str
    content_hash: str
    spans: list[Span]
    gaps: list[str] = Field(default_factory=list)


class Evidence(StrictModel):
    source_id: str
    span_id: str
    page: int | None = Field(None, ge=1)
    line_start: int | None = Field(None, ge=1)
    line_end: int | None = Field(None, ge=1)
    excerpt: str = Field(min_length=1)


class Candidate(StrictModel):
    kind: Literal["criticism", "praise"]
    target: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)
    absence_scope: list[str] = Field(default_factory=list)


class Proposals(StrictModel):
    candidates: list[Candidate]


class BackendResult(Proposals):
    """Proposals and explicit source coverage reported by an external backend."""

    inspected_span_ids: list[str]


class Verdict(StrictModel):
    decision: Literal["supported", "unsupported", "uncertain"]
    atomic: bool
    reason: str
    revision: str | None = None
    requested_span_ids: list[str] = Field(default_factory=list)


class ClaimFocus(StrictModel):
    claim: str = Field(min_length=1, max_length=2000)
    why_it_matters: str = Field(min_length=1, max_length=2000)
    span_ids: list[str] = Field(min_length=1, max_length=512)


class ClaimMap(StrictModel):
    claims: list[ClaimFocus] = Field(max_length=8)


class KnownArgument(StrictModel):
    id: str = Field(min_length=1, max_length=200)
    claim: str = Field(min_length=1, max_length=10000)
    position: Literal["positive", "negative"]


class QualityVerdict(Verdict):
    importance: Literal["substantive", "minor", "uncertain"]
    contribution: str = Field(min_length=1)
    strongest_counterargument: str = Field(min_length=1)
    counterargument_resolved: bool
    novelty: Literal["new", "duplicate", "uncertain"]
    novelty_reason: str = Field(min_length=1)


class Duplicate(StrictModel):
    duplicate: bool
    reason: str


class Provenance(StrictModel):
    agent_name: str
    model: str
    prompt_digest: str
    task_ids: list[str]


class Argument(Candidate):
    id: str
    provenance: Provenance
    local_checks: dict[str, str]


class TaskEnvelope(StrictModel):
    task_id: str
    run_id: str
    agent_name: str
    role: str
    objective: str
    source_ids: list[str]
    span_ids: list[str]
    candidate_ids: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    limits: dict[str, Any]


class TaskResult(StrictModel):
    task: TaskEnvelope
    status: Literal["complete", "failed", "cancelled"]
    output: dict[str, Any] | None = None
    source_references: list[str] = Field(default_factory=list)
    usage: list[ModelResponse] = Field(default_factory=list, exclude=True)
    error: str | None = None
    prompt_digest: str | None = None
    model: str | None = None


class PaperContext(StrictModel):
    paper: Source
    sources: list[Source]


class BackendBudget(Protocol):
    async def reserve_call(self) -> None: ...
    def report_usage(self, response: ModelResponse) -> None: ...


class ReviewBackend(Protocol):
    supports_budget: Literal[True]

    async def propose(
        self, context: PaperContext, limits: Limits, budget: BackendBudget
    ) -> BackendResult: ...


class ReviewResult(StrictModel):
    schema_version: Literal[1] = 1
    run_id: str
    paper: dict[str, str]
    status: Literal["complete", "partial", "failed"]
    arguments: list[Argument]
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    manifest: dict[str, Any] = Field(default_factory=dict)
    sources: list[Source] = Field(default_factory=list)

    def save(self, directory: str | Path) -> None:
        """Write a complete artifact set to a new or empty directory."""
        from .output import save_result

        save_result(self, directory)
