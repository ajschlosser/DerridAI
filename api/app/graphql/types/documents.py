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

"""Typed read projections for SourceDocument intelligence.

SourceDocument is the cELF identity. The extraction units and processing fields
below are explicitly implementation projections around that identity; they do
not introduce new normative cELF semantic object classes.
"""
from __future__ import annotations

from typing import Any

import strawberry
from starlette.concurrency import run_in_threadpool
from strawberry.scalars import JSON
from strawberry.types import Info

from ...celf_queries import source_documents as document_queries
from ..errors import translate
from .common import opt_float, opt_int, opt_str, str_list


@strawberry.type(description="One Corpus Capture provenance link for a SourceDocument.")
class SourceCaptureReference:
    capture_id: str
    candidate_id: str
    provider: str
    provider_item_id: str
    discovery_method: str | None
    discovered_at: str | None
    acquired_at: str | None
    author_name: str | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> SourceCaptureReference:
        return cls(
            capture_id=str(payload.get("capture_id") or ""),
            candidate_id=str(payload.get("candidate_id") or ""),
            provider=str(payload.get("provider") or ""),
            provider_item_id=str(payload.get("provider_item_id") or ""),
            discovery_method=opt_str(payload.get("discovery_method")),
            discovered_at=opt_str(payload.get("discovered_at")),
            acquired_at=opt_str(payload.get("acquired_at")),
            author_name=opt_str(payload.get("author_name")),
        )


@strawberry.type(description="One Corpus Builder build derived from a SourceDocument.")
class SourceBuildReference:
    build_id: str
    status: str
    created_at: str | None
    record_count: int | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> SourceBuildReference:
        return cls(
            build_id=str(payload.get("build_id") or ""),
            status=str(payload.get("status") or ""),
            created_at=opt_str(payload.get("created_at")),
            record_count=opt_int(payload.get("record_count")),
        )


@strawberry.type(description="One model artifact used by a Document Intelligence provider.")
class DocumentIntelligenceArtifact:
    role: str | None
    name: str | None
    sha256: str | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> DocumentIntelligenceArtifact:
        return cls(
            role=opt_str(payload.get("role")),
            name=opt_str(payload.get("name")),
            sha256=opt_str(payload.get("sha256")),
        )


@strawberry.type(description="One Record's offset range in the conserved whole-document analysis text.")
class DocumentIntelligenceRecordSpan:
    record_id: str
    record_revision: int | None
    start: int | None
    end: int | None
    text_sha256: str | None
    source_unit_ids: list[str]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> DocumentIntelligenceRecordSpan:
        return cls(
            record_id=str(payload.get("record_id") or ""),
            record_revision=opt_int(payload.get("record_revision")),
            start=opt_int(payload.get("start")),
            end=opt_int(payload.get("end")),
            text_sha256=opt_str(payload.get("text_sha256")),
            source_unit_ids=str_list(payload.get("source_unit_ids")),
        )


@strawberry.type(description="One normalized entity/coreference cluster from Document Intelligence.")
class DocumentEntityCluster:
    cluster_id: str
    canonical: str
    aliases: list[str]
    entity_type: str | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> DocumentEntityCluster:
        return cls(
            cluster_id=str(payload.get("cluster_id") or ""),
            canonical=str(payload.get("canonical") or ""),
            aliases=str_list(payload.get("aliases")),
            entity_type=opt_str(payload.get("entity_type")),
        )


@strawberry.type(description="One normalized entity mention in conserved whole-document offsets.")
class DocumentEntityMention:
    cluster_id: str
    start_char: int | None
    end_char: int | None
    text: str
    mention_type: str | None
    entity_type: str | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> DocumentEntityMention:
        return cls(
            cluster_id=str(payload.get("cluster_id") or ""),
            start_char=opt_int(payload.get("start_char")),
            end_char=opt_int(payload.get("end_char")),
            text=str(payload.get("text") or ""),
            mention_type=opt_str(payload.get("mention_type")),
            entity_type=opt_str(payload.get("entity_type")),
        )


@strawberry.type(description="One normalized quotation and its candidate speaker attribution.")
class DocumentQuotation:
    start_char: int | None
    end_char: int | None
    text: str
    speaker_cluster_id: str | None
    speaker_text: str | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> DocumentQuotation:
        return cls(
            start_char=opt_int(payload.get("start_char")),
            end_char=opt_int(payload.get("end_char")),
            text=str(payload.get("text") or ""),
            speaker_cluster_id=opt_str(payload.get("speaker_cluster_id")),
            speaker_text=opt_str(payload.get("speaker_text")),
        )


