# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.pipelines.metrics import aggregate_pipeline_metrics
from app.pipelines.models import PipelineRunTrace, PipelineStageTrace


def _stage(
    stage_id: str,
    strategy_id: str,
    *,
    status: str = "completed",
    elapsed_ms: int | None = None,
    fallback_reason: str | None = None,
    warnings: list[str] | None = None,
    model: str | None = None,
    input_count: int | None = None,
    output_count: int | None = None,
) -> PipelineStageTrace:
    return PipelineStageTrace(
        stage_id=stage_id,
        strategy_id=strategy_id,
        status=status,
        elapsed_ms=elapsed_ms,
        fallback_reason=fallback_reason,
        warnings=warnings or [],
        model=model,
        input_count=input_count,
        output_count=output_count,
    )


def _run(
    run_id: str,
    feature: str,
    elapsed_ms: int,
    stages: list[PipelineStageTrace],
    *,
    status: str = "completed",
    warnings: list[str] | None = None,
) -> PipelineRunTrace:
    started = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
    return PipelineRunTrace(
        run_id=run_id,
        feature=feature,
        pipeline_id=f"{feature}.pipeline",
        pipeline_version=1,
        resolved_pipeline={"pipeline_id": f"{feature}.pipeline"},
        resolved_hash="a" * 64,
        status=status,
        started_at=started,
        finished_at=started + timedelta(milliseconds=elapsed_ms),
        total_elapsed_ms=elapsed_ms,
        warnings=warnings or [],
        stages=stages,
    )


def test_pipeline_metrics_summarize_runs_fallbacks_and_stage_health() -> None:
    runs = [
        _run(
            "r1",
            "research",
            100,
            [
                _stage(
                    "retrieve",
                    "retrieve.chroma_similarity",
                    elapsed_ms=20,
                    input_count=1,
                    output_count=8,
                ),
                _stage(
                    "rerank",
                    "rerank.cross_encoder",
                    elapsed_ms=40,
                    input_count=8,
                    output_count=4,
                    model="ce-a",
                ),
            ],
        ),
        _run(
            "r2",
            "research",
            300,
            [
                _stage(
                    "retrieve",
                    "retrieve.chroma_similarity",
                    elapsed_ms=30,
                    input_count=1,
                    output_count=6,
                ),
                _stage(
                    "rerank",
                    "rerank.cross_encoder",
                    status="unavailable",
                    elapsed_ms=50,
                    fallback_reason="model unavailable",
                    input_count=6,
                    output_count=6,
                ),
            ],
            warnings=["reranker fallback"],
        ),
        _run(
            "r3",
            "metadata_precedents",
            500,
            [
                _stage(
                    "retrieve",
                    "retrieve.metadata_exemplars",
                    status="failed",
                    elapsed_ms=80,
                    fallback_reason="embedding backend failed",
                ),
            ],
            status="failed",
        ),
    ]

    result = aggregate_pipeline_metrics(runs)

    assert result["sampled_run_count"] == 3
    assert result["status_counts"] == {"completed": 2, "failed": 1}
    assert result["fallback_run_count"] == 2
    assert result["warning_run_count"] == 1
    assert result["average_run_elapsed_ms"] == 300
    assert result["p95_run_elapsed_ms"] == 500

    features = {row["feature"]: row for row in result["features"]}
    assert features["research"]["run_count"] == 2
    assert features["research"]["fallback_run_count"] == 1
    assert features["metadata_precedents"]["failed_count"] == 1

    workflows = {row["category"]: row for row in result["workflows"]}
    assert workflows["research"]["run_count"] == 2
    assert workflows["research"]["features"] == ["research"]
    assert workflows["metadata"]["failed_count"] == 1
    assert workflows["metadata"]["features"] == ["metadata_precedents"]

    strategies = {row["strategy_id"]: row for row in result["strategies"]}
    rerank = strategies["rerank.cross_encoder"]
    assert rerank["executions"] == 2
    assert rerank["issue_count"] == 1
    assert rerank["fallback_count"] == 1
    assert rerank["model_call_count"] == 1
    assert rerank["average_elapsed_ms"] == 45
    assert rerank["average_input_count"] == 7
    assert rerank["average_output_count"] == 5
    assert rerank["status_counts"] == {"completed": 1, "unavailable": 1}


def test_pipeline_metrics_empty_sample_is_explicit() -> None:
    result = aggregate_pipeline_metrics([])

    assert result == {
        "sampled_run_count": 0,
        "status_counts": {},
        "fallback_run_count": 0,
        "warning_run_count": 0,
        "average_run_elapsed_ms": None,
        "p95_run_elapsed_ms": None,
        "workflows": [],
        "features": [],
        "strategies": [],
    }
