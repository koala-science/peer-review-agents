"""Tests for reva.cli — command tree structure and --help output.

We use click's CliRunner to invoke commands in-process, which lets us
verify help output and argument parsing without touching tmux, the
network, or any backend binary.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from reva.cli import main


def _invoke(*args, input=None):
    runner = CliRunner()
    return runner.invoke(main, list(args), input=input, catch_exceptions=False)


# ── top-level ──────────────────────────────────────────────────────────

def test_main_help_exits_zero():
    result = _invoke("--help")
    assert result.exit_code == 0
    assert "reva — reviewer agent CLI" in result.output


def test_main_help_lists_expected_commands():
    result = _invoke("--help")
    assert result.exit_code == 0
    for cmd in (
        "init",
        "create",
        "launch",
        "stop",
        "status",
        "log",
        "view",
        "archive",
        "unarchive",
    ):
        assert cmd in result.output, f"{cmd!r} missing from `reva --help`"


def test_main_help_excludes_removed_command_groups():
    """batch, list, debug, persona, interests groups are all gone."""
    result = _invoke("--help")
    assert result.exit_code == 0
    for cmd in ("batch", "debug"):
        assert cmd not in result.output.split("Commands:", 1)[1], (
            f"{cmd!r} should not appear in `reva --help`"
        )


def test_batch_command_no_longer_exists():
    result = _invoke("batch", "--help")
    assert result.exit_code != 0


def test_debug_command_no_longer_exists():
    result = _invoke("debug", "--help")
    assert result.exit_code != 0


def test_list_command_no_longer_exists():
    result = _invoke("list", "--help")
    assert result.exit_code != 0


# ── per-command --help ────────────────────────────────────────────────

def test_init_help():
    result = _invoke("init", "--help")
    assert result.exit_code == 0
    assert "Initialize a reva project" in result.output


def test_create_help_lists_only_name_and_backend():
    result = _invoke("create", "--help")
    assert result.exit_code == 0
    assert "--name" in result.output
    assert "--backend" in result.output


def test_create_help_does_not_mention_removed_flags():
    result = _invoke("create", "--help")
    assert result.exit_code == 0
    for removed in (
        "--role",
        "--persona",
        "--interest",
        "--review-methodology",
        "--review-format",
    ):
        assert removed not in result.output, (
            f"{removed} should not appear in `reva create --help`"
        )


def test_create_help_lists_all_backends():
    result = _invoke("create", "--help")
    assert result.exit_code == 0
    for backend in ("claude-code", "gemini-cli", "codex", "aider", "opencode"):
        assert backend in result.output


def test_launch_help_lists_required_options():
    result = _invoke("launch", "--help")
    assert result.exit_code == 0
    assert "--name" in result.output
    assert "--duration" in result.output
    assert "--session-timeout" in result.output


def test_stop_help():
    result = _invoke("stop", "--help")
    assert result.exit_code == 0


def test_kill_alias_still_works():
    """Hidden `kill` alias should still be usable."""
    result = _invoke("kill", "--help")
    assert result.exit_code == 0


def test_status_help():
    result = _invoke("status", "--help")
    assert result.exit_code == 0


def test_log_help():
    result = _invoke("log", "--help")
    assert result.exit_code == 0


# ── unknown command / flag error handling ────────────────────────────

def test_unknown_command_exits_nonzero():
    result = _invoke("definitely-not-a-command")
    assert result.exit_code != 0


def test_create_missing_required_args_errors_out():
    result = _invoke("create")
    assert result.exit_code != 0
    assert "missing" in result.output.lower() or "required" in result.output.lower()


# ── functional: reva create ──────────────────────────────────────────

def _mock_cfg_with_starter(tmp_path, agents_dir, starter_text="STARTER {name}\n"):
    """Build a mock RevaConfig with a real default_system_prompt.md on disk."""
    global_rules = tmp_path / "GLOBAL_RULES.md"
    global_rules.write_text("GLOBAL RULES\n", encoding="utf-8")
    platform_skills = tmp_path / "platform_skills.md"
    platform_skills.write_text("PLATFORM SKILLS\n", encoding="utf-8")
    default_prompt = tmp_path / "default_system_prompt.md"
    default_prompt.write_text(starter_text, encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.agents_dir = agents_dir
    mock_cfg.global_rules_path = global_rules
    mock_cfg.platform_skills_path = platform_skills
    mock_cfg.default_system_prompt_path = default_prompt
    mock_cfg.github_repo = "https://github.com/test-owner/my-fork"
    mock_cfg.koala_base_url = "https://koala.science"
    return mock_cfg


def test_create_generates_system_prompt_and_config(tmp_path):
    """`reva create --name foo` creates a system_prompt.md and config.json."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    mock_cfg = _mock_cfg_with_starter(tmp_path, agents_dir)

    with patch("reva.cli._get_config", return_value=mock_cfg):
        result = _invoke("create", "--name", "foo")
        assert result.exit_code == 0, result.output

    agent_dir = agents_dir / "foo"
    assert agent_dir.exists()
    assert (agent_dir / "system_prompt.md").exists()
    assert (agent_dir / "config.json").exists()

    cfg_data = json.loads((agent_dir / "config.json").read_text())
    assert cfg_data["name"] == "foo"
    assert cfg_data["backend"] == "claude-code"  # default


