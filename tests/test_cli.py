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

def test_create_generates_system_prompt_and_config(tmp_path):
    """`reva create --name foo` creates a system_prompt.md and config.json."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    global_rules = tmp_path / "GLOBAL_RULES.md"
    global_rules.write_text("GLOBAL RULES\n", encoding="utf-8")
    platform_skills = tmp_path / "platform_skills.md"
    platform_skills.write_text("PLATFORM SKILLS\n", encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.agents_dir = agents_dir
    mock_cfg.global_rules_path = global_rules
    mock_cfg.platform_skills_path = platform_skills
    mock_cfg.github_repo = ""
    mock_cfg.koala_base_url = "https://koala.science"

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


def test_create_with_explicit_backend(tmp_path):
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    global_rules = tmp_path / "GLOBAL_RULES.md"
    global_rules.write_text("G\n", encoding="utf-8")
    platform_skills = tmp_path / "platform_skills.md"
    platform_skills.write_text("P\n", encoding="utf-8")

    mock_cfg = MagicMock()
    mock_cfg.agents_dir = agents_dir
    mock_cfg.global_rules_path = global_rules
    mock_cfg.platform_skills_path = platform_skills
    mock_cfg.github_repo = ""
    mock_cfg.koala_base_url = "https://koala.science"

    with patch("reva.cli._get_config", return_value=mock_cfg):
        result = _invoke("create", "--name", "bar", "--backend", "codex")
        assert result.exit_code == 0, result.output

    cfg_data = json.loads((agents_dir / "bar" / "config.json").read_text())
    assert cfg_data["backend"] == "codex"


def test_create_existing_agent_errors_out(tmp_path):
    agents_dir = tmp_path / "agents"
    (agents_dir / "foo").mkdir(parents=True)

    mock_cfg = MagicMock()
    mock_cfg.agents_dir = agents_dir
    mock_cfg.global_rules_path = tmp_path / "GLOBAL_RULES.md"
    mock_cfg.platform_skills_path = tmp_path / "platform_skills.md"
    mock_cfg.github_repo = ""
    mock_cfg.koala_base_url = "https://koala.science"

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
    mock_cfg.koala_base_url = "https://koala.science"

    with patch("reva.cli._get_config", return_value=mock_cfg):
        result = _invoke("launch", "--name", "foo")
        assert result.exit_code != 0
        assert ".api_key" in result.output


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
