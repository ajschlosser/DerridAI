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

"""Read-only candidate collection foundation; not a production routing adapter.

All values remain advisory, including exact adjudication memory and reviewed
precedents. Neither historical evidence nor an NLP mention establishes current
Record support. The caller supplies canonical, reviewer-visible exemplars and
dependency epochs after applying access and blind-review policy.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import document_intelligence, metadata_adjudication_cache, nlp_annotations
from ..corpus_document_context import record_fingerprint
from ..field_assertions import field_identity
from ..metadata_schema import SEMANTIC_COMPATIBILITY_IDS, MetadataSchema
from ..semantic_identity import canonical_json, canonical_value_key
from .graph_execution import StageHandler, StageResult
from .models import ComplexitySpec, PipelineStageDefinition, PortSpec, StrategySpec

Origin = Literal["nlp", "document_intelligence", "exact_memory", "reviewed_precedent"]
CandidateKind = Literal["value", "absence", "correction"]
COLLECTION_CONTRACT: Literal["metadata-candidate-collection-v1"] = "metadata-candidate-collection-v1"
PERSON_INDEXING_SEMANTICS = frozenset({"derridai.indexing.persons"})
MAX_PER_FIELD = 32
COLLECTORS = (
    "metadata.collect_nlp", "metadata.collect_document_intelligence",
    "metadata.collect_exact_memory", "metadata.collect_reviewed_precedents",
)


def candidate_collection_strategies() -> list[StrategySpec]:
    """Contracts for server-only observation graphs, not the public registry."""
    specs = []
    for name in (*COLLECTORS, "metadata.aggregate_candidates"):
        aggregate = name == "metadata.aggregate_candidates"
        specs.append(StrategySpec(
            strategy_id=name, family="fusion" if aggregate else "candidate_generation",
            scholarly_effect="advisory", label=name,
            description="Read-only, context-bound metadata candidates; no support or authority decision.",
            input_type="metadata_candidate_set" if aggregate else "any",
            output_type="metadata_candidate_set",
            inputs=[PortSpec(
                name="candidates" if aggregate else "context",
                data_type="metadata_candidate_set" if aggregate else "any", multiple=aggregate,
            )],
            outputs=[PortSpec(name="candidates", data_type="metadata_candidate_set")],
            complexity=ComplexitySpec(time="O(n)", space="O(n)", variables=["n"]),
        ))
    return specs


class CandidateBinding(BaseModel):
    """Exact dependency identity, including same-revision edits and reviewer scope."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    contract: Literal["metadata-candidate-collection-v1"] = COLLECTION_CONTRACT
    record_id: str = Field(min_length=1)
    record_revision: int | str
    source_fingerprint: str
    schema_hash: str
    context_hash: str