def test_create_system_prompt_uses_default_template(tmp_path):
    """`reva create` seeds system_prompt.md from cfg.default_system_prompt_path,
    substituting {name}. This lets maintainers evolve the starter template
    (e.g. verdict citation rules) without touching Python."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    template = "# Agent: {name}\n\nShared rule body\n"
    mock_cfg = _mock_cfg_with_starter(tmp_path, agents_dir, starter_text=template)

    with patch("reva.cli._get_config", return_value=mock_cfg):
        result = _invoke("create", "--name", "quux")
        assert result.exit_code == 0, result.output

    produced = (agents_dir / "quux" / "system_prompt.md").read_text(encoding="utf-8")
    assert produced == "# Agent: quux\n\nShared rule body\n"


def test_create_preserves_unrelated_braces_in_template(tmp_path):
    """Starter templates may contain literal `{...}` (LaTeX, JSON, example
    placeholders) — only `{name}` should be substituted, everything else
    must pass through verbatim."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    template = (
        "# Agent: {name}\n\n"
        "Example JSON: {\"foo\": 1}\n"
        "LaTeX: $\\mathbb{R}$\n"
        "Unrelated placeholder: {other}\n"
    )
    mock_cfg = _mock_cfg_with_starter(tmp_path, agents_dir, starter_text=template)

    with patch("reva.cli._get_config", return_value=mock_cfg):
        result = _invoke("create", "--name", "brace-test")
        assert result.exit_code == 0, result.output

    produced = (agents_dir / "brace-test" / "system_prompt.md").read_text(encoding="utf-8")
    assert produced == (
        "# Agent: brace-test\n\n"
        "Example JSON: {\"foo\": 1}\n"
        "LaTeX: $\\mathbb{R}$\n"
        "Unrelated placeholder: {other}\n"
    )


def test_create_with_explicit_backend(tmp_path):
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    mock_cfg = _mock_cfg_with_starter(tmp_path, agents_dir)

    with patch("reva.cli._get_config", return_value=mock_cfg):
        result = _invoke("create", "--name", "bar", "--backend", "codex")
        assert result.exit_code == 0, result.output

    cfg_data = json.loads((agents_dir / "bar" / "config.json").read_text())
    assert cfg_data["backend"] == "codex"


def test_create_existing_agent_errors_out(tmp_path):
    agents_dir = tmp_path / "agents"
    (agents_dir / "foo").mkdir(parents=True)
    mock_cfg = _mock_cfg_with_starter(tmp_path, agents_dir)

    with patch("reva.cli._get_config", return_value=mock_cfg):
        result = _invoke("create", "--name", "foo")
        assert result.exit_code != 0


# ── functional: reva launch .api_key gate ────────────────────────────

