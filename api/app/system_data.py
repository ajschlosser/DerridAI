# Copyright 2026 Aaron John Schlosser, PhD.
"""System Data service.

This is the application-facing boundary for durable system databases. The
service deliberately knows only the DatabaseBackend contract, not SQLite.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .database_backend import DatabaseBackend, redact_columns, redact_row

_READ_ONLY_TABLES = frozenset({"sessions", "login_failures"})
_PROTECTED_COLUMNS = frozenset(
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


class SystemDataService:
    def __init__(self, backends: Mapping[str, DatabaseBackend]) -> None:
        self._backends = dict(backends)

    def databases(self) -> list[dict[str, Any]]:
        result = []
        for name, backend in self._backends.items():
            description = backend.describe()
            description["name"] = name
            description["tables"] = backend.tables()
            description["tables"] = [
                {**table, "columns": redact_columns(table["columns"]), "writable": self._writable(table["name"])}
                for table in description["tables"]
            ]
            result.append(description)
        return result

    def rows(self, database: str, table: str, *, limit: int, offset: int) -> dict[str, Any]:
        backend = self._backend(database)
        payload = backend.rows(table, limit=limit, offset=offset)
        payload["database"] = database
        payload["writable"] = self._writable(table)
        payload["columns"] = redact_columns(payload["columns"])
        payload["rows"] = [redact_row(row) for row in payload["rows"]]
        return payload

    def insert(self, database: str, table: str, values: Mapping[str, Any]) -> dict[str, Any]:
        self._ensure_writable(table, values)
        return self._backend(database).insert(table, values)

    def update(self, database: str, table: str, key: Mapping[str, Any], values: Mapping[str, Any]) -> dict[str, Any]:
        self._ensure_writable(table, values)
        return self._backend(database).update(table, key, values)

    def delete(self, database: str, table: str, key: Mapping[str, Any]) -> dict[str, Any]:
        self._ensure_writable(table, {})
        return {"deleted": self._backend(database).delete(table, key)}

    def _backend(self, database: str) -> DatabaseBackend:
        try:
            return self._backends[str(database)]
        except KeyError as exc:
            raise KeyError(f"Unknown system database: {database}") from exc

    @staticmethod
    def _writable(table: str) -> bool:
        return str(table).lower() not in _READ_ONLY_TABLES

    @classmethod
    def _ensure_writable(cls, table: str, values: Mapping[str, Any]) -> None:
        if not cls._writable(table):
            raise PermissionError(f"The {table} table is read-only.")
        protected = {str(key).lower() for key in values} & _PROTECTED_COLUMNS
        if protected:
            raise PermissionError("Credential and session-secret columns cannot be edited through System Data.")
