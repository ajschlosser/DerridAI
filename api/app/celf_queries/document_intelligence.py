# Copyright 2026 Aaron John Schlosser, PhD.
"""Transport-independent SourceDocument intelligence reads.

The SourceDocument remains the canonical cELF object. Extraction units, layout
facts, page-detection results, and processing metadata are implementation
projections around that object; this module exposes them without creating a
second document model.

REST and GraphQL call these functions so source identity, provenance,
pagination, and bounded extraction-unit reads have one implementation.
"""
from __future__ import annotations

from typing import Any

from ..corpus_builder import pdf_corpus_repository
from ..services import capture_store
from .access import AccessContext, InvalidQuery, NotFound

MAX_SOURCE_UNIT_PAGE = 1000
MAX_DOCUMENT_PAGE_PAGE = 500
MAX_SOURCE_UNIT_IDS = 500


def _compact_catalog(value: Any) -> dict[str, Any]:
    """Keep provider metadata useful without shipping provider-sized page dumps."""
    catalog = dict(value or {}) if isinstance(value, dict) else {}
    for bulky in ("wikisource_pages", "catalog_record"):
        if isinstance(catalog.get(bulky), list):
            catalog[f"{bulky}_count"] = len(catalog.pop(bulky))
    proofread = catalog.get("proofread")
    if isinstance(proofread, dict):
        catalog["proofread"] = {key: item for key, item in proofread.items() if key != "pages"}
    return catalog


def source_document(
    access: AccessContext,
    source_document_id: str,
    *,
    repository: Any = None,
    capture_links: Any = None,
) -> dict[str, Any]:
    """Return one administrator-visible SourceDocument intelligence projection."""
    access.require_admin()
    repository = repository or pdf_corpus_repository
    capture_links = capture_links or capture_store
    source_id = str(source_document_id or "").strip()
    if not source_id:
        raise InvalidQuery("source_document_id is required")
    try:
        asset = repository.get_asset(source_id)
    except KeyError as exc:
        raise NotFound("Source document not found.") from exc

    builds = repository.list_builds(offset=0, limit=100000, asset_id=source_id)["items"]
    initial = dict(asset.get("initial_metadata") or {}) if isinstance(asset.get("initial_metadata"), dict) else {}
    return {
        "source_document_id": str(asset.get("asset_id") or source_id),
        "sha256": str(asset.get("sha256") or ""),
        "filename": str(asset.get("filename") or ""),
        "created_at": asset.get("created_at"),
        "media_type": asset.get("media_type"),
        "media_kind": asset.get("media_kind"),
        "content_suffix": asset.get("content_suffix"),
        "source_url": asset.get("source_url"),
        "page_count": asset.get("page_count"),
        "source_unit_count": asset.get("block_count"),
        "ocr_pages": asset.get("ocr_pages"),
        "derived_from_source_document_id": asset.get("derived_from_asset_id"),
        "source_illegibility": asset.get("source_illegibility"),
        "deterministic_checked_at": asset.get("deterministic_checked_at"),
        "warnings": list(asset.get("warnings") or []),
        "catalog_metadata": _compact_catalog(asset.get("catalog_metadata")),
        "initial_metadata": initial,
        "extraction_provenance": dict(asset.get("extraction_provenance") or {}),
        "page_number_detection": dict(asset.get("page_number_detection") or {}),
        "source_quality": dict(asset.get("source_quality") or {}),
        "extraction_noise": dict(asset.get("extraction_noise") or {}),
        "document_layout": dict(asset.get("document_layout") or {}),
        "unit_policy": dict(asset.get("unit_policy") or {}),
        "pages": list(asset.get("pages") or []),
        "captures": capture_links.links_for_sources([source_id]).get(source_id, []),
        "builds": [
            {
                "build_id": build.get("build_id"),
                "status": build.get("status"),
                "created_at": build.get("created_at"),
                "record_count": build.get("record_count"),
            }
            for build in builds
        ],
    }


