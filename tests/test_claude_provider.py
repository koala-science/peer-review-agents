"""Real subprocess tests with a fake Claude executable, without model access."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from koala_science.config import ModelConfig
from koala_science.providers import ProviderError, build_provider
from koala_science.types import Message, ModelRequest


@pytest.fixture
def fake_claude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from koala_science import claude_provider

    script = tmp_path / "fake.py"
    capture = tmp_path / "capture.json"
    script.write_text("""import sys, os, json, pathlib, time
prompt = sys.stdin.read()
pathlib.Path(os.environ["CLAUDE_TEST_CAPTURE"]).write_text(json.dumps({"args": sys.argv[1:], "cwd": os.getcwd(), "prompt": prompt, "key": os.environ.get("ANTHROPIC_API_KEY"), "owner": os.environ.get("KOALA_OWNER_ACCESS_TOKEN")}))
mode = os.environ.get("CLAUDE_TEST_MODE")
if mode == "hang": time.sleep(60)
if mode == "bad":
 print("SECRET bad output")
 sys.exit(0)
if mode == "large":
 print("x" * 100000)
 sys.exit(0)
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "structured_output": {"candidates": []}, "usage": {"input_tokens": 12, "output_tokens": 7}}))
""")
    monkeypatch.setenv("CLAUDE_TEST_CAPTURE", str(capture))
    monkeypatch.setattr(
        claude_provider, "_claude_command", lambda _: [sys.executable, str(script)]
    )
    return capture


def request(timeout: float = 5) -> ModelRequest:
    return ModelRequest(
        model="test",
        messages=[Message(role="user", content="paper text")],
        output_schema={"type": "object"},
        max_output_tokens=100,
        timeout_seconds=timeout,
    )


@pytest.mark.parametrize("api_mode", [False, True])
def test_auth_isolation_and_flags(
    fake_claude: Path, monkeypatch: pytest.MonkeyPatch, api_mode: bool
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ambient-key")
    monkeypatch.setenv("KOALA_OWNER_ACCESS_TOKEN", "human-secret")
    monkeypatch.setenv("REVIEW_KEY", "chosen-key")
    provider = build_provider(
        ModelConfig(
            provider="claude_cli",
            name="test",
            api_key_env="REVIEW_KEY" if api_mode else None,
        )
    )
    response = asyncio.run(provider.generate(request()))
    capture = json.loads(fake_claude.read_text())
    assert response.input_tokens == 12 and response.output_tokens == 7
    assert capture["key"] == ("chosen-key" if api_mode else None)
    assert capture["owner"] is None
    assert (
        "--safe-mode" in capture["args"]
        and "--no-session-persistence" in capture["args"]
    )
    assert "--strict-mcp-config" in capture["args"]
    assert ("--bare" in capture["args"]) == api_mode
    assert capture["args"][capture["args"].index("--tools") + 1] == ""
    assert "paper text" not in capture["args"]
    assert not Path(capture["cwd"]).exists()


@pytest.mark.parametrize("mode", ["bad", "hang", "large"])
def test_failure_is_bounded_and_sanitized(
    fake_claude: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    from koala_science import claude_provider

    monkeypatch.setattr(claude_provider, "MAX_RESPONSE_BYTES", 5000)
    monkeypatch.setenv("CLAUDE_TEST_MODE", mode)
    with pytest.raises(ProviderError) as error:
        asyncio.run(
            build_provider(ModelConfig(provider="claude_cli", name="test")).generate(
                request(0.5)
            )
        )
    assert "SECRET" not in str(error.value)
    assert not Path(json.loads(fake_claude.read_text())["cwd"]).exists()


def test_cancellation_reaps_process(
    fake_claude: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_TEST_MODE", "hang")
    processes = []
    spawn = asyncio.create_subprocess_exec

    async def track(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await spawn(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", track)

    async def cancel() -> None:
        task = asyncio.create_task(
            build_provider(ModelConfig(provider="claude_cli", name="test")).generate(
                request()
            )
        )
        for _ in range(200):
            if fake_claude.exists():
                break
            await asyncio.sleep(0.01)
        assert fake_claude.exists()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert processes and all(p.returncode is not None for p in processes)

    asyncio.run(cancel())


@pytest.mark.parametrize(
    "extra",
    [
        {"base_url": "https://example.com"},
        {"factory": "a.py:build"},
        {"parameters": {"key": "value"}},
        {"api_key_env": ""},
    ],
)
def test_config_rejects_ambiguous_modes(extra: dict) -> None:
    with pytest.raises(ValueError):
        ModelConfig(provider="claude_cli", name="test", **extra)
