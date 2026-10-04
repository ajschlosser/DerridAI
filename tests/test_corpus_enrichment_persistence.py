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

"""Enrichment completion durability, human ownership, and persistence scaling.

The optional benchmark uses real repository I/O and a deterministic fake provider.
Set CORPUS_PERSISTENCE_BENCHMARK to an output JSONL path to run it. It measures
the scheduler, not extraction, model latency, browser interaction, or human review.
"""
from __future__ import annotations

import copy
import json
import os
import platform
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from app.field_assertions import (
    create_human_assertion,
    create_model_assertion,
    current_assertion_by_name,
    project_record_assertions,
)
from test_human_metadata_ownership import cb, install


def _completed(record):
    result = copy.deepcopy(record)
    create_model_assertion(result, "speaker", "Model speaker", method="test")
    project_record_assertions(result)
    result["metadata_complete"] = True
    result["metadata_enrichment_finished"] = True
    result["metadata_stage_status"] = {key: "complete" for key in ("discourse", "quotation", "indexing")}
    return result


@pytest.fixture
def build_factory(tmp_path, monkeypatch):
    managers = []

    def make(count=3, pending=None):
        records = []
        for index in range(count):
            already_enriched = pending is not None and index >= pending
            record = {
                "text": f"Source {index}: " + "documentary evidence " * 100,
                "metadata_complete": already_enriched,
            }
            if already_enriched:
                record["metadata_enrichment_state"] = "complete"
                record["metadata_stage_status"] = {
                    "discourse": "complete",
                    "quotation": "complete",
                    "indexing": "complete",
                }
            records.append(record)
        repo, build = install(tmp_path, records)
        monkeypatch.setattr(cb.PdfCorpusBuildManager, "_schedule_metadata_exemplar_projection", lambda *args: None)
        manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
        managers.append(manager)
        monkeypatch.setattr(manager, "_allowed_fields", lambda _build: {"speaker"})
        monkeypatch.setattr(manager, "_enrich_record", lambda record, *_args, **_kwargs: _completed(record))
        return repo, build["build_id"], manager

    yield make
    for manager in managers:
        manager._executor.shutdown(wait=True)


@pytest.mark.parametrize("handoff", ["checkpoint", "completion"])
@pytest.mark.parametrize("changed_key", ["text", "record_revision", "source_document_id", "source_spans"])
def test_initial_handoff_discards_changed_documentary_context(
    build_factory, monkeypatch, caplog, handoff, changed_key,
):
    repo, build_id, manager = build_factory(count=1)
    baseline = repo.load_records(build_id)
    retained = {}
    notifications = []

    def change_context():
        live = repo.get_record(build_id, "r1")
        if changed_key == "record_revision":
            live[changed_key] += 1
        elif changed_key == "source_spans":
            live[changed_key] = [{"block_id": "replacement-source", "page": 2}]
        else:
            live[changed_key] = "Changed documentary context"
        live["metadata_enrichment_state"] = "queued"
        live["metadata_complete"] = False
        repo.update_record(build_id, live)
        retained.update(repo.get_record(build_id, "r1"))

    if handoff == "checkpoint":
        change_context()
        before_build = repo.get_build(build_id)
        manager._persist_build_metadata_stage(
            build_id, 3, _completed(baseline[0]), "discourse", "complete", None,
        )
        assert repo.get_build(build_id) == before_build
    else:
        def enrich(record, *_args, **_kwargs):
            change_context()
            return _completed(record)

        monkeypatch.setattr(manager, "_enrich_record", enrich)
        monkeypatch.setattr(cb, "note_record_metadata", lambda *args: notifications.append(args))
        result = manager._schedule_build_enrichment(build_id, {}, {}, baseline)
        assert result == [retained]
        assert not repo.get_build(build_id).get("metadata_first_settled_at")
        assert not notifications
    assert repo.get_record(build_id, "r1") == retained
    assert not repo.get_record(build_id, "r1").get("speaker")
    assert f"Discarded stale initial metadata {handoff}" in caplog.text


