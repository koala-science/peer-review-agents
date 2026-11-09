"""Claim-focused review spends calls on consequential, contextual arguments."""

import json
from pathlib import Path

import pytest

from koala_science import Agent, ModelRequest, ModelResponse
from koala_science.cli import initialize


def workspace(tmp_path: Path, *, calls: int = 10) -> tuple[Path, Path]:
    initialize(tmp_path)
    config = tmp_path / "agent.yaml"
    config.write_text(
        "schema_version: 1\nname: focused\ninstruction_file: instructions.md\n"
        "review_strategy: claims\nmax_claims: 2\n"
        "model:\n  provider: codex_cli\n  name: fake\n"
        f"limits:\n  max_model_calls: {calls}\n  max_tasks: 12\n"
        "  max_candidates_per_task: 1\n  max_input_tokens_per_call: 65536\n",
        encoding="utf-8",
    )
    paper = tmp_path / "paper.md"
    paper.write_text(
        "# Claim\nArchitecture A is better than B.\n"
        "# Methods\nA trained for 40 epochs; B trained for 10.\n"
        "# Appendix\nNo matched-duration comparison was performed.\n",
        encoding="utf-8",
    )
    return config, paper


class FocusedProvider:
    def __init__(
        self,
        *,
        importance: str = "substantive",
        novelty: str = "new",
        defense: bool = True,
    ) -> None:
        self.requests: list[dict] = []
        self.importance = importance
        self.novelty = novelty
        self.defense = defense

    async def generate(self, request: ModelRequest) -> ModelResponse:
        data = json.loads(request.messages[-1].content)
        self.requests.append(data)
        if data["stage"] in {"claim_map", "claim_plan"}:
            spans = data["spans"]
            output = {
                "claims": [
                    {
                        "claim": "Architecture A is better.",
                        "why_it_matters": "The main architectural attribution depends on fair training.",
                        "span_ids": [s["id"] for s in spans],
                    }
                ]
            }
        elif data["stage"] == "proposal":
            span = next(s for s in data["spans"] if "40 epochs" in s["text"])
            output = {
                "candidates": [
                    {
                        "kind": "criticism",
                        "target": "architectural attribution",
                        "statement": "The comparison does not isolate architecture from training duration.",
                        "rationale": "The training budgets differ, so the observed gain cannot be attributed to architecture alone.",
                        "evidence": [
                            {
                                "source_id": span["source_id"],
                                "span_id": span["id"],
                                "page": span["page"],
                                "line_start": span["line_start"],
                                "line_end": span["line_end"],
                                "excerpt": span["text"],
                            }
                        ],
                        "limitations": [
                            "The measured accuracies can still be correct."
                        ],
                        "absence_scope": [],
                    }
                ]
            }
        elif data["stage"] == "evidence":
            output = {
                "decision": "supported",
                "atomic": True,
                "reason": "The quoted budgets differ.",
                "revision": None,
                "requested_span_ids": [],
                "importance": self.importance,
                "contribution": "Limits attribution of the main performance gain.",
                "strongest_counterargument": "The additional training may be intrinsic to the method.",
                "counterargument_resolved": self.defense,
                "novelty": self.novelty,
                "novelty_reason": "Compared the conclusion with the supplied public arguments.",
            }
        else:
            output = {"duplicate": False, "reason": "Distinct conclusion."}
        return ModelResponse(text=json.dumps(output), model="fake")


def test_claim_packet_links_methods_and_appendix_in_three_calls(tmp_path: Path) -> None:
    config, paper = workspace(tmp_path)
    provider = FocusedProvider()
    result = Agent.from_config(config, provider=provider).review(paper)
    assert result.status == "complete"
    assert [r["stage"] for r in provider.requests] == [
        "claim_map",
        "proposal",
        "evidence",
    ]
    assert len(result.arguments) == 1
    assert result.arguments[0].local_checks["importance"] == "passed"
    assert result.arguments[0].local_checks["platform_novelty"] == "not_checked"
    assert all(len(r["spans"]) == 6 for r in provider.requests)
    assert result.manifest["review"]["strategy"] == "claims"
    assert result.manifest["coverage"]["skipped_spans"] == []


@pytest.mark.parametrize("kwargs", [{"importance": "minor"}, {"defense": False}])
def test_supported_but_weak_arguments_are_not_accepted(
    tmp_path: Path, kwargs: dict
) -> None:
    config, paper = workspace(tmp_path)
    result = Agent.from_config(config, provider=FocusedProvider(**kwargs)).review(paper)
    assert result.status == "complete"
    assert result.arguments == []
    assert any(
        "Scientific importance" in d.get("rejected", "") for d in result.diagnostics
    )


def test_existing_platform_conclusion_is_rejected_before_selection(
    tmp_path: Path,
) -> None:
    config, paper = workspace(tmp_path)
    provider = FocusedProvider(novelty="duplicate")
    known = [
        {
            "id": "remote-1",
            "claim": "Unequal training prevents architectural attribution.",
            "position": "negative",
        }
    ]
    result = Agent.from_config(config, provider=provider).review(
        paper, known_arguments=known
    )
    assert result.arguments == []
    assert result.status == "complete"
    assert provider.requests[-1]["known_arguments"] == known
    assert result.manifest["review"]["known_arguments"] == known


