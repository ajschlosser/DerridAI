# Copyright 2026 Aaron John Schlosser, PhD.
"""Typed contracts for configurable retrieval and model pipelines.

Pipeline definitions are declarative application state. They may reference only
server-registered strategies; no user-authored Python, SQL, shell, or network
code is executable through this contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

PipelineStatus = Literal["draft", "active", "disabled"]
StageFamily = Literal[
    "query_transform",
    "candidate_generation",
    "filter",
    "normalization",
    "fusion",
    "rerank",
    "support_validation",
    "diversity",
    "selection",
    "context_pack",
    "llm",
    "evaluation",
]
# What a stage may establish about evidence, support or provenance. Separate
# from ``StageFamily`` (how it computes) and from pipeline purpose (what the
# whole workflow is for). A gate is computational validation, never reviewer
# or scholarly authority.
ScholarlyEffect = Literal[
    "none",
    "advisory",
    "scope_constraint",
    "eligibility_gate",
    "provenance_gate",
    "transformation",
    "generation",
    "evaluation",
]


class StrategySpec(BaseModel):
    """Server-owned description of one executable pipeline capability."""

    strategy_id: str = Field(min_length=1, max_length=120)
    version: int = Field(default=1, ge=1)
    family: StageFamily
    scholarly_effect: ScholarlyEffect
    label: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1200)
    input_type: str = Field(min_length=1, max_length=80)
    output_type: str = Field(min_length=1, max_length=80)
    deterministic: bool = True
    invokes_llm: bool = False
    capabilities: list[str] = Field(default_factory=list)
    config_schema: dict[str, Any] = Field(default_factory=dict)


class PipelineStageDefinition(BaseModel):
    """One node in a bounded, typed pipeline graph."""

    id: str = Field(min_length=1, max_length=120)
    strategy: str = Field(min_length=1, max_length=120)
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    next: list[str] = Field(default_factory=list, max_length=16)
    on_empty: str | None = Field(default=None, max_length=120)
    on_unavailable: str | None = Field(default=None, max_length=120)
    on_timeout: str | None = Field(default=None, max_length=120)
    on_error: str | None = Field(default=None, max_length=120)

    def edge_targets(self) -> list[str]:
        values = [*self.next, self.on_empty, self.on_unavailable, self.on_timeout, self.on_error]
        return [str(value) for value in values if value]


class PipelineDefinition(BaseModel):
    """Versioned declarative chain assembled from registered strategies."""

    pipeline_id: str = Field(min_length=1, max_length=160)
    version: int = Field(default=1, ge=1)
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=160)
    status: PipelineStatus = "draft"
    entry_stage_ids: list[str] = Field(min_length=1, max_length=16)
    stages: list[PipelineStageDefinition] = Field(min_length=1, max_length=64)
    built_in: bool = False
    derived_from: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)
    created_at: datetime | None = None
    created_by: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_local_graph(self) -> PipelineDefinition:
        stage_ids = [stage.id for stage in self.stages]
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("Pipeline stage IDs must be unique.")
        known = set(stage_ids)
        missing_entries = sorted(set(self.entry_stage_ids) - known)
        if missing_entries:
            raise ValueError(
                "Pipeline entry stage(s) do not exist: " + ", ".join(missing_entries)
            )
        missing_targets = sorted(
            {
                target
                for stage in self.stages
                for target in stage.edge_targets()
                if target not in known
            }
        )
        if missing_targets:
            raise ValueError(
                "Pipeline edge target(s) do not exist: " + ", ".join(missing_targets)
            )
        return self


class PipelineAssignment(BaseModel):
    """Maps an application feature/scope to an immutable pipeline version."""

    feature: str = Field(min_length=1, max_length=160)
    pipeline_id: str = Field(min_length=1, max_length=160)
    pipeline_version: int = Field(ge=1)
    scope: str = Field(default="system", min_length=1, max_length=80)
    scope_id: str | None = Field(default=None, max_length=240)
    override_allowed: bool = False
    source: str = Field(default="built_in", min_length=1, max_length=80)


class PipelineValidationIssue(BaseModel):
    level: Literal["error", "warning"]
    code: str
    message: str
    stage_id: str | None = None


class PipelineValidationResult(BaseModel):
    valid: bool
    issues: list[PipelineValidationIssue] = Field(default_factory=list)


class PipelineStageTrace(BaseModel):
    """Safe per-stage telemetry persisted with a pipeline run.

    Prompt bodies, secrets, full source text, and hidden reviewer values do not
    belong in this object. Those require purpose-specific privileged storage.
    """

    stage_id: str
    strategy_id: str
    strategy_version: int = 1
    status: Literal[
        "pending",
        "running",
        "completed",
        "skipped",
        "unavailable",
        "timed_out",
        "failed",
    ]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    elapsed_ms: int | None = Field(default=None, ge=0)
    input_count: int | None = Field(default=None, ge=0)
    output_count: int | None = Field(default=None, ge=0)
    parameters: dict[str, Any] = Field(default_factory=dict)
    provider: str | None = None
    model: str | None = None
    collection: str | None = None
    fallback_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    score_summary: dict[str, Any] = Field(default_factory=dict)


class PipelineRunTrace(BaseModel):
    run_id: str
    feature: str
    pipeline_id: str
    pipeline_version: int
    resolved_pipeline: dict[str, Any]
    resolved_hash: str
    owner: str | None = None
    status: Literal["running", "completed", "failed", "cancelled"]
    started_at: datetime
    finished_at: datetime | None = None
    total_elapsed_ms: int | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)
    stages: list[PipelineStageTrace] = Field(default_factory=list)
