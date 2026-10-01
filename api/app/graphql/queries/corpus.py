# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Any

import strawberry
from starlette.concurrency import run_in_threadpool
from strawberry.scalars import JSON
from strawberry.types import Info

from ...celf_queries import corpus_records as corpus_queries
from ...celf_queries import document_intelligence_reads
from ...corpus_review_queue import QueueFilter
from ..errors import translate
from ..permissions import classify, require_admin
from ..types.corpus import CorpusQueueRow, CorpusRecord, CorpusReviewQueuePage
from ..types.documents import DocumentIntelligenceRun

# Record graphs expose Record text-bearing assertion values and node details.
# REST keeps /api/pdf/* administrator-only, so the GraphQL root does too until a
# researcher-safe projection is designed (docs/GRAPHQL.md).
classify("corpus_build", "admin")


@strawberry.type(description="One PDF Corpus Builder build's reviewable Records (REST: /api/pdf/corpus-builds/{id}).")
class CorpusBuildReview:
    build_id: str

    async def _records(self, info: Info) -> list[dict[str, Any]] | None:
        return await info.context.loaders.corpus_build_records.load(self.build_id)

    @strawberry.field(
        description="The paged, filtered review queue (REST: GET /api/pdf/corpus-builds/{id}/records).",
    )
    async def review_queue(
        self,
        info: Info,
        offset: int = 0,
        limit: int = 50,
        needs_review: bool | None = None,
        disposition: str | None = None,
        metadata_incomplete: bool | None = None,
        source_problem: bool | None = None,
        review_queue: str | None = None,
        query: str = "",
    ) -> CorpusReviewQueuePage:
        context = require_admin(info)
        filters = QueueFilter(
            needs_review=needs_review, disposition=disposition, metadata_incomplete=metadata_incomplete,
            source_problem=source_problem, review_queue=review_queue, query=query,
        )
        try:
            records = await self._records(info)
            payload = await run_in_threadpool(
                corpus_queries.review_queue, context.access, records, self.build_id,
                filters=filters, offset=offset, limit=limit,
            )
        except Exception as exc:
            raise translate(exc) from exc
        return CorpusReviewQueuePage.from_payload(payload)

    @strawberry.field(description="Queue-row projections for specific Records, in the order requested.")
    async def rows(self, info: Info, record_ids: list[str]) -> list[CorpusQueueRow | None]:
        context = require_admin(info)
        try:
            presented = await run_in_threadpool(
                corpus_queries.stored_records_by_ids, context.access, self.build_id, record_ids,
            )
        except Exception as exc:
            raise translate(exc) from exc
        return [CorpusQueueRow.from_presented_record(item) if item is not None else None for item in presented]

    @strawberry.field(description="One reviewer-presented Record (REST: full Record from the review page).")
    async def record(self, info: Info, record_id: str) -> CorpusRecord:
        context = require_admin(info)
        try:
            presented = await run_in_threadpool(
                corpus_queries.stored_record_by_id, context.access, self.build_id, record_id,
            )
        except Exception as exc:
            raise translate(exc) from exc
        return CorpusRecord.from_presented_record(presented)

    @strawberry.field(description="Reviewer-presented Records, in the order requested (missing ids come back null).")
    async def records(self, info: Info, record_ids: list[str]) -> list[CorpusRecord | None]:
        context = require_admin(info)
        try:
            presented = await run_in_threadpool(
                corpus_queries.stored_records_by_ids, context.access, self.build_id, record_ids,
            )
        except Exception as exc:
            raise translate(exc) from exc
        return [CorpusRecord.from_presented_record(item) if item is not None else None for item in presented]

    @strawberry.field(
        description=(
            "Retained derived whole-document linguistic analysis. Advisory only: "
            "it is not source evidence and does not confer FieldAssertion authority."
        ),
    )
    async def document_intelligence(self, info: Info) -> DocumentIntelligenceRun | None:
        context = require_admin(info)
        try:
            payload = await run_in_threadpool(
                document_intelligence_reads.build_document_intelligence,
                context.access,
                self.build_id,
            )
        except Exception as exc:
            raise translate(exc) from exc
        return DocumentIntelligenceRun.from_payload(payload) if payload is not None else None

    @strawberry.field(
        description="Build-wide observed metadata values, optionally narrowed to specific fields.",
    )
    async def metadata_facets(self, info: Info, fields: list[str] | None = None) -> JSON:
        require_admin(info)
        try:
            records = await self._records(info)
            facets = await run_in_threadpool(
                corpus_queries.metadata_facets, records, self.build_id, fields,
            )
        except Exception as exc:
            raise translate(exc) from exc
        return JSON(facets)


@strawberry.type
class CorpusQueries:
    @strawberry.field(description="A PDF Corpus Builder build by id (REST: GET /api/pdf/corpus-builds/{id}).")
    def corpus_build(self, info: Info, build_id: str) -> CorpusBuildReview:
        require_admin(info)
        return CorpusBuildReview(build_id=build_id)
