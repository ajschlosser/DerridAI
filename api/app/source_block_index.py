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

"""Rebuildable byte-offset lookup over authoritative extracted-source JSONL."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, BinaryIO

QUERY_BATCH_SIZE = 400
INDEX_VERSION = 1


def _signature(path: Path) -> str:
    stat = path.stat()
    return json.dumps([INDEX_VERSION, stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns])


def _read_indexed_block(handle: BinaryIO, offset: int, length: int) -> Any:
    handle.seek(offset)
    return json.loads(handle.read(length))


def load_selected_blocks(path: Path, block_ids: list[str]) -> list[dict[str, Any]]:
    """Seek only requested rows after one transactional, file-version-bound indexing pass."""
    wanted = list(dict.fromkeys(block_ids))
    if not wanted:
        return []
    signature = _signature(path)
    index_path = path.with_suffix(".index.sqlite3")
    with closing(sqlite3.connect(index_path, timeout=30)) as connection, connection:
        connection.execute("CREATE TABLE IF NOT EXISTS source_version (signature TEXT NOT NULL)")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS source_offsets "
            "(block_id TEXT PRIMARY KEY, byte_offset INTEGER NOT NULL, byte_length INTEGER NOT NULL)",
        )
        # Serialize index builders across repository instances/processes.
        connection.execute("BEGIN IMMEDIATE")
        stored = connection.execute("SELECT signature FROM source_version").fetchone()
        if stored is None or stored[0] != signature:
            connection.execute("DELETE FROM source_offsets")
            with path.open("rb") as handle:
                while True:
                    offset = handle.tell()
                    line = handle.readline()
                    if not line:
                        break
                    if not line.strip():
                        continue
                    block = json.loads(line)
                    block_id = str(block.get("block_id") or "") if isinstance(block, dict) else ""
                    if block_id:
                        # Matches the full projection's last-row-wins map.
                        connection.execute(
                            "INSERT OR REPLACE INTO source_offsets VALUES (?, ?, ?)",
                            (block_id, offset, len(line)),
                        )
            if _signature(path) != signature:
                raise RuntimeError("Source blocks changed while building their lookup index")
            connection.execute("DELETE FROM source_version")
            connection.execute("INSERT INTO source_version VALUES (?)", (signature,))
        offsets: dict[str, tuple[int, int]] = {}
        for start in range(0, len(wanted), QUERY_BATCH_SIZE):
            batch = wanted[start:start + QUERY_BATCH_SIZE]
            placeholders = ",".join("?" for _ in batch)
            offsets.update(
                (block_id, (offset, length))
                for block_id, offset, length in connection.execute(
                    f"SELECT block_id, byte_offset, byte_length FROM source_offsets WHERE block_id IN ({placeholders})",  # noqa: S608 - bounded placeholders only
                    batch,
                )
            )
        result: list[dict[str, Any]] = []
        with path.open("rb") as handle:
            for block_id in wanted:
                if block_id not in offsets:
                    continue
                offset, length = offsets[block_id]
                block = _read_indexed_block(handle, offset, length)
                if not isinstance(block, dict) or str(block.get("block_id") or "") != block_id:
                    raise RuntimeError("Source-block lookup does not match authoritative source identity")
                result.append(block)
        if _signature(path) != signature:
            raise RuntimeError("Source blocks changed during selected lookup")
    return result
