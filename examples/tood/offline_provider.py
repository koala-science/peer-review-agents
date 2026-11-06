"""No-network plumbing check. This provider never judges or proposes arguments."""

import json

from koala_science import ModelRequest, ModelResponse


class OfflineSmokeProvider:
    """Send every proposal task an empty result without interpreting its sources."""

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Return a labeled fixture response, never an evidence decision."""
        payload = next(
            json.loads(message.content)
            for message in request.messages
            if message.role == "user"
        )
        if payload["stage"] != "proposal":
            raise ValueError("Offline smoke provider cannot make scientific judgments")
        return ModelResponse(
            text='{"candidates": []}', model="offline-smoke-no-scientific-review"
        )


def build_provider() -> OfflineSmokeProvider:
    """Construct the deterministic provider without credentials or network access."""
    return OfflineSmokeProvider()
