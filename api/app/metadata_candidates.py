# Copyright 2026 Aaron John Schlosser, PhD.
"""Conservative non-LLM metadata candidates promoted through FieldAssertions.

Raw NLP annotations are rebuildable observations, not scholarly authority. This module
contains the narrow policy that decides when an exact current-Record NER span is
semantically sufficient for a built-in indexing field. The policy is keyed by stable
semantic compatibility IDs rather than storage/display field names.

Only direct-mention indexing semantics are eligible here. Discourse roles, quotation
relations, topics, concepts, and other interpretive fields remain model/human work.
"""

from __future__ import annotations

from typing import Any

from .field_assertions import (
    create_nlp_assertion,
    current_assertion_by_name,
    migrate_record_assertions,
    project_record_assertions,
)
from .nlp_annotations import current_field_candidates

DIRECT_NER_INDEXING_SEMANTICS: dict[str, frozenset[str]] = {
    "derridai.indexing.persons": frozenset({"PERSON"}),
    "derridai.indexing.works_referenced": frozenset({"WORK_OF_ART", "LAW"}),
}

# Above these small direct-mention sets, semantic selection becomes useful again:
# a long list of names/titles often contains incidental references that should not
# bypass the conservative indexing model merely because the tagger recognized them.
MAX_DIRECT_NER_VALUES: dict[str, int] = {
    "derridai.indexing.persons": 4,
    "derridai.indexing.works_referenced": 3,
}


def _available_for_candidate(record: dict[str, Any], field_name: str) -> bool:
    """Do not replace any selected present value or human-owned assertion."""
    current = current_assertion_by_name(record, field_name)
    if current is not None:
        if current.authority_status in {"human_confirmed", "human_override"}:
            return False
        if current.value_status == "present" and current.value not in (None, "", []):
            return False
    return record.get(field_name) in (None, "", [])


def apply_indexing_nlp_candidates(record: dict[str, Any], schema: Any) -> dict[str, Any]:
    """Promote exact direct-mention NER spans into unreviewed indexing assertions.

    The raw tagger output remains a derived projection. Promotion is allowed only
    for built-in semantic identities whose meaning is satisfied by direct mention:
    indexed persons and indexed works. Every promoted value keeps the exact current
    text offsets, tagger/model identity, and text digest in its assertion evidence.
    No confidence is invented when the tagger does not expose a calibrated score.
    """
    migrate_record_assertions(record, schema)
    eligible_fields = []
    for field in schema.fields_in("indexing"):
        semantic_id = str(schema.semantic_compatibility_id(field.name) or "")
        if field.type == "list" and semantic_id in DIRECT_NER_INDEXING_SEMANTICS:
            eligible_fields.append(field)
    if not eligible_fields:
        return {"resolved_fields": [], "values": {}}

    structured = current_field_candidates(
        record,
        {field.name for field in eligible_fields},
    )
    nlp_data = record.get("nlp_candidates")
    nlp_data = nlp_data if isinstance(nlp_data, dict) else {}
    model = str(nlp_data.get("model") or "")
    engine = str(nlp_data.get("engine") or "spacy")
    engine_version = str(nlp_data.get("engine_version") or "")
    text_sha256 = str(nlp_data.get("text_sha256") or "")
    current_text = str(record.get("text") or "")
    resolved: list[str] = []
    deferred: dict[str, str] = {}
    values_by_field: dict[str, list[str]] = {}

    for field in eligible_fields:
        if not _available_for_candidate(record, field.name):
            continue
        semantic_id = str(schema.semantic_compatibility_id(field.name) or "")
        allowed_tags = DIRECT_NER_INDEXING_SEMANTICS[semantic_id]
        spans = [
            item
            for item in structured.get(field.name, [])
            if str(item.get("source") or "") == "ner"
            and str(item.get("tag") or "") in allowed_tags
        ]
        values: list[str] = []
        seen: set[str] = set()
        evidence: list[dict[str, Any]] = []
        for item in spans:
            raw_value = str(item.get("text") or "")
            try:
                start = int(item.get("start"))
                end = int(item.get("end"))
            except (TypeError, ValueError):
                continue
            value = raw_value.strip()
            key = value.casefold()
            if (
                not value
                or value != raw_value
                or start < 0
                or end <= start
                or current_text[start:end] != raw_value
                or key in seen
            ):
                continue
            seen.add(key)
            values.append(value)
            evidence.append({
                "kind": "nlp_span",
                "start": start,
                "end": end,
                "text": value,
                "tag": str(item.get("tag") or ""),
                "source": "ner",
                "text_sha256": text_sha256,
                "engine": engine,
                "engine_version": engine_version,
                "model": model,
            })
        if not values:
            continue
        max_values = MAX_DIRECT_NER_VALUES[semantic_id]
        if len(values) > max_values:
            deferred[field.name] = (
                f"{len(values)} direct NER candidates exceed the conservative "
                f"candidate-only limit of {max_values}."
            )
            continue

        method = f"nlp:{engine}:{model or 'unversioned'}"
        create_nlp_assertion(
            record,
            field.name,
            values,
            schema=schema,
            reason=(
                "Direct named-entity mentions in the current Record satisfy this "
                f"indexing field's stable semantic identity ({semantic_id})."
            ),
            evidence=evidence,
            method=method,
            model=model or None,
            legacy_metadata={
                "candidate_only": True,
                "value_source": "nlp",
                "verification_status": "pending_review",
                "auto_populated": True,
                "autofilled": False,
                "reason_code": "direct_ner_indexing_candidate",
                "semantic_compatibility_id": semantic_id,
            },
        )
        resolved.append(field.name)
        values_by_field[field.name] = values

    if resolved:
        project_record_assertions(record)
    return {
        "resolved_fields": sorted(resolved),
        "deferred_fields": deferred,
        "values": values_by_field,
        "engine": engine,
        "engine_version": engine_version,
        "model": model,
        "text_sha256": text_sha256,
    }
