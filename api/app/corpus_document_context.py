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

"""Rebuildable documentary dependencies for whole-document annotation freshness."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from typing import Any

CONTRACT = "corpus-document-context-v1"
SOURCE_FIELDS = (
    "record_id", "text", "source_document_id", "source_asset_id", "source_spans",
    "source_block_ids", "source_unit_ids", "source_extracted_text",
)


def record_fingerprint(record: dict[str, Any]) -> str:
    # Revision-only/metadata edits do not change the text and locators NLP consumes.
    value = {key: record[key] for key in SOURCE_FIELDS if key in record}
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def initialize(connection: sqlite3.Connection) -> None:
    missing = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='document_context_records'"
    ).fetchone() is None
    connection.execute("""
        CREATE TABLE IF NOT EXISTS document_context_state (
            id INTEGER PRIMARY KEY CHECK(id=1), contract TEXT NOT NULL, epoch TEXT NOT NULL)
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS document_context_records (
            record_id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL, fingerprint TEXT NOT NULL)
    """)
    connection.execute("INSERT OR IGNORE INTO document_context_state VALUES(1,'','')")
    if missing:
        connection.execute("UPDATE document_context_state SET contract='' WHERE id=1")


def ensure(connection: sqlite3.Connection) -> str:
    """Refresh dependencies before the shared canonical dirty journal is acknowledged."""
    state = connection.execute("SELECT contract,epoch FROM document_context_state WHERE id=1").fetchone()
    rebuild = state[0] != CONTRACT
    if rebuild:
        connection.execute("DELETE FROM document_context_records")
        rows = connection.execute("SELECT record_id,ordinal,payload FROM corpus_records").fetchall()
    else:
        rows = connection.execute("""
            SELECT d.record_id,c.ordinal,c.payload FROM review_projection_dirty d
            LEFT JOIN corpus_records c ON c.record_id=d.record_id
        """).fetchall()
    changed = rebuild
    for record_id, ordinal, payload in rows:
        existing = connection.execute(
            "SELECT ordinal,fingerprint FROM document_context_records WHERE record_id=?", (record_id,),
        ).fetchone()
        if payload is None:
            if existing is not None:
                connection.execute("DELETE FROM document_context_records WHERE record_id=?", (record_id,))
                changed = True
            continue
        fingerprint = record_fingerprint(json.loads(payload))
        if existing == (int(ordinal), fingerprint):
            continue
        connection.execute("""
            INSERT INTO document_context_records VALUES(?,?,?)
            ON CONFLICT(record_id) DO UPDATE SET ordinal=excluded.ordinal,fingerprint=excluded.fingerprint
        """, (record_id, int(ordinal), fingerprint))
        changed = True
    if changed:
        epoch = uuid.uuid4().hex
        connection.execute(
            "UPDATE document_context_state SET contract=?,epoch=? WHERE id=1", (CONTRACT, epoch),
        )
        return epoch
    return str(state[1])


def matches(connection: sqlite3.Connection, records: list[dict[str, Any]]) -> bool:
    actual = connection.execute(
        "SELECT record_id,ordinal,fingerprint FROM document_context_records ORDER BY ordinal"
    ).fetchall()
    expected = [
        (str(record.get("record_id") or ""), index, record_fingerprint(record))
        for index, record in enumerate(records)
    ]
    return actual == expected
