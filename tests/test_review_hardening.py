"""Regression cases found while reviewing security and failure boundaries."""

import asyncio
import hashlib
import json
from pathlib import Path

import httpx
import pytest
from markdown_it import MarkdownIt
from pydantic import ValidationError
from test_local_contracts import model_request
from test_local_review import FakeProvider, workspace

from koala_science import Agent, BackendResult, Limits, ModelResponse, Proposals
from koala_science.cli import main
from koala_science.config import ModelConfig, load_config
from koala_science.output import markdown
from koala_science.providers import HTTPProvider, ProviderError, build_provider
from koala_science.sources import read_source
from koala_science.types import Verdict


def test_report_renders_untrusted_content_as_text(tmp_path):
    config = workspace(tmp_path)
    paper = tmp_path / "paper.txt"
    paper.write_text("Both models trained for 10 epochs.")
    result = Agent.from_config(config, provider=FakeProvider()).review(paper)
    attack = '<img src="https://tracking.invalid/secret" onerror="alert(1)"> ![x](https://tracking.invalid/pixel) [click](javascript:alert(1))'
    result.arguments[0].statement = attack
    result.arguments[0].evidence[0].excerpt = attack
    rendered = MarkdownIt("commonmark", {"html": True}).render(markdown(result))
    assert "<img" not in rendered
    assert "<a " not in rendered
    assert "&lt;img" in rendered


@pytest.mark.parametrize(
    "values",
    [
        {"max_tasks": True},
        {"max_run_seconds": float("inf")},
        {"request_timeout_seconds": float("nan")},
    ],
)
def test_limits_reject_coercion_and_nonfinite_values(values):
    with pytest.raises(ValidationError):
        Limits(**values)


def test_verdict_requires_a_boolean_atomicity_decision():
    with pytest.raises(ValidationError):
        Verdict(decision="supported", atomic="yes", reason="coerced")


def test_yaml_duplicate_fields_are_rejected(tmp_path):
    config = workspace(tmp_path)
    config.write_text(config.read_text() + "name: overridden\n")
    with pytest.raises(ValueError, match="Duplicate YAML"):
        load_config(config)


def test_recursive_yaml_alias_is_an_input_error(tmp_path):
    config = tmp_path / "agent.yaml"
    config.write_text("loop: &loop [*loop]\n")
    with pytest.raises(ValueError, match="Recursive YAML"):
        load_config(config)


def test_missing_input_does_not_leave_a_blocking_journal(tmp_path):
    config = workspace(tmp_path)
    assert (
        main(
            [
                "review",
                str(tmp_path / "missing.txt"),
                "--config",
                str(config),
                "--output",
                str(tmp_path / "run"),
            ]
        )
        == 2
    )
    assert not (tmp_path / ".run.journal.jsonl").exists()


def test_pdf_extraction_uses_the_hashed_snapshot(tmp_path, monkeypatch):
    from koala_science import sources

    file = tmp_path / "paper.pdf"
    file.write_bytes(b"original")

    class Reader:
        def __init__(self, stream):
            file.write_bytes(b"replacement")
            text = (
                stream.read().decode()
                if hasattr(stream, "read")
                else Path(stream).read_text()
            )

            class Page:
                def extract_text(self):
                    return text

            self.pages = [Page()]

    monkeypatch.setattr(sources, "PdfReader", Reader)
    source = read_source(file)
    assert source.content_hash == hashlib.sha256(b"original").hexdigest()
    assert source.spans[0].text == "original"


def test_repair_does_not_reset_transient_retry_allowance(tmp_path):
    class Unreliable:
        calls = 0

        async def generate(self, request):
            self.calls += 1
            if self.calls == 2:
                return ModelResponse(text="malformed", model="fake")
            raise ProviderError("temporary failure", retryable=True)

    config = workspace(tmp_path)
    paper = tmp_path / "paper.txt"
    paper.write_text("A result.")
    provider = Unreliable()
    result = Agent.from_config(config, provider=provider).review(paper)
    assert provider.calls == 4
    assert result.manifest["model_calls"] == 4


def test_custom_provider_can_define_dataclasses(tmp_path):
    factory = tmp_path / "provider.py"
    factory.write_text(
        'from __future__ import annotations\nfrom dataclasses import dataclass\nfrom koala_science import ModelResponse\n@dataclass\nclass Provider:\n name: str = "test"\n async def generate(self, request):\n  return ModelResponse(text="{}", model=self.name)\ndef build():\n return Provider()\n'
    )
    provider = build_provider(
        ModelConfig(provider="custom", name="test", factory=f"{factory}:build")
    )
    assert asyncio.run(provider.generate(model_request())).model == "test"


def test_http_response_size_is_bounded(monkeypatch):
    from koala_science import providers

    monkeypatch.setattr(providers, "MAX_RESPONSE_BYTES", 256, raising=False)
    response = {"choices": [{"message": {"content": "a" * 1024}}]}
    provider = HTTPProvider(
        ModelConfig(provider="compatible_api", name="test", base_url="http://local/v1"),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=response)
        ),
    )
    with pytest.raises(ProviderError, match="size limit"):
        asyncio.run(provider.generate(model_request()))


def test_empty_backend_does_not_claim_it_read_the_paper(tmp_path):
    class Empty:
        supports_budget = True

        async def propose(self, context, limits, budget):
            return Proposals(candidates=[])

    config = workspace(tmp_path)
    result = Agent.from_backend(Empty(), config=config, provider=FakeProvider()).review(
        tmp_path / "sample.md"
    )
    assert result.status == "partial"
    assert result.manifest["coverage"]["inspected_spans"] == []
    assert result.manifest["coverage"]["skipped_spans"]


