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

"""Corpus metadata family scheduling concurrency."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor as SharedPool

from app import corpus_metadata_enrichment_execution as enrichment


class _Session:
    def __init__(self) -> None:
        self.finished = 0
        self.cancelled = False

    @classmethod
    def open(cls):
        return cls()

    def finish(self, *, cancelled: bool = False) -> None:
        self.finished += 1
        self.cancelled = cancelled


class _Harness(enrichment.MetadataEnrichmentExecutionMixin):
    def __init__(self, barrier: threading.Barrier) -> None:
        self.barrier = barrier
        self.calls: list[list[str]] = []

    def _run_metadata_tasks(
        self,
        record,
        request,
        tasks,
        build_id,
        stage_callback,
        pipeline,
    ):
        names = [item[0] for item in tasks]
        self.calls.append(names)
        if len(tasks) == 1 and names[0] in enrichment.PARALLEL_METADATA_FAMILIES:
            self.barrier.wait(timeout=2)
        return [(name, {"metadata": {}}, None) for name in names]


def _spec(name: str):
    return (name, "prompt", object, 100, f"schema_{name}")


def test_builtin_metadata_families_overlap_and_results_keep_schema_order(monkeypatch) -> None:
    monkeypatch.setattr(enrichment, "EnrichmentSession", _Session)
    harness = _Harness(threading.Barrier(3))

    results = harness._execute_metadata_tasks(
        {},
        {"max_concurrent_requests": 3},
        [_spec("discourse"), _spec("quotation"), _spec("indexing")],
        "build",
        None,
    )

    assert [row[0] for row in results] == ["discourse", "quotation", "indexing"]
    assert sorted(call[0] for call in harness.calls) == [
        "discourse",
        "indexing",
        "quotation",
    ]


def test_custom_family_remains_exclusive_before_parallel_builtin_group(monkeypatch) -> None:
    monkeypatch.setattr(enrichment, "EnrichmentSession", _Session)
    harness = _Harness(threading.Barrier(3))

    results = harness._execute_metadata_tasks(
        {},
        {"max_concurrent_requests": 3},
        [
            _spec("custom"),
            _spec("discourse"),
            _spec("quotation"),
            _spec("indexing"),
        ],
        "build",
        None,
    )

    assert [row[0] for row in results] == [
        "custom",
        "discourse",
        "quotation",
        "indexing",
    ]
    assert harness.calls[0] == ["custom"]


def test_build_orchestration_can_supply_one_shared_family_executor(monkeypatch) -> None:
    monkeypatch.setattr(enrichment, "EnrichmentSession", _Session)
    harness = _Harness(threading.Barrier(3))

    def local_pool_must_not_be_created(*args, **kwargs):
        raise AssertionError("shared family executor should avoid a per-Record nested pool")

    monkeypatch.setattr(enrichment, "ThreadPoolExecutor", local_pool_must_not_be_created)
    with SharedPool(max_workers=3, thread_name_prefix="shared-family-test") as shared:
        results = harness._execute_metadata_tasks(
            {},
            {"max_concurrent_requests": 3},
            [_spec("discourse"), _spec("quotation"), _spec("indexing")],
            "build",
            None,
            family_executor=shared,
        )

    assert [row[0] for row in results] == ["discourse", "quotation", "indexing"]
