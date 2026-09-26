# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import logging
from typing import Any

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse

from ..config import settings
from ..corpus_builder import CORPUS_PROFILES, pdf_corpus_builds, pdf_corpus_repository
from ..corpus_review_state import _queue_counts
from ..field_assertions import field_identity
from ..http_auth import require_admin
from ..llm import TouchupFailure
from ..metadata_adjudication_cache import clear as clear_adjudication_cache
from ..metadata_adjudication_cache import remember as remember_adjudication
from ..metadata_adjudication_cache import suggestions as adjudication_suggestions
from ..metadata_schema import MetadataSchema, SchemaImportError
from ..metadata_schema_store import SchemaLocked, SchemaNotFound, SchemaStore
from ..models import (
    GutenbergImport,
    MetadataSchemaPreview,
    PdfCorpusBoundaryAdjudication,
    PdfCorpusBuildCreate,
    PdfCorpusBulkDisposition,
    PdfCorpusBulkMetadataPatch,
    PdfCorpusEvidencePatch,
    PdfCorpusManifestPatch,
    PdfCorpusMetadataCacheClear,
    PdfCorpusMetadataDecision,
    PdfCorpusMetadataDecisionBatch,
    PdfCorpusProviderSwitch,
    PdfCorpusPublishRequest,
    PdfCorpusRecordAccept,
    PdfCorpusRecordDisposition,
    PdfCorpusRecordMerge,
    PdfCorpusRecordPatch,
    PdfCorpusRecordRerun,
    PdfCorpusRecordSlice,
    PdfCorpusRecordSplit,
    PdfCorpusRecordTextPatch,
    PdfCorpusReviewDecision,
    PdfCorpusSecondOpinion,
    PdfCorpusTextTouchupProposalStatus,
    PdfCorpusTextTouchupRequest,
    PdfDocumentLayoutPatch,
    PdfPageLabelsPatch,
    PdfSourceUrlImport,
)
from ..pdf_tools import extract_pdf_text
from ..provider_profile_options import profile_generation_options
from ..source_media import (
    fetch_source_url,
    load_gutenberg_etext,
    search_project_gutenberg,
)
from ..system_store import system_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["corpus-builder"])


@router.post("/api/pdf/extract")
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


