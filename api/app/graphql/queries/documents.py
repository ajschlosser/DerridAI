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
