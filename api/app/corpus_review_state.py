# Copyright 2026 Aaron John Schlosser, PhD.
"""Pure record review-state derivation: queue membership, blockers, and invariants.

Queue membership, the "review_state" badge, and acceptance eligibility are all
derived from a record's own fields rather than independently persisted, so a saved
metadata decision cannot leave behind a stale review flag. Moved verbatim out of
PdfCorpusBuildManager (see PROGRESS.md); the stateful review-mutation methods
(set_disposition, review_decision, patch_record_text, etc.) stay on the manager.
"""

from __future__ import annotations

from typing import Any

from .corpus_metadata import REVIEW_METADATA_FIELDS
from .corpus_record_quality import iso_now


def _metadata_value_missing(field: str, value: Any) -> bool:
    # Booleans are three-state in review: True, False, None. False is a
    # deliberate human decision and must never be treated as missing.
    if field == "primary_text":
        return value is None
    return value is None or value == "" or value == []


def _sync_record_metadata_state(record: dict[str, Any], profile: dict[str, Any]) -> None:
    statuses = record.get("metadata_field_status") if isinstance(record.get("metadata_field_status"), dict) else {}
    required = list(profile.get("required_metadata_fields") or [])
    reviewable = list(profile.get("review_metadata_fields") or REVIEW_METADATA_FIELDS)
    incomplete: list[str] = []
    review_fields: list[str] = []
    for field in required:
        info = statuses.get(field) if isinstance(statuses.get(field), dict) else {}
        state = str(info.get("status") or "")
        if state == "confirmed_absent":
            continue
        if _metadata_value_missing(field, record.get(field)) or state in {"unresolved", "invalid"}:
            incomplete.append(field)
    for field in reviewable:
        info = statuses.get(field) if isinstance(statuses.get(field), dict) else {}
        if str(info.get("status") or "") in {"unresolved", "invalid"}:
            review_fields.append(field)
    record["metadata_incomplete_fields"] = list(dict.fromkeys(incomplete))
    record["metadata_review_fields"] = list(dict.fromkeys(review_fields))
    record["metadata_complete"] = not record["metadata_incomplete_fields"] and not record["metadata_review_fields"]
    record["metadata_needs_attention"] = not record["metadata_complete"]
    if record["metadata_needs_attention"]:
        record["metadata_attention_reasons"] = ["Record metadata requires a human decision before acceptance."]
    else:
        record["metadata_attention_reasons"] = []


def _settle_enrichment_review_reason(record: dict[str, Any]) -> None:
    if str(record.get("review_reason") or "") != "Metadata enrichment added, replaced, or disputed metadata; review the highlighted changes.":
        return
    unresolved_disputes = any(
        isinstance(item, dict) and not item.get("resolved_at")
        for item in (record.get("metadata_disputes") or [])
    )
    if record.get("metadata_incomplete_fields") or record.get("metadata_review_fields") or unresolved_disputes:
        return
    record["review_reason"] = "Pending human review."
    record["needs_review"] = True


def _review_issue_codes(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if record.get("source_quality_issues"):
        issues.append("source")
    if record.get("metadata_incomplete_fields") or record.get("metadata_review_fields"):
        issues.append("metadata")
    if record.get("needs_review") and str(record.get("review_reason") or "").strip():
        reason = str(record.get("review_reason") or "").casefold().strip()
        # Topology is a distinct exception class. Source/metadata review reasons
        # must not be flattened into topology merely because they are concrete.
        if reason not in {"pending human review.", "pending human review"} and any(token in reason for token in ("boundary", "topology", "merge", "split", "segmentation")):
            issues.append("topology")
    return list(dict.fromkeys(issues))


def _metadata_enrichment_finished(record: dict[str, Any]) -> bool:
    state = str(record.get("metadata_enrichment_state") or "").strip().casefold()
    # Records produced before the progressive-review marker existed are
    # considered finished only when they already carry metadata stage output.
    if not state:
        return bool(record.get("metadata_stage_status") or record.get("metadata_complete"))
    return state in {"complete", "failed", "skipped"}


def _matches_review_queue(record: dict[str, Any], queue: str | None) -> bool:
    if not queue or queue == "all":
        return True
    disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
    if queue in {"accepted", "rejected"}:
        return disposition == queue
    if disposition != "pending":
        return False
    codes = _review_issue_codes(record)
    if queue == "ready":
        return _metadata_enrichment_finished(record) and not codes
    if queue == "issues":
        return bool(codes)
    if queue in {"metadata", "topology", "source"}:
        return queue in codes
    return True


def _queue_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    result = {"all": len(records), "ready": 0, "preparing": 0, "issues": 0, "metadata": 0, "topology": 0, "source": 0, "accepted": 0, "rejected": 0, "pending": 0}
    for record in records:
        disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
        if disposition == "accepted":
            result["accepted"] += 1
            continue
        if disposition == "rejected":
            result["rejected"] += 1
            continue
        result["pending"] += 1
        if not _metadata_enrichment_finished(record):
            result["preparing"] += 1
            continue
        codes = _review_issue_codes(record)
        if not codes:
            result["ready"] += 1
        else:
            result["issues"] += 1
            for code in ("metadata", "topology", "source"):
                if code in codes:
                    result[code] += 1
    return result


def _decorate_review_state(record: dict[str, Any]) -> dict[str, Any]:
    """Attach the one authoritative human-review state consumed by the UI.

    Queue membership is derived rather than independently persisted. This
    prevents a saved metadata decision from leaving behind a stale review
    flag that can resurrect the record in a later refresh.
    """
    disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
    issue_codes = _review_issue_codes(record)
    blocking_fields = list(dict.fromkeys([
        str(value) for value in (record.get("metadata_incomplete_fields") or []) + (record.get("metadata_review_fields") or [])
    ]))
    enrichment_finished = _metadata_enrichment_finished(record)
    if disposition in {"accepted", "rejected"}:
        state = disposition
    elif not enrichment_finished:
        state = "preparing"
    elif "source" in issue_codes:
        state = "source"
    elif "metadata" in issue_codes:
        state = "metadata"
    elif "topology" in issue_codes:
        state = "topology"
    else:
        state = "ready"
    record["review_state"] = state
    record["review_issue_codes"] = issue_codes
    record["acceptance_blocking_fields"] = blocking_fields
    record["metadata_enrichment_finished"] = enrichment_finished
    record["can_accept"] = bool(disposition == "pending" and enrichment_finished and not issue_codes)
    return record


def _enforce_review_invariants(record: dict[str, Any]) -> None:
    """Keep persisted disposition consistent with authoritative blockers.

    Human approval is the last step for a record.  An accepted record may
    therefore never simultaneously carry source, metadata, or topology
    blockers.  If later deterministic validation discovers a blocker, reopen
    the record instead of letting contradictory state leak into queues or
    publication readiness.
    """
    disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
    if disposition != "accepted":
        return
    issues = _review_issue_codes(record)
    if not issues:
        return
    record["review_disposition"] = "pending"
    record["accepted"] = False
    record["rejected"] = False
    record["needs_review"] = True
    labels = ", ".join(issues)
    record["review_reason"] = f"Record reopened because validation found unresolved {labels} review work."
    audit = list(record.get("review_events") or [])
    audit.append({"at": iso_now(), "event": "acceptance_reopened", "issues": issues})
    record["review_events"] = audit[-100:]

