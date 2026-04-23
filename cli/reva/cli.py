"""reva CLI — reviewer agent command-line tool."""

import glob
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import click
from dotenv import load_dotenv

from reva.backends import BACKEND_CHOICES, get_backend
from reva.compiler import compile_agent_prompt, persona_to_markdown
from reva.config import DEFAULT_INITIAL_PROMPT, find_config, load_config, write_default_config
from reva.sampler import sample
from reva.tmux import (
    build_launch_script,
    create_session,
    has_session,
    kill_all_sessions,
    kill_session,
    list_sessions,
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
    # create default subdirectories
    cfg = load_config(str(config_file))
    for d in [
        cfg.agents_dir,
        cfg.personas_dir,
        cfg.roles_dir,
        cfg.interests_dir,
        cfg.review_methodology_dir,
        cfg.review_format_dir,
    ]:
        d.mkdir(parents=True, exist_ok=True)
    click.echo(f"Initialized reva project at {target}")
    click.echo(f"  config: {config_file}")


# --------------------------------------------------------------------------- #
# reva create
# --------------------------------------------------------------------------- #


@main.command()
@click.option("--name", required=True, help="Agent name (slug).")
@click.option("--backend", required=True, type=click.Choice(BACKEND_CHOICES), help="Agent backend.")
@click.option("--role", required=True, type=click.Path(exists=True), help="Path to role .md file.")
@click.option("--persona", required=True, type=click.Path(exists=True), help="Path to persona .json file.")
@click.option("--interest", required=True, type=click.Path(exists=True), help="Path to research interest .md file.")
@click.pass_context
def create(ctx, name, backend, role, persona, interest):
    """Create a new agent directory with compiled prompt."""
    cfg = _get_config(ctx)
    backend_obj = get_backend(backend)

    agent_dir = cfg.agents_dir / name
    if agent_dir.exists():
        raise click.ClickException(f"Agent directory already exists: {agent_dir}")
    agent_dir.mkdir(parents=True)

    # compile prompt
    prompt = compile_agent_prompt(
        role_path=Path(role),
        persona_path=Path(persona),
        interest_path=Path(interest),
        global_rules_path=cfg.global_rules_path,
        platform_skills_path=cfg.platform_skills_path,
        review_methodology_path=cfg.review_methodology_path,
        review_format_path=cfg.review_format_path,
    )

    # write files
    (agent_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    (agent_dir / backend_obj.prompt_filename).write_text(prompt, encoding="utf-8")
    initial_prompt = DEFAULT_INITIAL_PROMPT.format(
        owner_email=cfg.owner_email,
        owner_name=cfg.owner_name,
        owner_password=cfg.owner_password,
        github_repo=cfg.github_repo,
        koala_base_url=cfg.koala_base_url,
    )
    (agent_dir / "initial_prompt.txt").write_text(initial_prompt, encoding="utf-8")
    (agent_dir / ".agent_name").write_text(name, encoding="utf-8")

    config_data = {
        "name": name,
        "backend": backend,
        "role": str(Path(role).resolve()),
        "persona": str(Path(persona).resolve()),
        "interest": str(Path(interest).resolve()),
        "review_methodology": str(cfg.review_methodology_path.resolve()) if cfg.review_methodology_path else None,
        "review_format": str(cfg.review_format_path.resolve()) if cfg.review_format_path else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (agent_dir / "config.json").write_text(json.dumps(config_data, indent=2), encoding="utf-8")

    click.echo(f"Created agent: {name}")
    click.echo(f"  directory: {agent_dir}")
    click.echo(f"  backend:   {backend}")
    click.echo(f"  prompt:    {len(prompt)} chars")


# --------------------------------------------------------------------------- #
# reva launch
# --------------------------------------------------------------------------- #


@main.command()
@click.option("--name", required=True, help="Agent name to launch.")
@click.option("--duration", type=float, default=None, help="Hours to run (omit for indefinite).")
@click.option("--backend", type=click.Choice(BACKEND_CHOICES), default=None, help="Override backend.")
@click.option("--session-timeout", type=int, default=600, help="Max seconds per invocation before restart (default: 600).")
@click.pass_context
def launch(ctx, name, duration, backend, session_timeout):
    """Launch an agent in a tmux session."""
    cfg = _get_config(ctx)
    agent_dir = cfg.agents_dir / name
    if not agent_dir.exists():
        raise click.ClickException(f"Agent not found: {agent_dir}")

    agent_config = json.loads((agent_dir / "config.json").read_text())
    backend_name = backend or agent_config["backend"]
    backend_obj = get_backend(backend_name)

    # ensure backend-specific prompt file exists
    prompt_file = agent_dir / backend_obj.prompt_filename
    if not prompt_file.exists():
        prompt = (agent_dir / "prompt.md").read_text(encoding="utf-8")
        prompt_file.write_text(prompt, encoding="utf-8")

    initial_prompt = (agent_dir / "initial_prompt.txt").read_text(encoding="utf-8").strip()
    # escape double quotes for shell embedding
    escaped_prompt = initial_prompt.replace('"', '\\"')
    cmd = backend_obj.command_template.format(prompt=escaped_prompt)

    resume_cmd = backend_obj.resume_command_template
    script = build_launch_script(cmd, duration_hours=duration, session_timeout=session_timeout, resume_command=resume_cmd, session_id_extractor=backend_obj.session_id_extractor)
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

    # load backend from config.json where available
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
# reva list
# --------------------------------------------------------------------------- #


@main.command("list")
@click.argument("component", type=click.Choice(["roles", "personas", "interests", "agents"]))
@click.pass_context
def list_components(ctx, component):
    """List available components (roles, personas, interests, agents)."""
    cfg = _get_config(ctx)

    if component == "roles":
        _list_files(cfg.roles_dir, "*.md")
    elif component == "personas":
        _list_files(cfg.personas_dir, "*.json")
    elif component == "interests":
        _list_files(cfg.interests_dir, "**/*.md")
    elif component == "agents":
        _list_agents(cfg.agents_dir)


def _list_files(directory: Path, pattern: str):
    if not directory.exists():
        click.echo(f"Directory not found: {directory}")
        return
    files = sorted(directory.glob(pattern))
    files = [f for f in files if f.name != "README.md"]
    if not files:
        click.echo("  (none)")
        return
    for f in files:
        rel = f.relative_to(directory)
        click.echo(f"  {rel}")
    click.echo(f"\n{len(files)} file(s)")


def _list_agents(directory: Path):
    if not directory.exists():
        click.echo(f"Directory not found: {directory}")
        return
    agents = sorted(d for d in directory.iterdir() if d.is_dir() and (d / "config.json").exists())
    if not agents:
        click.echo("  (none)")
        return
    for a in agents:
        config = json.loads((a / "config.json").read_text())
        running = "running" if has_session(a.name) else "stopped"
        click.echo(f"  {a.name:<30s} {config.get('backend', '?'):<15s} {running}")
    click.echo(f"\n{len(agents)} agent(s)")


# --------------------------------------------------------------------------- #
# reva persona
# --------------------------------------------------------------------------- #


@main.group()
def persona():
    """Manage persona profiles."""
    pass


main.add_command(persona)


@persona.command("list")
@click.pass_context
def persona_list(ctx):
    """List available personas."""
    cfg = _get_config(ctx)
    _list_files(cfg.personas_dir, "*.json")


@persona.command("show")
@click.argument("name")
@click.pass_context
def persona_show(ctx, name):
    """Show a persona's details."""
    cfg = _get_config(ctx)
    path = cfg.personas_dir / f"{name}.json"
    if not path.exists():
        raise click.ClickException(f"Persona not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    click.echo(f"Name: {data['name']}")
    click.echo(f"Description: {data.get('description', '')}\n")

    click.echo("Trait vector:")
    for trait, value in data.get("trait_vector", {}).items():
        label = {-1: "Low", 0: "Neutral", 1: "High"}.get(value, str(value))
        click.echo(f"  {trait:<20s} {label}")

    rules = data.get("behavioral_rules", [])
    if rules:
        click.echo("\nBehavioral rules:")
        for r in rules:
            click.echo(f"  - {r}")

    forbidden = data.get("forbidden_behaviors", [])
    if forbidden:
        click.echo("\nForbidden:")
        for r in forbidden:
            click.echo(f"  - {r}")


# --------------------------------------------------------------------------- #
# reva interests
# --------------------------------------------------------------------------- #


@main.group()
def interests():
    """Manage research interest profiles."""
    pass


@interests.command("list-topics")
@click.option("--depth", type=int, multiple=True, default=None, help="Tree depths to show.")
@click.pass_context
def interests_list_topics(ctx, depth):
    """List taxonomy topics."""
    cfg = _get_config(ctx)
    taxonomy_path = cfg.interests_dir / "ml_taxonomy.json"
    if not taxonomy_path.exists():
        raise click.ClickException(f"Taxonomy not found: {taxonomy_path}")

    data = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    nodes = _walk_taxonomy(data)

    if depth:
        nodes = [n for n in nodes if n["depth"] in depth]
    # exclude root
    nodes = [n for n in nodes if n["depth"] > 0]

    for i, node in enumerate(nodes, 1):
        tag = "leaf" if node["is_leaf"] else f"parent, {len(node['children'])} children"
        click.echo(f"  {i:3d}. [depth={node['depth']}] {node['path']}  ({tag})")

    click.echo(f"\n{len(nodes)} topic(s)")


def _walk_taxonomy(node, parent_path="", depth=0):
    path = f"{parent_path} > {node['name']}" if parent_path else node["name"]
    children = node.get("children", [])
    entry = {
        "name": node["name"],
        "path": path,
        "depth": depth,
        "is_leaf": len(children) == 0,
        "children": [c["name"] for c in children],
    }
    results = [entry]
    for child in children:
        results.extend(_walk_taxonomy(child, path, depth + 1))
    return results


@interests.command("generate")
@click.option("--depth", type=int, multiple=True, help="Tree depths to generate for.")
@click.option("--levels", multiple=True, help="Expertise levels (senior, mid, junior, adjacent).")
@click.option("--dry-run", is_flag=True, help="Preview without calling API.")
@click.pass_context
def interests_generate(ctx, depth, levels, dry_run):
    """Generate interest profiles via LLM (placeholder)."""
    click.echo("Interest generation is not yet implemented in reva.")
    click.echo("Use the standalone generate_personas.py script for now.")


@interests.command("validate")
@click.pass_context
def interests_validate(ctx):
    """Validate generated interest profiles (placeholder)."""
    click.echo("Interest validation is not yet implemented in reva.")


# --------------------------------------------------------------------------- #
# reva batch
# --------------------------------------------------------------------------- #


@main.group()
def batch():
    """Batch operations on multiple agents."""
    pass


@batch.command("create")
@click.option("--roles", multiple=True, help="Role .md file globs (default: roles_dir/*.md).")
@click.option("--interests", "interest_globs", multiple=True, help="Interest .md file globs (default: interests_dir/**/*.md).")
@click.option("--personas", multiple=True, help="Persona .json file globs (default: personas_dir/*.json).")
@click.option(
    "--methodologies",
    "methodology_globs",
    multiple=True,
    help="Review methodology .md file globs. If provided, methodology becomes a sampled axis; otherwise the config default is used for every agent.",
)
@click.option(
    "--formats",
    "format_globs",
    multiple=True,
    help="Review format .md file globs. If provided, format becomes a sampled axis; otherwise the config default is used for every agent.",
)
@click.option("--n", "count", type=int, default=1, help="Number of agents to sample (default: 1).")
@click.option("--strategy", type=click.Choice(["stratified", "random"]), default="random")
@click.option("--seed", type=int, default=42)
@click.option("--backend", type=click.Choice(BACKEND_CHOICES), default="claude-code")
@click.option("--output-dir", type=click.Path(), default=None, help="Output directory (default: agents_dir).")
@click.option("--clean", is_flag=True, default=False, help="Kill running agents and wipe output dir before creating.")
@click.pass_context
def batch_create(ctx, roles, interest_globs, personas, methodology_globs, format_globs, count, strategy, seed, backend, output_dir, clean):
    """Create a batch of agents by sampling from role x interest x persona (optionally x methodology x format)."""
    cfg = _get_config(ctx)
    out = Path(output_dir) if output_dir else cfg.agents_dir

    if clean and out.exists():
        killed = kill_all_sessions()
        if killed:
            click.echo(f"Stopped {killed} running agent(s).")
        shutil.rmtree(out)
        click.echo(f"Cleared {out}")

    # fall back to config dirs when no globs provided
    role_files = _expand_globs(roles) if roles else sorted(
        str(f) for f in cfg.roles_dir.glob("*.md") if f.name != "README.md"
    )
    interest_files = _expand_globs(interest_globs) if interest_globs else sorted(
        str(f) for f in cfg.interests_dir.glob("**/*.md") if f.name != "README.md"
    )
    persona_files = _expand_globs(personas) if personas else sorted(
        str(f) for f in cfg.personas_dir.glob("*.json") if not f.name.startswith("all_")
    )
    methodology_files = _expand_globs(methodology_globs) if methodology_globs else sorted(
        str(f) for f in cfg.review_methodology_dir.glob("*.md") if f.name != "README.md"
    )
    # Apply per-methodology weights by duplicating entries in the pool.
    methodology_files = [f for f in methodology_files for _ in range(cfg.review_methodology_weights.get(Path(f).stem, 1))]
    format_files = _expand_globs(format_globs) if format_globs else sorted(
        str(f) for f in cfg.review_format_dir.glob("*.md") if f.name != "README.md"
    )

    if not role_files:
        raise click.ClickException("No role files matched.")
    if not interest_files:
        raise click.ClickException("No interest files matched.")
    if not persona_files:
        raise click.ClickException("No persona files matched.")
    if not methodology_files:
        raise click.ClickException("No methodology files matched.")
    if not format_files:
        raise click.ClickException("No review format files matched.")

    click.echo(
        f"Roles: {len(role_files)}, Interests: {len(interest_files)}, "
        f"Personas: {len(persona_files)}, Methodologies: {len(methodology_files)}, "
        f"Formats: {len(format_files)}"
    )
    click.echo(f"Sampling {count} agents ({strategy}, seed={seed})\n")

    samples = sample(
        role_files,
        interest_files,
        persona_files,
        methodology_files,
        format_files,
        n=count,
        strategy=strategy,
        seed=seed,
    )

    out.mkdir(parents=True, exist_ok=True)

    backend_obj = get_backend(backend)

    for i, s in enumerate(samples):
        agent_name = f"agent_{i:03d}__{s.name}"
        agent_dir = out / agent_name
        agent_dir.mkdir(exist_ok=True)

        prompt = compile_agent_prompt(
            role_path=Path(s.role),
            persona_path=Path(s.persona),
            interest_path=Path(s.interests),
            global_rules_path=cfg.global_rules_path,
            platform_skills_path=cfg.platform_skills_path,
            review_methodology_path=Path(s.methodology),
            review_format_path=Path(s.review_format),
        )

        (agent_dir / "prompt.md").write_text(prompt, encoding="utf-8")
        (agent_dir / backend_obj.prompt_filename).write_text(prompt, encoding="utf-8")
        initial_prompt = DEFAULT_INITIAL_PROMPT.format(
            owner_email=cfg.owner_email,
            owner_name=cfg.owner_name,
            owner_password=cfg.owner_password,
            github_repo=cfg.github_repo,
            koala_base_url=cfg.koala_base_url,
        )
        (agent_dir / "initial_prompt.txt").write_text(initial_prompt, encoding="utf-8")
        (agent_dir / ".agent_name").write_text(agent_name, encoding="utf-8")

        config_data = {
            "name": agent_name,
            "backend": backend,
            "role": str(Path(s.role).resolve()),
            "persona": str(Path(s.persona).resolve()),
            "interest": str(Path(s.interests).resolve()),
            "review_methodology": str(Path(s.methodology).resolve()),
            "review_format": str(Path(s.review_format).resolve()),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (agent_dir / "config.json").write_text(json.dumps(config_data, indent=2), encoding="utf-8")
        click.echo(f"  created: {agent_name}")

    click.echo(f"\n{len(samples)} agent(s) written to {out}")


@batch.command("launch")
@click.option("--agent-dirs", multiple=True, help="Agent directory globs (default: agents_dir/*).")
@click.option("--duration", type=float, default=None, help="Hours to run (default: indefinite).")
@click.option("--session-timeout", type=int, default=600, help="Max seconds per invocation before restart (default: 600).")
@click.pass_context
def batch_launch(ctx, agent_dirs, duration, session_timeout):
    """Launch all agents in parallel (one tmux session each)."""
    cfg = _get_config(ctx)
    if agent_dirs:
        dirs = _expand_globs(agent_dirs)
    else:
        dirs = sorted(str(d) for d in cfg.agents_dir.iterdir() if d.is_dir())
    dirs = [d for d in dirs if Path(d).is_dir() and (Path(d) / "config.json").exists()]

    if not dirs:
        raise click.ClickException("No valid agent directories found.")

    launched = 0
    for d in dirs:
        d = Path(d)
        agent_config = json.loads((d / "config.json").read_text())
        name = agent_config["name"]
        backend_obj = get_backend(agent_config["backend"])

        if has_session(name):
            click.echo(f"  skipped (already running): {name}")
            continue

        # ensure backend-specific prompt file
        prompt_file = d / backend_obj.prompt_filename
        if not prompt_file.exists():
            prompt = (d / "prompt.md").read_text(encoding="utf-8")
            prompt_file.write_text(prompt, encoding="utf-8")

        initial_prompt = (d / "initial_prompt.txt").read_text(encoding="utf-8").strip()
        escaped_prompt = initial_prompt.replace('"', '\\"')
        cmd = backend_obj.command_template.format(prompt=escaped_prompt)

        resume_cmd = backend_obj.resume_command_template
        script = build_launch_script(cmd, duration_hours=duration, session_timeout=session_timeout, resume_command=resume_cmd, session_id_extractor=backend_obj.session_id_extractor)
        create_session(name, str(d), script)
        launched += 1
        click.echo(f"  launched: {name}")

    click.echo(f"\n{launched} agent(s) launched.")


@batch.command("stop")
def batch_stop():
    """Stop all running agents."""
    count = kill_all_sessions()
    click.echo(f"Stopped {count} agent(s).")


# hidden alias so `reva batch kill` still works
_batch_kill = click.Command(name="kill", callback=batch_stop.callback, params=batch_stop.params, help=batch_stop.help, hidden=True)
batch.add_command(_batch_kill)


# --------------------------------------------------------------------------- #
# reva debug
# --------------------------------------------------------------------------- #


@main.command()
@click.option("--n", "count", type=int, default=3, help="Number of agents to preview.")
@click.option("--strategy", type=click.Choice(["stratified", "random"]), default="stratified")
@click.option("--seed", type=int, default=42)
@click.pass_context
def debug(ctx, count, strategy, seed):
    """Preview compiled prompts for sampled agents."""
    cfg = _get_config(ctx)

    role_files = sorted(str(f) for f in cfg.roles_dir.glob("*.md") if f.name != "README.md")
    interest_files = sorted(str(f) for f in cfg.interests_dir.glob("**/*.md") if f.name != "README.md")
    persona_files = sorted(str(f) for f in cfg.personas_dir.glob("*.json") if not f.name.startswith("all_"))
    methodology_files = sorted(str(f) for f in cfg.review_methodology_dir.glob("*.md") if f.name != "README.md")
    methodology_files = [f for f in methodology_files for _ in range(cfg.review_methodology_weights.get(Path(f).stem, 1))]
    format_files = sorted(str(f) for f in cfg.review_format_dir.glob("*.md") if f.name != "README.md")

    if not role_files or not interest_files or not persona_files or not methodology_files or not format_files:
        raise click.ClickException(
            f"Not enough components. Roles: {len(role_files)}, "
            f"Interests: {len(interest_files)}, Personas: {len(persona_files)}, "
            f"Methodologies: {len(methodology_files)}, Formats: {len(format_files)}"
        )

    samples = sample(
        role_files,
        interest_files,
        persona_files,
        methodology_files,
        format_files,
        n=count,
        strategy=strategy,
        seed=seed,
    )

    separator = "\n" + "=" * 80 + "\n"
    for i, s in enumerate(samples):
        prompt = compile_agent_prompt(
            role_path=Path(s.role),
            persona_path=Path(s.persona),
            interest_path=Path(s.interests),
            global_rules_path=cfg.global_rules_path,
            platform_skills_path=cfg.platform_skills_path,
            review_methodology_path=Path(s.methodology),
            review_format_path=Path(s.review_format),
        )
        click.echo(separator)
        click.echo(f"Agent {i + 1}/{len(samples)}: {s.name}")
        click.echo(f"  role:         {Path(s.role).name}")
        click.echo(f"  interests:    {Path(s.interests).name}")
        click.echo(f"  persona:      {Path(s.persona).name}")
        click.echo(f"  methodology:  {Path(s.methodology).name}")
        click.echo(f"  format:       {Path(s.review_format).name}")
        click.echo(f"  chars:        {len(prompt)}")
        click.echo(separator)
        click.echo(prompt)

    click.echo(separator)


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
        # pick most recently modified agent log
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
                # No new lines — flush any buffered paragraphs (plain-text
                # backends) so live viewers see complete steps.
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

    # Kill running tmux session if any
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


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _expand_globs(patterns: tuple[str, ...]) -> list[str]:
    """Expand shell glob patterns into a sorted list of paths."""
    result = []
    for pattern in patterns:
        expanded = glob.glob(pattern, recursive=True)
        if expanded:
            result.extend(expanded)
        else:
            # not a glob, treat as literal path
            result.append(pattern)
    return sorted(set(result))
