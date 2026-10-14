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

"""Record-local vector reconciliation and durable invalidation."""

from __future__ import annotations

import copy
import json
import os
import platform
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from app import corpus_builder as cb
from app import metadata_exemplar_projection as projection
from app import source_block_index
from app.chroma_store import encode_metadata
from app.field_assertions import current_assertion_by_name
from app.metadata_exemplar_retrieval import ChromaMetadataExemplarIndex
from app.metadata_exemplars import reviewed_values
from app.persistence import SQLiteSystemRepository
from app.reviewer_context import current_reviewer
from test_metadata_exemplar_projection import FakeRepo, _patch_quiet
from test_progressive_metadata_retrieval import exemplar
from test_review_queues import install_repo, ready_record


def test_clean_exemplar_journal_reads_do_not_wait_for_writers(tmp_path, monkeypatch):
    repo, build = install_repo(tmp_path, [ready_record("r1", "b1")])
    bid = build["build_id"]
    expected = (
        repo.metadata_exemplar_dirty(bid),
        repo.metadata_exemplar_dirty_count(bid),
        repo.metadata_exemplar_state(bid),
    )

    def fail(*args, **kwargs):
        pytest.fail("clean journal read initialized or bootstrapped storage")

    monkeypatch.setattr(repo, "_initialize_records_db", fail)
    monkeypatch.setattr(repo, "_bootstrap_records_db", fail)

    def read():
        return (
            repo.metadata_exemplar_dirty(bid),
            repo.metadata_exemplar_dirty_count(bid),
            repo.metadata_exemplar_state(bid),
        )

    with sqlite3.connect(repo.build_records_db_path(bid)) as writer:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE metadata_exemplar_state SET epoch='uncommitted' WHERE singleton=1")
        with ThreadPoolExecutor(max_workers=1) as pool:
            with repo._lock:
                assert pool.submit(read).result(timeout=5) == expected
        writer.rollback()
    assert cb.PdfCorpusRepository(repo.root).metadata_exemplar_state(bid) == expected[2]


def test_exemplar_journal_read_bootstraps_legacy_jsonl_once(tmp_path):
    repo, build = install_repo(tmp_path, [ready_record("r1", "b1")])
    bid = build["build_id"]
    repo.build_records_db_path(bid).unlink()
    restarted = cb.PdfCorpusRepository(repo.root)
    assert restarted.metadata_exemplar_dirty_count(bid) >= 1
    assert restarted.metadata_exemplar_state(bid) == ("", "")
    assert restarted.get_record(bid, "r1")["text"] == ready_record("r1", "b1")["text"]


def test_exemplar_journal_missing_state_fails_visibly(tmp_path):
    repo, build = install_repo(tmp_path, [ready_record("r1", "b1")])
    bid = build["build_id"]
    repo.metadata_exemplar_state(bid)


def test_external_invalidation_cannot_be_acknowledged_with_old_token(tmp_path):
    repo, build = install_repo(tmp_path, [ready_record("r1", "b1")])
    bid = build["build_id"]
    stale_items = repo.metadata_exemplar_dirty(bid)
    assert stale_items
    external = cb.PdfCorpusRepository(repo.root)
    external.invalidate_metadata_exemplars(bid, schedule=False)
    assert repo.complete_metadata_exemplar_dirty(bid, stale_items) == 0
    current_items = external.metadata_exemplar_dirty(bid)
    assert current_items != stale_items
    assert external.complete_metadata_exemplar_dirty(bid, current_items) >= 1
    assert repo.metadata_exemplar_dirty_count(bid) == 0
    with sqlite3.connect(repo.build_records_db_path(bid)) as writer:
        writer.execute("DELETE FROM metadata_exemplar_state")
    with pytest.raises(RuntimeError, match="initialized state row"):
        repo.metadata_exemplar_state(bid)


