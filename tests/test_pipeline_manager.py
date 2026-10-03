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


def test_custom_evidence_pipeline_can_be_saved_and_assigned(tmp_path) -> None:
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

    saved = manager.save_definition(custom, actor="admin")
    support = manager.runtime_support(saved)
    assigned = manager.assign(
        PipelineAssignment(
            feature="evidence_suggestion.reviewer",
            pipeline_id=saved.pipeline_id,
            pipeline_version=saved.version,
            override_allowed=False,
        )
    )

    assert support == {"supported": True, "adapter": "evidence_suggestion"}
    assert assigned.pipeline_id == "evidence.custom"
    assert manager.resolve("evidence_suggestion.reviewer")["pipeline"]["pipeline_id"] == "evidence.custom"


def test_custom_metadata_precedent_pipeline_can_be_saved_and_assigned(tmp_path) -> None:
    manager = _manager(tmp_path)
    source = built_in_pipeline("metadata.precedents.current", 1)
    assert source is not None
    custom = source.model_copy(
        update={
            "pipeline_id": "metadata.custom",
            "version": 1,
            "name": "Metadata custom",
            "status": "active",
            "built_in": False,
        }
    )

    saved = manager.save_definition(custom, actor="admin")
    support = manager.runtime_support(saved)
    assigned = manager.assign(
        PipelineAssignment(
            feature="metadata_precedents",
            pipeline_id=saved.pipeline_id,
            pipeline_version=saved.version,
            override_allowed=True,
        )
    )

    assert support == {"supported": True, "adapter": "metadata_precedents"}
    assert assigned.pipeline_id == "metadata.custom"
    assert manager.resolve("metadata_precedents")["pipeline"]["pipeline_id"] == "metadata.custom"


@pytest.mark.parametrize(
    ("pipeline_id", "feature", "custom_id", "adapter"),
    [
        ("memory.claim.current", "claim_memory", "memory.claim.custom", "claim_memory"),
        (
            "memory.response.current",
            "response_memory",
            "memory.response.custom",
            "response_memory",
        ),
    ],
)
def test_custom_memory_pipeline_can_be_saved_and_assigned(
    tmp_path,
    pipeline_id,
    feature,
    custom_id,
    adapter,
) -> None:
    manager = _manager(tmp_path)
    source = built_in_pipeline(pipeline_id, 1)
    assert source is not None
    custom = source.model_copy(
        update={
            "pipeline_id": custom_id,
            "version": 1,
            "name": f"{feature} custom",
            "status": "active",
            "built_in": False,
        }
    )

    saved = manager.save_definition(custom, actor="admin")
    support = manager.runtime_support(saved)
    assigned = manager.assign(
        PipelineAssignment(
            feature=feature,
            pipeline_id=saved.pipeline_id,
            pipeline_version=saved.version,
            override_allowed=False,
        )
    )

    assert support == {"supported": True, "adapter": adapter}
    assert assigned.pipeline_id == custom_id
    assert manager.resolve(feature)["pipeline"]["pipeline_id"] == custom_id


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



def test_prepare_clone_uses_authoritative_next_version_for_builtin(tmp_path) -> None:
    manager = _manager(tmp_path)
    source = built_in_pipeline("research.current", 1)
    assert source is not None

    first = manager.prepare_clone(source.pipeline_id, source.version)
    assert first.pipeline_id == "research.current.custom"
    assert first.version == 1
    assert first.status == "draft"
    assert first.built_in is False
    assert first.derived_from == "research.current@1"
    assert first.created_at is None
    assert first.created_by is None

    manager.save_definition(first, actor="admin")
    second = manager.prepare_clone(source.pipeline_id, source.version)

    assert second.pipeline_id == first.pipeline_id
    assert second.version == 2
    assert second.derived_from == "research.current@1"


def test_prepare_clone_of_custom_pipeline_creates_next_immutable_version(tmp_path) -> None:
    manager = _manager(tmp_path)
    source = built_in_pipeline("research.current", 1)
    assert source is not None
    custom = source.model_copy(
        update={
            "pipeline_id": "research.academic",
            "version": 4,
            "name": "Research — academic",
            "status": "draft",
            "built_in": False,
            "derived_from": "research.current@1",
        }
    )
    saved = manager.save_definition(custom, actor="admin")

    clone = manager.prepare_clone(saved.pipeline_id, saved.version)

    assert clone.pipeline_id == "research.academic"
    assert clone.version == 5
    assert clone.name == "Research — academic"
    assert clone.status == "draft"
    assert clone.derived_from == "research.academic@4"
