"""Tests for reva.cluster — SLURM submission, cancellation, and listing.

All tests mock subprocess.run / shutil.which — no real SLURM calls.
"""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from reva.cluster import (
    SBATCH_FILENAME,
    STOP_SENTINEL,
    ClusterJob,
    cancel_chain,
    list_cluster_jobs,
    submit_agent,
)


def _fake_sbatch_success(job_id: int = 12345):
    result = MagicMock()
    result.returncode = 0
    result.stdout = f"Submitted batch job {job_id}\n"
    result.stderr = ""
    return result


# ── submit_agent ──────────────────────────────────────────────────────

def test_submit_agent_renders_sbatch_script(tmp_path):
    """submit_agent writes .reva_cluster.sbatch with #SBATCH headers for
    partition/time/cpus/mem/job-name, its body invokes .reva_launch.sh, and
    the trap clause is present."""
    agent_dir = tmp_path / "foo"
    agent_dir.mkdir()
    # pretend launch script has already been written
    (agent_dir / ".reva_launch.sh").write_text("#!/bin/bash\necho hi\n")

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/sbatch"), \
         patch("reva.cluster.subprocess.run", return_value=_fake_sbatch_success()):
        submit_agent(
            str(agent_dir),
            agent_name="foo",
            partition="main-cpu",
            time="5-00:00:00",
            cpus=4,
            mem="16G",
            max_chain=3,
        )

    sbatch_path = agent_dir / SBATCH_FILENAME
    assert sbatch_path.exists()
    script = sbatch_path.read_text()

    assert "#SBATCH --job-name=reva_foo" in script
    assert "#SBATCH --partition=main-cpu" in script
    assert "#SBATCH --time=5-00:00:00" in script
    assert "#SBATCH --cpus-per-task=4" in script
    assert "#SBATCH --mem=16G" in script
    assert "#SBATCH --output=" in script
    assert "cluster.%j.out" in script
    assert "#SBATCH --error=" in script
    assert "cluster.%j.err" in script

    assert ".reva_launch.sh" in script
    assert "trap _chain_next EXIT" in script


def test_submit_agent_calls_sbatch_with_script_path(tmp_path):
    """mocked subprocess.run receives the sbatch script path, run in the
    agent dir."""
    agent_dir = tmp_path / "foo"
    agent_dir.mkdir()
    (agent_dir / ".reva_launch.sh").write_text("#!/bin/bash\necho hi\n")

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/sbatch"), \
         patch("reva.cluster.subprocess.run", return_value=_fake_sbatch_success()) as mock_run:
        submit_agent(
            str(agent_dir),
            agent_name="foo",
            partition="main-cpu",
            time="5-00:00:00",
            cpus=4,
            mem="16G",
            max_chain=3,
        )

    args, kwargs = mock_run.call_args
    cmd = args[0]
    assert cmd[0] == "sbatch"
    assert str(agent_dir / SBATCH_FILENAME) in cmd or SBATCH_FILENAME in cmd[-1]
    assert kwargs.get("cwd") == str(agent_dir)


def test_submit_agent_returns_parsed_job_id(tmp_path):
    """sbatch stdout 'Submitted batch job 12345\\n' → function returns 12345."""
    agent_dir = tmp_path / "foo"
    agent_dir.mkdir()
    (agent_dir / ".reva_launch.sh").write_text("echo hi\n")

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/sbatch"), \
         patch("reva.cluster.subprocess.run", return_value=_fake_sbatch_success(99999)):
        job_id = submit_agent(
            str(agent_dir),
            agent_name="foo",
            partition="main-cpu",
            time="5-00:00:00",
            cpus=4,
            mem="16G",
            max_chain=3,
        )

    assert job_id == 99999


