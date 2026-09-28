# Copyright 2026 Aaron John Schlosser, PhD.
import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import config
from app import cross_encoder as cross_encoder_module
from app.evidence_suggestions import (
    CASCADE_MAX_BLOCKS,
    evidence_cascade_llm_enabled,
    semantic_query,
    suggest_evidence_blocks,
    suggest_evidence_blocks_semantic,
    suggest_evidence_cascade,
    validate_llm_choice,
)

BLOCKS = [
    {"block_id": "b1", "text": "Preface by the editor on translation."},
    {"block_id": "b2", "text": "Il n'y a pas de hors-texte, écrit Derrida."},
    {"block_id": "b3", "text": "Speech and writing are opposed in the tradition."},
]


def test_verbatim_value_ranks_first_ignoring_case_accents_punctuation():
    out = suggest_evidence_blocks("IL N'Y A PAS DE HORS-TEXTE", BLOCKS)
    assert out[0]["block_id"] == "b2" and out[0]["score"] == 1.0


def test_partial_overlap_scores_below_verbatim_and_unrelated_is_dropped():
    out = suggest_evidence_blocks(["speech opposed writing"], BLOCKS)
    assert out[0]["block_id"] == "b3" and out[0]["score"] < 1.0
    assert all(item["block_id"] != "b1" for item in out)


def test_empty_value_or_blocks_yield_nothing():
    assert suggest_evidence_blocks(None, BLOCKS) == []
    assert suggest_evidence_blocks("x", []) == []


def test_llm_choice_drops_invented_ids_and_flags_unsupported_blocks():
    result = {"block_ids": ["b2", "ghost", "b2", "b1"], "reason": "states it"}
    out = validate_llm_choice(result, BLOCKS, "il n'y a pas de hors-texte")
    assert [o["block_id"] for o in out] == ["b2", "b1"]
    assert out[0]["lexical_support"] is True and out[1]["lexical_support"] is False


def test_citation_strings_do_not_assume_an_author():
    from app.rag import _citation_strings

    inline, full = _citation_strings({"work": "Of Grammatology", "year": 1967})
    assert "Derrida" not in inline + full
    assert full.startswith("Of Grammatology")


class LocalProjection:
    def __init__(self, vectors, query_vector=None, error=None):
        self.vectors = vectors
        self.query_vector = query_vector or [1.0, 0.0]
        self.error = error
        self.queries = []

    def sync(self, *args, **kwargs):
        if self.error:
            raise self.error

    def embeddings_for(self, _document_id, _unit_ids, **_kwargs):
        return self.vectors

    def embed_query(self, query, **_kwargs):
        self.queries.append(query)
        return self.query_vector


def test_semantic_query_uses_schema_metadata_and_proposed_value():
    query = semantic_query(
        {
            "name": "custom_field",
            "label": "Custom field",
            "type": "choice",
            "instruction": "Describe the relevant orientation.",
            "values": [{"value": "affirming"}, {"value": "critical"}],
        },
        "affirming",
    )
    assert "Custom field" in query
    assert "Describe the relevant orientation." in query
    assert "Proposed value: affirming" in query
    assert "affirming, critical" in query


def test_semantic_only_paraphrase_is_returned_with_separate_signal():
    blocks = [{"block_id": "b1", "text": "A passage about hospitality."}]
    projection = LocalProjection({"b1": [1.0, 0.0]})
    items, status = suggest_evidence_blocks_semantic(
        "welcoming the stranger",
        blocks,
        field_metadata={"label": "Ethical relation", "instruction": "Describe the relation."},
        source_document_id="doc",
        projection=projection,
    )
    assert status["semantic"] == "available"
    assert items[0]["block_id"] == "b1"
    assert items[0]["lexical_score"] is None
    assert items[0]["semantic_score"] == 1.0
    assert items[0]["method"] == "local-semantic-v1"
    assert "Ethical relation" in projection.queries[0]
    assert "welcoming the stranger" in projection.queries[0]


def test_lexical_and_semantic_signals_are_kept_separate():
    blocks = [{"block_id": "b1", "text": "Hospitality welcomes the stranger."}]
    projection = LocalProjection({"b1": [1.0, 0.0]})
    items, _ = suggest_evidence_blocks_semantic(
        "hospitality",
        blocks,
        field_metadata={"label": "Topic"},
        source_document_id="doc",
        projection=projection,
    )
    item = items[0]
    assert item["lexical_score"] == 1.0
    assert item["semantic_score"] == 1.0
    assert item["signals"]["lexical"]["method"].startswith("deterministic-lexical")
    assert item["signals"]["semantic"]["method"] == "local-semantic-v1"


def test_semantic_provider_failure_falls_back_to_lexical_and_is_visible():
    blocks = [{"block_id": "b1", "text": "Hospitality welcomes the stranger."}]
    projection = LocalProjection({}, error=RuntimeError("provider unavailable"))
    items, status = suggest_evidence_blocks_semantic(
        "hospitality",
        blocks,
        field_metadata={"label": "Topic"},
        source_document_id="doc",
        projection=projection,
    )
    assert items[0]["block_id"] == "b1"
    assert status["semantic"] == "fallback"
    assert "provider unavailable" in status["reason"]
    assert items[0]["semantic_status"] == "fallback"
    assert "provider unavailable" in items[0]["semantic_reason"]


def test_llm_choice_remains_closed_and_bounded():
    result = {"block_ids": ["b2", "b3", "b1"], "reason": "supported"}
    out = validate_llm_choice(result, BLOCKS, "speech", limit=1)
    assert [item["block_id"] for item in out] == ["b2"]


