# Copyright 2026 Aaron John Schlosser, PhD.
"""Compile declarative Research pipelines into a bounded execution plan.

Research remains implemented by explicit Python stages rather than a generic
workflow interpreter. The compiler translates a validated declarative graph
into the exact stage identities, fallbacks, and configuration that the feature
adapter is allowed to execute. Unsupported arrangements are rejected before an
administrator can assign them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from .models import PipelineDefinition, PipelineStageDefinition
from .registry import reject_unhonoured_config
from .service import pipeline_hash

ResearchDiversity = Literal["none", "source_aware", "mmr"]
FallbackCondition = Literal["empty", "unavailable", "timeout", "error"]


@dataclass(frozen=True, slots=True)
class ResearchRuntimeSettings:
    """Effective numeric/model settings resolved from pipeline config + request.

    A pipeline value is authoritative when the stage explicitly declares it.
    Request values remain the fallback for backwards-compatible per-run controls
    when the saved definition does not pin that parameter.
    """

    query_decomposition_num_predict: int
    semantic_fetch_k: int
    lexical_fetch_k: int
    retrieval_mmr_lambda: float
    retrieval_mmr_limit: int
    rrf_k: int
    rerank_top_n: int
    cross_encoder_model: str
    cross_encoder_timeout_seconds: float | None
    diversity_lambda: float
    diversity_limit: int
    evidence_record_char_limit: int
    evidence_total_char_limit: int


@dataclass(frozen=True, slots=True)
class ResearchPipelinePlan:
    pipeline_id: str
    pipeline_version: int
    pipeline_hash: str
    query_stage_id: str | None
    query_decomposition_available: bool
    semantic_stage_id: str | None
    lexical_stage_id: str | None
    normalization_stage_id: str | None
    pre_fusion_mmr_stage_id: str | None
    fusion_stage_id: str | None
    rerank_stage_id: str | None
    rerank_strategy: str | None
    lexical_rerank_stage_id: str | None
    rerank_fallbacks: dict[str, tuple[str, str]]
    post_rerank_diversity: ResearchDiversity
    diversity_stage_id: str | None
    provenance_stage_id: str
    context_pack_stage_id: str
    generation_stage_id: str
    citation_binding_stage_id: str
    evaluation_stage_id: str | None
    stage_configs: dict[str, dict[str, Any]]

    @property
    def semantic_retrieval(self) -> bool:
        return self.semantic_stage_id is not None

    @property
    def lexical_retrieval(self) -> bool:
        return self.lexical_stage_id is not None

    @property
    def pre_fusion_mmr(self) -> bool:
        return self.pre_fusion_mmr_stage_id is not None

    @property
    def reciprocal_rank_fusion(self) -> bool:
        return self.fusion_stage_id is not None

    @property
    def cross_encoder_available(self) -> bool:
        return self.rerank_strategy == "rerank.cross_encoder"

    @property
    def lexical_rerank_available(self) -> bool:
        return self.lexical_rerank_stage_id is not None

    @property
    def provenance_gate(self) -> bool:
        return bool(self.provenance_stage_id)

    @property
    def context_pack(self) -> bool:
        return bool(self.context_pack_stage_id)

    @property
    def generation(self) -> bool:
        return bool(self.generation_stage_id)

    @property
    def citation_binding(self) -> bool:
        return bool(self.citation_binding_stage_id)

    @property
    def evaluation_available(self) -> bool:
        return self.evaluation_stage_id is not None

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

    def config_value(self, stage_id: str | None, key: str, fallback: Any) -> Any:
        if not stage_id:
            return fallback
        config = self.stage_configs.get(stage_id) or {}
        return config[key] if key in config else fallback

    def rerank_fallback(self, condition: FallbackCondition) -> tuple[str, str] | None:
        return self.rerank_fallbacks.get(condition)


_ALLOWED_RESEARCH_STRATEGIES = {
    "query.passthrough",
    "query.research_decompose",
    "retrieve.chroma_similarity",
    "retrieve.lexical_bm25",
    "normalize.collection_relevance",
    "fusion.rrf",
    "rerank.cross_encoder",
    "rerank.lexical_fallback",
    "validate.provenance",
    "validate.citation_binding",
    "select.mmr",
    "select.source_diversity",
    "select.top_k",
    "pack.evidence_context",
    "llm.generate_answer",
    "llm.grade_rag",
}


def _enabled_stages(pipeline: PipelineDefinition) -> dict[str, PipelineStageDefinition]:
    return {stage.id: stage for stage in pipeline.stages if stage.enabled}


def _reachable(
    stages: Mapping[str, PipelineStageDefinition],
    source_id: str,
    target_id: str,
    *,
    include_fallbacks: bool = False,
) -> bool:
    if source_id not in stages or target_id not in stages:
        return False
    pending = (
        list(stages[source_id].edge_targets())
        if include_fallbacks
        else list(stages[source_id].next)
    )
    seen: set[str] = set()
    while pending:
        stage_id = pending.pop()
        if stage_id == target_id:
            return True
        if stage_id in seen or stage_id not in stages:
            continue
        seen.add(stage_id)
        stage = stages[stage_id]
        pending.extend(stage.edge_targets() if include_fallbacks else stage.next)
    return False


def _single_stage(
    by_strategy: Mapping[str, list[PipelineStageDefinition]],
    strategy: str,
    *,
    required: bool = False,
) -> PipelineStageDefinition | None:
    rows = by_strategy.get(strategy, [])
    if len(rows) > 1:
        raise ValueError(
            f"Research currently supports at most one {strategy!r} stage per pipeline."
        )
    if required and not rows:
        raise ValueError(f"Research pipelines require {strategy!r}.")
    return rows[0] if rows else None


def _require_normal_path(
    stages: Mapping[str, PipelineStageDefinition],
    source: PipelineStageDefinition,
    target: PipelineStageDefinition,
    message: str,
) -> None:
    if not _reachable(stages, source.id, target.id):
        raise ValueError(message)


def _fallback_condition(reason: str) -> FallbackCondition:
    value = str(reason or "").casefold()
    if "timeout" in value:
        return "timeout"
    if (
        "missing_dependency" in value
        or "not_configured" in value
        or "unavailable" in value
    ):
        return "unavailable"
    return "error"


def classify_cross_encoder_failure(reason: str) -> FallbackCondition:
    """Map CrossEncoder telemetry into the declarative fallback edge to follow."""

    return _fallback_condition(reason)


def resolve_research_runtime_settings(
    plan: ResearchPipelinePlan,
    request: Mapping[str, Any],
) -> ResearchRuntimeSettings:
    """Resolve stage parameters without letting request defaults mask pipeline edits."""

    request_fetch_k = max(1, int(request.get("fetch_k") or 500))
    request_k = max(1, int(request.get("k") or 64))
    semantic_fetch_k = max(
        request_k,
        int(plan.config_value(plan.semantic_stage_id, "fetch_k", request_fetch_k)),
    )
    lexical_fetch_k = max(
        request_k,
        int(plan.config_value(plan.lexical_stage_id, "fetch_k", request_fetch_k)),
    )

    request_lambda = float(request.get("lambda_mult") or 0.7)
    retrieval_mmr_lambda = float(
        plan.config_value(plan.pre_fusion_mmr_stage_id, "lambda_mult", request_lambda)
    )
    retrieval_mmr_limit = max(
        1,
        int(plan.config_value(plan.pre_fusion_mmr_stage_id, "limit", request_k)),
    )
    diversity_lambda = float(
        plan.config_value(plan.diversity_stage_id, "lambda_mult", request_lambda)
    )
    diversity_limit = max(
        1,
        int(
            plan.config_value(
                plan.diversity_stage_id,
                "limit",
                int(request.get("rerank_top_n") or 24),
            )
        ),
    )

    request_model = str(
        request.get("cross_encoder_model")
        or "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ).strip()
    configured_model = str(
        plan.config_value(plan.rerank_stage_id, "model", request_model) or request_model
    ).strip()

    timeout_raw = plan.config_value(plan.rerank_stage_id, "timeout_seconds", None)
    timeout = float(timeout_raw) if timeout_raw is not None else None

    return ResearchRuntimeSettings(
        query_decomposition_num_predict=max(
            64,
            int(
                plan.config_value(
                    plan.query_stage_id,
                    "num_predict",
                    int(request.get("query_decomposition_num_predict") or 768),
                )
            ),
        ),
        semantic_fetch_k=semantic_fetch_k,
        lexical_fetch_k=lexical_fetch_k,
        retrieval_mmr_lambda=max(0.0, min(1.0, retrieval_mmr_lambda)),
        retrieval_mmr_limit=retrieval_mmr_limit,
        rrf_k=max(
            1,
            int(
                plan.config_value(
                    plan.fusion_stage_id,
                    "rrf_k",
                    int(request.get("rrf_k") or 60),
                )
            ),
        ),
        rerank_top_n=max(
            1,
            int(
                plan.config_value(
                    plan.rerank_stage_id,
                    "top_k",
                    int(request.get("rerank_top_n") or 24),
                )
            ),
        ),
        cross_encoder_model=configured_model,
        cross_encoder_timeout_seconds=timeout,
        diversity_lambda=max(0.0, min(1.0, diversity_lambda)),
        diversity_limit=diversity_limit,
        evidence_record_char_limit=max(
            100,
            int(
                plan.config_value(
                    plan.context_pack_stage_id,
                    "record_char_limit",
                    int(request.get("evidence_record_char_limit") or 12000),
                )
            ),
        ),
        evidence_total_char_limit=max(
            100,
            int(
                plan.config_value(
                    plan.context_pack_stage_id,
                    "total_char_limit",
                    int(request.get("evidence_total_char_limit") or 120000),
                )
            ),
        ),
    )


def compile_research_pipeline(pipeline: PipelineDefinition) -> ResearchPipelinePlan:
    """Validate a Research graph against the feature adapter's supported shape."""

    if pipeline.purpose != "research":
        raise ValueError(
            f"Pipeline {pipeline.pipeline_id!r} has purpose {pipeline.purpose!r}, not 'research'."
        )
    reject_unhonoured_config(pipeline, "Research")

    stages = _enabled_stages(pipeline)
    unknown = sorted(
        {
            stage.strategy
            for stage in stages.values()
            if stage.strategy not in _ALLOWED_RESEARCH_STRATEGIES
        }
    )
    if unknown:
        raise ValueError(
            "Research does not implement these pipeline strategies yet: "
            + ", ".join(unknown)
        )

    by_strategy: dict[str, list[PipelineStageDefinition]] = {}
    for stage in stages.values():
        by_strategy.setdefault(stage.strategy, []).append(stage)

    query_decompose = _single_stage(by_strategy, "query.research_decompose")
    query_passthrough = _single_stage(by_strategy, "query.passthrough")
    if query_decompose and query_passthrough:
        raise ValueError("Research supports one query-transform stage, not both.")
    query_stage = query_decompose or query_passthrough

    semantic = _single_stage(by_strategy, "retrieve.chroma_similarity")
    lexical = _single_stage(by_strategy, "retrieve.lexical_bm25")
    if not semantic and not lexical:
        raise ValueError("Research pipelines need semantic and/or lexical candidate generation.")

    normalize = _single_stage(by_strategy, "normalize.collection_relevance")
    fusion = _single_stage(by_strategy, "fusion.rrf")
    cross_encoder = _single_stage(by_strategy, "rerank.cross_encoder")
    lexical_rerank = _single_stage(by_strategy, "rerank.lexical_fallback")
    top_k_stages = by_strategy.get("select.top_k", [])
    provenance = _single_stage(by_strategy, "validate.provenance")
    context_pack = _single_stage(by_strategy, "pack.evidence_context")
    generation = _single_stage(by_strategy, "llm.generate_answer")
    citation_binding = _single_stage(
        by_strategy,
        "validate.citation_binding",
    )
    evaluation = _single_stage(by_strategy, "llm.grade_rag")

    if provenance is None:
        raise ValueError(
            "Research pipelines must include the deterministic provenance gate."
        )
    if context_pack is None:
        raise ValueError("Research pipelines must include an evidence context packer.")
    if generation is None:
        raise ValueError("Research pipelines must include final answer generation.")
    if citation_binding is None:
        raise ValueError(
            "Research pipelines must include deterministic citation binding."
        )

    enabled_entries = [
        stage_id
        for stage_id in pipeline.entry_stage_ids
        if stage_id in stages
    ]
    if query_stage:
        if enabled_entries != [query_stage.id]:
            raise ValueError(
                "Research pipelines with a query-transform stage must use that "
                "stage as the single enabled entry point."
            )
        for retrieval_stage in (semantic, lexical):
            if retrieval_stage and not _reachable(
                stages,
                query_stage.id,
                retrieval_stage.id,
            ):
                raise ValueError(
                    f"Research query stage {query_stage.id!r} must feed "
                    f"retrieval stage {retrieval_stage.id!r}."
                )
    else:
        expected_entries = {
            stage.id
            for stage in (semantic, lexical)
            if stage is not None
        }
        if set(enabled_entries) != expected_entries:
            raise ValueError(
                "Research pipelines without a query transform must use their "
                "retrieval stages as entry points."
            )

    mmr_stages = by_strategy.get("select.mmr", [])
    if len(mmr_stages) > 2:
        raise ValueError("Research supports at most one retrieval MMR and one diversity MMR stage.")

    pre_fusion_mmr: PipelineStageDefinition | None = None
    post_mmr: PipelineStageDefinition | None = None
    for mmr in mmr_stages:
        if fusion and _reachable(stages, mmr.id, fusion.id):
            if semantic is None or not _reachable(stages, semantic.id, mmr.id):
                raise ValueError(
                    "Pre-fusion Research MMR must be fed by semantic retrieval."
                )
            if pre_fusion_mmr is not None:
                raise ValueError("Research supports only one pre-fusion MMR stage.")
            pre_fusion_mmr = mmr
        elif cross_encoder and _reachable(stages, cross_encoder.id, mmr.id):
            if post_mmr is not None:
                raise ValueError("Research supports only one post-rerank MMR stage.")
            post_mmr = mmr
        else:
            raise ValueError(
                "Research MMR must be connected before rank fusion or after reranking."
            )

    source_aware = _single_stage(by_strategy, "select.source_diversity")
    if source_aware and not cross_encoder:
        raise ValueError("Source-aware Research diversity requires a reranking stage.")
    if source_aware and cross_encoder and not _reachable(stages, cross_encoder.id, source_aware.id):
        raise ValueError("Source-aware Research diversity must run after reranking.")
    if source_aware and post_mmr:
        raise ValueError("Research supports one post-rerank diversity strategy at a time.")

    if semantic and lexical:
        if not fusion:
            raise ValueError(
                "Parallel semantic and lexical Research retrieval requires a fusion stage."
            )
        _require_normal_path(
            stages,
            semantic,
            fusion,
            "Semantic Research retrieval must feed the configured fusion stage.",
        )
        _require_normal_path(
            stages,
            lexical,
            fusion,
            "Lexical Research retrieval must feed the configured fusion stage.",
        )

    if normalize:
        if not semantic:
            raise ValueError("Collection relevance normalization requires semantic retrieval.")
        _require_normal_path(
            stages,
            semantic,
            normalize,
            "Collection relevance normalization must follow semantic retrieval.",
        )

    primary_rerank = cross_encoder or (
        lexical_rerank
        if lexical_rerank
        and not any(
            lexical_rerank.id
            in {
                stage.on_empty,
                stage.on_unavailable,
                stage.on_timeout,
                stage.on_error,
            }
            for stage in stages.values()
        )
        else None
    )

    upstream = fusion or semantic or lexical
    if primary_rerank:
        _require_normal_path(
            stages,
            upstream,
            primary_rerank,
            "The configured Research reranker must follow candidate retrieval/fusion.",
        )
        final_rank_stage = source_aware or post_mmr or primary_rerank
    else:
        final_rank_stage = source_aware or post_mmr or upstream

    _require_normal_path(
        stages,
        final_rank_stage,
        provenance,
        "Research ranking/selection must feed the deterministic provenance gate.",
    )
    _require_normal_path(
        stages,
        provenance,
        context_pack,
        "The Research provenance gate must feed the evidence context packer.",
    )
    _require_normal_path(
        stages,
        context_pack,
        generation,
        "The Research evidence context packer must feed answer generation.",
    )
    _require_normal_path(
        stages,
        generation,
        citation_binding,
        "Research answer generation must feed deterministic citation binding.",
    )
    if evaluation and not _reachable(stages, citation_binding.id, evaluation.id):
        raise ValueError("Research evaluation must follow citation binding.")

    fallbacks: dict[str, tuple[str, str]] = {}
    fallback_target_ids: set[str] = set()
    if cross_encoder:
        fallback_values = {
            "empty": cross_encoder.on_empty,
            "unavailable": cross_encoder.on_unavailable,
            "timeout": cross_encoder.on_timeout,
            "error": cross_encoder.on_error,
        }
        fallback_target_ids = {
            target_id
            for target_id in fallback_values.values()
            if target_id
        }
        if (
            lexical_rerank
            and lexical_rerank.id not in fallback_target_ids
        ):
            raise ValueError(
                "When a CrossEncoder is configured, the lexical reranker is "
                "supported only as an explicit fallback target."
            )
        for fallback_stage in [*top_k_stages, *([lexical_rerank] if lexical_rerank else [])]:
            if fallback_stage.id not in fallback_target_ids:
                if fallback_stage.strategy == "select.top_k":
                    raise ValueError(
                        "Research top-K stages are currently supported only as "
                        "explicit reranker fallback targets."
                    )
                continue
            normal_predecessors = [
                stage.id
                for stage in stages.values()
                if fallback_stage.id in stage.next
            ]
            if normal_predecessors:
                raise ValueError(
                    f"Research fallback stage {fallback_stage.id!r} cannot also "
                    "be on the normal execution path."
                )
        for condition, target_id in fallback_values.items():
            if not target_id:
                continue
            target = stages.get(target_id)
            if target is None:
                continue
            if target.strategy not in {"rerank.lexical_fallback", "select.top_k"}:
                raise ValueError(
                    "Research reranker fallbacks currently support lexical fallback "
                    "or deterministic top-K selection."
                )
            fallbacks[condition] = (target.id, target.strategy)
            _require_normal_path(
                stages,
                target,
                provenance,
                f"Research {condition} fallback must rejoin before the provenance gate.",
            )

    if source_aware:
        diversity_mode: ResearchDiversity = "source_aware"
        diversity_stage = source_aware
    elif post_mmr:
        diversity_mode = "mmr"
        diversity_stage = post_mmr
    else:
        diversity_mode = "none"
        diversity_stage = None

    return ResearchPipelinePlan(
        pipeline_id=pipeline.pipeline_id,
        pipeline_version=pipeline.version,
        pipeline_hash=pipeline_hash(pipeline),
        query_stage_id=query_stage.id if query_stage else None,
        query_decomposition_available=query_decompose is not None,
        semantic_stage_id=semantic.id if semantic else None,
        lexical_stage_id=lexical.id if lexical else None,
        normalization_stage_id=normalize.id if normalize else None,
        pre_fusion_mmr_stage_id=pre_fusion_mmr.id if pre_fusion_mmr else None,
        fusion_stage_id=fusion.id if fusion else None,
        rerank_stage_id=primary_rerank.id if primary_rerank else None,
        rerank_strategy=primary_rerank.strategy if primary_rerank else None,
        lexical_rerank_stage_id=lexical_rerank.id if lexical_rerank else None,
        rerank_fallbacks=fallbacks,
        post_rerank_diversity=diversity_mode,
        diversity_stage_id=diversity_stage.id if diversity_stage else None,
        provenance_stage_id=provenance.id,
        context_pack_stage_id=context_pack.id,
        generation_stage_id=generation.id,
        citation_binding_stage_id=citation_binding.id,
        evaluation_stage_id=evaluation.id if evaluation else None,
        stage_configs={
            stage.id: dict(stage.config)
            for stage in stages.values()
        },
    )
