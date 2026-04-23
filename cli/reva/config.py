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

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

CONFIG_FILENAME = "config.toml"

DEFAULT_CONFIG = {
    "agents_dir": "./agents/",
    "personas_dir": "./personas/",
    "roles_dir": "./roles/",
    "interests_dir": "./interests/",
    "review_methodology_dir": "./review_methodology/",
    "review_format_dir": "./review_formats/",
    "global_rules": "./GLOBAL_RULES.md",
    "platform_skills": "./platform_skills.md",
    "review_methodology": "",
    "review_format": "",
    "owner_email": "reva@agents.local",
    "owner_name": "reva",
    "owner_password": "reva-owner-2026",
    "github_repo": "",
}

DEFAULT_INITIAL_PROMPT = (
    "You are an agent on the Koala Science platform participating in the ICML 2026 "
    "Agent Review Competition. Your role, research interests, and persona are described "
    "in your instructions.\n\n"
    "IMPORTANT — Identity and authentication:\n"
    "1. Read `.agent_name` to get your platform username.\n"
    "2. Check if `.api_key` exists. If it does, use it to authenticate (call "
    "https://koala.science/api/v1/users/me to verify). Do NOT register again — you are "
    "already registered.\n"
    "3. If `.api_key` does NOT exist, register as follows:\n"
    "   a. Read https://koala.science/skill.md for API details.\n"
    "   b. Try POST https://koala.science/api/v1/auth/agents/register with:\n"
    '      {{"name": "<your .agent_name>", "owner_email": "{owner_email}", '
    '"owner_name": "{owner_name}", "owner_password": "{owner_password}", '
    '"github_repo": "{github_repo}"}}\n'
    "   c. If that fails (HTTP 409 or email-already-exists error), the owner account "
    "already exists. In that case:\n"
    '      - POST /api/v1/auth/login with {{"email": "{owner_email}", "password": "{owner_password}"}} '
    "to get an owner token.\n"
    "      - Use the owner token to register this agent under the existing owner "
    "(see skill.md for the current endpoint).\n"
    "   d. Save the returned API key to `.api_key` immediately. The API key is passed "
    "as a Bearer token in the Authorization header on every subsequent request.\n\n"
    "TRANSPARENCY WORKFLOW (required on every comment and verdict):\n"
    "Every POST that creates a comment or verdict MUST include a `github_file_url` "
    "pointing to a file in your agent repo that documents your reasoning and evidence. "
    "Before posting:\n"
    "  a. Write a markdown file in your working directory documenting the reasoning for "
    "this specific comment/verdict (e.g., `review_<paper_id>_<timestamp>.md`).\n"
    "  b. Commit and push it to the GitHub repo: {github_repo}\n"
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
    "submit verdicts when papers enter their verdict window. Never re-register if you "
    "already have a valid API key."
)


@dataclass
class RevaConfig:
    """Resolved project configuration."""

    project_root: Path
    agents_dir: Path
    personas_dir: Path
    roles_dir: Path
    interests_dir: Path
    review_methodology_dir: Path
    review_format_dir: Path
    global_rules_path: Path
    platform_skills_path: Path
    review_methodology_path: Path | None = None
    review_format_path: Path | None = None
    review_methodology_weights: dict[str, int] = field(default_factory=dict)
    owner_email: str = "reva@agents.local"
    owner_name: str = "reva"
    owner_password: str = "reva-owner-2026"
    github_repo: str = ""


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
    # 1. explicit --config flag
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
        return None

    # 2. REVA_CONFIG env var
    env = os.environ.get("REVA_CONFIG")
    if env:
        p = Path(env)
        if p.is_file():
            return p

    # 3. walk up from cwd
    found = _walk_up(Path.cwd())
    if found:
        return found

    # 4. global default
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

    def _optional(key: str) -> Path | None:
        val = merged.get(key, "")
        return (project_root / val).resolve() if val else None

    return RevaConfig(
        project_root=project_root,
        agents_dir=(project_root / merged["agents_dir"]).resolve(),
        personas_dir=(project_root / merged["personas_dir"]).resolve(),
        roles_dir=(project_root / merged["roles_dir"]).resolve(),
        interests_dir=(project_root / merged["interests_dir"]).resolve(),
        review_methodology_dir=(project_root / merged["review_methodology_dir"]).resolve(),
        review_format_dir=(project_root / merged["review_format_dir"]).resolve(),
        global_rules_path=(project_root / merged["global_rules"]).resolve(),
        platform_skills_path=(project_root / merged["platform_skills"]).resolve(),
        review_methodology_path=_optional("review_methodology"),
        review_format_path=_optional("review_format"),
        review_methodology_weights={str(k): int(v) for k, v in raw.get("review_methodology_weights", {}).items()},
        owner_email=merged["owner_email"],
        owner_name=merged["owner_name"],
        owner_password=merged["owner_password"],
        github_repo=merged["github_repo"],
    )


def write_default_config(path: Path) -> Path:
    """Write a default config.toml to *path* and return it."""
    path.mkdir(parents=True, exist_ok=True)
    config_file = path / CONFIG_FILENAME
    width = max(len(k) for k in DEFAULT_CONFIG)
    lines = [f'{k:<{width}s} = "{v}"' for k, v in DEFAULT_CONFIG.items()]
    config_file.write_text("\n".join(lines) + "\n")
    return config_file
