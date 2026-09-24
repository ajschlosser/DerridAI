# Copyright 2026 Aaron John Schlosser, PhD.
"""Vector-store, record, and search API routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..chroma_store import ChromaStore, StoreAlreadyExistsError
from ..config import settings
from ..content_filter import enforce_researcher_text
from ..dependencies import (
    get_store as store_dependency,
    request_user,
    require_admin,
)
from ..models import (
    BulkUpsert,
    DeriveLanguageStoresRequest,
    EmbeddingPreflightRequest,
    RecordStatusRequest,
    RecordUpsert,
    SearchRequest,
    StoreCreate,
    StoredRecordPatch,
    StoreDriftRequest,
    StoreEmbeddingUpdate,
    StoreLanguageUpdate,
    StoreProtectionUpdate,
)
from ..researcher_view import sanitize_records_payload, summarize_record

router = APIRouter(tags=["stores"])


def _stamp_record_activity(record: dict[str, Any], username: str) -> dict[str, Any]:
    """Attach the initiating user to audit entries that arrived without one.

    Browsers normally stamp edits before sending them. Keeping this server-side
    pass at the persistence boundary preserves audit provenance for direct API
    clients and older frontends as well.
    """
    copy_record = dict(record)
    updates = copy_record.get("updates")
    if isinstance(updates, list):
        stamped = []
        for update in updates:
            if isinstance(update, dict):
                item = dict(update)
                item.setdefault("initiated_by", username)
                stamped.append(item)
            else:
                stamped.append(update)
        copy_record["updates"] = stamped
    return copy_record


@router.get("/api/stores")
def list_stores(store: ChromaStore = Depends(store_dependency)) -> dict[str, Any]:
    try:
        return {"stores": store.list_stores()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/stores")
def create_store(
    body: StoreCreate,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.create_store(
            body.name,
            body.metadata,
            description=body.description,
            embedding_provider=body.embedding_provider,
            embedding_model=body.embedding_model,
            embedding_dimension=body.embedding_dimension,
            distance_metric=body.distance_metric,
            retrieval_mode=body.retrieval_mode,
            text_field=body.text_field,
            filter_fields=body.filter_fields,
            language_codes=body.language_codes,
            collection_role=body.collection_role,
            protected=body.protected,
        )
    except StoreAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/stores/preflight/embedding")
def preflight_embedding(
    body: EmbeddingPreflightRequest,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.preflight_embedding(
            provider=body.embedding_provider,
            model=body.embedding_model,
            embedding_dimension=body.embedding_dimension,
            distance_metric=body.distance_metric,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/stores/{store_name}")
def get_store(
    store_name: str,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.get_store(store_name)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/api/stores/{store_name}/embedding")
def update_store_embedding(
    store_name: str,
    body: StoreEmbeddingUpdate,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.set_embedding(
            store_name,
            provider=body.embedding_provider,
            model=body.embedding_model,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/api/stores/{store_name}/languages")
def update_store_languages(
    store_name: str,
    body: StoreLanguageUpdate,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.set_language_tags(
            store_name,
            language_codes=body.language_codes,
            collection_role=body.collection_role,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/api/stores/{store_name}/protection")
def update_store_protection(
    store_name: str,
    body: StoreProtectionUpdate,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.set_protection(store_name, body.protected)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/stores/{store_name}/derive-languages")
def derive_language_stores(
    store_name: str,
    body: DeriveLanguageStoresRequest,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.derive_language_stores(
            store_name,
            en_name=body.en_name,
            fr_name=body.fr_name,
            overwrite=body.overwrite,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/stores/{store_name}")
def delete_store(
    store_name: str,
    force: bool = Query(default=False),
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        store.delete_store(store_name, force=force)
        return {"deleted": store_name}
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/api/stores/{store_name}/works/{work:path}")
def delete_store_work(
    store_name: str,
    work: str,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.delete_work_with_language_sync(store_name, work)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/response-cache/records")
def get_response_cache_records(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    query: str | None = Query(default=None),
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.get_response_cache_records(
            limit=limit,
            offset=offset,
            query=query,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/stores/{store_name}/records")
def get_records(
    store_name: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    work: str | None = Query(default=None),
    sort_field: str | None = Query(default=None),
    sort_dir: str = Query(default="asc"),
    filters: str | None = Query(default=None),
    include_updates: bool = Query(default=False),
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        user = request_user(request)
        parsed_filters: dict[str, str] = {}
        if filters:
            candidate = json.loads(filters)
            if not isinstance(candidate, dict):
                raise ValueError("filters must encode a JSON object")
            parsed_filters = {
                str(key): str(value)
                for key, value in candidate.items()
            }
        if user.role != "admin":
            enforce_researcher_text({"work": work, "filters": parsed_filters})

        # Audit history is an administrator-only expansion. Researcher record
        # projections remain compact even if a crafted request asks for updates.
        allow_updates = include_updates and user.role == "admin"
        result = store.get_records(
            store_name,
            limit=limit,
            offset=offset,
            work=work,
            sort_field=sort_field,
            sort_dir=sort_dir,
            filters=parsed_filters,
            include_updates=allow_updates,
        )
        if user.role != "admin":
            return sanitize_records_payload(
                result,
                max_chars=settings.researcher_text_max_chars,
            )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/stores/{store_name}/works")
def list_store_works(
    store_name: str,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return {
            "works": store.list_works(store_name),
            "stats": store.work_stats(store_name),
        }
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/stores/{store_name}/records/status")
def record_status(
    store_name: str,
    body: RecordStatusRequest,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return {"existing_ids": store.existing_ids(store_name, body.ids)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/stores/{store_name}/drift")
def store_drift(
    store_name: str,
    body: StoreDriftRequest,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.drift_report(
            store_name,
            [item.model_dump(mode="json") for item in body.items],
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/stores/{store_name}/export")
def export_store(
    store_name: str,
    work: str | None = Query(default=None),
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return {
            "store": store.get_store(store_name),
            "records": store.export_records(store_name, work=work),
            "work": work,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/stores/{store_name}/records/{chroma_id:path}")
def get_record(
    store_name: str,
    chroma_id: str,
    request: Request,
    include_updates: bool = Query(default=False),
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        user = request_user(request)
        allow_updates = include_updates and user.role == "admin"
        record = store.get_record(
            store_name,
            chroma_id,
            include_updates=allow_updates,
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found.")
        if user.role != "admin":
            return summarize_record(
                record,
                max_chars=settings.researcher_text_max_chars,
            )
        return record
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/stores/{store_name}/records")
def create_record(
    store_name: str,
    body: RecordUpsert,
    request: Request,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        user = require_admin(request)
        record = dict(body.record)
        if not body.include_updates:
            record.pop("updates", None)
        record = _stamp_record_activity(record, user.username)
        return store.upsert_with_language_sync(
            store_name,
            [record],
            document_field=body.document_field,
            id_field=body.id_field,
            embedding_field=body.embedding_field,
            id_prefix=body.id_prefix,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/api/stores/{store_name}/records/{chroma_id:path}")
def patch_record(
    store_name: str,
    chroma_id: str,
    body: StoredRecordPatch,
    request: Request,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        user = require_admin(request)
        entries: list[dict[str, Any]] = []
        for update in body.audit_entries:
            if not isinstance(update, dict):
                continue
            item = dict(update)
            item.setdefault("initiated_by", user.username)
            entries.append(item)

        result = store.patch_existing(
            store_name,
            chroma_id,
            dict(body.changes),
            audit_entries=entries,
            document_field=body.document_field,
            embedding_field=body.embedding_field,
        )
        mirror = store.get_record(store_name, chroma_id, include_updates=False) or {}
        mirror["_chroma_id"] = chroma_id
        language_sync = store.sync_language_children(
            store_name,
            [mirror],
            id_field="_chroma_id",
        )
        return {**result, "language_sync": language_sync}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/stores/{store_name}/records/{chroma_id:path}")
def delete_record(
    store_name: str,
    chroma_id: str,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.delete_record_with_language_sync(store_name, chroma_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/stores/{store_name}/records/bulk")
def bulk_upsert(
    store_name: str,
    body: BulkUpsert,
    request: Request,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        user = require_admin(request)
        records: list[dict[str, Any]] = []
        audit_entries_by_id: dict[str, list[dict[str, Any]]] = {}
        replace_updates_by_id: dict[str, list[dict[str, Any]]] = {}

        for item in body.items:
            record = dict(item.record)
            record.pop("updates", None)
            if item.chroma_id:
                record[body.id_field] = item.chroma_id
            raw_id = record.get(body.id_field)
            if raw_id is None or str(raw_id).strip() == "":
                raise ValueError(f"Bulk upsert item is missing '{body.id_field}'.")

            storage_id = str(raw_id)
            chroma_id = (
                f"{body.id_prefix}::{storage_id}"
                if body.id_prefix
                else storage_id
            )
            if item.audit_entries:
                audit_entries_by_id[chroma_id] = [
                    {
                        **dict(entry),
                        "initiated_by": entry.get("initiated_by") or user.username,
                    }
                    for entry in item.audit_entries
                ]
            if item.replace_updates is not None:
                replace_updates_by_id[chroma_id] = [
                    {
                        **dict(entry),
                        "initiated_by": entry.get("initiated_by") or user.username,
                    }
                    for entry in item.replace_updates
                ]
            records.append(_stamp_record_activity(record, user.username))

        return store.upsert_with_language_sync(
            store_name,
            records,
            document_field=body.document_field,
            id_field=body.id_field,
            embedding_field=body.embedding_field,
            id_prefix=body.id_prefix,
            audit_entries_by_id=audit_entries_by_id,
            replace_updates_by_id=replace_updates_by_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/stores/{store_name}/search")
def search(
    store_name: str,
    body: SearchRequest,
    request: Request,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        user = request_user(request)
        if user.role != "admin":
            enforce_researcher_text({"query": body.query, "where": body.where})

        if body.mode == "filter":
            rows = store.filter_search(store_name, body.n_results, body.where)
        elif body.mode == "keyword":
            rows = store.keyword_search(
                store_name,
                body.query,
                body.n_results,
                body.where,
            )
        elif body.mode == "lexical":
            rows = store.lexical_search(
                store_name,
                body.query,
                body.n_results,
                body.where,
            )
        elif body.mode == "hybrid":
            rows = store.hybrid_search(
                store_name,
                body.query,
                body.n_results,
                body.where,
            )
        elif body.mode == "mmr":
            rows = store.mmr_search(
                store_name,
                body.query,
                body.n_results,
                body.where,
                fetch_k=body.fetch_k,
                lambda_mult=body.lambda_mult,
            )
        else:
            rows = store.search(
                store_name,
                body.query,
                body.n_results,
                body.where,
            )

        result = {"results": rows}
        if user.role != "admin":
            return sanitize_records_payload(
                result,
                max_chars=settings.researcher_text_max_chars,
            )
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
