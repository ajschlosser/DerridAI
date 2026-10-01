# Copyright 2026 Aaron John Schlosser, PhD.
"""Constant inputs: a fixed number on a tuning port, and nowhere else."""

from __future__ import annotations

import pytest
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.models import InputBinding, PipelineDefinition
from app.pipelines.purposes import purpose_registry
from app.pipelines.registry import strategy_registry
from app.pipelines.service import (
    PipelineService,
    canonical_pipeline_json,
    pipeline_hash,
)
from app.pipelines.store_search import (
    MODE_PIPELINES,
    StoreSearchRequest,
    compile_store_search_pipeline,
    execute_store_search,
)
from app.pipelines.wiring import resolve_wiring
from pydantic import ValidationError
from store_search_fakes import FakeEmbeddings, fake_store


def _constant(value: float) -> InputBinding:
    return InputBinding(source="constant", value=value)


def _with_input(pipeline: PipelineDefinition, stage_id: str, port: str, binding: InputBinding) -> PipelineDefinition:
    return pipeline.model_copy(
        update={
            "pipeline_id": pipeline.pipeline_id + ".const",
            "built_in": False,
            "stages": [
                s.model_copy(update={"inputs": {port: [binding]}}) if s.id == stage_id else s
                for s in pipeline.stages
            ],
        }
    )


def _hybrid() -> PipelineDefinition:
    return built_in_pipeline(*MODE_PIPELINES["similarity"])


def _issues(pipeline: PipelineDefinition) -> list[str]:
    wiring = resolve_wiring(pipeline, strategy_registry, purpose_registry.get(pipeline.purpose))
    return [i.code for i in wiring["issues"] if i.level == "error"]


def test_binding_shape_is_validated() -> None:
    with pytest.raises(ValidationError):
        InputBinding(source="constant")  # needs a value
    with pytest.raises(ValidationError):
        InputBinding(source="run_input", name="query", value=3)  # only constants carry one
    for bad in (float("inf"), float("nan"), 1e9):
        with pytest.raises(ValidationError):
            InputBinding(source="constant", value=bad)


def test_constant_binds_to_a_tuning_port_and_round_trips() -> None:
    pipeline = _with_input(_hybrid(), "select", "limit", _constant(2))
    assert _issues(pipeline) == []
    again = PipelineDefinition.model_validate_json(canonical_pipeline_json(pipeline))
    assert again.stages[-1].inputs["limit"][0].value == 2
    assert pipeline_hash(again) == pipeline_hash(pipeline)
    assert PipelineService().validate(pipeline).valid


def test_constants_are_refused_on_query_and_candidate_ports() -> None:
    for stage_id, port in (("select", "candidates"), ("dense", "query")):
        pipeline = _with_input(_hybrid(), stage_id, port, _constant(3))
        assert "binding_constant_not_allowed" in _issues(pipeline)


def test_constant_outside_the_declared_range_is_refused() -> None:
    for value in (0, 5000):
        assert "binding_constant_out_of_range" in _issues(_with_input(_hybrid(), "select", "limit", _constant(value)))


def test_pipelines_without_constants_keep_their_identity() -> None:
    bound = InputBinding(source="stage", stage="query", output="query")
    assert "value" not in bound.model_dump()
    assert "inputs" not in built_in_pipeline(*MODE_PIPELINES["similarity"]).stages[0].model_dump()


def test_store_search_delivers_the_constant() -> None:
    request = StoreSearchRequest(store="db", query="stranger", n_results=3, where=None, fetch_k=12, lambda_mult=0.5)
    pipeline = _with_input(_hybrid(), "select", "limit", _constant(1))
    plan = compile_store_search_pipeline(pipeline)
    assert plan.constants == {"select": {"limit": 1.0}}
    run = execute_store_search(
        plan, store=fake_store(embeddings=FakeEmbeddings()), request=request, resolved_hash=pipeline_hash(pipeline)
    )
    assert len(run.results) == 1
    assert run.trace.warnings == ["rewired_inputs: select.limit"]
    # A constant can narrow the request but never raise it above what was asked for.
    wide = compile_store_search_pipeline(_with_input(_hybrid(), "select", "limit", _constant(900)))
    assert len(execute_store_search(wide, store=fake_store(embeddings=FakeEmbeddings()), request=request, resolved_hash="x").results) <= 3


def test_other_purposes_keep_a_constant_inspect_only() -> None:
    from app.pipelines.defaults import BUILT_IN_PIPELINES
    from app.pipelines.workflows import runtime_support

    source = next(
        p
        for p in BUILT_IN_PIPELINES
        if p.purpose == "evidence_suggestion"
        and any(s.strategy == "select.top_k" for s in p.stages)
        and runtime_support(p)["supported"]
    )
    top_k = next(s.id for s in source.stages if s.strategy == "select.top_k")
    assert runtime_support(source)["supported"] is True
    rewired = _with_input(source, top_k, "limit", _constant(2))
    assert _issues(rewired) == []
    assert runtime_support(rewired)["supported"] is False
