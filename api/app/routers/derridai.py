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

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ..celf_queries import claims as claim_queries
from ..celf_queries import records as record_queries
from ..celf_queries.access import AccessContext, InvalidQuery, NotFound
from ..claim_memory import ClaimMemoryIndex, apply_claim_validation
from ..derridai_model import normative_model
from ..http_auth import request_user
from ..system_store import system_store

router = APIRouter(tags=["derridai-model"])


@router.get("/api/derridai/model")
def get_derridai_model(request: Request) -> dict[str, Any]:
    """Return the normative, walkable cELF 1.0 type graph."""
    request_user(request)
    return normative_model()


@router.post("/api/derridai/graph/record")
def get_record_object_graph(body: dict[str, Any], request: Request) -> dict[str, Any]:
    """Build a walkable instance graph around one Record.

    The caller may provide a local-workspace Record that is not currently stored
    in Chroma. Durable claim/support provenance is joined server-side by logical
    Record identity and remains owner-scoped for non-admin users. GraphQL's
    ``record_graph`` calls the same service.
    """
    access = AccessContext.for_user(request_user(request))
    try:
        return record_queries.record_graph(
            body.get("record"),
            access,
            include_assertion_history=bool(body.get("include_assertion_history")),
        )
    except InvalidQuery as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _claim_memory() -> ClaimMemoryIndex:
    return claim_queries.default_claim_index()


def _owned_claim(claim_id: str, user: Any) -> tuple[dict[str, Any], AccessContext]:
    access = AccessContext.for_user(user)
    try:
        return claim_queries.get_generated_claim(access, claim_id), access
    except NotFound as exc:
        raise HTTPException(status_code=404, detail="Generated claim not found") from exc


@router.get("/api/derridai/claims/{claim_id}")
def get_claim(claim_id: str, request: Request) -> dict[str, Any]:
    """Return the authoritative current state of one generated claim."""
    user = request_user(request)
    claim, _owner = _owned_claim(claim_id, user)
    return {"claim": claim}


@router.post("/api/derridai/claims/{claim_id}/validation")
def set_claim_validation(claim_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
    """Record a human audit decision on a generated claim.

    ``validated`` adds the claim to validated-claim memory (a derived vector
    projection); any other status removes it. The SQLite row is authoritative and is
    committed first; a projection failure is reported, never hidden.
    """
    user = request_user(request)
    claim, access = _owned_claim(claim_id, user)
    try:
        return apply_claim_validation(
            system_store,
            claim,
            status=str(body.get("status") or ""),
            actor=user.username,
            owner=access.owner,
            record=body.get("record") if isinstance(body.get("record"), dict) else None,
            index_factory=_claim_memory,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/derridai/claims/{claim_id}/similar")
def similar_claims(claim_id: str, request: Request, limit: int = 5) -> dict[str, Any]:
    """Advisory: previously validated claims similar to this one (never asserts support)."""
    user = request_user(request)
    claim, access = _owned_claim(claim_id, user)
    try:
        return claim_queries.similar_claims(access, claim, limit=limit, index_factory=_claim_memory)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Validated-claim memory unavailable: {exc}") from exc
