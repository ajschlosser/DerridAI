# Copyright 2026 Aaron John Schlosser, PhD.
"""Pure public JSONL schema validation and internal-field filtering."""

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
