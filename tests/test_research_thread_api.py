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

"""Research thread API/job linkage: every run is a turn, outcomes mirror onto turns.

Why: a thread is continuity, while each turn keeps its own auditable run. A lost,
duplicated, or cross-owner link would break that.
How: real SQLite thread store, a fake job manager standing in for ``RAGJobManager``.
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
from app.models import RAGRunRequest  # noqa: E402
from app.research_thread_store import (  # noqa: E402
    ResearchThreadStore,
    ThreadBusy,
    ThreadNotFound,
)
from app.route_policy import non_admin_route_allowed  # noqa: E402


class FakeJobs:
    """Binds like RAGJobManager.create: before the worker could possibly finish."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.created: list[dict] = []

    def create(self, body, *, owner=None, turn_id=None):
        if self.fail:
            raise RuntimeError("provider down")
        job_id = f"job-{len(self.created) + 1}"
        if turn_id:
            research_threads.bind_job(turn_id, owner or "", job_id)
        job = {"id": job_id, "owner": owner, "turn_id": turn_id, "status": "queued", "prompt": body.prompt}
        self.created.append(job)
        return job

    def get(self, job_id):
        return next(j for j in self.created if j["id"] == job_id)


@pytest.fixture()
def store(tmp_path, monkeypatch) -> ResearchThreadStore:
    s = ResearchThreadStore(tmp_path / "system.sqlite3")
    monkeypatch.setattr(research_threads, "thread_store", lambda: s)
    return s


def _body(prompt="What is différance?", **extra) -> RAGRunRequest:
    return RAGRunRequest(prompt=prompt, **extra)


def test_first_question_creates_thread_turn_and_links_job(store) -> None:
    jobs = FakeJobs()
    job = research_threads.start_run(jobs, _body(), owner="alice")
    turn = store.get_turn(job["turn_id"], "alice")
    assert job["thread_id"] == turn["thread_id"]
    assert turn["status"] == "running" and turn["job_id"] == job["id"] and turn["research_run_id"] == job["id"]
    assert store.get_thread(turn["thread_id"], "alice")["title"] == "What is différance?"


def test_completion_and_failure_mirror_onto_turn(store) -> None:
    jobs = FakeJobs()
    job = research_threads.start_run(jobs, _body(), owner="alice")
    research_threads.sync_turn_from_job(
        {**job, "status": "completed", "response_cache": {"record_id": "resp-1"}}
    )
    done = store.get_turn(job["turn_id"], "alice")
    assert done["status"] == "completed" and done["response_record_id"] == "resp-1"

    second = research_threads.start_run(jobs, _body("And Levinas?"), owner="alice", thread_id=job["thread_id"])
    assert second["thread_id"] == job["thread_id"]
    research_threads.sync_turn_from_job(
        {**second, "status": "failed", "error_message": "model unavailable"}
    )
    failed = store.get_turn(second["turn_id"], "alice")
    assert failed["status"] == "failed" and failed["error"] == "model unavailable"
    assert failed["ordinal"] == 2


def test_completion_without_cache_record_falls_back_to_run_id(store) -> None:
    job = research_threads.start_run(FakeJobs(), _body(), owner="alice")
    research_threads.sync_turn_from_job({**job, "status": "completed"})
    assert store.get_turn(job["turn_id"], "alice")["response_record_id"] == job["id"]


def test_idempotency_key_returns_same_job_without_a_second_run(store) -> None:
    jobs = FakeJobs()
    first = research_threads.start_run(jobs, _body(idempotency_key="k"), owner="alice")
    again = research_threads.start_run(
        jobs, _body(idempotency_key="k"), owner="alice", thread_id=first["thread_id"]
    )
    assert again["id"] == first["id"] and again["turn_id"] == first["turn_id"]
    assert len(jobs.created) == 1


def test_only_one_active_turn_per_thread(store) -> None:
    jobs = FakeJobs()
    first = research_threads.start_run(jobs, _body(), owner="alice")
    with pytest.raises(ThreadBusy):
        research_threads.start_run(jobs, _body("Next"), owner="alice", thread_id=first["thread_id"])


def test_other_users_cannot_append_to_or_read_a_thread(store) -> None:
    job = research_threads.start_run(FakeJobs(), _body(), owner="alice")
    with pytest.raises(ThreadNotFound):
        research_threads.start_run(FakeJobs(), _body("x"), owner="bob", thread_id=job["thread_id"])
    with pytest.raises(ThreadNotFound):
        store.get_thread(job["thread_id"], "bob")


def test_start_failure_marks_turn_failed_and_retry_reuses_it(store) -> None:
    with pytest.raises(RuntimeError):
        research_threads.start_run(FakeJobs(fail=True), _body(), owner="alice")
    thread = store.list_threads("alice")[0]
    detail = store.get_thread(thread["thread_id"], "alice")
    turn = detail["turns"][0]
    assert turn["status"] == "failed" and "provider down" in turn["error"]

    with pytest.raises(ValueError):
        research_threads.start_run(
            FakeJobs(), _body("different"), owner="alice", retry_turn_id=turn["turn_id"]
        )
    retried = research_threads.start_run(
        FakeJobs(), _body(), owner="alice", retry_turn_id=turn["turn_id"]
    )
    assert retried["turn_id"] == turn["turn_id"]
    after = store.get_thread(thread["thread_id"], "alice")
    assert len(after["turns"]) == 1 and after["turns"][0]["attempt"] == 2


def test_sync_ignores_deleted_threads_and_unlinked_jobs(store) -> None:
    job = research_threads.start_run(FakeJobs(), _body(), owner="alice")
    store.delete_thread(job["thread_id"], "alice")
    research_threads.sync_turn_from_job({**job, "status": "completed"})  # must not raise
    research_threads.sync_turn_from_job({"id": "j", "owner": "alice", "status": "completed"})


