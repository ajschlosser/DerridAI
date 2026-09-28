# Copyright 2026 Aaron John Schlosser, PhD.
"""Provider-neutral source APIs: providers, author resolution, Corpus Capture and the Sources workspace.

The legacy per-item ``/api/pdf/gutenberg|wikisource`` routes stay in ``corpus.py``;
new UI uses these. All routes are administrator-only through the route policy.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ..capture_models import CaptureCreate, CaptureSelectionPatch, SourceBulkDelete
from ..corpus_builder import pdf_corpus_builds, pdf_corpus_repository
from ..http_auth import request_user
from ..services import capture_jobs, capture_service, capture_store
from ..source_identity import CaptureError, CaptureErrorCode, CaptureOptions
from ..source_provider import ProviderHttp
from ..source_registry import list_sources

logger = logging.getLogger(__name__)
router = APIRouter(tags=["corpus-sources"])

_STATUS = {
    CaptureErrorCode.AUTHOR_NOT_FOUND: 404,
    CaptureErrorCode.SOURCE_NOT_FOUND: 404,
    CaptureErrorCode.IDENTITY_MISMATCH: 422,
    CaptureErrorCode.AMBIGUOUS_AUTHOR: 422,
    CaptureErrorCode.INVALID_OPTIONS: 422,
    CaptureErrorCode.UNSUPPORTED_SOURCE: 422,
    CaptureErrorCode.RATE_LIMITED: 429,
    CaptureErrorCode.NETWORK_TIMEOUT: 504,
    CaptureErrorCode.AUDIO_PROVIDER_NOT_CONFIGURED: 400,
    CaptureErrorCode.AUDIO_PROVIDER_UNAVAILABLE: 503,
    CaptureErrorCode.AUDIO_TRANSCRIPTION_FAILED: 502,
}


def _capture_error(exc: CaptureError) -> HTTPException:
    if exc.detail:
        logger.info("Corpus Capture %s: %s", exc.code, exc.detail[:500])
    return HTTPException(status_code=_STATUS.get(exc.code, 502), detail={"code": str(exc.code), "message": exc.message})


def _not_found(what: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "not_found", "message": f"{what} not found."})


# --- Providers and authors -------------------------------------------------------------


@router.get("/api/corpus/source-providers")
def source_providers() -> dict[str, Any]:
    """Provider capabilities; the Wikisource project list is discovered, never hard-coded in the browser."""
    from ..gutenberg_catalogue import gutenberg_offline
    from ..source_wikisource import discover_projects

    status = gutenberg_offline.status()
    projects = discover_projects()
    return {
        "items": [
            {
                "provider": "gutenberg",
                "catalogue_ready": bool(status.get("search_ready")),
                "catalogue_refreshed_at": (status.get("catalogue") or {}).get("refreshed_at"),
                "local_collection_ready": bool(status.get("ready")),
            },
            {
                "provider": "wikisource",
                "projects": [{"code": p["code"], "name": p["name"]} for p in projects["projects"]],
                "projects_authoritative": projects["authoritative"],
            },
        ]
    }


@router.get("/api/corpus/authors/search")
def search_authors(q: str = Query(min_length=1, max_length=200), language: str = Query(default="en", pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$"), limit: int = Query(default=10, ge=1, le=20)) -> dict[str, Any]:
    from ..source_wikidata import search_authors as wikidata_search

    try:
        people = wikidata_search(ProviderHttp("wikimedia"), q, language=language, limit=limit)
    except CaptureError as exc:
        raise _capture_error(exc) from exc
    return {"items": [person.to_dict() for person in people]}


# --- Captures ---------------------------------------------------------------------------------


def _capture_view(capture: dict[str, Any]) -> dict[str, Any]:
    return {**capture, "active_job": capture_jobs.active_for(capture["capture_id"])}


def _get_capture(capture_id: str) -> dict[str, Any]:
    try:
        return capture_store.get_capture(capture_id)
    except KeyError as exc:
        raise _not_found("Capture") from exc


@router.post("/api/corpus/captures")
def create_capture(body: CaptureCreate, request: Request) -> dict[str, Any]:
    from ..source_wikidata import resolve_author

    try:
        # The person is resolved server-side from the chosen QID; the browser never supplies identity data.
        author = resolve_author(ProviderHttp("wikimedia"), body.wikidata_qid, language=body.ui_language)
        options = CaptureOptions.from_dict(body.options.model_dump())
        options.validate_for_author(author)
        capture = capture_service.create(author, options)
    except CaptureError as exc:
        raise _capture_error(exc) from exc
    if body.start_discovery:
        capture_jobs.start(capture["capture_id"], "discover", owner=request_user(request).username)
    return _capture_view(capture_store.get_capture(capture["capture_id"]))


@router.get("/api/corpus/captures")
def list_captures(limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    keys = ("capture_id", "author", "status", "phase", "created_at", "discovery_completed_at", "last_refreshed_at", "summary")
    return {"items": [{k: capture.get(k) for k in keys} | {"author": {k: (capture.get("author") or {}).get(k) for k in ("canonical_name", "wikidata_qid", "birth_year", "death_year")}} for capture in capture_store.list_captures(limit)]}


@router.get("/api/corpus/captures/{capture_id}")
def get_capture(capture_id: str) -> dict[str, Any]:
    return _capture_view(_get_capture(capture_id))


@router.delete("/api/corpus/captures/{capture_id}")
def delete_capture(capture_id: str) -> dict[str, Any]:
    _get_capture(capture_id)
    if capture_jobs.active_for(capture_id):
        raise HTTPException(status_code=409, detail={"code": "capture_active", "message": "Cancel the running capture operation first."})
    capture_store.delete_capture(capture_id)
    return {"deleted": capture_id}


_CANDIDATE_FIELDS = (
    "candidate_id", "provider", "provider_item_id", "title", "document_author", "contribution_role", "document_languages",
    "original_language", "source_project_language", "translators", "editors", "publication_year", "edition", "source_uri",
    "catalog_uri", "wikidata_work_id", "wikidata_edition_id", "canonical_work_id", "relationship_to_work",
    "reconciliation_status", "possible_duplicates", "identity_confidence", "selection_status", "selection_reason",
    "acquisition_status", "source_document_id", "digital_duplicate_of", "error", "upstream_status", "metadata_changed_fields",
    "discovery_method", "discovery_evidence", "discovered_at", "acquired_at", "rights_status", "rights_source",
)


@router.get("/api/corpus/captures/{capture_id}/candidates")
def list_candidates(
    capture_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    provider: str | None = Query(default=None, max_length=40),
    language: str | None = Query(default=None, max_length=20),
    role: str | None = Query(default=None, max_length=40),
    selection: str | None = Query(default=None, pattern="^(selected|excluded)$"),
    acquisition: str | None = Query(default=None, max_length=40),
) -> dict[str, Any]:
    _get_capture(capture_id)
    rows = capture_store.candidates(capture_id)
    rows = [
        row for row in rows
        if (not provider or row.get("provider") == provider)
        and (not language or language in (row.get("document_languages") or []))
        and (not role or row.get("contribution_role") == role)
        and (not selection or row.get("selection_status") == selection)
        and (not acquisition or row.get("acquisition_status") == acquisition)
    ]
    # Work groups stay contiguous across pages: sort by group, then discovery order.
    rows.sort(key=lambda row: (str(row.get("canonical_work_id") or ""), int(row.get("sort_index") or 0)))
    page = rows[offset : offset + limit]
    return {"items": [{k: row.get(k) for k in _CANDIDATE_FIELDS} for row in page], "total": len(rows), "offset": offset, "limit": limit}


@router.patch("/api/corpus/captures/{capture_id}/selection")
def patch_selection(capture_id: str, body: CaptureSelectionPatch) -> dict[str, Any]:
    _get_capture(capture_id)
    if capture_jobs.active_for(capture_id):
        raise HTTPException(status_code=409, detail={"code": "capture_active", "message": "Wait for the running operation to finish."})
    try:
        return _capture_view(capture_service.set_selection(capture_id, body.candidate_ids, body.selected))
    except KeyError as exc:
        raise _not_found("Candidate") from exc


def _start(capture_id: str, kind: str, request: Request) -> dict[str, Any]:
    _get_capture(capture_id)
    try:
        capture_jobs.start(capture_id, kind, owner=request_user(request).username)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "capture_conflict", "message": str(exc)}) from exc
    return _capture_view(capture_store.get_capture(capture_id))


@router.post("/api/corpus/captures/{capture_id}/discover")
def discover_capture(capture_id: str, request: Request) -> dict[str, Any]:
    return _start(capture_id, "discover", request)


@router.post("/api/corpus/captures/{capture_id}/refresh")
def refresh_capture(capture_id: str, request: Request) -> dict[str, Any]:
    return _start(capture_id, "refresh", request)


@router.post("/api/corpus/captures/{capture_id}/acquire")
def acquire_capture(capture_id: str, request: Request) -> dict[str, Any]:
    if not capture_service.acquisition_queue(capture_id):
        _get_capture(capture_id)
        raise HTTPException(status_code=409, detail={"code": "nothing_selected", "message": "Select at least one source to capture."})
    return _start(capture_id, "acquire", request)


@router.post("/api/corpus/captures/{capture_id}/retry")
def retry_capture(capture_id: str, request: Request) -> dict[str, Any]:
    if not capture_service.acquisition_queue(capture_id, retry_failed_only=True):
        _get_capture(capture_id)
        raise HTTPException(status_code=409, detail={"code": "nothing_failed", "message": "No failed sources to retry."})
    return _start(capture_id, "retry", request)


@router.post("/api/corpus/captures/{capture_id}/cancel")
def cancel_capture(capture_id: str) -> dict[str, Any]:
    _get_capture(capture_id)
    capture_jobs.cancel_capture(capture_id)
    return _capture_view(capture_store.get_capture(capture_id))


# --- Sources workspace ----------------------------------------------------------------------


def _csv(value: str | None) -> list[str]:
    return [item for item in (value or "").split(",") if item][:50]


@router.get("/api/corpus/sources")
def get_sources(
    q: str = Query(default="", max_length=200),
    provider: str | None = None,
    document_language: str | None = None,
    original_language: str | None = None,
    capture_id: str | None = None,
    build_status: str | None = None,
    work: str | None = Query(default=None, max_length=200),
    relationship: str | None = None,
    role: str | None = None,
    media_kind: str | None = None,
    author: str = Query(default="", max_length=200),
    ids: str | None = Query(default=None, max_length=20000),
    sort: str = Query(default="added", pattern="^(title|added|provider|language|author)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    filters = {
        "q": q, "author": author, "provider": _csv(provider), "document_language": _csv(document_language),
        "original_language": _csv(original_language), "capture_id": _csv(capture_id), "build_status": _csv(build_status),
        "work": _csv(work), "relationship": _csv(relationship), "role": _csv(role), "media_kind": _csv(media_kind),
    }
    result = list_sources(
        pdf_corpus_repository.root / "assets",
        builds=pdf_corpus_repository.list_builds(offset=0, limit=100000)["items"],
        links=capture_store.links_for_sources(),
        filters=filters, sort=sort, descending=order == "desc", offset=0 if ids else offset, limit=100000 if ids else limit,
    )
    if ids:
        wanted = {item for item in ids.split(",") if item}
        result["items"] = [row for row in result["items"] if row["source_document_id"] in wanted]
        result["total"] = len(result["items"])
    return result


@router.get("/api/corpus/sources/{source_id}")
def get_source_detail(source_id: str) -> dict[str, Any]:
    """Identity, language, provider, provenance and processing facts — never the source text."""
    try:
        asset = pdf_corpus_repository.get_asset(source_id)
    except KeyError as exc:
        raise _not_found("Source") from exc
    builds = pdf_corpus_repository.list_builds(offset=0, limit=100000, asset_id=source_id)["items"]
    keep = ("asset_id", "sha256", "filename", "created_at", "media_type", "media_kind", "content_suffix", "source_url", "page_count", "block_count", "ocr_pages", "extraction_provenance", "catalog_metadata", "initial_metadata", "derived_from_asset_id", "page_number_detection")
    detail = {k: asset.get(k) for k in keep}
    catalog = dict(detail.get("catalog_metadata") or {})
    for bulky in ("wikisource_pages", "catalog_record"):
        if isinstance(catalog.get(bulky), list):
            catalog[f"{bulky}_count"] = len(catalog.pop(bulky))
    proofread = catalog.get("proofread")
    if isinstance(proofread, dict):
        catalog["proofread"] = {k: v for k, v in proofread.items() if k != "pages"}
    detail["catalog_metadata"] = catalog
    initial = dict(detail.get("initial_metadata") or {})
    initial.pop("field_provenance", None)
    detail["initial_metadata"] = {k: v for k, v in initial.items() if isinstance(v, (str, int, float)) or v is None}
    detail["captures"] = capture_store.links_for_sources([source_id]).get(source_id, [])
    detail["builds"] = [{"build_id": b.get("build_id"), "status": b.get("status"), "created_at": b.get("created_at"), "record_count": b.get("record_count")} for b in builds]
    return detail


@router.post("/api/corpus/sources/bulk-delete")
def bulk_delete_sources(body: SourceBulkDelete) -> dict[str, Any]:
    """Delete sources that no build uses; each refusal is reported with its reason, never skipped silently."""
    results = []
    for source_id in dict.fromkeys(body.source_document_ids):
        try:
            outcome = pdf_corpus_builds.discard_source(source_id, cascade=False)
            results.append({"source_document_id": source_id, "deleted": True, "removed": outcome["deleted"]})
        except KeyError:
            results.append({"source_document_id": source_id, "deleted": False, "reason": "not_found"})
        except ValueError as exc:
            results.append({"source_document_id": source_id, "deleted": False, "reason": "in_use", "message": str(exc)})
    return {"items": results}
