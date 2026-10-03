# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Bounded executable adapter for reviewer evidence-suggestion pipelines.

Pipeline definitions remain data. This module is the code-owned adapter that
translates the small supported evidence graph into existing DerridAI retrieval
primitives. Structurally valid graphs outside this contract remain inspectable
but are not executable until an explicit adapter supports them.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ..evidence_suggestions import (
    BACKFILL_MIN_SCORE,
    CROSS_ENCODER_METHOD,
    LLM_METHOD,
    METHOD,
    MMR_METHOD,
    SEMANTIC_MIN_SCORE,
    llm_prompt,
    merge_lexical_semantic_evidence,
    score_semantic_evidence_blocks,
    select_evidence_mmr,
    semantic_query,
    suggest_evidence_blocks,
    validate_llm_choice,
)
from .evidence_tracing import build_evidence_trace
from .models import PipelineDefinition, PipelineRunTrace, PipelineStageDefinition
from .registry import reject_unhonoured_config
from .service import pipeline_hash


@dataclass(frozen=True)
class EvidencePipelinePlan:
    """Executable subset of an evidence pipeline definition."""

    query_stage_id: str
    support_stage_id: str
    provenance_stage_id: str
    select_stage_id: str
    semantic_stage_id: str | None = None
    lexical_stage_id: str | None = None
    rerank_stage_id: str | None = None
    mmr_stage_id: str | None = None
    llm_stage_id: str | None = None
    selection_limit: int | None = None
    lexical_fetch_k: int | None = None
    lexical_min_score: float | None = None
    semantic_fetch_k: int | None = None
    semantic_min_similarity: float | None = None
    mmr_lambda: float | None = None
    mmr_limit: int | None = None
    mmr_min_relevance: float | None = None
    cross_encoder_top_k: int | None = None
    cross_encoder_model: str | None = None
    cross_encoder_timeout_seconds: float | None = None
    support_min_score: float = BACKFILL_MIN_SCORE


@dataclass(frozen=True)
class EvidencePipelineExecution:
    items: list[dict[str, Any]]
    status: dict[str, Any]
    trace: PipelineRunTrace


SUPPORTED_STRATEGIES = frozenset(
    {
        "query.evidence_field",
        "retrieve.source_cosine",
        "retrieve.lexical_bm25",
        "rerank.cross_encoder",
        "select.mmr",
        "validate.evidence_support",
        "validate.provenance",
        "llm.closed_choice_evidence",
        "select.top_k",
    }
)


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
        raise ValueError(f"Evidence adapter supports at most one {strategy!r} stage.")
    if required and not stages:
        raise ValueError(f"Evidence adapter requires a {strategy!r} stage.")
    return stages[0] if stages else None


def _require_target(stage: PipelineStageDefinition, target: str, *, edge: str = "next") -> None:
    values = stage.next if edge == "next" else [getattr(stage, edge)]
    if target not in [value for value in values if value]:
        raise ValueError(
            f"Evidence stage {stage.id!r} must route {edge.replace('_', ' ')} to {target!r}."
        )


