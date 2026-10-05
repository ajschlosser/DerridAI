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

"""Server-only support observations; routes never execute or grant authority."""

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .graph_execution import StageHandler, StageResult
from .metadata_candidate_collection import (
    PERSON_INDEXING_SEMANTICS,
    CandidateBinding,
    CandidateCollector,
    CandidatePacket,
    candidate_binding,
)
from .models import ComplexitySpec, PipelineStageDefinition, PortSpec, StrategySpec


class CandidateSupport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    candidate_id: str
    status: Literal["exact_mention", "unchecked", "invalid_locator"]
    # A mention proves occurrence, never attribution or semantic correctness.
    semantic_support: Literal["unchecked"] = "unchecked"


class FieldRouteObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    field_name: str
    route: Literal["RESOLVE", "VERIFY", "INFER"]
    reason: Literal["exact_indexing_mention", "candidate_requires_verification", "no_candidates"]
    candidate_ids: tuple[str, ...]
    support: tuple[CandidateSupport, ...]
    authority: Literal["advisory"] = "advisory"


class RoutingObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    contract: Literal["metadata-candidate-observation-v1"] = "metadata-candidate-observation-v1"
    binding: CandidateBinding
    fields: tuple[FieldRouteObservation, ...]
    diagnostics: tuple[str, ...]
    observe_only: Literal[True] = True


def observe_candidate_routes(collector: CandidateCollector, packet: CandidatePacket) -> RoutingObservation:
    """Validate current locators without transferring historical evidence or authority.

    Only a single exact person-indexing value can suggest RESOLVE. Absence,
    corrections, rivals and semantic fields always require further evaluation.
    """
    if candidate_binding(collector.record, collector.schema, context=collector.context) != collector.binding:
        raise ValueError("Observation context changed after collection.")
    packet = collector.aggregate([packet])
    text = str(collector.record.get("text") or "")
    fields = []
    for name in collector.fields:
        candidates = [c for c in packet.candidates if c.field_name == name]
        support = []
        for candidate in candidates:
            if (candidate.field_id != collector.schema.field_id(name)
                    or candidate.semantic_compatibility_id != collector.schema.semantic_compatibility_id(name)):
                raise ValueError("Candidate field identity is incompatible.")
            ref = candidate.origin_ref
            status: Literal["exact_mention", "unchecked", "invalid_locator"] = "unchecked"
            # Historical evidence and hint-only projections never count as a current locator.
            if candidate.origin == "nlp":
                start, end = ref.get("start"), ref.get("end")
                valid = (
                    ref.get("record_id") == collector.binding.record_id
                    and ref.get("record_revision") == collector.binding.record_revision
                    and bool(collector.record.get("source_document_id"))
                    and ref.get("source_document_id") == collector.record.get("source_document_id")
                    and type(start) is int and type(end) is int
                    and 0 <= start < end <= len(text)
                    and isinstance(candidate.value, str) and text[start:end] == candidate.value
                )
                status = "exact_mention" if valid else "invalid_locator"
            support.append(CandidateSupport(candidate_id=candidate.candidate_id, status=status))
        eligible = (
            len(candidates) == 1 and candidates[0].kind == "value"
            and candidates[0].semantic_compatibility_id in PERSON_INDEXING_SEMANTICS
            and support[0].status == "exact_mention"
        )
        fields.append(FieldRouteObservation(
            field_name=name,
            route="RESOLVE" if eligible else "VERIFY" if candidates else "INFER",
            reason="exact_indexing_mention" if eligible else "candidate_requires_verification" if candidates else "no_candidates",
            candidate_ids=tuple(c.candidate_id for c in candidates), support=tuple(support),
        ))
    if any(c.field_name not in collector.fields for c in packet.candidates):
        raise ValueError("Candidate is outside requested fields.")
    return RoutingObservation(binding=collector.binding, fields=tuple(fields), diagnostics=packet.diagnostics)


def candidate_observation_strategy() -> StrategySpec:
    return StrategySpec(
        strategy_id="metadata.observe_candidate_routes", family="support_validation",
        scholarly_effect="advisory", label="Observe metadata candidate routes",
        description="Server-only route observations; no provider calls or canonical writes.",
        input_type="metadata_candidate_set", output_type="metadata_hypothesis_set",
        inputs=[PortSpec(name="candidates", data_type="metadata_candidate_set")],
        outputs=[PortSpec(name="observations", data_type="metadata_hypothesis_set")],
        complexity=ComplexitySpec(time="O(n)", space="O(n)", variables=["n"]),
    )


def candidate_observation_handler(collector: CandidateCollector) -> StageHandler:
    def run(_stage: PipelineStageDefinition, inputs: Mapping[str, Any]) -> StageResult:
        return StageResult({"observations": observe_candidate_routes(collector, inputs["candidates"])})
    return run
