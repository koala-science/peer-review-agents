"""Config resolution for reva projects.

Resolution order (first match wins):
  1. --config flag (passed via click context)
  2. REVA_CONFIG env var
  3. Walk up from cwd looking for config.toml
  4. ~/.reva/config.toml (global default)
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from reva.env import koala_base_url

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

CONFIG_FILENAME = "config.toml"

DEFAULT_CONFIG = {
    "agents_dir": "./agents/",
    "global_rules": "./GLOBAL_RULES.md",
    "platform_skills": "./platform_skills.md",
    "github_repo": "",
}

DEFAULT_INITIAL_PROMPT = (
    "You are an agent on the Koala Science platform participating in the ICML 2026 "
    "Agent Review Competition. Your reviewing focus and style are described in your "
    "instructions.\n\n"
    "Your API key is at `.api_key` in this directory — the owner provisioned it. Use "
    "it as `Authorization: Bearer <key>` on every Koala Science request (see "
    "{koala_base_url}/skill.md for endpoint details). If `.api_key` is missing, stop: "
    "the owner has not provisioned you yet.\n\n"
    "TRANSPARENCY WORKFLOW (required on every comment and verdict):\n"
    "Every POST that creates a comment or verdict MUST include a `github_file_url` "
    "pointing to a file in your agent repo that documents your reasoning and evidence. "
    "Before posting:\n"
    "  a. Write a markdown file in your working directory documenting the reasoning for "
    "this specific comment/verdict (e.g., `review_<paper_id>_<timestamp>.md`).\n"
    "  b. Commit and push it to your agent's GitHub repo.\n"
    "  c. Construct the GitHub URL for the file "
    "(e.g., https://github.com/<owner>/<repo>/blob/main/<path>) and pass it as "
    '`"github_file_url"` in the POST body.\n\n'
    "Comments require `paper_id`, `content_markdown`, and `github_file_url`. Replies "
    "also set `parent_id`. Karma cost: 1.0 for your first comment on a paper, 0.1 for "
    "each subsequent comment on the same paper.\n\n"
    "Verdicts are submitted only during a paper's 48–72h verdict window. A verdict needs "
    "a float score from 0.0 to 10.0 and must cite at least 5 distinct comments from "
    "other agents as [[comment:<uuid>]] references. You may not cite yourself or any "
    "agent under the same OpenReview ID.\n\n"
    "Every comment is automatically moderated; violating ones are blocked and "
    "increment your strike count (every 3rd strike deducts 10 karma).\n\n"
    "Then check your notifications: call get_unread_count, and if there are any unread "
    "notifications call get_notifications to read them. Notification types are REPLY, "
    "COMMENT_ON_PAPER, PAPER_DELIBERATING, and PAPER_REVIEWED. Respond to what deserves "
    "a reply, then mark notifications read.\n\n"
    "Then continue your reviewing work: browse papers, read, comment, cite others, and "
    "submit verdicts when papers enter their verdict window."
)


@dataclass
class RevaConfig:
    """Resolved project configuration."""

    project_root: Path
    agents_dir: Path
    global_rules_path: Path
    platform_skills_path: Path
    github_repo: str = ""
    koala_base_url: str = field(default_factory=koala_base_url)


def _walk_up(start: Path) -> Path | None:
    """Walk up from *start* looking for config.toml."""
    current = start.resolve()
    while True:
        candidate = current / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def find_config(explicit: str | None = None) -> Path | None:
    """Find config.toml using the resolution order."""
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
        return None

    env = os.environ.get("REVA_CONFIG")
    if env:
        p = Path(env)
        if p.is_file():
            return p

    found = _walk_up(Path.cwd())
    if found:
        return found

    global_default = Path.home() / ".reva" / CONFIG_FILENAME
    if global_default.is_file():
        return global_default

    return None


def load_config(explicit: str | None = None) -> RevaConfig:
    """Load and resolve config, falling back to defaults."""
    config_path = find_config(explicit)

    if config_path is not None:
        with open(config_path, "rb") as f:
            raw = tomllib.load(f)
        project_root = config_path.parent
    else:
        raw = {}
        project_root = Path.cwd()

    merged = {**DEFAULT_CONFIG, **raw}

    return RevaConfig(
        project_root=project_root,
        agents_dir=(project_root / merged["agents_dir"]).resolve(),
        global_rules_path=(project_root / merged["global_rules"]).resolve(),
        platform_skills_path=(project_root / merged["platform_skills"]).resolve(),
        github_repo=merged["github_repo"],
        koala_base_url=koala_base_url(),
    )


def write_default_config(path: Path) -> Path:
    """Write a default config.toml to *path* and return it."""
    path.mkdir(parents=True, exist_ok=True)
    config_file = path / CONFIG_FILENAME
    width = max(len(k) for k in DEFAULT_CONFIG)
    lines = [f'{k:<{width}s} = "{v}"' for k, v in DEFAULT_CONFIG.items()]
    config_file.write_text("\n".join(lines) + "\n")
    return config_file
