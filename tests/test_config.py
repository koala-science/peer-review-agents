"""agent.yaml, the instruction files, and the payload sent to the platform."""

import pytest
import yaml
from fakes import ROOT, agent_dir

from koala_science.cli import main
from koala_science.config import load_config
from koala_science.payload import argument_payload
from koala_science.types import Argument, Evidence, Limits, Provenance


def test_repository_defaults_load(monkeypatch):
    monkeypatch.setenv("KOALA_AGENT_API_KEY", "cs_x")
    loaded = load_config(ROOT / "agent.yaml")
    assert loaded.config.model.provider == "koala_proxy"
    assert loaded.config.run.max_arguments == 10
    assert "selection strategy" in loaded.strategy.lower()
    assert loaded.reviewer.startswith("# Reviewer instructions")


def test_missing_key_is_reported_before_any_request(monkeypatch):
    monkeypatch.delenv("KOALA_AGENT_API_KEY", raising=False)
    with pytest.raises(ValueError, match="KOALA_AGENT_API_KEY"):
        load_config(ROOT / "agent.yaml")


def test_missing_or_empty_instruction_file(tmp_path):
    root = agent_dir(tmp_path)
    (root / "strategy.md").write_text("  \n")
    with pytest.raises(ValueError, match="empty: strategy.md"):
        load_config(root / "agent.yaml")
    (root / "strategy.md").unlink()
    with pytest.raises(ValueError, match="Missing instruction file: strategy.md"):
        load_config(root / "agent.yaml")


def test_unknown_fields_and_deadline_parsing(tmp_path):
    root = agent_dir(tmp_path, deadline="2026-12-01T00:00:00Z")
    assert load_config(root / "agent.yaml").config.run.deadline.year == 2026
    raw = yaml.safe_load((root / "agent.yaml").read_text())
    raw["run"]["max_argument"] = 3
    (root / "agent.yaml").write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError):
        load_config(root / "agent.yaml")


def test_yaml_duplicate_fields_are_rejected(tmp_path):
    root = agent_dir(tmp_path)
    (root / "agent.yaml").write_text(
        (root / "agent.yaml").read_text() + "name: again\n"
    )
    with pytest.raises(ValueError, match="Duplicate YAML"):
        load_config(root / "agent.yaml")


def argument(**overrides):
    fields = {
        "kind": "praise",
        "target": "ablation",
        "statement": "The ablation isolates the memory module's contribution.",
        "rationale": "Removing the module drops accuracy from 71.2 to 64.0 with everything else fixed.",
        "evidence": [
            Evidence(source_id="s", span_id="s:p3:0", page=3, excerpt="drops  to\n64.0")
        ],
        "id": "candidate-1",
        "provenance": Provenance(
            agent_name="a", model="m", prompt_digest="d", task_ids=[]
        ),
        "local_checks": {},
    }
    return Argument(**{**fields, **overrides})


def test_payload_is_self_contained():
    payload = argument_payload(argument(limitations=["Single seed."]), "p1")
    assert payload == {
        "paper_id": "p1",
        "claim": "The ablation isolates the memory module's contribution.",
        "position": "positive",
        "evidence": (
            "Removing the module drops accuracy from 71.2 to 64.0 with everything else fixed.\n\n"
            'From the paper:\n- Page 3: "drops to 64.0"\n\nScope: Single seed.'
        ),
    }


def test_payload_is_never_truncated():
    with pytest.raises(ValueError, match="nothing truncated"):
        argument_payload(argument(statement="x" * 10001), "p1")


def test_cli_reports_missing_key(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("KOALA_AGENT_API_KEY", raising=False)
    root = agent_dir(tmp_path)
    assert main(["--config", str(root / "agent.yaml"), "run", "--dry-run"]) == 2
    assert "KOALA_AGENT_API_KEY" in capsys.readouterr().err
    assert not (root / "logs").exists()


def test_setting_one_review_limit_keeps_the_other_defaults(tmp_path):
    root = agent_dir(tmp_path)
    config = yaml.safe_load((root / "agent.yaml").read_text())
    config["review"]["limits"] = {"max_run_seconds": 1800}
    (root / "agent.yaml").write_text(yaml.safe_dump(config))
    limits = load_config(root / "agent.yaml").config.review.limits
    assert limits.max_run_seconds == 1800
    assert limits.model_dump() == {**Limits().model_dump(), "max_run_seconds": 1800}
    assert limits.max_input_tokens_per_call == 1_000_000


class FakeClient:
    def __init__(self, key):
        assert key == "cs_new_key"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def me(self):
        return {"name": "new-agent", "id": "agent-9"}


def test_login_checks_the_key_and_saves_it_privately(tmp_path, monkeypatch, capsys):
    import io
    import os
    import stat

    from koala_science import cli

    monkeypatch.setattr(cli, "PlatformClient", FakeClient)
    monkeypatch.setattr("sys.stdin", io.StringIO("  cs_new_key\n"))
    assert main(["--config", str(tmp_path / "agent.yaml"), "login"]) == 0
    saved = tmp_path / ".koala_key"
    assert saved.read_text() == "cs_new_key\n"
    if os.name != "nt":
        assert stat.S_IMODE(saved.stat().st_mode) == 0o600
    out = capsys.readouterr().out
    assert "new-agent" in out and "cs_new_key" not in out


def test_login_refuses_text_that_is_not_a_key(tmp_path, monkeypatch, capsys):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("hello there\n"))
    assert main(["--config", str(tmp_path / "agent.yaml"), "login"]) == 2
    assert not (tmp_path / ".koala_key").exists()
    assert "start with cs_" in capsys.readouterr().err


def test_saved_key_is_used_and_the_environment_wins(tmp_path, monkeypatch):
    import os

    from koala_science.cli import load_saved_key

    (tmp_path / ".koala_key").write_text("cs_saved\n")
    monkeypatch.delenv("KOALA_AGENT_API_KEY", raising=False)
    load_saved_key(tmp_path)
    assert os.environ["KOALA_AGENT_API_KEY"] == "cs_saved"
    monkeypatch.setenv("KOALA_AGENT_API_KEY", "cs_env")
    load_saved_key(tmp_path)
    assert os.environ["KOALA_AGENT_API_KEY"] == "cs_env"


def test_saved_key_file_is_gitignored():
    assert ".koala_key" in (ROOT / ".gitignore").read_text().splitlines()
