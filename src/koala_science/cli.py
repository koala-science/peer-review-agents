"""Portable CLI over the public API."""

import argparse
import asyncio
import json
import os
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .config import load_config
from .runner import Agent


def initialize(directory: str | Path) -> None:
    """Scaffold a workspace after checking every destination for conflicts."""
    target = Path(directory)
    root = files("koala_science").joinpath("templates")
    entries = []

    def collect(node: Any, relative: Path = Path()) -> None:
        for item in node.iterdir():
            if item.name == "__pycache__" or item.name.endswith(".pyc"):
                continue
            path = relative / item.name
            if item.is_dir():
                collect(item, path)
            else:
                entries.append((path, item.read_bytes()))

    collect(root)
    if not root.joinpath("examples").is_dir():
        # Editable installs read the canonical examples from this source checkout.
        # Wheels carry the same files under templates/examples through build mapping.
        checkout = Path(__file__).resolve().parents[2]
        examples = checkout / "examples"
        if not (checkout / "pyproject.toml").is_file() or not examples.is_dir():
            raise ValueError("Example templates are missing; reinstall the package")
        collect(examples, Path("examples"))
    conflicts = []
    for path, _ in entries:
        destination = target / path
        if (
            destination.exists()
            or destination.is_symlink()
            or any(p.exists() and not p.is_dir() for p in destination.parents)
            or any(
                p.is_symlink()
                for p in destination.parents
                if p != target and p.is_relative_to(target)
            )
        ):
            conflicts.append(str(path))
    if conflicts:
        raise ValueError("Initialization conflict: " + ", ".join(conflicts))
    for path, content in entries:
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="koala", description="Review local papers with inspectable evidence"
    )
    parser.add_argument("--config", default="agent.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("directory", nargs="?", default=".")
    validate = commands.add_parser("validate")
    validate.add_argument("--config", default=argparse.SUPPRESS)
    review = commands.add_parser("review")
    review.add_argument("paper")
    review.add_argument("--config", default=argparse.SUPPRESS)
    review.add_argument("--source", action="append", default=[])
    review.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            initialize(args.directory)
            print(f"Workspace created: {args.directory}")
            return 0
        if args.command == "validate":
            load_config(args.config)
            print("Configuration is valid")
            return 0
        agent = Agent.from_config(args.config)
        output = Path(args.output).resolve()
        if output.exists() and (not output.is_dir() or any(output.iterdir())):
            raise ValueError("Output directory must be new or empty")
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
        try:
            result = asyncio.run(
                agent.areview(args.paper, sources=args.source, journal=journal)
            )
        except (ValueError, OSError):
            if journal.stat().st_size == initial_size:
                journal.unlink()
            raise
        result.save(output)
        journal.unlink()
        print(f"{output}: {len(result.arguments)} arguments ({result.status})")
        return {"complete": 0, "partial": 4, "failed": 3}[result.status]
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
