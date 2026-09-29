# Copyright 2026 Aaron John Schlosser, PhD.
"""Validation and resolution services for declarative pipelines."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from typing import Any

from .defaults import (
    BUILT_IN_ASSIGNMENTS,
    BUILT_IN_PIPELINES,
    built_in_assignment,
    built_in_pipeline,
)
from .models import (
    PipelineAssignment,
    PipelineDefinition,
    PipelineValidationIssue,
    PipelineValidationResult,
)
from .registry import StrategyRegistry, strategy_registry


def canonical_pipeline_json(pipeline: PipelineDefinition) -> str:
    """Stable serialized form used to bind execution traces to an exact chain."""

    return json.dumps(
        pipeline.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def pipeline_hash(pipeline: PipelineDefinition) -> str:
    return hashlib.sha256(canonical_pipeline_json(pipeline).encode("utf-8")).hexdigest()


class PipelineService:
    """Read/validate/resolve pipeline definitions against the strategy registry.

    Persistence is injected later by the application service layer. Keeping graph
    validation here means API, tests, migrations, and future CLI tooling share
    exactly the same safety rules.
    """

    def __init__(self, registry: StrategyRegistry = strategy_registry) -> None:
        self.registry = registry

    def strategies(self) -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in self.registry.list()]

    def built_in_pipelines(self) -> list[PipelineDefinition]:
        return list(BUILT_IN_PIPELINES)

    def built_in_assignments(self) -> list[PipelineAssignment]:
        return list(BUILT_IN_ASSIGNMENTS)

    def validate(self, pipeline: PipelineDefinition) -> PipelineValidationResult:
        issues: list[PipelineValidationIssue] = []
        stages = {stage.id: stage for stage in pipeline.stages}
        strategy_specs = {}

        for stage in pipeline.stages:
            spec = self.registry.get(stage.strategy)
            if spec is None:
                issues.append(
                    PipelineValidationIssue(
                        level="error",
                        code="unknown_strategy",
                        stage_id=stage.id,
                        message=f"Stage {stage.id!r} references unknown strategy {stage.strategy!r}.",
                    )
                )
                continue
            strategy_specs[stage.id] = spec
            issues.extend(self._validate_config(stage.id, stage.config, spec.config_schema))

        incoming: dict[str, set[str]] = defaultdict(set)
        for stage in pipeline.stages:
            for target in stage.edge_targets():
                incoming[target].add(stage.id)
                source_spec = strategy_specs.get(stage.id)
                target_spec = strategy_specs.get(target)
                if source_spec is None or target_spec is None:
                    continue
                if not self._types_compatible(source_spec.output_type, target_spec.input_type):
                    issues.append(
                        PipelineValidationIssue(
                            level="error",
                            code="incompatible_stage_types",
                            stage_id=stage.id,
                            message=(
                                f"{stage.id!r} outputs {source_spec.output_type!r}, but "
                                f"{target!r} expects {target_spec.input_type!r}."
                            ),
                        )
                    )

        reachable = self._reachable(pipeline)
        unreachable = sorted(set(stages) - reachable)
        for stage_id in unreachable:
            issues.append(
                PipelineValidationIssue(
                    level="error",
                    code="unreachable_stage",
                    stage_id=stage_id,
                    message=f"Stage {stage_id!r} is not reachable from a pipeline entry stage.",
                )
            )

        if self._has_cycle(pipeline):
            issues.append(
                PipelineValidationIssue(
                    level="error",
                    code="cycle",
                    message="Pipeline graphs must be acyclic.",
                )
            )

        terminal_ids = [
            stage.id for stage in pipeline.stages if not stage.edge_targets() and stage.enabled
        ]
        if not terminal_ids:
            issues.append(
                PipelineValidationIssue(
                    level="error",
                    code="missing_terminal",
                    message="Pipeline needs at least one enabled terminal stage.",
                )
            )

        # These are warnings rather than hard errors while legacy production
        # paths are being migrated. Once every evidence path has a support gate,
        # the migration can promote this to a required purpose contract.
        if pipeline.purpose == "evidence_suggestion":
            families = {
                strategy_specs[stage.id].family
                for stage in pipeline.stages
                if stage.id in strategy_specs and stage.enabled
            }
            if "support_validation" not in families:
                issues.append(
                    PipelineValidationIssue(
                        level="warning",
                        code="evidence_without_support_gate",
                        message=(
                            "This evidence pipeline ranks candidates without an explicit "
                            "support/provenance validation stage."
                        ),
                    )
                )

        return PipelineValidationResult(
            valid=not any(issue.level == "error" for issue in issues),
            issues=issues,
        )

    def resolve_builtin(self, feature: str) -> dict[str, Any]:
        assignment = built_in_assignment(feature)
        if assignment is None:
            raise KeyError(feature)
        pipeline = built_in_pipeline(assignment.pipeline_id, assignment.pipeline_version)
        if pipeline is None:
            raise KeyError(f"{assignment.pipeline_id}@{assignment.pipeline_version}")
        validation = self.validate(pipeline)
        return {
            "assignment": assignment.model_dump(mode="json"),
            "pipeline": pipeline.model_dump(mode="json"),
            "pipeline_hash": pipeline_hash(pipeline),
            "validation": validation.model_dump(mode="json"),
        }

    @staticmethod
    def _types_compatible(source: str, target: str) -> bool:
        return source == target or source == "any" or target == "any"

    @staticmethod
    def _reachable(pipeline: PipelineDefinition) -> set[str]:
        stages = {stage.id: stage for stage in pipeline.stages}
        seen: set[str] = set()
        queue = deque(pipeline.entry_stage_ids)
        while queue:
            stage_id = queue.popleft()
            if stage_id in seen or stage_id not in stages:
                continue
            seen.add(stage_id)
            queue.extend(stages[stage_id].edge_targets())
        return seen

    @staticmethod
    def _has_cycle(pipeline: PipelineDefinition) -> bool:
        stages = {stage.id: stage for stage in pipeline.stages}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(stage_id: str) -> bool:
            if stage_id in visiting:
                return True
            if stage_id in visited:
                return False
            visiting.add(stage_id)
            for target in stages[stage_id].edge_targets():
                if visit(target):
                    return True
            visiting.remove(stage_id)
            visited.add(stage_id)
            return False

        return any(visit(stage_id) for stage_id in stages if stage_id not in visited)

    @staticmethod
    def _validate_config(
        stage_id: str,
        config: dict[str, Any],
        schema: dict[str, Any],
    ) -> list[PipelineValidationIssue]:
        """Validate the small JSON-schema subset emitted by the strategy registry.

        The registry currently uses object/property/type/minimum/maximum rules.
        Keeping this validator intentionally narrow avoids accepting config
        keywords the runtime does not actually enforce.
        """

        issues: list[PipelineValidationIssue] = []
        properties = schema.get("properties") if isinstance(schema, dict) else None
        if not isinstance(properties, dict):
            return issues
        unknown = sorted(set(config) - set(properties) - {"optional"})
        for key in unknown:
            issues.append(
                PipelineValidationIssue(
                    level="warning",
                    code="unknown_config_key",
                    stage_id=stage_id,
                    message=f"Configuration key {key!r} is not declared by this strategy.",
                )
            )

        for key, rule in properties.items():
            if key not in config or not isinstance(rule, dict):
                continue
            value = config[key]
            expected = rule.get("type")
            valid_type = True
            if expected == "integer":
                valid_type = isinstance(value, int) and not isinstance(value, bool)
            elif expected == "number":
                valid_type = isinstance(value, (int, float)) and not isinstance(value, bool)
            elif expected == "string":
                valid_type = isinstance(value, str)
            elif expected == "boolean":
                valid_type = isinstance(value, bool)
            if not valid_type:
                issues.append(
                    PipelineValidationIssue(
                        level="error",
                        code="invalid_config_type",
                        stage_id=stage_id,
                        message=f"Configuration {key!r} must be {expected}.",
                    )
                )
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                minimum = rule.get("minimum")
                maximum = rule.get("maximum")
                if minimum is not None and value < minimum:
                    issues.append(
                        PipelineValidationIssue(
                            level="error",
                            code="config_below_minimum",
                            stage_id=stage_id,
                            message=f"Configuration {key!r} must be at least {minimum}.",
                        )
                    )
                if maximum is not None and value > maximum:
                    issues.append(
                        PipelineValidationIssue(
                            level="error",
                            code="config_above_maximum",
                            stage_id=stage_id,
                            message=f"Configuration {key!r} must be at most {maximum}.",
                        )
                    )
        return issues


pipeline_service = PipelineService()
