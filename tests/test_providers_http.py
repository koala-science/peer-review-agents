"""Provider wire contracts, extraction limits, and YAML safety. No paid calls."""

import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from koala_science import Limits, Message, ModelRequest
from koala_science.config import ModelConfig, load_config
from koala_science.providers import HTTPProvider, ProviderError
from koala_science.runner import Budget
from koala_science.sources import read_source
from koala_science.types import Proposals


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


@pytest.mark.parametrize(
    "values",
    [
        {"max_tasks": True},
        {"max_run_seconds": float("inf")},
        {"request_timeout_seconds": float("nan")},
    ],
)
def test_limits_reject_coercion_and_nonfinite_values(values):
    with pytest.raises(ValidationError):
        Limits(**values)


def test_recursive_yaml_alias_is_an_input_error(tmp_path):
    config = tmp_path / "agent.yaml"
    config.write_text("loop: &loop [*loop]\n")
    with pytest.raises(ValueError, match="Recursive YAML"):
        load_config(config)


def test_http_response_size_is_bounded(monkeypatch):
    from koala_science import providers

    monkeypatch.setattr(providers, "MAX_RESPONSE_BYTES", 256, raising=False)
    response = {"choices": [{"message": {"content": "a" * 1024}}]}
    provider = HTTPProvider(
        ModelConfig(provider="compatible_api", name="test", base_url="http://local/v1"),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=response)
        ),
    )
    with pytest.raises(ProviderError, match="size limit"):
        asyncio.run(provider.generate(model_request()))


def test_extracted_span_limit_is_enforced(tmp_path, monkeypatch):
    from koala_science import sources

    monkeypatch.setattr(sources, "MAX_SOURCE_SPANS", 2)
    file = tmp_path / "paper.txt"
    file.write_text("a\nb\nc\n")
    with pytest.raises(ValueError, match="span limit"):
        read_source(file)


@pytest.mark.parametrize("cancel", [False, True])
def test_pdf_parser_is_terminated_on_timeout_or_cancellation(
    tmp_path, monkeypatch, cancel
):
    import subprocess
    import sys

    from koala_science import sources

    real_popen = subprocess.Popen
    children = []

    def sleeper(*args, **kwargs):
        child = real_popen(
            [sys.executable, "-c", "import time; time.sleep(30)"], **kwargs
        )
        children.append(child)
        return child

    monkeypatch.setattr(sources.subprocess, "Popen", sleeper)

    async def exercise():
        task = asyncio.create_task(
            sources.read_source_async(tmp_path / "paper.pdf", 1 if cancel else 0.1)
        )
        if cancel:
            await asyncio.sleep(0.05)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(ValueError, match="deadline"):
                await task
        assert children[0].poll() is not None

    asyncio.run(exercise())


def test_real_text_pdf_uses_extraction_worker(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    from koala_science.sources import read_source_async

    writer = PdfWriter()
    page = writer.add_blank_page(200, 200)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 10 100 Td (Both models train for ten epochs.) Tj ET")
    page[NameObject("/Contents")] = stream
    path = tmp_path / "paper.pdf"
    writer.write(path)
    source = asyncio.run(read_source_async(path, 10))
    assert source.spans[0].page == 1
    assert "ten epochs" in source.spans[0].text


@pytest.mark.parametrize(
    "url",
    [
        "http:///missing-host",
        "https://user:password@api.test/v1",
        "https://api.test/v1?key=secret",
        "https://api.test/v1#fragment",
    ],
)
def test_provider_base_url_rejects_ambiguous_or_credential_bearing_urls(url):
    with pytest.raises(ValidationError):
        ModelConfig(provider="compatible_api", name="test", base_url=url)


def test_http_provider_refuses_compressed_responses():
    import gzip

    def handler(request):
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(
            200, headers={"content-encoding": "gzip"}, content=gzip.compress(b"{}")
        )

    provider = HTTPProvider(
        ModelConfig(provider="compatible_api", name="test", base_url="http://local/v1"),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderError, match="Compressed"):
        asyncio.run(provider.generate(model_request()))


def test_yaml_cannot_execute_python_objects(tmp_path, capsys):
    config = tmp_path / "agent.yaml"
    config.write_text("!!python/object/apply:builtins.print ['must not execute']\n")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config(config)
    assert "must not execute" not in capsys.readouterr().out
