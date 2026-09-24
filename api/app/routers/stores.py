# Copyright 2026 Aaron John Schlosser, PhD.
"""Vector-store collection administration API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..chroma_store import ChromaStore, StoreAlreadyExistsError
from ..dependencies import get_store as store_dependency
from ..models import (
    ChromaConnectionUpdate,
    ChromaPathUpdate,
    DeriveLanguageStoresRequest,
    EmbeddingPreflightRequest,
    StoreCreate,
    StoreEmbeddingUpdate,
    StoreLanguageUpdate,
    StoreProtectionUpdate,
)

router = APIRouter(tags=["stores"])


@router.get("/api/chroma/path")
def get_chroma_path(
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    return store.health()


@router.put("/api/chroma/path")
def set_chroma_path(
    body: ChromaPathUpdate,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.set_path(body.path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/chroma/connection")
def get_chroma_connection(
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    return store.health()


@router.post("/api/chroma/connection/probe")
def probe_chroma_connection(
    body: ChromaConnectionUpdate,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.probe_connection(
            mode=body.mode,
            path=body.path,
            url=body.url,
            token=body.token,
            tenant=body.tenant,
            database=body.database,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/api/chroma/connection")
def set_chroma_connection(
    body: ChromaConnectionUpdate,
    store: ChromaStore = Depends(store_dependency),
) -> dict[str, Any]:
    try:
        return store.set_connection(
            mode=body.mode,
            path=body.path,
            url=body.url,
            token=body.token,
            tenant=body.tenant,
            database=body.database,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