def compile_evidence_pipeline(pipeline: PipelineDefinition) -> EvidencePipelinePlan:
    """Compile the explicit evidence graph subset DerridAI can execute today."""

    if pipeline.purpose != "evidence_suggestion":
        raise ValueError("Evidence adapter can only compile evidence_suggestion pipelines.")
    reject_unhonoured_config(
        pipeline,
        "reviewer evidence",
        honour={
            "retrieve.lexical_bm25": frozenset({"min_score"}),
            "select.mmr": frozenset({"min_relevance"}),
        },
    )

    enabled = [stage for stage in pipeline.stages if stage.enabled]
    unsupported = sorted({stage.strategy for stage in enabled} - SUPPORTED_STRATEGIES)
    if unsupported:
        raise ValueError(
            "Evidence adapter does not implement strategy family/stage(s): "
            + ", ".join(unsupported)
        )

    by_strategy = _enabled_by_strategy(pipeline)
    query = _one(by_strategy, "query.evidence_field", required=True)
    semantic = _one(by_strategy, "retrieve.source_cosine")
    lexical = _one(by_strategy, "retrieve.lexical_bm25")
    select = _one(by_strategy, "select.top_k", required=True)
    rerank = _one(by_strategy, "rerank.cross_encoder")
    mmr = _one(by_strategy, "select.mmr")
    support = _one(by_strategy, "validate.evidence_support", required=True)
    provenance = _one(by_strategy, "validate.provenance", required=True)
    llm = _one(by_strategy, "llm.closed_choice_evidence")
    assert (
        query is not None
        and support is not None
        and provenance is not None
        and select is not None
    )
    if semantic is None and lexical is None:
        raise ValueError("Evidence pipelines need semantic and/or lexical candidate generation.")

    if pipeline.entry_stage_ids != [query.id]:
        raise ValueError("Evidence adapter requires the field-aware query stage as its sole entry stage.")
    for retriever in (semantic, lexical):
        if retriever is not None:
            _require_target(query, retriever.id)

    if rerank is not None and mmr is not None:
        convergence = rerank.id
        _require_target(rerank, mmr.id)
        _require_target(mmr, support.id)
    elif rerank is not None:
        convergence = rerank.id
        _require_target(rerank, support.id)
    elif mmr is not None:
        convergence = mmr.id
        _require_target(mmr, support.id)
    else:
        convergence = support.id
    for retriever in (semantic, lexical):
        if retriever is not None:
            _require_target(retriever, convergence)

    if rerank is not None:
        for fallback_edge in ("on_unavailable", "on_timeout", "on_error"):
            fallback = getattr(rerank, fallback_edge)
            if fallback is not None and fallback != support.id:
                raise ValueError(
                    f"Evidence cross-encoder {fallback_edge} must continue to {support.id!r}."
                )

    if support.next != [provenance.id]:
        raise ValueError(
            f"Evidence support stage must route normal results only to {provenance.id!r}."
        )
    for fallback_edge in ("on_unavailable", "on_timeout", "on_error"):
        if getattr(support, fallback_edge) is not None:
            raise ValueError(
                f"Evidence support stage may not use {fallback_edge}; support failures "
                "must not bypass deterministic validation."
            )
    if llm is not None:
        _require_target(support, llm.id, edge="on_empty")
        if llm.edge_targets() != [provenance.id]:
            raise ValueError(
                "Closed-choice evidence fallback may only continue to the provenance gate."
            )
    elif support.on_empty is not None:
        raise ValueError("Evidence support on_empty references an unsupported fallback stage.")

    if provenance.edge_targets() != [select.id]:
        raise ValueError(
            "Evidence provenance validation may only continue to top-K selection; "
            "it cannot expose a bypass edge."
        )

    if select.edge_targets():
        raise ValueError("Evidence top-K selection must be terminal in the current adapter.")

    return EvidencePipelinePlan(
        query_stage_id=query.id,
        semantic_stage_id=semantic.id if semantic else None,
        lexical_stage_id=lexical.id if lexical else None,
        select_stage_id=select.id,
        rerank_stage_id=rerank.id if rerank else None,
        mmr_stage_id=mmr.id if mmr else None,
        support_stage_id=support.id,
        provenance_stage_id=provenance.id,
        llm_stage_id=llm.id if llm else None,
        selection_limit=(int(select.config["limit"]) if "limit" in select.config else None),
        lexical_fetch_k=(
            int(lexical.config["fetch_k"])
            if lexical is not None and "fetch_k" in lexical.config
            else None
        ),
        lexical_min_score=(
            float(lexical.config["min_score"])
            if lexical is not None and "min_score" in lexical.config
            else None
        ),
        semantic_fetch_k=(
            int(semantic.config["fetch_k"])
            if semantic is not None and "fetch_k" in semantic.config
            else None
        ),
        semantic_min_similarity=(
            float(semantic.config["min_similarity"])
            if semantic is not None and "min_similarity" in semantic.config
            else None
        ),
        mmr_lambda=(float(mmr.config["lambda_mult"]) if mmr is not None and "lambda_mult" in mmr.config else None),
        mmr_limit=(int(mmr.config["limit"]) if mmr is not None and "limit" in mmr.config else None),
        mmr_min_relevance=(
            float(mmr.config["min_relevance"])
            if mmr is not None and "min_relevance" in mmr.config
            else None
        ),
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
        support_min_score=(
            float(support.config.get("min_score", BACKFILL_MIN_SCORE))
        ),
    )


