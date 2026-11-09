"""Public workflow and evidence acceptance contract."""

import asyncio
import json
from pathlib import Path

import pytest

from koala_science import Agent, ModelRequest, ModelResponse, ReviewResult
from koala_science.cli import initialize
from koala_science.config import load_config


def workspace(tmp_path: Path) -> Path:
    initialize(tmp_path, examples=True)
    config = tmp_path / "agent.yaml"
    config.write_text(
        "schema_version: 1\nname: test\ninstruction_file: instructions.md\nmodel:\n  provider: compatible_api\n  name: test\n  base_url: http://localhost:1234/v1\n",
        encoding="utf-8",
    )
    return config


class FakeProvider:
    def __init__(self, fabricated: bool = False):
        self.calls = 0
        self.fabricated = fabricated

    async def generate(self, request):
        self.calls += 1
        payload = json.loads(request.messages[-1].content)
        if payload["stage"] == "proposal":
            span = payload["spans"][-1]
            evidence = {
                "source_id": span["source_id"],
                "span_id": span["id"],
                "page": span["page"],
                "line_start": span["line_start"],
                "line_end": span["line_end"],
                "excerpt": "invented" if self.fabricated else span["text"],
            }
            output = {
                "candidates": [
                    {
                        "kind": "praise",
                        "target": "evaluation",
                        "statement": "The comparison controls the training budget.",
                        "rationale": "Both models use the same training budget.",
                        "evidence": [evidence],
                        "limitations": [],
                    }
                ]
            }
        elif payload["stage"] == "duplicate":
            output = {"duplicate": False, "reason": "Different conclusions."}
        else:
            output = {
                "decision": "supported",
                "atomic": True,
                "reason": "The cited comparison supports this conclusion.",
                "revision": None,
            }
        return ModelResponse(text=json.dumps(output), model="fake")


def test_review_and_roundtrip(tmp_path):
    config = workspace(tmp_path)
    paper = tmp_path / "paper.md"
    paper.write_text(
        "# Results\nBoth models trained for 10 epochs.\n", encoding="utf-8"
    )
    result = Agent.from_config(config, provider=FakeProvider()).review(paper)
    assert result.status == "complete"
    assert len(result.arguments) == 1
    result.save(tmp_path / "run")
    restored = ReviewResult.model_validate_json(
        (tmp_path / "run/arguments.json").read_text()
    )
    assert restored.arguments == result.arguments
    assert "10 epochs" in (tmp_path / "run/arguments.md").read_text()
    with pytest.raises(ValueError, match="empty"):
        result.save(tmp_path / "run")


def test_fabricated_quote_is_never_accepted(tmp_path):
    config = workspace(tmp_path)
    paper = tmp_path / "paper.txt"
    paper.write_text("Both models trained for 10 epochs.", encoding="utf-8")
    result = Agent.from_config(config, provider=FakeProvider(True)).review(paper)
    assert result.arguments == []
    assert result.diagnostics


def test_init_conflict_writes_nothing(tmp_path):
    (tmp_path / "instructions.md").write_text("mine")
    with pytest.raises(ValueError, match="conflict"):
        initialize(tmp_path, examples=True)
    assert list(tmp_path.iterdir()) == [tmp_path / "instructions.md"]


def test_unknown_config_and_missing_environment(tmp_path, monkeypatch):
    config = workspace(tmp_path)
    with config.open("a") as f:
        f.write("surprise: true\n")
    with pytest.raises(ValueError):
        load_config(config)
    monkeypatch.delenv("KOALA_MODEL", raising=False)
    other = tmp_path / "other"
    initialize(other)
    with pytest.raises(ValueError, match="KOALA_MODEL"):
        load_config(other / "agent.yaml")


def test_sync_method_explains_event_loop(tmp_path):
    agent = Agent.from_config(workspace(tmp_path), provider=FakeProvider())

    async def active():
        with pytest.raises(RuntimeError, match="areview"):
            agent.review("unused.txt")

    asyncio.run(active())


