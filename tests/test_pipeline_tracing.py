# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from app.models import RAGRunRequest
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.service import pipeline_hash
from app.pipelines.tracing import build_research_trace


def _result() -> dict:
    pipeline = built_in_pipeline("research.balanced", 1)
    assert pipeline is not None
    return {
        "pipeline": {
            "pipeline_id": pipeline.pipeline_id,
            "pipeline_version": pipeline.version,
            "pipeline_hash": pipeline_hash(pipeline),
            "resolved_pipeline": pipeline.model_dump(mode="json"),
        },
        "provider": "ollama",
        "model": "qwen3",
        "collections": ["derrida_primary"],
        "warnings": [
            "Cross-encoder fallback (model_unavailable); used lexical/vector fallback."
        ],
        "elapsed_seconds": 3.5,
        "retrieval": {
            "raw_count": 80,
            "deduplicated_count": 42,
            "reranked_count": 12,
            "search_types": ["similarity", "lexical"],
            "requested_search_types": ["similarity", "lexical"],
            "k": 64,
            "fetch_k": 500,
            "rrf_k": 60,
            "lambda_mult": 0.7,
            "reranker": "lexical",
            "requested_reranker": "cross_encoder",
            "rerank_top_n": 12,
            "query_decomposition": True,
            "requested_query_decomposition": True,
            "query_decomposition_num_predict": 768,
            "post_rerank_diversity": "source_aware",
            "skip_retrieval": False,
            "selected_evidence_count": 0,
            "evidence_record_char_limit": 12000,
            "evidence_total_char_limit": 120000,
        },
        "stages": [
            {
                "name": "query_metadata",
                "seconds": 0.25,
                "detail": {},
            },
            {
                "name": "retrieval",
                "seconds": 1.2,
                "detail": {"raw_results": 80, "deduplicated_results": 42},
            },
            {
                "name": "rerank",
                "seconds": 0.3,
                "detail": {
                    "rerank_pool_count": 36,
                    "reranker_telemetry": {
                        "mode": "lexical_fallback",
                        "fallback_reason": "model_unavailable",
                        "timing_ms": 120,
                        "candidate_count": 36,
                    },
                },
            },
            {
                "name": "diversity",
                "seconds": 0.02,
                "detail": {"input_count": 36, "output_count": 12},
            },
            {
                "name": "retrieval_context",
                "seconds": 0.08,
                "detail": {"evidence_count": 12, "characters": 18000},
            },
            {
                "name": "generation",
                "seconds": 1.6,
                "detail": {"provider": "ollama", "model": "qwen3"},
            },
            {
                "name": "bind_sources",
                "seconds": 0.05,
                "detail": {"bound": True},
            },
        ],
    }


def test_research_trace_records_cross_encoder_attempt_and_explicit_fallback() -> None:
    result = _result()
    request = RAGRunRequest(
        prompt="What is différance?",
        source_collection="derrida_primary",
        pipeline_id="research.balanced",
        pipeline_version=1,
        reranker="cross_encoder",
    )

    trace = build_research_trace(
        run_id="rag-1",
        owner="researcher",
        request=request,
        result=result,
        started_at="2026-09-28T20:00:00+00:00",
        finished_at="2026-09-28T20:00:04+00:00",
    )

    cross = next(stage for stage in trace.stages if stage.strategy_id == "rerank.cross_encoder")
    fallback = next(stage for stage in trace.stages if stage.strategy_id == "rerank.lexical_fallback")

    assert cross.status == "unavailable"
    assert cross.fallback_reason == "model_unavailable"
    assert cross.elapsed_ms == 120
    assert fallback.status == "completed"
    assert fallback.parameters["fallback_from"] == "rerank.cross_encoder"


def test_research_trace_does_not_invent_per_route_retrieval_timings() -> None:
    result = _result()
    request = RAGRunRequest(
        prompt="What is différance?",
        source_collection="derrida_primary",
        pipeline_id="research.balanced",
        pipeline_version=1,
    )

    trace = build_research_trace(
        run_id="rag-2",
        owner=None,
        request=request,
        result=result,
        started_at="2026-09-28T20:00:00+00:00",
        finished_at="2026-09-28T20:00:04+00:00",
    )

    semantic = next(
        stage for stage in trace.stages if stage.strategy_id == "retrieve.chroma_similarity"
    )
    lexical = next(
        stage for stage in trace.stages if stage.strategy_id == "retrieve.lexical_bm25"
    )
    fusion = next(stage for stage in trace.stages if stage.strategy_id == "fusion.rrf")
    normalization = next(
        stage for stage in trace.stages if stage.strategy_id == "normalize.collection_relevance"
    )

    assert semantic.elapsed_ms is None
    assert lexical.elapsed_ms is None
    assert fusion.elapsed_ms == 1200
    assert normalization.score_summary["metric_aware"] is True


