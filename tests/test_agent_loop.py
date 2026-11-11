"""The whole agent against an in-memory platform: select, review, submit, log."""

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import yaml
from fakes import ROOT, FakePlatform, ScriptedModel, agent_dir, iso, paper

from koala_science.audit import AuditLog, State
from koala_science.config import load_config
from koala_science.loop import AgentLoop
from koala_science.platform import PlatformClient


def run_agent(
    tmp_path, platform, model=None, *, dry_run=False, once=False, proxy=False, **rules
):
    root = agent_dir(tmp_path, **rules)
    if proxy:
        config = yaml.safe_load((root / "agent.yaml").read_text())
        config["model"] = yaml.safe_load((ROOT / "agent.yaml").read_text())["model"]
        (root / "agent.yaml").write_text(yaml.safe_dump(config))
    loaded = load_config(root / "agent.yaml")
    audit = AuditLog(root / "logs", dry_run=dry_run)
    state = State(root / "logs" / "state.json", readonly=dry_run)
    model = model or ScriptedModel()
    client = PlatformClient(
        "cs_test_key",
        origin="https://koala.test",
        transport=httpx.MockTransport(platform.handler),
        on_event=audit.call,
        sleep=lambda s: None,
    )
    now = [datetime.now(timezone.utc)]

    def sleep(seconds):
        now[0] += timedelta(seconds=seconds)

    loop = AgentLoop(
        loaded,
        client,
        {"model": model, "selector": model},
        audit,
        state,
        dry_run=dry_run,
        clock=lambda: now[0],
        sleep=sleep,
        say=lambda line: None,
    )
    reason = loop.run(once=once)
    return reason, audit, root, model


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_live_run_submits_and_records_everything(tmp_path):
    platform = FakePlatform([paper("p1")])
    reason, audit, root, _ = run_agent(tmp_path, platform, max_arguments=1)
    assert reason == "submitted 1 arguments (max_arguments)"
    [post] = platform.posts()
    assert post["paper_id"] == "p1"
    assert post["position"] == "negative"
    assert "confounded" in post["claim"]
    assert 'Page 1: "trained for 40 epochs' in post["evidence"]
    assert (
        "span" not in post["evidence"]
    )  # no internal identifiers leak to the platform
    state = json.loads((root / "logs" / "state.json").read_text())
    assert state["arguments"]["arg-1"]["paper_id"] == "p1"
    assert state["reviewed"]["p1"]["submitted"] == ["arg-1"]
    [submitted] = lines(root / "logs" / "arguments.jsonl")
    assert submitted["event"] == "submitted"
    assert submitted["budget_remaining"] == 49
    selection = lines(audit.run_dir / "selection.jsonl")[0]
    assert selection["ranked"] == [{"paper_id": "p1", "reason": "fits the strategy"}]
    calls = lines(audit.run_dir / "calls.jsonl")
    assert {c["kind"] for c in calls} == {"platform", "download"}
    assert not any("cs_test_key" in json.dumps(c) for c in calls)
    run = json.loads((audit.run_dir / "run.json").read_text())
    assert run["arguments_submitted"] == 1
    assert "Paper selection strategy" in run["strategy"]
    assert (audit.paper_dir("p1") / "review" / "arguments.md").exists()


def test_dry_run_posts_nothing_and_keeps_state(tmp_path):
    platform = FakePlatform([paper("p1")])
    reason, audit, root, _ = run_agent(tmp_path, platform, dry_run=True)
    assert reason == "no eligible papers fit the strategy"
    assert platform.posts() == []
    assert not (root / "logs" / "state.json").exists()
    assert not (root / "logs" / "arguments.jsonl").exists()
    [entry] = lines(audit.run_dir / "arguments.jsonl")
    assert entry["event"] == "dry_run"
    assert entry["payload"]["paper_id"] == "p1"


def test_hard_filters_run_before_the_model_ranks(tmp_path):
    platform = FakePlatform(
        [
            paper("fresh"),
            paper("old", created_at=iso(90)),
            paper("busy", argument_count=50),
            paper("nopdf", pdf_url=None),
        ]
    )
    _, audit, _, model = run_agent(tmp_path, platform, once=True)
    selection = lines(audit.run_dir / "selection.jsonl")[0]
    assert [p["id"] for p in selection["shortlist"]] == ["fresh"]
    assert selection["filtered"] == {
        "older than max_age_days": 1,
        "more arguments than max_existing_arguments": 1,
        "no PDF": 1,
    }
    ranking_request = json.loads(model.requests[0].messages[-1].content)
    assert [c["paper_id"] for c in ranking_request["candidates"]] == ["fresh"]
    assert "Paper selection strategy" in model.requests[0].messages[0].content


def test_papers_the_strategy_rejects_are_not_reviewed(tmp_path):
    platform = FakePlatform([paper("p1"), paper("p2")])
    _reason, audit, _, model = run_agent(
        tmp_path, platform, model=ScriptedModel(rank=["p2"])
    )
    assert model.stages.count("claim_map") == 1
    selection = lines(audit.run_dir / "selection.jsonl")[0]
    assert selection["not_selected"] == ["p1"]
    assert [p["paper_id"] for p in platform.posts()] == ["p2"]


def test_reviewed_papers_are_not_reviewed_again(tmp_path):
    platform = FakePlatform([paper("p1")])
    run_agent(tmp_path, platform, once=True)
    _, audit, _, model = run_agent(tmp_path, platform, once=True)
    assert lines(audit.run_dir / "selection.jsonl")[0]["filtered"] == {
        "already reviewed or skipped": 1
    }
    assert "claim_map" not in model.stages


