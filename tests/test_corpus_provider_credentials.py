# Copyright 2026 Aaron John Schlosser, PhD.
"""Corpus Builder must not drop an OpenAI key the browser already sent.

Why: administrator profiles keep that key in the browser. A published profile may
have no stored key, or a different one. Replacing the request key with the stored
key made OpenAI return HTTP 401. A blank request value still falls back to the store.
How: calls the resolver with a fake stored profile and checks which key survives.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.main import _resolve_pdf_corpus_provider  # noqa: E402


def _stored(monkeypatch, **profile):
    monkeypatch.setattr(
        "app.main.system_store.researcher_profile",
        lambda profile_id: {"id": profile_id, "type": "openai", "model": "stored-model", **profile},
    )


def test_a_browser_api_key_is_kept_when_the_profile_is_also_stored(monkeypatch):
    """The key and endpoint on the request are the ones OpenAI is called with."""
    _stored(monkeypatch, base_url="https://stored.example/v1", api_key="sk-stored")
    resolved = _resolve_pdf_corpus_provider({
        "provider_profile_id": "openai-1",
        "provider": "openai",
        "model": "browser-model",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-browser",
        "review_provider_profile_id": "openai-1",
        "review_provider": {"base_url": "https://api.openai.com/v1", "api_key": "sk-review"},
    })
    assert resolved["api_key"] == "sk-browser"
    assert resolved["base_url"] == "https://api.openai.com/v1"
    assert resolved["model"] == "browser-model"
    assert resolved["_review_provider"]["api_key"] == "sk-review"


def test_a_blank_request_key_uses_the_key_stored_with_the_profile(monkeypatch):
    """Omitting the key, or sending an empty string, does not hide a stored secret."""
    _stored(monkeypatch, base_url="https://stored.example/v1", api_key="sk-stored")
    resolved = _resolve_pdf_corpus_provider({
        "provider_profile_id": "openai-1",
        "api_key": "",
        "base_url": "  ",
    })
    assert resolved["api_key"] == "sk-stored"
    assert resolved["base_url"] == "https://stored.example/v1"


def test_missing_selected_profile_fails_explicitly(monkeypatch):
    monkeypatch.setattr("app.main.system_store.researcher_profile", lambda profile_id: None)
    try:
        _resolve_pdf_corpus_provider({"provider_profile_id": "removed-profile"})
    except ValueError as exc:
        assert str(exc) == "The selected LLM provider profile is not available."
    else:
        raise AssertionError("A missing provider profile must not produce a success-shaped request.")


def test_direct_provider_configuration_remains_valid_without_a_stored_profile(monkeypatch):
    """Interactive Corpus Builder actions may authenticate with browser-supplied credentials."""
    monkeypatch.setattr("app.main.system_store.researcher_profile", lambda profile_id: None)
    resolved = _resolve_pdf_corpus_provider({
        "provider_profile_id": "openai-1",
        "provider": "openai",
        "model": "browser-model",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-browser",
    })
    assert resolved["provider"] == "openai"
    assert resolved["model"] == "browser-model"
    assert resolved["base_url"] == "https://api.openai.com/v1"
    assert resolved["api_key"] == "sk-browser"
