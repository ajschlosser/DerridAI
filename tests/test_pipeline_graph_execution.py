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

"""Behavioral boundaries for the generic graph runtime before adapter migration."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock

import pytest
from app.pipelines.graph_execution import (
    ConcurrencyCapability,
    GraphExecutionError,
    GraphExecutor,
    StageResult,
)
from app.pipelines.models import PipelineDefinition, PortSpec, StrategySpec
from app.pipelines.purposes import PipelinePurposeSpec, RunInputSpec
from app.pipelines.registry import StrategyRegistry


def _strategy(name, *, outputs=("items",), multiple=False):
    return StrategySpec(
        strategy_id=name,
        family="selection",
        scholarly_effect="advisory",
        label=name,
        description=name,
        input_type="candidate_set",
        output_type="candidate_set",
        inputs=[PortSpec(name="items", data_type="candidate_set", multiple=multiple)],
        outputs=[
            PortSpec(name=output, data_type="candidate_set") for output in outputs
        ],
        config_schema={
            "type": "object",
            "properties": {"offset": {"type": "integer"}},
            "additionalProperties": False,
        },
    )


PURPOSE = PipelinePurposeSpec(
    purpose_id="test_graph",
    category="metadata",
    label="Test",
    description="Test",
    consuming_feature="test",
    consumer="test",
    input_semantics="test",
    output_semantics="test",
    authority_semantics="Advisory",
    output_type="candidate_set",
    run_inputs=[RunInputSpec(name="items", data_type="candidate_set")],
)


def _executor(stages, handlers, *, specs=None, entries=("start",), **options):
    pipeline = PipelineDefinition(
        pipeline_id="test.graph",
        name="Test graph",
        purpose="test_graph",
        entry_stage_ids=list(entries),
        stages=stages,
    )
    registry = StrategyRegistry(specs or [_strategy("transform")])
    return GraphExecutor(
        pipeline, registry=registry, purpose=PURPOSE, handlers=handlers, **options
    )


def test_repeated_strategy_uses_each_config_and_resolved_explicit_output():
    calls = []

    def transform(stage, inputs):
        calls.append(stage.id)
        return StageResult(
            {
                "items": [
                    item + stage.config.get("offset", 0) for item in inputs["items"]
                ]
            }
        )

    executor = _executor(
        [
            {
                "id": "last",
                "strategy": "transform",
                "config": {"offset": 10},
                "inputs": {
                    "items": [{"source": "stage", "stage": "start", "output": "items"}]
                },
            },
            {
                "id": "middle",
                "strategy": "transform",
                "config": {"offset": 100},
                "next": ["last"],
            },
            {
                "id": "start",
                "strategy": "transform",
                "config": {"offset": 1},
                "next": ["middle"],
            },
        ],
        {"transform": transform},
    )
    result = executor.run({"items": [1]})
    assert calls == ["start", "middle", "last"]
    assert result.outputs["last"]["items"] == [
        12
    ]  # Binding skips middle's transformed payload.
    assert [trace.stage_id for trace in result.stages] == ["last", "middle", "start"]
    assert len({trace.parameters["config_hash"] for trace in result.stages}) == 3


def test_named_branches_skip_empty_model_work_and_fan_in_survivors():
    calls = []

    def route(stage, inputs):
        return StageResult({"resolved": inputs["items"], "verify": [], "infer": []})

    def model(stage, inputs):
        pytest.fail("Empty verification/inference branches must not call a provider")

    def merge(stage, inputs):
        calls.append(inputs["items"])
        return StageResult(
            {"items": [item for branch in inputs["items"] for item in branch]}
        )

    stages = [
        {"id": "start", "strategy": "route", "next": ["verify", "infer", "merge"]}
    ]
    for branch in ("verify", "infer"):
        stages.append(
            {
                "id": branch,
                "strategy": "model",
                "next": ["merge"],
                "inputs": {
                    "items": [{"source": "stage", "stage": "start", "output": branch}]
                },
            }
        )
    stages.append(
        {
            "id": "merge",
            "strategy": "merge",
            "inputs": {
                "items": [
                    {"source": "stage", "stage": "start", "output": "resolved"},
                    {"source": "stage", "stage": "verify", "output": "items"},
                    {"source": "stage", "stage": "infer", "output": "items"},
                ]
            },
        }
    )
    executor = _executor(
        stages,
        {"route": route, "model": model, "merge": merge},
        specs=[
            _strategy("route", outputs=("resolved", "verify", "infer")),
            _strategy("model"),
            _strategy("merge", multiple=True),
        ],
    )
    result = executor.run({"items": ["evidence-bound proposal"]})
    assert calls == [[["evidence-bound proposal"]]]
    assert result.outputs["merge"]["items"] == ["evidence-bound proposal"]
    assert [trace.status for trace in result.stages] == [
        "completed",
        "skipped",
        "skipped",
        "completed",
    ]


@pytest.mark.parametrize(
    "edge,failure,status",
    [
        ("on_unavailable", LookupError("SECRET SOURCE"), "unavailable"),
        ("on_timeout", TimeoutError("SECRET SOURCE"), "timed_out"),
        ("on_error", ValueError("SECRET SOURCE"), "failed"),
        ("on_empty", None, "completed"),
    ],
)
def test_selected_fallback_receives_original_input_and_other_paths_stay_idle(
    edge, failure, status
):
    calls = []

    def handler(stage, inputs):
        calls.append((stage.id, inputs["items"]))
        if stage.id == "start":
            if failure is not None:
                raise failure
            return StageResult({"items": []})
        return StageResult({"items": inputs["items"]})

    stages = [
        {"id": "start", "strategy": "transform", "next": ["normal"], edge: "fallback"},
        {"id": "normal", "strategy": "transform"},
        {"id": "fallback", "strategy": "transform"},
    ]
    result = _executor(stages, {"transform": handler}).run(
        {"items": ["CURRENT RECORD"]}
    )
    assert calls == [("start", ["CURRENT RECORD"]), ("fallback", ["CURRENT RECORD"])]
    assert result.stages[0].status == status
    assert result.stages[0].fallback_reason == edge
    assert result.stages[1].status == "skipped"
    assert "SECRET SOURCE" not in repr([trace.model_dump() for trace in result.stages])


def test_fallback_target_also_on_next_forwards_input_when_fallback_selected():
    def handler(stage, inputs):
        if stage.id == "start":
            raise TimeoutError()
        return StageResult({"items": inputs["items"]})

    result = _executor(
        [
            {
                "id": "start",
                "strategy": "transform",
                "next": ["retry"],
                "on_timeout": "retry",
            },
            {"id": "retry", "strategy": "transform"},
        ],
        {"transform": handler},
    ).run({"items": [7]})
    assert result.outputs["retry"]["items"] == [7]


def test_failure_without_edge_retains_safe_partial_trace_and_does_not_run_next():
    def fail(stage, inputs):
        raise ValueError("private model response")

    executor = _executor(
        [
            {"id": "start", "strategy": "transform", "next": ["next"]},
            {"id": "next", "strategy": "transform"},
        ],
        {"transform": fail},
    )
    with pytest.raises(GraphExecutionError) as caught:
        executor.run({"items": [1]})
    assert caught.value.reason == "on_error"
    assert caught.value.result.stages[0].status == "failed"
    assert "private model response" not in str(caught.value)


def test_cancellation_propagates_without_provider_fallback():
    def cancel(stage, inputs):
        raise InterruptedError("cancelled")

    executor = _executor(
        [
            {"id": "start", "strategy": "transform", "on_error": "fallback"},
            {"id": "fallback", "strategy": "transform"},
        ],
        {"transform": cancel},
    )
    with pytest.raises(InterruptedError):
        executor.run({"items": [1]})


def test_missing_named_output_is_a_visible_handler_contract_failure():
    executor = _executor(
        [
            {"id": "start", "strategy": "route"},
        ],
        {"route": lambda stage, inputs: StageResult({"resolved": [1]})},
        specs=[
            _strategy("route", outputs=("resolved", "verify", "infer")),
        ],
    )
    with pytest.raises(GraphExecutionError, match="on_error"):
        executor.run({"items": [1]})


@pytest.mark.parametrize("value", [0, False])
def test_zero_and_false_are_valid_artifacts(value):
    executor = _executor(
        [
            {"id": "start", "strategy": "transform", "next": ["last"]},
            {"id": "last", "strategy": "transform"},
        ],
        {"transform": lambda stage, inputs: StageResult({"items": inputs["items"]})},
    )
    assert executor.run({"items": value}).outputs["last"]["items"] == value


def test_compilation_snapshots_definition_and_rejects_missing_handlers_and_bad_config():
    executor = _executor(
        [{"id": "start", "strategy": "transform", "config": {"offset": 2}}],
        {
            "transform": lambda stage, inputs: StageResult(
                {"items": [stage.config["offset"]]}
            )
        },
    )
    assert executor.run({"items": [1]}).outputs["start"]["items"] == [2]
    with pytest.raises(ValueError, match="No server handler"):
        _executor([{"id": "start", "strategy": "transform"}], {})
    with pytest.raises(ValueError):
        _executor(
            [{"id": "start", "strategy": "transform", "config": {"offset": "bad"}}],
            {"transform": lambda stage, inputs: StageResult({"items": []})},
        )


def test_cycle_and_missing_run_input_are_rejected():
    handler = {
        "transform": lambda stage, inputs: StageResult({"items": inputs["items"]})
    }
    with pytest.raises(ValueError, match="cycle"):
        _executor(
            [
                {"id": "start", "strategy": "transform", "next": ["last"]},
                {"id": "last", "strategy": "transform", "next": ["start"]},
            ],
            handler,
        )
    executor = _executor([{"id": "start", "strategy": "transform"}], handler)
    with pytest.raises(GraphExecutionError, match="missing_run_input"):
        executor.run({})


@pytest.mark.parametrize("version,attempts", [(1, 2), (2, 1)])
@pytest.mark.parametrize("primary_fails", [False, True])
def test_historical_metadata_builtins_keep_attempt_budgets_and_provider_fallback(
    version, attempts, primary_fails
):
    from app.pipelines.defaults import built_in_pipeline
    from app.pipelines.purposes import purpose_registry
    from app.pipelines.registry import strategy_registry

    calls = []

    def invoke(stage, inputs):
        calls.append(
            (stage.config["provider_role"], stage.config["attempts"], inputs["context"])
        )
        if primary_fails and stage.config["provider_role"] == "primary":
            raise TimeoutError()
        return StageResult(
            {"answer": {"label": "proposal"}},
            provider="fake",
            model=stage.config["provider_role"],
        )

    executor = GraphExecutor(
        built_in_pipeline("corpus.metadata_enrichment.current", version),
        registry=strategy_registry,
        purpose=purpose_registry.get("corpus_metadata_enrichment"),
        handlers={"llm.structured_metadata": invoke},
    )
    result = executor.run(
        {"context": {"record_id": "R1", "task": "schema-derived task"}}
    )
    assert len(calls) == (2 if primary_fails else 1)
    assert calls[0][:2] == ("primary", attempts)
    assert calls[-1][2] == calls[0][2]
    assert sum(trace.output_count or 0 for trace in result.stages) == 1
    assert result.stages[-1].status == ("completed" if primary_fails else "skipped")


def test_multiple_fallback_port_does_not_add_an_extra_payload_layer():
    def handler(stage, inputs):
        if stage.id == "start":
            raise TimeoutError()
        return StageResult({"items": inputs["items"]})

    result = _executor(
        [
            {"id": "start", "strategy": "transform", "on_timeout": "fallback"},
            {"id": "fallback", "strategy": "transform"},
        ],
        {"transform": handler},
        specs=[_strategy("transform", multiple=True)],
    ).run({"items": [1, 2]})
    assert result.outputs["fallback"]["items"] == [[1, 2]]


def _trait_executor(
    stages, specs, *, required_output_traits=(), run_traits=(), handlers=None
):
    purpose = PURPOSE.model_copy(
        update={
            "required_output_traits": list(required_output_traits),
            "run_inputs": [
                RunInputSpec(
                    name="items",
                    data_type="candidate_set",
                    produced_traits=list(run_traits),
                )
            ],
        }
    )
    pipeline = PipelineDefinition(
        pipeline_id="test.traits",
        name="Test traits",
        purpose="test_graph",
        entry_stage_ids=["start"],
        stages=stages,
    )
    return GraphExecutor(
        pipeline,
        registry=StrategyRegistry(specs),
        purpose=purpose,
        handlers=handlers
        or {
            spec.strategy_id: lambda stage, inputs: StageResult(
                {"items": inputs["items"]}
            )
            for spec in specs
        },
    )


def test_required_input_traits_reject_same_type_without_support_and_accept_substitution():
    producer = _strategy("collect")
    consumer = _strategy("validate")
    consumer.inputs[0].required_traits = ["source_bound"]
    consumer.outputs[0].produced_traits = ["source_bound", "support_validated"]
    stages = [
        {"id": "start", "strategy": "collect", "next": ["final"]},
        {"id": "final", "strategy": "validate"},
    ]
    with pytest.raises(ValueError, match="requires traits missing"):
        _trait_executor(stages, [producer, consumer])
    producer.outputs[0].produced_traits = ["source_bound"]
    executor = _trait_executor(
        stages,
        [producer, consumer],
        required_output_traits=["source_bound", "support_validated"],
    )
    assert executor.run({"items": [1]}).terminal_outputs == {"final": {"items": [1]}}
    # Guarantees are supplied by contracts, not by strategy-name checks.
    substitute = consumer.model_copy(
        deep=True, update={"strategy_id": "alternative_validator"}
    )
    stages[1]["strategy"] = substitute.strategy_id
    assert (
        _trait_executor(
            stages, [producer, substitute], required_output_traits=["support_validated"]
        )
        .run({"items": [1]})
        .terminal_outputs
    )


def test_trait_requirements_apply_to_explicit_bindings_and_run_inputs():
    producer = _strategy("collect")
    consumer = _strategy("validate")
    consumer.inputs[0].required_traits = ["source_bound"]
    stages = [
        {"id": "start", "strategy": "collect", "next": ["final"]},
        {
            "id": "final",
            "strategy": "validate",
            "inputs": {
                "items": [{"source": "stage", "stage": "start", "output": "items"}]
            },
        },
    ]
    with pytest.raises(ValueError, match="requires traits missing"):
        _trait_executor(stages, [producer, consumer])
    with pytest.raises(ValueError):
        _trait_executor([{"id": "start", "strategy": "validate"}], [consumer])
    result = _trait_executor(
        [{"id": "start", "strategy": "validate"}],
        [consumer],
        run_traits=["source_bound"],
    ).run({"items": [1]})
    assert result.terminal_outputs == {"start": {"items": [1]}}


@pytest.mark.parametrize("shared_target", [False, True])
def test_fallback_does_not_inherit_the_failed_stage_output_traits(shared_target):
    scorer = _strategy("score")
    scorer.outputs[0].produced_traits = ["support_validated"]
    fallback = _strategy("fallback")
    fallback.inputs[0].required_traits = ["support_validated"]
    stages = [
        {
            "id": "start",
            "strategy": "score",
            "on_error": "fallback",
            "next": ["fallback"] if shared_target else [],
        },
        {"id": "fallback", "strategy": "fallback"},
    ]
    with pytest.raises(ValueError, match="requires traits missing"):
        _trait_executor(stages, [scorer, fallback])


def test_terminal_contract_rejects_missing_guarantees_and_any_type_bypass():
    spec = _strategy("collect")
    stages = [{"id": "start", "strategy": "collect"}]
    with pytest.raises(ValueError, match="lacks required traits"):
        _trait_executor(stages, [spec], required_output_traits=["support_validated"])
    spec.outputs[0].data_type = "any"
    with pytest.raises(ValueError, match="No reachable terminal"):
        _trait_executor(stages, [spec])


def test_no_terminal_execution_is_a_visible_failure():
    producer = _strategy("collect")
    consumer = _strategy("validate")
    executor = _trait_executor(
        [
            {"id": "start", "strategy": "collect", "next": ["final"]},
            {"id": "final", "strategy": "validate"},
        ],
        [producer, consumer],
        handlers={
            "collect": lambda stage, inputs: StageResult({"items": []}),
            "validate": lambda stage, inputs: pytest.fail("empty branch must skip"),
        },
    )
    with pytest.raises(GraphExecutionError, match="missing_terminal_output"):
        executor.run({"items": [1]})


def test_wiring_options_exclude_outputs_that_lack_required_traits():
    producer = _strategy("collect")
    consumer = _strategy("validate")
    consumer.inputs[0].required_traits = ["source_bound"]
    executor = _trait_executor(
        [
            {"id": "start", "strategy": "collect", "next": ["final"]},
            {
                "id": "final",
                "strategy": "validate",
                "inputs": {"items": [{"source": "run_input", "name": "items"}]},
            },
        ],
        [producer, consumer],
        run_traits=["source_bound"],
    )
    port = executor.wiring["stages"]["final"]["inputs"][0]
    assert port["required_traits"] == ["source_bound"]
    assert not any(option.get("stage") == "start" for option in port["options"])


def test_named_output_binding_is_validated_instead_of_primary_output_summary():
    from app.pipelines.purposes import purpose_registry
    from app.pipelines.service import PipelineService

    producer = _strategy("collect")
    producer.input_type = "context_packet"
    producer.inputs[0].data_type = "context_packet"
    producer.output_type = "context_packet"
    producer.outputs = [
        PortSpec(name="diagnostic", data_type="context_packet"),
        PortSpec(name="proposal", data_type="model_output"),
    ]
    consumer = _strategy("validate")
    consumer.input_type = consumer.output_type = "model_output"
    consumer.inputs[0].data_type = consumer.outputs[0].data_type = "model_output"
    pipeline = PipelineDefinition(
        pipeline_id="test.named_outputs",
        name="Test named outputs",
        purpose="corpus_metadata_enrichment",
        entry_stage_ids=["start"],
        stages=[
            {"id": "start", "strategy": "collect", "next": ["final"]},
            {
                "id": "final",
                "strategy": "validate",
                "inputs": {
                    "items": [
                        {"source": "stage", "stage": "start", "output": "proposal"}
                    ]
                },
            },
        ],
    )
    registry = StrategyRegistry([producer, consumer])
    assert PipelineService(registry).validate(pipeline).valid
    result = GraphExecutor(
        pipeline,
        registry=registry,
        purpose=purpose_registry.get("corpus_metadata_enrichment"),
        handlers={
            "collect": lambda stage, inputs: StageResult(
                {"diagnostic": {}, "proposal": {"label": "proposal"}}
            ),
            "validate": lambda stage, inputs: StageResult({"items": inputs["items"]}),
        },
    ).run({"context": {"record_id": "R1"}})
    assert result.terminal_outputs == {"final": {"items": {"label": "proposal"}}}


def test_fanin_requires_guarantees_from_every_bound_source():
    first, second, merge = (
        _strategy("first"),
        _strategy("second"),
        _strategy("merge", multiple=True),
    )
    first.outputs[0].produced_traits = ["source_bound"]
    merge.inputs[0].required_traits = ["source_bound"]
    with pytest.raises(ValueError, match="requires traits missing"):
        _trait_executor(
            [
                {"id": "start", "strategy": "first", "next": ["second", "merge"]},
                {"id": "second", "strategy": "second", "next": ["merge"]},
                {
                    "id": "merge",
                    "strategy": "merge",
                    "inputs": {
                        "items": [
                            {"source": "stage", "stage": "start", "output": "items"},
                            {"source": "stage", "stage": "second", "output": "items"},
                        ]
                    },
                },
            ],
            [first, second, merge],
        )


def _parallel_graph(handler, *, capability=None, workers=2):
    return _executor(
        [
            {"id": "left", "strategy": "transform", "next": ["merge"]},
            {"id": "right", "strategy": "transform", "next": ["merge"]},
            {"id": "merge", "strategy": "merge"},
        ],
        {"transform": handler, "merge": lambda stage, inputs: StageResult(inputs)},
        specs=[_strategy("transform"), _strategy("merge", multiple=True)],
        entries=("left", "right"),
        concurrency={"transform": capability} if capability else {},
        max_workers=workers,
    )


def test_parallel_branches_overlap_and_merge_in_definition_order():
    rendezvous = Barrier(2, timeout=5)
    right_finished = Event()

    def handler(stage, inputs):
        rendezvous.wait()
        if stage.id == "right":
            right_finished.set()
        else:
            assert right_finished.wait(5)
        return StageResult({"items": [stage.id]})

    executor = _parallel_graph(handler, capability=ConcurrencyCapability("provider", 2))
    result = executor.run({"items": ["source"]})
    assert result.terminal_outputs == {"merge": {"items": [["left"], ["right"]]}}
    assert [trace.stage_id for trace in result.stages] == ["left", "right", "merge"]
    assert all(trace.status == "completed" for trace in result.stages)


@pytest.mark.parametrize(
    "capability,workers", [(None, 2), (ConcurrencyCapability("provider", 2), 1)]
)
def test_undeclared_handlers_and_default_worker_limit_remain_serial(
    capability, workers
):
    calls = []

    def handler(stage, inputs):
        calls.append(stage.id)
        return StageResult({"items": [stage.id]})

    result = _parallel_graph(handler, capability=capability, workers=workers).run(
        {"items": [1]}
    )
    assert calls == ["left", "right"]
    assert result.terminal_outputs["merge"]["items"] == [["left"], ["right"]]


def test_provider_capacity_is_shared_across_concurrent_runs():
    lock = Lock()
    release = Event()
    at_capacity = Event()
    active = peak = calls = 0

    def handler(stage, inputs):
        nonlocal active, peak, calls
        with lock:
            active += 1
            calls += 1
            peak = max(peak, active)
            if active == 2:
                at_capacity.set()
        try:
            assert release.wait(5)
            return StageResult({"items": [stage.id]})
        finally:
            with lock:
                active -= 1

    executor = _parallel_graph(handler, capability=ConcurrencyCapability("provider", 2))
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(executor.run, {"items": [1]})
        second = pool.submit(executor.run, {"items": [2]})
        try:
            assert at_capacity.wait(5)
        finally:
            release.set()
        assert first.result().terminal_outputs == second.result().terminal_outputs
    assert (peak, calls, active) == (2, 4, 0)


def test_parallel_failure_joins_sibling_and_fallback_receives_original_input():
    rendezvous = Barrier(2, timeout=5)
    sibling_finished = Event()

    def handler(stage, inputs):
        if stage.id in {"left", "right"}:
            rendezvous.wait()
            if stage.id == "left":
                raise LookupError("private")
            sibling_finished.set()
        return StageResult({"items": inputs["items"]})

    executor = _executor(
        [
            {"id": "left", "strategy": "transform", "on_unavailable": "fallback"},
            {"id": "right", "strategy": "transform"},
            {"id": "fallback", "strategy": "transform"},
        ],
        {"transform": handler},
        entries=("left", "right"),
        concurrency={"transform": ConcurrencyCapability("provider", 2)},
        max_workers=2,
    )
    result = executor.run({"items": ["original"]})
    assert sibling_finished.is_set()
    assert result.outputs["fallback"]["items"] == ["original"]
    assert result.stages[0].status == "unavailable"
    assert "private" not in repr(result.stages)


@pytest.mark.parametrize("failure", [ValueError("private"), InterruptedError()])
def test_parallel_fatal_failure_and_cancellation_join_running_sibling(failure):
    rendezvous = Barrier(2, timeout=5)
    sibling_finished = Event()

    def handler(stage, inputs):
        rendezvous.wait()
        if stage.id == "left":
            raise failure
        sibling_finished.set()
        return StageResult({"items": inputs["items"]})

    executor = _parallel_graph(handler, capability=ConcurrencyCapability("provider", 2))
    with pytest.raises(
        InterruptedError
        if isinstance(failure, InterruptedError)
        else GraphExecutionError
    ):
        executor.run({"items": [1]})
    assert sibling_finished.is_set()


def test_concurrency_rejects_conflicting_capacity_limits():
    with pytest.raises(ValueError, match="one limit"):
        _executor(
            [{"id": "start", "strategy": "transform"}],
            {
                "transform": lambda stage, inputs: StageResult(inputs),
                "other": lambda stage, inputs: StageResult(inputs),
            },
            concurrency={
                "transform": ConcurrencyCapability("provider", 1),
                "other": ConcurrencyCapability("provider", 2),
            },
        )


def test_parallel_empty_branch_does_not_run_downstream_provider():
    rendezvous = Barrier(2, timeout=5)
    calls = []

    def handler(stage, inputs):
        calls.append(stage.id)
        if stage.id in {"left", "right"}:
            rendezvous.wait()
        return StageResult({"items": [] if stage.id == "left" else inputs["items"]})

    executor = _executor(
        [
            {"id": "left", "strategy": "transform", "next": ["empty_child"]},
            {"id": "right", "strategy": "transform"},
            {"id": "empty_child", "strategy": "transform"},
        ],
        {"transform": handler},
        entries=("left", "right"),
        concurrency={"transform": ConcurrencyCapability("provider", 2)},
        max_workers=2,
    )
    result = executor.run({"items": [1]})
    assert set(calls) == {"left", "right"}
    assert result.stages[2].fallback_reason == "empty_required_input"


def test_unsafe_handler_is_a_barrier_between_parallel_waves():
    calls = []

    def handler(stage, inputs):
        calls.append(stage.id)
        return StageResult({"items": inputs["items"]})

    executor = _executor(
        [
            {"id": "start", "strategy": "transform"},
            {"id": "unsafe", "strategy": "unsafe"},
            {"id": "last", "strategy": "transform"},
        ],
        {"transform": handler, "unsafe": handler},
        specs=[_strategy("transform"), _strategy("unsafe")],
        entries=("start", "unsafe", "last"),
        concurrency={"transform": ConcurrencyCapability("provider", 2)},
        max_workers=2,
    )
    executor.run({"items": [1]})
    assert calls == ["start", "unsafe", "last"]
