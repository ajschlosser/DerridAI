# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import strawberry
from starlette.concurrency import run_in_threadpool
from strawberry.scalars import JSON
from strawberry.types import Info

from ...celf_queries import records as record_queries
from ..errors import translate
from ..permissions import classify, require_admin
from ..types.graph import ResearchObjectGraph

# Record graphs expose Record text-bearing assertion values and node details.
# REST keeps /api/derridai/* administrator-only, so the GraphQL root does too
# until a researcher-safe projection is designed (docs/GRAPHQL.md).
classify("record_graph", "admin")


@strawberry.type
class RecordQueries:
    @strawberry.field(
        description=(
            "Walkable instance graph around one Record (REST: POST /api/derridai/graph/record). "
            "`record` is the caller's local Record snapshot; claims and support are joined server-side."
        ),
    )
    async def record_graph(
        self,
        info: Info,
        record: JSON,
        include_assertion_history: bool = False,
    ) -> ResearchObjectGraph:
        context = require_admin(info)
        try:
            payload = await run_in_threadpool(
                record_queries.record_graph,
                record,
                context.access,
                include_assertion_history=include_assertion_history,
            )
        except Exception as exc:
            raise translate(exc) from exc
        return ResearchObjectGraph.from_payload(payload)
