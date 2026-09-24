# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ..http_auth import request_user, require_admin
from ..llm import llm_status
from ..models import ResearcherProviderProfilesUpdate, ResearcherProviderStatusRequest
from ..services import metadata_exemplars, store, system_data
from ..system_store import system_store

router = APIRouter(tags=["system"])


@router.delete("/api/system/data/response-cache-records/{record_id}")
def delete_system_response_cache_record(record_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        store.delete_record("_response_cache", record_id)
        return {"deleted": record_id}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/system/data")
def get_system_data(request: Request) -> dict[str, Any]:
    """List all durable system databases through the backend-neutral contract."""
    require_admin(request)
    try:
        return {"databases": system_data.databases()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/system/data/metadata-exemplars")
def get_system_metadata_exemplars(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    field: str = Query(default="", max_length=120),
    kind: str = Query(default="", max_length=40),
    language: str = Query(default="", max_length=40),
    scope_id: str = Query(default="", max_length=200),
    schema_id: str = Query(default="", max_length=200),
    record_id: str = Query(default="", max_length=300),
) -> dict[str, Any]:
    """Inspect progressive metadata exemplars as read-only system data."""
    require_admin(request)
    try:
        return metadata_exemplars.rows(
            limit=limit,
            offset=offset,
            field=field,
            kind=kind,
            language=language,
            scope_id=scope_id,
            schema_id=schema_id,
            record_id=record_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/system/data/{database}/{table}")
def get_system_data_table(
    database: str,
    table: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    require_admin(request)
    try:
        return system_data.rows(database, table, limit=limit, offset=offset)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/system/data/{database}/{table}")
def insert_system_data_row(
    database: str,
    table: str,
    body: dict[str, Any],
    request: Request,
) -> dict[str, Any]:
    require_admin(request)
    try:
        return system_data.insert(database, table, body)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/api/system/data/{database}/{table}")
def update_system_data_row(
    database: str,
    table: str,
    body: dict[str, Any],
    request: Request,
) -> dict[str, Any]:
    require_admin(request)
    key = body.get("key")
    values = body.get("values")
    if not isinstance(key, dict) or not isinstance(values, dict):
        raise HTTPException(
            status_code=422,
            detail="System Data updates require key and values objects.",
        )
    try:
        return system_data.update(database, table, key, values)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/system/data/{database}/{table}")
def delete_system_data_row(
    database: str,
    table: str,
    body: dict[str, Any],
    request: Request,
) -> dict[str, Any]:
    require_admin(request)
    key = body.get("key")
    if not isinstance(key, dict):
        raise HTTPException(
            status_code=422,
            detail="System Data deletes require a key object.",
        )
    try:
        return system_data.delete(database, table, key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/system/researcher-providers")
def researcher_provider_profiles(request: Request) -> dict[str, Any]:
    user = request_user(request)
    profiles = system_store.researcher_profiles()
    if user.role != "admin":
        profiles = [{k: v for k, v in profile.items() if k not in {"base_url", "has_api_key", "api_key"}} for profile in profiles]
    return {"profiles": profiles}


@router.put("/api/system/researcher-providers")
def update_researcher_provider_profiles(body: ResearcherProviderProfilesUpdate, request: Request) -> dict[str, Any]:
    require_admin(request)
    return {"profiles": system_store.set_researcher_profiles(body.profiles)}


@router.get("/api/system/storage")
def system_storage_info(request: Request) -> dict[str, Any]:
    """Describe the durable server-owned metadata store for administrators."""
    require_admin(request)
    return system_store.storage_info()


@router.post("/api/system/researcher-providers/status")
def researcher_provider_status(body: ResearcherProviderStatusRequest, request: Request) -> dict[str, Any]:
    require_admin(request)
    stored = system_store.researcher_profile(body.id) if body.id else None
    api_key = body.api_key or (stored or {}).get("api_key")
    return llm_status(body.type, base_url=body.base_url or (stored or {}).get("base_url"), api_key=api_key)


@router.post("/api/system/researcher-providers/availability")
def researcher_provider_availability(
    body: ResearcherProviderStatusRequest, request: Request
) -> dict[str, Any]:
    request_user(request)
    stored = system_store.researcher_profile(body.id) if body.id else None
    if not stored:
        return {"available": False, "model_available": False, "error": "Provider profile was not found."}
    status = llm_status(
        str(stored.get("type") or body.type),
        base_url=str(stored.get("base_url") or "") or None,
        api_key=str(stored.get("api_key") or "") or None,
    )
    configured_model = str(stored.get("model") or "").strip()
    models = {str(item.get("name") or "") for item in status.get("models") or [] if isinstance(item, dict)}
    model_available = bool(configured_model) and configured_model in models
    return {
        "available": bool(status.get("available")),
        "model_available": model_available,
        "configured_model": configured_model,
        "models": status.get("models") or [],
        "error": status.get("error"),
    }
