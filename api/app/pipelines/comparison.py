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
    return {
        "pipeline": {
            key: pipeline.get(key)
            for key in ("pipeline_id", "pipeline_version", "pipeline_hash", "name", "purpose")
        },
        "elapsed_seconds": result.get("elapsed_seconds"),
        "warnings": list(result.get("warnings") or []),
        "retrieval": retrieval,
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
    left_set = set(left_ids)
    right_set = set(right_ids)
    shared = [record_id for record_id in left_ids if record_id in right_set]
    union = left_set | right_set

    left_rank = {record_id: index for index, record_id in enumerate(left_ids, start=1)}
    right_rank = {record_id: index for index, record_id in enumerate(right_ids, start=1)}
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
            "shared_record_ids": shared,
            "left_only_record_ids": [record_id for record_id in left_ids if record_id not in right_set],
            "right_only_record_ids": [record_id for record_id in right_ids if record_id not in left_set],
            "shared_count": len(shared),
            "union_count": len(union),
            "jaccard_overlap": (len(shared) / len(union)) if union else 1.0,
            "rank_changes": rank_changes,
        },
    }
