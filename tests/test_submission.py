"""Submission uses mock HTTP exclusively; no platform mutations."""

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from koala_science.platform import PlatformClient, PlatformError, arxiv_identity
from koala_science.workspace import PaperWorkspace


def paper(
    pid: str = "11111111-1111-4111-8111-111111111111", version: str = "v1"
) -> dict:
    return {
        "id": pid,
        "arxiv_id": "2607.29592",
        "title": "TOOD",
        "pdf_url": f"https://arxiv.org/pdf/2607.29592{version}",
    }


def client(handler: Callable[[httpx.Request], httpx.Response]) -> PlatformClient:
    return PlatformClient(transport=httpx.MockTransport(handler))


def test_normalize_arxiv_versions() -> None:
    assert arxiv_identity("https://arxiv.org/abs/2607.29592v2") == ("2607.29592", 2)
    assert arxiv_identity("hep-th/9901001v1") == ("hep-th/9901001", 1)
    with pytest.raises(ValueError):
        arxiv_identity("https://evil.example/2607.29592")


def test_lookup_uses_listing_after_misleading_search() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/v1/papers/11111111-1111-4111-8111-111111111111":
            return httpx.Response(200, json=paper())
        if int(request.url.params.get("skip", 0)):
            return httpx.Response(200, json=[])
        if request.url.path == "/api/v1/search/":
            return httpx.Response(
                200,
                json=[{"paper": dict(paper(), arxiv_id="2607.11111", pdf_url=None)}],
            )
        return httpx.Response(200, json=[paper()])

    with client(handler) as api:
        assert (
            api.find_paper("2607.29592", "TOOD")["id"]
            == "11111111-1111-4111-8111-111111111111"
        )
    assert all(r.method == "GET" for r in requests)
    assert any(r.url.path == "/api/v1/papers/" for r in requests)


@pytest.mark.parametrize("status", [401, 403, 500])
def test_lookup_failure_is_not_absence(status: int) -> None:
    with client(lambda r: httpx.Response(status)) as api, pytest.raises(PlatformError):
        api.find_paper("2607.29592", "TOOD")


def test_ambiguous_identity_stops() -> None:
    with (
        client(
            lambda r: httpx.Response(
                200,
                json=[]
                if int(r.url.params.get("skip", 0))
                else [{"paper": paper()}, {"paper": paper("p2")}],
            )
        ) as api,
        pytest.raises(ValueError, match="Ambiguous"),
    ):
        api.find_paper("2607.29592", "TOOD")


def test_workspace_paths_and_strict_schema(tmp_path: Path) -> None:
    config = tmp_path / "paper.yaml"
    config.write_text(
        "schema_version: 1\nmanuscript: paper.md\nconfig: agent.yaml\nsources: [supp.md]\narxiv: 2607.29592v1\ntitle: TOOD\n"
    )
    workspace = PaperWorkspace.load(config)
    assert workspace.manuscript == tmp_path / "paper.md"
    assert workspace.sources == [tmp_path / "supp.md"]
    assert workspace.identity == ("2607.29592", 1)
    config.write_text(config.read_text() + "secret: no\n")
    with pytest.raises(ValueError):
        PaperWorkspace.load(config)


def test_failed_run_does_not_replace_last_usable(tmp_path: Path) -> None:
    (tmp_path / "paper.yaml").write_text("schema_version: 1\nmanuscript: paper.md\n")
    workspace = PaperWorkspace.load(tmp_path / "paper.yaml")
    workspace.record_run(tmp_path / "good", "complete")
    workspace.record_run(tmp_path / "bad", "failed")
    assert json.loads((tmp_path / ".koala/last-run.json").read_text())["run"] == str(
        tmp_path / "good"
    )


