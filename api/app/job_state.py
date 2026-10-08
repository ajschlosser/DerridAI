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

import copy
import json
import re
import threading
import time
from datetime import UTC, datetime
from threading import Thread
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
    """Keep active job state resident while SQLite owns historical operation data.

    Active jobs stay in memory for low-latency worker coordination. Finished
    history is durable and loaded on demand instead of being permanently
    deserialized into every manager. The checkpoint loop persists active jobs
    only, so an idle DerridAI process performs no recurring historical-job I/O.
    """

    JOB_TYPE = "operation"
    ACTIVE_STATUSES = frozenset({"queued", "running", "cancelling"})
    # SQLite is the sole owner of full terminal payloads. Realtime continuity
    # needs only the bounded summaries below; GET-by-id reads full historical
    # detail from SQLite on demand. Subclasses may opt into a tiny resident
    # terminal cache, but the application default keeps none.
    RESIDENT_FINISHED_MAX_JOBS = 0
    RESIDENT_FINISHED_MAX_BYTES = 0
    RECENT_TERMINAL_SUMMARY_LIMIT = 32

    _lock: threading.RLock
    _jobs: dict[str, JobPayload]

    def _start_persistent_state(self) -> None:
        persisted = job_repository.load_active(self.JOB_TYPE)
        with self._lock:
            self._jobs = {
                str(job["id"]): copy.deepcopy(job)
                for job in persisted
                if job.get("id")
            }
            self._recent_terminal_summaries: dict[str, JobPayload] = {}
            self._persistence_io_lock = threading.Lock()
            self._persistent_state_started = True

        thread = Thread(
            target=self._persistence_loop,
            daemon=True,
            name=f"derridai-{self.JOB_TYPE}-sqlite-checkpoint",
        )
        self._persistence_thread = thread
        thread.start()

    def _terminal_summaries(self) -> dict[str, JobPayload]:
        """Return the bounded terminal-summary cache, including lightweight test managers."""
        summaries = getattr(self, "_recent_terminal_summaries", None)
        if summaries is not None:
            return summaries
        with self._lock:
            summaries = getattr(self, "_recent_terminal_summaries", None)
            if summaries is None:
                summaries = {}
                self._recent_terminal_summaries = summaries
            return summaries

    def _persistence_lock(self) -> threading.Lock:
        """Return the manager's persistence lock, lazily for lightweight test doubles."""
        lock = getattr(self, "_persistence_io_lock", None)
        if lock is not None:
            return lock
        with self._lock:
            lock = getattr(self, "_persistence_io_lock", None)
            if lock is None:
                lock = threading.Lock()
                self._persistence_io_lock = lock
            return lock

    def _active_snapshots(self) -> JobPayloadList:
        """Copy only live jobs for one durable checkpoint."""
        with self._lock:
            return [
                copy.deepcopy(job)
                for job in self._jobs.values()
                if str(job.get("status") or "") in self.ACTIVE_STATUSES
            ]

    def _checkpoint_active_jobs(self) -> None:
        with self._persistence_lock():
            jobs = self._active_snapshots()
            if jobs:
                job_repository.upsert_many(jobs)

    def _persistence_loop(self) -> None:
        while True:
            time.sleep(1.0)
            try:
                self._checkpoint_active_jobs()
            except Exception as exc:
                # Persistence is allowed to degrade temporarily, but the failure
                # must remain visible on active jobs and retry on the next tick.
                detail = f"Durable job checkpoint failed and will be retried: {exc}"
                with self._lock:
                    for job in self._jobs.values():
                        if str(job.get("status") or "") in self.ACTIVE_STATUSES:
                            warnings = job.setdefault("warnings", [])
                            if detail not in warnings[-3:]:
                                warnings.append(detail)

    def _remember_terminal_summary(self, job: JobPayload) -> None:
        summary = job_realtime_summary(job)
        job_id = str(summary.get("id") or "")
        if not job_id:
            return
        summaries = self._terminal_summaries()
        summaries.pop(job_id, None)
        summaries[job_id] = summary
        while len(summaries) > self.RECENT_TERMINAL_SUMMARY_LIMIT:
            oldest = next(iter(summaries))
            summaries.pop(oldest, None)

    @staticmethod
    def _payload_size(job: JobPayload) -> int:
        return len(
            json.dumps(
                job,
                ensure_ascii=False,
                separators=(",", ":"),
                default=str,
            ).encode()
        )

    def _prune_resident_finished(self) -> None:
        """Evict full terminal payloads; SQLite owns historical job detail."""

        # The normal application policy keeps no full finished jobs resident.
        # Evict directly after the durable write rather than scanning SQLite
        # footprints on every completion merely to prove that zero rows may stay.
        if (
            self.RESIDENT_FINISHED_MAX_JOBS <= 0
            or self.RESIDENT_FINISHED_MAX_BYTES <= 0
        ):
            with self._lock:
                for job_id, job in list(self._jobs.items()):
                    if str(job.get("status") or "") in self.ACTIVE_STATUSES:
                        continue
                    self._remember_terminal_summary(job)
                    self._jobs.pop(job_id, None)
            return

        # Optional subclass policy: keep a strictly bounded amount of recent
        # terminal detail resident. Durable byte sizes avoid serializing large
        # results again solely to decide which entries fit.
        durable_sizes = {
            job_id: size
            for job_id, _created_at, size, _active
            in job_repository.footprints(self.JOB_TYPE)
        }
        with self._lock:
            finished = [
                (job_id, job)
                for job_id, job in self._jobs.items()
                if str(job.get("status") or "") not in self.ACTIVE_STATUSES
            ]
            finished.sort(
                key=lambda item: str(item[1].get("created_at") or ""),
                reverse=True,
            )
            keep: set[str] = set()
            kept_bytes = 0
            for job_id, job in finished:
                size = durable_sizes.get(
                    str(job_id),
                    self.RESIDENT_FINISHED_MAX_BYTES + 1,
                )
                if (
                    len(keep) < self.RESIDENT_FINISHED_MAX_JOBS
                    and kept_bytes + size <= self.RESIDENT_FINISHED_MAX_BYTES
                ):
                    keep.add(job_id)
                    kept_bytes += size
                    continue
                self._remember_terminal_summary(job)
                self._jobs.pop(job_id, None)

    def _persist_job(self, job_id: str) -> None:
        with self._lock:
            job = copy.deepcopy(self._jobs.get(job_id))
        if job is None:
            return
        with self._persistence_lock():
            job_repository.upsert(job)
        if str(job.get("status") or "") not in self.ACTIVE_STATUSES:
            self._prune_resident_finished()

    def _persist_all_jobs(self) -> None:
        with self._lock:
            jobs = [copy.deepcopy(job) for job in self._jobs.values()]
        if jobs:
            with self._persistence_lock():
                job_repository.upsert_many(jobs)
        self._prune_resident_finished()

    def _list_job_records(self) -> JobPayloadList:
        """Merge lightweight durable summaries with newer resident live state."""
        persisted = {
            str(job["id"]): job
            for job in job_repository.load_summaries(self.JOB_TYPE)
            if job.get("id")
        }
        with self._lock:
            for job_id, job in self._jobs.items():
                persisted[str(job_id)] = copy.deepcopy(job)
        return list(persisted.values())

    def _all_job_records(self) -> JobPayloadList:
        """Merge durable history with newer resident live state."""
        persisted = {
            str(job["id"]): job
            for job in job_repository.load(self.JOB_TYPE)
            if job.get("id")
        }
        with self._lock:
            for job_id, job in self._jobs.items():
                persisted[str(job_id)] = copy.deepcopy(job)
        return list(persisted.values())

    def _get_job_record(self, job_id: str) -> JobPayload:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                return copy.deepcopy(job)
        persisted = job_repository.get(job_id, job_type=self.JOB_TYPE)
        if persisted is None:
            raise KeyError(job_id)
        return persisted

    def _load_job_for_mutation(self, job_id: str) -> JobPayload:
        """Rehydrate a historical job only for the duration of a mutation."""
        with self._lock:
            existing = self._jobs.get(job_id)
            if existing is not None:
                return existing
        persisted = job_repository.get(job_id, job_type=self.JOB_TYPE)
        if persisted is None:
            raise KeyError(job_id)
        with self._lock:
            return self._jobs.setdefault(job_id, persisted)

    def _delete_finished_record(self, job_id: str, *, active_error: str) -> None:
        with self._persistence_lock():
            job = self._get_job_record(job_id)
            if str(job.get("status") or "") in self.ACTIVE_STATUSES:
                raise ValueError(active_error)
            with self._lock:
                self._jobs.pop(job_id, None)
                self._terminal_summaries().pop(job_id, None)
            if not job_repository.delete(job_id):
                raise KeyError(job_id)

    def _clear_finished_records(self) -> int:
        with self._persistence_lock():
            with self._lock:
                finished_ids = [
                    job_id
                    for job_id, job in self._jobs.items()
                    if str(job.get("status") or "") not in self.ACTIVE_STATUSES
                ]
                for job_id in finished_ids:
                    self._jobs.pop(job_id, None)
                    self._terminal_summaries().pop(job_id, None)
            return job_repository.clear_finished(self.JOB_TYPE)

    def _snapshot_finished_records(self) -> JobPayloadList:
        return [
            copy.deepcopy(job)
            for job in self._all_job_records()
            if str(job.get("status") or "") not in self.ACTIVE_STATUSES
        ]

    def realtime_job_summaries(self) -> JobPayloadList:
        """Small live/terminal summaries; full history stays in SQLite."""
        with self._lock:
            summaries = {
                str(job_id): job_realtime_summary(job)
                for job_id, job in self._jobs.items()
            }
            for job_id, summary in self._terminal_summaries().items():
                summaries.setdefault(job_id, copy.deepcopy(summary))
            return list(summaries.values())

    def realtime_job_summary(self, job_id: str) -> JobPayload | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                return job_realtime_summary(job)
            summary = self._terminal_summaries().get(job_id)
            return copy.deepcopy(summary) if summary is not None else None

    def job_footprints(self) -> list[tuple[str, str, int, bool]]:
        """Retention metadata without hydrating every historical payload."""
        footprints: dict[str, tuple[str, str, int, bool]] = {}
        # Lightweight managers used by tests and maintenance tooling may opt out
        # of the durable startup path; in that case their resident state is the
        # complete source of truth and must not be mixed with the global ledger.
        if getattr(self, "_persistent_state_started", False):
            footprints.update({
                job_id: (job_id, created_at, size, active)
                for job_id, created_at, size, active
                in job_repository.footprints(self.JOB_TYPE)
            })
        with self._lock:
            for job_id, job in self._jobs.items():
                footprints[str(job_id)] = (
                    str(job_id),
                    str(job.get("created_at") or ""),
                    self._payload_size(job),
                    str(job.get("status") or "") in self.ACTIVE_STATUSES,
                )
        return list(footprints.values())

    def clear_all(self) -> int:
        """Drop in-memory and durable history without checkpoint resurrection."""
        with self._persistence_lock():
            with self._lock:
                resident_count = len(self._jobs)
                self._jobs.clear()
                self._terminal_summaries().clear()

                provider_active = getattr(self, "_provider_active", None)
                if isinstance(provider_active, dict):
                    provider_active.clear()

                active = getattr(self, "_active", None)
                if isinstance(active, dict):
                    active.clear()

            durable_count = job_repository.clear_type(self.JOB_TYPE)

        return max(durable_count, resident_count)
