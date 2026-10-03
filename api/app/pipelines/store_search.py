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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..retrieval_selection import mmr_select
from .contracts import strategy_concurrency
from .models import PipelineDefinition, PipelineRunTrace, PipelineStageDefinition
from .purposes import purpose_registry
from .registry import reject_unhonoured_config, strategy_registry
from .service import pipeline_hash
from .trace_safety import trace_stage
from .wiring import resolve_wiring, rewired_warnings

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
# Declared capabilities, so rules follow what a consumer needs rather than which stage happens to be adjacent.
_MAX_PARALLEL_BRANCHES = 4
_NEEDS_EMBEDDINGS = frozenset({_MMR})  # consumers that need candidate embeddings
_EMBEDDING_PRODUCERS = frozenset({_DENSE})
_FALLBACK_EDGE = {"unavailable": "on_unavailable", "timed_out": "on_timeout", "failed": "on_error"}


@dataclass(frozen=True)
class StoreSearchPlan:
    pipeline: PipelineDefinition
    stages: dict[str, PipelineStageDefinition]
    order: list[str]
    # Data delivery resolved from the pipeline's wiring (graph edges plus explicit
    # input bindings), not from ``next`` alone: producer -> consuming stages.
    consumers: dict[str, list[str]]
    # Stages whose input is the run's own query rather than another stage's output.
    seeded: frozenset[str]
    # Fixed numbers bound to tuning ports: stage id -> port name -> value.
    constants: dict[str, dict[str, float]] = field(default_factory=dict)

    def tuned(self, stage: PipelineStageDefinition, port: str, fallback: Any) -> Any:
        """A tuning value: the bound constant, else the stage's own config, else ``fallback``.

        Only retrieval/fusion/selection arithmetic is tunable this way; nothing here can
        touch provenance, validation or access rules.
        """

        if port in self.constants.get(stage.id, {}):
            return self.constants[stage.id][port]
        return stage.config.get(port, fallback)


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
    consumers, seeded, constants = _resolve_delivery(pipeline, stages)
    producers: dict[str, list[str]] = defaultdict(list)
    for source_id, targets in consumers.items():
        for target in targets:
            producers[target].append(source_id)
    for stage in stages.values():
        if stage.strategy in _NEEDS_EMBEDDINGS:
            sources = producers[stage.id]
            if not sources or any(
                stages[source].strategy not in _EMBEDDING_PRODUCERS or consumers[source] != [stage.id]
                for source in sources
            ):
                raise ValueError(
                    "MMR needs query and candidate embeddings, so it may only follow semantic similarity "
                    "that feeds nothing else."
                )
    order = _topological_order(pipeline, stages, consumers)
    return StoreSearchPlan(
        pipeline=pipeline,
        stages=stages,
        order=order,
        consumers=dict(consumers),
        seeded=frozenset(seeded),
        constants=constants,
    )


def _resolve_delivery(
    pipeline: PipelineDefinition, stages: dict[str, PipelineStageDefinition]
) -> tuple[dict[str, list[str]], set[str], dict[str, dict[str, float]]]:
    """Who receives each stage's output, resolved by the shared wiring resolver.

    A ``next`` edge that only orders a producer ahead of an explicitly bound
    consumer delivers nothing; the binding decides. Fallback edges are routed by
    the executor itself and are not data delivery here.
    """

    wiring = resolve_wiring(pipeline, strategy_registry, purpose_registry.get(pipeline.purpose))
    errors = [issue for issue in wiring["issues"] if issue.level == "error"]
    if errors:
        raise ValueError("Store-search wiring is invalid: " + "; ".join(issue.message for issue in errors))
    consumers: dict[str, list[str]] = defaultdict(list)
    seeded: set[str] = set()
    constants: dict[str, dict[str, float]] = {}
    for stage_id in stages:
        for row in wiring["stages"].get(stage_id, {}).get("inputs", []):
            for source in row["sources"]:
                if source["kind"] == "constant":
                    constants.setdefault(stage_id, {})[row["port"]] = float(source["value"])
                elif source["kind"] == "run_input":
                    seeded.add(stage_id)
                elif source["kind"] == "stage" and source["via"] in ("next", "explicit"):
                    if source["stage"] not in stages:
                        raise ValueError(f"Stage {stage_id!r} takes input from disabled stage {source['stage']!r}.")
                    if stage_id not in consumers[source["stage"]]:
                        consumers[source["stage"]].append(stage_id)
    return consumers, seeded, constants