def test_launch_fails_when_api_key_missing(tmp_path):
    """`reva launch --name foo` without `.api_key` must abort non-zero."""
    agents_dir = tmp_path / "agents"
    agent_dir = agents_dir / "foo"
    agent_dir.mkdir(parents=True)
    (agent_dir / "config.json").write_text(
        json.dumps({"name": "foo", "backend": "claude-code"}),
        encoding="utf-8",
    )
    (agent_dir / "system_prompt.md").write_text("hi", encoding="utf-8")
    (agent_dir / "initial_prompt.txt").write_text("hi", encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.agents_dir = agents_dir
    mock_cfg.github_repo = "https://github.com/test-owner/my-fork"
    mock_cfg.koala_base_url = "https://koala.science"

    with patch("reva.cli._get_config", return_value=mock_cfg):
        result = _invoke("launch", "--name", "foo")
        assert result.exit_code != 0
        assert ".api_key" in result.output


def test_launch_fails_when_api_key_empty(tmp_path):
    """Empty `.api_key` file must also fail the gate."""
    agents_dir = tmp_path / "agents"
    agent_dir = agents_dir / "foo"
    agent_dir.mkdir(parents=True)
    (agent_dir / "config.json").write_text(
        json.dumps({"name": "foo", "backend": "claude-code"}),
        encoding="utf-8",
    )
    (agent_dir / "system_prompt.md").write_text("hi", encoding="utf-8")
    (agent_dir / "initial_prompt.txt").write_text("hi", encoding="utf-8")
    (agent_dir / ".api_key").write_text("   \n", encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.agents_dir = agents_dir
    mock_cfg.github_repo = "https://github.com/test-owner/my-fork"
    mock_cfg.koala_base_url = "https://koala.science"

    with patch("reva.cli._get_config", return_value=mock_cfg):
        result = _invoke("launch", "--name", "foo")
        assert result.exit_code != 0
        assert ".api_key" in result.output


def test_launch_claude_code_resume_collapses_mcp_config_braces(tmp_path):
    """Regression: _PAPER_LANTERN_MCP_CONFIG in backends.py intentionally
    doubles its braces ({{ / }}) so that str.format() in cli.launch() collapses
    them back to single braces. If cli.py applies .format() only to
    command_template and not to resume_command_template, the doubled braces
    leak into the generated bash script and `claude --mcp-config` receives
    `'{{"mcpServers":...}}}}'`. Since that string does not start with `{` +
    JSON whitespace, the claude CLI treats it as a file path, resolves it
    relative to the agent cwd, and aborts with "MCP config file not found".
    """
    agents_dir = tmp_path / "agents"
    agent_dir = agents_dir / "foo"
    agent_dir.mkdir(parents=True)
    (agent_dir / "config.json").write_text(
        json.dumps({"name": "foo", "backend": "claude-code"}),
        encoding="utf-8",
    )
    (agent_dir / "system_prompt.md").write_text("hi", encoding="utf-8")
    (agent_dir / ".api_key").write_text("KEY", encoding="utf-8")

    global_rules = tmp_path / "GLOBAL_RULES.md"
    global_rules.write_text("R\n", encoding="utf-8")
    platform_skills = tmp_path / "platform_skills.md"
    platform_skills.write_text("S\n", encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.agents_dir = agents_dir
    mock_cfg.global_rules_path = global_rules
    mock_cfg.platform_skills_path = platform_skills
    mock_cfg.github_repo = "https://github.com/test-owner/my-fork"
    mock_cfg.koala_base_url = "https://koala.science"

    captured = {}

    def fake_create_session(name, cwd, script):
        captured["script"] = script

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.create_session", side_effect=fake_create_session):
        result = _invoke("launch", "--name", "foo")
        assert result.exit_code == 0, result.output

    script = captured["script"]
    assert "claude --resume" in script
    assert "'{\"mcpServers\"" in script, (
        "resume --mcp-config JSON must collapse to a single leading brace; "
        "cli.py must run .format() on resume_command_template so the "
        "intentionally-doubled braces in _PAPER_LANTERN_MCP_CONFIG collapse."
    )
    assert "'{{\"mcpServers\"" not in script, (
        "doubled braces leaked into the resume command — cli.py is missing "
        ".format() on resume_command_template. The claude CLI will treat the "
        "--mcp-config argument as a file path and abort at resume time."
    )


# ── prompt assembly ──────────────────────────────────────────────────

def test_assemble_prompt_three_part_concatenation(tmp_path, monkeypatch):
    """The new assembly helper concatenates GLOBAL_RULES + platform_skills +
    agent system_prompt.md with SECTION_SEPARATOR and substitutes
    {KOALA_BASE_URL}."""
    monkeypatch.delenv("KOALA_BASE_URL", raising=False)

    global_rules = tmp_path / "GLOBAL_RULES.md"
    global_rules.write_text("RULES at {KOALA_BASE_URL}\n", encoding="utf-8")
    platform_skills = tmp_path / "platform_skills.md"
    platform_skills.write_text("SKILLS\n", encoding="utf-8")
    agent_prompt = tmp_path / "system_prompt.md"
    agent_prompt.write_text("AGENT PROMPT\n", encoding="utf-8")

    from reva.prompt import SECTION_SEPARATOR, assemble_prompt

    result = assemble_prompt(
        global_rules_path=global_rules,
        platform_skills_path=platform_skills,
        agent_prompt_path=agent_prompt,
    )

    expected = SECTION_SEPARATOR.join(
        [
            "RULES at https://koala.science",
            "SKILLS",
            "AGENT PROMPT",
        ]
    )
    assert result == expected


def test_assemble_prompt_honors_staging_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KOALA_BASE_URL", "https://staging.koala.science")
    global_rules = tmp_path / "GLOBAL_RULES.md"
    global_rules.write_text("See {KOALA_BASE_URL}/skill.md\n", encoding="utf-8")
    platform_skills = tmp_path / "platform_skills.md"
    platform_skills.write_text("S\n", encoding="utf-8")
    agent_prompt = tmp_path / "system_prompt.md"
    agent_prompt.write_text("A\n", encoding="utf-8")

    from reva.prompt import assemble_prompt

    result = assemble_prompt(
        global_rules_path=global_rules,
        platform_skills_path=platform_skills,
        agent_prompt_path=agent_prompt,
    )
    assert "https://staging.koala.science/skill.md" in result
    assert "{KOALA_BASE_URL}" not in result


# ── archive / unarchive ──────────────────────────────────────────────


def test_archive_help():
    result = _invoke("archive", "--help")
    assert result.exit_code == 0
    assert "Archive" in result.output or "archive" in result.output
    assert "--name" in result.output
    assert "--list" in result.output


def test_unarchive_help():
    result = _invoke("unarchive", "--help")
    assert result.exit_code == 0
    assert "Unarchive" in result.output or "unarchive" in result.output
    assert "--name" in result.output


def test_archive_and_unarchive_functional():
    """Create a temp agents_dir, archive an agent, verify, then unarchive."""
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir = Path(tmpdir) / "agents"
        agents_dir.mkdir()

        agent_name = "test-agent"
        agent_dir = agents_dir / agent_name
        agent_dir.mkdir()
        (agent_dir / "config.json").write_text(
            json.dumps({"name": agent_name, "backend": "claude-code"}),
            encoding="utf-8",
        )

        mock_cfg = MagicMock()
        mock_cfg.agents_dir = agents_dir

        with patch("reva.cli._get_config", return_value=mock_cfg), \
             patch("reva.cli.has_session", return_value=False):
            runner = CliRunner()

            result = runner.invoke(main, ["archive", "--name", agent_name], catch_exceptions=False)
            assert result.exit_code == 0
            assert f"Archived agent: {agent_name}" in result.output

            assert not (agents_dir / agent_name).exists()
            assert (agents_dir / ".archived" / agent_name).exists()
            assert (agents_dir / ".archived" / agent_name / "config.json").exists()

            result = runner.invoke(main, ["archive", "--list"], catch_exceptions=False)
            assert result.exit_code == 0
            assert agent_name in result.output

            result = runner.invoke(main, ["unarchive", "--name", agent_name], catch_exceptions=False)
            assert result.exit_code == 0
            assert f"Unarchived agent: {agent_name}" in result.output

            assert (agents_dir / agent_name).exists()
            assert (agents_dir / agent_name / "config.json").exists()
            assert not (agents_dir / ".archived" / agent_name).exists()


def test_archive_nonexistent_agent():
    """Archiving an agent that doesn't exist should fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir = Path(tmpdir) / "agents"
        agents_dir.mkdir()

        mock_cfg = MagicMock()
        mock_cfg.agents_dir = agents_dir

        with patch("reva.cli._get_config", return_value=mock_cfg):
            runner = CliRunner()
            result = runner.invoke(main, ["archive", "--name", "no-such-agent"], catch_exceptions=False)
            assert result.exit_code != 0
            assert "not found" in result.output.lower()


def test_unarchive_nonexistent_agent():
    """Unarchiving an agent that isn't archived should fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir = Path(tmpdir) / "agents"
        agents_dir.mkdir()

        mock_cfg = MagicMock()
        mock_cfg.agents_dir = agents_dir

        with patch("reva.cli._get_config", return_value=mock_cfg):
            runner = CliRunner()
            result = runner.invoke(main, ["unarchive", "--name", "no-such-agent"], catch_exceptions=False)
            assert result.exit_code != 0
            assert "not archived" in result.output.lower()


def test_load_project_env_reads_dotenv(monkeypatch, tmp_path):
    """`.env` in the project root is auto-loaded; values flow into os.environ."""
    import os

    from reva.cli import _load_project_env

    (tmp_path / "config.toml").write_text("agents_dir = './agents/'\n")
    (tmp_path / ".env").write_text("KOALA_BASE_URL=https://staging.koala.science\n")

    monkeypatch.delenv("KOALA_BASE_URL", raising=False)
    _load_project_env(str(tmp_path / "config.toml"))

    assert os.environ.get("KOALA_BASE_URL") == "https://staging.koala.science"


def test_load_project_env_missing_file_is_noop(monkeypatch, tmp_path):
    """No `.env` present → no crash, no env changes."""
    import os

    from reva.cli import _load_project_env

    (tmp_path / "config.toml").write_text("agents_dir = './agents/'\n")

    monkeypatch.delenv("KOALA_BASE_URL", raising=False)
    _load_project_env(str(tmp_path / "config.toml"))

    assert "KOALA_BASE_URL" not in os.environ


# ── cluster (SLURM) ──────────────────────────────────────────────────


def _make_agent_dir(tmp_path, name="foo", *, api_key="KEY"):
    agents_dir = tmp_path / "agents"
    agent_dir = agents_dir / name
    agent_dir.mkdir(parents=True)
    (agent_dir / "config.json").write_text(
        json.dumps({"name": name, "backend": "claude-code"}),
        encoding="utf-8",
    )
    (agent_dir / "system_prompt.md").write_text("hi", encoding="utf-8")
    if api_key is not None:
        (agent_dir / ".api_key").write_text(api_key, encoding="utf-8")

    global_rules = tmp_path / "GLOBAL_RULES.md"
    global_rules.write_text("R\n", encoding="utf-8")
    platform_skills = tmp_path / "platform_skills.md"
    platform_skills.write_text("S\n", encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.agents_dir = agents_dir
    mock_cfg.global_rules_path = global_rules
    mock_cfg.platform_skills_path = platform_skills
    mock_cfg.github_repo = "https://github.com/test-owner/my-fork"
    mock_cfg.koala_base_url = "https://koala.science"

    return agents_dir, agent_dir, mock_cfg


def test_launch_help_mentions_cluster_flag():
    result = _invoke("launch", "--help")
    assert result.exit_code == 0
    assert "--cluster" in result.output
    assert "--partition" in result.output
    assert "--time" in result.output
    assert "--cpus" in result.output
    assert "--mem" in result.output
    assert "--max-chain" in result.output


def test_launch_cluster_invokes_submit_agent_not_create_session(tmp_path):
    """--cluster routes to submit_agent; create_session is NOT called."""
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path)

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.create_session") as mock_create, \
         patch("reva.cli.submit_agent", return_value=42) as mock_submit:
        result = _invoke("launch", "--name", "foo", "--cluster")

    assert result.exit_code == 0, result.output
    mock_submit.assert_called_once()
    mock_create.assert_not_called()
    assert "42" in result.output


def test_launch_cluster_fails_without_api_key(tmp_path):
    """Same .api_key gate runs in cluster mode."""
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path, api_key=None)

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.submit_agent") as mock_submit:
        result = _invoke("launch", "--name", "foo", "--cluster")

    assert result.exit_code != 0
    assert ".api_key" in result.output
    mock_submit.assert_not_called()


def test_launch_cluster_fails_with_bad_time_format(tmp_path):
    """Invalid --time surfaces a validation error to the CLI — even on a host
    where sbatch is available (otherwise the 'SLURM not available' path would
    short-circuit first)."""
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path)

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cluster.shutil.which", return_value="/usr/bin/sbatch"), \
         patch("reva.cluster.subprocess.run") as mock_run:
        result = _invoke("launch", "--name", "foo", "--cluster", "--time", "99-notvalid")

    assert result.exit_code != 0
    assert "time" in result.output.lower()
    mock_run.assert_not_called()


def test_launch_cluster_fails_when_sbatch_missing(tmp_path):
    """Host without sbatch → non-zero with 'SLURM not available' in the message."""
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path)

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cluster.shutil.which", return_value=None):
        result = _invoke("launch", "--name", "foo", "--cluster")

    assert result.exit_code != 0
    assert "SLURM not available" in result.output


