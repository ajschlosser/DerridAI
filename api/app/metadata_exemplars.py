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
from collections.abc import Callable
from typing import Any

from .field_assertions import (
    FieldAssertion,
    current_assertion_by_name,
    current_assertions,
    migrate_record_assertions,
)
from .semantic_identity import (
    SEMANTIC_IDENTITY_VERSION,
    canonical_value_key,
    resolve_identity,
)
from .semantic_identity_registry import compare_field_values

DEFAULT_CONTEXT_BLOCK_RADIUS = 1
PROMPT_EVIDENCE_CHARS = 420
DEFAULT_PROMPT_TOKEN_BUDGET = 1200
PROMPT_CHARS_PER_TOKEN = 4
# Per-field limits come from each schema field's retrieval profile (max_items);
# this default applies only when a schema declares none.
DEFAULT_FIELD_EXAMPLE_LIMIT = 2
REVIEWED_AUTHORITY = {"human_confirmed", "human_override"}


def _json_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _unique_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(str(value) for value in values if str(value).strip()))


def reviewed_values(record: dict[str, Any]) -> dict[str, str]:
    """Human-reviewed present values on a record, keyed by field name.

    Values are JSON-encoded so they compare exactly. The snapshot is schema-agnostic:
    it lets a retrieval policy declare which *other* fields a precedent should agree
    on without this module knowing what any field means. Names are stable here
    because exemplars are only ever compared within one build's copied schema.
    """
    out: dict[str, str] = {}
    if not isinstance(record, dict):
        return out
    row = json.loads(json.dumps(record, default=str))
    migrate_record_assertions(row)
    for assertion in current_assertions(row):
        name = str(assertion.field_name or "")
        if name and assertion.value_status == "present" and assertion.authority_status in REVIEWED_AUTHORITY:
            out[name] = _json_key(assertion.value)
    return out


def _reviewed_evidence(assertion: FieldAssertion, evidence: dict[str, Any]) -> bool:
    """Whether an authoritative assertion's evidence is safe as model precedent.

    Canonical authority replaces the old overloaded method/status convention:
    confirming a model-derived value does not rewrite its derivation or method,
    but the human authority event still makes its bound evidence eligible.
    """

    if str(evidence.get("reviewed_by") or "") == "human":
        return True
    return (
        assertion.derivation_method == "model"
        and assertion.authority_status in {"human_confirmed", "human_override"}
    )


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
    why: list[str] | None = None,
    schema: Any = None,
    registry: Any = None,
    assertion_override: Any = None,
    value_override: Any = ...,
) -> dict[str, Any] | None:
    """Derive one trusted, evidence-bound positive metadata exemplar.

    Returns None when the assertion is not human-owned, evidence is absent/stale,
    a cited block does not belong to the record, or a cited source block cannot be
    resolved.  Returning no exemplar is safer than manufacturing a training precedent.
    """

    def skip(code: str) -> dict[str, Any] | None:
        # ``why`` lets a diagnosis say exactly why no precedent was derived.
        if why is not None:
            why.append(code)
        return None

    field = str(field or "").strip()
    if not field:
        return skip("no_field")

    migrate_record_assertions(record)
    assertion = assertion_override or current_assertion_by_name(record, field)
    if assertion is None:
        return skip("no_assertion")
    is_confirmed_absence = assertion.value_status == "confirmed_absent"
    if (
        assertion.authority_status not in {"human_confirmed", "human_override"}
        and not is_confirmed_absence
    ):
        return skip("not_human_confirmed")

    value = record.get(field) if value_override is ... else value_override
    if is_confirmed_absence:
        if value not in (None, "", []):
            return skip("absence_has_value")
    elif value in (None, "", []):
        return skip("no_value")

    evidence = next(
        (
            item
            for item in assertion.evidence
            if isinstance(item, dict) and item.get("block_ids")
        ),
        None,
    )
    if evidence is None:
        evidence_map = record.get("metadata_evidence")
        evidence = evidence_map.get(field) if isinstance(evidence_map, dict) else None
    if not isinstance(evidence, dict):
        return skip("no_evidence")
    if not _reviewed_evidence(assertion, evidence):
        return skip("evidence_not_human_reviewed")

    evidence_ids = _unique_strings(evidence.get("block_ids"))
    if not evidence_ids:
        return skip("no_evidence")

    ordered = _ordered_evidence_and_context_ids(
        record,
        evidence_ids,
        context_block_radius=context_block_radius,
    )
    if ordered is None:
        return skip("evidence_not_in_record")
    evidence_ids, context_ids = ordered

    needed_ids = set(evidence_ids)
    if any(
        block_id not in blocks_by_id
        or not str(blocks_by_id[block_id].get("text") or "")
        for block_id in needed_ids
    ):
        return skip("evidence_block_unresolved")

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
        "kind": "absence" if is_confirmed_absence else "positive",
        "record_id": record_id,
        "record_revision": record_revision,
        "source_document_id": effective_source_document_id,
        "field_name": field,
        "field_id": str(field_id or ""),
        "field_value": value,
        "assertion_status": assertion.authority_status,
        "assertion_method": str(assertion.method or assertion.derivation_method),
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
        "reviewed_values": reviewed_values(record),
        "page_start": pages[0] if pages else record.get("page_start"),
        "page_end": pages[-1] if pages else record.get("page_end"),
        "reviewed_at": evidence.get("reviewed_at") or record.get("metadata_reviewed_at"),
        **_identity_fields(schema, record, field, value, registry=registry),
    }