def _topological_order(
    pipeline: PipelineDefinition,
    stages: dict[str, PipelineStageDefinition],
    consumers: dict[str, list[str]],
) -> list[str]:
    """Kahn order with definition order as the tie-break, so fused branches keep a stable order."""

    position = {stage.id: index for index, stage in enumerate(pipeline.stages)}
    indegree = {stage_id: 0 for stage_id in stages}
    edges = {sid: set(stage.edge_targets()) | set(consumers.get(sid, ())) for sid, stage in stages.items()}
    for targets in edges.values():
        for target in targets:
            indegree[target] += 1
    ready = deque(sorted((sid for sid, degree in indegree.items() if degree == 0), key=position.get))
    order: list[str] = []
    while ready:
        stage_id = ready.popleft()
        order.append(stage_id)
        for target in sorted(edges[stage_id], key=position.get):
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

    tuned = plan.tuned(stage, "fetch_k", None)
    if tuned is not None:
        return int(tuned)
    depths = [request.n_results]
    for consumer in plan.consumers.get(stage.id, ()):
        strategy = plan.stages[consumer].strategy
        if strategy == _MMR:
            depths.append(max(request.n_results, request.fetch_k))
        elif strategy == _RRF:
            depths.append(min(max(request.n_results * 4, 32), 400))
    return max(depths)


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
                if any(self.plan.stages[c].strategy in _NEEDS_EMBEDDINGS for c in self.plan.consumers.get(stage.id, ())):
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
            limit = min(self.request.n_results, int(self.plan.tuned(stage, "limit", self.request.n_results)))
            return _single(stage, inputs)[:limit], {"parameters": {"limit": limit}}
        except _StageFailure:
            raise
        except ValueError as exc:
            raise _StageFailure("unavailable", exc) from exc
        except Exception as exc:  # noqa: BLE001 - routed by the graph or re-raised by the executor
            raise _StageFailure("failed", exc) from exc

    def _fuse(self, stage: PipelineStageDefinition, inputs: list[tuple[str, Any]]) -> tuple[Any, dict[str, Any]]:
        rrf_k = int(self.plan.tuned(stage, "rrf_k", 60))
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
        lambda_mult = float(self.plan.tuned(stage, "lambda_mult", self.request.lambda_mult))
        limit = min(self.request.n_results, int(self.plan.tuned(stage, "limit", self.request.n_results)))
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
    parallel: bool = False,
) -> StoreSearchExecution:
    """Run a compiled plan. ``parallel`` lets independent, concurrency-safe branches overlap.

    Results, fallback routing and trace order never depend on completion order: each
    overlapped batch is joined first and then processed in definition order.
    """

    runner = _Runner(store, plan, request)
    identity = collection_identity or {}
    inputs: dict[str, list[tuple[str, Any]]] = defaultdict(list)
    for seeded_id in plan.order:
        if seeded_id in plan.seeded:
            inputs[seeded_id].append(("__request__", None))
    stage_traces = []
    results: list[dict[str, Any]] = []
    started_at = datetime.now(UTC)
    attempts: dict[str, tuple[Any, ...]] = {}
    overlapped = False

    def _attempt(stage: PipelineStageDefinition, received: list[tuple[str, Any]]) -> tuple[Any, ...]:
        begun = time.perf_counter()
        try:
            output, observation = runner.run(stage, received)
        except _StageFailure as failure:
            return begun, time.perf_counter(), None, {}, failure
        return begun, time.perf_counter(), output, observation, None

    for stage_id in plan.order:
        if stage_id not in inputs:
            continue  # no edge routed here: this stage never runs
        stage = plan.stages[stage_id]
        received = inputs[stage_id]
        if parallel and stage_id not in attempts:
            # Independent branches: stages already holding their inputs whose strategy allows
            # overlap. Nothing here consumes another batch member's output, because a consumer
            # only receives input after its producer has been processed.
            batch = [
                plan.stages[other]
                for other in plan.order
                if other in inputs and other not in attempts and strategy_concurrency(plan.stages[other].strategy) != "exclusive"
            ]
            if stage in batch and len(batch) > 1:
                with ThreadPoolExecutor(max_workers=min(len(batch), _MAX_PARALLEL_BRANCHES)) as pool:
                    futures = {member.id: pool.submit(_attempt, member, list(inputs[member.id])) for member in batch}
                    for member_id, future in futures.items():
                        attempts[member_id] = future.result()
                overlapped = True
        status, fallback_reason = "completed", None
        begun, ended, output, observation, failed = attempts.get(stage_id) or _attempt(stage, received)
        if failed is not None:
            status, output, fallback_reason = failed.status, None, str(failed.error)[:300]
            edge = getattr(stage, _FALLBACK_EDGE[status])
            if edge is None:
                raise failed.error from None
            # A fallback edge replays what the failed stage received.
            inputs[edge].extend((stage.id, payload) for _source, payload in received)
        else:
            produced = bool(output)
            if produced:
                for target in plan.consumers.get(stage.id, ()):
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
                elapsed_seconds=ended - begun,
                input_count=in_count if stage.strategy not in _RETRIEVERS | {_QUERY} else None,
                output_count=len(output) if isinstance(output, list) else None,
                parameters={
                    **(observation.get("parameters") or {}),
                    **(
                        {"filter_fields": sorted(request.where or {})}
                        if stage.strategy in _RETRIEVERS and request.where
                        else {}
                    ),
                    # Size of the collection searched: a count, so scans can be fitted against it.
                    **(
                        {"scope_size": int(identity["scope_size"])}
                        if stage.strategy in _RETRIEVERS and isinstance(identity.get("scope_size"), int)
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
        warnings=[*rewired_warnings(plan.pipeline), *(['branches_overlapped'] if overlapped else [])],
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
