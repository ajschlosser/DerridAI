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

"""Turns left active by an interrupted run are settled, so the thread is usable again.

Why: a restart marks interrupted jobs failed in the job ledger but not their
turns. A turn stuck "running" blocks every follow-up and retry in its thread.
How: real SQLite thread store, a dict standing in for the Research job manager.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.modules.setdefault("chromadb", types.SimpleNamespace())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import research_threads  # noqa: E402
from app.research_thread_store import ResearchThreadStore  # noqa: E402


class Jobs:
    def __init__(self) -> None:
        self.jobs: dict[str, dict] = {}

    def get(self, job_id):
        if job_id not in self.jobs:
            raise KeyError(job_id)
        return dict(self.jobs[job_id])


@pytest.fixture()
def store(tmp_path, monkeypatch) -> ResearchThreadStore:
    s = ResearchThreadStore(tmp_path / "system.sqlite3")
    monkeypatch.setattr(research_threads, "thread_store", lambda: s)
    monkeypatch.setattr(research_threads, "notify_changed", lambda: None)
    return s


def _running_turn(store, jobs, owner="alice", job_id="job-1", status="running", question="Q?"):
    thread = store.create_thread(owner)
    turn, _ = store.append_turn(thread["thread_id"], owner, question)
    store.bind_job(turn["turn_id"], owner, job_id=job_id, research_run_id=job_id)
    jobs.jobs[job_id] = {"id": job_id, "owner": owner, "status": status}
    return thread, turn


def test_interrupted_job_fails_its_turn_and_the_turn_can_be_retried(store) -> None:
    jobs = Jobs()
    thread, turn = _running_turn(store, jobs)
    # What recover_interrupted leaves behind: the job failed, the turn still running.
    jobs.jobs["job-1"].update(status="failed", error_message="Operation interrupted by a DerridAI restart.")

    assert research_threads.reconcile_active_turns(jobs) == 1
    settled = store.get_turn(turn["turn_id"], "alice")
    assert settled["status"] == "failed"
    assert settled["error"] == "Operation interrupted by a DerridAI restart."
    assert store.retry_turn(turn["turn_id"], "alice")["attempt"] == 2


def test_completed_job_completes_its_turn(store) -> None:
    jobs = Jobs()
    _, turn = _running_turn(store, jobs)
    jobs.jobs["job-1"].update(status="completed", response_cache={"record_id": "resp-9"})
    research_threads.reconcile_active_turns(jobs)
    done = store.get_turn(turn["turn_id"], "alice")
    assert done["status"] == "completed" and done["response_record_id"] == "resp-9"


def test_active_jobs_are_left_alone(store) -> None:
    jobs = Jobs()
    _, turn = _running_turn(store, jobs)
    assert research_threads.reconcile_active_turns(jobs, startup=True) == 0
    assert store.get_turn(turn["turn_id"], "alice")["status"] == "running"


def test_missing_job_and_unbound_turn_fail_only_at_startup(store) -> None:
    jobs = Jobs()
    _, lost = _running_turn(store, jobs)
    del jobs.jobs["job-1"]
    other = store.create_thread("bob")
    unbound, _ = store.append_turn(other["thread_id"], "bob", "Never started")

    # During normal operation a turn is bound before its job is registered.
    assert research_threads.reconcile_active_turns(jobs) == 0
    assert store.get_turn(lost["turn_id"], "alice")["status"] == "running"
    assert store.get_turn(unbound["turn_id"], "bob")["status"] == "queued"

    assert research_threads.reconcile_active_turns(jobs, startup=True) == 2
    lost_after = store.get_turn(lost["turn_id"], "alice")
    unbound_after = store.get_turn(unbound["turn_id"], "bob")
    assert lost_after["status"] == unbound_after["status"] == "failed"
    assert lost_after["error"] == research_threads.RUN_UNAVAILABLE_ERROR
    assert unbound_after["error"] == research_threads.NOT_STARTED_ERROR


def test_deleted_threads_are_not_reconciled(store) -> None:
    jobs = Jobs()
    thread, _ = _running_turn(store, jobs)
    store.delete_thread(thread["thread_id"], "alice")
    del jobs.jobs["job-1"]
    assert research_threads.reconcile_active_turns(jobs, startup=True) == 0


def test_reading_a_thread_settles_a_finished_run(store, monkeypatch) -> None:
    from app.routers import research_threads as routes

    jobs = Jobs()
    thread, turn = _running_turn(store, jobs)
    _running_turn(store, jobs, job_id="job-2", question="Elsewhere")
    jobs.jobs["job-1"]["status"] = "cancelled"
    jobs.jobs["job-2"]["status"] = "failed"
    monkeypatch.setattr(routes, "rag_jobs", jobs)
    monkeypatch.setattr(routes, "request_user", lambda _: SimpleNamespace(username="alice", role="researcher"))

    detail = routes.get_thread(thread["thread_id"], None)
    assert detail["turns"][0]["status"] == "cancelled"
    # Only the thread being read is reconciled.
    assert [t["status"] for t in store.active_turns()] == ["running"]