class Collection:
    def __init__(self):
        self.metadata = {"derridai_exemplar_schema": 3, "derridai_exemplar_epoch": "epoch-1"}
        self.rows = {}
        self.documents = {}
        self.embeddings = {}
        self.queries = []
        self.returned_rows = 0

    def modify(self, *, metadata):
        self.metadata = metadata

    def get(self, *, where, include):
        self.queries.append(where)

        def matches(row, terms):
            if "$and" in terms:
                return all(matches(row, term) for term in terms["$and"])
            return all(
                row.get(key) in value["$in"] if isinstance(value, dict) else row.get(key) == value
                for key, value in terms.items()
            )

        ids = [key for key, row in self.rows.items() if matches(row, where)]
        self.returned_rows += len(ids)
        result = {"ids": ids, "metadatas": [self.rows[key] for key in ids]}
        if "documents" in include:
            result["documents"] = [self.documents[key] for key in ids]
        if "embeddings" in include:
            result["embeddings"] = [self.embeddings[key] for key in ids]
        return result

    def upsert(self, *, ids, documents, metadatas, embeddings):
        for key, document, metadata, vector in zip(ids, documents, metadatas, embeddings):
            self.rows[key] = metadata
            self.documents[key] = document
            self.embeddings[key] = vector

    def update(self, *, ids, metadatas):
        for key, row in zip(ids, metadatas):
            self.rows[key] = row

    def delete(self, *, ids):
        for key in ids:
            self.rows.pop(key, None)
            self.documents.pop(key, None)
            self.embeddings.pop(key, None)


class Store:
    def __init__(self):
        self.collection = Collection()
        self.client = self
        self.embedded = []
        self.fail = False

    def get_collection(self, *, name):
        return self.collection

    def upsert_many(self, name, records, *, document_field, id_field):
        if self.fail:
            raise RuntimeError("embedding unavailable")
        self.embedded.extend(records)
        for row in records:
            key = row[id_field]
            self.collection.rows[key] = encode_metadata(
                row, document_field=document_field, embedding_field="embedding",
            )
            self.collection.rows[key].update(_record_id=row["record_id"], _document_field="context_text")
            self.collection.documents[key] = row[document_field]
            self.collection.embeddings[key] = [1.0, 0.0]


def test_background_warning_holds_build_writer_lock_across_read_and_write(tmp_path, monkeypatch):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build = repo.create_build({"warnings": []})
    build_id = build["build_id"]
    captured = threading.Event()
    release = threading.Event()
    get_build = repo.get_build

    def paused_read(key):
        result = get_build(key)
        captured.set()
        assert release.wait(5)
        return result

    monkeypatch.setattr(repo, "get_build", paused_read)
    future = manager._executor.submit(manager._append_warning, build_id, "Index pending")
    try:
        assert captured.wait(5)
        acquired = repo._lock.acquire(blocking=False)
        if acquired:
            repo._lock.release()
        assert not acquired
    finally:
        release.set()
        future.result(timeout=5)
        monkeypatch.setattr(repo, "get_build", get_build)
        manager._executor.shutdown(wait=True)
    refreshed = repo.get_build(build_id)
    refreshed["boundary_review_count"] = 0
    repo.save_build(refreshed)
    assert repo.get_build(build_id)["warnings"] == ["Index pending"]
    assert repo.get_build(build_id)["boundary_review_count"] == 0


def test_reconciliation_is_record_scoped_and_reuses_unchanged_vectors():
    store = Store()
    index = ChromaMetadataExemplarIndex(store)
    one = exemplar("mex-one", "speaker", "Derrida", "Derrida speaks.")
    two = exemplar("mex-two", "speaker", "Levinas", "Levinas speaks.")
    index.reconcile_records("build-1", [one["record_id"], two["record_id"]], [one, two])
    index.reconcile_records("build-2", [one["record_id"]], [{**one, "metadata_exemplar_id": "other"}])
    store.embedded.clear()
    store.collection.queries.clear()

    stats = index.reconcile_records("build-1", [one["record_id"]], [one])

    assert stats["reused"] == 1
    assert stats["upserted"] == 0
    assert not store.embedded
    assert store.collection.queries == [
        {"$and": [{"scope_id": "build-1"}, {"record_id": {"$in": [one["record_id"]]}}]},
    ]
    index.reconcile_records("build-1", [one["record_id"]], [])
    assert set(store.collection.rows) == {"mex-two", "other"}


def test_changed_metadata_refreshes_without_embedding_and_changed_text_embeds():
    store = Store()
    index = ChromaMetadataExemplarIndex(store)
    row = exemplar("mex-one", "speaker", "Derrida", "Derrida speaks.")
    index.reconcile_records("build-1", [row["record_id"]], [row])
    store.embedded.clear()
    changed = {**row, "reviewed_values": {"position_holder": '"Levinas"'}}
    stats = index.reconcile_records("build-1", [row["record_id"]], [changed])
    assert stats["metadata_updated"] == 1
    assert not store.embedded
    changed["context_text"] = "New evidence context."
    stats = index.reconcile_records("build-1", [row["record_id"]], [changed])
    assert stats["upserted"] == 1
    assert len(store.embedded) == 1


