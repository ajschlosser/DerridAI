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

"""Run server-owned handlers through resolved named ports of a bounded DAG.

This is the execution foundation for adaptive metadata graphs, not a new
production assignment. Domain adapters still own payload validation, evidence
binding and canonical persistence. Artifacts stay run-local; telemetry contains
counts and configuration hashes, never source text or provider exception text.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .contracts import output_ports
from .models import PipelineDefinition, PipelineStageDefinition, PipelineStageTrace
from .purposes import PipelinePurposeSpec
from .registry import StrategyRegistry
from .service import PipelineService, pipeline_hash
from .wiring import FALLBACK_EDGES, resolve_wiring


@dataclass(frozen=True)
class StageResult:
    """Every declared output, including explicit empty branch outputs."""

    outputs: Mapping[str, Any]
    provider: str | None = None
    model: str | None = None


StageHandler = Callable[[PipelineStageDefinition, Mapping[str, Any]], StageResult]


@dataclass
class GraphResult:
    """Run-local artifacts and safe, definition-ordered operational telemetry."""

    pipeline_hash: str
    outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    stages: list[PipelineStageTrace] = field(default_factory=list)


class GraphExecutionError(RuntimeError):
    """A coded failure with partial telemetry; original payloads are not logged."""

    def __init__(self, stage_id: str, reason: str, result: GraphResult) -> None:
        super().__init__(f"Pipeline stage {stage_id!r}: {reason}")
        self.stage_id = stage_id
        self.reason = reason
        self.result = result


def _empty(value: Any) -> bool:
    # Zero and False are valid tuning/evaluation values, not empty branches.
    return (
        value is None
        or isinstance(value, (list, tuple, dict, set, str))
        and len(value) == 0
    )


def _count(value: Any) -> int:
    if _empty(value):
        return 0
    return len(value) if isinstance(value, (list, tuple, set)) else 1


class GraphExecutor:
    """Compile a snapshot and execute it serially with deterministic fan-in.

    Handlers are supplied by server code, keyed by registered strategy ID. A
    definition can never supply executable code. Each instance runs at most once
    per invocation; the same strategy may have any number of distinct instances.
    Serial scheduling is deliberate until concurrency capabilities are declared.
    """

    def __init__(
        self,
        pipeline: PipelineDefinition,
        *,
        registry: StrategyRegistry,
        purpose: PipelinePurposeSpec,
        handlers: Mapping[str, StageHandler],
    ) -> None:
        self.pipeline = pipeline.model_copy(deep=True)
        self.registry = StrategyRegistry(
            spec.model_copy(deep=True) for spec in registry.list()
        )
        self.handlers = dict(handlers)
        if self.pipeline.purpose != purpose.purpose_id:
            raise ValueError("The graph purpose must match its run-input contract.")
        self.wiring = resolve_wiring(self.pipeline, self.registry, purpose)
        issues = [issue for issue in self.wiring["issues"] if issue.level == "error"]
        for stage in self.pipeline.stages:
            spec = self.registry.require(stage.strategy)
            issues.extend(
                PipelineService._validate_config(
                    stage.id, stage.config, spec.config_schema
                )
            )
            if stage.enabled and stage.strategy not in self.handlers:
                raise ValueError(f"No server handler for strategy {stage.strategy!r}.")
        if issues:
            raise ValueError("; ".join(issue.message for issue in issues))
        self.order = self._topological_order()
        self.resolved_hash = pipeline_hash(self.pipeline)

    def _topological_order(self) -> list[PipelineStageDefinition]:
        """Break ties in definition order, including fallback dependencies."""
        pending = {stage.id: stage for stage in self.pipeline.stages}
        parents: dict[str, set[str]] = {
            stage.id: set() for stage in self.pipeline.stages
        }
        for stage in self.pipeline.stages:
            for target in stage.edge_targets():
                parents[target].add(stage.id)
        ordered = []
        while pending:
            ready = next(
                (stage for key, stage in pending.items() if not parents[key]), None
            )
            if ready is None:
                raise ValueError("Pipeline graph contains a cycle.")
            ordered.append(ready)
            del pending[ready.id]
            for dependencies in parents.values():
                dependencies.discard(ready.id)
        return ordered

    def run(self, run_inputs: Mapping[str, Any]) -> GraphResult:
        """Follow only selected edges; a required empty branch skips its handler.

        Multiple ports receive an ordered list of artifacts (not a flattened
        payload). A fan-in can proceed with surviving inputs after another branch
        skipped. Fallback edges forward the failed stage's primary input, as the
        wiring resolver specifies; explicit bindings always retain their meaning.
        """
        result = GraphResult(pipeline_hash=self.resolved_hash)
        active = set(self.pipeline.entry_stage_ids)
        deliveries: dict[tuple[str, str], str] = {}
        stage_inputs: dict[str, dict[str, Any]] = {}
        traces: dict[str, PipelineStageTrace] = {}

        for stage in self.order:
            spec = self.registry.require(stage.strategy)
            trace = PipelineStageTrace(
                stage_id=stage.id,
                strategy_id=stage.strategy,
                strategy_version=spec.version,
                status="skipped",
                parameters={
                    "config_hash": hashlib.sha256(
                        json.dumps(
                            stage.config, sort_keys=True, separators=(",", ":")
                        ).encode()
                    ).hexdigest()
                },
            )
            traces[stage.id] = trace
            result.stages = [
                traces[item.id] for item in self.pipeline.stages if item.id in traces
            ]
            if not stage.enabled or stage.id not in active:
                continue
            inputs = {}
            missing = False
            for port in self.wiring["stages"][stage.id]["inputs"]:
                values: list[Any] = []
                for source in port["sources"]:
                    kind, producer = source["kind"], source["stage"]
                    if kind == "constant":
                        value = source["value"]
                    elif kind == "run_input":
                        if source["name"] not in run_inputs:
                            if port["required"]:
                                raise GraphExecutionError(
                                    stage.id, "missing_run_input", result
                                )
                            continue
                        value = run_inputs[source["name"]]
                    else:
                        edge = deliveries.get((producer, stage.id))
                        if not source["explicit"] and edge is None:
                            continue
                        if not source["explicit"] and edge in FALLBACK_EDGES:
                            primary = self.wiring["stages"][producer]["inputs"][0][
                                "port"
                            ]
                            value = stage_inputs.get(producer, {}).get(primary)
                            producer_port = self.wiring["stages"][producer]["inputs"][0]
                            if producer_port["multiple"] and port["multiple"]:
                                values.extend(value or [])
                                continue
                        elif kind == "stage_input":
                            continue  # This fallback was not selected.
                        else:
                            outputs = result.outputs.get(producer, {})
                            if source["output"] not in outputs:
                                continue
                            value = outputs[source["output"]]
                    if not _empty(value):
                        values.append(value)
                if port["required"] and not values:
                    missing = True
                inputs[port["port"]] = (
                    values if port["multiple"] else (values[0] if values else None)
                )
            if missing:
                trace.fallback_reason = "empty_required_input"
                continue
            stage_inputs[stage.id] = inputs
            trace.input_count = sum(_count(value) for value in inputs.values())
            begun = time.perf_counter()
            try:
                outcome = self.handlers[stage.strategy](
                    stage.model_copy(deep=True), inputs
                )
                expected = {port.name for port in output_ports(spec)}
                if set(outcome.outputs) != expected:
                    raise ValueError(
                        "Handler must return every declared output and no undeclared outputs."
                    )
            except InterruptedError:
                raise
            except Exception as exc:  # noqa: BLE001 - explicit graph edges own degradation
                edge = (
                    "on_unavailable"
                    if isinstance(exc, LookupError)
                    else "on_timeout"
                    if isinstance(exc, TimeoutError) or getattr(exc, "timed_out", False)
                    else "on_error"
                )
                if edge == "on_unavailable":
                    trace.status = "unavailable"
                elif edge == "on_timeout":
                    trace.status = "timed_out"
                else:
                    trace.status = "failed"
                trace.fallback_reason = edge
                target = getattr(stage, edge)
                if target is None:
                    raise GraphExecutionError(stage.id, edge, result) from None
                targets = [target]
            else:
                result.outputs[stage.id] = dict(outcome.outputs)
                trace.provider, trace.model = outcome.provider, outcome.model
                trace.status = "completed"
                trace.output_count = sum(
                    _count(value) for value in outcome.outputs.values()
                )
                if (
                    all(_empty(value) for value in outcome.outputs.values())
                    and stage.on_empty
                ):
                    edge, targets = "on_empty", [stage.on_empty]
                    trace.fallback_reason = edge
                else:
                    edge, targets = "next", stage.next
            finally:
                trace.elapsed_ms = max(0, int((time.perf_counter() - begun) * 1000))
            for target in targets:
                active.add(target)
                deliveries[(stage.id, target)] = edge
        return result
