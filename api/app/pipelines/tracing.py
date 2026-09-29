# Copyright 2026 Aaron John Schlosser, PhD.
"""Safe construction of persistent pipeline execution traces.

Feature code may contain prompts, source text, provider credentials, and other
material that must not leak into generic operational telemetry. This module
translates completed feature results into an intentionally narrow trace: stage
identity, counts, timings, models, collections, fallback reasons, and bounded
scalar configuration only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..models import RAGRunRequest
from .models import PipelineRunTrace, PipelineStageTrace
from .registry import strategy_registry

_SECRET_KEYS = {
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
}
_MAX_TRACE_STRING = 500


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value or "").strip()
    if not text:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def sanitize_trace_value(value: Any, *, key: str = "") -> Any:
    """Recursively remove secrets and bound generic telemetry values."""

    normalized_key = str(key or "").casefold()
    if any(secret in normalized_key for secret in _SECRET_KEYS):
        return "[redacted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:_MAX_TRACE_STRING]
    if isinstance(value, (list, tuple)):
        return [
            sanitize_trace_value(item)
            for item in list(value)[:100]
        ]
    if isinstance(value, dict):
        return {
            str(item_key)[:120]: sanitize_trace_value(item_value, key=str(item_key))
            for item_key, item_value in list(value.items())[:100]
        }
    return str(value)[:_MAX_TRACE_STRING]


def _stage(
    stage_id: str,
    strategy_id: str,
    *,
    elapsed_seconds: float | None = None,
    input_count: int | None = None,
    output_count: int | None = None,
    parameters: dict[str, Any] | None = None,
    provider: str | None = None,
    model: str | None = None,
    collection: str | None = None,
    fallback_reason: str | None = None,
    warnings: list[str] | None = None,
    score_summary: dict[str, Any] | None = None,
    status: str = "completed",
) -> PipelineStageTrace:
    spec = strategy_registry.require(strategy_id)
    return PipelineStageTrace(
        stage_id=stage_id,
        strategy_id=strategy_id,
        strategy_version=spec.version,
        status=status,  # type: ignore[arg-type]
        elapsed_ms=(
            max(0, int(float(elapsed_seconds) * 1000))
            if elapsed_seconds is not None
            else None
        ),
        input_count=input_count,
        output_count=output_count,
        parameters=sanitize_trace_value(parameters or {}),
        provider=provider,
        model=model,
        collection=collection,
        fallback_reason=fallback_reason,
        warnings=[str(item)[:_MAX_TRACE_STRING] for item in (warnings or [])],
        score_summary=sanitize_trace_value(score_summary or {}),
    )


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

    pipeline_info = result.get("pipeline") if isinstance(result.get("pipeline"), dict) else {}
    resolved_pipeline = (
        pipeline_info.get("resolved_pipeline")
        if isinstance(pipeline_info.get("resolved_pipeline"), dict)
        else {}
    )
    pipeline_id = str(
        pipeline_info.get("pipeline_id")
        or request.pipeline_id
        or "research.current"
    )
    pipeline_version = int(
        pipeline_info.get("pipeline_version")
        or request.pipeline_version
        or 1
    )
    resolved_hash = str(pipeline_info.get("pipeline_hash") or "")

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
    trace_stages: list[PipelineStageTrace] = []

    query_stage = stage_payloads.get("query_metadata") or {}
    query_strategy = (
        "query.research_decompose"
        if bool(retrieval.get("query_decomposition"))
        else "query.passthrough"
    )
    trace_stages.append(
        _stage(
            "query",
            query_strategy,
            elapsed_seconds=query_stage.get("seconds"),
            input_count=1,
            output_count=1,
            provider=result.get("provider") if query_strategy.endswith("decompose") else None,
            model=result.get("model") if query_strategy.endswith("decompose") else None,
            parameters={
                "requested": retrieval.get("requested_query_decomposition"),
                "effective": retrieval.get("query_decomposition"),
                "num_predict": retrieval.get("query_decomposition_num_predict"),
            },
        )
    )

    selected_count = int(retrieval.get("selected_evidence_count") or 0)
    if selected_count:
        trace_stages.append(
            _stage(
                "selected_evidence",
                "retrieve.selected_evidence",
                input_count=selected_count,
                output_count=selected_count,
            )
        )

    retrieval_stage = stage_payloads.get("retrieval") or {}
    retrieval_seconds = retrieval_stage.get("seconds")
    # Candidate routes currently execute inside one feature-level retrieval
    # timer. Do not divide that aggregate duration between parallel branches:
    # doing so would manufacture stage precision that the runtime did not
    # measure. The aggregate is attached to rank fusion below until route-level
    # timers are introduced.
    if "similarity" in search_types:
        trace_stages.append(
            _stage(
                "semantic_retrieval",
                "retrieve.chroma_similarity",
                elapsed_seconds=None,
                output_count=raw_count,
                collection=collection_label,
                parameters={
                    "k": retrieval.get("k"),
                    "fetch_k": retrieval.get("fetch_k"),
                },
            )
        )
    resolved_stages = (
        resolved_pipeline.get("stages")
        if isinstance(resolved_pipeline.get("stages"), list)
        else []
    )
    resolved_strategies = {
        str(item.get("strategy") or "")
        for item in resolved_stages
        if isinstance(item, dict)
    }
    if (
        "normalize.collection_relevance" in resolved_strategies
        and {"similarity", "mmr"} & set(search_types)
    ):
        trace_stages.append(
            _stage(
                "normalize",
                "normalize.collection_relevance",
                input_count=raw_count,
                output_count=raw_count,
                collection=collection_label,
                score_summary={"metric_aware": True},
            )
        )
    if "lexical" in search_types:
        trace_stages.append(
            _stage(
                "lexical_retrieval",
                "retrieve.lexical_bm25",
                elapsed_seconds=None,
                output_count=raw_count,
                collection=collection_label,
                parameters={
                    "k": retrieval.get("k"),
                    "fetch_k": retrieval.get("fetch_k"),
                },
            )
        )
    if "mmr" in search_types:
        trace_stages.append(
            _stage(
                "retrieval_mmr",
                "select.mmr",
                elapsed_seconds=None,
                input_count=raw_count,
                output_count=raw_count,
                parameters={"lambda_mult": retrieval.get("lambda_mult")},
            )
        )

    if not bool(retrieval.get("skip_retrieval")):
        trace_stages.append(
            _stage(
                "rank_fusion",
                "fusion.rrf",
                elapsed_seconds=retrieval_seconds,
                input_count=raw_count,
                output_count=deduplicated_count,
                parameters={"rrf_k": retrieval.get("rrf_k")},
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
    reranker = str(retrieval.get("reranker") or "none")
    requested_reranker = str(retrieval.get("requested_reranker") or reranker)

    if requested_reranker == "cross_encoder":
        cross_encoder_completed = reranker == "cross_encoder"
        fallback_reason = (
            str(rerank_telemetry.get("fallback_reason") or "")
            or next(
                (
                    str(warning)
                    for warning in result.get("warnings") or []
                    if "cross-encoder" in str(warning).casefold()
                ),
                "",
            )
        )
        trace_stages.append(
            _stage(
                "rerank",
                "rerank.cross_encoder",
                elapsed_seconds=(
                    rerank_stage.get("seconds")
                    if cross_encoder_completed
                    else rerank_telemetry.get("timing_ms", 0) / 1000
                    if rerank_telemetry.get("timing_ms") is not None
                    else None
                ),
                input_count=deduplicated_count,
                output_count=(
                    int(rerank_detail.get("rerank_pool_count") or reranked_count)
                    if cross_encoder_completed
                    else 0
                ),
                provider="sentence-transformers",
                model=str(request.cross_encoder_model or "") or None,
                parameters={
                    "requested_reranker": requested_reranker,
                    "top_n": retrieval.get("rerank_top_n"),
                },
                fallback_reason=fallback_reason or None,
                status="completed" if cross_encoder_completed else "unavailable",
                score_summary={
                    key: rerank_telemetry[key]
                    for key in ("candidate_count", "reranked_count", "timing_ms")
                    if key in rerank_telemetry
                },
            )
        )

    if reranker == "lexical":
        trace_stages.append(
            _stage(
                "rerank_fallback" if requested_reranker == "cross_encoder" else "rerank",
                "rerank.lexical_fallback",
                elapsed_seconds=(
                    rerank_stage.get("seconds")
                    if requested_reranker != "cross_encoder"
                    else None
                ),
                input_count=deduplicated_count,
                output_count=reranked_count,
                parameters={
                    "top_n": retrieval.get("rerank_top_n"),
                    "fallback_from": (
                        "rerank.cross_encoder"
                        if requested_reranker == "cross_encoder"
                        else None
                    ),
                },
            )
        )
    elif reranker == "cross_encoder":
        pass
    else:
        trace_stages.append(
            _stage(
                "rerank_top_k",
                "select.top_k",
                elapsed_seconds=(
                    rerank_stage.get("seconds")
                    if requested_reranker != "cross_encoder"
                    else None
                ),
                input_count=deduplicated_count,
                output_count=reranked_count,
                parameters={
                    "limit": retrieval.get("rerank_top_n"),
                    "fallback_from": (
                        "rerank.cross_encoder"
                        if requested_reranker == "cross_encoder"
                        else None
                    ),
                },
            )
        )

    diversity_mode = str(retrieval.get("post_rerank_diversity") or "none")
    diversity_stage = stage_payloads.get("diversity") or {}
    if diversity_mode == "source_aware":
        trace_stages.append(
            _stage(
                "diversity",
                "select.source_diversity",
                elapsed_seconds=diversity_stage.get("seconds"),
                input_count=int((diversity_stage.get("detail") or {}).get("input_count") or 0),
                output_count=int((diversity_stage.get("detail") or {}).get("output_count") or 0),
            )
        )
    elif diversity_mode == "mmr":
        trace_stages.append(
            _stage(
                "diversity",
                "select.mmr",
                elapsed_seconds=diversity_stage.get("seconds"),
                input_count=int((diversity_stage.get("detail") or {}).get("input_count") or 0),
                output_count=int((diversity_stage.get("detail") or {}).get("output_count") or 0),
                parameters={"lambda_mult": retrieval.get("lambda_mult")},
            )
        )

    context_stage = stage_payloads.get("retrieval_context") or {}
    context_detail = context_stage.get("detail") if isinstance(context_stage.get("detail"), dict) else {}
    trace_stages.extend(
        [
            _stage(
                "provenance",
                "validate.provenance",
                input_count=reranked_count,
                output_count=int(context_detail.get("evidence_count") or 0),
                warnings=[
                    str(item)
                    for item in result.get("warnings") or []
                    if "provenance" in str(item).casefold()
                ],
            ),
            _stage(
                "context_pack",
                "pack.evidence_context",
                elapsed_seconds=context_stage.get("seconds"),
                input_count=int(context_detail.get("evidence_count") or 0),
                output_count=int(context_detail.get("evidence_count") or 0),
                parameters={
                    "record_char_limit": retrieval.get("evidence_record_char_limit"),
                    "total_char_limit": retrieval.get("evidence_total_char_limit"),
                    "characters": context_detail.get("characters"),
                },
            ),
        ]
    )

    if request.use_prior_response_memory:
        trace_stages.append(
            _stage(
                "response_memory",
                "retrieve.response_memory",
                parameters={"enabled": True},
            )
        )
    if request.use_prior_claim_memory:
        trace_stages.append(
            _stage(
                "claim_memory",
                "retrieve.claim_memory",
                parameters={"enabled": True},
            )
        )

    generation_stage = stage_payloads.get("generation") or {}
    trace_stages.append(
        _stage(
            "generation",
            "llm.generate_answer",
            elapsed_seconds=generation_stage.get("seconds"),
            input_count=int(context_detail.get("evidence_count") or 0),
            output_count=1,
            provider=str(result.get("provider") or "") or None,
            model=str(result.get("model") or "") or None,
        )
    )

    binding_stage = stage_payloads.get("bind_sources") or {}
    trace_stages.append(
        _stage(
            "citation_binding",
            "validate.citation_binding",
            elapsed_seconds=binding_stage.get("seconds"),
            input_count=1,
            output_count=1,
            parameters={
                "enabled": bool(request.bind_citations),
                "include_works_cited": bool(request.include_works_cited),
            },
        )
    )

    grade_stage = stage_payloads.get("auto_grade")
    if isinstance(grade_stage, dict):
        detail = grade_stage.get("detail") if isinstance(grade_stage.get("detail"), dict) else {}
        grade_failed = bool(result.get("auto_grade_error"))
        trace_stages.append(
            _stage(
                "evaluation",
                "llm.grade_rag",
                elapsed_seconds=grade_stage.get("seconds"),
                input_count=1,
                output_count=0 if grade_failed else 1,
                provider=str(detail.get("provider") or result.get("auto_grade_provider") or "") or None,
                model=str(detail.get("model") or result.get("auto_grade_model") or "") or None,
                fallback_reason=(
                    str(result.get("auto_grade_error") or "")[:_MAX_TRACE_STRING]
                    if grade_failed
                    else None
                ),
                status="failed" if grade_failed else "completed",
            )
        )

    finished = _parse_datetime(finished_at)
    started = _parse_datetime(started_at)
    total_elapsed = result.get("elapsed_seconds")
    return PipelineRunTrace(
        run_id=str(run_id),
        feature="research",
        pipeline_id=pipeline_id,
        pipeline_version=pipeline_version,
        resolved_pipeline=sanitize_trace_value(resolved_pipeline),
        resolved_hash=resolved_hash,
        owner=owner,
        status=status,  # type: ignore[arg-type]
        started_at=started,
        finished_at=finished,
        total_elapsed_ms=(
            max(0, int(float(total_elapsed) * 1000))
            if total_elapsed is not None
            else max(0, int((finished - started).total_seconds() * 1000))
        ),
        warnings=[str(item)[:_MAX_TRACE_STRING] for item in result.get("warnings") or []],
        stages=trace_stages,
    )
