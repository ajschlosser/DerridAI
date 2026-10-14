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

"""Authorization-aware resolution of pipeline choices at feature boundaries."""

from __future__ import annotations

from .manager import PipelineManager, pipeline_manager
from .models import PipelineDefinition
from .research import compile_research_pipeline


def resolve_research_pipeline(
    *,
    requested_id: str | None,
    requested_version: int | None,
    is_admin: bool,
    manager: PipelineManager = pipeline_manager,
) -> PipelineDefinition:
    """Resolve the Research pipeline an incoming run is allowed to execute.

    Administrators may explicitly run any valid Research definition that the
    feature compiler supports, including a draft being tested. Non-admin users
    inherit the system assignment and may only override it when the assignment
    explicitly allows overrides and the chosen pipeline is active.
    """

    resolved = manager.resolve("research")
    assignment = resolved["assignment"]
    assigned = PipelineDefinition.model_validate(resolved["pipeline"])

    if not requested_id:
        compile_research_pipeline(assigned)
        return assigned

    version = requested_version
    selected = manager.get_definition(str(requested_id), version)
    if selected is None:
        suffix = f"@{version}" if version is not None else ""
        raise ValueError(f"Research pipeline {requested_id}{suffix} was not found.")

    compile_research_pipeline(selected)
    if selected.status == "disabled":
        raise ValueError("Disabled Research pipelines cannot execute.")
    if is_admin:
        # Administrators may explicitly test draft versions, but "disabled"
        # remains an execution stop rather than a UI-only label.
        return selected

    same_as_assignment = (
        selected.pipeline_id == assigned.pipeline_id
        and selected.version == assigned.version
    )
    if same_as_assignment:
        return selected
    if not bool(assignment.get("override_allowed")):
        raise ValueError("The active Research pipeline does not allow per-run overrides.")
    if selected.status != "active":
        raise ValueError("Only active Research pipelines may be selected for researcher runs.")
    return selected
