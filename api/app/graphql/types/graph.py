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

"""Walkable cELF instance graph plus typed projections of its nodes."""
from __future__ import annotations

from typing import Any

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from .common import opt_float, opt_int, opt_str
from .research import GeneratedClaim
from .spans import SourceSpan


@strawberry.type(
    description=(
        "One field value with independent derivation, evaluation and authority. A value is never "
        "exposed without the provenance dimensions that qualify it."
    ),
)
class FieldAssertion:
    assertion_id: str
    field_id: str | None
    field_name: str | None
    value: JSON | None = strawberry.field(description="Schema-defined value; arbitrary by design.")
    derivation_method: str | None
    evaluation_status: str | None
    authority_status: str | None
    value_status: str | None
    confidence: float | None
    reason: str | None
    method: str | None
    actor: str | None
    model: str | None
    run_id: str | None
    record_revision: int | None
    evidence: JSON | None
    created_at: str | None
    supersedes_assertion_id: str | None
    is_current: bool = strawberry.field(description="Whether this is the field's selected current assertion.")

    @classmethod
    def from_details(cls, assertion_id: str, details: dict[str, Any]) -> FieldAssertion:
        evidence = details.get("evidence")
        return cls(
            assertion_id=assertion_id,
            field_id=opt_str(details.get("field_id")),
            field_name=opt_str(details.get("field_name")),
            value=JSON(details.get("value")),
            derivation_method=opt_str(details.get("derivation_method")),
            evaluation_status=opt_str(details.get("evaluation_status")),
            authority_status=opt_str(details.get("authority_status")),
            value_status=opt_str(details.get("value_status")),
            confidence=opt_float(details.get("confidence")),
            reason=opt_str(details.get("reason")),
            method=opt_str(details.get("method")),
            actor=opt_str(details.get("actor")),
            model=opt_str(details.get("model")),
            run_id=opt_str(details.get("run_id")),
            record_revision=opt_int(details.get("record_revision")),
            evidence=JSON(evidence) if isinstance(evidence, list) else None,
            created_at=opt_str(details.get("created_at")),
            supersedes_assertion_id=opt_str(details.get("supersedes_assertion_id")),
            is_current=bool(details.get("is_current")),
        )


@strawberry.type(description="A revision-bound evidence locator.")
class EvidenceRef:
    evidence_ref_id: str
    locator_kind: str | None
    record_id: str | None
    record_revision: int | None
    source_document_id: str | None


@strawberry.type(description="An edge of the instance graph, annotated from the normative relationship registry.")
class ResearchObjectEdge:
    id: str
    source: str
    target: str
    relation: str
    inverse_relation: str
    normative: bool
    source_cardinality: str | None
    target_cardinality: str | None
    profile: str | None
    status: str | None


@strawberry.type(description="A node of the instance graph. Typed projections resolve for their object_type only.")
class ResearchObjectNode:
    id: str
    object_type: str
    object_id: str
    label: str
    summary: str
    materialization: str = strawberry.field(
        description="materialized | embedded | reference | derived_view. Derived views are never canonical.",
    )
    status: str | None
    details: JSON
    raw_details: strawberry.Private[dict[str, Any]]

    @strawberry.field
    def source_span(self) -> SourceSpan | None:
        if self.object_type != "SourceSpan":
            return None
        return SourceSpan.from_locator(self.raw_details)

    @strawberry.field
    def field_assertion(self) -> FieldAssertion | None:
        if self.object_type != "FieldAssertion":
            return None
        return FieldAssertion.from_details(self.object_id, self.raw_details)

    @strawberry.field
    def evidence_ref(self) -> EvidenceRef | None:
        if self.object_type != "EvidenceRef":
            return None
        details = self.raw_details
        return EvidenceRef(
            evidence_ref_id=self.object_id,
            locator_kind=opt_str(details.get("locator_kind")),
            record_id=opt_str(details.get("record_id")),
            record_revision=opt_int(details.get("record_revision")),
            source_document_id=opt_str(details.get("source_document_id")),
        )

    @strawberry.field(description="The owner-scoped durable claim behind a GeneratedClaim node (batched).")
    async def generated_claim(self, info: Info) -> GeneratedClaim | None:
        if self.object_type != "GeneratedClaim":
            return None
        payload = await info.context.loaders.claims.load(self.object_id)
        return GeneratedClaim.from_payload(payload) if payload else None

    @classmethod
    def from_payload(cls, node: dict[str, Any]) -> ResearchObjectNode:
        details = node.get("details") if isinstance(node.get("details"), dict) else {}
        return cls(
            id=str(node["id"]),
            object_type=str(node["object_type"]),
            object_id=str(node["object_id"]),
            label=str(node.get("label") or ""),
            summary=str(node.get("summary") or ""),
            materialization=str(node.get("materialization") or "materialized"),
            status=opt_str(node.get("status")),
            details=JSON(details),
            raw_details=details,
        )


@strawberry.type(description="A finite, re-centerable cELF instance graph around one Record.")
class ResearchObjectGraph:
    specification_version: str
    root_id: str
    hidden_assertion_count: int
    record_state_origin: str = strawberry.field(
        description="client_snapshot: Record state came from the caller; claims/support are server-owned.",
    )
    nodes: list[ResearchObjectNode]
    edges: list[ResearchObjectEdge]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ResearchObjectGraph:
        return cls(
            specification_version=str(payload["specification_version"]),
            root_id=str(payload["root_id"]),
            hidden_assertion_count=int(payload.get("hidden_assertion_count") or 0),
            record_state_origin=str(payload.get("record_state_origin") or "client_snapshot"),
            nodes=[ResearchObjectNode.from_payload(node) for node in payload["nodes"]],
            edges=[
                ResearchObjectEdge(
                    id=str(edge["id"]),
                    source=str(edge["source"]),
                    target=str(edge["target"]),
                    relation=str(edge["relation"]),
                    inverse_relation=str(edge["inverse_relation"]),
                    normative=bool(edge.get("normative")),
                    source_cardinality=opt_str(edge.get("source_cardinality")),
                    target_cardinality=opt_str(edge.get("target_cardinality")),
                    profile=opt_str(edge.get("profile")),
                    status=opt_str(edge.get("status")),
                )
                for edge in payload["edges"]
            ],
        )
