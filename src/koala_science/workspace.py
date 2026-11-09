"""Paper workspace configuration, immutable run references, and local state."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field

from .config import ConfigLoader, _expand
from .platform import arxiv_identity
from .types import StrictModel


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        data = handle.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise ValueError("State or artifact exceeds size limit")
    return json.loads(data)


def write_json(path: Path, data: Any) -> None:
    """Atomically replace local state after flushing it to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".state-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class PaperConfig(StrictModel):
    schema_version: Literal[1]
    manuscript: str = Field(min_length=1)
    sources: list[str] = Field(default_factory=list)
    config: str = "agent.yaml"
    title: str = ""
    arxiv: str | None = None
    arxiv_version: int | None = Field(default=None, ge=1)
    platform_paper_id: str | None = Field(default=None, min_length=1)


class PaperWorkspace:
    def __init__(self, path: Path, config: PaperConfig) -> None:
        self.path = path.resolve()
        self.root = self.path.parent
        self.config = config
        self.manuscript = (self.root / config.manuscript).resolve()
        self.sources = [(self.root / source).resolve() for source in config.sources]
        self.agent_config = (self.root / config.config).resolve()
        self.state = self.root / ".koala"
        self.identity: tuple[str, int | None] | None = None
        if config.arxiv:
            canonical, version = arxiv_identity(config.arxiv)
            if version and config.arxiv_version and version != config.arxiv_version:
                raise ValueError("Conflicting workspace arXiv versions")
            self.identity = canonical, version or config.arxiv_version
        elif config.arxiv_version:
            raise ValueError("arxiv_version requires arxiv")

    @classmethod
    def load(cls, path: str | Path = "paper.yaml") -> PaperWorkspace:
        path = Path(path)
        with path.open(encoding="utf-8") as handle:
            data = handle.read(1048577)
        if len(data) > 1048576:
            raise ValueError("paper.yaml exceeds size limit")
        try:
            raw = yaml.load(data, Loader=ConfigLoader)
            config = PaperConfig.model_validate(_expand(raw))
        except (yaml.YAMLError, RecursionError) as exc:
            raise ValueError("Invalid paper.yaml") from exc
        return cls(path, config)

    def record_run(self, run: Path, status: str) -> None:
        if status in {"complete", "partial"}:
            write_json(self.state / "last-run.json", {"run": str(run.resolve())})

    def last_run(self) -> Path:
        path = self.state / "last-run.json"
        if not path.exists():
            raise ValueError(
                "No usable workspace review; run koala review or pass --run"
            )
        return Path(read_json(path)["run"])
