# Copyright 2026 Aaron John Schlosser, PhD.
"""Research (RAG) run reads shared by REST and GraphQL.

Owner-scoped like ``GET /api/jobs/{id}``: administrators see every run, a
Researcher only their own. ``generated_claims`` is further restricted to
administrators by the GraphQL root's own field policy, not by this service.
"""
from __future__ import annotations

from typing import Any

from ..config import settings
from ..researcher_view import sanitize_rag_job
from ..services import rag_jobs
from ..system_store import system_store
from .access import AccessContext, NotFound


def research_run(access: AccessContext, run_id: str) -> dict[str, Any]:
    try:
        job = rag_jobs.get(run_id)
    except KeyError as exc:
        raise NotFound(f"Research run {run_id!r} was not found.") from exc
    if not access.is_admin and job.get("owner") != access.username:
        raise NotFound(f"Research run {run_id!r} was not found.")
    if access.is_admin:
        return job
    return sanitize_rag_job(job, max_chars=settings.researcher_text_max_chars)


def generated_claims_for_run(access: AccessContext, run_id: str) -> list[dict[str, Any]]:
    """Owner-scoped generated claims produced by this run."""
    return system_store.list_generated_claims(run_id=run_id, owner=access.owner)
