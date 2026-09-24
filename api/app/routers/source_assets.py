# Copyright 2026 Aaron John Schlosser, PhD.
"""Source extraction and durable source-asset acquisition API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from ..config import settings
from ..corpus_builder import pdf_corpus_repository
from ..models import (
    GutenbergImport,
    PdfDocumentLayoutPatch,
    PdfPageLabelsPatch,
    PdfSourceUrlImport,
)
from ..pdf_tools import extract_pdf_text
from ..source_media import (
    fetch_source_url,
    load_gutenberg_etext,
    search_project_gutenberg,
)
from ..source_safety import MAX_SOURCE_BYTES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pdf", tags=["source-assets"])


@router.post("/extract")
async def pdf_extract(
    file: UploadFile = File(...),
    page: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    try:
        data = await file.read()
        return extract_pdf_text(data, page=page)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("PDF extraction failed")
        raise HTTPException(
            status_code=500,
            detail=f"PDF extraction failed: {exc}",
        ) from exc


@router.post("/assets")
async def create_pdf_asset(
    file: UploadFile = File(...),
    ocr_mode: str = Form(default="auto"),
    ocr_languages: str = Form(default="eng+fra+deu"),
    source_illegibility: float = Form(default=0),
) -> dict[str, Any]:
    if ocr_mode not in {"auto", "never", "always"}:
        raise HTTPException(
            status_code=422,
            detail="ocr_mode must be auto, never, or always",
        )
    if not 0 <= source_illegibility <= 100:
        raise HTTPException(
            status_code=422,
            detail="source_illegibility must be between 0 and 100",
        )

    try:
        configured_limit = settings.pdf_max_upload_mb * 1024 * 1024
        is_pdf = (
            str(file.filename or "").lower().endswith(".pdf")
            or file.content_type == "application/pdf"
        )
        max_bytes = configured_limit if is_pdf else min(
            configured_limit,
            MAX_SOURCE_BYTES,
        )

        # Read uploads incrementally so the request is rejected before an
        # oversized non-PDF source can consume unbounded process memory.
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        "Source exceeds the "
                        f"{max_bytes // (1024 * 1024)} MiB upload limit"
                    ),
                )
            chunks.append(chunk)

        return pdf_corpus_repository.save_asset(
            b"".join(chunks),
            filename=file.filename or "source.pdf",
            ocr_mode=ocr_mode,
            ocr_languages=ocr_languages or "eng+fra+deu",
            source_illegibility=source_illegibility,
            content_type=file.content_type or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("PDF asset ingestion failed")
        raise HTTPException(
            status_code=500,
            detail=f"PDF asset ingestion failed: {exc}",
        ) from exc


@router.post("/assets/url")
def import_pdf_asset_url(body: PdfSourceUrlImport) -> dict[str, Any]:
    try:
        data, filename, content_type = fetch_source_url(
            body.url,
            max_bytes=settings.pdf_max_upload_mb * 1024 * 1024,
        )
        return pdf_corpus_repository.save_asset(
            data,
            filename=filename,
            source_illegibility=body.source_illegibility,
            content_type=content_type,
            source_url=body.url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("URL source ingestion failed")
        raise HTTPException(
            status_code=500,
            detail=f"URL source ingestion failed: {exc}",
        ) from exc


@router.get("/gutenberg/search")
def search_gutenberg_texts(
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=12, ge=1, le=30),
) -> dict[str, Any]:
    try:
        return {"items": search_project_gutenberg(q, limit)}
    except Exception as exc:
        logger.exception("Project Gutenberg search failed")
        raise HTTPException(
            status_code=502,
            detail=f"Project Gutenberg search failed: {exc}",
        ) from exc


@router.post("/gutenberg/import")
def import_gutenberg_text(body: GutenbergImport) -> dict[str, Any]:
    try:
        text, catalog = load_gutenberg_etext(body.etext_id)
        return pdf_corpus_repository.save_asset(
            text.encode("utf-8"),
            filename=f"{catalog.get('title') or body.etext_id}.txt",
            source_illegibility=body.source_illegibility,
            content_type="text/plain",
            catalog_metadata=catalog,
            source_url=f"https://www.gutenberg.org/ebooks/{body.etext_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Project Gutenberg import failed")
        raise HTTPException(
            status_code=502,
            detail=f"Project Gutenberg import failed: {exc}",
        ) from exc


@router.get("/assets")
def list_pdf_assets() -> dict[str, Any]:
    return {"items": pdf_corpus_repository.list_assets()}


@router.get("/assets/{asset_id}")
def get_pdf_asset(asset_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.get_asset(asset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc


@router.patch("/assets/{asset_id}/page-labels")
def patch_pdf_asset_page_labels(
    asset_id: str,
    body: PdfPageLabelsPatch,
) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.update_page_labels(asset_id, body.labels)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/assets/{asset_id}/document-layout")
def patch_pdf_asset_document_layout(
    asset_id: str,
    body: PdfDocumentLayoutPatch,
) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.update_document_layout(
            asset_id,
            body.model_dump(exclude_none=True),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/assets/{asset_id}/content")
def get_pdf_asset_content(asset_id: str) -> FileResponse:
    try:
        asset = pdf_corpus_repository.get_asset(asset_id)
        suffix = str(asset.get("content_suffix") or ".pdf")
        path = pdf_corpus_repository.asset_content_path(asset_id, suffix)
        media_type = str(
            asset.get("media_type") or "application/pdf"
        ).split(";", 1)[0]
        filename = asset.get("filename") or "source"
        return FileResponse(
            path,
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"'
            },
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc


@router.get("/assets/{asset_id}/blocks")
def get_pdf_asset_blocks(
    asset_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    ids: str = Query(default="", max_length=20000),
) -> dict[str, Any]:
    try:
        blocks = pdf_corpus_repository.load_blocks(asset_id)
        if ids.strip():
            requested = {
                value.strip()
                for value in ids.split(",")
                if value.strip()
            }
            selected = [
                block
                for block in blocks
                if str(block.get("block_id") or "") in requested
            ]
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
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
