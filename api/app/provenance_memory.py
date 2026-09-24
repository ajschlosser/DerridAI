# Copyright 2026 Aaron John Schlosser, PhD.
"""Canonical, permission-aware memory and claim provenance.

Chroma and other search indexes may project these objects, but this module
keeps the durable decision and claim/support relationships in SQLite.  A
binding is intentionally resolved again against the corpus before it is used
as current evidence.
"""

from __future__ import annotations

import copy
import hashlib
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .system_store import system_store

DecisionKind = Literal["value", "absence", "correction"]
SupportRelation = Literal["supports", "contrasts", "qualifies", "quotes", "attribution"]


def _now() -> str:
    return datetime.now(UTC).isoformat()


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_document_id: str
    source_unit_ids: list[str] = Field(default_factory=list)
    physical_page_start: int | None = None
    physical_page_end: int | None = None
    printed_page_start: str | int | None = None
    printed_page_end: str | int | None = None
    character_start: int | None = Field(default=None, ge=0)
    character_end: int | None = Field(default=None, ge=0)


class MetadataMemoryBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    binding_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    record_id: str
    record_revision: int | None = Field(default=None, ge=1)
    source_document_id: str | None = None
    field_id: str
    field_name: str | None = None
    schema_id: str | None = None
    schema_version: str | None = None
    decision_kind: DecisionKind
    value: Any = None
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    visibility: Literal["corpus", "owner"] = "corpus"
    owner: str | None = None
    created_at: str = Field(default_factory=_now)

    @classmethod
    def absence(cls, **kwargs: Any) -> MetadataMemoryBinding:
        return cls(decision_kind="absence", value=None, **kwargs)

    @classmethod
    def correction(cls, *, rejected_value: Any = None, **kwargs: Any) -> MetadataMemoryBinding:
        payload = dict(kwargs)
        payload["value"] = {"accepted": payload.get("value"), "rejected": rejected_value}
        return cls(decision_kind="correction", **payload)


class GeneratedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str | None = None
    response_record_id: str | None = None
    owner: str | None = None
    claim_text: str = Field(min_length=1)
    answer_start: int | None = Field(default=None, ge=0)
    answer_end: int | None = Field(default=None, ge=0)
    validation_status: Literal["unvalidated", "validated", "rejected", "unresolved"] = "unvalidated"
    created_at: str = Field(default_factory=_now)


class SupportBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    support_binding_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim_id: str
    owner: str | None = None
    record_id: str
    record_revision: int | None = Field(default=None, ge=1)
    source_document_id: str | None = None
    source_spans: list[EvidenceSpan] = Field(default_factory=list)
    relation: SupportRelation
    citation: dict[str, Any] | None = None
    validation_status: Literal["unvalidated", "validated", "stale", "rejected", "unresolved"] = "unvalidated"
    created_at: str = Field(default_factory=_now)


def persist_record_decision(
    *,
    record: dict[str, Any],
    schema: Any,
    field_name: str,
    value: Any,
    decision_kind: DecisionKind = "value",
    owner: str | None = None,
    rejected_value: Any = None,
) -> MetadataMemoryBinding:
    """Create a binding from the canonical record's reviewed evidence."""
    spans: list[EvidenceSpan] = []
    evidence = record.get("metadata_evidence") or {}
    field_evidence = evidence.get(field_name) if isinstance(evidence, dict) else None
    block_ids = field_evidence.get("block_ids") if isinstance(field_evidence, dict) else []
    source_document_id = str(record.get("source_document_id") or "").strip()
    if block_ids and source_document_id:
        spans.append(EvidenceSpan(
            source_document_id=source_document_id,
            source_unit_ids=[str(item) for item in block_ids if str(item).strip()],
        ))
    if decision_kind == "correction":
        value = {"accepted": value, "rejected": rejected_value}
    try:
        field_id = schema.field_id(field_name)
    except KeyError:
        # Source/document fields predate user-schema identities. They remain
        # eligible for audit memory under a deterministic compatibility ID.
        field_id = f"legacy.{uuid.uuid5(uuid.NAMESPACE_URL, 'derridai:field:' + field_name)}"
    binding = MetadataMemoryBinding(
        record_id=str(record.get("record_id") or ""),
        record_revision=int(record.get("record_revision") or 1),
        source_document_id=source_document_id or None,
        field_id=field_id,
        field_name=field_name,
        schema_id=str(getattr(schema, "id", "") or "") or None,
        schema_version=str(getattr(schema, "schema_version", "") or "") or None,
        decision_kind=decision_kind,
        value=value,
        evidence=spans,
        visibility="owner" if owner else "corpus",
        owner=owner,
    )
    return persist_metadata_decision(binding)


def persist_metadata_decision(binding: MetadataMemoryBinding) -> MetadataMemoryBinding:
    """Persist one reviewed decision and enqueue rebuildable projections."""
    if binding.decision_kind == "absence" and binding.value is not None:
        raise ValueError("An explicit absence cannot carry a value.")
    system_store.put_memory_binding(binding.model_dump(mode="json"))
    system_store.mark_semantic_memory_dirty(
        "metadata_exemplars", record_id=binding.record_id, reason="reviewed_metadata_decision"
    )
    return binding


def persist_generated_claim(claim: GeneratedClaim) -> GeneratedClaim:
    system_store.put_generated_claim(claim.model_dump(mode="json"))
    return claim


def persist_support_binding(binding: SupportBinding) -> SupportBinding:
    system_store.put_claim_support_binding(binding.model_dump(mode="json"))
    return binding


def resolve_support_binding(
    binding: SupportBinding,
    resolver: Callable[[str], dict[str, Any] | None],
) -> SupportBinding:
    """Re-resolve a support binding against current canonical corpus state.

    A missing record, revision mismatch, source mismatch, or failed exact quote
    check is represented as stale/unresolved rather than silently reused.
    """
    record = resolver(binding.record_id)
    if not record:
        return binding.model_copy(update={"validation_status": "stale"})
    current_revision = int(record.get("record_revision") or 1)
    if binding.record_revision is not None and current_revision != binding.record_revision:
        return binding.model_copy(update={"validation_status": "stale"})
    if binding.source_document_id and str(record.get("source_document_id") or "") != binding.source_document_id:
        return binding.model_copy(update={"validation_status": "stale"})
    spans = [span.model_dump(mode="json") for span in binding.source_spans]
    if spans:
        known: set[str] = {
            str(value) for value in record.get("source_block_ids") or [] if str(value).strip()
        }
        for item in record.get("source_spans") or []:
            if not isinstance(item, dict):
                continue
            known.update(str(value) for value in item.get("source_unit_ids") or [] if str(value).strip())
            for key in ("source_unit_id", "block_id"):
                value = str(item.get(key) or "").strip()
                if value:
                    known.add(value)
        requested = {unit for span in spans for unit in span.get("source_unit_ids", [])}
        if requested and not requested.issubset(known):
            return binding.model_copy(update={"validation_status": "stale"})
    return binding.model_copy(update={"validation_status": "validated"})


def semantic_identity(value: Any) -> str:
    """Stable digest for projection de-duplication, never an authority key."""
    return hashlib.sha256(
        repr(copy.deepcopy(value)).encode("utf-8", errors="replace")
    ).hexdigest()
