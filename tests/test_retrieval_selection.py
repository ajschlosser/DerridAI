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

from __future__ import annotations

import math
import random
from copy import deepcopy

import pytest
from app import retrieval_selection
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



def test_source_aware_selection_penalizes_repeated_document_author() -> None:
    candidates = [
        {
            "id": "d1",
            "score": 1.0,
            "record": {
                "source_document_id": "derrida-a",
                "document_author": "Jacques Derrida",
                "work": "Of Grammatology",
                "page_start": 10,
                "text": "trace writing supplement difference",
            },
        },
        {
            "id": "d2",
            "score": 0.97,
            "record": {
                "source_document_id": "derrida-b",
                "document_author": "Jacques Derrida",
                "work": "Writing and Difference",
                "page_start": 80,
                "text": "structure play sign absence",
            },
        },
        {
            "id": "l1",
            "score": 0.90,
            "record": {
                "source_document_id": "levinas-a",
                "document_author": "Emmanuel Levinas",
                "work": "Totality and Infinity",
                "page_start": 40,
                "text": "alterity face infinity exteriority",
            },
        },
    ]

    selected = source_aware_select(
        candidates,
        limit=2,
        relevance=lambda row: float(row["score"]),
    )

    assert [row["id"] for row in selected] == ["d1", "l1"]


@pytest.mark.parametrize("limit", [0, 1, 7, 30])
@pytest.mark.parametrize("weight", [0.0, 0.5, 1.0])
def test_mmr_matches_exhaustive_selection(limit: int, weight: float) -> None:
    rng = random.Random(91)
    rows = [
        {"id": i, "relevance": rng.choice([0.5, 0.8, 1.0]),
         "embedding": [rng.uniform(-1, 1) for _ in range(4)]}
        for i in range(20)
    ]
    rows[1]["embedding"] = None
    rows[2]["embedding"] = [0.0] * 4
    rows[3]["embedding"] = [1.0]
    original = deepcopy(rows)
    remaining = list(rows)
    expected = []
    while remaining and len(expected) < limit:
        scores = [weight * row["relevance"] - (1 - weight) * max(
            (cosine_similarity(row["embedding"], chosen["embedding"]) for chosen in expected),
            default=0.0,
        ) for row in remaining]
        index = max(range(len(remaining)), key=scores.__getitem__)
        expected.append({**remaining.pop(index), "mmr_score": scores[index]})
    assert mmr_select(
        rows, limit=limit, lambda_mult=weight,
        relevance=lambda row: row["relevance"], vector=lambda row: row["embedding"],
    ) == expected
    assert rows == original


def test_mmr_preserves_negative_similarity_and_stable_ties() -> None:
    rows = [
        {"id": "a", "embedding": [1.0, 0.0]},
        {"id": "b", "embedding": [-1.0, 0.0]},
        {"id": "c", "embedding": [-1.0, 0.0]},
    ]
    selected = mmr_select(rows, limit=3, lambda_mult=0.5,
                          relevance=lambda row: 1.0, vector=lambda row: row["embedding"])
    assert [row["id"] for row in selected] == ["a", "b", "c"]
    assert [row["mmr_score"] for row in selected] == [0.5, 1.0, 0.0]


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("limit", [0, 1, 3, 10])
def test_source_selection_preserves_ties_missing_pages_and_inputs(nested: bool, limit: int) -> None:
    records = [
        {"source_asset_id": "s1", "work": "W", "text": "alpha beta gamma"},
        {"source_asset_id": "s1", "work": "W", "text": "ALPHA beta gamma"},
        {"source_document_id": "s2", "work": "X", "page_start": 4, "text": "delta epsilon"},
        {"source_document_id": "s2", "work": "X", "page_start": 9, "text": "different terms"},
    ]
    rows = [{"id": i, **({"record": record} if nested else record)} for i, record in enumerate(records)]
    original = deepcopy(rows)
    result = source_aware_select(rows, limit=limit, relevance=lambda row: 1.0)
    assert [row["id"] for row in result] == [0, 2, 3, 1][:limit]
    assert [row["diversity_score"] for row in result] == pytest.approx([1.0, 1.0, 0.6, 0.05][:limit])
    assert rows == original


def test_mmr_evaluates_each_candidate_pair_once(monkeypatch) -> None:
    comparisons = []
    original = cosine_similarity

    def counted(left, right):
        comparisons.append((id(left), id(right)))
        return original(left, right)

    monkeypatch.setattr(retrieval_selection, "cosine_similarity", counted)
    rows = [{"embedding": [1.0, float(i)]} for i in range(12)]
    mmr_select(rows, limit=5, lambda_mult=0.5,
               relevance=lambda row: 1.0, vector=lambda row: row["embedding"])
    assert len(comparisons) == sum(12 - selected for selected in range(1, 5))
    assert len(comparisons) == len(set(comparisons))


def test_source_selection_tokenizes_each_passage_once() -> None:
    class CountedText(str):
        calls = 0

        def __str__(self):
            type(self).calls += 1
            return super().__str__()

    rows = [{"text": CountedText(f"passage number {i}")} for i in range(12)]
    source_aware_select(rows, limit=5, relevance=lambda row: 1.0)
    assert CountedText.calls == len(rows)
