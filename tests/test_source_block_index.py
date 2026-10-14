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

"""Selected source reads preserve JSONL identity, ordering and file-version invalidation."""

from __future__ import annotations

import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from app import source_block_index as index


def write_blocks(path, rows):
    path.write_bytes(b"\r\n" + b"".join(
        (json.dumps(row, ensure_ascii=False) + "\r\n").encode("utf-8") for row in rows
    ))


@pytest.mark.parametrize("size", [1000, 10000])
def test_warm_selection_reads_only_selected_rows(tmp_path, monkeypatch, size):
    path = tmp_path / "source.blocks.jsonl"
    rows = [{"block_id": f"b{i}", "text": f"Source {i}: \u00e9", "printed_page_label": str(i)} for i in range(size)]
    write_blocks(path, rows)
    assert index.load_selected_blocks(path, ["b0"]) == [rows[0]]
    read = index._read_indexed_block
    lengths = []

    def counted(handle, offset, length):
        lengths.append(length)
        return read(handle, offset, length)

    monkeypatch.setattr(index, "_read_indexed_block", counted)
    assert index.load_selected_blocks(path, ["b9", "missing", "b2", "b9"]) == [rows[9], rows[2]]
    assert len(lengths) == 2
    assert sum(lengths) == sum(len((json.dumps(row, ensure_ascii=False) + "\r\n").encode("utf-8")) for row in (rows[9], rows[2]))


def test_replacement_and_in_place_changes_invalidate_existing_index(tmp_path):
    path = tmp_path / "source.blocks.jsonl"
    write_blocks(path, [{"block_id": "b1", "text": "old"}, {"block_id": "retired", "text": "gone"}])
    assert index.load_selected_blocks(path, ["b1"])[0]["text"] == "old"
    replacement = tmp_path / "replacement.jsonl"
    write_blocks(replacement, [{"block_id": "b1", "text": "new", "printed_page_label": "iv"}])
    os.replace(replacement, path)
    assert index.load_selected_blocks(path, ["retired", "b1"]) == [
        {"block_id": "b1", "text": "new", "printed_page_label": "iv"},
    ]
    write_blocks(path, [{"block_id": "b1", "text": "now", "printed_page_label": "ix"}])
    os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1_000_000))
    assert index.load_selected_blocks(path, ["b1"])[0]["printed_page_label"] == "ix"


def test_empty_selection_and_missing_source_are_explicit(tmp_path):
    missing = tmp_path / "missing.jsonl"
    assert index.load_selected_blocks(missing, []) == []
    assert not missing.with_suffix(".index.sqlite3").exists()
    with pytest.raises(FileNotFoundError):
        index.load_selected_blocks(missing, ["b1"])


def test_duplicate_ids_match_full_projection_and_assets_remain_isolated(tmp_path):
    one, two = tmp_path / "one.jsonl", tmp_path / "two.jsonl"
    write_blocks(one, [{"block_id": "b1", "text": "first"}, {"block_id": "b1", "text": "last"}])
    write_blocks(two, [{"block_id": "b1", "text": "other document"}])
    assert index.load_selected_blocks(one, ["b1"]) == [{"block_id": "b1", "text": "last"}]
    assert index.load_selected_blocks(two, ["b1"]) == [{"block_id": "b1", "text": "other document"}]


def test_failed_rebuild_rolls_back_and_repair_retries(tmp_path):
    path = tmp_path / "source.jsonl"
    write_blocks(path, [{"block_id": "b1", "text": "old"}])
    index.load_selected_blocks(path, ["b1"])
    path.write_bytes(b'{"block_id":"b2"}\n{broken\n')
    with pytest.raises(json.JSONDecodeError):
        index.load_selected_blocks(path, ["b2"])
    with sqlite3.connect(path.with_suffix(".index.sqlite3")) as connection:
        assert connection.execute("SELECT block_id FROM source_offsets").fetchall() == [("b1",)]
    write_blocks(path, [{"block_id": "b2", "text": "repaired"}])
    assert index.load_selected_blocks(path, ["b1", "b2"]) == [{"block_id": "b2", "text": "repaired"}]


def test_concurrent_cold_readers_and_bounded_query_batches(tmp_path, monkeypatch):
    path = tmp_path / "source.jsonl"
    rows = [{"block_id": f"b{i}", "text": str(i)} for i in range(1000)]
    write_blocks(path, rows)
    monkeypatch.setattr(index, "QUERY_BATCH_SIZE", 3)
    wanted = [f"b{i}" for i in range(10)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: index.load_selected_blocks(path, wanted), range(2)))
    assert results == [rows[:10], rows[:10]]


def test_lookup_identity_corruption_fails_visibly(tmp_path):
    path = tmp_path / "source.jsonl"
    write_blocks(path, [{"block_id": "b1"}, {"block_id": "b2"}])
    index.load_selected_blocks(path, ["b1"])
    with sqlite3.connect(path.with_suffix(".index.sqlite3")) as connection:
        offset, length = connection.execute(
            "SELECT byte_offset, byte_length FROM source_offsets WHERE block_id='b2'",
        ).fetchone()
        connection.execute(
            "UPDATE source_offsets SET byte_offset=?, byte_length=? WHERE block_id='b1'", (offset, length),
        )
    with pytest.raises(RuntimeError, match="authoritative source identity"):
        index.load_selected_blocks(path, ["b1"])


def test_source_change_during_selected_read_fails_visibly(tmp_path, monkeypatch):
    path = tmp_path / "source.jsonl"
    write_blocks(path, [{"block_id": "b1", "text": "old"}])
    index.load_selected_blocks(path, ["b1"])
    read = index._read_indexed_block

    def changed(handle, offset, length):
        block = read(handle, offset, length)
        os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1_000_000))
        return block

    monkeypatch.setattr(index, "_read_indexed_block", changed)
    with pytest.raises(RuntimeError, match="changed during selected lookup"):
        index.load_selected_blocks(path, ["b1"])
