# Copyright 2026 Aaron John Schlosser, PhD.
"""Administrative API for pipeline configuration and execution traces."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ..http_auth import request_user, require_admin
from ..models import RAGRunRequest
from ..pipelines.access import resolve_research_pipeline
from ..pipelines.benchmark import (
    ResearchPipelineBenchmarkRequest,
    build_research_benchmark_run,
)
from ..pipelines.comparison import (
    ResearchPipelineComparisonRequest,
    compare_research_dry_runs,
)
from ..pipelines.manager import pipeline_manager
from ..pipelines.metrics import aggregate_pipeline_metrics
from ..pipelines.models import PipelineAssignment, PipelineDefinition
from ..pipelines.store import pipeline_store
from ..rag import run_rag_pipeline
from ..services import store

router = APIRouter(prefix="/api/system/pipelines", tags=["pipelines"])


def _validate_research_retrieval_request(body: RAGRunRequest, *, label: str) -> None:
    if body.skip_retrieval:
        raise HTTPException(
            status_code=422,
            detail=f"{label} requires retrieval to be enabled.",
        )
    if not str(body.source_collection or "").strip():
        raise HTTPException(
            status_code=422,
            detail=f"Select a source collection for {label.lower()}.",
        )


def _execute_research_dry_run(
    request_body: RAGRunRequest,
    *,
    pipeline_id: str,
    version: int,
    owner: str,
) -> dict[str, Any]:
    selected = resolve_research_pipeline(
        requested_id=pipeline_id,
        requested_version=version,
        is_admin=True,
    )
    payload = request_body.model_dump(mode="python")
    payload.update(
        {
            "pipeline_id": selected.pipeline_id,
            "pipeline_version": selected.version,
            "auto_grade": False,
            "use_prior_response_memory": False,
            "use_prior_claim_memory": False,
        }
    )
    comparison_request = RAGRunRequest.model_validate(payload)
    return run_rag_pipeline(
        comparison_request,
        store,
        owner=owner,
        stop_after_context=True,
    )


@router.get("")
def pipeline_catalog(request: Request) -> dict[str, Any]:
    """Return the strategy catalog, saved pipelines, and effective assignments."""

    require_admin(request)
    return pipeline_manager.catalog()


@router.get("/research-options")
def research_pipeline_options(request: Request) -> dict[str, Any]:
    """Return the executable Research chains visible to the signed-in user.

    Pipeline definitions contain only registered strategy IDs and bounded
    configuration, so exposing them here improves runtime transparency without
    disclosing prompts, credentials, source text, or hidden reviewer values.
    """

    user = request_user(request)
    resolved = pipeline_manager.resolve("research")
    assignment = resolved["assignment"]
    assigned_id = str(assignment["pipeline_id"])
    assigned_version = int(assignment["pipeline_version"])
    override_allowed = bool(assignment.get("override_allowed"))

    rows: list[dict[str, Any]] = []
    for pipeline in pipeline_manager.list_definitions(purpose="research"):
        support = pipeline_manager.runtime_support(pipeline)
        assigned = (
            pipeline.pipeline_id == assigned_id
            and pipeline.version == assigned_version
        )
        if not bool(support.get("supported")):
            continue
        if user.role != "admin":
            if not assigned and (not override_allowed or pipeline.status != "active"):
                continue
        elif pipeline.status == "disabled":
            continue
        rows.append(
            {
                **pipeline.model_dump(mode="json"),
                "runtime_support": support,
                "assigned": assigned,
            }
        )

    rows.sort(
        key=lambda item: (
            not bool(item.get("assigned")),
            str(item.get("name") or item.get("pipeline_id") or "").casefold(),
            -int(item.get("version") or 0),
        )
    )
    strategy_ids = {
        str(stage.get("strategy") or "")
        for pipeline in rows
        for stage in pipeline.get("stages", [])
        if isinstance(stage, dict)
    }
    strategies = [
        spec
        for spec in pipeline_manager.service.strategies()
        if str(spec.get("strategy_id") or "") in strategy_ids
    ]
    return {
        "assignment": assignment,
        "override_allowed": user.role == "admin" or override_allowed,
        "pipelines": rows,
        "strategies": strategies,
    }


@router.get("/resolved/{feature}")
def resolved_pipeline(feature: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        return pipeline_manager.resolve(feature)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"No pipeline is assigned to {feature!r}.") from exc


@router.post("/validate")
def validate_pipeline_definition(
    body: PipelineDefinition,
    request: Request,
) -> dict[str, Any]:
    require_admin(request)
    validation = pipeline_manager.service.validate(body)
    runtime = (
        pipeline_manager.runtime_support(body)
        if validation.valid
        else {
            "supported": False,
            "reason": "Resolve graph validation errors before testing runtime support.",
        }
    )
    return {
        "validation": validation.model_dump(mode="json"),
        "runtime_supported": bool(runtime.get("supported")),
        "runtime_error": runtime.get("reason"),
    }


@router.post("/definitions/{pipeline_id}/{version}/clone-draft")
def clone_pipeline_definition_draft(
    pipeline_id: str,
    version: int,
    request: Request,
) -> dict[str, Any]:
    """Prepare an editable clone without persisting a new version yet."""

    require_admin(request)
    try:
        draft = pipeline_manager.prepare_clone(pipeline_id, version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Pipeline definition not found.") from exc
    return {"pipeline": draft.model_dump(mode="json")}


@router.post("/definitions")
def create_pipeline_definition(
    body: PipelineDefinition,
    request: Request,
) -> dict[str, Any]:
    user = require_admin(request)
    try:
        saved = pipeline_manager.save_definition(body, actor=user.username)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "pipeline": saved.model_dump(mode="json"),
        "validation": pipeline_manager.service.validate(saved).model_dump(mode="json"),
    }


@router.put("/assignments/{feature}")
def set_pipeline_assignment(
    feature: str,
    body: PipelineAssignment,
    request: Request,
) -> dict[str, Any]:
    require_admin(request)
    if body.feature != feature:
        raise HTTPException(
            status_code=422,
            detail="Assignment feature must match the URL feature.",
        )
    if body.scope != "system" or body.scope_id is not None:
        raise HTTPException(
            status_code=422,
            detail="The first configurable release supports system-scope assignments only.",
        )
    try:
        saved = pipeline_manager.assign(body, actor_source="system")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"assignment": saved.model_dump(mode="json")}


@router.delete("/assignments/{feature}")
def reset_pipeline_assignment(feature: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    removed = pipeline_store.delete_assignment(feature)
    try:
        resolved = pipeline_manager.resolve(feature)
    except KeyError:
        resolved = None
    return {"deleted": removed, "resolved": resolved}


@router.post("/compare/research")
def compare_research_pipelines(
    body: ResearchPipelineComparisonRequest,
    request: Request,
) -> dict[str, Any]:
    """Run two saved Research pipelines through retrieval without persisting a run.

    The comparison stops after provenance-checked evidence context construction.
    It never generates a final answer, grades a response, writes response memory,
    or creates a pipeline-run trace. Query decomposition may still call the
    configured language model when the submitted request explicitly enables it.
    """

    user = require_admin(request)
    _validate_research_retrieval_request(
        body.request,
        label="Research pipeline comparison",
    )
    try:
        left = _execute_research_dry_run(
            body.request,
            pipeline_id=body.left.pipeline_id,
            version=body.left.version,
            owner=user.username,
        )
        right = _execute_research_dry_run(
            body.request,
            pipeline_id=body.right.pipeline_id,
            version=body.right.version,
            owner=user.username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return compare_research_dry_runs(left, right)


@router.post("/benchmarks/research")
def run_research_pipeline_benchmark(
    body: ResearchPipelineBenchmarkRequest,
    request: Request,
) -> dict[str, Any]:
    """Run and persist one fixed-case retrieval benchmark.

    The two pipeline executions remain non-persistent dry runs: they do not
    create Research jobs, response memory, claim memory, or ordinary pipeline
    traces. The benchmark result itself is persisted in the dedicated benchmark
    store with fixed prompt/configuration and bounded candidate diagnostics.
    """

    user = require_admin(request)
    _validate_research_retrieval_request(
        body.request,
        label="Research pipeline benchmark",
    )
    try:
        left = _execute_research_dry_run(
            body.request,
            pipeline_id=body.left.pipeline_id,
            version=body.left.version,
            owner=user.username,
        )
        right = _execute_research_dry_run(
            body.request,
            pipeline_id=body.right.pipeline_id,
            version=body.right.version,
            owner=user.username,
        )
        comparison = compare_research_dry_runs(left, right)
        benchmark = build_research_benchmark_run(
            body,
            comparison,
            store=store,
            created_by=user.username,
        )
        pipeline_store.put_benchmark(benchmark)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"benchmark": benchmark.model_dump(mode="json")}


@router.get("/benchmarks")
def pipeline_benchmarks(
    request: Request,
    case_id: str = Query(default="", max_length=160),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """List persisted benchmark results without mixing them into run traces."""

    require_admin(request)
    rows = pipeline_store.list_benchmarks(
        case_id=case_id or None,
        limit=limit,
        offset=offset,
    )
    return {
        "benchmarks": [row.model_dump(mode="json") for row in rows],
        "limit": limit,
        "offset": offset,
    }


@router.get("/benchmarks/{benchmark_run_id}")
def pipeline_benchmark(
    benchmark_run_id: str,
    request: Request,
) -> dict[str, Any]:
    require_admin(request)
    row = pipeline_store.get_benchmark(benchmark_run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Pipeline benchmark not found.")
    return {"benchmark": row.model_dump(mode="json")}


@router.get("/metrics")
def pipeline_metrics(
    request: Request,
    feature: str = Query(default="", max_length=160),
    owner: str = Query(default="", max_length=200),
    limit: int = Query(default=250, ge=1, le=1000),
) -> dict[str, Any]:
    """Aggregate recent operational traces without exposing source/prompt content."""

    require_admin(request)
    rows = pipeline_store.list_runs(
        feature=feature or None,
        owner=owner or None,
        limit=limit,
        offset=0,
    )
    return {
        **aggregate_pipeline_metrics(rows),
        "sample_limit": limit,
        "feature_filter": feature or None,
        "owner_filter": owner or None,
    }


@router.get("/runs")
def pipeline_runs(
    request: Request,
    feature: str = Query(default="", max_length=160),
    owner: str = Query(default="", max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    require_admin(request)
    rows = pipeline_store.list_runs(
        feature=feature or None,
        owner=owner or None,
        limit=limit,
        offset=offset,
    )
    return {
        "runs": [row.model_dump(mode="json") for row in rows],
        "limit": limit,
        "offset": offset,
    }


@router.get("/runs/{run_id}")
def pipeline_run(run_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    trace = pipeline_store.get_run(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Pipeline trace not found.")
    return {"run": trace.model_dump(mode="json")}
