"""Bounded platform transport and exact arXiv identity lookup; no implicit writes."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any
from urllib.parse import quote, urlsplit

import httpx


class PlatformError(Exception):
    """Sanitized failure; uncertain writes must be reconciled before retrying."""

    def __init__(
        self, message: str, *, status: int | None = None, uncertain: bool = False
    ) -> None:
        super().__init__(message)
        self.status = status
        self.uncertain = uncertain


def arxiv_identity(value: str) -> tuple[str, int | None]:
    value = value.strip()
    if "://" in value:
        url = urlsplit(value)
        if (
            url.scheme not in {"http", "https"}
            or url.hostname not in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("Invalid arXiv identity URL")
        value = re.sub(r"^/(abs|pdf)/", "", url.path)
    value = (
        re.sub(r"^arxiv:", "", value, flags=re.IGNORECASE)
        .removesuffix("/")
        .removesuffix(".pdf")
    )
    match = re.fullmatch(
        r"(\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z]{2})?/\d{7})(?:v([1-9]\d*))?",
        value,
        re.IGNORECASE,
    )
    if not match:
        raise ValueError("Invalid arXiv identifier")
    canonical = re.sub(r"\.[a-z]{2}/", "/", match[1].lower())
    return canonical, int(match[2]) if match[2] else None


def remote_identity(paper: dict[str, Any]) -> tuple[str, int | None] | None:
    identities = []
    for key in ("arxiv_id", "pdf_url"):
        value = paper.get(key)
        if value:
            try:
                identities.append(arxiv_identity(value))
            except (ValueError, AttributeError):
                if key == "arxiv_id":
                    raise ValueError(
                        "Platform returned an invalid arXiv identity"
                    ) from None
    if not identities:
        return None
    if (
        len({i[0] for i in identities}) != 1
        or len({i[1] for i in identities if i[1] is not None}) > 1
    ):
        raise ValueError("Platform manuscript identifiers disagree")
    return identities[0][0], next((i[1] for i in identities if i[1] is not None), None)


def verify_paper(
    paper: dict[str, Any], identity: tuple[str, int | None], confirm_unknown: bool
) -> None:
    remote = remote_identity(paper)
    if remote is None or remote[0] != identity[0]:
        raise ValueError("Platform paper does not match workspace arXiv identity")
    if identity[1] is not None and remote[1] is not None and identity[1] != remote[1]:
        raise ValueError("Platform manuscript version differs from reviewed version")
    if (identity[1] is None or remote[1] is None) and not confirm_unknown:
        raise ValueError(
            "Manuscript version unavailable; inspect it and pass --confirm-version"
        )


class PlatformClient:
    """Fixed production origin; transport injection is reserved for offline tests."""

    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        self.client = httpx.Client(
            base_url="https://koala.science/api/v1/",
            timeout=30,
            follow_redirects=False,
            transport=transport,
            headers={"Accept-Encoding": "identity"},
        )

        self.deadline: float | None = None

    def __enter__(self) -> PlatformClient:  # noqa: PYI034 -- supports Python 3.10 without a typing backport
        return self

    def __exit__(self, *args: object) -> None:
        self.client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        actor: str | None = None,
        payload: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        headers = {}
        if actor:
            variable = (
                "KOALA_OWNER_ACCESS_TOKEN"
                if actor == "owner"
                else "KOALA_AGENT_API_KEY"
            )
            token = os.environ.get(variable)
            if not token:
                raise ValueError(f"Set {variable} in the environment")
            headers["Authorization"] = f"Bearer {token}"
        try:
            timeout = (
                30
                if self.deadline is None
                else min(30, self.deadline - time.monotonic())
            )
            if timeout <= 0:
                raise PlatformError("Platform polling deadline reached", uncertain=True)
            with self.client.stream(
                method,
                path,
                headers=headers,
                json=payload,
                params=params,
                timeout=timeout,
            ) as response:
                if not 200 <= response.status_code < 300:
                    status = response.status_code
                    detail = "Check authentication, eligibility, allowance, or budget"
                    raise PlatformError(
                        f"Platform HTTP {status}. {detail}",
                        status=status,
                        uncertain=method == "POST" and (status >= 500 or status == 408),
                    )
                if response.headers.get("content-encoding", "identity") != "identity":
                    raise ValueError("Compressed platform response")
                body = bytearray()
                for chunk in response.iter_bytes():
                    if self.deadline is not None and time.monotonic() >= self.deadline:
                        raise PlatformError(
                            "Platform polling deadline reached", uncertain=True
                        )
                    body.extend(chunk)
                    if len(body) > 8 * 1024 * 1024:
                        raise ValueError("Platform response exceeds limit")
                return json.loads(body)
        except (httpx.HTTPError, ValueError) as exc:
            raise PlatformError(
                "Platform response unavailable or invalid", uncertain=method == "POST"
            ) from exc

    def pages(
        self, path: str, *, params: dict | None = None, actor: str | None = None
    ) -> list[dict]:
        records: list[dict] = []
        seen = set()
        for offset in range(0, 100000, 100):
            page = self.request(
                "GET",
                path,
                params={**(params or {}), "skip": offset, "limit": 100},
                actor=actor,
            )
            if not isinstance(page, list) or len(page) > 100:
                raise PlatformError("Invalid platform pagination")
            for item in page:
                record = item.get("paper", item) if isinstance(item, dict) else {}
                identifier = record.get("id")
                if not isinstance(identifier, str) or identifier in seen:
                    raise PlatformError("Incomplete or unstable platform pagination")
                seen.add(identifier)
                records.append(record)
            if not page:
                return records
            # An explicit empty page proves exhaustion even if the server caps page size.
            if len(page) < 100:
                tail = self.request(
                    "GET",
                    path,
                    params={**(params or {}), "skip": offset + len(page), "limit": 100},
                    actor=actor,
                )
                if tail != []:
                    raise PlatformError("Incomplete platform pagination")
                return records
        raise PlatformError("Platform pagination limit reached; absence is unproven")

    def paper(self, paper_id: str) -> dict:
        data = self.request("GET", "papers/" + quote(paper_id, safe=""))
        if not isinstance(data, dict) or data.get("id") != paper_id:
            raise PlatformError("Invalid platform paper response")
        return data

    def find_paper(
        self, arxiv: str, title: str, saved_id: str | None = None
    ) -> dict | None:
        canonical, _ = arxiv_identity(arxiv)
        if saved_id:
            paper = self.paper(saved_id)
            identity = remote_identity(paper)
            if not identity or identity[0] != canonical:
                raise ValueError("Saved platform ID does not match workspace paper")
            return paper
        matches: dict[str, dict] = {}
        for query in dict.fromkeys([canonical, title]):
            if query:
                for paper in self.pages(
                    "search/", params={"q": query, "type": "paper"}
                ):
                    identity = remote_identity(paper)
                    if identity and identity[0] == canonical:
                        matches[paper["id"]] = paper
        if not matches:
            for paper in self.pages("papers/", params={"sort": "new"}):
                identity = remote_identity(paper)
                if identity and identity[0] == canonical:
                    matches[paper["id"]] = paper
        if len(matches) > 1:
            raise ValueError("Ambiguous platform paper identity")
        return self.paper(next(iter(matches))) if matches else None

    def arguments(self, paper_id: str, agent_id: str) -> list[dict]:
        # User listings include the agent's rejected/pending arguments when authenticated.
        own = self.pages(
            "users/" + quote(agent_id, safe="") + "/arguments", actor="agent"
        )
        public = self.pages("papers/" + quote(paper_id, safe="") + "/arguments")
        return list(
            {a["id"]: a for a in public + own if a.get("paper_id") == paper_id}.values()
        )
