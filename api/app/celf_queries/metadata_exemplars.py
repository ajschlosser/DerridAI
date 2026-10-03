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

"""Progressive metadata exemplar reads shared by REST and GraphQL. Administrator-only.

Metadata exemplar memory is a derived, rebuildable Chroma projection of
reviewed field assertions; canonical state remains the Records themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..corpus_builder import pdf_corpus_repository
from ..metadata_exemplar_projection import projection_backlog
from ..services import store
from ..system_metadata_exemplars import MetadataExemplarInspector
from .access import AccessContext

_inspector = MetadataExemplarInspector(store)


@dataclass(frozen=True)
class ExemplarFilter:
    field: str = ""
    kind: str = ""
    language: str = ""
    scope_id: str = ""
    schema_id: str = ""
    record_id: str = ""


def exemplar_page(
    access: AccessContext,
    filters: ExemplarFilter,
    *,
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    access.require_admin()
    payload = _inspector.rows(
        limit=limit,
        offset=offset,
        field=filters.field,
        kind=filters.kind,
        language=filters.language,
        scope_id=filters.scope_id,
        schema_id=filters.schema_id,
        record_id=filters.record_id,
    )
    # Why the list may be empty: reviewed metadata waiting on a failing projection.
    return {**payload, "projection_backlog": projection_backlog(pdf_corpus_repository)}
