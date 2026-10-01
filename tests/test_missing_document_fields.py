# Copyright 2026 Aaron John Schlosser, PhD.
"""Document fields detection missed on source load can be supplied before segmentation, and records say so."""
import sys
import types
from pathlib import Path

import pytest

sys.modules.setdefault("chromadb", types.SimpleNamespace())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app.corpus_manifest_workflow import _validated_document_metadata  # noqa: E402
from app.corpus_segmentation import _apply_manifest_metadata  # noqa: E402
from app.field_assertions import current_assertion_by_name  # noqa: E402


def test_supplied_document_fields_are_validated_and_blanks_dropped():
    assert _validated_document_metadata({"document_author": " Jane Author ", "translator": "  ", "publication_year": "1967"}) == {
        "document_author": "Jane Author", "publication_year": "1967",
    }
    assert _validated_document_metadata(None) == {}
    with pytest.raises(ValueError, match="shoe_size"):
        _validated_document_metadata({"shoe_size": "44"})
    with pytest.raises(ValueError):
        _validated_document_metadata({"document_is_translation": "perhaps"})
    with pytest.raises(ValueError):
        _validated_document_metadata(["document_author"])


def test_records_inherit_supplied_values_and_record_their_origin():
    manifest = {
        "title": "De la grammatologie",
        "document_author": "Jane Author",
        "reviewer_supplied": {"document_author": "Jane Author"},
    }
    record = {"record_id": "r1", "text": "Le texte précède le commentaire."}
    _apply_manifest_metadata(record, manifest)
    assert record["document_author"] == "Jane Author"
    author = current_assertion_by_name(record, "document_author")
    assert "supplied by the reviewer" in author.reason
    # A detected value carries no reviewer origin.
    assert "supplied by the reviewer" not in current_assertion_by_name(record, "work").reason
