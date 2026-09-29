# Copyright 2026 Aaron John Schlosser, PhD.
"""Aggregate operational metrics from immutable pipeline execution traces.

The dashboard deliberately summarizes operational telemetry only. It never
treats retrieval, ranking, fallback, or latency measurements as scholarly
evidence or source authority.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .models import PipelineRunTrace, PipelineStageTrace


def _percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(max(0, int(value)) for value in values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def _average(values: list[int]) -> int | None:
    if not values:
        return None
    return int(round(sum(values) / len(values)))


def _stage_issue(stage: PipelineStageTrace) -> bool:
    return stage.status in {"failed", "unavailable", "timed_out"} or bool(
        stage.fallback_reason
    )


def aggregate_pipeline_metrics(runs: list[PipelineRunTrace]) -> dict[str, Any]:
    """Summarize a bounded trace sample for System Data operational review."""

    run_statuses: Counter[str] = Counter()
    run_elapsed: list[int] = []
    fallback_run_count = 0
    warning_run_count = 0
    feature_rows: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "run_count": 0,
            "failed_count": 0,
            "fallback_run_count": 0,
            "warning_run_count": 0,
            "elapsed": [],
        }
    )
    strategy_rows: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "stage_ids": set(),
            "executions": 0,
            "statuses": Counter(),
            "fallback_count": 0,
            "warning_count": 0,
            "model_call_count": 0,
            "elapsed": [],
            "input_counts": [],
            "output_counts": [],
        }
    )

    for run in runs:
        run_statuses[run.status] += 1
        if run.total_elapsed_ms is not None:
            run_elapsed.append(int(run.total_elapsed_ms))

        has_fallback = any(_stage_issue(stage) for stage in run.stages)
        has_warning = bool(run.warnings) or any(stage.warnings for stage in run.stages)
        fallback_run_count += int(has_fallback)
        warning_run_count += int(has_warning)

        feature = feature_rows[run.feature]
        feature["run_count"] += 1
        feature["failed_count"] += int(run.status == "failed")
        feature["fallback_run_count"] += int(has_fallback)
        feature["warning_run_count"] += int(has_warning)
        if run.total_elapsed_ms is not None:
            feature["elapsed"].append(int(run.total_elapsed_ms))

        for stage in run.stages:
            row = strategy_rows[stage.strategy_id]
            row["stage_ids"].add(stage.stage_id)
            row["executions"] += 1
            row["statuses"][stage.status] += 1
            row["fallback_count"] += int(bool(stage.fallback_reason))
            row["warning_count"] += len(stage.warnings or [])
            row["model_call_count"] += int(bool(stage.model or stage.provider))
            if stage.elapsed_ms is not None:
                row["elapsed"].append(int(stage.elapsed_ms))
            if stage.input_count is not None:
                row["input_counts"].append(int(stage.input_count))
            if stage.output_count is not None:
                row["output_counts"].append(int(stage.output_count))

    features = []
    for feature_name, row in feature_rows.items():
        elapsed = row.pop("elapsed")
        features.append(
            {
                "feature": feature_name,
                **row,
                "average_elapsed_ms": _average(elapsed),
                "p95_elapsed_ms": _percentile(elapsed, 0.95),
            }
        )
    features.sort(key=lambda row: (-int(row["run_count"]), str(row["feature"])))

    strategies = []
    for strategy_id, row in strategy_rows.items():
        elapsed = row.pop("elapsed")
        input_counts = row.pop("input_counts")
        output_counts = row.pop("output_counts")
        statuses = row.pop("statuses")
        issue_count = sum(
            int(statuses.get(status, 0))
            for status in ("failed", "unavailable", "timed_out")
        )
        strategies.append(
            {
                "strategy_id": strategy_id,
                "stage_ids": sorted(row.pop("stage_ids")),
                **row,
                "issue_count": issue_count,
                "status_counts": dict(sorted(statuses.items())),
                "average_elapsed_ms": _average(elapsed),
                "p95_elapsed_ms": _percentile(elapsed, 0.95),
                "average_input_count": _average(input_counts),
                "average_output_count": _average(output_counts),
            }
        )
    strategies.sort(
        key=lambda row: (
            -int(row["issue_count"]),
            -int(row["fallback_count"]),
            -int(row["executions"]),
            str(row["strategy_id"]),
        )
    )

    return {
        "sampled_run_count": len(runs),
        "status_counts": dict(sorted(run_statuses.items())),
        "fallback_run_count": fallback_run_count,
        "warning_run_count": warning_run_count,
        "average_run_elapsed_ms": _average(run_elapsed),
        "p95_run_elapsed_ms": _percentile(run_elapsed, 0.95),
        "features": features,
        "strategies": strategies,
    }
