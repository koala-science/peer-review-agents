"""Adapt this example service contract to your own API."""

import json
import os

import httpx

from koala_science import ModelRequest, ModelResponse
from koala_science.providers import MAX_RESPONSE_BYTES, ProviderError


class CustomAPI:
    def __init__(self, endpoint: str, api_key_env: str) -> None:
        self.endpoint, self.api_key_env = endpoint, api_key_env

    async def generate(self, request: ModelRequest) -> ModelResponse:
        try:
            async with (
                httpx.AsyncClient(timeout=request.timeout_seconds) as client,
                client.stream(
                    "POST",
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {os.environ[self.api_key_env]}",
                        "Accept-Encoding": "identity",
                    },
                    json={
                        "model": request.model,
                        "messages": [m.model_dump() for m in request.messages],
                        "response_schema": request.output_schema,
                        "max_tokens": request.max_output_tokens,
                    },
                ) as response,
            ):
                if response.status_code >= 300:
                    raise ProviderError(
                        "Custom service rejected request",
                        status_code=response.status_code,
                        retryable=response.status_code == 429
                        or response.status_code >= 500,
                    )
                if response.headers.get("content-encoding", "identity") != "identity":
                    raise ProviderError("Compressed response unsupported")
                data = bytearray()
                async for chunk in response.aiter_bytes(65536):
                    data.extend(chunk)
                    if len(data) > MAX_RESPONSE_BYTES:
                        raise ProviderError("Custom response exceeds size limit")
                envelope = json.loads(data)
                return ModelResponse(
                    text=envelope["text"],
                    model=envelope.get("model", request.model),
                    input_tokens=envelope.get("input_tokens"),
                    output_tokens=envelope.get("output_tokens"),
                )
        except httpx.TransportError as exc:
            raise ProviderError("Custom transport failed", retryable=True) from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError("Invalid custom response") from exc


def build_provider(*, endpoint: str, api_key_env: str) -> CustomAPI:
    return CustomAPI(endpoint, api_key_env)
