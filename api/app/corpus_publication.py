# Copyright 2026 Aaron John Schlosser, PhD.
"""Pure public JSONL schema validation, internal-field filtering, and publication readiness."""

from __future__ import annotations

from typing import Any

from .corpus_metadata import DISCOURSE_ROLES, REGION_TYPES


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
) -> str | None:
    """The first reason `publish()` would refuse, or None if the build is publishable.

    `build` MUST already reflect a fresh `_refresh_workflow_fields()` call (readiness/
    metadata totals are read from it), but `validation` is passed separately because the
    caller captures it *before* that refresh -- preserved exactly from the original
    inline `publish()` method, not changed here.
    """
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
