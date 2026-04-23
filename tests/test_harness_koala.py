"""Tests for agent_definition/harness/koala.py — KoalaClient MCP URL."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock


def _load_koala_module():
    sys.modules.setdefault("httpx", MagicMock())
    path = Path(__file__).parent.parent / "agent_definition" / "harness" / "koala.py"
    spec = importlib.util.spec_from_file_location("_harness_koala", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_koala_client_mcp_url_uses_default(monkeypatch):
    monkeypatch.delenv("KOALA_BASE_URL", raising=False)
    module = _load_koala_module()
    client = module.KoalaClient(api_key="test-key")
    assert client.mcp_url == "https://koala.science/mcp"


def test_koala_client_mcp_url_honors_env(monkeypatch):
    monkeypatch.setenv("KOALA_BASE_URL", "https://staging.koala.science")
    module = _load_koala_module()
    client = module.KoalaClient(api_key="test-key")
    assert client.mcp_url == "https://staging.koala.science/mcp"
