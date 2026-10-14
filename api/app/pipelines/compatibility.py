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

"""Compatibility identity shared by Pipeline Studio, APIs, and native clients.

A released native binary is a frozen implementation of the pipeline strategies
that were present when it was built.  This module gives every client one small,
machine-readable compatibility surface instead of making the CLI infer support
from presentation-oriented catalog data.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..config import APP_VERSION
from .models import PipelineDefinition
from .registry import StrategyRegistry, strategy_registry

PIPELINE_CONTRACT_VERSION = 1
MINIMUM_READABLE_PIPELINE_VERSION = 1


def pipeline_contract_identity(
    registry: StrategyRegistry | None = None,
) -> dict[str, Any]:
    """Return the exact pipeline implementation identity of this application."""

    active = registry or strategy_registry
    return {
        "pipeline_contract_version": PIPELINE_CONTRACT_VERSION,
        "minimum_readable_pipeline_version": MINIMUM_READABLE_PIPELINE_VERSION,
        "application_version": APP_VERSION,
        "strategies": {
            spec.strategy_id: {"version": int(spec.version)}
            for spec in active.list()
        },
    }


def validate_pipeline_contract_version(version: int) -> None:
    """Require a contract version that this runtime explicitly declares readable."""

    parsed = int(version)
    if parsed < MINIMUM_READABLE_PIPELINE_VERSION:
        raise ValueError(
            f"Pipeline contract version {parsed} is older than this DerridAI runtime "
            f"can read (minimum {MINIMUM_READABLE_PIPELINE_VERSION})."
        )
    if parsed > PIPELINE_CONTRACT_VERSION:
        raise ValueError(
            f"Pipeline contract version {parsed} is newer than this DerridAI runtime "
            f"supports (current {PIPELINE_CONTRACT_VERSION})."
        )


def pipeline_strategy_requirements(
    definition: PipelineDefinition,
    *,
    registry: StrategyRegistry | None = None,
) -> dict[str, int]:
    """Pin the strategy versions needed by one immutable pipeline definition."""

    active = registry or strategy_registry
    requirements: dict[str, int] = {}
    for stage in definition.stages:
        spec = active.get(stage.strategy)
        if spec is None:
            raise ValueError(
                f"Pipeline {definition.pipeline_id}@{definition.version} references "
                f"unavailable strategy {stage.strategy!r}."
            )
        requirements[spec.strategy_id] = int(spec.version)
    return dict(sorted(requirements.items()))


def validate_pipeline_strategy_requirements(
    requirements: Mapping[str, int],
    *,
    registry: StrategyRegistry | None = None,
) -> None:
    """Reject an exported definition whose strategy implementation has drifted.

    Exact equality is deliberate.  A strategy-version change is an implementation
    contract change; silently running a saved definition against another version
    would make the pipeline hash look stable while changing execution semantics.
    """

    active = registry or strategy_registry
    for strategy_id, required_version in sorted(requirements.items()):
        spec = active.get(str(strategy_id))
        if spec is None:
            raise ValueError(
                f"Pipeline requires strategy {strategy_id!r}, which this DerridAI "
                "installation does not provide."
            )
        available_version = int(spec.version)
        expected_version = int(required_version)
        if available_version != expected_version:
            raise ValueError(
                f"Pipeline requires {strategy_id} v{expected_version}; this DerridAI "
                f"installation provides v{available_version}."
            )
