"""
koala.py

Thin HTTP client for the Koala Science MCP endpoint.
All platform tool calls go through here.
"""
import os
import httpx

from reva.env import koala_base_url


class KoalaClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["COALESCENCE_API_KEY"]
        self.mcp_url = f"{koala_base_url()}/mcp"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self._id = 0

    def call_tool(self, name: str, arguments: dict) -> str:
        self._id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        resp = httpx.post(self.mcp_url, json=payload, headers=self.headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Koala Science error: {data['error']}")
        content = data.get("result", {}).get("content", [])
        return "\n".join(
            block.get("text", "") for block in content if block.get("type") == "text"
        )
