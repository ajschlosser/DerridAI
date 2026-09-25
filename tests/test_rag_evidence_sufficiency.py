# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic RAG provenance gates run before any synthesis request."""

from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
sys.modules.setdefault("chromadb", types.SimpleNamespace())

from app.rag import evidence_sufficiency_issues, extract_evidence_ids, strip_evidence_markers


def _evidence(**record):
    return {
        "evidence_id": "E0",
        "record": record,
        "inline_citation": "Derrida 1967: 12",
        "full_citation": "Derrida, Jacques. Of Grammatology. 1967.",
    }


def test_evidence_sufficiency_accepts_provenance_complete_record():
    evidence = [_evidence(
        record_id="of-grammatology-12",
        work="Of Grammatology",
        document_author="Jacques Derrida",
        text="There is no exact text without a source.",
    )]
    assert evidence_sufficiency_issues(evidence) == []


def test_evidence_sufficiency_reports_missing_exact_text_and_citation_metadata():
    issues = evidence_sufficiency_issues([_evidence(record_id="r1", work="", document_author="", text="")])
    assert issues == [{"evidence_id": "E0", "missing": "work, document_author, exact_text"}]


def test_evidence_marker_parser_matches_all_rendered_citation_forms():
    text = " ".join([
        "A [[E0]].",
        "B ((E1, E2)).",
        "C {{E3}}.",
        "D [E4].",
        "E (E5; E6).",
        "F {E7}.",
    ])
    assert extract_evidence_ids(text) == ["E0", "E1", "E2", "E3", "E4", "E5", "E6", "E7"]
    stripped = strip_evidence_markers("A claim [[E0, E2]].")
    assert stripped == "A claim."
