"""Failure paths and backend wire contracts; no paid calls."""

import asyncio
import json
import os

import httpx
import pytest
import yaml
from pypdf import PdfWriter
from test_local_review import FakeProvider, workspace

from koala_science import (
    Agent,
    BackendResult,
    Limits,
    Message,
    ModelRequest,
    ModelResponse,
    Proposals,
)
from koala_science.cli import main
from koala_science.config import ModelConfig, load_config
from koala_science.providers import HTTPProvider, ProviderError
from koala_science.runner import Budget
from koala_science.sources import read_source


def model_request():
    return ModelRequest(
        model="gemini-3.5-flash",
        messages=[
            Message(role="system", content="rules"),
            Message(role="user", content="source"),
        ],
        output_schema=Proposals.model_json_schema(),
        max_output_tokens=200,
        timeout_seconds=2,
    )


def test_proxy_contract(monkeypatch):
    monkeypatch.setenv("TEST_AGENT_KEY", "cs_test")

    def handler(request):
        assert request.url.path == "/llm/v1beta/models/gemini-3.5-flash:generateContent"
        assert request.headers["Authorization"] == "Bearer cs_test"
        body = json.loads(request.content)
        assert body["contents"] == [{"role": "user", "parts": [{"text": "source"}]}]
        assert body["systemInstruction"]["parts"][0]["text"] == "rules"
        assert (
            body["generationConfig"]["responseJsonSchema"]
            == Proposals.model_json_schema()
        )
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"thought": True, "text": "private"},
                                {"text": '{"candidates":[]}'},
                            ]
                        }
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 5,
                    "thoughtsTokenCount": 2,
                },
                "modelVersion": "actual",
            },
        )

    provider = HTTPProvider(
        ModelConfig(
            provider="koala_proxy",
            name="x",
            base_url="https://koala.test/llm",
            api_key_env="TEST_AGENT_KEY",
        ),
        transport=httpx.MockTransport(handler),
    )
    response = asyncio.run(provider.generate(model_request()))
    assert response.text == '{"candidates":[]}'
    assert response.model == "actual"
    assert response.output_tokens == 7


@pytest.mark.parametrize(
    "code,retryable",
    [(400, False), (401, False), (402, False), (403, False), (429, True), (500, True)],
)
def test_proxy_errors_are_safe(code, retryable):
    provider = HTTPProvider(
        ModelConfig(provider="compatible_api", name="test", base_url="http://local/v1"),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(code, text="secret credential")
        ),
    )
    with pytest.raises(ProviderError) as error:
        asyncio.run(provider.generate(model_request()))
    assert error.value.retryable is retryable
    assert "secret" not in str(error.value)


def test_compatible_without_auth():
    def handler(request):
        assert "authorization" not in request.headers
        assert request.url.path == "/v1/chat/completions"
        assert json.loads(request.content)["response_format"]["type"] == "json_schema"
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    response = asyncio.run(
        HTTPProvider(
            ModelConfig(
                provider="compatible_api", name="test", base_url="http://local/v1"
            ),
            transport=httpx.MockTransport(handler),
        ).generate(model_request())
    )
    assert response.input_tokens is None


def test_concurrent_budget_reservations():
    async def exercise():
        budget = Budget(Limits(max_model_calls=3))
        results = await asyncio.gather(
            *(budget.reserve_call() for _ in range(20)), return_exceptions=True
        )
        assert sum(item is None for item in results) == 3
        assert budget.calls == 3

    asyncio.run(exercise())


def test_custom_validation_never_imports(tmp_path):
    config = workspace(tmp_path)
    factory = tmp_path / "danger.py"
    factory.write_text(
        "raise RuntimeError('must not import during validation')", encoding="utf-8"
    )
    raw = yaml.safe_load(config.read_text())
    raw["model"] = {
        "provider": "custom",
        "name": "custom",
        "factory": "danger.py:build",
    }
    config.write_text(yaml.safe_dump(raw))
    assert load_config(config).config.model.provider == "custom"


@pytest.mark.parametrize("change", ["duplicate", "nested", "unknown", "missing"])
def test_invalid_children(tmp_path, change):
    config = workspace(tmp_path)
    raw = yaml.safe_load(config.read_text())
    raw["sub_agents"] = [{"config_path": "agents/methods.yaml"}]
    child = tmp_path / "agents/methods.yaml"
    data = yaml.safe_load(child.read_text())
    if change == "duplicate":
        data["name"] = "test"
    elif change == "nested":
        data["sub_agents"] = [{"config_path": "../agent.yaml"}]
    elif change == "unknown":
        data["tools"] = ["shell"]
    else:
        data["instruction_file"] = "missing.md"
    child.write_text(yaml.safe_dump(data))
    config.write_text(yaml.safe_dump(raw))
    with pytest.raises((ValueError, OSError)):
        load_config(config)


