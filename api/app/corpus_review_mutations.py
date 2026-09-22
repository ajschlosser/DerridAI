# Copyright 2026 Aaron John Schlosser, PhD.
"""Small, side-effect-free policies shared by corpus review mutations."""

from __future__ import annotations

from typing import Any


METADATA_FAMILIES = ("discourse", "quotation", "indexing")


def requeue_record_metadata(record: dict[str, Any], reason: str) -> bool:
    """Mark changed text for a second pass only after enrichment has started.

    A Record that is still queued will be processed once from its new text by
    the original pass. A Record whose metadata pass is running or settled needs
    an explicit requeue marker so stale worker state cannot become authoritative.
    """
    stage_status = record.get("metadata_stage_status") if isinstance(record.get("metadata_stage_status"), dict) else {}
    has_prior_adjudication = bool(
        record.get("metadata_enrichment_finished")
        or str(record.get("metadata_enrichment_state") or "") in {"running", "complete", "failed"}
        or any(str(value) in {"running", "complete", "failed", "needs_review"} for value in stage_status.values())
    )
    record["metadata_needs_attention"] = True
    record["metadata_attention_reasons"] = list(dict.fromkeys(
        [*(record.get("metadata_attention_reasons") or []), reason]
    ))[-50:]
    if not has_prior_adjudication:
        return False
    record["metadata_enrichment_state"] = "stale"
    record["metadata_complete"] = False
    record["metadata_enrichment_finished"] = False
    record["metadata_stage_status"] = {family: "queued" for family in METADATA_FAMILIES}
    record["metadata_execution_ledger"] = {}
    record["metadata_requeue_requested"] = True
    return True
