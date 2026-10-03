# Copyright 2026 Aaron John Schlosser, PhD.
"""Non-persistent Research pipeline dry-run and comparison helpers.

These helpers deliberately compare computational behavior without writing a
Research job, response-memory row, corpus record, or pipeline execution trace.
They may still invoke retrieval dependencies (and, when explicitly requested,
the query-transform model) because the point is to exercise the real configured
pipeline rather than simulate it.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..models import RAGRunRequest


class PipelineVersionRef(BaseModel):
    pipeline_id: str = Field(min_length=1, max_length=160)
    version: int = Field(ge=1)


class ResearchPipelineComparisonRequest(BaseModel):
    request: RAGRunRequest
    left: PipelineVersionRef
    right: PipelineVersionRef


def _record_id(item: dict[str, Any]) -> str:
    record = item.get("record") if isinstance(item.get("record"), dict) else {}
    return str(record.get("record_id") or item.get("chroma_id") or item.get("id") or "")


def _numeric_summary(
    rows: list[dict[str, Any]],
    key: str,
) -> dict[str, float | int | None]:
    values = [
        float(row[key])
        for row in rows
        if isinstance(row.get(key), (int, float))
    ]
    if not values:
        return {"count": 0, "minimum": None, "maximum": None, "mean": None}
    return {
        "count": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "mean": sum(values) / len(values),
    }


def _phase_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "record_ids": [str(row.get("record_id") or "") for row in rows if row.get("record_id")],
        "scores": {
            "relevance": _numeric_summary(rows, "relevance"),
            "rrf_score": _numeric_summary(rows, "rrf_score"),
            "rerank_score": _numeric_summary(rows, "rerank_score"),
        },
    }


def _overlap(left_ids: list[str], right_ids: list[str]) -> dict[str, Any]:
    left_set = set(left_ids)
    right_set = set(right_ids)
    shared = [record_id for record_id in left_ids if record_id in right_set]
    union = left_set | right_set
    return {
        "shared_record_ids": shared,
        "left_only_record_ids": [
            record_id for record_id in left_ids if record_id not in right_set
        ],
        "right_only_record_ids": [
            record_id for record_id in right_ids if record_id not in left_set
        ],
        "shared_count": len(shared),
        "union_count": len(union),
        "jaccard_overlap": (len(shared) / len(union)) if union else 1.0,
    }


def summarize_research_dry_run(result: dict[str, Any]) -> dict[str, Any]:
    """Return a bounded comparison-safe view of one retrieval dry run."""

    evidence_rows: list[dict[str, Any]] = []
    for rank, item in enumerate(result.get("evidence") or [], start=1):
        if not isinstance(item, dict):
            continue
        record = item.get("record") if isinstance(item.get("record"), dict) else {}
        record_id = _record_id(item)
        if not record_id:
            continue
        evidence_rows.append(
            {
                "record_id": record_id,
                "rank": rank,
                "work": str(record.get("work") or ""),
                "citation": str(item.get("inline_citation") or ""),
                "collection": item.get("collection"),
                "distance": item.get("distance"),
                "rrf_score": item.get("rrf_score"),
                "rerank_score": item.get("rerank_score"),
                "retrieval_hits": item.get("retrieval_hits") or [],
            }
        )

    stages = []
    for stage in result.get("stages") or []:
        if not isinstance(stage, dict):
            continue
        stages.append(
            {
                "name": str(stage.get("name") or ""),
                "seconds": stage.get("seconds"),
                "detail": stage.get("detail") if isinstance(stage.get("detail"), dict) else {},
            }
        )

    pipeline = result.get("pipeline") if isinstance(result.get("pipeline"), dict) else {}
    retrieval = result.get("retrieval") if isinstance(result.get("retrieval"), dict) else {}
    diagnostics = (
        result.get("diagnostics")
        if isinstance(result.get("diagnostics"), dict)
        else {}
    )
    pre_rerank = [
        row for row in diagnostics.get("pre_rerank") or [] if isinstance(row, dict)
    ]
    post_rerank = [
        row for row in diagnostics.get("post_rerank") or [] if isinstance(row, dict)
    ]
    post_selection = [
        row for row in diagnostics.get("post_selection") or [] if isinstance(row, dict)
    ]
    return {
        "pipeline": {
            key: pipeline.get(key)
            for key in ("pipeline_id", "pipeline_version", "pipeline_hash", "name", "purpose")
        },
        "elapsed_seconds": result.get("elapsed_seconds"),
        "warnings": list(result.get("warnings") or []),
        "retrieval": retrieval,
        "candidate_retention": diagnostics.get("candidate_retention") or "unavailable",
        "candidates": {
            "pre_rerank": _phase_summary(pre_rerank),
            "post_rerank": _phase_summary(post_rerank),
            "post_selection": _phase_summary(post_selection),
        },
        "context_characters": diagnostics.get("context_characters"),
        "resource_use": {
            "query_transform_model_calls": int(
                retrieval.get("query_transform_model_calls") or 0
            ),
            "cross_encoder_calls": int(retrieval.get("cross_encoder_calls") or 0),
        },
        "evidence": evidence_rows,
        "stages": stages,
    }


def compare_research_dry_runs(
    left_result: dict[str, Any],
    right_result: dict[str, Any],
) -> dict[str, Any]:
    """Compare final evidence membership/rank without implying a quality winner."""

    left = summarize_research_dry_run(left_result)
    right = summarize_research_dry_run(right_result)

    left_ids = [str(item["record_id"]) for item in left["evidence"]]
    right_ids = [str(item["record_id"]) for item in right["evidence"]]
    evidence_overlap = _overlap(left_ids, right_ids)

    left_candidates = list(left["candidates"]["pre_rerank"]["record_ids"])
    right_candidates = list(right["candidates"]["pre_rerank"]["record_ids"])
    candidate_overlap = _overlap(left_candidates, right_candidates)

    left_post_rerank = list(left["candidates"]["post_rerank"]["record_ids"])
    right_post_rerank = list(right["candidates"]["post_rerank"]["record_ids"])
    post_rerank_overlap = _overlap(left_post_rerank, right_post_rerank)

    left_rank = {record_id: index for index, record_id in enumerate(left_ids, start=1)}
    right_rank = {record_id: index for index, record_id in enumerate(right_ids, start=1)}
    shared = evidence_overlap["shared_record_ids"]
    rank_changes = [
        {
            "record_id": record_id,
            "left_rank": left_rank[record_id],
            "right_rank": right_rank[record_id],
            "rank_delta": right_rank[record_id] - left_rank[record_id],
        }
        for record_id in shared
    ]

    return {
        "non_persistent": True,
        "left": left,
        "right": right,
        "comparison": {
            # Keep the original final-evidence fields stable for the first UI
            # while adding explicit candidate-stage comparisons for benchmarks.
            **evidence_overlap,
            "candidate_overlap": candidate_overlap,
            "post_rerank_overlap": post_rerank_overlap,
            "rank_changes": rank_changes,
            "elapsed_seconds_delta": (
                float(right["elapsed_seconds"]) - float(left["elapsed_seconds"])
                if isinstance(left.get("elapsed_seconds"), (int, float))
                and isinstance(right.get("elapsed_seconds"), (int, float))
                else None
            ),
            "context_characters_delta": (
                int(right["context_characters"]) - int(left["context_characters"])
                if isinstance(left.get("context_characters"), int)
                and isinstance(right.get("context_characters"), int)
                else None
            ),
        },
    }


def comparison_source_projection() -> Any:
    """Rebuildable source-unit embeddings for comparison, never scholarly evidence."""

    from ..services import store
    from ..source_embeddings import SourceEmbeddingProjection

    return SourceEmbeddingProjection(store)


class EvidencePipelineComparisonRequest(BaseModel):
    value: Any
    blocks: list[dict[str, Any]] = Field(min_length=1)
    field: str = Field(default="field", min_length=1, max_length=120)
    field_metadata: dict[str, Any] = Field(default_factory=dict)
    source_document_id: str = ""
    left: PipelineVersionRef
    right: PipelineVersionRef
    limit: int = Field(default=5, ge=1, le=64)


def _block_row(item: dict[str, Any], rank: int) -> dict[str, Any]:
    return {
        "block_id": str(item.get("block_id") or ""),
        "rank": rank,
        "score": item.get("score"),
        "lexical_score": item.get("lexical_score"),
        "semantic_score": item.get("semantic_score"),
        "cross_encoder_score": item.get("cross_encoder_score"),
        "mmr_score": item.get("mmr_score"),
        "support_score": item.get("support_score"),
        "method": item.get("method"),
    }


def _stage_rows(trace: Any) -> list[dict[str, Any]]:
    rows = []
    for stage in getattr(trace, "stages", []) or []:
        rows.append(
            {
                "stage_id": stage.stage_id,
                "strategy": getattr(stage, "strategy_id", None) or getattr(stage, "strategy", None),
                "status": stage.status,
                "elapsed_ms": stage.elapsed_ms,
                "input_count": stage.input_count,
                "output_count": stage.output_count,
                "fallback_reason": stage.fallback_reason,
            }
        )
    return rows


def summarize_evidence_suggestion_run(execution: Any) -> dict[str, Any]:
    """Bounded view of one reviewer-evidence run: ids, ranks, and stage timing only."""

    items = list(execution.items or [])
    pipeline = {
        "pipeline_id": execution.status.get("pipeline_id"),
        "pipeline_version": execution.status.get("pipeline_version"),
        "pipeline_hash": execution.status.get("pipeline_hash"),
        "purpose": "evidence_suggestion",
    }
    return {
        "pipeline": pipeline,
        "elapsed_seconds": (execution.trace.total_elapsed_ms or 0) / 1000,
        "stages": _stage_rows(execution.trace),
        "candidates": [_block_row(item, rank) for rank, item in enumerate(items, start=1)],
    }


def summarize_evidence_recovery_run(
    *,
    pipeline: Any,
    resolved_hash: str,
    items: list[dict[str, Any]],
    winner: str | None,
    trace: Any,
    celf_compliant: bool,
    compliance_reason: str,
) -> dict[str, Any]:
    return {
        "pipeline": {
            "pipeline_id": pipeline.pipeline_id,
            "pipeline_version": pipeline.version,
            "pipeline_hash": resolved_hash,
            "purpose": pipeline.purpose,
            "celf_compliant": celf_compliant,
            "compliance_reason": compliance_reason,
        },
        "elapsed_seconds": (trace.total_elapsed_ms or 0) / 1000,
        "winning_strategy": winner,
        "stages": _stage_rows(trace),
        "candidates": [_block_row(item, rank) for rank, item in enumerate(items, start=1)],
    }


def compare_evidence_runs(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compare selected block membership/rank without implying a quality winner."""

    left_ids = [str(item["block_id"]) for item in left.get("candidates") or [] if item.get("block_id")]
    right_ids = [str(item["block_id"]) for item in right.get("candidates") or [] if item.get("block_id")]
    overlap = _overlap(left_ids, right_ids)
    left_rank = {block_id: index for index, block_id in enumerate(left_ids, start=1)}
    right_rank = {block_id: index for index, block_id in enumerate(right_ids, start=1)}
    rank_changes = [
        {
            "block_id": block_id,
            "left_rank": left_rank[block_id],
            "right_rank": right_rank[block_id],
            "rank_delta": right_rank[block_id] - left_rank[block_id],
        }
        for block_id in overlap["shared_record_ids"]
    ]
    return {
        "non_persistent": True,
        "left": left,
        "right": right,
        "comparison": {
            "shared_block_ids": overlap["shared_record_ids"],
            "left_only_block_ids": overlap["left_only_record_ids"],
            "right_only_block_ids": overlap["right_only_record_ids"],
            "shared_count": overlap["shared_count"],
            "union_count": overlap["union_count"],
            "jaccard_overlap": overlap["jaccard_overlap"],
            "rank_changes": rank_changes,
            "elapsed_seconds_delta": (
                float(right["elapsed_seconds"]) - float(left["elapsed_seconds"])
                if isinstance(left.get("elapsed_seconds"), (int, float))
                and isinstance(right.get("elapsed_seconds"), (int, float))
                else None
            ),
        },
    }
