"""Literature search the review model can ask for. Results are untrusted data.

OpenAlex is the default: free, no key, and generous limits. With
SEMANTIC_SCHOLAR_API_KEY set, Semantic Scholar is used instead; its keyless pool
is shared by everyone and often answers 429.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Protocol

import httpx

OPENALEX_URL = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
MAX_QUERY_CHARS = 300
MAX_ABSTRACT_CHARS = 1500
RESULTS = 5


class Search(Protocol):
    async def __call__(self, query: str) -> list[dict[str, Any]]: ...


class SearchError(RuntimeError):
    pass


class HTTPSearch:
    name = "search"

    def __init__(
        self, *, transport: httpx.AsyncBaseTransport | None = None, sleep=asyncio.sleep
    ) -> None:
        self.transport, self.sleep = transport, sleep

    async def get(
        self, url: str, params: dict[str, Any], headers: dict[str, str]
    ) -> Any:
        async with httpx.AsyncClient(transport=self.transport, timeout=30) as client:
            for attempt in range(3):
                try:
                    response = await client.get(url, params=params, headers=headers)
                except httpx.TransportError as exc:
                    raise SearchError(f"{self.name} unreachable") from exc
                if response.status_code == 429 and attempt < 2:
                    await self.sleep(2 * 2**attempt)
                    continue
                if response.status_code != 200:
                    raise SearchError(f"{self.name} HTTP {response.status_code}")
                try:
                    return response.json()
                except ValueError as exc:
                    raise SearchError(f"Invalid {self.name} response") from exc


class OpenAlex(HTTPSearch):
    name = "OpenAlex"

    async def __call__(self, query: str) -> list[dict[str, Any]]:
        params = {
            "search": query[:MAX_QUERY_CHARS],
            "per_page": RESULTS,
            "select": "title,publication_year,authorships,primary_location,"
            "cited_by_count,abstract_inverted_index,ids,doi",
        }
        if key := os.environ.get("OPENALEX_API_KEY"):
            params["api_key"] = key
        data = await self.get(OPENALEX_URL, params, {})
        try:
            return [openalex_view(w) for w in data["results"] if isinstance(w, dict)]
        except (KeyError, TypeError, AttributeError) as exc:
            raise SearchError("Invalid OpenAlex response") from exc


class SemanticScholar(HTTPSearch):
    name = "Semantic Scholar"

    async def __call__(self, query: str) -> list[dict[str, Any]]:
        headers = {}
        if key := os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
            headers["x-api-key"] = key
        params = {
            "query": query[:MAX_QUERY_CHARS],
            "limit": RESULTS,
            "fields": "title,year,authors,venue,abstract,citationCount,externalIds",
        }
        data = await self.get(SEMANTIC_SCHOLAR_URL, params, headers)
        try:
            papers = data.get("data") or []
            return [semantic_scholar_view(p) for p in papers if isinstance(p, dict)]
        except (TypeError, AttributeError) as exc:
            raise SearchError("Invalid Semantic Scholar response") from exc


def default_search() -> Search:
    if os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        return SemanticScholar()
    return OpenAlex()


def record(
    title, year, authors, venue, arxiv_id, doi, citations, abstract
) -> dict[str, Any]:
    authors = [a for a in authors if a]
    return {
        "title": title,
        "year": year,
        "authors": authors[:3] + (["et al."] if len(authors) > 3 else []),
        "venue": venue or None,
        "arxiv_id": arxiv_id,
        "doi": doi,
        "citations": citations,
        "abstract": (abstract or "")[:MAX_ABSTRACT_CHARS] or None,
    }


def openalex_view(work: dict[str, Any]) -> dict[str, Any]:
    index = work.get("abstract_inverted_index") or {}
    words = sorted((p, w) for w, positions in index.items() for p in positions)
    source = ((work.get("primary_location") or {}).get("source")) or {}
    doi = work.get("doi") or ""
    return record(
        work.get("title"),
        work.get("publication_year"),
        [
            (a.get("author") or {}).get("display_name")
            for a in work.get("authorships") or []
        ],
        source.get("display_name"),
        None,
        doi.removeprefix("https://doi.org/") or None,
        work.get("cited_by_count"),
        " ".join(w for _, w in words),
    )


def semantic_scholar_view(paper: dict[str, Any]) -> dict[str, Any]:
    ids = paper.get("externalIds") or {}
    return record(
        paper.get("title"),
        paper.get("year"),
        [a.get("name") for a in paper.get("authors") or [] if isinstance(a, dict)],
        paper.get("venue"),
        ids.get("ArXiv"),
        ids.get("DOI"),
        paper.get("citationCount"),
        paper.get("abstract"),
    )
