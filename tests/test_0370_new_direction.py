from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_0370_release_identity_and_notes():
    package = json.loads(text("web/package.json"))
    assert package["version"] == "0.40.5"
    assert 'version="0.40.5"' in text("api/app/main.py")
    assert "# DerridAI Corpus Viewer 0.40.5" in text("README.md")
    assert "0.37.0 — New Direction" in text("README.md")


def test_collection_creation_is_strict_and_preflighted():
    chroma = text("api/app/chroma_store.py")
    main = text("api/app/main.py")
    create_slice = chroma[chroma.index("    def create_store("):chroma.index("    def delete_store(")]
    assert "self.client.create_collection(" in create_slice
    assert "get_or_create_collection" not in create_slice
    assert "StoreAlreadyExistsError" in create_slice
    assert '@app.post("/api/stores/preflight/embedding")' in main
    assert "status_code=409" in main


def test_manifest_contract_records_dimension_metric_source_builds_and_protection():
    chroma = text("api/app/chroma_store.py")
    for token in (
        "__derridai_manifest_version",
        "__derridai_embedding_dimension",
        "__derridai_distance_metric",
        "__derridai_retrieval_mode",
        "__derridai_source_snapshot_hash",
        "__derridai_build_history",
        "__derridai_protected",
    ):
        assert token in chroma
    assert "Embedding dimension mismatch" in chroma
    assert "immutable for manifest-backed collections" in chroma


def test_collection_name_contract_is_validated_in_api_schema():
    from app.models import StoreCreate

    with pytest.raises(ValidationError):
        StoreCreate(name="x")
    with pytest.raises(ValidationError):
        StoreCreate(name="192.168.1.1")
    with pytest.raises(ValidationError):
        StoreCreate(name="bad name")
    model = StoreCreate(name="derrida-primary")
    assert model.retrieval_mode == "hybrid"
    assert model.distance_metric == "cosine"


def test_background_vector_builds_are_spooled_and_resume_after_restart():
    jobs = text("api/app/jobs.py")
    runtime = text("web/src/legacy/runtime.js")
    assert "UPSERT_JOB_SPOOL_PATH" in jobs
    assert "_write_spool" in jobs
    assert "_resume_spooled_jobs" in jobs
    assert "Vector build restored from durable server-side spool after restart." in jobs
    assert "foregroundUpsertRows" not in runtime
    assert 'api("/api/jobs/upsert"' in runtime
    assert "Build collection in the background?" in runtime


def test_vector_store_ui_exposes_new_direction_workflow_and_retrieval_testing():
    runtime = text("web/src/legacy/runtime.js")
    for token in (
        "collection-wizard-v037",
        "Source",
        "Retrieval",
        "Review & build",
        "/api/stores/preflight/embedding",
        "Hybrid — recommended",
        "vectorRetrievalTest",
        "vectorSearchMode",
        "Manifest & builds",
        "toggleStoreProtection",
        "/protection",
        "Storage settings",
    ):
        assert token in runtime
    assert 'mode,n_results:30' in runtime


def test_hybrid_search_has_semantic_and_lexical_legs():
    chroma = text("api/app/chroma_store.py")
    main = text("api/app/main.py")
    section = chroma[chroma.index("    def hybrid_search("):chroma.index("    def _decode_result(")]
    assert "self.search(" in section
    assert "self.lexical_search(" in section
    assert "reciprocal rank" in section.lower()
    assert 'body.mode == "hybrid"' in main

def test_rag_retrieval_defaults_to_semantic_lexical_and_mmr_fusion():
    models = text("api/app/models.py")
    rag = text("api/app/rag.py")
    runtime = text("web/src/legacy/runtime.js")
    assert '["similarity", "lexical", "mmr"]' in models
    assert 'if "lexical" in request.search_types:' in rag
    assert 'store.lexical_search(' in rag
    assert 'Lexical (BM25)' in runtime
