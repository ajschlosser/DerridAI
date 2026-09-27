# Copyright 2026 Aaron John Schlosser, PhD.
"""Sources workspace and Corpus Capture routes: compact rows, honest refusals, background jobs.

Why: the Sources table pages through hundreds of sources, so a row must never carry the
source text or blocks. Deleting a source a build still uses must be refused with its
reason, never skipped silently. Capture work runs as a cancellable background job.
How: the route functions are called directly against a throwaway asset directory and
capture store; nothing reaches a network or the shared corpus.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from _capture_support import FakeProvider, FakeRegistrar, author, candidate
from app.capture_models import CaptureCreate, CaptureSelectionPatch, SourceBulkDelete
from app.capture_store import CaptureStore
from app.job_capture import CaptureJobManager
from app.routers import sources as routes
from app.source_capture import CorpusCaptureService
from app.source_identity import CaptureOptions
from fastapi import HTTPException
from pydantic import ValidationError

TEXT = "It was not the first time the city had refused."


def _asset(root, asset_id, **catalog):
    meta = {
        "asset_id": asset_id,
        "filename": f"{asset_id}.txt",
        "sha256": "ab" * 32,
        "created_at": catalog.pop("created_at", "2026-09-01T00:00:00+00:00"),
        "media_kind": catalog.pop("media_kind", "text"),
        "text": TEXT,
        "blocks": [{"text": TEXT, "page": 1}],
        "catalog_metadata": catalog,
    }
    (root / f"{asset_id}.json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    assets = tmp_path / "assets"
    assets.mkdir()
    metas = {
        "pdf-a": _asset(assets, "pdf-a", provider="gutenberg", title="Also sprach Zarathustra", document_languages=["de"], original_language="de", relationship_to_work="original_language_edition", contribution_role="author", created_at="2026-09-01"),
        "pdf-b": _asset(assets, "pdf-b", provider="wikisource", title="Thus Spake Zarathustra", document_languages=["en"], original_language="de", relationship_to_work="translation", contribution_role="author", created_at="2026-09-02"),
        "pdf-c": _asset(assets, "pdf-c", provider="wikisource", title="Ainsi parlait Zarathoustra", document_languages=["fr"], original_language="de", relationship_to_work="translation", created_at="2026-09-03"),
    }
    builds = [{"build_id": "b1", "asset_id": "pdf-a", "status": "completed", "created_at": "2026-09-04", "record_count": 12}]

    def get_asset(asset_id):
        if asset_id not in metas:
            raise KeyError(asset_id)
        return metas[asset_id]

    def list_builds(offset=0, limit=100, asset_id=None):
        return {"items": [b for b in builds if asset_id in (None, b["asset_id"])]}

    monkeypatch.setattr(routes, "pdf_corpus_repository", SimpleNamespace(root=tmp_path, get_asset=get_asset, list_builds=list_builds))
    store = CaptureStore(tmp_path / "captures.sqlite")
    monkeypatch.setattr(routes, "capture_store", store)
    return store


def _list(**params):
    defaults = {"q": "", "provider": None, "document_language": None, "original_language": None, "capture_id": None, "build_status": None, "work": None, "relationship": None, "role": None, "media_kind": None, "author": "", "ids": None, "sort": "added", "order": "desc", "offset": 0, "limit": 50}
    return routes.get_sources(**{**defaults, **params})


def test_source_rows_are_compact_and_never_carry_text_or_blocks(workspace):
    result = _list()
    assert result["total"] == result["all_total"] == 3
    serialized = json.dumps(result)
    assert TEXT not in serialized and '"blocks"' not in serialized
    by_id = {row["source_document_id"]: row for row in result["items"]}
    assert by_id["pdf-a"]["build_status"] == "built" and by_id["pdf-a"]["build_count"] == 1
    assert by_id["pdf-b"]["build_status"] == "not_built"
    assert result["facets"]["document_language"] == {"de": 1, "en": 1, "fr": 1}


def test_document_and_original_language_are_separate_filters(workspace):
    assert {r["source_document_id"] for r in _list(original_language="de")["items"]} == {"pdf-a", "pdf-b", "pdf-c"}
    assert [r["source_document_id"] for r in _list(document_language="de")["items"]] == ["pdf-a"]
    assert [r["source_document_id"] for r in _list(relationship="translation", document_language="en,fr", sort="title", order="asc")["items"]] == ["pdf-c", "pdf-b"]


def test_sort_pagination_and_explicit_ids(workspace):
    page = _list(sort="added", order="desc", offset=1, limit=1)
    assert (page["total"], [r["source_document_id"] for r in page["items"]]) == (3, ["pdf-b"])
    chosen = _list(ids="pdf-c,pdf-a", limit=1)
    assert {r["source_document_id"] for r in chosen["items"]} == {"pdf-a", "pdf-c"}


def test_source_detail_reports_provenance_and_builds_without_text(workspace):
    detail = routes.get_source_detail("pdf-a")
    assert detail["sha256"] == "ab" * 32
    assert detail["builds"] == [{"build_id": "b1", "status": "completed", "created_at": "2026-09-04", "record_count": 12}]
    assert "text" not in detail and "blocks" not in detail
    with pytest.raises(HTTPException) as error:
        routes.get_source_detail("pdf-missing")
    assert error.value.status_code == 404


def test_bulk_delete_reports_each_refusal_with_its_reason(monkeypatch):
    def discard(source_id, cascade=False):
        assert cascade is False
        if source_id == "pdf-used":
            raise ValueError("1 build(s) still use this source; delete them too to remove it.")
        if source_id == "pdf-gone":
            raise KeyError(source_id)
        return {"deleted": [source_id]}

    monkeypatch.setattr(routes, "pdf_corpus_builds", SimpleNamespace(discard_source=discard))
    result = routes.bulk_delete_sources(SourceBulkDelete(source_document_ids=["pdf-free", "pdf-used", "pdf-gone", "pdf-free"]))
    assert result["items"] == [
        {"source_document_id": "pdf-free", "deleted": True, "removed": ["pdf-free"]},
        {"source_document_id": "pdf-used", "deleted": False, "reason": "in_use", "message": "1 build(s) still use this source; delete them too to remove it."},
        {"source_document_id": "pdf-gone", "deleted": False, "reason": "not_found"},
    ]


def test_request_schemas_reject_invalid_identity_and_languages():
    with pytest.raises(ValidationError):
        CaptureCreate(wikidata_qid="Q9358 OR 1=1")
    with pytest.raises(ValidationError):
        CaptureCreate(wikidata_qid="Q9358", options={"languages": ["German"]})
    with pytest.raises(ValidationError):
        CaptureCreate(wikidata_qid="Q9358", options={"providers": ["archive_org"]})
    assert CaptureCreate(wikidata_qid="Q9358", options={"languages": []}).options.languages is None
    with pytest.raises(ValidationError):
        CaptureSelectionPatch(candidate_ids=["x"])


def _jobs(tmp_path, items):
    store = CaptureStore(tmp_path / "jobs.sqlite")
    service = CorpusCaptureService(
        store,
        provider_factory=lambda name, cancelled: FakeProvider(name, items if name == "gutenberg" else []),
        registrar=FakeRegistrar(),
        identity_enricher=lambda found, who, cancelled: [],
        sleep=lambda _s: None,
    )
    return store, service, CaptureJobManager(service)


def test_capture_jobs_discover_then_acquire_in_the_background(tmp_path):
    store, service, jobs = _jobs(tmp_path, [candidate("1", "A"), candidate("2", "B")])
    capture_id = service.create(author(), CaptureOptions())["capture_id"]
    with pytest.raises(ValueError, match="Discover sources"):
        jobs.start(capture_id, "acquire")
    job = jobs.wait(jobs.start(capture_id, "discover", owner="admin")["id"])
    assert (job["type"], job["status"], job["mode"]) == ("corpus_capture", "completed", "discover")
    assert store.get_capture(capture_id)["status"] == "awaiting_review"
    job = jobs.wait(jobs.start(capture_id, "acquire")["id"])
    assert job["status"] == "completed"
    assert store.get_capture(capture_id)["summary"]["acquisition"] == {"registered": 2}
    assert jobs.active_for(capture_id) is None
    with pytest.raises(ValueError):
        jobs.start(capture_id, "delete-everything")


def test_capture_routes_refuse_conflicting_work(tmp_path, monkeypatch):
    store, service, jobs = _jobs(tmp_path, [candidate("1", "A")])
    monkeypatch.setattr(routes, "capture_store", store)
    monkeypatch.setattr(routes, "capture_service", service)
    monkeypatch.setattr(routes, "capture_jobs", jobs)
    capture_id = service.create(author(), CaptureOptions())["capture_id"]
    service.discover(capture_id)
    service.set_selection(capture_id, None, False)
    request = SimpleNamespace(state=SimpleNamespace(user=SimpleNamespace(username="admin")))

    with pytest.raises(HTTPException) as error:
        routes.acquire_capture(capture_id, request)
    assert (error.value.status_code, error.value.detail["code"]) == (409, "nothing_selected")
    with pytest.raises(HTTPException) as error:
        routes.retry_capture(capture_id, request)
    assert error.value.detail["code"] == "nothing_failed"
    with pytest.raises(HTTPException) as error:
        routes.get_capture("cc_missing")
    assert error.value.status_code == 404

    view = routes.get_capture(capture_id)
    assert view["active_job"] is None
    page = routes.list_candidates(capture_id, offset=0, limit=10, provider=None, language=None, role=None, selection=None, acquisition=None)
    assert page["total"] == 1 and "discovery_evidence" in page["items"][0]
    listed = routes.list_captures(limit=10)["items"][0]
    assert listed["author"] == {"canonical_name": "Friedrich Nietzsche", "wikidata_qid": "Q9358", "birth_year": 1844, "death_year": 1900}
    assert routes.delete_capture(capture_id) == {"deleted": capture_id}
