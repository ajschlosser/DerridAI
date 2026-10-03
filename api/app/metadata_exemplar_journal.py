# Copyright 2026 Aaron John Schlosser, PhD.
"""Recoverable derived-index work committed beside canonical corpus Records."""
# ruff: noqa: S608 -- SQL identifiers come only from closed server-owned constants.

from __future__ import annotations

import sqlite3
from typing import Any

DEPENDENCIES = (
    "record_revision", "text", "source_document_id", "source_block_ids", "source_spans",
    "field_assertions", "current_field_assertions", "metadata_field_status",
    "metadata_evidence", "metadata_decisions", "llm_rejections", "second_opinion", "human_touched_at",
    "metadata_reviewed_at", "language", "region_type", "page_start", "page_end",
    "document_intelligence",
)


def initialize(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS metadata_exemplar_dirty "
        "(record_id TEXT PRIMARY KEY, token TEXT NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS metadata_exemplar_state "
        "(singleton INTEGER PRIMARY KEY CHECK(singleton=1), epoch TEXT NOT NULL, context TEXT NOT NULL)"
    )
    # The empty ID represents complete scope recovery, including deleted Records.
    fresh = connection.execute(
        "INSERT OR IGNORE INTO metadata_exemplar_state VALUES(1, '', '')"
    ).rowcount
    if fresh:
        invalidate(connection)
    changed = " OR ".join(
        f"json_extract(NEW.payload, '$.{field}') IS NOT json_extract(OLD.payload, '$.{field}')"
        for field in DEPENDENCIES
    )
    for operation, row, condition in (
        ("INSERT", "NEW", ""),
        ("DELETE", "OLD", ""),
        ("UPDATE", "NEW", f" AND ({changed})"),
    ):
        statement = f"""
            CREATE TRIGGER IF NOT EXISTS exemplar_dirty_{operation.lower()}
            AFTER {operation} ON corpus_records
            WHEN 1=1{condition}
            BEGIN
                INSERT INTO metadata_exemplar_dirty(record_id,token)
                VALUES(
                    CASE WHEN EXISTS(SELECT 1 FROM metadata_exemplar_dirty WHERE record_id='')
                         THEN '' ELSE {row}.record_id END,
                    lower(hex(randomblob(16)))
                )
                ON CONFLICT(record_id) DO UPDATE SET token=excluded.token;
            END
        """
        connection.execute(statement)


def invalidate(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO metadata_exemplar_dirty VALUES('', lower(hex(randomblob(16)))) "
        "ON CONFLICT(record_id) DO UPDATE SET token=excluded.token"
    )


def dirty(connection: sqlite3.Connection, limit: int = 100) -> list[dict[str, str]]:
    return [
        {"record_id": str(row[0]), "token": str(row[1])}
        for row in connection.execute(
            "SELECT record_id,token FROM metadata_exemplar_dirty ORDER BY record_id LIMIT ?",
            (max(1, min(1000, limit)),),
        )
    ]


def complete(connection: sqlite3.Connection, items: list[dict[str, Any]]) -> int:
    return connection.executemany(
        "DELETE FROM metadata_exemplar_dirty WHERE record_id=? AND token=?",
        [(item["record_id"], item["token"]) for item in items],
    ).rowcount
