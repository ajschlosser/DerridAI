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

"""Machine-readable compatibility identity for declarative pipelines.

Pipeline Studio, the API, and native binaries all consume the same code-owned
strategy registry.  This module exposes only compatibility facts: it deliberately
does not duplicate labels, presentation metadata, or pipeline definitions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import PipelineDefinition
from .registry import StrategyRegistry, strategy_registry

PIPELINE_CONTRACT_VERSION = 1
MINIMUM_READABLE_PIPELINE_VERSION = 1


class StrategyVersionRequirement(BaseModel):
    """Exact strategy implementation version required by a portable definition."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)


class PipelineContractRequirement(BaseModel):
    """Compatibility facts required to execute one exact pipeline definition."""

    model_config = ConfigDict(extra="forbid")

    pipeline_contract_version: int = Field(ge=1)
    strategies: dict[str, StrategyVersionRequirement]


def pipeline_contract_requirement(
    pipeline: PipelineDefinition,
    registry: StrategyRegistry = strategy_registry,
) -> PipelineContractRequirement:
    """Capture only the strategy versions referenced by one definition."""

    required: dict[str, StrategyVersionRequirement] = {}
    for strategy_id in sorted({stage.strategy for stage in pipeline.stages}):
        spec = registry.get(strategy_id)
        if spec is None:
            raise ValueError(
                f"Pipeline {pipeline.pipeline_id}@{pipeline.version} references "
                f"unknown strategy {strategy_id!r}."
            )
        required[strategy_id] = StrategyVersionRequirement(version=spec.version)
    return PipelineContractRequirement(
        pipeline_contract_version=PIPELINE_CONTRACT_VERSION,
        strategies=required,
    )


def assert_pipeline_contract_compatible(
    pipeline: PipelineDefinition,
    requirement: PipelineContractRequirement,
    registry: StrategyRegistry = strategy_registry,
) -> None:
    """Fail when this runtime cannot execute the definition's frozen contract."""

    if requirement.pipeline_contract_version != PIPELINE_CONTRACT_VERSION:
        raise ValueError(
            "Pipeline contract version "
            f"{requirement.pipeline_contract_version} is not supported by this "
            f"runtime (supports {PIPELINE_CONTRACT_VERSION})."
        )

    for strategy_id in sorted({stage.strategy for stage in pipeline.stages}):
        required = requirement.strategies.get(strategy_id)
        if required is None:
            raise ValueError(
                f"Pipeline contract does not pin strategy {strategy_id!r}."
            )
        current = registry.get(strategy_id)
        if current is None:
            raise ValueError(
                f"This DerridAI runtime does not provide strategy {strategy_id!r}."
            )
        if current.version != required.version:
            raise ValueError(
                f"Pipeline requires strategy {strategy_id} v{required.version}, "
                f"but this DerridAI runtime provides v{current.version}."
            )


def pipeline_contract_identity(
    registry: StrategyRegistry = strategy_registry,
    *,
    application_version: str | None = None,
) -> dict[str, Any]:
    """Return the compatibility identity implemented by this source tree.

    Strategy versions are sorted by stable strategy ID so the same mapping can be
    compared directly across the API catalog, source tests, and compiled binaries.
    """

    if application_version is None:
        from ..config import APP_VERSION

        application_version = APP_VERSION

    return {
        "pipeline_contract_version": PIPELINE_CONTRACT_VERSION,
        "minimum_readable_pipeline_version": MINIMUM_READABLE_PIPELINE_VERSION,
        "application_version": str(application_version),
        "strategies": {
            spec.strategy_id: {"version": spec.version}
            for spec in registry.list()
        },
    }
