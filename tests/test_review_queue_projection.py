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

"""Persistent queue reads preserve selection semantics without decoding the corpus."""
from __future__ import annotations

import copy
import itertools
import json
import os
import platform
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

import pytest
from test_review_queues import cb, install_repo, ready_record

# isort: split
# The fixture module sets api on sys.path before importing the application.
from app import corpus_queue_projection
from app import corpus_review_queue as queue
from app.corpus_reviewer_helpers import _present_for_reviewer
from app.metadata_schema import default_schema
from app.reviewer_context import current_reviewer


@pytest.fixture
def corpus(tmp_path):
    records = [ready_record(f"r{i}", f"b{i}") for i in range(6)]
    records[1].update(review_disposition="accepted", accepted=True)
    records[2].update(metadata_complete=False, metadata_incomplete_fields=["speaker"])
    records[3].update(source_quality_issues=["unreadable"])
    records[4].update(metadata_enrichment_state="running")
    records[5].update(review_disposition="rejected", rejected=True)
    records[0].update(speaker="Sealed answer", second_opinion={"speaker": {"first_reviewer": "alice", "done": False}})
    return install_repo(tmp_path, records)


def test_projection_matches_pure_selection_for_filter_combinations(corpus):
    repo, build = corpus
    bid = build["build_id"]
    records = repo.load_records(bid)
    for disposition, review_queue, query in itertools.product(
        (None, "pending", "accepted", "rejected"),
        (None, "ready", "issues", "metadata", "source", "topology", "preparing"),
        ("", "ÉDOUARD", "%_", '"record_id": "r0"'),
    ):
        filters = queue.QueueFilter(disposition=disposition, review_queue=review_queue, query=query)
        expected = queue.select_queue(records, filters, offset=0, limit=3)
        actual = repo.page_records(bid, offset=0, limit=3, **filters.__dict__)
        assert [r["record_id"] for r in actual["items"]] == [r["record_id"] for r in expected.items]
        assert actual["total"] == expected.total
        assert actual["queue_counts"] == expected.queue_counts


