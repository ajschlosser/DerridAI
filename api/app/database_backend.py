# Copyright 2026 Aaron John Schlosser, PhD.
"""Backend-neutral system-data access with a SQLite adapter.

The API and UI consume this narrow table/row contract. SQLite is an adapter
detail and can be replaced by another durable backend without changing them.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SECRET_COLUMNS = frozenset(
    {
        "api_key",
        "access_token",
        "client_secret",
        "credential",
        "credentials",
        "password_hash",
        "password_salt",
        "private_key",
        "refresh_token",
        "secret",
        "session_secret",
        "token",
        "token_hash",
    }
)


def _identifier(value: str) -> str:
    value = str(value or "").strip()
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError("Invalid database identifier.")
    return value


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class DatabaseBackend(Protocol):
    name: str
    path: str

    def describe(self) -> dict[str, Any]: ...
    def tables(self) -> list[dict[str, Any]]: ...
    def table(self, name: str) -> dict[str, Any]: ...
    def rows(self, name: str, *, limit: int, offset: int) -> dict[str, Any]: ...
    def insert(self, name: str, values: Mapping[str, Any]) -> dict[str, Any]: ...
    def update(self, name: str, key: Mapping[str, Any], values: Mapping[str, Any]) -> dict[str, Any]: ...
    def delete(self, name: str, key: Mapping[str, Any]) -> bool: ...


class SQLiteBackend:
    """SQLite implementation of the backend-neutral DatabaseBackend contract."""

    name = "sqlite"

    def __init__(self, database_name: str, path: str | Path) -> None:
        self.database_name = database_name
        self.path = str(Path(path).expanduser())

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    @staticmethod
    def _columns(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
        table = _identifier(table)
        return [
            {
                "name": str(row["name"]),
                "type": str(row["type"] or ""),
                "nullable": not bool(row["notnull"]),
                "default": row["dflt_value"],
                "primary_key": int(row["pk"]),
            }
            for row in connection.execute(f"PRAGMA table_info({table})")
        ]

    def describe(self) -> dict[str, Any]:
        path = Path(self.path)
        return {"name": self.database_name, "backend": self.name, "path": self.path, "size_bytes": path.stat().st_size if path.exists() else 0}

    def tables(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            names = [
                str(row["name"])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]
            return [self.table(name, connection=connection) for name in names]

    def table(self, name: str, *, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
        owns_connection = connection is None
        connection = connection or self._connect()
        try:
            table = _identifier(name)
            columns = self._columns(connection, table)
            if not columns:
                raise KeyError(table)
            count = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            return {"name": table, "columns": columns, "row_count": count}
        finally:
            if owns_connection:
                connection.close()

    def rows(self, name: str, *, limit: int, offset: int) -> dict[str, Any]:
        table = self.table(name)
        with self._connect() as connection:
            rows = [
                {str(key): value for key, value in dict(row).items()}
                for row in connection.execute(
                    f"SELECT * FROM {_identifier(name)} LIMIT ? OFFSET ?", (int(limit), int(offset))
                )
            ]
        return {**table, "rows": rows, "offset": offset, "limit": limit}

    def insert(self, name: str, values: Mapping[str, Any]) -> dict[str, Any]:
        table = self.table(name)
        allowed = {column["name"] for column in table["columns"]}
        clean = {str(key): value for key, value in values.items() if str(key) in allowed}
        if not clean:
            raise ValueError("At least one writable column is required.")
        columns = list(clean)
        placeholders = ",".join("?" for _ in columns)
        with self._connect() as connection:
            cursor = connection.execute(
                f"INSERT INTO {_identifier(name)} ({','.join(_identifier(column) for column in columns)}) VALUES ({placeholders})",
                [self._encode(value) for value in clean.values()],
            )
            connection.commit()
            return {"inserted": True, "rowid": cursor.lastrowid}

    def update(self, name: str, key: Mapping[str, Any], values: Mapping[str, Any]) -> dict[str, Any]:
        table = self.table(name)
        allowed = {column["name"] for column in table["columns"]}
        keys = {str(field): value for field, value in key.items() if str(field) in allowed}
        clean = {str(field): value for field, value in values.items() if str(field) in allowed and str(field) not in keys}
        if not keys or not clean:
            raise ValueError("A primary key and at least one changed column are required.")
        where = " AND ".join(f"{_identifier(field)}=?" for field in keys)
        assignments = ",".join(f"{_identifier(field)}=?" for field in clean)
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE {_identifier(name)} SET {assignments} WHERE {where}",
                [self._encode(value) for value in [*clean.values(), *keys.values()]],
            )
            connection.commit()
            return {"updated": bool(cursor.rowcount)}

    def delete(self, name: str, key: Mapping[str, Any]) -> bool:
        table = self.table(name)
        allowed = {column["name"] for column in table["columns"]}
        keys = {str(field): value for field, value in key.items() if str(field) in allowed}
        if not keys:
            raise ValueError("A primary key is required.")
        where = " AND ".join(f"{_identifier(field)}=?" for field in keys)
        with self._connect() as connection:
            cursor = connection.execute(
                f"DELETE FROM {_identifier(name)} WHERE {where}",
                [self._encode(value) for value in keys.values()],
            )
            connection.commit()
            return bool(cursor.rowcount)

    @staticmethod
    def _encode(value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return _json(value)
        if isinstance(value, bool):
            return int(value)
        return value


def redact_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): ("[redacted]" if str(key).lower() in _SECRET_COLUMNS else value)
        for key, value in row.items()
    }


def redact_columns(columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {**column, "sensitive": str(column.get("name") or "").lower() in _SECRET_COLUMNS}
        for column in columns
    ]