def _score_summary(items: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [float(item[key]) for item in items if item.get(key) is not None]
    if not values:
        return {}
    return {
        "count": len(values),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "mean": round(sum(values) / len(values), 4),
    }


def _support_rows(
    value: Any,
    blocks: list[dict[str, Any]],
    items: list[dict[str, Any]],
    *,
    min_score: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    supported = {
        item["block_id"]: item
        for item in suggest_evidence_blocks(
            value,
            blocks,
            limit=max(1, len(blocks)),
            min_score=min_score,
        )
    }
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for item in items:
        block_id = str(item.get("block_id") or "")
        support = supported.get(block_id)
        row = dict(item)
        row["support_score"] = support.get("score") if support else None
        row["support_method"] = METHOD
        row["support_status"] = "supported" if support else "rejected"
        signals = dict(row.get("signals") or {})
        signals["support"] = {
            "score": support.get("score") if support else None,
            "method": METHOD,
            "reason": (
                support.get("reason")
                if support
                else f"Deterministic support score did not reach {min_score:.2f}."
            ),
            "status": row["support_status"],
        }
        row["signals"] = signals
        if support:
            rows.append(row)
        else:
            rejected.append(row)
    return rows, rejected


def _provenance_rows(
    source_document_id: str,
    blocks: list[dict[str, Any]],
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Require every suggested item to bind to a real source unit in this document."""

    valid_block_ids = {
        str(block.get("block_id") or "")
        for block in blocks
        if str(block.get("block_id") or "")
    }
    verified: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for item in items:
        block_id = str(item.get("block_id") or "")
        row = dict(item)
        signals = dict(row.get("signals") or {})
        if source_document_id and block_id and block_id in valid_block_ids:
            row["provenance_status"] = "verified"
            signals["provenance"] = {
                "status": "verified",
                "source_document_id": source_document_id,
                "block_id": block_id,
                "reason": (
                    "Candidate block is a real source unit in the current source document."
                ),
            }
            row["signals"] = signals
            verified.append(row)
            continue

        reason = (
            "Source document identity is missing."
            if not source_document_id
            else "Candidate block does not belong to the current source-unit set."
        )
        row["provenance_status"] = "rejected"
        signals["provenance"] = {
            "status": "rejected",
            "source_document_id": source_document_id or None,
            "block_id": block_id or None,
            "reason": reason,
        }
        row["signals"] = signals
        rejected.append(row)
    return verified, rejected


def _candidate_decision(item: dict[str, Any], decision: str) -> dict[str, Any]:
    """Return bounded score/reason metadata without copying candidate source text."""

    payload = {
        "block_id": str(item.get("block_id") or ""),
        "decision": decision,
    }
    for key in (
        "score",
        "retrieval_score",
        "lexical_score",
        "semantic_score",
        "cross_encoder_score",
        "mmr_score",
        "support_score",
        "support_status",
        "provenance_status",
    ):
        if item.get(key) is not None:
            payload[key] = item[key]
    signals = item.get("signals") if isinstance(item.get("signals"), dict) else {}
    support = signals.get("support") if isinstance(signals.get("support"), dict) else {}
    provenance = (
        signals.get("provenance")
        if isinstance(signals.get("provenance"), dict)
        else {}
    )
    reason = (
        provenance.get("reason")
        if decision == "rejected_provenance"
        else support.get("reason")
    )
    if reason:
        payload["reason"] = str(reason)[:500]
    return payload


def execute_reviewer_evidence_pipeline(
    *,
    pipeline: PipelineDefinition,
    resolved_hash: str | None,
    value: Any,
    blocks: list[dict[str, Any]],
    field_metadata: Any,
    source_document_id: str,
    projection: Any,
    limit: int = 5,
    provider: str | None = None,
    model: str | None = None,
    llm_choice: Callable[[str], dict[str, Any]] | None = None,
    owner: str | None = None,
    run_id: str | None = None,
) -> EvidencePipelineExecution:
    """Execute a supported reviewer evidence pipeline with truthful stage telemetry."""

    from ..config import settings

    plan = compile_evidence_pipeline(pipeline)
    started_at = datetime.now(UTC)
    observations: dict[str, dict[str, Any]] = {}
    query_started = time.perf_counter()
    query_text = semantic_query(field_metadata, value)
    observations[plan.query_stage_id] = {
        "elapsed_seconds": time.perf_counter() - query_started,
        "input_count": 1,
        "output_count": 1,
    }

    lexical_by_id: dict[str, dict[str, Any]] = {}
    semantic_by_id: dict[str, dict[str, Any]] = {}
    retrieval_status = {"semantic": "skipped", "reason": ""}
    retrieval_seconds = 0.0
    if plan.lexical_stage_id is not None:
        lexical_started = time.perf_counter()
        lexical_min = 0.2 if plan.lexical_min_score is None else plan.lexical_min_score
        lexical_limit = plan.lexical_fetch_k if plan.lexical_fetch_k is not None else max(1, len(blocks))
        lexical_rows = suggest_evidence_blocks(
            value, blocks, limit=max(1, lexical_limit), min_score=lexical_min
        )
        lexical_by_id = {item["block_id"]: item for item in lexical_rows}
        retrieval_seconds += time.perf_counter() - lexical_started
        observations[plan.lexical_stage_id] = {
            "elapsed_seconds": time.perf_counter() - lexical_started,
            "input_count": len(blocks),
            "output_count": len(lexical_rows),
            "parameters": {
                "scope_size": len(blocks),
                "fetch_k": lexical_limit,
                "min_score": lexical_min,
            },
            "score_summary": _score_summary(lexical_rows, "score"),
        }
    if plan.semantic_stage_id is not None:
        semantic_started = time.perf_counter()
        semantic_min = SEMANTIC_MIN_SCORE if plan.semantic_min_similarity is None else plan.semantic_min_similarity
        semantic_by_id, retrieval_status = score_semantic_evidence_blocks(
            value,
            blocks,
            field_metadata=field_metadata,
            source_document_id=source_document_id,
            projection=projection,
            provider=provider,
            model=model,
            query=query_text,
            limit=plan.semantic_fetch_k,
            min_similarity=semantic_min,
        )
        retrieval_seconds += time.perf_counter() - semantic_started
        semantic_fallback = retrieval_status.get("semantic") == "fallback"
        observations[plan.semantic_stage_id] = {
            "elapsed_seconds": time.perf_counter() - semantic_started,
            "input_count": len(blocks),
            "output_count": len(semantic_by_id),
            "parameters": {
                "scope_size": len(blocks),
                "fetch_k": plan.semantic_fetch_k,
                "min_similarity": semantic_min,
            },
            "status": "unavailable" if semantic_fallback else "completed",
            "fallback_reason": retrieval_status.get("reason") if semantic_fallback else None,
            "score_summary": _score_summary(list(semantic_by_id.values()), "score"),
            "provider": provider,
            "model": model,
        }
    items = merge_lexical_semantic_evidence(blocks, lexical_by_id, semantic_by_id, retrieval_status)
    shared_retrieval_seconds = retrieval_seconds

    if plan.rerank_stage_id is not None:
        rerank_started = time.perf_counter()
        if not settings.metadata_cross_encoder_enabled:
            observations[plan.rerank_stage_id] = {
                "status": "unavailable",
                "input_count": len(items),
                "output_count": len(items),
                "fallback_reason": "Metadata cross-encoder is disabled by deployment settings.",
            }
        elif items:
            from ..cross_encoder import predict_scores

            block_text = {
                str(block.get("block_id") or ""): str(block.get("text") or "")
                for block in blocks
            }
            top_k = max(
                1,
                int(plan.cross_encoder_top_k or settings.metadata_cross_encoder_top_k),
            )
            model_name = plan.cross_encoder_model or settings.rag_cross_encoder_model
            timeout_seconds = float(
                plan.cross_encoder_timeout_seconds
                or settings.metadata_cross_encoder_timeout_seconds
            )
            head = items[:top_k]
            scores, telemetry = predict_scores(
                [
                    (query_text, block_text.get(str(item.get("block_id") or ""), ""))
                    for item in head
                ],
                model_name=model_name,
                timeout_seconds=timeout_seconds,
            )
            if scores:
                reranked: list[dict[str, Any]] = []
                for item, score in zip(head, scores):
                    row = dict(item)
                    row["retrieval_score"] = row.get("score")
                    row["cross_encoder_score"] = round(float(score), 4)
                    row["score"] = round(float(score), 4)
                    signals = dict(row.get("signals") or {})
                    signals["cross_encoder"] = {
                        "score": row["cross_encoder_score"],
                        "method": CROSS_ENCODER_METHOD,
                        "reason": "Cross-encoder relevance score for the field/value query and candidate span.",
                        "status": "available",
                    }
                    row["signals"] = signals
                    reranked.append(row)
                reranked.sort(key=lambda item: (-float(item.get("score") or 0.0), str(item.get("block_id") or "")))
                items = [*reranked, *items[len(head):]]
                observations[plan.rerank_stage_id] = {
                    "elapsed_seconds": time.perf_counter() - rerank_started,
                    "input_count": len(head),
                    "output_count": len(reranked),
                    "model": model_name,
                    "parameters": {"top_k": top_k, "timeout_seconds": timeout_seconds},
                    "score_summary": _score_summary(reranked, "cross_encoder_score"),
                }
            else:
                fallback_reason = str((telemetry or {}).get("fallback_reason") or "Cross-encoder produced no usable scores.")
                observations[plan.rerank_stage_id] = {
                    "elapsed_seconds": time.perf_counter() - rerank_started,
                    "status": "unavailable",
                    "input_count": len(head),
                    "output_count": len(items),
                    "model": model_name,
                    "fallback_reason": fallback_reason,
                }
        else:
            observations[plan.rerank_stage_id] = {
                "elapsed_seconds": time.perf_counter() - rerank_started,
                "input_count": 0,
                "output_count": 0,
            }

    if plan.mmr_stage_id is not None:
        mmr_started = time.perf_counter()
        mmr_limit = max(1, int(plan.mmr_limit or plan.selection_limit or limit))
        mmr_lambda = 0.72 if plan.mmr_lambda is None else plan.mmr_lambda
        min_relevance = 0.0 if plan.mmr_min_relevance is None else plan.mmr_min_relevance
        parameters = {"limit": mmr_limit, "lambda_mult": mmr_lambda, "min_relevance": min_relevance}
        input_count = len(items)
        if not items or float(items[0].get("score") or 0.0) < min_relevance:
            items = []
            observations[plan.mmr_stage_id] = {
                "elapsed_seconds": time.perf_counter() - mmr_started,
                "input_count": input_count,
                "output_count": 0,
                "parameters": parameters,
                "fallback_reason": f"Top relevance did not reach {min_relevance:.2f}.",
            }
        else:
            selected_mmr = select_evidence_mmr(items, limit=mmr_limit, lambda_mult=mmr_lambda)
            items = [
                {
                    **row,
                    "mmr_score": round(float(row.get("mmr_score") or 0.0), 4),
                    "method": row.get("method") or MMR_METHOD,
                }
                for row in selected_mmr
            ]
            observations[plan.mmr_stage_id] = {
                "elapsed_seconds": time.perf_counter() - mmr_started,
                "input_count": input_count,
                "output_count": len(items),
                "parameters": parameters,
                "score_summary": _score_summary(items, "mmr_score"),
            }

    support_rejected: list[dict[str, Any]] = []
    if plan.support_stage_id is not None:
        support_started = time.perf_counter()
        input_count = len(items)
        items, support_rejected = _support_rows(
            value,
            blocks,
            items,
            min_score=plan.support_min_score,
        )
        observations[plan.support_stage_id] = {
            "elapsed_seconds": time.perf_counter() - support_started,
            "input_count": input_count,
            "output_count": len(items),
            "parameters": {
                "min_score": plan.support_min_score,
                "validator": METHOD,
                "scope_size": len(blocks),
            },
            "score_summary": _score_summary(items, "support_score"),
        }
        if not items and plan.llm_stage_id is not None:
            if llm_choice is None:
                observations[plan.llm_stage_id] = {
                    "status": "skipped",
                    "input_count": len(blocks),
                    "output_count": 0,
                    "fallback_reason": "No closed-choice model callback was supplied for this reviewer request.",
                }
            else:
                llm_started = time.perf_counter()
                try:
                    choices = validate_llm_choice(
                        llm_choice(llm_prompt(str((field_metadata or {}).get("name") or "field"), value, blocks)),
                        blocks,
                        value,
                        limit=max(1, limit),
                    )
                except Exception as exc:  # noqa: BLE001 - advisory fallback must not fail review
                    choices = []
                    observations[plan.llm_stage_id] = {
                        "elapsed_seconds": time.perf_counter() - llm_started,
                        "status": "failed",
                        "input_count": len(blocks),
                        "output_count": 0,
                        "fallback_reason": str(exc),
                    }
                else:
                    items = [
                        {
                            **choice,
                            "score": None,
                            "support_score": None,
                            "support_method": LLM_METHOD,
                            "support_status": "model_selected",
                            "signals": {
                                "support": {
                                    "score": None,
                                    "method": LLM_METHOD,
                                    "reason": choice.get("reason") or "Closed-choice model selected this source unit.",
                                    "status": "model_selected",
                                }
                            },
                        }
                        for choice in choices
                    ]
                    observations[plan.llm_stage_id] = {
                        "elapsed_seconds": time.perf_counter() - llm_started,
                        "input_count": len(blocks),
                        "output_count": len(items),
                        "provider": provider,
                        "model": model,
                    }
        elif plan.llm_stage_id is not None:
            observations[plan.llm_stage_id] = {
                "status": "skipped",
                "input_count": len(blocks),
                "output_count": 0,
                "fallback_reason": "Support validation produced usable evidence candidates.",
            }

    provenance_started = time.perf_counter()
    provenance_input_count = len(items)
    items, provenance_rejected = _provenance_rows(
        source_document_id,
        blocks,
        items,
    )
    observations[plan.provenance_stage_id] = {
        "elapsed_seconds": time.perf_counter() - provenance_started,
        "input_count": provenance_input_count,
        "output_count": len(items),
        "parameters": {
            "validator": "current_source_unit_membership",
            "source_document_id_present": bool(source_document_id),
        },
    }

    effective_limit = max(1, int(limit))
    if plan.selection_limit is not None:
        effective_limit = min(effective_limit, max(1, plan.selection_limit))
    select_started = time.perf_counter()
    eligible_items = list(items)
    selected = eligible_items[:effective_limit]
    observations[plan.select_stage_id] = {
        "elapsed_seconds": time.perf_counter() - select_started,
        "input_count": len(eligible_items),
        "output_count": len(selected),
        "parameters": {"limit": effective_limit},
        "score_summary": _score_summary(selected, "score"),
    }

    finished_at = datetime.now(UTC)
    resolved = resolved_hash or pipeline_hash(pipeline)
    trace = build_evidence_trace(
        run_id=run_id or str(uuid.uuid4()),
        pipeline=pipeline,
        resolved_hash=resolved,
        started_at=started_at,
        finished_at=finished_at,
        observations=observations,
        owner=owner,
    )
    selected_ids = {str(item.get("block_id") or "") for item in selected}
    decisions = [
        *(_candidate_decision(item, "rejected_support") for item in support_rejected),
        *(
            _candidate_decision(item, "rejected_provenance")
            for item in provenance_rejected
        ),
        *(
            _candidate_decision(
                item,
                "selected"
                if str(item.get("block_id") or "") in selected_ids
                else "not_selected_top_k",
            )
            for item in eligible_items
        ),
    ]
    status = {
        **retrieval_status,
        "candidate_decision_count": len(decisions),
        "candidate_decisions": decisions[:100],
        "pipeline_id": pipeline.pipeline_id,
        "pipeline_version": pipeline.version,
        "pipeline_hash": resolved,
        "trace_id": trace.run_id,
        "shared_retrieval_elapsed_ms": max(0, int(shared_retrieval_seconds * 1000)),
    }
    for item in selected:
        item.pop("vector", None)
    return EvidencePipelineExecution(items=selected, status=status, trace=trace)
