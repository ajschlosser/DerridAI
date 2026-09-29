# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import pytest
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.models import PipelineDefinition
from app.pipelines.research import compile_research_pipeline


def test_current_research_pipeline_compiles_to_parallel_mmr_plan() -> None:
    pipeline = built_in_pipeline("research.current", 1)
    assert pipeline is not None

    plan = compile_research_pipeline(pipeline)

    assert plan.available_search_types == {"similarity", "lexical", "mmr"}
    assert plan.pre_fusion_mmr is True
    assert plan.post_rerank_diversity == "none"
    assert plan.cross_encoder_available is True


def test_balanced_research_pipeline_moves_diversity_after_reranking() -> None:
    pipeline = built_in_pipeline("research.balanced", 1)
    assert pipeline is not None

    plan = compile_research_pipeline(pipeline)

    assert plan.available_search_types == {"similarity", "lexical"}
    assert plan.pre_fusion_mmr is False
    assert plan.post_rerank_diversity == "source_aware"


def test_research_compiler_requires_provenance_gate() -> None:
    pipeline = PipelineDefinition.model_validate(
        {
            "pipeline_id": "research.unsafe",
            "version": 1,
            "name": "Unsafe research",
            "purpose": "research",
            "entry_stage_ids": ["retrieve"],
            "stages": [
                {
                    "id": "retrieve",
                    "strategy": "retrieve.lexical_bm25",
                    "next": ["pack"],
                },
                {
                    "id": "pack",
                    "strategy": "pack.evidence_context",
                    "next": ["generate"],
                },
                {
                    "id": "generate",
                    "strategy": "llm.generate_answer",
                },
            ],
        }
    )

    with pytest.raises(ValueError, match="provenance gate"):
        compile_research_pipeline(pipeline)


def test_research_compiler_rejects_unimplemented_strategy_family() -> None:
    pipeline = PipelineDefinition.model_validate(
        {
            "pipeline_id": "research.bad",
            "version": 1,
            "name": "Bad research",
            "purpose": "research",
            "entry_stage_ids": ["retrieve"],
            "stages": [
                {
                    "id": "retrieve",
                    "strategy": "retrieve.metadata_exemplars",
                    "next": ["provenance"],
                },
                {
                    "id": "provenance",
                    "strategy": "validate.provenance",
                    "next": ["pack"],
                },
                {
                    "id": "pack",
                    "strategy": "pack.evidence_context",
                    "next": ["generate"],
                },
                {"id": "generate", "strategy": "llm.generate_answer"},
            ],
        }
    )

    with pytest.raises(ValueError, match="does not implement"):
        compile_research_pipeline(pipeline)
