"""The quality bar: an argument is kept only if every check passes."""

import asyncio
import json

import pytest
import yaml
from fakes import PAPER_LINES, ScriptedModel, agent_dir

from koala_science.config import load_config
from koala_science.runner import Reviewer
from koala_science.sources import read_source
from koala_science.types import PLATFORM_CHECKS


def review(tmp_path, model, *, verifier=None, known=None, search=None, **settings):
    root = agent_dir(tmp_path)
    if settings:
        config = yaml.safe_load((root / "agent.yaml").read_text())
        config["review"].update(settings)
        (root / "agent.yaml").write_text(yaml.safe_dump(config))
    loaded = load_config(root / "agent.yaml")
    paper = tmp_path / "paper.md"
    paper.write_text("\n".join(PAPER_LINES) + "\n")
    providers = {"model": model, **({"verifier": verifier} if verifier else {})}
    return asyncio.run(
        Reviewer(loaded, providers, search=search).review(
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


@pytest.mark.parametrize("name", ["moderation", "relevance", "uniqueness"])
def test_failure_on_the_idea_drops_the_argument_without_repair(tmp_path, name):
    model = ScriptedModel(fail={name}, revision="Try again.")
    result = review(tmp_path, model)
    assert result.arguments == []
    assert "revision" not in model.stages
    rejection = next(d for d in result.diagnostics if "rejected" in d)
    assert rejection["rejected"] == f"Failed platform checks: {name}"
    assert rejection["reasons"] == {name: f"{name} judged"}


@pytest.mark.parametrize("name", ["validity", "verification"])
def test_fixable_failure_is_repaired_and_rechecked(tmp_path, name):
    model = ScriptedModel(fail={name})
    result = review(tmp_path, model)
    assert model.stages == ["claim_map", "proposal", "evidence", "revision", "evidence"]
    assert len(result.arguments) == 1
    feedback = json.loads(
        json.loads(model.requests[3].messages[-1].content)["guidance"]
    )
    assert feedback["failed_checks"] == {name: f"{name} judged"}


def test_repairs_stop_at_max_revisions(tmp_path):
    model = ScriptedModel(fail={"validity"}, stubborn=True)
    result = review(tmp_path, model)
    assert model.stages.count("revision") == 2  # review.max_revisions
    assert result.arguments == []
    assert any(
        d.get("reason") == "No revisions left for this candidate"
        for d in result.diagnostics
    )


def test_bad_quote_is_repaired_before_the_verifier_is_asked(tmp_path):
    model = ScriptedModel(bad_quotes=1)
    result = review(tmp_path, model)
    assert model.stages == ["claim_map", "proposal", "revision", "evidence"]
    assert len(result.arguments) == 1
    feedback = json.loads(
        json.loads(model.requests[2].messages[-1].content)["guidance"]
    )
    [problem] = feedback["quote_failures"]
    assert problem["problem"] == "quote is not verbatim in the paper text"
    assert "40 epochs" in problem["closest_paper_text"]["text"]


def test_invented_quote_never_reaches_the_verifier(tmp_path):
    model = ScriptedModel(excerpt="trained for 400 epochs")
    result = review(tmp_path, model)
    assert result.arguments == []
    assert "evidence" not in model.stages
    assert model.stages.count("revision") == 2
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
    writer = ScriptedModel()
    judge = ScriptedModel(fail={"verification"}, stubborn=True)
    result = review(tmp_path, writer, verifier=judge)
    assert writer.stages == ["claim_map", "proposal", "revision", "revision"]
    assert judge.stages == ["evidence", "evidence", "evidence"]
    assert result.arguments == []


def test_model_output_schemas_avoid_array_bounds_gemini_rejects():
    """Gemini refused ClaimMap while span_ids had maxItems 512; keep array bounds small."""
    from koala_science.types import (
        ClaimMap,
        Duplicate,
        Proposals,
        QualityVerdict,
        Ranking,
    )

    def max_items(node):
        if isinstance(node, dict):
            if "maxItems" in node:
                yield node["maxItems"]
            for value in node.values():
                yield from max_items(value)
        elif isinstance(node, list):
            for value in node:
                yield from max_items(value)

    for model in (ClaimMap, Proposals, QualityVerdict, Duplicate, Ranking):
        assert all(n <= 100 for n in max_items(model.model_json_schema())), model


def test_every_call_repeats_one_paper_prefix_for_caching(tmp_path):
    """System prompt + paper must be byte-identical across a paper's calls."""
    model = ScriptedModel(fail={"validity"})  # adds revision and a second check
    review(tmp_path, model)
    assert model.stages == ["claim_map", "proposal", "evidence", "revision", "evidence"]
    systems = {r.messages[0].content for r in model.requests}
    assert len(systems) == 1
    users = [r.messages[-1].content for r in model.requests]
    cut = users[0].index('"stage"')
    prefix = users[0][:cut]
    assert all(u.startswith(prefix) for u in users)
    assert all(r.cache_prefix_chars == cut for r in model.requests)
    head = json.loads(users[0])
    assert list(head)[:4] == [
        "paper",
        "paper_text",
        "known_arguments",
        "names_to_describe",
    ]
    assert len(head["paper_text"]) == 3  # the whole paper, every call
    # Nothing that varies per call may precede the paper text.
    assert '"guidance"' not in prefix and '"task"' not in prefix


def test_only_the_top_claims_are_examined(tmp_path):
    model = ScriptedModel(claims=5)
    review(tmp_path, model)
    assert model.stages.count("proposal") == 2  # review.max_claims


def test_names_to_describe_reach_proposal_and_verifier(tmp_path):
    from koala_science.runner import names_to_describe

    assert names_to_describe(
        "EchoMoE: Efficient Expert Parallelism",
        "We compress Mixture-of-Experts (MoE) traffic in vLLM on GPUs for LLM serving.",
    ) == ["EchoMoE", "MoE", "vLLM", "LLM"]
    model = ScriptedModel()
    loaded = load_config(agent_dir(tmp_path) / "agent.yaml")
    paper = tmp_path / "paper.md"
    paper.write_text("\n".join(PAPER_LINES) + "\n")
    asyncio.run(
        Reviewer(loaded, {"model": model}).review(
            read_source(paper), paper={"title": "EchoMoE", "abstract": "A MoE system."}
        )
    )
    for request in model.requests:
        assert json.loads(request.messages[-1].content)["names_to_describe"] == [
            "EchoMoE",
            "MoE",
        ]


def test_paper_too_long_for_one_call_is_refused_before_any_call(tmp_path):
    from koala_science.runner import PaperTooLong

    root = agent_dir(tmp_path)
    loaded = load_config(root / "agent.yaml")
    loaded.config.review.limits.max_input_tokens_per_call = 1000
    paper = tmp_path / "paper.md"
    paper.write_text("\n".join(PAPER_LINES) + "\n")
    model = ScriptedModel()
    with pytest.raises(PaperTooLong):
        asyncio.run(Reviewer(loaded, {"model": model}).review(read_source(paper)))
    assert model.requests == []


@pytest.mark.parametrize(
    ("page", "excerpt", "ok"),
    [
        ("the isolated perfor- mance drops", "the isolated performance drops", True),
        ("Across the25configurations with", "Across the 25 configurations with", True),
        ("a larger w u·z produces", "a larger w u'z produces", True),
        ("first chunk ends here", "first chunk ends here and the next", True),
        ("reports 81.2 accuracy", "reports 82.1 accuracy", False),
        ("the gain disappears", "the gain persists", False),
        ("The three arms sit inside", "Table 24: The three arms sit inside", False),
    ],
)
def test_quote_check_tolerates_extraction_noise_not_different_words(page, excerpt, ok):
    from koala_science.sources import check_evidence
    from koala_science.types import Candidate, Span

    spans = {
        "s:p1:0": Span(id="s:p1:0", source_id="s", text=page, page=1),
        "s:p1:1": Span(id="s:p1:1", source_id="s", text="and the next", page=1),
    }
    candidate = Candidate(
        kind="criticism",
        target="t",
        statement="s",
        rationale="r",
        evidence=[
            {"source_id": "s", "span_id": "s:p1:0", "page": 1, "excerpt": excerpt}
        ],
    )
    assert (check_evidence(candidate, spans, set(spans)) is None) is ok


class FakeSearch:
    def __init__(self, fail=False):
        self.queries, self.fail = [], fail

    async def __call__(self, query):
        self.queries.append(query)
        if self.fail:
            raise RuntimeError("secret upstream text")
        return [{"title": f"Prior work on {query}", "year": 2024}]


def test_model_can_search_before_proposing_and_sees_the_results(tmp_path):
    model = ScriptedModel(searches={"proposal": ["epoch-matched baselines"]})
    search = FakeSearch()
    result = review(tmp_path, model, search=search)
    assert search.queries == ["epoch-matched baselines"]
    assert model.stages == ["claim_map", "proposal", "proposal", "evidence"]
    first, second = (json.loads(r.messages[-1].content) for r in model.requests[1:3])
    assert first["literature"] == [] and first["searches_left"] == 4
    assert second["searches_left"] == 3
    assert second["literature"] == [
        {
            "query": "epoch-matched baselines",
            "results": [
                {"title": "Prior work on epoch-matched baselines", "year": 2024}
            ],
        }
    ]
    # The verifier sees what the proposer found.
    assert json.loads(model.requests[3].messages[-1].content)["literature"]
    assert len(result.arguments) == 1
    assert result.manifest["review"]["literature"] == second["literature"]
    assert {
        "search": "epoch-matched baselines",
        "results": 1,
        "error": None,
    }.items() <= next(d for d in result.diagnostics if "search" in d).items()


def test_searches_stop_at_the_per_paper_limit(tmp_path):
    model = ScriptedModel(searches={"proposal": ["a", "b", "c"], "evidence": ["d"]})
    search = FakeSearch()
    result = review(tmp_path, model, search=search, max_searches=2)
    assert search.queries == ["a", "b"]
    # The third request is answered as is: no searches left, no candidate.
    assert model.stages == ["claim_map", "proposal", "proposal", "proposal"]
    assert json.loads(model.requests[-1].messages[-1].content)["searches_left"] == 0
    assert result.arguments == []


def test_claim_map_cannot_search(tmp_path):
    model = ScriptedModel()
    review(tmp_path, model, search=FakeSearch())
    assert json.loads(model.requests[0].messages[-1].content)["searches_left"] == 0


def test_failed_search_is_reported_to_the_model_without_details(tmp_path):
    model = ScriptedModel(searches={"proposal": ["anything"]})
    result = review(tmp_path, model, search=FakeSearch(fail=True))
    later = json.loads(model.requests[2].messages[-1].content)
    assert later["literature"] == [
        {"query": "anything", "error": "Literature search failed"}
    ]
    assert "secret" not in json.dumps(result.manifest)
    assert len(result.arguments) == 1
