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

"""Gated, server-only experimental routing across every candidate source.

The canonical loader must authorize the caller before returning a current binding.
The visibility predicate must rehydrate/scope historical origins against canonical
state. These required server callbacks are never supplied by pipeline JSON. This
runner is not registered, persisted, or exposed as a client transport.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .graph_execution import GraphExecutor, StageHandler, StageResult
from .metadata_candidate_collection import (
    COLLECTORS,
    CandidateBinding,
    CandidateCollector,
    CandidatePacket,
    MetadataCandidate,
    candidate_binding,
    candidate_collection_strategies,
)
from .metadata_candidate_routing import (
    CandidateRouting,
    Evaluator,
    FieldEvaluation,
    InferenceRequest,
    MetadataProposal,
    ProposalPacket,
    candidate_routing_strategies,
)
from .models import PipelineDefinition, PipelineStageDefinition, PipelineStageTrace
from .purposes import PipelinePurposeSpec, RunInputSpec
from .registry import StrategyRegistry


class ReviewerProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    proposal: MetadataProposal
    support: Literal["mention_only", "model_inferred", "unresolved"]


class ReviewerPacket(BaseModel):
    """Review projection; withheld fields contain names only, never proposals."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    binding: CandidateBinding
    proposals: tuple[ReviewerProposal, ...]
    withheld_fields: tuple[str, ...]
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class RoutingSessionResult:
    # Internal server artifact; only reviewer_packet is a review projection.
    server_proposals: ProposalPacket
    reviewer_packet: ReviewerPacket
    stages: tuple[PipelineStageTrace, ...]
    pipeline_hash: str


def _definition() -> tuple[PipelineDefinition, PipelinePurposeSpec]:
    def bind(stage: str, output: str) -> dict[str, str]:
        return {"source": "stage", "stage": stage, "output": output}

    collect_ids = ["collect_" + name.rsplit("_", 1)[-1] for name in COLLECTORS]
    stages: list[dict[str, Any]] = [
        {"id": stage, "strategy": strategy, "next": ["aggregate"]}
        for stage, strategy in zip(collect_ids, COLLECTORS, strict=True)
    ]
    stages.extend([
        {"id": "aggregate", "strategy": "metadata.aggregate_candidates", "next": ["route"],
         "inputs": {"candidates": [bind(stage, "candidates") for stage in collect_ids]}},
        {"id": "route", "strategy": "metadata.route_candidates", "next": ["resolve", "verify", "infer", "merge"]},
        {"id": "resolve", "strategy": "metadata.resolve_candidates", "next": ["merge"],
         "inputs": {"tasks": [bind("route", "resolve")]}},
        {"id": "verify", "strategy": "metadata.verify_candidates", "next": ["infer", "merge"],
         "inputs": {"tasks": [bind("route", "verify")]}},
        {"id": "infer", "strategy": "metadata.infer_scoped", "next": ["merge"],
         "inputs": {"tasks": [bind("route", "infer"), bind("verify", "unresolved")]}},
        {"id": "merge", "strategy": "metadata.aggregate_proposals",
         "inputs": {"proposals": [bind("route", "preserved"), *[
             bind(stage, "proposals") for stage in ("resolve", "verify", "infer")
         ]]}},
    ])
    purpose = PipelinePurposeSpec(
        purpose_id="metadata_candidate_shadow", category="metadata", label="Metadata candidate shadow",
        description="Server-only gated candidate evaluation with mandatory review.",
        consuming_feature="metadata_candidate_shadow", consumer="server-only",
        input_semantics="Authorized current Record snapshot", output_semantics="Advisory proposals",
        authority_semantics="No canonical writes or reviewer approval", output_type="metadata_proposal_set",
        run_inputs=[RunInputSpec(name="context", data_type="any")],
    )
    return PipelineDefinition(
        pipeline_id="metadata.candidate_shadow", name="Metadata candidate shadow", purpose=purpose.purpose_id,
        entry_stage_ids=collect_ids, stages=[PipelineStageDefinition.model_validate(stage) for stage in stages],
    ), purpose


