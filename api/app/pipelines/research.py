# Copyright 2026 Aaron John Schlosser, PhD.
"""Compile declarative Research pipelines into a bounded execution plan.

Research remains implemented by explicit Python stages rather than a generic
workflow interpreter. The compiler lets administrators compose registered
strategies while preserving a small, reviewable execution surface: supported
graphs become a typed plan; unsupported arrangements are rejected before they
can be assigned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import PipelineDefinition
from .service import pipeline_hash

ResearchDiversity = Literal["none", "source_aware", "mmr"]


@dataclass(frozen=True, slots=True)
class ResearchPipelinePlan:
    pipeline_id: str
    pipeline_version: int
    pipeline_hash: str
    query_decomposition_available: bool
    semantic_retrieval: bool
    lexical_retrieval: bool
    pre_fusion_mmr: bool
    reciprocal_rank_fusion: bool
    cross_encoder_available: bool
    lexical_rerank_available: bool
    post_rerank_diversity: ResearchDiversity
    provenance_gate: bool
    context_pack: bool
    generation: bool
    evaluation_available: bool

    @property
    def available_search_types(self) -> set[str]:
        values: set[str] = set()
        if self.semantic_retrieval:
            values.add("similarity")
        if self.lexical_retrieval:
            values.add("lexical")
        if self.pre_fusion_mmr:
            values.add("mmr")
        return values


_ALLOWED_RESEARCH_STRATEGIES = {
    "query.research_decompose",
    "retrieve.chroma_similarity",
    "retrieve.lexical_bm25",
    "normalize.collection_relevance",
    "fusion.rrf",
    "rerank.cross_encoder",
    "rerank.lexical_fallback",
    "validate.provenance",
    "select.mmr",
    "select.source_diversity",
    "select.top_k",
    "pack.evidence_context",
    "llm.generate_answer",
    "llm.grade_rag",
}


def _reachable(
    pipeline: PipelineDefinition,
    source_id: str,
    target_id: str,
) -> bool:
    stages = {stage.id: stage for stage in pipeline.stages}
    pending = list(stages[source_id].edge_targets())
    seen: set[str] = set()
    while pending:
        stage_id = pending.pop()
        if stage_id == target_id:
            return True
        if stage_id in seen or stage_id not in stages:
            continue
        seen.add(stage_id)
        pending.extend(stages[stage_id].edge_targets())
    return False


def compile_research_pipeline(pipeline: PipelineDefinition) -> ResearchPipelinePlan:
    """Validate a Research graph against the feature adapter's supported shape."""

    if pipeline.purpose != "research":
        raise ValueError(
            f"Pipeline {pipeline.pipeline_id!r} has purpose {pipeline.purpose!r}, not 'research'."
        )

    unknown = sorted(
        {
            stage.strategy
            for stage in pipeline.stages
            if stage.enabled and stage.strategy not in _ALLOWED_RESEARCH_STRATEGIES
        }
    )
    if unknown:
        raise ValueError(
            "Research does not implement these pipeline strategies yet: "
            + ", ".join(unknown)
        )

    enabled = [stage for stage in pipeline.stages if stage.enabled]
    by_strategy: dict[str, list[str]] = {}
    for stage in enabled:
        by_strategy.setdefault(stage.strategy, []).append(stage.id)

    fusion_ids = by_strategy.get("fusion.rrf", [])
    rerank_ids = (
        by_strategy.get("rerank.cross_encoder", [])
        + by_strategy.get("rerank.lexical_fallback", [])
    )

    pre_fusion_mmr = False
    post_mmr = False
    for mmr_id in by_strategy.get("select.mmr", []):
        if any(_reachable(pipeline, mmr_id, fusion_id) for fusion_id in fusion_ids):
            pre_fusion_mmr = True
        if any(_reachable(pipeline, rerank_id, mmr_id) for rerank_id in rerank_ids):
            post_mmr = True
        if not fusion_ids and not rerank_ids:
            raise ValueError("Research MMR must be attached before fusion or after reranking.")

    source_aware_ids = by_strategy.get("select.source_diversity", [])
    post_source_aware = any(
        _reachable(pipeline, rerank_id, diversity_id)
        for rerank_id in rerank_ids
        for diversity_id in source_aware_ids
    )
    if source_aware_ids and not post_source_aware:
        raise ValueError("Source-aware Research diversity must run after reranking.")

    semantic = bool(by_strategy.get("retrieve.chroma_similarity"))
    lexical = bool(by_strategy.get("retrieve.lexical_bm25"))
    if not semantic and not lexical:
        raise ValueError("Research pipelines need semantic and/or lexical candidate generation.")
    if semantic and lexical and not fusion_ids:
        raise ValueError("Parallel semantic and lexical Research retrieval requires a fusion stage.")

    provenance = bool(by_strategy.get("validate.provenance"))
    context_pack = bool(by_strategy.get("pack.evidence_context"))
    generation = bool(by_strategy.get("llm.generate_answer"))
    if not provenance:
        raise ValueError("Research pipelines must include the deterministic provenance gate.")
    if not context_pack:
        raise ValueError("Research pipelines must include an evidence context packer.")
    if not generation:
        raise ValueError("Research pipelines must include final answer generation.")

    if post_source_aware:
        post_diversity: ResearchDiversity = "source_aware"
    elif post_mmr:
        post_diversity = "mmr"
    else:
        post_diversity = "none"

    return ResearchPipelinePlan(
        pipeline_id=pipeline.pipeline_id,
        pipeline_version=pipeline.version,
        pipeline_hash=pipeline_hash(pipeline),
        query_decomposition_available=bool(by_strategy.get("query.research_decompose")),
        semantic_retrieval=semantic,
        lexical_retrieval=lexical,
        pre_fusion_mmr=pre_fusion_mmr,
        reciprocal_rank_fusion=bool(fusion_ids),
        cross_encoder_available=bool(by_strategy.get("rerank.cross_encoder")),
        lexical_rerank_available=bool(by_strategy.get("rerank.lexical_fallback")),
        post_rerank_diversity=post_diversity,
        provenance_gate=provenance,
        context_pack=context_pack,
        generation=generation,
        evaluation_available=bool(by_strategy.get("llm.grade_rag")),
    )
