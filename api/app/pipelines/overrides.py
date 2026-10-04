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

"""Resolve layered stage configuration without changing pipeline structure.

The immutable Pipeline Studio definition is the baseline. Settings overrides are
applied next, and one-run overrides last. Every override remains bound to the
exact pipeline ID/version it was authored against; a stale stage/key is rejected
rather than silently mapped onto another version.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .models import (
    PipelineConfigOverrideSet,
    PipelineDefinition,
    PipelineStageDefinition,
)
from .service import PipelineService, pipeline_hash, pipeline_service

OverrideLayer = Literal["settings", "run"]


@dataclass(frozen=True, slots=True)
class PipelineConfigResolution:
    """Baseline/effective pipeline pair plus auditable value provenance."""

    baseline: PipelineDefinition
    effective: PipelineDefinition
    baseline_hash: str
    effective_hash: str
    settings_overrides: PipelineConfigOverrideSet | None
    run_overrides: PipelineConfigOverrideSet | None
    provenance: dict[str, dict[str, dict[str, Any]]]

    def summary(self) -> dict[str, Any]:
        return {
            "precedence": ["pipeline", "settings", "run"],
            "baseline_pipeline_hash": self.baseline_hash,
            "effective_pipeline_hash": self.effective_hash,
            "settings_overrides": (
                self.settings_overrides.model_dump(mode="json")
                if self.settings_overrides is not None
                else None
            ),
            "run_overrides": (
                self.run_overrides.model_dump(mode="json")
                if self.run_overrides is not None
                else None
            ),
            "values": self.provenance,
        }


def _require_matching_identity(
    pipeline: PipelineDefinition,
    override_set: PipelineConfigOverrideSet | None,
    layer: OverrideLayer,
) -> None:
    if override_set is None or override_set.empty:
        return
    if (
        override_set.pipeline_id != pipeline.pipeline_id
        or override_set.pipeline_version != pipeline.version
    ):
        raise ValueError(
            f"{layer.capitalize()} pipeline overrides target "
            f"{override_set.pipeline_id}@{override_set.pipeline_version}, but this run uses "
            f"{pipeline.pipeline_id}@{pipeline.version}. Recreate the override for the selected "
            "pipeline version."
        )


def _stage_map(pipeline: PipelineDefinition) -> dict[str, PipelineStageDefinition]:
    return {stage.id: stage for stage in pipeline.stages}


def _validate_patch(
    service: PipelineService,
    stage: PipelineStageDefinition,
    patch: dict[str, Any],
    *,
    layer: OverrideLayer,
) -> None:
    # Validate the merged config so a patch cannot hide an existing incompatible
    # value and so generic stage flags such as "optional" retain their normal rule.
    merged = {**stage.config, **patch}
    issues = service.validate_stage_config(
        stage_id=stage.id,
        strategy_id=stage.strategy,
        config=merged,
    )
    errors = [issue.message for issue in issues if issue.level == "error"]
    if errors:
        raise ValueError(
            f"{layer.capitalize()} override for stage {stage.id!r} is invalid: "
            + "; ".join(errors)
        )


def _apply_layer(
    pipeline: PipelineDefinition,
    override_set: PipelineConfigOverrideSet | None,
    *,
    layer: OverrideLayer,
    service: PipelineService,
) -> PipelineDefinition:
    if override_set is None or override_set.empty:
        return pipeline
    stages = _stage_map(pipeline)
    patched: list[PipelineStageDefinition] = []
    for stage in pipeline.stages:
        patch = override_set.stages.get(stage.id)
        if not patch:
            patched.append(stage)
            continue
        _validate_patch(service, stage, patch, layer=layer)
        patched.append(
            stage.model_copy(
                deep=True,
                update={"config": {**stage.config, **patch}},
            )
        )

    missing = sorted(set(override_set.stages) - set(stages))
    if missing:
        raise ValueError(
            f"{layer.capitalize()} overrides reference stage(s) not present in "
            f"{pipeline.pipeline_id}@{pipeline.version}: {', '.join(missing)}."
        )
    return pipeline.model_copy(deep=True, update={"stages": patched})


def _provenance(
    baseline: PipelineDefinition,
    settings: PipelineConfigOverrideSet | None,
    run: PipelineConfigOverrideSet | None,
    effective: PipelineDefinition,
) -> dict[str, dict[str, dict[str, Any]]]:
    baseline_stages = _stage_map(baseline)
    effective_stages = _stage_map(effective)
    stage_ids = set(baseline_stages)
    if settings is not None:
        stage_ids.update(settings.stages)
    if run is not None:
        stage_ids.update(run.stages)

    resolved: dict[str, dict[str, dict[str, Any]]] = {}
    for stage_id in sorted(stage_ids):
        baseline_config = dict((baseline_stages.get(stage_id) or PipelineStageDefinition(
            id=stage_id,
            strategy="missing",
        )).config)
        settings_config = dict(settings.stages.get(stage_id) or {}) if settings else {}
        run_config = dict(run.stages.get(stage_id) or {}) if run else {}
        effective_config = dict((effective_stages.get(stage_id) or PipelineStageDefinition(
            id=stage_id,
            strategy="missing",
        )).config)
        keys = set(baseline_config) | set(settings_config) | set(run_config)
        if not keys:
            continue
        stage_values: dict[str, dict[str, Any]] = {}
        for key in sorted(keys):
            source = "pipeline"
            if key in settings_config:
                source = "settings"
            if key in run_config:
                source = "run"
            stage_values[key] = {
                "pipeline": baseline_config.get(key),
                "settings": settings_config.get(key) if key in settings_config else None,
                "run": run_config.get(key) if key in run_config else None,
                "effective": effective_config.get(key),
                "source": source,
            }
        resolved[stage_id] = stage_values
    return resolved


def resolve_pipeline_config(
    pipeline: PipelineDefinition,
    *,
    settings_overrides: PipelineConfigOverrideSet | None = None,
    run_overrides: PipelineConfigOverrideSet | None = None,
    service: PipelineService = pipeline_service,
) -> PipelineConfigResolution:
    """Apply Settings then run overrides to one immutable pipeline definition."""

    _require_matching_identity(pipeline, settings_overrides, "settings")
    _require_matching_identity(pipeline, run_overrides, "run")

    after_settings = _apply_layer(
        pipeline,
        settings_overrides,
        layer="settings",
        service=service,
    )
    effective = _apply_layer(
        after_settings,
        run_overrides,
        layer="run",
        service=service,
    )

    # Re-run whole-pipeline validation after patching. Config-only changes are
    # not allowed to weaken or bypass graph/provenance invariants.
    validation = service.validate(effective)
    errors = [issue.message for issue in validation.issues if issue.level == "error"]
    if errors:
        raise ValueError(
            "Effective Research pipeline configuration is invalid: " + "; ".join(errors)
        )

    return PipelineConfigResolution(
        baseline=pipeline,
        effective=effective,
        baseline_hash=pipeline_hash(pipeline),
        effective_hash=pipeline_hash(effective),
        settings_overrides=settings_overrides,
        run_overrides=run_overrides,
        provenance=_provenance(
            pipeline,
            settings_overrides,
            run_overrides,
            effective,
        ),
    )
