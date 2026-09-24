# Copyright 2026 Aaron John Schlosser, PhD.
"""Background operation and RAG job API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import AuthUser
from ..config import settings
from ..content_filter import enforce_researcher_text
from ..corpus_builder import pdf_corpus_builds, pdf_corpus_repository
from ..dependencies import JobManagers, get_job_managers, request_user
from ..models import (
    LLMJobCreate,
    LLMJobRejectRequest,
    LLMResultResolutionRequest,
    LLMToolJobCreate,
    RAGConcurrencyUpdate,
    RAGRunRequest,
    UpsertJobCreate,
)
from ..provider_profiles import profile_generation_options
from ..researcher_view import sanitize_rag_job
from ..system_store import system_store

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

def _job_manager_for(job_id: str, managers: JobManagers) -> Any:
    """Resolve a retained job ID across all operation managers."""
    for manager in (
        managers.llm,
        managers.llm_tools,
        managers.rag,
        managers.upsert,
    ):
        try:
            manager.get(job_id)
            return manager
        except KeyError:
            continue

    try:
        pdf_corpus_repository.get_build(job_id)
        return pdf_corpus_builds
    except KeyError:
        raise KeyError(job_id) from None


def _researcher_job_access(
    user: AuthUser,
    manager: Any,
    job_id: str,
    managers: JobManagers,
) -> dict[str, Any]:
    """Apply owner scoping to the shared jobs endpoint.

    Researchers may inspect only their own RAG jobs. Other job types contain
    administrative or corpus-maintenance details and remain invisible even if a
    caller guesses a valid retained job identifier.
    """
    job = (
        manager.operation(job_id)
        if manager is pdf_corpus_builds
        else manager.get(job_id)
    )
    if user.role != "admin":
        if manager is not managers.rag or job.get("owner") != user.username:
            raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("/llm")
def create_llm_job(
    body: LLMJobCreate,
    request: Request,
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    try:
        # Audit history is never model-review context. Strip it server-side even
        # for older clients so large update trails cannot leak into retained jobs.
        for item in body.items:
            item.record.pop("updates", None)
        return managers.llm.create(body, owner=request_user(request).username)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rag/concurrency")
def get_rag_concurrency(
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    return managers.rag.concurrency_status()


@router.put("/rag/concurrency")
def set_rag_concurrency(
    body: RAGConcurrencyUpdate,
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    return managers.rag.set_ollama_limit(body.ollama_max_concurrent)


@router.post("/{job_id}/llm-results/resolve")
def resolve_llm_job_results(
    job_id: str,
    body: LLMResultResolutionRequest,
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    try:
        manager = _job_manager_for(job_id, managers)
        if manager is not managers.llm:
            raise HTTPException(
                status_code=409,
                detail="Job is not an LLM review job.",
            )
        return managers.llm.resolve_results(
            job_id,
            action=body.action,
            items=[item.model_dump() for item in body.items],
            dismiss_job=body.dismiss_job,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{job_id}/llm-results/reject")
def reject_llm_job_results(
    job_id: str,
    body: LLMJobRejectRequest,
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    try:
        manager = _job_manager_for(job_id, managers)
        if manager is not managers.llm:
            raise HTTPException(
                status_code=409,
                detail="Job is not an LLM review job.",
            )
        return managers.llm.reject_and_dismiss(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc


@router.post("/llm-tool")
def create_llm_tool_job(
    body: LLMToolJobCreate,
    request: Request,
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    try:
        return managers.llm_tools.create(
            body,
            owner=request_user(request).username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/rag")
def create_rag_job(
    body: RAGRunRequest,
    request: Request,
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    try:
        user = request_user(request)
        if user.role != "admin":
            enforce_researcher_text(
                {"prompt": body.prompt, "instructions": body.instructions}
            )

        for selection in body.selected_evidence:
            if isinstance(selection.record, dict):
                selection.record.pop("updates", None)

        if user.role != "admin":
            # A researcher can choose only a profile ID. Endpoint, credentials,
            # model, concurrency, and generation settings are rebuilt from the
            # administrator-owned profile and replace all browser-supplied values.
            if not body.provider_profile_id:
                raise ValueError(
                    "Select an administrator-approved researcher LLM profile."
                )
            profile = system_store.researcher_profile(body.provider_profile_id)
            if profile is None:
                raise ValueError(
                    "That researcher LLM profile is not available."
                )

            payload = body.model_dump()
            payload.update(
                {
                    "provider": profile.get("type") or "ollama",
                    "model": profile.get("model"),
                    "base_url": profile.get("base_url"),
                    "api_key": profile.get("api_key"),
                    "max_concurrent_requests": max(
                        1,
                        min(
                            64,
                            int(profile.get("max_concurrent_requests") or 1),
                        ),
                    ),
                    "generation": profile_generation_options(profile) or None,
                }
            )

            if payload.get("auto_grade"):
                grade_profile_id = (
                    body.auto_grade_provider_profile_id
                    or body.provider_profile_id
                )
                grade_profile = system_store.researcher_profile(grade_profile_id)
                if grade_profile is None:
                    raise ValueError(
                        "That researcher auto-grade LLM profile is not available."
                    )
                payload.update(
                    {
                        "auto_grade_provider": (
                            grade_profile.get("type") or "ollama"
                        ),
                        "auto_grade_model": grade_profile.get("model"),
                        "auto_grade_base_url": grade_profile.get("base_url"),
                        "auto_grade_api_key": grade_profile.get("api_key"),
                        "auto_grade_provider_profile_id": grade_profile_id,
                        "auto_grade_generation": (
                            profile_generation_options(grade_profile) or None
                        ),
                    }
                )
            body = RAGRunRequest(**payload)

        return managers.rag.create(body, owner=user.username)
    except HTTPException:
        raise
    except ValueError as exc:
        # A missing/stale approved profile is semantically unprocessable rather
        # than malformed HTTP; keep the actionable 422 contract used by Research.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Research could not start: {exc}",
        ) from exc


@router.post("/upsert")
def create_upsert_job(
    body: UpsertJobCreate,
    request: Request,
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    try:
        user = request_user(request)
        if not body.include_updates:
            for item in body.items:
                item.record.pop("updates", None)

        for item in body.items:
            for entry in item.audit_entries:
                if not entry.get("initiated_by"):
                    entry["initiated_by"] = user.username
            if item.replace_updates is not None:
                for entry in item.replace_updates:
                    if not entry.get("initiated_by"):
                        entry["initiated_by"] = user.username

        return managers.upsert.create(body, owner=user.username)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_jobs(
    request: Request,
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    user = request_user(request)
    if user.role != "admin":
        jobs = [
            job
            for job in managers.rag.list()
            if job.get("owner") == user.username
        ]
    else:
        jobs = (
            managers.llm.list()
            + managers.llm_tools.list()
            + managers.rag.list()
            + managers.upsert.list()
            + pdf_corpus_builds.list_operations()
        )
    jobs.sort(key=lambda job: job.get("created_at", ""), reverse=True)
    return {"jobs": jobs}


@router.get("/{job_id}")
def get_job(
    job_id: str,
    request: Request,
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    try:
        user = request_user(request)
        manager = _job_manager_for(job_id, managers)
        job = _researcher_job_access(user, manager, job_id, managers)
        if user.role != "admin":
            return sanitize_rag_job(
                job,
                max_chars=settings.researcher_text_max_chars,
            )
        return job
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc


@router.post("/{job_id}/cancel")
def cancel_job(
    job_id: str,
    request: Request,
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    try:
        user = request_user(request)
        manager = _job_manager_for(job_id, managers)
        _researcher_job_access(user, manager, job_id, managers)
        result = manager.cancel(job_id)
        if manager is pdf_corpus_builds:
            return manager.operation(job_id)
        if user.role != "admin":
            return sanitize_rag_job(
                result,
                max_chars=settings.researcher_text_max_chars,
            )
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc


@router.delete("/{job_id}")
def delete_job(
    job_id: str,
    request: Request,
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    try:
        user = request_user(request)
        manager = _job_manager_for(job_id, managers)
        _researcher_job_access(user, manager, job_id, managers)
        manager.delete(job_id)
        return {"deleted": job_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("")
def clear_finished_jobs(
    managers: JobManagers = Depends(get_job_managers),
) -> dict[str, Any]:
    return {
        "deleted": (
            managers.llm.clear_finished()
            + managers.llm_tools.clear_finished()
            + managers.rag.clear_finished()
            + managers.upsert.clear_finished()
            + pdf_corpus_builds.clear_finished()
        )
    }