def _identity_fields(schema: Any, record: dict[str, Any], field: str, value: Any, prefix: str = "", registry: Any = None) -> dict[str, Any]:
    """Derived identity of an exemplar value. ``field_value`` itself is never replaced.

    The key groups equivalent precedents for ranking; it is rebuildable and versioned, and
    None when no safe key exists (for example a lexical phrase with no lemmatizer installed).
    ``semantic_identity_id`` is set only when a reviewed identity names the value.
    """
    if schema is None or value in (None, "", []):
        return {}
    try:
        profile = schema.equivalence_profile_for(field)
    except KeyError:
        return {}
    identity = resolve_identity(value, profile=profile, registry=registry) if registry is not None else None
    key = canonical_value_key(value, profile=profile, language=str(record.get("language") or ""), registry=registry)
    out: dict[str, Any] = {
        f"{prefix}canonical_value_key": key,
        f"{prefix}semantic_identity_id": identity.identity_id if identity is not None else None,
    }
    if not prefix:
        out.update({"equivalence_profile": profile.mode, "equivalence_version": SEMANTIC_IDENTITY_VERSION})
    return out


def build_correction_exemplars(
    record: dict[str, Any],
    blocks_by_id: dict[str, dict[str, Any]],
    *,
    schema_id: str = "",
    schema_version: str = "",
    source_document_id: str = "",
    field_ids: dict[str, str] | None = None,
    context_block_radius: int = DEFAULT_CONTEXT_BLOCK_RADIUS,
    schema: Any = None,
    registry_for: Callable[[dict[str, Any]], Any] | None = None,
) -> list[dict[str, Any]]:
    """Derive hard-negative exemplars from model values a human corrected.

    Corrections are emitted only when the chosen value itself has trusted evidence.
    The rejected value is retained as a negative label; it is never represented as a
    positive assertion. Only a rejected value that is *different* from the accepted one
    is a correction: a restatement (``J.P.`` for ``J. P.``) or an unresolved comparison
    never becomes a hard negative, including in rejection rows recorded before
    equivalence existed. Those audit rows stay on the record untouched.
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
        registry = registry_for(record) if registry_for else None
        relation = rejection.get("equivalence_relation")
        if relation not in {"exact", "equivalent", "different", "unknown"}:
            relation = (
                compare_field_values(
                    schema, field, rejected_value, chosen_value, record=record, registry=registry,
                ).relation
                if schema is not None
                else ("exact" if rejected_value == chosen_value else "different")
            )
        if relation != "different":
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
            schema=schema,
            registry=registry,
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
        correction.update(_identity_fields(schema, record, field, rejected_value, prefix="rejected_", registry=registry))
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
    kind = str(exemplar.get("kind") or "positive")
    if kind != "positive":
        payload["kind"] = kind
    if kind == "correction":
        payload["rejected_value"] = exemplar.get("rejected_value")
    return payload


def budget_prompt_examples(
    examples: dict[str, list[dict[str, Any]]],
    *,
    token_budget: int = DEFAULT_PROMPT_TOKEN_BUDGET,
    field_limits: dict[str, int] | None = None,
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
        limit = max(
            0,
            int(
                (field_limits or {}).get(
                    field,
                    DEFAULT_FIELD_EXAMPLE_LIMIT,
                )
            ),
        )
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
