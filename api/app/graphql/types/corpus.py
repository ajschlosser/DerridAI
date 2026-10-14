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

"""Corpus Builder review reads: lightweight queue rows versus full reviewer-presented Records.

A queue page (``review_queue``, ``rows``) returns :class:`CorpusQueueRow` —
identifiers, page labels, review state and a short ``text_preview``, never the
full text or metadata. Opening a Record for review reads ``record``/``records``,
which return :class:`CorpusRecord` (the reviewer-presented Record, including the
transitional ``review_document: JSON`` field the review panels consume today).
"""
from __future__ import annotations

from typing import Any

import strawberry
from strawberry.scalars import JSON

from .common import opt_int, opt_str

TEXT_PREVIEW_CHARS = 240


def _preview(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) <= TEXT_PREVIEW_CHARS:
        return compact
    return compact[: TEXT_PREVIEW_CHARS - 1].rstrip() + "…"


@strawberry.type(description="Build-wide review-queue counts by state.")
class CorpusQueueCounts:
    all: int
    ready: int
    preparing: int
    issues: int
    metadata: int
    topology: int
    source: int
    accepted: int
    rejected: int
    pending: int

    @classmethod
    def from_payload(cls, payload: dict[str, int]) -> CorpusQueueCounts:
        keys = ("all", "ready", "preparing", "issues", "metadata", "topology", "source", "accepted", "rejected", "pending")
        return cls(**{key: int(payload.get(key) or 0) for key in keys})


@strawberry.type(
    description=(
        "One review-queue row: identifiers, page labels, review state and a short preview. Never the full "
        "text or metadata (REST: GET /api/pdf/corpus-builds/{id}/records, each `items` entry)."
    ),
)
class CorpusQueueRow:
    record_id: str
    record_revision: int | None
    page_start: str | None
    page_end: str | None
    text_length: int
    text_preview: str
    review_state: str | None
    review_disposition: str | None
    review_issue_codes: list[str]
    metadata_llm_processed: bool
    needs_review: bool
    source_quality_issues: bool
    metadata_complete: bool
    state_version: int | None

    @classmethod
    def from_presented_record(cls, record: dict[str, Any]) -> CorpusQueueRow:
        from ...corpus_review_state import _review_issue_codes

        text = str(record.get("text") or "")
        return cls(
            record_id=str(record.get("record_id") or ""),
            record_revision=opt_int(record.get("record_revision")),
            page_start=opt_str(record.get("page_start")),
            page_end=opt_str(record.get("page_end")),
            text_length=len(text),
            text_preview=_preview(text),
            review_state=opt_str(record.get("review_state")),
            review_disposition=opt_str(record.get("review_disposition")),
            review_issue_codes=_review_issue_codes(record),
            metadata_llm_processed=bool(record.get("metadata_llm_processed")),
            needs_review=bool(record.get("needs_review")),
            source_quality_issues=bool(record.get("source_quality_issues")),
            metadata_complete=bool(record.get("metadata_complete")),
            state_version=opt_int(record.get("queue_state_version")),
        )


@strawberry.type(description="One page of the review queue: rows, total, and build-wide counts.")
class CorpusReviewQueuePage:
    items: list[CorpusQueueRow]
    total: int
    offset: int
    limit: int
    queue_counts: CorpusQueueCounts
    topology_count: int
    data_generation: int
    topology_generation: int
    next_cursor: str | None
    previous_cursor: str | None
    has_next_page: bool
    has_previous_page: bool

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> CorpusReviewQueuePage:
        return cls(
            items=[CorpusQueueRow.from_presented_record(item) for item in payload.get("items") or []],
            total=int(payload.get("total") or 0),
            offset=int(payload.get("offset") or 0),
            limit=int(payload.get("limit") or 0),
            queue_counts=CorpusQueueCounts.from_payload(payload.get("queue_counts") or {}),
            topology_count=int(payload.get("topology_count") or 0),
            data_generation=int(payload.get("data_generation") or 0),
            topology_generation=int(payload.get("topology_generation") or 0),
            next_cursor=opt_str(payload.get("next_cursor")),
            previous_cursor=opt_str(payload.get("previous_cursor")),
            has_next_page=bool(payload.get("has_next_page")),
            has_previous_page=bool(payload.get("has_previous_page")),
        )


@strawberry.type(
    description=(
        "A reviewer-presented Corpus Builder Record. `review_document` is transitional: the review panels "
        "still consume the full presented Record as JSON; prefer the typed fields above where they exist."
    ),
)
class CorpusRecord:
    record_id: str
    record_revision: int | None
    work: str | None
    text: str
    review_state: str | None
    review_disposition: str | None
    review_document: JSON

    @classmethod
    def from_presented_record(cls, record: dict[str, Any]) -> CorpusRecord:
        return cls(
            record_id=str(record.get("record_id") or ""),
            record_revision=opt_int(record.get("record_revision")),
            work=opt_str(record.get("work")),
            text=str(record.get("text") or ""),
            review_state=opt_str(record.get("review_state")),
            review_disposition=opt_str(record.get("review_disposition")),
            review_document=JSON(record),
        )
