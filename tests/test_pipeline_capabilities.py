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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Pipeline contract identity tests shared by API and native CLI surfaces."""

from __future__ import annotations

import json

from app.corpus_cli import ExitCode, main
from app.pipelines.capabilities import pipeline_contract_identity
from app.pipelines.manager import PipelineManager
from app.pipelines.models import StrategySpec
from app.pipelines.registry import StrategyRegistry
from app.pipelines.service import PipelineService
from app.pipelines.store import PipelineStore


def test_contract_identity_reports_exact_strategy_versions():
    registry = StrategyRegistry(
        [
            StrategySpec(
                strategy_id="test.beta",
                version=3,
                family="selection",
                scholarly_effect="advisory",
                label="Beta",
                description="Test strategy beta.",
                input_type="candidate_set",
                output_type="candidate_set",
            ),
            StrategySpec(
                strategy_id="test.alpha",
                version=2,
                family="selection",
                scholarly_effect="advisory",
                label="Alpha",
                description="Test strategy alpha.",
                input_type="candidate_set",
                output_type="candidate_set",
            ),
        ]
    )

    identity = pipeline_contract_identity(registry, application_version="9.9.9")

    assert identity == {
        "pipeline_contract_version": 1,
        "minimum_readable_pipeline_version": 1,
        "application_version": "9.9.9",
        "strategies": {
            "test.alpha": {"version": 2},
            "test.beta": {"version": 3},
        },
    }


def test_cli_pipeline_capabilities_json_uses_shared_identity(capsys):
    code = main(["pipeline", "capabilities", "--json"])
    captured = capsys.readouterr()

    assert code == ExitCode.OK
    assert json.loads(captured.out) == pipeline_contract_identity()
    assert captured.err == ""



def test_catalog_contract_versions_match_the_strategy_catalog(tmp_path):
    """The machine capability identity cannot drift from the catalog clients edit."""

    manager = PipelineManager(
        service=PipelineService(),
        store=PipelineStore(tmp_path / "pipeline-capabilities.sqlite3"),
    )
    catalog = manager.catalog()

    advertised = {
        item["strategy_id"]: {"version": item["version"]}
        for item in catalog["strategies"]
    }
    assert catalog["contract"]["strategies"] == advertised
    assert catalog["contract"]["pipeline_contract_version"] >= 1
