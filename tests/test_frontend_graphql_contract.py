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

"""Contract tests binding frontend GraphQL documents to the Strawberry schema.

Why: GraphQL is one HTTP route, so the REST OpenAPI contract cannot catch an unknown field,
a wrong argument, a mistyped variable, or a mutation slipped into the read-only façade.
How: validates every checked-in operation with graphql-core against the live schema, and
proves the checker rejects each class of mistake using throwaway documents.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))

from app.application import create_app  # noqa: E402
from app.graphql.schema import build_schema  # noqa: E402

from scripts.check_frontend_graphql_contract import (  # noqa: E402
    contract_mismatches,
    transport_mismatches,
)

pytestmark = pytest.mark.contract


@pytest.fixture(scope="module")
def graphql_schema():
    return build_schema(introspection=True)._schema


def test_frontend_graphql_operations_match_the_schema(graphql_schema) -> None:
    mismatches = contract_mismatches(graphql_schema)
    assert mismatches == [], "\n".join(mismatches)


def test_graphql_transport_is_a_post_route() -> None:
    assert transport_mismatches(create_app().openapi()) == []


# Expected fragments avoid graphql-core's exact wording, which changes between releases.
@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ("query Bad { celf_model { no_such_field } }", ("no_such_field",)),
        ('query Bad { generated_claim(claim: "x") { claim_id } }', ("Unknown argument", "claim")),
        ("query Bad($id: Int!) { generated_claim(claim_id: $id) { claim_id } }", ("$id", "Int!", "String!")),
        ("query Bad { generated_claim { claim_id } }", ("claim_id", "String!", "required")),
        ("query Bad { celf_model }", ("celf_model", "selection")),
        ("mutation Bad { celf_model { specification_version } }", ("only queries are allowed",)),
        ("query Other { celf_model { specification_version } }", ("operation must be named Bad",)),
    ],
)
def test_the_checker_rejects_each_class_of_mistake(tmp_path, monkeypatch, graphql_schema, document, expected) -> None:
    import scripts.check_frontend_graphql_contract as checker

    monkeypatch.setattr(checker, "ROOT", tmp_path)
    fake = tmp_path / "src"
    fake.mkdir()
    (fake / "Bad.graphql").write_text(document, encoding="utf-8")
    failures = contract_mismatches(graphql_schema, fake)
    assert any(all(part in failure for part in expected) for failure in failures), failures


def _write(directory: Path, name: str, source: str) -> None:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_fragments_colocated_anywhere_are_validated_with_the_queries_that_spread_them(
    tmp_path, monkeypatch, graphql_schema,
) -> None:
    import scripts.check_frontend_graphql_contract as checker

    monkeypatch.setattr(checker, "ROOT", tmp_path)
    src = tmp_path / "src"
    _write(src, "features/a/ModelFields.graphql", "fragment ModelFields on CelfModel { specification_version }")
    _write(src, "api/Model.graphql", "query Model { celf_model { ...ModelFields } }")
    _write(src, "api/schema.graphql", "type Query { ignored: String }")
    assert contract_mismatches(graphql_schema, src) == []

    _write(src, "features/a/ModelFields.graphql", "fragment ModelFields on CelfModel { no_such_field }")
    assert any("no_such_field" in failure for failure in contract_mismatches(graphql_schema, src))


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        ({"Unused.graphql": "fragment Unused on CelfModel { specification_version }"}, "fragment Unused is not used"),
        ({"Wrong.graphql": "fragment Other on CelfModel { specification_version }"}, "fragment must be named Wrong"),
        ({"Q.graphql": "query Q { celf_model { ...Missing } }"}, "Missing"),
        (
            {"Two.graphql": "query Two { celf_model { nodes { type } } }\nfragment F on CelfModel { edges { id } }"},
            "expected exactly one definition",
        ),
    ],
)
def test_the_checker_enforces_fragment_rules(tmp_path, monkeypatch, graphql_schema, files, expected) -> None:
    import scripts.check_frontend_graphql_contract as checker

    monkeypatch.setattr(checker, "ROOT", tmp_path)
    src = tmp_path / "src"
    _write(src, "Model.graphql", "query Model { celf_model { specification_version } }")
    for name, source in files.items():
        _write(src, name, source)
    failures = contract_mismatches(graphql_schema, src)
    assert any(expected in failure for failure in failures), failures