def test_pdf_errors_and_unicode(tmp_path):
    blank = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(blank)
    with pytest.raises(ValueError, match="No usable text"):
        read_source(blank)
    blank.write_bytes(b"damaged")
    with pytest.raises(ValueError, match="extraction failed"):
        read_source(blank)
    text = tmp_path / "研究.md"
    text.write_text("# Results\nA result.\n", encoding="utf-8")
    source = read_source(text)
    assert source.spans[-1].line_start == 2
    assert source.content_hash == read_source(text).content_hash


def test_budget_exhaustion_records_coverage(tmp_path):
    config = workspace(tmp_path)
    raw = yaml.safe_load(config.read_text())
    raw["limits"] = {"max_model_calls": 1}
    config.write_text(yaml.safe_dump(raw))
    result = Agent.from_config(config, provider=FakeProvider()).review(
        tmp_path / "sample.md"
    )
    assert result.status == "partial"
    assert result.manifest["coverage"]["skipped_spans"]
    assert result.manifest["model_calls"] <= 1


def test_malformed_output_gets_one_repair(tmp_path):
    class Malformed:
        calls = 0

        async def generate(self, request):
            self.calls += 1
            return ModelResponse(text="invalid", model="fake")

    provider = Malformed()
    paper = tmp_path / "paper.txt"
    paper.write_text("One result.")
    result = Agent.from_config(workspace(tmp_path), provider=provider).review(paper)
    assert provider.calls == 2
    assert result.status == "failed"
    assert not result.arguments


def test_auth_failure_not_retried(tmp_path):
    class Unauthorized:
        calls = 0

        async def generate(self, request):
            self.calls += 1
            raise ProviderError("Model HTTP 401: invalid credential")

    provider = Unauthorized()
    paper = tmp_path / "paper.txt"
    paper.write_text("One result.")
    result = Agent.from_config(workspace(tmp_path), provider=provider).review(paper)
    assert provider.calls == 1
    assert result.status == "failed"


def test_parallel_children_and_duplicate_detection(tmp_path):
    config = workspace(tmp_path)
    raw = yaml.safe_load(config.read_text())
    raw["sub_agents"] = [
        {"config_path": "agents/methods.yaml"},
        {"config_path": "agents/results.yaml"},
        {"config_path": "agents/evidence.yaml"},
    ]
    config.write_text(yaml.safe_dump(raw))
    paper = tmp_path / "paper.txt"
    paper.write_text("Both models trained for 10 epochs.")
    result = Agent.from_config(config, provider=FakeProvider()).review(paper)
    assert result.status == "complete"
    assert len(result.arguments) == 1
    tasks = result.manifest["tasks"]
    assert [t["task"]["role"] for t in tasks[:2]] == ["proposal", "proposal"]
    assert tasks[2]["task"]["depends_on"]
    assert "Duplicate conclusion" in json.dumps(result.diagnostics)


def test_backend_passes_same_checks(tmp_path):
    class Backend:
        supports_budget = True

        async def propose(self, context, limits, budget):
            await budget.reserve_call()
            provider = FakeProvider(fabricated=True)
            request = model_request().model_copy(
                update={
                    "messages": [
                        Message(
                            role="user",
                            content=json.dumps(
                                {
                                    "stage": "proposal",
                                    "spans": [
                                        s.model_dump() for s in context.paper.spans
                                    ],
                                }
                            ),
                        )
                    ]
                }
            )
            response = await provider.generate(request)
            budget.report_usage(response)
            proposals = Proposals.model_validate_json(response.text)
            return BackendResult(
                candidates=proposals.candidates,
                inspected_span_ids=[
                    s.id for source in context.sources for s in source.spans
                ],
            )

    config = workspace(tmp_path)
    result = Agent.from_backend(
        Backend(), config=config, provider=FakeProvider()
    ).review(tmp_path / "sample.md")
    assert result.arguments == []
    assert result.manifest["model_calls"] == 1
    assert "Excerpt does not match" in json.dumps(result.diagnostics)
    with pytest.raises(ValueError, match="supports_budget"):
        Agent.from_backend(object(), config=config)


