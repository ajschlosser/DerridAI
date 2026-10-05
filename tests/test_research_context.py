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

"""Advisory turn history must be bounded, owner-scoped and separate from evidence."""

from __future__ import annotations

import pytest
from app.research_context import (
    ContextBudgetExceeded,
    ThreadContextPolicy,
    select_thread_context,
)
from app.research_thread_store import ResearchThreadStore, ThreadBusy, ThreadNotFound


@pytest.fixture()
def history(tmp_path):
    store = ResearchThreadStore(tmp_path / "system.sqlite3")
    thread_id = store.create_thread("alice")["thread_id"]
    jobs = {}
    turns = []
    for question, answer in (
        ("Derrida?", "Not a primary source [[E99]]"),
        ("Levinas?", "Prior generated interpretation"),
        ("Et la négation?", "Ne pas supprimer la négation."),
    ):
        turn, _ = store.append_turn(thread_id, "alice", question)
        job_id = "job-" + turn["turn_id"]
        store.bind_job(turn["turn_id"], "alice", job_id=job_id)
        jobs[job_id] = {
            "id": job_id,
            "owner": "alice",
            "turn_id": turn["turn_id"],
            "status": "completed",
            "result": {"answer": answer},
        }
        store.complete_turn(
            turn["turn_id"], "alice", research_run_id=job_id, response_record_id=job_id
        )
        turns.append(store.get_turn(turn["turn_id"], "alice"))
    current, _ = store.append_turn(thread_id, "alice", "What about him?")
    return store, jobs, turns, current


def test_chronology_previous_priority_and_advisory_snapshot(history):
    store, jobs, turns, current = history
    packet = select_thread_context(store, current["turn_id"], "alice", jobs.__getitem__)
    assert [(item.ordinal, item.role) for item in packet.items] == [
        (1, "user"),
        (1, "assistant"),
        (2, "user"),
        (2, "assistant"),
        (3, "user"),
        (3, "assistant"),
    ]
    assert [item.source for item in packet.items[-2:]] == ["immediate_previous"] * 2
    snapshot = packet.snapshot()
    assert snapshot["selected_turn_ids"] == [turn["turn_id"] for turn in turns]
    assert snapshot["advisory"] is True and snapshot["evidentiary"] is False
    assert snapshot["character_count"] == sum(len(item.text) for item in packet.items)
    assert "semantic_selection_unavailable_using_recent_turns" in packet.warnings
    assert "[[E99]]" in packet.items[1].text
    assert "evidence_refs" not in snapshot and "support_bindings" not in snapshot
    assert (
        store.get_turn(current["turn_id"], "alice")["user_question"]
        == "What about him?"
    )


def test_bounded_recent_selection_retains_exact_previous_turn(history):
    store, jobs, turns, current = history
    policy = ThreadContextPolicy(max_turns=1)
    packet = select_thread_context(
        store, current["turn_id"], "alice", jobs.__getitem__, policy=policy
    )
    assert [item.turn_id for item in packet.items] == [turns[-1]["turn_id"]] * 2
    assert packet.items[-1].text == "Ne pas supprimer la négation."
    assert not packet.warnings


@pytest.mark.parametrize(
    "policy",
    [
        ThreadContextPolicy(max_characters=2),
        ThreadContextPolicy(max_answer_characters=2),
    ],
)
def test_previous_turn_never_silently_truncated(history, policy):
    store, jobs, _, current = history
    with pytest.raises(ContextBudgetExceeded):
        select_thread_context(
            store, current["turn_id"], "alice", jobs.__getitem__, policy=policy
        )


def test_older_turns_skip_when_budget_full(history):
    store, jobs, turns, current = history
    size = len(turns[-1]["user_question"]) + len(
        jobs[turns[-1]["job_id"]]["result"]["answer"]
    )
    packet = select_thread_context(
        store,
        current["turn_id"],
        "alice",
        jobs.__getitem__,
        policy=ThreadContextPolicy(max_characters=size),
    )
    assert packet.snapshot()["character_count"] == size
    assert packet.snapshot()["selected_turn_ids"] == [turns[-1]["turn_id"]]
    assert any(
        warning.startswith("older_turn_exceeds_context_budget:")
        for warning in packet.warnings
    )


@pytest.mark.parametrize("change", ["missing", "owner", "turn_id", "status"])
def test_missing_or_unrelated_answers_never_enter_packet(history, change):
    store, jobs, turns, current = history
    job = jobs[turns[-1]["job_id"]]
    if change == "missing":
        del jobs[job["id"]]
    else:
        job[change] = "unrelated"
    packet = select_thread_context(store, current["turn_id"], "alice", jobs.__getitem__)
    assert packet.items[-1].role == "user"
    assert f"prior_answer_unavailable:{turns[-1]['turn_id']}" in packet.warnings


def test_owner_and_thread_isolation_and_failed_turn_exclusion(history):
    store, jobs, _, current = history
    with pytest.raises(ThreadNotFound):
        select_thread_context(store, current["turn_id"], "bob", jobs.__getitem__)
    other = store.create_thread("alice")["thread_id"]
    failed, _ = store.append_turn(other, "alice", "Failed unrelated question")
    store.end_turn(failed["turn_id"], "alice", status="failed")
    first, _ = store.append_turn(other, "alice", "First completed inquiry")
    calls = []
    packet = select_thread_context(
        store, first["turn_id"], "alice", lambda key: calls.append(key)
    )
    assert not packet.items and not calls and not packet.warnings


def test_question_only_policy_never_reads_assistant(history):
    store, _, _, current = history

    def forbidden(_):
        raise AssertionError("No answer reads allowed")

    packet = select_thread_context(
        store,
        current["turn_id"],
        "alice",
        forbidden,
        policy=ThreadContextPolicy(include_answers=False),
    )
    assert all(item.role == "user" for item in packet.items)


def test_reader_failure_is_visible(history):
    store, _, _, current = history

    def broken(_):
        raise RuntimeError("storage unavailable")

    with pytest.raises(RuntimeError, match="storage unavailable"):
        select_thread_context(store, current["turn_id"], "alice", broken)


def test_snapshot_is_immutable_per_attempt_and_survives_restart(history):
    store, jobs, _, current = history
    packet = select_thread_context(store, current["turn_id"], "alice", jobs.__getitem__)
    saved = store.save_context_selection(current["turn_id"], "alice", packet.snapshot())
    assert saved["context_selection"]["attempt"] == 1
    again = store.save_context_selection(current["turn_id"], "alice", {"items": []})
    assert again["context_selection"] == saved["context_selection"]
    store.bind_job(current["turn_id"], "alice", job_id="new-job")
    with pytest.raises(ThreadBusy):
        store.save_context_selection(current["turn_id"], "alice", {})
    store.end_turn(current["turn_id"], "alice", status="failed")
    store.retry_turn(current["turn_id"], "alice")
    retried = store.save_context_selection(
        current["turn_id"], "alice", packet.snapshot()
    )
    assert retried["context_selection"]["attempt"] == 2
    reopened = ResearchThreadStore(store.path)
    assert (
        reopened.get_turn(current["turn_id"], "alice")["context_selection"]
        == retried["context_selection"]
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_turns": 0},
        {"max_characters": 128001},
        {"max_answer_characters": True},
        {"include_answers": 1},
    ],
)
def test_invalid_policy_rejected(kwargs):
    with pytest.raises(ValueError):
        ThreadContextPolicy(**kwargs)
