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

"""Estimate pipeline and stage latency from recorded execution traces.

Everything here is operational telemetry. It says how long stages took on past
runs, never whether their output was right, and an estimate is only as good as
the sample behind it: every figure carries its sample size and the basis it came
from so a thin estimate cannot pass for a measurement.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from .models import PipelineDefinition, PipelineRunTrace, PipelineStageTrace

# Fewer samples than this are reported but labelled thin.
MIN_RELIABLE_SAMPLES = 5
# A scaling exponent is only fitted with enough distinct input sizes.
MIN_SCALING_POINTS = 8
MAX_MODELS_PER_STRATEGY = 5


def percentile(values: list[float], fraction: float) -> float | None:
    """Linear-interpolated percentile of a non-empty sample."""

    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * min(1.0, max(0.0, fraction))
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(ordered[low])
    return float(ordered[low] + (ordered[high] - ordered[low]) * (position - low))


def _summary(values: list[float]) -> dict[str, Any]:
    count = len(values)
    if not count:
        return {"samples": 0}
    return {
        "samples": count,
        "p50_ms": _round(percentile(values, 0.5)),
        "p90_ms": _round(percentile(values, 0.9)),
        "p95_ms": _round(percentile(values, 0.95)),
        "mean_ms": _round(sum(values) / count),
        "min_ms": _round(min(values)),
        "max_ms": _round(max(values)),
        "reliable": count >= MIN_RELIABLE_SAMPLES,
    }


def _round(value: float | None) -> int | None:
    return None if value is None else int(round(value))


def fit_scaling(points: list[tuple[int, float]]) -> dict[str, Any] | None:
    """Fit elapsed ≈ c·size^b by log-log least squares; None when under-determined."""

    usable = [(size, ms) for size, ms in points if size > 0 and ms > 0]
    if len(usable) < MIN_SCALING_POINTS or len({size for size, _ in usable}) < 3:
        return None
    xs = [math.log(size) for size, _ in usable]
    ys = [math.log(ms) for _, ms in usable]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx == 0:
        return None
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    exponent = sxy / sxx
    syy = sum((y - mean_y) ** 2 for y in ys)
    r_squared = 1.0 if syy == 0 else (sxy * sxy) / (sxx * syy)
    return {
        "exponent": round(exponent, 2),
        "r_squared": round(r_squared, 2),
        "points": len(usable),
        "min_input": min(size for size, _ in usable),
        "max_input": max(size for size, _ in usable),
    }


def _completed(stage: PipelineStageTrace) -> bool:
    return stage.status == "completed" and stage.elapsed_ms is not None


def strategy_latency(runs: Iterable[PipelineRunTrace]) -> dict[str, dict[str, Any]]:
    """Per-strategy latency, throughput, model breakdown and observed scaling."""

    elapsed: dict[str, list[float]] = defaultdict(list)
    per_item: dict[str, list[float]] = defaultdict(list)
    models: dict[str, dict[tuple[str, str], list[float]]] = defaultdict(lambda: defaultdict(list))
    points: dict[str, list[tuple[int, float]]] = defaultdict(list)
    scope_points: dict[str, list[tuple[int, float]]] = defaultdict(list)
    executions: dict[str, int] = defaultdict(int)
    for run in runs:
        for stage in run.stages:
            executions[stage.strategy_id] += 1
            if not _completed(stage):
                continue
            ms = float(stage.elapsed_ms or 0)
            elapsed[stage.strategy_id].append(ms)
            if stage.input_count:
                per_item[stage.strategy_id].append(ms / stage.input_count)
                points[stage.strategy_id].append((int(stage.input_count), ms))
            scope = (stage.parameters or {}).get("scope_size")
            if isinstance(scope, int) and not isinstance(scope, bool) and scope > 0:
                scope_points[stage.strategy_id].append((scope, ms))
            if stage.model or stage.provider:
                models[stage.strategy_id][(stage.provider or "", stage.model or "")].append(ms)

    result: dict[str, dict[str, Any]] = {}
    for strategy_id, values in elapsed.items():
        by_model = sorted(
            (
                {"provider": provider or None, "model": model or None, **_summary(samples)}
                for (provider, model), samples in models[strategy_id].items()
            ),
            key=lambda row: -int(row["samples"]),
        )[:MAX_MODELS_PER_STRATEGY]
        result[strategy_id] = {
            **_summary(values),
            "executions": executions[strategy_id],
            "median_ms_per_input": _round(percentile(per_item[strategy_id], 0.5)),
            "by_model": by_model,
            "observed_scaling": fit_scaling(points[strategy_id]),
            # Against the size of the collection or scope searched (counts only),
            # which candidate counts cannot reveal for a scan.
            "observed_scope_scaling": fit_scaling(scope_points[strategy_id]),
        }
    return result


def _stage_samples(runs: Iterable[PipelineRunTrace]) -> dict[str, dict[str, Any]]:
    """Per stage id: completed elapsed times and how often it was reached."""

    rows: dict[str, dict[str, Any]] = {}
    run_count = 0
    for run in runs:
        run_count += 1
        for stage in run.stages:
            row = rows.setdefault(
                stage.stage_id,
                {"strategy_id": stage.strategy_id, "elapsed": [], "reached": 0},
            )
            if stage.status != "pending":
                row["reached"] += 1
            if _completed(stage):
                row["elapsed"].append(float(stage.elapsed_ms or 0))
    for row in rows.values():
        row["runs"] = run_count
    return rows


def run_latency(runs: Iterable[PipelineRunTrace]) -> dict[str, Any]:
    totals = [
        float(run.total_elapsed_ms)
        for run in runs
        if run.status == "completed" and run.total_elapsed_ms is not None
    ]
    return _summary(totals)


def estimate_pipeline_latency(
    pipeline: PipelineDefinition,
    *,
    exact_runs: list[PipelineRunTrace],
    same_pipeline_runs: list[PipelineRunTrace],
    by_strategy: dict[str, dict[str, Any]],
    conditional_stage_ids: set[str],
) -> dict[str, Any]:
    """Per-stage and whole-pipeline latency estimates with their provenance.

    A stage takes its figure from, in order: the same stage in runs of this exact
    definition, the same stage id in other versions of this pipeline, then the
    strategy across all pipelines. ``basis`` names which, so a draft that has
    never run still gets an estimate that says it is borrowed.
    """

    exact = _stage_samples(exact_runs)
    same = _stage_samples(same_pipeline_runs)
    stage_rows: list[dict[str, Any]] = []
    enabled = {stage.id: stage for stage in pipeline.stages if stage.enabled}

    for stage in pipeline.stages:
        if not stage.enabled:
            continue
        figure: dict[str, Any] = {"samples": 0}
        basis = "none"
        reach: float | None = None
        for label, table in (("this_pipeline", exact), ("same_stage", same)):
            row = table.get(stage.id)
            if row is not None and row["strategy_id"] == stage.strategy and row["elapsed"]:
                figure = _summary(row["elapsed"])
                basis = label
                reach = row["reached"] / row["runs"] if row["runs"] else None
                if figure["reliable"]:
                    break
        if basis == "none" or not figure.get("reliable"):
            wide = by_strategy.get(stage.strategy)
            if wide and wide.get("samples", 0) > figure.get("samples", 0):
                figure = {key: wide[key] for key in figure_keys(wide)}
                basis = "strategy"
        conditional = stage.id in conditional_stage_ids
        if reach is None:
            reach = 0.0 if conditional else 1.0
        stage_rows.append(
            {
                "stage_id": stage.id,
                "strategy_id": stage.strategy,
                "basis": basis,
                "conditional": conditional,
                "reach": round(reach, 3),
                **figure,
                "median_ms_per_input": (by_strategy.get(stage.strategy) or {}).get(
                    "median_ms_per_input"
                ),
                # Strategy-wide, so the editor can show which model a stage was
                # slow on and whether elapsed time tracks input size.
                "by_model": (by_strategy.get(stage.strategy) or {}).get("by_model", []),
                "observed_scaling": (by_strategy.get(stage.strategy) or {}).get(
                    "observed_scaling"
                ),
                "observed_scope_scaling": (by_strategy.get(stage.strategy) or {}).get(
                    "observed_scope_scaling"
                ),
            }
        )

    known = {row["stage_id"]: row for row in stage_rows}
    typical = sum((row.get("p50_ms") or 0) * row["reach"] for row in stage_rows)
    slow = sum((row.get("p90_ms") or 0) * row["reach"] for row in stage_rows)
    critical = _critical_path(pipeline, enabled, known)
    unconditional = [row for row in stage_rows if not row["conditional"]]
    with_data = [row for row in unconditional if row["samples"] > 0]
    total = typical or 0
    for row in stage_rows:
        row["share"] = round((row.get("p50_ms") or 0) * row["reach"] / total, 3) if total else 0.0
    slowest = max(stage_rows, key=lambda row: (row.get("p50_ms") or 0) * row["reach"], default=None)

    return {
        "stages": stage_rows,
        "typical_ms": _round(typical),
        "slow_ms": _round(slow),
        "critical_path_ms": _round(critical["p50"]),
        "critical_path_slow_ms": _round(critical["p90"]),
        "critical_path": critical["stages"],
        "slowest_stage_id": slowest["stage_id"] if slowest and total else None,
        "coverage": round(len(with_data) / len(unconditional), 3) if unconditional else 0.0,
        "reliable": bool(unconditional) and all(row.get("reliable") for row in unconditional),
        "observed_runs": run_latency(exact_runs),
        "observed_pipeline_runs": run_latency(same_pipeline_runs),
    }


def figure_keys(summary: dict[str, Any]) -> list[str]:
    return [
        key
        for key in ("samples", "p50_ms", "p90_ms", "p95_ms", "mean_ms", "min_ms", "max_ms", "reliable")
        if key in summary
    ]


def _critical_path(
    pipeline: PipelineDefinition,
    enabled: dict[str, Any],
    known: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Longest chain by median (and by p90) over unconditional ``next`` edges.

    If branches run concurrently this is the wall-clock bound; the sum of all
    stages (``typical_ms``) is the figure when they run one after another.
    """

    order: dict[str, list[str]] = {
        stage.id: [t for t in stage.next if t in enabled] for stage in pipeline.stages if stage.enabled
    }
    memo: dict[tuple[str, str], tuple[float, list[str]]] = {}

    def longest(stage_id: str, metric: str) -> tuple[float, list[str]]:
        key = (stage_id, metric)
        if key in memo:
            return memo[key]
        memo[key] = (0.0, [stage_id])  # cycle guard; validation rejects cycles
        row = known.get(stage_id, {})
        own = float(row.get(metric) or 0)
        best: tuple[float, list[str]] = (0.0, [])
        for target in order.get(stage_id, []):
            candidate = longest(target, metric)
            if candidate[0] > best[0] or not best[1]:
                best = candidate
        memo[key] = (own + best[0], [stage_id, *best[1]])
        return memo[key]

    best = {"p50": 0.0, "p90": 0.0, "stages": []}
    for metric, label in (("p50_ms", "p50"), ("p90_ms", "p90")):
        top: tuple[float, list[str]] = (0.0, [])
        for entry in pipeline.entry_stage_ids:
            if entry in order:
                candidate = longest(entry, metric)
                if candidate[0] >= top[0]:
                    top = candidate
        best[label] = top[0]
        if label == "p50":
            best["stages"] = top[1]
    return best
