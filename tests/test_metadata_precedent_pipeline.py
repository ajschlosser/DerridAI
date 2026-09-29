# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import pytest
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.metadata_precedent_tracing import build_metadata_precedent_trace
from app.pipelines.metadata_precedents import compile_metadata_precedent_pipeline
from app.pipelines.service import pipeline_hash


def test_builtin_metadata_precedent_pipeline_compiles_to_current_runtime_defaults() -> None:
    pipeline = built_in_pipeline("metadata.precedents.current", 1)
    assert pipeline is not None

    plan = compile_metadata_precedent_pipeline(pipeline)

    assert plan.retrieve_stage_id == "retrieve"
    assert plan.scope_stage_id == "scope"
    assert plan.hybrid_stage_id == "hybrid"
    assert plan.rerank_stage_id == "rerank"
    assert plan.quotas_stage_id == "quotas"
    assert plan.mmr_stage_id == "mmr"
    assert plan.pack_stage_id == "pack"
    assert plan.lexical_fallback_stage_id == "lexical_fallback"
    assert plan.fetch_k == 16
    assert plan.semantic_weight == pytest.approx(0.8)
    assert plan.lexical_weight == pytest.approx(0.2)
    assert plan.cross_encoder_top_k == 8
    assert plan.cross_encoder_model == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    assert plan.cross_encoder_timeout_seconds == pytest.approx(15.0)
    assert plan.mmr_lambda == pytest.approx(0.72)
    assert plan.packet_char_budget == 4800


def test_metadata_precedent_pipeline_normalizes_custom_hybrid_weights() -> None:
    source = built_in_pipeline("metadata.precedents.current", 1)
    assert source is not None
    stages = []
    for stage in source.stages:
        if stage.id == "hybrid":
            stage = stage.model_copy(
                update={
                    "config": {
                        "semantic_weight": 0.6,
                        "lexical_weight": 0.2,
                    }
                }
            )
        elif stage.id == "rerank":
            stage = stage.model_copy(
                update={
                    "config": {
                        "top_k": 5,
                        "model": "custom/reranker",
                        "timeout_seconds": 9.0,
                    }
                }
            )
        elif stage.id == "mmr":
            stage = stage.model_copy(
                update={"config": {"lambda_mult": 0.61}}
            )
        elif stage.id == "pack":
            stage = stage.model_copy(
                update={"config": {"char_budget": 7200}}
            )
        stages.append(stage)

    custom = source.model_copy(
        update={
            "pipeline_id": "metadata.precedents.custom",
            "built_in": False,
            "stages": stages,
        }
    )
    plan = compile_metadata_precedent_pipeline(custom)

    assert plan.semantic_weight == pytest.approx(0.75)
    assert plan.lexical_weight == pytest.approx(0.25)
    assert plan.cross_encoder_top_k == 5
    assert plan.cross_encoder_model == "custom/reranker"
    assert plan.cross_encoder_timeout_seconds == pytest.approx(9.0)
    assert plan.mmr_lambda == pytest.approx(0.61)
    assert plan.packet_char_budget == 7200


def test_metadata_precedent_pipeline_rejects_zero_hybrid_weight() -> None:
    source = built_in_pipeline("metadata.precedents.current", 1)
    assert source is not None
    stages = [
        stage.model_copy(
            update={
                "config": {
                    "semantic_weight": 0.0,
                    "lexical_weight": 0.0,
                }
            }
        )
        if stage.id == "hybrid"
        else stage
        for stage in source.stages
    ]
    custom = source.model_copy(
        update={
            "pipeline_id": "metadata.precedents.invalid",
            "built_in": False,
            "stages": stages,
        }
    )

    with pytest.raises(ValueError, match="cannot both be zero"):
        compile_metadata_precedent_pipeline(custom)


