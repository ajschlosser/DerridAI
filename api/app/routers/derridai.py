# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ..derridai_model import normative_model
from ..http_auth import request_user
from ..provenance_memory import SupportBinding, resolve_support_binding
from ..research_object_graph import build_record_graph
from ..system_store import system_store

router = APIRouter(tags=["derridai-model"])


@router.get("/api/derridai/model")
def get_derridai_model(request: Request) -> dict[str, Any]:
    """Return the normative, walkable DERRIDAI 1.0 type graph."""
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
