# Copyright 2026 Aaron John Schlosser, PhD.
"""Validate every frontend GraphQL operation against the live Strawberry schema.

Each document under web/src/api/graphql/operations/ must parse, validate against
the schema (fields, arguments, variable types, required arguments, nesting),
contain exactly one query named after its file, and be registered in the
operations index. The REST OpenAPI contract is checked separately by
check_frontend_api_contract.py.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from graphql import (
    GraphQLError,
    OperationDefinitionNode,
    OperationType,
    parse,
    validate,
)

ROOT = Path(__file__).resolve().parents[1]
OPERATIONS_DIR = ROOT / "web" / "src" / "api" / "graphql" / "operations"


def frontend_operations(directory: Path = OPERATIONS_DIR) -> dict[str, str]:
    return {path.stem: path.read_text(encoding="utf-8") for path in sorted(directory.glob("*.graphql"))}


def _registered_operations(directory: Path) -> set[str]:
    index = directory / "index.ts"
    if not index.exists():
        return set()
    return set(re.findall(r"""^import\s+(\w+)\s+from\s+["']\./\1\.graphql\?raw["'];""", index.read_text(encoding="utf-8"), re.M))


def contract_mismatches(schema: Any, directory: Path = OPERATIONS_DIR) -> list[str]:
    """Return every operation problem; ``schema`` is a graphql-core GraphQLSchema."""
    failures: list[str] = []
    operations = frontend_operations(directory)
    if not operations:
        failures.append(f"{directory.relative_to(ROOT)}: no GraphQL operations found")
    registered = _registered_operations(directory)
    for name, source in operations.items():
        location = f"{(directory / (name + '.graphql')).relative_to(ROOT)}"
        try:
            document = parse(source)
        except GraphQLError as exc:
            failures.append(f"{location}: {exc.message}")
            continue
        definitions = [item for item in document.definitions if isinstance(item, OperationDefinitionNode)]
        if len(definitions) != 1:
            failures.append(f"{location}: expected exactly one operation, found {len(definitions)}")
        for definition in definitions:
            if definition.operation is not OperationType.QUERY:
                failures.append(f"{location}: only queries are allowed (found {definition.operation.value})")
            if definition.name is None or definition.name.value != name:
                failures.append(f"{location}: operation must be named {name}")
        for error in validate(schema, document):
            failures.append(f"{location}: {error.message}")
        if name not in registered:
            failures.append(f"{location}: not registered in operations/index.ts")
    for name in sorted(registered - set(operations)):
        failures.append(f"operations/index.ts: {name} has no {name}.graphql document")
    return failures


def transport_mismatches(openapi: dict[str, Any]) -> list[str]:
    """The browser's GraphQL transport must be a real POST route."""
    methods = {method.upper() for method in (openapi.get("paths", {}).get("/api/graphql") or {})}
    return [] if "POST" in methods else ["POST /api/graphql is not exposed by the API"]


def main() -> int:
    sys.path.insert(0, str(ROOT / "api"))
    from app.application import create_app
    from app.graphql.schema import build_schema

    failures = contract_mismatches(build_schema(introspection=True)._schema)
    failures += transport_mismatches(create_app().openapi())
    for failure in failures:
        print(failure)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