def test_thread_routes_are_gated_on_the_run_capability() -> None:
    allowed = {"researcher", "admin"}
    for role in ("researcher",):
        assert non_admin_route_allowed(role, "/api/research/threads", "GET") is (role in allowed)
        assert non_admin_route_allowed(role, "/api/research/threads/rt_1/turns", "POST")
        assert non_admin_route_allowed(role, "/api/research/threads/rt_1/turns/t/retry", "POST")
        assert non_admin_route_allowed(role, "/api/research/threads/rt_1", "DELETE")
        assert not non_admin_route_allowed(role, "/api/research/threads/rt_1/turns", "GET")
        assert not non_admin_route_allowed(role, "/api/research/threads/rt_1/other", "GET")


def test_job_manager_binds_turn_and_syncs_on_finish(store, monkeypatch) -> None:
    from app.job_rag import RAGJobManager

    manager = RAGJobManager(SimpleNamespace(), ollama_max_concurrent=1)
    monkeypatch.setattr(manager, "_run", lambda job_id, body: None)
    monkeypatch.setattr(manager, "_persist_job", lambda job_id: None)
    thread = store.create_thread("alice")
    turn, _ = store.append_turn(thread["thread_id"], "alice", "Q")
    job = manager.create(_body("Q", provider="ollama", model="m"), owner="alice", turn_id=turn["turn_id"])
    assert job["turn_id"] == turn["turn_id"]
    assert store.get_turn(turn["turn_id"], "alice")["job_id"] == job["id"]


@pytest.mark.parametrize("role", ["researcher", "custom_role"])
def test_rename_enforces_researcher_text_before_any_mutation(store, monkeypatch, role) -> None:
    from app.routers import research_threads as routes
    from fastapi import HTTPException

    thread = store.create_thread("alice", title="Original")
    monkeypatch.setattr(routes, "request_user", lambda _: SimpleNamespace(username="alice", role=role))
    seen = []

    def reject(value):
        seen.append(value)
        raise ValueError("text policy rejected title")

    monkeypatch.setattr(routes, "enforce_researcher_text", reject)
    with pytest.raises(HTTPException) as error:
        routes.patch_thread(thread["thread_id"], routes.ThreadPatch(title="Rejected", archived=True), None)
    assert error.value.status_code == 422
    assert seen == [{"title": "Rejected"}]
    unchanged = store.get_thread(thread["thread_id"], "alice")
    assert unchanged["title"] == "Original" and unchanged["archived_at"] is None


def test_thread_management_preserves_owner_boundary_and_sparse_patch(store, monkeypatch) -> None:
    from app.routers import research_threads as routes
    from fastapi import HTTPException

    thread = store.create_thread("alice", title="Original")
    monkeypatch.setattr(routes, "request_user", lambda _: SimpleNamespace(username="bob", role="admin"))
    with pytest.raises(HTTPException) as error:
        routes.patch_thread(thread["thread_id"], routes.ThreadPatch(title="Other owner"), None)
    assert error.value.status_code == 404
    monkeypatch.setattr(routes, "request_user", lambda _: SimpleNamespace(username="alice", role="researcher"))
    monkeypatch.setattr(routes, "enforce_researcher_text", lambda _: pytest.fail("No authored text in archive patch"))
    archived = routes.patch_thread(thread["thread_id"], routes.ThreadPatch(archived=True), None)
    assert archived["title"] == "Original" and archived["archived_at"] is not None
    monkeypatch.setattr(routes, "request_user", lambda _: SimpleNamespace(username="alice", role="admin"))
    renamed = routes.patch_thread(thread["thread_id"], routes.ThreadPatch(title="New title"), None)
    assert renamed["title"] == "New title" and renamed["archived_at"] is not None
    assert "turns" not in renamed



def test_context_snapshot_is_server_loaded_without_changing_current_prompt(store) -> None:
    jobs = FakeJobs()
    first = research_threads.start_run(jobs, _body("Derrida?"), owner="alice")
    jobs.created[0].update(status="completed", result={"answer": "Prior answer [[E99]]"})
    research_threads.sync_turn_from_job(jobs.created[0])
    second = research_threads.start_run(jobs, _body("What about him?"), owner="alice",
                                       thread_id=first["thread_id"])
    turn = store.get_turn(second["turn_id"], "alice")
    snapshot = turn["context_selection"]
    assert snapshot["selected_turn_ids"] == [first["turn_id"]]
    assert snapshot["items"][1]["text"] == "Prior answer [[E99]]"
    assert snapshot["advisory"] and not snapshot["evidentiary"]
    assert second["prompt"] == turn["user_question"] == "What about him?"
    assert "context" not in second and "result" not in second


def test_context_budget_failure_marks_new_turn_failed_without_starting_job(store) -> None:
    from app.research_context import ContextBudgetExceeded

    jobs = FakeJobs()
    first = research_threads.start_run(jobs, _body(), owner="alice")
    jobs.created[0].update(status="completed", result={"answer": "a" * 12001})
    research_threads.sync_turn_from_job(jobs.created[0])
    with pytest.raises(ContextBudgetExceeded):
        research_threads.start_run(jobs, _body("And Levinas?"), owner="alice",
                                   thread_id=first["thread_id"])
    turns = store.get_thread(first["thread_id"], "alice")["turns"]
    assert turns[-1]["status"] == "failed" and turns[-1]["job_id"] is None
    assert "context answer budget" in turns[-1]["error"]
    assert len(jobs.created) == 1