def test_outcomes_are_recorded_including_moderation_withholding(tmp_path):
    platform = FakePlatform([paper("p1")])
    run_agent(tmp_path, platform, once=True)
    [argument] = platform.arguments["p1"]
    argument["state"] = "accepted"
    argument["checks"] = [{"name": "verification", "status": "passed"}]
    run_agent(tmp_path, platform, once=True)
    events = lines(tmp_path / "logs" / "arguments.jsonl")
    outcome = events[-1]
    assert outcome["event"] == "outcome"
    assert outcome["state"] == "accepted"
    state = json.loads((tmp_path / "logs" / "state.json").read_text())
    assert state["arguments"]["arg-1"]["state"] == "accepted"


def test_withheld_argument_is_recorded(tmp_path):
    platform = FakePlatform([paper("p1")])
    run_agent(tmp_path, platform, once=True)
    platform.arguments["p1"][0]["state"] = "withheld"
    run_agent(tmp_path, platform, once=True)
    assert lines(tmp_path / "logs" / "arguments.jsonl")[-1]["state"] == "withheld"


def test_empty_budget_stops_the_run(tmp_path):
    platform = FakePlatform([paper("p1"), paper("p2")])
    platform.post_status = [402]
    reason, *_ = run_agent(tmp_path, platform)
    assert reason == "owner budget is empty (HTTP 402)"
    assert len([r for r in platform.requests if r.method == "POST"]) == 1


def test_uncertain_submission_is_reconciled_not_repeated(tmp_path):
    platform = FakePlatform([paper("p1")])
    platform.post_status = [500]
    run_agent(tmp_path, platform, once=True)
    assert len([r for r in platform.requests if r.method == "POST"]) == 1
    events = [e["event"] for e in lines(tmp_path / "logs" / "arguments.jsonl")]
    assert events == ["submit_failed"]


def test_crash_after_post_is_reconciled_from_the_platform(tmp_path):
    platform = FakePlatform([paper("p1")])
    platform.arguments["p1"].append(
        {
            "id": "arg-9",
            "paper_id": "p1",
            "author_id": "agent-1",
            "state": "pending",
            "claim": "c",
            "position": "negative",
            "evidence": "e",
            "checks": [],
        }
    )
    _, _, root, _ = run_agent(tmp_path, platform, once=True)
    state = json.loads((root / "logs" / "state.json").read_text())
    assert "arg-9" in state["arguments"]
    # The reconciled argument uses one of p1's three slots.
    assert len(platform.posts()) == 1


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        ({"github_repo": None}, "no github_repo"),
        ({"budget": 3}, "at or below min_budget"),
    ],
)
def test_preconditions_stop_before_any_review(tmp_path, profile, expected):
    platform = FakePlatform([paper("p1")], **profile)
    reason, _, _, model = run_agent(tmp_path, platform)
    assert expected in reason
    assert model.stages == []
    assert platform.posts() == []


def test_idle_agent_sleeps_then_stops_at_deadline(tmp_path):
    deadline = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    platform = FakePlatform([])
    reason, *_ = run_agent(tmp_path, platform, when_idle="sleep", deadline=deadline)
    assert reason == "deadline reached"


def test_koala_model_credit_is_checked_when_using_the_proxy(tmp_path, monkeypatch):
    monkeypatch.setenv("KOALA_AGENT_API_KEY", "cs_test_key")
    platform = FakePlatform([paper("p1")], model_credit_usd=0.1)
    reason, _, _, model = run_agent(tmp_path, platform, proxy=True)
    assert "model credit" in reason
    assert model.stages == []


def test_cli_dry_run_end_to_end(tmp_path, monkeypatch, capsys):
    from koala_science import cli

    platform = FakePlatform([paper("p1")])
    root = agent_dir(tmp_path)
    (root / "unused.py").write_text(
        "from fakes import ScriptedModel\n\ndef make():\n    return ScriptedModel()\n"
    )
    real = cli.PlatformClient
    monkeypatch.setattr(
        cli,
        "PlatformClient",
        lambda key, on_event: real(
            key,
            origin="https://koala.test",
            transport=httpx.MockTransport(platform.handler),
            on_event=on_event,
        ),
    )
    monkeypatch.setenv("KOALA_AGENT_API_KEY", "cs_test_key")
    assert cli.main(["--config", str(root / "agent.yaml"), "run", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "dry run: nothing is submitted" in out
    assert "1 argument(s) passed local checks; 1 would be submitted" in out
    assert platform.posts() == []
    [run_dir] = (root / "logs" / "runs").iterdir()
    models = [c for c in lines(run_dir / "calls.jsonl") if c["kind"] == "model"]
    assert [c["role"] for c in models][:2] == ["selector", "model"]
    assert all(c["response"] for c in models)


def test_refused_paper_gets_no_further_submissions(tmp_path):
    platform = FakePlatform([paper("p1")])
    platform.post_status = [403]
    model = ScriptedModel(claims=2)
    _, _, root, _ = run_agent(tmp_path, platform, model, once=True)
    assert len([r for r in platform.requests if r.method == "POST"]) == 1
    state = json.loads((root / "logs" / "state.json").read_text())
    assert state["reviewed"]["p1"]["passed_local_checks"] == 2


def test_too_long_paper_is_skipped_and_not_retried(tmp_path, monkeypatch):
    from koala_science import runner

    monkeypatch.setattr(runner, "PROMPT_ALLOWANCE", 10_000_000)
    platform = FakePlatform([paper("p1")])
    _, _, root, model = run_agent(tmp_path, platform, once=True)
    state = json.loads((root / "logs" / "state.json").read_text())
    assert "max_input_tokens_per_call" in state["skipped"]["p1"]["reason"]
    assert model.stages == ["rank"]
    assert platform.posts() == []
