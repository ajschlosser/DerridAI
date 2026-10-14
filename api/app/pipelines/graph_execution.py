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
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import BoundedSemaphore
from typing import Any, Literal

from .contracts import output_ports
from .models import PipelineDefinition, PipelineStageDefinition, PipelineStageTrace
from .purposes import PipelinePurposeSpec
from .registry import StrategyRegistry
from .service import PipelineService, pipeline_hash
from .wiring import FALLBACK_EDGES, resolve_wiring, terminal_contracts


@dataclass(frozen=True)
class StageResult:
    """Every declared output, including explicit empty branch outputs."""

    outputs: Mapping[str, Any]
    provider: str | None = None
    model: str | None = None


StageHandler = Callable[[PipelineStageDefinition, Mapping[str, Any]], StageResult]


@dataclass(frozen=True)
class ConcurrencyCapability:
    """Server-owned opt-in for read-only inputs and thread-safe handlers.

    A shared capacity key bounds provider calls across runs on this executor.
    The adapter still owns wider provider quotas and cancellation of in-flight I/O.
    """

    capacity_key: str
    max_inflight: int = 1

    def __post_init__(self) -> None:
        if not self.capacity_key or self.max_inflight < 1:
            raise ValueError("Concurrency requires a capacity key and positive limit.")


@dataclass
class GraphResult:
    """Run-local artifacts and safe, definition-ordered operational telemetry."""

    pipeline_hash: str
    outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    terminal_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    stages: list[PipelineStageTrace] = field(default_factory=list)


class GraphExecutionError(RuntimeError):
    """A coded failure with partial telemetry; original payloads are not logged."""

    def __init__(self, stage_id: str, reason: str, result: GraphResult) -> None:
        super().__init__(f"Pipeline stage {stage_id!r}: {reason}")
        self.stage_id = stage_id
        self.reason = reason
        self.result = result