def test_cli_with_custom_provider(tmp_path, capsys):
    config = workspace(tmp_path)
    custom = tmp_path / "empty.py"
    custom.write_text(
        'from koala_science import ModelResponse\nclass Empty:\n async def generate(self, request):\n  return ModelResponse(text=\'{"candidates": []}\', model="fake")\ndef build():\n return Empty()\n'
    )
    raw = yaml.safe_load(config.read_text())
    raw["model"] = {"provider": "custom", "name": "fake", "factory": "empty.py:build"}
    config.write_text(yaml.safe_dump(raw))
    output = tmp_path / "run"
    assert (
        main(
            [
                "review",
                str(tmp_path / "sample.md"),
                "--config",
                str(config),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert "0 arguments (complete)" in capsys.readouterr().out
    assert not (tmp_path / ".run.journal.jsonl").exists()
    assert (
        main(["review", "unused", "--config", str(config), "--output", str(output)])
        == 2
    )


@pytest.mark.network
def test_live_proxy_smoke():
    """Explicit opt-in: requires a staging base URL, model, and agent key."""
    base = os.environ.get("KOALA_SMOKE_BASE_URL")
    model = os.environ.get("KOALA_SMOKE_MODEL")
    if not base or not model or not os.environ.get("KOALA_SMOKE_API_KEY"):
        pytest.skip("Set KOALA_SMOKE_BASE_URL, KOALA_SMOKE_MODEL, KOALA_SMOKE_API_KEY")
    request = model_request().model_copy(
        update={
            "model": model,
            "timeout_seconds": 60,
            "messages": [
                Message(role="user", content='Return JSON: {"candidates": []}')
            ],
        }
    )
    provider = HTTPProvider(
        ModelConfig(
            provider="koala_proxy",
            name=model,
            base_url=base,
            api_key_env="KOALA_SMOKE_API_KEY",
        )
    )
    Proposals.model_validate_json(asyncio.run(provider.generate(request)).text)


def test_revision_requires_new_evidence_decision(tmp_path):
    class Revising(FakeProvider):
        def __init__(self):
            super().__init__()
            self.stages = []

        async def generate(self, request):
            payload = json.loads(request.messages[-1].content)
            stage = payload["stage"]
            self.stages.append(stage)
            if stage == "evidence" and self.stages.count("evidence") == 1:
                return ModelResponse(
                    text=json.dumps(
                        {
                            "decision": "uncertain",
                            "atomic": False,
                            "reason": "Narrow it",
                            "revision": "Only discuss the budget",
                        }
                    ),
                    model="fake",
                )
            if stage == "revision":
                candidate = dict(payload["candidates"][0])
                candidate.pop("id")
                candidate["statement"] = (
                    "Both reported training schedules use ten epochs."
                )
                return ModelResponse(
                    text=json.dumps({"candidates": [candidate]}), model="fake"
                )
            return await super().generate(request)

    provider = Revising()
    config = workspace(tmp_path)
    paper = tmp_path / "paper.txt"
    paper.write_text("Both models trained for 10 epochs.")
    result = Agent.from_config(config, provider=provider).review(paper)
    assert provider.stages == ["proposal", "evidence", "revision", "evidence"]
    assert len(result.arguments) == 1
    assert len(result.arguments[0].provenance.task_ids) == 4
    assert any(d.get("parent_id") == "candidate-1" for d in result.diagnostics)


def test_verifier_cannot_accept_compound_candidate(tmp_path):
    class Compound(FakeProvider):
        async def generate(self, request):
            payload = json.loads(request.messages[-1].content)
            if payload["stage"] == "evidence":
                return ModelResponse(
                    text=json.dumps(
                        {
                            "decision": "supported",
                            "atomic": False,
                            "reason": "Two independent claims",
                            "revision": None,
                        }
                    ),
                    model="fake",
                )
            return await super().generate(request)

    config = workspace(tmp_path)
    result = Agent.from_config(config, provider=Compound()).review(
        tmp_path / "sample.md"
    )
    assert not result.arguments
    assert result.status == "complete"


def test_cancellation_preserves_journal(tmp_path):
    async def exercise():
        started = asyncio.Event()

        class Waiting:
            async def generate(self, request):
                started.set()
                await asyncio.Event().wait()

        config = workspace(tmp_path)
        journal = tmp_path / "journal.jsonl"
        task = asyncio.create_task(
            Agent.from_config(config, provider=Waiting()).areview(
                tmp_path / "sample.md", journal=journal
            )
        )
        await started.wait()
        task.cancel()
        result = await task
        assert result.status == "partial"
        assert "cancelled" in journal.read_text()
        assert not result.arguments

    asyncio.run(exercise())


def test_verifier_additional_read_is_bounded(tmp_path):
    class Reader(FakeProvider):
        reads = 0

        async def generate(self, request):
            payload = json.loads(request.messages[-1].content)
            if payload["stage"] == "evidence":
                self.reads += 1
                return ModelResponse(
                    text=json.dumps(
                        {
                            "decision": "supported",
                            "atomic": True,
                            "reason": "Need more context",
                            "revision": None,
                            "requested_span_ids": [payload["source_index"][0]["id"]],
                        }
                    ),
                    model="fake",
                )
            return await super().generate(request)

    provider = Reader()
    config = workspace(tmp_path)
    paper = tmp_path / "paper.txt"
    paper.write_text("Both models trained for 10 epochs.")
    result = Agent.from_config(config, provider=provider).review(paper)
    assert provider.reads == 2
    assert not result.arguments


def test_wrong_locators_unread_sources_and_absence_scope(tmp_path):
    from koala_science import Candidate, Evidence
    from koala_science.sources import check_evidence

    file = tmp_path / "paper.txt"
    file.write_text("Actual evidence.")
    source = read_source(file)
    span = source.spans[0]
    evidence = Evidence(
        source_id=source.id,
        span_id=span.id,
        excerpt="Actual evidence.",
        line_start=1,
        line_end=1,
    )
    candidate = Candidate(
        kind="praise",
        target="method",
        statement="A conclusion",
        rationale="A rationale",
        evidence=[evidence],
    )
    assert (
        check_evidence(candidate, {span.id: span}, set())
        == "Evidence references an unread span"
    )
    candidate.evidence[0].page = 2
    assert "locator" in check_evidence(candidate, {span.id: span}, {span.id})
    candidate.evidence[0].page = None
    candidate.absence_scope = ["unread"]
    assert "Absence scope" in check_evidence(candidate, {span.id: span}, {span.id})


def test_truncated_provider_output_is_not_accepted():
    provider = HTTPProvider(
        ModelConfig(provider="compatible_api", name="test", base_url="http://local/v1"),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200,
                json={
                    "choices": [
                        {"finish_reason": "length", "message": {"content": "{}"}}
                    ]
                },
            )
        ),
    )
    with pytest.raises(ProviderError, match="truncated"):
        asyncio.run(provider.generate(model_request()))


def test_atomic_export_leaves_destination_empty_on_serialization_error(
    tmp_path, monkeypatch
):
    from koala_science import output

    config = workspace(tmp_path)
    result = Agent.from_config(config, provider=FakeProvider()).review(
        tmp_path / "sample.md"
    )
    target = tmp_path / "failed-export"
    target.mkdir()

    def fail(_result):
        raise ValueError("serialization failed")

    monkeypatch.setattr(output, "markdown", fail)
    with pytest.raises(ValueError, match="serialization"):
        result.save(target)
    assert list(target.iterdir()) == []


def test_transient_retries_consume_shared_budget(tmp_path):
    class RateLimited:
        calls = 0

        async def generate(self, request):
            self.calls += 1
            raise ProviderError("rate limited", retryable=True)

    provider = RateLimited()
    config = workspace(tmp_path)
    paper = tmp_path / "paper.txt"
    paper.write_text("A result.")
    result = Agent.from_config(config, provider=provider).review(paper)
    assert provider.calls == result.manifest["model_calls"] == 3
    assert result.status == "failed"


def test_custom_template_with_mock_service(tmp_path, monkeypatch):
    import httpx as http

    from koala_science.providers import build_provider

    monkeypatch.setenv("CUSTOM_KEY", "secret-test-key")
    workspace(tmp_path)
    real_client = http.AsyncClient

    def handler(request):
        body = json.loads(request.content)
        assert body["response_schema"] == Proposals.model_json_schema()
        assert request.headers["Authorization"] == "Bearer secret-test-key"
        return http.Response(200, json={"text": '{"candidates": []}'})

    monkeypatch.setattr(
        http,
        "AsyncClient",
        lambda **kwargs: real_client(transport=http.MockTransport(handler), **kwargs),
    )
    provider = build_provider(
        ModelConfig(
            provider="custom",
            name="fake",
            factory=f"{tmp_path / 'providers/custom_api.py'}:build_provider",
            parameters={
                "endpoint": "https://custom.test/generate",
                "api_key_env": "CUSTOM_KEY",
            },
        )
    )
    assert asyncio.run(provider.generate(model_request())).text == '{"candidates": []}'


def test_config_errors_do_not_print_credentials(tmp_path, monkeypatch, capsys):
    config = workspace(tmp_path)
    monkeypatch.setenv("SECRET_FOR_TEST", "never-print-this")
    config.write_text(config.read_text() + "unknown: ${SECRET_FOR_TEST}\n")
    assert main(["validate", "--config", str(config)]) == 2
    error = capsys.readouterr().err
    assert "unknown" in error
    assert "never-print-this" not in error
