# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..models import ChromaConnectionUpdate, ChromaPathUpdate
from ..services import store

router = APIRouter(tags=["chroma"])


@router.get("/api/chroma/path")
def get_chroma_path() -> dict[str, Any]:
    return store.health()


@router.put("/api/chroma/path")
def set_chroma_path(body: ChromaPathUpdate) -> dict[str, Any]:
    try:
        return store.set_path(body.path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/chroma/connection")
def get_chroma_connection() -> dict[str, Any]:
    return store.health()


@router.post("/api/chroma/connection/probe")
def probe_chroma_connection(body: ChromaConnectionUpdate) -> dict[str, Any]:
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
def set_chroma_connection(body: ChromaConnectionUpdate) -> dict[str, Any]:
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