@strawberry.type(
    description=(
        "Retained, derived whole-document linguistic analysis. Advisory only: it is not evidence "
        "and does not make any FieldAssertion authoritative."
    ),
)
class DocumentIntelligenceRun:
    version: int | None
    status: str
    profile: str | None
    selected_provider: str | None
    provider: str | None
    provider_version: str | None
    model: str | None
    capabilities: list[str]
    model_artifacts: list[DocumentIntelligenceArtifact]
    configuration: JSON
    text_sha256: str | None
    current_text_sha256: str | None
    text_length: int | None
    stale: bool
    reason: str | None
    warnings: list[str]
    record_spans: list[DocumentIntelligenceRecordSpan]
    entity_clusters: list[DocumentEntityCluster]
    entities: list[DocumentEntityMention]
    quotations: list[DocumentQuotation]
    characters: JSON
    events: JSON

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> DocumentIntelligenceRun:
        return cls(
            version=opt_int(payload.get("version")),
            status=str(payload.get("status") or ""),
            profile=opt_str(payload.get("profile")),
            selected_provider=opt_str(payload.get("selected_provider")),
            provider=opt_str(payload.get("provider")),
            provider_version=opt_str(payload.get("provider_version")),
            model=opt_str(payload.get("model")),
            capabilities=str_list(payload.get("capabilities")),
            model_artifacts=[
                DocumentIntelligenceArtifact.from_payload(item)
                for item in payload.get("model_artifacts") or []
                if isinstance(item, dict)
            ],
            configuration=JSON(dict(payload.get("configuration") or {})),
            text_sha256=opt_str(payload.get("text_sha256")),
            current_text_sha256=opt_str(payload.get("current_text_sha256")),
            text_length=opt_int(payload.get("text_length")),
            stale=bool(payload.get("stale")),
            reason=opt_str(payload.get("reason")),
            warnings=str_list(payload.get("warnings")),
            record_spans=[
                DocumentIntelligenceRecordSpan.from_payload(item)
                for item in payload.get("record_spans") or []
                if isinstance(item, dict)
            ],
            entity_clusters=[
                DocumentEntityCluster.from_payload(item)
                for item in payload.get("entity_clusters") or []
                if isinstance(item, dict)
            ],
            entities=[
                DocumentEntityMention.from_payload(item)
                for item in payload.get("entities") or []
                if isinstance(item, dict)
            ],
            quotations=[
                DocumentQuotation.from_payload(item)
                for item in payload.get("quotations") or []
                if isinstance(item, dict)
            ],
            characters=JSON(list(payload.get("characters") or [])),
            events=JSON(list(payload.get("events") or [])),
        )


@strawberry.type(description="One medium page/layout projection for a SourceDocument.")
class SourceDocumentPage:
    physical_page: int
    printed_page_label: str | None
    printed_page_label_source: str | None
    width: float | None
    height: float | None
    block_ids: list[str]
    extraction_method: str | None
    image_count: int | None
    deterministic_region_type: str | None
    thread_ids: list[str]
    logical_pages: JSON

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> SourceDocumentPage:
        return cls(
            physical_page=int(payload.get("pdf_page") or payload.get("page") or 0),
            printed_page_label=opt_str(payload.get("printed_page_label")),
            printed_page_label_source=opt_str(payload.get("printed_page_label_source")),
            width=opt_float(payload.get("width")),
            height=opt_float(payload.get("height")),
            block_ids=str_list(payload.get("block_ids")),
            extraction_method=opt_str(payload.get("extraction_method")),
            image_count=opt_int(payload.get("image_count")),
            deterministic_region_type=opt_str(payload.get("deterministic_region_type")),
            thread_ids=str_list(payload.get("thread_ids")),
            logical_pages=JSON(list(payload.get("logical_pages") or [])),
        )


@strawberry.type(description="A bounded page of SourceDocument page/layout projections.")
class SourceDocumentPagePage:
    items: list[SourceDocumentPage]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> SourceDocumentPagePage:
        return cls(
            items=[SourceDocumentPage.from_payload(item) for item in payload.get("items") or []],
            total=int(payload.get("total") or 0),
            offset=int(payload.get("offset") or 0),
            limit=int(payload.get("limit") or 0),
        )


@strawberry.type(
    description=(
        "One persisted implementation-level extraction unit for a SourceDocument. "
        "This is not an additional normative cELF semantic object class."
    ),
)
class SourceUnitProjection:
    source_unit_id: str
    page: int | None
    printed_page_label: str | None
    type: str | None
    text: str
    extraction_method: str | None
    confidence: float | None
    bbox: list[float]
    start: int | None
    end: int | None
    locator_kind: str | None
    speaker: str | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> SourceUnitProjection:
        bbox: list[float] = []
        for item in payload.get("bbox") or []:
            try:
                bbox.append(float(item))
            except (TypeError, ValueError):
                continue
        return cls(
            source_unit_id=str(payload.get("block_id") or payload.get("source_unit_id") or ""),
            page=opt_int(payload.get("page")),
            printed_page_label=opt_str(payload.get("printed_page_label")),
            type=opt_str(payload.get("type")),
            text=str(payload.get("text") or ""),
            extraction_method=opt_str(payload.get("extraction_method")),
            confidence=opt_float(payload.get("confidence")),
            bbox=bbox,
            start=opt_int(payload.get("start")),
            end=opt_int(payload.get("end")),
            locator_kind=opt_str(payload.get("locator_kind")),
            speaker=opt_str(payload.get("speaker")),
        )


