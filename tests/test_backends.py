"""Tests for reva.backends — backend registry and command templates."""
import pytest

from reva.backends import BACKEND_CHOICES, Backend, get_backend


EXPECTED_BACKENDS = {"claude-code", "gemini-cli", "codex", "aider", "opencode"}


def test_all_expected_backends_registered():
    assert set(BACKEND_CHOICES) == EXPECTED_BACKENDS


@pytest.mark.parametrize("name", sorted(EXPECTED_BACKENDS))
def test_get_backend_returns_backend_for_known_name(name):
    backend = get_backend(name)
    assert isinstance(backend, Backend)
    assert backend.name == name


def test_get_backend_raises_for_unknown_name():
    with pytest.raises(ValueError, match="Unknown backend"):
        get_backend("not-a-real-backend")


@pytest.mark.parametrize("name", sorted(EXPECTED_BACKENDS))
def test_backend_has_required_fields(name):
    b = get_backend(name)
    assert b.name == name
    assert b.prompt_filename, f"{name} missing prompt_filename"
    assert b.command_template, f"{name} missing command_template"


@pytest.mark.parametrize("name", sorted(EXPECTED_BACKENDS))
def test_command_template_tees_to_agent_log(name):
    """Every backend must pipe its output through `tee -a agent.log` so the
    log viewer and resume logic have something to read."""
    b = get_backend(name)
    assert "tee -a agent.log" in b.command_template


@pytest.mark.parametrize("name", sorted(EXPECTED_BACKENDS))
def test_command_template_includes_stderr_merge(name):
    b = get_backend(name)
    assert "2>&1" in b.command_template, f"{name} command_template missing 2>&1"


def test_codex_uses_exec_subcommand():
    """Regression: codex must invoke `codex exec` (non-interactive) rather
    than the bare `codex` which drops into the interactive TUI and hangs.
    See commit 4e50698."""
    b = get_backend("codex")
    assert "codex exec" in b.command_template
    assert b.resume_command_template and "codex exec resume" in b.resume_command_template


def test_codex_resume_command_passes_prompt():
    """Regression: `codex exec resume --last` without a prompt falls back to
    interactive behavior. The resume path must re-send the initial prompt."""
    b = get_backend("codex")
    assert b.resume_command_template is not None
    assert 'initial_prompt.txt' in b.resume_command_template


def test_codex_skip_git_repo_check():
    """Codex refuses to run outside a git repo by default. Agent directories
    are usually not git repos, so --skip-git-repo-check must be present."""
    b = get_backend("codex")
    assert "--skip-git-repo-check" in b.command_template
    assert b.resume_command_template and "--skip-git-repo-check" in b.resume_command_template


def test_claude_code_uses_stream_json_output():
    """Claude-code's resume flow parses session IDs out of the stream-json
    log. Removing --output-format stream-json would break that parser."""
    b = get_backend("claude-code")
    assert "--output-format stream-json" in b.command_template


def test_claude_code_resume_uses_session_id_template_var():
    """The session-ID resume path in tmux.py keys off `$SESSION_ID` in the
    resume command. Make sure the template still has that marker."""
    b = get_backend("claude-code")
    assert b.resume_command_template and "$SESSION_ID" in b.resume_command_template


def test_opencode_has_session_id_extractor():
    """opencode doesn't emit session IDs in a claude-style JSON log, so it
    ships a custom shell extractor. Missing extractor → broken resume."""
    b = get_backend("opencode")
    assert b.session_id_extractor is not None
    assert "opencode session list" in b.session_id_extractor


def test_command_template_uses_cat_for_prompt():
    """$(cat initial_prompt.txt) must be used instead of inlining the prompt
    so that multiline prompts and shell metacharacters survive."""
    for name in ("claude-code", "gemini-cli", "codex", "aider", "opencode"):
        b = get_backend(name)
        assert 'initial_prompt.txt' in b.command_template, (
            f"{name} command_template should read from initial_prompt.txt"
        )
