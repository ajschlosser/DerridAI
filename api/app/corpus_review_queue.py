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

"""Pure Corpus Builder review-queue filtering, extracted from ``PdfCorpusRepository``.

No I/O: every function here operates on an already-loaded list of Records so
REST (``page_records``) and GraphQL (``corpus_build.review_queue``/``rows``) page
and count the exact same in-memory selection instead of re-deriving it twice.
"""
from __future__ import annotations

import copy
import json
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any

from .corpus_review_state import (
    _decorate_review_state,
    _matches_review_queue,
    _queue_counts,
)
from .corpus_reviewer_helpers import _present_for_reviewer
from .field_assertions import _NON_ASSERTION_FIELDS, _operational_key
from .metadata_values import is_placeholder
from .reviewer_context import current_reviewer


@dataclass(frozen=True)
class QueueFilter:
    needs_review: bool | None = None
    disposition: str | None = None
    metadata_incomplete: bool | None = None
    source_problem: bool | None = None
    review_queue: str | None = None
    query: str = ""


@dataclass
class QueueSelection:
    items: list[dict[str, Any]]
    total: int
    queue_counts: dict[str, int]


def empty_page(offset: int, limit: int) -> dict[str, Any]:
    return {
        "items": [],
        "total": 0,
        "offset": offset,
        "limit": limit,
        "queue_counts": _queue_counts([]),
        "metadata_values": {},
    }


def _disposition(record: dict[str, Any]) -> str:
    if record.get("review_disposition"):
        return str(record["review_disposition"])
    if record.get("accepted"):
        return "accepted"
    if record.get("rejected"):
        return "rejected"
    return "pending"


class QueueSelectionCache:
    """Bounded derived selections for immutable repository snapshots only.

    Retain the snapshot to prevent object-id reuse. Never cache presented Records:
    each page still applies the active reviewer's visibility rules to fresh copies.
    Callers with mutable lists must use select_queue without this cache.
    """

    def __init__(self, capacity: int = 4, record_budget: int = 40_000) -> None:
        self._capacity = capacity
        self._record_budget = record_budget
        self._entries: OrderedDict[
            tuple[int, QueueFilter, str],
            tuple[list[dict[str, Any]], list[int], dict[str, int]],
        ] = OrderedDict()
        self._lock = RLock()

    def selection(
        self, records: list[dict[str, Any]], filters: QueueFilter,
    ) -> tuple[list[int], dict[str, int]]:
        key = (id(records), filters, str(current_reviewer.get() or ""))
        with self._lock:
            hit = self._entries.get(key)
            if hit is not None:
                self._entries.move_to_end(key)
                return hit[1], hit[2]
        indices, counts = _select_indices(records, filters)
        if len(records) <= self._record_budget:
            with self._lock:
                self._entries[key] = (records, indices, counts)
                while self._entries and (
                    len(self._entries) > self._capacity
                    or sum(len(entry[0]) for entry in self._entries.values()) > self._record_budget
                ):
                    self._entries.popitem(last=False)
        return indices, counts


def _select_indices(
    records: list[dict[str, Any]], filters: QueueFilter,
) -> tuple[list[int], dict[str, int]]:
    q = filters.query.casefold().strip()
    indices: list[int] = []
    queue_records: list[dict[str, Any]] = []
    for topology_index, record in enumerate(records):
        if filters.needs_review is not None and bool(record.get("needs_review")) is not filters.needs_review:
            continue
        record_disposition = _disposition(record)
        if filters.disposition is not None and record_disposition != filters.disposition:
            continue
        if filters.metadata_incomplete is not None and (not bool(record.get("metadata_complete"))) is not filters.metadata_incomplete:
            continue
        if filters.source_problem is not None and bool(record.get("source_quality_issues")) is not filters.source_problem:
            continue
        if q:
            searchable = copy.deepcopy(record)
            _present_for_reviewer(searchable)
            if q not in json.dumps(searchable, ensure_ascii=False).casefold():
                continue
        queue_records.append(record)
        if filters.review_queue and not _matches_review_queue(record, filters.review_queue):
            continue
        indices.append(topology_index)
    return indices, _queue_counts(queue_records)


