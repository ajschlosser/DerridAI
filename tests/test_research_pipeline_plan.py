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

from __future__ import annotations

import pytest
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.models import PipelineDefinition
from app.pipelines.research import (
    compile_research_pipeline,
    resolve_research_runtime_settings,
)


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



def test_pipeline_stage_config_overrides_request_defaults() -> None:
    source = built_in_pipeline("research.current", 1)
    assert source is not None
    stages = []
    for stage in source.stages:
        config = dict(stage.config)
        if stage.id == "dense":
            config["fetch_k"] = 37
        elif stage.id == "rrf":
            config["rrf_k"] = 17
        elif stage.id == "rerank":
            config.update(
                {
                    "top_k": 9,
                    "model": "custom/cross-encoder",
                    "timeout_seconds": 12.5,
                }
            )
        elif stage.id == "pack":
            config.update(
                {
                    "record_char_limit": 4321,
                    "total_char_limit": 54321,
                }
            )
        stages.append(stage.model_copy(update={"config": config}))

    custom = source.model_copy(
        update={
            "pipeline_id": "research.configured",
            "version": 2,
            "built_in": False,
            "stages": stages,
        }
    )
    plan = compile_research_pipeline(custom)
    settings = resolve_research_runtime_settings(
        plan,
        {
            "k": 64,
            "fetch_k": 500,
            "rrf_k": 60,
            "rerank_top_n": 24,
            "cross_encoder_model": "request/model",
            "lambda_mult": 0.7,
            "query_decomposition_num_predict": 768,
            "evidence_record_char_limit": 12000,
            "evidence_total_char_limit": 120000,
        },
    )

    assert settings.semantic_fetch_k == 64  # fetch_k cannot undercut requested retrieval K
    assert settings.rrf_k == 17
    assert settings.rerank_top_n == 9
    assert settings.cross_encoder_model == "custom/cross-encoder"
    assert settings.cross_encoder_timeout_seconds == 12.5
    assert settings.evidence_record_char_limit == 4321
    assert settings.evidence_total_char_limit == 54321


def test_research_fallbacks_follow_declared_edges() -> None:
    source = built_in_pipeline("research.current", 1)
    assert source is not None
    stages = []
    for stage in source.stages:
        if stage.id == "rerank":
            stage = stage.model_copy(
                update={
                    "on_unavailable": None,
                    "on_timeout": "rerank_fallback",
                    "on_error": None,
                }
            )
        stages.append(stage)

    custom = source.model_copy(
        update={
            "pipeline_id": "research.timeout-only-fallback",
            "built_in": False,
            "stages": stages,
        }
    )
    plan = compile_research_pipeline(custom)

    assert plan.rerank_fallback("timeout") == (
        "rerank_fallback",
        "rerank.lexical_fallback",
    )
    assert plan.rerank_fallback("unavailable") is None
    assert plan.rerank_fallback("error") is None
