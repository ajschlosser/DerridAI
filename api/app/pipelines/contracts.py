# Copyright 2026 Aaron John Schlosser, PhD.
"""Typed ports and declared algorithmic cost for every registered strategy.

The registry says what a strategy *is*; this table says what it *takes* and
*gives* (named, typed ports) and what it *costs* (declared complexity). Keeping
both in one reviewed table means a strategy cannot be registered without a
statement of its inputs and its cost, and the table is checked for completeness
in tests. The complexity formulas were read off the implementations; they are
declarations, and the empirical latency analysis is the check on them.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from .models import (
    ComplexitySpec,
    CostDriver,
    DataType,
    OutputCardinality,
    PortSpec,
    StrategySpec,
)

# Variables used by complexity formulas. Labels and descriptions are localized
# through ``pipelines.complexity_variable.<id>.*``.
COMPLEXITY_VARIABLES: tuple[str, ...] = ("n", "N", "k", "L", "q", "g", "P", "d", "S")
COST_DRIVERS: tuple[CostDriver, ...] = (
    "cpu",
    "storage",
    "embedding",
    "model_inference",
    "llm_generation",
)
# Declared-complexity ordering, used to name a pipeline's dominant cost.
COMPLEXITY_ORDERS: tuple[tuple[int, str], ...] = (
    (0, "constant"),
    (1, "sublinear"),
    (2, "linear_in_candidates"),
    (3, "linearithmic"),
    (4, "linear_in_scope"),
    (5, "superlinear"),
    (6, "model_inference"),
    (7, "generation"),
)


def _in(name: str, data_type: DataType, *, required: bool = True, multiple: bool = False) -> PortSpec:
    return PortSpec(name=name, data_type=data_type, required=required, multiple=multiple)


def _tuning(name: str, *, minimum: float, maximum: float) -> PortSpec:
    """An optional number input that may be fixed to a constant (a tuning knob)."""

    return PortSpec(
        name=name,
        data_type="number",
        required=False,
        accepts_constant=True,
        minimum=minimum,
        maximum=maximum,
    )


QUERY_IN = _in("query", "query")
CANDIDATES_IN = _in("candidates", "candidate_set", multiple=True)
CONTEXT_IN = _in("context", "context_packet")
ANSWER_IN = _in("answer", "model_output")


def _complexity(
    time: str,
    space: str,
    *,
    order: int,
    variables: Iterable[str] = (),
    driver: CostDriver = "cpu",
    model_calls: str = "0",
    scope: bool = False,
    cardinality: OutputCardinality | None = None,
) -> ComplexitySpec:
    return ComplexitySpec(
        time=time,
        space=space,
        variables=list(variables),
        driver=driver,
        model_calls=model_calls,
        scales_with_scope=scope,
        order=order,
        cardinality=cardinality or OutputCardinality(),
    )


def _cap(key: str) -> OutputCardinality:
    return OutputCardinality(rule="config_cap", config_key=key)


_SUM = OutputCardinality(rule="sum_inputs")
_FIXED = OutputCardinality(rule="fixed", default=1)
_POOL = OutputCardinality(rule="config_cap", config_key="fetch_k")

def _retrieve_ann() -> ComplexitySpec:
    """Embed the query, then an approximate nearest-neighbour lookup in the index."""

    return _complexity(
        "O(q + d·log N + k)",
        "O(k·d)",
        order=1,
        variables=("q", "d", "N", "k"),
        driver="embedding",
        model_calls="1",
        scope=True,
        cardinality=_POOL,
    )


def _retrieve_scan(
    driver: CostDriver = "cpu",
    *,
    time: str = "O(N·L)",
    variables: Iterable[str] = ("N", "L"),
) -> ComplexitySpec:
    """Read or tokenise every item in scope."""

    return _complexity(
        time,
        "O(N)",
        order=4,
        variables=variables,
        driver=driver,
        scope=True,
        cardinality=_POOL,
    )


def _llm_call(model_calls: str) -> ComplexitySpec:
    return _complexity(
        "O(P + g)",
        "O(P + g)",
        order=7,
        variables=("P", "g"),
        driver="llm_generation",
        model_calls=model_calls,
        cardinality=_FIXED,
    )


# strategy_id -> (inputs, outputs, complexity)
STRATEGY_CONTRACTS: dict[str, tuple[list[PortSpec], list[PortSpec], ComplexitySpec]] = {
    "query.passthrough": (
        [QUERY_IN],
        [_in("query", "query")],
        _complexity("O(1)", "O(1)", order=0),
    ),
    "query.research_decompose": (
        [QUERY_IN],
        [_in("query", "query")],
        _complexity(
            "O(q + g)",
            "O(q + g)",
            order=7,
            variables=("q", "g"),
            driver="llm_generation",
            model_calls="1",
        ),
    ),
    "query.evidence_field": (
        [QUERY_IN],
        [_in("query", "query")],
        _complexity("O(q)", "O(q)", order=2, variables=("q",)),
    ),
    "retrieve.selected_evidence": (
        [QUERY_IN],
        [_in("candidates", "candidate_set")],
        _complexity(
            "O(k)",
            "O(k)",
            order=2,
            variables=("k",),
            driver="storage",
            cardinality=OutputCardinality(rule="pool"),
        ),
    ),
    "retrieve.chroma_similarity": (
        [QUERY_IN, _tuning("fetch_k", minimum=1, maximum=1000)],
        [_in("candidates", "candidate_set")],
        _retrieve_ann(),
    ),
    "retrieve.source_cosine": (
        [QUERY_IN],
        [_in("candidates", "candidate_set")],
        _complexity(
            "O(N·d)",
            "O(N·d)",
            order=4,
            variables=("N", "d"),
            driver="embedding",
            model_calls="1",
            scope=True,
            cardinality=_POOL,
        ),
    ),
    "retrieve.lexical_bm25": (
        [QUERY_IN, _tuning("fetch_k", minimum=1, maximum=1000)],
        [_in("candidates", "candidate_set")],
        # ChromaStore.lexical_search reads at most max(100·n_results, 2000) items (cap 20000), so
        # cost is linear in N up to S and flat beyond it. Checked with
        # scripts/calibrate_store_search_complexity.py: exponent 1.04 for N <= 2000, 0.13 above.
        _retrieve_scan(time="O(min(N, S)·L)", variables=("N", "S", "L")),
    ),
    "retrieve.token_overlap": (
        [QUERY_IN],
        [_in("candidates", "candidate_set")],
        _retrieve_scan(),
    ),
    "retrieve.store_keyword": (
        [QUERY_IN, _tuning("fetch_k", minimum=1, maximum=1000)],
        [_in("candidates", "candidate_set")],
        _retrieve_scan("storage"),
    ),
    "retrieve.store_filter": (
        [QUERY_IN, _tuning("fetch_k", minimum=1, maximum=1000)],
        [_in("candidates", "candidate_set")],
        _complexity(
            "O(N)",
            "O(N)",
            order=4,
            variables=("N",),
            driver="storage",
            scope=True,
            cardinality=_POOL,
        ),
    ),
    "retrieve.metadata_exemplars": (
        [QUERY_IN],
        [_in("candidates", "candidate_set")],
        _retrieve_ann(),
    ),
    "retrieve.claim_memory": (
        [QUERY_IN],
        [_in("candidates", "candidate_set")],
        _retrieve_ann(),
    ),
    "retrieve.response_memory": (
        [QUERY_IN],
        [_in("candidates", "candidate_set")],
        _retrieve_ann(),
    ),
    "retrieve.memory_lexical_fallback": (
        [_in("query", "any", required=False)],
        [_in("candidates", "candidate_set")],
        _retrieve_scan(),
    ),
    "fallback.metadata_precedents_lexical": (
        [_in("query", "any", required=False)],
        [_in("context", "context_packet")],
        _complexity(
            "O(N·L + k log k)",
            "O(N)",
            order=4,
            variables=("N", "L", "k"),
            scope=True,
            cardinality=_FIXED,
        ),
    ),
    "filter.metadata_scope": (
        [CANDIDATES_IN],
        [_in("candidates", "candidate_set")],
        _complexity("O(n)", "O(n)", order=2, variables=("n",)),
    ),
    "normalize.collection_relevance": (
        [CANDIDATES_IN],
        [_in("candidates", "candidate_set")],
        _complexity("O(n)", "O(n)", order=2, variables=("n",)),
    ),
    "fusion.rrf": (
        [CANDIDATES_IN, _tuning("rrf_k", minimum=1, maximum=1000)],
        [_in("candidates", "candidate_set")],
        _complexity("O(n log n)", "O(n)", order=3, variables=("n",), cardinality=_SUM),
    ),
    "fusion.metadata_hybrid": (
        [CANDIDATES_IN],
        [_in("candidates", "candidate_set")],
        _complexity("O(n log n)", "O(n)", order=3, variables=("n",), cardinality=_SUM),
    ),
    "rerank.cross_encoder": (
        [CANDIDATES_IN, QUERY_IN],
        [_in("candidates", "candidate_set")],
        _complexity(
            "O(n·(q + L)²)",
            "O(n)",
            order=6,
            variables=("n", "q", "L"),
            driver="model_inference",
            # Upper bound: Research scores every incoming candidate, but the evidence
            # adapter scores only the head ``top_k`` (evidence.py), so the real count
            # there is min(n, top_k). Declared as n so the worst case is never hidden.
            model_calls="n",
            cardinality=_cap("top_k"),
        ),
    ),
    "rerank.lexical_fallback": (
        [CANDIDATES_IN, QUERY_IN],
        [_in("candidates", "candidate_set")],
        _complexity("O(n·L + n log n)", "O(n)", order=3, variables=("n", "L")),
    ),
    "validate.evidence_support": (
        [CANDIDATES_IN, _in("query", "query", required=False)],
        [_in("candidates", "candidate_set")],
        # Checked against evidence.py/_support_rows (read, not measured): the support
        # score is deterministic token overlap, not model-assisted, but it re-scores
        # *every* source unit in scope (``limit=len(blocks)``) and then looks the
        # incoming candidates up, so the cost follows the scope size N, not n.
        _complexity("O(N·L)", "O(N)", order=4, variables=("N", "L"), scope=True),
    ),
    "validate.citation_binding": (
        [ANSWER_IN],
        [_in("answer", "model_output")],
        _complexity("O(g)", "O(g)", order=2, variables=("g",), cardinality=_FIXED),
    ),
    "validate.provenance": (
        [CANDIDATES_IN],
        [_in("candidates", "candidate_set")],
        # Checked, left unchanged: the Research gate looks each candidate up in storage
        # (O(n)). The reviewer-evidence adapter's variant also builds a set of every
        # source unit in scope first (O(N + n), in memory), but one strategy id carries
        # one declaration and the Research reading is the dominant use.
        _complexity("O(n)", "O(n)", order=2, variables=("n",), driver="storage"),
    ),
    "select.mmr": (
        [
            CANDIDATES_IN,
            _tuning("lambda_mult", minimum=0, maximum=1),
            _tuning("limit", minimum=1, maximum=1000),
        ],
        [_in("candidates", "candidate_set")],
        _complexity(
            "O(n·k²·d)", "O(n·d)", order=5, variables=("n", "k", "d"), cardinality=_cap("limit")
        ),
    ),
    "select.source_diversity": (
        [CANDIDATES_IN],
        [_in("candidates", "candidate_set")],
        _complexity(
            "O(n·k)", "O(n)", order=3, variables=("n", "k"), cardinality=_cap("limit")
        ),
    ),
    "select.top_k": (
        [CANDIDATES_IN, _tuning("limit", minimum=1, maximum=1000)],
        [_in("candidates", "candidate_set")],
        _complexity(
            "O(n log n)", "O(n)", order=3, variables=("n",), cardinality=_cap("limit")
        ),
    ),
    "select.memory_hints": (
        [CANDIDATES_IN],
        [_in("candidates", "candidate_set")],
        _complexity(
            "O(n log n)", "O(n)", order=3, variables=("n",), cardinality=_cap("limit")
        ),
    ),
    "select.metadata_quotas": (
        [CANDIDATES_IN],
        [_in("candidates", "candidate_set")],
        _complexity("O(n log n)", "O(n)", order=3, variables=("n",)),
    ),
    "pack.evidence_context": (
        [CANDIDATES_IN],
        [_in("context", "context_packet")],
        _complexity(
            "O(n·L)", "O(n·L)", order=2, variables=("n", "L"), cardinality=_FIXED
        ),
    ),
    "pack.metadata_precedents": (
        [CANDIDATES_IN],
        [_in("context", "context_packet")],
        _complexity(
            "O(n·L)", "O(n·L)", order=2, variables=("n", "L"), cardinality=_FIXED
        ),
    ),
    "llm.generate_answer": (
        [CONTEXT_IN, QUERY_IN],
        [_in("answer", "model_output")],
        _llm_call("1"),
    ),
    "llm.structured_metadata": (
        [CONTEXT_IN],
        [_in("answer", "model_output")],
        _llm_call("attempts"),
    ),
    "llm.boundary_classification": (
        [CONTEXT_IN],
        [_in("answer", "model_output")],
        _llm_call("attempts"),
    ),
    "llm.document_manifest": (
        [CONTEXT_IN],
        [_in("answer", "model_output")],
        _llm_call("attempts"),
    ),
    "llm.text_touchup": (
        [CONTEXT_IN],
        [_in("answer", "model_output")],
        _llm_call("attempts"),
    ),
    "llm.reviewer_evidence_choice": (
        [CONTEXT_IN],
        [_in("answer", "model_output")],
        _llm_call("attempts"),
    ),
    "llm.closed_choice_evidence": (
        [_in("candidates", "any", required=False, multiple=True)],
        [_in("candidates", "candidate_set")],
        _complexity(
            "O(S·L + g)",
            "O(S·L)",
            order=7,
            variables=("S", "L", "g"),
            driver="llm_generation",
            model_calls="attempts",
            cardinality=OutputCardinality(rule="pool"),
        ),
    ),
    "llm.grade_rag": (
        [ANSWER_IN, QUERY_IN],
        [_in("evaluation", "evaluation")],
        _llm_call("1"),
    ),
}


# Whether a strategy's stage may overlap with independent sibling branches.
#   safe             pure retrieval/scoring over immutable inputs
#   provider_limited calls a model or embedder; must respect per-provider limits
#   exclusive        anything else (mutates state, order-dependent, unknown)
# Overlap is an opt-in executor feature; this only declares what is permitted.
Concurrency = Literal["safe", "provider_limited", "exclusive"]
STRATEGY_CONCURRENCY: dict[str, Concurrency] = {
    "retrieve.lexical_bm25": "safe",
    "retrieve.store_keyword": "safe",
    "retrieve.store_filter": "safe",
    "retrieve.chroma_similarity": "provider_limited",
}


def strategy_concurrency(strategy_id: str) -> Concurrency:
    """Declared concurrency of a strategy; undeclared strategies are ``exclusive``."""

    return STRATEGY_CONCURRENCY.get(strategy_id, "exclusive")


def with_contract(spec: StrategySpec) -> StrategySpec:
    """Attach the declared ports and complexity to a registered strategy."""

    contract = STRATEGY_CONTRACTS.get(spec.strategy_id)
    if contract is None:
        return spec
    inputs, outputs, complexity = contract
    return spec.model_copy(
        update={"inputs": inputs, "outputs": outputs, "complexity": complexity}
    )


def input_ports(spec: StrategySpec) -> list[PortSpec]:
    """Declared input ports, or one primary port derived from ``input_type``."""

    if spec.inputs:
        return list(spec.inputs)
    return [PortSpec(name="input", data_type=spec.input_type, required=spec.input_type != "any")]


def output_ports(spec: StrategySpec) -> list[PortSpec]:
    if spec.outputs:
        return list(spec.outputs)
    return [PortSpec(name="output", data_type=spec.output_type)]