# --- suggest_evidence_cascade ------------------------------------------------------------


class TrackingProjection(LocalProjection):
    """Counts sync/embedding calls so a test can prove a later stage was never reached."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sync_calls = 0

    def sync(self, *args, **kwargs):
        self.sync_calls += 1
        return super().sync(*args, **kwargs)


def test_cascade_stops_at_strong_lexical_match_without_touching_embeddings():
    projection = TrackingProjection({})
    result = suggest_evidence_cascade(
        "calm", [{"block_id": "b1", "text": "calm calm calm"}],
        field="mood", field_metadata={"label": "Mood"}, source_document_id="doc", projection=projection,
    )
    assert result["block_ids"] == ["b1"]
    assert result["method"] == "deterministic-lexical-v1"
    assert result["confidence"] is None and result["backfilled"] is True
    assert projection.sync_calls == 0  # stage 2/3 never reached


def test_cascade_falls_to_cross_encoder_rerank_when_lexical_is_weak(monkeypatch):
    blocks = [
        {"block_id": "b1", "text": "A passage about something else entirely."},
        {"block_id": "b2", "text": "A passage about hospitality and the stranger."},
    ]
    projection = LocalProjection({"b1": [1.0, 0.0], "b2": [0.9, 0.1]}, query_vector=[1.0, 0.0])

    def fake_predict_scores(pairs, *, model_name, timeout_seconds):
        # Cross-encoder disagrees with the cosine order above: whichever pair's text
        # mentions hospitality wins the rerank (positive), the other is rejected (negative).
        return [0.8 if "hospitality" in text else -0.5 for _query, text in pairs], {}

    monkeypatch.setattr(cross_encoder_module, "predict_scores", fake_predict_scores)
    result = suggest_evidence_cascade(
        "welcoming the stranger", blocks,
        field="topic", field_metadata={"label": "Topic"}, source_document_id="doc", projection=projection,
    )
    assert result["method"] == "cross-encoder-rerank-v1"
    assert result["block_ids"] == ["b2"]
    assert result["confidence"] is None and result["backfilled"] is True


def test_cascade_falls_to_mmr_similarity_when_cross_encoder_is_unavailable(monkeypatch):
    blocks = [
        {"block_id": "b1", "text": "A passage about hospitality and the stranger."},
        {"block_id": "b2", "text": "A passage about something else entirely."},
    ]
    projection = LocalProjection({"b1": [1.0, 0.0], "b2": [0.0, 1.0]}, query_vector=[1.0, 0.0])
    monkeypatch.setattr(cross_encoder_module, "predict_scores", lambda *a, **k: (None, {"fallback_reason": "missing_dependency"}))
    result = suggest_evidence_cascade(
        "welcoming the stranger", blocks,
        field="topic", field_metadata={"label": "Topic"}, source_document_id="doc", projection=projection,
        limit=1,
    )
    assert result["method"] == "mmr-similarity-v1"
    assert result["block_ids"] == ["b1"]
    assert len(result["block_ids"]) <= CASCADE_MAX_BLOCKS
    assert result["confidence"] is None and result["backfilled"] is True


def test_cascade_falls_to_llm_as_last_resort_and_accepts_unsupported_choice(monkeypatch):
    blocks = [{"block_id": "b1", "text": "Nothing relevant here."}]
    projection = LocalProjection({}, error=RuntimeError("no embedding backend"))
    monkeypatch.setattr(cross_encoder_module, "predict_scores", lambda *a, **k: (None, {}))

    def llm_choice(prompt: str):
        assert "topic" in prompt
        return {"block_ids": ["b1"], "reason": "The model's own judgment."}

    result = suggest_evidence_cascade(
        "an unrelated value", blocks,
        field="topic", field_metadata={"label": "Topic"}, source_document_id="doc", projection=projection,
        llm_choice=llm_choice,
    )
    assert result["method"] == "llm-evidence-choice-v1"
    assert result["block_ids"] == ["b1"]
    assert result["confidence"] is None and result["backfilled"] is True


def test_cascade_returns_none_when_the_llm_stage_raises():
    blocks = [{"block_id": "b1", "text": "Nothing relevant here."}]
    projection = LocalProjection({}, error=RuntimeError("no embedding backend"))

    def failing_llm_choice(prompt: str):
        raise RuntimeError("provider unreachable")

    result = suggest_evidence_cascade(
        "an unrelated value", blocks,
        field="topic", field_metadata={"label": "Topic"}, source_document_id="doc", projection=projection,
        llm_choice=failing_llm_choice,
    )
    assert result is None


def test_cascade_returns_none_for_empty_blocks_or_empty_value():
    projection = TrackingProjection({})
    assert suggest_evidence_cascade(
        "x", [], field="f", field_metadata={}, source_document_id="doc", projection=projection,
    ) is None
    assert suggest_evidence_cascade(
        None, [{"block_id": "b1", "text": "anything"}], field="f", field_metadata={}, source_document_id="doc",
        projection=projection,
    ) is None
    assert projection.sync_calls == 0


def test_evidence_cascade_llm_enabled_request_flag_wins_over_setting(monkeypatch):
    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, metadata_evidence_cascade_llm_enabled=True))
    assert evidence_cascade_llm_enabled({"evidence_cascade_llm_enabled": False}) is False
    assert evidence_cascade_llm_enabled({}) is True
    assert evidence_cascade_llm_enabled(None) is True

    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, metadata_evidence_cascade_llm_enabled=False))
    assert evidence_cascade_llm_enabled({"evidence_cascade_llm_enabled": True}) is True
    assert evidence_cascade_llm_enabled({}) is False