def test_launch_without_cluster_still_uses_tmux(tmp_path):
    """Regression: default --cluster-less path still takes the tmux route."""
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path)

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.create_session") as mock_create, \
         patch("reva.cli.submit_agent") as mock_submit:
        result = _invoke("launch", "--name", "foo")

    assert result.exit_code == 0, result.output
    mock_create.assert_called_once()
    mock_submit.assert_not_called()


def test_stop_cluster_cancels_chain(tmp_path):
    """`reva stop --name foo --cluster` calls cancel_chain, not kill_session."""
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path)

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.cancel_chain", return_value=1) as mock_cancel, \
         patch("reva.cli.kill_session") as mock_kill:
        result = _invoke("stop", "--name", "foo", "--cluster")

    assert result.exit_code == 0, result.output
    mock_cancel.assert_called_once()
    mock_kill.assert_not_called()


def test_stop_cluster_all_cancels_every_chain(tmp_path):
    """`reva stop --all --cluster` cancels every reva chain for the user."""
    _, _, mock_cfg = _make_agent_dir(tmp_path)

    from reva.cluster import ClusterJob

    jobs = [
        ClusterJob(agent_name="foo", job_id=1, state="RUNNING", time_left="1:00"),
        ClusterJob(agent_name="bar", job_id=2, state="PENDING", time_left="UNLIMITED"),
    ]

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.list_cluster_jobs", return_value=jobs), \
         patch("reva.cli.cancel_chain", return_value=1) as mock_cancel, \
         patch("reva.cli.kill_all_sessions") as mock_kill_all:
        result = _invoke("stop", "--all", "--cluster")

    assert result.exit_code == 0, result.output
    # two unique agent names → cancel_chain called twice
    assert mock_cancel.call_count == 2
    mock_kill_all.assert_not_called()


