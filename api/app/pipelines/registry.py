# Copyright 2026 Aaron John Schlosser, PhD.
"""Registry of pipeline strategies that DerridAI is allowed to execute.

The registry is deliberately code-owned. Saved pipelines reference these stable
IDs and parameter schemas, but cannot smuggle executable code into the server.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import StrategySpec


class StrategyRegistry:
    """Small immutable-by-convention registry for pipeline strategy metadata."""

    def __init__(self, specs: Iterable[StrategySpec] = ()) -> None:
        self._specs: dict[str, StrategySpec] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: StrategySpec) -> None:
        if spec.strategy_id in self._specs:
            raise ValueError(f"Duplicate pipeline strategy: {spec.strategy_id}")
        self._specs[spec.strategy_id] = spec

    def get(self, strategy_id: str) -> StrategySpec | None:
        return self._specs.get(str(strategy_id))

    def require(self, strategy_id: str) -> StrategySpec:
        spec = self.get(strategy_id)
        if spec is None:
            raise KeyError(strategy_id)
        return spec

    def list(self) -> list[StrategySpec]:
        return [self._specs[key] for key in sorted(self._specs)]


def _number(minimum: float | int | None = None, maximum: float | int | None = None) -> dict:
    schema: dict[str, object] = {"type": "number"}
    if minimum is not None:
        schema["minimum"] = minimum
    if maximum is not None:
        schema["maximum"] = maximum
    return schema


def _integer(minimum: int | None = None, maximum: int | None = None) -> dict:
    schema: dict[str, object] = {"type": "integer"}
    if minimum is not None:
        schema["minimum"] = minimum
    if maximum is not None:
        schema["maximum"] = maximum
    return schema


# The first catalog intentionally describes the strategies already present in
# production. Executor wiring is migrated feature-by-feature; the registry gives
# the UI and validators one authoritative answer to "what can this stage mean?"
DEFAULT_STRATEGIES = [
    StrategySpec(
        strategy_id="query.passthrough",
        family="query_transform",
        scholarly_effect="none",
        label="Query passthrough",
        description="Preserve the user query without invoking a model-based decomposition stage.",
        input_type="query",
        output_type="query",
    ),
    StrategySpec(
        strategy_id="query.research_decompose",
        family="query_transform",
        scholarly_effect="transformation",
        label="Research query decomposition",
        description="Use the configured chat model to derive bounded structured query metadata before retrieval.",
        input_type="query",
        output_type="query",
        deterministic=False,
        invokes_llm=True,
        capabilities=["chat_model"],
        config_schema={"type": "object", "properties": {"num_predict": _integer(64, 8192)}},
    ),
    StrategySpec(
        strategy_id="query.evidence_field",
        family="query_transform",
        scholarly_effect="transformation",
        label="Field-aware evidence query",
        description="Build an evidence query deterministically from the target metadata field and proposed value.",
        input_type="query",
        output_type="query",
    ),
    StrategySpec(
        strategy_id="retrieve.selected_evidence",
        family="candidate_generation",
        scholarly_effect="none",
        label="User-selected evidence",
        description="Resolve explicitly selected collection/record identifiers to authoritative Records without vector retrieval.",
        input_type="query",
        output_type="candidate_set",
    ),
    StrategySpec(
        strategy_id="retrieve.chroma_similarity",
        family="candidate_generation",
        scholarly_effect="advisory",
        label="Chroma semantic similarity",
        description="Embed the query and retrieve nearest candidates from a compatible Chroma collection.",
        input_type="query",
        output_type="candidate_set",
        deterministic=False,
        capabilities=["embedding", "chroma"],
        config_schema={"type": "object", "properties": {"fetch_k": _integer(1, 5000)}},
    ),
    StrategySpec(
        strategy_id="retrieve.source_cosine",
        family="candidate_generation",
        scholarly_effect="advisory",
        label="Source-unit semantic similarity",
        description="Compare a query embedding with source-unit embeddings inside the active source/Record scope.",
        input_type="query",
        output_type="candidate_set",
        deterministic=False,
        capabilities=["embedding"],
        config_schema={
            "type": "object",
            "properties": {
                "fetch_k": _integer(1, 500),
                "min_similarity": _number(-1, 1),
            },
        },
    ),
    StrategySpec(
        strategy_id="retrieve.lexical_bm25",
        family="candidate_generation",
        scholarly_effect="advisory",
        label="Lexical BM25 retrieval",
        description="Rank candidate text with the local deterministic BM25-style lexical retriever.",
        input_type="query",
        output_type="candidate_set",
        config_schema={
            "type": "object",
            "properties": {
                "fetch_k": _integer(1, 5000),
                "min_score": _number(0, 1),
            },
        },
    ),
    StrategySpec(
        strategy_id="retrieve.token_overlap",
        family="candidate_generation",
        scholarly_effect="advisory",
        label="Word overlap",
        description="Deterministic Jaccard overlap between the query's words and each source unit's words, with no stopword removal; a unit with no shared word is never a candidate.",
        input_type="query",
        output_type="candidate_set",
        config_schema={"type": "object", "properties": {"min_score": _number(0, 1)}},
    ),
    StrategySpec(
        strategy_id="retrieve.store_keyword",
        family="candidate_generation",
        scholarly_effect="advisory",
        label="Record text contains",
        description="Case-insensitive substring match on stored record text within the collection and metadata filter; an empty query lists records in storage order.",
        input_type="query",
        output_type="candidate_set",
        config_schema={"type": "object", "properties": {"fetch_k": _integer(1, 5000)}},
    ),
    StrategySpec(
        strategy_id="retrieve.store_filter",
        family="candidate_generation",
        scholarly_effect="advisory",
        label="Metadata filter",
        description="Return records matching the metadata filter without using the query text; contains filters match decoded list and text values.",
        input_type="query",
        output_type="candidate_set",
        config_schema={"type": "object", "properties": {"fetch_k": _integer(1, 5000)}},
    ),
    StrategySpec(
        strategy_id="retrieve.metadata_exemplars",
        family="candidate_generation",
        scholarly_effect="advisory",
        label="Metadata exemplar retrieval",
        description="Retrieve schema/field/language-filtered reviewed metadata precedents from the derived exemplar projection.",
        input_type="query",
        output_type="candidate_set",
        deterministic=False,
        capabilities=["embedding", "chroma"],
        config_schema={"type": "object", "properties": {"fetch_k": _integer(1, 500)}},
    ),
    StrategySpec(
        strategy_id="retrieve.claim_memory",
        family="candidate_generation",
        scholarly_effect="advisory",
        label="Validated-claim memory",
        description="Retrieve owner-scoped semantically similar validated claims, then rejoin authoritative claim/support state.",
        input_type="query",
        output_type="candidate_set",
        deterministic=False,
        capabilities=["embedding", "chroma"],
        config_schema={
            "type": "object",
            "properties": {
                "fetch_k": _integer(1, 500),
                "min_similarity": _number(0, 1),
            },
        },
    ),
    StrategySpec(
        strategy_id="retrieve.response_memory",
        family="candidate_generation",
        scholarly_effect="advisory",
        label="Prior-response memory",
        description="Retrieve owner-scoped semantically similar eligible Research responses and rejoin durable response state.",
        input_type="query",
        output_type="candidate_set",
        deterministic=False,
        capabilities=["embedding", "chroma"],
        config_schema={
            "type": "object",
            "properties": {
                "fetch_k": _integer(1, 500),
                "min_similarity": _number(0, 1),
            },
        },
    ),
    StrategySpec(
        strategy_id="retrieve.memory_lexical_fallback",
        family="candidate_generation",
        scholarly_effect="advisory",
        label="Lexical memory fallback",
        description="When semantic memory retrieval fails, match eligible durable memory rows by word overlap without changing their authority or provenance status.",
        input_type="any",
        output_type="candidate_set",
        config_schema={
            "type": "object",
            "properties": {
                "fetch_k": _integer(1, 500),
            },
        },
    ),
    StrategySpec(
        strategy_id="fallback.metadata_precedents_lexical",
        family="candidate_generation",
        scholarly_effect="advisory",
        label="Metadata lexical fallback",
        description="When semantic metadata-precedent retrieval is unavailable, use bounded deterministic word-overlap ranking while preserving schema scope, reviewed analogy conditions, correction policy, and packet limits.",
        input_type="any",
        output_type="context_packet",
    ),
    StrategySpec(
        strategy_id="filter.metadata_scope",
        family="filter",
        scholarly_effect="scope_constraint",
        label="Metadata scope filter",
        description="Constrain precedent candidates by schema, stable field identities, language, scope, and reviewed analogy fields.",
        input_type="candidate_set",
        output_type="candidate_set",
    ),
    StrategySpec(
        strategy_id="normalize.collection_relevance",
        family="normalization",
        scholarly_effect="none",
        label="Metric-aware relevance normalization",
        description="Convert collection-native distance/raw-score semantics into a normalized relevance contract.",
        input_type="candidate_set",
        output_type="candidate_set",
        config_schema={"type": "object", "properties": {"method": {"type": "string"}}},
    ),
    StrategySpec(
        strategy_id="fusion.rrf",
        family="fusion",
        scholarly_effect="advisory",
        label="Reciprocal-rank fusion",
        description="Deduplicate logical candidates and fuse rankings from parallel retrieval branches using reciprocal-rank fusion.",
        input_type="candidate_set",
        output_type="candidate_set",
        config_schema={"type": "object", "properties": {"rrf_k": _integer(1, 1000)}},
    ),
    StrategySpec(
        strategy_id="fusion.metadata_hybrid",
        family="fusion",
        scholarly_effect="advisory",
        label="Metadata semantic/lexical fusion",
        description="Combine semantic and lexical precedent relevance while preserving field/kind provenance.",
        input_type="candidate_set",
        output_type="candidate_set",
        config_schema={
            "type": "object",
            "properties": {
                "semantic_weight": _number(0, 1),
                "lexical_weight": _number(0, 1),
            },
        },
    ),
    StrategySpec(
        strategy_id="rerank.cross_encoder",
        family="rerank",
        scholarly_effect="advisory",
        label="Cross-encoder reranker",
        description="Score query/candidate text pairs with the shared sentence-transformers CrossEncoder boundary.",
        input_type="candidate_set",
        output_type="candidate_set",
        deterministic=False,
        capabilities=["cross_encoder"],
        config_schema={
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "top_k": _integer(1, 500),
                "timeout_seconds": _number(0.1, 300),
                "min_score": _number(-100, 100),
            },
        },
    ),
    StrategySpec(
        strategy_id="rerank.lexical_fallback",
        family="rerank",
        scholarly_effect="advisory",
        label="Lexical/vector fallback reranker",
        description="Use deterministic lexical overlap plus normalized vector relevance when the cross-encoder is unavailable.",
        input_type="candidate_set",
        output_type="candidate_set",
    ),
    StrategySpec(
        strategy_id="validate.evidence_support",
        family="support_validation",
        scholarly_effect="eligibility_gate",
        label="Evidence support validator",
        description="Verify that a candidate span directly supports the exact proposition/value; implementation may be deterministic or model-assisted but emits a distinct support result.",
        input_type="candidate_set",
        output_type="candidate_set",
        capabilities=["evidence_validation"],
        config_schema={"type": "object", "properties": {"min_score": _number(0, 1)}},
    ),
    StrategySpec(
        strategy_id="validate.citation_binding",
        family="support_validation",
        scholarly_effect="provenance_gate",
        label="Citation binding",
        description="Bind generated evidence markers to deterministic bibliographic citations and optional Works Cited entries.",
        input_type="model_output",
        output_type="model_output",
    ),
    StrategySpec(
        strategy_id="validate.provenance",
        family="support_validation",
        scholarly_effect="provenance_gate",
        label="Provenance sufficiency gate",
        description="Require source identity, revision/citation bindings, and other deterministic provenance needed by the consuming workflow.",
        input_type="candidate_set",
        output_type="candidate_set",
    ),
    StrategySpec(
        strategy_id="select.mmr",
        family="diversity",
        scholarly_effect="advisory",
        label="Maximum marginal relevance",
        description="Select a relevance/diversity-balanced subset while preserving the underlying relevance and MMR objective as separate scores.",
        input_type="candidate_set",
        output_type="candidate_set",
        config_schema={
            "type": "object",
            "properties": {
                "lambda_mult": _number(0, 1),
                "limit": _integer(1, 500),
                "min_relevance": _number(-1, 1),
            },
        },
    ),
    StrategySpec(
        strategy_id="select.source_diversity",
        family="diversity",
        scholarly_effect="advisory",
        label="Source-aware diversity",
        description="Apply explicit work/document/Record/adjacency/overlap constraints after relevance reranking.",
        input_type="candidate_set",
        output_type="candidate_set",
        config_schema={"type": "object", "properties": {"limit": _integer(1, 500)}},
    ),
    StrategySpec(
        strategy_id="select.top_k",
        family="selection",
        scholarly_effect="advisory",
        label="Top-K selection",
        description="Keep the highest-ranked K candidates without adding an additional relevance model.",
        input_type="candidate_set",
        output_type="candidate_set",
        config_schema={"type": "object", "properties": {"limit": _integer(1, 5000)}},
    ),
    StrategySpec(
        strategy_id="select.memory_hints",
        family="selection",
        scholarly_effect="advisory",
        label="Reviewed-precedent hints",
        description="Rank reviewed-precedent values by how many earlier records agree, then mean and best similarity, and keep up to the limit whose best similarity reaches the threshold (never below the field's own schema threshold). Hints are advisory; whether a value is pre-filled is decided by DerridAI, not by this stage.",
        input_type="candidate_set",
        output_type="candidate_set",
        config_schema={
            "type": "object",
            "properties": {"limit": _integer(1, 20), "min_similarity": _number(0, 1)},
        },
    ),
    StrategySpec(
        strategy_id="select.metadata_quotas",
        family="selection",
        scholarly_effect="advisory",
        label="Metadata precedent quotas",
        description="Preserve field, match-tier, positive/correction, and configured precedent quotas.",
        input_type="candidate_set",
        output_type="candidate_set",
    ),
    StrategySpec(
        strategy_id="pack.evidence_context",
        family="context_pack",
        scholarly_effect="transformation",
        label="Evidence context packer",
        description="Build a citation-aware evidence packet under configured per-record and total context budgets.",
        input_type="candidate_set",
        output_type="context_packet",
        config_schema={
            "type": "object",
            "properties": {
                "record_char_limit": _integer(100, 1000000),
                "total_char_limit": _integer(100, 5000000),
            },
        },
    ),
    StrategySpec(
        strategy_id="pack.metadata_precedents",
        family="context_pack",
        scholarly_effect="transformation",
        label="Metadata precedent packet",
        description="Serialize selected reviewed precedents and corrections into the bounded metadata-enrichment prompt context.",
        input_type="candidate_set",
        output_type="context_packet",
        config_schema={
            "type": "object",
            "properties": {
                "char_budget": _integer(1000, 500000),
            },
        },
    ),
    StrategySpec(
        strategy_id="llm.generate_answer",
        family="llm",
        scholarly_effect="generation",
        label="Research answer generation",
        description="Generate the final evidence-grounded Research answer with the configured provider/model profile.",
        input_type="context_packet",
        output_type="model_output",
        deterministic=False,
        invokes_llm=True,
        capabilities=["chat_model"],
    ),
    StrategySpec(
        strategy_id="llm.structured_metadata",
        family="llm",
        scholarly_effect="generation",
        label="Structured metadata generation",
        description="Run one schema-derived structured metadata task and validate the returned object at the backend boundary. The active metadata schema supplies the task and answer shape; the stage chooses which configured provider answers and how many attempts it gets.",
        input_type="context_packet",
        output_type="model_output",
        deterministic=False,
        invokes_llm=True,
        capabilities=["chat_model", "structured_output"],
        config_schema={
            "type": "object",
            "properties": {
                "provider_role": {"type": "string", "enum": ["primary", "review"], "default": "primary"},
                "attempts": {**_integer(1, 4), "default": 2},
            },
        },
    ),
    StrategySpec(
        strategy_id="llm.boundary_classification",
        family="llm",
        scholarly_effect="generation",
        label="Boundary classification",
        description="Ask a chat model a closed-choice question about a record boundary: split or keep an ambiguous transition, or whether a suspicious record seam should stay or move. Returned block IDs are checked deterministically; a failed, omitted, or low-confidence answer keeps the boundary. The stage chooses which configured provider answers and how many attempts it gets.",
        input_type="context_packet",
        output_type="model_output",
        deterministic=False,
        invokes_llm=True,
        capabilities=["chat_model", "structured_output"],
        config_schema={
            "type": "object",
            "properties": {
                "provider_role": {"type": "string", "enum": ["primary", "review"], "default": "primary"},
                "attempts": {**_integer(1, 4), "default": 2},
            },
        },
    ),
    StrategySpec(
        strategy_id="llm.document_manifest",
        family="llm",
        scholarly_effect="generation",
        label="Document manifest",
        description="Ask a chat model once per analysis for a source-bound document manifest: bibliography, language and the main-text page range, from embedded file metadata and a sample of the whole document. Embedded metadata, a confident start-page inference and reviewer-confirmed structure still outrank the answer, and a failed call falls back to embedded metadata. The stage chooses which configured provider answers and how many attempts it gets.",
        input_type="context_packet",
        output_type="model_output",
        deterministic=False,
        invokes_llm=True,
        capabilities=["chat_model", "structured_output"],
        config_schema={
            "type": "object",
            "properties": {
                "provider_role": {"type": "string", "enum": ["primary", "review"], "default": "primary"},
                "attempts": {**_integer(1, 4), "default": 2},
            },
        },
    ),
    StrategySpec(
        strategy_id="llm.text_touchup",
        family="llm",
        scholarly_effect="generation",
        label="Text touch-up",
        description="Ask a chat model to propose cleaned-up text for one Record, on a reviewer request or during metadata enrichment when the build asks for it. The answer is checked against the source text and stays a proposal until a reviewer approves it. The stage chooses which configured provider answers and how many attempts it gets.",
        input_type="context_packet",
        output_type="model_output",
        deterministic=False,
        invokes_llm=True,
        capabilities=["chat_model", "structured_output"],
        config_schema={
            "type": "object",
            "properties": {
                "provider_role": {"type": "string", "enum": ["primary", "review"], "default": "primary"},
                "attempts": {**_integer(1, 4), "default": 2},
            },
        },
    ),
    StrategySpec(
        strategy_id="llm.reviewer_evidence_choice",
        family="llm",
        scholarly_effect="generation",
        label="Reviewer evidence choice",
        description="When a reviewer asks, a chat model chooses which source-unit IDs of the Record support a metadata value. Every returned ID and its support are checked deterministically, and a suggestion stays advisory until the reviewer binds it. The stage chooses which configured provider answers and how many attempts it gets.",
        input_type="context_packet",
        output_type="model_output",
        deterministic=False,
        invokes_llm=True,
        capabilities=["chat_model", "structured_output"],
        config_schema={
            "type": "object",
            "properties": {
                "provider_role": {"type": "string", "enum": ["primary", "review"], "default": "primary"},
                "attempts": {**_integer(1, 4), "default": 2},
            },
        },
    ),
    StrategySpec(
        strategy_id="llm.closed_choice_evidence",
        family="llm",
        scholarly_effect="generation",
        label="Closed-choice evidence selection",
        description="Ask a chat model to choose only among the current Record's source-unit IDs, then validate the IDs deterministically. It reads every source unit of the Record, not only upstream candidates. In evidence recovery the stage chooses which configured provider answers (by default the primary provider, then the review provider) and how many attempts each gets.",
        input_type="any",
        output_type="candidate_set",
        deterministic=False,
        invokes_llm=True,
        capabilities=["chat_model", "closed_choice"],
        config_schema={
            "type": "object",
            "properties": {
                "provider_role": {"type": "string", "enum": ["chain", "primary", "review"], "default": "chain"},
                "attempts": {**_integer(1, 4), "default": 2},
            },
        },
    ),
    StrategySpec(
        strategy_id="llm.grade_rag",
        family="evaluation",
        scholarly_effect="evaluation",
        label="RAG response grading",
        description="Evaluate a generated answer against the evidence packet using the configured grading profile.",
        input_type="model_output",
        output_type="evaluation",
        deterministic=False,
        invokes_llm=True,
        capabilities=["chat_model"],
    ),
]

strategy_registry = StrategyRegistry(DEFAULT_STRATEGIES)


# Settings only the evidence-recovery runtime honours. Other adapters reject
# them so Pipeline Studio never shows an editable value that nothing applies.
RECOVERY_ONLY_CONFIG: dict[str, frozenset[str]] = {
    "retrieve.lexical_bm25": frozenset({"min_score"}),
    "rerank.cross_encoder": frozenset({"min_score"}),
    "select.mmr": frozenset({"min_relevance"}),
    # The reviewer-suggestion graph never calls a model; only recovery asks it.
    "llm.closed_choice_evidence": frozenset({"provider_role", "attempts"}),
}


def reject_unhonoured_config(pipeline: Any, adapter: str) -> None:
    """Raise when an enabled stage sets a recovery-only key this adapter ignores."""

    for stage in pipeline.stages:
        ignored = sorted(set(stage.config) & RECOVERY_ONLY_CONFIG.get(stage.strategy, frozenset()))
        if stage.enabled and ignored:
            raise ValueError(
                f"The {adapter} adapter does not apply {', '.join(ignored)} on stage {stage.id!r}."
            )
