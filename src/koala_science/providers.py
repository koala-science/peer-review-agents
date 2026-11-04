"""HTTP model adapters. Errors exclude response bodies and credentials."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from urllib.parse import quote

import httpx

from .config import ModelConfig
from .types import ModelProvider, ModelRequest, ModelResponse

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
HTTP_HINTS = {
    400: "request or structured output unsupported",
    401: "invalid credential",
    402: "insufficient model credit",
    403: "credential or model not allowed",
    429: "rate limit",
}


class ProviderError(RuntimeError):
    def __init__(
        self, message: str, *, retryable: bool = False, status_code: int | None = None
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code

    @property
    def public_message(self) -> str:
        """A diagnostic category that never includes an adapter's exception text."""
        if type(self.status_code) is int and 100 <= self.status_code <= 599:
            return f"Model HTTP {self.status_code}: {HTTP_HINTS.get(self.status_code, 'model service error')}"
        return "Model provider failed"


class HTTPProvider:
    def __init__(
        self, config: ModelConfig, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.config, self.transport = config, transport

    async def generate(self, request: ModelRequest) -> ModelResponse:
        config = self.config
        headers = {"Accept-Encoding": "identity"}
        if config.api_key_env:
            headers["Authorization"] = f"Bearer {os.environ[config.api_key_env]}"
        if config.provider == "koala_proxy":
            url = f"{config.base_url.rstrip('/')}/v1beta/models/{quote(request.model, safe='')}:generateContent"
            body = {
                "systemInstruction": {
                    "parts": [
                        {"text": m.content}
                        for m in request.messages
                        if m.role == "system"
                    ]
                },
                "contents": [
                    {
                        "role": "model" if m.role == "assistant" else "user",
                        "parts": [{"text": m.content}],
                    }
                    for m in request.messages
                    if m.role != "system"
                ],
                "generationConfig": {
                    "maxOutputTokens": request.max_output_tokens,
                    "responseMimeType": "application/json",
                    "responseJsonSchema": request.output_schema,
                },
            }
        else:
            url = f"{config.base_url.rstrip('/')}/chat/completions"
            body = {
                "model": request.model,
                "messages": [m.model_dump() for m in request.messages],
                "max_tokens": request.max_output_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "koala_result",
                        "schema": request.output_schema,
                    },
                },
            }
        try:
            async with (
                httpx.AsyncClient(
                    transport=self.transport, timeout=request.timeout_seconds
                ) as client,
                client.stream("POST", url, headers=headers, json=body) as response,
            ):
                if response.status_code >= 300:
                    code = response.status_code
                    hint = HTTP_HINTS.get(code, "model service error")
                    raise ProviderError(
                        f"Model HTTP {code}: {hint}",
                        retryable=code == 429 or code >= 500,
                        status_code=code,
                    )
                if (
                    response.headers.get("content-encoding", "identity").lower()
                    != "identity"
                ):
                    raise ProviderError("Compressed model responses are not supported")
                chunks = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    if len(chunks) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise ProviderError("Model response exceeds size limit")
                    chunks.extend(chunk)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise ProviderError("Model transport failed", retryable=True) from exc
        try:
            data = json.loads(chunks)
            if config.provider == "koala_proxy":
                candidate = data["candidates"][0]
                if candidate.get("finishReason", "STOP") != "STOP":
                    raise ProviderError("Model output was blocked or truncated")
                text = "".join(
                    p.get("text", "")
                    for p in candidate["content"]["parts"]
                    if not p.get("thought")
                )
                usage = data.get("usageMetadata", {})
                return ModelResponse(
                    text=text,
                    model=data.get("modelVersion", request.model),
                    input_tokens=usage.get("promptTokenCount"),
                    output_tokens=(
                        usage.get("candidatesTokenCount", 0)
                        + usage.get("thoughtsTokenCount", 0)
                    )
                    if usage
                    else None,
                )
            choice = data["choices"][0]
            if choice.get("finish_reason", "stop") != "stop":
                raise ProviderError("Model output was blocked or truncated")
            usage = data.get("usage", {})
            return ModelResponse(
                text=choice["message"]["content"],
                model=data.get("model", request.model),
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
            )
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderError("Invalid model response envelope") from exc


def build_provider(config: ModelConfig) -> ModelProvider:
    if config.provider != "custom":
        return HTTPProvider(config)
    path, symbol = config.factory.rsplit(":", 1)
    name = "koala_custom_provider_" + hashlib.sha256(path.encode()).hexdigest()
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("Custom provider must be an importable Python file")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        raise
    provider = getattr(module, symbol)(**config.parameters)
    if not callable(getattr(provider, "generate", None)):
        raise TypeError("Custom factory must return a ModelProvider")
    return provider
