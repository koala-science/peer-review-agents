"""Tests for reva.tmux — launch script generation and session naming.

No actual tmux server is required: these tests exercise the pure-Python
script-building helpers and only shell out to `bash -n` for syntax checking.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from reva.tmux import (
    SESSION_PREFIX,
    _BASH_TIMEOUT_FUNC,
    _make_run_block,
    build_launch_script,
    session_name,
)


# ── session_name ──────────────────────────────────────────────────────

def test_session_name_uses_prefix():
    assert session_name("foo") == f"{SESSION_PREFIX}foo"


def test_session_name_preserves_agent_name():
    # No sanitization: callers are responsible for passing tmux-safe names.
    assert session_name("my-agent-01") == f"{SESSION_PREFIX}my-agent-01"


# ── _BASH_TIMEOUT_FUNC ────────────────────────────────────────────────

def test_bash_timeout_func_sends_sigterm_first():
    """_timeout should try SIGTERM before escalating."""
    assert "kill -TERM" in _BASH_TIMEOUT_FUNC


def test_bash_timeout_func_escalates_to_sigkill():
    """Regression (PR #3): _timeout must escalate to SIGKILL after a grace
    period, otherwise backends that trap or ignore SIGTERM hang the wait.
    """
    assert "kill -KILL" in _BASH_TIMEOUT_FUNC
    # The grace period sleep must be *between* the TERM and the KILL.
    term_idx = _BASH_TIMEOUT_FUNC.index("kill -TERM")
    kill_idx = _BASH_TIMEOUT_FUNC.index("kill -KILL")
    between = _BASH_TIMEOUT_FUNC[term_idx:kill_idx]
    assert "sleep 10" in between, "SIGKILL must follow SIGTERM after a sleep"


def test_bash_timeout_func_parses_as_valid_bash():
    """The timeout function is injected verbatim into generated scripts —
    it must parse cleanly under `bash -n`."""
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
        f.write("#!/usr/bin/env bash\n")
        f.write(_BASH_TIMEOUT_FUNC)
        f.write('\n_timeout 1 echo "hi"\n')
        path = f.name
    try:
        result = subprocess.run(
            ["bash", "-n", path], capture_output=True, text=True
        )
        assert result.returncode == 0, f"bash -n failed: {result.stderr}"
    finally:
        Path(path).unlink()


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_bash_timeout_func_kills_sigterm_ignoring_process(tmp_path):
    """Integration check: a child process that traps SIGTERM must still be
    killed by the escalation path within grace_period + margin seconds.

    We use a bash-only busy loop (`while :; do :; done`) as the child so
    that SIGKILL'ing it leaves no orphaned `sleep` holding the parent's
    stdout pipe open. rc is written to a file to avoid any pipe plumbing
    at all — subprocess.run just waits for bash to exit.
    """
    rc_file = tmp_path / "rc.txt"
    script = f"""\
#!/usr/bin/env bash
{_BASH_TIMEOUT_FUNC}
# Trap SIGTERM and busy-loop in pure bash (no child process to orphan).
# _timeout's 1s timer fires, sends SIGTERM (trapped / ignored), waits
# 10s grace, then sends SIGKILL.
_timeout 1 bash -c 'trap "" TERM; while :; do :; done'
echo "$?" > {rc_file}
"""
    script_path = tmp_path / "run.sh"
    script_path.write_text(script)

    # 1s timeout + 10s grace = ~11s expected, plus slack.
    result = subprocess.run(
        ["bash", str(script_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    assert result.returncode == 0
    rc = rc_file.read_text().strip()
    # SIGKILL → 128 + 9 = 137
    assert rc == "137", f"expected rc=137 after SIGKILL, got rc={rc!r}"


# ── build_launch_script ───────────────────────────────────────────────

def _bash_n(script: str) -> None:
    """Assert that a generated script parses under `bash -n`."""
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
        f.write(script)
        path = f.name
    try:
        result = subprocess.run(
            ["bash", "-n", path], capture_output=True, text=True
        )
        assert result.returncode == 0, (
            f"bash -n failed:\nstderr={result.stderr}\nscript:\n{script}"
        )
    finally:
        Path(path).unlink()


def test_launch_script_with_duration_parses():
    script = build_launch_script(
        backend_command="echo hello 2>&1 | tee -a agent.log",
        duration_hours=0.01,
        session_timeout=60,
    )
    _bash_n(script)


def test_launch_script_without_duration_parses():
    script = build_launch_script(
        backend_command="echo hello 2>&1 | tee -a agent.log",
        duration_hours=None,
        session_timeout=60,
    )
    _bash_n(script)


def test_launch_script_with_simple_resume_parses():
    script = build_launch_script(
        backend_command="echo fresh 2>&1 | tee -a agent.log",
        duration_hours=0.01,
        resume_command="echo resume 2>&1 | tee -a agent.log",
    )
    _bash_n(script)
    # sentinel-file path
    assert ".reva_has_run" in script


def test_launch_script_with_session_id_resume_parses():
    script = build_launch_script(
        backend_command="echo fresh 2>&1 | tee -a agent.log",
        duration_hours=0.01,
        resume_command='echo resume --session "$SESSION_ID" | tee -a agent.log',
    )
    _bash_n(script)
    # session-ID path — must handle fallback and save id
    assert "last_session_id" in script
    assert "RESUME_RC" in script


def test_launch_script_with_session_id_extractor():
    extractor = "my-cli sessions --last 2>/dev/null"
    script = build_launch_script(
        backend_command="echo fresh 2>&1 | tee -a agent.log",
        duration_hours=0.01,
        resume_command='echo resume "$SESSION_ID" | tee -a agent.log',
        session_id_extractor=extractor,
    )
    _bash_n(script)
    assert extractor in script
    # Extractor replaces the default stream-json parser
    assert "last_session_id" in script


def test_launch_script_has_pipefail():
    """Without `set -o pipefail`, codex exiting non-zero through | tee would
    look like a successful run. See commit 56cf506."""
    script = build_launch_script("echo hi 2>&1 | tee -a agent.log", duration_hours=1.0)
    assert "set -o pipefail" in script


def test_launch_script_has_timeout_function():
    script = build_launch_script("echo hi 2>&1 | tee -a agent.log", duration_hours=1.0)
    assert "_timeout()" in script
    assert "kill -TERM" in script
    assert "kill -KILL" in script


def test_launch_script_duration_converts_hours_to_seconds():
    script = build_launch_script(
        "echo hi 2>&1 | tee -a agent.log", duration_hours=2.0
    )
    assert "TIMEOUT=7200" in script  # 2h * 3600


def test_launch_script_caps_per_run_at_session_timeout():
    """PER_RUN = min(REMAINING, SESSION_TIMEOUT) — protects against codex
    sitting idle forever after completing a prompt."""
    script = build_launch_script(
        "echo hi 2>&1 | tee -a agent.log",
        duration_hours=1.0,
        session_timeout=300,
    )
    assert "SESSION_TIMEOUT=300" in script
    assert "PER_RUN=" in script


def test_launch_script_loops_forever_without_duration():
    script = build_launch_script(
        "echo hi 2>&1 | tee -a agent.log", duration_hours=None
    )
    assert "while true" in script
    # No TIMEOUT variable when duration is None
    assert "TIMEOUT=" not in script.replace("SESSION_TIMEOUT", "")


def test_launch_script_loads_agent_env_inside_loop():
    """The .env and .api_key files are written after first registration, so
    they must be re-sourced on every cycle, not once at startup."""
    script = build_launch_script(
        "echo hi 2>&1 | tee -a agent.log", duration_hours=1.0
    )
    assert script.count("_load_agent_env") >= 2


# ── _make_run_block ───────────────────────────────────────────────────

def test_make_run_block_no_resume():
    block = _make_run_block("my-cmd", None, "60", None)
    assert "my-cmd" in block
    assert ".reva_has_run" not in block
    assert "$SESSION_ID" not in block


def test_make_run_block_simple_resume():
    block = _make_run_block("fresh-cmd", "resume-cmd", "60", None)
    assert "fresh-cmd" in block
    assert "resume-cmd" in block
    assert ".reva_has_run" in block


def test_make_run_block_session_id_resume_falls_back_on_failure():
    """Regression: session-id resume must fall back to a fresh run when the
    resume command exits non-zero (session deferred, deleted, etc.).
    See commit 8b5ea8b."""
    block = _make_run_block(
        "fresh-cmd",
        'claude --resume "$SESSION_ID" 2>&1 | tee -a agent.log',
        "60",
        None,
    )
    assert "RESUME_RC" in block
    # On non-zero resume, re-run the fresh command
    assert "fresh-cmd" in block
    assert "last_session_id" in block
