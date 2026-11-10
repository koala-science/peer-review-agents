"""Empty reports distinguish no proposals from rejected proposals."""

from koala_science.output import markdown
from koala_science.types import ReviewResult


def result(tasks: list[dict]) -> ReviewResult:
    return ReviewResult(
        run_id="test",
        status="complete",
        paper={"name": "paper.pdf"},
        arguments=[],
        sources=[],
        diagnostics=[],
        manifest={"tasks": tasks, "model_calls": 5, "elapsed_seconds": 126.4},
    )


def test_empty_proposals_are_not_described_as_rejections() -> None:
    report = markdown(
        result(
            [
                {
                    "task": {"role": "proposal"},
                    "status": "complete",
                    "output": {"candidates": []},
                },
                {
                    "task": {"role": "proposal"},
                    "status": "complete",
                    "output": {"candidates": []},
                },
            ]
        )
    )
    assert "No candidates were proposed in 2 completed proposal tasks" in report
    assert "No arguments passed" not in report
    assert "5 model calls" in report and "126.4 seconds" in report
    assert "does not mean the paper has no weaknesses" in report


def test_rejected_candidates_are_distinct() -> None:
    report = markdown(
        result(
            [
                {
                    "task": {"role": "proposal"},
                    "status": "complete",
                    "output": {"candidates": [{}]},
                },
            ]
        )
    )
    assert "1 candidate(s) were proposed; none passed all local checks" in report
    assert "diagnostics.json" in report


def test_no_proposal_tasks_does_not_claim_rejection() -> None:
    report = markdown(result([]))
    assert "No proposal tasks completed" in report
    assert "manifest.json" in report