def test_replacement_does_not_delete_old_rows_before_failed_embedding():
    store = Store()
    index = ChromaMetadataExemplarIndex(store)
    old = exemplar("mex-old", "speaker", "Derrida", "Derrida speaks.")
    index.reconcile_records("build-1", [old["record_id"]], [old])
    replacement = {**old, "metadata_exemplar_id": "mex-new", "record_revision": 3, "context_text": "changed"}
    store.fail = True
    with pytest.raises(RuntimeError, match="embedding unavailable"):
        index.reconcile_records("build-1", [old["record_id"]], [replacement])
    assert set(store.collection.rows) == {"mex-old"}
    store.fail = False
    index.reconcile_records("build-1", [old["record_id"]], [replacement])
    assert set(store.collection.rows) == {"mex-new"}


def test_selected_derivation_matches_full_and_never_loads_other_records(monkeypatch):
    _patch_quiet(monkeypatch)
    repo = FakeRepo()
    expected = projection.derive_build_metadata_exemplars(repo, "build-1")
    repo.get_records = lambda bid, ids: [
        copy.deepcopy(repo.records[0]) if rid == "r1" else None for rid in ids
    ]
    monkeypatch.setattr(repo, "load_records", lambda *args: pytest.fail("full corpus read"))
    assert projection.derive_record_metadata_exemplars(repo, "build-1", ["r1", "retired"]) == expected


@pytest.mark.parametrize("reviewer", ["", "alice", "bob"])
def test_shared_index_excludes_sealed_values_even_without_worker_reviewer_context(monkeypatch, reviewer):
    _patch_quiet(monkeypatch)
    repo = FakeRepo()
    repo.records[0]["second_opinion"] = {
        "position_holder": {"first_reviewer": "alice", "done": False},
    }
    token = current_reviewer.set(reviewer)
    try:
        assert projection.derive_build_metadata_exemplars(repo, "build-1") == []
        assert "position_holder" not in reviewed_values(repo.records[0])
        repo.records[0]["second_opinion"]["position_holder"]["done"] = True
        assert projection.derive_build_metadata_exemplars(repo, "build-1")
        assert reviewed_values(repo.records[0])["position_holder"] == '"Levinas"'
    finally:
        current_reviewer.reset(token)


@pytest.mark.parametrize(
    "authority,value_status",
    [("disputed", "present"), ("disputed", "confirmed_absent"), ("unreviewed", "confirmed_absent"),
     ("human_confirmed", "unresolved"), ("human_confirmed", "invalid")],
)
def test_shared_index_does_not_promote_unresolved_or_disputed_assertions(monkeypatch, authority, value_status):
    _patch_quiet(monkeypatch)
    repo = FakeRepo()
    assert projection.derive_build_metadata_exemplars(repo, "build-1")
    record = repo.records[0]
    current = current_assertion_by_name(record, "position_holder")
    assert current is not None
    for assertions in record["field_assertions"].values():
        for assertion in assertions:
            if assertion["assertion_id"] == current.assertion_id:
                assertion["authority_status"] = authority
                assertion["value_status"] = value_status
                if value_status == "confirmed_absent":
                    assertion["value"] = None
                for evidence in assertion["evidence"]:
                    evidence["reviewed_by"] = "human"
    assert projection.derive_build_metadata_exemplars(repo, "build-1") == []


def test_canonical_dirty_journal_survives_restart_and_does_not_ack_newer_edits(tmp_path):
    repo, build = install_repo(tmp_path, [ready_record("r1", "b1"), ready_record("r2", "b2")])
    bid = build["build_id"]
    initial = repo.metadata_exemplar_dirty(bid)
    repo.complete_metadata_exemplar_dirty(bid, initial)
    row = repo.get_record(bid, "r1")
    row["record_revision"] = 2
    repo.update_record(bid, row)
    captured = repo.metadata_exemplar_dirty(bid)
    assert {item["record_id"] for item in captured} == {"r1"}
    row["record_revision"] = 3
    repo.update_record(bid, row)
    restarted = type(repo)(repo.root)
    restarted.complete_metadata_exemplar_dirty(bid, captured)
    assert {item["record_id"] for item in restarted.metadata_exemplar_dirty(bid)} == {"r1"}
    assert restarted.get_record(bid, "r1")["record_revision"] == 3