def test_cold_and_post_edit_pages_and_facets_do_not_load_corpus(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    repo = cb.PdfCorpusRepository(repo.root)
    def fail(*args, **kwargs):
        pytest.fail("queue read loaded the entire corpus")
    monkeypatch.setattr(repo, "load_records", fail)
    monkeypatch.setattr(repo, "review_records", fail)
    decoded = []
    original_decode = repo._decode_migrated
    def decode(payload, *args):
        decoded.append(payload)
        return original_decode(payload, *args)
    monkeypatch.setattr(repo, "_decode_migrated", decode)
    first = repo.page_records(bid, limit=1)
    assert len(decoded) == 1
    changed = repo.get_record(bid, "r1")
    changed.update(review_disposition="pending", accepted=False, speaker="New facet")
    repo.update_record(bid, changed)
    second = repo.page_records(bid, limit=1)
    assert second["queue_counts"]["accepted"] == 0
    assert "New facet" in second["metadata_values"]["speaker"]
    assert second["data_generation"] > first["data_generation"]
    assert second["topology_generation"] == first["topology_generation"]

def test_clean_review_reads_do_not_initialize_or_reserve_a_writer(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    original = repo.get_records(bid, ["r1"], include_queue_version=True)[0]
    repo.page_records(bid, limit=1)

    def fail(*args, **kwargs):
        pytest.fail("clean review read attempted initialization or projection repair")

    monkeypatch.setattr(repo, "_initialize_records_db", fail)
    monkeypatch.setattr(repo, "_ensure_review_projection", fail)
    with sqlite3.connect(repo.build_records_db_path(bid)) as writer:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE corpus_records SET payload=payload WHERE record_id='r1'")
        actual = repo.get_records(bid, ["r1"], include_queue_version=True)[0]
        assert actual == original
        assert repo.page_records(bid, limit=1)["items"]
        assert repo.review_metadata_facets(bid)
        assert repo.review_build_aggregates(bid, automation_running=False)
        counts, next_record = repo.review_queue_summary(bid, "r0")
        assert counts == repo.page_records(bid, limit=0)["queue_counts"]
        assert next_record is not None
        writer.rollback()


def test_queue_summary_decodes_after_snapshot_and_preserves_counts(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    expected_counts, expected_record = repo.review_queue_summary(bid, "r0")
    assert expected_record is not None
    original_decode = repo._decode_migrated
    decoded = []

    def decode(payload, schema, signature):
        # Committing here would block if summary presentation still held a read transaction.
        with sqlite3.connect(repo.build_records_db_path(bid), timeout=1) as writer:
            writer.execute("BEGIN IMMEDIATE")
            writer.execute("UPDATE corpus_records SET payload=payload WHERE record_id=?", (expected_record["record_id"],))
        decoded.append(payload)
        return original_decode(payload, schema, signature)

    monkeypatch.setattr(repo, "_decode_migrated", decode)
    counts, record = repo.review_queue_summary(bid, "r0")
    assert counts == expected_counts
    assert record == expected_record
    assert len(decoded) == 1


def test_raw_record_reads_do_not_wait_for_repository_or_sqlite_writer(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    expected_rows = repo.load_records(bid)
    expected_context = repo.record_context(bid, "r2", before=1, after=1, max_chars=12)

    def fail(*args, **kwargs):
        pytest.fail("raw snapshot attempted bootstrap, initialization or projection repair")

    monkeypatch.setattr(repo, "_bootstrap_records_db", fail)
    monkeypatch.setattr(repo, "_initialize_records_db", fail)
    monkeypatch.setattr(repo, "_ensure_review_projection", fail)
    with sqlite3.connect(repo.build_records_db_path(bid)) as writer:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE corpus_records SET payload=payload WHERE record_id='r2'")
        with ThreadPoolExecutor(max_workers=1) as pool:
            with repo._lock:
                assert pool.submit(repo.load_records, bid).result(timeout=5) == expected_rows
                assert pool.submit(
                    repo.record_context, bid, "r2", before=1, after=1, max_chars=12,
                ).result(timeout=5) == expected_context
        writer.rollback()
    assert len(expected_context["before"]) == len(expected_context["after"]) == 1
    assert sum(len(item["text"]) for side in ("before", "after") for item in expected_context[side]) == 12
    assert expected_context["truncated"]


def test_full_record_decoding_releases_snapshot_and_keeps_captured_payloads(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    expected = repo.load_records(bid)
    original = repo._decode_migrated
    committed = False

    def decode(payload, schema, signature):
        nonlocal committed
        if not committed:
            committed = True
            with sqlite3.connect(repo.build_records_db_path(bid), timeout=1) as writer:
                writer.execute("BEGIN IMMEDIATE")
                changed = {**expected[-1], "text": "Committed while decoding"}
                writer.execute(
                    "UPDATE corpus_records SET payload=? WHERE record_id=?",
                    (json.dumps(changed), changed["record_id"]),
                )
        return original(payload, schema, signature)

    monkeypatch.setattr(repo, "_decode_migrated", decode)
    assert repo.load_records(bid) == expected
    assert committed
    assert cb.PdfCorpusRepository(repo.root).load_records(bid)[-1]["text"] == "Committed while decoding"


def test_projection_refresh_rejects_external_write_and_recovers(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    external = cb.PdfCorpusRepository(repo.root)
    replace = cb.os.replace
    raced = False

    def racing_replace(source, target):
        nonlocal raced
        replace(source, target)
        if Path(target) == repo.build_records_path(bid) and not raced:
            raced = True
            record = external.get_record(bid, "r1")
            external.update_record(bid, {**record, "text": "New canonical text"})

    monkeypatch.setattr(cb.os, "replace", racing_replace)
    with pytest.raises(cb.RecordStateConflict, match="refreshing JSONL"):
        repo.refresh_records_projection(bid)
    assert raced
    assert external.records_projection_dirty(bid)
    repo.refresh_records_projection(bid)
    assert not external.records_projection_dirty(bid)
    published = [json.loads(line) for line in repo.build_records_path(bid).read_text().splitlines()]
    assert published == external.load_records(bid)


def test_projection_replace_failure_remains_dirty_and_preserves_previous_file(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    original_bytes = repo.build_records_path(bid).read_bytes()
    replace = cb.os.replace

    def failing_replace(source, target):
        if Path(target) == repo.build_records_path(bid):
            raise OSError("Projection replacement failed")
        return replace(source, target)

    monkeypatch.setattr(cb.os, "replace", failing_replace)
    with pytest.raises(OSError, match="replacement failed"):
        repo.refresh_records_projection(bid)
    assert repo.build_records_path(bid).read_bytes() == original_bytes
    assert cb.PdfCorpusRepository(repo.root).records_projection_dirty(bid)
    assert not list(repo.build_records_path(bid).parent.glob(".records.jsonl.*.tmp"))


def test_concurrent_cold_raw_reads_bootstrap_once(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    expected = repo.load_records(bid)
    repo.build_records_db_path(bid).unlink()
    restarted = cb.PdfCorpusRepository(repo.root)
    initialize = restarted._initialize_records_db
    initialized = []

    def counted(connection):
        initialized.append(True)
        return initialize(connection)

    monkeypatch.setattr(restarted, "_initialize_records_db", counted)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(restarted.load_records, bid) for _ in range(4)]
        assert all(future.result(timeout=10) == expected for future in futures)
    assert len(initialized) == 1


def test_neighbour_snapshot_preserves_topology_during_external_reorder(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    with repo._records_db(bid) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
    expected = repo.record_context(bid, "r2", before=1, after=1)
    original_db = repo._record_store_read_db

    @contextmanager
    def reordered_snapshot(build_id):
        with original_db(build_id) as connection:
            connection.execute("SELECT ordinal FROM corpus_records WHERE record_id='r2'").fetchone()
            with sqlite3.connect(repo.build_records_db_path(bid)) as writer:
                writer.execute("UPDATE corpus_records SET ordinal=100-ordinal")
            yield connection

    monkeypatch.setattr(repo, "_record_store_read_db", reordered_snapshot)
    assert repo.record_context(bid, "r2", before=1, after=1) == expected
    assert cb.PdfCorpusRepository(repo.root).record_context(bid, "r2", before=1, after=1) != expected


@pytest.mark.parametrize("review_queue", [None, "ready", "issues", "metadata", "source", "topology", "preparing"])
@pytest.mark.parametrize("reviewer", ["", "alice", "bob"])
def test_queue_summary_matches_snapshot_selection_without_repository_lock(corpus, review_queue, reviewer):
    repo, build = corpus
    bid = build["build_id"]
    token = current_reviewer.set(reviewer)
    try:
        with repo._review_read_db(bid) as (connection, _schema, _signature):
            expected_id = corpus_queue_projection.next_pending(connection, "r5", review_queue)
        expected_counts = repo.page_records(bid, limit=0)["queue_counts"]

        def read():
            thread_token = current_reviewer.set(reviewer)
            try:
                return repo.review_queue_summary(bid, "r5", review_queue)
            finally:
                current_reviewer.reset(thread_token)

        with ThreadPoolExecutor(max_workers=1) as pool:
            with repo._lock:
                counts, record = pool.submit(read).result(timeout=5)
        assert counts == expected_counts
        assert (record["record_id"] if record else None) == expected_id
        if record and record["record_id"] == "r0" and reviewer == "bob":
            assert record.get("speaker") != "Sealed answer"
    finally:
        current_reviewer.reset(token)


def test_schema_snapshot_does_not_wait_for_repository_writer(corpus):
    repo, build = corpus
    bid = build["build_id"]
    build["schema"] = default_schema().model_dump(mode="json")
    repo.save_build(build)
    expected = repo._record_schema(bid)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with repo._lock:
            # The outer executor ensures a failure releases the writer lock
            # before joining the blocked reader.
            schema = pool.submit(repo._record_schema, bid).result(timeout=5)
    assert schema == expected
    assert schema is not None


@pytest.mark.parametrize("failure", ["missing", "conflict", "marker"])
def test_rejected_targeted_write_preserves_clean_projection(corpus, monkeypatch, failure):
    repo, build = corpus
    bid = build["build_id"]
    before = repo.get_records(bid, ["r1"], include_queue_version=True)[0]
    before_build = repo.get_build(bid)
    candidate = {**before, "text": "Must not be committed"}
    version = before["queue_state_version"]
    if failure == "missing":
        candidate["record_id"] = "retired"
        expected_error = KeyError
    elif failure == "conflict":
        version -= 1
        expected_error = cb.RecordStateConflict
    else:
        expected_error = OSError

    def marker(*args, **kwargs):
        if failure == "marker":
            raise OSError("Dirty marker persistence failed")
        pytest.fail("rejected write persisted a dirty marker")

    monkeypatch.setattr(repo, "_set_records_projection_state", marker)
    monkeypatch.setattr(repo, "_notify_metadata_projection", lambda *_: pytest.fail("rejected write notified projection"))
    with pytest.raises(expected_error):
        repo.update_record(bid, candidate, expected_queue_version=version)
    restarted = cb.PdfCorpusRepository(repo.root)
    assert restarted.get_records(bid, ["r1"], include_queue_version=True)[0] == before
    assert restarted.get_build(bid) == before_build
    assert not restarted.records_projection_dirty(bid)


def test_failed_targeted_transaction_retains_dirty_marker_without_partial_record(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    before = repo.get_records(bid, ["r1"], include_queue_version=True)[0]

    original_update = cb.corpus_queue_projection.update_rows

    def fail_queue_update(connection, rows, **kwargs):
        if not rows:
            return original_update(connection, rows, **kwargs)
        assert repo.records_projection_dirty(bid)
        raise RuntimeError("Queue projection failed")

    monkeypatch.setattr(cb.corpus_queue_projection, "update_rows", fail_queue_update)
    monkeypatch.setattr(repo, "_notify_metadata_projection", lambda *_: pytest.fail("failed transaction notified projection"))
    with pytest.raises(RuntimeError, match="Queue projection failed"):
        repo.update_record(
            bid, {**before, "text": "Must roll back"},
            expected_queue_version=before["queue_state_version"],
        )
    restarted = cb.PdfCorpusRepository(repo.root)
    assert restarted.get_records(bid, ["r1"], include_queue_version=True)[0] == before
    assert restarted.records_projection_dirty(bid)


def test_clean_selected_reads_do_not_wait_for_repository_coordination(corpus):
    repo, build = corpus
    bid = build["build_id"]
    repo.get_records(bid, ["r1"], include_queue_version=True)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with repo._lock:
            future = pool.submit(repo.get_records, bid, ["r1"], include_queue_version=True)
            assert future.result(timeout=3)[0]["record_id"] == "r1"


def test_external_dirty_write_repairs_before_payload_and_version_read(corpus):
    repo, build = corpus
    bid = build["build_id"]
    previous = repo.get_records(bid, ["r1"], include_queue_version=True)[0]
    changed = {**previous, "speaker": "Externally changed"}
    with sqlite3.connect(repo.build_records_db_path(bid)) as writer:
        writer.execute(
            "UPDATE corpus_records SET payload=? WHERE record_id='r1'",
            (json.dumps(changed),),
        )
    current = repo.get_records(bid, ["r1"], include_queue_version=True)[0]
    assert current["speaker"] == "Externally changed"
    assert current["queue_state_version"] > previous["queue_state_version"]
    assert "Externally changed" in repo.review_metadata_facets(bid)["speaker"]


def test_record_database_schema_change_reinitializes_once(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    repo.get_records(bid, ["r1"], include_queue_version=True)
    original = repo._initialize_records_db
    calls = []

    def initialize(connection):
        calls.append(True)
        original(connection)

    monkeypatch.setattr(repo, "_initialize_records_db", initialize)
    with sqlite3.connect(repo.build_records_db_path(bid)) as writer:
        writer.execute("DROP TABLE review_facets")
    assert repo.get_records(bid, ["r1"], include_queue_version=True)[0]
    assert repo.review_metadata_facets(bid)
    assert len(calls) == 1


def test_review_read_repair_churn_fails_visibly_after_bounded_retries(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    original = repo._ensure_review_projection
    calls = []

    def repair(connection, build_id):
        calls.append(True)
        original(connection, build_id)
        connection.execute("INSERT OR IGNORE INTO review_projection_dirty VALUES('r1')")

    with sqlite3.connect(repo.build_records_db_path(bid)) as writer:
        writer.execute("INSERT OR IGNORE INTO review_projection_dirty VALUES('r1')")
    monkeypatch.setattr(repo, "_ensure_review_projection", repair)
    with pytest.raises(RuntimeError, match="changed repeatedly"):
        repo.get_records(bid, ["r1"], include_queue_version=True)
    assert len(calls) == 3


def test_unknown_build_read_does_not_create_storage(corpus):
    repo, _build = corpus
    with pytest.raises(KeyError):
        repo.get_records("missing-build", ["r1"], include_queue_version=True)
    assert not repo.build_records_db_path("missing-build").parent.exists()
    with pytest.raises(KeyError):
        repo.get_records("missing-build", [])


def test_page_decode_releases_read_transaction_and_keeps_snapshot_coherent(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    before = repo.get_records(bid, ["r1"], include_queue_version=True)[0]
    original = repo._decode_migrated
    changed = False

    def decode(payload, *args):
        nonlocal changed
        if not changed:
            changed = True
            with sqlite3.connect(repo.build_records_db_path(bid), timeout=0.1) as writer:
                current = json.loads(writer.execute(
                    "SELECT payload FROM corpus_records WHERE record_id='r1'",
                ).fetchone()[0])
                current["speaker"] = "Changed during decode"
                current["text"] = "Changed during decode"
                current["record_revision"] = int(current.get("record_revision") or 1) + 1
                writer.execute(
                    "UPDATE corpus_records SET payload=? WHERE record_id='r1'",
                    (json.dumps(current),),
                )
        return original(payload, *args)

    monkeypatch.setattr(repo, "_decode_migrated", decode)
    result = repo.page_records(bid, limit=2)
    row = next(item for item in result["items"] if item["record_id"] == "r1")
    assert row["text"] == before["text"]
    assert row["record_revision"] == before["record_revision"]
    assert row["queue_state_version"] == before["queue_state_version"]
    assert "Changed during decode" not in result["metadata_values"].get("speaker", [])
    assert repo.get_record(bid, "r1")["speaker"] == "Changed during decode"


def test_blind_search_counts_and_facets_use_presented_values(corpus):
    repo, build = corpus
    bid = build["build_id"]
    for reviewer, expected in (("alice", 1), ("bob", 0), ("carol", 0)):
        token = current_reviewer.set(reviewer)
        try:
            page = repo.page_records(bid, query="Sealed answer")
            assert page["total"] == page["queue_counts"]["all"] == expected
            assert ("Sealed answer" in page["metadata_values"].get("speaker", [])) == bool(expected)
            presented = copy.deepcopy(repo.load_records(bid))
            for record in presented:
                _present_for_reviewer(record)
            assert page["metadata_values"] == queue.observed_metadata_values(presented)
        finally:
            current_reviewer.reset(token)


@pytest.mark.parametrize("reviewer", ["", "alice", "bob", "carol"])
def test_selected_facets_fetch_only_requested_values_with_reviewer_visibility(reviewer):
    records = [ready_record("r1", "b1"), ready_record("r2", "b2")]
    records[0].update(speaker="Sealed answer", second_opinion={"speaker": {"first_reviewer": "alice", "done": False}})
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE corpus_records(record_id TEXT PRIMARY KEY, ordinal INTEGER)")
    corpus_queue_projection.initialize(connection)
    corpus_queue_projection.update_rows(connection, list(enumerate(records)))
    token = current_reviewer.set(reviewer)
    try:
        all_values = corpus_queue_projection.facets(connection)
        requested = ["speaker", "speaker", "unknown'field"]
        expected = {field: values for field, values in all_values.items() if field in requested}
        fetched = []

        class CountingCursor:
            def __init__(self, cursor):
                self.cursor = cursor

            def fetchall(self):
                rows = self.cursor.fetchall()
                fetched.extend(rows)
                return rows

        class CountingConnection:
            def __init__(self, connection):
                self.connection = connection

            def execute(self, sql, parameters):
                return CountingCursor(self.connection.execute(sql, parameters))

        actual = corpus_queue_projection.facets(CountingConnection(connection), requested)
        assert actual == expected
        assert len(fetched) == sum(len(values) for values in expected.values())
        assert all(field == "speaker" for field, _ in fetched)
        assert ("Sealed answer" in actual.get("speaker", [])) == (reviewer in {"", "alice"})
    finally:
        current_reviewer.reset(token)
        connection.close()


def test_live_cursors_survive_edits_and_reject_topology_or_context_changes(corpus):
    repo, build = corpus
    bid = build["build_id"]
    first = repo.page_records(bid, limit=2)
    record = repo.get_record(bid, "r2")
    record["text"] = "Changed without a scholarly revision"
    repo.update_record(bid, record)
    second = repo.page_records(bid, cursor=first["next_cursor"], limit=2)
    assert [r["record_id"] for r in second["items"]] == ["r2", "r3"]
    previous = repo.page_records(bid, cursor=second["previous_cursor"], direction="backward", limit=2)
    assert [r["record_id"] for r in previous["items"]] == ["r0", "r1"]
    with pytest.raises(ValueError, match="context"):
        repo.page_records(bid, cursor=first["next_cursor"], query="Changed")
    token = current_reviewer.set("different")
    try:
        with pytest.raises(ValueError, match="context"):
            repo.page_records(bid, cursor=first["next_cursor"])
    finally:
        current_reviewer.reset(token)
    repo.save_records(bid, repo.load_records(bid)[1:])
    with pytest.raises(ValueError, match="topology"):
        repo.page_records(bid, cursor=first["next_cursor"])


def test_external_sql_write_is_repaired_and_restart_keeps_projection_current(corpus):
    repo, build = corpus
    bid = build["build_id"]
    changed = repo.get_record(bid, "r1")
    changed.update(review_disposition="pending", accepted=False, text="external row")
    with sqlite3.connect(repo.build_records_db_path(bid)) as connection:
        connection.execute("UPDATE corpus_records SET payload=? WHERE record_id=?", (json.dumps(changed), "r1"))
    other = cb.PdfCorpusRepository(repo.root)
    page = other.page_records(bid, query="external row")
    assert page["total"] == 1
    assert page["queue_counts"]["accepted"] == 0
    assert page["items"][0]["text"] == "external row"


def test_record_payload_and_queue_version_share_a_snapshot(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    initial = repo.get_records(bid, ["r1"], include_queue_version=True)[0]
    writer = cb.PdfCorpusRepository(repo.root)
    changed = writer.get_record(bid, "r1")
    changed["text"] = "committed after the reader's payload lookup"
    original_decode = repo._decode_migrated
    written = False
    def decode(payload, *args):
        nonlocal written
        if not written:
            written = True
            writer.update_record(bid, changed)
        return original_decode(payload, *args)
    monkeypatch.setattr(repo, "_decode_migrated", decode)
    observed = repo.get_records(bid, ["r1"], include_queue_version=True)[0]
    assert observed["text"] == initial["text"]
    assert observed["queue_state_version"] == initial["queue_state_version"]
    current = repo.get_records(bid, ["r1"], include_queue_version=True)[0]
    assert current["text"] == changed["text"]
    assert current["queue_state_version"] > observed["queue_state_version"]
    assert "queue_state_version" not in writer.get_record(bid, "r1")


def test_queue_version_is_operational_not_a_published_metadata_assertion(corpus):
    from app.corpus_publication import serialize_public_record
    from app.metadata_schema import SchemaField

    repo, build = corpus
    record = repo.get_records(build["build_id"], ["r1"], include_queue_version=True)[0]
    assert isinstance(record["queue_state_version"], int)
    public = serialize_public_record(record)
    assert "queue_state_version" not in public
    assert all(
        assertion["field_name"] != "queue_state_version"
        for assertions in public.get("field_assertions", {}).values()
        for assertion in assertions
    )
    with pytest.raises(ValueError, match="cannot be a field name"):
        SchemaField(name="queue_state_version", label="Queue version")
    repo.update_record(build["build_id"], record)
    assert "queue_state_version" not in repo.get_record(build["build_id"], "r1")
    repo.save_records(build["build_id"], repo.page_records(build["build_id"])["items"])
    assert all("queue_state_version" not in row for row in repo.load_records(build["build_id"]))


def test_projection_write_failure_rolls_back_canonical_payload(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    from app import corpus_queue_projection as projection
    before = repo.get_record(bid, "r0")
    changed = dict(before, text="must not commit")
    def fail(*args, **kwargs):
        raise RuntimeError("projection failure")
    monkeypatch.setattr(projection, "update_rows", fail)
    with pytest.raises(RuntimeError, match="projection failure"):
        repo.update_record(bid, changed)
    assert repo.get_record(bid, "r0")["text"] == before["text"]


def test_facet_variants_do_not_depend_on_the_writer_identity(corpus):
    repo, build = corpus
    bid = build["build_id"]
    token = current_reviewer.set("bob")
    try:
        record = repo.get_record(bid, "r0")
        record["text"] = "edited by second reviewer"
        repo.update_record(bid, record)
        assert "Sealed answer" not in repo.review_metadata_facets(bid).get("speaker", [])
    finally:
        current_reviewer.reset(token)
    token = current_reviewer.set("alice")
    try:
        assert "Sealed answer" in repo.review_metadata_facets(bid)["speaker"]
    finally:
        current_reviewer.reset(token)


def test_missing_projection_table_is_rebuilt_without_touching_canonical_state(corpus):
    repo, build = corpus
    bid = build["build_id"]
    before = repo.get_record(bid, "r0")
    with sqlite3.connect(repo.build_records_db_path(bid)) as connection:
        connection.execute("DROP TABLE review_search")
    assert repo.page_records(bid, query="Édouard")["total"] == 6
    assert repo.get_record(bid, "r0") == before


@pytest.mark.parametrize("running", [False, True])
def test_projected_build_summaries_equal_full_derivation(corpus, running):
    repo, build = corpus
    bid = build["build_id"]
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    records = repo.load_records(bid)
    expected = dict(build, record_count=len(records), metadata_total=len(records))
    manager._apply_review_aggregates(
        expected, records, {"valid": True}, automation_running=running, pass_running=False,
    )
    actual = repo.review_build_aggregates(bid, automation_running=running)
    for key in actual:
        if key == "llm_contribution":
            for metric, value in actual[key].items():
                assert expected[key][metric] == value
        else:
            assert expected[key] == actual[key]


def test_review_decision_and_blocked_decision_never_load_full_corpus(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    def fail(*args, **kwargs):
        pytest.fail("decision scanned canonical corpus")
    monkeypatch.setattr(repo, "review_records", fail)
    monkeypatch.setattr(repo, "load_records", fail)
    blocked = manager.review_decision(bid, "r3", "accepted", expected_revision=1)
    assert blocked["blocked"]
    accepted = manager.review_decision(bid, "r0", "accepted", expected_revision=1)
    assert accepted["applied"]
    assert accepted["queue_counts"]["accepted"] == 2
    assert accepted["next_record"]["record_id"] == "r2"


def test_multiple_first_reviewer_variants_and_second_opinion_completion(corpus):
    repo, build = corpus
    bid = build["build_id"]
    record = repo.get_record(bid, "r0")
    record["position_holder"] = "Other sealed value"
    record["second_opinion"]["position_holder"] = {"first_reviewer": "bob", "done": False}
    repo.update_record(bid, record)
    for reviewer, speaker, holder in (("alice", 1, 0), ("bob", 0, 1), ("carol", 0, 0)):
        token = current_reviewer.set(reviewer)
        try:
            assert repo.page_records(bid, query="Sealed answer")["total"] == speaker
            assert repo.page_records(bid, query="Other sealed value")["total"] == holder
        finally:
            current_reviewer.reset(token)
    record["second_opinion"]["speaker"]["done"] = True
    repo.update_record(bid, record)
    token = current_reviewer.set("carol")
    try:
        assert repo.page_records(bid, query="Sealed answer")["total"] == 1
        assert repo.page_records(bid, query="Other sealed value")["total"] == 0
    finally:
        current_reviewer.reset(token)


@pytest.mark.parametrize("cursor", ["", "@@@@", "W10=", "bnVsbA==", "e30=", "x" * 513])
def test_malformed_cursors_fail_explicitly(corpus, cursor):
    repo, build = corpus
    with pytest.raises(ValueError, match="Invalid queue cursor"):
        repo.page_records(build["build_id"], cursor=cursor)


def test_concurrent_repositories_observe_consistent_committed_counts(corpus):
    repo, build = corpus
    bid = build["build_id"]
    writer = cb.PdfCorpusRepository(repo.root)
    def write():
        for index in range(8):
            record = writer.get_record(bid, "r0")
            record.update(accepted=index % 2 == 0, review_disposition="accepted" if index % 2 == 0 else "pending")
            writer.update_record(bid, record)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(write)
        for _ in range(8):
            page = repo.page_records(bid, limit=6)
            accepted = sum(row["review_disposition"] == "accepted" for row in page["items"])
            assert page["queue_counts"]["accepted"] == accepted
        future.result()


def test_legacy_jsonl_bootstrap_and_explicit_repair(corpus):
    repo, build = corpus
    bid = build["build_id"]
    # Remove only this fixture's derived SQLite database, retaining its legacy JSONL.
    repo.build_records_db_path(bid).unlink()
    restored = cb.PdfCorpusRepository(repo.root)
    page = restored.page_records(bid, limit=2)
    assert page["total"] == 6
    old_topology = page["topology_generation"]
    rebuilt = restored.rebuild_review_queue(bid)
    assert rebuilt["topology_generation"] > old_topology
    with pytest.raises(ValueError, match="topology"):
        restored.page_records(bid, cursor=page["next_cursor"])


@pytest.mark.skipif(os.name != "nt", reason="Windows atomic-replacement sharing behavior")
def test_build_read_retries_transient_sharing_errors_but_surfaces_persistent_failure(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    original = Path.read_text
    calls = 0
    def transient(path, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError("sharing violation")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", transient)
    assert repo.get_build(bid)["build_id"] == bid
    assert calls == 2
    def persistent(*args, **kwargs):
        raise PermissionError("denied")
    monkeypatch.setattr(Path, "read_text", persistent)
    with pytest.raises(PermissionError, match="denied"):
        repo.get_build(bid)


@pytest.mark.skipif(not os.environ.get("CORPUS_PROJECTION_BENCHMARK"), reason="opt-in repository queue benchmark")
@pytest.mark.parametrize("count", [1000, 10000])
@pytest.mark.parametrize("build_count", [1, 2])
def test_repository_projection_benchmark(tmp_path, monkeypatch, count, build_count):
    from app.field_assertions import current_assertion_by_name, override_assertion

    builds = []
    for index in range(build_count):
        records = [ready_record(f"r{i}", f"b{i}") for i in range(count)]
        repo, build = install_repo(tmp_path / str(index), records)
        builds.append((repo.root, build["build_id"]))
    filters = queue.QueueFilter(query="Édouard")
    for sample in range(3):
        for mode in ("snapshot_selection", "projection"):
            decoded = 0
            readers = [(cb.PdfCorpusRepository(root), bid) for root, bid in builds]
            for repo, _ in readers:
                original = repo._decode_migrated
                def decode(payload, schema, signature, original=original):
                    nonlocal decoded
                    decoded += 1
                    return original(payload, schema, signature)
                monkeypatch.setattr(repo, "_decode_migrated", decode)
            def page(repo, bid, offset):
                if mode == "projection":
                    return repo.page_records(bid, offset=offset, limit=1, query=filters.query)
                records = repo.review_records(bid)
                selected = repo.select_review_queue(records, filters, offset=offset, limit=1)
                return {
                    "total": selected.total, "items": selected.items,
                    "metadata_values": queue.observed_metadata_values(records),
                }
            started = time.perf_counter()
            for repo, bid in readers:
                assert page(repo, bid, 0)["total"] == count
            cold = time.perf_counter() - started
            cold_decoded = decoded
            started = time.perf_counter()
            for offset in range(20):
                for repo, bid in readers:
                    assert page(repo, bid, offset)["items"][0]["record_id"] == f"r{offset}"
            warm = time.perf_counter() - started
            started = time.perf_counter()
            for repo, bid in readers:
                record = repo.get_record(bid, "r0")
                override_assertion(
                    record, "speaker", f"Changed {mode} {sample}",
                    supersedes=current_assertion_by_name(record, "speaker"), actor="benchmark",
                )
                repo.update_record(bid, record)
                assert f"Changed {mode} {sample}" in page(repo, bid, 0)["metadata_values"]["speaker"]
            edit = time.perf_counter() - started
            result = {
                "mode": mode, "records_per_build": count, "builds": build_count, "sample": sample,
                "cold_seconds": cold, "warm_20_pages_seconds": warm, "edit_and_read_seconds": edit,
                "cold_payloads_decoded": cold_decoded, "total_payloads_decoded": decoded,
                "python": platform.python_version(), "platform": platform.platform(),
                "includes": "repository, search, counts, facets; excludes initialization, HTTP, browser and models",
                "comparison": "current canonical writes in both modes; snapshot selection is a read-path characterization, not a prior deployment",
            }
            with Path(os.environ["CORPUS_PROJECTION_BENCHMARK"]).open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result) + "\n")


@pytest.mark.skipif(not os.environ.get("CORPUS_READ_BENCHMARK"), reason="opt-in clean-read benchmark")
@pytest.mark.parametrize("count", [1000, 10000])
@pytest.mark.parametrize("build_count", [1, 2])
@pytest.mark.parametrize("concurrent_writes", [False, True])
def test_clean_selected_read_benchmark(tmp_path, monkeypatch, count, build_count, concurrent_writes):
    _selected_read_benchmark(tmp_path, monkeypatch, count, build_count, concurrent_writes)


@pytest.mark.parametrize("build_count", [1, 2])
@pytest.mark.parametrize("journal_mode", ["delete", "wal"])
def test_selected_reads_with_concurrent_canonical_writes(tmp_path, monkeypatch, build_count, journal_mode):
    monkeypatch.setenv("CORPUS_READ_BENCHMARK", str(tmp_path / "measurements.jsonl"))
    monkeypatch.setenv("CORPUS_READ_BENCHMARK_JOURNAL", journal_mode)
    _selected_read_benchmark(tmp_path, monkeypatch, 40, build_count, True)
    result = json.loads((tmp_path / "measurements.jsonl").read_text())
    assert result["canonical_writes"] == 40 * build_count
    assert len(result["batch_times_ms"]) == 40
    assert len(result["write_times_ms"]) == 40 * build_count
    assert result["write_p95_ms"] >= result["write_p50_ms"] >= 0
    assert result["payloads_decoded"] == 80 * build_count
    assert result["journal_mode"] == journal_mode
    assert result["synchronous"] == "full"
    assert len(result["write_phase_samples_ms"]) == 40 * build_count
    for sample, total in zip(result["write_phase_samples_ms"], result["write_times_ms"], strict=True):
        assert set(sample) == set(result["write_phase_summary_ms"])
        assert all(0 <= duration <= total for duration in sample.values())


def _instrument_benchmark_writes(repo, monkeypatch):
    """Time bounded named scopes on writer threads only; nested scopes overlap."""
    state = threading.local()
    phases = (
        "lookup", "schema", "bootstrap", "projection_marker", "sqlite_scope",
        "projection_ensure", "queue_update", "semantic_invalidation", "notification",
        "repository_lock_wait", "sqlite_begin", "sqlite_statements", "sqlite_commit",
        "source_stage", "checkpoint",
    )

    @contextmanager
    def timed(phase):
        sample = getattr(state, "sample", None)
        if sample is None:
            yield
            return
        started = time.perf_counter()
        try:
            yield
        finally:
            sample[phase] += (time.perf_counter() - started) * 1000

    def wrap(owner, name, phase):
        original = getattr(owner, name)

        def measured(*args, **kwargs):
            with timed(phase):
                return original(*args, **kwargs)

        monkeypatch.setattr(owner, name, measured)

    for name, phase in (
        ("get_record", "lookup"),
        ("_record_schema", "schema"),
        ("_bootstrap_records_db", "bootstrap"),
        ("_set_records_projection_state", "projection_marker"),
        ("_ensure_review_projection", "projection_ensure"),
        ("_notify_metadata_projection", "notification"),
        ("_stage_asset", "source_stage"),
        ("save_checkpoint", "checkpoint"),
    ):
        wrap(repo, name, phase)
    wrap(cb.corpus_queue_projection, "update_rows", "queue_update")
    wrap(cb.system_store, "mark_semantic_map_dirty", "semantic_invalidation")
    wrap(cb, "note_resource_changed", "notification")
    original_connect = sqlite3.connect

    class MeasuredConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            phase = "sqlite_begin" if sql.lstrip().upper().startswith("BEGIN") else "sqlite_statements"
            with timed(phase):
                return super().execute(sql, parameters)

        def executemany(self, sql, parameters):
            with timed("sqlite_statements"):
                return super().executemany(sql, parameters)

        def commit(self):
            with timed("sqlite_commit"):
                return super().commit()

    def measured_connect(*args, **kwargs):
        kwargs.setdefault("factory", MeasuredConnection)
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", measured_connect)
    original_db = repo._records_db

    @contextmanager
    def measured_db(build_id):
        with timed("sqlite_scope"), original_db(build_id) as connection:
            yield connection

    monkeypatch.setattr(repo, "_records_db", measured_db)
    original_lock = repo._lock

    class MeasuredLock:
        def __enter__(self):
            with timed("repository_lock_wait"):
                original_lock.acquire()
            return self

        def __exit__(self, *exc):
            original_lock.release()

    monkeypatch.setattr(repo, "_lock", MeasuredLock())
    return state, phases


@pytest.mark.parametrize("scope", ["source_stage", "checkpoint"])
def test_scoped_coordination_work_counts(tmp_path, monkeypatch, scope):
    monkeypatch.setenv("CORPUS_READ_BENCHMARK", str(tmp_path / "scoped.jsonl"))
    _scoped_coordination_benchmark(tmp_path, monkeypatch, scope, 3)
    rows = [json.loads(line) for line in (tmp_path / "scoped.jsonl").read_text().splitlines()]
    assert [row["mode"] for row in rows] == ["coarse_comparison", "scoped"]
    for row in rows:
        assert row["canonical_writes"] == row["samples"] == 3
        assert row["payloads_decoded"] == 3
        assert len(row["write_phase_samples_ms"]) == 3
        assert len(row["blocking_operation_times_ms"]) == 3
        assert len(row["blocking_phase_samples_ms"]) == 3
        assert row["blocking_work_count"] == 3


@pytest.mark.skipif(not os.environ.get("CORPUS_READ_BENCHMARK"), reason="opt-in coordination measurements")
@pytest.mark.parametrize("scope", ["source_stage", "checkpoint"])
def test_scoped_coordination_benchmark(tmp_path, monkeypatch, scope):
    _scoped_coordination_benchmark(tmp_path, monkeypatch, scope, 10)


def _scoped_coordination_benchmark(tmp_path, monkeypatch, scope, samples):
    """Controlled I/O delay comparison, not a historical deployment replay."""
    repo, build = install_repo(tmp_path, [ready_record("r0", "b0")])
    bid = build["build_id"]
    other = repo.create_build({"asset_id": build["asset_id"]})
    timing_state, phases = _instrument_benchmark_writes(repo, monkeypatch)
    decoded = 0
    original_decode = repo._decode_migrated

    def decode(*args):
        nonlocal decoded
        decoded += 1
        return original_decode(*args)

    monkeypatch.setattr(repo, "_decode_migrated", decode)
    original_stage = repo._stage_asset
    original_json = cb._json_write
    admitted = threading.Event()

    def delay():
        admitted.set()
        time.sleep(0.04)

    def stage(*args):
        delay()
        return original_stage(*args)

    def write(path, payload):
        if path == repo.build_checkpoint_path(other["build_id"], "measurement"):
            delay()
        return original_json(path, payload)

    monkeypatch.setattr(repo, "_stage_asset", stage)
    monkeypatch.setattr(cb, "_json_write", write)
    for mode in ("coarse_comparison", "scoped"):
        durations = []
        phase_samples = []
        blocking_times = []
        blocking_phases = []
        decoded_before = decoded
        with ThreadPoolExecutor(max_workers=2) as pool:
            for index in range(samples):
                admitted.clear()

                def blocker():
                    def operation():
                        if scope == "source_stage":
                            return repo.save_asset(f"{mode}-{index}".encode(), filename="measurement.txt")
                        return repo.save_checkpoint(other["build_id"], "measurement", {"index": index})
                    timing_state.sample = dict.fromkeys(phases, 0.0)
                    started = time.perf_counter()
                    try:
                        if mode == "coarse_comparison":
                            with repo._lock:
                                operation()
                        else:
                            operation()
                        return (time.perf_counter() - started) * 1000, timing_state.sample
                    finally:
                        timing_state.sample = None

                blocked = pool.submit(blocker)
                assert admitted.wait(10)
                timing_state.sample = dict.fromkeys(phases, 0.0)
                started = time.perf_counter()
                try:
                    record = repo.get_record(bid, "r0")
                    record["metadata_enrichment_state"] = "running" if index % 2 == 0 else "complete"
                    committed = repo.update_record(bid, record)
                    assert committed["record_revision"] == record["record_revision"]
                    assert committed["queue_state_version"] > 0
                    durations.append((time.perf_counter() - started) * 1000)
                    phase_samples.append(timing_state.sample)
                finally:
                    timing_state.sample = None
                duration, sample = blocked.result(timeout=10)
                blocking_times.append(duration)
                blocking_phases.append(sample)
        ranked = sorted(durations)
        assert decoded - decoded_before == samples
        restarted = cb.PdfCorpusRepository(repo.root)
        assert restarted.get_record(bid, "r0")["metadata_enrichment_state"] == record["metadata_enrichment_state"]
        row = {
            "contract": "corpus-scoped-coordination-v1", "scope": scope, "mode": mode,
            "samples": samples, "canonical_writes": samples, "blocking_work_count": samples,
            "payloads_decoded": decoded - decoded_before, "write_times_ms": durations,
            "write_phase_samples_ms": phase_samples,
            "blocking_operation_times_ms": blocking_times,
            "blocking_phase_samples_ms": blocking_phases,
            "injected_io_delay_ms": 40,
            "write_p50_ms": ranked[(samples - 1) // 2],
            "write_p95_ms": ranked[(samples * 95 + 99) // 100 - 1],
            "python": platform.python_version(), "platform": platform.platform(),
            "basis": "one shared repository; two synthetic builds; injected 40-ms I/O delay",
            "comparison": "current code with explicit outer repository reservation, not prior deployment",
            "excludes": "HTTP, browser, live providers, real source extraction, crash/filesystem acceptance",
        }
        with Path(os.environ["CORPUS_READ_BENCHMARK"]).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")


@pytest.mark.parametrize("journal_mode", ["off", "memory", "unknown"])
def test_read_benchmark_rejects_unsupported_journal_mode(tmp_path, monkeypatch, journal_mode):
    monkeypatch.setenv("CORPUS_READ_BENCHMARK_JOURNAL", journal_mode)
    with pytest.raises(ValueError, match="must be delete or wal"):
        _selected_read_benchmark(tmp_path, monkeypatch, 40, 1, True)
    assert not (tmp_path / "repo").exists()


def _selected_read_benchmark(tmp_path, monkeypatch, count, build_count, concurrent_writes):
    journal_mode = os.environ.get("CORPUS_READ_BENCHMARK_JOURNAL", "delete").lower()
    if journal_mode not in {"delete", "wal"}:
        raise ValueError("CORPUS_READ_BENCHMARK_JOURNAL must be delete or wal.")
    builds = []
    repo = None
    for index in range(build_count):
        installed_repo, build = install_repo(
            tmp_path, [ready_record(f"r{i}", f"b{i}") for i in range(count)],
        )
        if repo is None:
            repo = installed_repo
        builds.append((repo, build["build_id"]))
        with repo._records_db(build["build_id"]) as connection:
            assert connection.execute(f"PRAGMA journal_mode={journal_mode}").fetchone()[0] == journal_mode
            assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
    decoded = 0
    decode_lock = threading.Lock()
    initial_versions = {}
    for repo, bid in builds:
        initial_versions[bid] = {
            row["record_id"]: row["queue_state_version"]
            for row in repo.get_records(bid, [f"r{i}" for i in range(40)], include_queue_version=True)
        }
    original = repo._decode_migrated

    def decode(payload, schema, signature):
        nonlocal decoded
        with decode_lock:
            decoded += 1
        return original(payload, schema, signature)

    monkeypatch.setattr(repo, "_decode_migrated", decode)
    monkeypatch.setattr(repo, "_initialize_records_db", lambda *_args: pytest.fail("hot read initialized storage"))
    if not concurrent_writes:
        monkeypatch.setattr(repo, "_ensure_review_projection", lambda *_args: pytest.fail("clean read repaired projection"))
    timing_state, phase_names = _instrument_benchmark_writes(repo, monkeypatch)
    samples = []
    write_samples = []
    write_phase_samples = []
    writes = 0
    with ThreadPoolExecutor(max_workers=build_count * (2 if concurrent_writes else 1)) as pool:
        for index in range(40):
            gate = threading.Barrier(build_count * (2 if concurrent_writes else 1))

            def read(bid):
                gate.wait(timeout=30)
                return repo.get_records(bid, [f"r{index}"], include_queue_version=True)

            def write(bid):
                gate.wait(timeout=30)
                started = time.perf_counter()
                phase_sample = dict.fromkeys(phase_names, 0.0)
                timing_state.sample = phase_sample
                try:
                    record = repo.get_record(bid, f"r{index}")
                    record["metadata_enrichment_state"] = "running"
                    repo.update_record(bid, record)
                    return (time.perf_counter() - started) * 1000, phase_sample
                finally:
                    timing_state.sample = None

            started = time.perf_counter()
            futures = [pool.submit(read, bid) for _, bid in builds]
            writers = [pool.submit(write, bid) for _, bid in builds] if concurrent_writes else []
            for (_, bid), future in zip(builds, futures, strict=True):
                record = future.result()[0]
                assert record["record_id"] == f"r{index}"
                assert record["record_revision"] == 1
                assert record["text"] == ready_record("", "")["text"]
                assert record["metadata_enrichment_state"] in {"complete", "running"}
                initial_version = initial_versions[bid][record["record_id"]]
                if record["metadata_enrichment_state"] == "complete":
                    assert record["queue_state_version"] == initial_version
                else:
                    assert record["queue_state_version"] > initial_version
            samples.append((time.perf_counter() - started) * 1000)
            for writer in writers:
                duration, phase_sample = writer.result()
                write_samples.append(duration)
                write_phase_samples.append(phase_sample)
                writes += 1
    measured_decoded = decoded
    assert measured_decoded == 40 * build_count * (2 if concurrent_writes else 1)
    for _, bid in builds:
        assert repo.get_record(bid, "r39")["metadata_enrichment_state"] == (
            "running" if concurrent_writes else "complete"
        )
    ranked = sorted(samples)
    result = {
        "contract": "corpus-selected-read-v6", "records_per_build": count,
        "journal_mode": journal_mode, "synchronous": "full",
        "builds": build_count, "samples": 40, "p50_ms": ranked[19], "p95_ms": ranked[37],
        "batch_times_ms": samples, "payloads_decoded": measured_decoded,
        "write_times_ms": write_samples,
        "write_phase_samples_ms": write_phase_samples,
        "write_phase_summary_ms": {
            phase: {
                "p50": sorted(sample[phase] for sample in write_phase_samples)[(len(write_phase_samples) - 1) // 2],
                "p95": sorted(sample[phase] for sample in write_phase_samples)[(len(write_phase_samples) * 95 + 99) // 100 - 1],
            }
            for phase in phase_names
        } if write_phase_samples else {},
        "write_p50_ms": sorted(write_samples)[(len(write_samples) - 1) // 2] if write_samples else None,
        "write_p95_ms": sorted(write_samples)[(len(write_samples) * 95 + 99) // 100 - 1] if write_samples else None,
        "shared_repository": True, "canonical_writes": writes,
        "python": platform.python_version(), "platform": platform.platform(),
        "basis": "prepared synthetic builds; warm storage schema; synchronized reads and optional canonical writes",
        "excludes": "HTTP, browser, cold initialization, full enrichment jobs, real sources and providers",
        "write_basis": "canonical Record lookup plus update, including repository coordination and durable persistence",
        "write_phase_basis": "writer-thread inclusive scopes; nested scopes and lock waits overlap and must not be summed",
    }
    with Path(os.environ["CORPUS_READ_BENCHMARK"]).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result) + "\n")
