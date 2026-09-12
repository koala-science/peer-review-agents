"""A drift alarm on the shipped prompt files.

`agent_definition/` described a retired platform for five months because
nothing read it. This checks vocabulary and floors, not quality: a prompt can
pass here and still give bad advice. `platform_skills.md` is exempt — it defers
to the live guide instead of restating it, which is why it never rotted.
"""
import re
from pathlib import Path

import pytest

AGENT_DEFINITION = Path(__file__).resolve().parents[1] / "agent_definition"

GUARDED_FILES = ("GLOBAL_RULES.md", "default_system_prompt.md")

# Agent-facing surfaces outside `agent_definition/`: the launch prompt and the
# tool descriptions. Both carried retired vocabulary.
EXTRA_GUARDED = (
    Path(__file__).resolve().parents[1] / "cli" / "reva" / "config.py",
    Path(__file__).resolve().parents[1] / "agent_definition" / "harness" / "tools.py",
)

# Concepts the platform removed; the value says what to write instead. Keys must
# have no ordinary-English homograph — a bare "reviewed" was tried and removed,
# since `in_review` and `72-hour` pin the lifecycle without banning real prose.
RETIRED_VOCABULARY = {
    "karma": "points",
    "verdict": "arguments and their checks",
    "score band": "nothing — papers no longer carry a verdict score",
    "deliberating": "nothing — papers no longer have a review window",
    "in_review": "nothing — papers no longer have a lifecycle status",
    "72-hour": "nothing — papers are not on a clock",
    "strike": "nothing — moderation is a check, not a strike count",
    "github_file_url": "nothing — arguments carry no per-post link",
}


@pytest.mark.parametrize("filename", GUARDED_FILES)
@pytest.mark.parametrize("retired,replacement", RETIRED_VOCABULARY.items())
def test_prompts_do_not_use_retired_vocabulary(filename, retired, replacement):
    path = AGENT_DEFINITION / filename
    text = path.read_text(encoding="utf-8")
    found = re.search(rf"\b{re.escape(retired)}\w*", text, re.IGNORECASE)
    assert not found, (
        f"{filename} says {found.group(0)!r}, which the platform retired — "
        f"say {replacement} instead"
    )


@pytest.mark.parametrize("filename", GUARDED_FILES)
def test_prompts_describe_arguments(filename):
    """The positive half: retired vocabulary can be deleted without the
    replacement ever being written."""
    text = (AGENT_DEFINITION / filename).read_text(encoding="utf-8").lower()
    assert "argument" in text, (
        f"{filename} never mentions arguments, which are the only thing an "
        f"agent can submit"
    )


@pytest.mark.parametrize("path", EXTRA_GUARDED)
@pytest.mark.parametrize("retired,replacement", RETIRED_VOCABULARY.items())
def test_agent_facing_code_does_not_use_retired_vocabulary(path, retired, replacement):
    found = re.search(rf"\b{re.escape(retired)}\w*", path.read_text(encoding="utf-8"), re.IGNORECASE)
    assert not found, (
        f"{path.name} says {found.group(0)!r}, which the platform retired — "
        f"say {replacement} instead"
    )


# Banning `TODO` was not enough: two sentences naming "argument" passed.
REQUIRED_ANCHORS = ("claim", "position", "evidence", "relevance", "verification", "uniqueness")

# `assemble_prompt` gives `GLOBAL_RULES.md` to every agent, while
# `default_system_prompt.md` invites replacement — so the permanent file needs
# its own floor.
RULES_ANCHORS = (
    "moderation", "validity", "relevance", "uniqueness", "verification",
    "points", "pending", "accepted",
    # Each is the sole anchor for one section: the owner-authored bar,
    # information hygiene, and the definition of an argument.
    "authored", "citation counts",
    "claim", "position", "evidence", "immutable",
)


def test_the_starter_prompt_is_not_a_stub():
    """`reva create` copies this file verbatim into every new agent.

    It shipped as a `TODO:` placeholder, so the default agent every fork
    inherited had no reviewing instructions at all.
    """
    text = (AGENT_DEFINITION / "default_system_prompt.md").read_text(encoding="utf-8")
    assert "TODO" not in text, "default_system_prompt.md is still a placeholder"
    missing = [a for a in REQUIRED_ANCHORS if a not in text.lower()]
    assert not missing, (
        f"default_system_prompt.md never mentions {missing}; an agent starting "
        f"from it would not know what an argument is made of or what rejects one"
    )
    assert len(text) > 1500, (
        f"default_system_prompt.md is {len(text)} characters — too thin to be the "
        "working default every fork inherits"
    )


def test_the_shared_rules_still_carry_the_rules():
    """`assemble_prompt` gives this file to every agent, whatever its persona.

    Without a floor here, every substantive rule — the five checks, the cap, the
    points pool, the owner-authored bar — could be deleted and nothing failed.
    """
    text = (AGENT_DEFINITION / "GLOBAL_RULES.md").read_text(encoding="utf-8")
    missing = [a for a in RULES_ANCHORS if a not in text.lower()]
    assert not missing, (
        f"GLOBAL_RULES.md never mentions {missing}; it is the prompt every agent "
        f"receives, so a rule absent here is a rule no agent is told"
    )
    # Near the real content (~6.9k): at 2500, whole sections were deletable.
    assert len(text) > 6000, (
        f"GLOBAL_RULES.md is {len(text)} characters — too thin to carry the rules "
        "every agent is given"
    )
