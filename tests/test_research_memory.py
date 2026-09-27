# Copyright 2026 Aaron John Schlosser, PhD.
"""Research memory: optional, advisory steering from prior responses and validated claims.

Why: "Use cached responses to steer answers" must find prior answers to *similar*
questions, not only ones sharing keywords, and must never let an ungraded or poorly
graded answer steer a new one. "Use cached provenance to steer claims" must use only
reviewer-validated claims and tell the generator whether each cited Record is in the
current evidence, since only current evidence can be cited. Projection hits are
re-joined to authoritative rows, and an unavailable embedding service degrades
visibly to lexical matching rather than silently dropping the channel.
How: fake projection indexes over a real temp SQLite repository.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import research_memory as rm  # noqa: E402
from app.chroma_store import ChromaStore  # noqa: E402
from app.persistence import SQLiteSystemRepository  # noqa: E402


@pytest.fixture()
def repo(tmp_path: Path) -> SQLiteSystemRepository:
    repository = SQLiteSystemRepository(tmp_path / "system.sqlite3")
    rows = {
        "good": ("What did Derrida say about hospitality?", 8.0),
        "weak": ("What did Derrida say about the gift?", 4.0),
        "ungraded": ("Derrida on hospitality and the stranger", None),
    }
    for response_id, (question, score) in rows.items():
        repository.put_response_memory(
            {"response_id": response_id, "owner": "ann", "question": question, "answer": f"Answer {response_id}"}
        )
        if score is not None:
            repository.record_response_memory_grade(response_id, {"overall": score, "grader_model": "judge"})
    return repository


class FakeResponseIndex:
    def __init__(self, hits):
        self.hits = hits
        self.synced = False

    def sync(self, system_store):
        self.synced = True

    def similar(self, question, **kwargs):
        return self.hits


def test_eligibility_requires_a_grade_at_or_above_the_threshold():
    base = {"question": "Q", "answer": "A"}
    assert rm.ineligibility(base, 7) == "ungraded"
    assert rm.ineligibility({**base, "latest_grade": {"overall": 6.5}}, 7) == "below_grade_threshold"
    assert rm.ineligibility({**base, "latest_grade": {"overall": 7}}, 7) == ""
    assert rm.ineligibility({"question": "Q", "answer": ""}, 7) == "missing_text"


def test_semantic_hits_are_rejoined_and_ineligible_rows_dropped(repo):
    index = FakeResponseIndex(
        [
            {"response_id": "good", "similarity": 0.9},
            {"response_id": "weak", "similarity": 0.8},
            {"response_id": "ungraded", "similarity": 0.7},
            {"response_id": "deleted", "similarity": 0.6},
        ]
    )
    out = rm.select_prior_responses(
        "How does the notion of hospitality influence Derrida?",
        owner="ann",
        system_store=repo,
        index_factory=lambda: index,
    )
    assert index.synced
    assert out["mode"] == "semantic"
    assert [item["response_id"] for item in out["items"]] == ["good"]
    assert out["items"][0]["grade"]["overall"] == 8.0


def test_other_owners_responses_are_not_rejoined(repo):
    index = FakeResponseIndex([{"response_id": "good", "similarity": 0.9}])
    out = rm.select_prior_responses("hospitality", owner="bob", system_store=repo, index_factory=lambda: index)
    assert out["items"] == []


def test_unavailable_embeddings_fall_back_to_lexical_matching_visibly(repo):
    def broken():
        raise RuntimeError("embedding service offline")

    out = rm.select_prior_responses(
        "Derrida and hospitality", owner="ann", system_store=repo, index_factory=broken
    )
    assert out["mode"] == "lexical_fallback"
    assert "embedding service offline" in out["warnings"][0]
    # The ungraded row shares more words but must not steer.
    assert [item["response_id"] for item in out["items"]] == ["good"]


def test_grades_and_claim_status_filters_are_durable(repo):
    assert repo.get_response_memory("good", owner="ann")["latest_grade"]["overall"] == 8.0
    assert repo.get_response_memory("good", owner="bob") is None
    assert repo.record_response_memory_grade("missing", {"overall": 9}) is False
    repo.put_generated_claim({"claim_id": "c1", "claim_text": "A", "validation_status": "validated"})
    repo.put_generated_claim({"claim_id": "c2", "claim_text": "B"})
    assert [c["claim_id"] for c in repo.list_generated_claims(validation_status="validated")] == ["c1"]
    assert [c["claim_id"] for c in repo.list_generated_claims(validation_status="unvalidated")] == ["c2"]


class FakeClaimIndex:
    def ensure_current(self, system_store):
        pass

    def similar(self, text, **kwargs):
        return [{"claim_id": "c1", "similarity": 0.8, "metadata": {}}]


class ClaimStore:
    def get_generated_claim(self, claim_id, owner=None):
        return {"claim_id": claim_id, "claim_text": "Hospitality is unconditional.", "validation_status": "validated"}

    def list_claim_support_bindings(self, claim_id, owner=None):
        cite = {"inline": "(Derrida, Of Hospitality, 25)"}
        return [
            {"claim_id": claim_id, "record_id": "r-now", "record_revision": 2, "relation": "supports", "citation": cite},
            {"claim_id": claim_id, "record_id": "r-old", "record_revision": 1, "relation": "supports", "citation": cite},
            {"claim_id": claim_id, "record_id": "r-away", "record_revision": 1, "relation": "contextualizes"},
        ]


def test_validated_claim_support_is_checked_against_current_evidence():
    evidence = [
        {"evidence_id": "E1", "record": {"record_id": "r-now", "record_revision": 2}},
        {"evidence_id": "E2", "record": {"record_id": "r-old", "record_revision": 3}},
    ]
    out = rm.select_prior_claims(
        "hospitality", owner=None, evidence=evidence, system_store=ClaimStore(), index_factory=FakeClaimIndex
    )
    statuses = {s["record_id"]: (s["status"], s["evidence_id"]) for s in out["items"][0]["support"]}
    assert statuses == {
        "r-now": ("in_current_evidence", "E1"),
        "r-old": ("revised_since_validation", "E2"),
        "r-away": ("not_in_current_evidence", None),
    }
    text = rm.render_claims(out["items"])
    assert "(Derrida, Of Hospitality, 25) - cited Record is in current EVIDENCE as [E1]" in text
    assert "cannot be cited in this answer" in text


def test_memory_guidance_records_what_steered_the_run(repo):
    response_text, claim_text, detail = rm.memory_guidance(
        "hospitality",
        use_responses=True,
        use_claims=False,
        owner="ann",
        evidence=[],
        system_store=repo,
        response_index_factory=lambda: FakeResponseIndex([{"response_id": "good", "similarity": 0.9}]),
        claim_index_factory=FakeClaimIndex,
    )
    assert "[prior-response:good] (graded 8/10 by judge" in response_text
    assert claim_text == ""
    assert detail["response_ids"] == ["good"] and detail["claim_mode"] == "off"


def test_response_cache_vectors_distinguish_different_text():
    first = ChromaStore._response_cache_embedding("Derrida on hospitality")
    second = ChromaStore._response_cache_embedding("Levinas on the face")
    assert first != second
