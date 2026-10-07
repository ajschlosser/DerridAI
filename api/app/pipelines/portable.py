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

"""Strict portable serialization for immutable pipeline definitions.

The portable document is deliberately smaller than the full Pipeline Studio
catalog. It carries exactly one canonical definition, its canonical hash, the
pipeline-contract version, and the strategy implementation versions required to
execute that definition. Unknown executable fields are rejected at this import
boundary instead of being silently discarded by permissive historical models.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .compatibility import (
    PIPELINE_CONTRACT_VERSION,
    pipeline_strategy_requirements,
    validate_pipeline_strategy_requirements,
)
from .models import InputBinding, PipelineDefinition, PipelineStageDefinition
from .registry import StrategyRegistry, strategy_registry
from .service import PipelineService, pipeline_hash, pipeline_service


def _unknown_keys(payload: object, model: type[BaseModel]) -> list[str]:
    if not isinstance(payload, Mapping):
        return []
    return sorted(set(payload) - set(model.model_fields))


def reject_unknown_pipeline_fields(value: object) -> object:
    """Reject graph fields that the native persistence model might ignore."""

    if not isinstance(value, Mapping):
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
        if not isinstance(stage, Mapping):
            continue
        inputs = stage.get("inputs")
        if not isinstance(inputs, Mapping):
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
    """One immutable pipeline definition plus exact runtime requirements."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["derridai-pipeline"]
    version: Literal[1]
    pipeline_contract_version: int = Field(ge=1)
    required_strategies: dict[str, int] = Field(min_length=1, max_length=64)
    pipeline_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    pipeline: PipelineDefinition

    @field_validator("pipeline", mode="before")
    @classmethod
    def reject_unknown_definition_fields(cls, value: object) -> object:
        return reject_unknown_pipeline_fields(value)

    @field_validator("required_strategies")
    @classmethod
    def normalize_strategy_versions(cls, value: dict[str, int]) -> dict[str, int]:
        normalized: dict[str, int] = {}
        for strategy_id, version in value.items():
            key = str(strategy_id).strip()
            if not key:
                raise ValueError("Strategy IDs cannot be empty.")
            parsed = int(version)
            if parsed < 1:
                raise ValueError("Strategy versions must be positive integers.")
            normalized[key] = parsed
        return dict(sorted(normalized.items()))

    @model_validator(mode="after")
    def validate_identity(self) -> "PipelineDocument":
        if self.pipeline_contract_version != PIPELINE_CONTRACT_VERSION:
            raise ValueError(
                "Pipeline contract version "
                f"{self.pipeline_contract_version} is not supported by this runtime "
                f"(supports {PIPELINE_CONTRACT_VERSION})."
            )

        actual_hash = pipeline_hash(self.pipeline)
        if actual_hash != self.pipeline_hash:
            raise ValueError(
                "pipeline_hash does not match the canonical PipelineDefinition."
            )

        strategies = {stage.strategy for stage in self.pipeline.stages}
        if set(self.required_strategies) != strategies:
            missing = sorted(strategies - set(self.required_strategies))
            extra = sorted(set(self.required_strategies) - strategies)
            details: list[str] = []
            if missing:
                details.append("missing " + ", ".join(missing))
            if extra:
                details.append("unexpected " + ", ".join(extra))
            raise ValueError(
                "Pipeline strategy requirements do not match the definition"
                + (": " + "; ".join(details) if details else ".")
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
        pipeline_contract_version=PIPELINE_CONTRACT_VERSION,
        required_strategies=pipeline_strategy_requirements(
            pipeline,
            registry=registry,
        ),
        pipeline_hash=pipeline_hash(pipeline),
        pipeline=pipeline.model_copy(deep=True),
    )


def validate_pipeline_document(
    document: PipelineDocument,
    *,
    service: PipelineService = pipeline_service,
) -> PipelineDefinition:
    """Validate runtime compatibility and graph semantics without persisting."""

    validate_pipeline_strategy_requirements(
        document.required_strategies,
        registry=service.registry,
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
    """Parse and fully validate one imported portable pipeline document."""

    document = PipelineDocument.model_validate(payload)
    validate_pipeline_document(document, service=service)
    return document
