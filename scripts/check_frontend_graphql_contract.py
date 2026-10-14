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

"""Validate every frontend GraphQL document against the live Strawberry schema.

Documents live beside the code that uses them (``web/src/**/*.graphql``; the
exported ``schema.graphql`` is excluded). Each file holds exactly one
definition named after the file: a query, or a fragment. Every query must
parse and validate against the schema together with the fragments it spreads
(fields, arguments, variable types, required arguments, nesting); fragments
must be unique and used. Mutations and subscriptions are rejected: the façade
is read-only. Generated TypeScript freshness is checked separately by
``npm run codegen:check``; the REST OpenAPI contract by
check_frontend_api_contract.py.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from graphql import (
    DocumentNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    GraphQLError,
    OperationDefinitionNode,
    OperationType,
    parse,
    validate,
    visit,
)
from graphql.language import Visitor

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = ROOT / "web" / "src"
SCHEMA_ARTIFACT = "schema.graphql"


def frontend_documents(directory: Path = DOCUMENTS_DIR) -> dict[Path, str]:
    return {
        path: path.read_text(encoding="utf-8")
        for path in sorted(directory.rglob("*.graphql"))
        if path.name != SCHEMA_ARTIFACT
    }


def frontend_operations(directory: Path = DOCUMENTS_DIR) -> dict[str, str]:
    """Query documents by operation name (fragment-only files excluded)."""
    found: dict[str, str] = {}
    for path, source in frontend_documents(directory).items():
        try:
            document = parse(source)
        except GraphQLError:
            continue
        if any(isinstance(item, OperationDefinitionNode) for item in document.definitions):
            found[path.stem] = source
    return found


def _spreads(node: Any) -> set[str]:
    names: set[str] = set()

    class Collector(Visitor):
        def enter_fragment_spread(self, spread: FragmentSpreadNode, *_: Any) -> None:
            names.add(spread.name.value)

    visit(node, Collector())
    return names


def _closure(start: set[str], fragments: dict[str, FragmentDefinitionNode]) -> set[str]:
    seen: set[str] = set()
    pending = list(start)
    while pending:
        name = pending.pop()
        if name in seen or name not in fragments:
            continue
        seen.add(name)
        pending.extend(_spreads(fragments[name]))
    return seen


def contract_mismatches(schema: Any, directory: Path = DOCUMENTS_DIR) -> list[str]:
    """Return every document problem; ``schema`` is a graphql-core GraphQLSchema."""
    failures: list[str] = []
    documents = frontend_documents(directory)
    fragments: dict[str, FragmentDefinitionNode] = {}
    operations: dict[Path, OperationDefinitionNode] = {}
    for path, source in documents.items():
        location = str(path.relative_to(ROOT))
        try:
            document = parse(source)
        except GraphQLError as exc:
            failures.append(f"{location}: {exc.message}")
            continue
        definitions = list(document.definitions)
        if len(definitions) != 1:
            failures.append(f"{location}: expected exactly one definition, found {len(definitions)}")
        for definition in definitions:
            if isinstance(definition, FragmentDefinitionNode):
                name = definition.name.value
                if name != path.stem:
                    failures.append(f"{location}: fragment must be named {path.stem}")
                if name in fragments:
                    failures.append(f"{location}: fragment {name} is defined more than once")
                fragments[name] = definition
            elif isinstance(definition, OperationDefinitionNode):
                if definition.operation is not OperationType.QUERY:
                    failures.append(f"{location}: only queries are allowed (found {definition.operation.value})")
                if definition.name is None or definition.name.value != path.stem:
                    failures.append(f"{location}: operation must be named {path.stem}")
                operations[path] = definition
    if not operations:
        failures.append(f"{directory.relative_to(ROOT)}: no GraphQL operations found")
    used: set[str] = set()
    for path, operation in operations.items():
        needed = _closure(_spreads(operation), fragments)
        used |= needed
        document = DocumentNode(definitions=(operation, *(fragments[name] for name in sorted(needed))))
        for error in validate(schema, document):
            failures.append(f"{path.relative_to(ROOT)}: {error.message}")
    for name in sorted(set(fragments) - used):
        failures.append(f"fragment {name} is not used by any operation")
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
