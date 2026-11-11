"""Safe agent.yaml loading. Custom Python is imported only when a run starts."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import yaml
from pydantic import Field, model_validator

from .types import Limits, StrictModel


class ConfigLoader(yaml.SafeLoader):
    """Safe YAML with duplicate fields rejected instead of silently overridden."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict:
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError("YAML keys must be strings")  # noqa: TRY004 -- invalid configuration document
            if key in mapping:
                raise ValueError("Duplicate YAML field")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


class ModelConfig(StrictModel):
    provider: Literal[
        "compatible_api",
        "koala_proxy",
        "custom",
        "codex_cli",
        "claude_cli",
        "gemini_cli",
        "openai_api",
        "anthropic_api",
        "gemini_api",
    ]
    name: str = Field(min_length=1)
    base_url: str | None = None
    api_key_env: str | None = None
    factory: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    executable: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_provider(self) -> ModelConfig:
        defaults = {
            "openai_api": "https://api.openai.com/v1",
            "anthropic_api": "https://api.anthropic.com/v1",
            "gemini_api": "https://generativelanguage.googleapis.com",
        }
        if self.provider in defaults:
            if not self.api_key_env:
                raise ValueError("Direct APIs require api_key_env")
            if self.factory or self.parameters:
                raise ValueError("Direct APIs do not accept custom factory fields")
            if self.base_url is None:
                self.base_url = defaults[self.provider]
        if self.executable is not None and self.provider not in {
            "codex_cli",
            "claude_cli",
            "gemini_cli",
        }:
            raise ValueError("executable is only supported by CLI providers")
        if self.provider in {"codex_cli", "claude_cli", "gemini_cli"}:
            if (
                any(value is not None for value in (self.base_url, self.factory))
                or self.parameters
            ):
                raise ValueError("CLI providers do not accept HTTP or custom fields")
            if (
                self.provider in {"codex_cli", "gemini_cli"}
                and self.api_key_env is not None
            ):
                raise ValueError(f"{self.provider} uses CLI authentication")
        elif self.provider == "custom":
            if not self.factory or ":" not in self.factory:
                raise ValueError("custom provider requires factory: path.py:function")
        else:
            try:
                parsed = urlsplit(self.base_url or "")
                valid = (
                    parsed.scheme in {"https", "http"}
                    and parsed.hostname
                    and len(parsed.hostname) <= 253
                    and parsed.username is None
                    and parsed.password is None
                    and not parsed.query
                    and not parsed.fragment
                    and (parsed.port is None or parsed.port > 0)
                )
            except ValueError:
                valid = False
            if not valid:
                raise ValueError(
                    "base_url must be an HTTP(S) URL without credentials, query, or fragment"
                )
        if self.provider == "koala_proxy" and not self.api_key_env:
            raise ValueError("koala_proxy requires api_key_env")
        if self.api_key_env is not None and not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", self.api_key_env
        ):
            raise ValueError("api_key_env must be an environment variable name")
        return self


class Discovery(StrictModel):
    """Hard filters applied in code before the model ranks papers."""

    domains: list[str] = Field(default_factory=list)
    sort: Literal["new", "active"] = "new"
    max_age_days: int | None = Field(None, ge=1)
    max_existing_arguments: int | None = Field(None, ge=0)
    scan_limit: int = Field(200, ge=1, le=2000)
    shortlist: int = Field(20, ge=1, le=100)


class Review(StrictModel):
    max_claims: int = Field(2, ge=1, le=8)
    max_arguments_per_paper: int = Field(2, ge=1, le=3)
    max_revisions: int = Field(2, ge=0, le=5)
    limits: Limits = Field(
        default_factory=lambda: Limits(
            max_arguments=3,
            max_concurrency=1,
            max_model_calls=16,
            max_tasks=20,
            max_candidates_per_task=1,
            # UTF-8 bytes per request; the whole paper goes into every call.
            max_input_tokens_per_call=1_000_000,
            max_output_tokens_per_call=8000,
            max_run_seconds=600,
            request_timeout_seconds=180,
        )
    )


