"""Shared process lifecycle and bounded streams for CLI model providers."""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
from pathlib import Path

from .providers import ProviderError


async def stop_process(process: asyncio.subprocess.Process) -> None:
    """Terminate and reap the owned process after cancellation or failure."""
    if process.returncode is None:
        if os.name == "nt":
            killer = await asyncio.create_subprocess_exec(
                str(
                    Path(os.environ.get("SystemRoot", "C:/Windows"))
                    / "System32/taskkill.exe"
                ),
                "/PID",
                str(process.pid),
                "/T",
                "/F",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            await killer.wait()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass

    # A full pipe can keep asyncio's transport open even after the child exits.
    # Callers cancel their readers before cleanup, so these drains own the streams.
    async def drain(stream: asyncio.StreamReader) -> None:
        while await stream.read(65536):
            pass

    await asyncio.gather(
        *(
            drain(stream)
            for stream in (process.stdout, process.stderr)
            if stream is not None
        )
    )
    await process.wait()


async def send_prompt(process: asyncio.subprocess.Process, prompt: bytes) -> None:
    assert process.stdin is not None
    try:
        process.stdin.write(prompt)
        await process.stdin.drain()
    except (BrokenPipeError, ConnectionResetError):
        pass
    finally:
        process.stdin.close()


async def read_stream(
    stream: asyncio.StreamReader, *, provider: str, max_bytes: int
) -> bytes:
    """Read one bounded output stream without exposing its contents in errors."""
    data = bytearray()
    while chunk := await stream.read(65536):
        if len(data) + len(chunk) > max_bytes:
            raise ProviderError(f"{provider} output exceeds size limit")
        data.extend(chunk)
    return bytes(data)
