# Copyright 2026 Aaron John Schlosser, PhD.
"""Compose declared stage complexity into a statement about a whole pipeline.

Each strategy declares its cost in the variables ``n`` (incoming candidates),
``N`` (collection or scope searched), ``k``, ``L``, ``q``, ``g``, ``P``, ``d``
and ``S`` (see ``contracts.py``). This module propagates how many candidates
each stage can see from the configured caps, then reports what the pipeline as a
whole scales with. Retrieval is the only place cost grows with the collection;
everything after a capped retrieval is bounded by that cap, which is the point
of reporting the bounds rather than a single formula.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from .contracts import COMPLEXITY_ORDERS, input_ports
from .models import PipelineDefinition, StrategySpec
from .registry import StrategyRegistry

DEFAULT_ATTEMPTS = 2

_ORDER_IDS = dict(COMPLEXITY_ORDERS)


def _topological(pipeline: PipelineDefinition, active: set[str]) -> list[str]:
    stages = {stage.id: stage for stage in pipeline.stages}
    indegree: dict[str, int] = {stage_id: 0 for stage_id in active}
    for stage_id in active:
        for target in stages[stage_id].edge_targets():
            if target in active:
                indegree[target] += 1
    queue = deque(sorted(stage_id for stage_id, degree in indegree.items() if degree == 0))
    ordered: list[str] = []
    while queue:
        current = queue.popleft()
        ordered.append(current)
        for target in stages[current].edge_targets():
            if target in active:
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)
    return ordered


def _config_int(config: dict[str, Any], key: str | None) -> int | None:
    if not key or key not in config:
        return None
    value = config[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return max(1, int(value))


@dataclass(frozen=True)
class _Flow:
    total: float
    origins: dict[str, float]


def _finite(value: float) -> int | None:
    return None if math.isinf(value) else int(value)


def _merge(flows: list[_Flow]) -> _Flow:
    """Union of candidate flows: each origin once, never more than the sources hold."""

    origins: dict[str, float] = {}
    for flow in flows:
        for origin, cap in flow.origins.items():
            origins[origin] = max(origins.get(origin, 0.0), cap)
    by_origin = sum(origins.values())
    by_source = sum(flow.total for flow in flows)
    return _Flow(min(by_origin, by_source), origins)


def analyze_complexity(
    pipeline: PipelineDefinition,
    registry: StrategyRegistry,
    conditional_stage_ids: set[str],
) -> dict[str, Any]:
    stages = {stage.id: stage for stage in pipeline.stages if stage.enabled}
    specs: dict[str, StrategySpec] = {}
    for stage_id, stage in stages.items():
        spec = registry.get(stage.strategy)
        if spec is not None:
            specs[stage_id] = spec
    active = set(specs)
    if not active:
        return {"stages": [], "summary": None}

    # What each stage hands downstream: ``total`` caps the candidate count and
    # ``origins`` records which retrieval stage each candidate came from, so a
    # candidate that passes through several branches is counted once. ``inf``
    # means only the request or the scope bounds it.
    out_state: dict[str, _Flow] = {}
    in_state: dict[str, _Flow] = {}
    incoming: dict[str, set[str]] = defaultdict(set)
    fallback_in: dict[str, set[str]] = defaultdict(set)
    for stage_id in active:
        stage = stages[stage_id]
        for target in stage.next:
            if target in active:
                incoming[target].add(stage_id)
        for edge in ("on_empty", "on_unavailable", "on_timeout", "on_error"):
            target = getattr(stage, edge)
            if target and target in active and target not in stage.next:
                fallback_in[target].add(stage_id)

    rows: list[dict[str, Any]] = []
    for stage_id in _topological(pipeline, active):
        stage = stages[stage_id]
        spec = specs[stage_id]
        cx = spec.complexity
        takes_candidates = input_ports(spec)[0].data_type == "candidate_set"
        feeders = [out_state[s] for s in sorted(incoming.get(stage_id, ())) if s in out_state]
        feeders += [in_state[s] for s in sorted(fallback_in.get(stage_id, ())) if s in in_state]
        flow = _merge(feeders) if (feeders and takes_candidates) else None
        n_in = _finite(flow.total) if flow else None
        in_state[stage_id] = flow or _Flow(math.inf, {})

        if cx is None:
            out_state[stage_id] = in_state[stage_id]
            continue
        rule = cx.cardinality
        configured = _config_int(stage.config, rule.config_key)
        incoming_flow = flow or _Flow(math.inf, {})
        if rule.rule == "fixed":
            cap = float(rule.default or 1)
            out = _Flow(cap, {stage_id: cap})
        elif rule.rule == "pool":
            out = _Flow(math.inf, {stage_id: math.inf})
        elif rule.rule == "config_cap" and not takes_candidates:
            cap = float(configured) if configured is not None else math.inf
            out = _Flow(cap, {stage_id: cap})
        elif rule.rule == "config_cap" and configured is not None:
            out = _Flow(min(incoming_flow.total, float(configured)), incoming_flow.origins)
        else:
            out = incoming_flow
        out_state[stage_id] = out

        calls = _model_calls(cx.model_calls, stage.config, n_in)
        rows.append(
            {
                "stage_id": stage_id,
                "strategy_id": stage.strategy,
                "time": cx.time,
                "space": cx.space,
                "order": cx.order,
                "order_id": _ORDER_IDS.get(cx.order, "constant"),
                "driver": cx.driver,
                "variables": cx.variables,
                "scales_with_scope": cx.scales_with_scope,
                "n_in": n_in,
                "n_in_bounded": n_in is not None,
                "n_out": _finite(out.total),
                "n_out_bounded": _finite(out.total) is not None,
                "model_calls": calls,
                "conditional": stage_id in conditional_stage_ids,
            }
        )

    return {"stages": rows, "summary": _summary(rows)}


def _model_calls(formula: str, config: dict[str, Any], n_in: int | None) -> dict[str, Any]:
    """Worst-case model invocations of one run of a stage."""

    if formula == "0":
        return {"formula": "0", "max": 0}
    if formula == "1":
        return {"formula": "1", "max": 1}
    if formula == "attempts":
        attempts = _config_int(config, "attempts") or DEFAULT_ATTEMPTS
        return {"formula": "attempts", "max": attempts}
    if formula == "n":
        # One pass per candidate received; ``None`` when only the request bounds it.
        return {"formula": "n", "max": n_in}
    return {"formula": formula, "max": None}


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    unconditional = [row for row in rows if not row["conditional"]]
    pool = unconditional or rows
    dominant = max(pool, key=lambda row: (row["order"], row["scales_with_scope"]))
    terms: list[str] = []
    for row in sorted(pool, key=lambda item: -item["order"]):
        if row["order"] > 0 and row["time"] not in terms:
            terms.append(row["time"])
    scope_stages = [row["stage_id"] for row in pool if row["scales_with_scope"]]
    bounded = [row["n_in"] for row in pool if row["n_in"] is not None]
    candidate_bound = max(bounded) if bounded else None
    unbounded_candidates = any(
        row["n_in"] is None and "n" in row["variables"] for row in pool
    )

    by_driver: dict[str, dict[str, Any]] = {}
    for row in rows:
        calls = row["model_calls"]
        if calls["formula"] == "0":
            continue
        entry = by_driver.setdefault(
            row["driver"], {"stage_ids": [], "max_calls": 0, "calls_known": True}
        )
        entry["stage_ids"].append(row["stage_id"])
        if calls["max"] is None:
            entry["calls_known"] = False
        else:
            entry["max_calls"] += calls["max"]

    return {
        "time_terms": terms[:6],
        "dominant_stage_id": dominant["stage_id"],
        "dominant_time": dominant["time"],
        "dominant_order_id": dominant["order_id"],
        "dominant_driver": dominant["driver"],
        "scales_with_scope": bool(scope_stages),
        "scope_stage_ids": scope_stages,
        # The most candidates any downstream stage can receive, when every
        # stage's cap is configured; None when the request or scope sets it.
        "candidate_bound": None if unbounded_candidates else candidate_bound,
        "candidates_request_bound": unbounded_candidates,
        "model_calls": by_driver,
    }
