# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ..content_filter import enforce_researcher_text
from ..http_auth import request_user
from ..models import AnnotationCreateRequest
from ..services import store
from ..system_store import system_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["annotations"])


@router.get("/api/annotations")
def list_annotations(request: Request, store_name: str | None = Query(default=None, alias="store")) -> dict[str, Any]:
    user = request_user(request)
    annotations = system_store.list_annotations()
    if user.role == "admin":
        return {"annotations": annotations}

    # Researcher annotations are always scoped to corpus evidence available in
    # the selected database. This prevents annotations or change context from a
    # work outside that database from leaking into the researcher workspace.
    candidate_stores: list[str] = []
    if store_name:
        candidate_stores = [store_name]
    else:
        try:
            candidate_stores = [
                str(item.get("name")) for item in store.list_stores()
                if item.get("name") and item.get("collection_role") != "language" and not str(item.get("name")).startswith("_response_cache")
            ]
        except Exception as exc:
            # Fail closed for researcher visibility instead of risking a
            # cross-corpus disclosure. The server log retains diagnosis.
            logger.warning("Researcher annotation store scope could not be loaded: %s", exc)
            candidate_stores = []
    accessible_works: dict[str, set[str]] = {}
    for name in candidate_stores:
        try:
            accessible_works[name] = {str(work) for work in store.list_works(name)}
        except Exception as exc:
            # Security scope checks fail closed: an unreadable store exposes no
            # works rather than risking cross-corpus annotation disclosure.
            logger.warning("Researcher annotation work scope could not be loaded for %s: %s", name, exc)
            accessible_works[name] = set()
    visible: list[dict] = []
    for item in annotations:
        item_store = str(item.get("store") or "")
        if item_store not in accessible_works:
            continue
        item_work = str(item.get("work") or "")
        if item_work and item_work not in accessible_works[item_store]:
            continue
        visible.append(item)
    return {"annotations": visible}


@router.post("/api/annotations")
def create_annotation(body: AnnotationCreateRequest, request: Request) -> dict[str, Any]:
    user = request_user(request)
    if user.role != "admin":
        try:
            enforce_researcher_text({"quote": body.quote, "note": body.note, "tags": body.tags})
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not body.store:
            raise HTTPException(status_code=403, detail="Researcher annotations must be attached to an accessible corpus database record.")
        try:
            accessible_record = store.get_record(body.store, body.record_id, include_updates=False)
        except Exception as exc:
            # Deliberately fail closed without exposing whether the record or
            # backing store failed, avoiding an account-enumeration distinction.
            logger.warning("Researcher annotation evidence check failed closed: %s", exc)
            accessible_record = None
        if accessible_record is None:
            raise HTTPException(status_code=403, detail="That record is not available in the selected corpus database.")
        if body.work and str(accessible_record.get("work") or "") != str(body.work):
            raise HTTPException(status_code=403, detail="That work is not available for this record in the selected corpus database.")
    item = body.model_dump()
    item.update({"user_id": user.id, "initiated_by": user.username, "author": user.username})
    return system_store.add_annotation(item)


@router.delete("/api/annotations/{annotation_id}")
def delete_annotation(annotation_id: str, request: Request) -> dict[str, Any]:
    user = request_user(request)
    deleted = system_store.delete_annotation(annotation_id, user_id=user.id, admin=user.role == "admin")
    if not deleted:
        raise HTTPException(status_code=404, detail="Annotation not found or not editable by this account.")
    return {"deleted": annotation_id}

