"""Tests for reva.env — KOALA_BASE_URL accessor."""
from reva.env import koala_base_url


def test_koala_base_url_default(monkeypatch):
    monkeypatch.delenv("KOALA_BASE_URL", raising=False)
    assert koala_base_url() == "https://koala.science"


def test_koala_base_url_override(monkeypatch):
    monkeypatch.setenv("KOALA_BASE_URL", "https://staging.koala.science")
    assert koala_base_url() == "https://staging.koala.science"


def test_koala_base_url_empty_string_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("KOALA_BASE_URL", "")
    assert koala_base_url() == "https://koala.science"


def test_koala_base_url_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("KOALA_BASE_URL", "https://staging.koala.science/")
    assert koala_base_url() == "https://staging.koala.science"


def test_koala_base_url_strips_multiple_trailing_slashes(monkeypatch):
    monkeypatch.setenv("KOALA_BASE_URL", "https://staging.koala.science///")
    assert koala_base_url() == "https://staging.koala.science"
