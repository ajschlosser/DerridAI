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
# Per-field limits come from the schema's retrieval profile; this applies when none is set.
DEFAULT_FIELD_LIMIT = 2
DEFAULT_CORRECTION_LIMIT = 2
# Analogy tiers, best first. "differs" candidates are dropped.
MATCH_TIERS = ("matched", "not_compared")
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
        "field_id": str(exemplar.get("field_id") or ""),
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


def _distance_similarity(value: Any) -> float:
    try:
        distance = max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0
    return 1.0 / (1.0 + distance)


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


def match_tier(
    exemplar: dict[str, Any],
    current_values: dict[str, str],
    match_fields: Iterable[str],
) -> tuple[str, list[str]]:
    """Compare a precedent with the current record on the policy's declared fields.

    Only fields reviewed on *both* sides are compared; an unreviewed side is never
    guessed. Returns ("matched" | "not_compared" | "differs", compared field names).
    """
    theirs = exemplar.get("reviewed_values") if isinstance(exemplar.get("reviewed_values"), dict) else {}
    compared = [name for name in match_fields if name in current_values and name in theirs]
    if not compared:
        return "not_compared", []
    if all(current_values[name] == theirs[name] for name in compared):
        return "matched", compared
    return "differs", compared


def _to_native(value: Any) -> Any:
    """Recursively convert any numpy array/scalar to plain Python lists/floats.

    Chroma may return ``embeddings`` as a top-level ndarray, a list containing
    ndarrays, or plain nested lists depending on version and backend; any numpy
    value left in the tree can raise "truth value of an array is ambiguous"
    the moment calling code puts it in a boolean context (``if``, ``or``).
    """
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [_to_native(item) for item in value]
    return value


