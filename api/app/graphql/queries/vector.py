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

import strawberry
from starlette.concurrency import run_in_threadpool
from strawberry.types import Info

from ...celf_queries import vector_records as vector_queries
from ..errors import translate
from ..permissions import classify, require_capability
from ..types.vector import VectorRecord, VectorRecordPage, VectorWorkStat

# Reachable by any account with the corpus.read capability (including
# Researchers): VectorRecordRow/VectorRecord apply the same researcher-text
# policy as REST. Hidden/system collections and _response_cache read as
# NotFound for non-administrators, matching REST.
classify("vector_store", "corpus.read")

MAX_RECORD_PAGE = 1000


@strawberry.type(description="A Chroma-backed vector store: derived corpus projection, never canonical.")
class VectorStore:
    name: str

    @strawberry.field(description="A page of vector-store records (REST: GET /api/stores/{name}/records).")
    async def records(
        self,
        info: Info,
        offset: int = 0,
        limit: int = 100,
        work: str | None = None,
    ) -> VectorRecordPage:
        context = require_capability(info, "corpus.read")
        limit = max(1, min(MAX_RECORD_PAGE, int(limit)))
        try:
            page = await run_in_threadpool(
                vector_queries.records_page, context.access, self.name, limit=limit, offset=offset, work=work,
            )
        except Exception as exc:
            raise translate(exc) from exc
        return VectorRecordPage.from_payload(page)

    @strawberry.field(description="One vector-store record by chroma_id (REST: GET /api/stores/{name}/records/{id}).")
    async def record(self, info: Info, chroma_id: str) -> VectorRecord | None:
        context = require_capability(info, "corpus.read")
        try:
            found = await run_in_threadpool(vector_queries.record, context.access, self.name, chroma_id)
        except Exception as exc:
            raise translate(exc) from exc
        return VectorRecord.from_payload(found) if found is not None else None

    @strawberry.field(description="Per-work aggregate stats (REST: GET /api/stores/{name}/works).")
    async def works(self, info: Info) -> list[VectorWorkStat]:
        context = require_capability(info, "corpus.read")
        try:
            stats = await run_in_threadpool(vector_queries.works, context.access, self.name)
        except Exception as exc:
            raise translate(exc) from exc
        return [VectorWorkStat.from_payload(item) for item in stats]


@strawberry.type
class VectorQueries:
    @strawberry.field(description="A vector store by name (REST: GET /api/stores/{name}).")
    def vector_store(self, info: Info, name: str) -> VectorStore:
        require_capability(info, "corpus.read")
        return VectorStore(name=name)
