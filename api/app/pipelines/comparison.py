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

from pydantic import BaseModel, Field, model_validator

from ..models import RAGRunRequest


class PipelineVersionRef(BaseModel):
    pipeline_id: str = Field(min_length=1, max_length=160)
    version: int = Field(ge=1)


class ResearchPipelineComparisonRequest(BaseModel):
    request: RAGRunRequest
    left: PipelineVersionRef
    right: PipelineVersionRef


class ResearchPipelineBenchmarkCase(BaseModel):
    """One fixed prompt/corpus case used to compare two Research pipelines."""

    case_id: str = Field(min_length=1, max_length=120)
    label: str = Field(default="", max_length=240)
    request: RAGRunRequest
    expected_record_ids: list[str] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def normalize_case(self) -> "ResearchPipelineBenchmarkCase":
        self.case_id = self.case_id.strip()
        self.label = self.label.strip()
        self.expected_record_ids = list(
            dict.fromkeys(
                value.strip()
                for value in self.expected_record_ids
                if value and value.strip()
            )
        )
        return self


class ResearchPipelineBenchmarkRequest(BaseModel):
    """A bounded, non-persistent batch of fixed Research comparison cases."""

    cases: list[ResearchPipelineBenchmarkCase] = Field(min_length=1, max_length=25)
    left: PipelineVersionRef
    right: PipelineVersionRef

    @model_validator(mode="after")
    def unique_case_ids(self) -> "ResearchPipelineBenchmarkRequest":
        case_ids = [item.case_id for item in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Benchmark case IDs must be unique.")
        return self


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



def expected_record_coverage(
    actual_record_ids: list[str],
    expected_record_ids: list[str],
) -> dict[str, Any]:
    """Describe benchmark-ground-truth coverage without declaring a winner."""

    expected = list(dict.fromkeys(str(value) for value in expected_record_ids if str(value)))
    actual = set(str(value) for value in actual_record_ids if str(value))
    matched = [record_id for record_id in expected if record_id in actual]
    return {
        "expected_count": len(expected),
        "matched_count": len(matched),
        "matched_record_ids": matched,
        "coverage": (len(matched) / len(expected)) if expected else None,
    }


def benchmark_case_result(
    case: ResearchPipelineBenchmarkCase,
    left_result: dict[str, Any],
    right_result: dict[str, Any],
) -> dict[str, Any]:
    """Compare one fixed benchmark case using the same safe dry-run summaries."""

    compared = compare_research_dry_runs(left_result, right_result)
    expected = list(case.expected_record_ids)
    left_candidates = list(compared["left"]["candidates"]["pre_rerank"]["record_ids"])
    right_candidates = list(compared["right"]["candidates"]["pre_rerank"]["record_ids"])
    left_evidence = [str(item["record_id"]) for item in compared["left"]["evidence"]]
    right_evidence = [str(item["record_id"]) for item in compared["right"]["evidence"]]
    return {
        "case_id": case.case_id,
        "label": case.label,
        "status": "completed",
        "expected_record_ids": expected,
        "comparison": compared,
        "expected_coverage": {
            "left": {
                "candidate": expected_record_coverage(left_candidates, expected),
                "final_evidence": expected_record_coverage(left_evidence, expected),
            },
            "right": {
                "candidate": expected_record_coverage(right_candidates, expected),
                "final_evidence": expected_record_coverage(right_evidence, expected),
            },
        },
    }


def _mean(values: list[float]) -> float | None:
    return (sum(values) / len(values)) if values else None


def aggregate_research_benchmark(
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate completed benchmark cases descriptively.

    The aggregate deliberately reports measurements rather than selecting a
    better pipeline. Expected-record coverage is calculated only when a case
    supplies reviewer-curated expected IDs.
    """

    completed = [item for item in cases if item.get("status") == "completed"]
    failed = [item for item in cases if item.get("status") != "completed"]

    candidate_overlap: list[float] = []
    evidence_overlap: list[float] = []
    left_elapsed: list[float] = []
    right_elapsed: list[float] = []
    left_context: list[float] = []
    right_context: list[float] = []
    left_expected_candidate: list[float] = []
    right_expected_candidate: list[float] = []
    left_expected_final: list[float] = []
    right_expected_final: list[float] = []
    left_cross_encoder_calls = 0
    right_cross_encoder_calls = 0

    for item in completed:
        compared = item["comparison"]
        comparison = compared["comparison"]
        candidate_overlap.append(float(comparison["candidate_overlap"]["jaccard_overlap"]))
        evidence_overlap.append(float(comparison["jaccard_overlap"]))

        left = compared["left"]
        right = compared["right"]
        if isinstance(left.get("elapsed_seconds"), (int, float)):
            left_elapsed.append(float(left["elapsed_seconds"]))
        if isinstance(right.get("elapsed_seconds"), (int, float)):
            right_elapsed.append(float(right["elapsed_seconds"]))
        if isinstance(left.get("context_characters"), int):
            left_context.append(float(left["context_characters"]))
        if isinstance(right.get("context_characters"), int):
            right_context.append(float(right["context_characters"]))
        left_cross_encoder_calls += int(
            (left.get("resource_use") or {}).get("cross_encoder_calls") or 0
        )
        right_cross_encoder_calls += int(
            (right.get("resource_use") or {}).get("cross_encoder_calls") or 0
        )

        coverage = item.get("expected_coverage") or {}
        for side, candidate_values, final_values in (
            ("left", left_expected_candidate, left_expected_final),
            ("right", right_expected_candidate, right_expected_final),
        ):
            side_coverage = coverage.get(side) or {}
            candidate = (side_coverage.get("candidate") or {}).get("coverage")
            final_evidence = (side_coverage.get("final_evidence") or {}).get("coverage")
            if isinstance(candidate, (int, float)):
                candidate_values.append(float(candidate))
            if isinstance(final_evidence, (int, float)):
                final_values.append(float(final_evidence))

    return {
        "case_count": len(cases),
        "completed_case_count": len(completed),
        "failed_case_count": len(failed),
        "mean_candidate_overlap": _mean(candidate_overlap),
        "mean_final_evidence_overlap": _mean(evidence_overlap),
        "left": {
            "mean_elapsed_seconds": _mean(left_elapsed),
            "mean_context_characters": _mean(left_context),
            "cross_encoder_calls": left_cross_encoder_calls,
            "mean_expected_candidate_coverage": _mean(left_expected_candidate),
            "mean_expected_final_coverage": _mean(left_expected_final),
        },
        "right": {
            "mean_elapsed_seconds": _mean(right_elapsed),
            "mean_context_characters": _mean(right_context),
            "cross_encoder_calls": right_cross_encoder_calls,
            "mean_expected_candidate_coverage": _mean(right_expected_candidate),
            "mean_expected_final_coverage": _mean(right_expected_final),
        },
    }
