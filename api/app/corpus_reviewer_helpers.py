# Copyright 2026 Aaron John Schlosser, PhD.
"""Pure reviewer-facing helpers: second-opinion blinding, sealed-field scrubbing, schema fields.

Deterministic operations applied when serving a record to a specific reviewer (blind
review), and small schema/build utility functions independent of repository state.
Moved verbatim out of PdfCorpusBuildManager (see PROGRESS.md).
"""

from __future__ import annotations

from typing import Any

from .corpus_metadata import ALLOWED_METADATA_FIELDS
from .metadata_schema import MetadataSchema, default_schema
from .reviewer_context import current_reviewer


def _second_opinion_owed(record: dict[str, Any], field: str) -> dict[str, Any] | None:
    """The pending second-opinion entry for this field if the current reviewer, not the first, is the one asked."""
    me = current_reviewer.get()
    item = (record.get("second_opinion") or {}).get(field)
    if me and isinstance(item, dict) and not item.get("done") and item.get("first_reviewer") and item["first_reviewer"] != me:
        return item
    return None


def _present_for_reviewer(record: dict[str, Any]) -> None:
    """Hide, from a second reviewer, the answer they are about to independently give.

    Applied where records are served, never before saving: it must not reach storage.
    """
    for field in list((record.get("second_opinion") or {}).keys()):
        if _second_opinion_owed(record, field):
            record[field] = [] if isinstance(record.get(field), list) else None
            record.setdefault("metadata_field_status", {})[field] = {
                "status": "unresolved", "method": "human", "blind": True, "reason_code": "second_opinion", "auto_populated": False, "reason": "",
            }
            for entry in record.get("metadata_decisions") or []:
                if isinstance(entry, dict) and entry.get("field") == field:
                    entry["value"] = None  # the decision log holds the first answer too
            _scrub_sealed_field(record, field)
            # Everything else on the record that repeats the first reviewer's answer for this field.
            record["llm_rejections"] = [r for r in record.get("llm_rejections") or [] if not (isinstance(r, dict) and r.get("field") == field)]
            for key in ("recheck_results", "blind_reveals", "recheck_scheduled"):
                if isinstance(record.get(key), dict):
                    record[key].pop(field, None)


def _scrub_sealed_field(record: dict[str, Any], field: str) -> None:
    """Remove every copy of a sealed value, and the confidence and reasoning that would give it away, from the record."""
    evidence = record.get("metadata_evidence")
    if isinstance(evidence, dict) and isinstance(evidence.get(field), dict):
        evidence[field] = {"block_ids": evidence[field].get("block_ids") or []}
    for result in (record.get("metadata_stage_results") or {}).values():
        if isinstance(result, dict):
            for section in ("metadata", "field_assessments", "field_evidence"):
                if isinstance(result.get(section), dict):
                    result[section].pop(field, None)


def _human_touched(record: dict[str, Any]) -> bool:
    return bool(record.get("human_touched_fields"))


def _allowed_for(schema: MetadataSchema) -> set[str]:
    """The fixed fields, minus those the default schema defines, plus this schema's: a schema that leaves a field out cannot have it set."""
    return (ALLOWED_METADATA_FIELDS - {f.name for f in default_schema().fields}) | set(schema.field_names())


