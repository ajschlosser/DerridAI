# Copyright 2026 Aaron John Schlosser, PhD.
"""Progressive metadata exemplar reads shared by REST and GraphQL. Administrator-only.

Metadata exemplar memory is a derived, rebuildable Chroma projection of
reviewed field assertions; canonical state remains the Records themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    return {**payload, "projection_backlog": projection_backlog()}
