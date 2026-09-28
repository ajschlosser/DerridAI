# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import strawberry
from starlette.concurrency import run_in_threadpool
from strawberry.types import Info

from ...celf_queries import source_documents as document_queries
from ..errors import translate
from ..permissions import classify, require_admin
from ..types.documents import SourceDocumentView

# SourceDocument intelligence currently carries full extracted text through
# source_units, matching the administrator-only REST source/asset endpoints.
classify("source_document", "admin")


@strawberry.type
class DocumentQueries:
    @strawberry.field(
        description=(
            "One canonical cELF SourceDocument with its extraction, structure, provenance, "
            "capture links, and downstream build references."
        ),
    )
    async def source_document(
        self,
        info: Info,
        source_document_id: str,
    ) -> SourceDocumentView:
        context = require_admin(info)
        try:
            payload = await run_in_threadpool(
                document_queries.source_document,
                context.access,
                source_document_id,
            )
        except Exception as exc:
            raise translate(exc) from exc
        return SourceDocumentView.from_payload(payload)
