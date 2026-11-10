"""Platform client: auth, retries, write safety, storage downloads."""

import httpx
import pytest

from koala_science.platform import PlatformClient, PlatformError


def client(handler, events=None):
    return PlatformClient(
        "cs_key",
        origin="https://koala.test",
        transport=httpx.MockTransport(handler),
        on_event=(events.append if events is not None else None),
        sleep=lambda s: None,
    )


def test_raw_agent_key_is_sent_and_never_logged():
    events = []

    def handler(request):
        assert request.headers["authorization"] == "cs_key"
        return httpx.Response(200, json={"id": "a", "actor_type": "agent"})

    assert client(handler, events).me()["id"] == "a"
    assert "cs_key" not in repr(events)


def test_human_token_is_refused():
    with pytest.raises(PlatformError, match="not a human token"):
        client(lambda r: httpx.Response(200, json={"actor_type": "human"})).me()


def test_reads_retry_on_rate_limit_and_server_errors():
    statuses = [429, 503, 200]

    def handler(request):
        return httpx.Response(statuses.pop(0), json=[])

    assert client(handler).papers() == []
    assert statuses == []


def test_failed_write_is_not_repeated_and_marked_uncertain():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(502, json={"detail": "bad gateway"})

    with pytest.raises(PlatformError) as error:
        client(handler).post_argument({"paper_id": "p"})
    assert len(calls) == 1
    assert error.value.uncertain


def test_rejected_write_carries_status_and_detail():
    def handler(request):
        return httpx.Response(409, json={"detail": "three live arguments"})

    with pytest.raises(PlatformError) as error:
        client(handler).post_argument({"paper_id": "p"})
    assert error.value.status == 409
    assert error.value.detail == "three live arguments"
    assert not error.value.uncertain


def test_download_resolves_relative_storage_urls_without_auth(tmp_path):
    events = []

    def handler(request):
        assert str(request.url) == "https://koala.test/storage/pdfs/x.pdf"
        assert "authorization" not in request.headers
        return httpx.Response(200, content=b"%PDF-1.4 data")

    digest = client(handler, events).download("/storage/pdfs/x.pdf", tmp_path / "x.pdf")
    assert (tmp_path / "x.pdf").read_bytes() == b"%PDF-1.4 data"
    assert events[-1]["sha256"] == digest
    assert not list(tmp_path.glob("*.part"))


def test_failed_download_leaves_no_file(tmp_path):
    with pytest.raises(PlatformError):
        client(lambda r: httpx.Response(404)).download(
            "/storage/x.pdf", tmp_path / "x.pdf"
        )
    assert list(tmp_path.iterdir()) == []


def test_key_is_required():
    with pytest.raises(ValueError, match="KOALA_AGENT_API_KEY"):
        PlatformClient("")
