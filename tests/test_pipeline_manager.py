# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.pipelines.defaults import built_in_pipeline
from app.pipelines.manager import PipelineManager
from app.pipelines.models import PipelineAssignment
from app.pipelines.service import PipelineService
from app.pipelines.store import PipelineStore


def _manager(tmp_path) -> PipelineManager:
    return PipelineManager(
        service=PipelineService(),
        store=PipelineStore(tmp_path / "system.sqlite3"),
    )


def test_system_assignment_rejects_draft_pipeline(tmp_path) -> None:
    manager = _manager(tmp_path)
    draft = built_in_pipeline("research.balanced", 1)
    assert draft is not None

    with pytest.raises(ValueError, match="Only active pipeline versions"):
        manager.assign(
            PipelineAssignment(
                feature="research",
                pipeline_id=draft.pipeline_id,
                pipeline_version=draft.version,
                override_allowed=True,
            )
        )


def test_active_custom_research_pipeline_can_be_saved_and_assigned(tmp_path) -> None:
    manager = _manager(tmp_path)
    source = built_in_pipeline("research.balanced", 1)
    assert source is not None
    custom = source.model_copy(
        update={
            "pipeline_id": "research.custom",
            "version": 1,
            "name": "Research custom",
            "status": "active",
            "built_in": False,
            "derived_from": "research.balanced@1",
        }
    )

    saved = manager.save_definition(custom, actor="admin")
    assigned = manager.assign(
        PipelineAssignment(
            feature="research",
            pipeline_id=saved.pipeline_id,
            pipeline_version=saved.version,
            override_allowed=True,
        )
    )

    assert assigned.pipeline_id == "research.custom"
    resolved = manager.resolve("research")
    assert resolved["pipeline"]["pipeline_id"] == "research.custom"
    assert resolved["pipeline_hash"]


def test_nonresearch_custom_pipeline_is_inspectable_but_not_runtime_supported(tmp_path) -> None:
    manager = _manager(tmp_path)
    source = built_in_pipeline("evidence.conservative", 1)
    assert source is not None
    custom = source.model_copy(
        update={
            "pipeline_id": "evidence.custom",
            "version": 1,
            "name": "Evidence custom",
            "status": "active",
            "built_in": False,
        }
    )

    support = manager.runtime_support(custom)

    assert support["supported"] is False
    assert "not yet been migrated" in support["reason"]



def test_custom_definition_cannot_shadow_code_owned_builtin(tmp_path) -> None:
    manager = _manager(tmp_path)
    source = built_in_pipeline("research.current", 1)
    assert source is not None
    collision = source.model_copy(
        update={
            "built_in": False,
            "status": "draft",
        }
    )

    with pytest.raises(ValueError, match="code-owned"):
        manager.save_definition(collision, actor="admin")



def test_catalog_hides_legacy_custom_collision_with_builtin(tmp_path) -> None:
    manager = _manager(tmp_path)
    source = built_in_pipeline("research.current", 1)
    assert source is not None
    legacy_collision = source.model_copy(
        update={
            "built_in": False,
            "created_at": datetime.now(UTC),
            "created_by": "legacy",
        }
    )
    manager.store.put_definition(legacy_collision)

    matches = [
        item
        for item in manager.list_definitions(purpose="research")
        if item.pipeline_id == "research.current" and item.version == 1
    ]

    assert len(matches) == 1
    assert matches[0].built_in is True
