# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..gutenberg_catalogue import gutenberg_offline
from ..http_auth import request_user

router = APIRouter(tags=["gutenberg"])


@router.get("/api/gutenberg/status")
def gutenberg_status(request: Request) -> dict:
    request_user(request)
    return gutenberg_offline.status()


@router.post("/api/gutenberg/catalogue/refresh")
def refresh_catalogue(request: Request) -> dict:
    request_user(request)
    try:
        return gutenberg_offline.refresh_catalogue()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Catalogue refresh failed: {exc}") from exc


@router.post("/api/gutenberg/archive/{action}")
def archive_action(action: str, request: Request) -> dict:
    request_user(request)
    try:
        result = gutenberg_offline.set_archive_status(action)
        if action in {"start", "resume"}:
            return gutenberg_offline.download_chunk()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Archive operation failed: {exc}") from exc
