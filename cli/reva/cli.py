"""reva CLI — reviewer agent command-line tool."""

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import click
from dotenv import load_dotenv

from reva.backends import BACKEND_CHOICES, get_backend
from reva.config import DEFAULT_INITIAL_PROMPT, find_config, load_config, write_default_config
from reva.prompt import assemble_prompt
from reva.tmux import (
    build_launch_script,
    create_session,
    has_session,
    kill_all_sessions,
    kill_session,
    list_sessions,
)

STARTER_SYSTEM_PROMPT = (
    "# Agent: {name}\n\n"
    "Describe this agent's reviewing focus and style here.\n"
)


def _load_project_env(config_path: str | None) -> None:
    """Load the project's `.env` so env-driven settings reach every subcommand."""
    found = find_config(config_path)
    project_root = found.parent if found is not None else Path.cwd()
    load_dotenv(project_root / ".env", override=False)


@click.group()
@click.option("--config", "config_path", default=None, help="Path to config.toml.")
@click.pass_context
def main(ctx, config_path):
    """reva — reviewer agent CLI."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    _load_project_env(config_path)


def _get_config(ctx):
    return load_config(ctx.obj.get("config_path"))


# --------------------------------------------------------------------------- #
# reva init
# --------------------------------------------------------------------------- #


@main.command()
@click.argument("path", default=".", type=click.Path())
@click.pass_context
def init(ctx, path):
    """Initialize a reva project (creates config.toml)."""
    target = Path(path).resolve()
    config_file = write_default_config(target)
    cfg = load_config(str(config_file))
    cfg.agents_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"Initialized reva project at {target}")
    click.echo(f"  config: {config_file}")


# --------------------------------------------------------------------------- #
# reva create
# --------------------------------------------------------------------------- #


@main.command()
@click.option("--name", required=True, help="Agent name (slug).")
@click.option(
    "--backend",
    type=click.Choice(BACKEND_CHOICES),
    default="claude-code",
    show_default=True,
    help="Agent backend.",
)
@click.pass_context
def create(ctx, name, backend):
    """Create a new agent directory with a starter system prompt."""
    cfg = _get_config(ctx)

    agent_dir = cfg.agents_dir / name
    if agent_dir.exists():
        raise click.ClickException(f"Agent directory already exists: {agent_dir}")
    agent_dir.mkdir(parents=True)

    (agent_dir / "system_prompt.md").write_text(
        STARTER_SYSTEM_PROMPT.format(name=name), encoding="utf-8"
    )

    config_data = {
        "name": name,
        "backend": backend,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (agent_dir / "config.json").write_text(
        json.dumps(config_data, indent=2), encoding="utf-8"
    )
    (agent_dir / ".agent_name").write_text(name, encoding="utf-8")

    click.echo(f"Created agent: {name}")
    click.echo(f"  directory: {agent_dir}")
    click.echo(f"  backend:   {backend}")
    click.echo(
        f"  next steps: edit {agent_dir / 'system_prompt.md'}, drop a key at "
        f"{agent_dir / '.api_key'}, then `reva launch --name {name}`"
    )


# --------------------------------------------------------------------------- #
# reva launch
# --------------------------------------------------------------------------- #


@main.command()
@click.option("--name", required=True, help="Agent name to launch.")
@click.option("--duration", type=float, default=None, help="Hours to run (omit for indefinite).")
@click.option("--backend", type=click.Choice(BACKEND_CHOICES), default=None, help="Override backend.")
@click.option(
    "--session-timeout",
    type=int,
    default=600,
    help="Max seconds per invocation before restart (default: 600).",
)
@click.pass_context
def launch(ctx, name, duration, backend, session_timeout):
    """Launch an agent in a tmux session."""
    cfg = _get_config(ctx)
    agent_dir = cfg.agents_dir / name
    if not agent_dir.exists():
        raise click.ClickException(f"Agent not found: {agent_dir}")

    api_key_path = agent_dir / ".api_key"
    if not api_key_path.exists() or not api_key_path.read_text(encoding="utf-8").strip():
        raise click.ClickException(
            f".api_key missing — ask the owner to provision it at "
            f"{cfg.koala_base_url}/owners and drop the key at {api_key_path}"
        )

    agent_config = json.loads((agent_dir / "config.json").read_text())
    backend_name = backend or agent_config["backend"]
    backend_obj = get_backend(backend_name)

    prompt = assemble_prompt(
        global_rules_path=cfg.global_rules_path,
        platform_skills_path=cfg.platform_skills_path,
        agent_prompt_path=agent_dir / "system_prompt.md",
    )
    (agent_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    (agent_dir / backend_obj.prompt_filename).write_text(prompt, encoding="utf-8")

    initial_prompt = DEFAULT_INITIAL_PROMPT.format(koala_base_url=cfg.koala_base_url)
    (agent_dir / "initial_prompt.txt").write_text(initial_prompt, encoding="utf-8")

    escaped_prompt = initial_prompt.replace('"', '\\"')
    cmd = backend_obj.command_template.format(prompt=escaped_prompt)

    resume_cmd = backend_obj.resume_command_template
    script = build_launch_script(
        cmd,
        duration_hours=duration,
        session_timeout=session_timeout,
        resume_command=resume_cmd,
        session_id_extractor=backend_obj.session_id_extractor,
    )
    create_session(name, str(agent_dir), script)

    dur_str = f"{duration}h" if duration else "indefinite"
    click.echo(f"Launched: {name} ({backend_name}, {dur_str})")
    click.echo(f"  tmux session: reva_{name}")
    click.echo(f"  attach: tmux attach -t reva_{name}")


# --------------------------------------------------------------------------- #
# reva stop
# --------------------------------------------------------------------------- #


@main.command()
@click.option("--name", default=None, help="Agent name to stop.")
@click.option("--all", "kill_all", is_flag=True, help="Stop all running agents.")
@click.pass_context
def stop(ctx, name, kill_all):
    """Stop a running agent (kill its tmux session)."""
    if kill_all:
        count = kill_all_sessions()
        click.echo(f"Stopped {count} agent(s).")
    elif name:
        if kill_session(name):
            click.echo(f"Stopped: {name}")
        else:
            click.echo(f"No running session for: {name}")
    else:
        raise click.ClickException("Provide --name or --all.")


# hidden alias so `reva kill` still works
_kill = click.Command(name="kill", callback=stop.callback, params=stop.params, help=stop.help, hidden=True)
main.add_command(_kill)


# --------------------------------------------------------------------------- #
# reva delete
# --------------------------------------------------------------------------- #


@main.command()
@click.argument("names", nargs=-1, required=True)
@click.option("--force", is_flag=True, help="Skip confirmation.")
@click.pass_context
def delete(ctx, names, force):
    """Remove agent directories (kills running sessions first)."""
    cfg = _get_config(ctx)
    for name in names:
        agent_dir = cfg.agents_dir / name
        if not agent_dir.exists():
            click.echo(f"Not found: {name}")
            continue
        if not force:
            click.confirm(f"Delete {agent_dir}?", abort=True)
        if has_session(name):
            kill_session(name)
        shutil.rmtree(agent_dir)
        click.echo(f"Deleted: {name}")


# --------------------------------------------------------------------------- #
# reva status
# --------------------------------------------------------------------------- #


@main.command()
@click.pass_context
def status(ctx):
    """List running agents."""
    sessions = list_sessions()
    if not sessions:
        click.echo("No running agents.")
        return

    cfg = _get_config(ctx)
    click.echo(f"{'NAME':<30s} {'BACKEND':<15s} {'SESSION'}")
    click.echo("-" * 70)
    for s in sessions:
        backend_name = "?"
        agent_config_path = cfg.agents_dir / s.agent_name / "config.json"
        if agent_config_path.exists():
            agent_config = json.loads(agent_config_path.read_text())
            backend_name = agent_config.get("backend", "?")
        click.echo(f"{s.agent_name:<30s} {backend_name:<15s} {s.session}")


# --------------------------------------------------------------------------- #
# reva log
# --------------------------------------------------------------------------- #


@main.command(name="log")
@click.argument("name", required=False)
@click.option("--all", "watch_all", is_flag=True, help="Interleave all running agents.")
@click.pass_context
def log(ctx, name, watch_all):
    """Stream a readable live view of agent activity (ATIF-backed)."""
    from reva.render import render_step_terminal
    from reva.session import SessionContext

    cfg = _get_config(ctx)

    if watch_all:
        agents = sorted(d for d in cfg.agents_dir.iterdir() if d.is_dir() and (d / "agent.log").exists())
        if not agents:
            raise click.ClickException("No agent logs found.")
        log_files = [(a.name, a / "agent.log") for a in agents]
    elif name:
        agent_dir = cfg.agents_dir / name
        log_file = agent_dir / "agent.log"
        if not log_file.exists():
            raise click.ClickException(f"No agent.log found for: {name}")
        log_files = [(name, log_file)]
    else:
        agents = sorted(
            (d for d in cfg.agents_dir.iterdir() if d.is_dir() and (d / "agent.log").exists()),
            key=lambda d: (d / "agent.log").stat().st_mtime,
            reverse=True,
        )
        if not agents:
            raise click.ClickException("No agent logs found.")
        log_files = [(agents[0].name, agents[0] / "agent.log")]
        click.echo(f"Watching: {agents[0].name}\n")

    handles = {n: open(p, "r") for n, p in log_files}
    contexts = {n: SessionContext.for_agent(cfg.agents_dir / n) for n, _ in log_files}
    prefix = len(log_files) > 1

    try:
        while True:
            activity = False
            for agent_name, fh in handles.items():
                line = fh.readline()
                if not line:
                    continue
                activity = True
                sess = contexts[agent_name]
                for step in sess.consume_lines([line]):
                    for rendered in render_step_terminal(step, agent_name if prefix else None):
                        click.echo(rendered)
            if not activity:
                for agent_name, sess in contexts.items():
                    for step in sess.flush_pending():
                        for rendered in render_step_terminal(step, agent_name if prefix else None):
                            click.echo(rendered)
                    try:
                        sess.flush()
                    except Exception:
                        pass
                time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        for fh in handles.values():
            fh.close()
        for sess in contexts.values():
            try:
                sess.flush()
            except Exception:
                pass


# hidden alias so `reva watch` still works
_watch = click.Command(name="watch", callback=log.callback, params=log.params, help=log.help, hidden=True)
main.add_command(_watch)


# --------------------------------------------------------------------------- #
# reva view
# --------------------------------------------------------------------------- #


@main.command()
@click.option("--web", is_flag=True, help="Serve an interactive web UI instead of the TUI.")
@click.option("--host", default="127.0.0.1", show_default=True, help="Web host (with --web).")
@click.option("--port", default=8765, show_default=True, type=int, help="Web port (with --web).")
@click.pass_context
def view(ctx, web, host, port):
    """Launch the interactive ATIF viewer (TUI, or web with --web)."""
    cfg = _get_config(ctx)
    if web:
        from reva.web import serve

        serve(cfg, host=host, port=port)
        return
    from reva.viewer import RevaViewer

    app = RevaViewer(cfg=cfg)
    app.run()


# --------------------------------------------------------------------------- #
# reva archive / unarchive
# --------------------------------------------------------------------------- #


@main.command()
@click.option("--name", default=None, help="Agent name to archive.")
@click.option("--list", "list_archived", is_flag=True, help="List archived agents.")
@click.pass_context
def archive(ctx, name, list_archived):
    """Archive (retire) an agent by moving it to .archived/."""
    cfg = _get_config(ctx)
    archived_dir = cfg.agents_dir / ".archived"

    if list_archived:
        if not archived_dir.exists():
            click.echo("No archived agents.")
            return
        agents = sorted(
            d for d in archived_dir.iterdir()
            if d.is_dir() and (d / "config.json").exists()
        )
        if not agents:
            click.echo("No archived agents.")
            return
        for a in agents:
            click.echo(f"  {a.name}")
        click.echo(f"\n{len(agents)} archived agent(s)")
        return

    if not name:
        raise click.ClickException("Provide --name or --list.")

    agent_dir = cfg.agents_dir / name
    if not agent_dir.exists():
        raise click.ClickException(f"Agent not found: {name}")

    if has_session(name):
        kill_session(name)
        click.echo(f"Killed running session for: {name}")

    archived_dir.mkdir(parents=True, exist_ok=True)
    dest = archived_dir / name
    if dest.exists():
        raise click.ClickException(f"Already archived: {name}")
    shutil.move(str(agent_dir), str(dest))
    click.echo(f"Archived agent: {name}")


@main.command()
@click.option("--name", required=True, help="Agent name to unarchive.")
@click.pass_context
def unarchive(ctx, name):
    """Unarchive (restore) an agent from .archived/ back to agents_dir."""
    cfg = _get_config(ctx)
    archived_dir = cfg.agents_dir / ".archived"
    src = archived_dir / name
    if not src.exists():
        raise click.ClickException(f"Agent '{name}' is not archived.")

    dest = cfg.agents_dir / name
    if dest.exists():
        raise click.ClickException(f"Agent already exists at: {dest}")

    shutil.move(str(src), str(dest))
    click.echo(f"Unarchived agent: {name}")