def test_worker_checkpoint_only_does_not_dirty_exemplars(tmp_path):
    repo, build = install_repo(tmp_path, [ready_record("r1", "b1")])
    bid = build["build_id"]
    repo.complete_metadata_exemplar_dirty(bid, repo.metadata_exemplar_dirty(bid))
    row = repo.get_record(bid, "r1")
    row["metadata_enrichment_state"] = "running"
    repo.update_record(bid, row)
    assert repo.metadata_exemplar_dirty(bid) == []


def reviewed_record(record_id, block_id):
    row = ready_record(record_id, block_id)
    row.update(position_holder="Levinas", human_touched_at="2026-10-02T12:00:00Z")
    row["metadata_field_status"]["position_holder"] = {"status": "human_confirmed", "method": "human"}
    row["metadata_evidence"] = {
        "position_holder": {"block_ids": [block_id], "reviewed_by": "human", "confidence": 1.0},
    }
    return row


@pytest.fixture
def projected_corpus(tmp_path, monkeypatch):
    _patch_quiet(monkeypatch)
    system = SQLiteSystemRepository(tmp_path / "system.sqlite")
    monkeypatch.setattr(projection, "system_store", system)
    repo, build = install_repo(tmp_path, [reviewed_record("r1", "b1"), reviewed_record("r2", "b2")])
    store = Store()
    index = ChromaMetadataExemplarIndex(store)
    projection.project_build_metadata_exemplars(repo, build["build_id"], index)
    store.embedded.clear()
    store.collection.queries.clear()
    return repo, build["build_id"], store, index, system


def test_post_edit_projects_only_selected_record_and_reuses_revision_vector(projected_corpus, monkeypatch):
    repo, bid, store, index, system = projected_corpus
    other = {key: copy.deepcopy(row) for key, row in store.collection.rows.items() if row["record_id"] == "r2"}
    row = repo.get_record(bid, "r1")
    row["record_revision"] += 1
    repo.update_record(bid, row)
    system.mark_semantic_memory_dirty(projection.PROJECTION, scope_id=bid, record_id="r1")
    monkeypatch.setattr(repo, "load_records", lambda *args: pytest.fail("ordinary edit loaded corpus"))
    result = projection.project_build_metadata_exemplars(repo, bid, index)
    assert result["mode"] == "incremental"
    assert result["records"] == 1
    assert result["embedded"] == 0
    assert result["vector_reused"] == 1
    assert not store.embedded
    assert not result["pending"]
    assert all(store.collection.rows[key] == value for key, value in other.items())
    assert repo.metadata_exemplar_dirty(bid) == []
    assert system.list_semantic_memory_dirty(projection.PROJECTION) == []


def test_retirement_and_repair_match_full_authoritative_derivation(projected_corpus):
    repo, bid, store, index, _ = projected_corpus
    repo.save_records(bid, [repo.get_record(bid, "r2")])
    result = projection.project_build_metadata_exemplars(repo, bid, index)
    assert result["mode"] == "rebuild"
    assert {row["record_id"] for row in store.collection.rows.values()} == {"r2"}
    assert len(store.collection.rows) == len(projection.derive_build_metadata_exemplars(repo, bid))


def test_edit_during_full_rebuild_remains_dirty_and_retry_converges(projected_corpus, monkeypatch):
    repo, bid, store, index, _ = projected_corpus
    repo.invalidate_metadata_exemplars(bid)
    original = index.rebuild_scope

    def raced(scope, exemplars):
        row = repo.get_record(bid, "r1")
        row["record_revision"] += 1
        repo.update_record(bid, row)
        return original(scope, exemplars)

    monkeypatch.setattr(index, "rebuild_scope", raced)
    result = projection.project_build_metadata_exemplars(repo, bid, index)
    assert result["pending"]
    assert any(not item["record_id"] for item in repo.metadata_exemplar_dirty(bid))
    monkeypatch.setattr(index, "rebuild_scope", original)
    assert not projection.project_build_metadata_exemplars(repo, bid, index)["pending"]
    expected = {row["metadata_exemplar_id"] for row in projection.derive_build_metadata_exemplars(repo, bid)}
    assert set(store.collection.rows) == expected


