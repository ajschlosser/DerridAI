# Copyright 2026 Aaron John Schlosser, PhD.
"""Built-in pipeline definitions and feature assignments.

These definitions describe the current production behavior closely enough for
operators to inspect it before all call sites are migrated onto the executor.
They are immutable built-ins; custom definitions are versioned separately.
"""

from __future__ import annotations

from .models import PipelineAssignment, PipelineDefinition


def _pipeline(**values: object) -> PipelineDefinition:
    return PipelineDefinition.model_validate({**values, "built_in": True})


BUILT_IN_PIPELINES: tuple[PipelineDefinition, ...] = (
    _pipeline(
        pipeline_id="research.current",
        version=1,
        name="Research — current production chain",
        purpose="research",
        status="active",
        entry_stage_ids=["query"],
        notes=(
            "The dense candidate pool currently feeds both similarity and MMR legs, "
            "with a separate lexical leg. RRF precedes the final reranker."
        ),
        stages=[
            {
                "id": "query",
                "strategy": "query.research_decompose",
                "config": {"optional": True},
                "next": ["dense", "lexical"],
            },
            {
                "id": "dense",
                "strategy": "retrieve.chroma_similarity",
                "config": {"fetch_k": 500},
                "next": ["mmr", "rrf"],
            },
            {
                "id": "mmr",
                "strategy": "select.mmr",
                "config": {"lambda_mult": 0.7},
                "next": ["rrf"],
            },
            {
                "id": "lexical",
                "strategy": "retrieve.lexical_bm25",
                "config": {"fetch_k": 500},
                "next": ["rrf"],
            },
            {
                "id": "rrf",
                "strategy": "fusion.rrf",
                "config": {"rrf_k": 60},
                "next": ["rerank"],
            },
            {
                "id": "rerank",
                "strategy": "rerank.cross_encoder",
                "config": {"top_k": 24},
                "on_unavailable": "rerank_fallback",
                "on_timeout": "rerank_fallback",
                "on_error": "rerank_fallback",
                "next": ["provenance"],
            },
            {
                "id": "rerank_fallback",
                "strategy": "rerank.lexical_fallback",
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
            {
                "id": "generate",
                "strategy": "llm.generate_answer",
                "next": ["grade"],
            },
            {
                "id": "grade",
                "strategy": "llm.grade_rag",
                "config": {"optional": True},
            },
        ],
    ),
    _pipeline(
        pipeline_id="research.balanced",
        version=1,
        name="Research — balanced target chain",
        purpose="research",
        status="draft",
        entry_stage_ids=["query"],
        derived_from="research.current@1",
        notes=(
            "Proposed target: fuse dense and lexical retrieval before relevance "
            "reranking, then apply source-aware diversity after reranking."
        ),
        stages=[
            {
                "id": "query",
                "strategy": "query.research_decompose",
                "config": {"optional": True},
                "next": ["dense", "lexical"],
            },
            {
                "id": "dense",
                "strategy": "retrieve.chroma_similarity",
                "next": ["normalize"],
            },
            {
                "id": "normalize",
                "strategy": "normalize.collection_relevance",
                "next": ["rrf"],
            },
            {
                "id": "lexical",
                "strategy": "retrieve.lexical_bm25",
                "next": ["rrf"],
            },
            {
                "id": "rrf",
                "strategy": "fusion.rrf",
                "next": ["rerank"],
            },
            {
                "id": "rerank",
                "strategy": "rerank.cross_encoder",
                "on_unavailable": "rerank_fallback",
                "on_timeout": "rerank_fallback",
                "on_error": "rerank_fallback",
                "next": ["diversity"],
            },
            {
                "id": "rerank_fallback",
                "strategy": "rerank.lexical_fallback",
                "next": ["diversity"],
            },
            {
                "id": "diversity",
                "strategy": "select.source_diversity",
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
            {
                "id": "generate",
                "strategy": "llm.generate_answer",
                "next": ["grade"],
            },
            {
                "id": "grade",
                "strategy": "llm.grade_rag",
                "config": {"optional": True},
            },
        ],
    ),
    _pipeline(
        pipeline_id="evidence.reviewer.current",
        version=1,
        name="Evidence suggestion — reviewer semantic",
        purpose="evidence_suggestion",
        status="active",
        entry_stage_ids=["query"],
        notes=(
            "Current reviewer-facing path combines deterministic lexical support "
            "with source-unit cosine similarity and does not cross-encode or MMR-rerank."
        ),
        stages=[
            {
                "id": "query",
                "strategy": "query.evidence_field",
                "next": ["semantic", "lexical"],
            },
            {
                "id": "semantic",
                "strategy": "retrieve.source_cosine",
                "next": ["select"],
            },
            {
                "id": "lexical",
                "strategy": "retrieve.lexical_bm25",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
            },
        ],
    ),
    _pipeline(
        pipeline_id="evidence.conservative",
        version=1,
        name="Evidence suggestion — conservative support",
        purpose="evidence_suggestion",
        status="draft",
        entry_stage_ids=["query"],
        derived_from="evidence.reviewer.current@1",
        notes=(
            "Target evidence chain: broad semantic/lexical retrieval, relevance "
            "reranking, explicit support validation, then bounded selection. MMR "
            "is reserved for alternate evidence sets rather than proof relevance."
        ),
        stages=[
            {
                "id": "query",
                "strategy": "query.evidence_field",
                "next": ["semantic", "lexical"],
            },
            {
                "id": "semantic",
                "strategy": "retrieve.source_cosine",
                "next": ["rerank"],
            },
            {
                "id": "lexical",
                "strategy": "retrieve.lexical_bm25",
                "next": ["rerank"],
            },
            {
                "id": "rerank",
                "strategy": "rerank.cross_encoder",
                "on_unavailable": "support",
                "on_timeout": "support",
                "on_error": "support",
                "next": ["support"],
            },
            {
                "id": "support",
                "strategy": "validate.evidence_support",
                "on_empty": "llm_choice",
                "next": ["select"],
            },
            {
                "id": "llm_choice",
                "strategy": "llm.closed_choice_evidence",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
            },
        ],
    ),
    _pipeline(
        pipeline_id="metadata.precedents.current",
        version=1,
        name="Metadata precedents — current",
        purpose="metadata_precedents",
        status="active",
        entry_stage_ids=["retrieve"],
        notes=(
            "Current filtered precedent retrieval: semantic candidates, lexical "
            "signal fusion, bounded CrossEncoder, quotas, then MMR diversity."
        ),
        stages=[
            {
                "id": "retrieve",
                "strategy": "retrieve.metadata_exemplars",
                "next": ["scope"],
            },
            {
                "id": "scope",
                "strategy": "filter.metadata_scope",
                "next": ["hybrid"],
            },
            {
                "id": "hybrid",
                "strategy": "fusion.metadata_hybrid",
                "config": {"semantic_weight": 0.8, "lexical_weight": 0.2},
                "next": ["rerank"],
            },
            {
                "id": "rerank",
                "strategy": "rerank.cross_encoder",
                "on_unavailable": "quotas",
                "on_timeout": "quotas",
                "on_error": "quotas",
                "next": ["quotas"],
            },
            {
                "id": "quotas",
                "strategy": "select.metadata_quotas",
                "next": ["mmr"],
            },
            {
                "id": "mmr",
                "strategy": "select.mmr",
                "next": ["pack"],
            },
            {
                "id": "pack",
                "strategy": "pack.metadata_precedents",
            },
        ],
    ),
    _pipeline(
        pipeline_id="memory.claim.current",
        version=1,
        name="Validated claim memory — similarity",
        purpose="claim_memory",
        status="active",
        entry_stage_ids=["retrieve"],
        stages=[
            {
                "id": "retrieve",
                "strategy": "retrieve.claim_memory",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
            },
        ],
    ),
    _pipeline(
        pipeline_id="memory.response.current",
        version=1,
        name="Prior response memory — similarity",
        purpose="response_memory",
        status="active",
        entry_stage_ids=["retrieve"],
        stages=[
            {
                "id": "retrieve",
                "strategy": "retrieve.response_memory",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
            },
        ],
    ),
)

BUILT_IN_ASSIGNMENTS: tuple[PipelineAssignment, ...] = (
    PipelineAssignment(
        feature="research",
        pipeline_id="research.current",
        pipeline_version=1,
        source="built_in",
        override_allowed=True,
    ),
    PipelineAssignment(
        feature="evidence_suggestion.reviewer",
        pipeline_id="evidence.reviewer.current",
        pipeline_version=1,
        source="built_in",
        override_allowed=True,
    ),
    PipelineAssignment(
        feature="metadata_precedents",
        pipeline_id="metadata.precedents.current",
        pipeline_version=1,
        source="built_in",
        override_allowed=True,
    ),
    PipelineAssignment(
        feature="claim_memory",
        pipeline_id="memory.claim.current",
        pipeline_version=1,
        source="built_in",
        override_allowed=False,
    ),
    PipelineAssignment(
        feature="response_memory",
        pipeline_id="memory.response.current",
        pipeline_version=1,
        source="built_in",
        override_allowed=False,
    ),
)


def built_in_pipeline(pipeline_id: str, version: int | None = None) -> PipelineDefinition | None:
    matches = [item for item in BUILT_IN_PIPELINES if item.pipeline_id == pipeline_id]
    if version is not None:
        matches = [item for item in matches if item.version == version]
    return max(matches, key=lambda item: item.version, default=None)


def built_in_assignment(feature: str) -> PipelineAssignment | None:
    return next((item for item in BUILT_IN_ASSIGNMENTS if item.feature == feature), None)
