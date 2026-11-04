"""Safe YAML loading. Custom Python is imported only when a run starts."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, model_validator

from .types import Limits, StrictModel


class ModelConfig(StrictModel):
    provider: Literal["compatible_api", "koala_proxy", "custom"]
    name: str = Field(min_length=1)
    base_url: str | None = None
    api_key_env: str | None = None
    factory: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_provider(self) -> ModelConfig:
        if self.provider == "custom":
            if not self.factory or ":" not in self.factory:
                raise ValueError("custom provider requires factory: path.py:function")
        elif not self.base_url or not re.match(r"^https?://", self.base_url):
            raise ValueError("provider requires an http(s) base_url")
        if self.provider == "koala_proxy" and not self.api_key_env:
            raise ValueError("koala_proxy requires api_key_env")
        if self.api_key_env and not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", self.api_key_env
        ):
            raise ValueError("api_key_env must be an environment variable name")
        return self


class ChildReference(StrictModel):
    config_path: str


class AgentConfig(StrictModel):
    schema_version: Literal[1]
    name: str = Field(min_length=1)
    description: str = ""
    role: Literal["proposer", "verifier"] = "proposer"
    instruction_file: str
    model: ModelConfig | None = None
    sub_agents: list[ChildReference] = Field(default_factory=list)
    limits: Limits = Field(default_factory=Limits)


class LoadedAgent:
    def __init__(
        self,
        config: AgentConfig,
        path: Path,
        instruction: str,
        children: list[LoadedAgent],
    ) -> None:
        self.config, self.path, self.instruction, self.children = (
            config,
            path,
            instruction,
            children,
        )
        self.explicit_model = config.model is not None


def _expand(value: Any) -> Any:
    if isinstance(value, str):

        def replace(match: re.Match) -> str:
            name = match.group(1)
            if not os.environ.get(name):
                raise ValueError(f"Missing environment variable: {name}")
            return os.environ[name]

        return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, value)
    if isinstance(value, list):
        return [_expand(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand(item) for key, item in value.items()}
    return value


def load_config(
    path: str | Path = "agent.yaml", *, supplied_provider: bool = False
) -> LoadedAgent:
    """Validate all files before any provider import or model request."""
    seen_paths: set[Path] = set()
    names: set[str] = set()

    def load(file: Path, parent: AgentConfig | None = None) -> LoadedAgent:
        file = file.resolve()
        if file in seen_paths:
            raise ValueError(f"Cyclic or duplicate config reference: {file.name}")
        seen_paths.add(file)
        try:
            raw = yaml.safe_load(file.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError("Invalid YAML syntax") from exc
        if not isinstance(raw, dict):
            raise ValueError("agent.yaml must contain a mapping")  # noqa: TRY004 -- invalid input document
        config = AgentConfig.model_validate(_expand(raw))
        if config.name in names:
            raise ValueError(f"Duplicate agent name: {config.name}")
        names.add(config.name)
        explicit_model = config.model is not None
        if parent:
            if config.sub_agents:
                raise ValueError("Nested delegation and cycles are not supported")
            if "limits" in raw:
                raise ValueError("Children inherit shared limits")
            config = config.model_copy(
                update={"model": config.model or parent.model, "limits": parent.limits}
            )
        if config.model is None:
            raise ValueError("Root model is required")
        model = config.model
        uses_override = supplied_provider and (parent is None or not explicit_model)
        if not uses_override:
            if model.api_key_env and not os.environ.get(model.api_key_env):
                raise ValueError(f"Missing environment variable: {model.api_key_env}")
            if model.provider == "custom":
                key_env = model.parameters.get("api_key_env")
                if key_env is not None:
                    if not isinstance(key_env, str) or not re.fullmatch(
                        r"[A-Za-z_][A-Za-z0-9_]*", key_env
                    ):
                        raise ValueError(
                            "Custom api_key_env must name an environment variable"
                        )
                    if not os.environ.get(key_env):
                        raise ValueError(f"Missing environment variable: {key_env}")
                factory_path, symbol = model.factory.rsplit(":", 1)
                resolved = (file.parent / factory_path).resolve()
                if not resolved.is_file() or not symbol.isidentifier():
                    raise ValueError("Invalid custom factory path or function name")
                model.factory = f"{resolved}:{symbol}"
        instruction = (file.parent / config.instruction_file).read_text(
            encoding="utf-8"
        )
        children = [
            load(file.parent / ref.config_path, config) for ref in config.sub_agents
        ]
        loaded = LoadedAgent(config, file, instruction, children)
        loaded.explicit_model = explicit_model
        return loaded

    return load(Path(path))
