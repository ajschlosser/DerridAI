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

"""Progressive metadata exemplar reads: a derived, rebuildable Chroma projection of reviewed field assertions."""
from __future__ import annotations

from typing import Any

import strawberry
from strawberry.scalars import JSON

from .common import opt_int, opt_str


@strawberry.type(description="One reviewed metadata exemplar (REST: GET /api/system/data/metadata-exemplars rows).")
class MetadataExemplar:
    exemplar_id: str
    scope_id: str | None
    record_id: str | None
    record_revision: int | None
    source_document_id: str | None
    field_name: str | None
    field_value: JSON | None
    kind: str
    assertion_status: str | None
    schema_id: str | None
    schema_version: str | None
    language: str | None
    region_type: str | None
    evidence_hash: str | None
    evidence_block_ids: JSON
    context_text: str

    @classmethod
    def from_payload(cls, item: dict[str, Any]) -> MetadataExemplar:
        return cls(
            exemplar_id=str(item.get("exemplar_id") or ""),
            scope_id=opt_str(item.get("scope_id")),
            record_id=opt_str(item.get("record_id")),
            record_revision=opt_int(item.get("record_revision")),
            source_document_id=opt_str(item.get("source_document_id")),
            field_name=opt_str(item.get("field_name")),
            field_value=JSON(item.get("field_value")) if item.get("field_value") is not None else None,
            kind=str(item.get("kind") or "positive"),
            assertion_status=opt_str(item.get("assertion_status")),
            schema_id=opt_str(item.get("schema_id")),
            schema_version=opt_str(item.get("schema_version")),
            language=opt_str(item.get("language")),
            region_type=opt_str(item.get("region_type")),
            evidence_hash=opt_str(item.get("evidence_hash")),
            evidence_block_ids=JSON(item.get("evidence_block_ids") or []),
            context_text=str(item.get("context_text") or ""),
        )


@strawberry.type(description="Distinct values observed across the current exemplar collection, for filter UIs.")
class MetadataExemplarFacets:
    fields: list[str]
    kinds: list[str]
    languages: list[str]
    scopes: list[str]
    schemas: list[str]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> MetadataExemplarFacets:
        return cls(
            fields=[str(v) for v in payload.get("fields") or []],
            kinds=[str(v) for v in payload.get("kinds") or []],
            languages=[str(v) for v in payload.get("languages") or []],
            scopes=[str(v) for v in payload.get("scopes") or []],
            schemas=[str(v) for v in payload.get("schemas") or []],
        )


@strawberry.type(description="A page of metadata exemplars. `exists=false` means the projection has not run yet.")
class MetadataExemplarPage:
    exists: bool
    count: int
    offset: int
    limit: int
    rows: list[MetadataExemplar]
    facets: MetadataExemplarFacets
    projection_backlog: JSON = strawberry.field(
        description="Unprojected reviewed-metadata work, with the most recent failure per build.",
    )

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> MetadataExemplarPage:
        return cls(
            exists=bool(payload.get("exists")),
            count=int(payload.get("count") or 0),
            offset=int(payload.get("offset") or 0),
            limit=int(payload.get("limit") or 0),
            rows=[MetadataExemplar.from_payload(item) for item in payload.get("rows") or []],
            facets=MetadataExemplarFacets.from_payload(payload.get("facets") or {}),
            projection_backlog=JSON(payload.get("projection_backlog") or {}),
        )
