# Copyright 2026 Aaron John Schlosser, PhD.
"""Derived semantic retrieval for evidence-bound metadata exemplars.

The authoritative facts live on corpus records and their reviewed evidence bindings.
This module owns only a rebuildable vector projection. Retrieval results are joined
back to the canonical exemplars supplied by the caller before anything reaches a
model, so a stale vector row cannot silently become scholarly evidence.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .metadata_exemplars import (
    DEFAULT_PROMPT_TOKEN_BUDGET,
    PROMPT_CHARS_PER_TOKEN,
    prompt_example,
)

COLLECTION_NAME = "derridai_metadata_exemplars"
COLLECTION_ROLE = "general"
PROJECTION_VERSION = 3
DEFAULT_FIELD_LIMITS = {
    "speaker": 2,
    "quoted_speaker": 2,
    "position_holder": 3,
    "stance": 3,
    "discourse_role": 2,
}
DEFAULT_FIELD_LIMIT = 2
DEFAULT_FETCH_K = 16
DEFAULT_MMR_LAMBDA = 0.72
DEFAULT_PACKET_CHAR_BUDGET = DEFAULT_PROMPT_TOKEN_BUDGET * PROMPT_CHARS_PER_TOKEN
MAX_QUERY_CHARS = 12000


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))


def _json_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _projection(exemplar: dict[str, Any], scope_id: str) -> dict[str, Any]:
    """Return the minimal rebuildable vector-store representation."""

    evidence_ref = exemplar.get("evidence_ref") if isinstance(exemplar.get("evidence_ref"), dict) else {}
    return {
        "metadata_exemplar_id": str(exemplar.get("metadata_exemplar_id") or ""),
        "scope_id": str(scope_id),
        "record_id": str(exemplar.get("record_id") or ""),
        "record_revision": exemplar.get("record_revision"),
        "source_document_id": str(exemplar.get("source_document_id") or ""),
        "field_name": str(exemplar.get("field_name") or ""),
        "field_value_json": _json_value(exemplar.get("field_value")),
        "rejected_value_json": _json_value(exemplar.get("rejected_value")) if exemplar.get("rejected_value") is not None else "",
        "kind": str(exemplar.get("kind") or "positive"),
        "assertion_status": str(exemplar.get("assertion_status") or ""),
        "assertion_method": str(exemplar.get("assertion_method") or ""),
        "reviewed_at": str(exemplar.get("reviewed_at") or ""),
        "page_start": exemplar.get("page_start") if exemplar.get("page_start") is not None else "",
        "page_end": exemplar.get("page_end") if exemplar.get("page_end") is not None else "",
        "schema_id": str(exemplar.get("schema_id") or ""),
        "schema_version": str(exemplar.get("schema_version") or ""),
        "language": str(exemplar.get("language") or ""),
        "region_type": str(exemplar.get("region_type") or ""),
        "evidence_hash": str(evidence_ref.get("quote_hash") or ""),
        "evidence_block_ids_json": _json_value(evidence_ref.get("block_ids") or []),
        # The embedded document is intentionally the small context window, never
        # the complete source record unless the evidence itself spans that record.
        "context_text": str(exemplar.get("context_text") or exemplar.get("evidence_text") or ""),
    }


def _bounded_query_text(text: str, *, max_chars: int = MAX_QUERY_CHARS) -> str:
    """Keep embedding input bounded without pretending omitted text disappeared."""

    value = str(text or "")
    limit = max(1000, int(max_chars))
    if len(value) <= limit:
        return value
    half = max(500, (limit - 80) // 2)
    return (
        value[:half]
        + "\n\n[...middle omitted from metadata-retrieval query...]\n\n"
        + value[-half:]
    )


def _cosine(a: Any, b: Any) -> float:
    if a is None or b is None:
        return 0.0
    try:
        left = list(a)
        right = list(b)
    except TypeError:
        return 0.0
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(float(x) * float(y) for x, y in zip(left, right))
    na = math.sqrt(sum(float(x) * float(x) for x in left))
    nb = math.sqrt(sum(float(y) * float(y) for y in right))
    return dot / (na * nb) if na and nb else 0.0


def _mmr(
    candidates: list[dict[str, Any]],
    limit: int,
    *,
    lambda_mult: float = DEFAULT_MMR_LAMBDA,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    remaining = list(candidates)
    while remaining and len(selected) < max(0, int(limit)):
        best_index = 0
        best_score = -float("inf")
        for index, candidate in enumerate(remaining):
            distance = candidate.get("distance")
            try:
                numeric_distance = max(0.0, float(distance))
            except (TypeError, ValueError):
                numeric_distance = 1.0
            relevance = 1.0 / (1.0 + numeric_distance)
            diversity = max(
                (
                    _cosine(candidate.get("embedding"), chosen.get("embedding"))
                    for chosen in selected
                ),
                default=0.0,
            )
            score = lambda_mult * relevance - (1.0 - lambda_mult) * diversity
            if score > best_score:
                best_score = score
                best_index = index
        chosen = dict(remaining.pop(best_index))
        chosen["mmr_score"] = best_score
        selected.append(chosen)
    return selected


def _where(
    scope_id: str,
    field: str,
    schema_id: str,
    schema_version: str,
    language: str,
) -> dict[str, Any]:
    """Keep semantic neighbors inside the current build/schema contract."""

    terms: list[dict[str, Any]] = [
        {"scope_id": str(scope_id)},
        {"field_name": str(field)},
        {"schema_id": str(schema_id or "")},
        {"schema_version": str(schema_version or "")},
    ]
    if language:
        terms.append({"language": str(language)})
    return {"$and": terms}


def _candidate_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    ids = (payload.get("ids") or [[]])[0]
    distances = (payload.get("distances") or [[]])[0]
    metadatas = (payload.get("metadatas") or [[]])[0]
    embeddings = payload.get("embeddings")
    if hasattr(embeddings, "tolist"):
        embeddings = embeddings.tolist()
    embeddings = (embeddings or [[]])[0]

    rows: list[dict[str, Any]] = []
    for index, exemplar_id in enumerate(ids):
        metadata = metadatas[index] if index < len(metadatas) else {}
        rows.append(
            {
                "id": str(exemplar_id),
                "metadata": metadata if isinstance(metadata, dict) else {},
                "distance": distances[index] if index < len(distances) else None,
                "embedding": embeddings[index] if index < len(embeddings) else None,
            }
        )
    return rows


def _bounded_packet(
    by_field: dict[str, list[dict[str, Any]]],
    field_order: Iterable[str],
    *,
    char_budget: int,
) -> tuple[dict[str, list[dict[str, Any]]], int]:
    """Round-robin examples across fields so one field cannot consume the packet."""

    budget = max(0, int(char_budget))
    if not budget:
        return {}, 0
    queues = {field: list(by_field.get(field) or []) for field in field_order}
    kept: dict[str, list[dict[str, Any]]] = {}
    used = 0
    while any(queues.values()):
        progressed = False
        for field in list(queues):
            if not queues[field]:
                continue
            item = queues[field].pop(0)
            size = len(json.dumps(item, ensure_ascii=False, separators=(",", ":"), default=str))
            if used + size > budget:
                queues[field].clear()
                continue
            kept.setdefault(field, []).append(item)
            used += size
            progressed = True
        if not progressed:
            break
    return kept, used


class ChromaMetadataExemplarIndex:
    """Best-effort Chroma projection with one query embedding per record.

    Chroma is deliberately behind this narrow boundary so concurrent work can replace
    the storage adapter without changing exemplar authority, prompt formatting, or
    fallback behavior.
    """

    def __init__(self, store: Any | None = None, *, collection_name: str = COLLECTION_NAME) -> None:
        if store is None:
            from .chroma_store import ChromaStore

            store = ChromaStore()
        self.store = store
        self.collection_name = str(collection_name)
        self._disabled_reason = ""

    @property
    def disabled_reason(self) -> str:
        return self._disabled_reason

    def _ensure(self) -> Any:
        try:
            collection = self.store.client.get_collection(name=self.collection_name)
            metadata = dict(getattr(collection, "metadata", None) or {})
            if int(metadata.get("derridai_exemplar_schema") or 0) == PROJECTION_VERSION:
                return collection
            # This collection is derived. A projection-contract change is safer
            # to rebuild than to query with stale metadata semantics.
            self.store.client.delete_collection(name=self.collection_name)
        except Exception as exc:
            missing = getattr(self.store, "_is_missing_collection_error", None)
            if callable(missing) and not missing(exc):
                raise
            if not callable(missing) and "not found" not in str(exc).casefold():
                raise

        try:
            self.store.create_store(
                self.collection_name,
                description="Derived evidence-bound metadata exemplars for progressive enrichment.",
                retrieval_mode="semantic",
                text_field="context_text",
                filter_fields=[
                    "scope_id",
                    "field_name",
                    "schema_id",
                    "schema_version",
                    "assertion_status",
                    "kind",
                    "language",
                    "region_type",
                ],
                collection_role=COLLECTION_ROLE,
                protected=True,
                metadata={
                    "derridai_system_collection": "metadata_exemplars",
                    "derridai_hidden_system_collection": True,
                    "derridai_derived": True,
                    "derridai_exemplar_schema": PROJECTION_VERSION,
                },
            )
        except Exception:
            # A concurrent request may have created the collection after our
            # existence check. Re-open it before treating creation as failure.
            return self.store.client.get_collection(name=self.collection_name)
        return self.store.client.get_collection(name=self.collection_name)

    def sync(self, scope_id: str, exemplars: list[dict[str, Any]]) -> dict[str, int]:
        """Incrementally mirror known record/field exemplars without scope churn.

        Callers may intentionally omit the current record to prevent self-retrieval.
        Therefore an incremental sync only prunes older rows for record/field keys that
        are represented in the supplied canonical set. A full rebuild is available
        separately when every canonical exemplar for the scope is known.
        """

        collection = self._ensure()
        scope_id = str(scope_id)
        desired = {
            str(item.get("metadata_exemplar_id") or ""): item
            for item in exemplars
            if str(item.get("metadata_exemplar_id") or "")
        }
        projections = {
            exemplar_id: _projection(item, scope_id)
            for exemplar_id, item in desired.items()
        }
        current_payload = collection.get(
            where={"scope_id": scope_id},
            include=["metadatas"],
        )
        current_ids_list = [str(value) for value in (current_payload.get("ids") or [])]
        current_metadatas = list(current_payload.get("metadatas") or [])
        current_ids = set(current_ids_list)
        desired_ids = set(desired)
        desired_keys = {
            (str(item.get("record_id") or ""), str(item.get("field_name") or ""))
            for item in projections.values()
        }

        stale: list[str] = []
        for index, exemplar_id in enumerate(current_ids_list):
            metadata = current_metadatas[index] if index < len(current_metadatas) else {}
            if not isinstance(metadata, dict):
                continue
            key = (
                str(metadata.get("record_id") or ""),
                str(metadata.get("field_name") or ""),
            )
            if key in desired_keys and exemplar_id not in desired_ids:
                stale.append(exemplar_id)
        if stale:
            collection.delete(ids=stale)

        missing = sorted(desired_ids - current_ids)
        if missing:
            self.store.upsert_many(
                self.collection_name,
                [projections[exemplar_id] for exemplar_id in missing],
                document_field="context_text",
                id_field="metadata_exemplar_id",
            )
        return {
            "desired": len(desired_ids),
            "upserted": len(missing),
            "deleted": len(stale),
        }

    def rebuild_scope(self, scope_id: str, exemplars: list[dict[str, Any]]) -> dict[str, int]:
        """Delete and recreate one derived scope from canonical reviewed data."""

        collection = self._ensure()
        payload = collection.get(where={"scope_id": str(scope_id)}, include=["metadatas"])
        existing = [str(value) for value in (payload.get("ids") or [])]
        if existing:
            collection.delete(ids=existing)
        desired = [
            item
            for item in exemplars
            if str(item.get("metadata_exemplar_id") or "")
        ]
        if desired:
            self.store.upsert_many(
                self.collection_name,
                [_projection(item, str(scope_id)) for item in desired],
                document_field="context_text",
                id_field="metadata_exemplar_id",
            )
        return {
            "desired": len(desired),
            "upserted": len(desired),
            "deleted": len(existing),
        }

    def retrieve(
        self,
        *,
        scope_id: str,
        query_text: str,
        exemplars: list[dict[str, Any]],
        fields: Iterable[str],
        schema_id: str = "",
        schema_version: str = "",
        language: str = "",
        field_limits: dict[str, int] | None = None,
        packet_char_budget: int = DEFAULT_PACKET_CHAR_BUDGET,
        fetch_k: int = DEFAULT_FETCH_K,
        exclude_record_id: str = "",
    ) -> dict[str, Any]:
        """Sync canonical exemplars, retrieve per field, and return a bounded packet."""

        if self._disabled_reason:
            return {
                "ok": False,
                "examples": {},
                "telemetry": {"fallback_reason": self._disabled_reason},
            }

        started_total = time.monotonic()
        canonical = {
            str(item.get("metadata_exemplar_id") or ""): item
            for item in exemplars
            if str(item.get("metadata_exemplar_id") or "")
        }
        ordered_fields = list(dict.fromkeys(str(field) for field in fields if str(field)))
        if not canonical or not str(query_text or "").strip() or not ordered_fields:
            return {
                "ok": True,
                "examples": {},
                "telemetry": {
                    "sync_ms": 0,
                    "query_ms": 0,
                    "search_ms": 0,
                    "select_ms": 0,
                    "examples_considered": 0,
                    "examples_used": 0,
                    "packet_chars": 0,
                    "total_ms": _elapsed_ms(started_total),
                },
            }

        try:
            sync_started = time.monotonic()
            sync_stats = self.sync(scope_id, list(canonical.values()))
            sync_ms = _elapsed_ms(sync_started)
            collection = self._ensure()

            query_started = time.monotonic()
            provider, model = self.store._embedding_spec(collection)
            query_vector = self.store.embeddings.embed_query(
                _bounded_query_text(str(query_text)),
                provider=provider,
                model=model,
            )
            query_ms = _elapsed_ms(query_started)

            search_started = time.monotonic()
            raw: dict[str, list[dict[str, Any]]] = {}
            considered = 0
            count = int(collection.count())

            def search_field(field: str) -> tuple[str, list[dict[str, Any]], int]:
                limit = max(
                    0,
                    int(
                        (field_limits or {}).get(
                            field,
                            DEFAULT_FIELD_LIMITS.get(field, DEFAULT_FIELD_LIMIT),
                        )
                    ),
                )
                if not limit or not count:
                    return field, [], 0
                payload = collection.query(
                    query_embeddings=[query_vector],
                    n_results=min(max(limit, int(fetch_k)), count),
                    where=_where(
                        scope_id,
                        field,
                        schema_id,
                        schema_version,
                        language,
                    ),
                    include=["metadatas", "distances", "embeddings"],
                )
                candidates = [
                    row
                    for row in _candidate_rows(payload)
                    if row["id"] in canonical
                    and str(canonical[row["id"]].get("field_name") or "") == field
                    and (
                        not exclude_record_id
                        or str(canonical[row["id"]].get("record_id") or "")
                        != str(exclude_record_id)
                    )
                ]
                return field, _mmr(candidates, limit), len(candidates)

            if ordered_fields and count:
                # One query embedding is shared by a small bounded worker pool.
                # Independent field filters can therefore overlap local/HTTP
                # Chroma latency without multiplying embedding/model calls.
                with ThreadPoolExecutor(
                    max_workers=min(4, len(ordered_fields)),
                    thread_name_prefix="metadata-exemplar-search",
                ) as executor:
                    futures = [
                        executor.submit(search_field, field)
                        for field in ordered_fields
                    ]
                    for future in futures:
                        field, selected, field_considered = future.result()
                        considered += field_considered
                        if selected:
                            raw[field] = selected
            search_ms = _elapsed_ms(search_started)

            select_started = time.monotonic()
            rendered: dict[str, list[dict[str, Any]]] = {}
            for field, rows in raw.items():
                for row in rows:
                    exemplar = canonical.get(row["id"])
                    if exemplar is None:
                        continue
                    distance = row.get("distance")
                    try:
                        similarity = 1.0 / (1.0 + max(0.0, float(distance)))
                    except (TypeError, ValueError):
                        similarity = None
                    rendered.setdefault(field, []).append(
                        prompt_example(exemplar, similarity=similarity)
                    )
            packet, packet_chars = _bounded_packet(
                rendered,
                ordered_fields,
                char_budget=packet_char_budget,
            )
            select_ms = _elapsed_ms(select_started)
            used = sum(len(items) for items in packet.values())
            return {
                "ok": True,
                "examples": packet,
                "telemetry": {
                    "sync_ms": sync_ms,
                    "query_ms": query_ms,
                    "search_ms": search_ms,
                    "select_ms": select_ms,
                    "examples_considered": considered,
                    "examples_used": used,
                    "packet_chars": packet_chars,
                    "fields_served": sorted(packet),
                    "sync": sync_stats,
                    "total_ms": _elapsed_ms(started_total),
                },
            }
        except Exception as exc:  # noqa: BLE001 - progressive RAG is advisory
            self._disabled_reason = f"{exc.__class__.__name__}: {str(exc)[:300]}"
            return {
                "ok": False,
                "examples": {},
                "telemetry": {
                    "fallback_reason": self._disabled_reason,
                    "total_ms": _elapsed_ms(started_total),
                },
            }