@pytest.mark.parametrize("handoff", ["checkpoint", "completion"])
def test_initial_handoff_serializes_external_same_record_writer(build_factory, monkeypatch, handoff):
    repo, build_id, manager = build_factory(count=1)
    baseline = repo.load_records(build_id)
    external = cb.PdfCorpusRepository(repo.root)
    entered = threading.Event()
    writer_started = threading.Event()
    writer_committed = threading.Event()
    release = threading.Event()
    merge = cb._merge_enrichment_snapshot

    def paused_merge(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return merge(*args, **kwargs)

    def handoff_record():
        if handoff == "checkpoint":
            manager._persist_build_metadata_stage(
                build_id, 3, _completed(baseline[0]), "discourse", "complete", None,
            )
        else:
            manager._schedule_build_enrichment(build_id, {}, {}, baseline)

    def edit():
        assert entered.wait(10)
        writer_started.set()
        external.reconcile_records(
            build_id, lambda rows: rows[0].update(review_reason="External review decision"),
            record_ids=["r1"],
        )
        writer_committed.set()

    monkeypatch.setattr(cb, "_merge_enrichment_snapshot", paused_merge)
    with ThreadPoolExecutor(max_workers=2) as pool:
        automatic = pool.submit(handoff_record)
        writer = pool.submit(edit)
        try:
            assert writer_started.wait(10)
            assert not writer_committed.wait(0.2), "Writer interleaved with the initial Record merge"
        finally:
            release.set()
        automatic.result(timeout=10)
        writer.result(timeout=10)
    stored = cb.PdfCorpusRepository(repo.root).get_record(build_id, "r1")
    assert stored["review_reason"] == "External review decision"
    assert stored["speaker"] == "Model speaker"
    assert stored["metadata_stage_status"]["discourse"] == "complete"


@pytest.mark.parametrize("handoff", ["checkpoint", "completion"])
def test_initial_handoff_rolls_back_record_and_summary_on_projection_failure(
    build_factory, monkeypatch, handoff,
):
    repo, build_id, manager = build_factory(count=1)
    baseline = repo.load_records(build_id)
    before = []
    notifications = []

    def fail_projection(*args, **kwargs):
        before.append(repo.get_build(build_id))
        raise RuntimeError("Queue projection failed")

    monkeypatch.setattr(cb.corpus_queue_projection, "update_rows", fail_projection)
    monkeypatch.setattr(cb, "note_record_metadata", lambda *args: notifications.append(args))
    with pytest.raises(RuntimeError, match="Queue projection failed"):
        if handoff == "checkpoint":
            manager._persist_build_metadata_stage(
                build_id, 3, _completed(baseline[0]), "discourse", "complete", None,
            )
        else:
            manager._schedule_build_enrichment(build_id, {}, {}, baseline)
    assert before
    assert repo.get_build(build_id) == before[-1]
    assert repo.get_record(build_id, "r1") == baseline[0]
    assert not notifications
    assert not repo.get_build(build_id).get("metadata_first_settled_at")


def test_initial_family_checkpoint_noop_does_not_write_or_notify(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=1)
    snapshot = _completed(repo.get_record(build_id, "r1"))
    manager._persist_build_metadata_stage(build_id, 3, snapshot, "discourse", "complete", None)
    updates = []
    notifications = []
    update_rows = cb.corpus_queue_projection.update_rows

    def counted(connection, rows, **kwargs):
        updates.extend(row["record_id"] for _ordinal, row in rows)
        return update_rows(connection, rows, **kwargs)

    monkeypatch.setattr(cb.corpus_queue_projection, "update_rows", counted)
    monkeypatch.setattr(repo, "_metadata_projection_callback", lambda *args: notifications.append(args))
    manager._persist_build_metadata_stage(build_id, 3, snapshot, "discourse", "complete", None)
    assert not updates
    assert not notifications


@pytest.mark.parametrize("count", [1, 1000, 10000])
def test_initial_family_checkpoint_decodes_and_writes_only_its_record(build_factory, monkeypatch, count):
    repo, build_id, manager = build_factory(count=count)
    snapshot = _completed(repo.get_record(build_id, "r1"))
    decoded = []
    written = []
    decode = repo._decode_migrated
    write = repo._write_reconciled_rows

    def counted_decode(payload, schema, signature):
        decoded.append(json.loads(payload)["record_id"])
        return decode(payload, schema, signature)

    def counted_write(connection, bid, rows):
        written.extend(row["record_id"] for _ordinal, row, _payload in rows)
        return write(connection, bid, rows)

    monkeypatch.setattr(repo, "_decode_migrated", counted_decode)
    monkeypatch.setattr(repo, "_write_reconciled_rows", counted_write)
    monkeypatch.setattr(repo, "load_records", lambda *args: pytest.fail("Checkpoint scanned the corpus"))
    monkeypatch.setattr(repo, "update_record", lambda *args: pytest.fail("Checkpoint used a separate row write"))
    manager._persist_build_metadata_stage(build_id, count * 3, snapshot, "discourse", "complete", None)
    assert decoded == written == ["r1"]


def test_initial_completion_requeues_after_actual_review_command(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=1)
    processed = []

    def enrich(record, *_args, **_kwargs):
        processed.append(record["record_revision"])
        if len(processed) == 1:
            manager.patch_metadata(
                build_id,
                "r1",
                {"speaker": "Reviewer speaker"},
                expected_revision=1,
            )
        return _completed(record)

    monkeypatch.setattr(manager, "_enrich_record", enrich)
    result = manager._schedule_build_enrichment(build_id, {}, {}, repo.load_records(build_id))

    assert processed == [1, 2]
    assert result[0]["record_revision"] == 2
    assert result[0]["speaker"] == "Reviewer speaker"
    assert current_assertion_by_name(result[0], "speaker").authority_status == "human_confirmed"
    assert result[0]["metadata_complete"]
    assert not result[0].get("metadata_requeue_requested")
    assert repo.get_build(build_id).get("metadata_first_settled_at")


def test_initial_completion_retries_requeued_current_documentary_context(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=1)
    processed = []

    def enrich(record, *_args, **_kwargs):
        processed.append(record["record_revision"])
        if len(processed) == 1:
            live = repo.get_record(build_id, "r1")
            live["text"] = "Current documentary text"
            live["record_revision"] = 2
            live["metadata_requeue_requested"] = True
            repo.update_record(build_id, live)
        return _completed(record)

    monkeypatch.setattr(manager, "_enrich_record", enrich)
    result = manager._schedule_build_enrichment(build_id, {}, {}, repo.load_records(build_id))
    assert processed == [1, 2]
    assert result[0]["text"] == "Current documentary text"
    assert result[0]["record_revision"] == 2
    assert result[0]["metadata_complete"]
    assert not result[0].get("metadata_requeue_requested")
    assert repo.get_build(build_id).get("metadata_first_settled_at")


def test_retired_initial_checkpoint_does_not_write_or_advance_counters(build_factory):
    repo, build_id, manager = build_factory(count=1)
    snapshot = _completed(repo.get_record(build_id, "r1"))
    replacement = copy.deepcopy(snapshot)
    replacement["record_id"] = "replacement"
    repo.save_records(build_id, [replacement])
    before = repo.get_build(build_id)
    manager._persist_build_metadata_stage(build_id, 3, snapshot, "discourse", "complete", None)
    assert repo.get_build(build_id) == before
    assert [row["record_id"] for row in repo.load_records(build_id)] == ["replacement"]


@pytest.mark.parametrize("count", [1, 50])
def test_queue_setup_batches_dirty_projection_state_instead_of_per_record_writes(
    build_factory, monkeypatch, count,
):
    repo, build_id, manager = build_factory(count=count)
    records = repo.load_records(build_id)
    for record in records:
        record["metadata_enrichment_state"] = "running"
    repo.save_records(build_id, records)
    dirty_updates = []
    direct_updates = []
    mark_dirty, update = repo._set_records_projection_state, repo.update_record

    def counted_dirty(bid, **kwargs):
        if kwargs.get("dirty"):
            dirty_updates.append(bid)
        return mark_dirty(bid, **kwargs)

    def counted_update(*args, **kwargs):
        direct_updates.append(args[1]["record_id"])
        return update(*args, **kwargs)

    monkeypatch.setattr(repo, "_set_records_projection_state", counted_dirty)
    monkeypatch.setattr(repo, "update_record", counted_update)
    result = manager._initialize_build_enrichment(build_id, {})
    assert all(row["metadata_enrichment_state"] == "queued" for row in result)
    assert dirty_updates == [build_id]
    assert not direct_updates


def test_queue_setup_preserves_family_checkpoints_and_skips_unchanged_rows(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=2)
    baseline = repo.load_records(build_id)
    baseline[0]["metadata_enrichment_state"] = "running"
    baseline[0]["metadata_stage_status"]["discourse"] = "complete"
    baseline[0]["metadata_execution_ledger"] = {"discourse": {"state": "complete", "model": "test"}}
    create_human_assertion(baseline[0], "speaker", "Human speaker", method="human")
    project_record_assertions(baseline[0])
    repo.save_records(build_id, baseline)
    writes = []
    write = repo._write_reconciled_rows

    def counted(connection, bid, rows):
        writes.extend(row["record_id"] for _ordinal, row, _payload in rows)
        return write(connection, bid, rows)

    monkeypatch.setattr(repo, "_write_reconciled_rows", counted)
    result = manager._initialize_build_enrichment(build_id, {})
    assert writes == ["r1"]
    assert result[0]["metadata_enrichment_state"] == "queued"
    assert result[0]["metadata_stage_status"]["discourse"] == "complete"
    assert result[0]["metadata_execution_ledger"] == baseline[0]["metadata_execution_ledger"]
    assert current_assertion_by_name(result[0], "speaker").authority_status == "human_confirmed"
    assert result[1] == baseline[1]
    summary = repo.get_build(build_id)
    assert summary["metadata_tasks_completed"] == 1
    assert summary["metadata_tasks_queued"] == 5
    assert summary["metadata_enriched_count"] == 0
    assert summary["metadata_started_at"]
    writes.clear()
    manager._initialize_build_enrichment(build_id, {})
    assert not writes


@pytest.mark.parametrize("edit", ["text", "metadata", "retirement"])
def test_queue_setup_releases_review_locks_and_recomputes_current_snapshot(
    build_factory, monkeypatch, edit,
):
    repo, build_id, manager = build_factory(count=2, pending=0)
    entered, edited, release = threading.Event(), threading.Event(), threading.Event()
    family_states = cb._metadata_family_states
    attempts = []

    def paused(rows):
        attempts.append([row["record_id"] for row in rows])
        if len(attempts) == 1:
            entered.set()
            assert release.wait(10)
        return family_states(rows)

    def review():
        assert entered.wait(10)
        if edit == "text":
            manager.patch_record_text(build_id, "r1", "Reviewer corrected text", expected_revision=1)
        elif edit == "metadata":
            manager.patch_metadata(build_id, "r1", {"speaker": "Reviewer speaker"}, expected_revision=1)
        else:
            external = cb.PdfCorpusRepository(repo.root)
            external.save_records(build_id, [external.get_record(build_id, "r2")])
        edited.set()

    monkeypatch.setattr(cb, "_metadata_family_states", paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        initialization = pool.submit(manager._initialize_build_enrichment, build_id, {})
        reviewer = pool.submit(review)
        try:
            assert edited.wait(10), "Queue computation prevented concurrent review"
            assert not initialization.done()
        finally:
            release.set()
        reviewer.result(timeout=10)
        result = initialization.result(timeout=10)
    assert len(attempts) == 2
    assert result == repo.load_records(build_id)
    if edit == "text":
        assert result[0]["text"] == "Reviewer corrected text"
        assert result[0]["record_revision"] == 2
    elif edit == "metadata":
        assert result[0]["speaker"] == "Reviewer speaker"
        assert current_assertion_by_name(result[0], "speaker").authority_status == "human_confirmed"
    else:
        assert [row["record_id"] for row in result] == ["r2"]
        assert repo.get_build(build_id)["metadata_enrichment_total"] == 1


@pytest.mark.parametrize("action", ["cancel", "pause"])
def test_queue_setup_respects_cancellation_before_commit(build_factory, monkeypatch, action):
    repo, build_id, manager = build_factory(count=1, pending=0)
    manager._update(build_id, status="running", stage="enriching")
    before = repo.load_records(build_id)
    family_states = cb._metadata_family_states

    def stopped(rows):
        getattr(manager, action)(build_id)
        return family_states(rows)

    monkeypatch.setattr(cb, "_metadata_family_states", stopped)
    with pytest.raises(InterruptedError, match="cancelled"):
        manager._initialize_build_enrichment(build_id, {})
    assert repo.load_records(build_id) == before
    assert repo.get_build(build_id)["cancel_requested"]
    assert not repo.get_build(build_id).get("metadata_started_at")


def test_queue_setup_preserves_settle_request_received_during_computation(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=1, pending=0)
    manager._update(build_id, status="running", stage="enriching")
    family_states = cb._metadata_family_states

    def settle(rows):
        manager.settle_metadata_unresolved(build_id)
        return family_states(rows)

    monkeypatch.setattr(cb, "_metadata_family_states", settle)
    manager._initialize_build_enrichment(build_id, {})
    assert repo.get_build(build_id)["metadata_settle_requested"]


def test_queue_setup_repeated_conflicts_fail_without_committing_candidates(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=1)
    external = cb.PdfCorpusRepository(repo.root)
    before = repo.get_build(build_id)
    family_states = cb._metadata_family_states
    attempts = []
    writes = []

    def conflicting(rows):
        attempts.append(len(attempts) + 1)
        external.reconcile_records(
            build_id, lambda current: current[0].update(review_reason=f"Review {attempts[-1]}"),
            record_ids=["r1"],
        )
        return family_states(rows)

    monkeypatch.setattr(cb, "_metadata_family_states", conflicting)
    monkeypatch.setattr(repo, "_write_reconciled_rows", lambda *args: writes.append(args))
    with pytest.raises(cb.RecordStateConflict, match="enrichment queue setup"):
        manager._initialize_build_enrichment(build_id, {})
    assert attempts == [1, 2, 3]
    assert not writes
    assert {key: value for key, value in repo.get_build(build_id).items() if key != "records_projection"} == {
        key: value for key, value in before.items() if key != "records_projection"
    }
    record = repo.get_record(build_id, "r1")
    assert record["review_reason"] == "Review 3"
    assert record["metadata_enrichment_state"] == "queued"


def test_queue_setup_projection_failure_rolls_back_the_entire_batch(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=2)
    records = repo.load_records(build_id)
    for record in records:
        record["metadata_enrichment_state"] = "running"
    repo.save_records(build_id, records)
    before = repo.get_records(build_id, ["r1", "r2"], include_queue_version=True)
    before_build = repo.get_build(build_id)
    notifications = []
    update_rows = cb.corpus_queue_projection.update_rows

    def fail_projection(connection, rows, **kwargs):
        if not rows:
            return update_rows(connection, rows, **kwargs)
        assert [row["record_id"] for _ordinal, row in rows] == ["r1", "r2"]
        raise RuntimeError("Queue projection failed")

    monkeypatch.setattr(cb.corpus_queue_projection, "update_rows", fail_projection)
    monkeypatch.setattr(repo, "_metadata_projection_callback", lambda *args: notifications.append(args))
    with pytest.raises(RuntimeError, match="Queue projection failed"):
        manager._initialize_build_enrichment(build_id, {})
    assert repo.get_records(build_id, ["r1", "r2"], include_queue_version=True) == before
    assert {key: value for key, value in repo.get_build(build_id).items() if key != "records_projection"} == {
        key: value for key, value in before_build.items() if key != "records_projection"
    }
    assert not notifications


def test_queue_setup_schedules_current_topology_instead_of_obsolete_input(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=1)
    obsolete = repo.load_records(build_id)
    replacement = copy.deepcopy(obsolete[0])
    replacement["record_id"] = "replacement"
    repo.save_records(build_id, [replacement])
    processed = []

    def enrich(record, *_args, **_kwargs):
        processed.append(record["record_id"])
        return _completed(record)

    monkeypatch.setattr(manager, "_enrich_record", enrich)
    result = manager._schedule_build_enrichment(build_id, {}, {}, obsolete)
    assert processed == ["replacement"]
    assert [row["record_id"] for row in result] == ["replacement"]
    assert result[0]["metadata_complete"]
    assert repo.get_build(build_id)["metadata_enrichment_total"] == 1
    with pytest.raises(KeyError):
        repo.get_record(build_id, "r1")


def test_queue_setup_summary_failure_keeps_committed_records_observable(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=1)
    record = repo.get_record(build_id, "r1")
    record["metadata_enrichment_state"] = "running"
    repo.update_record(build_id, record)
    notifications = []

    def committed(bid):
        assert cb.PdfCorpusRepository(repo.root).get_record(bid, "r1")["metadata_enrichment_state"] == "queued"
        notifications.append(bid)

    def fail_summary(*args):
        raise OSError("Queue summary storage unavailable")

    monkeypatch.setattr(repo, "_metadata_projection_callback", committed)
    monkeypatch.setattr(repo, "save_build", fail_summary)
    with pytest.raises(OSError, match="Queue summary"):
        manager._initialize_build_enrichment(build_id, {})
    assert notifications == [build_id]
    assert repo.records_projection_dirty(build_id)


def test_completion_preserves_human_assertion_and_other_record_edit(build_factory, monkeypatch):
    repo, build_id, manager = build_factory()

    def enrich(record, *_args, **_kwargs):
        if record["record_id"] == "r1":
            with manager._lock:
                live = repo.get_record(build_id, "r1")
                create_human_assertion(live, "speaker", "Reviewed speaker", method="human")
                project_record_assertions(live)
                repo.update_record(build_id, live)
                neighbour = repo.get_record(build_id, "r3")
                neighbour["text"] = "Human-corrected text"
                neighbour["record_revision"] = 2
                neighbour["human_touched_fields"] = ["__text__"]
                repo.update_record(build_id, neighbour)
        return _completed(record)

    monkeypatch.setattr(manager, "_enrich_record", enrich)
    result = manager._schedule_build_enrichment(build_id, {"max_concurrent_requests": 1}, {}, repo.load_records(build_id))
    persisted = repo.load_records(build_id)
    assert result == persisted
    assert persisted[0]["speaker"] == "Reviewed speaker"
    assert current_assertion_by_name(persisted[0], "speaker").authority_status == "human_confirmed"
    assert persisted[2]["text"] == "Human-corrected text"
    assert persisted[2]["record_revision"] == 2
    assert persisted[1]["speaker"] == "Model speaker"


def test_completion_is_durable_before_notification_and_after_restart(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=1)

    def interrupt_after_commit(_build, record_id, event):
        assert event == "record_completed"
        restarted = cb.PdfCorpusRepository(repo.root)
        assert restarted.get_record(build_id, record_id)["metadata_complete"]
        assert restarted.get_build(build_id)["metadata_first_settled_at"]
        raise InterruptedError("simulated stop after durable completion")

    monkeypatch.setattr(cb, "note_record_metadata", interrupt_after_commit)
    with pytest.raises(InterruptedError, match="simulated stop"):
        manager._schedule_build_enrichment(build_id, {}, {}, repo.load_records(build_id))
    restarted = cb.PdfCorpusRepository(repo.root)
    assert restarted.get_record(build_id, "r1")["speaker"] == "Model speaker"
    restarted.refresh_records_projection(build_id)
    exported = [json.loads(line) for line in restarted.build_records_path(build_id).read_text(encoding="utf-8").splitlines()]
    assert exported == restarted.load_records(build_id)
    assert not restarted.records_projection_dirty(build_id)


def test_first_settled_milestone_is_not_reset_by_later_completions(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=3)
    seen = []

    def completed_notification(_build, record_id, event):
        assert event == "record_completed"
        snapshot = repo.get_build(build_id)
        seen.append(snapshot["metadata_first_settled_at"])
        assert repo.get_record(build_id, record_id)["metadata_enrichment_state"] == "complete"

    monkeypatch.setattr(cb, "note_record_metadata", completed_notification)
    manager._schedule_build_enrichment(build_id, {}, {}, repo.load_records(build_id))
    assert len(seen) == 3
    assert len(set(seen)) == 1


def test_failed_worker_preserves_source_and_reports_failure(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=1)
    original = repo.get_record(build_id, "r1")

    def fail(*_args, **_kwargs):
        raise ValueError("provider failed")

    monkeypatch.setattr(manager, "_enrich_record", fail)
    result = manager._schedule_build_enrichment(build_id, {}, {}, repo.load_records(build_id))
    assert result[0]["text"] == original["text"]
    assert result[0]["source_spans"] == original["source_spans"]
    assert result[0]["metadata_enrichment_state"] == "failed"
    assert not result[0]["metadata_complete"]
    assert any("provider failed" in reason for reason in result[0]["metadata_attention_reasons"])


def test_completion_does_not_rewrite_the_corpus(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=4)
    records = repo.load_records(build_id)
    saves, loads = [], []
    save, load = repo.save_records, repo.load_records

    def saved(*args):
        saves.append(len(args[1]))
        return save(*args)

    def loaded(*args):
        loads.append(args[0])
        return load(*args)

    monkeypatch.setattr(repo, "save_records", saved)
    monkeypatch.setattr(repo, "load_records", loaded)
    result = manager._schedule_build_enrichment(build_id, {}, {}, records)
    assert all(row["metadata_complete"] for row in result)
    assert saves == []  # Queue initialization and completion both write target rows.
    assert len(loads) == 1  # Final handoff only; initialization uses the coordinated SQLite snapshot.


@pytest.mark.parametrize("workers", [1, 3])
def test_build_submission_window_is_bounded_until_durable_completion(
    build_factory, monkeypatch, workers,
):
    repo, build_id, manager = build_factory(count=20)
    submitted = []
    completed = []
    original_pool = cb.ThreadPoolExecutor

    class TrackingPool(original_pool):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.is_record_pool = kwargs.get("thread_name_prefix") == "pdf-corpus-meta"

        def submit(self, fn, *args, **kwargs):
            if self.is_record_pool:
                submitted.append(args[0]["record_id"])
                assert len(submitted) - len(completed) <= workers
            return super().submit(fn, *args, **kwargs)

    def notification(_build, record_id, event):
        assert event == "record_completed"
        assert repo.get_record(build_id, record_id)["metadata_complete"]
        completed.append(record_id)

    monkeypatch.setattr(cb, "ThreadPoolExecutor", TrackingPool)
    monkeypatch.setattr(cb, "note_record_metadata", notification)
    result = manager._schedule_build_enrichment(
        build_id, {"max_concurrent_requests": workers}, {}, repo.load_records(build_id),
    )
    assert len(submitted) == len(completed) == 20
    assert len(set(completed)) == 20
    assert all(row["metadata_complete"] for row in result)
    assert submitted == [f"r{index}" for index in range(1, 21)]


def test_build_cancellation_does_not_admit_the_remaining_corpus(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=20)
    admitted = []
    stop = False

    def enrich(record, *_args, **_kwargs):
        admitted.append(record["record_id"])
        return _completed(record)

    def notification(_build, record_id, event):
        nonlocal stop
        assert repo.get_record(build_id, record_id)["metadata_complete"]
        stop = True

    monkeypatch.setattr(manager, "_enrich_record", enrich)
    monkeypatch.setattr(manager, "_cancelled", lambda _build: stop)
    monkeypatch.setattr(cb, "note_record_metadata", notification)
    with pytest.raises(InterruptedError, match="cancelled"):
        manager._schedule_build_enrichment(build_id, {"max_concurrent_requests": 1}, {}, repo.load_records(build_id))
    assert admitted == ["r1"]
    assert repo.get_record(build_id, "r1")["metadata_complete"]
    assert not repo.get_record(build_id, "r2")["metadata_complete"]


def test_retired_record_completion_does_not_restore_old_topology(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=1)

    def replace_topology(record, *_args, **_kwargs):
        replacement = _completed(record)
        replacement["record_id"] = "replacement"
        replacement["record_revision"] = 1
        with manager._lock:
            repo.save_records(build_id, [replacement])
        return _completed(record)

    monkeypatch.setattr(manager, "_enrich_record", replace_topology)
    result = manager._schedule_build_enrichment(build_id, {}, {}, repo.load_records(build_id))
    assert [row["record_id"] for row in result] == ["replacement"]
    assert result == repo.load_records(build_id)
    with pytest.raises(KeyError):
        repo.get_record(build_id, "r1")


def test_split_during_enrichment_requeues_successors_and_conserves_source(build_factory, monkeypatch):
    repo, build_id, manager = build_factory(count=1)
    original = repo.get_record(build_id, "r1")["text"]
    processed = []

    def enrich(record, *_args, **_kwargs):
        processed.append(record["record_id"])
        if record["record_id"] == "r1":
            manager.split(build_id, "r1", expected_revision=1, offset=original.index("evidence") + 8)
        return _completed(record)

    monkeypatch.setattr(manager, "_enrich_record", enrich)
    result = manager._schedule_build_enrichment(build_id, {}, {}, repo.load_records(build_id))
    successor_ids = {row["record_id"] for row in result}
    assert len(result) == 2
    assert "r1" not in successor_ids
    assert set(processed) == {"r1", *successor_ids}
    assert all(row["metadata_complete"] and not row.get("metadata_requeue_requested") for row in result)
    assert "".join("".join(row["text"].split()) for row in result) == "".join(original.split())
    assert all(row["lineage"]["parent_record_ids"] == ["r1"] for row in result)
    assert result == repo.load_records(build_id)
    assert manager.retired_records(build_id)[0]["record_id"] == "r1"


@pytest.mark.skipif(not os.environ.get("CORPUS_PERSISTENCE_BENCHMARK"), reason="opt-in persistence benchmark")
@pytest.mark.parametrize("count", [1000, 10000])
@pytest.mark.parametrize("sample", range(3))
def test_persistence_benchmark(build_factory, monkeypatch, count, sample):
    repo, build_id, manager = build_factory(count=count, pending=20)
    records = repo.load_records(build_id)
    counters = {"full_saves": 0, "full_save_rows": 0, "row_updates": 0}
    save, update, reconcile_write = repo.save_records, repo.update_record, repo._write_reconciled_rows

    def saved(build_id, rows):
        counters["full_saves"] += 1
        counters["full_save_rows"] += len(rows)
        return save(build_id, rows)

    def updated(*args, **kwargs):
        counters["row_updates"] += 1
        return update(*args, **kwargs)

    def reconciled(connection, bid, rows):
        counters["row_updates"] += len(rows)
        return reconcile_write(connection, bid, rows)

    monkeypatch.setattr(repo, "save_records", saved)
    monkeypatch.setattr(repo, "update_record", updated)
    monkeypatch.setattr(repo, "_write_reconciled_rows", reconciled)
    start = time.perf_counter()
    result = manager._schedule_build_enrichment(build_id, {"max_concurrent_requests": 1}, {}, records)
    elapsed = time.perf_counter() - start
    assert all(row["metadata_complete"] for row in result)
    row = {"contract": "corpus-persistence-repository-v2",
           "records": count, "completions": 20, "sample": sample, "seconds": elapsed,
           "python": platform.python_version(), "platform": platform.platform(), **counters}
    with Path(os.environ["CORPUS_PERSISTENCE_BENCHMARK"]).open("a", encoding="utf-8") as output:
        output.write(json.dumps(row) + "\n")
