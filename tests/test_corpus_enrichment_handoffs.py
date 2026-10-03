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

"""Enrichment handoffs preserve current Records, bounded writes, and writer access."""

from __future__ import annotations

import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from app import corpus_builder as cb
from app import corpus_enrichment_reruns as reruns
from app.corpus_pipeline import BuildScope
from app.field_assertions import (
    create_human_assertion,
    create_model_assertion,
    current_assertion_by_name,
    project_record_assertions,
)
from app.metadata_schema import default_schema
from test_enrichment_cycles import make_manager, proposal
from test_review_queues import install_repo, ready_record


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    repo, build = install_repo(tmp_path, [ready_record("r1", "b1"), ready_record("r2", "b2")])
    # Isolate canonical handoffs from asynchronous vector-provider retries.
    monkeypatch.setattr(cb.PdfCorpusBuildManager, "_schedule_metadata_exemplar_projection", lambda *args: None)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    yield repo, build["build_id"], manager
    manager._executor.shutdown(wait=True)


def forbid_replacement(monkeypatch, repo):
    monkeypatch.setattr(repo, "save_records", lambda *args: pytest.fail("handoff replaced the corpus"))


def test_reconciliation_writes_only_changed_rows_and_keeps_cursor_context(prepared, monkeypatch):
    repo, bid, _manager = prepared
    before = repo.get_records(bid, ["r1", "r2"], include_queue_version=True)
    updates = []
    update_rows = cb.corpus_queue_projection.update_rows

    def counted(connection, rows, **kwargs):
        updates.extend(record["record_id"] for _ordinal, record in rows)
        return update_rows(connection, rows, **kwargs)

    monkeypatch.setattr(cb.corpus_queue_projection, "update_rows", counted)
    forbid_replacement(monkeypatch, repo)

    def reconcile(rows):
        rows[0]["review_reason"] = "Current review reason"

    repo.reconcile_records(bid, reconcile)
    assert updates == ["r1"]
    after = repo.get_records(bid, ["r1", "r2"], include_queue_version=True)
    assert after[0]["queue_state_version"] > before[0]["queue_state_version"]
    assert after[1]["queue_state_version"] == before[1]["queue_state_version"]
    assert cb.PdfCorpusRepository(repo.root).get_record(bid, "r1")["review_reason"] == "Current review reason"
    assert repo.records_projection_dirty(bid)
    updates.clear()
    repo.reconcile_records(bid, lambda rows: None)
    assert not updates
    repo.refresh_records_projection(bid)
    assert [
        json.loads(line) for line in repo.build_records_path(bid).read_text(encoding="utf-8").splitlines()
    ] == repo.load_records(bid)


@pytest.mark.parametrize("optimistic", [False, True])
@pytest.mark.parametrize("failure", ["exception", "identity", "addition", "retirement", "reorder"])
def test_reconciliation_rolls_back_failed_or_topology_changing_callback(prepared, failure, optimistic):
    repo, bid, _manager = prepared
    before = repo.load_records(bid)

    def reconcile(rows):
        rows[0]["review_reason"] = "Must roll back"
        if failure == "exception":
            raise ValueError("Failed validation")
        if failure == "identity":
            rows[0]["record_id"] = "invented"
        elif failure == "addition":
            rows.append(ready_record("invented", "b3"))
        elif failure == "retirement":
            rows.pop()
        elif failure == "reorder":
            rows.reverse()

    with pytest.raises(ValueError):
        repo.reconcile_records(bid, reconcile, optimistic=optimistic)
    assert repo.load_records(bid) == before
    assert not repo.records_projection_dirty(bid)


def test_selected_reconciliation_is_bounded_skips_retired_ids_and_notifies_after_commit(prepared, monkeypatch):
    repo, bid, _manager = prepared
    decoded = []
    decode = repo._decode_migrated

    def counted(payload, schema, signature):
        decoded.append(json.loads(payload)["record_id"])
        return decode(payload, schema, signature)

    def committed(build_id):
        assert cb.PdfCorpusRepository(repo.root).get_record(build_id, "r2")["review_reason"] == "Changed"

    monkeypatch.setattr(repo, "_decode_migrated", counted)
    monkeypatch.setattr(repo, "_metadata_projection_callback", committed)
    forbid_replacement(monkeypatch, repo)
    result = repo.reconcile_records(
        bid, lambda rows: rows[0].update(review_reason="Changed"), record_ids=["retired", "r2", "r2"],
    )
    assert decoded == ["r2"]
    assert [row["record_id"] for row in result] == ["r2"]


