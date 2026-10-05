# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import RAGRunRequest, ResearchFilterPlan
from app.research_filters import (
    combine_metadata_filters,
    metadata_filter_fields,
    normalize_document_filter,
    normalize_metadata_filter,
)


def test_metadata_filter_accepts_nested_chroma_subset() -> None:
    raw = {
        "$and": [
            {"work": {"$eq": "Of Grammatology"}},
            {
                "$or": [
                    {"page_start": {"$gte": 100}},
                    {"speaker": {"$in": ["Derrida", "Levinas"]}},
                ]
            },
        ]
    }

    normalized = normalize_metadata_filter(raw)

    assert normalized == raw
    assert metadata_filter_fields(normalized) == {"work", "page_start", "speaker"}


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ({"work": "A", "speaker": "B"}, "exactly one"),
        ({"$and": [{"work": "A"}]}, "at least two"),
        ({"page_start": {"$gte": True}}, "numeric"),
        ({"speaker": {"$in": []}}, "non-empty"),
        ({"speaker": {"$in": ["Derrida", 1]}}, "same-type"),
        ({"speaker": {"$contains": "Derrida"}}, "unsupported operator"),
    ],
)
def test_metadata_filter_rejects_ambiguous_or_unsupported_shapes(value, message) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_metadata_filter(value)


def test_document_filter_supports_contains_negation_and_boolean_groups() -> None:
    raw = {
        "$and": [
            {"$contains": "trace"},
            {"$not_contains": "Heidegger"},
        ]
    }

    assert normalize_document_filter(raw) == raw


def test_combining_scope_filters_preserves_both_constraints() -> None:
    combined = combine_metadata_filters(
        {"work": {"$ne": "Totality and Infinity"}},
        {"work": {"$in": ["Of Grammatology"]}},
    )

    assert combined == {
        "$and": [
            {"work": {"$ne": "Totality and Infinity"}},
            {"work": {"$in": ["Of Grammatology"]}},
        ]
    }


def test_rag_filter_plan_validates_before_job_execution() -> None:
    request = RAGRunRequest(
        prompt="What is the trace?",
        source_collection="corpus",
        filter_plan={
            "metadata_filter": {"work": {"$eq": "Of Grammatology"}},
            "document_filter": {"$not_contains": "editorial note"},
            "source": "explicit",
        },
    )

    assert isinstance(request.filter_plan, ResearchFilterPlan)
    assert request.filter_plan.metadata_filter == {"work": {"$eq": "Of Grammatology"}}

    with pytest.raises(ValidationError, match="requires a numeric value"):
        RAGRunRequest(
            prompt="What is the trace?",
            source_collection="corpus",
            filter_plan={"metadata_filter": {"page_start": {"$gte": "late"}}},
        )
