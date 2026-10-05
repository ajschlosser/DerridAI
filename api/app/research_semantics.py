# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""Semantic metadata access for Research retrieval and reranking.

Research algorithms should depend on stable semantic identities, not mutable
schema/storage field names. Legacy top-level Record projections remain readable
at this boundary so older stores continue to work while FieldAssertions become
the authoritative metadata representation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .field_assertions import current_assertions
from .metadata_schema import DOCUMENT_FIELDS, SEMANTIC_COMPATIBILITY_IDS

SOURCE_AUTHOR_ID = "derridai.document.document_author"
QUOTED_AUTHOR_ID = "derridai.quotation.author"
QUOTED_WORK_ID = "derridai.quotation.work"
POSITION_HOLDER_ID = "derridai.position_holder"
SPEAKER_ID = "derridai.speaker"
TOPICS_ID = "derridai.indexing.topics"
CONCEPTS_ID = "derridai.indexing.concepts"
PERSONS_ID = "derridai.indexing.persons"


def _projection_names(semantic_id: str) -> tuple[str, ...]:
    """Return compatibility projection names declared for one semantic identity."""

    names = [
        name
        for name, identity in DOCUMENT_FIELDS.items()
        if identity == semantic_id
    ]
    names.extend(
        name
        for name, identity in SEMANTIC_COMPATIBILITY_IDS.items()
        if identity == semantic_id
    )
    return tuple(dict.fromkeys(names))


def semantic_value(record: Mapping[str, Any], semantic_id: str) -> Any:
    """Resolve the selected value for a stable semantic identity.

    Current FieldAssertions win. Top-level projections are compatibility-only
    fallbacks discovered from the schema registries rather than embedded in
    retrieval/reranking algorithms.
    """

    assertion_buckets = record.get("field_assertions")
    if isinstance(assertion_buckets, dict):
        mutable = record if isinstance(record, dict) else dict(record)
        for assertion in current_assertions(mutable):
            if assertion.field_id != semantic_id:
                continue
            if assertion.value_status == "confirmed_absent":
                return None
            if assertion.value_status == "present":
                return assertion.value
            return None

    for name in _projection_names(semantic_id):
        if name in record:
            return record.get(name)
    return None


def semantic_text(record: Mapping[str, Any], semantic_id: str) -> str:
    value = semantic_value(record, semantic_id)
    if isinstance(value, (list, tuple, set)):
        return " ".join(str(item) for item in value if item not in (None, ""))
    return str(value or "").strip()


def source_author(record: Mapping[str, Any]) -> str:
    return semantic_text(record, SOURCE_AUTHOR_ID)


def source_work_label(record: Mapping[str, Any]) -> str:
    """Return the legacy/publication work label at one compatibility boundary.

    The work projection predates stable semantic field identities and remains
    part of the published Record compatibility projection. Retrieval code must
    use this helper instead of binding itself to that storage name.
    """

    return str(record.get("work") or "").strip()


def rerank_attribution_context(record: Mapping[str, Any], passage: str) -> str:
    """Render source/attribution roles for rerankers from semantic identities."""

    rows = [
        ("Source document author", semantic_value(record, SOURCE_AUTHOR_ID)),
        ("Source work", source_work_label(record)),
        ("Quoted author", semantic_value(record, QUOTED_AUTHOR_ID)),
        ("Quoted work", semantic_value(record, QUOTED_WORK_ID)),
        ("Position holder", semantic_value(record, POSITION_HOLDER_ID)),
        ("Passage", passage),
    ]
    return "\n".join(f"{label}: {value or ''}" for label, value in rows)
