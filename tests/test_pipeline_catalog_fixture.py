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

"""The checked-in Pipeline Studio catalog fixture must match the served pipeline contracts.

Why: Storybook stories and Vitest build their purposes, vocabularies and strategies from
`web/src/components/pipelines/fixtures/pipelineCatalogContract.json`. A purpose or strategy
changed without regenerating it would leave the frontend exercising a contract the API no
longer serves.
How: renders the fixture exactly as `scripts/export_pipeline_catalog_fixture.py` does and
compares bytes; `--check` is exercised so the CLI contract (exit code, message) is covered.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.export_pipeline_catalog_fixture as export_module  # noqa: E402
from scripts.export_pipeline_catalog_fixture import (  # noqa: E402
    COMMAND,
    FIXTURE_PATH,
    rendered_fixture,
)

pytestmark = pytest.mark.contract


def test_the_checked_in_catalog_fixture_is_current():
    assert FIXTURE_PATH.exists(), f"{FIXTURE_PATH} is missing. Run: {COMMAND}"
    assert FIXTURE_PATH.read_text(encoding="utf-8") == rendered_fixture(), (
        f"The Pipeline Studio catalog fixture is stale. Run: {COMMAND}"
    )


def test_check_flag_fails_without_writing_when_stale(tmp_path, monkeypatch, capsys):
    stale_path = tmp_path / "pipelineCatalogContract.json"
    stale_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(export_module, "FIXTURE_PATH", stale_path)
    monkeypatch.setattr(sys, "argv", ["export_pipeline_catalog_fixture.py", "--check"])

    assert export_module.main() == 1
    output = capsys.readouterr().out
    assert "stale" in output.casefold()
    assert COMMAND in output
    assert stale_path.read_text(encoding="utf-8") == "{}\n"


def test_writing_regenerates_a_stale_fixture(tmp_path, monkeypatch):
    stale_path = tmp_path / "fixtures" / "pipelineCatalogContract.json"
    monkeypatch.setattr(export_module, "FIXTURE_PATH", stale_path)
    monkeypatch.setattr(sys, "argv", ["export_pipeline_catalog_fixture.py"])

    assert export_module.main() == 0
    assert stale_path.read_text(encoding="utf-8") == rendered_fixture()
    monkeypatch.setattr(sys, "argv", ["export_pipeline_catalog_fixture.py", "--check"])
    assert export_module.main() == 0
