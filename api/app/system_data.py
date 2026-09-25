# Copyright 2026 Aaron John Schlosser, PhD.
"""System Data service.

This is the application-facing boundary for durable system databases. The
service deliberately knows only the DatabaseBackend contract, not SQLite.

System Data is an inspection surface. Generic table mutation is denied unless a
specific database/table/operation is deliberately added to the policy below.
Purpose-built application APIs remain the correct place to change users,
providers, languages, roles, and other domain objects because they can enforce
their domain invariants and audit behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .database_backend import DatabaseBackend, redact_columns, redact_row

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

# Explicit allow-list. Keep empty until a System Data mutation has a concrete
# administrative use case that cannot be served safely by an existing
# purpose-built endpoint. Keys are (database, table); values are allowed verbs.
_MUTATION_POLICY: dict[tuple[str, str], frozenset[str]] = {}


class SystemDataService:
    def __init__(self, backends: Mapping[str, DatabaseBackend]) -> None:
        self._backends = dict(backends)

    def databases(self) -> list[dict[str, Any]]:
        result = []
        for name, backend in self._backends.items():
            description = backend.describe()
            description["name"] = name
            description["tables"] = [
                self._describe_table(name, table) for table in backend.tables()
            ]
            result.append(description)
        return result

    def rows(
        self,
        database: str,
        table: str,
        *,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        backend = self._backend(database)
        payload = backend.rows(table, limit=limit, offset=offset)
        payload["database"] = database
        payload.update(self._permissions(database, table))
        payload["columns"] = redact_columns(payload["columns"])
        payload["rows"] = [redact_row(row) for row in payload["rows"]]
        return payload

    def insert(
        self,
        database: str,
        table: str,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._ensure_allowed(database, table, "insert", values)
        return self._backend(database).insert(table, values)

    def update(
        self,
        database: str,
        table: str,
        key: Mapping[str, Any],
        values: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._ensure_allowed(database, table, "update", values)
        self._ensure_safe_key(key)
        return self._backend(database).update(table, key, values)

    def delete(
        self,
        database: str,
        table: str,
        key: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._ensure_allowed(database, table, "delete", {})
        self._ensure_safe_key(key)
        return {"deleted": self._backend(database).delete(table, key)}

    def _backend(self, database: str) -> DatabaseBackend:
        try:
            return self._backends[str(database)]
        except KeyError as exc:
            raise KeyError(f"Unknown system database: {database}") from exc

    @classmethod
    def _permissions(cls, database: str, table: str) -> dict[str, Any]:
        allowed = _MUTATION_POLICY.get(
            (str(database).lower(), str(table).lower()),
            frozenset(),
        )
        return {
            "writable": bool(allowed),
            "operations": {
                "insert": "insert" in allowed,
                "update": "update" in allowed,
                "delete": "delete" in allowed,
            },
        }

    @classmethod
    def _describe_table(cls, database: str, table: Mapping[str, Any]) -> dict[str, Any]:
        return {
            **table,
            "columns": redact_columns(list(table["columns"])),
            **cls._permissions(database, str(table["name"])),
        }

    @classmethod
    def _ensure_allowed(
        cls,
        database: str,
        table: str,
        operation: str,
        values: Mapping[str, Any],
    ) -> None:
        permissions = cls._permissions(database, table)["operations"]
        if not permissions.get(operation):
            raise PermissionError(
                f"The {database}.{table} table is read-only in System Data. "
                "Use the purpose-built administration surface for supported changes."
            )
        protected = {str(key).lower() for key in values} & _PROTECTED_COLUMNS
        if protected:
            raise PermissionError(
                "Credential and session-secret columns cannot be edited through System Data."
            )

    @staticmethod
    def _ensure_safe_key(key: Mapping[str, Any]) -> None:
        protected = {str(field).lower() for field in key} & _PROTECTED_COLUMNS
        if protected:
            raise PermissionError(
                "Credential and session-secret columns cannot be used as mutation keys "
                "through System Data."
            )