def test_new_outbox_event_during_projection_is_not_acknowledged(projected_corpus, monkeypatch):
    repo, bid, _, index, system = projected_corpus
    old = system.mark_semantic_memory_dirty(projection.PROJECTION, scope_id=bid, record_id="r1")
    original = index.reconcile_records
    newer = []

    def raced(*args):
        newer.append(system.mark_semantic_memory_dirty(projection.PROJECTION, scope_id=bid, record_id="r1"))
        return original(*args)

    monkeypatch.setattr(index, "reconcile_records", raced)
    assert projection.project_build_metadata_exemplars(repo, bid, index)["pending"]
    pending = {row["item_id"] for row in system.list_semantic_memory_dirty(projection.PROJECTION)}
    assert old not in pending
    assert pending == set(newer)


def test_collection_epoch_change_rebuilds_even_without_a_new_review(projected_corpus):
    repo, bid, store, index, _ = projected_corpus
    store.collection.rows.clear()
    store.collection.metadata["derridai_exemplar_epoch"] = "replacement"
    result = projection.project_build_metadata_exemplars(repo, bid, index)
    assert result["mode"] == "rebuild"
    assert len(store.collection.rows) == 2
    assert repo.metadata_exemplar_state(bid)[0] == "replacement"


def test_failed_clean_index_check_leaves_recoverable_pending_work(projected_corpus, monkeypatch):
    repo, bid, _, index, _ = projected_corpus

    def unavailable():
        raise RuntimeError("collection unavailable")

    monkeypatch.setattr(index, "collection_epoch", unavailable)
    with pytest.raises(RuntimeError, match="collection unavailable"):
        projection.project_build_metadata_exemplars(repo, bid, index)
    assert any(not item["record_id"] for item in repo.metadata_exemplar_dirty(bid))


def test_memory_reset_and_reviewed_aliases_invalidate_complete_scope(projected_corpus):
    from app.semantic_identity_store import create_alias_set

    repo, bid, store, index, _ = projected_corpus
    create_alias_set(repo, bid, kind="person", canonical_label="Levinas", aliases=["E. Levinas"])
    assert any(not item["record_id"] for item in repo.metadata_exemplar_dirty(bid))
    projection.project_build_metadata_exemplars(repo, bid, index)
    build = repo.get_build(bid)
    build["editorial_memory_reset_at"] = "2026-10-03T00:00:00Z"
    repo.save_build(build)
    assert projection.project_build_metadata_exemplars(repo, bid, index)["mode"] == "rebuild"
    assert not store.collection.rows


def test_failed_projection_keeps_canonical_work_for_restart(projected_corpus):
    repo, bid, store, index, _ = projected_corpus
    row = repo.get_record(bid, "r1")
    row["text"] = "Changed authoritative text."
    repo.update_record(bid, row)
    original = store.collection.update
    store.collection.update = lambda **kw: (_ for _ in ()).throw(RuntimeError("vector down"))
    # Changing an existing ID's reviewed metadata also requires an index update.
    row["language"] = "fr"
    repo.update_record(bid, row)
    with pytest.raises(RuntimeError, match="vector down"):
        projection.project_build_metadata_exemplars(repo, bid, index)
    restarted = type(repo)(repo.root)
    assert restarted.metadata_exemplar_dirty(bid)
    assert restarted.get_record(bid, "r1")["text"] == row["text"]
    store.collection.update = original
    assert not projection.project_build_metadata_exemplars(restarted, bid, index)["pending"]


def test_outbox_scope_filter_and_legacy_resolution_do_not_starve(projected_corpus):
    repo, bid, _, index, system = projected_corpus
    for _ in range(101):
        system.mark_semantic_memory_dirty(projection.PROJECTION, record_id="unknown")
    for _ in range(1001):
        system.mark_semantic_memory_dirty(projection.PROJECTION, scope_id="another-build", record_id="elsewhere")
    legacy = system.mark_semantic_memory_dirty(projection.PROJECTION, record_id="r1")
    result = projection.project_build_metadata_exemplars(repo, bid, index)
    assert result["acknowledged"] == 1
    assert result["records"] == 1
    assert not result["pending"]
    assert all(row["item_id"] != legacy for row in system.list_semantic_memory_dirty(projection.PROJECTION, scope_id=bid))
    assert sum(row["dirty"] for row in system.semantic_memory_dirty_summary(projection.PROJECTION)) == 1102