class StageFailure(Exception):
    """A server handler's explicit failure category, without private error text."""

    def __init__(
        self, edge: Literal["on_unavailable", "on_timeout", "on_error"]
    ) -> None:
        super().__init__(edge)
        self.edge = edge


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
    """Compile a snapshot with bounded opt-in concurrency and deterministic fan-in.

    Handlers are supplied by server code, keyed by registered strategy ID. A
    definition can never supply executable code. Each instance runs at most once
    per invocation; the same strategy may have any number of distinct instances.
    Undeclared handlers remain serial. Parallel handlers must not mutate inputs.
    """

    def __init__(
        self,
        pipeline: PipelineDefinition,
        *,
        registry: StrategyRegistry,
        purpose: PipelinePurposeSpec,
        handlers: Mapping[str, StageHandler],
        concurrency: Mapping[str, ConcurrencyCapability] | None = None,
        max_workers: int = 1,
    ) -> None:
        self.pipeline = pipeline.model_copy(deep=True)
        self.registry = StrategyRegistry(
            spec.model_copy(deep=True) for spec in registry.list()
        )
        self.handlers = dict(handlers)
        if max_workers < 1:
            raise ValueError("max_workers must be positive.")
        self.max_workers = max_workers
        self.concurrency = dict(concurrency or {})
        limits: dict[str, int] = {}
        for strategy, capability in self.concurrency.items():
            if strategy not in self.handlers:
                raise ValueError(f"Concurrency names an unknown handler {strategy!r}.")
            previous = limits.setdefault(
                capability.capacity_key, capability.max_inflight
            )
            if previous != capability.max_inflight:
                raise ValueError("A shared capacity key must have one limit.")
        self.capacity = {key: BoundedSemaphore(limit) for key, limit in limits.items()}
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
        self.terminals, terminal_issues = terminal_contracts(
            self.pipeline, self.registry, purpose
        )
        if terminal_issues:
            raise ValueError("; ".join(issue.message for issue in terminal_issues))
        self.resolved_hash = pipeline_hash(self.pipeline)

    def _topological_order(self) -> list[PipelineStageDefinition]:
        """Break ties in definition order, including fallback dependencies."""
        pending = {stage.id: stage for stage in self.pipeline.stages}
        parents = self._parents()
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

    def _parents(self) -> dict[str, set[str]]:
        parents: dict[str, set[str]] = {
            stage.id: set() for stage in self.pipeline.stages
        }
        for stage in self.pipeline.stages:
            for target in stage.edge_targets():
                parents[target].add(stage.id)
            for port in self.wiring["stages"][stage.id]["inputs"]:
                for source in port["sources"]:
                    if source["stage"] is not None:
                        parents[stage.id].add(source["stage"])
        return parents

    def _waves(self) -> list[list[PipelineStageDefinition]]:
        parents = self._parents()
        pending = {stage.id: stage for stage in self.order}
        waves = []
        while pending:
            ready = [stage for key, stage in pending.items() if not parents[key]]
            first = ready[0]
            # A serial handler is a barrier; never overlap it with a safe handler.
            wave = [first]
            if self.max_workers > 1 and first.strategy in self.concurrency:
                for stage in ready[1:]:
                    if stage.strategy not in self.concurrency:
                        break
                    wave.append(stage)
                    if len(wave) == self.max_workers:
                        break
            waves.append(wave)
            for stage in wave:
                del pending[stage.id]
                for dependencies in parents.values():
                    dependencies.discard(stage.id)
        return waves

    def _invoke(
        self, stage: PipelineStageDefinition, inputs: Mapping[str, Any]
    ) -> StageResult:
        capability = self.concurrency.get(stage.strategy)
        if capability is None:
            return self.handlers[stage.strategy](stage.model_copy(deep=True), inputs)
        with self.capacity[capability.capacity_key]:
            return self.handlers[stage.strategy](stage.model_copy(deep=True), inputs)

    def run(self, run_inputs: Mapping[str, Any]) -> GraphResult:
        # On failure, queued work is cancelled and running handlers are joined.
        # No background handler outlives this run or its task-owned context.
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            try:
                return self._run(run_inputs, pool)
            except BaseException:
                pool.shutdown(wait=True, cancel_futures=True)
                raise

    def _run(
        self, run_inputs: Mapping[str, Any], pool: ThreadPoolExecutor
    ) -> GraphResult:
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

        for wave in self._waves():
            submitted: dict[str, Future[StageResult]] = {}
            elapsed: dict[str, int] = {}

            def invoke(
                stage: PipelineStageDefinition,
                inputs: Mapping[str, Any],
                durations: dict[str, int] = elapsed,
            ) -> StageResult:
                begun = time.perf_counter()
                try:
                    return self._invoke(stage, inputs)
                finally:
                    durations[stage.id] = max(
                        0, int((time.perf_counter() - begun) * 1000)
                    )

            for stage in wave:
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
                    traces[item.id]
                    for item in self.pipeline.stages
                    if item.id in traces
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
                                producer_port = self.wiring["stages"][producer][
                                    "inputs"
                                ][0]
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
                if len(wave) == 1:
                    future: Future[StageResult] = Future()
                    try:
                        future.set_result(invoke(stage, inputs))
                    except BaseException as exc:
                        future.set_exception(exc)
                    submitted[stage.id] = future
                else:
                    submitted[stage.id] = pool.submit(invoke, stage, inputs)
            for stage in wave:
                if stage.id not in submitted:
                    continue
                future = submitted[stage.id]
                trace = traces[stage.id]
                spec = self.registry.require(stage.strategy)
                try:
                    outcome = future.result()
                    expected = {port.name for port in output_ports(spec)}
                    if set(outcome.outputs) != expected:
                        raise ValueError(
                            "Handler must return every declared output and no undeclared outputs."
                        )
                except InterruptedError:
                    for pending_future in submitted.values():
                        pending_future.cancel()
                    raise
                except Exception as exc:  # noqa: BLE001 - explicit graph edges own degradation
                    edge = (
                        exc.edge
                        if isinstance(exc, StageFailure)
                        else (
                            "on_unavailable"
                            if isinstance(exc, LookupError)
                            else "on_timeout"
                            if isinstance(exc, TimeoutError)
                            or getattr(exc, "timed_out", False)
                            else "on_error"
                        )
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
                        for pending_future in submitted.values():
                            pending_future.cancel()
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
                    trace.elapsed_ms = elapsed[stage.id]
                for target in targets:
                    active.add(target)
                    deliveries[(stage.id, target)] = edge
        result.terminal_outputs = {
            stage_id: {name: result.outputs[stage_id][name] for name in names}
            for stage_id, names in self.terminals.items()
            if stage_id in result.outputs
            and traces[stage_id].status == "completed"
            and traces[stage_id].fallback_reason != "on_empty"
        }
        if not result.terminal_outputs:
            raise GraphExecutionError("terminal", "missing_terminal_output", result)
        return result
