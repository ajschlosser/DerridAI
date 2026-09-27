# Copyright 2026 Aaron John Schlosser, PhD.
"""Locale scoping of RAG candidates must not drop records with no language."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app.rag import _scope_rag_candidates  # noqa: E402


def _row(language):
    record = {"record_id": "r"}
    if language is not None:
        record["document_language"] = language
    return {"record": record}


def test_records_without_language_survive_locale_scope():
    rows = [_row(None), _row("fr"), _row("en")]
    kept = _scope_rag_candidates(rows, {"collection_role": "source"}, {"fr"})
    assert rows[0] in kept and rows[1] in kept and rows[2] not in kept
