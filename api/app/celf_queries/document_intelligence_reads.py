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
