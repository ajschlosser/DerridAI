# Copyright 2026 Aaron John Schlosser, PhD.
"""Pure enrichment/editorial helpers: semantic atoms, family states, human touch, snapshot merge.

Deterministic record-level and build-level bookkeeping for the metadata-enrichment
pipeline, independent of repository state or an active LLM session. Moved verbatim
out of PdfCorpusBuildManager (extracted during the 0.70 decomposition).
"""

from __future__ import annotations

import json
import re
from typing import Any

from .corpus_metadata import ALLOWED_METADATA_FIELDS, MANIFEST_INHERITED_FIELDS
from .corpus_record_quality import iso_now


def _semantic_atoms(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reconstruct stable semantic atoms from noisy PDF layout blocks.

    PyMuPDF blocks are provenance units, not reliable discourse units. Many
    PDFs emit one block per visual line. We conservatively join adjacent tiny
    body blocks on the same physical page while preserving the last original
    block ID as the transition anchor and retaining every source block ID.
    """
    atoms: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal pending
        if not pending:
            return
        last = pending[-1]
        text_parts = [str(item.get("text") or "").strip() for item in pending if str(item.get("text") or "").strip()]
        atom = dict(last)
        atom["text"] = " ".join(text_parts)
        atom["source_block_ids"] = [str(item.get("block_id") or "") for item in pending]
        atom["atom_first_block_id"] = str(pending[0].get("block_id") or "")
        atom["atom_last_block_id"] = str(last.get("block_id") or "")
        # Keep the last real source block ID so a boundary remains directly
        # applicable to deterministic record construction.
        atom["block_id"] = str(last.get("block_id") or "")
        atoms.append(atom)
        pending = []

    for block in blocks:
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        block_type = str(block.get("type") or "body")
        if block_type not in {"body", "paragraph", "text"}:
            flush()
            atom = dict(block)
            atom["source_block_ids"] = [str(block.get("block_id") or "")]
            atom["atom_first_block_id"] = atom["atom_last_block_id"] = str(block.get("block_id") or "")
            atoms.append(atom)
            continue
        if not pending:
            pending = [block]
            continue
        prev = pending[-1]
        same_page = int(prev.get("page") or 0) == int(block.get("page") or 0)
        pending_chars = sum(len(str(item.get("text") or "")) for item in pending)
        prev_text = str(prev.get("text") or "").rstrip()
        # Join line-like fragments, but stop at likely paragraph endings,
        # headings, quotations, list starts, or a healthy paragraph size.
        likely_continuation = (
            same_page
            and pending_chars < 1400
            and (len(prev_text) < 180 or not re.search(r'[.!?][”"\']?$', prev_text))
            and not re.match(r'^\s*(?:[-•*]|\d+[.)])\s+', text)
            and not (len(text) < 90 and text.isupper())
        )
        if likely_continuation:
            pending.append(block)
        else:
            flush()
            pending = [block]
    flush()
    return atoms


def _metadata_family_states(rows: list[dict[str, Any]]) -> list[str]:
    metadata_families = ("discourse", "quotation", "indexing")
    states: list[str] = []
    for row in rows:
        row_status = row.get("metadata_stage_status") if isinstance(row.get("metadata_stage_status"), dict) else {}
        for family in metadata_families:
            fallback = "complete" if row.get("metadata_complete") else "queued"
            states.append(str(row_status.get(family) or fallback))
    return states


def _mark_human_touch(record: dict[str, Any], fields: list[str] | set[str] | tuple[str, ...]) -> None:
    touched = [str(value) for value in (record.get("human_touched_fields") or []) if str(value)]
    for field in fields:
        field_name = str(field)
        if field_name and field_name not in touched:
            touched.append(field_name)
    record["human_touched_fields"] = touched
    record["human_touched_at"] = iso_now()
    record["human_touched_revision"] = int(record.get("record_revision") or 1) + 1
    activity = dict(record.get("activity") or {})
    activity["human_review_count"] = int(activity.get("human_review_count") or 0) + 1
    activity["last_human_reviewed_at"] = record["human_touched_at"]
    record["activity"] = activity


def _editorial_tokens(value: str) -> set[str]:
    stop = {"the", "and", "for", "that", "this", "with", "from", "into", "dans", "les", "des", "une", "pour", "que", "qui", "sur", "est", "pas", "aux"}
    return {
        token for token in re.findall(r"[\wÀ-ÖØ-öø-ÿ]{3,}", str(value or "").casefold(), flags=re.UNICODE)
        if token not in stop
    }


def _merge_enrichment_snapshot(live: dict[str, Any], worker: dict[str, Any], allowed_fields: set[str] | None = None) -> dict[str, Any]:
    """Merge automatic enrichment into current human state without overwriting it."""
    merged = json.loads(json.dumps(live))
    live_status = live.get("metadata_field_status") if isinstance(live.get("metadata_field_status"), dict) else {}
    worker_status = worker.get("metadata_field_status") if isinstance(worker.get("metadata_field_status"), dict) else {}
    touched_markers = set(str(v) for v in (live.get("human_touched_fields") or []))
    text_was_touched = "__text__" in touched_markers
    record_frozen_by_review = "__review__" in touched_markers
    automatic_merge_blocked = (text_was_touched or record_frozen_by_review) and not live.get("metadata_requeue_requested")
    for field in (allowed_fields if allowed_fields is not None else ALLOWED_METADATA_FIELDS):
        if field in MANIFEST_INHERITED_FIELDS:
            continue
        info = live_status.get(field) if isinstance(live_status.get(field), dict) else {}
        if str(info.get("status") or "") in {"human_confirmed", "human_override"}:
            continue
        if not automatic_merge_blocked and field in worker:
            merged[field] = worker[field]
        if not automatic_merge_blocked and field in worker_status:
            merged.setdefault("metadata_field_status", {})[field] = worker_status[field]
    if not automatic_merge_blocked:
        worker_evidence = worker.get("metadata_evidence") if isinstance(worker.get("metadata_evidence"), dict) else {}
        live_evidence = merged.setdefault("metadata_evidence", {})
        for field, info in worker_evidence.items():
            status = live_status.get(field) if isinstance(live_status.get(field), dict) else {}
            if str(status.get("status") or "") not in {"human_confirmed", "human_override"}:
                live_evidence[field] = info
    for key in (
        "metadata_stage_status", "metadata_execution_ledger", "metadata_incomplete_fields",
        "metadata_review_fields", "metadata_needs_attention", "metadata_attention_reasons",
        "metadata_complete", "metadata_enrichment_state", "metadata_enrichment_finished",
        "semantic_classification_confidence", "attribution_confidence", "editorial_memory_used",
        "text_touchup_proposal",
    ):
        if key in worker:
            merged[key] = worker[key]
    if automatic_merge_blocked:
        status = merged.setdefault("metadata_stage_status", {})
        ledger = merged.setdefault("metadata_execution_ledger", {})
        reason = "Human edited reviewed text before automatic enrichment settled." if text_was_touched else "Human completed record review before automatic enrichment settled."
        if not live.get("metadata_requeue_requested"):
            for family in ("discourse", "quotation", "indexing"):
                status[family] = "skipped"
                ledger[family] = {"state": "skipped", "finished_at": iso_now(), "error": reason}
        else:
            merged["metadata_enrichment_state"] = "queued"
            merged["metadata_complete"] = False
            merged["metadata_enrichment_finished"] = False
    return merged


def _initial_enrichment_operation(build_id: str, records: list[dict[str, Any]], *, started_at: str | None = None) -> dict[str, Any]:
    """Describe the book-scale first pass so the review workspace can start another immediately."""
    total = len(records)
    return {
        "operation_id": f"metadata-enrichment-initial-{str(build_id)[:12]}",
        "kind": "metadata_enrichment",
        "state": "completed",
        "started_at": started_at,
        "finished_at": iso_now(),
        "records_total": total,
        "records_processed": total,
        "passes_requested": 1,
        "passes_completed": 1,
        "current_pass": 1,
        "converged": False,
        "pass_results": [{"pass": 1, "records_processed": total}],
    }


def _enrichment_pass_indices(records: list[dict[str, Any]], scope: str, record_ids: list[str] | None = None) -> list[int]:
    """Records a pass should visit. Evaluated per pass: reviewers keep working between passes."""
    indices = []
    selected = {str(value) for value in (record_ids or []) if str(value)}
    for index, record in enumerate(records):
        if selected and str(record.get("record_id") or "") not in selected:
            continue
        disposition = str(record.get("review_disposition") or ("accepted" if record.get("accepted") else "rejected" if record.get("rejected") else "pending"))
        if disposition == "rejected" or (scope == "accepted" and disposition != "accepted") or (scope == "pending" and disposition != "pending"):
            continue
        indices.append(index)
    return indices


def _prepend_metadata_priority(build: dict[str, Any], record_id: str) -> None:
    """Put a changed record ahead of ordinary enrichment work."""
    if not record_id:
        return
    priority = [
        str(value)
        for value in build.get("metadata_priority_record_ids") or []
        if str(value) != record_id
    ]
    build["metadata_priority_record_ids"] = [record_id, *priority][-100:]

