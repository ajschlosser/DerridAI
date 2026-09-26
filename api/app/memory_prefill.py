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
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from typing import Any

from .field_assertions import create_memory_assertion, current_assertion_by_name

logger = logging.getLogger(__name__)

MIN_AGREE = 2
OBVIOUS_SIMILARITY = 0.88
HINT_SIMILARITY = 0.72
CONFLICT_MARGIN = 0.05
FETCH_K = 8
MAX_SPANS = 3000
MIN_SPAN_CHARS = 20
BATCH = 48
MAX_HINTS_PER_FIELD = 3


def _similarity(distance: Any) -> float:
    try:
        return 1.0 / (1.0 + max(0.0, float(distance)))
    except (TypeError, ValueError):
        return 0.0


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


def _decide(groups: dict[str, dict[str, Any]], min_similarity: float) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """(the value to pre-fill or None, hint rows best-first) from value groups."""
    ranked = sorted(
        groups.values(),
        key=lambda g: (g["support"], sum(g["sims"]) / len(g["sims"]), g["best"]),
        reverse=True,
    )
    hints = [
        {
            "value": g["value"], "similarity": round(g["best"], 3), "support": g["support"],
            "exemplar_ids": g["exemplar_ids"][:5], "span_block_id": g["span"], "absence": g["absence"],
        }
        for g in ranked if g["best"] >= max(HINT_SIMILARITY, min_similarity)
    ][:MAX_HINTS_PER_FIELD]
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
) -> dict[str, Any]:
    """Pre-fill ``records`` in place. Returns a summary; never raises."""
    started = time.monotonic()
    summary: dict[str, Any] = {"status": "ok", "spans": 0, "prefilled": 0, "hinted": 0, "truncated": False, "error": ""}
    try:
        text_by_block = {str(b.get("block_id")): str(b.get("text") or "").strip() for b in blocks}
        fields = [name for name in schema.field_names() if (p := _profile(schema, name)) is not None and p.enabled]
        if not fields or not records:
            summary["status"] = "skipped"
            return summary
        # Unique span texts across the build, in first-seen order.
        wanted: dict[str, list[tuple[int, str]]] = defaultdict(list)  # text -> [(record index, block id)]
        for i, record in enumerate(records):
            for block_id in record.get("source_block_ids") or []:
                text = text_by_block.get(str(block_id), "")
                if len(text) >= MIN_SPAN_CHARS:
                    wanted[text].append((i, str(block_id)))
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
        provider, model = index.store._embedding_spec(collection)
        where = {"$and": [
            {"field_name": {"$in": fields}}, {"kind": {"$in": ["positive", "absence"]}},
            {"scope_id": {"$ne": build_id}},
        ]}
        # per record -> field -> value key -> group
        found: dict[int, dict[str, dict[str, dict[str, Any]]]] = defaultdict(lambda: defaultdict(dict))
        for start in range(0, len(texts), BATCH):
            if time.monotonic() - started > time_budget:
                summary["truncated"] = True
                break
            batch = texts[start:start + BATCH]
            vectors = index.store.embeddings.embed(batch, [{}] * len(batch), "embedding", provider=provider, model=model)
            payload = collection.query(
                query_embeddings=vectors, n_results=FETCH_K, where=where, include=["metadatas", "distances"],
            )
            for text, ids, metas, distances in zip(
                batch, payload.get("ids") or [], payload.get("metadatas") or [], payload.get("distances") or [],
            ):
                for exemplar_id, meta, distance in zip(ids, metas, distances):
                    if not isinstance(meta, dict):
                        continue
                    similarity = _similarity(distance)
                    field = str(meta.get("field_name") or "")
                    absence = str(meta.get("kind") or "") == "absence"
                    try:
                        value = None if absence else json.loads(str(meta.get("field_value_json") or "null"))
                    except ValueError:
                        continue
                    if field not in fields or (not absence and not _allowed(schema, field, value)):
                        continue
                    source = (str(meta.get("scope_id") or ""), str(meta.get("record_id") or ""))
                    for record_index, block_id in wanted[text]:
                        group = found[record_index][field].setdefault(
                            "__absent__" if absence else _key(value),
                            {"value": value, "absence": absence, "sims": [], "sources": set(), "best": 0.0,
                             "span": block_id, "exemplar_ids": []},
                        )
                        if source in group["sources"]:
                            continue  # one vote per earlier record
                        group["sources"].add(source)
                        group["sims"].append(similarity)
                        group["exemplar_ids"].append(str(exemplar_id))
                        if similarity > group["best"]:
                            group["best"], group["span"] = similarity, block_id
        for record_index, by_field in found.items():
            record = records[record_index]
            for field, groups in by_field.items():
                for group in groups.values():
                    group["support"] = len(group["sources"])
                profile = _profile(schema, field)
                choice, hints = _decide(groups, float(getattr(profile, "min_similarity", 0.0) or 0.0))
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
    except Exception as exc:  # unreachable store or embedder: report it, never block the build
        logger.warning("Metadata-memory pre-fill unavailable", exc_info=True)
        summary.update(status="unavailable", error=f"{type(exc).__name__}: {exc}"[:300])
    return summary


def _can_fill(record: dict[str, Any], field: str, schema: Any) -> bool:
    """Only an empty field, never one a human owns or that already holds a value."""
    current = current_assertion_by_name(record, field)
    if current is not None and (
        current.authority_status in {"human_confirmed", "human_override"}
        or (current.value_status == "present" and current.value not in (None, "", []))
    ):
        return False
    return record.get(field) in (None, "", [])