def test_status_merges_tmux_and_cluster(tmp_path):
    """reva status prints rows for both tmux sessions and cluster jobs."""
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path, name="foo")
    _make_agent_dir(tmp_path, name="bar")  # cluster-only

    from reva.cluster import ClusterJob
    from reva.tmux import SessionInfo

    sessions = [SessionInfo(agent_name="foo", session="reva_foo", created=None)]
    jobs = [ClusterJob(agent_name="bar", job_id=999, state="RUNNING", time_left="4:00:00")]

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.list_sessions", return_value=sessions), \
         patch("reva.cli.list_cluster_jobs", return_value=jobs):
        result = _invoke("status")

    assert result.exit_code == 0, result.output
    assert "foo" in result.output
    assert "bar" in result.output
    assert "tmux" in result.output
    assert "slurm" in result.output
    assert "MODE" in result.output
    assert "999" in result.output


def test_launch_cluster_generates_identical_launch_sh_as_tmux(tmp_path):
    """Byte-identity check: the .reva_launch.sh written in cluster mode must
    match what the tmux path writes for the same agent + options (modulo
    the per-dir env-source prelude paths)."""
    from reva.launch_script import write_launch_files

    agents_dir, agent_dir_tmux, mock_cfg = _make_agent_dir(tmp_path, name="foo")
    _, agent_dir_cluster, _ = _make_agent_dir(tmp_path, name="bar")
    mock_cfg.agents_dir = agents_dir

    # tmux path — mock create_session to call write_launch_files (what the
    # real create_session does internally) without touching tmux.
    def fake_create_session(name, cwd, script):
        write_launch_files(cwd, script)

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.create_session", side_effect=fake_create_session):
        result = _invoke("launch", "--name", "foo")
        assert result.exit_code == 0, result.output

    tmux_launch = (agent_dir_tmux / ".reva_launch.sh").read_text()

    # cluster path
    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cluster.shutil.which", return_value="/usr/bin/sbatch"), \
         patch("reva.cluster.subprocess.run",
               return_value=MagicMock(returncode=0, stdout="Submitted batch job 1\n", stderr="")):
        result = _invoke("launch", "--name", "bar", "--cluster")
        assert result.exit_code == 0, result.output

    cluster_launch = (agent_dir_cluster / ".reva_launch.sh").read_text()

    assert "claude" in tmux_launch
    assert "claude" in cluster_launch

    def _strip_prelude(s):
        lines = s.splitlines(keepends=True)
        return "".join(lines[2:]) if len(lines) > 2 and lines[0].startswith("source ") else s

    assert _strip_prelude(tmux_launch) == _strip_prelude(cluster_launch)


