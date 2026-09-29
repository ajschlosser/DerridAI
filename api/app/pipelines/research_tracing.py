# Copyright 2026 Aaron John Schlosser, PhD.
"""Research-specific adapter from runtime results to the common trace contract.

The trace is deliberately definition-bound: every persisted stage_id comes from
the immutable resolved pipeline snapshot. Operational helpers such as selected
user evidence or advisory memory remain in their purpose-specific result data
until they are modeled as first-class pipeline stages.
"""

from __future__ import annotations

from typing import Any

from ..models import RAGRunRequest
from .models import PipelineDefinition, PipelineRunTrace, PipelineStageTrace
from .research import compile_research_pipeline
from .trace_safety import (
    MAX_TRACE_STRING,
    parse_trace_datetime,
    sanitize_trace_value,
    trace_stage,
)


def _status_for_fallback(condition: str | None) -> str:
    if condition == "timeout":
        return "timed_out"
    if condition == "unavailable":
        return "unavailable"
    return "failed"


def build_research_trace(
    *,
    run_id: str,
    owner: str | None,
    request: RAGRunRequest,
    result: dict[str, Any],
    started_at: Any,
    finished_at: Any,
    status: str = "completed",
) -> PipelineRunTrace:
    """Translate an executed Research result into the common trace contract."""

    pipeline_info = (
        result.get("pipeline")
        if isinstance(result.get("pipeline"), dict)
        else {}
    )
    resolved_pipeline = (
        pipeline_info.get("resolved_pipeline")
        if isinstance(pipeline_info.get("resolved_pipeline"), dict)
        else {}
    )
    pipeline = PipelineDefinition.model_validate(resolved_pipeline)
    plan = compile_research_pipeline(pipeline)

    pipeline_id = str(
        pipeline_info.get("pipeline_id")
        or request.pipeline_id
        or pipeline.pipeline_id
    )
    pipeline_version = int(
        pipeline_info.get("pipeline_version")
        or request.pipeline_version
        or pipeline.version
    )
    resolved_hash = str(pipeline_info.get("pipeline_hash") or plan.pipeline_hash)

    stage_payloads = {
        str(item.get("name") or ""): item
        for item in (result.get("stages") or [])
        if isinstance(item, dict)
    }
    retrieval = (
        result.get("retrieval")
        if isinstance(result.get("retrieval"), dict)
        else {}
    )
    raw_count = int(retrieval.get("raw_count") or 0)
    deduplicated_count = int(retrieval.get("deduplicated_count") or 0)
    reranked_count = int(retrieval.get("reranked_count") or 0)
    search_types = [str(item) for item in retrieval.get("search_types") or []]
    collections = [str(item) for item in result.get("collections") or []]
    collection_label = ", ".join(collections[:6]) or None

    resolved_stage_rows = {
        str(item.get("id") or ""): item
        for item in resolved_pipeline.get("stages") or []
        if isinstance(item, dict) and str(item.get("id") or "")
    }

    def strategy_for(stage_id: str) -> str:
        row = resolved_stage_rows.get(stage_id) or {}
        strategy = str(row.get("strategy") or "")
        if not strategy:
            raise ValueError(
                f"Resolved Research trace stage {stage_id!r} has no strategy."
            )
        return strategy

    trace_stages: list[PipelineStageTrace] = []
    retrieval_skipped = bool(retrieval.get("skip_retrieval"))
    retrieval_stage = stage_payloads.get("retrieval") or {}
    retrieval_seconds = retrieval_stage.get("seconds")
    semantic_executed = (
        not retrieval_skipped
        and plan.semantic_stage_id is not None
        and bool({"similarity", "mmr"} & set(search_types))
    )
    lexical_executed = (
        not retrieval_skipped
        and plan.lexical_stage_id is not None
        and "lexical" in search_types
    )

    if plan.query_stage_id:
        query_stage = stage_payloads.get("query_metadata") or {}
        query_executed = (
            not plan.query_decomposition_available
            or bool(retrieval.get("query_decomposition"))
        )
        trace_stages.append(
            trace_stage(
                plan.query_stage_id,
                strategy_for(plan.query_stage_id),
                elapsed_seconds=(
                    query_stage.get("seconds") if query_executed else None
                ),
                input_count=1,
                output_count=1 if query_executed else 0,
                provider=(
                    result.get("provider")
                    if query_executed and plan.query_decomposition_available
                    else None
                ),
                model=(
                    result.get("model")
                    if query_executed and plan.query_decomposition_available
                    else None
                ),
                parameters={
                    "requested": retrieval.get("requested_query_decomposition"),
                    "effective": retrieval.get("query_decomposition"),
                    "num_predict": retrieval.get(
                        "query_decomposition_num_predict"
                    ),
                },
                status="completed" if query_executed else "skipped",
            )
        )

    if plan.semantic_stage_id:
        trace_stages.append(
            trace_stage(
                plan.semantic_stage_id,
                strategy_for(plan.semantic_stage_id),
                elapsed_seconds=(
                    retrieval_seconds
                    if semantic_executed
                    and not lexical_executed
                    and plan.fusion_stage_id is None
                    else None
                ),
                output_count=raw_count if semantic_executed else 0,
                collection=collection_label,
                parameters={
                    "k": retrieval.get("k"),
                    "fetch_k": retrieval.get(
                        "semantic_fetch_k",
                        retrieval.get("fetch_k"),
                    ),
                },
                status="completed" if semantic_executed else "skipped",
            )
        )

    if plan.normalization_stage_id:
        trace_stages.append(
            trace_stage(
                plan.normalization_stage_id,
                strategy_for(plan.normalization_stage_id),
                input_count=raw_count if semantic_executed else 0,
                output_count=raw_count if semantic_executed else 0,
                collection=collection_label,
                score_summary={"metric_aware": semantic_executed},
                status="completed" if semantic_executed else "skipped",
            )
        )

    if plan.lexical_stage_id:
        trace_stages.append(
            trace_stage(
                plan.lexical_stage_id,
                strategy_for(plan.lexical_stage_id),
                elapsed_seconds=(
                    retrieval_seconds
                    if lexical_executed
                    and not semantic_executed
                    and plan.fusion_stage_id is None
                    else None
                ),
                output_count=raw_count if lexical_executed else 0,
                collection=collection_label,
                parameters={
                    "k": retrieval.get("k"),
                    "fetch_k": retrieval.get(
                        "lexical_fetch_k",
                        retrieval.get("fetch_k"),
                    ),
                },
                status="completed" if lexical_executed else "skipped",
            )
        )

    if plan.pre_fusion_mmr_stage_id:
        mmr_executed = not retrieval_skipped and "mmr" in search_types
        trace_stages.append(
            trace_stage(
                plan.pre_fusion_mmr_stage_id,
                strategy_for(plan.pre_fusion_mmr_stage_id),
                input_count=raw_count if mmr_executed else 0,
                output_count=raw_count if mmr_executed else 0,
                parameters={
                    "lambda_mult": retrieval.get(
                        "retrieval_mmr_lambda",
                        retrieval.get("lambda_mult"),
                    ),
                },
                status="completed" if mmr_executed else "skipped",
            )
        )

    if plan.fusion_stage_id:
        fusion_executed = (
            not retrieval_skipped and (semantic_executed or lexical_executed)
        )
        trace_stages.append(
            trace_stage(
                plan.fusion_stage_id,
                strategy_for(plan.fusion_stage_id),
                elapsed_seconds=retrieval_seconds if fusion_executed else None,
                input_count=raw_count if fusion_executed else 0,
                output_count=deduplicated_count if fusion_executed else 0,
                parameters={"rrf_k": retrieval.get("rrf_k")},
                status="completed" if fusion_executed else "skipped",
            )
        )

    rerank_stage = stage_payloads.get("rerank") or {}
    rerank_detail = (
        rerank_stage.get("detail")
        if isinstance(rerank_stage.get("detail"), dict)
        else {}
    )
    rerank_telemetry = (
        rerank_detail.get("reranker_telemetry")
        if isinstance(rerank_detail.get("reranker_telemetry"), dict)
        else {}
    )
    active_rerank_stage_id = str(
        rerank_detail.get("active_stage_id") or ""
    ) or None
    fallback_condition = str(
        rerank_detail.get("fallback_condition")
        or rerank_telemetry.get("fallback_condition")
        or ""
    ) or None
    if active_rerank_stage_id is None:
        telemetry_mode = str(rerank_telemetry.get("mode") or "")
        if telemetry_mode == "cross_encoder":
            active_rerank_stage_id = plan.rerank_stage_id
        elif telemetry_mode == "lexical_fallback":
            active_rerank_stage_id = plan.lexical_rerank_stage_id
        elif telemetry_mode == "top_k_fallback":
            active_rerank_stage_id = (
                str(rerank_telemetry.get("fallback_stage_id") or "") or None
            )
    requested_reranker = str(
        retrieval.get("requested_reranker")
        or rerank_detail.get("requested_mode")
        or "none"
    )
    effective_reranker = str(
        retrieval.get("reranker")
        or rerank_detail.get("mode")
        or "none"
    )

    if plan.rerank_stage_id:
        primary_active = active_rerank_stage_id == plan.rerank_stage_id
        primary_attempted = (
            plan.rerank_strategy == "rerank.cross_encoder"
            and requested_reranker == "cross_encoder"
        )
        primary_failed = primary_attempted and not primary_active
        if primary_failed:
            primary_status = _status_for_fallback(fallback_condition)
        elif primary_active:
            primary_status = "completed"
        else:
            primary_status = "skipped"
        trace_stages.append(
            trace_stage(
                plan.rerank_stage_id,
                strategy_for(plan.rerank_stage_id),
                elapsed_seconds=(
                    rerank_stage.get("seconds")
                    if primary_active
                    else (
                        float(rerank_telemetry.get("timing_ms")) / 1000
                        if primary_attempted
                        and rerank_telemetry.get("timing_ms") is not None
                        else None
                    )
                ),
                input_count=deduplicated_count if primary_attempted or primary_active else 0,
                output_count=(
                    int(rerank_detail.get("rerank_pool_count") or reranked_count)
                    if primary_active
                    else 0
                ),
                provider=(
                    "sentence-transformers"
                    if plan.rerank_strategy == "rerank.cross_encoder"
                    else None
                ),
                model=(
                    str(
                        rerank_detail.get("cross_encoder_model")
                        or request.cross_encoder_model
                        or ""
                    )
                    or None
                    if plan.rerank_strategy == "rerank.cross_encoder"
                    else None
                ),
                parameters={
                    "requested_reranker": requested_reranker,
                    "top_n": retrieval.get("rerank_top_n"),
                },
                fallback_reason=(
                    str(rerank_telemetry.get("fallback_reason") or "") or None
                    if primary_failed
                    else None
                ),
                status=primary_status,
                score_summary={
                    key: rerank_telemetry[key]
                    for key in ("candidate_count", "reranked_count", "timing_ms")
                    if key in rerank_telemetry
                },
            )
        )

    fallback_targets: dict[str, str] = {}
    for target_id, target_strategy in plan.rerank_fallbacks.values():
        fallback_targets[target_id] = target_strategy
    if (
        plan.lexical_rerank_stage_id
        and plan.lexical_rerank_stage_id != plan.rerank_stage_id
    ):
        fallback_targets.setdefault(
            plan.lexical_rerank_stage_id,
            strategy_for(plan.lexical_rerank_stage_id),
        )

    for stage_id, strategy_id in fallback_targets.items():
        active = active_rerank_stage_id == stage_id
        trace_stages.append(
            trace_stage(
                stage_id,
                strategy_id,
                elapsed_seconds=(
                    rerank_stage.get("seconds")
                    if active and requested_reranker != "cross_encoder"
                    else None
                ),
                input_count=deduplicated_count if active else 0,
                output_count=reranked_count if active else 0,
                parameters={
                    "top_n": retrieval.get("rerank_top_n"),
                    "fallback_from": (
                        plan.rerank_stage_id
                        if active and requested_reranker == "cross_encoder"
                        else None
                    ),
                    "fallback_condition": fallback_condition if active else None,
                },
                fallback_reason=(
                    str(rerank_telemetry.get("fallback_reason") or "") or None
                    if active and requested_reranker == "cross_encoder"
                    else None
                ),
                status="completed" if active else "skipped",
            )
        )

    if plan.diversity_stage_id:
        diversity_stage = stage_payloads.get("diversity") or {}
        detail = (
            diversity_stage.get("detail")
            if isinstance(diversity_stage.get("detail"), dict)
            else {}
        )
        executed = bool(diversity_stage)
        trace_stages.append(
            trace_stage(
                plan.diversity_stage_id,
                strategy_for(plan.diversity_stage_id),
                elapsed_seconds=(
                    diversity_stage.get("seconds") if executed else None
                ),
                input_count=int(detail.get("input_count") or 0),
                output_count=int(detail.get("output_count") or 0),
                parameters={
                    "lambda_mult": detail.get("lambda_mult"),
                    "limit": detail.get("limit"),
                },
                status="completed" if executed else "skipped",
            )
        )

    context_stage = stage_payloads.get("retrieval_context") or {}
    context_detail = (
        context_stage.get("detail")
        if isinstance(context_stage.get("detail"), dict)
        else {}
    )
    evidence_count = int(context_detail.get("evidence_count") or 0)

    trace_stages.append(
        trace_stage(
            plan.provenance_stage_id,
            strategy_for(plan.provenance_stage_id),
            input_count=reranked_count,
            output_count=evidence_count,
            warnings=[
                str(item)
                for item in result.get("warnings") or []
                if "provenance" in str(item).casefold()
            ],
        )
    )
    trace_stages.append(
        trace_stage(
            plan.context_pack_stage_id,
            strategy_for(plan.context_pack_stage_id),
            elapsed_seconds=context_stage.get("seconds"),
            input_count=evidence_count,
            output_count=evidence_count,
            parameters={
                "record_char_limit": retrieval.get("evidence_record_char_limit"),
                "total_char_limit": retrieval.get("evidence_total_char_limit"),
                "characters": context_detail.get("characters"),
            },
        )
    )

    generation_stage = stage_payloads.get("generation") or {}
    trace_stages.append(
        trace_stage(
            plan.generation_stage_id,
            strategy_for(plan.generation_stage_id),
            elapsed_seconds=generation_stage.get("seconds"),
            input_count=evidence_count,
            output_count=1,
            provider=str(result.get("provider") or "") or None,
            model=str(result.get("model") or "") or None,
        )
    )

    binding_stage = stage_payloads.get("bind_sources") or {}
    trace_stages.append(
        trace_stage(
            plan.citation_binding_stage_id,
            strategy_for(plan.citation_binding_stage_id),
            elapsed_seconds=binding_stage.get("seconds"),
            input_count=1,
            output_count=1,
            parameters={
                "enabled": bool(request.bind_citations),
                "include_works_cited": bool(request.include_works_cited),
            },
            status="completed" if request.bind_citations else "skipped",
        )
    )

    if plan.evaluation_stage_id:
        grade_stage = stage_payloads.get("auto_grade")
        if isinstance(grade_stage, dict):
            detail = (
                grade_stage.get("detail")
                if isinstance(grade_stage.get("detail"), dict)
                else {}
            )
            grade_failed = bool(result.get("auto_grade_error"))
            trace_stages.append(
                trace_stage(
                    plan.evaluation_stage_id,
                    strategy_for(plan.evaluation_stage_id),
                    elapsed_seconds=grade_stage.get("seconds"),
                    input_count=1,
                    output_count=0 if grade_failed else 1,
                    provider=(
                        str(
                            detail.get("provider")
                            or result.get("auto_grade_provider")
                            or ""
                        )
                        or None
                    ),
                    model=(
                        str(
                            detail.get("model")
                            or result.get("auto_grade_model")
                            or ""
                        )
                        or None
                    ),
                    fallback_reason=(
                        str(result.get("auto_grade_error") or "")[
                            :MAX_TRACE_STRING
                        ]
                        if grade_failed
                        else None
                    ),
                    status="failed" if grade_failed else "completed",
                )
            )
        else:
            trace_stages.append(
                trace_stage(
                    plan.evaluation_stage_id,
                    strategy_for(plan.evaluation_stage_id),
                    input_count=1,
                    output_count=0,
                    parameters={"optional": True},
                    status="skipped",
                )
            )

    defined_stage_ids = set(resolved_stage_rows)
    traced_stage_ids = {stage.stage_id for stage in trace_stages}
    if not traced_stage_ids <= defined_stage_ids:
        extras = sorted(traced_stage_ids - defined_stage_ids)
        raise ValueError(
            "Research trace contains stage IDs not present in the resolved "
            f"pipeline: {', '.join(extras)}"
        )

    finished = parse_trace_datetime(finished_at)
    started = parse_trace_datetime(started_at)
    total_elapsed = result.get("elapsed_seconds")
    return PipelineRunTrace(
        run_id=str(run_id),
        feature="research",
        pipeline_id=pipeline_id,
        pipeline_version=pipeline_version,
        resolved_pipeline=sanitize_trace_value(resolved_pipeline),
        resolved_hash=resolved_hash,
        owner=owner,
        status=status,
        started_at=started,
        finished_at=finished,
        total_elapsed_ms=(
            max(0, int(float(total_elapsed) * 1000))
            if total_elapsed is not None
            else max(0, int((finished - started).total_seconds() * 1000))
        ),
        warnings=[
            str(item)[:MAX_TRACE_STRING]
            for item in result.get("warnings") or []
        ],
        stages=trace_stages,
    )
