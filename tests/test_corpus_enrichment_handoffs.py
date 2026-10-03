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

"""Transactional enrichment handoffs preserve current Records and bounded writes."""

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
from test_enrichment_cycles import make_manager, proposal
from test_review_queues import install_repo, ready_record


@pytest.fixture
def prepared(tmp_path):
    repo, build = install_repo(tmp_path, [ready_record("r1", "b1"), ready_record("r2", "b2")])
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


@pytest.mark.parametrize("failure", ["exception", "identity", "addition", "retirement", "reorder"])
def test_reconciliation_rolls_back_failed_or_topology_changing_callback(prepared, failure):
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
        repo.reconcile_records(bid, reconcile)
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
