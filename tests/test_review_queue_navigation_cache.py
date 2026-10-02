# Copyright 2026 Aaron John Schlosser, PhD.
"""Queue navigation must reuse work without retaining stale or presented records."""
from __future__ import annotations

import json
import os
import platform
import time
from pathlib import Path

import pytest
from test_review_queues import cb, install_repo, ready_record

# isort: split
# The repository fixture installs the optional Chroma stub before app imports.
from app import corpus_review_queue as queue
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


@pytest.mark.parametrize("filters,ids,total_count", [
    ({}, ["r0", "r1", "r2", "r3", "r4", "r5"], 6),
    ({"review_queue": "ready"}, ["r0"], 6),
    ({"review_queue": "issues"}, ["r2", "r3"], 6),
    ({"disposition": "accepted"}, ["r1"], 1),
    ({"metadata_incomplete": True}, ["r2"], 1),
    ({"source_problem": True}, ["r3"], 1),
    ({"needs_review": True}, [], 0),
    ({"query": "  ÉDOUARD  "}, ["r0", "r1", "r2", "r3", "r4", "r5"], 6),
    ({"query": "missing value"}, [], 0),
])
def test_filtered_navigation_preserves_order_counts_and_topology(corpus, filters, ids, total_count):
    repo, build = corpus
    bid = build["build_id"]
    observed = []
    for offset in range(len(ids) + 1):
        page = repo.page_records(bid, offset=offset, limit=1, **filters)
        observed.extend(row["record_id"] for row in page["items"])
        assert page["total"] == len(ids)
        assert page["queue_counts"]["all"] == total_count
        for row in page["items"]:
            assert row["topology_index"] == int(row["record_id"][1:])
            assert row["topology_count"] == 6
    assert observed == ids


def test_navigation_recomputes_after_writes_and_restart(corpus):
    repo, build = corpus
    bid = build["build_id"]
    assert repo.page_records(bid, review_queue="accepted")["total"] == 1
    record = repo.get_record(bid, "r0")
    record.update(review_disposition="accepted", accepted=True)
    repo.update_record(bid, record)
    assert repo.page_records(bid, review_queue="accepted")["total"] == 2
    # A different repository instance writes the store while this instance is warm.
    other = cb.PdfCorpusRepository(repo.root)
    other.save_records(bid, [record])
    for reader in (repo, other, cb.PdfCorpusRepository(repo.root)):
        result = reader.page_records(bid)
        assert [row["record_id"] for row in result["items"]] == ["r0"]
        assert result["items"][0]["topology_count"] == 1
        assert result["queue_counts"]["accepted"] == 1


def test_navigation_presents_each_reviewer_and_returns_independent_values(corpus):
    repo, build = corpus
    bid = build["build_id"]
    for reviewer, expected in [("alice", "Sealed answer"), ("bob", None), ("alice", "Sealed answer")]:
        token = current_reviewer.set(reviewer)
        try:
            page = repo.page_records(bid, limit=1)
            assert page["items"][0]["speaker"] == expected
            page["items"][0]["text"] = "caller mutation"
            page["queue_counts"]["all"] = -1
            fresh = repo.page_records(bid, limit=1)
            assert fresh["items"][0]["text"] != "caller mutation"
            assert fresh["queue_counts"]["all"] == 6
        finally:
            current_reviewer.reset(token)


def test_warm_navigation_does_not_rescan_records(corpus, monkeypatch):
    repo, build = corpus
    bid = build["build_id"]
    first = repo.page_records(bid, limit=1, query="Édouard")
    def unexpected_scan(*args, **kwargs):
        pytest.fail("warm page navigation rescanned queue candidates")
    monkeypatch.setattr(queue, "_disposition", unexpected_scan)
    second = repo.page_records(bid, offset=1, limit=1, query="Édouard")
    assert second["items"][0]["record_id"] == "r1"
    assert second["queue_counts"] == first["queue_counts"]


def test_selection_cache_is_bounded_and_default_selection_handles_mutation(monkeypatch):
    cache = queue.QueueSelectionCache(capacity=1, record_budget=2)
    first = [ready_record("r0", "b0")]
    second = [ready_record("r1", "b1")]
    filters = queue.QueueFilter()
    calls = []
    original = queue._select_indices
    def counted(records, filters):
        calls.append(records)
        return original(records, filters)
    monkeypatch.setattr(queue, "_select_indices", counted)
    for records in (first, first, second, first):
        queue.select_queue(records, filters, offset=0, limit=1, cache=cache)
    assert len(calls) == 3  # second snapshot evicts first; warm first did not scan
    large = first * 3
    for _ in range(2):
        queue.select_queue(large, filters, offset=0, limit=1, cache=cache)
    assert len(calls) == 5  # oversized snapshots are not retained
    pending = queue.QueueFilter(disposition="pending")
    assert queue.select_queue(first, pending, offset=0, limit=1).total == 1
    first[0]["review_disposition"] = "accepted"
    assert queue.select_queue(first, pending, offset=0, limit=1).total == 0


@pytest.mark.skipif(not os.environ.get("CORPUS_QUEUE_BENCHMARK"), reason="opt-in synthetic queue benchmark")
@pytest.mark.parametrize("count", [1000, 10000])
def test_queue_navigation_benchmark(count):
    records = [ready_record(f"r{i}", f"b{i}") for i in range(count)]
    filters = queue.QueueFilter(query="Édouard")
    for sample in range(3):
        for mode in ("uncached", "cached"):
            cache = queue.QueueSelectionCache() if mode == "cached" else None
            started = time.perf_counter()
            for offset in range(20):
                page = queue.select_queue(records, filters, offset=offset, limit=1, cache=cache)
                assert page.total == count
                assert page.items[0]["record_id"] == f"r{offset}"
            result = {
                "mode": mode, "records": count, "pages": 20, "sample": sample,
                "seconds": time.perf_counter() - started,
                "python": platform.python_version(), "platform": platform.platform(),
            }
            with Path(os.environ["CORPUS_QUEUE_BENCHMARK"]).open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result) + "\n")
