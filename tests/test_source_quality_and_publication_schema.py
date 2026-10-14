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

"""Source-quality gate and publication schema.

Why: corrupted PDF text must stop enrichment; published JSONL must be namespaced,
Unicode-safe, and use only allowed vocabulary.
How: pure functions and small dicts; no LLM or disk.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import corpus_builder as cb


def test_source_quality_blocks_corruption_not_unicode():
    """Real Unicode passes the quality gate; replacement characters do not.

    Healthy text (accents, Greek, CJK) is valid for enrichment. OCR text with the
    Unicode replacement character makes the page a blocking page (page 2).
    Why: enriching garbled text would create confident but meaningless metadata.
    """
    healthy = [{"page": 1, "text": "Hélène Cixous · Édouard Glissant · différance · Łódź · Ελληνικά · 東京", "extraction_method": "native"}]
    report = cb.page_source_quality_report(healthy)
    assert report["valid_for_enrichment"] is True
    assert report["blocking_pages"] == []
    damaged = [{"page": 2, "text": "corrupt � � source text", "extraction_method": "ocr"}]
    report = cb.page_source_quality_report(damaged)
    assert report["valid_for_enrichment"] is False
    assert report["blocking_pages"] == [2]


def test_publication_schema_is_namespaced_unicode_safe_and_enum_valid():
    """A valid public record has no errors; an invented region type is rejected.

    The record carries build details under corpus_build_details, non-ASCII text, and
    allowed enum values. Changing region_type to "invented" must produce an error
    naming region_type.
    """
    public = {
        "record_id": "rec-1",
        "text": "Édouard Glissant writes of relation — 東京",
        "source_document_id": "source-1",
        "source_block_ids": ["p001-b001"],
        "source_spans": [{"source_document_id": "source-1", "block_id": "p001-b001"}],
        "region_type": cb.REGION_TYPES[0],
        "discourse_role": cb.DISCOURSE_ROLES[0],
        "primary_text": True,
        "corpus_build_details": {
            "build_id": "build-1", "publication_id": "publication-1", "published_at": "2026-09-17T00:00:00Z",
            "app_version": "0.60.0", "schema_version": cb.SCHEMA_VERSION,
            "publication_schema_version": cb.PUBLICATION_SCHEMA_VERSION,
            "profile_id": cb.PROFILE_VERSION, "source_sha256": "abc",
        },
    }
    assert cb.validate_publication_record(public) == []
    assert "東京" in json.dumps(public, ensure_ascii=False)
    public["region_type"] = "invented"
    assert any("region_type" in error for error in cb.validate_publication_record(public))


def test_unreviewed_publication_quarantines_non_boolean_primary_text_without_losing_provenance():
    """A malformed classification must not block as-is publication or become a bool."""
    from app.corpus_publication import (
        mark_unreviewed_publication,
        serialize_public_record,
        validate_publication_record,
    )
    from app.field_assertions import current_assertion_by_name

    for invalid_value in ("false", "true", "not detected", 0, 1, [], {"answer": False}):
        record = {
            "record_id": "sodome-et-gomorrhe-00012",
            "record_revision": 1,
            "source_document_id": "source-1",
            "source_spans": [{"source_document_id": "source-1", "block_id": "b1"}],
            "text": "A passage preserved verbatim.",
            "region_type": "main_text",
            "primary_text": invalid_value,
            "discourse_role": "analysis",
            "accepted": False,
            "needs_review": True,
        }
        snapshots, unreviewed_count, accepted_fields = mark_unreviewed_publication([record])
        snapshot = snapshots[0]
        published = serialize_public_record(snapshot)

        assert unreviewed_count == 1
        assert accepted_fields == 0
        assert snapshot["publication_review_status"] == "unreviewed_suggestion"
        assert published.get("primary_text") is None
        assert validate_publication_record(published) == []
        assertion = current_assertion_by_name(snapshot, "primary_text")
        assert assertion is not None
        assert assertion.value is None and assertion.value_status == "invalid"
        assert assertion.authority_status == "unreviewed"
        assert assertion.legacy_metadata["publication_validation"]["candidate_value"] == invalid_value
        # The original proposal remains recoverable from assertion history.
        history = snapshot["field_assertions"][assertion.field_id]
        if assertion.supersedes_assertion_id:
            assert any(
                entry["assertion_id"] == assertion.supersedes_assertion_id
                and entry["value"] == invalid_value
                for entry in history
            )
        assert record["primary_text"] == invalid_value
        assert "field_assertions" not in record


def test_unreviewed_publication_preserves_boolean_false_and_reviewed_fields():
    """False is a valid boolean, not an unresolved or missing classification."""
    from app.corpus_publication import (
        mark_unreviewed_publication,
        serialize_public_record,
    )
    from app.field_assertions import current_assertion_by_name

    record = {
        "record_id": "r-false",
        "record_revision": 1,
        "source_document_id": "source-1",
        "source_spans": [{"source_document_id": "source-1", "block_id": "b1"}],
        "text": "A note.",
        "region_type": "notes",
        "primary_text": False,
        "discourse_role": "commentary",
        "accepted": True,
        "needs_review": False,
        "metadata_field_status": {"primary_text": {"status": "human_confirmed", "method": "human_review"}},
    }
    snapshots, unreviewed_count, accepted_fields = mark_unreviewed_publication([record])
    published = serialize_public_record(snapshots[0])
    assert published["primary_text"] is False
    assert unreviewed_count == 0 and accepted_fields == 0
    assert snapshots[0]["publication_review_status"] == "reviewer_accepted"
    assert current_assertion_by_name(snapshots[0], "primary_text").authority_status == "human_confirmed"


def test_autonomous_publication_never_substitutes_unsupported_controlled_vocabulary():
    """The same safeguard applies to invalid core enums without inventing values."""
    from app.corpus_publication import (
        mark_unreviewed_publication,
        serialize_public_record,
        validate_publication_record,
    )
    from app.field_assertions import current_assertion_by_name

    record = {
        "record_id": "r-invalid-enums",
        "record_revision": 1,
        "source_document_id": "source-1",
        "source_spans": [{"source_document_id": "source-1", "block_id": "b1"}],
        "text": "Source text.",
        "region_type": "unrecognized-region",
        "primary_text": True,
        "discourse_role": "unrecognized-role",
        "accepted": False,
        "needs_review": True,
    }
    [snapshot], _, _ = mark_unreviewed_publication([record])
    public = serialize_public_record(snapshot)
    assert public.get("region_type") is None and public.get("discourse_role") is None
    assert public["primary_text"] is True
    assert validate_publication_record(public) == []
    for field in ("region_type", "discourse_role"):
        current = current_assertion_by_name(snapshot, field)
        assert current.value_status == "invalid"
        assert current.legacy_metadata["publication_validation"]["candidate_value"] == record[field]
