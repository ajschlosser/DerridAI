# Copyright 2026 Aaron John Schlosser, PhD.
"""Corpus Builder review reads shared by REST and GraphQL.

Administrator-only, matching ``/api/pdf/*`` (route policy in ``middleware.py``).
GraphQL loads a build's Records once per request through
``graphql.loaders.RequestLoaders.corpus_build_records`` (see ``load_build_records``
below) and passes that same list into every pure function here, so a queue page,
a single Record read, ``rows`` and ``metadata_facets`` never each re-read the build
from disk. REST and GraphQL share repository-owned snapshot selections, while
reviewer presentation still runs for every request.
"""
from __future__ import annotations

import copy
from typing import Any

from ..corpus_builder import pdf_corpus_repository
from ..corpus_review_queue import (
    QueueFilter,
    empty_page,
    observed_metadata_values,
)
from ..corpus_review_state import _decorate_review_state
from ..corpus_reviewer_helpers import _present_for_reviewer
from .access import AccessContext, NotFound, reviewer_scope

# Mirrors REST's own page-size ceiling (``Query(..., le=200)`` on
# ``GET /api/pdf/corpus-builds/{id}/records``).
MAX_QUEUE_PAGE = 200


def load_build_records(access: AccessContext, build_ids: list[str]) -> list[list[dict[str, Any]] | None]:
    """One build's stored Records, loaded once per request however many fields read them.

    Returned records are raw (topology order, no presentation): callers apply
    review-state decoration and blind-review scrubbing themselves, scoped to
    their own reviewer identity. ``None`` means the build does not exist or has
    not stored any Records yet.
    """
    access.require_admin()
    results: list[list[dict[str, Any]] | None] = []
    for build_id in build_ids:
        try:
            records = pdf_corpus_repository.review_records(str(build_id))
        except KeyError:
            records = None
        results.append(records)
    return results


def require_build(records: list[dict[str, Any]] | None, build_id: str) -> list[dict[str, Any]]:
    if records is None:
        raise NotFound(f"Corpus build {build_id!r} was not found.")
    return records


def review_queue(
    access: AccessContext,
    records: list[dict[str, Any]] | None,
    build_id: str,
    *,
    filters: QueueFilter,
    offset: int,
    limit: int,
) -> dict[str, Any]:
    """REST's composite review page (``GET /api/pdf/corpus-builds/{id}/records``)."""
    resolved = require_build(records, build_id)
    limit = max(1, min(MAX_QUEUE_PAGE, int(limit)))
    if not resolved:
        return empty_page(offset, limit)
    with reviewer_scope(access):
        selection = pdf_corpus_repository.select_review_queue(resolved, filters, offset=offset, limit=limit)
    return {
        "items": selection.items,
        "total": selection.total,
        "offset": offset,
        "limit": limit,
        "queue_counts": selection.queue_counts,
    }


def present_record(access: AccessContext, record: dict[str, Any]) -> dict[str, Any]:
    """One Record as this reviewer should see it: review state plus blind-review scrub."""
    presented = copy.deepcopy(record)
    _decorate_review_state(presented)
    with reviewer_scope(access):
        _present_for_reviewer(presented)
    return presented


def stored_records_by_ids(
    access: AccessContext,
    build_id: str,
    record_ids: list[str],
) -> list[dict[str, Any] | None]:
    """Indexed reviewer-presented Record reads; never deserialize the whole corpus."""
    access.require_admin()
    try:
        records = pdf_corpus_repository.get_records(build_id, record_ids)
    except KeyError as exc:
        raise NotFound(f"Corpus build {build_id!r} was not found.") from exc
    return [present_record(access, record) if record is not None else None for record in records]


def stored_record_by_id(
    access: AccessContext,
    build_id: str,
    record_id: str,
) -> dict[str, Any]:
    record = stored_records_by_ids(access, build_id, [record_id])[0]
    if record is None:
        raise NotFound(f"Record {record_id!r} was not found.")
    return record


def record_by_id(
    access: AccessContext,
    records: list[dict[str, Any]] | None,
    build_id: str,
    record_id: str,
) -> dict[str, Any]:
    resolved = require_build(records, build_id)
    for record in resolved:
        if str(record.get("record_id")) == str(record_id):
            return present_record(access, record)
    raise NotFound(f"Record {record_id!r} was not found.")


def records_by_ids(
    access: AccessContext,
    records: list[dict[str, Any]] | None,
    build_id: str,
    record_ids: list[str],
) -> list[dict[str, Any] | None]:
    resolved = require_build(records, build_id)
    by_id = {str(record.get("record_id")): record for record in resolved}
    return [
        present_record(access, by_id[str(record_id)]) if str(record_id) in by_id else None
        for record_id in record_ids
    ]


def metadata_facets(
    records: list[dict[str, Any]] | None,
    build_id: str,
    fields: list[str] | None = None,
) -> dict[str, list[str]]:
    """Build-wide observed metadata values, optionally narrowed to specific fields."""
    resolved = require_build(records, build_id)
    facets = observed_metadata_values(resolved)
    if not fields:
        return facets
    wanted = set(fields)
    return {field: values for field, values in facets.items() if field in wanted}
