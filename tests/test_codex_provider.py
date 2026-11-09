"""Behavioral tests use a real child process without contacting a model."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from koala_science.config import ModelConfig, load_config
from koala_science.providers import ProviderError, build_provider
from koala_science.types import Message, ModelRequest


def request(timeout: float = 5.0) -> ModelRequest:
    return ModelRequest(
        model="test-model",
        messages=[
            Message(role="system", content="Review supplied evidence only."),
            Message(role="user", content="Untrusted paper: $(do not execute)"),
        ],
        output_schema={
            "type": "object",
            "properties": {
                "candidates": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                }
            },
            "required": [],
            "additionalProperties": False,
        },
        max_output_tokens=1000,
        timeout_seconds=timeout,
    )


@pytest.fixture
def fake_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from koala_science import codex_provider

    script = tmp_path / "fake codex.py"
    script.write_text(
        """
import json, os, pathlib, sys, time
args = sys.argv[1:]
prompt = sys.stdin.read()
schema = json.loads(pathlib.Path(args[args.index("--output-schema") + 1]).read_text())
pathlib.Path(os.environ["CODEX_TEST_CAPTURE"]).write_text(json.dumps({
    "args": args, "prompt": prompt, "schema": schema, "cwd": os.getcwd(), "pid": os.getpid()}))
mode = os.environ.get("CODEX_TEST_MODE", "ok")
if mode == "hang":
    time.sleep(60)
if mode == "fail":
    print("SECRET-do-not-leak", file=sys.stderr)
    sys.exit(1)
if mode == "oversize":
    print("x" * 100000)
    sys.exit(0)
if mode == "tool":
    print(json.dumps({"type": "item.started", "item": {"type": "command_execution"}}), flush=True)
    time.sleep(60)
print(json.dumps({"type": "thread.started", "thread_id": "test"}))
print(json.dumps({"type": "turn.started"}))
if mode == "warning":
    print(json.dumps({"type": "item.completed", "item": {"type": "error", "message": "Optional tool unavailable"}}))
if mode != "incomplete":
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 12, "output_tokens": 7}}))
if mode != "missing":
    pathlib.Path(args[args.index("--output-last-message") + 1]).write_text('{"candidates": []}')
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        codex_provider, "_codex_command", lambda _: [sys.executable, str(script)]
    )
    capture = tmp_path / "capture.json"
    monkeypatch.setenv("CODEX_TEST_CAPTURE", str(capture))
    return capture


def test_codex_provider_routes_without_http() -> None:
    from koala_science.codex_provider import CodexCLIProvider

    config = ModelConfig(provider="codex_cli", name="test-model")
    assert isinstance(build_provider(config), CodexCLIProvider)


@pytest.mark.parametrize(
    "extra",
    [
        {"base_url": "https://example.com"},
        {"api_key_env": "KEY"},
        {"factory": "file.py:build"},
        {"parameters": {"x": 1}},
        {"base_url": ""},
        {"api_key_env": ""},
    ],
)
def test_codex_rejects_ambiguous_configuration(extra: dict) -> None:
    with pytest.raises(ValidationError):
        ModelConfig(provider="codex_cli", name="test-model", **extra)


def test_codex_cli_sends_stdin_schema_and_records_usage(fake_cli: Path) -> None:
    provider = build_provider(ModelConfig(provider="codex_cli", name="test-model"))
    original = request()
    response = asyncio.run(provider.generate(original))
    assert json.loads(response.text) == {"candidates": []}
    assert response.input_tokens == 12
    assert response.output_tokens == 7
    assert response.model == "unknown (Codex CLI requested test-model)"
    capture = json.loads(fake_cli.read_text())
    assert "$(do not execute)" in capture["prompt"]
    assert not any("Untrusted paper" in arg for arg in capture["args"])
    assert "--ignore-user-config" in capture["args"]
    assert "read-only" in capture["args"]
    assert "features.shell_tool=false" in capture["args"]
    assert "features.plugins=false" in capture["args"]
    assert "features.hooks=false" in capture["args"]
    assert "features.multi_agent=false" in capture["args"]
    assert capture["schema"]["required"] == ["candidates"]
    assert "default" not in capture["schema"]["properties"]["candidates"]
    assert original.output_schema["required"] == []
    assert not Path(capture["cwd"]).exists()


