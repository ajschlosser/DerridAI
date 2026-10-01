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
from .purposes import FAMILY_PHASES, effect_note, purpose_registry
from .registry import StrategyRegistry, strategy_registry
from .wiring import ordering_only_edges, resolve_wiring


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
        """Serialize strategy contracts with stable localization keys.

        The server remains authoritative for strategy identity and fallback
        English copy. Clients resolve these keys through the normal locale
        dictionary rather than hard-coding strategy names in each surface.
        """

        rows: list[dict[str, Any]] = []
        for item in self.registry.list():
            payload = item.model_dump(mode="json")
            key_stem = item.strategy_id.replace(".", "_").replace("-", "_")
            payload["label_key"] = f"pipelines.strategy.{key_stem}.label"
            payload["description_key"] = f"pipelines.strategy.{key_stem}.description"
            payload["phase"] = FAMILY_PHASES[item.family]
            payload["effect_note"] = effect_note(item.family, item.scholarly_effect)
            rows.append(payload)
        return rows

    def built_in_pipelines(self) -> list[PipelineDefinition]:
        return list(BUILT_IN_PIPELINES)

    def built_in_assignments(self) -> list[PipelineAssignment]:
        return list(BUILT_IN_ASSIGNMENTS)

    def validate(self, pipeline: PipelineDefinition) -> PipelineValidationResult:
        issues: list[PipelineValidationIssue] = []
        stages = {stage.id: stage for stage in pipeline.stages}
        if purpose_registry.get(pipeline.purpose) is None:
            issues.append(
                PipelineValidationIssue(
                    level="error",
                    code="unknown_purpose",
                    message=f"Pipeline purpose {pipeline.purpose!r} is not a registered workflow.",
                )
            )
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

        issues.extend(
            resolve_wiring(pipeline, self.registry, purpose_registry.get(pipeline.purpose))[
                "issues"
            ]
        )

        ordering_only = ordering_only_edges(pipeline, self.registry)
        incoming: dict[str, set[str]] = defaultdict(set)
        for stage in pipeline.stages:
            fallback_targets = {
                stage.on_empty,
                stage.on_unavailable,
                stage.on_timeout,
                stage.on_error,
            } - set(stage.next)
            for target in stage.edge_targets():
                incoming[target].add(stage.id)
                source_spec = strategy_specs.get(stage.id)
                target_spec = strategy_specs.get(target)
                if source_spec is None or target_spec is None:
                    continue
                if (stage.id, target) in ordering_only:
                    continue
                # A fallback edge hands the target the input the failed stage
                # was given, so either the stage's output or input type fits.
                compatible = self._types_compatible(
                    source_spec.output_type, target_spec.input_type
                ) or (
                    target in fallback_targets
                    and self._types_compatible(source_spec.input_type, target_spec.input_type)
                )
                if not compatible:
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

        if pipeline.purpose == "evidence_suggestion":
            enabled_strategies = {
                stage.strategy for stage in pipeline.stages if stage.enabled
            }
            gate_level = "error" if pipeline.status == "active" else "warning"
            if "validate.evidence_support" not in enabled_strategies:
                issues.append(
                    PipelineValidationIssue(
                        level=gate_level,
                        code="evidence_without_support_gate",
                        message=(
                            "Evidence pipelines must validate direct proposition/value "
                            "support before a candidate may be selected. Draft or disabled "
                            "legacy chains may remain inspectable, but an active chain "
                            "cannot omit this gate."
                        ),
                    )
                )
            if "validate.provenance" not in enabled_strategies:
                issues.append(
                    PipelineValidationIssue(
                        level=gate_level,
                        code="evidence_without_provenance_gate",
                        message=(
                            "Evidence pipelines must verify that selected candidates bind "
                            "to real source units in the current source document before "
                            "selection. Draft or disabled legacy chains may remain "
                            "inspectable, but an active chain cannot omit this gate."
                        ),
                    )
                )

        if pipeline.purpose == "evidence_recovery":
            issues.extend(self._recovery_issues(pipeline))

        return PipelineValidationResult(
            valid=not any(issue.level == "error" for issue in issues),
            issues=issues,
        )

    @staticmethod
    def _recovery_issues(pipeline: PipelineDefinition) -> list[PipelineValidationIssue]:
        """Provenance is mandatory; loosening the support gate is allowed but reported."""

        enabled = {stage.strategy for stage in pipeline.stages if stage.enabled}
        if "validate.provenance" not in enabled:
            return [
                PipelineValidationIssue(
                    level="error" if pipeline.status == "active" else "warning",
                    code="evidence_without_provenance_gate",
                    message=(
                        "Evidence recovery must verify that every suggestion binds to a real "
                        "source unit of the current source document. An active chain cannot "
                        "omit this gate."
                    ),
                )
            ]
        from .evidence_recovery import compile_recovery_pipeline

        try:
            plan = compile_recovery_pipeline(pipeline)
        except ValueError:
            return []  # runtime support reports why the graph cannot execute
        if plan.celf_compliant:
            return []
        return [
            PipelineValidationIssue(
                level="warning",
                code="evidence_recovery_not_celf_compliant",
                message=plan.compliance_reason,
            )
        ]

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
        properties = schema.get("properties") if isinstance(schema, dict) else {}
        if properties is None:
            properties = {}
        if not isinstance(properties, dict):
            properties = {}
        unknown = sorted(set(config) - set(properties) - {"optional"})
        for key in unknown:
            issues.append(
                PipelineValidationIssue(
                    level="error",
                    code="unknown_config_key",
                    stage_id=stage_id,
                    message=(
                        f"Configuration key {key!r} is not declared by this strategy. "
                        "Unknown settings are rejected because silently ignoring them "
                        "would make the saved pipeline differ from runtime behavior."
                    ),
                )
            )
        if "optional" in config and not isinstance(config["optional"], bool):
            issues.append(
                PipelineValidationIssue(
                    level="error",
                    code="invalid_optional_flag",
                    stage_id=stage_id,
                    message="Configuration 'optional' must be boolean.",
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
