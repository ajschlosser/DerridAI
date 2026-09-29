# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..corpus_builder import pdf_corpus_repository
from ..data_retention import RetentionPolicy
from ..http_auth import request_user, require_admin
from ..llm import llm_status
from ..metadata_memory import MetadataMemoryService
from ..models import (
    ResearcherProviderProfilesUpdate,
    ResearcherProviderStatusRequest,
    SystemAudioTranscriptionUpdate,
    SystemEmbeddingDefaultsProbe,
    SystemEmbeddingDefaultsUpdate,
)
from ..services import retention_service, store
from ..system_chroma_console import (
    execute_system_chroma_command,
    list_system_chroma_collections,
    validate_system_chroma_command,
)
from ..system_store import system_store

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)
metadata_memory = MetadataMemoryService(store, pdf_corpus_repository)


@router.get("/api/system/researcher-providers")
def researcher_provider_profiles(request: Request) -> dict[str, Any]:
    user = request_user(request)
    profiles = system_store.researcher_profiles()
    if user.role != "admin":
        profiles = [{k: v for k, v in profile.items() if k not in {"base_url", "has_api_key", "api_key"}} for profile in profiles]
    return {"profiles": profiles}


@router.put("/api/system/researcher-providers")
def update_researcher_provider_profiles(body: ResearcherProviderProfilesUpdate, request: Request) -> dict[str, Any]:
    require_admin(request)
    return {"profiles": system_store.set_researcher_profiles(body.profiles)}


@router.get("/api/system/embedding-defaults")
def embedding_defaults(request: Request) -> dict[str, Any]:
    require_admin(request)
    return system_store.embedding_defaults()


