# Copyright 2026 Aaron John Schlosser, PhD.
"""Pure scholarly metadata vocabulary and deterministic ownership constraints.

No repository, model-provider, or job-manager dependency is permitted here.
"""
from __future__ import annotations

import re
from typing import Any

from .field_assertions import (
    create_deterministic_assertion,
    current_assertion_by_name,
    migrate_record_assertions,
    project_record_assertions,
)
from .metadata_values import clean as clean_value
from .metadata_values import is_placeholder

REGION_TYPES = [
    "front_matter", "main_text", "notes", "bibliography", "index",
    "appendix", "back_matter", "paratext", "unknown",
]

DISCOURSE_ROLES = [
    "assertion", "analysis", "quotation", "reported_position", "critique",
    "qualification", "transition", "question", "definition", "example",
    "commentary", "paratext", "bibliographic",
]

PROPOSITION_STATUS_VALUES = [
    "asserted", "affirmed", "rejected", "criticized", "questioned", "qualified",
    "hypothetical", "attributed", "reported", "conceded", "suspended",
]

STANCE_VALUES = ["affirm", "reject", "criticize", "question", "qualify", "suspend", "neutral", "describe"]

STANCE_ALIASES = {
    "affirmed": "affirm",
    "rejected": "reject",
    "criticized": "criticize",
    "questioned": "question",
    "qualified": "qualify",
    "suspended": "suspend",
    "descriptive": "describe",
}

STRONG_STRUCTURAL_METHODS = {
    "human_document_layout",
    "document_layout_rule",
    "confirmed_manifest_page_range",
}

_LLM_TRANSPORT_SUFFIX = re.compile(
    r"\s*,?\s*(?:field[_ -]?evidence|field[_ -]?assessments)"
    r"(?:-[A-Za-z0-9_.:-]+)?\s*:",
    re.IGNORECASE,
)


# A list item that is structured-output residue rather than a value: an evidence reference, a confidence score, an
# assessment key, or a source-block ID. Small models sometimes flatten {value, evidence, confidence, reason} into one
# list ("Balzac", "field_evidence_id-…:p00001-b0001", "confidence_score_0.95", "The text presents…").
_LLM_TRANSPORT_ITEM = re.compile(
    r"^\s*(?:field[_ -]?(?:evidence|assessments?)|evidence[_ -]?(?:ids?|blocks?)|block[_ -]?ids?)(?:\b|_)"
    r"|^\s*confidence(?:[_ -]?score)?\s*[_:=]?\s*(?:0|1)?\.?\d"
    r"|^\s*(?:needs[_ -]?review|reason)\s*[:=]"
    r"|:p\d{3,}-b\d{3,}|^\s*p\d{3,}-b\d{3,}\s*$",
    re.IGNORECASE,
)


def _strip_llm_transport_items(value: list[Any]) -> tuple[list[Any], list[Any] | None]:
    """List items before the first transport marker; everything from it on is residue (its reason included)."""
    kept: list[Any] = []
    for item in value:
        if isinstance(item, str) and _LLM_TRANSPORT_ITEM.search(item):
            return kept, list(value)
        if isinstance(item, str):
            cleaned, raw = _strip_llm_transport_suffix(item)
            if raw is not None:
                if cleaned:
                    kept.append(cleaned)
                return kept, list(value)
        kept.append(item)
    return value, None


def _strip_llm_transport_suffix(value: Any) -> tuple[Any, Any | None]:
    """Keep model transport/audit syntax out of scholarly metadata values.

    Some small models occasionally flatten a neighbouring structured-output
    field into a scalar value, such as a person name followed by a
    field_evidence marker. Preserve the raw response for audit while selecting
    only the value before that explicit structured-output marker.
    """
    if isinstance(value, list):
        return _strip_llm_transport_items(value)
    if not isinstance(value, str):
        return value, None
    text: str = value
    parts = _LLM_TRANSPORT_SUFFIX.split(text, maxsplit=1)
    if len(parts) < 2 or not parts[0].strip():
        return value, None
    clean = parts[0].rstrip(" ,;")
    return (clean or None), value