def test_submit_agent_refuses_if_sbatch_missing(tmp_path):
    """shutil.which('sbatch') returns None → raises RuntimeError mentioning SLURM."""
    agent_dir = tmp_path / "foo"
    agent_dir.mkdir()
    (agent_dir / ".reva_launch.sh").write_text("echo hi\n")

    with patch("reva.cluster.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="SLURM"):
            submit_agent(
                str(agent_dir),
                agent_name="foo",
                partition="main-cpu",
                time="5-00:00:00",
                cpus=4,
                mem="16G",
                max_chain=3,
            )


def test_submit_agent_validates_time_format(tmp_path):
    """Bad --time value raises before any subprocess.run."""
    agent_dir = tmp_path / "foo"
    agent_dir.mkdir()
    (agent_dir / ".reva_launch.sh").write_text("echo hi\n")

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/sbatch"), \
         patch("reva.cluster.subprocess.run") as mock_run:
        with pytest.raises(ValueError, match="time"):
            submit_agent(
                str(agent_dir),
                agent_name="foo",
                partition="main-cpu",
                time="99-notvalid",
                cpus=4,
                mem="16G",
                max_chain=3,
            )
        mock_run.assert_not_called()


def test_submit_agent_accepts_valid_time_formats(tmp_path):
    """Accepts days-HH:MM:SS, HH:MM:SS, and HH:MM formats."""
    agent_dir = tmp_path / "foo"
    agent_dir.mkdir()
    (agent_dir / ".reva_launch.sh").write_text("echo hi\n")

    valid = ["5-00:00:00", "1-12:30:00", "12:00:00", "02:30:00", "00:10"]
    for t in valid:
        with patch("reva.cluster.shutil.which", return_value="/usr/bin/sbatch"), \
             patch("reva.cluster.subprocess.run", return_value=_fake_sbatch_success()):
            submit_agent(
                str(agent_dir),
                agent_name="foo",
                partition="main-cpu",
                time=t,
                cpus=4,
                mem="16G",
                max_chain=3,
            )


def test_chain_trap_uses_max_chain_env_var(tmp_path):
    """Inspect generated script: assert the chain trap wires up the exact
    sbatch dependency + env-var propagation expected by SLURM, and that the
    sentinel / chain-counter plumbing is present.

    These are the single most failure-prone lines in the whole SLURM
    integration: a subtle typo here silently breaks chaining past wall time
    with no error, and an agent just stops after its first wall-time hit."""
    agent_dir = tmp_path / "foo"
    agent_dir.mkdir()
    (agent_dir / ".reva_launch.sh").write_text("echo hi\n")

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/sbatch"), \
         patch("reva.cluster.subprocess.run", return_value=_fake_sbatch_success()):
        submit_agent(
            str(agent_dir),
            agent_name="foo",
            partition="main-cpu",
            time="5-00:00:00",
            cpus=4,
            mem="16G",
            max_chain=7,
        )

    script = (agent_dir / SBATCH_FILENAME).read_text()
    assert "$REVA_MAX_CHAIN" in script
    assert "$REVA_CHAIN_N" in script
    assert ".reva_stop" in script
    # first-submit default is 7 (baked into the script)
    assert "REVA_MAX_CHAIN:-7" in script
    # chained-successor wiring: dependency syntax and env-var propagation
    # must be exact, or SLURM runs the successor immediately or without
    # the chain counter, and the chain cap silently breaks.
    assert "--dependency=afterany:$SLURM_JOB_ID" in script
    assert "--export=ALL,REVA_CHAIN_N=$NEXT,REVA_MAX_CHAIN=$REVA_MAX_CHAIN" in script
    # sentinel-wipe must be gated so successor jobs preserve a sentinel
    # written by cancel_chain during the scancel race window.
    assert "[ -z \"$REVA_CHAIN_N\" ]" in script, (
        "only the first chain link may rm the sentinel; successor jobs "
        "(REVA_CHAIN_N set via --export) must preserve it"
    )


@pytest.mark.skipif(os.name != "posix", reason="SLURM shell scripts execute on POSIX")
def test_chain_trap_sbatch_script_parses_under_bash_n(tmp_path):
    """The generated sbatch script must parse cleanly under `bash -n`.

    The sbatch template uses nested braces (trap + arithmetic expansion +
    parameter expansion) that are easy to break at format-string level.
    `bash -n` catches malformed generated bash before any real SLURM call."""
    import subprocess as _sp
    agent_dir = tmp_path / "foo"
    agent_dir.mkdir()
    (agent_dir / ".reva_launch.sh").write_text("echo hi\n")

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/sbatch"), \
         patch("reva.cluster.subprocess.run", return_value=_fake_sbatch_success()):
        submit_agent(
            str(agent_dir),
            agent_name="foo",
            partition="main-cpu",
            time="5-00:00:00",
            cpus=4,
            mem="16G",
            max_chain=3,
        )

    script = (agent_dir / SBATCH_FILENAME).read_text()
    result = _sp.run(
        ["bash", "-n"],
        input=script,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"bash -n failed:\nstderr={result.stderr}\nscript:\n{script}"
    )


# ── cancel_chain ──────────────────────────────────────────────────────

def test_cancel_chain_writes_stop_sentinel_then_scancels(tmp_path):
    """cancel_chain writes .reva_stop sentinel before invoking scancel, so
    that a pending successor job won't proceed even if scancel misses it."""
    agent_dir = tmp_path / "foo"
    agent_dir.mkdir()

    # squeue returns two matching job IDs
    squeue_result = MagicMock()
    squeue_result.returncode = 0
    squeue_result.stdout = "55555|reva_foo|RUNNING|4:00:00\n55556|reva_foo|PENDING|UNLIMITED\n"

    scancel_result = MagicMock()
    scancel_result.returncode = 0
    scancel_result.stdout = ""

    call_order = []

    def fake_run(cmd, *args, **kwargs):
        call_order.append(cmd[0])
        if cmd[0] == "squeue":
            return squeue_result
        if cmd[0] == "scancel":
            return scancel_result
        raise AssertionError(f"Unexpected call: {cmd}")

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/scancel"), \
         patch("reva.cluster.subprocess.run", side_effect=fake_run):
        count = cancel_chain(agent_name="foo", agent_dir=str(agent_dir))

    assert (agent_dir / STOP_SENTINEL).exists()
    assert count == 2

    # sentinel written first → scancel afterwards
    # (we can't observe the file write in call_order, but we can ensure squeue
    # came before scancel and that sentinel is on disk)
    assert call_order[0] == "squeue"
    assert "scancel" in call_order


def test_cancel_chain_no_matching_jobs_still_writes_sentinel(tmp_path):
    agent_dir = tmp_path / "foo"
    agent_dir.mkdir()

    squeue_result = MagicMock()
    squeue_result.returncode = 0
    squeue_result.stdout = ""

    def fake_run(cmd, *args, **kwargs):
        assert cmd[0] == "squeue"
        return squeue_result

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/scancel"), \
         patch("reva.cluster.subprocess.run", side_effect=fake_run):
        count = cancel_chain(agent_name="foo", agent_dir=str(agent_dir))

    assert count == 0
    assert (agent_dir / STOP_SENTINEL).exists()


# ── list_cluster_jobs ─────────────────────────────────────────────────

def test_list_cluster_jobs_parses_squeue_output():
    """Canned squeue stdout parses into ClusterJob records."""
    squeue_result = MagicMock()
    squeue_result.returncode = 0
    squeue_result.stdout = (
        "12345|reva_foo|RUNNING|4:23:11\n"
        "12346|reva_bar|PENDING|UNLIMITED\n"
        "12347|reva_foo|PENDING|5-00:00:00\n"
    )

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/squeue"), \
         patch("reva.cluster.subprocess.run", return_value=squeue_result):
        jobs = list_cluster_jobs()

    assert len(jobs) == 3
    assert jobs[0] == ClusterJob(agent_name="foo", job_id=12345, state="RUNNING", time_left="4:23:11")
    assert jobs[1] == ClusterJob(agent_name="bar", job_id=12346, state="PENDING", time_left="UNLIMITED")
    assert jobs[2] == ClusterJob(agent_name="foo", job_id=12347, state="PENDING", time_left="5-00:00:00")


def test_list_cluster_jobs_returns_empty_when_no_jobs():
    squeue_result = MagicMock()
    squeue_result.returncode = 0
    squeue_result.stdout = ""

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/squeue"), \
         patch("reva.cluster.subprocess.run", return_value=squeue_result):
        jobs = list_cluster_jobs()

    assert jobs == []


def test_list_cluster_jobs_returns_empty_when_squeue_missing():
    """No squeue on $PATH → empty list (not a crash)."""
    with patch("reva.cluster.shutil.which", return_value=None):
        jobs = list_cluster_jobs()
    assert jobs == []


def test_list_cluster_jobs_skips_jobs_without_reva_prefix():
    """squeue listing includes every user job (no --name glob — see
    test_list_cluster_jobs_does_not_glob_name); non-reva jobs must be
    filtered out client-side."""
    squeue_result = MagicMock()
    squeue_result.returncode = 0
    squeue_result.stdout = (
        "12345|reva_foo|RUNNING|4:23:11\n"
        "12346|other_job|RUNNING|1:00:00\n"
    )

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/squeue"), \
         patch("reva.cluster.subprocess.run", return_value=squeue_result):
        jobs = list_cluster_jobs()

    assert len(jobs) == 1
    assert jobs[0].agent_name == "foo"


def test_list_cluster_jobs_does_not_glob_name():
    """Regression: squeue's --name takes exact job names (comma-separated),
    not globs. Passing --name=reva_* silently returns zero rows, so
    list_cluster_jobs must NOT use --name at all — it must list every
    user job and filter by prefix client-side."""
    captured_cmd: list[str] = []

    def fake_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        r = MagicMock()
        r.returncode = 0
        r.stdout = "12345|reva_foo|RUNNING|4:23:11\n"
        return r

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/squeue"), \
         patch("reva.cluster.subprocess.run", side_effect=fake_run):
        list_cluster_jobs()

    assert any(arg.startswith("--name") for arg in captured_cmd) is False, (
        f"--name argument found in squeue call {captured_cmd!r}; "
        "squeue's --name takes exact names, not globs — filter client-side instead"
    )


def test_submit_agent_refuses_without_launch_script(tmp_path):
    """submit_agent must not render sbatch if .reva_launch.sh is missing."""
    agent_dir = tmp_path / "foo"
    agent_dir.mkdir()

    with patch("reva.cluster.shutil.which", return_value="/usr/bin/sbatch"), \
         patch("reva.cluster.subprocess.run") as mock_run:
        with pytest.raises(FileNotFoundError, match=".reva_launch.sh"):
            submit_agent(
                str(agent_dir),
                agent_name="foo",
                partition="main-cpu",
                time="5-00:00:00",
                cpus=4,
                mem="16G",
                max_chain=3,
            )
        mock_run.assert_not_called()
