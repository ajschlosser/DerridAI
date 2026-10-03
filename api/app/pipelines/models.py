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

"""Typed contracts for configurable retrieval and model pipelines.

Pipeline definitions are declarative application state. They may reference only
server-registered strategies; no user-authored Python, SQL, shell, or network
code is executable through this contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_serializer, model_validator

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


# What flows between stages. A port declares exactly one of these and the
# validator refuses any wiring that would hand a stage something else.
# Constants are tuning values, so they are small, finite numbers.
CONSTANT_BOUND = 1_000_000.0

DataType = Literal[
    "query",
    "candidate_set",
    "context_packet",
    "model_output",
    "evaluation",
    "number",
    "any",
]
CostDriver = Literal["cpu", "storage", "embedding", "model_inference", "llm_generation"]
CardinalityRule = Literal["same", "pool", "config_cap", "fixed", "sum_inputs"]


class PortSpec(BaseModel):
    """One named, typed input or output of a strategy."""

    name: str = Field(min_length=1, max_length=60)
    data_type: DataType
    # An optional input may stay unconnected; a required one must be bound.
    required: bool = True
    # A port that merges several upstream sources (a union of candidate sets).
    multiple: bool = False
    # A tuning port: it may take a fixed number instead of another stage's output.
    # Only ports that declare this accept a constant; query/candidate ports never do.
    accepts_constant: bool = False
    minimum: float | None = None
    maximum: float | None = None


class OutputCardinality(BaseModel):
    """How many items a stage can hand downstream, for pipeline-level bounds."""

    rule: CardinalityRule = "same"
    # ``config_cap``: the stage keeps at most config[key] items (else ``default``).
    config_key: str | None = None
    default: int | None = Field(default=None, ge=1)


class ComplexitySpec(BaseModel):
    """Declared algorithmic cost of one strategy, in the variables below.

    ``n`` is the size of the stage's incoming candidate set, ``N`` the size of the
    collection or Record scope it searches, ``k`` the number kept, ``L`` the text
    length per item and ``q`` the query length. The formulas are code-owned
    declarations reviewed against the implementation, not measurements; observed
    latency is reported separately and compared against them.
    """

    time: str = Field(min_length=1, max_length=80)
    space: str = Field(min_length=1, max_length=80)
    variables: list[str] = Field(default_factory=list)
    driver: CostDriver = "cpu"
    # Model invocations per run of the stage, as a formula ("0", "1", "n").
    model_calls: str = "0"
    # Whether the cost grows with the collection/scope size N and not only n.
    scales_with_scope: bool = False
    # 0 constant … 7 generation. Orders stages when naming the dominant cost.
    order: int = Field(default=0, ge=0, le=9)
    cardinality: OutputCardinality = Field(default_factory=OutputCardinality)


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
    # Named, typed ports. The first input/output is the primary data port that
    # ``input_type`` / ``output_type`` summarise.
    inputs: list[PortSpec] = Field(default_factory=list)
    outputs: list[PortSpec] = Field(default_factory=list)
    complexity: ComplexitySpec | None = None


class InputBinding(BaseModel):
    """Where one stage input gets its value.

    ``stage`` binds to a named output of an upstream stage; ``run_input`` binds
    to a value the consuming workflow supplies for every run (its purpose
    declares which); ``constant`` fixes a number on a tuning port that declares
    it accepts one. A port with no explicit binding is wired implicitly from
    the graph edges, and the resolved wiring says which.
    """

    source: Literal["stage", "run_input", "constant"]
    stage: str | None = Field(default=None, max_length=120)
    output: str | None = Field(default=None, max_length=60)
    name: str | None = Field(default=None, max_length=60)
    # Only for ``constant``; omitted from the serialised form otherwise so the
    # identity hashes of pipelines saved before constants existed stay valid.
    value: float | None = Field(default=None, ge=-CONSTANT_BOUND, le=CONSTANT_BOUND)

    @model_validator(mode="after")
    def _shape(self) -> InputBinding:
        if self.source == "stage" and not self.stage:
            raise ValueError("A stage binding names the producing stage.")
        if self.source == "run_input" and not self.name:
            raise ValueError("A run-input binding names the run input.")
        if self.source == "constant" and self.value is None:
            raise ValueError("A constant binding carries a value.")
        if self.source != "constant" and self.value is not None:
            raise ValueError("Only a constant binding carries a value.")
        return self

    @model_serializer(mode="wrap")
    def _omit_absent_value(self, handler: Any) -> dict[str, Any]:
        data = handler(self)
        if data.get("value") is None:
            data.pop("value", None)
        return data


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
    # Explicit input wiring per port name. Absent ports are wired from the
    # edges. Omitted from the serialised form while empty so pipeline identity
    # hashes recorded before bindings existed stay valid.
    inputs: dict[str, list[InputBinding]] = Field(default_factory=dict)

    @model_serializer(mode="wrap")
    def _omit_empty_inputs(self, handler: Any) -> dict[str, Any]:
        data = handler(self)
        if not data.get("inputs"):
            data.pop("inputs", None)
        return data

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
