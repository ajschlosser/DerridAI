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
                "config": {"optional": True, "num_predict": 768},
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
                "config": {
                    "record_char_limit": 12000,
                    "total_char_limit": 120000,
                },
                "next": ["generate"],
            },
            {
                "id": "generate",
                "strategy": "llm.generate_answer",
                "next": ["bind"],
            },
            {
                "id": "bind",
                "strategy": "validate.citation_binding",
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
                "config": {"optional": True, "num_predict": 768},
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
                "config": {
                    "top_k": 24,
                    "model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
                },
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
                "config": {
                    "record_char_limit": 12000,
                    "total_char_limit": 120000,
                },
                "next": ["generate"],
            },
            {
                "id": "generate",
                "strategy": "llm.generate_answer",
                "next": ["bind"],
            },
            {
                "id": "bind",
                "strategy": "validate.citation_binding",
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
        name="Evidence suggestion — reviewer semantic (legacy)",
        purpose="evidence_suggestion",
        status="disabled",
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
        pipeline_id="evidence.reviewer.current",
        version=2,
        name="Evidence suggestion — reviewer support-gated",
        purpose="evidence_suggestion",
        status="active",
        entry_stage_ids=["query"],
        derived_from="evidence.reviewer.current@1",
        notes=(
            "Reviewer-facing evidence retrieval preserves the current lexical and "
            "semantic candidate generation while adding mandatory direct-support and "
            "source-provenance gates before top-K selection. Retrieval relevance may "
            "surface a candidate; only deterministic validation may make it eligible "
            "for evidence suggestion."
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
                "next": ["support"],
            },
            {
                "id": "lexical",
                "strategy": "retrieve.lexical_bm25",
                "next": ["support"],
            },
            {
                "id": "support",
                "strategy": "validate.evidence_support",
                "config": {"min_score": 0.5},
                "next": ["provenance"],
            },
            {
                "id": "provenance",
                "strategy": "validate.provenance",
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
                "next": ["provenance"],
            },
            {
                "id": "llm_choice",
                "strategy": "llm.closed_choice_evidence",
                "next": ["provenance"],
            },
            {
                "id": "provenance",
                "strategy": "validate.provenance",
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
                "config": {"fetch_k": 16},
                "on_unavailable": "lexical_fallback",
                "on_timeout": "lexical_fallback",
                "on_error": "lexical_fallback",
                "next": ["scope"],
            },
            {
                "id": "lexical_fallback",
                "strategy": "fallback.metadata_precedents_lexical",
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
                "config": {
                    "top_k": 8,
                    "model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
                    "timeout_seconds": 15.0,
                },
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
                "config": {"lambda_mult": 0.72},
                "next": ["pack"],
            },
            {
                "id": "pack",
                "strategy": "pack.metadata_precedents",
                "config": {"char_budget": 4800},
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
        notes=(
            "Search reviewer-validated claims semantically, fall back visibly to "
            "deterministic lexical matching on retrieval failures, then keep a "
            "bounded advisory set. Claim validation and support provenance remain "
            "authoritative outside this computational graph."
        ),
        stages=[
            {
                "id": "retrieve",
                "strategy": "retrieve.claim_memory",
                "config": {"fetch_k": 6, "min_similarity": 0.5},
                "on_unavailable": "lexical",
                "on_timeout": "lexical",
                "on_error": "lexical",
                "next": ["select"],
            },
            {
                "id": "lexical",
                "strategy": "retrieve.memory_lexical_fallback",
                "config": {"fetch_k": 6},
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
                "config": {"limit": 6},
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
        notes=(
            "Search eligible graded responses semantically, fall back visibly to "
            "deterministic lexical matching on retrieval failures, then keep a "
            "bounded advisory set. Response grade eligibility remains authoritative "
            "outside this computational graph."
        ),
        stages=[
            {
                "id": "retrieve",
                "strategy": "retrieve.response_memory",
                "config": {"fetch_k": 4, "min_similarity": 0.5},
                "on_unavailable": "lexical",
                "on_timeout": "lexical",
                "on_error": "lexical",
                "next": ["select"],
            },
            {
                "id": "lexical",
                "strategy": "retrieve.memory_lexical_fallback",
                "config": {"fetch_k": 4},
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
                "config": {"limit": 4},
            },
        ],
    ),
    _pipeline(
        pipeline_id="evidence.recovery.celf",
        version=1,
        name="Evidence recovery — cELF-compliant",
        purpose="evidence_recovery",
        status="active",
        entry_stage_ids=["lexical"],
        notes=(
            "Direct text support first; only when no block is directly supported may "
            "a closed-choice model pick among this Record's own source units, and that "
            "pick is flagged when it has no text match. Similarity and cross-encoder "
            "relevance never establish a suggestion, so this chain needs no embeddings "
            "or reranking. Every result stays advisory and pending review."
        ),
        stages=[
            {
                "id": "lexical",
                "strategy": "retrieve.lexical_bm25",
                "config": {"min_score": 0.5},
                "next": ["support"],
                "on_empty": "llm_choice",
            },
            {
                "id": "support",
                "strategy": "validate.evidence_support",
                "config": {"min_score": 0.5},
                "next": ["provenance"],
                "on_empty": "llm_choice",
            },
            {
                "id": "llm_choice",
                "strategy": "llm.closed_choice_evidence",
                "next": ["provenance"],
            },
            {
                "id": "provenance",
                "strategy": "validate.provenance",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
                "config": {"limit": 2},
            },
        ],
    ),
    _pipeline(
        pipeline_id="evidence.recovery.cascade",
        version=1,
        name="Evidence recovery — legacy cascade (not cELF-compliant)",
        purpose="evidence_recovery",
        status="active",
        entry_stage_ids=["query"],
        notes=(
            "The original first-hit cascade: direct text match; otherwise source-unit "
            "similarity, then cross-encoder rerank (positive scores), then MMR when the "
            "best similarity reaches 0.35; closed-choice model last. Each stage runs only "
            "if the previous one found nothing. Cross-encoder and MMR results reach "
            "selection without direct-support validation, so this chain is not "
            "cELF-compliant. Results stay advisory and pending review."
        ),
        stages=[
            {
                "id": "query",
                "strategy": "query.evidence_field",
                "next": ["lexical"],
            },
            {
                "id": "lexical",
                "strategy": "retrieve.lexical_bm25",
                "config": {"min_score": 0.5},
                "next": ["provenance"],
                "on_empty": "semantic",
            },
            {
                "id": "semantic",
                "strategy": "retrieve.source_cosine",
                "next": ["rerank"],
                "on_empty": "llm_choice",
                "on_unavailable": "llm_choice",
                "on_error": "llm_choice",
            },
            {
                "id": "rerank",
                "strategy": "rerank.cross_encoder",
                "config": {"min_score": 0},
                "next": ["provenance"],
                "on_empty": "mmr",
                "on_unavailable": "mmr",
                "on_timeout": "mmr",
                "on_error": "mmr",
            },
            {
                "id": "mmr",
                "strategy": "select.mmr",
                "config": {"lambda_mult": 0.72, "limit": 2, "min_relevance": 0.35},
                "next": ["provenance"],
                "on_empty": "llm_choice",
            },
            {
                "id": "llm_choice",
                "strategy": "llm.closed_choice_evidence",
                "next": ["provenance"],
            },
            {
                "id": "provenance",
                "strategy": "validate.provenance",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
                "config": {"limit": 2},
            },
        ],
    ),
    _pipeline(
        pipeline_id="store_search.similarity",
        version=1,
        name="Store search — semantic similarity",
        purpose="vector_store_search",
        status="active",
        entry_stage_ids=["dense"],
        notes=(
            "Nearest records by embedding distance."
        ),
        stages=[
            {
                "id": "dense",
                "strategy": "retrieve.chroma_similarity",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
            },
        ],
    ),
    _pipeline(
        pipeline_id="store_search.mmr",
        version=1,
        name="Store search — maximum marginal relevance",
        purpose="vector_store_search",
        status="active",
        entry_stage_ids=["dense"],
        notes=(
            "Draws a candidate pool of the request's fetch_k nearest records, then "
            "selects a relevance/diversity balance using the collection's distance "
            "metric."
        ),
        stages=[
            {
                "id": "dense",
                "strategy": "retrieve.chroma_similarity",
                "next": ["mmr"],
            },
            {
                "id": "mmr",
                "strategy": "select.mmr",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
            },
        ],
    ),
    _pipeline(
        pipeline_id="store_search.hybrid",
        version=1,
        name="Store search — hybrid (semantic + lexical)",
        purpose="vector_store_search",
        status="active",
        entry_stage_ids=["query"],
        notes=(
            "Semantic and BM25-style lexical legs fused by reciprocal rank. An empty "
            "query lists records by metadata filter; a collection that cannot embed "
            "queries continues with the lexical leg; a query with no lexical terms "
            "uses record-text matching for that leg."
        ),
        stages=[
            {
                "id": "query",
                "strategy": "query.passthrough",
                "next": ["dense", "lexical"],
                "on_empty": "filter",
            },
            {
                "id": "dense",
                "strategy": "retrieve.chroma_similarity",
                "next": ["fuse"],
                "on_unavailable": "fuse",
            },
            {
                "id": "lexical",
                "strategy": "retrieve.lexical_bm25",
                "next": ["fuse"],
                "on_unavailable": "keyword",
            },
            {
                "id": "keyword",
                "strategy": "retrieve.store_keyword",
                "next": ["fuse"],
            },
            {
                "id": "fuse",
                "strategy": "fusion.rrf",
                "next": ["select"],
            },
            {
                "id": "filter",
                "strategy": "retrieve.store_filter",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
            },
        ],
    ),
    _pipeline(
        pipeline_id="store_search.lexical",
        version=1,
        name="Store search — lexical (BM25-style)",
        purpose="vector_store_search",
        status="active",
        entry_stage_ids=["query"],
        notes=(
            "Ranks stored record text and key metadata by BM25-style term weighting. "
            "An empty query, or one with no lexical terms, uses record-text matching "
            "instead."
        ),
        stages=[
            {
                "id": "query",
                "strategy": "query.passthrough",
                "next": ["lexical"],
                "on_empty": "keyword",
            },
            {
                "id": "lexical",
                "strategy": "retrieve.lexical_bm25",
                "next": ["select"],
                "on_unavailable": "keyword",
            },
            {
                "id": "keyword",
                "strategy": "retrieve.store_keyword",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
            },
        ],
    ),
    _pipeline(
        pipeline_id="store_search.keyword",
        version=1,
        name="Store search — record text contains",
        purpose="vector_store_search",
        status="active",
        entry_stage_ids=["keyword"],
        notes=(
            "Case-insensitive substring match on record text."
        ),
        stages=[
            {
                "id": "keyword",
                "strategy": "retrieve.store_keyword",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
            },
        ],
    ),
    _pipeline(
        pipeline_id="store_search.filter",
        version=1,
        name="Store search — metadata filter",
        purpose="vector_store_search",
        status="active",
        entry_stage_ids=["filter"],
        notes=(
            "Records matching the metadata filter, ignoring the query text."
        ),
        stages=[
            {
                "id": "filter",
                "strategy": "retrieve.store_filter",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
            },
        ],
    ),
    _pipeline(
        pipeline_id="metadata.prefill.current",
        version=1,
        name="Metadata pre-fill — reviewed precedents",
        purpose="metadata_prefill",
        status="active",
        entry_stage_ids=["retrieve"],
        notes=(
            "Each source span of a new Record queries reviewed metadata exemplars "
            "(positive and confirmed-absence, other builds only). Distances become "
            "similarity as 1 / (1 + distance). Up to three hints per field surface "
            "at similarity 0.72 or above. Pre-filling a value additionally needs two "
            "agreeing earlier Records at mean similarity 0.88 and no rival within "
            "0.05; those rules are DerridAI policy, not pipeline settings."
        ),
        stages=[
            {
                "id": "retrieve",
                "strategy": "retrieve.metadata_exemplars",
                "config": {"fetch_k": 8},
                "next": ["normalize"],
            },
            {
                "id": "normalize",
                "strategy": "normalize.collection_relevance",
                "config": {"method": "inverse_distance"},
                "next": ["hints"],
            },
            {
                "id": "hints",
                "strategy": "select.memory_hints",
                "config": {"limit": 3, "min_similarity": 0.72},
            },
        ],
    ),
    _pipeline(
        pipeline_id="precedent.remap.current",
        version=1,
        name="Precedent evidence remapping — current Record",
        purpose="precedent_evidence_remap",
        status="active",
        entry_stage_ids=["semantic"],
        notes=(
            "Ranks the current Record's own source units against a reviewed "
            "precedent's evidence text by embedding similarity, falling back to "
            "word overlap when no embedding service is available or it fails. "
            "Only source units of the current Record can be candidates, and the "
            "three best per precedent are kept. Candidates are advisory and bind "
            "nothing."
        ),
        stages=[
            {
                "id": "semantic",
                "strategy": "retrieve.source_cosine",
                "next": ["provenance"],
                "on_unavailable": "lexical",
                "on_error": "lexical",
            },
            {
                "id": "lexical",
                "strategy": "retrieve.token_overlap",
                "next": ["provenance"],
            },
            {
                "id": "provenance",
                "strategy": "validate.provenance",
                "next": ["select"],
            },
            {
                "id": "select",
                "strategy": "select.top_k",
                "config": {"limit": 3},
            },
        ],
    ),
    _pipeline(
        pipeline_id="corpus.metadata_enrichment.current",
        version=1,
        name="Corpus metadata enrichment — current",
        purpose="corpus_metadata_enrichment",
        status="active",
        entry_stage_ids=["primary"],
        notes=(
            "Runs each schema-derived metadata group on the build's primary "
            "provider with two attempts. When those fail or time out and the "
            "build configures a review provider, the review provider gets two "
            "attempts of its own. The active metadata schema supplies the task; "
            "every answer is validated, and review and evidence rules apply "
            "after this pipeline."
        ),
        stages=[
            {
                "id": "primary",
                "strategy": "llm.structured_metadata",
                "config": {"provider_role": "primary", "attempts": 2},
                "on_error": "review",
                "on_timeout": "review",
            },
            {
                "id": "review",
                "strategy": "llm.structured_metadata",
                "config": {"provider_role": "review", "attempts": 2},
            },
        ],
    ),
)

BUILT_IN_ASSIGNMENTS: tuple[PipelineAssignment, ...] = (
    PipelineAssignment(
        feature="corpus_metadata_enrichment",
        pipeline_id="corpus.metadata_enrichment.current",
        pipeline_version=1,
        source="built_in",
        override_allowed=True,
    ),
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
        pipeline_version=2,
        source="built_in",
        override_allowed=True,
    ),
    PipelineAssignment(
        feature="precedent_evidence_remap",
        pipeline_id="precedent.remap.current",
        pipeline_version=1,
        source="built_in",
        override_allowed=True,
    ),
    PipelineAssignment(
        feature="metadata_prefill",
        pipeline_id="metadata.prefill.current",
        pipeline_version=1,
        source="built_in",
        override_allowed=True,
    ),
    PipelineAssignment(
        feature="vector_store_search",
        pipeline_id="store_search.similarity",
        pipeline_version=1,
        source="built_in",
        override_allowed=True,
    ),
    PipelineAssignment(
        feature="evidence_recovery",
        pipeline_id="evidence.recovery.cascade",
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
