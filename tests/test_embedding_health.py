# Copyright 2026 Aaron John Schlosser, PhD.
"""The Settings embedding default is probed for real, and failures explain themselves."""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import embedding_health as health  # noqa: E402
from app.system_store import system_store  # noqa: E402


class Embedder:
    def __init__(self, error=None, size=4):
        self.error, self.size, self.calls = error, size, []

    def embed_query(self, text, *, provider=None, model=None):
        self.calls.append((provider, model))
        if self.error:
            raise self.error
        return [0.1] * self.size


def test_reachable_reports_dimension_and_uses_the_saved_settings_default():
    system_store.set_embedding_defaults("ollama", "bge-m3:latest")
    embedder = Embedder()
    result = health.check_embedding_defaults(embedder=embedder)
    assert result["reachable"] is True and result["dimension"] == 4 and result["error"] == ""
    assert embedder.calls == [("ollama", "bge-m3:latest")]


def test_a_draft_is_probed_instead_of_the_saved_default():
    system_store.set_embedding_defaults("ollama", "bge-m3:latest")
    embedder = Embedder()
    health.check_embedding_defaults("ollama", "nomic-embed-text", embedder=embedder)
    assert embedder.calls == [("ollama", "nomic-embed-text")]


def test_unreachable_server_gets_a_docker_hint():
    system_store.set_embedding_defaults("ollama", "bge-m3:latest")
    result = health.check_embedding_defaults(embedder=Embedder(httpx.ConnectError("[Errno -2] Name or service not known")))
    assert result["reachable"] is False and "host.docker.internal" in result["hint"]


def test_missing_model_says_to_pull_it():
    request = httpx.Request("POST", "http://x/api/embed")
    error = httpx.HTTPStatusError("404 model 'bge-m3' not found", request=request, response=httpx.Response(404, request=request))
    result = health.check_embedding_defaults("ollama", "bge-m3", embedder=Embedder(error))
    assert "ollama pull bge-m3" in result["hint"]


def test_precomputed_is_reported_as_unusable_for_retrieval():
    result = health.check_embedding_defaults("precomputed", embedder=Embedder(ValueError("precomputed")))
    assert result["reachable"] is False and "cannot embed query text" in result["hint"]


def test_metadata_exemplar_index_creates_its_collection_from_the_settings_default():
    from app.metadata_exemplar_retrieval import ChromaMetadataExemplarIndex

    class Store:
        def default_embedding_spec(self):
            return "profile:lab", "embed-x"

        class client:  # noqa: N801
            @staticmethod
            def get_collection(name):
                raise RuntimeError("not found")

        created = {}

        def create_store(self, name, **kwargs):
            Store.created = kwargs

        _is_missing_collection_error = None

    index = ChromaMetadataExemplarIndex(Store())
    try:
        index._ensure()
    except Exception:
        pass
    assert Store.created["embedding_provider"] == "profile:lab"
    assert Store.created["embedding_model"] == "embed-x"