def test_repair_digest_matches_the_prompt_used(tmp_path):
    class Repairing:
        requests = None

        async def generate(self, request):
            if self.requests is None:
                self.requests = []
            self.requests.append(request)
            return ModelResponse(
                text="bad" if len(self.requests) == 1 else '{"candidates": []}',
                model="fake",
            )

    config = workspace(tmp_path)
    paper = tmp_path / "paper.txt"
    paper.write_text("A result.")
    provider = Repairing()
    result = Agent.from_config(config, provider=provider).review(paper)
    expected = hashlib.sha256(
        json.dumps([m.model_dump() for m in provider.requests[-1].messages]).encode()
    ).hexdigest()
    assert result.manifest["tasks"][0]["prompt_digest"] == expected


def test_backend_reports_explicit_coverage_without_mutating_sources(tmp_path):
    class Backend:
        supports_budget = True

        async def propose(self, context, limits, budget):
            ids = [s.id for source in context.sources for s in source.spans]
            context.paper.spans[0].text = "accidentally modified by the backend"
            return BackendResult(candidates=[], inspected_span_ids=ids)

    config = workspace(tmp_path)
    result = Agent.from_backend(
        Backend(), config=config, provider=FakeProvider()
    ).review(tmp_path / "sample.md")
    assert result.status == "complete"
    assert "accidentally modified" not in result.sources[0].spans[0].text


def test_backend_unknown_coverage_is_failure(tmp_path):
    class Backend:
        supports_budget = True

        async def propose(self, context, limits, budget):
            return BackendResult(candidates=[], inspected_span_ids=["invented"])

    config = workspace(tmp_path)
    result = Agent.from_backend(
        Backend(), config=config, provider=FakeProvider()
    ).review(tmp_path / "sample.md")
    assert result.status == "failed"
    assert result.manifest["tasks"][0]["status"] == "failed"


def test_extracted_span_limit_is_enforced(tmp_path, monkeypatch):
    from koala_science import sources

    monkeypatch.setattr(sources, "MAX_SOURCE_SPANS", 2)
    file = tmp_path / "paper.txt"
    file.write_text("a\nb\nc\n")
    with pytest.raises(ValueError, match="span limit"):
        read_source(file)


@pytest.mark.parametrize("cancel", [False, True])
def test_pdf_parser_is_terminated_on_timeout_or_cancellation(
    tmp_path, monkeypatch, cancel
):
    import subprocess
    import sys

    from koala_science import sources

    real_popen = subprocess.Popen
    children = []

    def sleeper(*args, **kwargs):
        child = real_popen(
            [sys.executable, "-c", "import time; time.sleep(30)"], **kwargs
        )
        children.append(child)
        return child

    monkeypatch.setattr(sources.subprocess, "Popen", sleeper)

    async def exercise():
        task = asyncio.create_task(
            sources.read_source_async(tmp_path / "paper.pdf", 1 if cancel else 0.1)
        )
        if cancel:
            await asyncio.sleep(0.05)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(ValueError, match="deadline"):
                await task
        assert children[0].poll() is not None

    asyncio.run(exercise())


def test_real_text_pdf_uses_extraction_worker(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    from koala_science.sources import read_source_async

    writer = PdfWriter()
    page = writer.add_blank_page(200, 200)
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
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 10 100 Td (Both models train for ten epochs.) Tj ET")
    page[NameObject("/Contents")] = stream
    path = tmp_path / "paper.pdf"
    writer.write(path)
    source = asyncio.run(read_source_async(path, 10))
    assert source.spans[0].page == 1
    assert "ten epochs" in source.spans[0].text


def test_custom_provider_error_cannot_persist_configured_credential(
    tmp_path, monkeypatch
):
    import yaml

    config = workspace(tmp_path)
    raw = yaml.safe_load(config.read_text())
    raw["model"]["api_key_env"] = "REVIEW_SECRET_KEY"
    config.write_text(yaml.safe_dump(raw))
    monkeypatch.setenv("REVIEW_SECRET_KEY", "cs_do_not_persist_me")

    class Leaky:
        async def generate(self, request):
            raise ProviderError("Authentication failed for cs_do_not_persist_me")

    result = Agent.from_config(config, provider=Leaky()).review(tmp_path / "sample.md")
    assert "cs_do_not_persist_me" not in result.model_dump_json()


@pytest.mark.parametrize(
    "url",
    [
        "http:///missing-host",
        "https://user:password@api.test/v1",
        "https://api.test/v1?key=secret",
        "https://api.test/v1#fragment",
    ],
)
def test_provider_base_url_rejects_ambiguous_or_credential_bearing_urls(url):
    with pytest.raises(ValidationError):
        ModelConfig(provider="compatible_api", name="test", base_url=url)


def test_http_provider_refuses_compressed_responses():
    import gzip

    def handler(request):
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(
            200, headers={"content-encoding": "gzip"}, content=gzip.compress(b"{}")
        )

    provider = HTTPProvider(
        ModelConfig(provider="compatible_api", name="test", base_url="http://local/v1"),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderError, match="Compressed"):
        asyncio.run(provider.generate(model_request()))


def test_yaml_cannot_execute_python_objects(tmp_path, capsys):
    config = tmp_path / "agent.yaml"
    config.write_text("!!python/object/apply:builtins.print ['must not execute']\n")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config(config)
    assert "must not execute" not in capsys.readouterr().out
