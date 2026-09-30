# Copyright 2026 Aaron John Schlosser, PhD.
"""Pre-fill record metadata from reviewed precedents, matched on the *source span*.

A metadata exemplar stores the evidence a reviewer bound to a value. So the query here is each source
span (unit) of a record, never the record's whole text: if a span reads like evidence a reviewer has
already accepted for a value, that value is a good first guess for this record, and the span is its evidence.

Rules (advisory, never authoritative):

* A value is pre-filled only when at least ``MIN_AGREE`` distinct earlier records agree on it at high
  similarity and no rival value is nearly as close. The matching span becomes its evidence. Authority stays
  ``unreviewed``; the evidence is *not* marked human-reviewed.
* Anything less certain is kept as a ``memory_hints`` suggestion (value, similarity, support, exemplar ids)
  for the reviewer and the prompt.
* Fields a human already owns, or that already hold a value, are never overwritten; confirmed absence is only
  ever a hint.
* Failure to reach the embedding provider or the store is reported, never hidden and never fatal.

Exemplar retrieval depth, distance-to-similarity conversion, and which hints surface are set by the
assigned ``metadata_prefill`` pipeline. The rules above are domain policy and are not pipeline settings.
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from .field_assertions import create_memory_assertion, current_assertion_by_name
from .pipelines.metadata_prefill import (
    PREFILL_FEATURE,
    PrefillPlan,
    build_prefill_trace,
    resolve_prefill_plan,
)
from .semantic_identity import canonical_value_key
from .source_embeddings import SourceEmbeddingProjection

logger = logging.getLogger(__name__)

# Domain policy: the evidentiary bar for writing a value into a record.
MIN_AGREE = 2
OBVIOUS_SIMILARITY = 0.88
CONFLICT_MARGIN = 0.05
# Resource bounds enforced by the server.
MAX_SPANS = 3000
MIN_SPAN_CHARS = 20
BATCH = 48


def _key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _allowed(schema: Any, field: str, value: Any) -> bool:
    """Would the schema accept ``value`` for ``field``? Closed vocabularies are enforced."""
    from .corpus_metadata import DISCOURSE_ROLES, REGION_TYPES

    if value in (None, "", []):
        return False
    if field == "region_type":
        return value in REGION_TYPES
    if field == "discourse_role":
        return value in DISCOURSE_ROLES
    if field == "primary_text":
        return isinstance(value, bool)
    definition = next((f for f in getattr(schema, "fields", []) if f.name == field), None)
    if definition is None:
        return False
    if definition.type == "choice":
        allowed = {v.value for v in definition.values}
        return value in allowed if not isinstance(value, list) else all(v in allowed for v in value)
    if definition.type == "list":
        return isinstance(value, list)
    if definition.type == "boolean":
        return isinstance(value, bool)
    if definition.type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, str)


def _profile(schema: Any, field: str) -> Any:
    try:
        return schema.retrieval_profile_for(field)
    except KeyError:
        return None


def _group_key(schema: Any, field: str, value: Any, language: str, registry: Any = None) -> str:
    """The vote bucket for a precedent value: its semantic identity, else its exact value.

    Keys are recomputed here under *this* build's schema policy (and reviewed aliases),
    so precedents from other builds vote together exactly when this build would call
    their values the same value.
    """
    try:
        profile = schema.equivalence_profile_for(field)
    except (AttributeError, KeyError):
        return _key(value)
    key = canonical_value_key(value, profile=profile, language=language, registry=registry)
    return f"identity:{key}" if key else _key(value)


def _display_value(schema: Any, field: str, surfaces: dict[str, dict[str, Any]]) -> Any:
    """The surface a winning bucket offers: a controlled value's own spelling, else the
    best-supported reviewed surface, then the most recently reviewed, then a stable order.
    Every supporting surface stays listed on the hint."""
    definition = next((f for f in getattr(schema, "fields", []) if f.name == field), None)
    allowed = {v.value for v in getattr(definition, "values", [])} if definition is not None else set()
    # Stable sorts, least significant criterion first.
    ranked = sorted(surfaces.values(), key=lambda item: _key(item["value"]))
    ranked.sort(key=lambda item: item["latest"], reverse=True)
    ranked.sort(key=lambda item: item["count"], reverse=True)
    ranked.sort(key=lambda item: not (isinstance(item["value"], str) and item["value"] in allowed))
    return ranked[0]["value"]


def _decide(
    groups: dict[str, dict[str, Any]], min_similarity: float, plan: PrefillPlan
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """(the value to pre-fill or None, hint rows best-first) from value groups.

    Hint selection follows the pipeline; the pre-fill decision is domain policy.
    """
    ranked = sorted(
        groups.values(),
        key=lambda g: (g["support"], sum(g["sims"]) / len(g["sims"]), g["best"]),
        reverse=True,
    )
    hints = [
        {
            "value": g["value"], "similarity": round(g["best"], 3), "support": g["support"],
            "exemplar_ids": g["exemplar_ids"][:5], "span_block_id": g["span"], "absence": g["absence"],
            **({"surface_forms": [item["value"] for item in g["surfaces"].values()]} if len(g.get("surfaces") or {}) > 1 else {}),
        }
        for g in ranked if g["best"] >= max(plan.hint_min_similarity, min_similarity)
    ][: plan.hint_limit]
    if not ranked:
        return None, hints
    top = ranked[0]
    mean = sum(top["sims"]) / len(top["sims"])
    rivals = [g for g in ranked[1:] if g["best"] >= top["best"] - CONFLICT_MARGIN]
    obvious = (
        not top["absence"] and top["support"] >= MIN_AGREE and mean >= max(OBVIOUS_SIMILARITY, min_similarity)
        and not rivals
    )
    return (top if obvious else None), hints


def prefill_records(
    records: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    schema: Any,
    index: Any,
    *,
    build_id: str,
    time_budget: float = 90.0,
    registry: Any = None,
) -> dict[str, Any]:
    """Pre-fill ``records`` in place. Returns a summary; never raises.

    Votes are grouped by semantic identity (``push the boundaries`` and ``pushing the
    boundaries`` are one bucket when the field matches lemmas), so restatements agree
    instead of splitting the vote. ``registry`` supplies this build's reviewed aliases.
    """
    started = time.monotonic()
    summary: dict[str, Any] = {"status": "ok", "spans": 0, "prefilled": 0, "hinted": 0, "truncated": False, "error": ""}
    plan: PrefillPlan | None = None
    resolved_hash = ""
    observations: dict[str, dict[str, Any]] = {}
    trace_started = datetime.now(UTC)
    try:
        text_by_block = {
            str(b.get("block_id") or b.get("source_unit_id")): str(b.get("text") or "").strip()
            for b in blocks
        }
        fields = [name for name in schema.field_names() if (p := _profile(schema, name)) is not None and p.enabled]
        if not fields or not records:
            summary["status"] = "skipped"
            return summary
        # Unique span texts across the build, in first-seen order.
        wanted: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
        block_documents: dict[str, str] = {}
        for i, record in enumerate(records):
            document_id = str(
                record.get("source_document_id")
                or record.get("source_asset_id")
                or build_id
            )
            for block_id in record.get("source_unit_ids") or record.get("source_block_ids") or []:
                normalized_block_id = str(block_id)
                text = text_by_block.get(normalized_block_id, "")
                if len(text) >= MIN_SPAN_CHARS:
                    block_documents.setdefault(normalized_block_id, document_id)
                    wanted[text].append((i, normalized_block_id, document_id))
        texts = list(wanted)
        if len(texts) > MAX_SPANS:
            texts, summary["truncated"] = texts[:MAX_SPANS], True
        summary["spans"] = len(texts)
        if not texts:
            summary["status"] = "skipped"
            return summary
        collection = index._ensure()
        if not int(collection.count()):
            summary["status"] = "empty"
            return summary
        plan, resolved_hash = resolve_prefill_plan()
        trace_started = datetime.now(UTC)
        provider, model = index.store._embedding_spec(collection)
        retrieve_started = time.monotonic()
        observations[plan.retrieve_stage_id] = {"status": "running", "input_count": len(texts)}
        source_projection = SourceEmbeddingProjection(index.store)
        source_blocks_by_document: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for block in blocks:
            block_id = str(block.get("block_id") or block.get("source_unit_id") or "")
            document_id = block_documents.get(block_id)
            text = str(block.get("text") or "").strip()
            if document_id and block_id and len(text) >= MIN_SPAN_CHARS:
                source_blocks_by_document[document_id].append({
                    **block,
                    "block_id": block_id,
                    "source_unit_id": block_id,
                    "text": text,
                })
        vectors_by_document: dict[str, dict[str, list[float]]] = {}
        for document_id, source_blocks in source_blocks_by_document.items():
            source_projection.sync(
                document_id,
                source_blocks,
                provider=provider,
                model=model,
                prune=False,
            )
            vectors_by_document[document_id] = source_projection.embeddings_for(
                document_id,
                [str(block.get("block_id") or "") for block in source_blocks],
                provider=provider,
                model=model,
            )
        query_vectors: dict[str, list[float]] = {}
        for text in texts:
            references = wanted[text]
            for _, block_id, document_id in references:
                vector = vectors_by_document.get(document_id, {}).get(block_id)
                if vector is not None:
                    query_vectors[text] = vector
                    break
        if len(query_vectors) != len(texts):
            raise RuntimeError("Source embedding projection did not return every requested source span.")
        where = {"$and": [
            {"field_name": {"$in": fields}}, {"kind": {"$in": ["positive", "absence"]}},
            {"scope_id": {"$ne": build_id}},
        ]}
        # per record -> field -> value key -> group
        found: dict[int, dict[str, dict[str, dict[str, Any]]]] = defaultdict(lambda: defaultdict(dict))
        candidate_rows = 0
        similarities: list[float] = []
        for start in range(0, len(texts), BATCH):
            if time.monotonic() - started > time_budget:
                summary["truncated"] = True
                break
            batch = texts[start:start + BATCH]
            vectors = [query_vectors[text] for text in batch]
            payload = collection.query(
                query_embeddings=vectors, n_results=plan.fetch_k, where=where, include=["metadatas", "distances"],
            )
            # Chroma may return numpy arrays; evaluating them with `or []`
            # raises "truth value of an array is ambiguous".
            payload_ids = payload.get("ids")
            payload_metas = payload.get("metadatas")
            payload_distances = payload.get("distances")
            for text, ids, metas, distances in zip(
                batch,
                payload_ids if payload_ids is not None else [],
                payload_metas if payload_metas is not None else [],
                payload_distances if payload_distances is not None else [],
            ):
                for exemplar_id, meta, distance in zip(ids, metas, distances):
                    if not isinstance(meta, dict):
                        continue
                    candidate_rows += 1
                    similarity = plan.similarity(distance)
                    similarities.append(similarity)
                    field = str(meta.get("field_name") or "")
                    absence = str(meta.get("kind") or "") == "absence"
                    try:
                        value = None if absence else json.loads(str(meta.get("field_value_json") or "null"))
                    except ValueError:
                        continue
                    if field not in fields or (not absence and not _allowed(schema, field, value)):
                        continue
                    source = (str(meta.get("scope_id") or ""), str(meta.get("record_id") or ""))
                    bucket = "__absent__" if absence else _group_key(schema, field, value, str(meta.get("language") or ""), registry)
                    for record_index, block_id, _ in wanted[text]:
                        group = found[record_index][field].setdefault(
                            bucket,
                            {"value": value, "absence": absence, "sims": [], "sources": set(), "best": 0.0,
                             "span": block_id, "exemplar_ids": [], "surfaces": {}},
                        )
                        if source in group["sources"]:
                            continue  # one vote per earlier record
                        if not absence:
                            surface = group["surfaces"].setdefault(_key(value), {"value": value, "count": 0, "latest": ""})
                            surface["count"] += 1
                            surface["latest"] = max(surface["latest"], str(meta.get("reviewed_at") or ""))
                        group["sources"].add(source)
                        group["sims"].append(similarity)
                        group["exemplar_ids"].append(str(exemplar_id))
                        if similarity > group["best"]:
                            group["best"], group["span"] = similarity, block_id
        observations[plan.retrieve_stage_id] = {
            "elapsed_seconds": time.monotonic() - retrieve_started,
            "input_count": len(texts),
            "output_count": candidate_rows,
            "parameters": {"fetch_k": plan.fetch_k, "batch": BATCH, "filter_fields": ["field_name", "kind", "scope_id"]},
            "provider": provider,
            "model": model,
            "collection": str(getattr(collection, "name", "") or "") or None,
            "warnings": ["Stopped at the pre-fill time budget or span cap."] if summary["truncated"] else [],
        }
        observations[plan.normalize_stage_id] = {
            "input_count": candidate_rows,
            "output_count": candidate_rows,
            "parameters": {"method": plan.normalization},
            "warnings": ["Normalization runs inside the retrieval loop; its time is included in retrieval."],
            "score_summary": (
                {"score_type": "similarity", "count": len(similarities), "min": round(min(similarities), 4),
                 "max": round(max(similarities), 4)}
                if similarities else {}
            ),
        }
        hints_started = time.monotonic()
        group_count = hint_count = 0
        for record_index, by_field in found.items():
            record = records[record_index]
            for field, groups in by_field.items():
                for group in groups.values():
                    group["support"] = len(group["sources"])
                    if group["surfaces"]:
                        group["value"] = _display_value(schema, field, group["surfaces"])
                profile = _profile(schema, field)
                choice, hints = _decide(groups, float(getattr(profile, "min_similarity", 0.0) or 0.0), plan)
                group_count += len(groups)
                hint_count += len(hints)
                if hints:
                    record.setdefault("memory_hints", {})[field] = hints
                    summary["hinted"] += 1
                if choice is None or not _can_fill(record, field, schema):
                    continue
                mean = sum(choice["sims"]) / len(choice["sims"])
                evidence = {
                    "block_ids": [choice["span"]], "confidence": round(min(0.9, mean), 3),
                    "reason": "The source span matches evidence reviewers accepted for this value.",
                    "reviewed_by": "memory", "reviewed_at": None,
                }
                create_memory_assertion(
                    record, field, choice["value"], schema=schema, confidence=round(min(0.9, mean), 3),
                    reason=(
                        f"Suggested by {choice['support']} reviewed precedents whose evidence matches this source span "
                        f"(mean similarity {mean:.2f}); exemplars {', '.join(choice['exemplar_ids'][:3])}."
                    ),
                    evidence=[evidence], model=str(model or "") or None,
                )
                record[field] = choice["value"]
                record.setdefault("metadata_evidence", {})[field] = evidence
                summary["prefilled"] += 1
        observations[plan.hints_stage_id] = {
            "elapsed_seconds": time.monotonic() - hints_started,
            "input_count": group_count,
            "output_count": hint_count,
            "parameters": {"limit": plan.hint_limit, "min_similarity": plan.hint_min_similarity},
        }
    except Exception as exc:  # unreachable store or embedder: report it, never block the build
        logger.warning("Metadata-memory pre-fill unavailable", exc_info=True)
        summary.update(status="unavailable", error=f"{type(exc).__name__}: {exc}"[:300])
        for observation in observations.values():
            if observation.get("status") == "running":
                observation.update(status="failed", fallback_reason=summary["error"])
    if plan is not None:
        summary["pipeline"] = _record_trace(plan, resolved_hash, trace_started, observations, summary)
    return summary


def _record_trace(
    plan: PrefillPlan,
    resolved_hash: str,
    started_at: datetime,
    observations: dict[str, dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Persist one trace for the build and return the identity the build summary keeps."""
    from .pipelines.store import pipeline_store

    trace = build_prefill_trace(
        plan,
        resolved_hash=resolved_hash,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        observations=observations,
        status="failed" if summary["status"] == "unavailable" else "completed",
    )
    identity: dict[str, Any] = {
        "feature": PREFILL_FEATURE,
        "pipeline_id": plan.pipeline.pipeline_id,
        "pipeline_version": plan.pipeline.version,
        "pipeline_hash": resolved_hash,
        "trace_id": trace.run_id,
    }
    try:
        pipeline_store.put_run(trace)
    except Exception:  # noqa: BLE001 - telemetry must never block the build
        identity["trace_warning"] = "Pipeline trace persistence failed."
    return identity


def _can_fill(record: dict[str, Any], field: str, schema: Any) -> bool:
    """Only an empty field, never one a human owns or that already holds a value."""
    current = current_assertion_by_name(record, field)
    if current is not None and (
        current.authority_status in {"human_confirmed", "human_override"}
        or (current.value_status == "present" and current.value not in (None, "", []))
    ):
        return False
    return record.get(field) in (None, "", [])
