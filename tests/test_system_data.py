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
