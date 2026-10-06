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

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .. import research_threads
from ..auth import AuthUser
from ..config import settings
from ..content_filter import enforce_researcher_text
from ..corpus_builder import pdf_corpus_builds, pdf_corpus_repository
from ..http_auth import request_user
from ..models import (
    LLMJobCreate,
    LLMJobRejectRequest,
    LLMResultResolutionRequest,
    LLMToolJobCreate,
    RAGConcurrencyUpdate,
    RAGRunRequest,
    UpsertJobCreate,
)
from ..pipelines.access import resolve_research_pipeline
from ..pipelines.overrides import resolve_pipeline_config
from ..provider_profile_options import profile_generation_options
from ..research_thread_store import ThreadBusy, ThreadNotFound
from ..researcher_view import sanitize_rag_job
from ..services import (
    capture_jobs,
    document_nlp_pack_jobs,
    llm_jobs,
    llm_tool_jobs,
    rag_jobs,
    upsert_jobs,
)
from ..system_store import system_store

router = APIRouter(tags=["jobs"])


@router.post("/api/jobs/llm")
def create_llm_job(body: LLMJobCreate, request: Request) -> dict[str, Any]:
    try:
        # ``updates`` is never part of LLM review context. Strip it even for
        # older clients so a large audit trail cannot be retained by the job.
        for item in body.items:
            item.record.pop("updates", None)
        return llm_jobs.create(body, owner=request_user(request).username)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/jobs/rag/concurrency")
def get_rag_concurrency() -> dict[str, Any]:
    return rag_jobs.concurrency_status()


@router.put("/api/jobs/rag/concurrency")
def set_rag_concurrency(body: RAGConcurrencyUpdate) -> dict[str, Any]:
    return rag_jobs.set_ollama_limit(body.ollama_max_concurrent)


