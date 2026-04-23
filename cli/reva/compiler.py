"""Prompt compilation: assemble agent system prompts from component files."""

import json
from pathlib import Path

from reva.env import koala_base_url

SECTION_SEPARATOR = "\n\n---\n\n"


def persona_to_markdown(path: Path) -> str:
    """Convert a persona .json file to markdown. Pass-through for .md files."""
    if path.suffix != ".json":
        return path.read_text(encoding="utf-8")

    d = json.loads(path.read_text(encoding="utf-8"))
    lines = [f"## Persona: {d['name']}", f"\n{d['description']}"]

    traits = {k: v for k, v in d["trait_vector"].items() if v != 0}
    if traits:
        lines.append("\n### Traits")
        for trait, value in traits.items():
            definition = d.get("trait_definitions", {}).get(trait, "")
            direction = "High" if value == 1 else "Low"
            lines.append(f"- **{trait}** ({direction}): {definition}")

    if d.get("behavioral_rules"):
        lines.append("\n### Behavioral rules")
        lines.extend(f"- {r}" for r in d["behavioral_rules"])

    if d.get("forbidden_behaviors"):
        lines.append("\n### Do not")
        lines.extend(f"- {r}" for r in d["forbidden_behaviors"])

    return "\n".join(lines)


def compile_prompt(
    *,
    global_rules: str = "",
    platform_skills: str = "",
    role: str,
    review_methodology: str = "",
    review_format: str = "",
    interests: str,
    persona: str,
) -> str:
    """Assemble a full system prompt from component sections."""
    sections = [
        global_rules,
        platform_skills,
        role,
        review_methodology,
        interests,
        persona,
        review_format,
    ]
    joined = SECTION_SEPARATOR.join(s.strip() for s in sections if s and s.strip())
    return joined.replace("{KOALA_BASE_URL}", koala_base_url())


def interests_to_markdown(path: Path) -> str:
    """Wrap a research interests .md file with a section header."""
    content = path.read_text(encoding="utf-8").strip()
    return f"## Research Interests\n\n{content}"


def compile_agent_prompt(
    *,
    role_path: Path,
    persona_path: Path,
    interest_path: Path,
    global_rules_path: Path | None = None,
    platform_skills_path: Path | None = None,
    review_methodology_path: Path | None = None,
    review_format_path: Path | None = None,
) -> str:
    """High-level: read files and compile the full prompt."""

    def _read(p: Path | None) -> str:
        if p is None or not p.exists():
            return ""
        return p.read_text(encoding="utf-8")

    return compile_prompt(
        global_rules=_read(global_rules_path),
        platform_skills=_read(platform_skills_path),
        role=_read(role_path),
        review_methodology=_read(review_methodology_path),
        review_format=_read(review_format_path),
        interests=interests_to_markdown(interest_path),
        persona=persona_to_markdown(persona_path),
    )
