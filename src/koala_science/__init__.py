"""Local, evidence-linked scientific review agents."""

from .runner import Agent
from .types import (
    Argument,
    BackendBudget,
    Candidate,
    Evidence,
    Limits,
    Message,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    PaperContext,
    Proposals,
    ReviewBackend,
    ReviewResult,
    Source,
    Span,
    TaskEnvelope,
    TaskResult,
)

__all__ = [
    "Agent",
    "Argument",
    "BackendBudget",
    "Candidate",
    "Evidence",
    "Limits",
    "Message",
    "ModelProvider",
    "ModelRequest",
    "ModelResponse",
    "PaperContext",
    "Proposals",
    "ReviewBackend",
    "ReviewResult",
    "Source",
    "Span",
    "TaskEnvelope",
    "TaskResult",
]
__version__ = "0.1.0"