def test_metadata_precedent_pipeline_rejects_unsupported_fallback_route() -> None:
    source = built_in_pipeline("metadata.precedents.current", 1)
    assert source is not None
    stages = [
        stage.model_copy(update={"on_timeout": "pack"})
        if stage.id == "rerank"
        else stage
        for stage in source.stages
    ]
    custom = source.model_copy(
        update={
            "pipeline_id": "metadata.precedents.invalid-fallback",
            "built_in": False,
            "stages": stages,
        }
    )

    with pytest.raises(ValueError, match="on_timeout"):
        compile_metadata_precedent_pipeline(custom)



def test_metadata_precedent_pipeline_requires_explicit_reranker_fallbacks() -> None:
    source = built_in_pipeline("metadata.precedents.current", 1)
    assert source is not None
    stages = [
        stage.model_copy(update={"on_unavailable": None})
        if stage.id == "rerank"
        else stage
        for stage in source.stages
    ]
    custom = source.model_copy(
        update={
            "pipeline_id": "metadata.precedents.missing-fallback",
            "built_in": False,
            "stages": stages,
        }
    )

    with pytest.raises(ValueError, match="on_unavailable"):
        compile_metadata_precedent_pipeline(custom)



def test_metadata_precedent_trace_binds_every_stage_to_resolved_definition() -> None:
    pipeline = built_in_pipeline("metadata.precedents.current", 1)
    assert pipeline is not None
    trace = build_metadata_precedent_trace(
        run_id="metadata-precedents-test",
        pipeline=pipeline,
        resolved_hash=pipeline_hash(pipeline),
        telemetry={
            "sync_ms": 1,
            "query_ms": 2,
            "search_ms": 3,
            "rerank_ms": 4,
            "select_ms": 2,
            "total_ms": 12,
            "examples_considered": 8,
            "examples_used": 2,
            "packet_chars": 900,
            "fields_served": ["speaker"],
            "fetch_k": 16,
            "semantic_weight": 0.8,
            "lexical_weight": 0.2,
            "mmr_lambda": 0.72,
            "packet_char_budget": 4800,
            "embedding_provider": "ollama",
            "embedding_model": "embed-model",
            "reranking": {
                "mode": "cross_encoder",
                "provider": "sentence-transformers",
                "model": "reranker",
                "candidate_count": 8,
                "reranked_count": 8,
            },
        },
    )

    defined = {stage.id for stage in pipeline.stages}
    assert {stage.stage_id for stage in trace.stages} == defined
    assert trace.feature == "metadata_precedents"
    assert next(stage for stage in trace.stages if stage.stage_id == "retrieve").collection == (
        "derridai_metadata_exemplars"
    )
    assert next(stage for stage in trace.stages if stage.stage_id == "rerank").status == "completed"
    assert next(
        stage for stage in trace.stages if stage.stage_id == "lexical_fallback"
    ).status == "skipped"


def test_metadata_precedent_trace_makes_lexical_fallback_visible() -> None:
    pipeline = built_in_pipeline("metadata.precedents.current", 1)
    assert pipeline is not None
    trace = build_metadata_precedent_trace(
        run_id="metadata-precedents-fallback",
        pipeline=pipeline,
        resolved_hash=pipeline_hash(pipeline),
        telemetry={
            "total_ms": 6,
            "fallback_reason": "RuntimeError: embedding service offline",
            "fallback_kind": "error",
            "fallback_mode": "lexical",
            "ranking": "lexical_overlap",
            "candidates_considered": 5,
            "examples_considered": 3,
            "examples_used": 2,
            "packet_chars": 700,
            "fields_served": ["speaker"],
        },
    )

    stages = {stage.stage_id: stage for stage in trace.stages}
    assert stages["retrieve"].status == "failed"
    assert stages["retrieve"].fallback_reason == "RuntimeError: embedding service offline"
    assert stages["lexical_fallback"].status == "completed"
    assert stages["scope"].status == "skipped"
    assert stages["pack"].status == "skipped"
