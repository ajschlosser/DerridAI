# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic RAG provenance gates run before any synthesis request."""

from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
sys.modules.setdefault("chromadb", types.SimpleNamespace())

from app.rag import evidence_sufficiency_issues


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
