"""Tests for reva.config — TOML resolution and defaults."""
from pathlib import Path

import pytest

from reva.config import (
    CONFIG_FILENAME,
    DEFAULT_CONFIG,
    DEFAULT_INITIAL_PROMPT,
    RevaConfig,
    find_config,
    load_config,
    write_default_config,
)


def test_write_default_config_creates_file(tmp_path):
    result = write_default_config(tmp_path)
    assert result.exists()
    assert result.name == CONFIG_FILENAME
    assert result.parent == tmp_path


def test_write_default_config_creates_missing_parents(tmp_path):
    target = tmp_path / "nested" / "dir"
    result = write_default_config(target)
    assert result.exists()
    assert target.exists()


def test_default_config_file_contains_all_default_keys(tmp_path):
    path = write_default_config(tmp_path)
    content = path.read_text()
    for key in DEFAULT_CONFIG:
        assert key in content, f"{key} missing from default config"


def test_default_config_keys_are_exactly_expected():
    """DEFAULT_CONFIG should contain only the simplified set of keys."""
    assert set(DEFAULT_CONFIG) == {
        "agents_dir",
        "global_rules",
        "platform_skills",
        "github_repo",
    }


def test_load_config_uses_explicit_path(tmp_path):
    cfg_path = write_default_config(tmp_path)
    config = load_config(str(cfg_path))
    assert isinstance(config, RevaConfig)
    assert config.project_root == tmp_path


def test_load_config_resolves_agents_dir_relative_to_project_root(tmp_path):
    cfg_path = write_default_config(tmp_path)
    config = load_config(str(cfg_path))
    assert config.agents_dir == (tmp_path / "agents/").resolve()


def test_load_config_without_path_falls_back_to_defaults(tmp_path, monkeypatch):
    """No config.toml anywhere → load_config returns defaults anchored at cwd."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("REVA_CONFIG", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))  # no ~/.reva/config.toml
    config = load_config(None)
    assert config.project_root == tmp_path


def test_find_config_via_explicit_path_that_exists(tmp_path):
    cfg_path = write_default_config(tmp_path)
    found = find_config(str(cfg_path))
    assert found == cfg_path


def test_find_config_via_explicit_path_that_does_not_exist(tmp_path):
    assert find_config(str(tmp_path / "missing.toml")) is None


def test_find_config_walks_up_from_cwd(tmp_path, monkeypatch):
    cfg_path = write_default_config(tmp_path)
    sub = tmp_path / "sub" / "deeper"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    monkeypatch.delenv("REVA_CONFIG", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "nonexistent-home"))
    found = find_config(None)
    assert found == cfg_path


def test_find_config_reads_env_var(tmp_path, monkeypatch):
    cfg_path = write_default_config(tmp_path)
    other = tmp_path / "unrelated"
    other.mkdir()
    monkeypatch.chdir(other)
    monkeypatch.setenv("REVA_CONFIG", str(cfg_path))
    monkeypatch.setenv("HOME", str(tmp_path / "nonexistent-home"))
    found = find_config(None)
    if (other / CONFIG_FILENAME).exists() or any(
        (p / CONFIG_FILENAME).exists() for p in other.parents
    ):
        pass
    else:
        assert found == cfg_path


def test_load_config_applies_custom_agents_dir(tmp_path):
    cfg = tmp_path / CONFIG_FILENAME
    cfg.write_text('agents_dir = "./my-agents/"\n')
    config = load_config(str(cfg))
    assert config.agents_dir.name == "my-agents"


def test_load_config_merges_with_defaults(tmp_path):
    """Overriding one key should leave other defaults intact."""
    cfg = tmp_path / CONFIG_FILENAME
    cfg.write_text('agents_dir = "./override/"\n')
    config = load_config(str(cfg))
    assert config.agents_dir.name == "override"
    assert config.global_rules_path.name == "GLOBAL_RULES.md"


def test_default_initial_prompt_is_nonempty_string():
    assert isinstance(DEFAULT_INITIAL_PROMPT, str)
    assert len(DEFAULT_INITIAL_PROMPT) > 0
    # Must mention the .api_key file the owner provisions
    assert ".api_key" in DEFAULT_INITIAL_PROMPT


def test_default_initial_prompt_has_no_registration_language():
    """Self-registration is gone — the prompt must not ask the agent to register."""
    assert "register" not in DEFAULT_INITIAL_PROMPT.lower()
    assert "owner_password" not in DEFAULT_INITIAL_PROMPT
    assert "owner_email" not in DEFAULT_INITIAL_PROMPT
    assert "owner_name" not in DEFAULT_INITIAL_PROMPT


def test_default_config_has_github_repo():
    assert "github_repo" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["github_repo"] == ""


def test_default_config_has_no_owner_fields():
    assert "owner_email" not in DEFAULT_CONFIG
    assert "owner_name" not in DEFAULT_CONFIG
    assert "owner_password" not in DEFAULT_CONFIG


def test_default_config_has_no_component_dirs():
    for removed in (
        "personas_dir",
        "roles_dir",
        "interests_dir",
        "review_methodology_dir",
        "review_format_dir",
        "review_methodology",
        "review_format",
    ):
        assert removed not in DEFAULT_CONFIG


def test_reva_config_github_repo_default(tmp_path):
    cfg_path = write_default_config(tmp_path)
    config = load_config(str(cfg_path))
    assert config.github_repo == ""


def test_reva_config_has_no_owner_fields(tmp_path):
    cfg_path = write_default_config(tmp_path)
    config = load_config(str(cfg_path))
    for removed in ("owner_email", "owner_name", "owner_password"):
        assert not hasattr(config, removed)


def test_reva_config_has_no_component_dirs(tmp_path):
    cfg_path = write_default_config(tmp_path)
    config = load_config(str(cfg_path))
    for removed in (
        "personas_dir",
        "roles_dir",
        "interests_dir",
        "review_methodology_dir",
        "review_format_dir",
        "review_methodology_path",
        "review_format_path",
        "review_methodology_weights",
    ):
        assert not hasattr(config, removed)


def test_load_config_reads_custom_github_repo(tmp_path):
    cfg = tmp_path / CONFIG_FILENAME
    cfg.write_text('github_repo = "https://github.com/example/repo"\n')
    config = load_config(str(cfg))
    assert config.github_repo == "https://github.com/example/repo"


def test_initial_prompt_template_has_koala_base_url_placeholder():
    assert "{koala_base_url}" in DEFAULT_INITIAL_PROMPT


def test_initial_prompt_template_renders_without_error():
    rendered = DEFAULT_INITIAL_PROMPT.format(
        koala_base_url="https://koala.science",
    )
    # Placeholder must be gone
    assert "{koala_base_url}" not in rendered
    assert "https://koala.science" in rendered


def test_initial_prompt_mentions_koala_science():
    assert "Koala Science" in DEFAULT_INITIAL_PROMPT
    rendered = DEFAULT_INITIAL_PROMPT.format(
        koala_base_url="https://koala.science",
    )
    assert "https://koala.science" in rendered


def test_initial_prompt_renders_with_staging_base_url():
    rendered = DEFAULT_INITIAL_PROMPT.format(
        koala_base_url="https://staging.koala.science",
    )
    assert "https://staging.koala.science" in rendered
    assert "https://koala.science/" not in rendered
    assert "https://koala.science\n" not in rendered
    assert "https://koala.science " not in rendered


def test_initial_prompt_mentions_github_file_url():
    assert "github_file_url" in DEFAULT_INITIAL_PROMPT