class MetadataCandidate(BaseModel):
    """One origin's value; evidence locators belong to that origin's Record."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    candidate_id: str
    field_id: str
    field_name: str
    semantic_compatibility_id: str | None
    value: Any
    kind: CandidateKind = "value"
    origin: Origin
    canonical_key: str | None
    origin_ref: dict[str, Any]
    observations: dict[str, Any] = Field(default_factory=dict)
    # Code-owned constants: collection can never assert authority/support.
    authority: Literal["advisory"] = "advisory"
    current_record_support: Literal["unchecked"] = "unchecked"


class CandidatePacket(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    binding: CandidateBinding
    candidates: tuple[MetadataCandidate, ...] = ()
    diagnostics: tuple[str, ...] = ()


def candidate_binding(
    record: dict[str, Any], schema: MetadataSchema, *, context: Mapping[str, Any]
) -> CandidateBinding:
    """Context must include reviewer scope and memory/identity/configuration epochs.

    Projection payloads and existing assertions are included in the fingerprint;
    a refreshed projection or human decision invalidates even without a revision.
    Only the digest is retained, never sealed values or provider credentials.
    """
    if not record.get("record_id") or record.get("record_revision") is None:
        raise ValueError("Candidate collection requires persistent Record identity/revision.")
    if not context.get("reviewer_scope"):
        raise ValueError("Candidate collection requires an explicit reviewer scope.")
    dependencies = {
        "context": dict(context),
        "fields": {name: record.get(name) for name in schema.field_names()},
        "assertions": record.get("field_assertions"),
        "selected_assertions": record.get("current_field_assertions"),
        "field_status": record.get("metadata_field_status"),
        "human_touched_fields": record.get("human_touched_fields"),
        "evidence": record.get("metadata_evidence"),
        "nlp": record.get("nlp_candidates"),
        "document_intelligence": record.get("document_intelligence"),
    }
    return CandidateBinding(
        record_id=str(record["record_id"]),
        record_revision=record["record_revision"],
        source_fingerprint=record_fingerprint(record),
        schema_hash=schema.content_hash(),
        context_hash=hashlib.sha256(canonical_json(dependencies).encode("utf-8")).hexdigest(),
    )


class CandidateCollector:
    """Call-local snapshot, schema-scoped inputs, bounded outputs, no corpus writes."""

    def __init__(
        self,
        record: dict[str, Any],
        schema: MetadataSchema,
        *,
        fields: Sequence[str],
        context: Mapping[str, Any],
        exemplars: Mapping[str, Sequence[dict[str, Any]]] | None = None,
        exact_lookup: Callable[..., dict[str, Any] | None] = metadata_adjudication_cache.suggestions,
    ) -> None:
        self.record = deepcopy(record)
        self.schema = schema.model_copy(deep=True)
        self.fields = tuple(dict.fromkeys(fields))
        unknown = set(self.fields) - set(schema.field_names())
        if unknown:
            raise ValueError("Candidate collection requested unknown schema fields.")
        # Canonical exemplars must already be scoped to the caller's reviewer.
        self.exemplars = deepcopy(dict(exemplars or {}))
        self.context = deepcopy(dict(context))
        self.context["requested_fields"] = list(self.fields)
        self.context["exemplars"] = self.exemplars
        self.exact_rows = {}
        for name in self.fields:
            definition = next((item for item in self.schema.fields if item.name == name), None)
            cardinality = "list" if definition and definition.type == "list" else "single"
            self.exact_rows[name] = deepcopy(exact_lookup(
                record_id=str(self.record["record_id"]), text=str(self.record.get("text") or ""),
                field=name, cardinality=cardinality, schema_version=self.schema.schema_version,
            ))
        self.context["exact_memory"] = self.exact_rows
        self.binding = candidate_binding(self.record, self.schema, context=self.context)

    def _candidate(
        self, field: str, value: Any, origin: Origin, origin_ref: dict[str, Any],
        *, kind: CandidateKind = "value", observations: dict[str, Any] | None = None,
    ) -> MetadataCandidate:
        profile = self.schema.equivalence_profile_for(field)
        key = canonical_value_key(
            value, profile=profile, language=str(self.record.get("language") or "")
        )
        payload = {
            "binding": self.binding.model_dump(), "field_id": self.schema.field_id(field),
            "value": value, "kind": kind, "origin": origin, "origin_ref": origin_ref,
            "observations": observations or {},
        }
        return MetadataCandidate(
            candidate_id="mc-" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest(),
            field_id=self.schema.field_id(field), field_name=field,
            semantic_compatibility_id=self.schema.semantic_compatibility_id(field),
            value=deepcopy(value), kind=kind, origin=origin, canonical_key=key,
            origin_ref=deepcopy(origin_ref), observations=deepcopy(observations or {}),
        )

    def _packet(self, candidates: list[MetadataCandidate], diagnostics: list[str]) -> CandidatePacket:
        counts: dict[str, int] = {}
        kept = []
        seen = set()
        for candidate in candidates:
            if candidate.candidate_id in seen:
                continue
            seen.add(candidate.candidate_id)
            count = counts.get(candidate.field_id, 0)
            if count >= MAX_PER_FIELD:
                diagnostics.append("candidate_limit_reached")
                continue
            counts[candidate.field_id] = count + 1
            kept.append(candidate)
        return CandidatePacket(
            binding=self.binding, candidates=tuple(kept),
            diagnostics=tuple(dict.fromkeys(diagnostics)),
        )

    def collect_nlp(self) -> CandidatePacket:
        candidates = []
        diagnostics: list[str] = []
        source_names = {
            name: next((builtin for builtin, semantic_id in SEMANTIC_COMPATIBILITY_IDS.items()
                        if semantic_id == self.schema.semantic_compatibility_id(name)), name)
            for name in self.fields
        }
        spans = nlp_annotations.current_field_candidates(self.record, set(source_names.values()))
        projection = self.record.get("nlp_candidates") or {}
        if not spans:
            diagnostics.append(
                "nlp_failed" if projection.get("status") in {"failed", "error"}
                else "nlp_unavailable" if projection.get("status") != "ok"
                else "nlp_stale" if projection.get("text_sha256") != nlp_annotations.text_digest(str(self.record.get("text") or ""))
                else "nlp_empty"
            )
        text = str(self.record.get("text") or "")
        for field in self.fields:
            for span in spans.get(source_names[field], []):
                start, end, value = span.get("start"), span.get("end"), span.get("text")
                if (
                    type(start) is not int or type(end) is not int
                    or not isinstance(value, str) or not value
                    or not 0 <= start < end <= len(text) or text[start:end] != value
                ):
                    diagnostics.append("invalid_nlp_span")
                    continue
                candidates.append(self._candidate(field, value, "nlp", {
                    "record_id": self.binding.record_id,
                    "record_revision": self.binding.record_revision,
                    "source_document_id": self.record.get("source_document_id"),
                    "start": start, "end": end,
                }, observations={
                    key: projection.get(key) for key in ("engine", "engine_version", "model", "text_sha256")
                } | {"tag": span.get("tag"), "source": span.get("source")}))
        return self._packet(candidates, diagnostics)

    def collect_document_intelligence(self) -> CandidatePacket:
        # Reuse the provider-neutral, digest/source-bound hints contract. Hints
        # have no exact locator and MUST remain distinct from source evidence.
        candidates = []
        hints = document_intelligence.prompt_hints(self.record, ["persons"]) if any(
            self.schema.semantic_compatibility_id(name) in PERSON_INDEXING_SEMANTICS
            for name in self.fields
        ) else {}
        for field in self.fields:
            semantic_id = self.schema.semantic_compatibility_id(field)
            if semantic_id not in PERSON_INDEXING_SEMANTICS:
                continue
            for value in hints.get("person_candidates", []):
                candidates.append(self._candidate(field, value, "document_intelligence", {
                    "record_id": self.binding.record_id,
                    "record_revision": self.binding.record_revision,
                }, observations={"hint_kind": "person_candidates"}))
        projection = self.record.get("document_intelligence") or {}
        diagnostic = (
            "document_intelligence_failed" if projection.get("status") in {"failed", "error"}
            else "document_intelligence_unavailable" if projection.get("status") != "ok"
            else "document_intelligence_stale" if not document_intelligence.record_annotations_current(self.record)
            else "document_intelligence_empty"
        )
        return self._packet(candidates, [] if hints else [diagnostic])

    def collect_exact_memory(self) -> CandidatePacket:
        candidates = []
        diagnostics: list[str] = []
        for field in self.fields:
            row = self.exact_rows[field]
            if row is None:
                continue
            # Legacy memory lacking stable field/schema provenance is not eligible.
            if row.get("field_id") != self.schema.field_id(field) or row.get("schema_version") != self.schema.schema_version:
                diagnostics.append("incompatible_exact_memory")
                continue
            decision = row.get("decision")
            if decision not in {"value", "absence", "correction"}:
                diagnostics.append("invalid_exact_memory")
                continue
            kind: CandidateKind = "absence" if decision == "absence" else "correction" if decision == "correction" else "value"
            value = row.get("latest_value")
            if (kind != "absence" and value in (None, "", [])) or (kind == "absence" and value not in (None, "", [])):
                diagnostics.append("invalid_exact_memory")
                continue
            candidates.append(self._candidate(field, value, "exact_memory", {
                "record_id": self.binding.record_id,
                "record_revision": self.binding.record_revision,
                "text_sha512": hashlib.sha512(str(self.record.get("text") or "").encode("utf-8")).hexdigest(),
            }, kind=kind))
        return self._packet(candidates, diagnostics)

    def collect_reviewed_precedents(self) -> CandidatePacket:
        candidates = []
        diagnostics: list[str] = []
        for field in self.fields:
            for exemplar in self.exemplars.get(field, []):
                ref = exemplar.get("evidence_ref") or {}
                if (
                    exemplar.get("field_id") not in {self.schema.field_id(field), field_identity(field, self.schema)}
                    or exemplar.get("assertion_status") not in {"human_confirmed", "human_override"}
                    or not exemplar.get("metadata_exemplar_id")
                    or not ref.get("record_id") or ref.get("record_revision") is None
                    or not ref.get("source_document_id") or not ref.get("block_ids")
                    or ref.get("record_id") != exemplar.get("record_id")
                    or ref.get("record_revision") != exemplar.get("record_revision")
                    or ref.get("source_document_id") != exemplar.get("source_document_id")
                ):
                    diagnostics.append("ineligible_reviewed_precedent")
                    continue
                raw_kind = exemplar.get("kind", "positive")
                if raw_kind not in {"positive", "absence", "correction"}:
                    diagnostics.append("ineligible_reviewed_precedent")
                    continue
                kind: CandidateKind = "value" if raw_kind == "positive" else raw_kind
                value = exemplar.get("field_value")
                if (kind != "absence" and value in (None, "", [])) or (kind == "absence" and value not in (None, "", [])):
                    diagnostics.append("ineligible_reviewed_precedent")
                    continue
                candidates.append(self._candidate(field, value, "reviewed_precedent", {
                    **ref, "exemplar_id": exemplar["metadata_exemplar_id"],
                }, kind=kind, observations={"rejected_value": exemplar.get("rejected_value")} if kind == "correction" else {}))
        return self._packet(candidates, diagnostics)

    def aggregate(self, packets: Sequence[CandidatePacket]) -> CandidatePacket:
        candidates: dict[str, MetadataCandidate] = {}
        diagnostics: list[str] = []
        for packet in packets:
            if packet.binding != self.binding:
                raise ValueError("Stale or incompatible candidate packet.")
            diagnostics.extend(packet.diagnostics)
            for candidate in packet.candidates:
                candidates.setdefault(candidate.candidate_id, candidate)
        # Equivalent values retain each contributing origin. Rival values,
        # explicit absence and corrections are never overwritten by consensus.
        return self._packet(list(candidates.values()), diagnostics)

    def handlers(self) -> dict[str, StageHandler]:
        """Server-owned handlers for isolated graphs; absent from the public catalog."""
        collectors = {
            "metadata.collect_nlp": self.collect_nlp,
            "metadata.collect_document_intelligence": self.collect_document_intelligence,
            "metadata.collect_exact_memory": self.collect_exact_memory,
            "metadata.collect_reviewed_precedents": self.collect_reviewed_precedents,
        }

        def handler(operation: Callable[[], CandidatePacket]) -> StageHandler:
            def run(_stage: PipelineStageDefinition, _inputs: Mapping[str, Any]) -> StageResult:
                if _inputs["context"] != self.binding:
                    raise ValueError("Collection graph has an incompatible context binding.")
                return StageResult({"candidates": operation()})
            return run

        def aggregate(_stage: PipelineStageDefinition, inputs: Mapping[str, Any]) -> StageResult:
            return StageResult({"candidates": self.aggregate(inputs["candidates"])})

        return {name: handler(operation) for name, operation in collectors.items()} | {
            "metadata.aggregate_candidates": aggregate,
        }