@pytest.mark.parametrize("mode", ["fail", "incomplete", "missing", "tool"])
def test_codex_failure_is_sanitized_and_not_retried(
    fake_cli: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    monkeypatch.setenv("CODEX_TEST_MODE", mode)
    provider = build_provider(ModelConfig(provider="codex_cli", name="test-model"))
    with pytest.raises(ProviderError) as error:
        asyncio.run(provider.generate(request()))
    assert "SECRET" not in str(error.value)
    assert not error.value.retryable
    assert not Path(json.loads(fake_cli.read_text())["cwd"]).exists()


def test_codex_timeout_reaps_process(
    fake_cli: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CODEX_TEST_MODE", "hang")
    provider = build_provider(ModelConfig(provider="codex_cli", name="test-model"))
    with pytest.raises(ProviderError, match="deadline"):
        asyncio.run(provider.generate(request(0.5)))
    assert not Path(json.loads(fake_cli.read_text())["cwd"]).exists()


def test_codex_output_is_bounded(
    fake_cli: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science import codex_provider

    monkeypatch.setattr(codex_provider, "MAX_RESPONSE_BYTES", 1000)
    monkeypatch.setenv("CODEX_TEST_MODE", "oversize")
    provider = build_provider(ModelConfig(provider="codex_cli", name="test-model"))
    with pytest.raises(ProviderError):
        asyncio.run(provider.generate(request()))


def test_codex_startup_warning_requires_successful_completion(
    fake_cli: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CODEX_TEST_MODE", "warning")
    provider = build_provider(ModelConfig(provider="codex_cli", name="test-model"))
    assert json.loads(asyncio.run(provider.generate(request())).text) == {
        "candidates": []
    }


def test_tood_codex_template_inherits_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.cli import initialize

    monkeypatch.setenv("KOALA_MODEL", "test-model")
    initialize(tmp_path, examples=True)
    config = load_config(tmp_path / "examples/tood/codex.yaml")
    assert config.config.model.provider == "codex_cli"
    assert all(c.config.model == config.config.model for c in config.children)
    assert config.config.limits.max_concurrency == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows npm installation")
def test_resolve_windows_npm_shim_without_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science import codex_provider

    shim = tmp_path / "codex.cmd"
    shim.touch()
    native = (
        tmp_path
        / "node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe"
    )
    native.parent.mkdir(parents=True)
    native.touch()
    monkeypatch.setattr(codex_provider.shutil, "which", lambda _: str(shim))
    assert codex_provider._codex_command(None) == [str(native)]


def test_codex_cancellation_reaps_owned_process(
    fake_cli: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CODEX_TEST_MODE", "hang")
    processes = []
    spawn = asyncio.create_subprocess_exec

    async def track(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        process = await spawn(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", track)

    async def cancel() -> None:
        provider = build_provider(ModelConfig(provider="codex_cli", name="test-model"))
        task = asyncio.create_task(provider.generate(request()))
        for _ in range(100):
            if fake_cli.exists():
                break
            await asyncio.sleep(0.01)
        assert fake_cli.exists()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert processes and all(p.returncode is not None for p in processes)

    asyncio.run(cancel())


def test_cli_manifest_discloses_codex_limits(
    fake_cli: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.cli import initialize, main

    monkeypatch.setenv("KOALA_MODEL", "test-model")
    initialize(tmp_path / "workspace", examples=True)
    root = tmp_path / "workspace"
    assert main(["validate", "--config", str(root / "examples/tood/codex.yaml")]) == 0
    assert (
        main(
            [
                "review",
                str(root / "sample.md"),
                "--config",
                str(root / "examples/tood/codex.yaml"),
                "--output",
                str(root / "result"),
            ]
        )
        == 0
    )
    manifest = json.loads((root / "result/manifest.json").read_text())
    assert manifest["model_calls"] > 0
    assert (
        manifest["provider_notes"][0]["model_call_unit"]
        == "CLI invocation; internal requests unknown"
    )
    assert (
        manifest["provider_notes"][0]["output_token_limit"] == "prompt instruction only"
    )
    assert (
        manifest["provider_notes"][0]["input_token_limit"]
        == "Koala request only; CLI context is additional"
    )
