# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import pytest

from app import chroma_store
from app.chroma_store import Embeddings
from app.system_store import system_store


def test_profile_embedding_uses_stored_ollama_endpoint_and_selected_model(monkeypatch):
    monkeypatch.setattr(
        system_store,
        "researcher_profile",
        lambda profile_id: {
            "id": profile_id,
            "type": "ollama",
            "base_url": "http://ollama.example:11434",
            "model": "profile-default",
        },
    )
    embeddings = Embeddings()
    calls = []

    def fake_ollama(texts, *, model, base_url=None):
        calls.append((texts, model, base_url))
        return [[0.1, 0.2] for _ in texts]

    monkeypatch.setattr(embeddings, "_ollama", fake_ollama)

    result = embeddings.embed_query(
        "test passage",
        provider="profile:Lab-Ollama",
        model="nomic-embed-text",
    )

    assert result == [0.1, 0.2]
    assert calls == [
        (
            ["test passage"],
            "nomic-embed-text",
            "http://ollama.example:11434",
        )
    ]


def test_profile_embedding_uses_stored_openai_compatible_configuration(monkeypatch):
    monkeypatch.setattr(
        system_store,
        "researcher_profile",
        lambda profile_id: {
            "id": profile_id,
            "type": "openai",
            "base_url": "https://example.invalid/v1",
            "api_key": "test-key",
            "model": "text-embedding-3-small",
        },
    )
    embeddings = Embeddings()
    calls = []

    def fake_openai(texts, *, model, base_url, api_key=""):
        calls.append((texts, model, base_url, api_key))
        return [[0.4, 0.5] for _ in texts]

    monkeypatch.setattr(embeddings, "_openai_compatible", fake_openai)

    result = embeddings.embed_query(
        "test passage",
        provider="profile:OpenAI-Lab",
    )

    assert result == [0.4, 0.5]
    assert calls == [
        (
            ["test passage"],
            "text-embedding-3-small",
            "https://example.invalid/v1",
            "test-key",
        )
    ]


def test_ollama_embedding_404_reports_modern_and_legacy_endpoint_failure(monkeypatch):
    calls: list[str] = []

    class MissingResponse:
        status_code = 404
        text = '{"error":"not found"}'

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, **kwargs):
            calls.append(url)
            return MissingResponse()

    monkeypatch.setattr(chroma_store.httpx, "Client", FakeClient)
    embeddings = Embeddings()

    with pytest.raises(RuntimeError) as exc:
        embeddings._ollama(
            ["test passage"],
            model="missing-embedding-model",
            base_url="http://ollama.example:11434",
        )

    message = str(exc.value)
    assert "both /api/embed and the legacy /api/embeddings endpoint returned 404" in message
    assert "missing-embedding-model" in message
    assert calls == [
        "http://ollama.example:11434/api/embed",
        "http://ollama.example:11434/api/embeddings",
    ]
