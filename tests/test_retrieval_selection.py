# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import math

from app.retrieval_selection import (
    cosine_similarity,
    distance_to_relevance,
    mmr_select,
    source_aware_select,
)


def test_distance_to_relevance_is_metric_aware() -> None:
    assert distance_to_relevance(0.0, "cosine") == 1.0
    assert distance_to_relevance(1.0, "cosine") == 0.5
    assert distance_to_relevance(2.0, "cosine") == 0.0

    assert distance_to_relevance(0.0, "l2") == 1.0
    assert distance_to_relevance(1.0, "l2") == 0.5

    # Inner-product distances may be negative; unlike the legacy clamp, the
    # normalizer must preserve that ordering.
    assert distance_to_relevance(-2.0, "ip") > distance_to_relevance(0.0, "ip")
    assert distance_to_relevance(0.0, "ip") > distance_to_relevance(2.0, "ip")


def test_distance_to_relevance_legacy_fallback_preserves_old_rule() -> None:
    assert distance_to_relevance(-4.0) == 1.0
    assert math.isclose(distance_to_relevance(3.0), 0.25)


def test_cosine_similarity_handles_empty_and_orthogonal_vectors() -> None:
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_mmr_preserves_relevance_and_emits_separate_objective() -> None:
    candidates = [
        {"id": "a", "relevance": 1.0, "embedding": [1.0, 0.0]},
        {"id": "b", "relevance": 0.95, "embedding": [0.99, 0.01]},
        {"id": "c", "relevance": 0.80, "embedding": [0.0, 1.0]},
    ]

    selected = mmr_select(
        candidates,
        limit=2,
        lambda_mult=0.5,
        relevance=lambda row: float(row["relevance"]),
        vector=lambda row: row["embedding"],
    )

    assert [row["id"] for row in selected] == ["a", "c"]
    assert selected[0]["relevance"] == 1.0
    assert "mmr_score" in selected[0]
    assert "_mmr_vector" not in selected[0]


def test_source_aware_selection_avoids_adjacent_duplicate_context() -> None:
    candidates = [
        {
            "id": "a",
            "score": 1.0,
            "record": {
                "source_document_id": "s1",
                "work": "W",
                "page_start": 10,
                "text": "alpha beta gamma delta epsilon",
            },
        },
        {
            "id": "b",
            "score": 0.98,
            "record": {
                "source_document_id": "s1",
                "work": "W",
                "page_start": 11,
                "text": "alpha beta gamma delta zeta",
            },
        },
        {
            "id": "c",
            "score": 0.85,
            "record": {
                "source_document_id": "s2",
                "work": "Other",
                "page_start": 40,
                "text": "difference trace supplement writing",
            },
        },
    ]

    selected = source_aware_select(
        candidates,
        limit=2,
        relevance=lambda row: float(row["score"]),
    )

    assert [row["id"] for row in selected] == ["a", "c"]
    assert "diversity_score" in selected[1]