@router.put("/api/system/embedding-defaults")
def update_embedding_defaults(
    body: SystemEmbeddingDefaultsUpdate,
    request: Request,
) -> dict[str, Any]:
    require_admin(request)
    try:
        return system_store.set_embedding_defaults(
            body.embedding_provider,
            body.embedding_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/system/embedding-defaults/status")
def embedding_defaults_status(
    request: Request,
    body: SystemEmbeddingDefaultsProbe | None = None,
) -> dict[str, Any]:
    """Is the configured (or a not-yet-saved draft) embedding model reachable?"""
    require_admin(request)
    from ..embedding_health import check_embedding_defaults

    return check_embedding_defaults(
        body.embedding_provider if body else None,
        body.embedding_model if body else None,
    )


@router.get("/api/system/audio-transcription")
def audio_transcription(request: Request) -> dict[str, Any]:
    require_admin(request)
    return system_store.audio_transcription_settings()


@router.put("/api/system/audio-transcription")
def update_audio_transcription(body: SystemAudioTranscriptionUpdate, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        return system_store.set_audio_transcription_settings(
            base_url=body.base_url, model=body.model, api_key=body.api_key, clear_key=body.clear_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/system/audio-transcription/status")
def audio_transcription_status(request: Request) -> dict[str, Any]:
    """Is the transcription endpoint reachable with the stored key? (Lists models; sends no audio.)"""
    require_admin(request)
    import httpx

    config = system_store.audio_transcription_settings(include_key=True)
    result: dict[str, Any] = {"reachable": False, "model": config["model"], "base_url": config["base_url"], "error": "", "hint": ""}
    if not config.get("api_key"):
        result["error"] = "No API key is set."
        result["hint"] = "Add an audio transcription API key below."
        return result
    try:
        response = httpx.get(
            f"{config['base_url']}/models",
            headers={"Authorization": f"Bearer {config['api_key']}"},
            timeout=httpx.Timeout(15.0, connect=8.0),
        )
        if response.status_code in (401, 403):
            result["error"] = f"HTTP {response.status_code}"
            result["hint"] = "The provider rejected this key."
        elif response.status_code >= 400:
            result["error"] = f"HTTP {response.status_code}"
        else:
            result["reachable"] = True
    except httpx.HTTPError as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"[:300]
        result["hint"] = "The endpoint could not be reached from the server."
    return result


@router.get("/api/system/storage")
def system_storage_info(request: Request) -> dict[str, Any]:
    """Describe the durable server-owned metadata store for administrators."""
    require_admin(request)
    return system_store.storage_info()


@router.post("/api/system/researcher-providers/status")
def researcher_provider_status(body: ResearcherProviderStatusRequest, request: Request) -> dict[str, Any]:
    require_admin(request)
    stored = system_store.researcher_profile(body.id) if body.id else None
    api_key = body.api_key or (stored or {}).get("api_key")
    return llm_status(body.type, base_url=body.base_url or (stored or {}).get("base_url"), api_key=api_key)


@router.post("/api/system/researcher-providers/availability")
def researcher_provider_availability(
    body: ResearcherProviderStatusRequest, request: Request
) -> dict[str, Any]:
    request_user(request)
    stored = system_store.researcher_profile(body.id) if body.id else None
    if not stored:
        return {"available": False, "model_available": False, "error": "Provider profile was not found."}
    status = llm_status(
        str(stored.get("type") or body.type),
        base_url=str(stored.get("base_url") or "") or None,
        api_key=str(stored.get("api_key") or "") or None,
    )
    configured_model = str(stored.get("model") or "").strip()
    models = {str(item.get("name") or "") for item in status.get("models") or [] if isinstance(item, dict)}
    model_available = bool(configured_model) and configured_model in models
    return {
        "available": bool(status.get("available")),
        "model_available": model_available,
        "configured_model": configured_model,
        "models": status.get("models") or [],
        "error": status.get("error"),
    }



@router.get("/api/system/metadata-memory")
@router.get("/api/system/data/metadata-memory")
def inspect_metadata_memory(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    field: str = Query(default="", max_length=120),
    kind: str = Query(default="", max_length=40),
    build_id: str = Query(default="", max_length=160),
    language: str = Query(default="", max_length=40),
    q: str = Query(default="", max_length=300),
) -> dict[str, Any]:
    """Inspect learned metadata precedents as scholarly memory, not vector rows."""

    require_admin(request)
    return metadata_memory.list_entries(
        limit=limit,
        offset=offset,
        field=field,
        kind=kind,
        build_id=build_id,
        language=language,
        query=q,
    )


@router.get("/api/system/chroma/collections")
def system_chroma_collections(request: Request) -> dict[str, Any]:
    """List internal Chroma collections without exposing them as ordinary corpus stores."""

    require_admin(request)
    try:
        return {"collections": list_system_chroma_collections(store)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/system/chroma/validate")
def validate_system_chroma(body: dict[str, Any], request: Request) -> dict[str, Any]:
    """Validate and explain one read-only CLI-style system Chroma command."""

    require_admin(request)
    try:
        return validate_system_chroma_command(store, str(body.get("command") or ""))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/system/chroma/query")
def query_system_chroma(body: dict[str, Any], request: Request) -> dict[str, Any]:
    """Execute a previously understandable read-only system Chroma command."""

    require_admin(request)
    try:
        return execute_system_chroma_command(store, str(body.get("command") or ""))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/system/research-memory")
def inspect_research_memory(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    run_id: str = Query(default="", max_length=160),
) -> dict[str, Any]:
    """Inspect durable Research memory without exposing another user's private runs."""

    user = request_user(request)
    owner = None if user.role == "admin" else user.username
    claims = system_store.list_generated_claims(
        owner=owner,
        run_id=run_id or None,
        limit=limit,
    )
    bindings: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = str(claim.get("claim_id") or "")
        if claim_id:
            bindings.extend(
                system_store.list_claim_support_bindings(claim_id, owner=owner)
            )
    return {
        "responses": system_store.list_response_memory(owner=owner, limit=limit),
        "claims": claims,
        "support_bindings": bindings[: max(1, limit * 4)],
    }


class DataRetentionApply(BaseModel):
    store_ids: list[str] | None = Field(default=None, max_length=500)


@router.get("/api/system/data-retention")
def data_retention(request: Request) -> dict[str, Any]:
    """Operational stores, their sizes, and what the saved policy would remove now."""
    require_admin(request)
    return retention_service.overview()


@router.put("/api/system/data-retention")
def update_data_retention(body: RetentionPolicy, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        retention_service.save_policy(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return retention_service.overview()


@router.post("/api/system/data-retention/apply")
def apply_data_retention(body: DataRetentionApply, request: Request) -> dict[str, Any]:
    """Remove what the saved policy selects now. The UI previews and confirms first."""
    user = require_admin(request)
    result = retention_service.apply(store_ids=set(body.store_ids) if body.store_ids is not None else None)
    removed = sum(int(row.get("removed_count") or 0) for row in result["stores"])
    logger.info("Administrator %s applied data retention; %s record(s) removed.", getattr(user, "username", "?"), removed)
    return result


@router.post("/api/system/data-retention/reclaim")
def reclaim_data_retention_space(request: Request) -> dict[str, Any]:
    """Compact the system database so removed records release disk space."""
    require_admin(request)
    try:
        return retention_service.reclaim_disk_space()
    except Exception as exc:  # noqa: BLE001 - surfaced to the administrator
        raise HTTPException(status_code=409, detail=f"Could not reclaim disk space: {exc}") from exc
