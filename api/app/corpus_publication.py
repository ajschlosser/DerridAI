# Copyright 2026 Aaron John Schlosser, PhD.
"""Pure public JSONL schema validation, internal-field filtering, and publication readiness."""

from __future__ import annotations

import copy
import hashlib
import re
from typing import Any

from .corpus_metadata import DISCOURSE_ROLES, REGION_TYPES
from .field_assertions import accept_unreviewed_suggestions, migrate_record_assertions


def warning_key(text: str) -> str:
    """A stable identity for a build warning, so an acknowledgement stays attached to the warning it names."""
    return hashlib.blake2b(str(text).encode("utf-8"), digest_size=8).hexdigest()


_RECORD_SCOPED = re.compile(r"^\s*([\w.\-]+):\s")


def provenance_warnings(
    build: dict[str, Any], record_ids: set[str]
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """The build's warnings as provenance: (build-wide warnings, warnings per record ID), with acknowledgements.

    A warning is part of how a corpus was made, so it travels with the corpus. One that names a record
    ("cosmopolitanism-00006: LLM text touch-up failed") belongs to that record; the rest belong to the build.
    """
    acknowledgements = build.get("warning_acknowledgements") or {}
    build_wide: list[dict[str, Any]] = []
    per_record: dict[str, list[dict[str, Any]]] = {}
    for text in [str(item) for item in build.get("warnings") or [] if str(item).strip()]:
        key = warning_key(text)
        entry: dict[str, Any] = {"warning_id": key, "text": text}
        acknowledged = acknowledgements.get(key)
        if isinstance(acknowledged, dict):
            entry["acknowledged_by"] = acknowledged.get("acknowledged_by")
            entry["acknowledged_at"] = acknowledged.get("acknowledged_at")
        match = _RECORD_SCOPED.match(text)
        if match and match.group(1) in record_ids:
            per_record.setdefault(match.group(1), []).append(entry)
        else:
            build_wide.append(entry)
    return build_wide, per_record


def validate_publication_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not str(record.get("record_id") or "").strip():
        errors.append("record_id is required")
    if (
        not isinstance(record.get("text"), str)
        or not str(record.get("text") or "").strip()
    ):
        errors.append("text is required")
    region = record.get("region_type")
    role = record.get("discourse_role")
    primary = record.get("primary_text")
    if region not in (None, "") and str(region) not in REGION_TYPES:
        errors.append(f"region_type is not a supported enum value: {region}")
    if role not in (None, "") and str(role) not in DISCOURSE_ROLES:
        errors.append(f"discourse_role is not a supported enum value: {role}")
    if primary is not None and not isinstance(primary, bool):
        errors.append("primary_text must be boolean when present")
    return errors


def serialize_public_record(record: dict[str, Any]) -> dict[str, Any]:
    public_record = dict(record)
    migrate_record_assertions(public_record)
    if not public_record.get("source_document_id") and public_record.get("source_asset_id"):
        public_record["source_document_id"] = public_record["source_asset_id"]
    source_document_id = public_record.get("source_document_id")
    if source_document_id and isinstance(public_record.get("source_spans"), list):
        public_record["source_spans"] = [
            {
                **span,
                "source_document_id": span.get("source_document_id") or source_document_id,
                "source_unit_id": span.get("source_unit_id") or span.get("block_id"),
            }
            for span in public_record["source_spans"]
            if isinstance(span, dict)
        ]
    internal_fields = {
        "accepted",
        "rejected",
        "review_disposition",
        "build_id",
        "publication_id",
        "app_version",
        "schema_version",
        "profile_id",
        "profile_version",
        "provider_profile_id",
        "provider",
        "model",
        "document_prompt_version",
        "segmentation_prompt_version",
        "metadata_prompt_version",
        "record_sizing_policy",
        "topology_quality",
        "source_asset_id",
        "source_unit_ids",
        "source_block_ids",
        "source_extracted_text",
        "pdf_pages",
        "topology_index",
        "topology_count",
        "boundary_review",
        "boundary_suspicion",
        "metadata_field_status",
        "metadata_evidence",
        "metadata_guidance_matches",
        "metadata_decisions",
        "metadata_stage_status",
        "metadata_execution_ledger",
        "metadata_incomplete_fields",
        "metadata_review_fields",
        "metadata_attention_reasons",
        "metadata_needs_attention",
        "metadata_complete",
        "metadata_enrichment_state",
        "metadata_enrichment_history",
        "metadata_disputes",
        "record_revision",
        "review_state",
        "can_accept",
        "text_review_status",
        "text_revision_history",
        "source_quality_issues",
        "resolved_source_quality_issues",
        "text_noise",
        "inline_citation",
        "full_citation",
        "text_length",
        "corpus_build_details",
    }
    return {
        k: v
        for k, v in public_record.items()
        if k not in internal_fields and not k.startswith("_")
    }


def build_text_touchup_prompt(current_text: str, instructions: str) -> str:
    return f"""You are performing a conservative scholarly text touch-up on OCR/PDF extracted text.

RULES:
- Preserve wording, meaning, quotations, terminology, paragraph order, and authorial style.
- Do NOT paraphrase, summarize, modernize, translate, or add content.
- Correct only obvious OCR artifacts, broken words, spacing, punctuation, accidental line wrapping, duplicated running headers/footers/page numbers, and clear textual errata caused by extraction.
- Preserve poetry, verse, block quotations, lists, footnotes, and deliberate typographic/orthographic oddities unless the artifact is unambiguous.
- When uncertain, leave the source text unchanged and mention the uncertainty in warnings.
- Return the COMPLETE touched-up text.
- In the JSON text field, return ONLY the corrected passage text. Do not add Markdown fences, triple-hyphen separators, SOURCE_TEXT labels, quotation wrappers, or commentary around the passage.

Optional reviewer instruction: {instructions or 'None'}

SOURCE_TEXT:
<SOURCE_TEXT>
{current_text}
</SOURCE_TEXT>
"""


# Segmentation must conserve text even when review is skipped; page mapping and metadata
# validation issues are review-resolvable and are carried as unreviewed instead.
TEXT_CONSERVATION_ERROR_KEYS = ("missing_block_ids", "duplicate_block_ids", "text_fidelity_errors", "source_order_errors")
UNREVIEWED_PUBLISHABLE_STATUSES = frozenset({"ready", "awaiting_review"})
# Public per-record marker for publications that bypassed human review.
REVIEWER_ACCEPTED = "reviewer_accepted"
UNREVIEWED = "unreviewed_suggestion"


def mark_unreviewed_publication(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, int]:
    """Accept every outstanding suggestion in a publication snapshot, without changing stored review state.

    Reviewer decisions made before the bypass are preserved: rejected records are already
    excluded, and human-confirmed or overridden fields are never replaced. Every other
    suggested value is accepted as-is (see `accept_unreviewed_suggestions`), and each record
    is labelled `reviewer_accepted` or `unreviewed_suggestion`.
    Returns the snapshot, the number of unreviewed records, and the number of accepted fields.
    """
    marked: list[dict[str, Any]] = []
    unreviewed = 0
    accepted_fields = 0
    for record in records:
        snapshot = copy.deepcopy(record)
        fields = accept_unreviewed_suggestions(snapshot)
        accepted_fields += fields
        reviewed = bool(record.get("accepted")) and not record.get("needs_review") and not fields
        unreviewed += 0 if reviewed else 1
        snapshot["needs_review"] = False
        snapshot["publication_review_status"] = REVIEWER_ACCEPTED if reviewed else UNREVIEWED
        marked.append(snapshot)
    return marked, unreviewed, accepted_fields


def publishable_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "pending")) != "rejected"
        and not record.get("rejected")
    ]


