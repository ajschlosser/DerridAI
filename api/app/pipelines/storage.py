# Copyright 2026 Aaron John Schlosser, PhD.
"""Shared SQLite boundary for durable pipeline configuration and traces."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from ..persistence import system_repository


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def load_json(value: str | bytes | None, default: Any) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


class PipelineDatabase:
    """Own the pipeline tables and connection policy for the system database."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or system_repository.path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_schema(self) -> None:
        with self.lock, self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS pipeline_definitions (
                    pipeline_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (pipeline_id, version)
                );
                CREATE INDEX IF NOT EXISTS idx_pipeline_definitions_purpose
                    ON pipeline_definitions(purpose, status, pipeline_id, version DESC);

                CREATE TABLE IF NOT EXISTS pipeline_assignments (
                    feature TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    scope_id TEXT NOT NULL DEFAULT '',
                    pipeline_id TEXT NOT NULL,
                    pipeline_version INTEGER NOT NULL,
                    override_allowed INTEGER NOT NULL DEFAULT 0,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (feature, scope, scope_id)
                );
                CREATE INDEX IF NOT EXISTS idx_pipeline_assignments_pipeline
                    ON pipeline_assignments(pipeline_id, pipeline_version);

                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_id TEXT PRIMARY KEY,
                    feature TEXT NOT NULL,
                    pipeline_id TEXT NOT NULL,
                    pipeline_version INTEGER NOT NULL,
                    owner TEXT,
                    status TEXT NOT NULL,
                    resolved_hash TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_pipeline_runs_feature_started
                    ON pipeline_runs(feature, started_at DESC);
                CREATE INDEX IF NOT EXISTS idx_pipeline_runs_owner_started
                    ON pipeline_runs(owner, started_at DESC);

                CREATE TABLE IF NOT EXISTS pipeline_stage_runs (
                    run_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, stage_id),
                    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_pipeline_stage_strategy
                    ON pipeline_stage_runs(strategy_id, started_at DESC);

                CREATE TABLE IF NOT EXISTS pipeline_benchmark_cases (
                    benchmark_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (benchmark_id, version)
                );
                CREATE INDEX IF NOT EXISTS idx_pipeline_benchmark_cases_created
                    ON pipeline_benchmark_cases(created_at DESC, benchmark_id, version DESC);

                CREATE TABLE IF NOT EXISTS pipeline_benchmark_runs (
                    benchmark_run_id TEXT PRIMARY KEY,
                    benchmark_id TEXT NOT NULL,
                    benchmark_version INTEGER NOT NULL,
                    owner TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY (benchmark_id, benchmark_version)
                        REFERENCES pipeline_benchmark_cases(benchmark_id, version)
                        ON DELETE RESTRICT
                );
                CREATE INDEX IF NOT EXISTS idx_pipeline_benchmark_runs_case_created
                    ON pipeline_benchmark_runs(benchmark_id, benchmark_version, created_at DESC);
                """
            )
