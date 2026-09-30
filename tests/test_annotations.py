# Copyright 2026 Aaron John Schlosser, PhD.
"""Contracts for scoped annotation and thread payloads."""

from __future__ import annotations

import pytest
from app.models import AnnotationCreateRequest, AnnotationReplyRequest
from pydantic import ValidationError


def test_legacy_annotation_shape_derives_scope_from_quote() -> None:
    text = AnnotationCreateRequest(record_id="record-1", quote="selected passage", note="review")
    assert text.scope == "text"

    record = AnnotationCreateRequest(record_id="record-1", note="whole-record note")
    assert record.scope == "record"


def test_work_annotations_require_work_and_can_link_records() -> None:
    annotation = AnnotationCreateRequest(
        scope="work",
        work="Writing and Difference",
        linked_record_ids=["record-2", "record-3"],
        note="Compare these passages.",
    )
    assert annotation.record_id is None
    assert annotation.linked_record_ids == ["record-2", "record-3"]


@pytest.mark.parametrize(
    "payload",
    [
        {"scope": "text", "record_id": "record-1", "note": "missing quote"},
        {"scope": "record", "note": "missing record"},
        {"scope": "work", "record_id": "record-1", "note": "missing work"},
    ],
)
def test_scoped_annotation_targets_are_required(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        AnnotationCreateRequest(**payload)


def test_reply_requires_no_target_and_preserves_content_contract() -> None:
    reply = AnnotationReplyRequest(note="A useful qualification.", tags=["review"])
    assert reply.note == "A useful qualification."
    with pytest.raises(ValidationError):
        AnnotationReplyRequest(note="", quote="", tags=[])
