# Copyright 2026 Aaron John Schlosser, PhD.
"""Derived semantic retrieval for evidence-bound metadata exemplars.

The authoritative facts live on corpus records and their reviewed evidence bindings.
This module owns only a rebuildable vector projection. Retrieval results are joined
back to the canonical exemplars supplied by the caller before anything reaches a
model, so a stale vector row cannot silently become scholarly evidence.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .config import settings
from .cross_encoder import predict_scores
from .metadata_exemplars import (
    DEFAULT_PROMPT_TOKEN_BUDGET,
    PROMPT_CHARS_PER_TOKEN,
    prompt_example,
)
from .retrieval_selection import cosine_similarity, distance_to_relevance, mmr_select

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
MAX_FALLBACK_CANDIDATES = 256
_STOP_WORDS = {
    "en": {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
        "in", "is", "it", "of", "on", "or", "that", "the", "their", "this",
        "to", "was", "were", "with",
    },
    "fr": {
        "au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du", "elle",
        "en", "est", "et", "les", "leur", "mais", "ne", "ou", "par", "pour",
        "que", "qui", "sur", "un", "une",
    },
}


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


def _retrieval_query_text(text: str, language: str = "") -> str:
    """Remove only high-frequency function words from the embedding query.

    The authoritative evidence and stored exemplar text are never changed. If
    filtering would erase the query, the original bounded text is retained.
    """

    value = _bounded_query_text(text)
    words = str(language or "").casefold().split("-")
    stop_words = _STOP_WORDS.get(words[0], set())
    if not stop_words:
        return value
    filtered = " ".join(
        token for token in value.split()
        if token.casefold().strip(".,;:!?()[]{}\"'") not in stop_words
    )
    return filtered.strip() or value


def _lexical_overlap(query: str, text: str, language: str = "") -> float:
    stop_words = _STOP_WORDS.get(str(language or "").casefold().split("-")[0], set())

    def terms(value: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[\wÀ-ÿ'-]+", value.casefold())
            if token not in stop_words
        }

    query_terms = terms(_retrieval_query_text(query, language))
    text_terms = terms(str(text or ""))
    if not query_terms:
        return 0.0
    return len(query_terms & text_terms) / len(query_terms)


def _fallback_text(exemplar: dict[str, Any]) -> str:
    return " ".join(
        str(exemplar.get(key) or "")
        for key in ("field_name", "field_value", "rejected_value", "evidence_text", "context_text")
    )


def _fallback_candidates(
    *,
    canonical: dict[str, dict[str, Any]],
    query_text: str,
    fields: list[str],
    language: str,
    current_values: dict[str, str],
    field_match_fields: dict[str, list[str]],
    exclude_record_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """Return conservative lexical matches when semantic retrieval is unavailable."""

    ranked: dict[str, list[dict[str, Any]]] = {}
    for exemplar in list(canonical.values())[:MAX_FALLBACK_CANDIDATES]:
        field = str(exemplar.get("field_name") or "")
        if field not in fields:
            continue
        if exclude_record_id and str(exemplar.get("record_id") or "") == str(exclude_record_id):
            continue
        tier, compared = match_tier(
            exemplar,
            current_values,
            list(field_match_fields.get(field) or []),
        )
        if tier == "differs":
            continue
        score = _lexical_overlap(query_text, _fallback_text(exemplar), language)
        if score <= 0.0:
            continue
        ranked.setdefault(field, []).append({
            "id": str(exemplar.get("metadata_exemplar_id") or ""),
            "distance": None,
            "embedding": None,
            "match_tier": tier,
            "match_compared": compared,
            "lexical_score": score,
            "hybrid_score": score,
            "fallback": True,
        })
    for _field, rows in ranked.items():
        rows.sort(
            key=lambda row: (
                -float(row["lexical_score"]),
                str(canonical[row["id"]].get("metadata_exemplar_id") or ""),
            )
        )
    return ranked


def _cosine(a: Any, b: Any) -> float:
    """Compatibility wrapper around the shared vector similarity primitive."""

    return cosine_similarity(a, b)


def _distance_similarity(value: Any, metric: str | None = None) -> float:
    """Normalize collection-native distance while preserving legacy callers."""

    return distance_to_relevance(value, metric)


def _mmr(
    candidates: list[dict[str, Any]],
    limit: int,
    *,
    lambda_mult: float = DEFAULT_MMR_LAMBDA,
) -> list[dict[str, Any]]:
    """Select diverse precedents without overwriting their relevance scores."""

    return mmr_select(
        candidates,
        limit=limit,
        lambda_mult=lambda_mult,
        relevance=lambda candidate: float(
            candidate.get("hybrid_score")
            if candidate.get("hybrid_score") is not None
            else _distance_similarity(
                candidate.get("distance"),
                candidate.get("distance_metric"),
            )
        ),
        vector=lambda candidate: candidate.get("embedding"),
    )

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


def _as_sequence(value: Any) -> list[Any]:
    """Convert Chroma/numpy response values without evaluating array truthiness."""
    if value is None:
        return []
    converted = value.tolist() if hasattr(value, "tolist") else value
    if converted is not value:
        value = converted
    if isinstance(value, (list, tuple)):
        return list(value)
    try:
        return list(value)
    except TypeError:
        return []


def _first_query_row(value: Any) -> list[Any]:
    rows = _as_sequence(value)
    if not rows:
        return []
    return _as_sequence(rows[0])


def _candidate_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    ids = _first_query_row(payload.get("ids"))
    distances = _first_query_row(payload.get("distances"))
    metadatas = _first_query_row(payload.get("metadatas"))
    documents = _first_query_row(payload.get("documents"))
    embeddings = _first_query_row(payload.get("embeddings"))

    rows: list[dict[str, Any]] = []
    for index, exemplar_id in enumerate(ids):
        metadata = metadatas[index] if index < len(metadatas) else {}
        row: dict[str, Any] = {
            "id": str(exemplar_id),
            "metadata": metadata if isinstance(metadata, dict) else {},
            "distance": distances[index] if index < len(distances) else None,
            "embedding": embeddings[index] if index < len(embeddings) else None,
        }
        if index < len(documents):
            row["document"] = documents[index]
        rows.append(row)
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


def _rerank_candidates(
    by_field: dict[str, list[dict[str, Any]]],
    *,
    canonical: dict[str, dict[str, Any]],
    query_text: str,
    enabled: bool,
    top_k: int,
    model_name: str,
    timeout_seconds: float,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Rerank a small field-balanced candidate set, preserving all other rows."""

    selected: list[dict[str, Any]] = []
    queues = {
        field: sorted(
            by_field[field],
            key=lambda item: (
                -float(item.get("hybrid_score") or 0.0),
                str(item.get("id") or ""),
            ),
        )
        for field in by_field
    }
    while queues and len(selected) < max(0, int(top_k)):
        progressed = False
        for field in list(queues):
            if queues[field] and len(selected) < max(0, int(top_k)):
                selected.append(queues[field].pop(0))
                progressed = True
            if not queues[field]:
                queues.pop(field, None)
        if not progressed:
            break
    telemetry: dict[str, Any] = {
        "mode": "hybrid",
        "provider": "sentence-transformers",
        "model": model_name,
        "candidate_count": len(selected),
        "reranked_count": 0,
        "timing_ms": 0,
    }
    if not enabled:
        telemetry["mode"] = "disabled"
        telemetry["fallback_reason"] = "cross_encoder_disabled"
        return by_field, telemetry
    if not selected:
        telemetry["mode"] = "not_needed"
        telemetry["fallback_reason"] = "no_candidates"
        return by_field, telemetry
    scores, result = predict_scores(
        [
            (
                query_text,
                str(
                    row.get("document")
                    or (row.get("metadata") or {}).get("context_text")
                    or canonical.get(str(row.get("id") or ""), {}).get("context_text")
                    or canonical.get(str(row.get("id") or ""), {}).get("evidence_text")
                    or "",
                ),
            )
            for row in selected
        ],
        model_name=model_name,
        timeout_seconds=timeout_seconds,
    )
    telemetry.update(result)
    if scores is None:
        telemetry["mode"] = "hybrid"
        return by_field, telemetry
    reranked_ids = {str(row.get("id") or "") for row in selected}
    score_by_id = {
        str(row.get("id") or ""): score
        for row, score in zip(selected, scores)
    }
    updated: dict[str, list[dict[str, Any]]] = {}
    for field, rows in by_field.items():
        field_rows = []
        for row in rows:
            copy = dict(row)
            row_id = str(row.get("id") or "")
            if row_id in reranked_ids:
                copy["hybrid_score"] = score_by_id[row_id]
                copy["rerank_score"] = score_by_id[row_id]
                copy["reranked"] = True
            field_rows.append(copy)
        updated[field] = field_rows
    telemetry["mode"] = "cross_encoder"
    return updated, telemetry


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

    def _lexical_fallback_result(
        self,
        *,
        started_total: float,
        canonical: dict[str, dict[str, Any]],
        query_text: str,
        ordered_fields: list[str],
        language: str,
        field_limits: dict[str, int] | None,
        field_include_corrections: dict[str, bool] | None,
        field_correction_limits: dict[str, int] | None,
        field_match_fields: dict[str, list[str]] | None,
        current_values: dict[str, str] | None,
        packet_char_budget: int,
        exclude_record_id: str,
        reason: str,
    ) -> dict[str, Any]:
        raw = _fallback_candidates(
            canonical=canonical,
            query_text=query_text,
            fields=ordered_fields,
            language=language,
            current_values=current_values or {},
            field_match_fields=field_match_fields or {},
            exclude_record_id=exclude_record_id,
        )
        selected: dict[str, list[dict[str, Any]]] = {}
        considered = 0
        for field in ordered_fields:
            limit = max(0, int((field_limits or {}).get(field, DEFAULT_FIELD_LIMIT)))
            correction_limit = (
                max(0, int((field_correction_limits or {}).get(field, DEFAULT_CORRECTION_LIMIT)))
                if bool((field_include_corrections or {}).get(field, True))
                else 0
            )
            rows = raw.get(field, [])
            considered += len(rows)
            field_selected: list[dict[str, Any]] = []
            for is_correction, quota in ((False, limit), (True, correction_limit)):
                pool = [
                    row for row in rows
                    if (str(canonical[row["id"]].get("kind") or "positive") == "correction") == is_correction
                ]
                field_selected.extend(pool[:quota])
            if field_selected:
                selected[field] = field_selected

        rendered: dict[str, list[dict[str, Any]]] = {}
        for field, rows in selected.items():
            for row in rows:
                exemplar = canonical.get(row["id"])
                if exemplar is None:
                    continue
                example = prompt_example(exemplar, similarity=None)
                if row.get("match_compared"):
                    example["match"] = {"tier": row["match_tier"], "fields": row["match_compared"]}
                rendered.setdefault(field, []).append(example)
        packet, packet_chars = _bounded_packet(
            rendered,
            ordered_fields,
            char_budget=packet_char_budget,
        )
        used = sum(len(items) for items in packet.values())
        return {
            "ok": False,
            "examples": packet,
            "telemetry": {
                "fallback_reason": reason,
                "fallback_mode": "lexical",
                "ranking": "lexical_overlap",
                "candidates_considered": min(len(canonical), MAX_FALLBACK_CANDIDATES),
                "examples_considered": considered,
                "examples_used": used,
                "packet_chars": packet_chars,
                "fields_served": sorted(packet),
                "total_ms": _elapsed_ms(started_total),
            },
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
        cross_encoder_enabled: bool | None = None,
        cross_encoder_top_k: int | None = None,
        cross_encoder_model: str | None = None,
        cross_encoder_timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Sync canonical exemplars, retrieve per field, and return a bounded packet."""

        started_total = time.monotonic()
        canonical = {
            str(item.get("metadata_exemplar_id") or ""): item
            for item in exemplars
            if str(item.get("metadata_exemplar_id") or "")
        }
        ordered_fields = list(dict.fromkeys(str(field) for field in fields if str(field)))
        if self._disabled_reason:
            return self._lexical_fallback_result(
                started_total=started_total,
                canonical=canonical,
                query_text=str(query_text or ""),
                ordered_fields=ordered_fields,
                language=language,
                field_limits=field_limits,
                field_include_corrections=field_include_corrections,
                field_correction_limits=field_correction_limits,
                field_match_fields=field_match_fields,
                current_values=current_values,
                packet_char_budget=packet_char_budget,
                exclude_record_id=exclude_record_id,
                reason=self._disabled_reason,
            )
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
                _retrieval_query_text(str(query_text), language),
                provider=provider,
                model=model,
            )
            distance_metric = None
            metric_resolver = getattr(self.store, "_distance_metric", None)
            if callable(metric_resolver):
                distance_metric = metric_resolver(collection)
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
                    include=["documents", "metadatas", "distances", "embeddings"],
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
                    semantic_similarity = _distance_similarity(
                        row.get("distance"),
                        distance_metric,
                    )
                    if semantic_similarity < floor:
                        continue
                    tier, compared = match_tier(exemplar, current_values or {}, match_fields)
                    if tier == "differs":
                        continue  # declared analogy conditions contradict this precedent
                    lexical_similarity = _lexical_overlap(
                        query_text,
                        str(row.get("document") or (row.get("metadata") or {}).get("context_text") or ""),
                        language,
                    )
                    candidates.append({
                        **row,
                        "match_tier": tier,
                        "match_compared": compared,
                        "semantic_score": semantic_similarity,
                        "lexical_score": lexical_similarity,
                        "distance_metric": distance_metric,
                        "hybrid_score": (semantic_similarity * 0.8) + (lexical_similarity * 0.2),
                    })
                return field, candidates, len(candidates)

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
                        field, field_candidates, field_considered = future.result()
                        considered += field_considered
                        if field_candidates:
                            raw[field] = field_candidates
            search_ms = _elapsed_ms(search_started)

            rerank_started = time.monotonic()
            raw, rerank_telemetry = _rerank_candidates(
                raw,
                canonical=canonical,
                query_text=str(query_text),
                enabled=(
                    settings.metadata_cross_encoder_enabled
                    if cross_encoder_enabled is None
                    else bool(cross_encoder_enabled)
                ),
                top_k=min(
                    32,
                    max(
                        1,
                        int(
                            settings.metadata_cross_encoder_top_k
                            if cross_encoder_top_k is None
                            else cross_encoder_top_k
                        ),
                    ),
                ),
                model_name=str(
                    cross_encoder_model or settings.rag_cross_encoder_model
                ),
                timeout_seconds=float(
                    settings.metadata_cross_encoder_timeout_seconds
                    if cross_encoder_timeout_seconds is None
                    else cross_encoder_timeout_seconds
                ),
            )
            rerank_telemetry["selection_ms"] = _elapsed_ms(rerank_started)

            # Positives and corrections retain separate quotas, and MMR remains the
            # final diversity step after optional reranking.
            selected_raw: dict[str, list[dict[str, Any]]] = {}
            for field in ordered_fields:
                limit = max(0, int((field_limits or {}).get(field, DEFAULT_FIELD_LIMIT)))
                correction_limit = (
                    max(0, int((field_correction_limits or {}).get(field, DEFAULT_CORRECTION_LIMIT)))
                    if bool((field_include_corrections or {}).get(field, True))
                    else 0
                )
                selected: list[dict[str, Any]] = []
                rows = raw.get(field, [])
                for is_correction, quota in ((False, limit), (True, correction_limit)):
                    pool = [
                        row for row in rows
                        if (str(canonical[row["id"]].get("kind") or "positive") == "correction") == is_correction
                    ]
                    for tier in MATCH_TIERS:
                        remaining = quota - sum(
                            1 for row in selected
                            if (str(canonical[row["id"]].get("kind") or "positive") == "correction") == is_correction
                        )
                        if remaining > 0:
                            selected.extend(_mmr([row for row in pool if row["match_tier"] == tier], remaining))
                if selected:
                    selected_raw[field] = selected

            select_started = time.monotonic()
            rendered: dict[str, list[dict[str, Any]]] = {}
            for field, rows in selected_raw.items():
                for row in rows:
                    exemplar = canonical.get(row["id"])
                    if exemplar is None:
                        continue
                    similarity = row.get("semantic_score")
                    if similarity is None:
                        similarity = _distance_similarity(
                            row.get("distance"),
                            row.get("distance_metric"),
                        )
                    example = prompt_example(exemplar, similarity=float(similarity))
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
                    "embedding_provider": provider,
                    "embedding_model": model,
                    "search_ms": search_ms,
                    "rerank_ms": rerank_telemetry.get("selection_ms", 0),
                    "reranking": rerank_telemetry,
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
            return self._lexical_fallback_result(
                started_total=started_total,
                canonical=canonical,
                query_text=str(query_text or ""),
                ordered_fields=ordered_fields,
                language=language,
                field_limits=field_limits,
                field_include_corrections=field_include_corrections,
                field_correction_limits=field_correction_limits,
                field_match_fields=field_match_fields,
                current_values=current_values,
                packet_char_budget=packet_char_budget,
                exclude_record_id=exclude_record_id,
                reason=self._disabled_reason,
            )
