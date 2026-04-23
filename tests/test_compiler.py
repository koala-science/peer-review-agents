"""Tests for reva.compiler — prompt assembly and persona conversion."""
import json
from pathlib import Path

from reva.compiler import (
    SECTION_SEPARATOR,
    compile_agent_prompt,
    compile_prompt,
    persona_to_markdown,
)


def test_persona_to_markdown_from_md_passthrough(tmp_path):
    path = tmp_path / "persona.md"
    path.write_text("# Already markdown\n\nbody")
    assert persona_to_markdown(path) == "# Already markdown\n\nbody"


def test_persona_to_markdown_renders_json_fields(tmp_path):
    persona = {
        "name": "Alice",
        "description": "A careful reviewer.",
        "trait_vector": {"openness": 1, "neuroticism": -1, "agreeableness": 0},
        "trait_definitions": {
            "openness": "willing to engage with new ideas",
            "neuroticism": "emotional stability",
            "agreeableness": "",
        },
        "behavioral_rules": ["always cite sources", "be precise"],
        "forbidden_behaviors": ["personal attacks"],
    }
    path = tmp_path / "persona.json"
    path.write_text(json.dumps(persona))

    md = persona_to_markdown(path)

    assert "## Persona: Alice" in md
    assert "A careful reviewer." in md
    assert "### Traits" in md
    assert "openness" in md
    assert "(High)" in md  # openness = 1
    assert "(Low)" in md   # neuroticism = -1
    # agreeableness has value 0 and must be filtered out
    assert "agreeableness" not in md
    assert "### Behavioral rules" in md
    assert "always cite sources" in md
    assert "### Do not" in md
    assert "personal attacks" in md


def test_persona_to_markdown_skips_empty_sections(tmp_path):
    persona = {
        "name": "Bob",
        "description": "Minimal persona",
        "trait_vector": {"openness": 0, "neuroticism": 0},
        "trait_definitions": {},
    }
    path = tmp_path / "persona.json"
    path.write_text(json.dumps(persona))

    md = persona_to_markdown(path)
    assert "## Persona: Bob" in md
    assert "Minimal persona" in md
    # No traits should be listed (all zero)
    assert "### Traits" not in md
    assert "### Behavioral rules" not in md
    assert "### Do not" not in md


def test_compile_prompt_joins_with_section_separator():
    result = compile_prompt(
        global_rules="RULES",
        platform_skills="SKILLS",
        role="ROLE",
        review_methodology="METHOD",
        review_format="FORMAT",
        interests="INTERESTS",
        persona="PERSONA",
    )
    assert SECTION_SEPARATOR in result
    # All seven sections must appear in order
    assert result.index("RULES") < result.index("SKILLS")
    assert result.index("SKILLS") < result.index("ROLE")
    assert result.index("ROLE") < result.index("METHOD")
    assert result.index("METHOD") < result.index("INTERESTS")
    assert result.index("INTERESTS") < result.index("PERSONA")
    assert result.index("PERSONA") < result.index("FORMAT")


def test_compile_prompt_skips_empty_optional_sections():
    """Empty optional sections should not produce stray separators."""
    result = compile_prompt(
        global_rules="",
        platform_skills="",
        role="ROLE",
        review_methodology="",
        review_format="",
        interests="INTERESTS",
        persona="PERSONA",
    )
    # No consecutive separators
    assert SECTION_SEPARATOR + SECTION_SEPARATOR not in result
    assert "ROLE" in result
    assert "INTERESTS" in result
    assert "PERSONA" in result


def test_compile_prompt_strips_whitespace_from_sections():
    """Leading/trailing whitespace in a section shouldn't bleed into the
    section separators."""
    result = compile_prompt(
        role="  ROLE  \n\n",
        interests="\tINTERESTS\t",
        persona="PERSONA",
    )
    # Each section is stripped before joining
    assert "ROLE\n\n---" in result or "ROLE\n\n--" in result
    assert "INTERESTS" in result


def test_compile_prompt_substitutes_koala_base_url_default(tmp_path, monkeypatch):
    """`{KOALA_BASE_URL}` tokens in any source file are replaced by the
    accessor value in the compiled prompt."""
    monkeypatch.delenv("KOALA_BASE_URL", raising=False)

    global_rules = tmp_path / "GLOBAL_RULES.md"
    global_rules.write_text(
        "Fetch {KOALA_BASE_URL}/skill.md for onboarding.\n"
    )
    platform_skills = tmp_path / "platform_skills.md"
    platform_skills.write_text(
        "See {KOALA_BASE_URL}/skill.md for live docs.\n"
    )
    role = tmp_path / "role.md"
    role.write_text("Reviewer role.\n")
    interests = tmp_path / "interests.md"
    interests.write_text("- NLP\n")
    persona = tmp_path / "persona.json"
    persona.write_text(json.dumps({
        "name": "P",
        "description": "d",
        "trait_vector": {},
        "trait_definitions": {},
    }))

    result = compile_agent_prompt(
        role_path=role,
        persona_path=persona,
        interest_path=interests,
        global_rules_path=global_rules,
        platform_skills_path=platform_skills,
    )
    assert "{KOALA_BASE_URL}" not in result
    assert "https://koala.science/skill.md" in result


def test_compile_prompt_substitutes_koala_base_url_override(tmp_path, monkeypatch):
    monkeypatch.setenv("KOALA_BASE_URL", "https://staging.koala.science")

    global_rules = tmp_path / "GLOBAL_RULES.md"
    global_rules.write_text("Fetch {KOALA_BASE_URL}/skill.md\n")
    role = tmp_path / "role.md"
    role.write_text("Reviewer role.\n")
    interests = tmp_path / "interests.md"
    interests.write_text("- NLP\n")
    persona = tmp_path / "persona.json"
    persona.write_text(json.dumps({
        "name": "P",
        "description": "d",
        "trait_vector": {},
        "trait_definitions": {},
    }))

    result = compile_agent_prompt(
        role_path=role,
        persona_path=persona,
        interest_path=interests,
        global_rules_path=global_rules,
    )
    assert "{KOALA_BASE_URL}" not in result
    assert "https://staging.koala.science/skill.md" in result
    assert "https://koala.science/skill.md" not in result
