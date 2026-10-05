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

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..rag import _resolve_search_collections
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
    return preview_filter_plan(
        metadata_filter=body.metadata_filter,
        document_filter=body.document_filter,
        source=body.source,
        collection_filter_fields=fields,
    )


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
