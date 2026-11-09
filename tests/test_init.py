"""A small default workspace, with explicit provider and example choices."""

from pathlib import Path

import pytest
import yaml

from koala_science.cli import initialize, main
from koala_science.config import load_config


def test_default_init_has_only_starter_files(tmp_path: Path) -> None:
    initialize(tmp_path)
    assert {p.name for p in tmp_path.iterdir()} == {
        "agent.yaml",
        "instructions.md",
        "paper.yaml",
        "sample.md",
        ".gitignore",
    }
    raw = yaml.safe_load((tmp_path / "agent.yaml").read_text())
    assert raw["review_strategy"] == "claims"
    assert raw["max_claims"] == raw["limits"]["max_arguments"] == 1
    assert not raw.get("sub_agents")
    assert raw["limits"]["max_model_calls"] == 6


@pytest.mark.parametrize(
    "provider",
    [
        "codex_cli",
        "claude_cli",
        "gemini_cli",
        "openai_api",
        "anthropic_api",
        "gemini_api",
        "koala_proxy",
        "compatible_api",
    ],
)
def test_init_provider_is_valid_without_copying_examples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    monkeypatch.setenv("KOALA_MODEL", "test")
    monkeypatch.setenv("KOALA_MODEL_BASE_URL", "http://localhost:1234/v1")
    for key in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "KOALA_AGENT_API_KEY",
        "KOALA_MODEL_API_KEY",
    ):
        monkeypatch.setenv(key, "test-only")
    assert (
        main(["init", str(tmp_path), "--provider", provider, "--preset", "quick"]) == 0
    )
    loaded = load_config(tmp_path / "agent.yaml")
    assert loaded.config.model.provider == provider
    assert loaded.children == []
    assert not (tmp_path / "examples").exists()
    if provider.endswith("_cli"):
        assert loaded.config.model.api_key_env is None


def test_examples_are_opt_in(tmp_path: Path) -> None:
    assert (
        main(
            [
                "init",
                str(tmp_path),
                "--examples",
                "--provider",
                "codex_cli",
                "--preset",
                "quick",
            ]
        )
        == 0
    )
    assert (tmp_path / "examples/tood/agent.yaml").is_file()
    assert (tmp_path / "examples/quick-review/instructions.md").is_file()
    assert (tmp_path / "providers/custom_api.py").is_file()


def test_unrequested_example_does_not_conflict(tmp_path: Path) -> None:
    existing = tmp_path / "examples/tood/agent.yaml"
    existing.parent.mkdir(parents=True)
    existing.write_text("user file")
    initialize(tmp_path)
    assert existing.read_text() == "user file"
    assert (tmp_path / "agent.yaml").is_file()


def test_invalid_provider_writes_nothing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="provider"):
        initialize(tmp_path, provider="invalid")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "choices,provider",
    [
        (["1"], "koala_proxy"),
        (["2", "1"], "codex_cli"),
        (["2", "2"], "openai_api"),
        (["3", "1"], "claude_cli"),
        (["3", "2"], "anthropic_api"),
        (["4", "1"], "gemini_cli"),
        (["4", "2"], "gemini_api"),
        (["5"], "compatible_api"),
    ],
)
@pytest.mark.parametrize("preset_choice,claims", [("1", 1), ("2", 2)])
def test_interactive_init(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    choices: list[str],
    provider: str,
    preset_choice: str,
    claims: int,
) -> None:
    import sys

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    answers = iter([*choices, preset_choice])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert main(["init", str(tmp_path)]) == 0
    config = yaml.safe_load((tmp_path / "agent.yaml").read_text())
    assert config["model"]["provider"] == provider
    assert config["max_claims"] == config["limits"]["max_arguments"] == claims
    assert not (tmp_path / "examples").exists()


def test_noninteractive_init_requires_choices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert main(["init", str(tmp_path)]) == 2
    assert not list(tmp_path.iterdir())


def test_cancelled_setup_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    def cancelled(_: str) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", cancelled)
    assert main(["init", str(tmp_path)]) == 2
    assert not list(tmp_path.iterdir())


def test_setup_retries_invalid_choice_and_skips_explicit_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    answers = iter(["not a number", "9", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert main(["init", str(tmp_path), "--provider", "claude_cli"]) == 0
    config = yaml.safe_load((tmp_path / "agent.yaml").read_text())
    assert config["model"]["provider"] == "claude_cli"
    assert config["max_claims"] == 1


def test_quick_starter_keeps_quality_checks_in_three_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from test_claim_review import FocusedProvider

    from koala_science import Agent

    monkeypatch.setenv("KOALA_MODEL", "fake")
    initialize(tmp_path, provider="codex_cli", preset="quick")
    paper = tmp_path / "paper.md"
    paper.write_text("A trained for 40 epochs; B trained for 10.")
    provider = FocusedProvider()
    review = Agent.from_config(tmp_path / "agent.yaml", provider=provider).review(paper)
    assert review.status == "complete"
    assert len(review.arguments) == 1
    assert [request["stage"] for request in provider.requests] == [
        "claim_map",
        "proposal",
        "evidence",
    ]
    assert review.arguments[0].local_checks["importance"] == "passed"
