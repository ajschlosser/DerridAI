# Copyright 2026 Aaron John Schlosser, PhD.
"""Generated claims, support bindings and advisory similar-claim precedents."""
from __future__ import annotations

from typing import Any

import strawberry
from starlette.concurrency import run_in_threadpool
from strawberry.scalars import JSON
from strawberry.types import Info

from ..errors import Unavailable
from .common import opt_int, opt_str
from .spans import SourceSpan


@strawberry.type(description="A durable support relation between a generated claim and Record evidence.")
class SupportBinding:
    support_binding_id: str
    claim_id: str
    record_id: str
    record_revision: int | None
    source_document_id: str | None
    relation: str
    validation_status: str = strawberry.field(
        description="unvalidated | validated | stale | rejected | unresolved. Stale/unresolved stay visible.",
    )
    citation: JSON | None = strawberry.field(description="Deterministic citation rendered when bound.")
    created_at: str | None
    raw_source_spans: strawberry.Private[list[dict[str, Any]]]

    @strawberry.field(description="Medium-aware source spans bound as evidence.")
    def source_spans(self) -> list[SourceSpan]:
        return [SourceSpan.from_locator(span) for span in self.raw_source_spans]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> SupportBinding:
        citation = payload.get("citation")
        return cls(
            support_binding_id=str(payload.get("support_binding_id") or ""),
            claim_id=str(payload.get("claim_id") or ""),
            record_id=str(payload.get("record_id") or ""),
            record_revision=opt_int(payload.get("record_revision")),
            source_document_id=opt_str(payload.get("source_document_id")),
            relation=str(payload.get("relation") or ""),
            validation_status=str(payload.get("validation_status") or "unvalidated"),
            citation=JSON(citation) if isinstance(citation, dict) else None,
            created_at=opt_str(payload.get("created_at")),
            raw_source_spans=[span for span in payload.get("source_spans") or [] if isinstance(span, dict)],
        )


@strawberry.type(description="Record support carried by an advisory validated-claim precedent.")
class SimilarClaimSupport:
    record_id: str
    record_revision: int | None
    relation: str | None
    semantic: JSON = strawberry.field(description="Checked attribution snapshot (speaker, position_holder, …).")


@strawberry.type(description="Advisory precedent only: similarity never asserts evidentiary support.")
class SimilarValidatedClaim:
    claim_id: str
    claim_text: str
    similarity: float
    validated_by: str | None
    validated_at: str | None
    advisory: bool
    support: list[SimilarClaimSupport]

    @classmethod
    def from_payload(cls, item: dict[str, Any]) -> SimilarValidatedClaim:
        return cls(
            claim_id=str(item.get("claim_id") or ""),
            claim_text=str(item.get("claim_text") or ""),
            similarity=float(item.get("similarity") or 0.0),
            validated_by=opt_str(item.get("validated_by")),
            validated_at=opt_str(item.get("validated_at")),
            advisory=True,
            support=[
                SimilarClaimSupport(
                    record_id=str(entry.get("record_id") or ""),
                    record_revision=opt_int(entry.get("record_revision")),
                    relation=opt_str(entry.get("relation")),
                    semantic=JSON(entry.get("semantic") if isinstance(entry.get("semantic"), dict) else {}),
                )
                for entry in item.get("support") or []
                if isinstance(entry, dict)
            ],
        )


@strawberry.type(description="A claim produced by a research run, owner-scoped.")
class GeneratedClaim:
    claim_id: str
    claim_text: str
    run_id: str | None
    response_record_id: str | None
    answer_start: int | None
    answer_end: int | None
    validation_status: str
    validated_by: str | None
    validated_at: str | None
    created_at: str | None
    payload: strawberry.Private[dict[str, Any]]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> GeneratedClaim:
        return cls(
            claim_id=str(payload.get("claim_id") or ""),
            claim_text=str(payload.get("claim_text") or ""),
            run_id=opt_str(payload.get("run_id")),
            response_record_id=opt_str(payload.get("response_record_id")),
            answer_start=opt_int(payload.get("answer_start")),
            answer_end=opt_int(payload.get("answer_end")),
            validation_status=str(payload.get("validation_status") or "unvalidated"),
            validated_by=opt_str(payload.get("validated_by")),
            validated_at=opt_str(payload.get("validated_at")),
            created_at=opt_str(payload.get("created_at")),
            payload=payload,
        )

    @strawberry.field(description="Durable support bindings for this claim (batched per request).")
    async def support_bindings(self, info: Info) -> list[SupportBinding]:
        rows = await info.context.loaders.support_bindings_by_claim.load(self.claim_id)
        return [SupportBinding.from_payload(row) for row in rows]

    @strawberry.field(description="Advisory validated-claim precedents (REST: GET /api/derridai/claims/{id}/similar).")
    async def similar_validated_claims(self, info: Info, limit: int = 5) -> list[SimilarValidatedClaim]:
        from ...celf_queries import claims as claim_queries

        access = info.context.access
        try:
            result = await run_in_threadpool(
                claim_queries.similar_claims,
                access,
                self.payload,
                limit=limit,
                index_factory=claim_queries.default_claim_index,
            )
        except Exception as exc:
            raise Unavailable(f"Validated-claim memory unavailable: {exc}") from exc
        return [SimilarValidatedClaim.from_payload(item) for item in result.get("items") or []]