@strawberry.type(description="A bounded page of persisted extraction units for one SourceDocument.")
class SourceUnitProjectionPage:
    items: list[SourceUnitProjection]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> SourceUnitProjectionPage:
        return cls(
            items=[SourceUnitProjection.from_payload(item) for item in payload.get("items") or []],
            total=int(payload.get("total") or 0),
            offset=int(payload.get("offset") or 0),
            limit=int(payload.get("limit") or 0),
        )


@strawberry.type(
    description=(
        "Read projection around one canonical cELF SourceDocument: identity, extraction provenance, "
        "document structure, and links to downstream Corpus Builder builds."
    ),
)
class SourceDocumentView:
    source_document_id: str
    sha256: str
    filename: str
    created_at: str | None
    media_type: str | None
    media_kind: str | None
    content_suffix: str | None
    source_url: str | None
    page_count: int | None
    source_unit_count: int | None
    ocr_pages: int | None
    derived_from_source_document_id: str | None
    source_illegibility: float | None
    deterministic_checked_at: str | None
    warnings: list[str]
    extraction_provenance: JSON
    catalog_metadata: JSON
    initial_metadata: JSON
    page_number_detection: JSON
    source_quality: JSON
    extraction_noise: JSON
    document_layout: JSON
    unit_policy: JSON
    captures: list[SourceCaptureReference]
    builds: list[SourceBuildReference]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> SourceDocumentView:
        return cls(
            source_document_id=str(payload.get("source_document_id") or ""),
            sha256=str(payload.get("sha256") or ""),
            filename=str(payload.get("filename") or ""),
            created_at=opt_str(payload.get("created_at")),
            media_type=opt_str(payload.get("media_type")),
            media_kind=opt_str(payload.get("media_kind")),
            content_suffix=opt_str(payload.get("content_suffix")),
            source_url=opt_str(payload.get("source_url")),
            page_count=opt_int(payload.get("page_count")),
            source_unit_count=opt_int(payload.get("source_unit_count")),
            ocr_pages=opt_int(payload.get("ocr_pages")),
            derived_from_source_document_id=opt_str(payload.get("derived_from_source_document_id")),
            source_illegibility=opt_float(payload.get("source_illegibility")),
            deterministic_checked_at=opt_str(payload.get("deterministic_checked_at")),
            warnings=str_list(payload.get("warnings")),
            extraction_provenance=JSON(dict(payload.get("extraction_provenance") or {})),
            catalog_metadata=JSON(dict(payload.get("catalog_metadata") or {})),
            initial_metadata=JSON(dict(payload.get("initial_metadata") or {})),
            page_number_detection=JSON(dict(payload.get("page_number_detection") or {})),
            source_quality=JSON(dict(payload.get("source_quality") or {})),
            extraction_noise=JSON(dict(payload.get("extraction_noise") or {})),
            document_layout=JSON(dict(payload.get("document_layout") or {})),
            unit_policy=JSON(dict(payload.get("unit_policy") or {})),
            captures=[
                SourceCaptureReference.from_payload(item)
                for item in payload.get("captures") or []
            ],
            builds=[
                SourceBuildReference.from_payload(item)
                for item in payload.get("builds") or []
            ],
        )

    @strawberry.field(description="A bounded page of implementation-level extraction/source units.")
    async def source_units(
        self,
        info: Info,
        offset: int = 0,
        limit: int = 100,
        ids: list[str] | None = None,
        around: str | None = None,
    ) -> SourceUnitProjectionPage:
        try:
            payload = await run_in_threadpool(
                document_queries.source_units_page,
                info.context.access,
                self.source_document_id,
                offset=offset,
                limit=limit,
                ids=ids,
                around=around,
            )
        except Exception as exc:
            raise translate(exc) from exc
        return SourceUnitProjectionPage.from_payload(payload)

    @strawberry.field(description="A bounded page of medium-specific page/layout projections.")
    async def pages(
        self,
        info: Info,
        offset: int = 0,
        limit: int = 100,
    ) -> SourceDocumentPagePage:
        try:
            payload = await run_in_threadpool(
                document_queries.document_pages,
                info.context.access,
                self.source_document_id,
                offset=offset,
                limit=limit,
            )
        except Exception as exc:
            raise translate(exc) from exc
        return SourceDocumentPagePage.from_payload(payload)
