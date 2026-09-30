# Copyright 2026 Aaron John Schlosser, PhD.
"""Bounded executable adapters for Research advisory-memory pipelines.

Memory pipelines control retrieval mechanics only. Durable eligibility rules stay
outside the graph: prior responses must still satisfy the configured grade gate,
and claim memory still requires reviewer-validated claims with usable support
bindings. A custom pipeline therefore cannot turn unreviewed prose into trusted
memory; it can only change how eligible memory is searched and bounded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast

from .models import PipelineDefinition, PipelineRunTrace, PipelineStageDefinition
from .trace_safety import trace_stage

MemoryPurpose = Literal["claim_memory", "response_memory"]


@dataclass(frozen=True, slots=True)
class MemoryPipelinePlan:
    """Executable subset shared by claim- and response-memory pipelines."""

    purpose: MemoryPurpose
    retrieve_stage_id: str
    select_stage_id: str
    lexical_fallback_stage_id: str | None = None
    fetch_k: int = 1
    min_similarity: float = 0.5
    selection_limit: int = 1
    fallback_fetch_k: int = 1

    fallback_unavailable: str | None = None
    fallback_timeout: str | None = None
    fallback_error: str | None = None

    def fallback_for(self, failure_kind: str) -> str | None:
        """Return the configured fallback target for one classified failure."""

        return {
            "unavailable": self.fallback_unavailable,
            "timeout": self.fallback_timeout,
            "error": self.fallback_error,
        }.get(failure_kind)


def _enabled_by_strategy(
    pipeline: PipelineDefinition,
) -> dict[str, list[PipelineStageDefinition]]:
    out: dict[str, list[PipelineStageDefinition]] = {}
    for stage in pipeline.stages:
        if stage.enabled:
            out.setdefault(stage.strategy, []).append(stage)
    return out


_SEMANTIC_STRATEGIES = {
    "claim_memory": "retrieve.claim_memory",
    "response_memory": "retrieve.response_memory",
}


def supported_strategies(purpose: str) -> frozenset[str]:
    """Strategies the memory adapter runs for one memory purpose."""

    return frozenset(
        {_SEMANTIC_STRATEGIES[purpose], "retrieve.memory_lexical_fallback", "select.top_k"}
    )


def _one(
    by_strategy: dict[str, list[PipelineStageDefinition]],
    strategy: str,
    *,
    required: bool = False,
) -> PipelineStageDefinition | None:
    stages = by_strategy.get(strategy) or []
    if len(stages) > 1:
        raise ValueError(f"Memory adapter supports at most one {strategy!r} stage.")
    if required and not stages:
        raise ValueError(f"Memory adapter requires a {strategy!r} stage.")
    return stages[0] if stages else None


def compile_memory_pipeline(pipeline: PipelineDefinition) -> MemoryPipelinePlan:
    """Compile the small memory graph subset DerridAI can execute."""

    if pipeline.purpose not in {"claim_memory", "response_memory"}:
        raise ValueError("Memory adapter supports claim_memory and response_memory pipelines.")

    semantic_strategy = _SEMANTIC_STRATEGIES[pipeline.purpose]
    enabled = [stage for stage in pipeline.stages if stage.enabled]
    unsupported = sorted(
        {stage.strategy for stage in enabled} - supported_strategies(pipeline.purpose)
    )
    if unsupported:
        raise ValueError(
            "Memory adapter does not implement strategy stage(s): "
            + ", ".join(unsupported)
        )

    by_strategy = _enabled_by_strategy(pipeline)
    retrieve = _one(by_strategy, semantic_strategy, required=True)
    lexical = _one(by_strategy, "retrieve.memory_lexical_fallback")
    select = _one(by_strategy, "select.top_k", required=True)
    assert retrieve is not None and select is not None

    if pipeline.entry_stage_ids != [retrieve.id]:
        raise ValueError("Memory semantic retrieval must be the sole pipeline entry stage.")
    if retrieve.next != [select.id]:
        raise ValueError(
            f"Memory retrieval stage {retrieve.id!r} must route normal results "
            f"directly to {select.id!r}."
        )
    if select.edge_targets():
        raise ValueError("Memory top-K selection must be terminal.")

    fallback_targets = {
        edge: getattr(retrieve, edge)
        for edge in ("on_unavailable", "on_timeout", "on_error")
    }
    configured_targets = {target for target in fallback_targets.values() if target}
    if lexical is None:
        if configured_targets:
            raise ValueError(
                "Memory retrieval defines fallback edges but no lexical fallback stage."
            )
    else:
        if not configured_targets:
            raise ValueError(
                "Memory lexical fallback stage is unreachable; configure at least one "
                "retrieval failure edge to use it."
            )
        if configured_targets != {lexical.id}:
            raise ValueError(
                "Memory retrieval failure edges may target only the configured lexical "
                "fallback stage."
            )
        if lexical.next != [select.id]:
            raise ValueError(
                f"Memory lexical fallback {lexical.id!r} must rejoin at {select.id!r}."
            )
        if lexical.edge_targets() != [select.id]:
            raise ValueError(
                "Memory lexical fallback may only continue to the top-K selection stage."
            )

    fetch_k = int(retrieve.config.get("fetch_k", select.config.get("limit", 1)))
    selection_limit = int(select.config.get("limit", fetch_k))
    fallback_fetch_k = (
        int(lexical.config.get("fetch_k", selection_limit))
        if lexical is not None
        else selection_limit
    )
    min_similarity = float(retrieve.config.get("min_similarity", 0.5))

    return MemoryPipelinePlan(
        purpose=cast(MemoryPurpose, pipeline.purpose),
        retrieve_stage_id=retrieve.id,
        select_stage_id=select.id,
        lexical_fallback_stage_id=lexical.id if lexical else None,
        fetch_k=fetch_k,
        min_similarity=min_similarity,
        selection_limit=selection_limit,
        fallback_fetch_k=fallback_fetch_k,
        fallback_unavailable=fallback_targets["on_unavailable"],
        fallback_timeout=fallback_targets["on_timeout"],
        fallback_error=fallback_targets["on_error"],
    )


def classify_memory_failure(exc: Exception) -> str:
    """Map runtime failures onto the fallback vocabulary supported by graphs."""

    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return "unavailable"
    return "error"


def build_memory_trace(
    *,
    feature: MemoryPurpose,
    pipeline: PipelineDefinition,
    resolved_hash: str,
    run_id: str,
    started_at: datetime,
    finished_at: datetime,
    observations: dict[str, dict[str, Any]],
    owner: str | None = None,
) -> PipelineRunTrace:
    """Translate bounded memory telemetry into the shared pipeline trace model."""

    stages = []
    for stage in pipeline.stages:
        if not stage.enabled:
            continue
        observation = observations.get(stage.id) or {"status": "skipped"}
        stages.append(
            trace_stage(
                stage.id,
                stage.strategy,
                elapsed_seconds=observation.get("elapsed_seconds"),
                input_count=observation.get("input_count"),
                output_count=observation.get("output_count"),
                parameters=observation.get("parameters"),
                fallback_reason=observation.get("fallback_reason"),
                warnings=observation.get("warnings"),
                score_summary=observation.get("score_summary"),
                status=str(observation.get("status") or "completed"),
            )
        )

    return PipelineRunTrace(
        run_id=run_id,
        feature=feature,
        pipeline_id=pipeline.pipeline_id,
        pipeline_version=pipeline.version,
        resolved_pipeline=pipeline.model_dump(mode="json"),
        resolved_hash=resolved_hash,
        owner=owner,
        status="completed",
        started_at=started_at,
        finished_at=finished_at,
        total_elapsed_ms=max(0, int((finished_at - started_at).total_seconds() * 1000)),
        warnings=[
            warning
            for observation in observations.values()
            for warning in observation.get("warnings") or []
        ],
        stages=stages,
    )
