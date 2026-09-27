# Copyright 2026 Aaron John Schlosser, PhD.
"""Source-unit reconciliation for human structural record edits."""

from __future__ import annotations

import json
from pathlib import Path

from test_boundary_suspects_and_undo import install


def _manager(tmp_path: Path):
    from app import corpus_builder as cb

    repo, build = install(tmp_path)
    return repo, build["build_id"], cb.PdfCorpusBuildManager(repo, max_workers=1)


def _active(repo, build_id: str) -> dict[str, dict]:
    return {
        str(row["source_unit_id"]): row
        for row in repo.load_source_units(build_id)
        if row.get("active")
    }


def test_split_inside_unit_retires_parent_and_mints_whole_replacements(tmp_path: Path):
    repo, build_id, manager = _manager(tmp_path)
    before = _active(repo, build_id)
    result = manager.split(build_id, "r2", offset=10, expected_revision=1)
    after = _active(repo, build_id)
    ids = [str(row["source_unit_ids"][0]) for row in result["records"]]
    assert len(ids) == 2 and len(set(ids)) == 2
    assert "b2" not in after
    assert all(after[unit_id]["parent_unit_ids"] == ["b2"] for unit_id in ids)
    assert all(after[unit_id]["text_hash"] for unit_id in ids)
    retired = {str(row["source_unit_id"]): row for row in repo.load_source_units(build_id) if not row.get("active")}
    assert retired["b2"]["successor_unit_ids"] == ids
    assert before["b2"]["active"] is True


def test_split_between_units_reuses_units_unchanged(tmp_path: Path):
    repo, build_id, manager = _manager(tmp_path)
    rows = repo.load_records(build_id)
    rows[1]["text"] = rows[1]["text"] + "\n\n" + rows[2]["text"]
    rows[1]["text_length"] = len(rows[1]["text"])
    rows[1]["source_block_ids"] = ["b2", "b3"]
    rows[1]["source_unit_ids"] = ["b2", "b3"]
    rows.pop(2)
    repo.save_records(build_id, rows)
    original = {key: value["text_hash"] for key, value in _active(repo, build_id).items()}
    result = manager.split(build_id, "r2", offset=len("Misplaced beginning. Proper current text."), expected_revision=1)
    assert [row["source_unit_ids"] for row in result["records"]] == [["b2"], ["b3"]]
    active = _active(repo, build_id)
    assert {key: active[key]["text_hash"] for key in ("b2", "b3")} == {key: original[key] for key in ("b2", "b3")}


def test_merge_reuses_units_and_does_not_retire_them(tmp_path: Path):
    repo, build_id, manager = _manager(tmp_path)
    original = _active(repo, build_id)
    result = manager.merge(build_id, "r2", "next", expected_revision=1)
    assert result["record"]["source_unit_ids"] == ["b2", "b3"]
    active = _active(repo, build_id)
    assert set(active) == set(original)
    assert all(active[key]["text_hash"] == original[key]["text_hash"] for key in original)


def test_unsafe_neighbor_boundary_keeps_fragment_unit_separate(tmp_path: Path):
    repo, build_id, manager = _manager(tmp_path)
    blocks = repo.load_blocks("a")
    blocks[0]["type"] = "heading"
    with repo.asset_blocks_path("a").open("w", encoding="utf-8") as handle:
        for block in blocks:
            handle.write(json.dumps(block) + "\n")
    target = repo.load_records(build_id)[1]
    cut = target["text"].index("Proper")
    result = manager.create_from_selection(build_id, "r2", cut, len(target["text"]), left="merge_prior", expected_revision=1)
    assert len(result["record"]["source_unit_ids"]) == 1
    rows = repo.load_records(build_id)
    assert len(rows[0]["source_unit_ids"]) == 2
    assert len(set(rows[0]["source_unit_ids"])) == 2


def test_create_selection_undo_redo_restores_records_and_units(tmp_path: Path):
    repo, build_id, manager = _manager(tmp_path)
    target = repo.load_records(build_id)[1]
    cut = target["text"].index("Proper")
    before_records = repo.load_records(build_id)
    before_units = repo.load_source_units(build_id)
    manager.create_from_selection(build_id, "r2", 0, cut, right="merge_next", expected_revision=1)
    manager.undo_last_review_edit(build_id)
    restored_records = repo.load_records(build_id)
    assert [(row["record_id"], row["text"], row["source_block_ids"]) for row in restored_records] == [
        (row["record_id"], row["text"], row["source_block_ids"]) for row in before_records
    ]
    restored_units = repo.load_source_units(build_id)
    unit_state = lambda rows: [
        (
            row["source_unit_id"],
            row["text_hash"],
            row.get("active"),
            row.get("parent_unit_ids"),
            row.get("successor_unit_ids"),
            row.get("consumed_ranges"),
        )
        for row in rows
    ]
    assert unit_state(restored_units) == unit_state(before_units)
    manager.redo_last_review_edit(build_id)
    assert repo.load_records(build_id)[2]["text"].startswith("Proper current text.")
    assert all(row.get("active") for row in _active(repo, build_id).values())


def test_structural_units_conserve_text(tmp_path: Path):
    repo, build_id, manager = _manager(tmp_path)
    before = "".join(row["text"] for row in repo.load_records(build_id))
    manager.split(build_id, "r2", offset=10, expected_revision=1)
    after = "".join(row["text"] for row in repo.load_records(build_id))
    assert "".join(before.split()) == "".join(after.split())


def test_unambiguous_evidence_is_remapped_to_one_successor():
    from app.corpus_record_restructure import remap_evidence_bindings

    retiring = [{
        "record_id": "old",
        "metadata_evidence": {
            "stance": {"block_ids": ["u1"], "reviewed_by": "human"},
        },
    }]
    created = [{"record_id": "new", "source_unit_ids": ["u2"]}]
    units = [{
        "source_unit_id": "u1",
        "active": False,
        "successor_unit_ids": ["u2"],
    }, {
        "source_unit_id": "u2",
        "active": True,
        "parent_unit_ids": ["u1"],
    }]
    remapped, pending = remap_evidence_bindings(retiring, created, units)
    assert not pending
    assert remapped["0"]["stance"]["block_ids"] == ["u2"]
    assert remapped["0"]["stance"]["remapped_from_record_id"] == "old"


def test_ambiguous_evidence_remap_is_not_auto_bound():
    from app.corpus_record_restructure import remap_evidence_bindings

    retiring = [{
        "record_id": "old",
        "metadata_evidence": {"stance": {"block_ids": ["u1"]}},
    }]
    created = [
        {"record_id": "left", "source_unit_ids": ["u2"]},
        {"record_id": "right", "source_unit_ids": ["u3"]},
    ]
    units = [{
        "source_unit_id": "u1",
        "active": False,
        "successor_unit_ids": ["u2", "u3"],
    }, {
        "source_unit_id": "u2", "active": True,
    }, {
        "source_unit_id": "u3", "active": True,
    }]
    remapped, pending = remap_evidence_bindings(retiring, created, units)
    assert not remapped
    assert pending[0]["parent_record_id"] == "old"
