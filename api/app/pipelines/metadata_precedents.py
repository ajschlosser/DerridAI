# Copyright 2026 Aaron John Schlosser, PhD.
"""Executable contract for metadata-precedent retrieval pipelines.

The metadata schema remains authoritative for field-level eligibility, similarity
floors, positive/correction quotas, and analogy fields. This adapter owns only
the computational choices that are appropriate to version independently:
candidate depth, hybrid score weights, optional cross-encoder settings, MMR
diversity, and the final prompt-packet budget.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import PipelineDefinition, PipelineStageDefinition
from .registry import reject_unhonoured_config


@dataclass(frozen=True, slots=True)
class MetadataPrecedentPipelinePlan:
    retrieve_stage_id: str
    scope_stage_id: str
    hybrid_stage_id: str
    quotas_stage_id: str
    mmr_stage_id: str
    pack_stage_id: str
    lexical_fallback_stage_id: str | None = None
    rerank_stage_id: str | None = None
    fetch_k: int | None = None
    semantic_weight: float = 0.8
    lexical_weight: float = 0.2
    cross_encoder_top_k: int | None = None
    cross_encoder_model: str | None = None
    cross_encoder_timeout_seconds: float | None = None
    mmr_lambda: float = 0.72
    packet_char_budget: int | None = None


def _enabled_by_strategy(
    pipeline: PipelineDefinition,
) -> dict[str, list[PipelineStageDefinition]]:
    out: dict[str, list[PipelineStageDefinition]] = {}
    for stage in pipeline.stages:
        if stage.enabled:
            out.setdefault(stage.strategy, []).append(stage)
    return out


def _one(
    by_strategy: dict[str, list[PipelineStageDefinition]],
    strategy: str,
    *,
    required: bool = False,
) -> PipelineStageDefinition | None:
    stages = by_strategy.get(strategy) or []
    if len(stages) > 1:
        raise ValueError(
            f"Metadata-precedent adapter supports at most one {strategy!r} stage."
        )
    if required and not stages:
        raise ValueError(
            f"Metadata-precedent adapter requires a {strategy!r} stage."
        )
    return stages[0] if stages else None


def _require_next(stage: PipelineStageDefinition, target: str) -> None:
    if target not in stage.next:
        raise ValueError(
            f"Metadata-precedent stage {stage.id!r} must route next to {target!r}."
        )


SUPPORTED_STRATEGIES = frozenset(
    {
        "retrieve.metadata_exemplars",
        "filter.metadata_scope",
        "fusion.metadata_hybrid",
        "rerank.cross_encoder",
        "select.metadata_quotas",
        "select.mmr",
        "pack.metadata_precedents",
        "fallback.metadata_precedents_lexical",
    }
)


def compile_metadata_precedent_pipeline(
    pipeline: PipelineDefinition,
) -> MetadataPrecedentPipelinePlan:
    """Compile the bounded graph supported by progressive metadata retrieval."""

    if pipeline.purpose != "metadata_precedents":
        raise ValueError(
            "Metadata-precedent adapter can only compile metadata_precedents pipelines."
        )

    reject_unhonoured_config(pipeline, "metadata-precedent")

    enabled = [stage for stage in pipeline.stages if stage.enabled]
    unsupported = sorted({stage.strategy for stage in enabled} - SUPPORTED_STRATEGIES)
    if unsupported:
        raise ValueError(
            "Metadata-precedent adapter does not implement strategy stage(s): "
            + ", ".join(unsupported)
        )

    by_strategy = _enabled_by_strategy(pipeline)
    retrieve = _one(by_strategy, "retrieve.metadata_exemplars", required=True)
    scope = _one(by_strategy, "filter.metadata_scope", required=True)
    hybrid = _one(by_strategy, "fusion.metadata_hybrid", required=True)
    rerank = _one(by_strategy, "rerank.cross_encoder")
    quotas = _one(by_strategy, "select.metadata_quotas", required=True)
    mmr = _one(by_strategy, "select.mmr", required=True)
    pack = _one(by_strategy, "pack.metadata_precedents", required=True)
    lexical_fallback = _one(
        by_strategy,
        "fallback.metadata_precedents_lexical",
    )
    assert retrieve is not None
    assert scope is not None
    assert hybrid is not None
    assert quotas is not None
    assert mmr is not None
    assert pack is not None

    if pipeline.entry_stage_ids != [retrieve.id]:
        raise ValueError(
            "Metadata-precedent retrieval stage must be the sole pipeline entry."
        )

    fallback_targets = {
        edge: getattr(retrieve, edge)
        for edge in ("on_unavailable", "on_timeout", "on_error")
    }
    configured_fallbacks = {target for target in fallback_targets.values() if target}
    if lexical_fallback is None:
        if configured_fallbacks:
            raise ValueError(
                "Metadata retrieval defines fallback edges but has no registered "
                "lexical fallback stage."
            )
    else:
        if configured_fallbacks != {lexical_fallback.id}:
            raise ValueError(
                "Metadata retrieval unavailable/timeout/error fallbacks must all "
                "target the explicit lexical fallback stage."
            )
        if lexical_fallback.edge_targets():
            raise ValueError(
                "Metadata lexical fallback is terminal because it returns the "
                "already bounded precedent packet."
            )

    _require_next(retrieve, scope.id)
    _require_next(scope, hybrid.id)
    if rerank is not None:
        _require_next(hybrid, rerank.id)
        _require_next(rerank, quotas.id)
        for edge in ("on_unavailable", "on_timeout", "on_error"):
            target = getattr(rerank, edge)
            if target != quotas.id:
                raise ValueError(
                    f"Metadata-precedent cross-encoder {edge} must route to "
                    f"{quotas.id!r}; the runtime falls open only through an "
                    "explicitly declared fallback."
                )
    else:
        _require_next(hybrid, quotas.id)

    _require_next(quotas, mmr.id)
    _require_next(mmr, pack.id)
    if pack.edge_targets():
        raise ValueError(
            "Metadata-precedent packet stage must be terminal in the current adapter."
        )

    semantic_weight = float(hybrid.config.get("semantic_weight", 0.8))
    lexical_weight = float(hybrid.config.get("lexical_weight", 0.2))
    total_weight = semantic_weight + lexical_weight
    if total_weight <= 0:
        raise ValueError(
            "Metadata hybrid semantic_weight and lexical_weight cannot both be zero."
        )
    semantic_weight /= total_weight
    lexical_weight /= total_weight

    return MetadataPrecedentPipelinePlan(
        retrieve_stage_id=retrieve.id,
        scope_stage_id=scope.id,
        hybrid_stage_id=hybrid.id,
        rerank_stage_id=rerank.id if rerank else None,
        quotas_stage_id=quotas.id,
        mmr_stage_id=mmr.id,
        pack_stage_id=pack.id,
        lexical_fallback_stage_id=(
            lexical_fallback.id if lexical_fallback is not None else None
        ),
        fetch_k=(
            int(retrieve.config["fetch_k"])
            if "fetch_k" in retrieve.config
            else None
        ),
        semantic_weight=semantic_weight,
        lexical_weight=lexical_weight,
        cross_encoder_top_k=(
            int(rerank.config["top_k"])
            if rerank is not None and "top_k" in rerank.config
            else None
        ),
        cross_encoder_model=(
            str(rerank.config["model"])
            if rerank is not None and rerank.config.get("model")
            else None
        ),
        cross_encoder_timeout_seconds=(
            float(rerank.config["timeout_seconds"])
            if rerank is not None and "timeout_seconds" in rerank.config
            else None
        ),
        mmr_lambda=float(mmr.config.get("lambda_mult", 0.72)),
        packet_char_budget=(
            int(pack.config["char_budget"])
            if "char_budget" in pack.config
            else None
        ),
    )