def test_binding_and_outbox_are_rolled_back_together(tmp_path):
    import sqlite3

    path = tmp_path / "system.sqlite"
    repository = SQLiteSystemRepository(path)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TRIGGER refuse_outbox BEFORE INSERT ON semantic_memory_outbox "
            "BEGIN SELECT RAISE(ABORT,'outbox unavailable'); END",
        )
    with pytest.raises(sqlite3.IntegrityError, match="outbox unavailable"):
        repository.put_memory_binding(
            {"binding_id": "binding-1", "record_id": "r1", "field_id": "core.speaker"},
            enqueue_projection=True,
        )
    assert repository.list_memory_bindings() == []


def test_scheduling_coalesces_requests_and_reschedules_newer_work():
    manager = object.__new__(cb.PdfCorpusBuildManager)
    manager._metadata_schedule_lock = threading.RLock()
    manager._metadata_scheduled = set()
    manager._metadata_reschedule = set()
    tasks = []

    class Executor:
        def submit(self, operation, *args):
            tasks.append((operation, args))

    manager._executor = Executor()
    manager._project_metadata_exemplars_best_effort = lambda bid: {"pending": False}
    manager._schedule_metadata_exemplar_projection("build-1")
    for _ in range(50):
        manager._schedule_metadata_exemplar_projection("build-1")
    assert len(tasks) == 1
    operation, args = tasks.pop()
    operation(*args)
    assert len(tasks) == 1
    operation, args = tasks.pop()
    operation(*args)
    assert not manager._metadata_scheduled


def test_scheduling_failure_does_not_spin_or_block_review():
    manager = object.__new__(cb.PdfCorpusBuildManager)
    manager._metadata_schedule_lock = threading.RLock()
    manager._metadata_scheduled = set()
    manager._metadata_reschedule = set()
    tasks = []

    class Executor:
        def submit(self, operation, *args):
            tasks.append((operation, args))

    manager._executor = Executor()
    manager._project_metadata_exemplars_best_effort = lambda bid: {"error": "vector unavailable"}
    manager._schedule_metadata_exemplar_projection("build-1")
    manager._schedule_metadata_exemplar_projection("build-1")
    operation, args = tasks.pop()
    operation(*args)
    assert tasks == []
    assert not manager._metadata_scheduled


def _measure_source_block_reads(repo, monkeypatch, counters):
    """Count file-level JSONL loads, including asset-quality reads inside load_blocks."""
    original = repo._load_block_rows

    def measured(asset_id):
        path = repo.asset_blocks_path(asset_id)
        byte_count = path.stat().st_size if path.exists() else 0
        started = time.perf_counter()
        rows = original(asset_id)
        counters["source_read_seconds"] += time.perf_counter() - started
        counters["source_read_calls"] += 1
        counters["source_rows_read"] += len(rows)
        counters["source_bytes_read"] += byte_count
        return rows

    monkeypatch.setattr(repo, "_load_block_rows", measured)
    indexed_read = source_block_index._read_indexed_block

    def measured_indexed(handle, offset, length):
        result = indexed_read(handle, offset, length)
        if Path(handle.name) == repo.asset_blocks_path("a"):
            counters["source_rows_read"] += 1
            counters["source_bytes_read"] += length
        return result

    monkeypatch.setattr(source_block_index, "_read_indexed_block", measured_indexed)
    selected = repo.load_selected_blocks

    def measured_selected(asset_id, block_ids):
        started = time.perf_counter()
        rows = selected(asset_id, block_ids)
        counters["source_read_seconds"] += time.perf_counter() - started
        counters["source_read_calls"] += 1
        return rows

    monkeypatch.setattr(repo, "load_selected_blocks", measured_selected)


