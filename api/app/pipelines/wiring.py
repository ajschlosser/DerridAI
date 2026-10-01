# Copyright 2026 Aaron John Schlosser, PhD.
"""Resolve what every stage input is wired to, and prove it is the right type.

A stage declares named, typed input ports (``contracts.py``). Each port gets its
value from exactly one place:

* an explicit binding saved on the stage (an upstream stage output, or a value
  the workflow supplies to every run), or
* the graph itself: the first port takes what its ``next`` edges deliver, an
  entry stage takes the matching run input, and other ports take the run input
  of the same name.

Resolution never invents a source. A required port with no source, a source of
the wrong type, a binding to a stage that does not run before the consumer, or
several sources feeding a port that takes one are validation errors, so a saved
pipeline either hands every stage the input it declares or says why it cannot.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from .contracts import input_ports, output_ports
from .models import (
    PipelineDefinition,
    PipelineStageDefinition,
    PipelineValidationIssue,
    PortSpec,
    StrategySpec,
)
from .purposes import PipelinePurposeSpec
from .registry import StrategyRegistry

FALLBACK_EDGES = ("on_empty", "on_unavailable", "on_timeout", "on_error")


def types_compatible(source: str, target: str) -> bool:
    return source == target or source == "any" or target == "any"


def _issue(
    level: str, code: str, message: str, stage_id: str | None = None
) -> PipelineValidationIssue:
    return PipelineValidationIssue(level=level, code=code, message=message, stage_id=stage_id)


def _descendants(pipeline: PipelineDefinition) -> dict[str, set[str]]:
    stages = {stage.id: stage for stage in pipeline.stages}
    result: dict[str, set[str]] = {}
    for start in stages:
        seen: set[str] = set()
        queue = deque(stages[start].edge_targets())
        while queue:
            current = queue.popleft()
            if current in seen or current not in stages:
                continue
            seen.add(current)
            queue.extend(stages[current].edge_targets())
        result[start] = seen
    return result


def ordering_only_edges(
    pipeline: PipelineDefinition, registry: StrategyRegistry
) -> set[tuple[str, str]]:
    """``next`` edges that only make a producer run first for an explicit binding.

    A ``next`` edge normally hands the target the producer's primary output. When
    the target explicitly binds the producer to one of its *other* inputs and the
    producer's output is not what the target's primary input takes, the edge is
    there for ordering alone: the binding explains it, and it feeds nothing.
    """

    stages = {stage.id: stage for stage in pipeline.stages}
    pairs: set[tuple[str, str]] = set()
    for target in pipeline.stages:
        spec = registry.get(target.strategy)
        if spec is None or not target.inputs:
            continue
        ports = input_ports(spec)
        for port_name, bindings in target.inputs.items():
            if not ports or port_name == ports[0].name:
                continue
            for binding in bindings:
                producer = stages.get(binding.stage or "") if binding.source == "stage" else None
                producer_spec = registry.get(producer.strategy) if producer else None
                if producer is None or producer_spec is None or target.id not in producer.next:
                    continue
                if not types_compatible(output_ports(producer_spec)[0].data_type, ports[0].data_type):
                    pairs.add((producer.id, target.id))
    return pairs


def _source_row(
    *,
    kind: str,
    data_type: str,
    stage: str | None = None,
    output: str | None = None,
    name: str | None = None,
    via: str = "next",
    explicit: bool = False,
    producer_enabled: bool = True,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "stage": stage,
        "output": output,
        "name": name,
        "data_type": data_type,
        "via": via,
        "explicit": explicit,
        "producer_enabled": producer_enabled,
    }


def resolve_wiring(
    pipeline: PipelineDefinition,
    registry: StrategyRegistry,
    purpose: PipelinePurposeSpec | None,
) -> dict[str, Any]:
    """Return per-stage input/output wiring plus the issues it implies."""

    issues: list[PipelineValidationIssue] = []
    stages = {stage.id: stage for stage in pipeline.stages}
    specs: dict[str, StrategySpec] = {}
    for stage in pipeline.stages:
        spec = registry.get(stage.strategy)
        if spec is not None:
            specs[stage.id] = spec
    run_inputs = [(item.name, item.data_type) for item in (purpose.run_inputs if purpose else [])]
    run_input_types = dict(run_inputs)
    descendants = _descendants(pipeline)
    entries = set(pipeline.entry_stage_ids)

    # Edge-derived deliveries into each stage's primary input port.
    ordering_only = ordering_only_edges(pipeline, registry)
    delivered: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for stage in pipeline.stages:
        spec = specs.get(stage.id)
        if spec is None:
            continue
        primary_out = output_ports(spec)[0]
        primary_in = input_ports(spec)[0]
        for target in stage.next:
            if (stage.id, target) in ordering_only:
                continue
            delivered[target].append(
                _source_row(
                    kind="stage",
                    stage=stage.id,
                    output=primary_out.name,
                    data_type=primary_out.data_type,
                    via="next",
                    producer_enabled=stage.enabled,
                )
            )
        for edge in FALLBACK_EDGES:
            target = getattr(stage, edge)
            if target and target not in stage.next:
                # A fallback hands the target what the failed stage was given.
                delivered[target].append(
                    _source_row(
                        kind="stage_input",
                        stage=stage.id,
                        output=primary_in.name,
                        data_type=primary_in.data_type,
                        via=edge,
                        producer_enabled=stage.enabled,
                    )
                )

    def run_input_for(port: PortSpec, *, by_type: bool) -> dict[str, Any] | None:
        if port.name in run_input_types and types_compatible(
            run_input_types[port.name], port.data_type
        ):
            return _source_row(
                kind="run_input",
                name=port.name,
                data_type=run_input_types[port.name],
                via="run_input",
            )
        if by_type and port.data_type != "any":
            for name, data_type in run_inputs:
                if types_compatible(data_type, port.data_type):
                    return _source_row(
                        kind="run_input", name=name, data_type=data_type, via="run_input"
                    )
        return None

    def options_for(stage: PipelineStageDefinition, port: PortSpec) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for other in pipeline.stages:
            other_spec = specs.get(other.id)
            if other_spec is None or other.id == stage.id:
                continue
            for output in output_ports(other_spec):
                if not types_compatible(output.data_type, port.data_type):
                    continue
                rows.append(
                    {
                        "kind": "stage",
                        "stage": other.id,
                        "output": output.name,
                        "data_type": output.data_type,
                        # Choosing a stage that does not yet run before this one
                        # means adding the edge that makes it so.
                        "upstream": stage.id in descendants.get(other.id, set()),
                        # A stage downstream of this one cannot feed it.
                        "possible": other.id not in descendants.get(stage.id, set()),
                    }
                )
        for name, data_type in run_inputs:
            if types_compatible(data_type, port.data_type):
                rows.append(
                    {
                        "kind": "run_input",
                        "name": name,
                        "data_type": data_type,
                        "upstream": True,
                        "possible": True,
                    }
                )
        return rows

    stage_rows: dict[str, dict[str, Any]] = {}
    consumers: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    run_consumers: dict[str, list[dict[str, str]]] = defaultdict(list)

    for stage in pipeline.stages:
        spec = specs.get(stage.id)
        if spec is None:
            continue
        ports = input_ports(spec)
        port_names = {port.name for port in ports}
        for unknown in sorted(set(stage.inputs) - port_names):
            issues.append(
                _issue(
                    "error",
                    "binding_unknown_port",
                    f"Stage {stage.id!r} binds input {unknown!r}, which strategy "
                    f"{stage.strategy!r} does not declare.",
                    stage.id,
                )
            )
        input_rows: list[dict[str, Any]] = []
        for index, port in enumerate(ports):
            explicit = stage.inputs.get(port.name)
            sources: list[dict[str, Any]] = []
            if explicit:
                for binding in explicit:
                    sources.extend(
                        _explicit_source(
                            binding, stage, port, stages, specs, descendants, run_input_types, issues
                        )
                    )
            elif index == 0:
                sources = list(delivered.get(stage.id, []))
                if not sources and stage.id in entries:
                    entry_source = run_input_for(port, by_type=True)
                    if entry_source is not None:
                        sources = [entry_source]
            else:
                implicit = run_input_for(port, by_type=False)
                sources = [implicit] if implicit is not None else []

            status = "bound"
            if not sources:
                status = "unbound" if port.required else "optional_unbound"
            if sources and any(not types_compatible(s["data_type"], port.data_type) for s in sources):
                status = "mismatch"
                for source in sources:
                    if types_compatible(source["data_type"], port.data_type):
                        continue
                    # Edge-derived mismatches on the primary port are already
                    # reported as ``incompatible_stage_types``; do not repeat them.
                    if source["explicit"] or index > 0:
                        origin = source.get("stage") or source.get("name")
                        issues.append(
                            _issue(
                                "error",
                                "input_type_mismatch",
                                f"Input {port.name!r} of {stage.id!r} takes "
                                f"{port.data_type!r}, but {origin!r} provides "
                                f"{source['data_type']!r}.",
                                stage.id,
                            )
                        )
            if stage.enabled and status == "unbound":
                issues.append(
                    _issue(
                        "error",
                        "input_unbound",
                        f"Input {port.name!r} of {stage.id!r} ({port.data_type}) has no "
                        "source. Connect an upstream stage or bind a run input.",
                        stage.id,
                    )
                )
            direct = [s for s in sources if s["via"] == "next" or s["explicit"]]
            if stage.enabled and not port.multiple and len(direct) > 1:
                issues.append(
                    _issue(
                        "error",
                        "input_multiple_sources",
                        f"Input {port.name!r} of {stage.id!r} takes one {port.data_type!r} "
                        f"but is fed by {len(direct)} sources. Bind one explicitly.",
                        stage.id,
                    )
                )
            if stage.enabled and sources and all(not s["producer_enabled"] for s in sources):
                issues.append(
                    _issue(
                        "warning",
                        "input_producer_disabled",
                        f"Every source of input {port.name!r} on {stage.id!r} is disabled.",
                        stage.id,
                    )
                )
            for source in sources:
                key = (source["stage"], source["output"]) if source["stage"] else None
                target = {"stage": stage.id, "port": port.name}
                if source["kind"] == "stage" and key:
                    consumers[key].append(target)
                elif source["kind"] == "run_input" and source["name"]:
                    run_consumers[source["name"]].append(target)
            input_rows.append(
                {
                    "port": port.name,
                    "data_type": port.data_type,
                    "required": port.required,
                    "multiple": port.multiple,
                    "explicit": bool(explicit),
                    "status": status,
                    "sources": sources,
                    "options": options_for(stage, port),
                }
            )
        stage_rows[stage.id] = {"inputs": input_rows, "outputs": []}

    for stage_id, row in stage_rows.items():
        for output in output_ports(specs[stage_id]):
            row["outputs"].append(
                {
                    "name": output.name,
                    "data_type": output.data_type,
                    "consumers": consumers.get((stage_id, output.name), []),
                }
            )

    return {
        "stages": stage_rows,
        "run_inputs": [
            {"name": name, "data_type": data_type, "consumers": run_consumers.get(name, [])}
            for name, data_type in run_inputs
        ],
        "issues": issues,
    }


def _explicit_source(
    binding: Any,
    stage: PipelineStageDefinition,
    port: PortSpec,
    stages: dict[str, PipelineStageDefinition],
    specs: dict[str, StrategySpec],
    descendants: dict[str, set[str]],
    run_input_types: dict[str, str],
    issues: list[PipelineValidationIssue],
) -> list[dict[str, Any]]:
    where = f"input {port.name!r} of {stage.id!r}"
    if binding.source == "run_input":
        name = str(binding.name)
        if name not in run_input_types:
            known = ", ".join(sorted(run_input_types)) or "none"
            issues.append(
                _issue(
                    "error",
                    "binding_unknown_run_input",
                    f"The {where} binds run input {name!r}; this workflow supplies: {known}.",
                    stage.id,
                )
            )
            return []
        return [
            _source_row(
                kind="run_input",
                name=name,
                data_type=run_input_types[name],
                via="run_input",
                explicit=True,
            )
        ]

    producer_id = str(binding.stage)
    producer = stages.get(producer_id)
    producer_spec = specs.get(producer_id)
    if producer is None or producer_spec is None:
        issues.append(
            _issue(
                "error",
                "binding_unknown_stage",
                f"The {where} binds stage {producer_id!r}, which does not exist "
                "or has an unknown strategy.",
                stage.id,
            )
        )
        return []
    outputs = output_ports(producer_spec)
    output = next(
        (item for item in outputs if item.name == (binding.output or outputs[0].name)), None
    )
    if output is None:
        issues.append(
            _issue(
                "error",
                "binding_unknown_output",
                f"The {where} binds output {binding.output!r}, which "
                f"{producer_id!r} does not produce.",
                stage.id,
            )
        )
        return []
    if stage.id not in descendants.get(producer_id, set()):
        issues.append(
            _issue(
                "error",
                "binding_not_upstream",
                f"The {where} binds {producer_id!r}, but {producer_id!r} does not run "
                f"before {stage.id!r}. Connect it with a next edge first.",
                stage.id,
            )
        )
    if not producer.enabled:
        issues.append(
            _issue(
                "error",
                "binding_producer_disabled",
                f"The {where} binds {producer_id!r}, which is disabled.",
                stage.id,
            )
        )
    return [
        _source_row(
            kind="stage",
            stage=producer_id,
            output=output.name,
            data_type=output.data_type,
            via="explicit",
            explicit=True,
            producer_enabled=producer.enabled,
        )
    ]


def _signature(wiring: dict[str, Any]) -> dict[tuple[str, str], list[tuple[Any, ...]]]:
    return {
        (stage_id, row["port"]): sorted(
            (s["kind"], s["stage"] or "", s["output"] or "", s["name"] or "")
            for s in row["sources"]
        )
        for stage_id, stage in wiring["stages"].items()
        for row in stage["inputs"]
    }


def bindings_changing_wiring(
    pipeline: PipelineDefinition,
    registry: StrategyRegistry,
    purpose: PipelinePurposeSpec | None,
) -> list[str]:
    """Stage/port pairs whose explicit binding differs from the graph's own wiring.

    Runtime adapters take their inputs from the graph, so a binding that only
    restates the implicit wiring is harmless and one that changes it is not
    something they can honour.
    """

    if not any(stage.inputs for stage in pipeline.stages if stage.enabled):
        return []
    bare = pipeline.model_copy(
        update={
            "stages": [stage.model_copy(update={"inputs": {}}) for stage in pipeline.stages]
        }
    )
    explicit = _signature(resolve_wiring(pipeline, registry, purpose))
    implicit = _signature(resolve_wiring(bare, registry, purpose))
    return sorted(
        f"{stage_id}.{port}"
        for (stage_id, port), value in explicit.items()
        if value != implicit.get((stage_id, port))
    )
