# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import pytest

from app.pipelines.defaults import built_in_pipeline
from app.pipelines.metadata_precedents import compile_metadata_precedent_pipeline


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
