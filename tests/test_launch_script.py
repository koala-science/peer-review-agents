"""Tests for reva.launch_script.write_launch_files — the extracted helper
that writes .reva_launch.sh and .reva_env.sh into an agent directory.

Both the tmux path and the cluster path share this helper, so the
behavior must be identical regardless of caller.
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from reva.launch_script import ENV_FILENAME, LAUNCH_FILENAME, write_launch_files


def test_write_launch_files_writes_launch_sh(tmp_path):
    write_launch_files(str(tmp_path), "echo hi\n")
    assert (tmp_path / LAUNCH_FILENAME).exists()


def test_write_launch_files_writes_env_sh(tmp_path):
    write_launch_files(str(tmp_path), "echo hi\n")
    assert (tmp_path / ENV_FILENAME).exists()


def test_write_launch_files_launch_sh_sources_env_sh(tmp_path):
    write_launch_files(str(tmp_path), "echo body\n")
    launch = (tmp_path / LAUNCH_FILENAME).read_text()
    assert ENV_FILENAME in launch
    assert "source" in launch
    assert "echo body" in launch


@pytest.mark.skipif(os.name != "posix", reason="Legacy launcher requires POSIX executable mode bits")
def test_write_launch_files_launch_sh_is_executable(tmp_path):
    write_launch_files(str(tmp_path), "echo hi\n")
    mode = (tmp_path / LAUNCH_FILENAME).stat().st_mode & 0o777
    assert mode & 0o100, f"launch script not executable: {oct(mode)}"


@pytest.mark.skipif(os.name != "posix", reason="Legacy launcher requires POSIX permission bits")
def test_write_launch_files_env_sh_has_restrictive_perms(tmp_path):
    write_launch_files(str(tmp_path), "echo hi\n")
    mode = (tmp_path / ENV_FILENAME).stat().st_mode & 0o777
    # must not be world-readable (secrets)
    assert not (mode & 0o077), f"env file too permissive: {oct(mode)}"


def test_write_launch_files_forwards_relevant_env_vars(tmp_path, monkeypatch):
    """Only GEMINI_/ANTHROPIC_/OPENAI_/GOOGLE_/COALESCENCE_ vars are forwarded."""
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-value")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-value")
    monkeypatch.setenv("RANDOM_UNRELATED", "nope")

    write_launch_files(str(tmp_path), "echo hi\n")
    env = (tmp_path / ENV_FILENAME).read_text()

    assert "GEMINI_API_KEY" in env
    assert "gemini-value" in env
    assert "ANTHROPIC_API_KEY" in env
    assert "RANDOM_UNRELATED" not in env


def test_write_launch_files_self_cleans_env_file(tmp_path):
    """The generated launch script should rm the env file after sourcing."""
    write_launch_files(str(tmp_path), "echo hi\n")
    launch = (tmp_path / LAUNCH_FILENAME).read_text()
    assert "rm -f" in launch
    assert ENV_FILENAME in launch
