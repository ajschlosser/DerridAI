# Copyright 2026 Aaron John Schlosser, PhD.
"""Validated-claim memory: reviewer-validated generated claims as retrievable precedent.

SQLite (generated claims + support bindings) is authoritative. A claim enters this
memory only when a human sets its ``validation_status`` to ``validated`` and at least
one usable support binding resolves to a Record. The Chroma collection is a rebuildable projection: the claim text is the embedded document; its
metadata is the reviewer-validated support (relation, cited Record IDs/revisions) and
a snapshot of the cited Record's *current, checked* attribution assertions.

Retrieval is advisory. Hits are joined back to authoritative rows (a claim that is no
longer validated, or no longer visible to the caller, is dropped) and are shown as
"similar validated claims". They never create support bindings, citations or values.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from .field_assertions import current_assertions, migrate_record_assertions
from .metadata_exemplar_retrieval import (
    ChromaMetadataExemplarIndex,
    _bounded_query_text,
    _distance_similarity,
)
from .provenance_memory import SupportBinding, resolve_support_binding

COLLECTION_NAME = "derridai_validated_claims"
# 2: schema-agnostic reviewed-field snapshot and deterministic citations in support.
PROJECTION_VERSION = 2
DEFAULT_LIMIT = 5
DEFAULT_MIN_SIMILARITY = 0.55
# Bounds the snapshot so a wide schema cannot bloat projection metadata.
SNAPSHOT_FIELD_LIMIT = 24
VALIDATION_STATUSES = {"unvalidated", "validated", "rejected", "unresolved"}
_USABLE_BINDING = {"validated", "unvalidated"}


def semantic_snapshot(record: dict[str, Any] | None) -> dict[str, Any]:
    """Reviewed, present field values of a cited Record, keyed by field name.

    The snapshot is schema-agnostic: it does not know which fields matter for
    attribution. Only human-reviewed values are kept, because an unreviewed model
    value is not a fact about the Record that a later comparison may rely on.
    """
    if not isinstance(record, dict):
        return {}
    row = json.loads(json.dumps(record))
    migrate_record_assertions(row)
    out: dict[str, Any] = {}
    for assertion in current_assertions(row):
        name = str(assertion.field_name or assertion.field_id or "")
        if not name or assertion.value_status != "present" or assertion.authority_status == "unreviewed":
            continue
        out[name] = {
            "value": assertion.value,
            "authority": assertion.authority_status,
            "field_id": assertion.field_id,
        }
        if len(out) >= SNAPSHOT_FIELD_LIMIT:
            break
    return out


def _verified_record(binding: dict[str, Any], record: dict[str, Any] | None) -> dict[str, Any] | None:
    """Use a caller-supplied Record only when it resolves against the binding's identity and revision."""
    if not isinstance(record, dict) or str(record.get("record_id") or "") != str(binding.get("record_id") or ""):
        return None
    try:
        resolved = resolve_support_binding(SupportBinding.model_validate(binding), lambda _requested: record)
    except Exception:
        return None
    return record if resolved.validation_status == "validated" else None


