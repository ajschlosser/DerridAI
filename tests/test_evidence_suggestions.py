# Copyright 2026 Aaron John Schlosser, PhD.
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import config
from app.evidence_suggestions import (
    evidence_cascade_llm_enabled,
    semantic_query,
    suggest_evidence_blocks,
    suggest_evidence_blocks_semantic,
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


def test_evidence_cascade_llm_enabled_request_flag_wins_over_setting(monkeypatch):
    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, metadata_evidence_cascade_llm_enabled=True))
    assert evidence_cascade_llm_enabled({"evidence_cascade_llm_enabled": False}) is False
    assert evidence_cascade_llm_enabled({}) is True
    assert evidence_cascade_llm_enabled(None) is True

    monkeypatch.setattr(config, "settings", dataclasses.replace(config.settings, metadata_evidence_cascade_llm_enabled=False))
    assert evidence_cascade_llm_enabled({"evidence_cascade_llm_enabled": True}) is True
    assert evidence_cascade_llm_enabled({}) is False