def test_external_writer_cannot_interleave_with_reconciliation(prepared):
    repo, bid, _manager = prepared
    external = cb.PdfCorpusRepository(repo.root)
    external_record = external.get_record(bid, "r2")
    started = threading.Event()
    attempt = threading.Event()
    release = threading.Event()

    def reconcile(rows):
        started.set()
        assert release.wait(10)
        rows[0]["metadata_attention_reasons"] = ["Validated reason"]

    def edit():
        assert started.wait(10)
        current = external_record
        current["review_reason"] = "External decision"
        attempt.set()
        external.update_record(bid, current)

    with ThreadPoolExecutor(max_workers=2) as pool:
        validation = pool.submit(repo.reconcile_records, bid, reconcile)
        writer = pool.submit(edit)
        try:
            assert attempt.wait(10)
            assert not writer.done()
        finally:
            release.set()
        validation.result(timeout=10)
        writer.result(timeout=10)
    assert repo.get_record(bid, "r1")["metadata_attention_reasons"] == ["Validated reason"]
    assert repo.get_record(bid, "r2")["review_reason"] == "External decision"


@pytest.mark.parametrize("same_repository", [False, True])
def test_optimistic_validation_releases_writer_and_repository_locks(prepared, monkeypatch, same_repository):
    repo, bid, manager = prepared
    writer_repo = repo if same_repository else cb.PdfCorpusRepository(repo.root)
    started = threading.Event()
    committed = threading.Event()
    release = threading.Event()
    validate = manager._validate_record_states
    attempts = []

    def paused(build, records):
        attempts.append([record["review_reason"] for record in records])
        if len(attempts) == 1:
            started.set()
            assert release.wait(10)
        validate(build, records)

    def edit():
        assert started.wait(10)
        record = writer_repo.get_record(bid, "r2")
        record["review_reason"] = "Concurrent reviewer decision"
        writer_repo.update_record(bid, record)
        committed.set()

    monkeypatch.setattr(manager, "_validate_record_states", paused)
    forbid_replacement(monkeypatch, repo)
    with ThreadPoolExecutor(max_workers=2) as pool:
        validation = pool.submit(manager._reconcile_and_validate, bid)
        writer = pool.submit(edit)
        try:
            assert committed.wait(10), "Validation prevented an independent Record commit"
            assert not validation.done()
        finally:
            release.set()
        writer.result(timeout=10)
        result = validation.result(timeout=10)
    assert len(attempts) == 2
    assert attempts[1][1] == "Concurrent reviewer decision"
    assert repo.get_record(bid, "r2")["review_reason"] == "Concurrent reviewer decision"
    assert result["record_count"] == 2


