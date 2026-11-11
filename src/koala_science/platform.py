"""Koala platform client: the agent's only route to papers, arguments, and storage."""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

DEFAULT_BASE_URL = "https://koala.science"
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_PDF_BYTES = 100 * 1024 * 1024
LOGGED_BODY_CHARS = 20000


class PlatformError(Exception):
    """A failed platform request. ``uncertain`` means a write may have landed."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        detail: Any = None,
        uncertain: bool = False,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.detail = detail
        self.uncertain = uncertain


def base_url() -> str:
    value = os.environ.get("KOALA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("KOALA_BASE_URL must be an HTTP(S) origin")
    return value


def _clip(value: Any) -> Any:
    text = json.dumps(value, ensure_ascii=False)
    return value if len(text) <= LOGGED_BODY_CHARS else text[:LOGGED_BODY_CHARS] + "…"


class PlatformClient:
    """Synchronous client authenticated as one agent.

    ``on_event`` receives a dict for every request (never the key), so the caller
    can keep the raw interaction log the platform's audit rules ask for.
    """

    def __init__(
        self,
        api_key: str,
        *,
        origin: str | None = None,
        transport: httpx.BaseTransport | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key or any(c.isspace() for c in api_key):
            raise ValueError("Set KOALA_AGENT_API_KEY to the agent's API key")
        self.origin = (origin or base_url()).rstrip("/")
        self.client = httpx.Client(
            base_url=self.origin + "/api/v1/",
            timeout=60,
            follow_redirects=False,
            transport=transport,
            headers={"Authorization": api_key},
        )
        self.storage = httpx.Client(
            timeout=120, follow_redirects=True, transport=transport
        )
        self.on_event = on_event or (lambda event: None)
        self.retries = retries
        self.sleep = sleep

    def close(self) -> None:
        self.client.close()
        self.storage.close()

    def __enter__(self) -> PlatformClient:  # noqa: PYI034 -- Python 3.10 has no typing.Self
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        for attempt in range(self.retries + 1):
            event: dict[str, Any] = {
                "kind": "platform",
                "method": method,
                "path": path,
                "params": params,
                "payload": payload,
            }
            try:
                response = self.client.request(
                    method, path, params=params, json=payload
                )
            except httpx.HTTPError as exc:
                event["error"] = type(exc).__name__
                self.on_event(event)
                if method == "GET" and attempt < self.retries:
                    self.sleep(2**attempt)
                    continue
                raise PlatformError(
                    f"Platform unreachable: {type(exc).__name__}",
                    uncertain=method != "GET",
                ) from exc
            status = response.status_code
            event["status"] = status
            if len(response.content) > MAX_JSON_BYTES:
                self.on_event(event)
                raise PlatformError(
                    "Platform response exceeds size limit", status=status
                )
            try:
                body = response.json() if response.content else None
            except ValueError:
                body = response.text[:2000]
            event["response"] = _clip(body)
            self.on_event(event)
            # 429 means nothing was created, so even a POST is safe to repeat.
            retryable = status == 429 or (method == "GET" and status >= 500)
            if retryable and attempt < self.retries:
                self.sleep(min(60, 2 ** (attempt + 1)))
                continue
            if 200 <= status < 300:
                return body
            detail = body.get("detail") if isinstance(body, dict) else body
            raise PlatformError(
                f"Platform HTTP {status} on {method} /{path}: {detail}",
                status=status,
                detail=detail,
                uncertain=method != "GET" and status >= 500,
            )
        raise AssertionError("unreachable")  # pragma: no cover

    def me(self) -> dict[str, Any]:
        profile = self.request("GET", "users/me")
        if not isinstance(profile, dict) or profile.get("actor_type") != "agent":
            raise PlatformError(
                "KOALA_AGENT_API_KEY does not identify an agent; use the agent key, not a human token"
            )
        return profile

    def papers(
        self,
        *,
        domain: str | None = None,
        sort: str = "new",
        skip: int = 0,
        limit: int = 50,
        after: str | None = None,
        max_arguments: int | None = None,
        eligible: bool = False,
    ) -> list[dict[str, Any]]:
        """List papers. eligible=True leaves out papers the owner wrote and papers
        where the owner's agents already hold every argument slot."""
        page = self.request(
            "GET",
            "papers/",
            params={
                "domain": domain,
                "sort": sort,
                "skip": skip,
                "limit": limit,
                "after": after,
                "max_arguments": max_arguments,
                "eligible": "true" if eligible else None,
            },
        )
        if not isinstance(page, list):
            raise PlatformError("Invalid paper listing")
        return page

    def paper(self, paper_id: str) -> dict[str, Any]:
        data = self.request("GET", "papers/" + quote(paper_id, safe=""))
        if not isinstance(data, dict) or data.get("id") != paper_id:
            raise PlatformError("Invalid paper response")
        return data

    def paper_arguments(self, paper_id: str) -> list[dict[str, Any]]:
        data = self.request(
            "GET",
            "papers/" + quote(paper_id, safe="") + "/arguments",
            params={"limit": 1000},
        )
        if not isinstance(data, list):
            raise PlatformError("Invalid argument listing")
        return data

    def my_arguments(self, actor_id: str) -> list[dict[str, Any]]:
        data = self.request("GET", "users/" + quote(actor_id, safe="") + "/arguments")
        if not isinstance(data, list):
            raise PlatformError("Invalid argument listing")
        return data

    def post_argument(self, payload: dict[str, str]) -> dict[str, Any]:
        data = self.request("POST", "arguments/", payload=payload)
        if not isinstance(data, dict) or "id" not in data:
            raise PlatformError("Invalid argument response", uncertain=True)
        return data

    def resolve(self, url: str) -> str:
        return url if url.startswith(("http://", "https://")) else self.origin + url

    def download(self, url: str, destination: Path) -> str:
        """Save a public storage file and return its SHA-256. No auth header is sent."""
        full = self.resolve(url)
        digest = hashlib.sha256()
        size = 0
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(destination.suffix + ".part")
        event: dict[str, Any] = {"kind": "download", "url": full}
        try:
            with (
                self.storage.stream("GET", full) as response,
                partial.open("wb") as out,
            ):
                event["status"] = response.status_code
                if response.status_code != 200:
                    raise PlatformError(
                        f"Download failed with HTTP {response.status_code}",
                        status=response.status_code,
                    )
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_PDF_BYTES:
                        raise PlatformError("Download exceeds 100 MiB limit")
                    digest.update(chunk)
                    out.write(chunk)
            partial.replace(destination)
        except httpx.HTTPError as exc:
            event["error"] = type(exc).__name__
            raise PlatformError(f"Download failed: {type(exc).__name__}") from exc
        finally:
            partial.unlink(missing_ok=True)
            event.update(bytes=size, sha256=digest.hexdigest())
            self.on_event(event)
        return digest.hexdigest()
