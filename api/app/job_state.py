# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import copy
import re
import threading
import time
from datetime import UTC, datetime
from typing import Any

from .persistence import job_repository

JobPayload = dict[str, Any]
JobPayloadList = list[JobPayload]


def iso_now() -> str:
    """Return the current UTC timestamp in ISO 8601 form."""
    return datetime.now(UTC).isoformat()


def error_details(exc: Exception | dict[str, Any]) -> dict[str, Any]:
    """Normalize upstream and local exceptions into durable job error metadata."""
    if isinstance(exc, dict):
        message = str(exc.get("message") or exc.get("error") or exc)
        status = exc.get("status_code") or exc.get("http_status")
        diagnostic = exc.get("diagnostic")
    else:
        response = getattr(exc, "response", None)
        status = (
            getattr(exc, "status_code", None)
            or getattr(exc, "status", None)
            or getattr(response, "status_code", None)
        )
        message = str(
            getattr(exc, "message", None)
            or str(exc)
            or exc.__class__.__name__
        )
        diagnostic = getattr(exc, "diagnostic", None)
        if not diagnostic and response is not None:
            try:
                diagnostic = (
                    str(getattr(response, "text", "") or "").strip()[:2000]
                    or None
                )
            except Exception:
                diagnostic = None

    match = re.search(
        r"(?:returned\s+HTTP|HTTP(?:Error)?\s*[: ]?|status(?:_code)?[=: ]+)([45]\d\d)",
        message,
        re.I,
    )
    if match:
        embedded = int(match.group(1))
        if status is None or int(status) == 502 or embedded != 502:
            status = embedded

    try:
        status = int(status) if status is not None else None
    except (TypeError, ValueError):
        status = None

    return {
        "message": message,
        "http_status": status,
        "diagnostic": str(diagnostic)[:12000] if diagnostic else None,
    }


def store_job_error(job: JobPayload, exc: Exception) -> dict[str, Any]:
    """Attach normalized fatal-error metadata to a live job payload."""
    details = error_details(exc)
    job["fatal_error"] = details["message"]
    job["error_message"] = details["message"]
    job["http_status"] = details["http_status"]
    job["error_diagnostic"] = details["diagnostic"]
    return details


# Small, text-free fields that describe a job's live state. The realtime plane
# publishes only these; clients fetch full job detail (results, requests,
# evidence, diagnostics) through the owner-scoped REST endpoints.
_REALTIME_SCALAR_KEYS = (
    "id",
    "type",
    "tool",
    "mode",
    "owner",
    "status",
    "stage",
    "total",
    "completed",
    "failed",
    "cancel_requested",
    "created_at",
    "started_at",
    "finished_at",
    "store_name",
    "build_id",
    "dismissed",
)
_REALTIME_TEXT_LIMIT = 240
# Grading details quote the research question; it stays in the owner-scoped REST
# job detail rather than generic progress events.
_REALTIME_DETAIL_EXCLUDED_TOOLS = frozenset({"rag_grade", "rag_grade_batch"})
_REALTIME_ACTIVE_STATUSES = frozenset({"queued", "running", "cancelling"})


def job_realtime_summary(job: JobPayload) -> JobPayload:
    """Bounded live-state summary shared by every manager's realtime feed."""
    summary: JobPayload = {key: job.get(key) for key in _REALTIME_SCALAR_KEYS if key in job}
    detail = job.get("stage_detail")
    # Only live operational detail is published. A finished job's detail can be
    # an upstream error message, which clients read from REST with the rest of
    # the error metadata.
    if (
        detail not in (None, "")
        and job.get("status") in _REALTIME_ACTIVE_STATUSES
        and (job.get("tool") or job.get("mode")) not in _REALTIME_DETAIL_EXCLUDED_TOOLS
    ):
        summary["stage_detail"] = str(detail)[:_REALTIME_TEXT_LIMIT]
    summary["warnings_count"] = len(job.get("warnings") or [])
    summary["has_error"] = bool(job.get("fatal_error") or job.get("error_message") or job.get("error"))
    results = job.get("results")
    if job.get("type") == "llm" and isinstance(results, list):
        summary["pending_result_count"] = sum(
            1 for result in results
            if isinstance(result, dict) and not result.get("error") and result.get("proposal")
        )
    return summary


class PersistentJobStateMixin:
    """Mirror live worker state into the durable SQLite operation ledger.

    Workers retain an in-process working copy for low-latency progress updates,
    while SQLite remains the durable source across restarts. A lightweight
    checkpoint loop captures nested progress/event mutations without forcing a
    database transaction for every token or record-field update.
    """

    JOB_TYPE = "operation"
    _lock: threading.RLock
    _jobs: dict[str, JobPayload]

    def _start_persistent_state(self) -> None:
        persisted = job_repository.load(self.JOB_TYPE)
        with self._lock:
            self._jobs = {
                str(job["id"]): copy.deepcopy(job)
                for job in persisted
                if job.get("id")
            }

        thread = threading.Thread(
            target=self._persistence_loop,
            daemon=True,
            name=f"derridai-{self.JOB_TYPE}-sqlite-checkpoint",
        )
        self._persistence_thread = thread
        thread.start()

    def _persistence_loop(self) -> None:
        while True:
            time.sleep(1.0)
            try:
                with self._lock:
                    jobs = [copy.deepcopy(job) for job in self._jobs.values()]
                if jobs:
                    job_repository.upsert_many(jobs)
            except Exception as exc:
                # Persistence is allowed to degrade temporarily, but the failure
                # must remain visible on active jobs and retry on the next tick.
                detail = f"Durable job checkpoint failed and will be retried: {exc}"
                with self._lock:
                    for job in self._jobs.values():
                        if job.get("status") in {"queued", "running", "cancelling"}:
                            warnings = job.setdefault("warnings", [])
                            if detail not in warnings[-3:]:
                                warnings.append(detail)

    def _persist_job(self, job_id: str) -> None:
        with self._lock:
            job = copy.deepcopy(self._jobs.get(job_id))
        if job is not None:
            job_repository.upsert(job)

    def _persist_all_jobs(self) -> None:
        with self._lock:
            jobs = [copy.deepcopy(job) for job in self._jobs.values()]
        job_repository.upsert_many(jobs)

    def realtime_job_summaries(self) -> JobPayloadList:
        """Live-state summaries for the realtime observer (read-only, no deep copy).

        Event emission is derived from this one shared view rather than from
        per-manager socket calls, so status/terminal semantics stay identical to
        the REST snapshot and a publishing failure can never affect a worker.
        """
        with self._lock:
            return [job_realtime_summary(job) for job in self._jobs.values()]

    def realtime_job_summary(self, job_id: str) -> JobPayload | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job_realtime_summary(job) if job is not None else None

    def clear_all(self) -> int:
        """Drop in-memory and durable history for this manager."""
        with self._lock:
            count = len(self._jobs)
            self._jobs.clear()

            provider_active = getattr(self, "_provider_active", None)
            if isinstance(provider_active, dict):
                provider_active.clear()

            active = getattr(self, "_active", None)
            if isinstance(active, dict):
                active.clear()

        job_repository.clear_type(self.JOB_TYPE)
        return count
