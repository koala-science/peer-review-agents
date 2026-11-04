"""Adapt this example service contract to your own API."""

import os

import httpx

from koala_science import ModelRequest, ModelResponse


class CustomAPI:
    def __init__(self, endpoint: str, api_key_env: str):
        self.endpoint, self.api_key_env = endpoint, api_key_env

    async def generate(self, request: ModelRequest) -> ModelResponse:
        async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
            response = await client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {os.environ[self.api_key_env]}"},
                json={
                    "model": request.model,
                    "messages": [m.model_dump() for m in request.messages],
                    "response_schema": request.output_schema,
                    "max_tokens": request.max_output_tokens,
                },
            )
            response.raise_for_status()
            return ModelResponse(text=response.json()["text"], model=request.model)


def build_provider(*, endpoint: str, api_key_env: str) -> CustomAPI:
    return CustomAPI(endpoint, api_key_env)
