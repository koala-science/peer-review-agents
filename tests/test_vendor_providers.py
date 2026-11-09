"""Direct vendor contracts use HTTP mocks, never bill an account."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from koala_science.config import ModelConfig
from koala_science.providers import HTTPProvider, ProviderError
from koala_science.types import Message, ModelRequest


@pytest.mark.parametrize(
    "provider,path,header,response",
    [
        (
            "openai_api",
            "/v1/responses",
            "authorization",
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "{}"}],
                    }
                ],
                "usage": {"input_tokens": 3, "output_tokens": 2},
            },
        ),
        (
            "anthropic_api",
            "/v1/messages",
            "x-api-key",
            {
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "{}"}],
                "usage": {"input_tokens": 3, "output_tokens": 2},
            },
        ),
        (
            "gemini_api",
            "/v1beta/models/test:generateContent",
            "x-goog-api-key",
            {
                "candidates": [
                    {"finishReason": "STOP", "content": {"parts": [{"text": "{}"}]}}
                ],
                "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 2},
            },
        ),
    ],
)
def test_vendor_wire(
    provider: str,
    path: str,
    header: str,
    response: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VENDOR_KEY", "secret")

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == path
        assert "secret" in req.headers[header]
        assert "secret" not in req.content.decode()
        assert "tools" not in json.loads(req.content)
        return httpx.Response(200, json=response)

    config = ModelConfig(provider=provider, name="test", api_key_env="VENDOR_KEY")
    request = ModelRequest(
        model="test",
        messages=[Message(role="user", content="paper")],
        output_schema={"type": "object", "properties": {}},
        max_output_tokens=50,
        timeout_seconds=2,
    )
    result = asyncio.run(
        HTTPProvider(config, transport=httpx.MockTransport(handler)).generate(request)
    )
    assert (
        result.text == "{}" and result.input_tokens == 3 and result.output_tokens == 2
    )


@pytest.mark.parametrize("provider", ["openai_api", "anthropic_api", "gemini_api"])
def test_api_requires_explicit_key(provider: str) -> None:
    with pytest.raises(ValueError):
        ModelConfig(provider=provider, name="test")


@pytest.mark.parametrize(
    "provider,response",
    [
        ("openai_api", {"status": "incomplete", "output": []}),
        ("anthropic_api", {"stop_reason": "max_tokens", "content": []}),
        ("gemini_api", {"candidates": [{"finishReason": "MAX_TOKENS"}]}),
    ],
)
def test_incomplete_vendor_output_rejected(
    provider: str, response: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VENDOR_KEY", "secret")
    request = ModelRequest(
        model="test",
        messages=[],
        output_schema={},
        max_output_tokens=10,
        timeout_seconds=2,
    )
    adapter = HTTPProvider(
        ModelConfig(provider=provider, name="test", api_key_env="VENDOR_KEY"),
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=response)),
    )
    with pytest.raises(ProviderError):
        asyncio.run(adapter.generate(request))


def test_all_tood_provider_templates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.cli import initialize
    from koala_science.config import load_config

    for key in (
        "KOALA_MODEL",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "KOALA_AGENT_API_KEY",
    ):
        monkeypatch.setenv(key, "test")
    initialize(tmp_path, examples=True)
    for name in ("openai-api", "anthropic-api", "gemini-api", "gemini", "koala"):
        config = load_config(tmp_path / f"examples/tood/{name}.yaml")
        assert all(
            child.config.model == config.config.model for child in config.children
        )


@pytest.mark.parametrize("status", [401, 402, 403])
def test_proxy_does_not_fall_back(status: int, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_KEY", "secret")
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        return httpx.Response(status, text="secret")

    provider = HTTPProvider(
        ModelConfig(
            provider="koala_proxy",
            name="test",
            base_url="https://koala.science/llm",
            api_key_env="AGENT_KEY",
        ),
        transport=httpx.MockTransport(handler),
    )
    request = ModelRequest(
        model="test",
        messages=[],
        output_schema={},
        max_output_tokens=10,
        timeout_seconds=2,
    )
    with pytest.raises(ProviderError) as error:
        asyncio.run(provider.generate(request))
    assert not error.value.retryable and "secret" not in str(error.value)
    assert len(calls) == 1


def test_custom_provider_scaffold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.cli import initialize
    from koala_science.providers import build_provider

    initialize(tmp_path, examples=True)
    monkeypatch.setenv("CUSTOM_KEY", "secret")
    original_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret"
        return httpx.Response(
            200, json={"text": "{}", "model": "actual", "input_tokens": 4}
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )
    config = ModelConfig(
        provider="custom",
        name="test",
        factory=f"{tmp_path / 'providers/custom_api.py'}:build_provider",
        parameters={
            "endpoint": "https://example.test/review",
            "api_key_env": "CUSTOM_KEY",
        },
    )
    response = asyncio.run(
        build_provider(config).generate(
            ModelRequest(
                model="test",
                messages=[],
                output_schema={},
                max_output_tokens=20,
                timeout_seconds=2,
            )
        )
    )
    assert (
        response.text == "{}"
        and response.model == "actual"
        and response.input_tokens == 4
    )