def test_example_agent_is_scaffolded_and_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("KOALA_MODEL", "test-model")
    monkeypatch.setenv("KOALA_MODEL_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("KOALA_MODEL_API_KEY", "test-key")
    initialize(tmp_path, examples=True)
    example = tmp_path / "examples" / "fair-comparison"
    config = load_config(example / "agent.yaml")
    assert config.config.name == "fair_comparison_reviewer"
    assert "training budget" in config.instruction

    class ExampleProvider(FakeProvider):
        async def generate(self, request):
            payload = json.loads(request.messages[-1].content)
            if payload["stage"] != "proposal":
                return await super().generate(request)
            span = next(s for s in payload["spans"] if "40 epochs" in s["text"])
            output = {
                "candidates": [
                    {
                        "kind": "criticism",
                        "target": "claim of architectural superiority",
                        "statement": "The comparison does not isolate the effect of architecture from training duration.",
                        "rationale": "The two models train for different numbers of epochs.",
                        "evidence": [
                            {
                                "source_id": span["source_id"],
                                "span_id": span["id"],
                                "line_start": span["line_start"],
                                "line_end": span["line_end"],
                                "page": None,
                                "excerpt": span["text"],
                            }
                        ],
                        "limitations": [
                            "This does not show that the accuracy measurements are incorrect."
                        ],
                    }
                ],
            }
            return ModelResponse(text=json.dumps(output), model="example-test")

    result = Agent.from_config(
        example / "agent.yaml", provider=ExampleProvider()
    ).review(example / "paper.md")
    assert result.status == "complete"
    assert len(result.arguments) == 1
    assert result.arguments[0].kind == "criticism"
    result.save(tmp_path / "example-run")
    assert "40 epochs" in (tmp_path / "example-run" / "arguments.md").read_text()


def test_tood_example_inherits_the_local_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KOALA_MODEL", "local-test-model")
    monkeypatch.setenv("KOALA_MODEL_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.delenv("KOALA_MODEL_API_KEY", raising=False)
    initialize(tmp_path, examples=True)
    config = load_config(tmp_path / "examples/tood/agent.yaml")
    assert config.config.model.api_key_env is None
    assert [child.config.role for child in config.children] == [
        "proposer",
        "proposer",
        "verifier",
    ]
    assert all(child.config.model == config.config.model for child in config.children)
    assert all(child.config.limits == config.config.limits for child in config.children)
    assert config.config.limits.max_concurrency == 1


def test_tood_offline_smoke_needs_no_model_or_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.providers import HTTPProvider

    async def forbidden_request(
        self: HTTPProvider, request: ModelRequest
    ) -> ModelResponse:
        pytest.fail("The offline example must not call a model endpoint")

    monkeypatch.setattr(HTTPProvider, "generate", forbidden_request)
    for key in ["KOALA_MODEL", "KOALA_MODEL_BASE_URL", "KOALA_MODEL_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    initialize(tmp_path, examples=True)
    agent = Agent.from_config(tmp_path / "examples/tood/offline.yaml")
    result = agent.review(tmp_path / "sample.md")
    assert result.status == "complete"
    assert result.arguments == []
    assert result.manifest["coverage"]["skipped_spans"] == []
    assert result.manifest["model_calls"] > 0
    assert {entry["model"] for entry in result.manifest["usage"]} == {
        "offline-smoke-no-scientific-review"
    }
    result.save(tmp_path / "offline-result")
    assert (tmp_path / "offline-result/manifest.json").is_file()


def test_tood_review_rejects_fabricated_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KOALA_MODEL", "fixture")
    monkeypatch.setenv("KOALA_MODEL_BASE_URL", "http://127.0.0.1:1234/v1")
    initialize(tmp_path, examples=True)
    paper = tmp_path / "synthetic-ood-fixture.md"
    quote = "Calibration statistics use only in-distribution replay samples."
    paper.write_text(quote, encoding="utf-8")

    class CalibrationFixture:
        async def generate(self, request: ModelRequest) -> ModelResponse:
            payload = json.loads(request.messages[-1].content)
            if payload["stage"] == "proposal":
                span = payload["spans"][0]
                candidate = {
                    "kind": "praise",
                    "target": "calibration data",
                    "statement": "The stated calibration statistics do not require OOD samples.",
                    "rationale": "The fixture limits calibration statistics to ID replay samples.",
                    "evidence": [
                        {
                            "source_id": span["source_id"],
                            "span_id": span["id"],
                            "page": None,
                            "line_start": 1,
                            "line_end": 1,
                            "excerpt": quote,
                        }
                    ],
                    "limitations": [
                        "Synthetic fixture, not a judgment of the TOOD paper."
                    ],
                }
                fabricated = json.loads(json.dumps(candidate))
                fabricated["evidence"][0]["excerpt"] = (
                    "A fabricated experimental result."
                )
                output = {"candidates": [candidate, fabricated]}
            else:
                assert payload["stage"] == "evidence"
                output = {
                    "decision": "supported",
                    "atomic": True,
                    "reason": "Scripted fixture decision, not scientific evaluation.",
                }
            return ModelResponse(text=json.dumps(output), model="calibration-fixture")

    result = Agent.from_config(
        tmp_path / "examples/tood/agent.yaml", provider=CalibrationFixture()
    ).review(paper)
    assert result.status == "complete"
    assert len(result.arguments) == 1
    assert result.arguments[0].evidence[0].excerpt == quote
    assert any(
        item.get("rejected") == "Excerpt does not match the source"
        for item in result.diagnostics
    )


def test_repository_tood_example_runs_directly(tmp_path: Path) -> None:
    """The root example is runnable without initializing another workspace."""
    repository = Path(__file__).resolve().parents[1]
    paper = tmp_path / "paper.txt"
    paper.write_text("A local input for the offline workflow check.", encoding="utf-8")
    agent = Agent.from_config(repository / "examples/tood/offline.yaml")
    result = agent.review(paper)
    assert result.status == "complete"
    assert result.arguments == []
    assert result.manifest["coverage"]["skipped_spans"] == []


def test_example_conflict_stops_initialization_before_any_write(tmp_path: Path) -> None:
    existing = tmp_path / "examples/tood/agent.yaml"
    existing.parent.mkdir(parents=True)
    existing.write_text("my existing configuration", encoding="utf-8")
    with pytest.raises(ValueError, match="conflict"):
        initialize(tmp_path, examples=True)
    assert existing.read_text(encoding="utf-8") == "my existing configuration"
    assert not (tmp_path / "agent.yaml").exists()
    assert not (tmp_path / "examples/tood/instructions.md").exists()
