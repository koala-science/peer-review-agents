"""Assemble an agent's compiled system prompt.

The agent prompt is the concatenation of three hand-authored files:
GLOBAL_RULES.md, platform_skills.md, and the agent's own system_prompt.md.
`{KOALA_BASE_URL}` tokens anywhere in the text are substituted.
"""

from pathlib import Path

from reva.env import koala_base_url

SECTION_SEPARATOR = "\n\n---\n\n"


def assemble_prompt(
    *,
    global_rules_path: Path,
    platform_skills_path: Path,
    agent_prompt_path: Path,
) -> str:
    sections = [
        global_rules_path.read_text(encoding="utf-8").strip(),
        platform_skills_path.read_text(encoding="utf-8").strip(),
        agent_prompt_path.read_text(encoding="utf-8").strip(),
    ]
    joined = SECTION_SEPARATOR.join(sections)
    return joined.replace("{KOALA_BASE_URL}", koala_base_url())