@router.post("/api/jobs/{job_id}/llm-results/resolve")
def resolve_llm_job_results(job_id: str, body: LLMResultResolutionRequest) -> dict[str, Any]:
    try:
        manager = _job_manager_for(job_id)
        if manager is not llm_jobs:
            raise HTTPException(status_code=409, detail="Job is not an LLM review job.")
        return llm_jobs.resolve_results(
            job_id,
            action=body.action,
            items=[item.model_dump() for item in body.items],
            dismiss_job=body.dismiss_job,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/jobs/{job_id}/llm-results/reject")
def reject_llm_job_results(job_id: str, body: LLMJobRejectRequest) -> dict[str, Any]:
    try:
        manager = _job_manager_for(job_id)
        if manager is not llm_jobs:
            raise HTTPException(status_code=409, detail="Job is not an LLM review job.")
        return llm_jobs.reject_and_dismiss(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc


@router.post("/api/jobs/llm-tool")
def create_llm_tool_job(body: LLMToolJobCreate, request: Request) -> dict[str, Any]:
    try:
        return llm_tool_jobs.create(body, owner=request_user(request).username)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/jobs/rag")
def create_rag_job(body: RAGRunRequest, request: Request) -> dict[str, Any]:
    """Start a Research run; every run is persisted as a turn of a Research thread."""
    return start_research_run(body, request, thread_id=body.thread_id)


def start_research_run(
    body: RAGRunRequest,
    request: Request,
    *,
    thread_id: str | None = None,
    retry_turn_id: str | None = None,
) -> dict[str, Any]:
    """Shared by the job and thread routes so both apply identical validation."""
    try:
        user = request_user(request)
        if user.role != "admin":
            enforce_researcher_text({"prompt": body.prompt, "instructions": body.instructions})
        for selection in body.selected_evidence:
            if isinstance(selection.record, dict):
                selection.record.pop("updates", None)

        if body.filter_plan is not None:
            from .research_filters import ResearchFilterPreviewRequest, preview_research_filter

            preview = preview_research_filter(ResearchFilterPreviewRequest(
                collection=body.source_collection, locales=body.locales,
                metadata_filter=body.filter_plan.metadata_filter,
                document_filter=body.filter_plan.document_filter,
                source=body.filter_plan.source,
            ))
            if not preview["valid"]:
                raise ValueError(f"Invalid Research scope: {preview['errors']}")

        pipeline = resolve_research_pipeline(
            requested_id=body.pipeline_id,
            requested_version=body.pipeline_version,
            is_admin=user.role == "admin",
        )
        # Reject stale/invalid override targets before spawning a background job.
        # The same resolver runs again inside RAG execution and produces the
        # auditable effective-pipeline snapshot.
        resolve_pipeline_config(
            pipeline,
            settings_overrides=body.settings_pipeline_overrides,
            run_overrides=body.run_pipeline_overrides,
        )

        pipeline_payload = body.model_dump()
        pipeline_payload.update(
            {
                "pipeline_id": pipeline.pipeline_id,
                "pipeline_version": pipeline.version,
            }
        )
        body = RAGRunRequest(**pipeline_payload)

        if user.role != "admin":
            # Researchers may only use administrator-approved static profiles.
            # Secrets and endpoint overrides are resolved server-side, preventing
            # arbitrary provider access from a crafted browser request.
            if not body.provider_profile_id:
                raise ValueError("Select an administrator-approved researcher LLM profile.")
            profile = system_store.researcher_profile(body.provider_profile_id)
            if profile is None:
                raise ValueError("That researcher LLM profile is not available.")

            generation = profile_generation_options(profile)
            payload = body.model_dump()
            payload.update({
                "provider": profile.get("type") or "ollama",
                "model": profile.get("model"),
                "base_url": profile.get("base_url"),
                "api_key": profile.get("api_key"),
                "max_concurrent_requests": max(1, min(64, int(profile.get("max_concurrent_requests") or 1))),
            })
            # Always replace browser-supplied generation settings for a non-admin
            # role. Researcher/custom-role runs are defined by the approved static
            # profile, including the empty/default case.
            payload["generation"] = generation or None
            # Ollama profiles on the same normalized endpoint share one server-side
            # execution gate. The stored profiles are normalized to that endpoint's
            # lowest configured limit, so one profile cannot overrun a shared server.

            # The grader may use a different approved static profile.  The client
            # supplies only its profile id; provider URL, credentials and model
            # settings still come from the server-owned profile definition.
            if payload.get("auto_grade"):
                grade_profile_id = body.auto_grade_provider_profile_id or body.provider_profile_id
                grade_profile = system_store.researcher_profile(grade_profile_id)
                if grade_profile is None:
                    raise ValueError("That researcher auto-grade LLM profile is not available.")
                grade_generation = profile_generation_options(grade_profile)
                payload.update({
                    "auto_grade_provider": grade_profile.get("type") or "ollama",
                    "auto_grade_model": grade_profile.get("model"),
                    "auto_grade_base_url": grade_profile.get("base_url"),
                    "auto_grade_api_key": grade_profile.get("api_key"),
                    "auto_grade_provider_profile_id": grade_profile_id,
                    "auto_grade_generation": grade_generation or None,
                })
            body = RAGRunRequest(**payload)
        return research_threads.start_run(
            rag_jobs,
            body,
            owner=user.username,
            thread_id=thread_id,
            retry_turn_id=retry_turn_id,
        )
    except HTTPException:
        raise
    except ThreadNotFound as exc:
        raise HTTPException(status_code=404, detail="Research thread not found.") from exc
    except ThreadBusy as exc:
        raise HTTPException(
            status_code=409,
            detail="This Research thread already has a question in progress.",
        ) from exc
    except ValueError as exc:
        # UI payloads are validated client-side as well. A stale profile or
        # server-owned policy conflict is semantically unprocessable, not a
        # malformed HTTP request; Research therefore never degrades these into
        # an opaque 400 Bad Request.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Research could not start: {exc}") from exc


@router.post("/api/jobs/upsert")
def create_upsert_job(body: UpsertJobCreate, request: Request) -> dict[str, Any]:
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
        return upsert_jobs.create(body, owner=user.username)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/jobs")
def list_jobs(request: Request) -> dict[str, Any]:
    user = request_user(request)
    if user.role != "admin":
        jobs = [job for job in rag_jobs.list() if job.get("owner") == user.username]
    else:
        jobs = llm_jobs.list() + llm_tool_jobs.list() + rag_jobs.list() + upsert_jobs.list() + capture_jobs.list() + document_nlp_pack_jobs.list() + pdf_corpus_builds.list_operations()
    jobs.sort(key=lambda job: job.get("created_at", ""), reverse=True)
    return {"jobs": jobs}


def _job_manager_for(job_id: str) -> Any:
    for manager in (llm_jobs, llm_tool_jobs, rag_jobs, upsert_jobs, capture_jobs, document_nlp_pack_jobs):
        try:
            manager.get(job_id)
            return manager
        except KeyError:
            continue
    try:
        pdf_corpus_repository.get_build(job_id)
        return pdf_corpus_builds
    except KeyError:
        pass
    raise KeyError(job_id)


def _researcher_job_access(user: AuthUser, manager: Any, job_id: str) -> dict[str, Any]:
    job = manager.operation(job_id) if manager is pdf_corpus_builds else manager.get(job_id)
    if user.role != "admin":
        if manager is not rag_jobs or job.get("owner") != user.username:
            raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/api/jobs/{job_id}")
def get_job(job_id: str, request: Request) -> dict[str, Any]:
    try:
        user = request_user(request)
        manager = _job_manager_for(job_id)
        job = _researcher_job_access(user, manager, job_id)
        if user.role != "admin":
            return sanitize_rag_job(job, max_chars=settings.researcher_text_max_chars)
        return job
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str, request: Request) -> dict[str, Any]:
    try:
        user = request_user(request)
        manager = _job_manager_for(job_id)
        _researcher_job_access(user, manager, job_id)
        result = manager.cancel(job_id)
        if manager is pdf_corpus_builds:
            return manager.operation(job_id)
        if user.role != "admin":
            return sanitize_rag_job(result, max_chars=settings.researcher_text_max_chars)
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc


@router.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, request: Request) -> dict[str, Any]:
    try:
        user = request_user(request)
        manager = _job_manager_for(job_id)
        _researcher_job_access(user, manager, job_id)
        manager.delete(job_id)
        return {"deleted": job_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/api/jobs")
def clear_finished_jobs() -> dict[str, Any]:
    return {
        "deleted": (
            llm_jobs.clear_finished()
            + llm_tool_jobs.clear_finished()
            + rag_jobs.clear_finished()
            + upsert_jobs.clear_finished()
            + capture_jobs.clear_finished()
            + document_nlp_pack_jobs.clear_finished()
            + pdf_corpus_builds.clear_finished()
        )
    }

