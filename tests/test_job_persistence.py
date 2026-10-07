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
import threading

from app import job_state
from app.job_state import PersistentJobStateMixin
from app.persistence import SQLiteJobRepository


class FakeJobRepository:
    def __init__(self, jobs):
        self.jobs = {str(job["id"]): copy.deepcopy(job) for job in jobs}
        self.upsert_many_calls = []

    def load_active(self, job_type):
        return [
            copy.deepcopy(job)
            for job in self.jobs.values()
            if job.get("type") == job_type
            and job.get("status") in {"queued", "running", "cancelling"}
        ]

    def load(self, job_type):
        return [
            copy.deepcopy(job)
            for job in self.jobs.values()
            if job.get("type") == job_type
        ]

    def get(self, job_id, *, job_type=None):
        job = self.jobs.get(str(job_id))
        if job is None or (job_type is not None and job.get("type") != job_type):
            return None
        return copy.deepcopy(job)

    def upsert(self, job):
        self.jobs[str(job["id"])] = copy.deepcopy(job)

    def upsert_many(self, jobs):
        snapshots = [copy.deepcopy(job) for job in jobs]
        self.upsert_many_calls.append(snapshots)
        for job in snapshots:
            self.jobs[str(job["id"])] = copy.deepcopy(job)

    def footprints(self, job_type):
        out = []
        for job in self.jobs.values():
            if job.get("type") != job_type:
                continue
            size = len(job_state.json.dumps(job, ensure_ascii=False, separators=(",", ":")).encode())
            out.append(
                (
                    str(job["id"]),
                    str(job.get("created_at") or ""),
                    size,
                    str(job.get("status") or "") in {"queued", "running", "cancelling"},
                )
            )
        return out

    def delete(self, job_id):
        return self.jobs.pop(str(job_id), None) is not None

    def clear_finished(self, job_type):
        ids = [
            job_id
            for job_id, job in self.jobs.items()
            if job.get("type") == job_type
            and job.get("status") not in {"queued", "running", "cancelling"}
        ]
        for job_id in ids:
            del self.jobs[job_id]
        return len(ids)

    def clear_type(self, job_type):
        ids = [job_id for job_id, job in self.jobs.items() if job.get("type") == job_type]
        for job_id in ids:
            del self.jobs[job_id]
        return len(ids)


class Jobs(PersistentJobStateMixin):
    JOB_TYPE = "test"
    RESIDENT_FINISHED_MAX_JOBS = 0

    def __init__(self):
        self._lock = threading.RLock()
        self._persistence_io_lock = threading.Lock()
        self._jobs = {}

    def _persistence_loop(self):
        # Startup behavior is under test, not the immortal daemon loop.
        return


def _job(job_id, status, *, payload="x", job_type="test"):
    return {
        "id": job_id,
        "type": job_type,
        "status": status,
        "created_at": f"2026-10-06T00:00:0{len(job_id)}+00:00",
        "events": [],
        "payload": payload,
    }


def test_manager_startup_hydrates_only_active_jobs(monkeypatch):
    repository = FakeJobRepository(
        [
            _job("active", "running"),
            _job("finished", "completed", payload="large historical result"),
        ]
    )
    monkeypatch.setattr(job_state, "job_repository", repository)

    manager = Jobs()
    manager._start_persistent_state()

    assert set(manager._jobs) == {"active"}
    assert {job["id"] for job in manager._all_job_records()} == {"active", "finished"}
    assert manager._get_job_record("finished")["payload"] == "large historical result"


def test_checkpoint_writes_only_active_jobs(monkeypatch):
    repository = FakeJobRepository([])
    monkeypatch.setattr(job_state, "job_repository", repository)
    manager = Jobs()
    manager._recent_terminal_summaries = {}
    manager._jobs = {
        "active": _job("active", "running"),
        "finished": _job("finished", "completed", payload="do not rewrite me"),
    }

    manager._checkpoint_active_jobs()

    assert len(repository.upsert_many_calls) == 1
    assert [job["id"] for job in repository.upsert_many_calls[0]] == ["active"]


def test_terminal_job_is_persisted_once_then_evicted_from_full_resident_state(monkeypatch):
    repository = FakeJobRepository([])
    monkeypatch.setattr(job_state, "job_repository", repository)
    manager = Jobs()
    manager._recent_terminal_summaries = {}
    manager._jobs = {
        "done": _job("done", "completed", payload="z" * 1_000_000),
    }

    manager._persist_job("done")

    assert "done" not in manager._jobs
    assert "done" in manager._recent_terminal_summaries
    assert manager._get_job_record("done")["payload"] == "z" * 1_000_000


def test_clear_finished_uses_durable_count_even_when_history_is_not_resident(monkeypatch):
    repository = FakeJobRepository(
        [
            _job("active", "running"),
            _job("done-a", "completed"),
            _job("done-b", "failed"),
        ]
    )
    monkeypatch.setattr(job_state, "job_repository", repository)
    manager = Jobs()
    manager._recent_terminal_summaries = {}
    manager._jobs = {"active": _job("active", "running")}

    assert manager._clear_finished_records() == 2
    assert set(repository.jobs) == {"active"}
    assert set(manager._jobs) == {"active"}


def test_repository_recovery_preserves_restart_resumable_upserts(tmp_path):
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    repository.upsert(_job("upsert-running", "running", job_type="upsert"))
    repository.upsert(_job("llm-running", "running", job_type="llm"))

    assert repository.recover_interrupted() == 1
    assert repository.get("upsert-running", job_type="upsert")["status"] == "running"
    llm = repository.get("llm-running", job_type="llm")
    assert llm["status"] == "failed"
    assert "restart" in llm["fatal_error"].lower()


def test_repository_footprints_measure_utf8_bytes_without_deserializing(tmp_path):
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    job = _job("unicode", "completed", payload="Derrida — différance")
    repository.upsert(job)

    footprints = repository.footprints("test")

    expected = len(job_state.json.dumps(job, ensure_ascii=False, separators=(",", ":")).encode())
    assert footprints == [("unicode", job["created_at"], expected, False)]


def test_repository_list_summaries_drop_heavy_results(tmp_path):
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    job = {
        **_job("rag-finished", "completed", job_type="rag"),
        "result": {"answer": "x" * 100_000},
        "results": [{"proposal": {"changes": {"speaker": "Derrida"}}}],
        "request": {"prompt": "What is différance?"},
        "_resume_dictionary": {"heavy": "y" * 100_000},
        "_resume_failed_keys": ["heavy"],
    }
    repository.upsert(job)

    summaries = repository.load_summaries("rag")

    assert summaries == [
        {
            key: value
            for key, value in job.items()
            if key
            not in {
                "result",
                "results",
                "_resume_dictionary",
                "_resume_failed_keys",
            }
        }
    ]