def test_empty_claim_map_is_valid_without_proposal_calls(tmp_path: Path) -> None:
    config, paper = workspace(tmp_path)

    class Empty(FocusedProvider):
        async def generate(self, request: ModelRequest) -> ModelResponse:
            self.requests.append(json.loads(request.messages[-1].content))
            return ModelResponse(text='{"claims": []}', model="fake")

    provider = Empty()
    result = Agent.from_config(config, provider=provider).review(paper)
    assert result.status == "complete"
    assert result.arguments == []
    assert len(provider.requests) == 1


def test_unknown_claim_locators_fail_closed(tmp_path: Path) -> None:
    config, paper = workspace(tmp_path)

    class Invalid(FocusedProvider):
        async def generate(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(
                text=json.dumps(
                    {
                        "claims": [
                            {
                                "claim": "A is better.",
                                "why_it_matters": "Central claim.",
                                "span_ids": ["invented"],
                            }
                        ]
                    }
                ),
                model="fake",
            )

    result = Agent.from_config(config, provider=Invalid()).review(paper)
    assert result.arguments == []
    assert result.status != "complete"


def test_budget_exhaustion_never_accepts_unchecked_claim(tmp_path: Path) -> None:
    config, paper = workspace(tmp_path, calls=2)
    result = Agent.from_config(config, provider=FocusedProvider()).review(paper)
    assert result.status == "partial"
    assert result.arguments == []
    assert result.manifest["model_calls"] <= 2


def test_two_claims_need_only_six_calls(tmp_path: Path) -> None:
    config, paper = workspace(tmp_path)

    class Two(FocusedProvider):
        async def generate(self, request: ModelRequest) -> ModelResponse:
            response = await super().generate(request)
            stage = self.requests[-1]["stage"]
            output = json.loads(response.text)
            if stage == "claim_map":
                output["claims"].append(
                    {
                        **output["claims"][0],
                        "claim": "Budget matching changes the result.",
                    }
                )
            if (
                stage == "proposal"
                and sum(r["stage"] == "proposal" for r in self.requests) == 2
            ):
                output["candidates"][0]["statement"] = (
                    "The result may change when training budgets are matched."
                )
            return ModelResponse(text=json.dumps(output), model="fake")

    provider = Two()
    result = Agent.from_config(config, provider=provider).review(
        paper, known_arguments=[]
    )
    assert len(result.arguments) == 2
    assert result.manifest["model_calls"] == 6
    assert all(a.local_checks["platform_novelty"] == "passed" for a in result.arguments)


def test_multiple_mapping_packets_are_consolidated_before_proposal(
    tmp_path: Path,
) -> None:
    config, paper = workspace(tmp_path)
    with paper.open("a", encoding="utf-8") as handle:
        for index in range(20):
            handle.write(f"\nContext {index}: " + "Evidence detail. " * 95)
    provider = FocusedProvider()
    result = Agent.from_config(config, provider=provider).review(paper)
    stages = [r["stage"] for r in provider.requests]
    assert stages.count("claim_map") > 1
    assert "claim_plan" in stages
    assert stages.index("claim_plan") < stages.index("proposal")
    assert result.status == "complete"
    assert result.arguments
    assert result.manifest["coverage"]["skipped_spans"] == []


def test_oversized_evidence_is_partial_without_truncating(tmp_path: Path) -> None:
    config, paper = workspace(tmp_path)
    with paper.open("a", encoding="utf-8") as handle:
        for index in range(70):
            handle.write(f"\nContext {index}: " + "Evidence detail. " * 95)
    provider = FocusedProvider()
    result = Agent.from_config(config, provider=provider).review(paper)
    assert result.status == "partial"
    assert result.arguments == []
    assert all(r["stage"] == "claim_map" for r in provider.requests)
    assert any("Input exceeds" in d.get("error", "") for d in result.diagnostics)


def test_quality_check_can_request_cross_section_context(tmp_path: Path) -> None:
    config, paper = workspace(tmp_path)

    class MoreContext(FocusedProvider):
        async def generate(self, request: ModelRequest) -> ModelResponse:
            response = await super().generate(request)
            data = self.requests[-1]
            output = json.loads(response.text)
            if data["stage"] == "claim_map":
                output["claims"][0]["span_ids"] = [
                    s["id"] for s in data["spans"] if "Appendix" not in s["section"]
                ]
            if (
                data["stage"] == "evidence"
                and sum(r["stage"] == "evidence" for r in self.requests) == 1
            ):
                output["decision"] = "uncertain"
                output["requested_span_ids"] = [
                    s["id"] for s in data["source_index"] if s["section"] == "Appendix"
                ]
            return ModelResponse(text=json.dumps(output), model="fake")

    provider = MoreContext()
    result = Agent.from_config(config, provider=provider).review(paper)
    assert result.arguments
    checks = [r for r in provider.requests if r["stage"] == "evidence"]
    assert len(checks) == 2
    assert not any(s["section"] == "Appendix" for s in checks[0]["spans"])
    assert any(s["section"] == "Appendix" for s in checks[1]["spans"])


def test_unknown_novelty_with_supplied_snapshot_is_rejected(tmp_path: Path) -> None:
    config, paper = workspace(tmp_path)
    result = Agent.from_config(
        config, provider=FocusedProvider(novelty="uncertain")
    ).review(paper, known_arguments=[])
    assert result.arguments == []
