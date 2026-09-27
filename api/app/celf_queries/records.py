# Copyright 2026 Aaron John Schlosser, PhD.
"""Record traceability graph reads shared by REST and GraphQL."""
from __future__ import annotations

import copy
import json
from typing import Any

from ..config import settings
from ..provenance_memory import SupportBinding, resolve_support_binding
from ..research_object_graph import build_record_graph
from ..response_filters import scrub_second_opinions
from ..reviewer_context import current_reviewer
from ..system_store import system_store
from .access import AccessContext, InvalidQuery

SUPPORT_BINDING_LIMIT = 200


def prepare_record_snapshot(record: Any, access: AccessContext) -> dict[str, Any]:
    """Validate and reviewer-scrub a client-supplied local Record snapshot.

    The snapshot bridge exists because a Record may live only in the browser
    workspace. It is bounded, never mutated in place, and presented through the
    same blind-review scrubber as corpus-build responses so a second reviewer's
    graph cannot reveal a sealed first answer.
    """
    if not isinstance(record, dict):
        raise InvalidQuery("record must be an object")
    record_id = str(record.get("record_id") or "").strip()
    if not record_id:
        raise InvalidQuery("record.record_id is required")
    try:
        size = len(json.dumps(record, ensure_ascii=False, default=str).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise InvalidQuery("record must be JSON-serializable") from exc
    if size > settings.graphql_max_record_bytes:
        raise InvalidQuery("record snapshot is too large")
    snapshot = copy.deepcopy(record)
    snapshot["record_id"] = record_id
    token = current_reviewer.set(access.reviewer or current_reviewer.get())
    try:
        scrub_second_opinions(snapshot)
    finally:
        current_reviewer.reset(token)
    return snapshot


def resolved_support_bindings(record: dict[str, Any], access: AccessContext) -> list[dict[str, Any]]:
    """Server-owned support bindings for one logical Record, resolved against it.

    Malformed historical provenance is kept as ``unresolved`` rather than dropped,
    so stale or broken evidence stays visible for review.
    """
    record_id = str(record["record_id"])
    resolver_record = dict(record)
    if not resolver_record.get("source_document_id") and resolver_record.get("source_asset_id"):
        resolver_record["source_document_id"] = resolver_record["source_asset_id"]
    raw_bindings = system_store.list_claim_support_bindings_for_record(
        record_id,
        owner=access.owner,
        limit=SUPPORT_BINDING_LIMIT,
    )
    bindings: list[dict[str, Any]] = []
    for raw in raw_bindings:
        try:
            binding = resolve_support_binding(
                SupportBinding.model_validate(raw),
                lambda requested: resolver_record if str(requested) == record_id else None,
            )
            payload = binding.model_dump(mode="json")
        except Exception:
            payload = dict(raw)
            payload["validation_status"] = "unresolved"
        bindings.append(payload)
    return bindings


def record_graph(
    record: Any,
    access: AccessContext,
    *,
    include_assertion_history: bool = False,
) -> dict[str, Any]:
    """Walkable cELF instance graph around one Record.

    Claims and support bindings are joined server-side by logical Record identity
    and owner scope; the client snapshot only supplies Record state, never claim
    or support authority.
    """
    snapshot = prepare_record_snapshot(record, access)
    bindings = resolved_support_bindings(snapshot, access)
    claim_ids = sorted({
        str(binding.get("claim_id") or "").strip()
        for binding in bindings
        if str(binding.get("claim_id") or "").strip()
    })
    found = system_store.get_generated_claims(claim_ids, owner=access.owner)
    claims = [found[claim_id] for claim_id in claim_ids if claim_id in found]
    try:
        graph = build_record_graph(
            snapshot,
            claims=claims,
            support_bindings=bindings,
            include_assertion_history=include_assertion_history,
        )
    except ValueError as exc:
        raise InvalidQuery(str(exc)) from exc
    graph["record_state_origin"] = "client_snapshot"
    return graph
