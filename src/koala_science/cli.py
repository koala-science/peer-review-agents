"""Portable CLI over the public API."""

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

from pydantic import ValidationError

from .config import load_config
from .platform import PlatformError
from .runner import Agent
from .scaffold import INIT_PROVIDERS, initialize, setup_choices
from .workspace import PaperWorkspace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="koala", description="Review local papers with inspectable evidence"
    )
    parser.add_argument("--config", default=None)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("directory", nargs="?", default=".")
    init.add_argument(
        "--examples",
        action="store_true",
        help="Include optional examples and extension templates",
    )
    init.add_argument(
        "--provider",
        choices=INIT_PROVIDERS,
        help="Model provider for the starter agent",
    )
    init.add_argument(
        "--preset",
        choices=("quick", "default"),
        help="Starting review breadth and budget",
    )
    validate = commands.add_parser("validate")
    validate.add_argument("--config", default=argparse.SUPPRESS)
    validate.add_argument("--workspace", default="paper.yaml")
    review = commands.add_parser("review")
    review.add_argument("paper", nargs="?")
    review.add_argument("--config", default=argparse.SUPPRESS)
    review.add_argument("--source", action="append", default=[])
    review.add_argument("--output")
    review.add_argument("--workspace", default="paper.yaml")
    review.add_argument(
        "--platform-context",
        action="store_true",
        help="Read existing public arguments for novelty checks (GET only; requires a paper workspace and claims strategy)",
    )
    submit_parser = commands.add_parser("submit")
    submit_parser.add_argument("--workspace", default="paper.yaml")
    submit_parser.add_argument("--send", action="store_true")
    submit_parser.add_argument("--select", action="store_true")
    submit_parser.add_argument("--run")
    submit_parser.add_argument("--argument", action="append", default=[])
    submit_parser.add_argument("--allow-partial", action="store_true")
    submit_parser.add_argument("--confirm-version", action="store_true")
    submit_parser.add_argument("--wait", type=float, nargs="?", const=60, default=0)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            provider, preset = setup_choices(args.provider, args.preset)
            initialize(
                args.directory, examples=args.examples, provider=provider, preset=preset
            )
            print(f"Workspace created: {args.directory}")
            print("Edit paper.yaml for your manuscript and agent.yaml for your model.")
            print(
                "Set KOALA_MODEL and any provider credentials, then run koala validate and koala review."
            )
            return 0
        if args.command == "validate":
            workspace = (
                PaperWorkspace.load(args.workspace)
                if Path(args.workspace).exists()
                else None
            )
            load_config(
                args.config or (workspace.agent_config if workspace else "agent.yaml")
            )
            print("Configuration is valid")
            return 0
        if args.command == "submit":
            from .submission import submit

            return submit(
                PaperWorkspace.load(args.workspace),
                send=args.send,
                run=args.run,
                arguments=args.argument,
                select=args.select,
                allow_partial=args.allow_partial,
                confirm_version=args.confirm_version,
                wait=args.wait,
            )
        workspace = PaperWorkspace.load(args.workspace) if args.paper is None else None
        paper = workspace.manuscript if workspace else args.paper
        sources = (
            [*workspace.sources, *((workspace.root / p).resolve() for p in args.source)]
            if workspace
            else args.source
        )
        agent = Agent.from_config(
            args.config or (workspace.agent_config if workspace else "agent.yaml")
        )
        output = (
            ((workspace.root if workspace else Path.cwd()) / args.output).resolve()
            if args.output
            else (workspace.root if workspace else Path.cwd())
            / "runs"
            / uuid.uuid4().hex
        )
        if output.exists() and (not output.is_dir() or any(output.iterdir())):
            raise ValueError("Output directory must be new or empty")
        known_arguments = None
        if args.platform_context:
            if workspace is None or workspace.identity is None:
                raise ValueError(
                    "--platform-context requires a paper workspace with an arXiv identity"
                )
            if agent.loaded.config.review_strategy != "claims":
                raise ValueError("--platform-context requires review_strategy: claims")
            from .platform import PlatformClient

            print("Reading platform paper and public arguments...", flush=True)
            with PlatformClient() as api:
                found = api.find_paper(
                    workspace.identity[0],
                    workspace.config.title,
                    workspace.config.platform_paper_id,
                )
                if not found:
                    raise ValueError(
                        "Platform paper not found; review locally without --platform-context or choose an existing paper"
                    )
                public = api.pages("papers/" + found["id"] + "/arguments")
            known_arguments = [
                {key: item.get(key) for key in ("id", "claim", "position")}
                for item in public
            ]
            print(
                f"Loaded {len(known_arguments)} public arguments for novelty checks (read-only snapshot).",
                flush=True,
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        journal = output.parent / f".{output.name}.journal.jsonl"
        try:
            fd = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise ValueError(
                "Interrupted journal exists; choose a new output directory"
            ) from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"status": "running"}) + "\n")
        initial_size = journal.stat().st_size
        print(
            f"Reviewing with {agent.loaded.config.model.provider}; "
            f"up to {agent.loaded.config.limits.max_model_calls} model calls. "
            "Mapping and checking evidence can take several minutes.",
            flush=True,
        )
        try:
            result = asyncio.run(
                agent.areview(
                    paper,
                    sources=sources,
                    journal=journal,
                    known_arguments=known_arguments,
                )
            )
        except (ValueError, OSError):
            if journal.stat().st_size == initial_size:
                journal.unlink()
            raise
        result.save(output)
        journal.unlink()
        if workspace:
            workspace.record_run(output, result.status)
        print(f"{output}: {len(result.arguments)} arguments ({result.status})")
        print(
            f"{result.manifest['model_calls']} model calls; "
            f"{result.manifest['elapsed_seconds']:.1f} seconds. "
            "See arguments.md for the review summary."
        )
        return {"complete": 0, "partial": 4, "failed": 3}[result.status]
    except PlatformError as exc:
        print(str(exc), file=sys.stderr)
        return 4 if exc.uncertain else 3
    except (ValueError, OSError) as exc:
        # Validation exceptions can include environment-expanded values.
        if isinstance(exc, ValidationError):
            detail = "; ".join(
                f"{'.'.join(str(part) for part in error['loc'])}: {error['type']}"
                for error in exc.errors(include_input=False, include_context=False)
            )
        elif isinstance(exc, OSError):
            detail = f"Cannot access input or output path ({type(exc).__name__})"
        else:
            detail = str(exc)
        print(
            f"Configuration or input error: {detail}",
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        print("Interrupted; diagnostic journal preserved", file=sys.stderr)
        return 4
    except Exception as exc:  # noqa: BLE001 -- CLI boundary must not leak custom exception secrets
        print(
            f"Runtime failure ({type(exc).__name__}); diagnostic journal preserved",
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    sys.exit(main())
