"""Autonomous reviewing agent for koala.science."""

from .config import LoadedAgent, load_config
from .loop import AgentLoop
from .platform import PlatformClient, PlatformError
from .runner import Reviewer
from .types import (
    Argument,
    Candidate,
    Check,
    Evidence,
    KnownArgument,
    Limits,
    Message,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    QualityVerdict,
    Ranking,
    ReviewResult,
    Source,
    Span,
)

__all__ = [
    "AgentLoop",
    "Argument",
    "Candidate",
    "Check",
    "Evidence",
    "KnownArgument",
    "Limits",
    "LoadedAgent",
    "Message",
    "ModelProvider",
    "ModelRequest",
    "ModelResponse",
    "PlatformClient",
    "PlatformError",
    "QualityVerdict",
    "Ranking",
    "ReviewResult",
    "Reviewer",
    "Source",
    "Span",
    "load_config",
]
__version__ = "0.2.0"
