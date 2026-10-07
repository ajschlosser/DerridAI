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

"""Background jobs that install Document Intelligence language packs.

Each install runs on its own thread, reports byte progress, can be cancelled, and is
mirrored into the durable operation ledger. After a restart an interrupted install is
marked failed (never replayed); its staging directory is discarded on the next try.
"""
from __future__ import annotations

import copy
import threading
import uuid
from typing import Any

from . import document_nlp_packs as packs
from .job_state import JobPayloadList, PersistentJobStateMixin, iso_now

ACTIVE = {"queued", "running", "cancelling"}


class DocumentNlpPackJobManager(PersistentJobStateMixin):
    JOB_TYPE = "document_nlp_pack"

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._cancel: dict[str, threading.Event] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._start_persistent_state()

    def active_for(self, pack_id: str) -> dict[str, Any] | None:
        with self._lock:
            for job in self._jobs.values():
                if job.get("pack_id") == pack_id and job.get("status") in ACTIVE:
                    return copy.deepcopy(job)
        return None

    def start(self, pack_id: str, *, owner: str | None = None) -> dict[str, Any]:
        entry = packs.pack_status(packs.get_pack(pack_id))
        if not entry["installable"]:
            raise ValueError("This pack is listed for reference; no worker for its engine is bundled.")
        if self.active_for(pack_id):
            raise ValueError("This pack is already being installed.")
        job_id = f"nlp-pack-{uuid.uuid4().hex[:12]}"
        job = {
            "id": job_id,
            "type": self.JOB_TYPE,
            "mode": "install",
            "pack_id": pack_id,
            "language": entry["language"],
            "label": entry["label"],
            "status": "queued",
            "owner": owner,
            "created_at": iso_now(),
            "started_at": None,
            "finished_at": None,
            "stage": "download",
            "stage_detail": "",
            "completed": 0,
            "total": entry["download_bytes"],
            "warnings": [],
            "events": [],
        }
        with self._lock:
            self._jobs[job_id] = job
            self._cancel[job_id] = threading.Event()
        self._persist_job(job_id)
        thread = threading.Thread(target=self._run, args=(job_id,), daemon=True, name=f"derridai-{job_id}")
        self._threads[job_id] = thread
        thread.start()
        return self.get(job_id)

    def _run(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "running"
            job["started_at"] = iso_now()
            pack_id = job["pack_id"]
        cancelled = self._cancel[job_id].is_set

        def progress(done: int, total: int, detail: str) -> None:
            with self._lock:
                current = self._jobs[job_id]
                current["completed"], current["total"], current["stage_detail"] = done, total, detail

        status, error = "completed", None
        try:
            manifest = packs.install_pack(pack_id, cancelled=cancelled, progress=progress)
            with self._lock:
                self._jobs[job_id]["result"] = {"pack_id": pack_id, "language": manifest["language"]}
        except packs.InstallCancelled:
            status = "cancelled"
        except Exception as exc:  # noqa: BLE001 - the durable record must say why the install stopped
            status, error = "failed", str(exc) or exc.__class__.__name__
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = status
            job["finished_at"] = iso_now()
            if error:
                job["fatal_error"] = job["error_message"] = error
        self._persist_job(job_id)
        with self._lock:
            self._threads.pop(job_id, None)
            self._cancel.pop(job_id, None)

    def list(self) -> JobPayloadList:
        jobs = [copy.deepcopy(job) for job in self._all_job_records()]
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

    def delete(self, job_id: str) -> None:
        self._delete_finished_record(
            job_id,
            active_error="Cancel the install before deleting it.",
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
