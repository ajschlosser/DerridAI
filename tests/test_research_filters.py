# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

from __future__ import annotations

import pytest
from app.chroma_store import ChromaStore
from app.models import RAGRunRequest, ResearchFilterPlan
from app.research_filters import (
    combine_metadata_filters,
    metadata_filter_fields,
    normalize_document_filter,
    normalize_metadata_filter,
)
from pydantic import ValidationError


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


class _CaptureCollection:
    def __init__(self) -> None:
        self.metadata = {"hnsw:space": "cosine"}
        self.last_get = None
        self.last_query = None

    def count(self) -> int:
        return 1

    def query(self, **kwargs):
        self.last_query = kwargs
        return {
            "ids": [["r1"]],
            "documents": [["The trace is not a presence."]],
            "metadatas": [[{"_record_id": "r1", "work": "Of Grammatology"}]],
            "distances": [[0.1]],
            "embeddings": [[[0.2, 0.3]]],
        }

    def get(self, **kwargs):
        self.last_get = kwargs
        return {
            "ids": ["r1"],
            "documents": ["The trace is not a presence."],
            "metadatas": [{"_record_id": "r1", "work": "Of Grammatology"}],
        }


class _Embeddings:
    def embed_query(self, _query, *, provider=None, model=None):
        return [0.1, 0.2]


def _capture_store(collection: _CaptureCollection) -> ChromaStore:
    store = object.__new__(ChromaStore)
    store._collection = lambda _name: collection
    store._embedding_spec = lambda _collection: ("chroma", None)
    store.embeddings = _Embeddings()
    return store


def test_chroma_candidate_generation_receives_both_filter_channels() -> None:
    collection = _CaptureCollection()
    store = _capture_store(collection)
    where = {"work": {"$eq": "Of Grammatology"}}
    where_document = {"$contains": "trace"}

    semantic = store.semantic_candidates(
        "corpus",
        "trace",
        4,
        where=where,
        where_document=where_document,
    )

    assert [item["record"]["record_id"] for item in semantic] == ["r1"]
    assert collection.last_query["where"] == where
    assert collection.last_query["where_document"] == where_document

    lexical = store.lexical_search(
        "corpus",
        "trace",
        4,
        where=where,
        where_document=where_document,
    )

    assert [item["record"]["record_id"] for item in lexical] == ["r1"]
    assert collection.last_get["where"] == where
    assert collection.last_get["where_document"] == where_document
