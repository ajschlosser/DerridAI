# Copyright 2026 Aaron John Schlosser, PhD.
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

    directory = ROOT / "web" / "src" / "api" / "graphql" / "operations"
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    fake = tmp_path / "ops"
    fake.mkdir()
    (fake / "Bad.graphql").write_text(document, encoding="utf-8")
    (fake / "index.ts").write_text('import Bad from "./Bad.graphql?raw";\n', encoding="utf-8")
    failures = contract_mismatches(graphql_schema, fake)
    assert any(all(part in failure for part in expected) for failure in failures), failures
    assert directory.exists()


def test_the_checker_requires_registration(tmp_path, monkeypatch, graphql_schema) -> None:
    import scripts.check_frontend_graphql_contract as checker

    monkeypatch.setattr(checker, "ROOT", tmp_path)
    fake = tmp_path / "ops"
    fake.mkdir()
    (fake / "Orphan.graphql").write_text("query Orphan { celf_model { specification_version } }", encoding="utf-8")
    (fake / "index.ts").write_text("", encoding="utf-8")
    assert contract_mismatches(graphql_schema, fake) == ["ops/Orphan.graphql: not registered in operations/index.ts"]
