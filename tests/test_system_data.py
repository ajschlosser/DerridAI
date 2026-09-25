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

    assert payload["writable"] is False
    assert payload["operations"] == {"insert": False, "update": False, "delete": False}
    assert payload["rows"] == [{"id": 1, "value": "visible", "secret": "[redacted]"}]
    assert next(column for column in payload["columns"] if column["name"] == "secret")["sensitive"] is True


@pytest.mark.parametrize("operation", ["insert", "update", "delete"])
def test_system_data_blocks_generic_mutation_by_default(tmp_path, operation: str) -> None:
    path = tmp_path / "system.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE settings (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO settings VALUES (1, 'visible')")
        connection.commit()

    service = SystemDataService({"system": SQLiteBackend("system", path)})
    with pytest.raises(PermissionError, match="read-only in System Data"):
        if operation == "insert":
            service.insert("system", "settings", {"value": "new"})
        elif operation == "update":
            service.update("system", "settings", {"id": 1}, {"value": "changed"})
        else:
            service.delete("system", "settings", {"id": 1})


def test_system_data_describes_mutation_permissions_per_table(tmp_path) -> None:
    path = tmp_path / "auth.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE sessions (token_hash TEXT PRIMARY KEY)")
        connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
        connection.commit()

    service = SystemDataService({"auth": SQLiteBackend("auth", path)})
    payload = service.databases()[0]

    assert payload["name"] == "auth"
    assert {table["name"] for table in payload["tables"]} == {"sessions", "users"}
    for table in payload["tables"]:
        assert table["writable"] is False
        assert table["operations"] == {"insert": False, "update": False, "delete": False}
