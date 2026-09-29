# Copyright 2026 Aaron John Schlosser, PhD.
"""Translate completed Research results into durable pipeline execution traces."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from .models import PipelineDefinition, PipelineRunTrace, PipelineStageTrace
from .registry import strategy_registry


def _runtime_stage_map(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("name") or ""): item
        for item in result.get("stages") or []
        if isinstance(item, dict) and item.get("name")
    }


def _seconds_ms(item: dict[str, Any] | None) -> int | None:
    if not item:
        return None
    try:
        return max(0, int(round(float(item.get("seconds") or 0.0) * 1000)))
    except (TypeError, ValueError):
        return None


def _stage_status(
    *,
    strategy: str,
    result: dict[str, Any],
    auto_grade_ran: bool,
) -> tuple[str, str | None]:
    retrieval = result.get("retrieval") if isinstance(result.get("retrieval"), dict) else {}
    effective_search = set(retrieval.get("search_types") or [])
    reranker = str(retrieval.get("reranker") or "none")
    requested_reranker = str(retrieval.get("requested_reranker") or reranker)
    diversity = str(retrieval.get("post_rerank_diversity") or "none")
    skip_retrieval = bool(retrieval.get("skip_retrieval"))

    if strategy == "query.research_decompose":
        return ("completed", None) if retrieval.get("query_decomposition") else ("skipped", None)
    if strategy == "retrieve.chroma_similarity":
        return (
            ("completed", None)
            if not skip_retrieval and bool({"similarity", "mmr"} & effective_search)
            else ("skipped", None)
        )
    if strategy == "retrieve.lexical_bm25":
        return (
            ("completed", None)
            if not skip_retrieval and "lexical" in effective_search
            else ("skipped", None)
        )
    if strategy == "normalize.collection_relevance":
        return (
            ("completed", None)
            if not skip_retrieval and bool({"similarity", "mmr"} & effective_search)
            else ("skipped", None)
        )
    if strategy == "fusion.rrf":
        return ("completed", None) if not skip_retrieval else ("skipped", None)
    if strategy == "rerank.cross_encoder":
        if reranker == "cross_encoder":
            return "completed", None
        if requested_reranker == "cross_encoder":
            detail = next(
                (
                    str(item)
                    for item in result.get("warnings") or []
                    if "cross-encoder" in str(item).casefold()
                ),
                "Cross-encoder was unavailable and the configured fallback path ran.",
            )
            return "unavailable", detail
        return "skipped", None
    if strategy == "rerank.lexical_fallback":
        if requested_reranker == "cross_encoder" and reranker == "lexical":
            return "completed", "Used because the cross-encoder was unavailable."
        if requested_reranker == "lexical" and reranker == "lexical":
            return "completed", None
        return "skipped", None
    if strategy == "select.mmr":
        return (
            ("completed", None)
            if ("mmr" in effective_search or diversity == "mmr")
            else ("skipped", None)
        )
    if strategy == "select.source_diversity":
        return ("completed", None) if diversity == "source_aware" else ("skipped", None)
    if strategy in {"validate.provenance", "pack.evidence_context", "llm.generate_answer"}:
        return "completed", None
    if strategy == "llm.grade_rag":
        return ("completed", None) if auto_grade_ran else ("skipped", None)
    return "completed", None


def _trace_timing(
    strategy: str,
    runtime: dict[str, dict[str, Any]],
) -> tuple[int | None, dict[str, Any]]:
    """Map feature-level runtime timers onto declarative strategy stages.

    Retrieval currently times the parallel candidate-generation/fusion block as a
    unit. We do not copy that aggregate duration onto every branch because doing
    so would imply false per-strategy precision. Those stages therefore expose
    counts/parameters while only stage boundaries with dedicated timers receive
    elapsed_ms.
    """

    if strategy == "query.research_decompose":
        item = runtime.get("query_metadata")
    elif strategy in {"rerank.cross_encoder", "rerank.lexical_fallback"}:
        item = runtime.get("rerank")
    elif strategy in {"select.source_diversity"}:
        item = runtime.get("diversity")
    elif strategy in {"validate.provenance", "pack.evidence_context"}:
        item = runtime.get("retrieval_context")
    elif strategy == "llm.generate_answer":
        item = runtime.get("generation")
    else:
        item = None
    return _seconds_ms(item), dict((item or {}).get("detail") or {})


def research_trace_from_result(
    *,
    run_id: str,
    owner: str | None,
    pipeline: PipelineDefinition,
    result: dict[str, Any],
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    auto_grade_ran: bool = False,
) -> PipelineRunTrace:
    """Build a safe, source-text-free trace for one completed Research run."""

    finished = finished_at or datetime.now(UTC)
    elapsed_seconds = float(result.get("elapsed_seconds") or 0.0)
    started = started_at or (finished - timedelta(seconds=max(0.0, elapsed_seconds)))
    runtime = _runtime_stage_map(result)
    retrieval = result.get("retrieval") if isinstance(result.get("retrieval"), dict) else {}
    pipeline_meta = result.get("pipeline") if isinstance(result.get("pipeline"), dict) else {}
    resolved_hash = str(pipeline_meta.get("pipeline_hash") or "")

    traces: list[PipelineStageTrace] = []
    for stage in pipeline.stages:
        spec = strategy_registry.get(stage.strategy)
        status, fallback_reason = _stage_status(
            strategy=stage.strategy,
            result=result,
            auto_grade_ran=auto_grade_ran,
        )
        elapsed_ms, detail = _trace_timing(stage.strategy, runtime)

        input_count: int | None = None
        output_count: int | None = None
        score_summary: dict[str, Any] = {}
        collection: str | None = None
        provider: str | None = None
        model: str | None = None

        if stage.strategy in {
            "retrieve.chroma_similarity",
            "retrieve.lexical_bm25",
            "normalize.collection_relevance",
            "fusion.rrf",
            "select.mmr",
        }:
            input_count = int(retrieval.get("raw_count") or 0)
            output_count = int(retrieval.get("deduplicated_count") or 0)
            collections = result.get("collections") or []
            if len(collections) == 1:
                collection = str(collections[0])
            score_summary = {
                "distance_metric_normalized": stage.strategy
                in {"retrieve.chroma_similarity", "normalize.collection_relevance"},
            }
        elif stage.strategy in {"rerank.cross_encoder", "rerank.lexical_fallback"}:
            input_count = int(retrieval.get("deduplicated_count") or 0)
            output_count = int(retrieval.get("reranked_count") or 0)
            telemetry = detail.get("reranker_telemetry")
            if isinstance(telemetry, dict):
                score_summary = {
                    key: telemetry[key]
                    for key in ("candidate_count", "reranked_count", "timing_ms")
                    if key in telemetry
                }
            if stage.strategy == "rerank.cross_encoder":
                model = str(detail.get("cross_encoder_model") or "") or None
                provider = "sentence-transformers"
        elif stage.strategy in {"validate.provenance", "pack.evidence_context"}:
            input_count = int(retrieval.get("reranked_count") or 0)
            output_count = int(detail.get("evidence_count") or 0)
        elif stage.strategy == "llm.generate_answer":
            output_count = 1
            provider = str(result.get("provider") or "") or None
            model = str(result.get("model") or "") or None
        elif stage.strategy == "llm.grade_rag":
            output_count = 1 if auto_grade_ran else 0

        traces.append(
            PipelineStageTrace(
                stage_id=stage.id,
                strategy_id=stage.strategy,
                strategy_version=spec.version if spec else 1,
                status=status,
                elapsed_ms=elapsed_ms,
                input_count=input_count,
                output_count=output_count,
                parameters=dict(stage.config),
                provider=provider,
                model=model,
                collection=collection,
                fallback_reason=fallback_reason,
                score_summary=score_summary,
            )
        )

    return PipelineRunTrace(
        run_id=str(run_id),
        feature="research",
        pipeline_id=pipeline.pipeline_id,
        pipeline_version=pipeline.version,
        resolved_pipeline=pipeline.model_dump(mode="json"),
        resolved_hash=resolved_hash,
        owner=owner,
        status="completed",
        started_at=started,
        finished_at=finished,
        total_elapsed_ms=max(0, int(round(elapsed_seconds * 1000))),
        warnings=[str(item) for item in result.get("warnings") or []],
        stages=traces,
    )