def source_detail_payload(
    access: AccessContext,
    source_document_id: str,
    *,
    repository: Any = None,
    capture_links: Any = None,
) -> dict[str, Any]:
    """Compatibility projection for the existing source-detail REST endpoint."""
    payload = source_document(
        access,
        source_document_id,
        repository=repository,
        capture_links=capture_links,
    )
    initial = dict(payload.get("initial_metadata") or {})
    initial.pop("field_provenance", None)
    initial = {
        key: value
        for key, value in initial.items()
        if isinstance(value, (str, int, float)) or value is None
    }
    return {
        "asset_id": payload["source_document_id"],
        "sha256": payload["sha256"],
        "filename": payload["filename"],
        "created_at": payload["created_at"],
        "media_type": payload["media_type"],
        "media_kind": payload["media_kind"],
        "content_suffix": payload["content_suffix"],
        "source_url": payload["source_url"],
        "page_count": payload["page_count"],
        "block_count": payload["source_unit_count"],
        "ocr_pages": payload["ocr_pages"],
        "extraction_provenance": payload["extraction_provenance"],
        "catalog_metadata": payload["catalog_metadata"],
        "initial_metadata": initial,
        "derived_from_asset_id": payload["derived_from_source_document_id"],
        "page_number_detection": payload["page_number_detection"],
        "captures": payload["captures"],
        "builds": payload["builds"],
    }


def source_units_page(
    access: AccessContext,
    source_document_id: str,
    *,
    offset: int = 0,
    limit: int = 200,
    ids: list[str] | None = None,
    around: str | None = None,
    repository: Any = None,
) -> dict[str, Any]:
    """Return a bounded page of persisted extraction/source units."""
    access.require_admin()
    repository = repository or pdf_corpus_repository
    source_id = str(source_document_id or "").strip()
    if not source_id:
        raise InvalidQuery("source_document_id is required")
    offset = max(0, int(offset))
    limit = max(1, min(MAX_SOURCE_UNIT_PAGE, int(limit)))
    requested = [str(value).strip() for value in (ids or []) if str(value).strip()]
    if len(requested) > MAX_SOURCE_UNIT_IDS:
        raise InvalidQuery(f"At most {MAX_SOURCE_UNIT_IDS} source-unit ids may be requested.")

    try:
        blocks = repository.load_blocks(source_id)
    except KeyError as exc:
        raise NotFound("Source document not found.") from exc

    center = str(around or "").strip()
    if center:
        index = next(
            (index for index, block in enumerate(blocks) if str(block.get("block_id") or "") == center),
            None,
        )
        if index is None:
            raise NotFound("Source unit not found.")
        start = max(0, index - limit // 4)
        return {
            "items": blocks[start : start + limit],
            "total": len(blocks),
            "offset": start,
            "limit": limit,
        }

    if requested:
        wanted = set(requested)
        selected = [block for block in blocks if str(block.get("block_id") or "") in wanted]
        return {
            "items": selected,
            "total": len(selected),
            "offset": 0,
            "limit": len(selected),
        }

    return {
        "items": blocks[offset : offset + limit],
        "total": len(blocks),
        "offset": offset,
        "limit": limit,
    }


def document_pages(
    access: AccessContext,
    source_document_id: str,
    *,
    offset: int = 0,
    limit: int = 100,
    repository: Any = None,
    capture_links: Any = None,
) -> dict[str, Any]:
    """Return a bounded page of medium-specific page/layout projections."""
    payload = source_document(
        access,
        source_document_id,
        repository=repository,
        capture_links=capture_links,
    )
    pages = list(payload.get("pages") or [])
    offset = max(0, int(offset))
    limit = max(1, min(MAX_DOCUMENT_PAGE_PAGE, int(limit)))
    return {
        "items": pages[offset : offset + limit],
        "total": len(pages),
        "offset": offset,
        "limit": limit,
    }
