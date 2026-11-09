"""Isolated Gemini CLI login requests. CLI requests and token limits are advisory."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ._cli_process import read_stream, send_prompt, stop_process
from .config import ModelConfig
from .providers import MAX_RESPONSE_BYTES, ProviderError
from .types import ModelRequest, ModelResponse


def _command(executable: str | None) -> list[str]:
    found = shutil.which(executable or "gemini")
    if not found:
        raise ProviderError("Install Gemini CLI 0.60 or later, or set model.executable")
    path = Path(found).resolve()
    if os.name == "nt" and path.suffix.lower() != ".exe":
        script = path.parent / "node_modules/@google/gemini-cli/dist/index.js"
        node = shutil.which("node")
        if not script.is_file() or not node:
            raise ProviderError(
                "Cannot resolve Gemini npm installation without a shell"
            )
        return [node, str(script)]
    return [str(path)]


async def _run(
    args: list[str], work: Path, env: dict[str, str], prompt: bytes
) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=work,
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **(
            {"creationflags": subprocess.CREATE_NO_WINDOW}
            if os.name == "nt"
            else {"start_new_session": True}
        ),
    )
    tasks = []
    try:
        tasks = [
            asyncio.create_task(
                read_stream(
                    process.stdout, provider="Gemini", max_bytes=MAX_RESPONSE_BYTES
                )
            ),
            asyncio.create_task(
                read_stream(
                    process.stderr, provider="Gemini", max_bytes=MAX_RESPONSE_BYTES
                )
            ),
            asyncio.create_task(send_prompt(process, prompt)),
        ]
        output, _, _ = await asyncio.gather(*tasks)
        await process.wait()
        if process.returncode:
            raise ProviderError(
                "Gemini failed; check installed login, model access, and CLI version"
            )
        return output
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await stop_process(process)


class GeminiCLIProvider:
    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    async def generate(self, request: ModelRequest) -> ModelResponse:
        try:
            return await asyncio.wait_for(
                self._generate(request), request.timeout_seconds
            )
        except asyncio.TimeoutError as exc:
            raise ProviderError("Gemini exceeded request deadline") from exc
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ProviderError("Gemini invocation or response failed") from exc

    async def _generate(self, request: ModelRequest) -> ModelResponse:
        command = _command(self.config.executable)
        login = (
            Path(os.environ.get("GEMINI_CLI_HOME", str(Path.home())))
            / ".gemini/oauth_creds.json"
        )
        if not login.is_file():
            raise ProviderError(
                "Run gemini interactively and sign in with Google before review; use gemini_api for API keys"
            )
        with tempfile.TemporaryDirectory(prefix="koala-gemini-") as directory:
            work = Path(directory)
            state = work / ".gemini"
            state.mkdir(mode=0o700)
            # Copy only CLI-owned OAuth state, never user settings, extensions or instructions.
            with (state / "oauth_creds.json").open("xb") as handle:
                os.chmod(handle.name, 0o600)
                handle.write(login.read_bytes())
            policy = work / "deny.toml"
            policy.write_text(
                '[[rule]]\ntoolName = "*"\ndecision = "deny"\npriority = 999\n',
                encoding="utf-8",
            )
            settings = {
                "security": {"auth": {"selectedType": "oauth-personal"}},
                "admin": {"extensions": {"enabled": False}, "mcp": {"enabled": False}},
                "tools": {"core": []},
                "hooksConfig": {"enabled": False},
                "skills": {"enabled": False},
                "context": {
                    "fileName": [],
                    "includeDirectoryTree": False,
                    "discoveryMaxDirs": 0,
                },
                "general": {"enableAutoUpdate": False},
                "adminPolicyPaths": [str(policy)],
                "advanced": {"ignoreLocalEnv": True},
                "telemetry": {"enabled": False},
            }
            config = state / "settings.json"
            config.write_text(json.dumps(settings), encoding="utf-8")
            env = {
                k: v
                for k, v in os.environ.items()
                if not k.upper().startswith(
                    ("GEMINI_", "GOOGLE_", "KOALA_", "ANTHROPIC_", "OPENAI_")
                )
            }
            env.update(
                GEMINI_CLI_HOME=str(work),
                GEMINI_CLI_SYSTEM_SETTINGS_PATH=str(config),
                GEMINI_CLI_SYSTEM_DEFAULTS_PATH=str(config),
            )
            version = (
                (await _run(command + ["--version"], work, env, b"")).decode().strip()
            )
            match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
            if not match or tuple(map(int, match.groups())) < (0, 60, 0):
                raise ProviderError(
                    "Gemini CLI 0.60 or later is required for isolation controls"
                )
            prompt = json.dumps(
                {
                    "instruction": "Review supplied data only. Never use tools. Return only JSON matching schema.",
                    "schema": request.output_schema,
                    "max_output_tokens": request.max_output_tokens,
                    "messages": [m.model_dump() for m in request.messages],
                }
            ).encode()
            data = json.loads(
                await _run(
                    command
                    + [
                        "--prompt",
                        "",
                        "--model",
                        request.model,
                        "--output-format",
                        "json",
                    ],
                    work,
                    env,
                    prompt,
                )
            )
            if data.get("error") or data.get("stats", {}).get("tools", {}).get(
                "totalCalls", 0
            ):
                raise ProviderError("Gemini reported an error or tool activity")
            text = data["response"]
            if not isinstance(text, str) or not text.strip():
                raise ProviderError("Gemini returned no final text")
            models = data.get("stats", {}).get("models", {})
            counts = [m.get("tokens", {}) for m in models.values()]
            return ModelResponse(
                text=text,
                model=f"unknown (Gemini CLI requested {request.model})",
                input_tokens=sum(c["prompt"] for c in counts)
                if counts and all(type(c.get("prompt")) is int for c in counts)
                else None,
                output_tokens=sum(
                    c["candidates"] + c.get("thoughts", 0) for c in counts
                )
                if counts and all(type(c.get("candidates")) is int for c in counts)
                else None,
            )
