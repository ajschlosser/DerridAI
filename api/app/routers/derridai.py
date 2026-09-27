# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ..claim_memory import (
    ClaimMemoryIndex,
    apply_claim_validation,
    similar_validated_claims,
)
from ..derridai_model import normative_model
from ..http_auth import request_user
from ..provenance_memory import SupportBinding, resolve_support_binding
from ..research_object_graph import build_record_graph
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
    Record identity and remains owner-scoped for non-admin users.
    """
    user = request_user(request)
    record = body.get("record")
    if not isinstance(record, dict):
        raise HTTPException(status_code=422, detail="record must be an object")
    record_id = str(record.get("record_id") or "").strip()
    if not record_id:
        raise HTTPException(status_code=422, detail="record.record_id is required")

    owner = None if user.role == "admin" else user.username
    resolver_record = dict(record)
    if not resolver_record.get("source_document_id") and resolver_record.get("source_asset_id"):
        resolver_record["source_document_id"] = resolver_record["source_asset_id"]
    raw_bindings = system_store.list_claim_support_bindings_for_record(
        record_id,
        owner=owner,
        limit=200,
    )
    bindings: list[dict[str, Any]] = []
    claim_ids: set[str] = set()
    for raw in raw_bindings:
        try:
            binding = resolve_support_binding(
                SupportBinding.model_validate(raw),
                lambda requested: resolver_record if str(requested) == record_id else None,
            )
            payload = binding.model_dump(mode="json")
        except Exception:
            # Preserve malformed historical provenance as unresolved rather than
            # making the graph endpoint unusable for an otherwise valid Record.
            payload = dict(raw)
            payload["validation_status"] = "unresolved"
        bindings.append(payload)
        claim_id = str(payload.get("claim_id") or "").strip()
        if claim_id:
            claim_ids.add(claim_id)

    claims = [
        claim
        for claim_id in sorted(claim_ids)
        if (claim := system_store.get_generated_claim(claim_id, owner=owner)) is not None
    ]
    try:
        return build_record_graph(
            record,
            claims=claims,
            support_bindings=bindings,
            include_assertion_history=bool(body.get("include_assertion_history")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


_claim_index: ClaimMemoryIndex | None = None


def _claim_memory() -> ClaimMemoryIndex:
    global _claim_index
    if _claim_index is None:
        _claim_index = ClaimMemoryIndex()
    return _claim_index


def _owned_claim(claim_id: str, user: Any) -> tuple[dict[str, Any], str | None]:
    owner = None if user.role == "admin" else user.username
    claim = system_store.get_generated_claim(claim_id, owner=owner)
    if claim is None:
        raise HTTPException(status_code=404, detail="Generated claim not found")
    return claim, owner


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
    claim, owner = _owned_claim(claim_id, user)
    try:
        return apply_claim_validation(
            system_store,
            claim,
            status=str(body.get("status") or ""),
            actor=user.username,
            owner=owner,
            record=body.get("record") if isinstance(body.get("record"), dict) else None,
            index_factory=_claim_memory,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/derridai/claims/{claim_id}/similar")
def similar_claims(claim_id: str, request: Request, limit: int = 5) -> dict[str, Any]:
    """Advisory: previously validated claims similar to this one (never asserts support)."""
    user = request_user(request)
    claim, owner = _owned_claim(claim_id, user)
    try:
        return similar_validated_claims(
            _claim_memory(), system_store, claim, owner=owner, limit=max(1, min(10, int(limit))),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Validated-claim memory unavailable: {exc}") from exc
