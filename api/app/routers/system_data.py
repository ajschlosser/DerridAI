# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ..auth import auth_store
from ..database_backend import SQLiteBackend
from ..http_auth import require_admin
from ..services import store
from ..system_data import SystemDataService
from ..system_metadata_exemplars import MetadataExemplarInspector
from ..system_store import system_store

router = APIRouter(tags=["system-data"])

system_data = SystemDataService(
    {
        "system": SQLiteBackend("system", system_store.path),
        "auth": SQLiteBackend("auth", auth_store.path),
    }
)
metadata_exemplars = MetadataExemplarInspector(store)


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
    """List durable system databases through the backend-neutral contract."""
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
    """Inspect progressive metadata exemplars as read-only System Data."""
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
