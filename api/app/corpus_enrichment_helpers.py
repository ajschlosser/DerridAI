# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Pure enrichment/editorial helpers: semantic atoms, family states, human touch, snapshot merge.

Deterministic record-level and build-level bookkeeping for the metadata-enrichment
pipeline, independent of repository state or an active LLM session. Moved verbatim
out of PdfCorpusBuildManager (extracted during the 0.70 decomposition).
"""

from __future__ import annotations

import json
import re
import threading
from collections import deque
from dataclasses import dataclass
from typing import Any, Literal

from .corpus_metadata import MANIFEST_INHERITED_FIELDS
from .corpus_record_quality import iso_now
from .field_assertions import (
    current_assertion_by_name,
    current_assertions,
    migrate_record_assertions,
    project_record_assertions,
    store_assertion,
)


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
        same_layout = (
            str(prev.get("document_thread") or "") == str(block.get("document_thread") or "")
            and str(prev.get("layout_region_id") or "") == str(block.get("layout_region_id") or "")
            and str(prev.get("layout_flow") or "") == str(block.get("layout_flow") or "")
        )
        pending_chars = sum(len(str(item.get("text") or "")) for item in pending)
        prev_text = str(prev.get("text") or "").rstrip()
        # Join line-like fragments, but stop at likely paragraph endings,
        # headings, quotations, list starts, a thread change, or a healthy paragraph size.
        likely_continuation = (
            same_page
            and same_layout
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
    """Merge automatic enrichment without overwriting human-owned assertions."""
    migrate_record_assertions(live)
    migrate_record_assertions(worker)
    merged = json.loads(json.dumps(live))
    touched_markers = set(str(v) for v in (live.get("human_touched_fields") or []))
    text_was_touched = "__text__" in touched_markers
    record_frozen_by_review = "__review__" in touched_markers
    automatic_merge_blocked = (text_was_touched or record_frozen_by_review) and not live.get("metadata_requeue_requested")
    merge_fields = (
        set(allowed_fields)
        if allowed_fields is not None
        else {
            str(assertion.field_name)
            for source in (live, worker)
            for assertion in current_assertions(source)
            if assertion.field_name
        }
    )
    for field in merge_fields:
        if field in MANIFEST_INHERITED_FIELDS:
            continue
        live_assertion = current_assertion_by_name(live, field)
        if live_assertion is not None and live_assertion.authority_status in {"human_confirmed", "human_override"}:
            continue
        if automatic_merge_blocked:
            continue
        worker_assertion = current_assertion_by_name(worker, field)
        if worker_assertion is not None:
            store_assertion(merged, worker_assertion)
        elif field in worker:
            merged[field] = worker[field]
    project_record_assertions(merged)
    for key in (
        "metadata_stage_status", "metadata_execution_ledger", "metadata_incomplete_fields",
        "metadata_review_fields", "metadata_needs_attention", "metadata_attention_reasons",
        "metadata_complete", "metadata_enrichment_state", "metadata_enrichment_finished",
        "semantic_classification_confidence", "attribution_confidence", "editorial_memory_used",
        "metadata_precedents_cache", "text_touchup_proposal",
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


_RECORD_SOURCE_KEYS = (
    "record_id", "record_revision", "text", "source_document_id", "source_asset_id",
    "source_spans", "source_block_ids", "source_unit_ids", "source_extracted_text",
)


def _record_source_matches(left: dict[str, Any], right: dict[str, Any]) -> bool:
    missing = object()
    return all(left.get(key, missing) == right.get(key, missing) for key in _RECORD_SOURCE_KEYS)


def _merge_preparation_snapshot(
    base: dict[str, Any], live: dict[str, Any], worker: dict[str, Any],
    allowed_fields: set[str],
) -> dict[str, Any]:
    """Apply preparation deltas only to unchanged documentary and field state."""
    missing = object()
    if not _record_source_matches(worker, base):
        raise ValueError("Preparation cannot change authoritative text, revision, or source bindings.")
    if not _record_source_matches(live, base):
        return json.loads(json.dumps(live))
    frozen = {"__text__", "__review__"} & set(live.get("human_touched_fields") or [])
    if frozen - set(base.get("human_touched_fields") or []):
        return json.loads(json.dumps(live))
    merged = json.loads(json.dumps(live))
    base = json.loads(json.dumps(base))
    live = json.loads(json.dumps(live))
    worker = json.loads(json.dumps(worker))
    migrate_record_assertions(base)
    migrate_record_assertions(live)
    migrate_record_assertions(worker)
    protected = {
        *_RECORD_SOURCE_KEYS, *allowed_fields, "queue_state_version",
        "field_assertions", "current_field_assertions",
        "metadata_field_status", "metadata_evidence",
        "human_touched_at", "human_touched_fields", "metadata_decisions",
        "review_disposition", "accepted", "rejected", "reviewed_at", "reviewed_by",
    }
    for key in set(base) | set(worker):
        if key in protected or worker.get(key, missing) == base.get(key, missing) or live.get(key, missing) != base.get(key, missing):
            continue
        if key in worker:
            merged[key] = json.loads(json.dumps(worker[key]))
        else:
            merged.pop(key, None)
    for field in allowed_fields:
        if frozen:
            continue
        baseline = [item.model_dump(mode="json") for item in current_assertions(base) if item.field_name == field]
        current = [item.model_dump(mode="json") for item in current_assertions(live) if item.field_name == field]
        proposals = [item for item in current_assertions(worker) if item.field_name == field]
        if current != baseline or any(item["authority_status"] in {"human_confirmed", "human_override"} for item in current):
            continue
        proposed_ids = {item.field_id for item in proposals}
        for item in baseline:
            if item["field_id"] not in proposed_ids:
                merged["current_field_assertions"].pop(item["field_id"], None)
        for assertion in proposals:
            if assertion.model_dump(mode="json") not in baseline:
                store_assertion(merged, assertion)
    project_record_assertions(merged)
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


def _remove_metadata_priority(build: dict[str, Any], record_id: str) -> None:
    """Remove one Record from the foreground-priority set after its queued visit settles."""
    build["metadata_priority_record_ids"] = [
        str(value)
        for value in build.get("metadata_priority_record_ids") or []
        if str(value) != record_id
    ]


_REQUEUE_COUNTERS = {
    "queued": "metadata_requeue_tasks_queued",
    "running": "metadata_requeue_tasks_running",
    "completed": "metadata_requeue_tasks_completed",
    "failed": "metadata_requeue_tasks_failed",
}
_AGGREGATE_REQUEUE_COUNTERS = {
    "queued": "metadata_tasks_queued",
    "running": "metadata_tasks_running",
    "completed": "metadata_tasks_completed",
    "failed": "metadata_tasks_failed",
}


def _queue_metadata_requeue_task(
    build: dict[str, Any],
    record_id: str,
    task_id: str,
) -> None:
    """Add one reviewer-requested Record visit to the live task counters.

    Initial enrichment counts metadata-family work. A reviewer requeue is a single
    additional Record-level task, regardless of how many internal families it
    executes, so the visible denominator advances by exactly one.
    """
    build["metadata_requeue_tasks_total"] = int(build.get("metadata_requeue_tasks_total") or 0) + 1
    build["metadata_requeue_tasks_queued"] = int(build.get("metadata_requeue_tasks_queued") or 0) + 1
    build["metadata_tasks_total"] = int(build.get("metadata_tasks_total") or 0) + 1
    build["metadata_tasks_queued"] = int(build.get("metadata_tasks_queued") or 0) + 1
    history = [
        item
        for item in build.get("metadata_requeue_tasks") or []
        if isinstance(item, dict) and str(item.get("task_id") or "") != task_id
    ]
    history.append(
        {
            "task_id": task_id,
            "record_id": record_id,
            "state": "queued",
            "requested_at": iso_now(),
            "started_at": None,
            "finished_at": None,
        }
    )
    build["metadata_requeue_tasks"] = history[-100:]


def _transition_metadata_requeue_task(
    build: dict[str, Any],
    task_id: str,
    state: Literal["running", "completed", "failed"],
) -> bool:
    """Move one reviewer requeue between durable and aggregate counter buckets."""
    tasks = [
        dict(item)
        for item in build.get("metadata_requeue_tasks") or []
        if isinstance(item, dict)
    ]
    task = next((item for item in tasks if str(item.get("task_id") or "") == task_id), None)
    if task is None:
        return False
    prior = str(task.get("state") or "")
    if prior == state:
        return False
    prior_counter = _REQUEUE_COUNTERS.get(prior)
    prior_aggregate = _AGGREGATE_REQUEUE_COUNTERS.get(prior)
    next_counter = _REQUEUE_COUNTERS[state]
    next_aggregate = _AGGREGATE_REQUEUE_COUNTERS[state]
    if prior_counter:
        build[prior_counter] = max(0, int(build.get(prior_counter) or 0) - 1)
    if prior_aggregate:
        build[prior_aggregate] = max(0, int(build.get(prior_aggregate) or 0) - 1)
    build[next_counter] = int(build.get(next_counter) or 0) + 1
    build[next_aggregate] = int(build.get(next_aggregate) or 0) + 1
    task["state"] = state
    if state == "running":
        task["started_at"] = iso_now()
    else:
        task["finished_at"] = iso_now()
    build["metadata_requeue_tasks"] = tasks[-100:]
    return True


def _metadata_task_counts_with_requeues(
    build: dict[str, Any],
    *,
    total: int,
    completed: int,
    failed: int,
    skipped: int,
    running: int,
    queued: int,
) -> dict[str, int]:
    """Combine base family-task counters with reviewer-requested Record tasks."""
    return {
        "metadata_tasks_total": total + int(build.get("metadata_requeue_tasks_total") or 0),
        "metadata_tasks_completed": completed
        + int(build.get("metadata_requeue_tasks_completed") or 0),
        "metadata_tasks_failed": failed + int(build.get("metadata_requeue_tasks_failed") or 0),
        "metadata_tasks_skipped": skipped,
        "metadata_tasks_running": running + int(build.get("metadata_requeue_tasks_running") or 0),
        "metadata_tasks_queued": queued + int(build.get("metadata_requeue_tasks_queued") or 0),
    }


@dataclass(frozen=True)
class MetadataWorkItem:
    """One bounded Record visit, optionally created by an explicit reviewer requeue."""

    index: int
    record_id: str
    requeue_task_id: str = ""
    priority_requested: bool = False

    @property
    def is_requeue(self) -> bool:
        return bool(self.requeue_task_id)


class MetadataWorkQueue:
    """A bounded scheduler source that accepts reviewer priority work while running.

    The bounded completion iterator repeatedly asks this object for the next item
    when a worker slot opens. Reviewer requests therefore enter the next available
    slot instead of waiting for the original fixed list to drain.
    """

    def __init__(
        self,
        records: list[dict[str, Any]],
        indices: list[int],
        *,
        priority_record_ids: list[str] | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._index_by_record = {
            str(record.get("record_id") or ""): index
            for index, record in enumerate(records)
            if str(record.get("record_id") or "")
        }
        priority = [str(value) for value in (priority_record_ids or []) if str(value)]
        priority_rank = {record_id: rank for rank, record_id in enumerate(priority)}
        ordered = sorted(
            indices,
            key=lambda index: (
                priority_rank.get(str(records[index].get("record_id") or ""), len(priority_rank)),
                index,
            ),
        )
        self._ordinary = deque(
            MetadataWorkItem(
                index=index,
                record_id=str(records[index].get("record_id") or ""),
                priority_requested=str(records[index].get("record_id") or "") in priority_rank,
            )
            for index in ordered
        )
        self._priority: deque[MetadataWorkItem] = deque()
        self._in_flight: set[str] = set()
        self._logical_total = len(indices)

    @property
    def logical_total(self) -> int:
        with self._lock:
            return self._logical_total

    def inject(self, record_id: str, task_id: str) -> Literal["missing", "prioritized", "requeued"]:
        """Move unstarted work to the front, or add one new visit for settled/running work."""
        record_id = str(record_id or "")
        with self._lock:
            index = self._index_by_record.get(record_id)
            if index is None:
                return "missing"
            ordinary = list(self._ordinary)
            for position, item in enumerate(ordinary):
                if item.record_id != record_id:
                    continue
                ordinary.pop(position)
                self._ordinary = deque(ordinary)
                self._priority.appendleft(
                    MetadataWorkItem(
                        index=item.index,
                        record_id=item.record_id,
                        priority_requested=True,
                    )
                )
                return "prioritized"
            self._priority.appendleft(
                MetadataWorkItem(
                    index=index,
                    record_id=record_id,
                    requeue_task_id=task_id,
                    priority_requested=True,
                )
            )
            self._logical_total += 1
            return "requeued"

    def __iter__(self) -> "MetadataWorkQueue":
        return self

    def _pop_available(self, values: deque[MetadataWorkItem]) -> MetadataWorkItem | None:
        for _ in range(len(values)):
            item = values.popleft()
            if item.record_id not in self._in_flight:
                self._in_flight.add(item.record_id)
                return item
            values.append(item)
        return None

    def __next__(self) -> MetadataWorkItem:
        with self._lock:
            item = self._pop_available(self._priority) or self._pop_available(self._ordinary)
            if item is None:
                # This iterator is intentionally resumable: the bounded scheduler
                # may ask again after a reviewer injects work while futures run.
                raise StopIteration
            return item

    def complete(self, item: MetadataWorkItem) -> None:
        with self._lock:
            self._in_flight.discard(item.record_id)
