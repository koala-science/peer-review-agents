"""The quality bar: an argument is kept only if every check passes."""

import asyncio
import json

import pytest
from fakes import PAPER_LINES, ScriptedModel, agent_dir

from koala_science.config import load_config
from koala_science.runner import Reviewer
from koala_science.sources import read_source
from koala_science.types import PLATFORM_CHECKS


def review(tmp_path, model, *, verifier=None, known=None):
    loaded = load_config(agent_dir(tmp_path) / "agent.yaml")
    paper = tmp_path / "paper.md"
    paper.write_text("\n".join(PAPER_LINES) + "\n")
    providers = {"model": model, **({"verifier": verifier} if verifier else {})}
    return asyncio.run(
        Reviewer(loaded, providers).review(
            read_source(paper),
            paper={"id": "p1", "title": "A paper", "abstract": "About A."},
            known_arguments=known,
        )
    )


def test_argument_passing_every_check_is_kept(tmp_path):
    model = ScriptedModel()
    result = review(tmp_path, model)
    assert len(result.arguments) == 1
    checks = result.arguments[0].local_checks
    assert set(checks) == {"evidence_resolves", *PLATFORM_CHECKS, "self_duplicate"}
    assert set(checks.values()) == {"passed"}
    assert model.stages == ["claim_map", "proposal", "evidence"]


@pytest.mark.parametrize("name", PLATFORM_CHECKS)
def test_one_failed_check_drops_the_argument(tmp_path, name):
    result = review(tmp_path, ScriptedModel(fail={name}))
    assert result.arguments == []
    rejection = next(d for d in result.diagnostics if "rejected" in d)
    assert rejection["rejected"] == f"Failed platform checks: {name}"
    assert rejection["reasons"] == {name: f"{name} judged"}


def test_fixable_failure_gets_one_rewrite_through_the_full_bar(tmp_path):
    model = ScriptedModel(fail={"validity"}, revision="State the missing comparison.")
    result = review(tmp_path, model)
    assert model.stages == ["claim_map", "proposal", "evidence", "revision", "evidence"]
    assert len(result.arguments) == 1
    assert "equal-duration" in result.arguments[0].statement


def test_relevance_failure_is_not_rewritten(tmp_path):
    model = ScriptedModel(fail={"relevance"}, revision="Try again.")
    result = review(tmp_path, model)
    assert "revision" not in model.stages
    assert result.arguments == []


def test_invented_quote_never_reaches_the_verifier(tmp_path):
    model = ScriptedModel(excerpt="trained for 400 epochs")
    result = review(tmp_path, model)
    assert result.arguments == []
    assert "evidence" not in model.stages
    assert any(d.get("check") == "evidence_resolves" for d in result.diagnostics)


def test_existing_arguments_and_reviewer_instructions_reach_the_model(tmp_path):
    model = ScriptedModel()
    known = [{"id": "a1", "claim": "Existing point.", "position": "negative"}]
    review(tmp_path, model, known=known)
    request = model.requests[0]
    assert json.loads(request.messages[-1].content)["known_arguments"] == known
    system = request.messages[0].content
    assert "Reviewer instructions:" in system
    assert "training budget" in system  # from the repository's reviewer.md
    assert "verification: rejects evidence" in system


def test_verifier_model_judges_evidence(tmp_path):
    writer, judge = ScriptedModel(), ScriptedModel(fail={"verification"})
    result = review(tmp_path, writer, verifier=judge)
    assert writer.stages == ["claim_map", "proposal"]
    assert judge.stages == ["evidence"]
    assert result.arguments == []
