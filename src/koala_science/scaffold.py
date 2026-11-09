"""Small workspaces and interactive provider/preset selection."""

import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

INIT_PROVIDERS = (
    "compatible_api",
    "codex_cli",
    "claude_cli",
    "gemini_cli",
    "openai_api",
    "anthropic_api",
    "gemini_api",
    "koala_proxy",
)
STARTER_FILES = {
    "agent.yaml",
    "instructions.md",
    "paper.yaml",
    "sample.md",
    ".gitignore",
}


def initialize(
    directory: str | Path,
    *,
    examples: bool = False,
    provider: str = "compatible_api",
    preset: str = "quick",
) -> None:
    """Scaffold a workspace after checking every destination for conflicts."""
    if provider not in INIT_PROVIDERS:
        raise ValueError("Unsupported starter provider")
    if preset not in {"quick", "default"}:
        raise ValueError("Unsupported review preset")
    target = Path(directory)
    root = files("koala_science").joinpath("templates")
    entries = []

    def collect(node: Any, relative: Path = Path()) -> None:
        for item in node.iterdir():
            if item.name == "__pycache__" or item.name.endswith(".pyc"):
                continue
            path = relative / item.name
            if not examples and str(path) not in STARTER_FILES:
                continue
            if item.is_dir():
                collect(item, path)
            else:
                entries.append((path, item.read_bytes()))

    collect(root)
    if examples and not root.joinpath("examples").is_dir():
        # Editable installs read the canonical examples from this source checkout.
        # Wheels carry the same files under templates/examples through build mapping.
        checkout = Path(__file__).resolve().parents[2]
        example_root = checkout / "examples"
        if not (checkout / "pyproject.toml").is_file() or not example_root.is_dir():
            raise ValueError("Example templates are missing; reinstall the package")
        collect(example_root, Path("examples"))
    for index, (path, content) in enumerate(entries):
        if path != Path("agent.yaml"):
            continue
        config = yaml.safe_load(content)
        if provider != "compatible_api":
            model = {"provider": provider, "name": "${KOALA_MODEL}"}
            key_variables = {
                "openai_api": "OPENAI_API_KEY",
                "anthropic_api": "ANTHROPIC_API_KEY",
                "gemini_api": "GEMINI_API_KEY",
                "koala_proxy": "KOALA_AGENT_API_KEY",
            }
            if provider in key_variables:
                model["api_key_env"] = key_variables[provider]
            if provider == "koala_proxy":
                model["base_url"] = "https://koala.science/llm"
            config["model"] = model
        if preset == "default":
            config["description"] = (
                "Examine two consequential claims with skeptical evidence checks."
            )
            config["max_claims"] = 2
            config["limits"].update(
                max_arguments=2, max_model_calls=10, max_run_seconds=360
            )
        entries[index] = (path, yaml.safe_dump(config, sort_keys=False).encode("utf-8"))
        break
    conflicts = []
    for path, _ in entries:
        destination = target / path
        if (
            destination.exists()
            or destination.is_symlink()
            or any(p.exists() and not p.is_dir() for p in destination.parents)
            or any(
                p.is_symlink()
                for p in destination.parents
                if p != target and p.is_relative_to(target)
            )
        ):
            conflicts.append(str(path))
    if conflicts:
        raise ValueError("Initialization conflict: " + ", ".join(conflicts))
    for path, content in entries:
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write(content)


def _choose(question: str, options: list[tuple[str, str]]) -> str:
    print(question)
    for index, (_, label) in enumerate(options, 1):
        print(f"  {index}. {label}")
    while True:
        try:
            answer = input("Choose a number: ").strip()
        except EOFError as exc:
            raise ValueError("Setup cancelled; no files were created") from exc
        if answer.isdecimal() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1][0]
        print(f"Enter a number from 1 to {len(options)}.")


def setup_choices(provider: str | None, preset: str | None) -> tuple[str, str]:
    """Ask only for missing choices; automation must make both explicit."""
    if (provider is None or preset is None) and not sys.stdin.isatty():
        raise ValueError(
            "Noninteractive initialization requires --provider and --preset (quick or default)"
        )
    if provider is None:
        family = _choose(
            "Choose your model provider:",
            [
                ("koala_proxy", "Koala model credits"),
                ("codex", "Codex / OpenAI"),
                ("claude", "Claude / Anthropic"),
                ("gemini", "Gemini / Google"),
                ("compatible_api", "Other OpenAI-compatible API"),
            ],
        )
        modes = {
            "codex": ("codex_cli", "openai_api"),
            "claude": ("claude_cli", "anthropic_api"),
            "gemini": ("gemini_cli", "gemini_api"),
        }
        if family in modes:
            cli, api = modes[family]
            provider = _choose(
                "Choose how to access the model:",
                [
                    (cli, "CLI - use your installed login"),
                    (api, "API - use a provider API key"),
                ],
            )
        else:
            provider = family
    if preset is None:
        preset = _choose(
            "Choose a starting review:",
            [
                ("quick", "Quick - one claim, up to 6 model calls / 4 minutes"),
                ("default", "Default - two claims, up to 10 model calls / 6 minutes"),
            ],
        )
    return provider, preset