@pytest.fixture
def reviewed(tmp_path: Path) -> PaperWorkspace:
    from koala_science.sources import read_source
    from koala_science.types import Argument, Evidence, Provenance, ReviewResult

    (tmp_path / "paper.md").write_text("The experiment used five independent trials.\n")
    (tmp_path / "paper.yaml").write_text(
        "schema_version: 1\nmanuscript: paper.md\narxiv: 2607.29592v1\ntitle: TOOD\n"
    )
    source = read_source(tmp_path / "paper.md")
    span = source.spans[0]
    argument = Argument(
        id="a1",
        kind="praise",
        target="experiment",
        statement="Uses independent trials.",
        rationale="Repeated trials support the evaluation.",
        evidence=[
            Evidence(
                source_id=source.id,
                span_id=span.id,
                line_start=1,
                line_end=1,
                excerpt=span.text,
            )
        ],
        limitations=["Only five trials."],
        provenance=Provenance(
            agent_name="test", model="fake", prompt_digest="x", task_ids=[]
        ),
        local_checks={
            k: "passed"
            for k in (
                "schema",
                "source_resolution",
                "atomicity",
                "support",
                "duplicate",
            )
        },
    )
    result = ReviewResult(
        run_id="r1",
        paper={
            "id": source.id,
            "name": source.name,
            "content_hash": source.content_hash,
        },
        status="complete",
        arguments=[argument],
        sources=[source],
        manifest={
            "run_id": "r1",
            "status": "complete",
            "sources": {source.id: source.content_hash},
            "coverage": {
                "inspected_spans": [span.id],
                "skipped_spans": [],
                "extraction_gaps": {source.id: []},
            },
        },
    )
    result.save(tmp_path / "runs/one")
    workspace = PaperWorkspace.load(tmp_path / "paper.yaml")
    workspace.record_run(tmp_path / "runs/one", "complete")
    return workspace


class Server:
    def __init__(self, *, exists: bool = True) -> None:
        self.exists = exists
        self.calls = []
        self.arguments = []
        self.import_mode = "ok"
        self.argument_mode = "ok"
        self.version = "v1"
        self.allowance = 1

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path.removeprefix("/api/v1/")
        owner = request.headers.get("authorization") == "Bearer owner-secret"
        if path == "users/me":
            return httpx.Response(
                200,
                json={
                    "actor_type": "human" if owner else "agent",
                    "id": "agent1",
                    "github_repo": "https://github.com/example/audit",
                    "budget": 10,
                    "papers_available": self.allowance,
                },
            )
        if request.method == "POST" and path == "papers/arxiv":
            assert owner
            assert json.loads(request.content) == {
                "url": "https://arxiv.org/abs/2607.29592v1"
            }
            if self.import_mode == "timeout_absent":
                raise httpx.ReadTimeout("secret", request=request)
            self.exists = True
            if self.import_mode == "conflict":
                return httpx.Response(409)
            if self.import_mode == "timeout_created":
                raise httpx.ReadTimeout("secret", request=request)
            return httpx.Response(201, json=paper(version=self.version))
        if request.method == "POST" and path == "arguments/":
            assert request.headers["authorization"] == "Bearer agent-secret"
            if self.argument_mode == "fail":
                return httpx.Response(403)
            if self.argument_mode == "timeout_absent":
                raise httpx.ReadTimeout("secret", request=request)
            receipt = {
                **json.loads(request.content),
                "id": f"arg{len(self.arguments)}",
                "author_id": "agent1",
                "state": "pending",
            }
            self.arguments.append(receipt)
            if self.argument_mode == "timeout_created":
                raise httpx.ReadTimeout("secret", request=request)
            return httpx.Response(201, json=receipt)
        if path == "papers/11111111-1111-4111-8111-111111111111":
            return httpx.Response(200, json=paper(version=self.version))
        if int(request.url.params.get("skip", 0)):
            return httpx.Response(200, json=[])
        if path == "search/":
            return httpx.Response(
                200,
                json=[{"paper": paper(version=self.version)}] if self.exists else [],
            )
        if path == "papers/":
            return httpx.Response(
                200, json=[paper(version=self.version)] if self.exists else []
            )
        if path.endswith("/arguments"):
            return httpx.Response(200, json=self.arguments)
        raise AssertionError(path)


def install_server(
    monkeypatch: pytest.MonkeyPatch, server: Callable[[httpx.Request], httpx.Response]
) -> None:
    from koala_science import submission

    monkeypatch.setattr(submission, "PlatformClient", lambda: client(server))
    monkeypatch.setenv("KOALA_AGENT_API_KEY", "agent-secret")
    monkeypatch.setenv("KOALA_OWNER_ACCESS_TOKEN", "owner-secret")


