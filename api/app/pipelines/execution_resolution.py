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

"""Resolve an executable pipeline from a frozen run binding or system assignment.

Ordinary web/API execution continues to resolve Pipeline Studio's current system
assignment. A portable headless run may instead carry "_pipeline_bindings" in
its server-owned build request. Those bindings are validated before the build is
created and are revalidated here so a resumed build cannot silently execute a
different strategy implementation after an application upgrade.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .compatibility import validate_pipeline_strategy_requirements
from .models import PipelineConfigOverrideSet, PipelineDefinition
from .overrides import resolve_pipeline_config
from .service import pipeline_hash

RUN_PIPELINE_BINDINGS_KEY = "_pipeline_bindings"


def execution_pipeline_bindings(
    request: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    """Return the internal feature-binding mapping carried by one build request."""

    if not isinstance(request, Mapping):
        return {}
    value = request.get(RUN_PIPELINE_BINDINGS_KEY)
    return value if isinstance(value, Mapping) else {}


def resolve_execution_pipeline(
    feature: str,
    request: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve one feature, preferring a frozen run-envelope binding when present."""

    raw = execution_pipeline_bindings(request).get(feature)
    if raw is None:
        from .manager import pipeline_manager

        return pipeline_manager.resolve(feature)
    if not isinstance(raw, Mapping):
        raise ValueError(f"Frozen pipeline binding for {feature!r} is malformed.")

    definition_payload = raw.get("definition")
    if not isinstance(definition_payload, Mapping):
        raise ValueError(
            f"Frozen pipeline binding for {feature!r} has no pipeline definition."
        )
    definition = PipelineDefinition.model_validate(definition_payload)
    if definition.purpose != feature:
        raise ValueError(
            f"Frozen pipeline binding for {feature!r} has purpose "
            f"{definition.purpose!r}."
        )

    expected_hash = str(raw.get("pipeline_hash") or "")
    actual_hash = pipeline_hash(definition)
    if expected_hash != actual_hash:
        raise ValueError(
            f"Frozen pipeline binding for {feature!r} failed its canonical hash check."
        )

    requirements = raw.get("required_strategies")
    if not isinstance(requirements, Mapping) or not requirements:
        raise ValueError(
            f"Frozen pipeline binding for {feature!r} has no strategy-version requirements."
        )
    validate_pipeline_strategy_requirements(
        {str(key): int(value) for key, value in requirements.items()}
    )

    overrides_payload = raw.get("overrides")
    overrides = (
        PipelineConfigOverrideSet.model_validate(overrides_payload)
        if isinstance(overrides_payload, Mapping)
        else None
    )
    resolution = resolve_pipeline_config(
        definition,
        run_overrides=overrides,
    )
    effective = resolution.effective
    return {
        "pipeline": effective.model_dump(mode="json"),
        "pipeline_hash": resolution.effective_hash,
        "baseline_pipeline_hash": resolution.baseline_hash,
        "assignment": {
            "feature": feature,
            "pipeline_id": definition.pipeline_id,
            "pipeline_version": definition.version,
            "source": "run_envelope",
            "override_allowed": overrides is not None,
        },
        "config_resolution": resolution.summary(),
        "source": "run_envelope",
    }
