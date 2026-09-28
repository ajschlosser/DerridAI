# Copyright 2026 Aaron John Schlosser, PhD.
"""Transport-independent reads for retained Document Intelligence analysis.

The analysis engine lives in app.document_intelligence. This module is the
read/application boundary used by REST and GraphQL so transport code does not
reimplement build lookup, absence semantics, or authorization.
"""
from __future__ import annotations

from typing import Any

from ..corpus_builder import pdf_corpus_builds
from .access import AccessContext, NotFound


def build_document_intelligence(
    access: AccessContext,
    build_id: str,
    *,
    builds_service: Any = None,
) -> dict[str, Any] | None:
    """Return the retained whole-document analysis, or None before it exists."""
    access.require_admin()
    service = builds_service or pdf_corpus_builds
    normalized = str(build_id or "").strip()
    if not normalized:
        raise NotFound("Corpus build not found.")
    try:
        value = service.document_intelligence(normalized)
    except KeyError as exc:
        raise NotFound("Corpus build not found.") from exc
    if not value:
        return None
    return dict(value)
