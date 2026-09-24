# Copyright 2026 Aaron John Schlosser, PhD.
"""Evidence-bound exemplars for progressively improving metadata enrichment.

The corpus remains authoritative.  This module only derives compact, revision-aware
training precedents from metadata decisions whose value and evidence have both crossed
a human-review boundary.  Future semantic/vector indexes should store projections of
these objects, never replace them as the source of truth.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

TRUSTED_ASSERTION_STATUSES = frozenset({"human_confirmed", "human_override"})
TRUSTED_MODEL_REVIEW_METHODS = frozenset({"human_review_of_llm_proposal"})
DEFAULT_CONTEXT_BLOCK_RADIUS = 1
PROMPT_EVIDENCE_CHARS = 420
DEFAULT_PROMPT_TOKEN_BUDGET = 1200
PROMPT_CHARS_PER_TOKEN = 4
FIELD_EXAMPLE_LIMITS = {
    "speaker": 2,
    "quoted_speaker": 2,
    "position_holder": 3,
    "stance": 3,
    "discourse_role": 2,
}
DEFAULT_FIELD_EXAMPLE_LIMIT = 2


def _json_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _unique_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _reviewed_evidence(status: dict[str, Any], evidence: dict[str, Any]) -> bool:
    """Whether the field value and its evidence are safe to teach to another model.

    An explicit human evidence edit is strongest.  We also accept evidence attached to
    a model value when record acceptance promoted that exact model proposal through the
    existing human_review_of_llm_proposal path.  A later human value edit does not
    automatically bless the old model evidence, preventing stale evidence from becoming
    a precedent for a corrected value.
    """

    if str(evidence.get("reviewed_by") or "") == "human":
        return True
    return str(status.get("method") or "") in TRUSTED_MODEL_REVIEW_METHODS


def _source_span(span: dict[str, Any]) -> dict[str, Any]:
    """Copy only stable source-location fields needed by the exemplar."""

    allowed = (
        "block_id",
        "page",
        "pdf_page",
        "printed_page_label",
        "bbox",
        "char_start",
        "char_end",
        "start",
        "end",
    )
    return {key: span[key] for key in allowed if key in span}


def _evidence_source_spans(
    record: dict[str, Any],
    evidence_ids: list[str],
    blocks_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    wanted = set(evidence_ids)
    spans = [
        _source_span(span)
        for span in (record.get("source_spans") or [])
        if isinstance(span, dict) and str(span.get("block_id") or "") in wanted
    ]
    if spans:
        return spans

    derived: list[dict[str, Any]] = []
    for block_id in evidence_ids:
        block = blocks_by_id[block_id]
        item: dict[str, Any] = {"block_id": block_id}
        for source_key, target_key in (
            ("page", "page"),
            ("pdf_page", "pdf_page"),
            ("printed_page_label", "printed_page_label"),
            ("bbox", "bbox"),
        ):
            if source_key in block:
                item[target_key] = block[source_key]
        derived.append(item)
    return derived


def _ordered_evidence_and_context_ids(
    record: dict[str, Any],
    evidence_ids: list[str],
    *,
    context_block_radius: int,
) -> tuple[list[str], list[str]] | None:
    source_ids = _unique_strings(record.get("source_block_ids"))
    if not source_ids:
        # Exact evidence must be provably part of the reviewed record. A globally
        # resolvable block is not enough: without record membership we cannot bind
        # the assertion to this RecordRevision. Fall back to lexical memory instead.
        return None

    position = {block_id: index for index, block_id in enumerate(source_ids)}
    if any(block_id not in position for block_id in evidence_ids):
        return None

    ordered = sorted(evidence_ids, key=position.__getitem__)
    first = max(0, position[ordered[0]] - max(0, int(context_block_radius)))
    last = min(
        len(source_ids),
        position[ordered[-1]] + max(0, int(context_block_radius)) + 1,
    )
    return ordered, source_ids[first:last]


def build_metadata_exemplar(
    record: dict[str, Any],
    field: str,
    blocks_by_id: dict[str, dict[str, Any]],
    *,
    schema_id: str = "",
    schema_version: str = "",
    source_document_id: str = "",
    field_id: str = "",
    context_block_radius: int = DEFAULT_CONTEXT_BLOCK_RADIUS,
) -> dict[str, Any] | None:
    """Derive one trusted, evidence-bound positive metadata exemplar.

    Returns None when the assertion is not human-owned, evidence is absent/stale,
    a cited block does not belong to the record, or a cited source block cannot be
    resolved.  Returning no exemplar is safer than manufacturing a training precedent.
    """

    field = str(field or "").strip()
    if not field:
        return None

    statuses = record.get("metadata_field_status")
    if not isinstance(statuses, dict):
        return None
    status = statuses.get(field)
    if not isinstance(status, dict) or str(status.get("status") or "") not in TRUSTED_ASSERTION_STATUSES:
        return None

    value = record.get(field)
    if value in (None, "", []):
        return None

    evidence_map = record.get("metadata_evidence")
    evidence = evidence_map.get(field) if isinstance(evidence_map, dict) else None
    if not isinstance(evidence, dict) or not _reviewed_evidence(status, evidence):
        return None

    evidence_ids = _unique_strings(evidence.get("block_ids"))
    if not evidence_ids:
        return None

    ordered = _ordered_evidence_and_context_ids(
        record,
        evidence_ids,
        context_block_radius=context_block_radius,
    )
    if ordered is None:
        return None
    evidence_ids, context_ids = ordered

    needed_ids = set(evidence_ids)
    if any(
        block_id not in blocks_by_id
        or not str(blocks_by_id[block_id].get("text") or "")
        for block_id in needed_ids
    ):
        return None

    evidence_text = "\n\n".join(str(blocks_by_id[block_id]["text"]) for block_id in evidence_ids)
    context_text = "\n\n".join(
        str(blocks_by_id[block_id].get("text") or "")
        for block_id in context_ids
        if block_id in blocks_by_id and str(blocks_by_id[block_id].get("text") or "")
    )
    if not context_text:
        context_text = evidence_text

    evidence_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
    record_id = str(record.get("record_id") or "")
    record_revision = record.get("record_revision")
    effective_source_document_id = str(
        record.get("source_document_id") or source_document_id or ""
    )
    identity = {
        "record_id": record_id,
        "record_revision": record_revision,
        "field": field,
        "field_id": str(field_id or ""),
        "value": value,
        "evidence_hash": evidence_hash,
        "schema_id": schema_id,
        "schema_version": schema_version,
    }
    exemplar_id = "mex-" + hashlib.sha256(_json_key(identity).encode("utf-8")).hexdigest()[:24]

    source_spans = _evidence_source_spans(record, evidence_ids, blocks_by_id)
    pages = sorted(
        {
            int(page)
            for page in [
                *(span.get("page") for span in source_spans if isinstance(span, dict)),
                *(blocks_by_id[block_id].get("page") for block_id in evidence_ids),
            ]
            if isinstance(page, (int, float)) and not isinstance(page, bool)
        }
    )

    return {
        "metadata_exemplar_id": exemplar_id,
        "kind": "positive",
        "record_id": record_id,
        "record_revision": record_revision,
        "source_document_id": effective_source_document_id,
        "field_name": field,
        "field_id": str(field_id or ""),
        "field_value": value,
        "assertion_status": str(status.get("status") or ""),
        "assertion_method": str(status.get("method") or ""),
        "evidence_ref": {
            "record_id": record_id,
            "record_revision": record_revision,
            "source_document_id": effective_source_document_id,
            "source_spans": source_spans,
            "block_ids": evidence_ids,
            "quote_hash": evidence_hash,
        },
        "evidence_text": evidence_text,
        "context_text": context_text,
        "context_block_ids": context_ids,
        "schema_id": schema_id,
        "schema_version": schema_version,
        "language": record.get("language"),
        "region_type": record.get("region_type"),
        "speaker": record.get("speaker"),
        "position_holder": record.get("position_holder"),
        "stance": record.get("stance"),
        "discourse_role": record.get("discourse_role"),
        "page_start": pages[0] if pages else record.get("page_start"),
        "page_end": pages[-1] if pages else record.get("page_end"),
        "reviewed_at": evidence.get("reviewed_at") or record.get("metadata_reviewed_at"),
    }


def build_correction_exemplars(
    record: dict[str, Any],
    blocks_by_id: dict[str, dict[str, Any]],
    *,
    schema_id: str = "",
    schema_version: str = "",
    source_document_id: str = "",
    field_ids: dict[str, str] | None = None,
    context_block_radius: int = DEFAULT_CONTEXT_BLOCK_RADIUS,
) -> list[dict[str, Any]]:
    """Derive hard-negative exemplars from model values a human corrected.

    Corrections are emitted only when the chosen value itself has trusted evidence.
    The rejected value is retained as a negative label; it is never represented as a
    positive assertion.
    """

    corrections: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for rejection in record.get("llm_rejections") or []:
        if not isinstance(rejection, dict):
            continue
        field = str(rejection.get("field") or "").strip()
        rejected_value = rejection.get("rejected_value")
        chosen_value = rejection.get("chosen_value")
        if not field or rejected_value in (None, "", []) or record.get(field) != chosen_value:
            continue

        base = build_metadata_exemplar(
            record,
            field,
            blocks_by_id,
            schema_id=schema_id,
            schema_version=schema_version,
            source_document_id=source_document_id,
            field_id=str((field_ids or {}).get(field) or ""),
            context_block_radius=context_block_radius,
        )
        if base is None:
            continue

        rejected_key = _json_key(rejected_value)
        dedupe_key = (field, rejected_key)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        correction = dict(base)
        correction["kind"] = "correction"
        correction["rejected_value"] = rejected_value
        correction["source_model"] = rejection.get("model")
        correction["corrected_at"] = rejection.get("at")
        correction["metadata_exemplar_id"] = "mex-" + hashlib.sha256(
            _json_key(
                {
                    "positive_exemplar_id": base["metadata_exemplar_id"],
                    "rejected_value": rejected_value,
                    "model": rejection.get("model"),
                }
            ).encode("utf-8")
        ).hexdigest()[:24]
        corrections.append(correction)
    return corrections


def prompt_example(exemplar: dict[str, Any], *, similarity: float | None = None) -> dict[str, Any]:
    """Render a deliberately compact exemplar for an enrichment prompt."""

    evidence = re.sub(r"\s+", " ", str(exemplar.get("evidence_text") or "")).strip()
    payload: dict[str, Any] = {
        "exemplar_id": str(exemplar.get("metadata_exemplar_id") or ""),
        "record_id": str(exemplar.get("record_id") or ""),
        "record_revision": exemplar.get("record_revision"),
        "value": exemplar.get("field_value"),
        "evidence_bound": True,
        "evidence_block_ids": list((exemplar.get("evidence_ref") or {}).get("block_ids") or []),
        "evidence": evidence[:PROMPT_EVIDENCE_CHARS],
        "excerpt": evidence[:PROMPT_EVIDENCE_CHARS],
    }
    if similarity is not None:
        payload["similarity"] = round(max(0.0, min(1.0, float(similarity))), 4)
    if exemplar.get("kind") == "correction":
        payload["kind"] = "correction"
        payload["rejected_value"] = exemplar.get("rejected_value")
    return payload


def budget_prompt_examples(
    examples: dict[str, list[dict[str, Any]]],
    *,
    token_budget: int = DEFAULT_PROMPT_TOKEN_BUDGET,
) -> dict[str, list[dict[str, Any]]]:
    """Bound the complete exemplar packet, not merely each field's top-k.

    Selection is deterministic and round-robin across fields so one metadata
    family cannot consume the entire prompt budget.  The budget is intentionally
    approximate: JSON character count divided by four is used as a conservative,
    provider-independent token estimate without invoking another tokenizer/model.
    """

    char_budget = max(0, int(token_budget)) * PROMPT_CHARS_PER_TOKEN
    if char_budget <= 0:
        return {}

    queues: dict[str, list[dict[str, Any]]] = {}
    for field in sorted(examples):
        items = examples.get(field)
        if not isinstance(items, list):
            continue
        limit = FIELD_EXAMPLE_LIMITS.get(field, DEFAULT_FIELD_EXAMPLE_LIMIT)
        queues[field] = [dict(item) for item in items[:limit] if isinstance(item, dict)]

    selected: dict[str, list[dict[str, Any]]] = {}
    used_chars = 0
    while any(queues.values()):
        progressed = False
        for field in sorted(queues):
            queue = queues[field]
            if not queue:
                continue
            item = queue.pop(0)
            cost = len(
                json.dumps(
                    {field: item},
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
            )
            if used_chars + cost > char_budget:
                continue
            selected.setdefault(field, []).append(item)
            used_chars += cost
            progressed = True
        if not progressed:
            break
    return selected


def prompt_example_token_estimate(examples: dict[str, list[dict[str, Any]]]) -> int:
    """Provider-independent approximate token count for instrumentation."""

    if not examples:
        return 0
    chars = len(
        json.dumps(
            examples,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    )
    return (chars + PROMPT_CHARS_PER_TOKEN - 1) // PROMPT_CHARS_PER_TOKEN
