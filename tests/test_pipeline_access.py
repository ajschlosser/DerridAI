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

import pytest
from app.pipelines.access import resolve_research_pipeline
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


def _save_active_custom(manager: PipelineManager, pipeline_id: str = "research.custom"):
    source = built_in_pipeline("research.current", 1)
    assert source is not None
    custom = source.model_copy(
        update={
            "pipeline_id": pipeline_id,
            "version": 1,
            "name": "Custom Research",
            "status": "active",
            "built_in": False,
            "derived_from": "research.current@1",
        }
    )
    return manager.save_definition(custom, actor="admin")


def test_research_resolution_uses_system_assignment_without_override(tmp_path) -> None:
    manager = _manager(tmp_path)

    resolved = resolve_research_pipeline(
        requested_id=None,
        requested_version=None,
        is_admin=False,
        manager=manager,
    )

    assert resolved.pipeline_id == "research.current"
    assert resolved.version == 2
    assert manager.get_definition("research.current", 1) is not None


def test_researcher_can_select_active_pipeline_when_assignment_allows_overrides(tmp_path) -> None:
    manager = _manager(tmp_path)
    custom = _save_active_custom(manager)

    selected = resolve_research_pipeline(
        requested_id=custom.pipeline_id,
        requested_version=custom.version,
        is_admin=False,
        manager=manager,
    )

    assert selected.pipeline_id == custom.pipeline_id


def test_researcher_cannot_select_draft_pipeline(tmp_path) -> None:
    manager = _manager(tmp_path)
    source = built_in_pipeline("research.balanced", 1)
    assert source is not None

    with pytest.raises(ValueError, match="Only active Research pipelines"):
        resolve_research_pipeline(
            requested_id=source.pipeline_id,
            requested_version=source.version,
            is_admin=False,
            manager=manager,
        )


def test_researcher_override_respects_assignment_policy(tmp_path) -> None:
    manager = _manager(tmp_path)
    custom = _save_active_custom(manager)
    manager.store.put_assignment(
        PipelineAssignment(
            feature="research",
            pipeline_id="research.current",
            pipeline_version=1,
            override_allowed=False,
            source="system",
        ),
        updated_at="test",
    )

    with pytest.raises(ValueError, match="does not allow per-run overrides"):
        resolve_research_pipeline(
            requested_id=custom.pipeline_id,
            requested_version=custom.version,
            is_admin=False,
            manager=manager,
        )


def test_admin_can_explicitly_test_supported_draft_pipeline(tmp_path) -> None:
    manager = _manager(tmp_path)
    draft = built_in_pipeline("research.balanced", 1)
    assert draft is not None

    selected = resolve_research_pipeline(
        requested_id=draft.pipeline_id,
        requested_version=draft.version,
        is_admin=True,
        manager=manager,
    )

    assert selected.status == "draft"


def test_admin_cannot_execute_disabled_pipeline(tmp_path) -> None:
    manager = _manager(tmp_path)
    source = built_in_pipeline("research.current", 1)
    assert source is not None
    disabled = source.model_copy(
        update={
            "pipeline_id": "research.disabled",
            "version": 1,
            "name": "Disabled Research",
            "status": "disabled",
            "built_in": False,
        }
    )
    manager.save_definition(disabled, actor="admin")

    with pytest.raises(ValueError, match="Disabled Research pipelines"):
        resolve_research_pipeline(
            requested_id=disabled.pipeline_id,
            requested_version=disabled.version,
            is_admin=True,
            manager=manager,
        )