def _operation_from_build(build: dict[str, Any]) -> dict[str, Any]:
    raw_status = str(build.get("status") or "queued")
    if raw_status in {"queued", "running"}:
        status = raw_status
    elif raw_status == "cancelled":
        status = "cancelled"
    elif raw_status in {"failed", "interrupted"}:
        status = "failed"
    elif raw_status in {"blocked", "awaiting_manifest_review"}:
        status = "blocked"
    else:
        status = "completed"
    source_total = max(1, int(build.get("source_block_count") or 1))
    progress = max(0.0, min(1.0, float(build.get("progress") or 0.0)))
    unresolved = list(build.get("segmentation_unresolved_regions") or [])
    metadata_total = int(build.get("metadata_tasks_total") or 0)
    metadata_completed = int(build.get("metadata_tasks_completed") or 0)
    metadata_failed = int(build.get("metadata_tasks_failed") or 0)
    metadata_skipped = int(build.get("metadata_tasks_skipped") or 0)
    metadata_running = int(build.get("metadata_tasks_running") or 0)
    metadata_queued = int(build.get("metadata_tasks_queued") or 0)
    if raw_status in {"queued", "running"} and str(build.get("stage") or "") == "enriching" and metadata_total:
        settled = metadata_completed + metadata_failed + metadata_skipped
        metadata_stage_detail = (
            f"Metadata: {settled}/{metadata_total} settled · "
            f"{metadata_running} active · {metadata_queued} queued · "
            f"{metadata_failed + metadata_skipped} review"
        )
    else:
        metadata_stage_detail = None
    if metadata_stage_detail:
        operation_stage_detail = metadata_stage_detail
    elif raw_status in {"queued", "running"} and build.get("retrying_segmentation"):
        operation_stage_detail = f"Retrying {len(unresolved)} unresolved segmentation region(s)"
    elif build.get("segmentation_blocked"):
        operation_stage_detail = f"{len(unresolved)} unresolved segmentation region(s)"
    else:
        operation_stage_detail = str(build.get("stage") or raw_status).replace("_", " ")
    return {
        "id": str(build.get("build_id") or ""),
        "type": "pdf_corpus",
        "kind": "pdf_corpus",
        "label": f"PDF corpus · {build.get('source_filename') or 'source'}",
        "status": status,
        "raw_status": raw_status,
        "stage": build.get("stage"),
        "stage_detail": operation_stage_detail,
        "provider": build.get("provider"),
        "model": build.get("model"),
        "provider_profile_id": (build.get("request") or {}).get("provider_profile_id"),
        "max_concurrent_requests": (build.get("request") or {}).get("max_concurrent_requests", 1),
        "request": build.get("request") or {},
        "source_filename": build.get("source_filename"),
        "build_id": build.get("build_id"),
        "record_count": int(build.get("record_count") or 0),
        "review_count": int(build.get("needs_review_count") or 0),
        "metadata_tasks_total": metadata_total,
        "metadata_tasks_completed": metadata_completed,
        "metadata_tasks_failed": metadata_failed,
        "metadata_tasks_skipped": metadata_skipped,
        "metadata_tasks_running": metadata_running,
        "metadata_tasks_queued": metadata_queued,
        "metadata_started_at": build.get("metadata_started_at"),
        "metadata_last_progress_at": build.get("metadata_last_progress_at"),
        "unresolved_regions": len(unresolved),
        "progress": progress,
        "total": source_total,
        "completed": min(source_total, int(round(source_total * progress))),
        # Localized segmentation uncertainty is review work, not a failed operation.
        "failed": 1 if raw_status == "failed" else 0,
        "review_required": len(unresolved),
        "created_at": build.get("created_at"),
        "started_at": build.get("started_at"),
        "finished_at": build.get("finished_at"),
        "cancel_requested": bool(build.get("cancel_requested")),
        "fatal_error": build.get("error"),
        "href": f"/pdf?mode=builder&build={build.get('build_id')}",
    }


def _metadata_issue_type(status: dict[str, Any] | None, record: dict[str, Any]) -> str:
    info = status or {}
    explicit = str(info.get("reason_code") or "").strip()
    if explicit:
        return explicit
    state = str(info.get("status") or "unresolved")
    reason = str(info.get("reason") or "").casefold()
    stage_status = record.get("metadata_stage_status") if isinstance(record.get("metadata_stage_status"), dict) else {}
    if "source quality" in reason or "extraction" in reason:
        return "source_quality"
    if state == "invalid":
        return "invalid_value"
    if any(value == "needs_review" for value in stage_status.values()) and "model" in reason:
        return "llm_failed"
    if "evidence" in reason or "confidence" in reason:
        return "evidence_failed"
    if "ambiguous" in reason or "disagree" in reason:
        return "ambiguous"
    if not info:
        return "not_run"
    return "unresolved"

