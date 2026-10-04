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

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx
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
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse

from ..celf_queries import document_intelligence_reads as intelligence_reads
from ..celf_queries import source_documents as document_queries
from ..celf_queries.access import AccessContext, InvalidQuery, NotFound
from ..claim_memory import validated_claims_citing
from ..concurrency import capacity_coordinator, provider_capacity_key, provider_limit
from ..config import settings
from ..corpus_builder import CORPUS_PROFILES, pdf_corpus_builds, pdf_corpus_repository
from ..corpus_review_state import _queue_counts
from ..http_auth import require_admin
from ..llm import TouchupFailure
from ..llm_tools import run_pdf_llm
from ..metadata_adjudication_cache import clear as clear_adjudication_cache
from ..metadata_adjudication_cache import suggestions as adjudication_suggestions
from ..metadata_schema import MetadataSchema, SchemaImportError
from ..metadata_schema_store import SchemaLocked, SchemaNotFound, SchemaStore
from ..models import (
    BuildWarningAcknowledgement,
    GutenbergImport,
    MetadataSchemaPreview,
    PageEstimatePatch,
    PdfAssetLanguagePatch,
    PdfAssetMetadataPatch,
    PdfAudioVoiceAssignments,
    PdfCorpusBoundaryAdjudication,
    PdfCorpusBuildCreate,
    PdfCorpusBuildResume,
    PdfCorpusBulkDisposition,
    PdfCorpusBulkMetadataPatch,
    PdfCorpusEvidencePatch,
    PdfCorpusEvidenceSuggestLlm,
    PdfCorpusManifestPatch,
    PdfCorpusMetadataCacheClear,
    PdfCorpusMetadataDecision,
    PdfCorpusMetadataDecisionBatch,
    PdfCorpusProviderSwitch,
    PdfCorpusPublishRequest,
    PdfCorpusRecordAccept,
    PdfCorpusRecordDisposition,
    PdfCorpusRecordFromSelection,
    PdfCorpusRecordMerge,
    PdfCorpusRecordPatch,
    PdfCorpusRecordRerun,
    PdfCorpusRecordSplit,
    PdfCorpusRecordTextPatch,
    PdfCorpusReviewDecision,
    PdfCorpusSecondOpinion,
    PdfCorpusSemanticAliasImport,
    PdfCorpusSemanticAliasSet,
    PdfCorpusTextTouchupProposalStatus,
    PdfCorpusTextTouchupRequest,
    PdfDocumentLayoutPatch,
    PdfLlmRequest,
    PdfPageLabelsPatch,
    PdfSourceUnitPolicy,
    PdfSourceUrlImport,
)
from ..pdf_tools import extract_pdf_text
from ..provider_profile_options import profile_generation_options
from ..semantic_identity_store import AliasConflict
from ..source_media import (
    fetch_source_url,
    load_gutenberg_etext,
    search_project_gutenberg,
    search_wikisource,
)
from ..system_store import system_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["corpus-builder"])