@pytest.mark.parametrize("size", [10, 100])
def test_single_record_projection_reads_only_record_blocks(tmp_path, monkeypatch, size):
    _patch_quiet(monkeypatch)
    monkeypatch.setattr(projection, "system_store", SQLiteSystemRepository(tmp_path / "system.sqlite"))
    rows = [reviewed_record(f"r{i}", f"b{i + 1}") for i in range(size)]
    repo, build = install_repo(tmp_path, rows)
    bid = build["build_id"]
    # Settle asset-quality initialization before measuring the warm read path.
    repo.load_blocks("a")
    expected = [row for row in projection.derive_build_metadata_exemplars(repo, bid) if row["record_id"] == "r0"]
    repo.load_selected_blocks("a", ["b1"])
    counters = dict(source_read_seconds=0.0, source_read_calls=0, source_rows_read=0, source_bytes_read=0)
    _measure_source_block_reads(repo, monkeypatch, counters)

    actual = projection.derive_record_metadata_exemplars(repo, bid, ["r0"])

    assert actual == expected
    assert actual
    assert {row["record_id"] for row in actual} == {"r0"}
    assert counters["source_read_calls"] == 1
    assert counters["source_rows_read"] == 1
    assert counters["source_bytes_read"] < repo.asset_blocks_path("a").stat().st_size
    assert counters["source_read_seconds"] >= 0
    assert set(counters) == {
        "source_read_seconds", "source_read_calls", "source_rows_read", "source_bytes_read",
    }


def test_selected_projection_preserves_context_and_page_label_updates(tmp_path, monkeypatch):
    _patch_quiet(monkeypatch)
    monkeypatch.setattr(projection, "system_store", SQLiteSystemRepository(tmp_path / "system.sqlite"))
    row = reviewed_record("r0", "b2")
    row["source_block_ids"] = ["b1", "b2", "b3"]
    rows = [row, reviewed_record("r1", "b2"), reviewed_record("r2", "b3")]
    repo, build = install_repo(tmp_path, rows)
    bid = build["build_id"]
    asset = cb._json_read(repo.asset_meta_path("a"))
    asset["pages"] = [{"pdf_page": 1}]
    cb._json_write(repo.asset_meta_path("a"), asset)
    expected = [item for item in projection.derive_build_metadata_exemplars(repo, bid) if item["record_id"] == "r0"]
    assert projection.derive_record_metadata_exemplars(repo, bid, ["r0"]) == expected
    assert "text 1" in expected[0]["context_text"] and "text 3" in expected[0]["context_text"]
    repo.update_page_labels("a", {1: "iv"})
    expected = [item for item in projection.derive_build_metadata_exemplars(repo, bid) if item["record_id"] == "r0"]
    assert projection.derive_record_metadata_exemplars(repo, bid, ["r0"]) == expected
    assert repo.load_selected_blocks("a", ["b2"])[0]["printed_page_label"] == "iv"


