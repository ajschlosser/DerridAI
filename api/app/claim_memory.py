# Copyright 2026 Aaron John Schlosser, PhD.
"""Validated-claim memory: reviewer-validated generated claims as retrievable precedent.

SQLite (generated claims + support bindings) is authoritative. A claim enters this
memory only when a human sets its ``validation_status`` to ``validated``. The Chroma
collection is a rebuildable projection: the claim text is the embedded document; its
metadata is the reviewer-validated support (relation, cited Record IDs/revisions) and
a snapshot of the cited Record's *current, checked* attribution assertions.

Retrieval is advisory. Hits are joined back to authoritative rows (a claim that is no
longer validated, or no longer visible to the caller, is dropped) and are shown as
"similar validated claims". They never create support bindings, citations or values.
"""

from __future__ import annotations

import json
import time
from typing import Any

from .field_assertions import current_assertions, migrate_record_assertions
from .metadata_exemplar_retrieval import (
    ChromaMetadataExemplarIndex,
    _bounded_query_text,
    _distance_similarity,
)

COLLECTION_NAME = "derridai_validated_claims"
PROJECTION_VERSION = 1
# Attribution fields whose reviewed values a similar claim may inform.
SEMANTIC_FIELDS = ("speaker", "quoted_speaker", "position_holder", "stance", "discourse_role")
DEFAULT_LIMIT = 5
DEFAULT_MIN_SIMILARITY = 0.55
_USABLE_BINDING = {"validated", "unvalidated"}


def semantic_snapshot(record: dict[str, Any] | None) -> dict[str, Any]:
    """Current present assertion values for the attribution fields, with their authority."""
    if not isinstance(record, dict):
        return {}
    row = json.loads(json.dumps(record))
    migrate_record_assertions(row)
    out: dict[str, Any] = {}
    for assertion in current_assertions(row):
        name = str(assertion.field_name or "")
        if name in SEMANTIC_FIELDS and assertion.value_status == "present":
            out[name] = {"value": assertion.value, "authority": assertion.authority_status}
    return out


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
        record_id = str(binding.get("record_id") or "")
        support.append({
            "record_id": record_id,
            "record_revision": binding.get("record_revision"),
            "relation": binding.get("relation"),
            "source_document_id": binding.get("source_document_id"),
            "semantic": semantic_snapshot((records or {}).get(record_id)),
        })
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
