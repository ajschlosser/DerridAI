# Copyright 2026 Aaron John Schlosser, PhD.
"""The checked-in GraphQL SDL artifact must match the live Strawberry schema.

Why: `web/src/api/graphql/generated.ts` is generated from `schema.graphql`, not from
the live Python schema directly. A root/field added without regenerating the SDL
would silently leave the frontend codegen contract stale until someone happened to
run the export script.
How: renders the schema exactly as `scripts/export_graphql_schema.py` does and
diffs it against the checked-in file; `--check` is exercised as a subprocess so the
CLI contract (exit code, message) is covered too, not just the importable function.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.export_graphql_schema as export_module  # noqa: E402
from scripts.export_graphql_schema import SCHEMA_PATH, rendered_schema  # noqa: E402

pytestmark = pytest.mark.contract


def test_the_checked_in_schema_artifact_is_current():
    assert SCHEMA_PATH.exists(), f"{SCHEMA_PATH} is missing. Run: python scripts/export_graphql_schema.py"
    current = SCHEMA_PATH.read_text(encoding="utf-8")
    assert current == rendered_schema(), (
        "web/src/api/graphql/schema.graphql is stale. Run: python scripts/export_graphql_schema.py"
    )


def test_check_flag_fails_without_writing_when_stale(tmp_path, monkeypatch, capsys):
    stale_path = tmp_path / "schema.graphql"
    stale_path.write_text("type Query { stale: String }\n", encoding="utf-8")
    monkeypatch.setattr(export_module, "SCHEMA_PATH", stale_path)
    monkeypatch.setattr(sys, "argv", ["export_graphql_schema.py", "--check"])

    assert export_module.main() == 1
    assert "stale" in capsys.readouterr().out.casefold()
    assert stale_path.read_text(encoding="utf-8") == "type Query { stale: String }\n"


def test_check_flag_passes_once_the_artifact_is_written(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["export_graphql_schema.py", "--check"])
    assert export_module.main() == 0
