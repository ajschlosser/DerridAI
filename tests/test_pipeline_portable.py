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

"""Portable PipelineDefinition export/import and compatibility tests."""

from __future__ import annotations

import pytest
from app.pipelines.capabilities import (
    PipelineContractRequirement,
    StrategyVersionRequirement,
)
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.models import PipelineDefinition
from app.pipelines.portable import (
    PipelineDocument,
    export_pipeline_document,
    parse_pipeline_document,
)
from app.pipelines.service import pipeline_hash
from pydantic import ValidationError


def _pipeline() -> PipelineDefinition:
    pipeline = built_in_pipeline("corpus.metadata_enrichment.current", 2)
    assert pipeline is not None
    return pipeline


def test_export_import_preserves_canonical_pipeline_hash():
    pipeline = _pipeline()

    document = export_pipeline_document(pipeline)
    parsed = parse_pipeline_document(document.model_dump(mode="json"))

    assert parsed.format == "derridai-pipeline"
    assert parsed.version == 1
    assert parsed.pipeline_hash == pipeline_hash(pipeline)
    assert pipeline_hash(parsed.pipeline) == pipeline_hash(pipeline)


def test_portable_document_rejects_unknown_execution_fields():
    payload = export_pipeline_document(_pipeline()).model_dump(mode="json")
    payload["pipeline"]["stages"][0]["unexpected"] = "ignored-by-native-model"

    with pytest.raises(ValidationError, match="Unknown pipeline stage field"):
        PipelineDocument.model_validate(payload)


def test_portable_document_rejects_tampered_pipeline_hash():
    payload = export_pipeline_document(_pipeline()).model_dump(mode="json")
    payload["pipeline"]["name"] = "Changed after export"

    with pytest.raises(ValidationError, match="pipeline_hash does not match"):
        PipelineDocument.model_validate(payload)


def test_import_rejects_missing_strategy_version_pin():
    pipeline = _pipeline()
    payload = export_pipeline_document(pipeline).model_dump(mode="json")
    strategy_id = pipeline.stages[0].strategy
    del payload["contract"]["strategies"][strategy_id]

    with pytest.raises(ValueError, match="does not pin strategy"):
        parse_pipeline_document(payload)


def test_import_rejects_incompatible_strategy_version():
    pipeline = _pipeline()
    document = export_pipeline_document(pipeline)
    payload = document.model_dump(mode="json")
    strategy_id = pipeline.stages[0].strategy
    payload["contract"]["strategies"][strategy_id]["version"] += 1

    with pytest.raises(ValueError, match="Pipeline requires strategy"):
        parse_pipeline_document(payload)


def test_pipeline_document_contract_is_strict():
    pipeline = _pipeline()
    document = export_pipeline_document(pipeline)
    requirement = PipelineContractRequirement(
        pipeline_contract_version=document.contract.pipeline_contract_version,
        strategies={
            key: StrategyVersionRequirement(version=value.version)
            for key, value in document.contract.strategies.items()
        },
    )
    payload = {
        **document.model_dump(mode="json"),
        "contract": requirement.model_dump(mode="json"),
        "extra": True,
    }

    with pytest.raises(ValidationError):
        PipelineDocument.model_validate(payload)