# ── functional: reva launch github_repo gate ─────────────────────────

def test_launch_fails_when_github_repo_empty(tmp_path, monkeypatch):
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path)
    mock_cfg.github_repo = ""
    monkeypatch.delenv("REVA_ALLOW_UPSTREAM_REPO", raising=False)

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.create_session") as mock_create:
        result = _invoke("launch", "--name", "foo")

    assert result.exit_code != 0
    assert "github_repo" in result.output
    mock_create.assert_not_called()


def test_launch_fails_when_github_repo_is_placeholder(tmp_path, monkeypatch):
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path)
    mock_cfg.github_repo = "REPLACE WITH YOUR FORK"
    monkeypatch.delenv("REVA_ALLOW_UPSTREAM_REPO", raising=False)

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.create_session") as mock_create:
        result = _invoke("launch", "--name", "foo")

    assert result.exit_code != 0
    assert "REPLACE WITH YOUR FORK" in result.output
    mock_create.assert_not_called()


def test_launch_fails_when_github_repo_is_canonical_upstream(tmp_path, monkeypatch):
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path)
    mock_cfg.github_repo = "https://github.com/koala-science/peer-review-agents"
    monkeypatch.delenv("REVA_ALLOW_UPSTREAM_REPO", raising=False)

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.create_session") as mock_create:
        result = _invoke("launch", "--name", "foo")

    assert result.exit_code != 0
    assert "fork" in result.output.lower()
    mock_create.assert_not_called()


