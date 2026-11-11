"""In-memory platform and scripted model for offline tests."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from koala_science.types import ModelRequest, ModelResponse

ROOT = Path(__file__).resolve().parents[1]
PAPER_LINES = [
    "Method A reaches 81.2 accuracy versus 76.0 for baseline B.",
    "Method A was trained for 40 epochs while baseline B was trained for 10.",
    "No comparison at equal training duration is reported.",
]


def make_pdf(lines: list[str]) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(600, 400)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    ops = ["BT /F1 10 Tf 20 360 Td"]
    for line in lines:
        ops.append(f"({line}) Tj 0 -20 Td")
    ops.append("ET")
    stream = DecodedStreamObject()
    stream.set_data(" ".join(ops).encode())
    page[NameObject("/Contents")] = stream
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def iso(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def paper(pid: str, **overrides: Any) -> dict[str, Any]:
    return {
        "id": pid,
        "title": f"Paper {pid}",
        "abstract": "We propose method A and compare it with baseline B.",
        "domains": ["d/NLP"],
        "pdf_url": f"/storage/pdfs/{pid}.pdf",
        "argument_count": 0,
        "arxiv_id": None,
        "created_at": iso(1),
        **overrides,
    }


class FakePlatform:
    """Enough of the Koala API for the agent loop, with every request recorded."""

    def __init__(self, papers: list[dict[str, Any]], **profile: Any) -> None:
        self.papers = {p["id"]: p for p in papers}
        self.arguments: dict[str, list[dict[str, Any]]] = {p["id"]: [] for p in papers}
        self.profile = {
            "id": "agent-1",
            "name": "test-agent",
            "actor_type": "agent",
            "github_repo": "https://github.com/someone/agent",
            "budget": 50,
            "model_credit_usd": 10.0,
            **profile,
        }
        self.requests: list[httpx.Request] = []
        self.post_status: list[int] = []
        self.pdf = make_pdf(PAPER_LINES)
        self.counter = 0

    def posts(self) -> list[dict[str, Any]]:
        return [
            json.loads(r.content)
            for r in self.requests
            if r.method == "POST" and r.url.path.endswith("/arguments/")
        ]

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.startswith("/storage/"):
            assert "authorization" not in request.headers
            return httpx.Response(200, content=self.pdf)
        assert request.headers["authorization"] == "cs_test_key"
        api = path.removeprefix("/api/v1/")
        if api == "users/me":
            return httpx.Response(200, json=self.profile)
        if api == "papers/":
            params = request.url.params
            domain = params.get("domain")
            skip = int(params.get("skip", 0))
            limit = int(params.get("limit", 20))
            after = params.get("after")
            max_arguments = params.get("max_arguments")
            assert params.get("eligible") == "true"
            # A paper marked eligible=False stands for one the owner wrote or has
            # no argument slots left on.
            listed = [
                p
                for p in self.papers.values()
                if (not domain or domain in p["domains"])
                and (not after or p["created_at"] > after)
                and (max_arguments is None or p["argument_count"] <= int(max_arguments))
                and p.get("eligible", True)
            ]
            return httpx.Response(200, json=listed[skip : skip + limit])
        if api.startswith("papers/") and api.endswith("/arguments"):
            pid = api.split("/")[1]
            visible = [a for a in self.arguments[pid] if a["state"] != "withheld"]
            return httpx.Response(200, json=visible)
        if api.startswith("papers/"):
            return httpx.Response(200, json=self.papers[api.split("/")[1]])
        if api.startswith("users/") and api.endswith("/arguments"):
            mine = [
                a
                for args in self.arguments.values()
                for a in args
                if a["author_id"] == self.profile["id"]
            ]
            return httpx.Response(200, json=mine)
        if api == "arguments/" and request.method == "POST":
            status = self.post_status.pop(0) if self.post_status else 201
            if status != 201:
                return httpx.Response(status, json={"detail": f"status {status}"})
            body = json.loads(request.content)
            self.counter += 1
            argument = {
                "id": f"arg-{self.counter}",
                "author_id": self.profile["id"],
                "state": "pending",
                "checks": [],
                "created_at": iso(0),
                **body,
            }
            self.arguments[body["paper_id"]].append(argument)
            self.profile["budget"] -= 1
            return httpx.Response(
                201, json={**argument, "budget_remaining": self.profile["budget"]}
            )
        return httpx.Response(404, json={"detail": "not found"})


def check(passed: bool = True, reason: str = "ok") -> dict[str, Any]:
    return {"passed": passed, "reason": reason}


class ScriptedModel:
    """Answers each review stage; `fail` names platform checks the verifier fails."""

    def __init__(
        self,
        *,
        rank: list[str] | None = None,
        fail: set[str] | None = None,
        revision: str | None = None,
        excerpt: str | None = None,
        claims: int = 1,
        bad_quotes: int = 0,
        stubborn: bool = False,
    ) -> None:
        # bad_quotes: how many proposal/revision attempts quote text not in the paper.
        # stubborn: revisions still fail the verifier's `fail` checks.
        self.bad_quotes = bad_quotes
        self.stubborn = stubborn
        self.claims = claims
        self.proposals = 0
        self.rank = rank
        self.fail = fail or set()
        self.revision = revision
        self.excerpt = excerpt
        self.requests: list[ModelRequest] = []
        self.stages: list[str] = []

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        data = json.loads(request.messages[-1].content)
        if request.output_schema.get("title") == "Ranking":
            self.stages.append("rank")
            ids = [c["paper_id"] for c in data["candidates"]]
            chosen = ids if self.rank is None else [i for i in self.rank]
            output = {
                "ranked": [
                    {"paper_id": i, "reason": "fits the strategy"} for i in chosen
                ]
            }
            return ModelResponse(text=json.dumps(output), model="fake")
        stage = data["stage"]
        self.stages.append(stage)
        if stage in {"claim_map", "claim_plan"}:
            output = {
                "claims": [
                    {
                        "claim": f"Method A outperforms baseline B ({n}).",
                        "why_it_matters": "It is the headline result.",
                        "span_ids": [s["id"] for s in data["paper_text"]],
                    }
                    for n in range(self.claims)
                ]
            }
        elif stage in {"proposal", "revision"}:
            span = next(s for s in data["paper_text"] if "40 epochs" in s["text"])
            source_id = data["paper"]["source_id"]
            excerpt = (
                self.excerpt
                or "trained for 40 epochs while baseline B was trained for 10"
            )
            if self.bad_quotes > 0:
                self.bad_quotes -= 1
                excerpt = "trained for 400 epochs while baseline B was trained for 10"
            statement = (
                "The accuracy gain of the proposed method over the baseline is confounded "
                "by four times more training epochs."
            )
            if stage == "revision":
                statement += " No equal-duration comparison is reported."
            self.proposals += 1
            if self.proposals > 1:
                statement += f" (variant {self.proposals})"
            output = {
                "candidates": [
                    {
                        "kind": "criticism",
                        "target": "headline comparison",
                        "statement": statement,
                        "rationale": "The method trained for 40 epochs and the baseline for 10, so the 81.2 versus 76.0 gap may come from training length.",
                        "evidence": [
                            {
                                "source_id": source_id,
                                "span_id": span["id"],
                                "page": span["page"],
                                "line_start": span.get("line_start"),
                                "line_end": span.get("line_end"),
                                "excerpt": excerpt,
                            }
                        ],
                        "limitations": [],
                        "absence_scope": [],
                    }
                ]
            }
        elif stage == "evidence":
            revised = "equal-duration" in data["candidates"][0]["statement"]
            failing = set() if revised and not self.stubborn else self.fail
            output = {
                name: check(name not in failing, f"{name} judged")
                for name in (
                    "moderation",
                    "validity",
                    "relevance",
                    "uniqueness",
                    "verification",
                )
            }
            output["revision"] = None if revised else self.revision
        else:
            output = {"duplicate": False, "reason": "distinct"}
        return ModelResponse(text=json.dumps(output), model="fake")


def agent_dir(tmp_path: Path, **run: Any) -> Path:
    """A fork-like directory: the repository's agent.yaml with test overrides."""
    import yaml

    for name in ("strategy.md", "reviewer.md"):
        shutil.copy(ROOT / name, tmp_path / name)
    config = yaml.safe_load((ROOT / "agent.yaml").read_text())
    config["model"] = {
        "provider": "custom",
        "name": "fake",
        "factory": "unused.py:make",
    }
    config["discovery"]["max_age_days"] = 30
    config["run"].update({"max_arguments": None, "when_idle": "stop", **run})
    (tmp_path / "unused.py").write_text("def make():\n    raise AssertionError\n")
    (tmp_path / "agent.yaml").write_text(yaml.safe_dump(config))
    return tmp_path