def derive_entry(
    claim: dict[str, Any],
    bindings: list[dict[str, Any]],
    records: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Canonical memory entry for one validated claim, or None if it is not eligible."""
    if str(claim.get("validation_status") or "") != "validated":
        return None
    claim_id = str(claim.get("claim_id") or "").strip()
    text = str(claim.get("claim_text") or "").strip()
    if not claim_id or not text:
        return None
    support = []
    for binding in bindings:
        if str(binding.get("claim_id") or "") != claim_id:
            continue
        if str(binding.get("validation_status") or "unvalidated") not in _USABLE_BINDING:
            continue
        record_id = str(binding.get("record_id") or "").strip()
        relation = str(binding.get("relation") or "").strip()
        if not record_id or not relation:
            continue
        citation = binding.get("citation") if isinstance(binding.get("citation"), dict) else {}
        support.append({
            "record_id": record_id,
            "record_revision": binding.get("record_revision"),
            "relation": relation,
            "source_document_id": binding.get("source_document_id"),
            # Citations were rendered by deterministic code when the claim was bound.
            "citation": {key: citation.get(key) for key in ("inline", "full") if citation.get(key)},
            "semantic": semantic_snapshot(_verified_record(binding, (records or {}).get(record_id))),
        })
    # Validated-claim memory is provenance memory, not a bag of approved prose.
    # A legacy or malformed claim with no usable evidence binding must never become
    # retrievable precedent merely because its validation_status says "validated".
    if not support:
        return None
    return {
        "claim_id": claim_id,
        "claim_text": text,
        "owner": claim.get("owner"),
        "run_id": claim.get("run_id"),
        "validated_by": claim.get("validated_by"),
        "validated_at": claim.get("validated_at"),
        "support": support,
    }


def _projection(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": entry["claim_id"],
        "owner": str(entry.get("owner") or ""),
        "run_id": str(entry.get("run_id") or ""),
        "validated_by": str(entry.get("validated_by") or ""),
        "validated_at": str(entry.get("validated_at") or ""),
        "support_json": json.dumps(entry["support"], ensure_ascii=False, sort_keys=True),
        "claim_text": entry["claim_text"],
    }


class ClaimMemoryIndex(ChromaMetadataExemplarIndex):
    """Derived vector projection of validated claims (owner-scoped)."""

    SYSTEM_KIND = "validated_claims"
    SCHEMA_KEY = "derridai_claim_memory_schema"
    SCHEMA_VERSION = PROJECTION_VERSION
    DESCRIPTION = "Derived memory of reviewer-validated generated claims."
    TEXT_FIELD = "claim_text"
    FILTER_FIELDS = ["owner", "run_id"]

    def __init__(self, store: Any | None = None) -> None:
        super().__init__(store, collection_name=COLLECTION_NAME)

    def upsert(self, entry: dict[str, Any]) -> None:
        self._ensure()
        self.store.upsert_many(
            self.collection_name, [_projection(entry)], document_field="claim_text", id_field="claim_id"
        )

    def remove(self, claim_id: str) -> None:
        self._ensure().delete(ids=[str(claim_id)])

    def rebuild(self, system_store: Any) -> int:
        """Recreate the projection from authoritative validated claims."""
        collection = self._ensure()
        existing = [str(value) for value in (collection.get(include=[]).get("ids") or [])]
        if existing:
            collection.delete(ids=existing)
        entries = []
        for claim in system_store.list_generated_claims(validation_status="validated", limit=1000):
            entry = derive_entry(claim, system_store.list_claim_support_bindings(str(claim.get("claim_id") or "")))
            if entry is not None:
                entries.append(_projection(entry))
        if entries:
            self.store.upsert_many(self.collection_name, entries, document_field="claim_text", id_field="claim_id")
        return len(entries)

    def ensure_current(self, system_store: Any) -> None:
        """Rebuild when the projection was (re)created empty, e.g. after an embedding change."""
        if int(self._ensure().count()) == 0 and system_store.list_generated_claims(validation_status="validated", limit=1):
            self.rebuild(system_store)

    def similar(
        self,
        claim_text: str,
        *,
        owner: str | None,
        exclude_claim_id: str = "",
        limit: int = DEFAULT_LIMIT,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ) -> list[dict[str, Any]]:
        """Raw projection hits (id, similarity, metadata); callers must re-join to authority."""
        text = _bounded_query_text(str(claim_text or ""))
        if not text.strip():
            return []
        collection = self._ensure()
        count = int(collection.count())
        if not count:
            return []
        provider, model = self.store._embedding_spec(collection)
        vector = self.store.embeddings.embed_query(text, provider=provider, model=model)
        payload = collection.query(
            query_embeddings=[vector],
            n_results=min(count, max(1, int(limit)) + 1),
            where={"owner": str(owner)} if owner is not None else None,
            include=["metadatas", "distances"],
        )
        ids = (payload.get("ids") or [[]])[0]
        distances = (payload.get("distances") or [[]])[0]
        metadatas = (payload.get("metadatas") or [[]])[0]
        hits = []
        for index, claim_id in enumerate(ids):
            similarity = _distance_similarity(distances[index] if index < len(distances) else None)
            if str(claim_id) == exclude_claim_id or similarity < min_similarity:
                continue
            hits.append({"claim_id": str(claim_id), "similarity": round(similarity, 4), "metadata": metadatas[index] if index < len(metadatas) else {}})
        return hits[: int(limit)]


def similar_validated_claims(
    index: ClaimMemoryIndex,
    system_store: Any,
    claim: dict[str, Any],
    *,
    owner: str | None,
    limit: int = DEFAULT_LIMIT,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> dict[str, Any]:
    """Advisory precedents for ``claim``, re-joined to authoritative validated rows."""
    started = time.monotonic()
    claim_id = str(claim.get("claim_id") or "")
    hits = index.similar(
        str(claim.get("claim_text") or ""), owner=owner, exclude_claim_id=claim_id,
        limit=limit, min_similarity=min_similarity,
    )
    items = []
    for hit in hits:
        authority = system_store.get_generated_claim(hit["claim_id"], owner=owner)
        if not authority or str(authority.get("validation_status") or "") != "validated":
            continue  # stale projection row: never surfaced
        bindings = system_store.list_claim_support_bindings(hit["claim_id"], owner=owner)
        entry = derive_entry(authority, bindings)
        if entry is None:
            continue
        stored = {}
        try:
            stored = {str(item.get("record_id")): item.get("semantic") for item in json.loads(hit["metadata"].get("support_json") or "[]")}
        except (TypeError, ValueError):
            pass
        for item in entry["support"]:
            item["semantic"] = stored.get(str(item.get("record_id"))) or {}
        items.append({**entry, "similarity": hit["similarity"], "advisory": True})
    return {"items": items, "elapsed_ms": int((time.monotonic() - started) * 1000)}


def apply_claim_validation(
    system_store: Any,
    claim: dict[str, Any],
    *,
    status: str,
    actor: str,
    owner: str | None,
    record: dict[str, Any] | None = None,
    index_factory: Callable[[], ClaimMemoryIndex],
) -> dict[str, Any]:
    """Record a human audit decision on a generated claim, then update the projection.

    A claim cannot be validated without at least one usable support binding. The
    SQLite row is authoritative and committed first once the decision is admissible.
    ``validated`` adds the claim to validated-claim memory; any other status removes
    it. A projection failure is reported in the result and never undoes or hides the
    audit decision.
    """
    if status not in VALIDATION_STATUSES:
        raise ValueError("status must be unvalidated, validated, rejected, or unresolved")
    claim = {
        **claim,
        "validation_status": status,
        "validated_by": None if status == "unvalidated" else actor,
        "validated_at": None if status == "unvalidated" else datetime.now(UTC).isoformat(),
    }
    records = {str(record["record_id"]): record} if isinstance(record, dict) and record.get("record_id") else {}
    bindings = system_store.list_claim_support_bindings(str(claim["claim_id"]), owner=owner)
    entry = derive_entry(claim, bindings, records)
    if status == "validated" and entry is None:
        raise ValueError(
            "A claim requires at least one usable support binding before it can be validated."
        )

    # The audit row is canonical and is committed before touching the rebuildable
    # vector projection. Projection failures therefore never erase a valid decision.
    system_store.put_generated_claim(claim)
    projection = {"status": "removed" if entry is None else "indexed", "error": ""}
    try:
        index = index_factory()
        if entry is not None:
            index.upsert(entry)
        else:
            index.remove(str(claim["claim_id"]))
    except Exception as exc:  # noqa: BLE001 - the projection is derived; surface, do not fail
        projection = {"status": "failed", "error": str(exc)[:300]}
    return {"claim": claim, "projection": projection}


def validated_claims_citing(system_store: Any, record: dict[str, Any], *, limit: int = 50) -> list[dict[str, Any]]:
    """Reviewer-validated Research claims whose support cites ``record``.

    A cross-reference for Record Review, not metadata memory: each binding is
    re-resolved against the record as it is now, so support bound to an earlier
    revision is shown as stale rather than silently applied to the current text.
    """
    record_id = str(record.get("record_id") or "")
    if not record_id:
        return []
    resolver_record = dict(record)
    if not resolver_record.get("source_document_id") and resolver_record.get("source_asset_id"):
        resolver_record["source_document_id"] = resolver_record["source_asset_id"]
    out: list[dict[str, Any]] = []
    for raw in system_store.list_claim_support_bindings_for_record(record_id, owner=None, limit=200):
        claim = system_store.get_generated_claim(str(raw.get("claim_id") or ""))
        if not claim or str(claim.get("validation_status") or "") != "validated":
            continue
        try:
            binding = resolve_support_binding(SupportBinding.model_validate(raw), lambda _requested: resolver_record)
            status = binding.validation_status
        except Exception:  # noqa: BLE001 - malformed history stays visible as unresolved
            status = "unresolved"
        citation = raw.get("citation") if isinstance(raw.get("citation"), dict) else {}
        out.append({
            "claim_id": claim.get("claim_id"),
            "claim_text": claim.get("claim_text"),
            "run_id": claim.get("run_id"),
            "validated_by": claim.get("validated_by"),
            "validated_at": claim.get("validated_at"),
            "relation": raw.get("relation"),
            "record_revision": raw.get("record_revision"),
            "citation": {key: citation.get(key) for key in ("inline", "full") if citation.get(key)},
            "binding_status": "current" if status == "validated" else status,
        })
        if len(out) >= limit:
            break
    return out
