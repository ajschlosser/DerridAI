# Copyright 2026 Aaron John Schlosser, PhD.
"""Administrative API for pipeline configuration and execution traces."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ..http_auth import request_user, require_admin
from ..models import RAGRunRequest
from ..pipelines.access import resolve_research_pipeline
from ..pipelines.analysis import TraceSampler, analyze_pipeline
from ..pipelines.benchmark import (
    BenchmarkCorpusDriftError,
    ResearchPipelineBenchmarkCase,
    ResearchPipelineBenchmarkCaseCreate,
    ResearchPipelineBenchmarkRequest,
    assert_benchmark_corpus_unchanged,
    benchmark_request_for_case,
    build_research_benchmark_case,
    build_research_benchmark_run,
)
from ..pipelines.comparison import (
    EvidencePipelineComparisonRequest,
    ResearchPipelineComparisonRequest,
    compare_evidence_runs,
    compare_research_dry_runs,
    comparison_source_projection,
    summarize_evidence_recovery_run,
    summarize_evidence_suggestion_run,
)
from ..pipelines.latency import strategy_latency
from ..pipelines.manager import pipeline_manager
from ..pipelines.metrics import aggregate_pipeline_metrics
from ..pipelines.models import PipelineAssignment, PipelineDefinition
from ..pipelines.purposes import WORKFLOW_CATEGORIES, purpose_registry
from ..pipelines.service import pipeline_hash
from ..pipelines.store import pipeline_store
from ..rag import run_rag_pipeline
from ..services import store

router = APIRouter(prefix="/api/system/pipelines", tags=["pipelines"])
trace_sampler = TraceSampler(pipeline_store)


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


@router.post("/analyze")
def analyze_pipeline_definition(
    body: PipelineDefinition,
    request: Request,
) -> dict[str, Any]:
    """Explain a draft or saved pipeline: input wiring, declared cost, expected latency.

    Reads recent execution traces for latency; the figures are operational
    telemetry and carry their sample sizes and basis.
    """

    require_admin(request)
    validation = pipeline_manager.service.validate(body)
    analysis = analyze_pipeline(
        body,
        pipeline_manager.service.registry,
        resolved_hash=pipeline_hash(body),
        sample_runs=trace_sampler.sample(),
        pipeline_runs=trace_sampler.for_pipeline(body.pipeline_id),
    )
    return {"validation": validation.model_dump(mode="json"), **analysis}


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


@router.post("/definitions/new-draft")
def new_pipeline_definition_draft(
    body: dict[str, Any],
    request: Request,
) -> dict[str, Any]:
    """Prepare a blank, valid draft for a workflow without persisting it."""

    require_admin(request)
    purpose = str(body.get("purpose") or "")
    try:
        draft = pipeline_manager.prepare_blank(purpose)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown workflow.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"pipeline": draft.model_dump(mode="json")}


@router.get("/strategy-latency")
def strategy_latency_figures(request: Request) -> dict[str, Any]:
    """Observed per-strategy latency, throughput and scaling from recent traces."""

    require_admin(request)
    sample = trace_sampler.sample()
    return {"strategies": strategy_latency(sample), "sampled_run_count": len(sample)}


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


def _evidence_pipeline(ref: Any, *, purpose: str):
    pipeline = pipeline_manager.get_definition(ref.pipeline_id, ref.version)
    if pipeline is None:
        raise ValueError(f"Pipeline {ref.pipeline_id!r}@{ref.version} was not found.")
    if pipeline.purpose != purpose:
        raise ValueError(
            f"Pipeline {pipeline.pipeline_id}@{pipeline.version} is a {pipeline.purpose} "
            f"pipeline, not a {purpose} pipeline."
        )
    return pipeline


@router.post("/compare/evidence-suggestion")
def compare_evidence_suggestion_pipelines(
    body: EvidencePipelineComparisonRequest,
    request: Request,
) -> dict[str, Any]:
    """Run two saved reviewer-evidence pipelines on the same value and blocks.

    The comparison never writes a corpus record, review decision, or pipeline
    trace. It does not bind evidence.
    """

    require_admin(request)
    from ..pipelines.evidence import execute_reviewer_evidence_pipeline

    try:
        sides = []
        projection = comparison_source_projection()
        for ref in (body.left, body.right):
            pipeline = _evidence_pipeline(ref, purpose="evidence_suggestion")
            execution = execute_reviewer_evidence_pipeline(
                pipeline=pipeline,
                resolved_hash=pipeline_hash(pipeline),
                value=body.value,
                blocks=list(body.blocks),
                field_metadata=body.field_metadata or {"name": body.field, "label": body.field},
                source_document_id=body.source_document_id,
                projection=projection,
                limit=body.limit,
            )
            sides.append(summarize_evidence_suggestion_run(execution))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return compare_evidence_runs(sides[0], sides[1])


@router.post("/compare/evidence-recovery")
def compare_evidence_recovery_pipelines(
    body: EvidencePipelineComparisonRequest,
    request: Request,
) -> dict[str, Any]:
    """Run two saved evidence-recovery pipelines on the same value and blocks.

    The comparison walks the cascade in memory and does not persist a run trace
    or attach evidence to a record.
    """

    require_admin(request)
    from ..pipelines.evidence_recovery import compile_recovery_pipeline, execute_recovery_pipeline

    try:
        sides = []
        projection = comparison_source_projection()
        for ref in (body.left, body.right):
            pipeline = _evidence_pipeline(ref, purpose="evidence_recovery")
            plan = compile_recovery_pipeline(pipeline)
            items, winner, trace = execute_recovery_pipeline(
                plan,
                resolved_hash=pipeline_hash(pipeline),
                value=body.value,
                blocks=list(body.blocks),
                field=body.field,
                field_metadata=body.field_metadata or {"name": body.field, "label": body.field},
                source_document_id=body.source_document_id,
                projection=projection,
                llm_choice=None,
                llm_skip_reason="Evidence-recovery comparison does not call a language model.",
            )
            sides.append(
                summarize_evidence_recovery_run(
                    pipeline=pipeline,
                    resolved_hash=pipeline_hash(pipeline),
                    items=items,
                    winner=winner,
                    trace=trace,
                    celf_compliant=plan.celf_compliant,
                    compliance_reason=plan.compliance_reason,
                )
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return compare_evidence_runs(sides[0], sides[1])


def _same_benchmark_fixture(
    case: ResearchPipelineBenchmarkCase,
    body: ResearchPipelineBenchmarkCaseCreate,
    *,
    corpus_fingerprint: str,
) -> bool:
    """Treat identical case creation as idempotent without permitting mutation."""

    existing = case.model_dump(mode="json")
    requested = body.model_dump(mode="json")
    return (
        all(existing.get(key) == value for key, value in requested.items())
        and case.corpus_snapshot.fingerprint == corpus_fingerprint
    )


@router.post("/benchmarks/research/cases")
def create_research_pipeline_benchmark_case(
    body: ResearchPipelineBenchmarkCaseCreate,
    request: Request,
) -> dict[str, Any]:
    """Create one immutable retrieval-only benchmark fixture.

    Re-submitting the exact same fixed input and corpus/index fingerprint is
    idempotent so the case can be reused for multiple pipeline comparisons.
    Any change requires a new case version.
    """

    user = require_admin(request)
    try:
        candidate = build_research_benchmark_case(
            body,
            store=store,
            created_by=user.username,
        )
        existing = pipeline_store.get_benchmark_case(body.case_id, body.version)
        if existing is not None:
            if not _same_benchmark_fixture(
                existing,
                body,
                corpus_fingerprint=candidate.corpus_snapshot.fingerprint,
            ):
                raise ValueError(
                    f"Benchmark case {body.case_id}@{body.version} already exists "
                    "with different fixed inputs or corpus/index identity. Create "
                    "a new case version."
                )
            return {"case": existing.model_dump(mode="json"), "created": False}
        case = pipeline_store.put_benchmark_case(candidate)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"case": case.model_dump(mode="json"), "created": True}


@router.get("/benchmarks/research/cases")
def research_pipeline_benchmark_cases(
    request: Request,
    case_id: str = Query(default="", max_length=160),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """List immutable benchmark case versions."""

    require_admin(request)
    rows = pipeline_store.list_benchmark_cases(
        case_id=case_id or None,
        limit=limit,
        offset=offset,
    )
    return {
        "cases": [row.model_dump(mode="json") for row in rows],
        "limit": limit,
        "offset": offset,
    }


@router.get("/benchmarks/research/cases/{case_id}/{version}")
def research_pipeline_benchmark_case(
    case_id: str,
    version: int,
    request: Request,
) -> dict[str, Any]:
    require_admin(request)
    row = pipeline_store.get_benchmark_case(case_id, version)
    if row is None:
        raise HTTPException(status_code=404, detail="Pipeline benchmark case not found.")
    return {"case": row.model_dump(mode="json")}


@router.post("/benchmarks/research")
def run_research_pipeline_benchmark(
    body: ResearchPipelineBenchmarkRequest,
    request: Request,
) -> dict[str, Any]:
    """Run two immutable Research pipelines against one saved fixed case.

    The executions use the non-persistent retrieval path. They never create
    Research jobs, response/claim memory, generated answers, grades, or ordinary
    pipeline traces. Only the dedicated benchmark result is persisted.
    """

    user = require_admin(request)
    case = pipeline_store.get_benchmark_case(body.case_id, body.case_version)
    if case is None:
        raise HTTPException(status_code=404, detail="Pipeline benchmark case not found.")

    try:
        assert_benchmark_corpus_unchanged(case, store=store)
        left_request = benchmark_request_for_case(
            case,
            pipeline_id=body.left.pipeline_id,
            pipeline_version=body.left.version,
        )
        right_request = benchmark_request_for_case(
            case,
            pipeline_id=body.right.pipeline_id,
            pipeline_version=body.right.version,
        )
        left = _execute_research_dry_run(
            left_request,
            pipeline_id=body.left.pipeline_id,
            version=body.left.version,
            owner=user.username,
        )
        right = _execute_research_dry_run(
            right_request,
            pipeline_id=body.right.pipeline_id,
            version=body.right.version,
            owner=user.username,
        )
        comparison = compare_research_dry_runs(left, right)
        benchmark = build_research_benchmark_run(
            case,
            comparison,
            left_result=left,
            right_result=right,
            created_by=user.username,
        )
        pipeline_store.put_benchmark(benchmark)
    except BenchmarkCorpusDriftError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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


def _category_features(category: str) -> list[str] | None:
    """Features whose purpose belongs to a workflow category; None when unfiltered."""

    if not category:
        return None
    if category not in {term.id for term in WORKFLOW_CATEGORIES}:
        raise HTTPException(status_code=400, detail=f"Unknown workflow category {category!r}.")
    return [
        spec.consuming_feature for spec in purpose_registry.list() if spec.category == category
    ]


@router.get("/metrics")
def pipeline_metrics(
    request: Request,
    feature: str = Query(default="", max_length=160),
    category: str = Query(default="", max_length=40),
    owner: str = Query(default="", max_length=200),
    limit: int = Query(default=250, ge=1, le=1000),
) -> dict[str, Any]:
    """Aggregate recent operational traces without exposing source/prompt content."""

    require_admin(request)
    rows = pipeline_store.list_runs(
        feature=feature or None,
        features=_category_features(category),
        owner=owner or None,
        limit=limit,
        offset=0,
    )
    return {
        **aggregate_pipeline_metrics(rows),
        "sample_limit": limit,
        "feature_filter": feature or None,
        "category_filter": category or None,
        "owner_filter": owner or None,
    }


@router.get("/runs")
def pipeline_runs(
    request: Request,
    feature: str = Query(default="", max_length=160),
    category: str = Query(default="", max_length=40),
    owner: str = Query(default="", max_length=200),
    pipeline_id: str = Query(default="", max_length=160),
    status: str = Query(default="", max_length=40),
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    require_admin(request)
    features = _category_features(category)
    filters: dict[str, str | None] = {
        "feature": feature or None,
        "owner": owner or None,
        "pipeline_id": pipeline_id or None,
        "status": status or None,
        "query": q or None,
    }
    rows = pipeline_store.list_runs(limit=limit, offset=offset, features=features, **filters)
    return {
        "runs": [row.model_dump(mode="json") for row in rows],
        "limit": limit,
        "offset": offset,
        "total": pipeline_store.count_runs(features=features, **filters),
    }


@router.post("/runs/clear")
def clear_pipeline_runs(body: dict[str, Any], request: Request) -> dict[str, Any]:
    """Delete every execution trace. Definitions and assignments are untouched."""

    require_admin(request)
    if body.get("confirm") != "clear-execution-history":
        raise HTTPException(
            status_code=422,
            detail="Confirm history deletion with confirm=clear-execution-history.",
        )
    return {"deleted": pipeline_store.clear_runs()}


@router.get("/runs/{run_id}")
def pipeline_run(run_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    trace = pipeline_store.get_run(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Pipeline trace not found.")
    return {"run": trace.model_dump(mode="json")}


@router.delete("/runs/{run_id}")
def delete_pipeline_run(run_id: str, request: Request) -> dict[str, Any]:
    """Delete one execution trace. The saved pipeline version is not affected."""

    require_admin(request)
    deleted = pipeline_store.delete_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Pipeline trace not found.")
    return {"deleted": True, "run_id": run_id}