@pytest.mark.parametrize("exists", [True, False])
def test_preview_never_posts(
    reviewed: PaperWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    exists: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from koala_science.submission import submit

    server = Server(exists=exists)
    install_server(monkeypatch, server)
    monkeypatch.delenv("KOALA_AGENT_API_KEY")
    monkeypatch.delenv("KOALA_OWNER_ACCESS_TOKEN")
    assert submit(reviewed, arguments=["1"]) == 0
    assert all(r.method == "GET" for r in server.calls)
    assert (reviewed.state / "selection.json").exists()
    exports = list((reviewed.state / "exports").glob("*/arguments.json"))
    assert bool(exports) == exists
    if exports:
        payload = json.loads(exports[0].read_text())[0]
        assert set(payload) == {"paper_id", "claim", "position", "evidence"}
        assert payload["paper_id"] == "11111111-1111-4111-8111-111111111111"
    output = capsys.readouterr().out
    assert "https://koala.science/dashboard" in output
    assert "KOALA_AGENT_API_KEY" in output
    assert "not verified" in output


@pytest.mark.parametrize("key", [None, "", "   "])
def test_send_missing_key_guides_setup_before_lookup(
    reviewed: PaperWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    key: str | None,
) -> None:
    from koala_science.cli import main

    server = Server(exists=False)
    install_server(monkeypatch, server)
    if key is None:
        monkeypatch.delenv("KOALA_AGENT_API_KEY")
    else:
        monkeypatch.setenv("KOALA_AGENT_API_KEY", key)
    assert (
        main(["submit", "--workspace", str(reviewed.path), "--argument", "1", "--send"])
        == 2
    )
    output = capsys.readouterr().err
    assert "https://koala.science/dashboard" in output
    assert "register" in output.lower()
    assert "KOALA_AGENT_API_KEY" in output
    assert "Read-Host" in output and "export KOALA_AGENT_API_KEY" in output
    assert server.calls == []


@pytest.mark.parametrize("send", [False, True])
@pytest.mark.parametrize("status", [401, 403])
def test_rejected_key_guides_setup_without_posting(
    reviewed: PaperWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    send: bool,
    status: int,
) -> None:
    from koala_science.cli import main

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.path == "/api/v1/users/me"
        assert request.headers["authorization"] == "Bearer agent-secret"
        return httpx.Response(
            status, json={"detail": "agent-secret must never be echoed"}
        )

    install_server(monkeypatch, handler)
    argv = ["submit", "--workspace", str(reviewed.path), "--argument", "1"]
    assert main(argv + (["--send"] if send else [])) == 3
    captured = capsys.readouterr()
    assert "https://koala.science/dashboard" in captured.err
    assert "KOALA_AGENT_API_KEY" in captured.err
    assert "agent-secret" not in captured.out + captured.err
    assert len(calls) == 1


@pytest.mark.parametrize(
    "profile",
    [
        {
            "actor_type": "human",
            "id": "human1",
            "github_repo": "https://github.com/example/repo",
        },
        {
            "actor_type": "agent",
            "id": "",
            "github_repo": "https://github.com/example/repo",
        },
        [],
    ],
)
def test_unregistered_or_wrong_actor_cannot_submit(
    reviewed: PaperWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    profile: dict | list,
) -> None:
    from koala_science.cli import main

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.path == "/api/v1/users/me"
        return httpx.Response(200, json=profile)

    install_server(monkeypatch, handler)
    assert (
        main(["submit", "--workspace", str(reviewed.path), "--argument", "1", "--send"])
        == 3
    )
    assert "registered agent" in capsys.readouterr().err
    assert len(calls) == 1


def test_valid_agent_checked_before_import(
    reviewed: PaperWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from koala_science.submission import submit

    server = Server(exists=False)
    install_server(monkeypatch, server)
    assert submit(reviewed, arguments=["1"], send=True) == 0
    assert server.calls[0].url.path == "/api/v1/users/me"
    assert server.calls[0].headers["authorization"] == "Bearer agent-secret"
    assert "Registered platform agent verified" in capsys.readouterr().out


def test_profile_outage_is_not_reported_as_missing_registration(
    reviewed: PaperWorkspace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from koala_science.cli import main

    install_server(monkeypatch, lambda request: httpx.Response(503))
    assert (
        main(["submit", "--workspace", str(reviewed.path), "--argument", "1", "--send"])
        == 3
    )
    output = capsys.readouterr().err
    assert "Could not verify" in output
    assert "register" not in output.lower()


def test_noninteractive_never_auto_selects(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    from koala_science.submission import submit

    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(ValueError, match="Noninteractive"):
        submit(reviewed)


def test_existing_needs_no_owner_and_deduplicates(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.submission import submit

    server = Server()
    install_server(monkeypatch, server)
    monkeypatch.delenv("KOALA_OWNER_ACCESS_TOKEN")
    assert submit(reviewed, arguments=["1"], send=True) == 0
    assert submit(reviewed, send=True) == 0
    assert len([r for r in server.calls if r.method == "POST"]) == 1
    assert len(server.arguments) == 1
    payloads = list((reviewed.state / "exports").glob("*/arguments.json"))
    sent = next(json.loads(r.content) for r in server.calls if r.method == "POST")
    assert json.loads(payloads[0].read_text()) == [sent]


@pytest.mark.parametrize("mode", ["ok", "conflict", "timeout_created"])
def test_import_receipt_precedes_argument(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    from koala_science.submission import submit

    server = Server(exists=False)
    server.import_mode = mode
    install_server(monkeypatch, server)
    assert submit(reviewed, arguments=["1"], send=True) == 0
    events = [
        json.loads(line)
        for line in (reviewed.state / "delivery.jsonl").read_text().splitlines()
    ]
    receipt = next(
        i
        for i, e in enumerate(events)
        if e["key"].startswith("import:") and e["status"] == "receipt"
    )
    intent = next(
        i
        for i, e in enumerate(events)
        if e["key"].startswith("argument:") and e["status"] == "intent"
    )
    assert receipt < intent
    assert (
        len(
            [
                r
                for r in server.calls
                if r.method == "POST" and r.url.path.endswith("arxiv")
            ]
        )
        == 1
    )
    assert "secret" not in (reviewed.state / "delivery.jsonl").read_text()


def test_uncertain_import_never_reposts(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.submission import submit

    server = Server(exists=False)
    server.import_mode = "timeout_absent"
    install_server(monkeypatch, server)
    for _ in range(2):
        with pytest.raises(PlatformError) as error:
            submit(reviewed, arguments=["1"], send=True)
        assert error.value.uncertain
    assert len([r for r in server.calls if r.method == "POST"]) == 1


@pytest.mark.parametrize("mode", ["timeout_absent", "timeout_created"])
def test_uncertain_argument_reconciliation(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    from koala_science.submission import submit

    server = Server()
    server.argument_mode = mode
    install_server(monkeypatch, server)
    expected = 4 if mode == "timeout_absent" else 0
    assert submit(reviewed, arguments=["1"], send=True) == expected
    assert submit(reviewed, send=True) == expected
    assert len([r for r in server.calls if r.method == "POST"]) == 1


def test_import_allowance_and_missing_owner(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.submission import submit

    server = Server(exists=False)
    install_server(monkeypatch, server)
    server.allowance = 0
    with pytest.raises(PlatformError, match="allowance"):
        submit(reviewed, arguments=["1"], send=True)
    monkeypatch.delenv("KOALA_OWNER_ACCESS_TOKEN")
    with pytest.raises(ValueError, match="KOALA_OWNER_ACCESS_TOKEN"):
        submit(reviewed, send=True)
    assert all(r.method == "GET" for r in server.calls)


@pytest.mark.parametrize("version", ["v2", ""])
def test_version_guard(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    from koala_science.submission import submit

    server = Server()
    server.version = version
    install_server(monkeypatch, server)
    with pytest.raises(ValueError, match="version"):
        submit(reviewed, arguments=["1"], send=True)
    if not version:
        assert submit(reviewed, send=True, confirm_version=True) == 0
    assert not any(r.method == "POST" for r in server.calls) if version else True


@pytest.mark.parametrize("changed", ["manuscript", "arguments", "selection", "sources"])
def test_changed_artifacts_rejected(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch, changed: str
) -> None:
    from koala_science.submission import submit

    server = Server()
    install_server(monkeypatch, server)
    submit(reviewed, arguments=["1"])
    path = {
        "manuscript": reviewed.manuscript,
        "arguments": reviewed.last_run() / "arguments.json",
        "selection": reviewed.state / "selection.json",
        "sources": reviewed.last_run() / "sources.json",
    }[changed]
    if changed == "manuscript":
        path.write_text("Changed paper")
    else:
        value = json.loads(path.read_text())
        if changed == "arguments":
            value["arguments"][0]["statement"] = "Changed statement"
        elif changed == "selection":
            value["argument_ids"] = ["other"]
        else:
            value[0]["spans"][0]["text"] = "Changed source"
        path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        submit(reviewed, send=True)
    assert all(r.method == "GET" for r in server.calls)


def test_partial_acknowledgment_is_pinned(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.submission import submit

    server = Server()
    install_server(monkeypatch, server)
    for filename in ("arguments.json", "manifest.json"):
        path = reviewed.last_run() / filename
        data = json.loads(path.read_text())
        data["status"] = "partial"
        path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="allow-partial"):
        submit(reviewed, arguments=["1"])
    assert submit(reviewed, arguments=["1"], allow_partial=True) == 0
    assert submit(reviewed, send=True) == 0


def test_new_review_does_not_replace_selection(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.submission import submit

    server = Server()
    install_server(monkeypatch, server)
    assert submit(reviewed, arguments=["1"]) == 0
    reviewed.record_run(reviewed.root / "new-missing-run", "complete")
    assert submit(reviewed) == 0
    saved = json.loads((reviewed.state / "selection.json").read_text())
    assert saved["run_id"] == "r1"


def test_pagination_exhaustion_and_failure() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("skip", 0))
        calls.append(offset)
        return httpx.Response(
            200, json=[{"id": str(i)} for i in range(offset, min(offset + 100, 150))]
        )

    with client(handler) as api:
        assert len(api.pages("papers/")) == 150
    assert calls == [0, 100, 150]
    with (
        client(lambda r: httpx.Response(200, json=[{"id": "same"}])) as api,
        pytest.raises(PlatformError, match="pagination"),
    ):
        api.pages("papers/")


def test_preview_pins_discovered_target(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.submission import submit

    install_server(monkeypatch, Server())
    submit(reviewed, arguments=["1"])
    saved = json.loads((reviewed.state / "selection.json").read_text())
    assert (
        saved["target"]["platform_paper_id"] == "11111111-1111-4111-8111-111111111111"
    )


def test_oversized_payload_rejected_without_truncation(
    reviewed: PaperWorkspace,
) -> None:
    from koala_science.submission import prepare

    path = reviewed.last_run() / "arguments.json"
    data = json.loads(path.read_text())
    data["arguments"][0]["rationale"] = "a" * 10001
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="10,000"):
        prepare(
            reviewed,
            run=None,
            arguments=["1"],
            select=False,
            allow_partial=False,
            confirm_version=False,
        )


def test_imported_version_mismatch_preserves_receipt(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.submission import submit

    server = Server(exists=False)
    server.version = "v2"
    install_server(monkeypatch, server)
    with pytest.raises(ValueError, match="version"):
        submit(reviewed, arguments=["1"], send=True)
    assert len(server.arguments) == 0
    assert any(
        e["status"] == "receipt"
        for e in map(
            json.loads, (reviewed.state / "delivery.jsonl").read_text().splitlines()
        )
    )


def test_partial_submission_recovers_without_reposting(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.submission import submit

    path = reviewed.last_run() / "arguments.json"
    data = json.loads(path.read_text())
    second = dict(
        data["arguments"][0], id="a2", statement="A second supported observation."
    )
    data["arguments"].append(second)
    path.write_text(json.dumps(data))
    server = Server()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("arguments/"):
            server.argument_mode = "fail" if server.arguments else "ok"
        return server(request)

    install_server(monkeypatch, handler)
    assert submit(reviewed, arguments=["1", "2"], send=True) == 4
    install_server(monkeypatch, server)
    server.argument_mode = "ok"
    assert submit(reviewed, send=True) == 0
    assert len(server.arguments) == 2


def test_cli_no_argument_review_uses_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.cli import initialize, main

    initialize(tmp_path)
    (tmp_path / "empty.py").write_text(
        'from koala_science import ModelResponse\nclass Empty:\n async def generate(self, request):\n  return ModelResponse(text=\'{"candidates": []}\', model="fake")\ndef build():\n return Empty()\n'
    )
    (tmp_path / "agent.yaml").write_text(
        "schema_version: 1\nname: smoke\ninstruction_file: instructions.md\nmodel:\n  provider: custom\n  name: fake\n  factory: empty.py:build\n"
    )
    monkeypatch.chdir(tmp_path)
    assert main(["validate"]) == 0
    assert main(["review"]) == 0
    first = json.loads((tmp_path / ".koala/last-run.json").read_text())["run"]
    assert main(["review"]) == 0
    assert json.loads((tmp_path / ".koala/last-run.json").read_text())["run"] != first
    monkeypatch.chdir(tmp_path.parent)
    assert (
        main(
            [
                "review",
                "--workspace",
                str(tmp_path / "paper.yaml"),
                "--output",
                "chosen",
            ]
        )
        == 0
    )
    assert (tmp_path / "chosen/manifest.json").exists()


def test_argument_reconcile_lookup_failure_is_unresolved(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.submission import submit

    server = Server()
    server.argument_mode = "timeout_absent"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/arguments") and any(
            r.method == "POST" for r in server.calls
        ):
            return httpx.Response(503)
        return server(request)

    install_server(monkeypatch, handler)
    with pytest.raises(PlatformError) as error:
        submit(reviewed, arguments=["1"], send=True)
    assert error.value.uncertain


def test_later_lookup_failure_preserves_mixed_exit(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.cli import main

    path = reviewed.last_run() / "arguments.json"
    data = json.loads(path.read_text())
    data["arguments"].append(
        dict(data["arguments"][0], id="a2", statement="Another supported observation.")
    )
    path.write_text(json.dumps(data))
    server = Server()

    def handler(request: httpx.Request) -> httpx.Response:
        if server.arguments and request.url.path.endswith("/arguments"):
            return httpx.Response(503)
        return server(request)

    install_server(monkeypatch, handler)
    assert (
        main(
            [
                "submit",
                "--workspace",
                str(reviewed.path),
                "--argument",
                "1",
                "--argument",
                "2",
                "--send",
            ]
        )
        == 4
    )


@pytest.mark.parametrize(
    "state,expected", [("accepted", 0), ("rejected", 4), ("pending", 4)]
)
def test_wait_reports_checks_separately(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch, state: str, expected: int
) -> None:
    from koala_science.cli import main

    server = Server()
    install_server(monkeypatch, server)
    assert (
        main(["submit", "--workspace", str(reviewed.path), "--argument", "1", "--send"])
        == 0
    )
    server.arguments[0]["state"] = state
    assert (
        main(["submit", "--workspace", str(reviewed.path), "--send", "--wait", "0.01"])
        == expected
    )


def test_saved_platform_id_must_match() -> None:
    with (
        client(
            lambda r: httpx.Response(
                200, json=dict(paper(), arxiv_id="2607.12345", pdf_url=None)
            )
        ) as api,
        pytest.raises(ValueError, match="Saved platform"),
    ):
        api.find_paper("2607.29592", "TOOD", "11111111-1111-4111-8111-111111111111")


def test_disappearing_duplicate_import_stops(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.cli import main

    server = Server(exists=False)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            server.calls.append(request)
            return httpx.Response(409)
        return server(request)

    install_server(monkeypatch, handler)
    for _ in range(2):
        assert (
            main(
                [
                    "submit",
                    "--workspace",
                    str(reviewed.path),
                    "--argument",
                    "1",
                    "--send",
                ]
            )
            == 4
        )
    assert len([r for r in server.calls if r.method == "POST"]) == 1


def test_preview_does_not_offer_an_unresolved_import(
    reviewed: PaperWorkspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from koala_science.cli import main

    server = Server(exists=False)
    server.import_mode = "timeout_absent"
    install_server(monkeypatch, server)
    assert (
        main(["submit", "--workspace", str(reviewed.path), "--argument", "1", "--send"])
        == 4
    )
    assert main(["submit", "--workspace", str(reviewed.path)]) == 4
    assert len([r for r in server.calls if r.method == "POST"]) == 1
