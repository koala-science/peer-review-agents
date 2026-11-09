"""Gemini subprocess boundary without model access."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from koala_science.config import ModelConfig
from koala_science.providers import ProviderError, build_provider
from koala_science.types import ModelRequest


@pytest.mark.parametrize("mode", ["ok", "bad", "hang", "cancel", "oversize"])
def test_isolated_gemini(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    from koala_science import gemini_provider

    home = tmp_path / "login"
    (home / ".gemini").mkdir(parents=True)
    (home / ".gemini/oauth_creds.json").write_text("{}")
    capture = tmp_path / "capture.json"
    script = tmp_path / "fake.py"
    script.write_text("""import os, sys, json, pathlib, time
if "--version" in sys.argv:
 print("0.60.0")
 sys.exit()
sys.stdin.read()
pathlib.Path(os.environ["TEST_CAPTURE"]).write_text(json.dumps({"home": os.environ["GEMINI_CLI_HOME"], "args": sys.argv, "key": os.environ.get("GEMINI_API_KEY")}))
if os.environ["TEST_MODE"] in ("hang", "cancel"): time.sleep(60)
if os.environ["TEST_MODE"] == "oversize":
 print("x" * 10_000_000)
 sys.exit()
print("bad" if os.environ["TEST_MODE"] == "bad" else json.dumps({"response": "{}", "stats": {"tools": {"totalCalls": 0}}}))
""")
    monkeypatch.setenv("GEMINI_CLI_HOME", str(home))
    monkeypatch.setenv("GEMINI_API_KEY", "ambient-secret")
    monkeypatch.setenv("TEST_CAPTURE", str(capture))
    monkeypatch.setenv("TEST_MODE", mode)
    monkeypatch.setattr(
        gemini_provider, "_command", lambda _: [sys.executable, str(script)]
    )
    provider = build_provider(ModelConfig(provider="gemini_cli", name="test"))
    request = ModelRequest(
        model="test",
        messages=[],
        output_schema={},
        max_output_tokens=10,
        timeout_seconds=1 if mode == "hang" else 5,
    )
    if mode == "cancel":

        async def cancel() -> None:
            task = asyncio.create_task(provider.generate(request))
            for _ in range(100):
                if capture.exists():
                    break
                await asyncio.sleep(0.005)
            assert capture.exists()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        asyncio.run(cancel())
    elif mode == "ok":
        assert asyncio.run(provider.generate(request)).text == "{}"
    elif mode == "oversize":
        with pytest.raises(ProviderError, match="Gemini output exceeds size limit"):
            asyncio.run(provider.generate(request))
    else:
        with pytest.raises(ProviderError):
            asyncio.run(provider.generate(request))
    data = json.loads(capture.read_text())
    assert data["key"] is None and not Path(data["home"]).exists()


@pytest.mark.parametrize("provider", ["codex_cli", "gemini_cli"])
def test_login_provider_rejects_api_key_with_own_name(provider: str) -> None:
    with pytest.raises(ValueError, match=f"{provider} uses CLI authentication"):
        ModelConfig(provider=provider, name="test", api_key_env="TEST_KEY")