class CandidateRoutingSession:
    """One serial call-local graph with live access/context and visibility gates.

    Construct the collector only after authorizing its source reads. read_current
    must repeat that authorization and derive the full binding from canonical
    Record/schema/reviewer/memory/configuration state. Matching a caller-provided
    hash is not authorization. Provider adapters still own quotas and cancellation
    of in-flight transport. This runner only prevents further work or delivery.
    """

    def __init__(
        self, collector: CandidateCollector, *,
        read_current: Callable[[], CandidateBinding],
        candidate_visible: Callable[[MetadataCandidate], bool],
        verify: Evaluator, infer: Evaluator, blind_fields: Sequence[str] = (),
    ) -> None:
        self.collector = collector
        self.read_current = read_current
        self.candidate_visible = candidate_visible
        self.blind_fields = frozenset(blind_fields)
        if self.blind_fields - set(collector.fields):
            raise ValueError("Blind fields must belong to the requested scope.")
        if set(collector.context.get("blind_fields") or []) != self.blind_fields:
            raise ValueError("Blind policy must be included in the context binding.")
        self.adapter = CandidateRouting(
            collector, verify=self._evaluator(verify), infer=self._evaluator(infer),
        )

    def _guard(self) -> None:
        try:
            current = CandidateBinding.model_validate(self.read_current())
        except InterruptedError:
            raise InterruptedError("Routing cancelled.") from None
        except Exception:
            raise ValueError("Routing access/context check failed.") from None
        if (current != self.collector.binding or candidate_binding(
            self.collector.record, self.collector.schema, context=self.collector.context,
        ) != self.collector.binding):
            raise ValueError("Routing canonical context changed.")

    def _evaluator(self, evaluate: Evaluator) -> Evaluator:
        def run(task: InferenceRequest) -> FieldEvaluation:
            self._guard()
            result = evaluate(task)
            self._guard()
            return result
        return run

    def _aggregate(
        self, _stage: PipelineStageDefinition, inputs: Mapping[str, Any],
    ) -> StageResult:
        # Recheck scoped candidates before aggregate limits and routing. Source
        # collectors remain bounded; their inputs must already be scoped.
        packets = []
        for packet in inputs["candidates"]:
            packet = CandidatePacket.model_validate(packet.model_dump())
            if packet.binding != self.collector.binding:
                raise ValueError("Stale candidate packet.")
            visible = []
            diagnostics = list(packet.diagnostics)
            for candidate in packet.candidates:
                if (candidate.field_name in self.blind_fields
                        and candidate.origin in {"exact_memory", "reviewed_precedent"}):
                    diagnostics.append("blind_memory_withheld")
                    continue
                allowed = self.candidate_visible(candidate.model_copy(deep=True))
                if type(allowed) is not bool:
                    raise ValueError("Candidate visibility requires an explicit decision.")
                if allowed:
                    visible.append(candidate)
                else:
                    diagnostics.append("candidate_not_visible")
            packets.append(CandidatePacket(
                binding=packet.binding, candidates=tuple(visible), diagnostics=tuple(diagnostics),
            ))
        return StageResult({"candidates": self.collector.aggregate(packets)})

    def _handler(self, operation: StageHandler) -> StageHandler:
        def run(stage: PipelineStageDefinition, inputs: Mapping[str, Any]) -> StageResult:
            self._guard()
            result = operation(stage, inputs)
            self._guard()
            return result
        return run

    def run(self) -> RoutingSessionResult:
        self._guard()
        pipeline, purpose = _definition()
        handlers = self.collector.handlers() | self.adapter.handlers()
        handlers["metadata.aggregate_candidates"] = self._aggregate
        executor = GraphExecutor(
            pipeline, registry=StrategyRegistry(
                candidate_collection_strategies() + candidate_routing_strategies()
            ), purpose=purpose, handlers={key: self._handler(value) for key, value in handlers.items()},
        )
        result = executor.run({"context": self.collector.binding})
        self._guard()
        packet = self.adapter.aggregate([result.terminal_outputs["merge"]["proposals"]])
        proposals = tuple(ReviewerProposal(
            proposal=proposal.model_copy(deep=True),
            support="unresolved" if proposal.evaluation.outcome != "supported_value"
            else "mention_only" if proposal.route == "RESOLVE" else "model_inferred",
        ) for proposal in packet.proposals if proposal.field_name not in self.blind_fields)
        self._guard()
        return RoutingSessionResult(
            server_proposals=packet,
            reviewer_packet=ReviewerPacket(
                binding=packet.binding, proposals=proposals,
                withheld_fields=tuple(name for name in self.collector.fields if name in self.blind_fields),
                diagnostics=packet.diagnostics,
            ),
            stages=tuple(result.stages), pipeline_hash=result.pipeline_hash,
        )
