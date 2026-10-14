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

"""Deterministic RAG provenance gates run before any synthesis request."""

from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
sys.modules.setdefault("chromadb", types.SimpleNamespace())

from app.rag import (
    evidence_sufficiency_issues,
    extract_evidence_ids,
    partition_sufficient_records,
    strip_evidence_markers,
)


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


def test_partition_excludes_only_provenance_incomplete_records():
    complete = {"record": {
        "record_id": "r1", "work": "Of Grammatology",
        "document_author": "Jacques Derrida", "text": "Il n'y a pas de hors-texte.",
    }}
    authorless = {"record": {"record_id": "r2", "work": "Anonymous gloss", "text": "Unattributed."}}
    kept, excluded = partition_sufficient_records([authorless, complete])
    assert [item["record"]["record_id"] for item in kept] == ["r1"]
    assert excluded == [{"record_id": "r2", "missing": "document_author, inline_citation"}]