@router.post("/api/pdf/assets")
async def create_pdf_asset(
    file: UploadFile = File(...),
    ocr_mode: str = Form(default="auto"),
    ocr_languages: str = Form(default="eng+fra+deu"),
    source_illegibility: float = Form(default=0),
) -> dict[str, Any]:
    if ocr_mode not in {"auto", "never", "always"}:
        raise HTTPException(status_code=422, detail="ocr_mode must be auto, never, or always")
    if source_illegibility < 0 or source_illegibility > 100:
        raise HTTPException(status_code=422, detail="source_illegibility must be between 0 and 100")
    try:
        from ..source_safety import MAX_SOURCE_BYTES

        max_bytes = settings.pdf_max_upload_mb * 1024 * 1024
        if not str(file.filename or "").lower().endswith(".pdf") and file.content_type != "application/pdf":
            max_bytes = min(max_bytes, MAX_SOURCE_BYTES)
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
                    detail=f"Source exceeds the {max_bytes // (1024 * 1024)} MiB upload limit",
                )
            chunks.append(chunk)
        data = b"".join(chunks)
        return pdf_corpus_repository.save_asset(
            data,
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
        raise HTTPException(status_code=500, detail=f"PDF asset ingestion failed: {exc}") from exc


@router.post("/api/pdf/assets/url")
def import_pdf_asset_url(body: PdfSourceUrlImport) -> dict[str, Any]:
    try:
        data, filename, content_type = fetch_source_url(body.url, max_bytes=settings.pdf_max_upload_mb * 1024 * 1024)
        return pdf_corpus_repository.save_asset(
            data, filename=filename, source_illegibility=body.source_illegibility,
            content_type=content_type, source_url=body.url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("URL source ingestion failed")
        raise HTTPException(status_code=500, detail=f"URL source ingestion failed: {exc}") from exc


@router.get("/api/pdf/gutenberg/search")
def search_gutenberg_texts(q: str = Query(default="", max_length=200), limit: int = Query(default=12, ge=1, le=30)) -> dict[str, Any]:
    try:
        return {"items": search_project_gutenberg(q, limit)}
    except Exception as exc:
        logger.exception("Project Gutenberg search failed")
        raise HTTPException(status_code=502, detail=f"Project Gutenberg search failed: {exc}") from exc


@router.post("/api/pdf/gutenberg/import")
def import_gutenberg_text(body: GutenbergImport) -> dict[str, Any]:
    try:
        text, catalog = load_gutenberg_etext(body.etext_id)
        return pdf_corpus_repository.save_asset(
            text.encode("utf-8"), filename=f"{catalog.get('title') or body.etext_id}.txt",
            source_illegibility=body.source_illegibility, content_type="text/plain",
            catalog_metadata=catalog, source_url=f"https://www.gutenberg.org/ebooks/{body.etext_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Project Gutenberg import failed")
        raise HTTPException(status_code=502, detail=f"Project Gutenberg import failed: {exc}") from exc


@router.get("/api/pdf/assets")
def list_pdf_assets() -> dict[str, Any]:
    return {"items": pdf_corpus_repository.list_assets()}


@router.get("/api/pdf/assets/{asset_id}")
def get_pdf_asset(asset_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.get_asset(asset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc




@router.patch("/api/pdf/assets/{asset_id}/page-labels")
def patch_pdf_asset_page_labels(asset_id: str, body: PdfPageLabelsPatch) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.update_page_labels(asset_id, body.labels)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/api/pdf/assets/{asset_id}/document-layout")
def patch_pdf_asset_document_layout(asset_id: str, body: PdfDocumentLayoutPatch) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.update_document_layout(asset_id, body.model_dump(exclude_none=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/assets/{asset_id}/content")
def get_pdf_asset_content(asset_id: str) -> FileResponse:
    try:
        asset = pdf_corpus_repository.get_asset(asset_id)
        suffix = str(asset.get("content_suffix") or ".pdf")
        path = pdf_corpus_repository.asset_content_path(asset_id, suffix)
        media_type = str(asset.get("media_type") or "application/pdf").split(";", 1)[0]
        return FileResponse(path, media_type=media_type, headers={"Content-Disposition": f'inline; filename="{asset.get("filename") or "source"}"'})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc


@router.get("/api/pdf/assets/{asset_id}/blocks")
def get_pdf_asset_blocks(
    asset_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    ids: str = Query(default="", max_length=20000),
) -> dict[str, Any]:
    try:
        blocks = pdf_corpus_repository.load_blocks(asset_id)
        if ids.strip():
            requested = {value.strip() for value in ids.split(",") if value.strip()}
            selected = [block for block in blocks if str(block.get("block_id") or "") in requested]
            return {"items": selected, "total": len(selected), "offset": 0, "limit": len(selected)}
        return {"items": blocks[offset:offset + limit], "total": len(blocks), "offset": offset, "limit": limit}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc


@router.get("/api/pdf/corpus-profiles")
def list_pdf_corpus_profiles() -> dict[str, Any]:
    return {"items": list(CORPUS_PROFILES.values())}


def _supplied_secret(value: Any) -> str | None:
    """A blank string was not sent. Only a real value should override a stored secret."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _resolve_pdf_corpus_provider(payload: dict[str, Any]) -> dict[str, Any]:
    """Resolve server-owned researcher profiles without rejecting admin profiles.

    Administrator profiles keep the OpenAI key in the browser and send it on the
    request. A published researcher profile keeps its key on the server. A key or
    endpoint on the request wins; a stored value is used only when the request
    omits it. Secrets are stripped before the public build manifest is saved.
    """
    resolved = dict(payload)
    # Experiment conditions travel as flat request keys inside the pipeline.
    experiment = resolved.pop("experiment", None)
    if isinstance(experiment, dict):
        resolved.update({key: value for key, value in experiment.items() if value not in (None, [], "")})
    # Build-level generation overrides are intentionally distinct from the saved
    # profile.  Resolve server-owned credentials/options first, then layer only
    # the explicitly supplied per-build values over the profile defaults.
    generation_override = resolved.get("generation")
    if hasattr(generation_override, "model_dump"):
        generation_override = generation_override.model_dump(exclude_none=True)
    if not isinstance(generation_override, dict):
        generation_override = {}
    direct_review = resolved.pop("review_provider", None)
    if hasattr(direct_review, "model_dump"):
        direct_review = direct_review.model_dump(exclude_none=True)

    requested_model = str(resolved.get("model") or "").strip() or None
    profile_id = str(resolved.get("provider_profile_id") or "").strip()
    if profile_id:
        profile = system_store.researcher_profile(profile_id)
        if profile is not None:
            profile_generation = profile_generation_options(profile) or {}
            profile_generation.update({key: value for key, value in generation_override.items() if value is not None})
            resolved.update({
                "provider": profile.get("type") or resolved.get("provider") or "ollama",
                "model": requested_model or profile.get("model"),
                "base_url": _supplied_secret(resolved.get("base_url")) or profile.get("base_url"),
                "api_key": _supplied_secret(resolved.get("api_key")) or profile.get("api_key"),
                "generation": profile_generation or None,
                "provider_profile_id": profile_id,
            })
        elif not (resolved.get("provider") and (resolved.get("model") or resolved.get("base_url"))):
            raise ValueError("The selected LLM provider profile is not available.")

    review_profile_id = str(resolved.get("review_provider_profile_id") or "").strip()
    if review_profile_id:
        review_profile = system_store.researcher_profile(review_profile_id)
        if review_profile is not None:
            supplied = direct_review if isinstance(direct_review, dict) else {}
            resolved["_review_provider"] = {
                "provider": review_profile.get("type") or supplied.get("provider") or "ollama",
                "model": supplied.get("model") or review_profile.get("model"),
                "base_url": _supplied_secret(supplied.get("base_url")) or review_profile.get("base_url"),
                "api_key": _supplied_secret(supplied.get("api_key")) or review_profile.get("api_key"),
                "generation": profile_generation_options(review_profile) or supplied.get("generation") or None,
                "provider_profile_id": review_profile_id,
            }
        elif isinstance(direct_review, dict) and direct_review.get("provider"):
            resolved["_review_provider"] = {**direct_review, "provider_profile_id": review_profile_id}
        else:
            raise ValueError("The selected escalation provider profile is not available.")
    elif isinstance(direct_review, dict) and direct_review.get("provider"):
        resolved["_review_provider"] = direct_review

    return {key: value for key, value in resolved.items() if value is not None}


@router.post("/api/pdf/corpus-builds")
def create_pdf_corpus_build(body: PdfCorpusBuildCreate) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.create(_resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/corpus-builds")
def list_pdf_corpus_builds(offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200), asset_id: str | None = None) -> dict[str, Any]:
    return pdf_corpus_repository.list_builds(offset=offset, limit=limit, asset_id=asset_id)


metadata_schemas = SchemaStore(pdf_corpus_repository.root)


def _schema_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, SchemaNotFound):
        return HTTPException(status_code=404, detail="Metadata schema not found")
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/api/pdf/metadata-schemas")
def list_metadata_schemas(request: Request):
    require_admin(request)
    return {"items": metadata_schemas.list()}


@router.post("/api/pdf/metadata-schemas/import")
def import_metadata_schema(request: Request, payload: dict[str, Any]):
    require_admin(request)
    try:
        return metadata_schemas.import_(payload).model_dump(mode="json")
    except (SchemaImportError, SchemaLocked, ValueError) as exc:
        raise _schema_errors(exc) from exc


@router.post("/api/pdf/metadata-schemas")
def create_metadata_schema(request: Request, body: MetadataSchema):
    require_admin(request)
    try:
        return metadata_schemas.save(body).model_dump(mode="json")
    except (SchemaLocked, ValueError) as exc:
        raise _schema_errors(exc) from exc


@router.post("/api/pdf/metadata-schemas/preview")
def preview_metadata_schema_group(request: Request, body: MetadataSchemaPreview):
    require_admin(request)
    try:
        payload = body.model_dump(exclude_none=True, by_alias=False)
        for key in ("schema_", "group", "text", "run"):
            payload.pop(key, None)
        if body.run and not str(payload.get("provider_profile_id") or "").strip():
            profiles = system_store.researcher_profiles(include_secrets=True)
            if profiles:
                payload["provider_profile_id"] = profiles[0].get("id")
        request_payload = _resolve_pdf_corpus_provider(payload) if body.run else {}
        return pdf_corpus_builds.preview_schema_group(body.schema_, body.group, body.text, request_payload, body.run)
    except (ValueError, TouchupFailure) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/metadata-schemas/{schema_id}")
def get_metadata_schema(request: Request, schema_id: str):
    require_admin(request)
    try:
        return metadata_schemas.get(schema_id).model_dump(mode="json")
    except SchemaNotFound as exc:
        raise _schema_errors(exc) from exc


@router.get("/api/pdf/metadata-schemas/{schema_id}/export")
def export_metadata_schema(request: Request, schema_id: str):
    require_admin(request)
    try:
        return JSONResponse(metadata_schemas.export(schema_id), headers={"Content-Disposition": f'attachment; filename="{schema_id}.derridai-schema.json"'})
    except SchemaNotFound as exc:
        raise _schema_errors(exc) from exc


@router.put("/api/pdf/metadata-schemas/{schema_id}")
def update_metadata_schema(request: Request, schema_id: str, body: MetadataSchema):
    require_admin(request)
    try:
        return metadata_schemas.save(body, schema_id).model_dump(mode="json")
    except (SchemaNotFound, SchemaLocked, ValueError) as exc:
        raise _schema_errors(exc) from exc


@router.delete("/api/pdf/metadata-schemas/{schema_id}")
def delete_metadata_schema(request: Request, schema_id: str):
    require_admin(request)
    try:
        metadata_schemas.delete(schema_id)
        return {"deleted": schema_id}
    except (SchemaNotFound, SchemaLocked) as exc:
        raise _schema_errors(exc) from exc


@router.get("/api/pdf/corpus-builds/{build_id}")
def get_pdf_corpus_build(build_id: str) -> dict[str, Any]:
    try:
        build = pdf_corpus_repository.get_build(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    # Not stored: it is a live reading of what the build is waiting for right now.
    build["llm_activity"] = pdf_corpus_builds.llm_activity(build_id)
    return build


@router.patch("/api/pdf/corpus-builds/{build_id}/provider-profile")
def patch_pdf_corpus_provider_profile(build_id: str, body: PdfCorpusProviderSwitch) -> dict[str, Any]:
    try:
        resolved = _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        return pdf_corpus_builds.switch_provider_profile(build_id, resolved)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@router.post("/api/pdf/corpus-builds/{build_id}/manifest/regenerate")
def regenerate_pdf_corpus_manifest(build_id: str, body: PdfCorpusRecordRerun):
    try:
        return pdf_corpus_builds.regenerate_manifest(build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/api/pdf/corpus-builds/{build_id}/manifest")
def patch_pdf_corpus_manifest(build_id: str, body: PdfCorpusManifestPatch) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.patch_manifest(build_id, body.changes, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/corpus-builds/{build_id}/records")
def list_pdf_corpus_records(
    build_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    needs_review: bool | None = None,
    disposition: str | None = Query(default=None, pattern="^(pending|accepted|rejected)$"),
    metadata_incomplete: bool | None = None,
    source_problem: bool | None = None,
    review_queue: str | None = Query(default=None, pattern="^(ready|issues|metadata|source|topology|accepted|rejected)$"),
    query: str = "",
) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.page_records(build_id, offset=offset, limit=limit, needs_review=needs_review, disposition=disposition, metadata_incomplete=metadata_incomplete, source_problem=source_problem, review_queue=review_queue, query=query)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@router.post("/api/pdf/corpus-builds/{build_id}/confirm-manifest")
def confirm_pdf_corpus_manifest(build_id: str, body: PdfCorpusRecordRerun) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.confirm_manifest(
            build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/cancel")
def cancel_pdf_corpus_build(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.cancel(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@router.post("/api/pdf/corpus-builds/{build_id}/settle-metadata")
def settle_pdf_corpus_metadata(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.settle_metadata_unresolved(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/resume")
def resume_pdf_corpus_build(build_id: str, body: PdfCorpusRecordRerun) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.resume(build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata")
def patch_pdf_corpus_record_metadata(
    build_id: str, record_id: str, body: PdfCorpusRecordPatch, include_state: bool = False
) -> dict[str, Any]:
    try:
        record = pdf_corpus_builds.patch_metadata(build_id, record_id, body.changes, body.expected_revision)
        if include_state:
            records = pdf_corpus_builds.repo.load_records(build_id)
            return {
                "record": record,
                "build": pdf_corpus_builds.repo.get_build(build_id),
                "queue_counts": _queue_counts(records),
            }
        return record
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/text")
def patch_pdf_corpus_record_text(build_id: str, record_id: str, body: PdfCorpusRecordTextPatch) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.patch_record_text(build_id, record_id, body.text, body.expected_revision, body.resolve_source_issues)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata-decision")
def decide_pdf_corpus_record_metadata(build_id: str, record_id: str, body: PdfCorpusMetadataDecision) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.metadata_decision(build_id, record_id, body.field, body.value, body.expected_revision, body.confirm_no_supported_value)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata-decisions")
def decide_pdf_corpus_record_metadata_batch(
    build_id: str,
    record_id: str,
    body: PdfCorpusMetadataDecisionBatch,
) -> dict[str, Any]:
    try:
        pdf_corpus_builds.patch_metadata(
            build_id, record_id, body.changes, body.expected_revision
        )
        build = pdf_corpus_repository.get_build(build_id)
        records = pdf_corpus_repository.load_records(build_id)
        record = next(
            (
                row
                for row in records
                if str(row.get("record_id") or "") == record_id
            ),
            None,
        )
        if record is None:
            raise KeyError(record_id)
        schema = pdf_corpus_builds._schema_for(build_id)
        for field, value in body.changes.items():
            remember_adjudication(
                record_id=record_id,
                text=str(record.get("text") or ""),
                field=field,
                value=value,
                schema_version=str(build.get("schema_version") or ""),
                field_id=field_identity(field, schema),
            )
        return {
            "applied": True,
            "record": record,
            "build": build,
            "changed_fields": list(body.changes),
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata-cache")
def get_pdf_corpus_metadata_cache(build_id: str, record_id: str, field: str) -> dict[str, Any]:
    try:
        record = next(
            (
                row
                for row in pdf_corpus_repository.load_records(build_id)
                if str(row.get("record_id") or "") == record_id
            ),
            None,
        )
        if record is None:
            raise KeyError(record_id)
        build = pdf_corpus_repository.get_build(build_id)
        cached = adjudication_suggestions(
            record_id=record_id,
            text=str(record.get("text") or ""),
            field=field,
            cardinality="list" if isinstance(record.get(field), list) else "single",
            schema_version=str(build.get("schema_version") or ""),
        )
        return {"suggestions": cached or {}}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata-cache")
def clear_pdf_corpus_metadata_cache(
    build_id: str,
    record_id: str,
    body: PdfCorpusMetadataCacheClear | None = None,
) -> dict[str, Any]:
    try:
        if not any(
            str(row.get("record_id") or "") == record_id
            for row in pdf_corpus_repository.load_records(build_id)
        ):
            raise KeyError(record_id)
        return {
            "cleared": clear_adjudication_cache(
                record_id=record_id,
                field=body.field if body else None,
            )
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc


@router.delete("/api/pdf/metadata-cache")
def clear_all_pdf_corpus_metadata_cache() -> dict[str, Any]:
    return {"cleared": clear_adjudication_cache()}


@router.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/evidence")
def patch_pdf_corpus_record_evidence(build_id: str, record_id: str, body: PdfCorpusEvidencePatch) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.patch_evidence(
            build_id, record_id, body.field, body.block_ids, body.confidence, body.reason, body.expected_revision
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/corpus-builds/{build_id}/second-opinions")
def list_pdf_corpus_second_opinions(build_id: str) -> dict[str, Any]:
    try:
        return {"items": pdf_corpus_builds.pending_second_opinions(build_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/second-opinion")
def submit_pdf_corpus_second_opinion(build_id: str, record_id: str, body: PdfCorpusSecondOpinion) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.submit_second_opinion(build_id, record_id, body.field, body.value)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/accept")
def accept_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusRecordAccept) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.accept_record(build_id, record_id, body.accepted, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/disposition")
def set_pdf_corpus_record_disposition(build_id: str, record_id: str, body: PdfCorpusRecordDisposition) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.set_disposition(build_id, record_id, body.disposition, body.reason, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/review-decision")
def decide_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusReviewDecision) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.review_decision(build_id, record_id, body.disposition, body.reason, body.expected_revision, body.review_queue)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/disposition")
def bulk_pdf_corpus_record_disposition(build_id: str, body: PdfCorpusBulkDisposition) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.bulk_disposition(build_id, body.disposition, body.reason, body.needs_review, body.query, body.filter_disposition, body.review_queue, body.record_ids)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/api/pdf/corpus-builds/{build_id}/records/metadata")
def bulk_patch_pdf_corpus_record_metadata(build_id: str, body: PdfCorpusBulkMetadataPatch) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.bulk_patch_metadata(
            build_id, body.changes, record_ids=body.record_ids, apply_to_all=body.apply_to_all,
            review_queue=body.review_queue, query=body.query,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/review/undo")
def undo_pdf_corpus_review_edit(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.undo_last_review_edit(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No review edit is available to undo") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc




@router.post("/api/pdf/corpus-builds/{build_id}/review/redo")
def redo_pdf_corpus_review_edit(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.redo_last_review_edit(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No review edit is available to redo") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/merge")
def merge_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusRecordMerge) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.merge(build_id, record_id, body.direction, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc




@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/slice")
def slice_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusRecordSlice) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.slice_to_neighbor(build_id, record_id, body.direction, body.offset, body.expected_revision, body.keep_end)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/boundary-adjudication")
def adjudicate_pdf_corpus_boundary(build_id: str, record_id: str, body: PdfCorpusBoundaryAdjudication) -> dict[str, Any]:
    try:
        payload = _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        direction = str(payload.pop("direction"))
        return pdf_corpus_builds.adjudicate_record_boundary(build_id, record_id, direction, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/split")
def split_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusRecordSplit) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.split(build_id, record_id, body.after_block_id, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/metadata/retry")
def retry_pdf_corpus_metadata(build_id: str, body: PdfCorpusRecordRerun) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.retry_incomplete_metadata(
            build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/corpus-builds/{build_id}/editorial-memory")
def get_pdf_corpus_editorial_memory(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.editorial_memory(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@router.delete("/api/pdf/corpus-builds/{build_id}/editorial-memory")
def reset_pdf_corpus_editorial_memory(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.reset_editorial_memory(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@router.get("/api/pdf/corpus-builds/{build_id}/records/{record_id}/preview")
def preview_pdf_corpus_record(build_id: str, record_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.preview_record(build_id, record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/viewed")
def mark_pdf_corpus_record_viewed(build_id: str, record_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.record_view(build_id, record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/text-touchup")
def touchup_pdf_corpus_record_text(build_id: str, record_id: str, body: PdfCorpusTextTouchupRequest) -> dict[str, Any]:
    try:
        payload = _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        instructions = str(payload.pop("instructions", "") or "")
        text_override = payload.pop("text", None)
        result = pdf_corpus_builds.touchup_record_text(build_id, record_id, payload, instructions, text_override)
        pdf_corpus_builds.save_text_touchup_proposal(build_id, record_id, result)
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/text-touchup-proposal")
def set_pdf_corpus_text_touchup_proposal_status(build_id: str, record_id: str, body: PdfCorpusTextTouchupProposalStatus) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.set_text_touchup_proposal_status(
            build_id, record_id, body.status
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/corpus-enrichment-metrics")
def get_pdf_corpus_enrichment_metrics(build_id: str = "", run_id: str = "", arm: str = "", group_by: str = ""):
    try:
        return pdf_corpus_builds.enrichment_metrics(build_id, run_id, arm, group_by)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@router.get("/api/pdf/corpus-enrichment-ledger.csv")
def export_pdf_corpus_enrichment_ledger():
    """Every ledger event as one CSV row with its experiment columns, for analysis outside the app."""
    return Response(pdf_corpus_builds.enrichment_ledger_csv(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="enrichment-ledger.csv"'})


@router.post("/api/pdf/corpus-builds/{build_id}/autonomous/run")
def run_pdf_corpus_autonomous(build_id: str, body: PdfCorpusRecordRerun):
    try:
        return pdf_corpus_builds.start_autonomous(build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/metadata/enrich")
def rerun_pdf_corpus_metadata_enrichment(build_id: str, body: PdfCorpusRecordRerun) -> dict[str, Any]:
    try:
        request = body.model_dump(exclude_none=True)
        request.update(_resolve_pdf_corpus_provider(request))
        return pdf_corpus_builds.rerun_metadata_enrichment(build_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/rerun-metadata")
def rerun_pdf_corpus_record_metadata(build_id: str, record_id: str, body: PdfCorpusRecordRerun) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.rerun_metadata(build_id, record_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/publish")
def publish_pdf_corpus_build(build_id: str, body: PdfCorpusPublishRequest) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.publish(build_id, require_acceptance=body.require_acceptance)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/api/pdf/publications/{publication_id}/download")
def download_pdf_corpus_publication(publication_id: str) -> FileResponse:
    path = pdf_corpus_repository.publication_path(publication_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Publication not found")
    if path.name.endswith(".jsonl.zst"):
        return FileResponse(path, media_type="application/zstd", filename=f"{publication_id}.jsonl.zst")
    return FileResponse(path, media_type="application/x-ndjson", filename=f"{publication_id}.jsonl")
