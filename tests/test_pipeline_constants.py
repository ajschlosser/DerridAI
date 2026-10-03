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


def _bound_run(mode: str, stage_id: str, port: str, value: float):
    pipeline = _with_input(built_in_pipeline(*MODE_PIPELINES[mode]), stage_id, port, _constant(value))
    request = StoreSearchRequest(store="db", query="stranger", n_results=3, where=None, fetch_k=12, lambda_mult=0.5)
    run = execute_store_search(
        compile_store_search_pipeline(pipeline),
        store=fake_store(embeddings=FakeEmbeddings()),
        request=request,
        resolved_hash=pipeline_hash(pipeline),
    )
    return {stage.stage_id: stage.parameters for stage in run.trace.stages}


def _stage_of(mode: str, strategy: str) -> str:
    return next(s.id for s in built_in_pipeline(*MODE_PIPELINES[mode]).stages if s.strategy == strategy)


@pytest.mark.parametrize(
    ("mode", "strategy", "port", "value", "parameter"),
    [
        ("hybrid", "fusion.rrf", "rrf_k", 10, "rrf_k"),
        ("mmr", "select.mmr", "lambda_mult", 0.9, "lambda_mult"),
        ("mmr", "select.mmr", "limit", 2, "limit"),
        ("similarity", "retrieve.chroma_similarity", "fetch_k", 7, "fetch_k"),
        ("lexical", "retrieve.lexical_bm25", "fetch_k", 5, "fetch_k"),
    ],
)
def test_tuning_constants_reach_the_stage_that_owns_them(mode, strategy, port, value, parameter) -> None:
    stage_id = _stage_of(mode, strategy)
    assert _issues(_with_input(built_in_pipeline(*MODE_PIPELINES[mode]), stage_id, port, _constant(value))) == []
    assert _bound_run(mode, stage_id, port, value)[stage_id][parameter] == value


def test_tuning_constants_respect_their_declared_range() -> None:
    stage_id = _stage_of("mmr", "select.mmr")
    for value in (-0.1, 1.5):
        pipeline = _with_input(built_in_pipeline(*MODE_PIPELINES["mmr"]), stage_id, "lambda_mult", _constant(value))
        assert "binding_constant_out_of_range" in _issues(pipeline)


def test_retrieval_traces_record_the_collection_size_as_a_count() -> None:
    pipeline = built_in_pipeline(*MODE_PIPELINES["hybrid"])
    request = StoreSearchRequest(store="db", query="stranger", n_results=3, where=None, fetch_k=12, lambda_mult=0.5)
    run = execute_store_search(
        compile_store_search_pipeline(pipeline),
        store=fake_store(embeddings=FakeEmbeddings()),
        request=request,
        resolved_hash=pipeline_hash(pipeline),
        collection_identity={"scope_size": 40},
    )
    sizes = {s.strategy_id: s.parameters.get("scope_size") for s in run.trace.stages}
    assert sizes["retrieve.chroma_similarity"] == sizes["retrieve.lexical_bm25"] == 40
    assert sizes["fusion.rrf"] is None  # only the stages that search the collection


def test_latency_fits_growth_against_collection_size() -> None:
    from datetime import UTC, datetime

    from app.pipelines.latency import strategy_latency
    from app.pipelines.models import PipelineRunTrace
    from app.pipelines.trace_safety import trace_stage

    now = datetime.now(UTC)
    runs = []
    for scope in (100, 200, 400, 800, 100, 200, 400, 800):
        stage = trace_stage(
            "lex", "retrieve.lexical_bm25", elapsed_seconds=scope / 1000, input_count=3, output_count=3,
            parameters={"scope_size": scope},
        )
        runs.append(
            PipelineRunTrace(
                run_id=f"r{scope}{len(runs)}", feature="search", pipeline_id="p", pipeline_version=1,
                resolved_pipeline={}, resolved_hash="h", status="completed", started_at=now, finished_at=now,
                total_elapsed_ms=1, stages=[stage],
            )
        )
    row = strategy_latency(runs)["retrieve.lexical_bm25"]
    assert row["observed_scaling"] is None  # candidate count never varied
    assert row["observed_scope_scaling"]["exponent"] == pytest.approx(1.0, abs=0.05)
