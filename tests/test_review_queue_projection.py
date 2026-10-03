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
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from test_review_queues import cb, install_repo, ready_record

# isort: split
# The fixture module sets api on sys.path before importing the application.
from app import corpus_review_queue as queue
from app.corpus_reviewer_helpers import _present_for_reviewer
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
