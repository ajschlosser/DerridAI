# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.pipelines.models import (
    PipelineAssignment,
    PipelineDefinition,
    PipelineRunTrace,
    PipelineStageTrace,
)
from app.pipelines.store import PipelineStore


def _definition(version: int = 1) -> PipelineDefinition:
    return PipelineDefinition.model_validate(
        {
            "pipeline_id": "custom.fast",
            "version": version,
            "name": "Custom fast",
            "purpose": "research",
            "status": "draft",
            "entry_stage_ids": ["retrieve"],
            "stages": [
                {
                    "id": "retrieve",
                    "strategy": "retrieve.lexical_bm25",
                    "next": ["select"],
                },
                {
                    "id": "select",
                    "strategy": "select.top_k",
                    "config": {"limit": 12},
                },
            ],
            "created_at": datetime.now(UTC),
            "created_by": "admin",
        }
    )


def test_pipeline_store_versions_definitions_immutably(tmp_path) -> None:
    store = PipelineStore(tmp_path / "system.sqlite3")

    store.put_definition(_definition(1))
    with pytest.raises(ValueError, match="already exists"):
        store.put_definition(_definition(1))
    store.put_definition(_definition(2))

    assert store.get_definition("custom.fast", 1).version == 1
    assert store.get_definition("custom.fast").version == 2
    assert [item.version for item in store.list_definitions()] == [2, 1]


def test_pipeline_store_round_trips_assignments_and_trace_lineage(tmp_path) -> None:
    store = PipelineStore(tmp_path / "system.sqlite3")
    store.put_definition(_definition())
    assignment = PipelineAssignment(
        feature="research",
        pipeline_id="custom.fast",
        pipeline_version=1,
        override_allowed=True,
        source="system",
    )
    store.put_assignment(assignment, updated_at=datetime.now(UTC).isoformat())

    now = datetime.now(UTC)
    trace = PipelineRunTrace(
        run_id="run-1",
        feature="research",
        pipeline_id="custom.fast",
        pipeline_version=1,
        resolved_pipeline=_definition().model_dump(mode="json"),
        resolved_hash="a" * 64,
        owner="admin",
        status="completed",
        started_at=now,
        finished_at=now,
        total_elapsed_ms=10,
        stages=[
            PipelineStageTrace(
                stage_id="retrieve",
                strategy_id="retrieve.lexical_bm25",
                status="completed",
                started_at=now,
                finished_at=now,
                elapsed_ms=4,
                input_count=1,
                output_count=12,
                score_summary={"top": 0.9},
            )
        ],
    )
    store.put_run(trace)

    assert store.get_assignment("research") == assignment
    restored = store.get_run("run-1")
    assert restored is not None
    assert restored.stages[0].output_count == 12
    assert store.list_runs(feature="research")[0].run_id == "run-1"


def test_pipeline_store_snapshot_restores_config_and_history(tmp_path) -> None:
    first = PipelineStore(tmp_path / "first.sqlite3")
    first.put_definition(_definition())
    first.put_assignment(
        PipelineAssignment(
            feature="research",
            pipeline_id="custom.fast",
            pipeline_version=1,
            source="system",
        ),
        updated_at="now",
    )

    snapshot = first.snapshot()
    second = PipelineStore(tmp_path / "second.sqlite3")
    second.restore_snapshot(snapshot)

    assert second.get_definition("custom.fast", 1) is not None
    assert second.get_assignment("research") is not None



def test_invalid_snapshot_does_not_destroy_existing_pipeline_state(tmp_path) -> None:
    store = PipelineStore(tmp_path / "system.sqlite3")
    store.put_definition(_definition())
    before = store.snapshot()

    broken = {
        **before,
        "stages": [
            {
                "run_id": "missing-run",
                "payload": {
                    "stage_id": "retrieve",
                    "strategy_id": "retrieve.lexical_bm25",
                    "status": "completed",
                },
            }
        ],
    }

    with pytest.raises(ValueError, match="unknown run"):
        store.restore_snapshot(broken)

    restored = store.get_definition("custom.fast", 1)
    assert restored is not None
    assert restored.name == "Custom fast"
    assert store.snapshot() == before
