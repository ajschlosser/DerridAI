# Copyright 2026 Aaron John Schlosser, PhD.
"""Derive local and CI test obligations from changed repository paths."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass


@dataclass
class PreflightPlan:
    backend: bool = False
    frontend: bool = False
    frontend_unit: bool = False
    unit_full: bool = False
    frontend_build: bool = False
    storybook: bool = False
    e2e: bool = False
    a11y: bool = False
    a11y_full: bool = False
    sdk: bool = False
    contract: bool = False
    format: bool = False
    publication: bool = False
    generated: bool = False
    legacy: bool = False


FORMAT_SUFFIXES = (
    ".md",
    ".json",
    ".yml",
    ".yaml",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".vue",
    ".css",
    ".scss",
    ".html",
)

PUBLICATION_PATHS = {
    "api/app/site_publication.py",
    "api/app/routers/sites.py",
    "api/app/site_assets/derridai-site.js",
    "api/app/site_assets/derridai-sdk.js",
    "web/vite.sdk.config.ts",
    "web/vite.sdk.package.config.ts",
    "web/playwright.publication.config.ts",
    "scripts/build_publication_acceptance_fixtures.py",
    "scripts/check_publication_artifacts.sh",
}

CONTRACT_BACKEND_PREFIXES = (
    "api/app/routers/",
    "api/app/graphql/",
    "api/app/celf_queries/",
)

FRONTEND_UI_PREFIXES = (
    "web/src/components/",
    "web/src/views/",
    "web/src/router/",
    "web/src/stores/",
    "web/src/composables/",
    "web/src/runtime/",
    "web/src/styles/",
)

A11Y_FULL_PATHS = {
    "web/src/style.css",
    "web/src/styles/tokens.css",
    "web/tests/e2e/corpus-builder-theme-sweep.spec.ts",
    "web/playwright.a11y.config.ts",
}


def _mark_full_frontend(plan: PreflightPlan) -> None:
    plan.frontend = True
    plan.frontend_unit = True
    plan.unit_full = True
    plan.frontend_build = True
    plan.storybook = True
    plan.e2e = True
    plan.a11y = True
    plan.a11y_full = True
    plan.legacy = True
    plan.sdk = True


def build_plan(paths: list[str]) -> PreflightPlan:
    plan = PreflightPlan()
    for raw_path in paths:
        path = raw_path.replace("\\", "/")
        while path.startswith("./"):
            path = path[2:]
        if not path:
            continue

        if path == ".github/workflows/frontend.yml":
            plan.backend = plan.contract = plan.format = plan.publication = True
            _mark_full_frontend(plan)
        elif path.startswith("scripts/"):
            # Repository automation should test the automation it can affect, not every application surface.
            plan.backend = True
            if path in {
                "scripts/check_frontend_api_contract.py",
                "scripts/check_frontend_graphql_contract.py",
            }:
                plan.contract = True
            if path == "scripts/run_frontend_related_tests.sh":
                plan.frontend = plan.frontend_unit = plan.unit_full = True
            if path in PUBLICATION_PATHS:
                plan.publication = True
        elif path.startswith("api/"):
            plan.backend = True
            if (
                path.startswith(CONTRACT_BACKEND_PREFIXES)
                or path in {"api/app/application.py", "api/app/models.py"}
            ):
                plan.contract = True
        elif path in {
            "tests/test_frontend_api_contract.py",
            "tests/test_frontend_graphql_contract.py",
            "pytest.ini",
        }:
            plan.backend = plan.contract = True
        elif path.startswith("tests/") or path in {"ruff.toml", "mypy.ini"}:
            plan.backend = True

        # SDK/publication work is a frontend concern but does not require the app browser suite.
        if (
            path.startswith("web/sdk/")
            or path.startswith("web/tests/fixtures/sdk-consumer/")
            or path == "web/scripts/check-sdk-consumer.mjs"
            or path.startswith("web/vite.sdk")
            or path == "api/app/site_assets/derridai-sdk.js"
        ):
            plan.frontend = plan.frontend_unit = plan.sdk = True
            plan.publication = True

        if path.startswith("web/src/api/"):
            plan.frontend = plan.frontend_unit = plan.frontend_build = plan.contract = True
        elif path.startswith("web/tests/frontend/"):
            plan.frontend = plan.frontend_unit = True
            if path == "web/tests/frontend/setup.ts":
                plan.unit_full = True
        elif path.startswith("web/tests/e2e/legacy-dom"):
            plan.frontend = plan.frontend_build = plan.legacy = True
        elif path == "web/tests/e2e/corpus-builder-theme-sweep.spec.ts":
            plan.frontend = plan.storybook = plan.a11y = plan.a11y_full = True
        elif path == "web/tests/e2e/static-site-export.spec.ts":
            plan.frontend = True
            plan.publication = True
        elif path.startswith("web/tests/e2e/static-site-"):
            plan.frontend = plan.frontend_build = plan.storybook = plan.e2e = True
            plan.publication = True
        elif path.startswith("web/tests/e2e/"):
            plan.frontend = plan.frontend_build = plan.storybook = plan.e2e = True
        elif path == "web/playwright.config.ts":
            plan.frontend = plan.frontend_build = plan.storybook = plan.e2e = True
        elif path == "web/playwright.legacy.config.ts":
            plan.frontend = plan.frontend_build = plan.legacy = True
        elif path == "web/playwright.a11y.config.ts":
            plan.frontend = plan.storybook = plan.a11y = plan.a11y_full = True
        elif path == "web/playwright.publication.config.ts":
            plan.frontend = plan.publication = True
        elif path.startswith("web/.storybook/") or path.startswith("web/.storybook"):
            plan.frontend = plan.storybook = plan.e2e = plan.a11y = plan.a11y_full = True
        elif path in {
            "web/vite.config.ts",
            "web/vitest.config.ts",
            "web/tsconfig.json",
            "web/tsconfig.tests.json",
        }:
            plan.frontend = plan.frontend_unit = plan.frontend_build = True
            if path in {"web/vitest.config.ts", "web/tsconfig.tests.json"}:
                plan.unit_full = True
        elif path in {"web/package.json", "web/package-lock.json"}:
            _mark_full_frontend(plan)
            plan.publication = True
        elif path.startswith("web/src/"):
            if ".stories." in path:
                plan.frontend = plan.storybook = plan.a11y = True
            else:
                plan.frontend = plan.frontend_unit = plan.frontend_build = True
                if path.startswith(FRONTEND_UI_PREFIXES) or path in {
                    "web/src/App.vue",
                    "web/src/style.css",
                }:
                    plan.storybook = plan.e2e = True
                if (
                    path.startswith(("web/src/components/", "web/src/views/"))
                    or path in A11Y_FULL_PATHS
                ):
                    plan.a11y = True
                if path.startswith("web/src/runtime/") or path == "web/src/App.vue":
                    plan.legacy = True

        if (
            path in A11Y_FULL_PATHS
            or path.startswith("web/src/components/ui/")
            or path.startswith("web/src/styles/")
        ):
            plan.a11y = plan.a11y_full = True
            plan.storybook = True
            plan.e2e = True

        if path in {
            "README.md",
            "CONTRIBUTING.md",
            "AGENTS.md",
            ".prettierignore",
            ".editorconfig",
        } or path.startswith("docs/"):
            plan.format = True
        if path.endswith(FORMAT_SUFFIXES):
            plan.format = True

        if (
            path in PUBLICATION_PATHS
            or path.startswith("web/sdk/")
            or path.startswith("web/tests/e2e/static-site-")
            or path.startswith("web/tests/fixtures/sdk-consumer/")
            or path == "web/scripts/check-sdk-consumer.mjs"
        ):
            plan.publication = True

        if (
            path.startswith(
                ("api/app/graphql/", "api/app/celf_queries/", "api/app/pipelines/")
            )
            or path.startswith("web/src/api/graphql/")
            or path.startswith("web/src/components/pipelines/fixtures/")
            or path.startswith("scripts/export_")
        ):
            plan.generated = True

    return plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "shell"), default="json")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    paths = args.paths or [line.rstrip("\n") for line in sys.stdin]
    values = asdict(build_plan(paths))
    if args.format == "json":
        print(json.dumps(values, sort_keys=True))
        return
    for key, value in values.items():
        print(f"{key.upper()}={'true' if value else 'false'}")


if __name__ == "__main__":
    main()
