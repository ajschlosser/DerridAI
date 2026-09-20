# Copyright 2026 Aaron John Schlosser, PhD.
"""Failures that could affect scholarship must be surfaced, not swallowed.

Why: AGENTS.md forbids silently swallowing errors that can affect segmentation, metadata,
attribution, citation, evidence, or durable operation state. Each test injects a specific failure
and asserts it surfaces as an error or a build warning.
How: monkeypatches the failing dependency (repository read, Chroma client, job database) and calls
the real code path; small fake classes stand in for storage.
"""

from __future__ import annotations

from pathlib import Path
import sys
import threading
import types

import pytest

sys.modules.setdefault("chromadb", types.SimpleNamespace())
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import corpus_builder as cb
from app import chroma_store as cs
from app import jobs
from app.models import UpsertJobCreate


def make_build(repo: cb.PdfCorpusRepository) -> dict:
    """Create a temp asset and a one-block build for the tests below."""
    asset_id = "asset-0610-failure"
    asset = {
        "asset_id": asset_id,
        "sha256": "sha",
        "filename": "book.pdf",
        "page_count": 1,
        "block_count": 1,
        "ocr_pages": 0,
        "warnings": [],
        "metadata": {},
        "pages": [{"pdf_page": 1, "width": 600, "height": 800}],
    }
    cb._json_write(repo.asset_meta_path(asset_id), asset)
    repo.asset_blocks_path(asset_id).write_text(
        '{"block_id":"b1","page":1,"bbox":[0,0,100,100],"type":"paragraph","text":"Text.","extraction_method":"native","confidence":1.0}\n',
        encoding="utf-8",
    )
    return repo.create_build({
        "asset_id": asset_id,
        "source_sha256": "sha",
        "source_filename": "book.pdf",
        "source_page_count": 1,
        "source_block_count": 1,
        "schema_version": cb.SCHEMA_VERSION,
        "profile_id": cb.PROFILE_VERSION,
        "profile_version": 12,
        "app_version": cb.APP_VERSION,
        "provider": "ollama",
        "model": "test-model",
        "request": {"provider_profile_id": "primary"},
        "manifest": {},
        "validation": {"valid": True},
    })


def test_metadata_enrichment_propagates_build_state_refresh_failure(tmp_path: Path, monkeypatch):
    """If the current build state cannot be read, enrichment raises instead of using stale state."""
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = make_build(repo)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    monkeypatch.setattr(repo, "get_build", lambda _build_id: (_ for _ in ()).throw(OSError("state unavailable")))
    record = {"record_id": "r1", "text": "Text.", "source_block_ids": ["b1"], "source_spans": []}

    with pytest.raises(RuntimeError, match="refresh corpus build state"):
        manager._enrich_record(
            record,
            {},
            {"provider": "ollama", "model": "test-model", "enrichment_mode": "fast"},
            build_id=build["build_id"],
        )


def test_metadata_family_stops_when_live_reviewer_ownership_cannot_be_read(tmp_path: Path, monkeypatch):
    """If human ownership of fields cannot be checked, the LLM family is not run.

    Why: without that check the model could overwrite a reviewer's decision.
    """
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = make_build(repo)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    monkeypatch.setattr(repo, "load_records", lambda _build_id: (_ for _ in ()).throw(OSError("records unavailable")))
    called = {"chat": False}
    monkeypatch.setattr(manager, "_chat_json", lambda *args, **kwargs: called.__setitem__("chat", True))

    record = {"record_id": "r1", "text": "Text."}
    results = manager._execute_metadata_tasks(
        record,
        {"provider": "ollama", "model": "test-model", "enrichment_mode": "deep"},
        [("discourse", "prompt", cb.DocumentManifestModel, 64, "test_schema")],
        build["build_id"],
        None,
    )

    assert called["chat"] is False
    assert record["metadata_stage_status"]["discourse"] == "needs_review"
    assert record["metadata_execution_ledger"]["discourse"]["reason_code"] == "ownership_state_unavailable"
    assert isinstance(results[0][2], RuntimeError)
    refreshed = repo.get_build(build["build_id"])
    assert any("Could not verify live reviewer ownership" in warning for warning in refreshed.get("warnings", []))


class NotFoundError(Exception):
    """Stands in for Chroma's "collection does not exist" exception."""
    pass


class FakeCacheClient:
    """Chroma client whose get_collection always raises the given error."""
    def __init__(self, exc: Exception):
        self.exc = exc

    def get_collection(self, *, name: str):
        raise self.exc


def bare_store(client) -> cs.ChromaStore:
    """Build a ChromaStore without running __init__, wired to a fake client."""
    store = object.__new__(cs.ChromaStore)
    store._client = client
    return store


def test_response_cache_distinguishes_absence_from_storage_failure():
    """A missing response-cache collection means "empty"; any other error is raised."""
    missing = bare_store(FakeCacheClient(NotFoundError("collection does not exist")))
    result = missing.get_response_cache_records()
    assert result["exists"] is False

    broken = bare_store(FakeCacheClient(RuntimeError("disk I/O error")))
    with pytest.raises(RuntimeError, match="Could not open response-cache collection"):
        broken.get_response_cache_records()


class BrokenSearchCollection:
    """Collection whose reads always fail."""
    def get(self, **_kwargs):
        raise RuntimeError("storage read failed")


def test_keyword_search_does_not_hide_storage_failure(monkeypatch):
    """Keyword search raises the storage error instead of returning "no results"."""
    store = object.__new__(cs.ChromaStore)
    monkeypatch.setattr(store, "_collection", lambda _name: BrokenSearchCollection())
    with pytest.raises(RuntimeError, match="storage read failed"):
        store.keyword_search("db", "Derrida", 5)


class FailingQueueStore:
    """Store where marking the collection failed also fails (secondary failure)."""
    def set_build_status(self, _name: str, _status: str):
        return None

    def fail_sync(self, _name: str, _message: str):
        raise OSError("manifest database unavailable")


class NoopExecutor:
    """Executor that fails the test if any work is queued."""
    def submit(self, *_args, **_kwargs):
        raise AssertionError("worker must not be queued when persistence fails")


def test_vector_queue_surfaces_secondary_failure_status_persistence_error(tmp_path: Path):
    """If queuing fails and recording the failure also fails, both errors are reported.

    No worker may be queued and no spool file may be left behind.
    """
    manager = object.__new__(jobs.UpsertJobManager)
    manager._store = FailingQueueStore()
    manager._jobs = {}
    manager._lock = threading.RLock()
    manager._executor = NoopExecutor()
    manager._spool_dir = tmp_path
    manager._persist_job = lambda _job_id: (_ for _ in ()).throw(OSError("job database unavailable"))

    body = UpsertJobCreate(
        store_name="test-store",
        items=[{"key": "r1", "record": {"record_id": "r1", "text": "Text."}}],
    )
    with pytest.raises(RuntimeError, match="collection failure status could not be persisted"):
        manager.create(body)
    assert list(tmp_path.glob("*.json")) == []


def test_editorial_memory_failure_is_recorded_as_build_warning(tmp_path: Path, monkeypatch):
    """If editorial memory cannot be read, enrichment continues but the build shows a warning."""
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = make_build(repo)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    monkeypatch.setattr(repo, "load_records", lambda _build_id: (_ for _ in ()).throw(OSError("records unavailable")))

    memory = manager._editorial_memory(build["build_id"])

    assert memory == {"conventions": {}, "examples": {}, "pass_learning": {}}
    warnings = repo.get_build(build["build_id"])["warnings"]
    assert any("Editorial memory was unavailable" in item and "records unavailable" in item for item in warnings)