def _normalize_semantic_value(field: str, value: Any) -> tuple[Any, Any | None]:
    """Canonicalize only closed-vocabulary grammatical aliases.

    The raw model value is returned separately for audit. We deliberately avoid
    semantic synonym expansion: only direct inflectional variants are normalized.
    """
    value, transport_raw = _strip_llm_transport_suffix(value)
    if isinstance(value, str) and is_placeholder(value):
        return None, transport_raw or value  # raw text is kept for audit; it is not a value
    if isinstance(value, list) and any(is_placeholder(item) for item in value):
        return clean_value(value), transport_raw or value
    if field != "stance" or not isinstance(value, str):
        return value, transport_raw
    raw = transport_raw or value
    token = value.strip().casefold()
    if token in STANCE_VALUES:
        return token, None
    normalized = STANCE_ALIASES.get(token)
    return (normalized, raw) if normalized else (value, None)

DISCOURSE_ROLE_DEFINITIONS = {
    "assertion": "The speaker directly advances a proposition as part of the argument.",
    "analysis": "The passage examines, interprets, or explicates a claim, text, concept, or distinction.",
    "quotation": "The record primarily functions as direct quoted material rather than the surrounding author's own proposition.",
    "reported_position": "The passage presents a proposition held or advanced by another position holder without necessarily endorsing it.",
    "critique": "The passage explicitly challenges, rejects, problematizes, or exposes a limitation in a position.",
    "qualification": "The passage limits, modifies, complicates, or adds a condition to another proposition.",
    "transition": "The passage primarily moves between argumentative stages rather than advancing a substantive proposition.",
    "question": "The passage primarily poses a question or problem rather than asserting an answer.",
    "definition": "The passage explicitly defines, specifies, or characterizes a term or concept.",
    "example": "The passage primarily provides an illustration, case, or example for another point.",
    "commentary": "The passage offers explanatory commentary that is not itself the principal argumentative move.",
    "paratext": "Editorial, publishing, prefatory, front/back matter, or other apparatus rather than substantive argument.",
    "bibliographic": "Bibliographic citation, reference-list, or works-cited material.",
}

HYBRID_REQUIRED_FIELDS = ("region_type", "primary_text", "discourse_role")

REVIEW_METADATA_FIELDS = ("region_type", "primary_text", "discourse_role", "speaker", "position_holder", "target", "stance", "proposition_status", "claim_scope")

NON_PRIMARY_REGION_TYPES = {"front_matter", "back_matter", "bibliography", "index", "paratext"}

def apply_metadata_constraints(
    record: dict[str, Any],
    schema: Any | None = None,
) -> list[dict[str, Any]]:
    """Apply deterministic record-metadata relationships.

    Hard semantic invariants are applied consistently in single-record editing,
    bulk editing, and automatic enrichment. Human decisions remain authoritative
    for soft defaults, but impossible apparatus/primary-text combinations are not
    offered as scholarly choices.
    """
    region = str(record.get("region_type") or "")
    migrate_record_assertions(record, schema)
    changes: list[dict[str, Any]] = []

    primary_assertion = current_assertion_by_name(record, "primary_text")
    human_primary = bool(primary_assertion and primary_assertion.authority_status in {"human_confirmed", "human_override"})
    strong_structural_primary = bool(primary_assertion and primary_assertion.method in STRONG_STRUCTURAL_METHODS)
    semantic_disagreement = bool(primary_assertion and "disagreement" in primary_assertion.reason)
    desired_primary: bool | None = None
    primary_reason = ""
    primary_hard = False
    if region in NON_PRIMARY_REGION_TYPES:
        desired_primary = False
        primary_hard = True
        primary_reason = f"{region} cannot be primary text."
    elif region == "main_text" and not human_primary:
        desired_primary = True
        primary_reason = "main_text is deterministically suggested as primary text unless a reviewer overrides it."
    if desired_primary is not None and (primary_hard or not human_primary):
        if record.get("primary_text") is not desired_primary:
            changes.append({"field": "primary_text", "value": desired_primary, "reason": primary_reason})
        record["primary_text"] = desired_primary
        if not semantic_disagreement and not strong_structural_primary:
            create_deterministic_assertion(
                record,
                "primary_text",
                desired_primary,
                schema=schema,
                method="region_type_consistency",
                reason=primary_reason,
            )

    role_assertion = current_assertion_by_name(record, "discourse_role")
    human_role = bool(role_assertion and role_assertion.authority_status in {"human_confirmed", "human_override"})
    desired_role: str | None = None
    role_reason = ""
    if region == "bibliography":
        desired_role = "bibliographic"
        role_reason = "Bibliography regions are deterministically bibliographic discourse."
    elif region in {"front_matter", "back_matter", "paratext"}:
        desired_role = "paratext"
        role_reason = f"{region} is deterministically classified as paratext unless a reviewer explicitly overrides it."
    if desired_role is not None and not human_role:
        if record.get("discourse_role") != desired_role:
            changes.append({"field": "discourse_role", "value": desired_role, "reason": role_reason})
        record["discourse_role"] = desired_role
        create_deterministic_assertion(
            record,
            "discourse_role",
            desired_role,
            schema=schema,
            method="region_type_consistency",
            reason=role_reason,
        )
    project_record_assertions(record)
    return changes