@pytest.mark.parametrize("size", [1000, 10000])
@pytest.mark.parametrize("build_count", [1, 2])
def test_incremental_exemplar_repository_benchmark(tmp_path, monkeypatch, size, build_count):
    output = os.getenv("CORPUS_EXEMPLAR_BENCHMARK")
    if not output:
        pytest.skip("opt-in repository exemplar benchmark")
    _patch_quiet(monkeypatch)
    monkeypatch.setattr(projection, "system_store", SQLiteSystemRepository(tmp_path / "system.sqlite"))
    builds = []
    for number in range(build_count):
        rows = [reviewed_record(f"build{number}-r{i}", f"b{i + 1}") for i in range(size)]
        repo, build = install_repo(tmp_path / str(number), rows)
        builds.append((repo, build["build_id"]))
    store = Store()
    index = ChromaMetadataExemplarIndex(store)
    source_index_initialization_seconds = 0.0
    for repo, bid in builds:
        projection.project_build_metadata_exemplars(repo, bid, index)
        started_index = time.perf_counter()
        repo.load_selected_blocks("a", ["b1"])
        source_index_initialization_seconds += time.perf_counter() - started_index

    counters = {"decoded": 0, "source_load_seconds": 0.0}
    for repo, _ in builds:
        _measure_source_block_reads(repo, monkeypatch, counters)
        decode = repo._decode_migrated
        load_blocks = repo.load_blocks

        def measured_decode(*args, original=decode):
            counters["decoded"] += 1
            return original(*args)

        def measured_blocks(*args, original=load_blocks):
            started = time.perf_counter()
            result = original(*args)
            counters["source_load_seconds"] += time.perf_counter() - started
            return result

        monkeypatch.setattr(repo, "_decode_migrated", measured_decode)
        monkeypatch.setattr(repo, "load_blocks", measured_blocks)
        load_selected = repo.load_selected_blocks

        def measured_selection(*args, original=load_selected):
            started = time.perf_counter()
            result = original(*args)
            counters["source_load_seconds"] += time.perf_counter() - started
            return result

        monkeypatch.setattr(repo, "load_selected_blocks", measured_selection)
    for sample in range(3):
        for mode in ("rebuild", "incremental"):
            for pattern in ("single", "coalesced"):
                counters.update(
                    decoded=0, source_load_seconds=0.0, source_read_seconds=0.0,
                    source_read_calls=0, source_rows_read=0, source_bytes_read=0,
                )
                store.embedded.clear()
                store.collection.returned_rows = 0
                save_seconds = 0.0
                stats = []
                unchanged = {}
                changed_ids = {}
                for number, (_, bid) in enumerate(builds):
                    ids = [f"build{number}-r0"] if pattern == "single" else [f"build{number}-r{i}" for i in range(5)]
                    changed_ids[bid] = ids
                    unchanged[bid] = {
                        key: row for key, row in store.collection.rows.items()
                        if row["scope_id"] == bid and row["record_id"] not in ids
                    }
                started = time.perf_counter()
                for number, (repo, bid) in enumerate(builds):
                    ids = [f"build{number}-r0"] if pattern == "single" else [f"build{number}-r{i}" for i in range(5)]
                    saved = time.perf_counter()
                    for rid in ids:
                        for _ in range(1 if pattern == "single" else 3):
                            row = repo.get_record(bid, rid)
                            row["record_revision"] += 1
                            repo.update_record(bid, row)
                    save_seconds += time.perf_counter() - saved
                    stats.append(projection.project_build_metadata_exemplars(repo, bid, index, force=mode == "rebuild"))
                elapsed = time.perf_counter() - started
                expected_reads = build_count * (1 if pattern == "single" else 15)
                affected = build_count * (1 if pattern == "single" else 5)
                assert counters["decoded"] == expected_reads + (size * build_count if mode == "rebuild" else affected)
                assert len(store.embedded) == (size * build_count if mode == "rebuild" else 0)
                if mode == "incremental":
                    assert sum(item["vector_reused"] for item in stats) == affected
                    assert store.collection.returned_rows == affected
                source_load_seconds = counters["source_load_seconds"]
                source_reads = {
                    key: counters[key] for key in (
                        "source_read_seconds", "source_read_calls", "source_rows_read", "source_bytes_read",
                    )
                }
                assert source_reads["source_read_calls"] >= build_count
                assert source_reads["source_rows_read"] == (size * build_count if mode == "rebuild" else affected)
                # Check the complete changed set and preserve every unaffected row
                # outside the timed/counted workload.
                for repo, bid in builds:
                    expected = {
                        row["metadata_exemplar_id"] for row in projection.derive_record_metadata_exemplars(
                            repo, bid, changed_ids[bid],
                        )
                    }
                    actual = {
                        key for key, row in store.collection.rows.items()
                        if row["scope_id"] == bid and row["record_id"] in changed_ids[bid]
                    }
                    assert actual == expected
                    assert all(store.collection.rows[key] == row for key, row in unchanged[bid].items())
                    assert sum(row["scope_id"] == bid for row in store.collection.rows.values()) == size
                    assert not repo.metadata_exemplar_dirty(bid)
                result = {
                    "records_per_build": size, "builds": build_count, "sample": sample,
                    "mode": mode, "pattern": pattern, "elapsed_seconds": elapsed,
                    "save_seconds": save_seconds, "decoded": expected_reads + (size * build_count if mode == "rebuild" else affected),
                    "source_load_seconds": source_load_seconds,
                    **source_reads,
                    "benchmark_contract": "corpus-exemplar-repository-v3",
                    "source_index_initialization_seconds": source_index_initialization_seconds,
                    "cache_state": "warm application state; OS filesystem cache uncontrolled",
                    "embedding_documents": len(store.embedded),
                    "vector_rows_read": store.collection.returned_rows,
                    "vector_rows_written": sum(item["upserted"] for item in stats),
                    "vector_rows_deleted": sum(item["deleted"] for item in stats),
                    "python": platform.python_version(), "platform": platform.platform(),
                    "vector_backend": "in-memory double; no real embeddings",
                }
                with Path(output).open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(result) + "\n")
    for repo, bid in builds:
        expected = {row["metadata_exemplar_id"] for row in projection.derive_build_metadata_exemplars(repo, bid)}
        assert {key for key, row in store.collection.rows.items() if row["scope_id"] == bid} == expected