def publication_blocker(
    build: dict[str, Any],
    publishable: list[dict[str, Any]],
    validation: dict[str, Any],
    *,
    require_acceptance: bool,
    accept_unreviewed: bool = False,
) -> str | None:
    """The first reason `publish()` would refuse, or None if the build is publishable.

    `build` MUST already reflect a fresh `_refresh_workflow_fields()` call (readiness/
    metadata totals are read from it), but `validation` is passed separately because the
    caller captures it *before* that refresh -- preserved exactly from the original
    inline `publish()` method, not changed here.

    `accept_unreviewed` skips only the human-review gates (document metadata, metadata
    completion, pending review, acceptance). Text-conservation validation and an empty
    publication still block: an unreviewed corpus may be unverified, never lossy.
    """
    if accept_unreviewed:
        if str(build.get("status") or "") not in UNREVIEWED_PUBLISHABLE_STATUSES:
            return "Publication is unavailable until the build has finished processing."
        if not validation or any(validation.get(key) for key in TEXT_CONSERVATION_ERROR_KEYS):
            return "Publication is blocked until source coverage and text-fidelity validation pass."
        if not publishable:
            return "Publication is unavailable because every record is rejected. Restore at least one record or discard this build."
        return None
    publication_readiness = build.get("publication_readiness")
    readiness: dict[str, Any] = publication_readiness if isinstance(publication_readiness, dict) else {}
    readiness_blockers_raw = readiness.get("blockers")
    readiness_blockers: list[Any] = readiness_blockers_raw if isinstance(readiness_blockers_raw, list) else []
    missing_document = [item for item in readiness_blockers if isinstance(item, dict) and item.get("code") == "required_document_metadata"]
    if missing_document:
        fields = ", ".join(str(value) for value in (missing_document[0].get("fields") or []))
        return f"Publication is blocked: required document metadata is missing ({fields})."
    metadata_total = int(build.get("metadata_total") or 0)
    metadata_completed = int(build.get("metadata_completed") or 0)
    if metadata_total and metadata_completed < metadata_total:
        summary = build.get("metadata_issue_summary") or {}
        by_field = summary.get("by_field") if isinstance(summary, dict) else {}
        detail = ", ".join(f"{field}: {count}" for field, count in sorted((by_field or {}).items()))
        suffix = f" Unresolved fields — {detail}." if detail else ""
        return f"Publication is blocked: metadata is complete for {metadata_completed} of {metadata_total} record(s).{suffix} Resolve the metadata issue queue before publishing."
    if not validation.get("valid"):
        return "Publication is blocked until source coverage and text-fidelity validation pass."
    if not publishable:
        return "Publication is unavailable because every record is rejected. Restore at least one record or discard this build."
    unresolved = [record for record in publishable if record.get("needs_review")]
    if unresolved:
        return f"Publication is blocked: {len(unresolved)} publishable record(s) still need review."
    if require_acceptance:
        unaccepted = [record for record in publishable if not record.get("accepted")]
        if unaccepted:
            return f"Publication is blocked: {len(unaccepted)} publishable record(s) have not been accepted."
    return None
