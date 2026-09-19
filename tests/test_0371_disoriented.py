from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_0371_release_identity_and_notes():
    package = json.loads(text("web/package.json"))
    assert package["version"] == "0.59.0"
    assert 'version="0.59.0"' in text("api/app/main.py")
    assert "# DerridAI 0.59.0" in text("README.md")
    assert "0.37.1 — Disoriented" in text("README.md")


def test_response_cache_logical_alias_is_validated_as_physical_name():
    chroma = text("api/app/chroma_store.py")
    assert '_RESPONSE_CACHE_PUBLIC = "_response_cache"' in chroma
    assert '_RESPONSE_CACHE_STORAGE = "derridai_response_cache"' in chroma
    assert "validation_name = name if requested_name == self._RESPONSE_CACHE_PUBLIC else requested_name" in chroma
    assert 'self.upsert_many(\n            "_response_cache"' in chroma
    cache_block = chroma[chroma.index("def ensure_response_cache"):chroma.index("def cache_rag_response")]
    assert "embedding_dimension=64" in cache_block
    assert 'distance_metric="cosine"' in cache_block


def test_llm_jobs_do_not_call_upsert_spool_methods_or_persist_secrets():
    jobs = text("api/app/jobs.py")
    llm = jobs[jobs.index("class LLMJobManager"):jobs.index("class LLMToolJobManager")]
    assert "self._write_spool" not in llm
    assert "self._run_from_spool" not in llm
    assert "self._executor.submit(self._run, job_id, body)" in llm
    assert "api_key" not in llm[llm.index("request_summary = {"):llm.index("job = {")]


def test_auto_grade_retries_transient_provider_failures_and_degrades_gracefully():
    jobs = text("api/app/jobs.py")
    config = text("api/app/config.py")
    assert "RAG_AUTO_GRADE_MAX_ATTEMPTS" in config
    assert "RAG_AUTO_GRADE_RETRY_DELAY_SECONDS" in config
    assert "retrying {grade_attempt + 1}/{grade_attempts}" in jobs
    assert "Auto-grade provider unavailable" in jobs
    assert 'result["auto_grade_error_details"] = failure' in jobs
    assert "retry grading from the Response Library" in jobs


def test_vector_stores_uses_task_focused_workspace_and_progressive_disclosure():
    runtime = text("web/src/runtime/runtime.js")
    css = text("web/src/style.css")
    for token in (
        "vectorCollectionFilter",
        "data-vector-tab",
        'vectorTab==="overview"',
        'vectorTab==="data"',
        'vectorTab==="retrieval"',
        'vectorTab==="builds"',
        'vectorTab==="settings"',
        "openVectorRecordInspector",
        "openVectorRetrievalComparison",
        "vector-row-menu",
    ):
        assert token in runtime
    assert "vector-summary-grid" not in runtime[runtime.index("async function renderVector"):runtime.index("async function deleteStoreRecord")]
    assert ".vector-workspace-tabs" in css
    assert ".vector-record-inspector" in css
    assert ".vector-comparison-grid" in css


def test_mmr_handles_numpy_embedding_arrays_without_truth_value_testing():
    chroma = text("api/app/chroma_store.py")
    rag = text("api/app/rag.py")
    assert 'embedding_payload = payload.get("embeddings")' in chroma
    assert 'hasattr(embedding_payload, "tolist")' in chroma
    assert 'embedding_payload = embedding_payload.tolist()' in chroma
    assert 'if not a or not b' not in chroma[chroma.index("def _cosine"):chroma.index("def mmr_search")]
    assert 'if not a or not b' not in rag[rag.index("def _cosine"):rag.index("def _distance_similarity")]
    assert "len(a) == 0" in chroma
    assert "len(b) == 0" in chroma
    assert "len(a) == 0" in rag
    assert "len(b) == 0" in rag
