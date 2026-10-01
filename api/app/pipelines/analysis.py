# Copyright 2026 Aaron John Schlosser, PhD.
"""One call that explains a pipeline: its wiring, cost and expected latency."""

from __future__ import annotations

import threading
import time
from typing import Any, Protocol

from .complexity import analyze_complexity
from .latency import estimate_pipeline_latency, strategy_latency
from .models import PipelineDefinition, PipelineRunTrace
from .purposes import purpose_registry
from .registry import StrategyRegistry
from .wiring import resolve_wiring


def conditional_stages(pipeline: PipelineDefinition) -> set[str]:
    """Enabled stages reached only through a fallback edge, never a normal one."""

    entries = set(pipeline.entry_stage_ids)
    normal: set[str] = set(entries)
    fallback: set[str] = set()
    for stage in pipeline.stages:
        normal.update(stage.next)
        for target in stage.edge_targets():
            if target not in stage.next:
                fallback.add(target)
    return {stage.id for stage in pipeline.stages if stage.id in fallback and stage.id not in normal}


def analyze_pipeline(
    pipeline: PipelineDefinition,
    registry: StrategyRegistry,
    *,
    resolved_hash: str,
    sample_runs: list[PipelineRunTrace],
    pipeline_runs: list[PipelineRunTrace],
) -> dict[str, Any]:
    """Wiring, declared complexity and observed latency for ``pipeline``.

    ``sample_runs`` is a recent cross-pipeline sample (for strategy-wide
    figures); ``pipeline_runs`` are runs of this pipeline id in any version.
    """

    purpose = purpose_registry.get(pipeline.purpose)
    wiring = resolve_wiring(pipeline, registry, purpose)
    conditional = conditional_stages(pipeline)
    exact = [run for run in pipeline_runs if run.resolved_hash == resolved_hash]
    by_strategy = strategy_latency(sample_runs)
    return {
        "wiring": {
            "stages": wiring["stages"],
            "run_inputs": wiring["run_inputs"],
            "ordering_only_edges": wiring["ordering_only_edges"],
        },
        "complexity": analyze_complexity(pipeline, registry, conditional),
        "latency": estimate_pipeline_latency(
            pipeline,
            exact_runs=exact,
            same_pipeline_runs=pipeline_runs,
            by_strategy=by_strategy,
            conditional_stage_ids=conditional,
        ),
        "sample": {
            "runs": len(sample_runs),
            "pipeline_runs": len(pipeline_runs),
            "exact_runs": len(exact),
        },
    }


class _RunSource(Protocol):
    def list_runs(
        self,
        *,
        pipeline_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineRunTrace]: ...


class TraceSampler:
    """Short-lived cache of recent traces so editing a draft does not re-read them.

    Trace reads are one query per run; an editor asking for a fresh analysis on
    every change must not turn into hundreds of reads each time.
    """

    def __init__(
        self,
        source: _RunSource,
        *,
        ttl_seconds: float = 30.0,
        sample_limit: int = 400,
        pipeline_limit: int = 200,
    ) -> None:
        self.source = source
        self.ttl_seconds = ttl_seconds
        self.sample_limit = sample_limit
        self.pipeline_limit = pipeline_limit
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[float, list[PipelineRunTrace]]] = {}

    def _cached(self, key: str, **filters: Any) -> list[PipelineRunTrace]:
        now = time.monotonic()
        with self._lock:
            hit = self._cache.get(key)
            if hit is not None and now - hit[0] < self.ttl_seconds:
                return hit[1]
        rows = self.source.list_runs(**filters)
        with self._lock:
            self._cache[key] = (now, rows)
            if len(self._cache) > 64:
                oldest = min(self._cache, key=lambda name: self._cache[name][0])
                self._cache.pop(oldest, None)
        return rows

    def sample(self) -> list[PipelineRunTrace]:
        return self._cached("*", limit=self.sample_limit, offset=0)

    def for_pipeline(self, pipeline_id: str) -> list[PipelineRunTrace]:
        return self._cached(
            f"pipeline:{pipeline_id}", pipeline_id=pipeline_id, limit=self.pipeline_limit, offset=0
        )

    def invalidate(self) -> None:
        with self._lock:
            self._cache.clear()
