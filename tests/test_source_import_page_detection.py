# Copyright 2026 Aaron John Schlosser, PhD.
"""Importing a URL, Wikisource page or Gutenberg text with model-assisted page numbers uses the browser's profile.

Why: administrator provider profiles live in the browser, so the server cannot resolve them by ID. The import sent
only the ID, and every Wikisource/URL import with "let a model help find page numbers" on failed with HTTP 400
("The selected LLM provider profile is not available"). The import now carries the profile's connection, as a build
does.
How: calls the import routes with a throwaway repository and a stubbed fetch, and records the request the page-number
chooser receives.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.models import GutenbergImport, PdfSourceUrlImport  # noqa: E402
from app.routers import corpus as routes  # noqa: E402
from fastapi import HTTPException  # noqa: E402

BROWSER_PROFILE = {
    "provider_profile_id": "admin-openai",
    "provider": "openai",
    "model": "gpt-test",
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-browser",
}


@pytest.fixture
def captured(monkeypatch):
    seen: dict[str, object] = {}
    monkeypatch.setattr("app.routers.corpus.system_store.researcher_profile", lambda profile_id: None)
    monkeypatch.setattr(
        routes.pdf_corpus_builds, "page_marker_chooser", lambda request: seen.setdefault("request", request)
    )
    monkeypatch.setattr(
        routes, "fetch_source_url", lambda url, max_bytes: (b"<p>Text</p>", "page.html", "text/html")
    )
    monkeypatch.setattr(routes, "load_gutenberg_etext", lambda etext_id: ("Text", {"title": "A book"}))

    def save_asset(data, **kwargs):
        seen["page_llm"] = kwargs.get("page_llm")
        return {"asset_id": "a1"}

    monkeypatch.setattr(routes.pdf_corpus_repository, "save_asset", save_asset)
    return seen


def test_a_wikisource_import_uses_the_browser_profile_connection(captured):
    body = PdfSourceUrlImport(
        url="https://en.wikisource.org/wiki/Balzac", page_number_detection="auto_llm", **BROWSER_PROFILE
    )
    assert routes.import_pdf_asset_url(body) == {"asset_id": "a1"}
    request = captured["request"]
    assert request["provider"] == "openai"
    assert request["model"] == "gpt-test"
    assert request["api_key"] == "sk-browser"
    assert captured["page_llm"] is request


def test_a_gutenberg_import_uses_the_browser_profile_connection(captured):
    body = GutenbergImport(etext_id=1342, page_number_detection="auto_llm", **BROWSER_PROFILE)
    routes.import_gutenberg_text(body)
    assert captured["request"]["base_url"] == "https://api.openai.com/v1"


def test_an_unknown_profile_without_a_connection_still_fails_explicitly(captured):
    body = PdfSourceUrlImport(
        url="https://en.wikisource.org/wiki/Balzac",
        page_number_detection="auto_llm",
        provider_profile_id="missing",
    )
    with pytest.raises(HTTPException) as caught:
        routes.import_pdf_asset_url(body)
    assert caught.value.status_code == 400
    assert "not available" in str(caught.value.detail)


def test_deterministic_page_detection_needs_no_provider(captured):
    body = PdfSourceUrlImport(url="https://en.wikisource.org/wiki/Balzac", page_number_detection="auto")
    routes.import_pdf_asset_url(body)
    assert captured["page_llm"] is None
    assert "request" not in captured
