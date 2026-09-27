# Copyright 2026 Aaron John Schlosser, PhD.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app.evidence_suggestions import suggest_evidence_blocks, validate_llm_choice

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