def select_queue(
    records: list[dict[str, Any]],
    filters: QueueFilter,
    *,
    offset: int,
    limit: int,
    cache: QueueSelectionCache | None = None,
) -> QueueSelection:
    """Select and present a page without mutating stored Records.

    Only immutable repository snapshots may opt into selection reuse. Counts
    retain the pre-queue-filter scope; topology positions retain corpus order.
    Presentation runs within the caller's reviewer_scope on every request.
    """
    indices, counts = (
        cache.selection(records, filters) if cache is not None else _select_indices(records, filters)
    )
    start = max(0, offset)
    items: list[dict[str, Any]] = []
    for index in indices[start:start + max(0, limit)]:
        presented = copy.deepcopy(records[index])
        presented["topology_index"] = index
        presented["topology_count"] = len(records)
        _decorate_review_state(presented)
        _present_for_reviewer(presented)
        items.append(presented)
    return QueueSelection(items=items, total=len(indices), queue_counts=dict(counts))


# Facets inspect every Record, so they are memoized per (snapshot, reviewer). The snapshot is the
# repository's cached list, which is replaced (never mutated) when any Record changes, so identity
# is a sound key; the list itself is held so its id cannot be reused while the entry lives.
_FACET_MEMO_CAPACITY = 8
_facet_memo: dict[tuple[int, str], tuple[list[dict[str, Any]], dict[str, list[str]]]] = {}


def observed_metadata_values(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    key = (id(records), str(current_reviewer.get() or ""))
    hit = _facet_memo.get(key)
    if hit is not None and hit[0] is records:
        return {field: list(values) for field, values in hit[1].items()}
    result = _compute_observed_metadata_values(records)
    _facet_memo[key] = (records, result)
    while len(_facet_memo) > _FACET_MEMO_CAPACITY:
        _facet_memo.pop(next(iter(_facet_memo)))
    return {field: list(values) for field, values in result.items()}


def _compute_observed_metadata_values(records: list[dict[str, Any]], *, present: bool = True) -> dict[str, list[str]]:
    """Every non-placeholder value seen for a metadata field, for build-wide facets.

    Computed over the reviewer-presented view of every stored Record, not the raw
    stored values: a build-wide facet list must not let a second reviewer recover
    another reviewer's sealed first answer merely because that value happens to
    populate a filter's suggestion list. Call within the caller's ``reviewer_scope``.
    """
    metadata_values: dict[str, set[str]] = {}
    for raw in records:
        record = copy.deepcopy(raw)
        if present:
            _present_for_reviewer(record)
        for field, value in record.items():
            if field in _NON_ASSERTION_FIELDS or (
                _operational_key(field) and field not in (record.get("metadata_field_status") or {})
            ):
                continue
            if field not in metadata_values and not isinstance(value, (str, list, tuple)):
                continue
            metadata_values.setdefault(field, set())
            values = value if isinstance(value, list) else [value]
            for item in values:
                if isinstance(item, str) and item.strip() and not is_placeholder(item):
                    metadata_values[field].add(item.strip())
        deterministic_ingest = record.get("deterministic_ingest")
        if isinstance(deterministic_ingest, dict):
            speakers = deterministic_ingest.get("speakers")
            if isinstance(speakers, (list, tuple)):
                for speaker in speakers:
                    if isinstance(speaker, str) and speaker.strip() and not is_placeholder(speaker):
                        metadata_values.setdefault("speaker", set()).add(speaker.strip())
        field_status = record.get("metadata_field_status")
        if isinstance(field_status, dict):
            for field, status in field_status.items():
                if field in _NON_ASSERTION_FIELDS or not isinstance(status, dict):
                    continue
                for candidate_key in ("proposed_value", "llm_value"):
                    candidate = status.get(candidate_key)
                    candidates = candidate if isinstance(candidate, (list, tuple)) else [candidate]
                    for item in candidates:
                        if isinstance(item, str) and item.strip() and not is_placeholder(item):
                            metadata_values.setdefault(field, set()).add(item.strip())
    return {
        field: sorted(values, key=str.casefold)
        for field, values in metadata_values.items()
        if values
    }
