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

"""Operational data retention: policy, planning, each store kind, and the admin API."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from app import http_auth
from app.data_retention import (
    GIGABYTE,
    BenchmarkRunRetention,
    JobHistoryRetention,
    PipelineTraceRetention,
    ResponseCacheRetention,
    RetentionItem,
    RetentionPolicy,
    RetentionRule,
    RetentionScheduler,
    RetentionService,
    plan,
)
from app.job_state import PersistentJobStateMixin
from app.pipelines.store import PipelineStore
from app.routers import system as system_router
from fastapi import HTTPException

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def ago(days: float) -> str:
    return (NOW - timedelta(days=days)).isoformat()


class Settings:
    def __init__(self):
        self.values = {}

    def get_setting(self, key):
        return self.values.get(key)

    def put_setting(self, key, value):
        self.values[key] = value


class Jobs(PersistentJobStateMixin):
    """A job manager with the real footprint listing and delete semantics."""

    def __init__(self, job_type, jobs):
        self.JOB_TYPE = job_type
        self._lock = threading.RLock()
        self._jobs = {job["id"]: job for job in jobs}

    def delete(self, job_id):
        job = self._jobs[job_id]
        if job["status"] in {"queued", "running", "cancelling"}:
            raise ValueError("active")
        del self._jobs[job_id]


class Collection:
    def __init__(self, records):
        self.records = dict(records)
        self.get_calls = []

    def get(self, *, ids=None, include=(), limit=None, offset=0):
        self.get_calls.append({
            "ids": list(ids) if ids is not None else None,
            "include": list(include),
            "limit": limit,
            "offset": offset,
        })
        keys = list(ids) if ids is not None else list(self.records)
        if ids is None:
            stop = offset + int(limit or len(keys))
            keys = keys[offset:stop]
        out = {"ids": keys, "documents": [self.records[k][0] for k in keys],
               "metadatas": [{"created_at": self.records[k][1]} for k in keys]}
        if "embeddings" in include:
            out["embeddings"] = [[0.0] * 8 for _ in keys]
        return out

    def delete(self, *, ids):
        for key in ids:
            self.records.pop(key, None)


def _trace(database, run_id, feature, started_at, size=100):
    with database.lock, database.connect() as conn:
        conn.execute(
            "INSERT INTO pipeline_runs VALUES(?,?,?,?,?,?,?,?,?,?)",
            (run_id, feature, "p", 1, None, "completed", "h", started_at, started_at, "x" * size),
        )
        conn.execute(
            "INSERT INTO pipeline_stage_runs VALUES(?,?,?,?,?,?,?)",
            (run_id, "s", "select.top_k", "completed", started_at, started_at, "y" * 10),
        )
        conn.commit()


def _count(database, table, where="1=1"):
    with database.lock, database.connect() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]  # noqa: S608


@pytest.fixture
def world(tmp_path):
    database = PipelineStore(tmp_path / "system.sqlite3").database
    rag = Jobs("rag", [
        {"id": "rag-old", "status": "completed", "created_at": ago(40)},
        {"id": "rag-running", "status": "running", "created_at": ago(90)},
    ])
    tools = Jobs("llm_tool", [{"id": "tool-old", "status": "failed", "created_at": ago(50)}])
    collection = Collection({"resp-old": ("answer", ago(60)), "resp-new": ("answer", ago(1))})
    settings = Settings()
    service = RetentionService(
        settings_repository=settings,
        pipeline_database=database,
        job_managers=lambda: [rag, tools],
        response_cache_collection=lambda: collection,
        known_trace_features=lambda: ["vector_store_search"],
    )
    _trace(database, "rag-old", "research", ago(40))
    _trace(database, "research-orphan", "research", ago(40))
    _trace(database, "search-old", "vector_store_search", ago(40))
    _trace(database, "search-new", "vector_store_search", ago(1))
    return SimpleNamespace(database=database, rag=rag, tools=tools, collection=collection, settings=settings,
                           service=service)


# --- Policy -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rule", "match"),
    [
        ({"mode": "max_age_days", "value": 1.5}, "whole number"),
        ({"mode": "max_age_days", "value": 0}, "whole number"),
        ({"mode": "max_size_gb", "value": 0}, "between"),
        ({"mode": "keep", "value": 3}, "Only day and size"),
    ],
)
def test_invalid_rules_are_rejected(rule, match) -> None:
    with pytest.raises(ValueError, match=match):
        RetentionRule.model_validate(rule)


def test_default_is_keep_everything_and_cannot_inherit() -> None:
    assert RetentionPolicy().default.mode == "keep"
    with pytest.raises(ValueError, match="cannot inherit"):
        RetentionPolicy(default=RetentionRule(mode="inherit"))


def test_unknown_stores_cannot_be_configured(world) -> None:
    with pytest.raises(ValueError, match="Unknown data store"):
        world.service.save_policy(RetentionPolicy(stores={"corpus_records": RetentionRule(mode="keep")}))


# --- Planning ---------------------------------------------------------------------------


def test_age_rule_keeps_pinned_and_undated_records() -> None:
    items = [
        RetentionItem("old", NOW - timedelta(days=10), 5),
        RetentionItem("pinned", NOW - timedelta(days=10), 5, pinned=True),
        RetentionItem("undated", None, 5),
        RetentionItem("new", NOW - timedelta(days=1), 5),
    ]
    report = plan(items, RetentionRule(mode="max_age_days", value=7), now=NOW)
    assert report["remove_keys"] == ["old"] and report["remove_bytes"] == 5


def test_size_rule_removes_oldest_first_until_under_the_cap() -> None:
    items = [RetentionItem(f"r{i}", NOW - timedelta(days=i), GIGABYTE // 4) for i in range(4)]
    report = plan(items, RetentionRule(mode="max_size_gb", value=0.5), now=NOW)
    assert report["remove_keys"] == ["r3", "r2"]


def test_size_rule_reports_when_pinned_data_alone_exceeds_the_cap() -> None:
    items = [RetentionItem("pinned", NOW, GIGABYTE, pinned=True), RetentionItem("old", NOW - timedelta(days=1), 10)]
    report = plan(items, RetentionRule(mode="max_size_gb", value=0.5), now=NOW)
    assert report["remove_keys"] == ["old"] and report["warnings"] == ["pinned_exceeds_cap"]


# --- Stores -----------------------------------------------------------------------------


def test_research_traces_stay_while_their_job_exists(world) -> None:
    store = PipelineTraceRetention(world.database, "research", world.service._research_job_ids)
    pinned = {item.key: item.pinned for item in store.items()}
    assert pinned == {"rag-old": True, "research-orphan": False}


def test_trace_deletion_removes_stage_rows_and_only_that_feature(world) -> None:
    store = PipelineTraceRetention(world.database, "vector_store_search", set)
    assert store.delete(["search-old", "rag-old"]) == 1
    assert _count(world.database, "pipeline_runs") == 3
    assert _count(world.database, "pipeline_stage_runs", "run_id='search-old'") == 0


def test_benchmark_runs_expire_by_age(world) -> None:
    with world.database.lock, world.database.connect() as conn:
        conn.execute("INSERT INTO pipeline_benchmark_cases VALUES('c',1,?,NULL,'db','fp','{}')", (ago(90),))
        for run_id, age in (("b-old", 90), ("b-new", 1)):
            conn.execute(
                "INSERT INTO pipeline_benchmark_runs VALUES(?,?,?,?,NULL,'l',1,'r',1,'{}')",
                (run_id, "c", 1, ago(age)),
            )
        conn.commit()
    store = BenchmarkRunRetention(world.database)
    report = plan(store.items(), RetentionRule(mode="max_age_days", value=30), now=NOW)
    assert report["remove_keys"] == ["b-old"]
    assert store.delete(report["remove_keys"]) == 1
    assert _count(world.database, "pipeline_benchmark_cases") == 1, "cases are canonical"


def test_job_history_never_removes_active_jobs_and_uses_the_manager(world) -> None:
    store = JobHistoryRetention(lambda: [world.rag, world.tools])
    report = plan(store.items(), RetentionRule(mode="max_age_days", value=30), now=NOW)
    assert sorted(report["remove_keys"]) == ["llm_tool:tool-old", "rag:rag-old"]
    assert store.delete([*report["remove_keys"], "rag:rag-running"]) == 2
    assert set(world.rag._jobs) == {"rag-running"} and world.tools._jobs == {}


def test_response_cache_sizes_include_vectors_and_expire_oldest(world) -> None:
    store = ResponseCacheRetention(lambda: world.collection)
    items = {item.key: item for item in store.items()}
    assert items["resp-old"].size > 32, "document, metadata and an 8-dimension vector"
    store.delete(["resp-old"])
    assert list(world.collection.records) == ["resp-new"]
    assert ResponseCacheRetention(lambda: None).items() == []


def test_response_cache_retention_pages_large_collections() -> None:
    collection = Collection({
        f"resp-{index:04d}": ("answer" * 20, ago(index % 60))
        for index in range(1200)
    })

    items = ResponseCacheRetention(lambda: collection).items()

    assert len(items) == 1200
    scan_calls = [call for call in collection.get_calls if call["ids"] is None]
    assert len(scan_calls) == 3
    assert all(call["limit"] == 512 for call in scan_calls)
    assert [call["offset"] for call in scan_calls] == [0, 512, 1024]
    assert all(call["include"] == ["documents", "metadatas"] for call in scan_calls)
    sample_calls = [call for call in collection.get_calls if call["ids"] is not None]
    assert len(sample_calls) == 1
    assert sample_calls[0]["include"] == ["embeddings"]


# --- Service ----------------------------------------------------------------------------


def test_overview_previews_without_removing_anything(world) -> None:
    world.service.save_policy(RetentionPolicy(default=RetentionRule(mode="max_age_days", value=30)))
    overview = world.service.overview(now=NOW)

    rows = {row["store_id"]: row for row in overview["stores"]}
    assert set(rows) == {
        "pipeline_traces:research", "pipeline_traces:vector_store_search",
        "pipeline_benchmark_runs", "job_history", "response_cache",
    }
    assert rows["pipeline_traces:research"]["remove_count"] == 1
    assert rows["pipeline_traces:research"]["pinned_count"] == 1
    assert rows["response_cache"]["remove_count"] == 1
    assert _count(world.database, "pipeline_runs") == 4 and len(world.collection.records) == 2


def test_store_overrides_win_and_inherit_uses_the_system_default(world) -> None:
    world.service.save_policy(RetentionPolicy(
        default=RetentionRule(mode="max_age_days", value=30),
        stores={
            "response_cache": RetentionRule(mode="keep"),
            "job_history": RetentionRule(mode="inherit"),
        },
    ))
    assert "job_history" not in world.settings.values["data_retention"]["stores"], "inherit is not stored"
    result = world.service.apply(now=NOW)

    rows = {row["store_id"]: row for row in result["stores"]}
    assert rows["response_cache"]["effective_rule"]["mode"] == "keep" and rows["response_cache"]["remove_count"] == 0
    assert len(world.collection.records) == 2
    assert rows["job_history"]["effective_rule"] == {"mode": "max_age_days", "value": 30.0}
    assert rows["job_history"]["removed_count"] == 2
    assert _count(world.database, "pipeline_runs", "run_id IN ('search-old','research-orphan')") == 0
    # Traces are evaluated before job history, so this trace was still pinned by
    # its job; it becomes eligible on the next pass now that the job is gone.
    assert _count(world.database, "pipeline_runs", "run_id='rag-old'") == 1
    world.service.apply(now=NOW)
    assert _count(world.database, "pipeline_runs", "run_id='rag-old'") == 0


def test_apply_can_target_selected_stores(world) -> None:
    world.service.save_policy(RetentionPolicy(default=RetentionRule(mode="max_age_days", value=30)))
    result = world.service.apply(now=NOW, store_ids={"response_cache"})
    assert [row["store_id"] for row in result["stores"]] == ["response_cache"]
    assert _count(world.database, "pipeline_runs") == 4


def test_one_unreadable_store_does_not_hide_the_others(world) -> None:
    world.service.response_cache_collection = lambda: (_ for _ in ()).throw(RuntimeError("chroma down"))
    rows = {row["store_id"]: row for row in world.service.overview(now=NOW)["stores"]}
    assert "chroma down" in rows["response_cache"]["error"]
    assert rows["job_history"]["count"] == 3


def test_scheduler_does_nothing_while_everything_is_kept(world) -> None:
    calls = []
    world.service.apply = lambda **_kwargs: calls.append(1)
    scheduler = RetentionScheduler(lambda: world.service)
    scheduler.tick()
    assert calls == []
    world.service.save_policy(RetentionPolicy(stores={"job_history": RetentionRule(mode="max_age_days", value=7)}))
    scheduler.tick()
    assert calls == [1]


def test_reclaim_returns_removed_space_to_the_disk(world) -> None:
    for index in range(200):
        _trace(world.database, f"bulk-{index}", "vector_store_search", ago(90), size=5000)
    world.service.save_policy(RetentionPolicy(default=RetentionRule(mode="max_age_days", value=30)))
    world.service.apply(now=NOW)

    result = world.service.reclaim_disk_space()
    assert result["bytes_after"] < result["bytes_before"]


# --- Admin API --------------------------------------------------------------------------


def test_retention_routes_are_admin_only(monkeypatch) -> None:
    monkeypatch.setattr(http_auth, "request_user", lambda _request: SimpleNamespace(role="researcher"))
    for call in (
        lambda: system_router.data_retention(None),
        lambda: system_router.update_data_retention(RetentionPolicy(), None),
        lambda: system_router.apply_data_retention(system_router.DataRetentionApply(), None),
        lambda: system_router.reclaim_data_retention_space(None),
    ):
        with pytest.raises(HTTPException) as caught:
            call()
        assert caught.value.status_code == 403


def test_saving_an_unknown_store_is_a_validation_error(monkeypatch, world) -> None:
    monkeypatch.setattr(system_router, "require_admin", lambda _request: SimpleNamespace(username="admin"))
    monkeypatch.setattr(system_router, "retention_service", world.service)
    with pytest.raises(HTTPException) as caught:
        system_router.update_data_retention(
            RetentionPolicy(stores={"corpus_records": RetentionRule(mode="keep")}), None
        )
    assert caught.value.status_code == 422
