# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import sqlite3

import pytest

from app.database_backend import SQLiteBackend
from app.system_data import SystemDataService


def test_system_data_exposes_tables_and_redacts_secrets(tmp_path) -> None:
    path = tmp_path / "system.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE settings (id INTEGER PRIMARY KEY, value TEXT, secret TEXT)")
        connection.execute("INSERT INTO settings VALUES (1, 'visible', 'do-not-show')")
        connection.commit()

    service = SystemDataService({"system": SQLiteBackend("system", path)})
    payload = service.rows("system", "settings", limit=10, offset=0)

    assert payload["writable"] is True
    assert payload["rows"] == [{"id": 1, "value": "visible", "secret": "[redacted]"}]
    assert next(column for column in payload["columns"] if column["name"] == "secret")["sensitive"] is True


def test_system_data_blocks_session_mutation(tmp_path) -> None:
    path = tmp_path / "auth.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE sessions (token_hash TEXT PRIMARY KEY)")
        connection.commit()

    service = SystemDataService({"auth": SQLiteBackend("auth", path)})
    with pytest.raises(PermissionError):
        service.delete("auth", "sessions", {"token_hash": "x"})
