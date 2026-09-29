# Copyright 2026 Aaron John Schlosser, PhD.
"""Registry of pipeline strategies that DerridAI is allowed to execute.

The registry is deliberately code-owned. Saved pipelines reference these stable
IDs and parameter schemas, but cannot smuggle executable code into the server.
"""

from __future__ import annotations

from collections.abc import Iterable

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
        strategy_id="query.research_decompose",
        family="query_transform",
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
        label="Field-aware evidence query",
        description="Build an evidence query deterministically from the target metadata field and proposed value.",
        input_type="query",
        output_type="query",
    ),
    StrategySpec(
        strategy_id="retrieve.chroma_similarity",
        family="candidate_generation",
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
        label="Lexical BM25 retrieval",
        description="Rank candidate text with the local deterministic BM25-style lexical retriever.",
        input_type="query",
        output_type="candidate_set",
        config_schema={"type": "object", "properties": {"fetch_k": _integer(1, 5000)}},
    ),
    StrategySpec(
        strategy_id="retrieve.metadata_exemplars",
        family="candidate_generation",
        label="Metadata exemplar retrieval",
        description="Retrieve schema/field/language-filtered reviewed metadata precedents from the derived exemplar projection.",
        input_type="query",
        output_type="candidate_set",
        deterministic=False,
        capabilities=["embedding", "chroma"],
        config_schema={"type": "object", "properties": {"max_items": _integer(1, 100)}},
    ),
    StrategySpec(
        strategy_id="retrieve.claim_memory",
        family="candidate_generation",
        label="Validated-claim memory",
        description="Retrieve owner-scoped semantically similar validated claims, then rejoin authoritative claim/support state.",
        input_type="query",
        output_type="candidate_set",
        deterministic=False,
        capabilities=["embedding", "chroma"],
    ),
    StrategySpec(
        strategy_id="retrieve.response_memory",
        family="candidate_generation",
        label="Prior-response memory",
        description="Retrieve owner-scoped semantically similar eligible Research responses and rejoin durable response state.",
        input_type="query",
        output_type="candidate_set",
        deterministic=False,
        capabilities=["embedding", "chroma"],
    ),
    StrategySpec(
        strategy_id="filter.metadata_scope",
        family="filter",
        label="Metadata scope filter",
        description="Constrain precedent candidates by schema, stable field identities, language, scope, and reviewed analogy fields.",
        input_type="candidate_set",
        output_type="candidate_set",
    ),
    StrategySpec(
        strategy_id="normalize.collection_relevance",
        family="normalization",
        label="Metric-aware relevance normalization",
        description="Convert collection-native distance/raw-score semantics into a normalized relevance contract.",
        input_type="candidate_set",
        output_type="candidate_set",
    ),
    StrategySpec(
        strategy_id="fusion.rrf",
        family="fusion",
        label="Reciprocal-rank fusion",
        description="Deduplicate logical candidates and fuse rankings from parallel retrieval branches using reciprocal-rank fusion.",
        input_type="candidate_set",
        output_type="candidate_set",
        config_schema={"type": "object", "properties": {"rrf_k": _integer(1, 1000)}},
    ),
    StrategySpec(
        strategy_id="fusion.metadata_hybrid",
        family="fusion",
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
            },
        },
    ),
    StrategySpec(
        strategy_id="rerank.lexical_fallback",
        family="rerank",
        label="Lexical/vector fallback reranker",
        description="Use deterministic lexical overlap plus normalized vector relevance when the cross-encoder is unavailable.",
        input_type="candidate_set",
        output_type="candidate_set",
    ),
    StrategySpec(
        strategy_id="validate.evidence_support",
        family="support_validation",
        label="Evidence support validator",
        description="Verify that a candidate span directly supports the exact proposition/value; implementation may be deterministic or model-assisted but emits a distinct support result.",
        input_type="candidate_set",
        output_type="candidate_set",
        capabilities=["evidence_validation"],
        config_schema={"type": "object", "properties": {"min_score": _number(0, 1)}},
    ),
    StrategySpec(
        strategy_id="validate.provenance",
        family="support_validation",
        label="Provenance sufficiency gate",
        description="Require source identity, revision/citation bindings, and other deterministic provenance needed by the consuming workflow.",
        input_type="candidate_set",
        output_type="candidate_set",
    ),
    StrategySpec(
        strategy_id="select.mmr",
        family="diversity",
        label="Maximum marginal relevance",
        description="Select a relevance/diversity-balanced subset while preserving the underlying relevance and MMR objective as separate scores.",
        input_type="candidate_set",
        output_type="candidate_set",
        config_schema={
            "type": "object",
            "properties": {
                "lambda_mult": _number(0, 1),
                "limit": _integer(1, 500),
            },
        },
    ),
    StrategySpec(
        strategy_id="select.source_diversity",
        family="diversity",
        label="Source-aware diversity",
        description="Apply explicit work/document/Record/adjacency/overlap constraints after relevance reranking.",
        input_type="candidate_set",
        output_type="candidate_set",
        config_schema={"type": "object", "properties": {"limit": _integer(1, 500)}},
    ),
    StrategySpec(
        strategy_id="select.top_k",
        family="selection",
        label="Top-K selection",
        description="Keep the highest-ranked K candidates without adding an additional relevance model.",
        input_type="candidate_set",
        output_type="candidate_set",
        config_schema={"type": "object", "properties": {"limit": _integer(1, 5000)}},
    ),
    StrategySpec(
        strategy_id="select.metadata_quotas",
        family="selection",
        label="Metadata precedent quotas",
        description="Preserve field, match-tier, positive/correction, and configured precedent quotas.",
        input_type="candidate_set",
        output_type="candidate_set",
    ),
    StrategySpec(
        strategy_id="pack.evidence_context",
        family="context_pack",
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
        label="Metadata precedent packet",
        description="Serialize selected reviewed precedents and corrections into the bounded metadata-enrichment prompt context.",
        input_type="candidate_set",
        output_type="context_packet",
    ),
    StrategySpec(
        strategy_id="llm.generate_answer",
        family="llm",
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
        label="Structured metadata generation",
        description="Run one schema-derived structured metadata task and validate the returned object at the backend boundary.",
        input_type="context_packet",
        output_type="model_output",
        deterministic=False,
        invokes_llm=True,
        capabilities=["chat_model", "structured_output"],
    ),
    StrategySpec(
        strategy_id="llm.closed_choice_evidence",
        family="llm",
        label="Closed-choice evidence selection",
        description="Ask a chat model to choose only from supplied source-unit IDs, then validate the IDs deterministically.",
        input_type="candidate_set",
        output_type="candidate_set",
        deterministic=False,
        invokes_llm=True,
        capabilities=["chat_model", "closed_choice"],
    ),
    StrategySpec(
        strategy_id="llm.grade_rag",
        family="evaluation",
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
