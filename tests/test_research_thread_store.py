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

import pytest
from app.research_thread_store import (
    ResearchThreadStore,
    ThreadBusy,
    ThreadNotFound,
    derive_title,
)


@pytest.fixture()
def store(tmp_path) -> ResearchThreadStore:
    return ResearchThreadStore(tmp_path / "system.sqlite3")


def _thread(store: ResearchThreadStore, owner: str = "alice") -> str:
    return store.create_thread(owner)["thread_id"]


def _finish(store: ResearchThreadStore, turn: dict, owner: str = "alice") -> None:
    store.bind_job(turn["turn_id"], owner, job_id="job-" + turn["turn_id"])
    store.complete_turn(turn["turn_id"], owner, research_run_id="run", response_record_id="resp")


def test_turns_are_ordered_and_parented_and_title_is_deterministic(store) -> None:
    tid = _thread(store)
    first, created = store.append_turn(tid, "alice", "What is différance in Of Grammatology?")
    assert created and first["ordinal"] == 1 and first["parent_turn_id"] is None
    _finish(store, first)
    second, _ = store.append_turn(tid, "alice", "What about Levinas?")
    assert second["ordinal"] == 2 and second["parent_turn_id"] == first["turn_id"]
    detail = store.get_thread(tid, "alice")
    assert detail["title"] == "What is différance in Of Grammatology?"
    assert [t["user_question"] for t in detail["turns"]][1] == "What about Levinas?"
    assert derive_title("word " * 40).endswith("…") and len(derive_title("word " * 40)) <= 81


def test_idempotency_key_returns_original_turn(store) -> None:
    tid = _thread(store)
    a, created_a = store.append_turn(tid, "alice", "Q", idempotency_key="k1")
    b, created_b = store.append_turn(tid, "alice", "Q", idempotency_key="k1")
    assert created_a and not created_b and a["turn_id"] == b["turn_id"]
    assert len(store.get_thread(tid, "alice")["turns"]) == 1


def test_one_active_turn_per_thread_and_retry_keeps_visible_turn(store) -> None:
    tid = _thread(store)
    turn, _ = store.append_turn(tid, "alice", "Q1")
    with pytest.raises(ThreadBusy):
        store.append_turn(tid, "alice", "Q2")
    store.bind_job(turn["turn_id"], "alice", job_id="j1")
    failed = store.end_turn(turn["turn_id"], "alice", status="failed", error="boom")
    assert failed["status"] == "failed" and failed["user_question"] == "Q1"
    retried = store.retry_turn(turn["turn_id"], "alice")
    assert retried["turn_id"] == turn["turn_id"] and retried["attempt"] == 2
    assert retried["status"] == "queued" and retried["job_id"] is None
    assert len(store.get_thread(tid, "alice")["turns"]) == 1
    with pytest.raises(ThreadBusy):
        store.retry_turn(turn["turn_id"], "alice")


def test_other_threads_stay_usable_while_one_is_active(store) -> None:
    a, b = _thread(store), _thread(store)
    store.append_turn(a, "alice", "Q")
    store.append_turn(b, "alice", "Q")


def test_owner_isolation(store) -> None:
    tid = _thread(store)
    turn, _ = store.append_turn(tid, "alice", "secret question")
    for call in (
        lambda: store.get_thread(tid, "bob"),
        lambda: store.append_turn(tid, "bob", "x"),
        lambda: store.get_turn(turn["turn_id"], "bob"),
        lambda: store.rename_thread(tid, "bob", "x"),
        lambda: store.delete_thread(tid, "bob"),
        lambda: store.bind_job(turn["turn_id"], "bob", job_id="j"),
    ):
        with pytest.raises(ThreadNotFound):
            call()
    assert store.list_threads("bob") == []
    assert store.list_threads("bob", search="secret") == []


def test_list_is_bounded_summary_with_search_and_archive(store) -> None:
    tid = _thread(store)
    t1, _ = store.append_turn(tid, "alice", "Trace and archive")
    _finish(store, t1)
    t2, _ = store.append_turn(tid, "alice", "What about Levinas?")
    items = store.list_threads("alice")
    assert items[0]["turn_count"] == 2
    assert items[0]["first_question"] == "Trace and archive"
    assert items[0]["last_question"] == "What about Levinas?"
    assert items[0]["last_status"] == "queued" and t2
    assert store.list_threads("alice", search="levinas")
    assert store.list_threads("alice", search="%") == []
    store.set_archived(tid, "alice", True)
    assert store.list_threads("alice") == []
    assert len(store.list_threads("alice", include_archived=True)) == 1


def test_delete_tombstones_thread_and_drops_turns(store) -> None:
    tid = _thread(store)
    turn, _ = store.append_turn(tid, "alice", "Q")
    store.delete_thread(tid, "alice")
    with pytest.raises(ThreadNotFound):
        store.get_thread(tid, "alice")
    assert store.turn_for_job("anything") is None
    assert store.list_threads("alice") == []
    with pytest.raises(ThreadNotFound):
        store.get_turn(turn["turn_id"], "alice")


def test_cancel_preserves_sequence_and_completed_turn_cannot_be_failed(store) -> None:
    tid = _thread(store)
    turn, _ = store.append_turn(tid, "alice", "Q")
    store.end_turn(turn["turn_id"], "alice", status="cancelled")
    nxt, _ = store.append_turn(tid, "alice", "Q2")
    assert nxt["ordinal"] == 2
    _finish(store, nxt)
    with pytest.raises(ThreadBusy):
        store.end_turn(nxt["turn_id"], "alice", status="failed")


