# Copyright 2026 Aaron John Schlosser, PhD.
"""Pipeline adapter for metadata pre-fill from reviewed precedents.

The pipeline owns the computational side of pre-fill: how many exemplars each
source span retrieves, how exemplar distance becomes a similarity, and which
advisory hints surface. It does not own whether a value may be pre-filled:
multi-record agreement, the pre-fill similarity bar, the rival margin, schema
validity, exemplar eligibility, and never overwriting reviewed or present values
stay domain policy in ``memory_prefill``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from .models import PipelineDefinition, PipelineRunTrace
from .registry import reject_unhonoured_config
from .service import pipeline_hash
from .trace_safety import trace_stage

PREFILL_FEATURE = "metadata_prefill"
PREFILL_PURPOSE = "metadata_prefill"
_RETRIEVE = "retrieve.metadata_exemplars"
_NORMALIZE = "normalize.collection_relevance"
_HINTS = "select.memory_hints"
SUPPORTED_STRATEGIES = frozenset({_RETRIEVE, _NORMALIZE, _HINTS})
# Pre-fill thresholds were calibrated against this conversion, so it is the
# only one the adapter accepts until a metric-aware alternative is calibrated.
NORMALIZATIONS = ("inverse_distance",)


@dataclass(frozen=True)
class PrefillPlan:
    pipeline: PipelineDefinition
    retrieve_stage_id: str
    normalize_stage_id: str
    hints_stage_id: str
    fetch_k: int
    normalization: str
    hint_limit: int
    hint_min_similarity: float

    def similarity(self, distance: Any) -> float:
        """Exemplar distance as similarity: ``1 / (1 + distance)``, floored at zero distance."""
        try:
            return 1.0 / (1.0 + max(0.0, float(distance)))
        except (TypeError, ValueError):
            return 0.0


def compile_prefill_pipeline(pipeline: PipelineDefinition) -> PrefillPlan:
    """Accept the retrieve → normalize → hint-selection chain pre-fill can execute."""

    if pipeline.purpose != PREFILL_PURPOSE:
        raise ValueError("Metadata pre-fill adapter can only compile metadata_prefill pipelines.")
    reject_unhonoured_config(pipeline, "metadata pre-fill")
    stages = [stage for stage in pipeline.stages if stage.enabled]
    unsupported = sorted({stage.strategy for stage in stages} - SUPPORTED_STRATEGIES)
    if unsupported:
        raise ValueError("Metadata pre-fill adapter does not implement strategy stage(s): " + ", ".join(unsupported))

    def single(strategy: str):
        matches = [stage for stage in stages if stage.strategy == strategy]
        if len(matches) != 1:
            raise ValueError(f"Metadata pre-fill requires exactly one {strategy!r} stage.")
        return matches[0]

    retrieve, normalize, hints = single(_RETRIEVE), single(_NORMALIZE), single(_HINTS)
    if pipeline.entry_stage_ids != [retrieve.id]:
        raise ValueError("Metadata pre-fill must start with exemplar retrieval.")
    if retrieve.next != [normalize.id] or normalize.next != [hints.id] or hints.next:
        raise ValueError("Metadata pre-fill runs retrieval, then normalization, then hint selection.")
    for stage in stages:
        if any(getattr(stage, edge) for edge in ("on_empty", "on_unavailable", "on_timeout", "on_error")):
            raise ValueError(
                "Metadata pre-fill has no fallback stages; an unavailable store or embedder is "
                "reported in the build summary and the build continues without pre-fill."
            )
    normalization = str(normalize.config.get("method", "inverse_distance"))
    if normalization not in NORMALIZATIONS:
        raise ValueError(f"Metadata pre-fill supports normalization method(s): {', '.join(NORMALIZATIONS)}.")
    return PrefillPlan(
        pipeline=pipeline,
        retrieve_stage_id=retrieve.id,
        normalize_stage_id=normalize.id,
        hints_stage_id=hints.id,
        fetch_k=int(retrieve.config.get("fetch_k", 8)),
        normalization=normalization,
        hint_limit=int(hints.config.get("limit", 3)),
        hint_min_similarity=float(hints.config.get("min_similarity", 0.72)),
    )


def resolve_prefill_plan() -> tuple[PrefillPlan, str]:
    from .manager import pipeline_manager

    resolved = pipeline_manager.resolve(PREFILL_FEATURE)
    pipeline = PipelineDefinition.model_validate(resolved["pipeline"])
    return compile_prefill_pipeline(pipeline), str(resolved.get("pipeline_hash") or pipeline_hash(pipeline))


def build_prefill_trace(
    plan: PrefillPlan,
    *,
    resolved_hash: str,
    started_at: datetime,
    finished_at: datetime,
    observations: dict[str, dict[str, Any]],
    status: Literal["completed", "failed"],
) -> PipelineRunTrace:
    """One trace per build. Only stages that ran appear, in execution order."""

    order = [plan.retrieve_stage_id, plan.normalize_stage_id, plan.hints_stage_id]
    strategies = {stage.id: stage.strategy for stage in plan.pipeline.stages}
    stages = [
        trace_stage(
            stage_id,
            strategies[stage_id],
            elapsed_seconds=observations[stage_id].get("elapsed_seconds"),
            input_count=observations[stage_id].get("input_count"),
            output_count=observations[stage_id].get("output_count"),
            parameters=observations[stage_id].get("parameters"),
            provider=observations[stage_id].get("provider"),
            model=observations[stage_id].get("model"),
            collection=observations[stage_id].get("collection"),
            fallback_reason=observations[stage_id].get("fallback_reason"),
            warnings=observations[stage_id].get("warnings"),
            score_summary=observations[stage_id].get("score_summary"),
            status=str(observations[stage_id].get("status") or "completed"),
        )
        for stage_id in order
        if stage_id in observations
    ]
    return PipelineRunTrace(
        run_id=str(uuid.uuid4()),
        feature=PREFILL_FEATURE,
        pipeline_id=plan.pipeline.pipeline_id,
        pipeline_version=plan.pipeline.version,
        resolved_pipeline=plan.pipeline.model_dump(mode="json"),
        resolved_hash=resolved_hash,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        total_elapsed_ms=max(0, int((finished_at - started_at).total_seconds() * 1000)),
        stages=stages,
    )
