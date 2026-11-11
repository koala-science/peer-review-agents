"""`koala check` and `koala run`."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .audit import AuditLog, LoggedProvider, State
from .config import LoadedAgent, load_config
from .loop import AgentLoop
from .platform import PlatformClient, PlatformError
from .providers import ProviderError, build_provider
from .types import Message, ModelRequest


class Ping(BaseModel):
    ok: bool


KEY_ENV = "KOALA_AGENT_API_KEY"
KEY_FILE = ".koala_key"
NO_KEY = (
    "No agent key. Run `uv run koala login` and paste the key from "
    f"https://koala.science/dashboard, or set {KEY_ENV}."
)


def agent_key() -> str:
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise ValueError(NO_KEY)
    return key


def load_saved_key(root: Path) -> None:
    """Use the key `koala login` saved, unless the environment already sets one."""
    path = root / KEY_FILE
    if not os.environ.get(KEY_ENV, "").strip() and path.is_file():
        os.environ[KEY_ENV] = path.read_text(encoding="utf-8").strip()


def login(root: Path, key: str) -> int:
    """Check the key with the platform, then save it where every koala command finds it."""
    key = key.strip()
    if not key.startswith("cs_") or len(key.split()) != 1:
        raise ValueError("That is not an agent key; agent keys start with cs_")
    with PlatformClient(key) as client:
        profile = client.me()
    path = root / KEY_FILE
    # Create the file readable by its owner only, then write; never echo the key.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(key + "\n")
    if os.name != "nt":
        os.chmod(path, 0o600)
    print(
        f"Saved the key for agent {profile.get('name')} ({profile.get('id')}) to "
        f"{path} (gitignored). Every koala command in this folder now uses it."
    )
    return 0


def read_key() -> str:
    if sys.stdin.isatty():
        return getpass.getpass("Paste the agent API key (input is hidden): ")
    return sys.stdin.read()


def check(loaded: LoadedAgent) -> int:
    config = loaded.config
    print(
        f"Config: {loaded.path} (agent {config.name}, model {config.model.provider}:{config.model.name})"
    )
    with PlatformClient(agent_key()) as client:
        profile = client.me()
    print(f"Platform agent: {profile.get('name')} ({profile.get('id')})")
    problems = []
    print(f"Owner budget: {profile.get('budget')}")
    if profile.get("model_credit_usd") is not None:
        print(f"Koala model credit: ${profile['model_credit_usd']}")
    for role, model in (
        ("model", config.model),
        ("verifier_model", config.verifier_model),
    ):
        if model is None:
            continue
        response = asyncio.run(
            build_provider(model).generate(
                ModelRequest(
                    model=model.name,
                    messages=[
                        Message(
                            role="system", content="Return JSON matching the schema."
                        ),
                        Message(role="user", content='Reply with {"ok": true}.'),
                    ],
                    output_schema=Ping.model_json_schema(),
                    max_output_tokens=200,
                    timeout_seconds=120,
                )
            )
        )
        print(f"{role}: reachable ({response.model})")
    for problem in problems:
        print("Problem: " + problem, file=sys.stderr)
    return 1 if problems else 0


def run(loaded: LoadedAgent, *, dry_run: bool, once: bool) -> int:
    key = agent_key()
    dry_run = dry_run or loaded.config.run.dry_run
    logs = loaded.root / "logs"
    audit = AuditLog(logs, dry_run=dry_run)
    state = State(logs / "state.json", readonly=dry_run)
    providers = {"model": build_provider(loaded.config.model)}
    if loaded.config.verifier_model is not None:
        providers["verifier"] = build_provider(loaded.config.verifier_model)
    providers["selector"] = providers["model"]
    logged = {role: LoggedProvider(p, audit, role) for role, p in providers.items()}
    print(f"Run {audit.run_id}{' (dry run: nothing is submitted)' if dry_run else ''}")
    print(f"Logs: {audit.run_dir}")
    with PlatformClient(key, on_event=audit.call) as client:
        AgentLoop(loaded, client, logged, audit, state, dry_run=dry_run).run(once=once)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="koala", description="Autonomous reviewing agent for koala.science"
    )
    parser.add_argument("--config", default="agent.yaml", help="Path to agent.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "login", help="Save the agent key for this folder (paste it, or pipe it in)"
    )
    commands.add_parser("check", help="Validate config, platform key, and model access")
    run_parser = commands.add_parser("run", help="Select, review, and submit")
    run_parser.add_argument(
        "--dry-run", action="store_true", help="Do everything except submit"
    )
    run_parser.add_argument(
        "--once", action="store_true", help="Run one selection round, then stop"
    )
    args = parser.parse_args(argv)
    root = Path(args.config).resolve().parent
    try:
        if args.command == "login":
            return login(root, read_key())
        load_saved_key(root)
        if not os.environ.get(KEY_ENV, "").strip():
            raise ValueError(NO_KEY)
        loaded = load_config(Path(args.config))
        if args.command == "check":
            return check(loaded)
        return run(loaded, dry_run=args.dry_run, once=args.once)
    except (ValueError, ValidationError, PlatformError, ProviderError, OSError) as exc:
        message = exc.public_message if isinstance(exc, ProviderError) else str(exc)
        print(f"Error: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
