# Copyright 2026 Aaron John Schlosser, PhD.
"""Typed stage inputs, binding validation, declared complexity and latency estimates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.pipelines.analysis import TraceSampler, analyze_pipeline, conditional_stages
from app.pipelines.complexity import analyze_complexity
from app.pipelines.contracts import input_ports, output_ports
from app.pipelines.defaults import BUILT_IN_PIPELINES
from app.pipelines.latency import (
    estimate_pipeline_latency,
    fit_scaling,
    percentile,
    strategy_latency,
)
from app.pipelines.models import (
    PipelineDefinition,
    PipelineRunTrace,
    PipelineStageTrace,
)
from app.pipelines.registry import strategy_registry
from app.pipelines.service import PipelineService, pipeline_hash
from app.pipelines.workflows import runtime_support

WIRING_CODES = {
    "input_unbound",
    "input_type_mismatch",
    "input_multiple_sources",
    "binding_unknown_port",
    "binding_unknown_stage",
    "binding_unknown_output",
    "binding_unknown_run_input",
    "binding_not_upstream",
    "binding_producer_disabled",
}


def _built_in(pipeline_id: str) -> PipelineDefinition:
    return next(item for item in BUILT_IN_PIPELINES if item.pipeline_id == pipeline_id)


def _research(stages: list[dict[str, Any]], entry: list[str] | None = None) -> PipelineDefinition:
    return PipelineDefinition.model_validate(
        {
            "pipeline_id": "wiring.test",
            "version": 1,
            "name": "Wiring test",
            "purpose": "research",
            "entry_stage_ids": entry or [stages[0]["id"]],
            "stages": stages,
        }
    )


def _codes(pipeline: PipelineDefinition) -> set[str]:
    return {issue.code for issue in PipelineService().validate(pipeline).issues}


def test_every_strategy_declares_typed_ports_and_complexity_consistent_with_its_types() -> None:
    for spec in strategy_registry.list():
        assert spec.complexity is not None, spec.strategy_id
        assert spec.inputs and spec.outputs, spec.strategy_id
        # The primary ports are the single input/output type the registry summarises.
        assert input_ports(spec)[0].data_type == spec.input_type, spec.strategy_id
        assert output_ports(spec)[0].data_type == spec.output_type, spec.strategy_id
        assert all(name in "nNkLqgPdS" for name in spec.complexity.variables), spec.strategy_id


def test_built_in_pipelines_wire_without_new_input_errors_or_identity_changes() -> None:
    service = PipelineService()
    for pipeline in BUILT_IN_PIPELINES:
        codes = {issue.code for issue in service.validate(pipeline).issues}
        assert not (codes & WIRING_CODES), (pipeline.pipeline_id, pipeline.version, codes)
        # Pipelines without explicit bindings serialise exactly as before, so
        # identity hashes recorded in historical traces stay valid.
        assert all("inputs" not in stage for stage in pipeline.model_dump(mode="json")["stages"])


def test_edge_that_hands_a_stage_the_wrong_type_is_still_rejected() -> None:
    pipeline = _research(
        [
            {"id": "query", "strategy": "query.passthrough", "next": ["generate"]},
            # generate takes a context packet; a query cannot stand in for it.
            {"id": "generate", "strategy": "llm.generate_answer"},
        ]
    )

    result = PipelineService().validate(pipeline)

    assert "incompatible_stage_types" in {i.code for i in result.issues}
    assert not result.valid


def test_required_port_with_no_source_reports_input_unbound() -> None:
    # A corpus workflow supplies only ``context``; a reranker needs a ``query``.
    pipeline = PipelineDefinition.model_validate(
        {
            "pipeline_id": "unbound.test",
            "version": 1,
            "name": "Unbound",
            "purpose": "corpus_text_touchup",
            "entry_stage_ids": ["rerank"],
            "stages": [{"id": "rerank", "strategy": "rerank.cross_encoder"}],
        }
    )

    issues = [i for i in PipelineService().validate(pipeline).issues if i.code == "input_unbound"]

    assert {i.stage_id for i in issues} == {"rerank"}
    assert any("'query'" in i.message for i in issues)


def test_orphan_stage_with_required_input_reports_input_unbound() -> None:
    pipeline = _research(
        [
            {"id": "query", "strategy": "query.passthrough", "next": ["dense"]},
            {"id": "dense", "strategy": "retrieve.chroma_similarity", "next": ["pack"]},
            {"id": "pack", "strategy": "pack.evidence_context", "next": ["generate"]},
            # Needs ``context`` but the packer feeding it is bypassed by an explicit binding
            # to a stage that does not exist.
            {
                "id": "generate",
                "strategy": "llm.generate_answer",
                "inputs": {"context": [{"source": "stage", "stage": "ghost"}]},
            },
        ]
    )

    codes = _codes(pipeline)

    assert "binding_unknown_stage" in codes


def test_explicit_binding_must_be_type_compatible_and_upstream() -> None:
    base = [
        {"id": "query", "strategy": "query.passthrough", "next": ["dense"]},
        {"id": "dense", "strategy": "retrieve.chroma_similarity", "next": ["rerank"]},
        {"id": "rerank", "strategy": "rerank.cross_encoder", "next": ["pack"]},
        {"id": "pack", "strategy": "pack.evidence_context"},
    ]
    # The rerank query may come from the query stage, which runs before it.
    good = [dict(stage) for stage in base]
    good[2] = {**good[2], "inputs": {"query": [{"source": "stage", "stage": "query"}]}}
    assert "input_type_mismatch" not in _codes(_research(good))
    assert "binding_not_upstream" not in _codes(_research(good))

    # Candidates cannot feed a query port.
    wrong_type = [dict(stage) for stage in base]
    wrong_type[2] = {**wrong_type[2], "inputs": {"query": [{"source": "stage", "stage": "dense"}]}}
    assert "input_type_mismatch" in _codes(_research(wrong_type))

    # pack runs after rerank, so it cannot feed it.
    downstream = [dict(stage) for stage in base]
    downstream[2] = {
        **downstream[2],
        "inputs": {"candidates": [{"source": "stage", "stage": "pack"}]},
    }
    assert "binding_not_upstream" in _codes(_research(downstream))


def test_run_input_binding_must_be_supplied_by_the_workflow() -> None:
    stages = [
        {
            "id": "query",
            "strategy": "query.passthrough",
            "inputs": {"query": [{"source": "run_input", "name": "no_such_input"}]},
        }
    ]

    assert "binding_unknown_run_input" in _codes(_research(stages))

    stages[0]["inputs"] = {"query": [{"source": "run_input", "name": "query"}]}
    assert not (_codes(_research(stages)) & WIRING_CODES)


def test_a_port_that_takes_one_value_rejects_several_normal_sources() -> None:
    pipeline = _research(
        [
            {"id": "a", "strategy": "query.passthrough", "next": ["merge"]},
            {"id": "b", "strategy": "query.passthrough", "next": ["merge"]},
            {"id": "merge", "strategy": "query.passthrough"},
        ],
        entry=["a", "b"],
    )

    assert "input_multiple_sources" in _codes(pipeline)


def test_unknown_port_binding_is_rejected() -> None:
    pipeline = _research(
        [
            {
                "id": "query",
                "strategy": "query.passthrough",
                "inputs": {"nonsense": [{"source": "run_input", "name": "query"}]},
            }
        ]
    )

    assert "binding_unknown_port" in _codes(pipeline)


def _with_binding(
    pipeline: PipelineDefinition, stage_id: str, port: str, binding: dict[str, str]
) -> PipelineDefinition:
    payload = pipeline.model_dump(mode="json")
    for stage in payload["stages"]:
        if stage["id"] == stage_id:
            stage["inputs"] = {port: [binding]}
    return PipelineDefinition.model_validate(payload)


def test_bindings_that_change_wiring_make_a_pipeline_inspect_only() -> None:
    pipeline = _built_in("research.current")
    assert runtime_support(pipeline)["supported"] is True

    # Restating the implicit run-input wiring is harmless.
    same = _with_binding(pipeline, "rerank", "query", {"source": "run_input", "name": "query"})
    assert runtime_support(same)["supported"] is True

    # Rewiring the query to the decomposed query is something no adapter applies.
    changed = _with_binding(pipeline, "rerank", "query", {"source": "stage", "stage": "query"})
    support = runtime_support(changed)
    assert support["supported"] is False
    assert "rerank.query" in support["reason"]
    assert pipeline_hash(changed) != pipeline_hash(pipeline)


def test_wiring_reports_sources_options_and_consumers() -> None:
    pipeline = _built_in("research.current")
    analysis = analyze_pipeline(
        pipeline,
        strategy_registry,
        resolved_hash=pipeline_hash(pipeline),
        sample_runs=[],
        pipeline_runs=[],
    )

    rerank = {row["port"]: row for row in analysis["wiring"]["stages"]["rerank"]["inputs"]}
    assert rerank["candidates"]["sources"][0]["stage"] == "rrf"
    assert rerank["candidates"]["explicit"] is False
    assert rerank["query"]["sources"][0] == {
        **rerank["query"]["sources"][0],
        "kind": "run_input",
        "name": "query",
    }
    # A query port can be re-sourced from the upstream query stage, not from candidates.
    option_stages = {
        (item["stage"], item["output"])
        for item in rerank["query"]["options"]
        if item["kind"] == "stage"
    }
    assert ("query", "query") in option_stages
    assert all(stage != "dense" for stage, _ in option_stages)

    rrf_outputs = analysis["wiring"]["stages"]["rrf"]["outputs"]
    assert {"stage": "rerank", "port": "candidates"} in rrf_outputs[0]["consumers"]
    # A fallback target receives what the failed stage was given.
    fallback = analysis["wiring"]["stages"]["rerank_fallback"]["inputs"][0]["sources"]
    assert {s["via"] for s in fallback} == {"on_unavailable", "on_timeout", "on_error"}
    assert fallback[0]["kind"] == "stage_input"
    assert conditional_stages(pipeline) == {"rerank_fallback"}


def test_complexity_bounds_candidates_by_origin_not_by_path() -> None:
    pipeline = _built_in("research.current")

    result = analyze_complexity(pipeline, strategy_registry, conditional_stages(pipeline))
    rows = {row["stage_id"]: row for row in result["stages"]}

    # dense feeds rrf directly and through mmr; the lexical leg adds its own 500.
    assert rows["rrf"]["n_in"] == 1000
    assert rows["rerank"]["n_out"] == 24
    assert rows["rerank"]["model_calls"] == {"formula": "n", "max": 1000}
    summary = result["summary"]
    assert summary["scales_with_scope"] is True
    assert set(summary["scope_stage_ids"]) == {"dense", "lexical"}
    assert summary["candidate_bound"] == 1000
    assert summary["model_calls"]["model_inference"]["stage_ids"] == ["rerank"]
    assert summary["model_calls"]["llm_generation"]["max_calls"] == 3


def test_unconfigured_retrieval_leaves_candidate_counts_request_bound() -> None:
    pipeline = _built_in("evidence.conservative")

    result = analyze_complexity(pipeline, strategy_registry, conditional_stages(pipeline))

    assert result["summary"]["candidates_request_bound"] is True
    assert result["summary"]["candidate_bound"] is None
    llm_choice = next(row for row in result["stages"] if row["stage_id"] == "llm_choice")
    assert llm_choice["conditional"] is True
    assert llm_choice["model_calls"]["max"] == 2


def _trace(
    run_id: str,
    stages: list[PipelineStageTrace],
    *,
    pipeline_hash_value: str = "a" * 64,
    total: int = 100,
    pipeline_id: str = "research.current",
) -> PipelineRunTrace:
    started = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
    return PipelineRunTrace(
        run_id=run_id,
        feature="research",
        pipeline_id=pipeline_id,
        pipeline_version=1,
        resolved_pipeline={},
        resolved_hash=pipeline_hash_value,
        status="completed",
        started_at=started,
        finished_at=started + timedelta(milliseconds=total),
        total_elapsed_ms=total,
        stages=stages,
    )


def _stage(
    stage_id: str,
    strategy: str,
    ms: int | None,
    *,
    status: str = "completed",
    inputs: int | None = None,
    model: str | None = None,
) -> PipelineStageTrace:
    return PipelineStageTrace(
        stage_id=stage_id,
        strategy_id=strategy,
        status=status,  # type: ignore[arg-type]
        elapsed_ms=ms,
        input_count=inputs,
        model=model,
    )


def test_percentiles_interpolate_and_handle_tiny_samples() -> None:
    assert percentile([], 0.5) is None
    assert percentile([7], 0.9) == 7
    assert percentile([10, 20, 30, 40], 0.5) == 25
    assert percentile([0, 100], 0.9) == 90


def test_scaling_fit_recovers_a_linear_and_a_quadratic_relationship() -> None:
    linear = fit_scaling([(n, 3.0 * n) for n in (10, 20, 40, 80, 160, 320, 640, 1280)])
    quadratic = fit_scaling([(n, 0.01 * n * n) for n in (10, 20, 40, 80, 160, 320, 640, 1280)])

    assert linear is not None and abs(linear["exponent"] - 1.0) < 0.01
    assert quadratic is not None and abs(quadratic["exponent"] - 2.0) < 0.01
    # Too few distinct sizes: refuse to fit rather than report a made-up exponent.
    assert fit_scaling([(10, 5.0)] * 10) is None
    assert fit_scaling([(10, 5.0), (20, 9.0)]) is None


def test_strategy_latency_excludes_incomplete_stages_and_groups_by_model() -> None:
    runs = [
        _trace(
            f"r{i}",
            [
                _stage("generate", "llm.generate_answer", 1000 + i * 100, model="m-a"),
                _stage("rerank", "rerank.cross_encoder", None, status="unavailable"),
            ],
        )
        for i in range(6)
    ]

    stats = strategy_latency(runs)

    assert stats["llm.generate_answer"]["samples"] == 6
    assert stats["llm.generate_answer"]["reliable"] is True
    assert stats["llm.generate_answer"]["by_model"][0]["model"] == "m-a"
    assert "rerank.cross_encoder" not in stats  # never completed, so no latency to report


def test_pipeline_latency_prefers_exact_runs_then_same_stage_then_strategy() -> None:
    pipeline = PipelineDefinition.model_validate(
        {
            "pipeline_id": "research.current",
            "version": 1,
            "name": "t",
            "purpose": "research",
            "entry_stage_ids": ["dense"],
            "stages": [
                {"id": "dense", "strategy": "retrieve.chroma_similarity", "next": ["generate"]},
                {"id": "generate", "strategy": "llm.generate_answer"},
            ],
        }
    )
    exact_hash = pipeline_hash(pipeline)
    exact = [
        _trace(
            f"e{i}",
            [
                _stage("dense", "retrieve.chroma_similarity", 40),
                _stage("generate", "llm.generate_answer", 2000),
            ],
            pipeline_hash_value=exact_hash,
            total=2100,
        )
        for i in range(6)
    ]
    elsewhere = [
        _trace(
            f"o{i}",
            [_stage("dense", "retrieve.chroma_similarity", 400)],
            pipeline_id="other",
        )
        for i in range(6)
    ]
    by_strategy = strategy_latency([*exact, *elsewhere])

    estimate = estimate_pipeline_latency(
        pipeline,
        exact_runs=exact,
        same_pipeline_runs=exact,
        by_strategy=by_strategy,
        conditional_stage_ids=set(),
    )

    rows = {row["stage_id"]: row for row in estimate["stages"]}
    assert rows["dense"]["basis"] == "this_pipeline" and rows["dense"]["p50_ms"] == 40
    assert estimate["typical_ms"] == 2040
    assert estimate["critical_path"] == ["dense", "generate"]
    assert estimate["slowest_stage_id"] == "generate"
    assert estimate["coverage"] == 1.0 and estimate["reliable"] is True
    assert estimate["observed_runs"]["p50_ms"] == 2100

    # A draft that never ran still gets a figure, and says it is borrowed.
    draft = estimate_pipeline_latency(
        pipeline,
        exact_runs=[],
        same_pipeline_runs=[],
        by_strategy=by_strategy,
        conditional_stage_ids=set(),
    )
    assert {row["basis"] for row in draft["stages"]} == {"strategy"}
    assert draft["observed_runs"] == {"samples": 0}


def test_stage_without_any_trace_is_reported_as_unknown_not_zero_confidence() -> None:
    pipeline = _built_in("research.current")

    analysis = analyze_pipeline(
        pipeline,
        strategy_registry,
        resolved_hash=pipeline_hash(pipeline),
        sample_runs=[],
        pipeline_runs=[],
    )

    latency = analysis["latency"]
    assert latency["coverage"] == 0.0
    assert latency["reliable"] is False
    assert all(row["basis"] == "none" and row["samples"] == 0 for row in latency["stages"])


class _FakeSource:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def list_runs(self, **filters: Any) -> list[PipelineRunTrace]:
        self.calls.append(filters)
        return []


def test_trace_sampler_reuses_reads_until_invalidated() -> None:
    source = _FakeSource()
    sampler = TraceSampler(source, ttl_seconds=60)

    sampler.sample()
    sampler.sample()
    sampler.for_pipeline("p")
    sampler.for_pipeline("p")
    assert len(source.calls) == 2

    sampler.invalidate()
    sampler.sample()
    assert len(source.calls) == 3


def test_blank_draft_for_every_workflow_is_valid_runnable_and_uniquely_identified(tmp_path) -> None:
    from app.pipelines.manager import PipelineManager
    from app.pipelines.purposes import purpose_registry
    from app.pipelines.store import PipelineStore

    manager = PipelineManager(
        service=PipelineService(), store=PipelineStore(tmp_path / "system.sqlite3")
    )

    for purpose in purpose_registry.list():
        draft = manager.prepare_blank(purpose.purpose_id)
        result = manager.service.validate(draft)
        assert result.valid, (purpose.purpose_id, result.model_dump())
        assert draft.status == "draft" and draft.built_in is False
        assert draft.entry_stage_ids == [draft.stages[0].id]
        # A blank draft starts with a stage that costs nothing beyond what the
        # workflow already runs: no model call when a deterministic stage fits.
        spec = strategy_registry.get(draft.stages[0].strategy)
        assert spec is not None
        if purpose.purpose_id in {"research", "evidence_suggestion", "vector_store_search"}:
            assert spec.invokes_llm is False

    first = manager.prepare_blank("research")
    manager.save_definition(first.model_copy(update={"name": "Mine"}), actor="admin")
    second = manager.prepare_blank("research")
    assert second.pipeline_id != first.pipeline_id


def test_blank_draft_rejects_unknown_workflow(tmp_path) -> None:
    import pytest
    from app.pipelines.manager import PipelineManager
    from app.pipelines.store import PipelineStore

    manager = PipelineManager(
        service=PipelineService(), store=PipelineStore(tmp_path / "system.sqlite3")
    )

    with pytest.raises(KeyError):
        manager.prepare_blank("no_such_workflow")


def test_an_edge_that_only_orders_a_binding_feeds_nothing_and_is_not_a_type_error() -> None:
    stages = [
        {"id": "start", "strategy": "query.passthrough", "next": ["dense"]},
        {"id": "alt", "strategy": "query.passthrough", "next": ["rerank"]},
        {"id": "dense", "strategy": "retrieve.chroma_similarity", "next": ["rerank"]},
        {"id": "rerank", "strategy": "rerank.cross_encoder", "next": ["pack"]},
        {"id": "pack", "strategy": "pack.evidence_context"},
    ]

    # Without a binding, a query handed to a reranker's candidates input is wrong.
    unbound = _research([dict(stage) for stage in stages], entry=["start", "alt"])
    assert "incompatible_stage_types" in _codes(unbound)

    # With the reranker's query bound to alt, the alt edge only makes alt run first.
    bound = [dict(stage) for stage in stages]
    bound[3] = {**bound[3], "inputs": {"query": [{"source": "stage", "stage": "alt"}]}}
    pipeline = _research(bound, entry=["start", "alt"])
    codes = _codes(pipeline)
    assert not (codes & (WIRING_CODES | {"incompatible_stage_types"})), codes
    analysis = analyze_pipeline(
        pipeline,
        strategy_registry,
        resolved_hash=pipeline_hash(pipeline),
        sample_runs=[],
        pipeline_runs=[],
    )
    rerank = {row["port"]: row for row in analysis["wiring"]["stages"]["rerank"]["inputs"]}
    assert [s["stage"] for s in rerank["candidates"]["sources"]] == ["dense"]
    assert [s["stage"] for s in rerank["query"]["sources"]] == ["alt"]
    assert rerank["query"]["explicit"] is True
