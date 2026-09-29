# Copyright 2026 Aaron John Schlosser, PhD.
"""Administrative API for pipeline configuration and execution traces."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ..http_auth import require_admin
from ..pipelines.manager import pipeline_manager
from ..pipelines.models import PipelineAssignment, PipelineDefinition
from ..pipelines.store import pipeline_store

router = APIRouter(prefix="/api/system/pipelines", tags=["pipelines"])


@router.get("")
def pipeline_catalog(request: Request) -> dict[str, Any]:
    """Return the strategy catalog, saved pipelines, and effective assignments."""

    require_admin(request)
    return pipeline_manager.catalog()


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
    runtime_error = None
    if validation.valid and body.purpose == "research":
        from ..pipelines.research import compile_research_pipeline

        try:
            compile_research_pipeline(body)
        except ValueError as exc:
            runtime_error = str(exc)
    return {
        "validation": validation.model_dump(mode="json"),
        "runtime_supported": validation.valid and runtime_error is None,
        "runtime_error": runtime_error,
    }


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
