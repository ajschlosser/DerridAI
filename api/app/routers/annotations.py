# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ..content_filter import enforce_researcher_text
from ..http_auth import request_user
from ..models import AnnotationCreateRequest, AnnotationReplyRequest
from ..services import store
from ..system_store import system_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["annotations"])


def _record_is_accessible(store_name: str, record_id: str) -> dict[str, Any] | None:
    try:
        return store.get_record(store_name, record_id, include_updates=False)
    except Exception as exc:
        logger.warning("Annotation record scope check failed for %s/%s: %s", store_name, record_id, exc)
        return None


def _annotation_is_visible(item: dict[str, Any], accessible_works: dict[str, set[str]]) -> bool:
    item_store = str(item.get("store") or "")
    works = accessible_works.get(item_store)
    if works is None:
        return False
    return bool(item.get("work")) and str(item.get("work")) in works


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
        if _annotation_is_visible(item, accessible_works):
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
    if user.role != "admin":
        if not body.store:
            raise HTTPException(status_code=403, detail="Researcher annotations must be attached to an accessible corpus database.")
        if body.scope == "work":
            try:
                works = {str(work) for work in store.list_works(body.store)}
            except Exception as exc:
                logger.warning("Researcher annotation work check failed closed: %s", exc)
                works = set()
            if str(body.work or "") not in works:
                raise HTTPException(status_code=403, detail="That work is not available in the selected corpus database.")
        else:
            accessible_record = _record_is_accessible(body.store, str(body.record_id))
            if accessible_record is None:
                raise HTTPException(status_code=403, detail="That record is not available in the selected corpus database.")
            if body.work and str(accessible_record.get("work") or "") != str(body.work):
                raise HTTPException(status_code=403, detail="That work is not available for this record in the selected corpus database.")
        for linked_id in body.linked_record_ids:
            if _record_is_accessible(body.store, linked_id) is None:
                raise HTTPException(status_code=403, detail="A linked record is not available in the selected corpus database.")
    if body.parent_id:
        parent = next(
            (item for item in system_store.list_annotations() if str(item.get("id") or "") == body.parent_id),
            None,
        )
        if parent is None:
            raise HTTPException(status_code=404, detail="Annotation thread not found.")
        if user.role != "admin" and (
            str(parent.get("store") or "") != str(body.store or "")
            or not _annotation_is_visible(
                parent,
                {str(body.store): {str(body.work or parent.get("work") or "")}},
            )
        ):
            raise HTTPException(status_code=403, detail="That annotation thread is not accessible.")
    item = body.model_dump()
    item.update({"user_id": user.id, "initiated_by": user.username, "author": user.username})
    return system_store.add_annotation(item)


@router.post("/api/annotations/{annotation_id}/replies")
def reply_to_annotation(
    annotation_id: str, body: AnnotationReplyRequest, request: Request
) -> dict[str, Any]:
    user = request_user(request)
    parent = next(
        (item for item in system_store.list_annotations() if str(item.get("id") or "") == annotation_id),
        None,
    )
    if parent is None:
        raise HTTPException(status_code=404, detail="Annotation thread not found.")
    if not body.note.strip() and not body.quote.strip() and not body.tags:
        raise HTTPException(status_code=422, detail="A reply must contain text or tags.")
    if user.role != "admin":
        try:
            enforce_researcher_text({"quote": body.quote, "note": body.note, "tags": body.tags})
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        parent_store = str(parent.get("store") or "")
        if not parent_store:
            raise HTTPException(status_code=403, detail="That annotation thread is not accessible.")
        if parent.get("scope") == "work":
            try:
                accessible = str(parent.get("work") or "") in {
                    str(work) for work in store.list_works(parent_store)
                }
            except Exception as exc:
                logger.warning("Reply work scope check failed closed: %s", exc)
                accessible = False
        else:
            accessible = _record_is_accessible(parent_store, str(parent.get("record_id") or "")) is not None
        if not accessible:
            raise HTTPException(status_code=403, detail="That annotation thread is not accessible.")
    item = {
        "store": parent.get("store"),
        "scope": parent.get("scope") or "record",
        "record_id": parent.get("record_id"),
        "work": parent.get("work"),
        "linked_record_ids": parent.get("linked_record_ids") or [],
        "parent_id": annotation_id,
        "thread_id": parent.get("thread_id") or annotation_id,
        "field": parent.get("field") or "text",
        "quote": body.quote,
        "note": body.note,
        "tags": body.tags,
    }
    item.update({"user_id": user.id, "initiated_by": user.username, "author": user.username})
    return system_store.add_annotation(item)


@router.delete("/api/annotations/{annotation_id}")
def delete_annotation(annotation_id: str, request: Request) -> dict[str, Any]:
    user = request_user(request)
    deleted = system_store.delete_annotation(annotation_id, user_id=user.id, admin=user.role == "admin")
    if not deleted:
        raise HTTPException(status_code=404, detail="Annotation not found or not editable by this account.")
    return {"deleted": annotation_id}
