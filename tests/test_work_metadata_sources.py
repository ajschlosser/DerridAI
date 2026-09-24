# Copyright 2026 Aaron John Schlosser, PhD.
"""Regression coverage for source-aware Works metadata enrichment."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.work_metadata_sources import (  # noqa: E402
    applicable_fields_for,
    canonical_source_type,
    catalogue_sources_for,
    source_types_for_metadata,
)


def test_source_type_aliases_are_canonical() -> None:
    assert canonical_source_type("journal article") == "journal_article"
    assert canonical_source_type("podcast") == "audio"
    assert canonical_source_type("unknown-format") == "unknown"


def test_source_types_preserve_mixed_scopes() -> None:
    assert source_types_for_metadata({"source_types": ["book", "audio", "book"]}) == [
        "book",
        "audio",
    ]


def test_applicable_fields_do_not_offer_book_identifiers_for_audio() -> None:
    fields = applicable_fields_for("audio")
    assert "document_title" in fields
    assert "isbn" not in fields
    assert "pages" not in fields


def test_catalogue_sources_follow_source_type() -> None:
    assert catalogue_sources_for("journal_article")[0] == "Crossref"
    assert catalogue_sources_for("image") == ["Embedded source metadata"]
