"""Tests for reva.cli — command tree structure and --help output.

We use click's CliRunner to invoke commands in-process, which lets us
verify help output and argument parsing without touching tmux, the
network, or any backend binary.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

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


def test_main_help_lists_all_expected_commands():
    result = _invoke("--help")
    assert result.exit_code == 0
    # Commands that should be visible in `reva --help` output
    for cmd in (
        "init",
        "create",
        "launch",
        "stop",
        "status",
        "persona",
        "interests",
        "list",
        "batch",
        "log",
        "view",
        "debug",
        "archive",
        "unarchive",
    ):
        assert cmd in result.output, f"{cmd!r} missing from `reva --help`"


# ── per-command --help ────────────────────────────────────────────────

def test_init_help():
    result = _invoke("init", "--help")
    assert result.exit_code == 0
    assert "Initialize a reva project" in result.output


def test_create_help_lists_required_options():
    result = _invoke("create", "--help")
    assert result.exit_code == 0
    # Required flags must appear in the help text
    for flag in ("--name", "--backend", "--role", "--persona", "--interest"):
        assert flag in result.output


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


def test_persona_help_has_subcommands():
    result = _invoke("persona", "--help")
    assert result.exit_code == 0
    assert "list" in result.output
    assert "show" in result.output


def test_interests_help_has_subcommands():
    result = _invoke("interests", "--help")
    assert result.exit_code == 0
    assert "list-topics" in result.output
    assert "generate" in result.output
    assert "validate" in result.output


def test_batch_help_has_subcommands():
    result = _invoke("batch", "--help")
    assert result.exit_code == 0
    assert "create" in result.output
    assert "launch" in result.output
    assert "stop" in result.output


def test_batch_kill_alias_still_works():
    """Hidden `batch kill` alias should still be usable."""
    result = _invoke("batch", "kill", "--help")
    assert result.exit_code == 0


def test_batch_create_help_lists_required_options():
    result = _invoke("batch", "create", "--help")
    assert result.exit_code == 0
    # Batch create takes counts/axes
    assert "--n" in result.output or "-n" in result.output or "count" in result.output.lower()


# ── unknown command / flag error handling ────────────────────────────

def test_unknown_command_exits_nonzero():
    result = _invoke("definitely-not-a-command")
    assert result.exit_code != 0


def test_create_missing_required_args_errors_out():
    result = _invoke("create")
    assert result.exit_code != 0
    # Click's error message should mention a missing required option
    assert "missing" in result.output.lower() or "required" in result.output.lower()


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

        # Create a fake agent directory with minimal config.json
        agent_name = "test-agent"
        agent_dir = agents_dir / agent_name
        agent_dir.mkdir()
        (agent_dir / "config.json").write_text(
            json.dumps({"name": agent_name, "backend": "claude-code"}),
            encoding="utf-8",
        )

        # Mock _get_config to return our temp agents_dir
        from unittest.mock import MagicMock
        mock_cfg = MagicMock()
        mock_cfg.agents_dir = agents_dir

        with patch("reva.cli._get_config", return_value=mock_cfg), \
             patch("reva.cli.has_session", return_value=False):
            runner = CliRunner()

            # Archive the agent
            result = runner.invoke(main, ["archive", "--name", agent_name], catch_exceptions=False)
            assert result.exit_code == 0
            assert f"Archived agent: {agent_name}" in result.output

            # Agent should be gone from agents_dir
            assert not (agents_dir / agent_name).exists()
            # Agent should be in .archived/
            assert (agents_dir / ".archived" / agent_name).exists()
            assert (agents_dir / ".archived" / agent_name / "config.json").exists()

            # List archived agents
            result = runner.invoke(main, ["archive", "--list"], catch_exceptions=False)
            assert result.exit_code == 0
            assert agent_name in result.output

            # Unarchive the agent
            result = runner.invoke(main, ["unarchive", "--name", agent_name], catch_exceptions=False)
            assert result.exit_code == 0
            assert f"Unarchived agent: {agent_name}" in result.output

            # Agent should be back in agents_dir
            assert (agents_dir / agent_name).exists()
            assert (agents_dir / agent_name / "config.json").exists()
            # Agent should be gone from .archived/
            assert not (agents_dir / ".archived" / agent_name).exists()


def test_archive_nonexistent_agent():
    """Archiving an agent that doesn't exist should fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir = Path(tmpdir) / "agents"
        agents_dir.mkdir()

        from unittest.mock import MagicMock
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

        from unittest.mock import MagicMock
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
