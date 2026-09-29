# Copyright 2026 Aaron John Schlosser, PhD.
"""Authorization-aware resolution of pipeline choices at feature boundaries."""

from __future__ import annotations

from .evidence import compile_evidence_pipeline
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



def resolve_evidence_pipeline(
    *,
    requested_id: str | None,
    requested_version: int | None,
    is_admin: bool,
    manager: PipelineManager = pipeline_manager,
) -> PipelineDefinition:
    """Resolve the reviewer evidence pipeline a request is allowed to preview.

    The evidence-suggestion endpoint is currently administrator-only, but this
    function mirrors Research access semantics so the authorization rule stays
    explicit if reviewer roles are broadened later. Administrators may preview a
    supported draft without assigning it. Disabled definitions never execute.
    """

    resolved = manager.resolve("evidence_suggestion.reviewer")
    assignment = resolved["assignment"]
    assigned = PipelineDefinition.model_validate(resolved["pipeline"])

    if not requested_id:
        compile_evidence_pipeline(assigned)
        return assigned

    version = requested_version
    selected = manager.get_definition(str(requested_id), version)
    if selected is None:
        suffix = f"@{version}" if version is not None else ""
        raise ValueError(f"Evidence pipeline {requested_id}{suffix} was not found.")

    compile_evidence_pipeline(selected)
    if selected.status == "disabled":
        raise ValueError("Disabled evidence pipelines cannot execute.")
    if is_admin:
        return selected

    same_as_assignment = (
        selected.pipeline_id == assigned.pipeline_id
        and selected.version == assigned.version
    )
    if same_as_assignment:
        return selected
    if not bool(assignment.get("override_allowed")):
        raise ValueError("The active evidence pipeline does not allow per-run overrides.")
    if selected.status != "active":
        raise ValueError("Only active evidence pipelines may be selected for reviewer runs.")
    return selected
