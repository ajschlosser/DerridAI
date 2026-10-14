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

from threading import BoundedSemaphore
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from ..rag import _resolve_search_collections
from ..research_filter_catalog import validate_catalog_filter
from ..research_filter_preview import preview_filter_plan
from ..research_semantics import source_author, source_work_label
from ..services import store

router = APIRouter(tags=["research"])


class ResearchFilterPreviewRequest(BaseModel):
    """Raw (unvalidated) filter input; validation errors are returned, not raised."""

    model_config = ConfigDict(extra="forbid")

    collection: str = Field(min_length=1, max_length=256)
    metadata_filter: Any = None
    document_filter: Any = None
    source: Literal["explicit", "deterministic_natural_language", "model_assisted"] = "explicit"
    locales: list[str] = Field(default_factory=list, max_length=16)


@router.post("/api/research/filters/preview")
def preview_research_filter(body: ResearchFilterPreviewRequest) -> dict[str, Any]:
    """Validate a filter plan against a Research collection without running retrieval."""
    try:
        # Rejects missing and system/hidden collections exactly as a Research run does.
        collections = _resolve_search_collections(store, body.collection, body.locales)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    fields: list[str] = []
    for item in collections:
        fields.extend(str(name) for name in item.get("filter_fields") or [])
    result = preview_filter_plan(
        metadata_filter=body.metadata_filter,
        document_filter=body.document_filter,
        source=body.source,
        collection_filter_fields=fields,
    )

    if callable(getattr(store, "research_filter_inventory", None)):
        catalog = store.research_filter_inventory([str(item["name"]) for item in collections])["fields"]
        result = preview_filter_plan(metadata_filter=body.metadata_filter, document_filter=body.document_filter,
            source=body.source, collection_filter_fields=[field["key"] for field in catalog])
        if result["valid"]:
            result["errors"].extend(validate_catalog_filter(result["plan"]["metadata_filter"], catalog))
            result["valid"] = not result["errors"]
        result["field_catalog"] = catalog
    return result


INVENTORY_MAX_WORKS = 500


class ResearchFilterInventoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection: str = Field(min_length=1, max_length=256)
    locales: list[str] = Field(default_factory=list, max_length=16)


@router.post("/api/research/filters/inventory")
def research_filter_inventory(body: ResearchFilterInventoryRequest) -> dict[str, Any]:
    """Bounded work/author names so the browser can resolve named scopes.

    Names only (no passages). The browser proposes filters from these; the server
    still validates any plan before a run, and the inventory is never evidence.
    """
    try:
        collections = _resolve_search_collections(store, body.collection, body.locales)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if callable(getattr(store, "research_filter_inventory", None)):
        return store.research_filter_inventory([str(item["name"]) for item in collections])
    works: dict[str, set[str]] = {}
    work_stats = getattr(store, "work_stats", None)
    for item in collections:
        name = str(item.get("name") or "")
        if not name or not callable(work_stats):
            continue
        for row in work_stats(name):
            work = source_work_label(row)
            if not work:
                continue
            authors = works.setdefault(work, set())
            author = source_author(row)
            if author:
                authors.add(author)
    ordered = sorted(works, key=str.casefold)
    return {
        "works": [
            {"work": work, "authors": sorted(works[work])}
            for work in ordered[:INVENTORY_MAX_WORKS]
        ],
        "truncated": len(ordered) > INVENTORY_MAX_WORKS,
    }


class ResearchFilterResolveRequest(ResearchFilterInventoryRequest):
    provider_profile_id: str | None = Field(default=None, max_length=256)
    instructions: str = Field(min_length=1, max_length=8000)


_model_slot = BoundedSemaphore(1)


@router.post("/api/research/filters/resolve")
def resolve_research_filter(body: ResearchFilterResolveRequest, request: Request) -> dict[str, Any]:
    import httpx

    from ..content_filter import enforce_researcher_text
    from ..http_auth import request_user
    from ..research_filter_model import resolve_with_local_model
    from ..system_store import system_store

    user = request_user(request)
    profile = system_store.researcher_profile(body.provider_profile_id) if body.provider_profile_id else None
    if user.role != "admin":
        try:
            enforce_researcher_text({"instructions": body.instructions})
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if profile is None:
            raise HTTPException(status_code=403, detail="Select an administrator-approved Ollama profile")
    if body.provider_profile_id and profile is None:
        raise HTTPException(status_code=403, detail="That approved Ollama profile is unavailable")
    if profile is not None and profile.get("type") != "ollama":
        raise HTTPException(status_code=422, detail="Scope suggestions require an Ollama profile")
    inventory = research_filter_inventory(ResearchFilterInventoryRequest(collection=body.collection, locales=body.locales))
    catalog = inventory.get("fields", [])
    if not catalog:
        raise HTTPException(status_code=409, detail="No indexed field inventory is available")
    if not _model_slot.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="The scope model is busy; try again later")
    try:
        return resolve_with_local_model(body.instructions, catalog, profile=profile)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="The local model did not return a valid scope proposal") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="The configured Ollama model is unavailable; install it locally or use explicit filters") from exc
    finally:
        _model_slot.release()