def _page_llm(
    mode: str,
    profile_id: str | None,
    model: str | None,
    *,
    provider: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> Any:
    """The model-assisted page-number chooser, only when asked for and a provider profile is named.

    Administrator profiles live in the browser, so their provider, endpoint and key travel on the request exactly as
    they do for a build; a published researcher profile is resolved on the server. Nothing here is persisted.
    """
    if mode != "auto_llm" or not profile_id:
        return None
    payload: dict[str, Any] = {"provider_profile_id": profile_id}
    for key, value in (("model", model), ("provider", provider), ("base_url", base_url), ("api_key", api_key)):
        if value:
            payload[key] = value
    return pdf_corpus_builds.page_marker_chooser(_resolve_pdf_corpus_provider(payload))


def _attach_wikisource_scans(asset: dict[str, Any], data: bytes, url: str) -> dict[str, Any]:
    """Best-effort DjVu page renders for a Wikisource import. The transcription is already saved."""
    if "wikisource.org" not in url.lower():
        return asset
    try:
        from urllib.parse import urlparse

        from ..source_provider import ProviderHttp
        from ..source_wikisource import fetch_wikisource_scans, scan_targets_from_html

        targets = scan_targets_from_html(data.decode("utf-8", errors="replace"))
        if not targets:
            return asset
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        scans, warnings = fetch_wikisource_scans(ProviderHttp("wikimedia"), base, targets)
        if scans or warnings:
            return pdf_corpus_repository.store_source_scans(
                asset["asset_id"], scans, source="wikisource_djvu", warnings=warnings,
            )
    except Exception:
        logger.warning("Wikisource scan download failed", exc_info=True)
    return asset


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
    page_number_detection: str = Form(default="auto"),
    provider_profile_id: str = Form(default=""),
    model: str = Form(default=""),
    provider: str = Form(default=""),
    base_url: str = Form(default=""),
    api_key: str = Form(default=""),
    audio_diarization: bool = Form(default=True),
) -> dict[str, Any]:
    if ocr_mode not in {"auto", "never", "always"}:
        raise HTTPException(status_code=422, detail="ocr_mode must be auto, never, or always")
    if source_illegibility < 0 or source_illegibility > 100:
        raise HTTPException(status_code=422, detail="source_illegibility must be between 0 and 100")
    if page_number_detection not in {"auto", "auto_llm", "off"}:
        raise HTTPException(status_code=422, detail="page_number_detection must be auto, auto_llm, or off")
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
        # Extraction, OCR and page-number detection are blocking and can take minutes;
        # running them on the event loop would stall every other API request meanwhile.
        return await run_in_threadpool(
            pdf_corpus_repository.save_asset,
            data,
            filename=file.filename or "source.pdf",
            ocr_mode=ocr_mode,
            ocr_languages=ocr_languages or "eng+fra+deu",
            source_illegibility=source_illegibility,
            content_type=file.content_type or "",
            detect_page_numbers=page_number_detection != "off",
            page_llm=_page_llm(
                page_number_detection, provider_profile_id, model,
                provider=provider, base_url=base_url, api_key=api_key,
            ),
            audio_diarization=audio_diarization,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("PDF asset ingestion failed")
        raise HTTPException(status_code=500, detail=f"PDF asset ingestion failed: {exc}") from exc


@router.post("/api/corpus/ledger/decode")
async def decode_corpus_ledger(file: UploadFile = File(...)) -> dict[str, Any]:
    """Decode an uploaded ``.jsonl.zst`` publication into plain JSONL text.

    The browser importer only reads plaintext JSONL, so archival ledgers are
    decompressed, validated, and evidence-rehydrated here rather than guessed at
    client-side.
    """
    import tempfile

    from .. import derridai_ledger

    name = file.filename or "ledger.jsonl.zst"
    if not name.endswith(".zst"):
        raise HTTPException(status_code=400, detail="Expected a .jsonl.zst ledger.")
    limit = settings.pdf_max_upload_mb * 1024 * 1024
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "ledger.jsonl.zst"
        size = 0
        with target.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(status_code=413, detail="The ledger exceeds the upload size limit.")
                handle.write(chunk)
        try:
            records = derridai_ledger.read_jsonl_zst(target)
        except (derridai_ledger.LedgerValidationError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    text = "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n"
    return {"text": text, "record_count": len(records), "filename": name.removesuffix(".zst")}


@router.post("/api/pdf/assets/{asset_id}/units/preview")
def preview_pdf_asset_units(asset_id: str, body: PdfSourceUnitPolicy) -> dict[str, Any]:
    """How a source-unit policy would divide this source (counts and samples; nothing is saved)."""
    try:
        return pdf_corpus_repository.preview_unit_policy(asset_id, body.model_dump(exclude_none=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/assets/{asset_id}/units")
def derive_pdf_asset_units(asset_id: str, body: PdfSourceUnitPolicy) -> dict[str, Any]:
    """Create a source asset whose evidence units follow the policy; the original is kept."""
    try:
        return pdf_corpus_repository.derive_asset_with_units(asset_id, body.model_dump(exclude_none=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/assets/url")
def import_pdf_asset_url(body: PdfSourceUrlImport) -> dict[str, Any]:
    try:
        data, filename, content_type = fetch_source_url(body.url, max_bytes=settings.pdf_max_upload_mb * 1024 * 1024)
        asset = pdf_corpus_repository.save_asset(
            data, filename=filename, source_illegibility=body.source_illegibility,
            content_type=content_type, source_url=body.url,
            detect_page_numbers=body.page_number_detection != "off",
            page_llm=_page_llm(
                body.page_number_detection, body.provider_profile_id, body.model,
                provider=body.provider, base_url=body.base_url, api_key=body.api_key,
            ),
        )
        return _attach_wikisource_scans(asset, data, body.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        # The remote site refused or lacked the page: an upstream problem, not a server fault.
        logger.warning("URL source fetch returned %s for %s", exc.response.status_code, body.url)
        raise HTTPException(
            status_code=502,
            detail=f"The source site returned HTTP {exc.response.status_code} for {body.url}.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach the source site: {exc}") from exc
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


@router.get("/api/pdf/wikisource/search")
def search_wikisource_texts(
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=12, ge=1, le=30),
    language: str = Query(default="en", pattern="^[a-z]{2,3}$"),
) -> dict[str, Any]:
    try:
        return {"items": search_wikisource(q, limit, language)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Wikisource search failed")
        raise HTTPException(status_code=502, detail=f"Wikisource search failed: {exc}") from exc


@router.post("/api/pdf/gutenberg/import")
def import_gutenberg_text(body: GutenbergImport) -> dict[str, Any]:
    try:
        text, catalog = load_gutenberg_etext(body.etext_id)
        return pdf_corpus_repository.save_asset(
            text.encode("utf-8"), filename=f"{catalog.get('title') or body.etext_id}.txt",
            source_illegibility=body.source_illegibility, content_type="text/plain",
            catalog_metadata=catalog, source_url=f"https://www.gutenberg.org/ebooks/{body.etext_id}",
            detect_page_numbers=body.page_number_detection != "off",
            page_llm=_page_llm(
                body.page_number_detection, body.provider_profile_id, body.model,
                provider=body.provider, base_url=body.base_url, api_key=body.api_key,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Project Gutenberg import failed")
        raise HTTPException(status_code=502, detail=f"Project Gutenberg import failed: {exc}") from exc


@router.get("/api/pdf/assets")
def list_pdf_assets() -> dict[str, Any]:
    return {"items": pdf_corpus_repository.list_assets()}


@router.delete("/api/pdf/assets/{asset_id}")
def delete_pdf_asset(asset_id: str, cascade: bool = Query(default=False)) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.discard_source(asset_id, cascade=cascade)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/api/pdf/assets/{asset_id}")
def get_pdf_asset(asset_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.get_asset(asset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc


@router.patch("/api/pdf/assets/{asset_id}/voice-assignments")
def patch_audio_voice_assignments(asset_id: str, body: PdfAudioVoiceAssignments) -> dict[str, Any]:
    """Name diarized voices and project the reviewed names into current records."""
    try:
        return pdf_corpus_builds.update_voice_assignments(asset_id, body.assignments)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source asset not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc




@router.patch("/api/pdf/assets/{asset_id}/page-labels")
def patch_pdf_asset_page_labels(asset_id: str, body: PdfPageLabelsPatch) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.update_page_labels(asset_id, body.labels)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/api/pdf/assets/{asset_id}/page-estimate")
def patch_pdf_asset_page_estimate(asset_id: str, body: PageEstimatePatch) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.apply_page_estimate(
            asset_id, words_per_page=body.words_per_page, one_record_per_page=body.one_record_per_page,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/assets/{asset_id}/scans/{index}")
def get_pdf_asset_scan(asset_id: str, index: int) -> FileResponse:
    try:
        path = pdf_corpus_repository.scan_image_path(asset_id, index)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Scan page not found") from exc
    return FileResponse(path, media_type="image/jpeg")


@router.patch("/api/pdf/assets/{asset_id}/language")
def patch_pdf_asset_language(asset_id: str, body: PdfAssetLanguagePatch) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.update_asset_language(
            asset_id,
            language=body.language,
            skipped=body.skip_language,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc


@router.patch("/api/pdf/assets/{asset_id}/metadata")
def patch_pdf_asset_metadata(asset_id: str, body: PdfAssetMetadataPatch) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.update_asset_metadata(
            asset_id,
            metadata=body.metadata,
            skip_fields=body.skip_fields,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/assets/{asset_id}/language-suggestion")
def suggest_pdf_asset_language(asset_id: str, body: PdfLlmRequest) -> dict[str, Any]:
    if body.mode != "detect_language":
        raise HTTPException(status_code=422, detail="Language suggestions require detect_language mode.")
    try:
        asset = pdf_corpus_repository.get_asset(asset_id)
        initial = asset.get("initial_metadata") if isinstance(asset.get("initial_metadata"), dict) else {}
        if initial.get("language"):
            return {"mode": "detect_language", "language": initial["language"], "source": "existing"}
        source = "\n\n".join(str(block.get("text") or "") for block in pdf_corpus_repository.load_blocks(asset_id))
        body.raw_text = source[:12000]
        return run_pdf_llm(body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Source language suggestion failed")
        raise HTTPException(status_code=502, detail=f"Source language could not be suggested: {exc}") from exc


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
    request: Request,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    ids: str = Query(default="", max_length=20000),
    around: str = Query(default="", max_length=200),
    page: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    access = AccessContext.for_user(require_admin(request))
    try:
        return document_queries.source_units_page(
            access,
            asset_id,
            offset=offset,
            limit=limit,
            ids=[value.strip() for value in ids.split(",") if value.strip()],
            around=around or None,
            page=page,
            repository=pdf_corpus_repository,
        )
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidQuery as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
    # Not stored: these are live readings of what the build is waiting for right now.
    build["llm_activity"] = pdf_corpus_builds.llm_activity(build_id)
    request_payload = build.get("request") if isinstance(build.get("request"), dict) else {}
    provider = str(request_payload.get("provider") or build.get("provider") or "ollama")
    model = str(request_payload.get("model") or build.get("model") or "")
    capacity_key = provider_capacity_key(
        provider_profile_id=str(request_payload.get("provider_profile_id") or "") or None,
        provider=provider,
        base_url=str(request_payload.get("base_url") or "") or None,
        model=model or None,
    )
    capacity_limit = provider_limit(
        request_payload.get("max_concurrent_requests"), default=1, maximum=64
    )
    provider_snapshot = capacity_coordinator.snapshot(
        "provider_generation", capacity_key, limit=capacity_limit
    )
    build["provider_capacity"] = {
        "limit": provider_snapshot.limit,
        "active": provider_snapshot.active,
        "waiting": provider_snapshot.waiting,
    }
    if provider == "ollama":
        ollama_limit = capacity_coordinator.configured_limit(
            "ollama_runtime",
            "global",
            fallback=max(1, int(settings.rag_ollama_max_concurrent)),
        )
        ollama_snapshot = capacity_coordinator.snapshot(
            "ollama_runtime", "global", limit=ollama_limit
        )
        build["ollama_capacity"] = {
            "limit": ollama_snapshot.limit,
            "active": ollama_snapshot.active,
            "waiting": ollama_snapshot.waiting,
        }
    return build


@router.get("/api/pdf/corpus-builds/{build_id}/llm-live-output")
def get_pdf_corpus_llm_live_output(build_id: str, request: Request) -> dict[str, Any]:
    """Current unvalidated model drafts for an administrator who opened Model activity."""
    require_admin(request)
    try:
        return pdf_corpus_builds.llm_live_output(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc

@router.get("/api/pdf/corpus-builds/{build_id}/llm-trace")
def get_pdf_corpus_llm_trace(build_id: str, request: Request) -> dict[str, Any]:
    """Rendered prompts and validated/raw outputs for administrator build inspection."""
    require_admin(request)
    try:
        return pdf_corpus_builds.llm_trace(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@router.get("/api/pdf/corpus-builds/{build_id}/document-intelligence")
def get_pdf_corpus_document_intelligence(build_id: str, request: Request) -> dict[str, Any]:
    """Retained derived linguistic-analysis run for inspection and reproducibility."""
    access = AccessContext.for_user(require_admin(request))
    try:
        value = intelligence_reads.build_document_intelligence(
            access,
            build_id,
            builds_service=pdf_corpus_builds,
        )
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if value is None:
        raise HTTPException(
            status_code=404,
            detail="Document intelligence has not run for this build.",
        )
    return value


@router.get("/api/pdf/corpus-builds/{build_id}/semantic-content-graph")
def get_pdf_corpus_semantic_content_graph(build_id: str) -> dict[str, Any]:
    """Current reviewer-safe semantic graph rebuilt from the latest Record revisions."""
    try:
        return pdf_corpus_builds.semantic_content_graph(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@router.get("/api/pdf/corpus-builds/{build_id}/semantic-content-graph/view")
def get_pdf_corpus_semantic_content_graph_view(
    build_id: str,
    q: str = Query("", max_length=200),
    types: list[str] = Query(default_factory=list),
    relation_kind: str = Query("all", pattern="^(all|semantic|observational)$"),
    focus: str = Query("", max_length=200),
    node_limit: int = Query(80, ge=1, le=250),
    edge_limit: int = Query(400, ge=0, le=1200),
    min_mentions: int = Query(0, ge=0),
    index_offset: int = Query(0, ge=0),
    index_limit: int = Query(50, ge=1, le=200),
    index_sort: str = Query("mentions", pattern="^(mentions|label|degree|records)$"),
) -> dict[str, Any]:
    """Bounded, ranked view of the semantic graph (overview or one entity's neighbourhood).

    Large corpora can hold tens of thousands of entities; clients receive a capped
    slice, facet counts, and a paged index, with truncation reported explicitly.
    """
    try:
        return pdf_corpus_builds.semantic_content_graph_view(
            build_id,
            query=q,
            types=types,
            relation_kind=relation_kind,
            focus=focus,
            node_limit=node_limit,
            edge_limit=edge_limit,
            min_mentions=min_mentions,
            index_offset=index_offset,
            index_limit=index_limit,
            index_sort=index_sort,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@router.get("/api/pdf/corpus-builds/{build_id}/records/{record_id}/semantic-map")
def get_pdf_corpus_record_semantic_map(build_id: str, record_id: str) -> dict[str, Any]:
    """Reviewer-safe semantic map of one Record and the Records it shares nodes with."""
    try:
        return pdf_corpus_builds.record_semantic_map(build_id, record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build or record not found") from exc


@router.get("/api/records/{record_id}/semantic-map")
def get_record_semantic_map(record_id: str) -> dict[str, Any]:
    """Read or materialize the semantic map associated with a published Record.

    Missing historical provenance produces a valid empty map instead of a
    "map not available" failure. Records with provenance materialize and persist
    their current projection on first access.
    """
    build_id = system_store.get_record_build_id(record_id)
    if build_id:
        try:
            return pdf_corpus_builds.record_semantic_map(build_id, record_id)
        except KeyError:
            pass
    return {
        "version": 1,
        "kind": "record_semantic_map",
        "record_id": record_id,
        "record_revision": 0,
        "record_text_sha256": "",
        "layers": {
            "document_intelligence": {"status": "missing"},
            "terms": {"status": "missing"},
        },
        "mentions": [],
        "nodes": [],
        "edges": [],
        "linked_records": [],
        "summary": {
            "local_nodes": 0,
            "shown_local_nodes": 0,
            "neighbor_nodes": 0,
            "in_record_edges": 0,
            "outward_edges": 0,
            "linked_records": 0,
        },
        "epistemic_note": (
            "No semantic relationships have been derived for this Record yet. "
            "The map remains a valid empty derived projection."
        ),
    }


@router.get("/api/records/{record_id}/semantic-map-build")
def get_record_semantic_map_build(record_id: str) -> dict[str, Any]:
    """Resolve the build whose Document Intelligence covers a published Record.

    A published Record never carries `build_id` (it is stripped at publication);
    this looks up the provenance recorded when the build was published so the
    reviewer-safe semantic map endpoints above can still be reached by record_id.
    """
    return {"build_id": system_store.get_record_build_id(record_id)}


@router.get("/api/works/{work}/semantic-map-builds")
def get_work_semantic_map_builds(work: str) -> dict[str, Any]:
    """Resolve the build(s) whose Document Intelligence covers a Work's Records."""
    return {"build_ids": system_store.list_build_ids_for_work(work)}


@router.get("/api/works/{work}/semantic-map-records")
def get_work_semantic_map_records(work: str) -> dict[str, Any]:
    """Published Record IDs (with their builds) of a Work, so a Record's semantic map can be opened from the Work.

    IDs only: no text or metadata leaves here, so this is as safe for researchers as the build lookup above.
    """
    return {"records": system_store.list_records_for_work(work)}


@router.get("/api/works/{work}/semantic-map")
def get_work_semantic_map(work: str) -> dict[str, Any]:
    """Persisted visual Work map projected from the canonical semantic graph.

    The first request after an invalidation materializes System Data. Subsequent
    requests are indexed reads and do not rescan corpus Records or relationships.
    """
    rows = system_store.list_records_for_work(work, limit=500)
    records_by_build: dict[str, list[str]] = {}
    for row in rows:
        build_id = str(row.get("build_id") or "")
        record_id = str(row.get("record_id") or "")
        if build_id and record_id:
            records_by_build.setdefault(build_id, []).append(record_id)

    sources: list[dict[str, Any]] = []
    generations: dict[str, int] = {}
    for build_id, record_ids in records_by_build.items():
        payload: dict[str, Any] | None = None
        try:
            payload = pdf_corpus_builds.work_semantic_map(build_id, work)
        except KeyError:
            # Older records may have acquired their Work association at publication
            # even when the build-time Record lacked a work field. The Record
            # projections are still persisted; derive the same visual source
            # contract from their local canonical nodes.
            pass
        generations[build_id] = int(system_store.semantic_map_state(build_id).get("generation") or 0)
        if payload is not None:
            for source in payload.get("sources") or []:
                if isinstance(source, dict) and str(source.get("id") or "") in record_ids:
                    sources.append(source)
            continue

        for record_id in record_ids:
            try:
                record_map = pdf_corpus_builds.record_semantic_map(build_id, record_id)
            except KeyError:
                continue
            local_nodes = [
                node
                for node in record_map.get("nodes") or []
                if isinstance(node, dict) and node.get("local")
            ]
            sources.append({
                "id": record_id,
                "work": work,
                "concepts": sorted({
                    str(node.get("label") or "")
                    for node in local_nodes
                    if node.get("type") == "concept" and node.get("label")
                }, key=str.casefold),
                "topics": sorted({
                    str(node.get("label") or "")
                    for node in local_nodes
                    if node.get("type") == "topic" and node.get("label")
                }, key=str.casefold),
                "persons": sorted({
                    str(node.get("label") or "")
                    for node in local_nodes
                    if node.get("type") in {"person", "character"} and node.get("label")
                }, key=str.casefold),
            })

    deduped: dict[str, dict[str, Any]] = {}
    for source in sources:
        record_id = str(source.get("id") or "")
        key = record_id or json.dumps(source, sort_keys=True, ensure_ascii=False)
        deduped.setdefault(key, source)
    return {
        "state": "ready" if deduped else "empty",
        "kind": "work_semantic_map_sources",
        "work": work,
        "sources": list(deduped.values()),
        "record_count": len(deduped),
        "build_generations": generations,
    }


@router.get("/api/pdf/corpus-builds/{build_id}/semantic-content-graph/nodes/{node_id}")
def get_pdf_corpus_semantic_graph_node(build_id: str, node_id: str) -> dict[str, Any]:
    """One semantic-graph node with its relations and Records, for graph walking."""
    try:
        return pdf_corpus_builds.semantic_graph_node(build_id, node_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build or graph node not found") from exc


@router.post("/api/pdf/corpus-builds/{build_id}/document-intelligence/rerun")
def rerun_pdf_corpus_document_intelligence(build_id: str) -> dict[str, Any]:
    """Refresh derived document NLP after text/topology review changes."""
    try:
        return pdf_corpus_builds.rerun_document_intelligence(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
    cursor: str | None = Query(default=None, max_length=512),
    direction: str = Query(default="forward", pattern="^(forward|backward)$"),
) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.page_records(build_id, offset=offset, limit=limit, needs_review=needs_review, disposition=disposition, metadata_incomplete=metadata_incomplete, source_problem=source_problem, review_queue=review_queue, query=query, cursor=cursor, direction=direction)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        from ..corpus_queue_projection import QueueCursorError, StaleQueueCursor
        if isinstance(exc, QueueCursorError):
            raise HTTPException(
                status_code=409 if isinstance(exc, StaleQueueCursor) else 422,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc
        raise


@router.post("/api/pdf/corpus-builds/{build_id}/review-queue/rebuild")
def rebuild_pdf_corpus_review_queue(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.rebuild_review_queue(build_id)
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


@router.post("/api/pdf/corpus-builds/{build_id}/warnings/acknowledge")
def acknowledge_pdf_corpus_warnings(build_id: str, body: BuildWarningAcknowledgement, request: Request) -> dict[str, Any]:
    user = require_admin(request)
    try:
        build = pdf_corpus_builds.acknowledge_warnings(build_id, body.warnings, user.username)
        # Only what changed: the acknowledgements, not the whole build.
        return {"build_id": build["build_id"], "warning_acknowledgements": build.get("warning_acknowledgements") or {}}
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


@router.post("/api/pdf/corpus-builds/{build_id}/pause")
def pause_pdf_corpus_build(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.pause(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/api/pdf/corpus-builds/{build_id}")
def delete_pdf_corpus_build(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.discard_build(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/settle-metadata")
def settle_pdf_corpus_metadata(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.settle_metadata_unresolved(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/resume")
def resume_pdf_corpus_build(build_id: str, body: PdfCorpusBuildResume) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.resume(
            build_id, body.model_dump(exclude_unset=True, exclude_none=True),
            resolve_provider=_resolve_pdf_corpus_provider,
        )
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
        return pdf_corpus_builds.metadata_decision(build_id, record_id, body.field, body.value, body.expected_revision, body.confirm_no_supported_value, body.evidence_block_ids, body.evidence_source, body.evidence_note, body.external_evidence_block_ids)
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
        return pdf_corpus_builds.apply_metadata_decisions(
            build_id,
            record_id,
            body.changes,
            body.expected_revision,
            body.confirmed_absent_fields,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/corpus-builds/{build_id}/semantic-aliases")
def get_pdf_corpus_semantic_aliases(build_id: str, include_retired: bool = False) -> dict[str, Any]:
    """Reviewed alias sets: which surfaces a reviewer has said name one identity."""
    try:
        return pdf_corpus_builds.semantic_aliases(build_id, include_retired=include_retired)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/pdf/corpus-builds/{build_id}/semantic-aliases")
def create_pdf_corpus_semantic_alias(build_id: str, body: PdfCorpusSemanticAliasSet) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.save_semantic_alias(
            build_id, kind=body.kind, canonical_label=body.canonical_label,
            aliases=body.aliases, reason=body.reason, replaces=body.replaces,
        )
    except AliasConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build or alias set not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/corpus-builds/{build_id}/semantic-aliases/sources")
def get_pdf_corpus_semantic_alias_sources(build_id: str) -> dict[str, Any]:
    """Other corpus builds with reviewed identities that can be imported into this one."""
    try:
        return {"items": pdf_corpus_builds.semantic_alias_sources(build_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@router.post("/api/pdf/corpus-builds/{build_id}/semantic-aliases/import")
def import_pdf_corpus_semantic_aliases(build_id: str, body: PdfCorpusSemanticAliasImport) -> dict[str, Any]:
    """Copy reviewed identities from another build; clashes are skipped and reported."""
    try:
        return pdf_corpus_builds.import_semantic_aliases(build_id, body.source_build_id, body.alias_set_ids)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build or alias set not found") from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/api/pdf/corpus-builds/{build_id}/semantic-aliases/{alias_set_id}")
def retire_pdf_corpus_semantic_alias(build_id: str, alias_set_id: str) -> dict[str, Any]:
    """Retire a reviewed alias set; it stays in the build's history."""
    try:
        return pdf_corpus_builds.retire_semantic_alias(build_id, alias_set_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build or alias set not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/corpus-builds/{build_id}/records/{record_id}/field-precedents")
def get_pdf_corpus_record_field_precedents(build_id: str, record_id: str) -> dict[str, Any]:
    """Every field's precedents kept from the last enrichment, re-verified for this reviewer."""
    try:
        return pdf_corpus_builds.record_precedents(build_id, record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc


@router.get("/api/pdf/corpus-builds/{build_id}/records/{record_id}/precedents")
def get_pdf_corpus_record_precedents(
    build_id: str, record_id: str, field: str, refresh: bool = False
) -> dict[str, Any]:
    """Advisory reviewed precedents for one field, as metadata enrichment used them (``refresh`` searches again)."""
    try:
        return pdf_corpus_builds.metadata_precedents(build_id, record_id, field, refresh=refresh)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/pdf/corpus-builds/{build_id}/records/{record_id}/research-claims")
def get_pdf_corpus_record_research_claims(build_id: str, record_id: str) -> dict[str, Any]:
    """Reviewer-validated Research claims that cite this record (cross-reference only)."""
    try:
        record = pdf_corpus_repository.get_record(build_id, record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    return {"items": validated_claims_citing(system_store, record)}


@router.get("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata-cache")
def get_pdf_corpus_metadata_cache(build_id: str, record_id: str, field: str) -> dict[str, Any]:
    try:
        record = pdf_corpus_repository.get_record(build_id, record_id)
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


@router.get("/api/pdf/corpus-builds/{build_id}/records/{record_id}/evidence-suggestions")
def suggest_pdf_corpus_record_evidence(
    request: Request, build_id: str, record_id: str, field: str = Query(min_length=1, max_length=120), limit: int = Query(5, ge=1, le=20)
) -> dict[str, Any]:
    require_admin(request)
    try:
        return pdf_corpus_builds.suggest_evidence_result(build_id, record_id, field, limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/evidence-suggestions/llm")
def suggest_pdf_corpus_record_evidence_llm(
    request: Request, build_id: str, record_id: str, body: PdfCorpusEvidenceSuggestLlm
) -> dict[str, Any]:
    require_admin(request)
    payload = body.model_dump(exclude={"field", "limit"}, exclude_none=True)
    try:
        items = pdf_corpus_builds.suggest_evidence_llm(
            build_id, record_id, body.field, _resolve_pdf_corpus_provider(payload), body.limit
        )
        return {"items": items}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/evidence")
def patch_pdf_corpus_record_evidence(build_id: str, record_id: str, body: PdfCorpusEvidencePatch) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.patch_evidence(
            build_id, record_id, body.field, body.block_ids, body.confidence, body.reason, body.expected_revision,
            body.source_kind, body.external_block_ids,
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




@router.get("/api/pdf/corpus-builds/{build_id}/retired-records")
def list_retired_pdf_corpus_records(build_id: str) -> dict[str, Any]:
    try:
        return {"items": pdf_corpus_builds.retired_records(build_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@router.get("/api/pdf/corpus-builds/{build_id}/metadata-exemplars/diagnosis")
def diagnose_pdf_corpus_metadata_exemplars(build_id: str) -> dict[str, Any]:
    """Why a build has (or lacks) metadata exemplars; counts only, no record content."""
    from ..metadata_exemplar_projection import diagnose_build_metadata_exemplars

    try:
        return diagnose_build_metadata_exemplars(pdf_corpus_repository, build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@router.post("/api/pdf/corpus-builds/{build_id}/metadata-exemplars/project")
def project_pdf_corpus_metadata_exemplars(build_id: str) -> dict[str, Any]:
    """Rebuild this build's exemplar projection now and report the real error, if any."""
    try:
        return pdf_corpus_builds._project_metadata_exemplars(build_id, force=True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except Exception as exc:
        logger.exception("Metadata exemplar projection failed")
        raise HTTPException(status_code=503, detail=f"Metadata exemplar projection failed: {exc}") from exc


@router.get("/api/pdf/corpus-builds/{build_id}/records/{record_id}/context")
def get_pdf_corpus_record_context(build_id: str, record_id: str, before: int = Query(default=6, ge=0, le=30), after: int = Query(default=6, ge=0, le=30)) -> dict[str, Any]:
    """The text of neighbouring records, in document order, for reading a record in context."""
    try:
        return pdf_corpus_repository.record_context(build_id, record_id, before=before, after=after)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/from-selection")
def create_pdf_corpus_record_from_selection(build_id: str, record_id: str, body: PdfCorpusRecordFromSelection) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.create_from_selection(
            build_id, record_id, body.start, body.end, body.left, body.right, body.expected_revision,
        )
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
        return pdf_corpus_builds.split(build_id, record_id, body.after_block_id, body.expected_revision, body.offset)
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


@router.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/viewed", deprecated=True)
def mark_pdf_corpus_record_viewed(build_id: str, record_id: str) -> dict[str, Any]:
    """Compatibility read of historical activity; does not count opens or mutate Records."""
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
        return pdf_corpus_builds.publish(
            build_id, require_acceptance=body.require_acceptance, accept_unreviewed=body.accept_unreviewed
        )
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


@router.get("/api/pdf/publications/{publication_id}/integrity")
def download_pdf_corpus_publication_integrity(publication_id: str) -> FileResponse:
    path = pdf_corpus_repository.publication_path(publication_id)
    integrity = pdf_corpus_repository.publication_integrity_path(publication_id)
    if not path.exists() or not integrity.exists():
        raise HTTPException(status_code=404, detail="Publication integrity file not found")
    return FileResponse(integrity, media_type="text/plain", filename=f"{publication_id}.sha512")
