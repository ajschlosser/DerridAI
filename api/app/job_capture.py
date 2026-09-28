# Copyright 2026 Aaron John Schlosser, PhD.
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
from .persistence import job_repository
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
        with self._lock:
            jobs = [copy.deepcopy(job) for job in self._jobs.values()]
        return sorted(jobs, key=lambda job: job["created_at"], reverse=True)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return copy.deepcopy(self._jobs[job_id])

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
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
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            if job["status"] in ACTIVE:
                raise ValueError("Cancel the capture operation before deleting it.")
            del self._jobs[job_id]
        job_repository.delete(job_id)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for job in self._jobs.values() if job["status"] in ACTIVE)

    def clear_finished(self) -> int:
        with self._lock:
            ids = [job_id for job_id, job in self._jobs.items() if job["status"] not in ACTIVE]
            for job_id in ids:
                del self._jobs[job_id]
        job_repository.clear_finished(self.JOB_TYPE)
        return len(ids)

    def wait(self, job_id: str, timeout: float = 30.0) -> dict[str, Any]:
        """Test/diagnostic helper: block until the job's thread finishes."""
        thread = self._threads.get(job_id)
        if thread:
            thread.join(timeout)
        return self.get(job_id)
