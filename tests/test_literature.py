"""Literature search adapters, against a mocked HTTP transport."""

import asyncio

import httpx
import pytest

from koala_science.literature import (
    OpenAlex,
    SearchError,
    SemanticScholar,
    default_search,
)

RECORD = {
    "title": "Prior Work",
    "year": 2024,
    "authors": [{"name": n} for n in ["A", "B", "C", "D"]],
    "venue": "",
    "abstract": "x" * 5000,
    "citationCount": 12,
    "externalIds": {"ArXiv": "2401.00001", "DOI": "10.1/abc"},
}


def search(handler, query="order-preserving activations", adapter=SemanticScholar):
    slept = []

    async def sleep(seconds):
        slept.append(seconds)

    client = adapter(transport=httpx.MockTransport(handler), sleep=sleep)
    return asyncio.run(client(query)), slept


def test_results_are_compact_records(monkeypatch):
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"total": 1, "data": [RECORD]})

    [result], _ = search(handler)
    assert result == {
        "title": "Prior Work",
        "year": 2024,
        "authors": ["A", "B", "C", "et al."],
        "venue": None,
        "arxiv_id": "2401.00001",
        "doi": "10.1/abc",
        "abstract": "x" * 1500,
    }
    assert seen[0].url.params["query"] == "order-preserving activations"
    assert "x-api-key" not in seen[0].headers


def test_api_key_is_sent_when_set(monkeypatch):
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "s2-key")
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"data": []})

    assert search(handler)[0] == []
    assert seen[0].headers["x-api-key"] == "s2-key"


def test_rate_limit_is_retried_then_reported():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429)

    with pytest.raises(SearchError, match="HTTP 429"):
        search(handler)
    assert len(calls) == 3


def test_rate_limit_recovers():
    responses = [httpx.Response(429), httpx.Response(200, json={"data": [RECORD]})]
    results, slept = search(lambda request: responses.pop(0))
    assert len(results) == 1 and slept == [2]


def test_long_queries_are_cut():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"data": []})

    search(handler, query="q" * 1000)
    assert len(seen[0].url.params["query"]) == 300


def test_openalex_rebuilds_the_abstract(monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    work = {
        "title": "Prior Work",
        "publication_year": 2023,
        "authorships": [{"author": {"display_name": "A"}}],
        "primary_location": {"source": {"display_name": "NeurIPS"}},
        "cited_by_count": 7,
        "abstract_inverted_index": {"Activations": [0], "matter": [1, 3], "a": [2]},
        "doi": "https://doi.org/10.1/xyz",
    }
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"results": [work]})

    [result], _ = search(handler, adapter=OpenAlex)
    assert result == {
        "title": "Prior Work",
        "year": 2023,
        "authors": ["A"],
        "venue": "NeurIPS",
        "arxiv_id": None,
        "doi": "10.1/xyz",
        "abstract": "Activations matter a matter",
    }
    assert seen[0].url.params["search"] == "order-preserving activations"
    assert "api_key" not in seen[0].url.params


def test_semantic_scholar_is_used_only_with_a_key(monkeypatch):
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    assert isinstance(default_search(), OpenAlex)
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "s2-key")
    assert isinstance(default_search(), SemanticScholar)


def test_requests_never_ask_for_citation_counts():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"data": [], "results": []})

    search(handler)
    search(handler, adapter=OpenAlex)
    assert "citation" not in seen[0].url.params["fields"].lower()
    assert "cited" not in seen[1].url.params["select"]
