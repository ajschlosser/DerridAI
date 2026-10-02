# Copyright 2026 Aaron John Schlosser, PhD.
"""Change-impact regression coverage for the merge-readiness preflight."""

from scripts.preflight_plan import build_plan


def test_documentation_change_only_requires_formatting():
    plan = build_plan(["docs/ARCHITECTURE.md"])

    assert plan.format
    assert not plan.backend
    assert not plan.frontend
    assert not plan.contract


def test_backend_graphql_change_requires_contract_and_generated_checks():
    plan = build_plan(["api/app/graphql/schema.py"])

    assert plan.backend
    assert plan.contract
    assert plan.generated
    assert not plan.frontend


def test_frontend_api_change_requires_both_frontend_and_contract_checks():
    plan = build_plan(["web/src/api/client.ts"])

    assert plan.frontend
    assert plan.contract
    assert plan.format


def test_legacy_and_publication_paths_select_specialized_acceptance_gates():
    plan = build_plan(
        [
            "web/tests/e2e/legacy-dom-baseline.spec.ts",
            "web/sdk/src/client.ts",
        ]
    )

    assert plan.frontend
    assert plan.legacy
    assert plan.publication


def test_workflow_or_preflight_script_change_exercises_all_general_gates():
    plan = build_plan(["scripts/preflight.sh"])

    assert plan.backend
    assert plan.frontend
    assert plan.contract
    assert plan.format