@pytest.mark.parametrize("operation", ["validation", "retry", "rerun", "final_handoff"])
@pytest.mark.parametrize("edit", ["text", "metadata", "disposition"])
def test_review_commands_commit_during_automatic_validation(prepared, monkeypatch, operation, edit):
    repo, bid, manager = prepared
    manager._update(
        bid, status="running",
        stage="finalizing_review" if operation == "final_handoff" else
        "metadata_retry" if operation == "retry" else
        "metadata_enrichment_rerun" if operation == "rerun" else "enriching",
    )
    entered = threading.Event()
    edited = threading.Event()
    release = threading.Event()
    validate = manager._validate_record_states
    attempts = []
    monkeypatch.setattr(manager, "_share_generalizable_learning", lambda _: None)
    monkeypatch.setattr(manager, "_run_enrichment_pass", lambda *args, **kwargs: {})

    def paused(build, records):
        attempts.append(None)
        if len(attempts) == 1:
            entered.set()
            assert release.wait(10)
        validate(build, records)

    def run():
        if operation == "retry":
            manager._retry_metadata_worker(bid, {}, "retry-test", [], {})
        elif operation == "rerun":
            manager._metadata_enrichment_rerun_worker(bid, {}, "rerun-test", "all", [], 1)
        elif operation == "final_handoff":
            scope = BuildScope(repo.get_build(bid), {}, {}, repo.load_blocks("a"), [], {}, False)
            manager._finalize_build_review(bid, scope, repo.load_records(bid))
        else:
            manager._reconcile_and_validate(bid)

    def review():
        assert entered.wait(10)
        if edit == "text":
            result = manager.patch_record_text(bid, "r1", "Human-corrected documentary text", expected_revision=1)
        elif edit == "metadata":
            result = manager.patch_metadata(bid, "r1", {"speaker": "Reviewed speaker"}, expected_revision=1)
        else:
            result = manager.review_decision(bid, "r1", "rejected", expected_revision=1)["record"]
        edited.set()
        return result

    monkeypatch.setattr(manager, "_validate_record_states", paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        validation = pool.submit(run)
        reviewer = pool.submit(review)
        try:
            assert edited.wait(10), "Automatic validation held the manager lock against review"
            assert not validation.done()
        finally:
            release.set()
        reviewed = reviewer.result(timeout=10)
        validation.result(timeout=10)
    assert len(attempts) == 2
    saved = repo.get_record(bid, "r1")
    assert saved["record_revision"] == reviewed["record_revision"] == 2
    if edit == "text":
        assert saved["text"] == "Human-corrected documentary text"
        assert saved["source_extracted_text"] == reviewed["source_extracted_text"]
    elif edit == "metadata":
        assert saved["speaker"] == "Reviewed speaker"
        assert current_assertion_by_name(saved, "speaker").authority_status == "human_confirmed"
    else:
        assert saved["review_disposition"] == "rejected"
        assert repo.get_build(bid)["rejected_count"] == 1
    if operation in {"retry", "rerun"}:
        assert repo.get_build(bid)["metadata_operation"]["state"] == "completed"


def test_automatic_validation_retries_build_only_updates(prepared, monkeypatch):
    repo, bid, manager = prepared
    validate = manager._validate_record_states
    seen = []

    def changed_operation(build, records):
        seen.append(build.get("operation_hidden"))
        validate(build, records)
        if len(seen) == 1:
            manager._update(bid, operation_hidden=True, human_decision_count=12)

    monkeypatch.setattr(manager, "_validate_record_states", changed_operation)
    result = manager._reconcile_and_validate(bid)
    assert seen == [None, True]
    assert result["operation_hidden"] is True
    assert result["human_decision_count"] == repo.get_build(bid)["human_decision_count"] == 12


def test_build_only_conflicts_are_bounded_and_do_not_publish_candidate(prepared, monkeypatch):
    repo, bid, manager = prepared
    before = repo.load_records(bid)
    validate = manager._validate_record_states
    attempts = []

    def conflicting(build, records):
        attempts.append(None)
        validate(build, records)
        records[0]["reviewer_note"] = "Uncommitted"
        manager._update(bid, human_decision_count=len(attempts))

    monkeypatch.setattr(manager, "_validate_record_states", conflicting)
    with pytest.raises(cb.RecordStateConflict, match="validation"):
        manager._reconcile_and_validate(bid)
    assert len(attempts) == 3
    assert repo.load_records(bid) == before
    assert repo.get_build(bid)["human_decision_count"] == 3


def test_automatic_validation_keeps_review_serialized_through_summary_handoff(prepared, monkeypatch):
    repo, bid, manager = prepared
    summary_entered = threading.Event()
    reviewer_attempted = threading.Event()
    release = threading.Event()
    save = repo.save_build

    def paused(build):
        if threading.current_thread().name.startswith("validation-handoff"):
            summary_entered.set()
            assert release.wait(10)
        return save(build)

    def review():
        assert summary_entered.wait(10)
        reviewer_attempted.set()
        return manager.review_decision(bid, "r1", "rejected", expected_revision=1)

    monkeypatch.setattr(repo, "save_build", paused)
    with (
        ThreadPoolExecutor(max_workers=1, thread_name_prefix="validation-handoff") as validation_pool,
        ThreadPoolExecutor(max_workers=1) as review_pool,
    ):
        validation = validation_pool.submit(manager._reconcile_and_validate, bid)
        reviewer = review_pool.submit(review)
        try:
            assert reviewer_attempted.wait(10)
            assert not reviewer.done(), "Review interleaved between Record commit and summary save"
        finally:
            release.set()
        validation.result(timeout=10)
        assert reviewer.result(timeout=10)["applied"]
    assert repo.get_build(bid)["rejected_count"] == 1
    assert repo.get_record(bid, "r1")["review_disposition"] == "rejected"


def test_other_build_review_does_not_wait_for_or_invalidate_validation(prepared, monkeypatch):
    repo, bid, manager = prepared
    payload = repo.get_build(bid)
    payload.pop("build_id")
    other = repo.create_build(payload)["build_id"]
    repo.save_records(other, [ready_record("r3", "b1")])
    entered = threading.Event()
    edited = threading.Event()
    release = threading.Event()
    validate = manager._validate_record_states
    calls = []

    def paused(build, records):
        calls.append(None)
        entered.set()
        assert release.wait(10)
        validate(build, records)

    def review():
        assert entered.wait(10)
        result = manager.patch_metadata(other, "r3", {"speaker": "Other reviewed speaker"}, expected_revision=1)
        edited.set()
        return result

    monkeypatch.setattr(manager, "_validate_record_states", paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        validation = pool.submit(manager._reconcile_and_validate, bid)
        reviewer = pool.submit(review)
        try:
            assert edited.wait(10)
            assert not validation.done()
        finally:
            release.set()
        assert reviewer.result(timeout=10)["speaker"] == "Other reviewed speaker"
        validation.result(timeout=10)
    assert len(calls) == 1
    assert repo.get_record(other, "r3")["speaker"] == "Other reviewed speaker"


def test_summary_save_failure_is_visible_without_hiding_committed_records(prepared, monkeypatch):
    repo, bid, manager = prepared
    validate = manager._validate_record_states
    notifications = []

    def changed(build, records):
        validate(build, records)
        records[0]["reviewer_note"] = "Committed delta"

    def fail_summary(build):
        raise OSError("Summary storage unavailable")

    def committed(build_id):
        assert cb.PdfCorpusRepository(repo.root).get_record(build_id, "r1")["reviewer_note"] == "Committed delta"
        notifications.append(build_id)

    monkeypatch.setattr(manager, "_validate_record_states", changed)
    monkeypatch.setattr(repo, "save_build", fail_summary)
    monkeypatch.setattr(repo, "_metadata_projection_callback", committed)
    with pytest.raises(OSError, match="Summary storage unavailable"):
        manager._reconcile_and_validate(bid)
    assert notifications == [bid]
    assert repo.records_projection_dirty(bid)


def test_final_handoff_does_not_repeat_validation_against_stale_worker_scope(prepared, monkeypatch):
    repo, bid, manager = prepared
    scope = BuildScope(repo.get_build(bid), {}, {}, [{"block_id": "obsolete", "text": "Old source"}], [], {}, False)
    validate = manager.validate_records
    calls = []

    def counted(blocks, records, profile):
        calls.append([block["block_id"] for block in blocks])
        return validate(blocks, records, profile)

    monkeypatch.setattr(manager, "validate_records", counted)
    manager._finalize_build_review(bid, scope, repo.load_records(bid))
    assert calls == [["b1", "b2"]]
    assert repo.get_build(bid)["record_count"] == 2


@pytest.mark.parametrize("action", ["cancel", "pause"])
@pytest.mark.parametrize("operation", ["validation", "retry", "rerun", "final_handoff"])
def test_cancellation_during_validation_is_not_erased_at_handoff(prepared, monkeypatch, action, operation):
    repo, bid, manager = prepared
    manager._update(bid, status="running", stage="metadata_enrichment_rerun" if operation == "rerun" else "enriching")
    validate = manager._validate_record_states
    calls = []
    monkeypatch.setattr(manager, "_share_generalizable_learning", lambda _: None)
    monkeypatch.setattr(manager, "_run_enrichment_pass", lambda *args, **kwargs: {})

    def interrupted(build, records):
        calls.append(None)
        validate(build, records)
        if len(calls) == 1:
            getattr(manager, action)(bid)

    monkeypatch.setattr(manager, "_validate_record_states", interrupted)
    if operation == "retry":
        manager._retry_metadata_worker(bid, {}, "retry-test", [], {})
        assert repo.get_build(bid)["metadata_operation"]["state"] == "failed"
        assert "cancelled" in repo.get_build(bid)["metadata_operation"]["error"]
    elif operation == "rerun":
        manager._metadata_enrichment_rerun_worker(bid, {}, "rerun-test", "all", [], 1)
        assert repo.get_build(bid)["metadata_operation"]["state"] == "cancelled"
    elif operation == "final_handoff":
        scope = BuildScope(repo.get_build(bid), {}, {}, repo.load_blocks("a"), [], {}, False)
        with pytest.raises(InterruptedError, match="cancelled"):
            manager._finalize_build_review(bid, scope, repo.load_records(bid))
        assert repo.get_build(bid)["cancel_requested"] is True
    else:
        result = manager._reconcile_and_validate(bid)
        assert result["cancel_requested"] is True
    assert len(calls) == 2
    if action == "pause":
        assert repo.get_build(bid)["pause_requested"] is True


@pytest.mark.parametrize("stage", ["preparing", "constructing_topology", "document_intelligence"])
def test_preparation_still_blocks_review_commands(prepared, stage):
    repo, bid, manager = prepared
    manager._update(bid, status="running", stage=stage)
    before = repo.get_record(bid, "r1")
    with pytest.raises(ValueError, match="not editable"):
        manager.patch_metadata(bid, "r1", {"speaker": "Premature decision"}, expected_revision=1)
    assert repo.get_record(bid, "r1") == before


@pytest.mark.parametrize("change", ["text", "human", "retirement", "reorder", "repair", "counter_reset", "raw_write"])
def test_optimistic_reconciliation_recomputes_changed_snapshot(prepared, monkeypatch, change):
    repo, bid, _manager = prepared
    external = cb.PdfCorpusRepository(repo.root)
    attempts = []
    notifications = []

    def reconcile(records):
        attempts.append([record["record_id"] for record in records])
        records[0]["review_reason"] = f"Validated attempt {len(attempts)}"
        if len(attempts) != 1:
            return
        current = external.load_records(bid)
        if change == "text":
            current[0]["text"] = "Corrected documentary text"
            current[0]["record_revision"] += 1
            external.update_record(bid, current[0])
        elif change == "human":
            create_human_assertion(current[0], "speaker", "Reviewed speaker", method="human")
            project_record_assertions(current[0])
            external.update_record(bid, current[0])
        elif change == "retirement":
            external.save_records(bid, current[1:])
        elif change == "reorder":
            external.save_records(bid, list(reversed(current)))
        elif change in {"repair", "counter_reset"}:
            with external._records_db(bid) as connection:
                if change == "counter_reset":
                    connection.execute("UPDATE review_projection_meta SET generation=0, topology=0 WHERE id=1")
                external._ensure_review_projection(connection, bid, rebuild=True)
        else:
            current[0]["reviewer_note"] = "Direct canonical write"
            with external._records_db(bid) as connection:
                connection.execute(
                    "UPDATE corpus_records SET payload=? WHERE record_id=?",
                    (json.dumps(current[0], ensure_ascii=False), "r1"),
                )

    def committed(build_id):
        rows = cb.PdfCorpusRepository(repo.root).load_records(build_id)
        assert rows[0]["review_reason"] == "Validated attempt 2"
        notifications.append(build_id)

    monkeypatch.setattr(repo, "_metadata_projection_callback", committed)
    result = repo.reconcile_records(bid, reconcile, optimistic=True)
    assert len(attempts) == 2
    assert notifications == [bid]
    assert result == cb.PdfCorpusRepository(repo.root).load_records(bid)
    assert result[0]["review_reason"] == "Validated attempt 2"
    if change == "text":
        assert result[0]["text"] == "Corrected documentary text"
        assert result[0]["record_revision"] == 2
    elif change == "human":
        assert result[0]["speaker"] == "Reviewed speaker"
        assert current_assertion_by_name(result[0], "speaker").authority_status == "human_confirmed"
    elif change == "retirement":
        assert attempts[1] == ["r2"]
    elif change == "reorder":
        assert attempts[1] == ["r2", "r1"]
    elif change == "raw_write":
        assert result[0]["reviewer_note"] == "Direct canonical write"


def test_optimistic_reconciliation_has_bounded_visible_conflicts(prepared, monkeypatch):
    repo, bid, manager = prepared
    external = cb.PdfCorpusRepository(repo.root)
    attempts = []
    saved_build = repo.get_build(bid)
    notifications = []
    validate = manager._validate_record_states

    def conflicting(build, records):
        attempts.append(None)
        validate(build, records)
        records[0]["reviewer_note"] = "Must never commit"
        current = external.get_record(bid, "r2")
        current["review_reason"] = f"External edit {len(attempts)}"
        external.update_record(bid, current)

    monkeypatch.setattr(manager, "_validate_record_states", conflicting)
    monkeypatch.setattr(repo, "_metadata_projection_callback", notifications.append)
    with pytest.raises(cb.RecordStateConflict, match="validation"):
        manager._reconcile_and_validate(bid)
    assert len(attempts) == 3
    assert not notifications
    assert "reviewer_note" not in repo.get_record(bid, "r1")
    assert repo.get_record(bid, "r2")["review_reason"] == "External edit 3"
    assert repo.get_build(bid)["validation"] == saved_build["validation"]


def test_optimistic_noop_does_not_write_or_notify(prepared, monkeypatch):
    repo, bid, _manager = prepared
    before = repo.get_records(bid, ["r1", "r2"], include_queue_version=True)
    monkeypatch.setattr(repo, "_metadata_projection_callback", lambda _: pytest.fail("No-op notified"))
    repo.reconcile_records(bid, lambda rows: None, optimistic=True)
    assert repo.get_records(bid, ["r1", "r2"], include_queue_version=True) == before
    assert not repo.records_projection_dirty(bid)


def test_optimistic_selected_reconciliation_decodes_only_requested_current_rows(prepared, monkeypatch):
    repo, bid, _manager = prepared
    decoded = []
    decode = repo._decode_migrated
    writes = []
    update_rows = cb.corpus_queue_projection.update_rows

    def counted(payload, schema, signature):
        decoded.append(json.loads(payload)["record_id"])
        return decode(payload, schema, signature)

    def counted_write(connection, rows, **kwargs):
        writes.extend(record["record_id"] for _, record in rows)
        return update_rows(connection, rows, **kwargs)

    monkeypatch.setattr(repo, "_decode_migrated", counted)
    monkeypatch.setattr(cb.corpus_queue_projection, "update_rows", counted_write)
    result = repo.reconcile_records(
        bid, lambda rows: rows[0].update(review_reason="Selected"),
        record_ids=["retired", "r2", "r2"], optimistic=True,
    )
    assert decoded == ["r2"]
    assert writes == ["r2"]
    assert [row["record_id"] for row in result] == ["r2"]


def test_optimistic_reconciliation_rechecks_schema_without_database_write(prepared, monkeypatch):
    repo, bid, _manager = prepared
    schema = default_schema().model_copy(update={"name": "Original"})
    calls = []
    monkeypatch.setattr(repo, "_record_schema", lambda _: schema)

    def reconcile(rows):
        nonlocal schema
        calls.append(None)
        rows[0]["review_reason"] = schema.name
        if len(calls) == 1:
            schema = schema.model_copy(update={"name": "Changed"})

    result = repo.reconcile_records(bid, reconcile, optimistic=True)
    assert len(calls) == 2
    assert result[0]["review_reason"] == "Changed"


def test_automatic_validation_reloads_build_contract_on_conflict(prepared, monkeypatch):
    repo, bid, manager = prepared
    external = cb.PdfCorpusRepository(repo.root)
    build = external.get_build(bid)
    build["schema"] = default_schema().model_dump(mode="json")
    build["schema"]["name"] = "Original"
    external.save_build(build)
    seen = []
    validate = manager._validate_record_states

    def changed_contract(build, records):
        seen.append(build["schema"]["name"])
        validate(build, records)
        if len(seen) == 1:
            current = external.get_build(bid)
            current["schema"]["name"] = "Changed"
            external.save_build(current)

    monkeypatch.setattr(manager, "_validate_record_states", changed_contract)
    result = manager._reconcile_and_validate(bid)
    assert seen == ["Original", "Changed"]
    assert result["schema"]["name"] == "Changed"
    assert repo.get_build(bid)["schema"]["name"] == "Changed"


def test_conflicting_noop_is_recomputed_instead_of_returning_stale_state(prepared):
    repo, bid, _manager = prepared
    external = cb.PdfCorpusRepository(repo.root)
    calls = []

    def reconcile(rows):
        calls.append(None)
        if len(calls) == 1:
            current = external.get_record(bid, "r1")
            current["review_reason"] = "Current"
            external.update_record(bid, current)

    result = repo.reconcile_records(bid, reconcile, optimistic=True)
    assert len(calls) == 2
    assert result[0]["review_reason"] == "Current"


def test_current_validation_matches_existing_validation_and_does_not_restore_stale_input(prepared, monkeypatch):
    repo, bid, manager = prepared
    original = repo.load_records(bid)
    manager._rewrite_and_validate(bid, copy.deepcopy(original))
    expected = repo.load_records(bid)
    repo.save_records(bid, original)
    forbid_replacement(monkeypatch, repo)
    manager._reconcile_and_validate(bid)
    assert repo.load_records(bid) == expected
    current = repo.get_record(bid, "r1")
    current["text"] = "Corrected authoritative source"
    current["record_revision"] += 1
    create_human_assertion(current, "speaker", "Reviewed speaker", method="human")
    project_record_assertions(current)
    repo.update_record(bid, current)
    manager._reconcile_and_validate(bid)
    saved = repo.get_record(bid, "r1")
    assert saved["text"] == current["text"]
    assert saved["record_revision"] == current["record_revision"]
    assert saved["speaker"] == "Reviewed speaker"
    assert current_assertion_by_name(saved, "speaker").authority_status == "human_confirmed"
    assert repo.records_projection_dirty(bid)
    assert repo.get_build(bid)["record_count"] == 2


def test_final_handoff_keeps_replacement_topology_and_is_write_free_when_settled(prepared, monkeypatch):
    repo, bid, manager = prepared
    stale = repo.load_records(bid)
    replacement = ready_record("replacement", "b1")
    repo.save_records(bid, [replacement])
    scope = BuildScope(repo.get_build(bid), {}, {}, repo.load_blocks("a"), [], {}, False)
    forbid_replacement(monkeypatch, repo)
    manager._finalize_build_review(bid, scope, stale)
    assert [row["record_id"] for row in repo.load_records(bid)] == ["replacement"]
    assert repo.get_build(bid)["record_count"] == 1
    assert repo.get_build(bid)["status"] == "awaiting_review"
    manager._reconcile_and_validate(bid)
    before = repo.get_records(bid, ["replacement"], include_queue_version=True)
    manager._reconcile_and_validate(bid)
    assert repo.get_records(bid, ["replacement"], include_queue_version=True) == before


def test_requeue_clears_only_current_marker_without_full_replacement(prepared, monkeypatch):
    repo, bid, manager = prepared
    current = repo.get_record(bid, "r1")
    current["metadata_requeue_requested"] = True
    repo.update_record(bid, current)
    forbid_replacement(monkeypatch, repo)
    result = manager._schedule_build_enrichment(bid, {}, {}, repo.load_records(bid))
    assert not result[0].get("metadata_requeue_requested")
    assert [row["record_id"] for row in result] == ["r1", "r2"]
    assert cb.PdfCorpusRepository(repo.root).load_records(bid) == result


def test_queued_retry_targets_identity_not_obsolete_ordinal(prepared, monkeypatch):
    repo, bid, manager = prepared
    records = repo.load_records(bid)
    repo.save_records(bid, list(reversed(records)))
    seen = []

    def enrich(record, *args, **kwargs):
        seen.append(record["record_id"])
        return record

    monkeypatch.setattr(manager, "_enrich_record", enrich)
    forbid_replacement(monkeypatch, repo)
    manager._retry_metadata_worker(bid, {}, "queued-retry", [0], {"r1": ["speaker"]})
    assert seen == ["r1"]
    assert repo.get_build(bid)["metadata_operation"]["state"] == "completed"


@pytest.mark.parametrize("change", ["human", "text", "revision", "source", "retirement", "failure"])
def test_retry_completion_is_targeted_durable_and_rejects_stale_source(prepared, monkeypatch, change):
    repo, bid, manager = prepared
    original = repo.get_record(bid, "r1")
    events = []

    def enrich(record, *args, **kwargs):
        current = repo.get_record(bid, "r1")
        if change == "human":
            create_human_assertion(current, "speaker", "Reviewed speaker", method="human")
            project_record_assertions(current)
        elif change == "text":
            current["text"] = "Corrected source"
        elif change == "revision":
            current["record_revision"] += 1
        elif change == "source":
            current["source_block_ids"] = ["replacement-block"]
        elif change == "retirement":
            replacement = copy.deepcopy(current)
            replacement["record_id"] = "replacement"
            # Actual structural replacement remains an intentional full write.
            saved(bid, [replacement, repo.get_record(bid, "r2")])
            return record
        current["reviewer_note"] = "Intervening decision"
        repo.update_record(bid, current)
        if change == "failure":
            raise ValueError("Provider unavailable")
        create_model_assertion(record, "speaker", "Model speaker", method="test")
        project_record_assertions(record)
        return record

    def committed(build_id, record_id, event):
        assert event == "record_completed"
        restarted = cb.PdfCorpusRepository(repo.root)
        assert restarted.get_record(build_id, record_id)["reviewer_note"] == "Intervening decision"
        events.append(record_id)

    saved = repo.save_records
    monkeypatch.setattr(manager, "_enrich_record", enrich)
    monkeypatch.setattr(reruns, "note_record_metadata", committed)
    forbid_replacement(monkeypatch, repo)
    manager._retry_metadata_worker(bid, {}, "retry-test", [0], {"r1": ["speaker"]})
    operation = repo.get_build(bid)["metadata_operation"]
    assert operation["state"] == "completed", operation.get("error")
    if change == "retirement":
        assert [row["record_id"] for row in repo.load_records(bid)] == ["replacement", "r2"]
        assert not events
        return
    saved_record = repo.get_record(bid, "r1")
    assert saved_record["reviewer_note"] == "Intervening decision"
    assert events == ["r1"]
    if change == "human":
        assert saved_record["speaker"] == "Reviewed speaker"
    elif change == "failure":
        assert saved_record["metadata_needs_attention"]
    else:
        assert saved_record.get("speaker") == original.get("speaker")


@pytest.mark.parametrize("change", ["human", "text", "revision", "source", "retirement", "failure"])
def test_rerun_completion_uses_one_current_row_without_full_reads(tmp_path, monkeypatch, change):
    manager, repo, bid = make_manager(tmp_path, [{"speaker": "Existing"}, {}])
    saved = repo.save_records
    loads = []
    load = repo.load_records

    def counted(build_id):
        loads.append(build_id)
        return load(build_id)

    def enrich(record, *args, **kwargs):
        current = repo.get_record(bid, "r1")
        if change == "human":
            create_human_assertion(current, "speaker", "Reviewed speaker", method="human")
            project_record_assertions(current)
        elif change == "text":
            current["text"] = "Corrected"
        elif change == "revision":
            current["record_revision"] = 2
        elif change == "source":
            current["source_block_ids"] = ["changed"]
        elif change == "retirement":
            saved(bid, [repo.get_record(bid, "r2")])
            return record
        repo.update_record(bid, current)
        if change == "failure":
            raise ValueError("Provider unavailable")
        return proposal(record, speaker=("Model speaker", 0.99))

    monkeypatch.setattr(manager, "_enrich_record", enrich)
    monkeypatch.setattr(repo, "load_records", counted)
    forbid_replacement(monkeypatch, repo)
    totals = manager._run_enrichment_pass(
        bid, {"record_ids": ["r1"]}, "run-test", "all", ["discourse"], lambda *args: None,
    )
    assert len(loads) == 1
    if change == "retirement":
        assert totals.get("records_processed", 0) == 0
        return
    current = repo.get_record(bid, "r1")
    if change == "human":
        assert current["speaker"] == "Reviewed speaker"
    elif change == "failure":
        assert totals["records_failed"] == 1
        assert current["metadata_enrichment_history"][-1]["state"] == "failed"
    else:
        assert totals["records_skipped"] == 1
        assert current["speaker"] == "Existing"
