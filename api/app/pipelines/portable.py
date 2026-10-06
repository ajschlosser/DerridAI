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

"""Portable, strict serialization for immutable pipeline definitions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .capabilities import (
    PipelineContractRequirement,
    assert_pipeline_contract_compatible,
    pipeline_contract_requirement,
)
from .models import InputBinding, PipelineDefinition, PipelineStageDefinition
from .registry import StrategyRegistry, strategy_registry
from .service import PipelineService, pipeline_hash, pipeline_service


def _unknown_keys(payload: object, model: type[BaseModel]) -> list[str]:
    if not isinstance(payload, dict):
        return []
    return sorted(set(payload) - set(model.model_fields))


def reject_unknown_pipeline_fields(value: object) -> object:
    """Reject executable fields that the native model would otherwise ignore.

    Native pipeline persistence remains backward-readable, but portable imports
    are a trust boundary. Unknown graph, stage, or binding fields therefore fail
    before the definition is interpreted.
    """

    if not isinstance(value, dict):
        return value

    unknown = _unknown_keys(value, PipelineDefinition)
    if unknown:
        raise ValueError(
            "Unknown pipeline definition field(s): " + ", ".join(unknown)
        )

    stages = value.get("stages")
    if not isinstance(stages, list):
        return value

    for index, stage in enumerate(stages):
        stage_unknown = _unknown_keys(stage, PipelineStageDefinition)
        if stage_unknown:
            raise ValueError(
                f"Unknown pipeline stage field(s) at stages[{index}]: "
                + ", ".join(stage_unknown)
            )
        if not isinstance(stage, dict):
            continue
        inputs = stage.get("inputs")
        if not isinstance(inputs, dict):
            continue
        for port_name, bindings in inputs.items():
            if not isinstance(bindings, list):
                continue
            for binding_index, binding in enumerate(bindings):
                binding_unknown = _unknown_keys(binding, InputBinding)
                if binding_unknown:
                    raise ValueError(
                        "Unknown pipeline input-binding field(s) at "
                        f"stages[{index}].inputs[{port_name!r}][{binding_index}]: "
                        + ", ".join(binding_unknown)
                    )
    return value


class PipelineDocument(BaseModel):
    """Self-describing pipeline definition for API, Studio, and CLI exchange."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["derridai-pipeline"]
    version: Literal[1]
    contract: PipelineContractRequirement
    pipeline_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    pipeline: PipelineDefinition

    @field_validator("pipeline", mode="before")
    @classmethod
    def reject_unknown_definition_fields(cls, value: object) -> object:
        return reject_unknown_pipeline_fields(value)

    @model_validator(mode="after")
    def validate_hash(self) -> "PipelineDocument":
        actual = pipeline_hash(self.pipeline)
        if self.pipeline_hash != actual:
            raise ValueError(
                "pipeline_hash does not match the canonical PipelineDefinition."
            )
        return self


def export_pipeline_document(
    pipeline: PipelineDefinition,
    *,
    registry: StrategyRegistry = strategy_registry,
) -> PipelineDocument:
    """Create one deterministic portable document from a canonical definition."""

    return PipelineDocument(
        format="derridai-pipeline",
        version=1,
        contract=pipeline_contract_requirement(pipeline, registry),
        pipeline_hash=pipeline_hash(pipeline),
        pipeline=pipeline.model_copy(deep=True),
    )


def validate_pipeline_document(
    document: PipelineDocument,
    *,
    service: PipelineService = pipeline_service,
) -> PipelineDefinition:
    """Validate compatibility and graph semantics without persisting anything."""

    assert_pipeline_contract_compatible(
        document.pipeline,
        document.contract,
        service.registry,
    )
    validation = service.validate(document.pipeline)
    errors = [issue.message for issue in validation.issues if issue.level == "error"]
    if errors:
        raise ValueError(
            f"Pipeline {document.pipeline.pipeline_id}@{document.pipeline.version} "
            "is invalid: "
            + "; ".join(errors)
        )
    return document.pipeline


def parse_pipeline_document(
    payload: Any,
    *,
    service: PipelineService = pipeline_service,
) -> PipelineDocument:
    """Parse and fully validate an imported portable pipeline document."""

    document = PipelineDocument.model_validate(payload)
    validate_pipeline_document(document, service=service)
    return document
