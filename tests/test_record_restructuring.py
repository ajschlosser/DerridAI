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

"""Split, merge and create-from-selection retire Records and mint new IDs (SPECIFICATION: Record identity)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_boundary_suspects_and_undo import cb, install  # noqa: E402


def _manager(tmp_path):
    repo, build = install(tmp_path)
    return repo, build["build_id"], cb.PdfCorpusBuildManager(repo, max_workers=1)


def _squash(rows):
    return "".join("".join(str(row["text"]).split()) for row in rows)


def test_split_retires_parent_and_mints_two_new_ids(tmp_path):
    repo, bid, manager = _manager(tmp_path)
    before = repo.load_records(bid)
    text = before[1]["text"]
    result = manager.split(bid, "r2", offset=text.index("Proper"), expected_revision=1)
    rows = repo.load_records(bid)
    assert [r["record_id"] for r in rows if r["record_id"] in {"r1", "r3"}] == ["r1", "r3"]
    assert "r2" not in {r["record_id"] for r in rows}
    left, right = result["records"]
    assert left["record_id"] != right["record_id"] and "r2" not in {left["record_id"], right["record_id"]}
    assert left["text"] == "Misplaced beginning." and right["text"] == "Proper current text."
    assert left["lineage"]["parent_record_ids"] == ["r2"] and left["lineage"]["operation"] == "split"
    assert _squash(rows) == _squash(before)
    retired = manager.retired_records(bid)
    assert [t["record_id"] for t in retired] == ["r2"]
    assert set(retired[0]["successor_record_ids"]) == {left["record_id"], right["record_id"]}
    assert retired[0]["record"]["text"] == text


def test_split_returns_records_unreviewed_even_if_parent_was_accepted(tmp_path):
    repo, bid, manager = _manager(tmp_path)
    rows = repo.load_records(bid)
    rows[1].update(accepted=True, review_disposition="accepted")
    repo.save_records(bid, rows)
    result = manager.split(bid, "r2", offset=10, expected_revision=1)
    assert all(not r["accepted"] and r["needs_review"] and r["record_revision"] == 1 for r in result["records"])


def test_merge_retires_both_and_mints_one(tmp_path):
    repo, bid, manager = _manager(tmp_path)
    result = manager.merge(bid, "r2", "next", expected_revision=1)
    rows = repo.load_records(bid)
    assert len(rows) == 2
    merged = result["record"]
    assert merged["record_id"] not in {"r2", "r3"}
    assert merged["text"] == "Misplaced beginning. Proper current text.\n\nNext beginning."
    assert merged["source_block_ids"] == ["b2", "b3"]
    assert {t["record_id"] for t in manager.retired_records(bid)} == {"r2", "r3"}


def test_create_from_selection_distinct_makes_three_new_records(tmp_path):
    repo, bid, manager = _manager(tmp_path)
    text = repo.load_records(bid)[1]["text"]
    start = text.index("beginning.")
    end = text.index("Proper")
    result = manager.create_from_selection(bid, "r2", start, end, expected_revision=1)
    assert len(result["records"]) == 3
    assert result["record"]["text"] == "beginning."
    rows = repo.load_records(bid)
    assert len(rows) == 5 and rows[0]["record_id"] == "r1" and rows[-1]["record_id"] == "r3"
    assert len({r["record_id"] for r in rows}) == 5


def test_create_from_selection_can_join_neighbours(tmp_path):
    repo, bid, manager = _manager(tmp_path)
    text = repo.load_records(bid)[1]["text"]
    start = text.index("beginning.")
    end = text.index("Proper")
    result = manager.create_from_selection(bid, "r2", start, end, "merge_prior", "merge_next", expected_revision=1)
    texts = [r["text"] for r in repo.load_records(bid)]
    assert texts == ["Previous ending.\n\nMisplaced", "beginning.", "Proper current text.\n\nNext beginning."]
    assert {t["record_id"] for t in manager.retired_records(bid)} == {"r1", "r2", "r3"}
    assert result["retired_record_ids"] == ["r1", "r2", "r3"]


def test_retired_ids_are_never_reused_and_undo_restores_parents(tmp_path):
    repo, bid, manager = _manager(tmp_path)
    first = manager.split(bid, "r2", offset=10, expected_revision=1)
    manager.merge(bid, first["records"][0]["record_id"], "next", expected_revision=1)
    ids = {t["record_id"] for t in manager.retired_records(bid)}
    assert {"r2"} <= ids and len(ids) == 3
    live = {r["record_id"] for r in repo.load_records(bid)}
    assert not live & ids
    manager.undo_last_review_edit(bid)
    manager.undo_last_review_edit(bid)
    assert "r2" in {r["record_id"] for r in repo.load_records(bid)}
    assert "r2" not in {t["record_id"] for t in manager.retired_records(bid)}


@pytest.mark.parametrize("args", [
    dict(start=0, end=10_000),
    dict(start=5, end=5),
    dict(start=0, end=41),
])
def test_create_from_selection_rejects_bad_selections(tmp_path, args):
    repo, bid, manager = _manager(tmp_path)
    with pytest.raises(ValueError):
        manager.create_from_selection(bid, "r2", expected_revision=1, **args)


def test_selection_cannot_merge_into_missing_neighbour(tmp_path):
    repo, bid, manager = _manager(tmp_path)
    with pytest.raises(ValueError):
        manager.create_from_selection(bid, "r1", 3, 6, "merge_prior", expected_revision=1)


def test_stale_revision_is_refused(tmp_path):
    repo, bid, manager = _manager(tmp_path)
    with pytest.raises(ValueError):
        manager.split(bid, "r2", offset=10, expected_revision=9)


def test_sourceunit_topology_does_not_duplicate_a_split_legacy_block():
    """Two active SourceUnit fragments may share one immutable extraction root."""
    blocks = [
        {
            "block_id": "b1",
            "page": 1,
            "bbox": [0, 0, 1, 1],
            "type": "paragraph",
            "text": "Alpha Beta",
        }
    ]
    units = [
        {
            **blocks[0],
            "source_unit_id": "b1",
            "unit_id": "b1",
            "source_block_ids": ["b1"],
            "text": "Alpha Beta",
            "active": False,
        },
        {
            **blocks[0],
            "source_unit_id": "u-left",
            "unit_id": "u-left",
            "source_block_ids": ["b1"],
            "parent_unit_ids": ["b1"],
            "consumed_ranges": [{"unit_id": "b1", "start": 0, "end": 5}],
            "text": "Alpha",
            "active": True,
        },
        {
            **blocks[0],
            "source_unit_id": "u-right",
            "unit_id": "u-right",
            "source_block_ids": ["b1"],
            "parent_unit_ids": ["b1"],
            "consumed_ranges": [{"unit_id": "b1", "start": 6, "end": 10}],
            "text": "Beta",
            "active": True,
        },
    ]
    records = [
        {
            "record_id": "r-left",
            "text": "Alpha",
            "source_extracted_text": "Alpha",
            "source_unit_ids": ["u-left"],
            "source_block_ids": ["b1"],
            "pdf_pages": [1],
            "page_start": None,
            "page_end": None,
            "review_disposition": "rejected",
        },
        {
            "record_id": "r-right",
            "text": "Beta",
            "source_extracted_text": "Beta",
            "source_unit_ids": ["u-right"],
            "source_block_ids": ["b1"],
            "pdf_pages": [1],
            "page_start": None,
            "page_end": None,
            "review_disposition": "rejected",
        },
    ]

    validation = cb.PdfCorpusBuildManager.validate_records(
        blocks,
        records,
        {},
        source_units=units,
    )

    assert validation["source_valid"] is True
    assert validation["missing_block_ids"] == []
    assert validation["missing_source_unit_ids"] == []
    assert validation["duplicate_block_ids"] == []
    assert validation["text_fidelity_errors"] == []
    assert validation["source_order_errors"] == []
    assert validation["source_conservation_errors"] == []


def test_sourceunit_root_resolution_crosses_retired_generations():
    """A current unit may descend through retired replacement units to one extraction root."""
    blocks = [{"block_id": "b1", "page": 1, "type": "paragraph", "text": "Alpha"}]
    units = [
        {**blocks[0], "source_unit_id": "b1", "unit_id": "b1", "source_block_ids": ["b1"], "active": False},
        {**blocks[0], "source_unit_id": "u1", "unit_id": "u1", "source_block_ids": ["b1"], "parent_unit_ids": ["b1"], "text": "Alpha", "active": False},
        {**blocks[0], "source_unit_id": "u2", "unit_id": "u2", "source_block_ids": ["b1"], "parent_unit_ids": ["u1"], "text": "Alpha", "active": True},
    ]
    records = [{
        "record_id": "r1",
        "text": "Alpha",
        "source_extracted_text": "Alpha",
        "source_unit_ids": ["u2"],
        "source_block_ids": ["b1"],
        "pdf_pages": [1],
        "page_start": None,
        "page_end": None,
        "review_disposition": "rejected",
    }]
    validation = cb.PdfCorpusBuildManager.validate_records(
        blocks, records, {}, source_units=units
    )
    assert validation["source_valid"] is True
    assert validation["missing_block_ids"] == []


def test_duplicate_active_sourceunit_ownership_is_blocking():
    blocks = [{"block_id": "b1", "page": 1, "type": "paragraph", "text": "Alpha"}]
    units = [{
        **blocks[0],
        "source_unit_id": "u1",
        "unit_id": "u1",
        "source_block_ids": ["b1"],
        "parent_unit_ids": ["b1"],
        "text": "Alpha",
        "active": True,
    }]
    base = {
        "text": "Alpha",
        "source_extracted_text": "Alpha",
        "source_unit_ids": ["u1"],
        "source_block_ids": ["b1"],
        "pdf_pages": [1],
        "page_start": None,
        "page_end": None,
        "review_disposition": "rejected",
    }
    validation = cb.PdfCorpusBuildManager.validate_records(
        blocks,
        [{**base, "record_id": "r1"}, {**base, "record_id": "r2"}],
        {},
        source_units=units,
    )
    assert validation["source_valid"] is False
    assert validation["duplicate_source_unit_ids"] == ["u1"]
    assert any(
        issue["code"] == "source_duplicate" and issue["field"] == "u1"
        for issue in validation["validation_issues"]
    )


def test_inactive_sourceunit_reference_is_blocking():
    blocks = [{"block_id": "b1", "page": 1, "type": "paragraph", "text": "Alpha"}]
    units = [{
        **blocks[0],
        "source_unit_id": "u-old",
        "unit_id": "u-old",
        "source_block_ids": ["b1"],
        "parent_unit_ids": ["b1"],
        "text": "Alpha",
        "active": False,
    }]
    records = [{
        "record_id": "r1",
        "text": "Alpha",
        "source_extracted_text": "Alpha",
        "source_unit_ids": ["u-old"],
        "source_block_ids": ["b1"],
        "pdf_pages": [1],
        "page_start": None,
        "page_end": None,
        "review_disposition": "rejected",
    }]
    validation = cb.PdfCorpusBuildManager.validate_records(
        blocks, records, {}, source_units=units
    )
    assert validation["source_valid"] is False
    assert validation["unknown_source_unit_ids"] == ["u-old"]
    assert validation["source_reference_errors"][0]["field"] == "u-old"


def test_reconciliation_repairs_retired_sourceunit_to_conserving_descendants():
    from app.corpus_record_restructure import repair_record_source_topology

    units = [
        {
            "source_unit_id": "u-old",
            "unit_id": "u-old",
            "source_block_ids": ["b1"],
            "text": "Alpha Beta",
            "active": False,
        },
        {
            "source_unit_id": "u-left",
            "unit_id": "u-left",
            "source_block_ids": ["b1"],
            "parent_unit_ids": ["u-old"],
            "text": "Alpha",
            "active": True,
        },
        {
            "source_unit_id": "u-right",
            "unit_id": "u-right",
            "source_block_ids": ["b1"],
            "parent_unit_ids": ["u-old"],
            "text": "Beta",
            "active": True,
        },
    ]
    records = [{
        "record_id": "r1",
        "source_unit_ids": ["u-old"],
        "source_block_ids": ["b1"],
        "source_extracted_text": "Alpha Beta",
        "text": "Alpha Beta",
    }]

    events = repair_record_source_topology(records, units)

    assert records[0]["source_unit_ids"] == ["u-left", "u-right"]
    assert events[0]["method"] == "active_descendant_lineage"
    history = records[0]["source_topology_reconciliation_history"]
    assert history[-1]["previous_source_unit_ids"] == ["u-old"]
    assert history[-1]["source_unit_ids"] == ["u-left", "u-right"]
    assert history[-1]["source_text_conserved"] is True


def test_reconciliation_does_not_guess_ambiguous_sourceunit_ownership():
    from app.corpus_record_restructure import repair_record_source_topology

    units = [
        {
            "source_unit_id": "u-old",
            "unit_id": "u-old",
            "source_block_ids": ["b1"],
            "text": "Alpha",
            "active": False,
        },
        {
            "source_unit_id": "u-new",
            "unit_id": "u-new",
            "source_block_ids": ["b1"],
            "parent_unit_ids": ["u-old"],
            "text": "Alpha",
            "active": True,
        },
    ]
    records = [
        {
            "record_id": "r1",
            "source_unit_ids": ["u-old"],
            "source_block_ids": ["b1"],
            "source_extracted_text": "Alpha",
            "text": "Alpha",
        },
        {
            "record_id": "r2",
            "source_unit_ids": ["u-old"],
            "source_block_ids": ["b1"],
            "source_extracted_text": "Alpha",
            "text": "Alpha",
        },
    ]

    events = repair_record_source_topology(records, units)

    assert events == []
    assert records[0]["source_unit_ids"] == ["u-old"]
    assert records[1]["source_unit_ids"] == ["u-old"]


def test_reconciliation_can_recover_unique_projection_when_stale_unit_is_missing():
    from app.corpus_record_restructure import repair_record_source_topology

    units = [
        {
            "source_unit_id": "u-left",
            "unit_id": "u-left",
            "source_block_ids": ["b1"],
            "text": "Alpha",
            "active": True,
        },
        {
            "source_unit_id": "u-right",
            "unit_id": "u-right",
            "source_block_ids": ["b1"],
            "text": "Beta",
            "active": True,
        },
    ]
    records = [{
        "record_id": "r1",
        "source_unit_ids": ["missing-old-unit"],
        "source_block_ids": ["b1"],
        "source_extracted_text": "Alpha Beta",
        "text": "Reviewed wording may differ",
    }]

    events = repair_record_source_topology(records, units)

    assert records[0]["source_unit_ids"] == ["u-left", "u-right"]
    assert events[0]["method"] == "unique_source_projection_match"


def test_reconciliation_resolves_duplicate_active_ownership_when_projection_is_unique():
    from app.corpus_record_restructure import repair_record_source_topology

    units = [
        {
            "source_unit_id": "u-left",
            "unit_id": "u-left",
            "source_block_ids": ["b1"],
            "text": "Alpha",
            "active": True,
        },
        {
            "source_unit_id": "u-right",
            "unit_id": "u-right",
            "source_block_ids": ["b1"],
            "text": "Beta",
            "active": True,
        },
    ]
    records = [
        {
            "record_id": "r1",
            "source_unit_ids": ["u-left"],
            "source_block_ids": ["b1"],
            "source_extracted_text": "Alpha",
            "text": "Alpha",
        },
        {
            "record_id": "r2",
            "source_unit_ids": ["u-left"],
            "source_block_ids": ["b1"],
            "source_extracted_text": "Beta",
            "text": "Beta",
        },
    ]

    events = repair_record_source_topology(
        records, units, source_block_ids={"b1"}
    )

    assert records[0]["source_unit_ids"] == ["u-left"]
    assert records[1]["source_unit_ids"] == ["u-right"]
    assert [event["record_id"] for event in events] == ["r2"]
    assert events[0]["method"] == "unique_source_projection_match"
    assert events[0]["source_text_conserved"] is True


def test_reconciliation_keeps_duplicate_active_ownership_when_ambiguous():
    from app.corpus_record_restructure import repair_record_source_topology

    units = [
        {
            "source_unit_id": "u1",
            "unit_id": "u1",
            "source_block_ids": ["b1"],
            "text": "Alpha",
            "active": True,
        }
    ]
    records = [
        {
            "record_id": record_id,
            "source_unit_ids": ["u1"],
            "source_block_ids": ["b1"],
            "source_extracted_text": "Alpha",
            "text": "Alpha",
        }
        for record_id in ("r1", "r2")
    ]

    events = repair_record_source_topology(
        records, units, source_block_ids={"b1"}
    )

    assert events == []
    assert [record["source_unit_ids"] for record in records] == [["u1"], ["u1"]]


def test_source_projection_reconciliation_is_audited():
    from app.corpus_record_restructure import synchronize_record_source_projection

    units = [
        {
            "source_unit_id": "u1",
            "unit_id": "u1",
            "source_block_ids": ["b1"],
            "text": "Alpha",
            "active": True,
        }
    ]
    records = [{
        "record_id": "r1",
        "source_unit_ids": ["u1"],
        "source_block_ids": ["b1"],
        "source_extracted_text": "stale projection",
        "text": "Reviewed wording may differ",
    }]

    changed = synchronize_record_source_projection(records, units)

    assert changed == 1
    assert records[0]["source_extracted_text"] == "Alpha"
    history = records[0]["source_projection_reconciliation_history"]
    assert history[-1]["method"] == "derive_from_active_source_units"
    assert history[-1]["source_unit_ids"] == ["u1"]
    assert history[-1]["previous_source_projection_hash"]
    assert history[-1]["source_projection_hash"]
    assert history[-1]["source_text_conserved"] is False

def test_reordered_sourceunits_are_blocking():
    blocks = [
        {"block_id": "b1", "page": 1, "type": "paragraph", "text": "Alpha"},
        {"block_id": "b2", "page": 1, "type": "paragraph", "text": "Beta"},
    ]
    units = [
        {**blocks[0], "source_unit_id": "u1", "unit_id": "u1", "source_block_ids": ["b1"], "parent_unit_ids": ["b1"], "text": "Alpha", "active": True},
        {**blocks[1], "source_unit_id": "u2", "unit_id": "u2", "source_block_ids": ["b2"], "parent_unit_ids": ["b2"], "text": "Beta", "active": True},
    ]
    records = [
        {
            "record_id": "r2",
            "text": "Beta",
            "source_extracted_text": "Beta",
            "source_unit_ids": ["u2"],
            "source_block_ids": ["b2"],
            "pdf_pages": [1],
            "page_start": None,
            "page_end": None,
            "review_disposition": "rejected",
        },
        {
            "record_id": "r1",
            "text": "Alpha",
            "source_extracted_text": "Alpha",
            "source_unit_ids": ["u1"],
            "source_block_ids": ["b1"],
            "pdf_pages": [1],
            "page_start": None,
            "page_end": None,
            "review_disposition": "rejected",
        },
    ]
    validation = cb.PdfCorpusBuildManager.validate_records(
        blocks, records, {}, source_units=units
    )
    assert validation["source_valid"] is False
    assert validation["source_order_errors"]
    assert validation["source_conservation_errors"] == ["corpus"]


def test_timed_sourceunit_locator_mismatch_is_blocking():
    blocks = [{
        "block_id": "b1",
        "locator_kind": "time",
        "start": 10.0,
        "end": 20.0,
        "type": "transcript",
        "text": "Alpha",
    }]
    units = [{
        **blocks[0],
        "source_unit_id": "u1",
        "unit_id": "u1",
        "source_block_ids": ["b1"],
        "parent_unit_ids": ["b1"],
        "start": 20.0,
        "end": 10.0,
        "text": "Alpha",
        "active": True,
    }]
    records = [{
        "record_id": "r1",
        "text": "Alpha",
        "source_extracted_text": "Alpha",
        "source_unit_ids": ["u1"],
        "source_block_ids": ["b1"],
        "review_disposition": "rejected",
    }]
    validation = cb.PdfCorpusBuildManager.validate_records(
        blocks, records, {}, source_units=units
    )
    assert validation["source_valid"] is False
    assert validation["page_mapping_errors"] == ["r1"]


def test_block_bound_evidence_survives_sourceunit_partition():
    blocks = [{"block_id": "b1", "page": 1, "type": "paragraph", "text": "Alpha"}]
    units = [{
        **blocks[0],
        "source_unit_id": "u1",
        "unit_id": "u1",
        "source_block_ids": ["b1"],
        "parent_unit_ids": ["b1"],
        "text": "Alpha",
        "active": True,
    }]
    records = [{
        "record_id": "r1",
        "text": "Alpha",
        "source_extracted_text": "Alpha",
        "source_unit_ids": ["u1"],
        "source_block_ids": ["b1"],
        "pdf_pages": [1],
        "page_start": None,
        "page_end": None,
        "speaker": "Derrida",
        "metadata_evidence": {
            "speaker": {
                "block_ids": ["b1"],
                "confidence": 1.0,
                "reviewed_by": "human",
            }
        },
        "review_disposition": "pending",
    }]
    validation = cb.PdfCorpusBuildManager.validate_records(
        blocks,
        records,
        {"attribution_evidence_fields": ["speaker"], "min_metadata_confidence": 0.65},
        source_units=units,
    )
    assert validation["metadata_evidence_errors"] == []


def test_text_conservation_guard_refuses_lost_or_invented_text():
    from app.corpus_record_restructure import assert_text_conserved

    assert_text_conserved(["a b c"], ["a b", "\n\nc"])
    with pytest.raises(ValueError):
        assert_text_conserved(["a b c"], ["a b"])
    with pytest.raises(ValueError):
        assert_text_conserved(["a b c"], ["a b c d"])
    with pytest.raises(ValueError):
        assert_text_conserved(["a b", "c"], ["c", "a b"])


def test_edited_text_falls_back_to_parent_blocks_instead_of_inventing_provenance():
    from app.corpus_record_restructure import block_ids_for_range

    blocks = {"b1": {"text": "Original wording."}}
    ids, precise = block_ids_for_range("Human corrected wording.", ["b1"], blocks, 0, 5)
    assert ids == ["b1"] and precise is False


def test_split_request_needs_exactly_one_split_point():
    from app.models import PdfCorpusRecordSplit

    with pytest.raises(ValueError):
        PdfCorpusRecordSplit()
    with pytest.raises(ValueError):
        PdfCorpusRecordSplit(after_block_id="b1", offset=3)
    assert PdfCorpusRecordSplit(offset=3).offset == 3


def test_metadata_decision_can_save_value_and_evidence_in_one_call(tmp_path):
    repo, bid, manager = _manager(tmp_path)
    result = manager.metadata_decision(bid, "r2", "speaker", "Derrida", 1, False, ["b2"])
    record = result["record"]
    assert record["speaker"] == "Derrida"
    assert record["metadata_evidence"]["speaker"]["block_ids"] == ["b2"]
    assert record["metadata_evidence"]["speaker"]["reviewed_by"] == "human"


def test_evidence_outside_the_record_is_refused_before_anything_is_saved(tmp_path):
    repo, bid, manager = _manager(tmp_path)
    with pytest.raises(ValueError, match="belong to the selected record"):
        manager.metadata_decision(bid, "r2", "speaker", "Derrida", 1, False, ["b1"])
    row = repo.load_records(bid)[1]
    assert row.get("speaker") in (None, "") and row["record_revision"] == 1


def test_operational_record_keys_never_become_metadata_assertions(tmp_path):
    from app.field_assertions import migrate_record_assertions

    row = {
        "record_id": "r1", "source_document_id": "d", "text": "t",
        "source_spans": [{"source_document_id": "d", "block_id": "b"}],
        "boundary_evidence": {"after_block_id": "b1"}, "lineage": {"operation": "split"},
        "nlp_candidates": {"status": "ok"}, "text_review_source": "human_split", "unit_policy": "sentence",
        "speaker": "Derrida",
    }
    migrate_record_assertions(row)
    names = {a["field_name"] for bucket in row["field_assertions"].values() for a in bucket}
    assert names == {"speaker"}


def test_record_context_returns_neighbours_in_document_order(tmp_path):
    repo, bid, manager = _manager(tmp_path)
    context = repo.record_context(bid, "r2", before=5, after=5)
    assert [r["record_id"] for r in context["before"]] == ["r1"]
    assert [r["record_id"] for r in context["after"]] == ["r3"]
    assert set(context["before"][0]) == {
        "record_id", "record_revision", "source_document_id", "text", "text_length",
        "text_truncated", "record_character_start", "record_character_end",
        "page_start", "page_end", "review_disposition",
    }
    for neighbour in context["before"] + context["after"]:
        original = repo.get_record(bid, neighbour["record_id"])
        assert neighbour["record_revision"] == original.get("record_revision")
        assert neighbour["source_document_id"] == original.get("source_document_id")
        assert neighbour["text"] == original["text"]
        assert neighbour["record_character_start"] == 0
        assert neighbour["record_character_end"] == len(original["text"])
        assert neighbour["text_truncated"] is False
    assert repo.record_context(bid, "r2", before=0, after=0) == {"record_id": "r2", "before": [], "after": [], "truncated": False}
    with pytest.raises(KeyError):
        repo.record_context(bid, "nope")


def test_record_context_is_bounded_by_a_character_budget(tmp_path):
    repo, bid, manager = _manager(tmp_path)
    context = repo.record_context(bid, "r2", before=5, after=5, max_chars=5)
    assert context["truncated"] is True


def test_context_route_reads_from_the_repository(tmp_path, monkeypatch):
    from app.routers import corpus as routes

    repo, bid, manager = _manager(tmp_path)
    monkeypatch.setattr(routes, "pdf_corpus_repository", repo)
    result = routes.get_pdf_corpus_record_context(bid, "r2", before=3, after=3)
    assert [r["record_id"] for r in result["before"]] == ["r1"]
    with pytest.raises(Exception) as info:
        routes.get_pdf_corpus_record_context(bid, "missing", before=1, after=1)
    assert getattr(info.value, "status_code", None) == 404