def test_research_trace_records_post_rerank_source_diversity() -> None:
    result = _result()
    request = RAGRunRequest(
        prompt="What is différance?",
        source_collection="derrida_primary",
        pipeline_id="research.balanced",
        pipeline_version=1,
    )

    trace = build_research_trace(
        run_id="rag-3",
        owner=None,
        request=request,
        result=result,
        started_at="2026-09-28T20:00:00+00:00",
        finished_at="2026-09-28T20:00:04+00:00",
    )

    diversity = next(
        stage for stage in trace.stages if stage.strategy_id == "select.source_diversity"
    )
    assert diversity.input_count == 36
    assert diversity.output_count == 12
    assert diversity.elapsed_ms == 20



def test_research_trace_stage_ids_are_bound_to_resolved_definition() -> None:
    source = built_in_pipeline("research.balanced", 1)
    assert source is not None
    payload = source.model_dump(mode="json")
    rename = {stage["id"]: f"custom_{stage['id']}" for stage in payload["stages"]}
    payload["pipeline_id"] = "research.renamed"
    payload["built_in"] = False
    payload["entry_stage_ids"] = [rename[item] for item in payload["entry_stage_ids"]]
    for stage in payload["stages"]:
        stage["id"] = rename[stage["id"]]
        stage["next"] = [rename[item] for item in stage.get("next", [])]
        for key in ("on_empty", "on_unavailable", "on_timeout", "on_error"):
            if stage.get(key):
                stage[key] = rename[stage[key]]
    pipeline = type(source).model_validate(payload)

    result = _result()
    result["pipeline"] = {
        "pipeline_id": pipeline.pipeline_id,
        "pipeline_version": pipeline.version,
        "pipeline_hash": pipeline_hash(pipeline),
        "resolved_pipeline": pipeline.model_dump(mode="json"),
    }
    result["stages"][2]["detail"]["active_stage_id"] = rename["rerank_fallback"]
    result["stages"][2]["detail"]["fallback_condition"] = "unavailable"

    request = RAGRunRequest(
        prompt="What is différance?",
        source_collection="derrida_primary",
        pipeline_id=pipeline.pipeline_id,
        pipeline_version=pipeline.version,
        reranker="cross_encoder",
        use_prior_response_memory=True,
        use_prior_claim_memory=True,
    )

    trace = build_research_trace(
        run_id="rag-renamed",
        owner="researcher",
        request=request,
        result=result,
        started_at="2026-09-28T20:00:00+00:00",
        finished_at="2026-09-28T20:00:04+00:00",
    )

    defined_ids = {stage.id for stage in pipeline.stages}
    traced_ids = {stage.stage_id for stage in trace.stages}
    assert traced_ids <= defined_ids
    assert rename["rerank"] in traced_ids
    assert rename["rerank_fallback"] in traced_ids
    assert "response_memory" not in traced_ids
    assert "claim_memory" not in traced_ids


def _research_trace(retrieval_extra: dict):
    result = _result()
    result["retrieval"] = {**result["retrieval"], **retrieval_extra}
    request = RAGRunRequest(
        prompt="What is différance?",
        source_collection="derrida_primary",
        pipeline_id="research.balanced",
        pipeline_version=1,
    )
    return build_research_trace(
        run_id="rag-scope",
        owner=None,
        request=request,
        result=result,
        started_at="2026-09-28T20:00:00+00:00",
        finished_at="2026-09-28T20:00:04+00:00",
    )


def test_research_retrievers_record_scope_size_as_a_count() -> None:
    trace = _research_trace({"scope_size": 1200})
    by_strategy = {stage.strategy_id: stage for stage in trace.stages}
    assert by_strategy["retrieve.chroma_similarity"].parameters["scope_size"] == 1200
    assert by_strategy["retrieve.lexical_bm25"].parameters["scope_size"] == 1200
    assert "scope_size" not in by_strategy["fusion.rrf"].parameters


def test_research_retrievers_omit_unknown_or_empty_scope_size() -> None:
    for extra in ({}, {"scope_size": 0}, {"scope_size": True}):
        trace = _research_trace(extra)
        for stage in trace.stages:
            assert "scope_size" not in (stage.parameters or {})
