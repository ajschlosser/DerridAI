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

from __future__ import annotations

import pytest
from app.pipelines.contracts import input_ports, output_ports
from app.pipelines.defaults import BUILT_IN_PIPELINES
from app.pipelines.models import PipelineDefinition
from app.pipelines.registry import strategy_registry
from app.pipelines.service import PipelineService, pipeline_hash
from pydantic import ValidationError


def test_legacy_strategy_ports_keep_their_declared_types() -> None:
    spec = strategy_registry.require("retrieve.lexical_bm25").model_copy(
        update={"inputs": [], "outputs": []}
    )
    assert input_ports(spec)[0].model_dump()["data_type"] == spec.input_type
    assert output_ports(spec)[0].model_dump()["data_type"] == spec.output_type
    assert input_ports(spec)[0].required is True
    any_input = spec.model_copy(update={"input_type": "any"})
    assert input_ports(any_input)[0].required is False


@pytest.mark.parametrize("direction", ["input", "output"])
def test_legacy_strategy_ports_reject_unknown_types(direction: str) -> None:
    spec = strategy_registry.require("retrieve.lexical_bm25").model_copy(
        update={"inputs": [], "outputs": [], f"{direction}_type": "not-a-port-type"}
    )
    with pytest.raises(ValidationError) as exc:
        (input_ports if direction == "input" else output_ports)(spec)
    assert exc.value.errors()[0]["loc"] == ("data_type",)


def test_built_in_pipeline_catalog_is_graph_valid() -> None:
    service = PipelineService()

    results = {
        (item.pipeline_id, item.version): service.validate(item)
        for item in BUILT_IN_PIPELINES
    }

    assert results
    for pipeline_key, result in results.items():
        assert result.valid, (pipeline_key, result.model_dump())

    reviewer = results[("evidence.reviewer.current", 2)]
    reviewer_codes = {issue.code for issue in reviewer.issues}
    assert "evidence_without_support_gate" not in reviewer_codes
    assert "evidence_without_provenance_gate" not in reviewer_codes

    legacy = results[("evidence.reviewer.current", 1)]
    legacy_codes = {issue.code for issue in legacy.issues}
    assert "evidence_without_support_gate" in legacy_codes
    assert "evidence_without_provenance_gate" in legacy_codes


def test_pipeline_validator_rejects_pinned_strategy_version_mismatch() -> None:
    service = PipelineService()
    source = next(item for item in BUILT_IN_PIPELINES if item.pipeline_id == "research.current")
    first = source.stages[0]
    incompatible = source.model_copy(
        deep=True,
        update={
            "pipeline_id": "research.imported-old-strategy",
            "built_in": False,
            "stages": [
                first.model_copy(update={"strategy_version": 999}),
                *source.stages[1:],
            ],
        },
    )

    result = service.validate(incompatible)

    assert result.valid is False
    issue = next(item for item in result.issues if item.code == "strategy_version_mismatch")
    assert issue.stage_id == first.id
    assert str(first.strategy) in issue.message
    assert "version 999" in issue.message
    assert "Migrate the stage" in issue.message


def test_pipeline_without_strategy_version_pin_keeps_legacy_hash_shape() -> None:
    source = next(item for item in BUILT_IN_PIPELINES if item.pipeline_id == "research.current")
    payload = source.model_dump(mode="json")

    assert all("strategy_version" not in stage for stage in payload["stages"])
    reconstructed = PipelineDefinition.model_validate(payload)
    assert pipeline_hash(reconstructed) == pipeline_hash(source)


def test_pipeline_validator_rejects_unknown_strategy_and_cycles() -> None:
    service = PipelineService()
    pipeline = PipelineDefinition.model_validate(
        {
            "pipeline_id": "broken",
            "version": 1,
            "name": "Broken",
            "purpose": "test",
            "entry_stage_ids": ["a"],
            "stages": [
                {
                    "id": "a",
                    "strategy": "retrieve.lexical_bm25",
                    "next": ["b"],
                },
                {
                    "id": "b",
                    "strategy": "missing.strategy",
                    "next": ["a"],
                },
            ],
        }
    )

    result = service.validate(pipeline)

    assert result.valid is False
    codes = {issue.code for issue in result.issues}
    assert "unknown_strategy" in codes
    assert "cycle" in codes


def test_pipeline_validator_checks_stage_contract_types() -> None:
    service = PipelineService()
    pipeline = PipelineDefinition.model_validate(
        {
            "pipeline_id": "bad-types",
            "version": 1,
            "name": "Bad types",
            "purpose": "test",
            "entry_stage_ids": ["retrieve"],
            "stages": [
                {
                    "id": "retrieve",
                    "strategy": "retrieve.chroma_similarity",
                    "next": ["generate"],
                },
                {
                    "id": "generate",
                    "strategy": "llm.generate_answer",
                },
            ],
        }
    )

    result = service.validate(pipeline)

    assert result.valid is False
    assert any(issue.code == "incompatible_stage_types" for issue in result.issues)


def test_pipeline_hash_is_stable_for_equivalent_model_dumps() -> None:
    pipeline = next(item for item in BUILT_IN_PIPELINES if item.pipeline_id == "research.current")
    reconstructed = PipelineDefinition.model_validate(pipeline.model_dump(mode="json"))

    assert pipeline_hash(pipeline) == pipeline_hash(reconstructed)


def test_builtin_resolution_exposes_assignment_pipeline_and_validation() -> None:
    result = PipelineService().resolve_builtin("research")

    assert result["assignment"]["pipeline_id"] == "research.current"
    assert result["pipeline"]["purpose"] == "research"
    assert result["validation"]["valid"] is True
    assert len(result["pipeline_hash"]) == 64



def test_pipeline_validator_rejects_unknown_config_keys() -> None:
    service = PipelineService()
    pipeline = PipelineDefinition.model_validate(
        {
            "pipeline_id": "bad-config",
            "version": 1,
            "name": "Bad config",
            "purpose": "test",
            "entry_stage_ids": ["retrieve"],
            "stages": [
                {
                    "id": "retrieve",
                    "strategy": "retrieve.lexical_bm25",
                    "config": {"fetch_kk": 25},
                    "next": ["select"],
                },
                {
                    "id": "select",
                    "strategy": "select.top_k",
                    "config": {"limit": 5},
                },
            ],
        }
    )

    result = service.validate(pipeline)

    assert result.valid is False
    assert any(issue.code == "unknown_config_key" for issue in result.issues)



def test_active_evidence_pipeline_without_required_gates_is_invalid() -> None:
    service = PipelineService()
    legacy = next(
        item
        for item in BUILT_IN_PIPELINES
        if item.pipeline_id == "evidence.reviewer.current" and item.version == 1
    )
    active = legacy.model_copy(
        update={
            "pipeline_id": "evidence.unsafe",
            "status": "active",
            "built_in": False,
        }
    )

    result = service.validate(active)

    assert result.valid is False
    codes = {issue.code for issue in result.issues}
    assert "evidence_without_support_gate" in codes
    assert "evidence_without_provenance_gate" in codes
