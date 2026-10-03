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

"""Vector-store (Chroma projection) records. Derived, never canonical."""
from __future__ import annotations

from typing import Any

import strawberry
from starlette.concurrency import run_in_threadpool
from strawberry.scalars import JSON
from strawberry.types import Info

from .common import opt_str
from .graph import ResearchObjectGraph

TEXT_PREVIEW_CHARS = 240
_WORK_STAT_CORE_KEYS = {"work", "count", "total_words", "average_record_length"}


def _preview(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) <= TEXT_PREVIEW_CHARS:
        return compact
    return compact[: TEXT_PREVIEW_CHARS - 1].rstrip() + "…"


@strawberry.type(
    description=(
        "One vector-store table row: identifiers, work, pages and a short preview. Never the full text "
        "(materialization: vector_projection)."
    ),
)
class VectorRecordRow:
    chroma_id: str
    record_id: str | None
    work: str | None
    page_start: str | None
    page_end: str | None
    text_preview: str
    materialization: str

    @classmethod
    def from_payload(cls, record: dict[str, Any]) -> VectorRecordRow:
        return cls(
            chroma_id=str(record.get("_chroma_id") or ""),
            record_id=opt_str(record.get("record_id")),
            work=opt_str(record.get("work")),
            page_start=opt_str(record.get("page_start")),
            page_end=opt_str(record.get("page_end")),
            text_preview=_preview(str(record.get("text") or "")),
            materialization="vector_projection",
        )


@strawberry.type(description="A page of vector-store table rows (REST: GET /api/stores/{name}/records).")
class VectorRecordPage:
    items: list[VectorRecordRow]
    count: int
    offset: int
    limit: int
    work: str | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> VectorRecordPage:
        return cls(
            items=[VectorRecordRow.from_payload(record) for record in payload.get("records") or []],
            count=int(payload.get("count") or 0),
            offset=int(payload.get("offset") or 0),
            limit=int(payload.get("limit") or 0),
            work=opt_str(payload.get("work")),
        )


@strawberry.type(
    description=(
        "A full vector-store Record projection. Derived, never canonical: `graph` builds a walkable "
        "cELF graph from this stored record's own fields, which is weaker provenance than a `record_graph` "
        "built from the canonical corpus Record (materialization: vector_projection)."
    ),
)
class VectorRecord:
    chroma_id: str
    record_id: str | None
    work: str | None
    text: str
    text_summarized: bool = strawberry.field(
        description="True when text was shortened by the researcher-text policy (REST: summarize_record).",
    )
    materialization: str
    document: JSON = strawberry.field(
        description="The full stored record, already access-scoped (researcher-text-summarized when applicable).",
    )
    raw_record: strawberry.Private[dict[str, Any]]

    @classmethod
    def from_payload(cls, record: dict[str, Any]) -> VectorRecord:
        return cls(
            chroma_id=str(record.get("_chroma_id") or ""),
            record_id=opt_str(record.get("record_id")),
            work=opt_str(record.get("work")),
            text=str(record.get("text") or ""),
            text_summarized="_researcher_text_policy" in record,
            materialization="vector_projection",
            document=JSON(record),
            raw_record=record,
        )

    @strawberry.field(
        description="record_graph built from this stored record's own fields (record_state_origin: vector_projection).",
    )
    async def graph(self, info: Info) -> ResearchObjectGraph:
        from ...celf_queries import records as record_queries
        from ..errors import translate

        access = info.context.access
        try:
            payload = await run_in_threadpool(
                record_queries.graph_for_record, self.raw_record, access, origin="vector_projection",
            )
        except Exception as exc:
            raise translate(exc) from exc
        return ResearchObjectGraph.from_payload(payload)


@strawberry.type(description="Aggregate stats for one work across the store (REST: GET /api/stores/{name}/works).")
class VectorWorkStat:
    work: str
    count: int
    total_words: int
    average_record_length: int
    details: JSON = strawberry.field(description="Other fields observed for the work (mixed values, edition, …).")

    @classmethod
    def from_payload(cls, item: dict[str, Any]) -> VectorWorkStat:
        return cls(
            work=str(item.get("work") or ""),
            count=int(item.get("count") or 0),
            total_words=int(item.get("total_words") or 0),
            average_record_length=int(item.get("average_record_length") or 0),
            details=JSON({key: value for key, value in item.items() if key not in _WORK_STAT_CORE_KEYS}),
        )