ATTRIBUTION_EVIDENCE_FIELDS = {
    "speaker", "position_holder", "target", "stance", "proposition_status",
    "quoted_speaker", "quoted_author", "quoted_work", "quoted_position_holder",
    "quoted_addressee", "quoted_referent", "quotation_chain",
}

EVIDENCE_REQUIRED_FIELDS = ATTRIBUTION_EVIDENCE_FIELDS | set(HYBRID_REQUIRED_FIELDS)

SOURCE_BOUND_FIELDS = {
    "record_id", "record_revision", "text", "text_length", "page_start", "page_end", "pdf_file",
    "pdf_pages", "source_asset_id", "source_block_ids", "source_spans",
}

ALLOWED_METADATA_FIELDS = {
    "work", "document_title", "short_title", "original_title", "document_author",
    "edition", "year", "publication_year", "publisher", "publication_place", "isbn",
    "language", "document_language", "original_language", "document_is_translation", "translator", "region_type",
    "region_author", "primary_text", "speaker", "position_holder", "target",
    "discourse_role", "proposition_status", "semantic_function", "stance",
    "claim_scope", "is_direct_quote", "quoted_speaker", "quoted_author",
    "quoted_work", "quoted_position_holder", "quoted_addressee", "quoted_referent",
    "quotation_chain", "topics", "concepts", "persons", "works_referenced",
    "attribution_confidence", "semantic_classification_confidence", "extraction_quality",
    "canonical_work_id", "inline_citation", "full_citation", "needs_review",
    "review_reason",
}

METADATA_FAMILY_FIELDS = {
    "discourse": {
        "region_type", "region_author", "primary_text", "speaker", "position_holder",
        "target", "discourse_role", "proposition_status", "semantic_function", "stance",
        "claim_scope", "attribution_confidence", "semantic_classification_confidence",
    },
    "quotation": {
        "is_direct_quote", "quoted_speaker", "quoted_author", "quoted_work",
        "quoted_position_holder", "quoted_addressee", "quoted_referent", "quotation_chain",
    },
    "indexing": {"topics", "concepts", "persons", "works_referenced"},
}

MANIFEST_INHERITED_FIELDS = {
    "work", "document_title", "short_title", "original_title", "canonical_work_id",
    "document_author", "translator", "edition", "year", "publication_year", "publisher",
    "publication_place", "isbn", "document_language", "original_language",
    "document_is_translation",
}

# Runtime schema policy is intentionally smaller than the legacy compatibility
# whitelists below. Ordinary scholarly fields come from the build's pinned
# MetadataSchema; only document-level or computed record metadata stays fixed.
FIXED_RECORD_METADATA_FIELDS = MANIFEST_INHERITED_FIELDS | {
    "language",
    "attribution_confidence",
    "semantic_classification_confidence",
    "extraction_quality",
    "inline_citation",
    "full_citation",
    "needs_review",
    "review_reason",
}

FIXED_HUMAN_EDITABLE_METADATA_FIELDS = MANIFEST_INHERITED_FIELDS | {
    "language",
    "needs_review",
    "review_reason",
}

HUMAN_EDITABLE_METADATA_FIELDS = {
    # Record-level overrides of inherited bibliographic metadata are explicit
    # human decisions. They never mutate the document manifest and must survive
    # later automatic enrichment.
    "work", "document_title", "short_title", "original_title", "canonical_work_id",
    "document_author", "translator", "edition", "year", "publication_year",
    "publisher", "publication_place", "isbn", "document_language",
    "original_language", "document_is_translation",
    "language", "region_type", "region_author", "primary_text", "speaker",
    "position_holder", "target", "discourse_role", "proposition_status",
    "semantic_function", "stance", "claim_scope", "is_direct_quote",
    "quoted_speaker", "quoted_author", "quoted_work", "quoted_position_holder",
    "quoted_addressee", "quoted_referent", "quotation_chain", "topics",
    "concepts", "persons", "works_referenced", "needs_review", "review_reason",
}
