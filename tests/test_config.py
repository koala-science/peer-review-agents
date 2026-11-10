"""agent.yaml, the instruction files, and the payload sent to the platform."""

import pytest
import yaml
from fakes import ROOT, agent_dir

from koala_science.cli import main
from koala_science.config import load_config
from koala_science.payload import argument_payload
from koala_science.types import Argument, Evidence, Provenance


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