def test_job_linkage_and_completion(store) -> None:
    tid = _thread(store)
    turn, _ = store.append_turn(tid, "alice", "Q")
    bound = store.bind_job(
        turn["turn_id"],
        "alice",
        job_id="j1",
        research_run_id="run1",
        contextualized_query="standalone",
        context_selection={"turn_ids": [], "strategy": "none"},
    )
    assert bound["status"] == "running" and bound["context_selection"]["strategy"] == "none"
    assert store.turn_for_job("j1")["turn_id"] == turn["turn_id"]
    done = store.complete_turn(
        turn["turn_id"], "alice", research_run_id="run1", response_record_id="resp1"
    )
    assert done["status"] == "completed" and done["response_record_id"] == "resp1"
    assert done["user_question"] == "Q" and done["contextualized_query"] == "standalone"


def test_legacy_materialization_is_idempotent_and_survives_delete(store) -> None:
    legacy = [
        {"record_id": "r1", "question": "Old question", "created_at": "2026-01-01T00:00:00+00:00"},
        {"record_id": "r2", "question": "Another", "run_id": "run2"},
        {"record_id": "", "question": "ignored"},
    ]
    assert len(store.materialize_legacy("alice", legacy)) == 2
    assert store.materialize_legacy("alice", legacy) == []
    threads = store.list_threads("alice")
    assert {t["originating_response_record_id"] for t in threads} == {"r1", "r2"}
    assert all(t["turn_count"] == 1 and t["last_status"] == "completed" for t in threads)
    victim = next(t for t in threads if t["originating_response_record_id"] == "r1")
    store.delete_thread(victim["thread_id"], "alice")
    assert store.materialize_legacy("alice", legacy) == []  # not resurrected
    assert store.materialize_legacy("bob", legacy[:1])  # per-owner


def test_store_reopen_keeps_state(tmp_path) -> None:
    path = tmp_path / "system.sqlite3"
    first = ResearchThreadStore(path)
    tid = first.create_thread("alice")["thread_id"]
    first.append_turn(tid, "alice", "Q")
    again = ResearchThreadStore(path)  # idempotent schema init
    assert again.get_thread(tid, "alice")["turns"][0]["user_question"] == "Q"


def test_pinned_threads_list_first_without_changing_activity_order_or_other_owners(store) -> None:
    older = _thread(store)
    newer = _thread(store)
    bob = _thread(store, "bob")
    assert [t["thread_id"] for t in store.list_threads("alice")] == [newer, older]
    before = store.get_thread(older, "alice")["updated_at"]
    pinned = store.set_pinned(older, "alice", True)
    assert pinned["pinned_at"] and pinned["updated_at"] == before
    assert [t["thread_id"] for t in store.list_threads("alice")] == [older, newer]
    with pytest.raises(ThreadNotFound):
        store.set_pinned(bob, "alice", True)
    assert store.set_pinned(older, "alice", False)["pinned_at"] is None
    assert [t["thread_id"] for t in store.list_threads("alice")] == [newer, older]


def test_list_orders_by_last_question_asked_not_run_progress_or_rename(store) -> None:
    first = _thread(store)
    second = _thread(store)
    first_turn, _ = store.append_turn(first, "alice", "What is the trace?")
    store.append_turn(second, "alice", "What is the supplement?")
    assert [t["thread_id"] for t in store.list_threads("alice")] == [second, first]

    # Finishing the earlier question's run and renaming its thread are not new questions.
    _finish(store, first_turn)
    store.rename_thread(first, "alice", "Renamed")
    assert [t["thread_id"] for t in store.list_threads("alice")] == [second, first]

    store.append_turn(first, "alice", "And différance?")
    listed = store.list_threads("alice")
    assert [t["thread_id"] for t in listed] == [first, second]
    assert listed[0]["last_asked_at"] > listed[1]["last_asked_at"]


def test_thread_without_questions_sorts_by_its_creation_time(store, monkeypatch) -> None:
    # The contract compares distinct event times, independent of host clock resolution.
    stamps = iter([
        "2026-10-17T10:00:00+00:00", "2026-10-17T10:00:01+00:00", "2026-10-17T10:00:02+00:00",
    ])
    monkeypatch.setattr("app.research_thread_store._iso_now", lambda: next(stamps))
    asked = _thread(store)
    store.append_turn(asked, "alice", "What is the trace?")
    empty = _thread(store)
    listed = store.list_threads("alice")
    assert [t["thread_id"] for t in listed] == [empty, asked]
    assert listed[0]["last_asked_at"] == listed[0]["created_at"]


def test_pinned_column_is_added_to_an_existing_thread_table(tmp_path) -> None:
    import sqlite3
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE research_threads (thread_id TEXT PRIMARY KEY, owner TEXT NOT NULL,"
            " title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,"
            " archived_at TEXT, deleted_at TEXT, originating_response_record_id TEXT)"
        )
        conn.execute("INSERT INTO research_threads VALUES ('rt_old','alice','Old','t','t',NULL,NULL,NULL)")
    store = ResearchThreadStore(path)
    assert store.get_thread("rt_old", "alice")["pinned_at"] is None
    assert store.set_pinned("rt_old", "alice", True)["pinned_at"]
