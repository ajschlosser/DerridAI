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


def test_backend_internal_change_does_not_pay_for_frontend_contract_install():
    plan = build_plan(["api/app/bibliography.py"])

    assert plan.backend
    assert not plan.contract
    assert not plan.frontend


def test_frontend_api_change_requires_contract_but_not_browser_catalogues():
    plan = build_plan(["web/src/api/client.ts"])

    assert plan.frontend
    assert plan.frontend_unit
    assert not plan.unit_full
    assert plan.frontend_build
    assert plan.contract
    assert plan.format
    assert not plan.storybook
    assert not plan.e2e
    assert not plan.a11y
    assert not plan.legacy


def test_component_change_gets_related_units_and_representative_browser_quality():
    plan = build_plan(["web/src/components/CorpusBuildReadiness.vue"])

    assert plan.frontend
    assert plan.frontend_unit
    assert plan.frontend_build
    assert plan.storybook
    assert plan.e2e
    assert plan.a11y
    assert not plan.a11y_full
    assert not plan.legacy


def test_shared_ui_or_global_css_change_requires_full_a11y():
    component = build_plan(["web/src/components/ui/UiButton.vue"])
    stylesheet = build_plan(["web/src/styles/tokens.css"])

    assert component.a11y and component.a11y_full
    assert stylesheet.a11y and stylesheet.a11y_full


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
    assert plan.sdk
    assert not plan.e2e



def test_static_site_browser_test_stays_in_composed_browser_and_publication_gates():
    plan = build_plan(["web/tests/e2e/static-site-a11y.spec.ts"])

    assert plan.publication
    assert plan.frontend_build
    assert plan.storybook
    assert plan.e2e


def test_publication_export_browser_test_does_not_force_general_app_e2e():
    plan = build_plan(["web/tests/e2e/static-site-export.spec.ts"])

    assert plan.publication
    assert not plan.e2e


def test_related_unit_selector_change_runs_full_frontend_units_only():
    plan = build_plan(["scripts/run_frontend_related_tests.sh"])

    assert plan.backend
    assert plan.frontend
    assert plan.frontend_unit
    assert plan.unit_full
    assert not plan.e2e

def test_preflight_script_change_tests_automation_without_every_frontend_gate():
    plan = build_plan(["scripts/preflight.sh"])

    assert plan.backend
    assert not plan.frontend
    assert not plan.contract
    assert not plan.storybook
    assert not plan.e2e


def test_workflow_change_exercises_all_quality_gate_shapes():
    plan = build_plan([".github/workflows/frontend.yml"])

    assert plan.backend
    assert plan.frontend
    assert plan.contract
    assert plan.frontend_unit
    assert plan.unit_full
    assert plan.frontend_build
    assert plan.storybook
    assert plan.e2e
    assert plan.a11y_full
    assert plan.legacy
    assert plan.sdk
