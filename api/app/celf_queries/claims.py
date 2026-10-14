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

"""Generated-claim and support-binding reads shared by REST and GraphQL."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..claim_memory import ClaimMemoryIndex, similar_validated_claims
from ..system_store import system_store
from .access import AccessContext, NotFound

MAX_SIMILAR_CLAIMS = 10

_claim_index: ClaimMemoryIndex | None = None


def default_claim_index() -> ClaimMemoryIndex:
    """Process-wide validated-claim projection (derived, rebuildable)."""
    global _claim_index
    if _claim_index is None:
        _claim_index = ClaimMemoryIndex()
    return _claim_index


def get_generated_claim(access: AccessContext, claim_id: str) -> dict[str, Any]:
    """Owner-scoped generated claim; another user's claim reads as missing."""
    claim = system_store.get_generated_claim(str(claim_id), owner=access.owner)
    if claim is None:
        raise NotFound("Generated claim not found")
    return claim


def generated_claims_by_ids(access: AccessContext, claim_ids: list[str]) -> list[dict[str, Any] | None]:
    """Batch lookup in request order (``None`` where missing or not visible)."""
    found = system_store.get_generated_claims(list(claim_ids), owner=access.owner)
    return [found.get(str(claim_id)) for claim_id in claim_ids]


def support_bindings_by_claim_ids(access: AccessContext, claim_ids: list[str]) -> list[list[dict[str, Any]]]:
    """Batch support-binding lookup in request order, owner-scoped."""
    grouped = system_store.list_claim_support_bindings_for_claims(list(claim_ids), owner=access.owner)
    return [list(grouped.get(str(claim_id), [])) for claim_id in claim_ids]


def clamp_similar_limit(limit: int | None) -> int:
    return max(1, min(MAX_SIMILAR_CLAIMS, int(limit or 5)))


def similar_claims(
    access: AccessContext,
    claim: dict[str, Any],
    *,
    limit: int,
    index_factory: Callable[[], ClaimMemoryIndex],
) -> dict[str, Any]:
    """Advisory validated-claim precedents; similarity never asserts support.

    ``claim`` must already have been resolved through :func:`get_generated_claim`
    so owner scoping has been applied before the projection is consulted.
    """
    return similar_validated_claims(
        index_factory(),
        system_store,
        claim,
        owner=access.owner,
        limit=clamp_similar_limit(limit),
    )