class RunRules(StrictModel):
    """When a run stops. Unset limits do not apply; with none set it runs until stopped."""

    max_arguments: int | None = Field(None, ge=1)
    max_papers: int | None = Field(None, ge=1)
    deadline: datetime | None = None
    min_budget: int = Field(5, ge=0)
    when_idle: Literal["sleep", "stop"] = "sleep"
    idle_minutes: float = Field(30, gt=0)
    dry_run: bool = False


class AgentConfig(StrictModel):
    schema_version: Literal[1]
    name: str = Field(min_length=1)
    strategy_file: str = "strategy.md"
    reviewer_file: str = "reviewer.md"
    model: ModelConfig
    verifier_model: ModelConfig | None = None
    discovery: Discovery = Field(default_factory=Discovery)
    review: Review = Field(default_factory=Review)
    run: RunRules = Field(default_factory=RunRules)


class LoadedAgent:
    """Validated configuration plus the two plain-language instruction files."""

    def __init__(
        self, config: AgentConfig, path: Path, strategy: str, reviewer: str
    ) -> None:
        self.config, self.path, self.strategy, self.reviewer = (
            config,
            path,
            strategy,
            reviewer,
        )

    @property
    def root(self) -> Path:
        return self.path.parent


def _expand(
    value: Any,
    active: set[int] | None = None,
    depth: int = 0,
    count: list[int] | None = None,
) -> Any:
    active = set() if active is None else active
    count = [0] if count is None else count
    count[0] += 1
    if depth > 32 or count[0] > 10000:
        raise ValueError("YAML configuration exceeds nesting or node limit")
    if isinstance(value, str):

        def replace(match: re.Match) -> str:
            name = match.group(1)
            if not os.environ.get(name):
                raise ValueError(f"Missing environment variable: {name}")
            return os.environ[name]

        return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, value)
    if isinstance(value, (list, dict)):
        if id(value) in active:
            raise ValueError("Recursive YAML aliases are not supported")
        active.add(id(value))
        try:
            if isinstance(value, list):
                return [_expand(item, active, depth + 1, count) for item in value]
            return {
                key: _expand(item, active, depth + 1, count)
                for key, item in value.items()
            }
        finally:
            active.remove(id(value))
    return value


def _check_model(model: ModelConfig, base: Path, *, check_env: bool) -> None:
    if check_env and model.api_key_env and not os.environ.get(model.api_key_env):
        raise ValueError(f"Missing environment variable: {model.api_key_env}")
    if model.provider == "custom":
        key_env = model.parameters.get("api_key_env")
        if key_env is not None:
            if not isinstance(key_env, str) or not re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_]*", key_env
            ):
                raise ValueError("Custom api_key_env must name an environment variable")
            if check_env and not os.environ.get(key_env):
                raise ValueError(f"Missing environment variable: {key_env}")
        factory_path, symbol = model.factory.rsplit(":", 1)
        resolved = (base / factory_path).resolve()
        if (
            not resolved.is_file()
            or resolved.suffix != ".py"
            or not symbol.isidentifier()
        ):
            raise ValueError("Invalid custom factory path or function name")
        model.factory = f"{resolved}:{symbol}"


def load_config(
    path: str | Path = "agent.yaml", *, check_env: bool = True
) -> LoadedAgent:
    """Validate configuration and instruction files before any network request."""
    file = Path(path).resolve()
    try:
        with file.open("r", encoding="utf-8") as handle:
            content = handle.read(1_048_577)
        if len(content) > 1_048_576:
            raise ValueError("YAML configuration exceeds size limit")
        raw = yaml.load(content, Loader=ConfigLoader)
    except (yaml.YAMLError, RecursionError) as exc:
        raise ValueError("Invalid YAML syntax") from exc
    if not isinstance(raw, dict):
        raise ValueError("agent.yaml must contain a mapping")  # noqa: TRY004 -- invalid input document
    config = AgentConfig.model_validate(_expand(raw), strict=False)
    for model in filter(None, (config.model, config.verifier_model)):
        _check_model(model, file.parent, check_env=check_env)
    texts = []
    for name in (config.strategy_file, config.reviewer_file):
        instruction = file.parent / name
        if not instruction.is_file():
            raise ValueError(f"Missing instruction file: {name}")
        text = instruction.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"Instruction file is empty: {name}")
        texts.append(text)
    return LoadedAgent(config, file, *texts)
