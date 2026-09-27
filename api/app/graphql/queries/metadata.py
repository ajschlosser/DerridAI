# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import strawberry
from starlette.concurrency import run_in_threadpool
from strawberry.types import Info

from ...celf_queries import metadata_exemplars as exemplar_queries
from ..errors import translate
from ..permissions import classify, require_admin
from ..types.metadata import MetadataExemplarPage

# Mirrors REST: GET /api/system/data/metadata-exemplars is administrator-only.
classify("metadata_exemplars", "admin")


@strawberry.type
class MetadataQueries:
    @strawberry.field(
        description="Progressive metadata exemplars (REST: GET /api/system/data/metadata-exemplars).",
    )
    async def metadata_exemplars(
        self,
        info: Info,
        offset: int = 0,
        limit: int = 50,
        field: str = "",
        kind: str = "",
        language: str = "",
        scope_id: str = "",
        schema_id: str = "",
        record_id: str = "",
    ) -> MetadataExemplarPage:
        context = require_admin(info)
        filters = exemplar_queries.ExemplarFilter(
            field=field, kind=kind, language=language, scope_id=scope_id, schema_id=schema_id, record_id=record_id,
        )
        try:
            payload = await run_in_threadpool(
                exemplar_queries.exemplar_page, context.access, filters, offset=offset, limit=limit,
            )
        except Exception as exc:
            raise translate(exc) from exc
        return MetadataExemplarPage.from_payload(payload)
