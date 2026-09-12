"""A drift alarm on the shipped prompt files.

`agent_definition/` sat for five months describing a platform that no longer
existed — karma, verdicts, score bands, comment threads, a 72-hour paper
lifecycle — because nothing here read it. Every fork started from that.

What this checks is narrow and worth being honest about: that the prompts do
not use vocabulary the platform has retired. It cannot tell whether they give
good advice, and a prompt can be accurate in vocabulary and wrong in substance.
It exists to make the *next* rename loud rather than silent.

`platform_skills.md` is exempt by design — it deliberately says almost nothing
and defers to the live guide at `{KOALA_BASE_URL}/skill.md`, which is why it is
the one file that survived the rewrite intact.
"""
import re
from pathlib import Path

import pytest

AGENT_DEFINITION = Path(__file__).resolve().parents[1] / "agent_definition"

GUARDED_FILES = ("GLOBAL_RULES.md", "default_system_prompt.md")

# Two more surfaces an agent reads, neither of them in `agent_definition/`:
# the message every backend is launched with, and the tool descriptions the
# model sees. Both carried retired vocabulary before this was written.
EXTRA_GUARDED = (
    Path(__file__).resolve().parents[1] / "cli" / "reva" / "config.py",
    Path(__file__).resolve().parents[1] / "agent_definition" / "harness" / "tools.py",
)

# Concepts the platform removed. The replacement names what to say instead, so
# a failure reads as an instruction rather than a scolding.
#
# Every key here is a token with no ordinary-English homograph. A bare
# "reviewed" was tried and removed: it is correct English about a real concern
# ("a paper you have already reviewed"), and `in_review` and `72-hour` pin the
# retired lifecycle unambiguously without it.
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


# What a usable starter prompt has to tell an agent. Banning the word `TODO`
# was not enough: the whole file could be replaced with two sentences naming
# "argument" and the guard stayed green.
REQUIRED_ANCHORS = ("claim", "position", "evidence", "relevance", "verification", "uniqueness")

# `GLOBAL_RULES.md` is injected into every agent unconditionally by
# `assemble_prompt`, while `default_system_prompt.md` invites the author to
# replace it. Guarding only the replaceable one left the permanent one
# reducible to a single sentence with the suite still green.
RULES_ANCHORS = (
    "moderation", "validity", "relevance", "uniqueness", "verification",
    "points", "pending", "accepted",
    # Rules with no other foothold in the file. Without them the sections could
    # be deleted while every anchor above still matched elsewhere: the 403 for
    # arguing about your owner's paper, the bar on judging a paper by how it was
    # received, and — the worst of them — the definition of what an argument is
    # and what its three fields are.
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
    # Near the real content (~6.9k), not a third of it: at 2500 the two
    # unanchored sections could both be deleted with the suite still green.
    assert len(text) > 6000, (
        f"GLOBAL_RULES.md is {len(text)} characters — too thin to carry the rules "
        "every agent is given"
    )
