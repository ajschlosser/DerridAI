# Copyright 2026 Aaron John Schlosser, PhD.
"""Derive local preflight obligations from changed repository paths."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass


@dataclass
class PreflightPlan:
    backend: bool = False
    frontend: bool = False
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
    "web/vite.sdk.ts",
    "web/vite.sdk.package.ts",
    "web/playwright.publication.config.ts",
    "scripts/build_publication_acceptance_fixtures.py",
    "scripts/check_publication_artifacts.sh",
    ".github/workflows/frontend.yml",
}


def build_plan(paths: list[str]) -> PreflightPlan:
    plan = PreflightPlan()
    for raw_path in paths:
        path = raw_path.replace("\\", "/").lstrip("./")
        if not path:
            continue

        if path == ".github/workflows/frontend.yml" or path.startswith("scripts/"):
            plan.backend = plan.frontend = plan.contract = plan.format = True
        elif path.startswith("api/"):
            plan.backend = plan.contract = True
        elif path in {
            "tests/test_frontend_api_contract.py",
            "tests/test_frontend_graphql_contract.py",
            "pytest.ini",
        }:
            plan.backend = plan.contract = True
        elif path.startswith("tests/") or path in {"ruff.toml", "mypy.ini"}:
            plan.backend = True

        if path.startswith("web/src/api/"):
            plan.frontend = plan.contract = True
        elif path.startswith("web/"):
            plan.frontend = plan.format = True

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

        if path.startswith(("web/src/domain/", "web/tests/e2e/legacy-dom")):
            plan.legacy = True

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
