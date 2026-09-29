# Copyright 2026 Aaron John Schlosser, PhD.
"""Dataflow runtime for general Vector Store search pipelines.

Store search resolves an immutable ``vector_store_search`` pipeline and runs
its graph over a closed set of registered strategies. A stage runs only when
an edge routes to it:

- a stage that produces results sends them along every ``next`` edge;
- an empty result follows ``on_empty``; a stage that is unavailable, times
  out, or fails follows ``on_unavailable``/``on_timeout``/``on_error`` with the
  input it received;
- an unavailable or failed stage with no matching edge raises, so a search
  never quietly returns nothing because a stage broke;
- ``fusion.rrf`` merges every branch that reached it.

Permission checks, researcher text limits, and collection visibility stay in
the route. Pipelines tune retrieval; they never decide who may see what.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ..retrieval_selection import mmr_select
from .models import PipelineDefinition, PipelineRunTrace, PipelineStageDefinition
from .registry import reject_unhonoured_config
from .service import pipeline_hash
from .trace_safety import trace_stage

SEARCH_FEATURE = "vector_store_search"
SEARCH_PURPOSE = "vector_store_search"
MODE_PIPELINES = {
    mode: (f"store_search.{mode}", 1)
    for mode in ("similarity", "mmr", "hybrid", "lexical", "keyword", "filter")
}

_QUERY = "query.passthrough"
_DENSE = "retrieve.chroma_similarity"
_LEXICAL = "retrieve.lexical_bm25"
_KEYWORD = "retrieve.store_keyword"
_FILTER = "retrieve.store_filter"
_RRF = "fusion.rrf"
_MMR = "select.mmr"
_SELECT = "select.top_k"
SUPPORTED_STRATEGIES = frozenset({_QUERY, _DENSE, _LEXICAL, _KEYWORD, _FILTER, _RRF, _MMR, _SELECT})
_RETRIEVERS = frozenset({_DENSE, _LEXICAL, _KEYWORD, _FILTER})
_LEG_TYPES = {_DENSE: "semantic", _LEXICAL: "lexical", _KEYWORD: "keyword", _FILTER: "filter"}
_FALLBACK_EDGE = {"unavailable": "on_unavailable", "timed_out": "on_timeout", "failed": "on_error"}


@dataclass(frozen=True)
class StoreSearchPlan:
    pipeline: PipelineDefinition
    stages: dict[str, PipelineStageDefinition]
    order: list[str]


@dataclass(frozen=True)
class StoreSearchRequest:
    store: str
    query: str
    n_results: int
    where: dict[str, Any] | None
    fetch_k: int
    lambda_mult: float


@dataclass(frozen=True)
class StoreSearchExecution:
    results: list[dict[str, Any]]
    trace: PipelineRunTrace


class _StageFailure(Exception):
    def __init__(self, status: str, error: Exception) -> None:
        super().__init__(str(error))
        self.status = status
        self.error = error


def compile_store_search_pipeline(pipeline: PipelineDefinition) -> StoreSearchPlan:
    """Check that a graph is an executable store-search dataflow."""

    if pipeline.purpose != SEARCH_PURPOSE:
        raise ValueError("Store-search runtime can only compile vector_store_search pipelines.")
    reject_unhonoured_config(pipeline, "store-search")
    stages = {stage.id: stage for stage in pipeline.stages if stage.enabled}
    unsupported = sorted({stage.strategy for stage in stages.values()} - SUPPORTED_STRATEGIES)
    if unsupported:
        raise ValueError("Store-search runtime does not implement strategy stage(s): " + ", ".join(unsupported))
    for stage in stages.values():
        disabled = [target for target in stage.edge_targets() if target not in stages]
        if disabled:
            raise ValueError(f"Stage {stage.id!r} routes to disabled stage(s): {', '.join(disabled)}.")
    if len(pipeline.entry_stage_ids) != 1 or pipeline.entry_stage_ids[0] not in stages:
        raise ValueError("Store search requires exactly one enabled entry stage.")
    selects = [stage for stage in stages.values() if stage.strategy == _SELECT]
    if len(selects) != 1 or selects[0].edge_targets():
        raise ValueError("Store search requires exactly one terminal top-K selection stage.")
    for stage in stages.values():
        if stage.strategy != _SELECT and not stage.next:
            raise ValueError(f"Stage {stage.id!r} has no next stage, so its results could never be returned.")
        if stage.strategy == _QUERY and stage.id != pipeline.entry_stage_ids[0]:
            raise ValueError("The query stage must be the entry stage.")
        if stage.strategy != _QUERY and len(stage.next) > 1:
            raise ValueError(f"Only the query stage may fan out; {stage.id!r} has several next stages.")
    incoming: dict[str, list[PipelineStageDefinition]] = defaultdict(list)
    for stage in stages.values():
        for target in stage.edge_targets():
            incoming[target].append(stage)
    for stage in stages.values():
        if stage.strategy == _MMR:
            sources = incoming[stage.id]
            if not sources or any(source.strategy != _DENSE or source.next != [stage.id] for source in sources):
                raise ValueError(
                    "MMR needs query and candidate embeddings, so it may only follow semantic similarity."
                )
    order = _topological_order(pipeline, stages)
    return StoreSearchPlan(pipeline=pipeline, stages=stages, order=order)


def _topological_order(pipeline: PipelineDefinition, stages: dict[str, PipelineStageDefinition]) -> list[str]:
    """Kahn order with definition order as the tie-break, so fused branches keep a stable order."""

    position = {stage.id: index for index, stage in enumerate(pipeline.stages)}
    indegree = {stage_id: 0 for stage_id in stages}
    for stage in stages.values():
        for target in set(stage.edge_targets()):
            indegree[target] += 1
    ready = deque(sorted((sid for sid, degree in indegree.items() if degree == 0), key=position.get))
    order: list[str] = []
    while ready:
        stage_id = ready.popleft()
        order.append(stage_id)
        for target in sorted(set(stages[stage_id].edge_targets()), key=position.get):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
        ready = deque(sorted(ready, key=position.get))
    if len(order) != len(stages):
        raise ValueError("Store-search pipelines must be acyclic.")
    return order


def _candidate_depth(stage: PipelineStageDefinition, plan: StoreSearchPlan, request: StoreSearchRequest) -> int:
    """Candidate depth: stage ``fetch_k`` when set, else the depth its consumer needs.

    MMR draws from the request's ``fetch_k`` pool; fusion draws a bounded pool
    four times the result count (at least 32, at most 400); anything else
    fetches exactly the requested number of results.
    """

    if "fetch_k" in stage.config:
        return int(stage.config["fetch_k"])
    consumer = plan.stages[stage.next[0]].strategy if stage.next else None
    if consumer == _MMR:
        return max(request.n_results, request.fetch_k)
    if consumer == _RRF:
        return min(max(request.n_results * 4, 32), 400)
    return request.n_results


class _Runner:
    def __init__(self, store: Any, plan: StoreSearchPlan, request: StoreSearchRequest) -> None:
        self.store = store
        self.plan = plan
        self.request = request

    def run(self, stage: PipelineStageDefinition, inputs: list[tuple[str, Any]]) -> tuple[Any, dict[str, Any]]:
        strategy = stage.strategy
        try:
            if strategy == _QUERY:
                return self.request.query.strip(), {}
            if strategy == _DENSE:
                depth = _candidate_depth(stage, self.plan, self.request)
                if stage.next and self.plan.stages[stage.next[0]].strategy == _MMR:
                    rows = self.store.mmr_candidates(self.request.store, self.request.query, depth, self.request.where)
                else:
                    rows = self.store.search(self.request.store, self.request.query, depth, self.request.where)
                return rows, {"parameters": {"fetch_k": depth}}
            if strategy == _LEXICAL:
                depth = _candidate_depth(stage, self.plan, self.request)
                if not self.request.query.strip() or not self.store._lexical_tokens(self.request.query):
                    raise _StageFailure("unavailable", ValueError("The query has no lexical terms."))
                rows = self.store.lexical_search(self.request.store, self.request.query, depth, self.request.where)
                return rows, {"parameters": {"fetch_k": depth}}
            if strategy == _KEYWORD:
                depth = _candidate_depth(stage, self.plan, self.request)
                rows = self.store.keyword_search(self.request.store, self.request.query, depth, self.request.where)
                return rows, {"parameters": {"fetch_k": depth}}
            if strategy == _FILTER:
                depth = _candidate_depth(stage, self.plan, self.request)
                return self.store.filter_search(self.request.store, depth, self.request.where), {
                    "parameters": {"fetch_k": depth}
                }
            if strategy == _RRF:
                return self._fuse(stage, inputs)
            if strategy == _MMR:
                return self._mmr(stage, inputs)
            limit = min(self.request.n_results, int(stage.config.get("limit", self.request.n_results)))
            return _single(stage, inputs)[:limit], {"parameters": {"limit": limit}}
        except _StageFailure:
            raise
        except ValueError as exc:
            raise _StageFailure("unavailable", exc) from exc
        except Exception as exc:  # noqa: BLE001 - routed by the graph or re-raised by the executor
            raise _StageFailure("failed", exc) from exc

    def _fuse(self, stage: PipelineStageDefinition, inputs: list[tuple[str, Any]]) -> tuple[Any, dict[str, Any]]:
        rrf_k = int(stage.config.get("rrf_k", 60))
        fused: dict[str, dict[str, Any]] = {}
        for source_id, rows in inputs:
            if not isinstance(rows, list):
                continue  # a leg that arrived by fallback contributes no ranking
            search_type = _LEG_TYPES.get(self.plan.stages[source_id].strategy, source_id)
            for rank, row in enumerate(rows, start=1):
                item_id = str(row.get("id") or (row.get("record") or {}).get("record_id") or "")
                if not item_id:
                    continue
                score = 1.0 / (float(rrf_k) + float(rank))
                if item_id not in fused:
                    fused[item_id] = {**row, "hybrid_score": score, "retrieval_hits": [{"type": search_type, "rank": rank}]}
                else:
                    fused[item_id]["hybrid_score"] += score
                    fused[item_id]["retrieval_hits"].append({"type": search_type, "rank": rank})
                    if row.get("distance") is not None:
                        current = fused[item_id].get("distance")
                        if current is None or float(row["distance"]) < float(current):
                            fused[item_id]["distance"] = row["distance"]
        ranked = sorted(
            fused.values(),
            key=lambda item: (float(item.get("hybrid_score") or 0.0), -float(item.get("distance") or 0.0)),
            reverse=True,
        )[: self.request.n_results]
        return ranked, {"parameters": {"rrf_k": rrf_k}}

    def _mmr(self, stage: PipelineStageDefinition, inputs: list[tuple[str, Any]]) -> tuple[Any, dict[str, Any]]:
        lambda_mult = float(stage.config.get("lambda_mult", self.request.lambda_mult))
        limit = min(self.request.n_results, int(stage.config.get("limit", self.request.n_results)))
        selected = mmr_select(
            _single(stage, inputs),
            limit=limit,
            lambda_mult=lambda_mult,
            relevance=lambda candidate: float(candidate.get("relevance") or 0.0),
            vector=lambda candidate: candidate.get("embedding"),
        )
        for row in selected:
            row.pop("embedding", None)
        return selected, {"parameters": {"lambda_mult": lambda_mult, "limit": limit}}


def _single(stage: PipelineStageDefinition, inputs: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    lists = [rows for _source, rows in inputs if isinstance(rows, list)]
    if len(lists) > 1:
        raise RuntimeError(f"Stage {stage.id!r} received several result sets; route them through fusion.")
    return list(lists[0]) if lists else []


def _summary(rows: Any, key: str) -> dict[str, Any]:
    values = [float(row[key]) for row in rows or [] if isinstance(row, dict) and isinstance(row.get(key), (int, float))]
    if not values:
        return {}
    return {"score_type": key, "count": len(values), "min": round(min(values), 4), "max": round(max(values), 4)}


_SCORE_KEY = {_DENSE: "distance", _LEXICAL: "lexical_score", _RRF: "hybrid_score", _MMR: "mmr_score"}


def execute_store_search(
    plan: StoreSearchPlan,
    *,
    store: Any,
    request: StoreSearchRequest,
    resolved_hash: str,
    owner: str | None = None,
    collection_identity: dict[str, Any] | None = None,
) -> StoreSearchExecution:
    runner = _Runner(store, plan, request)
    identity = collection_identity or {}
    inputs: dict[str, list[tuple[str, Any]]] = defaultdict(list)
    inputs[plan.order[0]].append(("__request__", None))
    stage_traces = []
    results: list[dict[str, Any]] = []
    started_at = datetime.now(UTC)
    for stage_id in plan.order:
        if stage_id not in inputs:
            continue  # no edge routed here: this stage never runs
        stage = plan.stages[stage_id]
        received = inputs[stage_id]
        begun = time.perf_counter()
        status, fallback_reason = "completed", None
        observation: dict[str, Any] = {}
        try:
            output, observation = runner.run(stage, received)
        except _StageFailure as failure:
            status, output, fallback_reason = failure.status, None, str(failure.error)[:300]
            edge = getattr(stage, _FALLBACK_EDGE[status])
            if edge is None:
                raise failure.error from None
            # A fallback edge replays what the failed stage received.
            inputs[edge].extend((stage.id, payload) for _source, payload in received)
        else:
            produced = bool(output)
            if produced:
                for target in stage.next:
                    inputs[target].append((stage.id, output))
            elif stage.on_empty:
                fallback_reason = "No results." if stage.strategy != _QUERY else "The query is empty."
                inputs[stage.on_empty].append((stage.id, None))
            if stage.strategy == _SELECT:
                results = list(output or [])
        in_count = sum(len(rows) for _source, rows in received if isinstance(rows, list))
        stage_traces.append(
            trace_stage(
                stage.id,
                stage.strategy,
                elapsed_seconds=time.perf_counter() - begun,
                input_count=in_count if stage.strategy not in _RETRIEVERS | {_QUERY} else None,
                output_count=len(output) if isinstance(output, list) else None,
                parameters={
                    **(observation.get("parameters") or {}),
                    **(
                        {"filter_fields": sorted(request.where or {})}
                        if stage.strategy in _RETRIEVERS and request.where
                        else {}
                    ),
                },
                provider=identity.get("embedding_provider") if stage.strategy == _DENSE else None,
                model=identity.get("embedding_model") if stage.strategy == _DENSE else None,
                collection=request.store if stage.strategy in _RETRIEVERS else None,
                fallback_reason=fallback_reason,
                score_summary=_summary(output, _SCORE_KEY.get(stage.strategy, "")),
                status=status,
            )
        )
    finished_at = datetime.now(UTC)
    trace = PipelineRunTrace(
        run_id=str(uuid.uuid4()),
        feature=SEARCH_FEATURE,
        pipeline_id=plan.pipeline.pipeline_id,
        pipeline_version=plan.pipeline.version,
        resolved_pipeline=plan.pipeline.model_dump(mode="json"),
        resolved_hash=resolved_hash,
        owner=owner,
        status="completed",
        started_at=started_at,
        finished_at=finished_at,
        total_elapsed_ms=max(0, int((finished_at - started_at).total_seconds() * 1000)),
        stages=stage_traces,
    )
    return StoreSearchExecution(results=results, trace=trace)


def resolve_store_search_pipeline(
    *, mode: str, pipeline_id: str | None, pipeline_version: int | None
) -> tuple[PipelineDefinition, str]:
    """Pick the definition for a request: explicit version, assignment, or a mode's built-in."""

    from .manager import pipeline_manager

    if pipeline_id:
        pipeline = pipeline_manager.get_definition(pipeline_id, pipeline_version)
        if pipeline is None:
            raise KeyError(f"{pipeline_id}@{pipeline_version}")
        if pipeline.purpose != SEARCH_PURPOSE:
            raise ValueError(f"Pipeline {pipeline_id}@{pipeline.version} is not a store-search pipeline.")
        return pipeline, pipeline_hash(pipeline)
    if mode == "assigned":
        resolved = pipeline_manager.resolve(SEARCH_FEATURE)
        pipeline = PipelineDefinition.model_validate(resolved["pipeline"])
        return pipeline, str(resolved.get("pipeline_hash") or pipeline_hash(pipeline))
    built_in_id, version = MODE_PIPELINES[mode]
    pipeline = pipeline_manager.get_definition(built_in_id, version)
    if pipeline is None:  # pragma: no cover - built-ins are code-owned
        raise KeyError(f"{built_in_id}@{version}")
    return pipeline, pipeline_hash(pipeline)