def _candidate_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    ids = (payload.get("ids") or [[]])[0]
    distances = (payload.get("distances") or [[]])[0]
    metadatas = (payload.get("metadatas") or [[]])[0]
    embeddings = _to_native(payload.get("embeddings"))
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

    # Collection identity is class-level so other derived semantic projections
    # (for example validated-claim memory) share this compatibility logic.
    SYSTEM_KIND = "metadata_exemplars"
    SCHEMA_KEY = "derridai_exemplar_schema"
    SCHEMA_VERSION = PROJECTION_VERSION
    DESCRIPTION = "Derived evidence-bound metadata exemplars for progressive enrichment."
    TEXT_FIELD = "context_text"
    FILTER_FIELDS = [
        "scope_id",
        "field_name",
        "schema_id",
        "schema_version",
        "assertion_status",
        "kind",
        "language",
        "region_type",
    ]

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
        default_spec = getattr(self.store, "default_embedding_spec", None)
        expected_provider: str | None = None
        expected_model: str | None = None
        if callable(default_spec):
            expected_provider, expected_model = default_spec()
            if expected_provider == "precomputed":
                raise ValueError(
                    "Metadata exemplar retrieval requires a query-capable embedding "
                    "provider; the configured default is precomputed vectors."
                )

        try:
            collection = self.store.client.get_collection(name=self.collection_name)
            metadata = dict(getattr(collection, "metadata", None) or {})
            schema_current = (
                int(metadata.get(self.SCHEMA_KEY) or 0) == self.SCHEMA_VERSION
            )
            embedding_current = True
            embedding_spec = getattr(self.store, "_embedding_spec", None)
            if callable(embedding_spec) and expected_provider:
                current_provider, current_model = embedding_spec(collection)
                embedding_current = (
                    current_provider == expected_provider
                    and (current_model or None) == (expected_model or None)
                )
            if schema_current and embedding_current:
                return collection
            # This collection is derived. Schema or embedding-contract changes
            # are safer to rebuild than to query with stale/incompatible vectors.
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
                description=self.DESCRIPTION,
                embedding_provider=expected_provider,
                embedding_model=expected_model,
                retrieval_mode="semantic",
                text_field=self.TEXT_FIELD,
                filter_fields=list(self.FILTER_FIELDS),
                collection_role=COLLECTION_ROLE,
                protected=True,
                metadata={
                    "derridai_system_collection": self.SYSTEM_KIND,
                    "derridai_hidden_system_collection": True,
                    "derridai_derived": True,
                    self.SCHEMA_KEY: self.SCHEMA_VERSION,
                },
            )
        except Exception as exc:
            # Only an actual create race should be converted into a reopen. The
            # previous broad catch masked provider/configuration failures with the
            # misleading follow-up error "Collection ... does not exist".
            message = str(exc).casefold()
            if "already exists" not in message and "unique" not in message:
                raise
        return self.store.client.get_collection(name=self.collection_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed texts with the provider this projection queries with, without touching any collection.

        Used to rank a record's own source blocks against reviewed precedent evidence; nothing
        is written to Chroma. Raises when retrieval is disabled or vectors cannot be computed.
        """

        if self._disabled_reason:
            raise RuntimeError(self._disabled_reason)
        provider: str | None = None
        model: str | None = None
        default_spec = getattr(self.store, "default_embedding_spec", None)
        if callable(default_spec):
            provider, model = default_spec()
        if provider == "precomputed":
            raise ValueError("Precomputed embeddings cannot embed source blocks for ranking.")
        return self.store.embeddings.embed(
            [_bounded_query_text(str(text)) for text in texts],
            [{} for _ in texts],
            "embedding",
            provider=provider,
            model=model,
        )

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
        field_min_similarity: dict[str, float] | None = None,
        field_include_corrections: dict[str, bool] | None = None,
        field_correction_limits: dict[str, int] | None = None,
        field_match_fields: dict[str, list[str]] | None = None,
        current_values: dict[str, str] | None = None,
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
                limit = max(0, int((field_limits or {}).get(field, DEFAULT_FIELD_LIMIT)))
                correction_limit = (
                    max(0, int((field_correction_limits or {}).get(field, DEFAULT_CORRECTION_LIMIT)))
                    if bool((field_include_corrections or {}).get(field, True))
                    else 0
                )
                if not (limit or correction_limit) or not count:
                    return field, [], 0
                payload = collection.query(
                    query_embeddings=[query_vector],
                    n_results=min(max(limit + correction_limit, int(fetch_k)), count),
                    where=_where(
                        scope_id,
                        field,
                        schema_id,
                        schema_version,
                        language,
                    ),
                    include=["metadatas", "distances", "embeddings"],
                )
                floor = max(0.0, min(1.0, float((field_min_similarity or {}).get(field, 0.0))))
                match_fields = list((field_match_fields or {}).get(field) or [])
                candidates = []
                for row in _candidate_rows(payload):
                    exemplar = canonical.get(row["id"])
                    if exemplar is None or str(exemplar.get("field_name") or "") != field:
                        continue
                    if exclude_record_id and str(exemplar.get("record_id") or "") == str(exclude_record_id):
                        continue
                    if _distance_similarity(row.get("distance")) < floor:
                        continue
                    tier, compared = match_tier(exemplar, current_values or {}, match_fields)
                    if tier == "differs":
                        continue  # declared analogy conditions contradict this precedent
                    candidates.append({**row, "match_tier": tier, "match_compared": compared})
                # Positives (including reviewed absence) and corrections have separate
                # quotas; within each, precedents that satisfy the declared conditions
                # come before ones that could not be compared.
                selected: list[dict[str, Any]] = []
                for is_correction, quota in ((False, limit), (True, correction_limit)):
                    pool = [
                        row for row in candidates
                        if (str(canonical[row["id"]].get("kind") or "positive") == "correction") == is_correction
                    ]
                    for tier in MATCH_TIERS:
                        remaining = quota - sum(
                            1 for row in selected
                            if (str(canonical[row["id"]].get("kind") or "positive") == "correction") == is_correction
                        )
                        if remaining > 0:
                            selected.extend(_mmr([row for row in pool if row["match_tier"] == tier], remaining))
                return field, selected, len(candidates)

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
                    example = prompt_example(exemplar, similarity=similarity)
                    if row.get("match_compared"):
                        example["match"] = {"tier": row["match_tier"], "fields": row["match_compared"]}
                    rendered.setdefault(field, []).append(example)
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