def test_launch_fails_when_github_repo_is_canonical_upstream_cluster_mode(tmp_path, monkeypatch):
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path)
    mock_cfg.github_repo = "https://github.com/koala-science/peer-review-agents.git"
    monkeypatch.delenv("REVA_ALLOW_UPSTREAM_REPO", raising=False)

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.submit_agent") as mock_submit:
        result = _invoke("launch", "--name", "foo", "--cluster")

    assert result.exit_code != 0
    mock_submit.assert_not_called()


def test_launch_bypasses_upstream_check_when_env_var_set(tmp_path, monkeypatch):
    """REVA_ALLOW_UPSTREAM_REPO=1 lets maintainers run against the canonical upstream."""
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path)
    mock_cfg.github_repo = "https://github.com/koala-science/peer-review-agents"
    monkeypatch.setenv("REVA_ALLOW_UPSTREAM_REPO", "1")

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.create_session") as mock_create:
        result = _invoke("launch", "--name", "foo")

    assert result.exit_code == 0, result.output
    mock_create.assert_called_once()


def test_launch_does_not_bypass_upstream_check_when_env_var_is_zero(tmp_path, monkeypatch):
    """REVA_ALLOW_UPSTREAM_REPO=0 must NOT bypass the gate (explicit off)."""
    _, agent_dir, mock_cfg = _make_agent_dir(tmp_path)
    mock_cfg.github_repo = "https://github.com/koala-science/peer-review-agents"
    monkeypatch.setenv("REVA_ALLOW_UPSTREAM_REPO", "0")

    with patch("reva.cli._get_config", return_value=mock_cfg), \
         patch("reva.cli.create_session") as mock_create:
        result = _invoke("launch", "--name", "foo")

    assert result.exit_code != 0
    mock_create.assert_not_called()
