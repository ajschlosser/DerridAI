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

"""Background jobs for Corpus Capture discovery, acquisition, retry and refresh.

Each job runs on its own thread, is cancellable, mirrors its progress into the
shared durable operation ledger (so it appears in Operations and survives a
browser close), and is marked failed — never replayed — after a restart.
"""
from __future__ import annotations

import copy
import threading
import uuid
from typing import Any

from .job_state import JobPayloadList, PersistentJobStateMixin, iso_now
from .source_capture import CorpusCaptureService
from .source_identity import CaptureError

ACTIVE = {"queued", "running", "cancelling"}
KINDS = {"discover", "acquire", "retry", "refresh"}


class CaptureJobManager(PersistentJobStateMixin):
    JOB_TYPE = "corpus_capture"

    def __init__(self, service: CorpusCaptureService) -> None:
        self.service = service
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._cancel: dict[str, threading.Event] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._start_persistent_state()

    def active_for(self, capture_id: str) -> dict[str, Any] | None:
        with self._lock:
            for job in self._jobs.values():
                if job.get("capture_id") == capture_id and job.get("status") in ACTIVE:
                    return copy.deepcopy(job)
        return None

    def start(self, capture_id: str, kind: str, *, owner: str | None = None) -> dict[str, Any]:
        if kind not in KINDS:
            raise ValueError(f"Unsupported capture job: {kind}")
        capture = self.service.store.get_capture(capture_id)
        if self.active_for(capture_id):
            raise ValueError("This capture already has a running operation.")
        if kind in {"acquire", "retry"} and not capture.get("discovery_completed_at"):
            raise ValueError("Discover sources before acquiring them.")
        job_id = f"capture-{uuid.uuid4().hex[:12]}"
        author = str((capture.get("author") or {}).get("canonical_name") or "")
        job = {
            "id": job_id,
            "type": self.JOB_TYPE,
            "mode": kind,
            "capture_id": capture_id,
            "label": author,
            "status": "queued",
            "owner": owner,
            "created_at": iso_now(),
            "started_at": None,
            "finished_at": None,
            "stage": kind,
            "stage_detail": "",
            "completed": 0,
            "total": 0,
            "warnings": [],
            "events": [],
        }
        with self._lock:
            self._jobs[job_id] = job
            self._cancel[job_id] = threading.Event()
        self._persist_job(job_id)
        thread = threading.Thread(target=self._run, args=(job_id,), daemon=True, name=f"derridai-capture-{job_id}")
        self._threads[job_id] = thread
        thread.start()
        return self.get(job_id)

    def _progress(self, job_id: str, phase: str, detail: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["stage"] = phase
            job["completed"] = int(detail.get("done") or 0)
            job["total"] = int(detail.get("total") or 0)
            job["stage_detail"] = str(detail.get("project") or detail.get("current") or "")

    def _run(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "running"
            job["started_at"] = iso_now()
            kind, capture_id = job["mode"], job["capture_id"]
        cancelled = self._cancel[job_id].is_set

        def progress(phase: str, detail: dict[str, Any]) -> None:
            self._progress(job_id, phase, detail)

        status = "completed"
        error: str | None = None
        try:
            if kind in {"discover", "refresh"}:
                result = self.service.discover(capture_id, cancelled=cancelled, progress=progress)
            else:
                result = self.service.acquire(capture_id, retry_failed_only=kind == "retry", cancelled=cancelled, progress=progress)
            if result.get("status") == "cancelled":
                status = "cancelled"
            with self._lock:
                job = self._jobs[job_id]
                job["result"] = {
                    "capture_id": capture_id,
                    "status": result.get("status"),
                    "summary": copy.deepcopy(result.get("summary") or {}),
                    "progress": copy.deepcopy(result.get("progress") or {}),
                }
        except CaptureError as exc:
            status, error = "failed", exc.message
            self.service.store.update_capture(capture_id, status="failed", phase="failed", errors=[exc.to_dict()])
        except Exception as exc:  # noqa: BLE001 - the durable record must say why the job stopped
            status, error = "failed", str(exc) or exc.__class__.__name__
            self.service.store.update_capture(capture_id, status="failed", phase="failed", errors=[{"code": "acquisition_failed", "message": error}])
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = status
            job["finished_at"] = iso_now()
            if error:
                job["fatal_error"] = job["error_message"] = error
        self._persist_job(job_id)

    def list(self) -> JobPayloadList:
        jobs = [copy.deepcopy(job) for job in self._list_job_records()]
        return sorted(jobs, key=lambda job: job["created_at"], reverse=True)

    def get(self, job_id: str) -> dict[str, Any]:
        return copy.deepcopy(self._get_job_record(job_id))

    def cancel(self, job_id: str) -> dict[str, Any]:
        self._load_job_for_mutation(job_id)
        with self._lock:
            job = self._jobs[job_id]
            if job["status"] in ACTIVE:
                job["status"] = "cancelling"
                job["cancel_requested"] = True
                self._cancel.setdefault(job_id, threading.Event()).set()
        self._persist_job(job_id)
        return self.get(job_id)

    def cancel_capture(self, capture_id: str) -> dict[str, Any] | None:
        active = self.active_for(capture_id)
        return self.cancel(active["id"]) if active else None

    def delete(self, job_id: str) -> None:
        self._delete_finished_record(
            job_id,
            active_error="Cancel the capture operation before deleting it.",
        )

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for job in self._jobs.values() if job["status"] in ACTIVE)

    def clear_finished(self) -> int:
        return self._clear_finished_records()

    def wait(self, job_id: str, timeout: float = 30.0) -> dict[str, Any]:
        """Test/diagnostic helper: block until the job's thread finishes."""
        thread = self._threads.get(job_id)
        if thread:
            thread.join(timeout)
        return self.get(job_id)
