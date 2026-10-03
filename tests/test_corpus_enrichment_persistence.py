# Copyright 2026 Aaron John Schlosser, PhD.
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
import time
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
        records = [
            {"text": f"Source {index}: " + "documentary evidence " * 100,
             "metadata_complete": pending is not None and index >= pending}
            for index in range(count)
        ]
        repo, build = install(tmp_path, records)
        manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
        managers.append(manager)
        monkeypatch.setattr(manager, "_allowed_fields", lambda _build: {"speaker"})
        monkeypatch.setattr(manager, "_enrich_record", lambda record, *_args, **_kwargs: _completed(record))
        return repo, build["build_id"], manager

    yield make
    for manager in managers:
        manager._executor.shutdown(wait=True)


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
    assert len(loads) == 2  # Queue initialization reconciliation plus final handoff, not per completion.


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
    save, update = repo.save_records, repo.update_record

    def saved(build_id, rows):
        counters["full_saves"] += 1
        counters["full_save_rows"] += len(rows)
        return save(build_id, rows)

    def updated(*args):
        counters["row_updates"] += 1
        return update(*args)

    monkeypatch.setattr(repo, "save_records", saved)
    monkeypatch.setattr(repo, "update_record", updated)
    start = time.perf_counter()
    result = manager._schedule_build_enrichment(build_id, {"max_concurrent_requests": 1}, {}, records)
    elapsed = time.perf_counter() - start
    assert all(row["metadata_complete"] for row in result)
    row = {"records": count, "completions": 20, "sample": sample, "seconds": elapsed,
           "python": platform.python_version(), "platform": platform.platform(), **counters}
    with Path(os.environ["CORPUS_PERSISTENCE_BENCHMARK"]).open("a", encoding="utf-8") as output:
        output.write(json.dumps(row) + "\n")
