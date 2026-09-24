# Copyright 2026 Aaron John Schlosser, PhD.
"""Application health, configuration, and provider-profile API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from ..chroma_store import ChromaStore
from ..config import APP_GIT_COMMIT, APP_VERSION, settings
from ..dependencies import get_rag_jobs, get_store, request_user, require_admin
from ..jobs import RAGJobManager
from ..llm import llm_status
from ..models import ResearcherProviderProfilesUpdate, ResearcherProviderStatusRequest
from ..system_store import system_store

router = APIRouter(tags=["system"])


@router.get("/api/system/researcher-providers")
def researcher_provider_profiles(request: Request) -> dict[str, Any]:
    user = request_user(request)
    profiles = system_store.researcher_profiles()
    if user.role != "admin":
        profiles = [
            {
                key: value
                for key, value in profile.items()
                if key not in {"base_url", "has_api_key", "api_key"}
            }
            for profile in profiles
        ]
    return {"profiles": profiles}


@router.put("/api/system/researcher-providers")
def update_researcher_provider_profiles(
    body: ResearcherProviderProfilesUpdate,
    request: Request,
) -> dict[str, Any]:
    require_admin(request)
    return {"profiles": system_store.set_researcher_profiles(body.profiles)}


@router.get("/api/system/storage")
def system_storage_info(request: Request) -> dict[str, Any]:
    """Describe the durable server-owned metadata store for administrators."""
    require_admin(request)
    return system_store.storage_info()


@router.post("/api/system/researcher-providers/status")
def researcher_provider_status(
    body: ResearcherProviderStatusRequest,
    request: Request,
) -> dict[str, Any]:
    require_admin(request)
    stored = system_store.researcher_profile(body.id) if body.id else None
    api_key = body.api_key or (stored or {}).get("api_key")
    return llm_status(
        body.type,
        base_url=body.base_url or (stored or {}).get("base_url"),
        api_key=api_key,
    )


@router.post("/api/system/researcher-providers/availability")
def researcher_provider_availability(
    body: ResearcherProviderStatusRequest,
    request: Request,
) -> dict[str, Any]:
    request_user(request)
    stored = system_store.researcher_profile(body.id) if body.id else None
    if not stored:
        return {
            "available": False,
            "model_available": False,
            "error": "Provider profile was not found.",
        }

    status = llm_status(
        str(stored.get("type") or body.type),
        base_url=str(stored.get("base_url") or "") or None,
        api_key=str(stored.get("api_key") or "") or None,
    )
    configured_model = str(stored.get("model") or "").strip()
    models = {
        str(item.get("name") or "")
        for item in status.get("models") or []
        if isinstance(item, dict)
    }
    return {
        "available": bool(status.get("available")),
        "model_available": bool(configured_model) and configured_model in models,
        "configured_model": configured_model,
        "models": status.get("models") or [],
        "error": status.get("error"),
    }


@router.get("/api/live")
def live() -> dict[str, Any]:
    return {
        "ok": True,
        "version": APP_VERSION,
        "git_commit": APP_GIT_COMMIT or None,
    }


@router.get("/api/health")
def health(
    request: Request,
    store: ChromaStore = Depends(get_store),
    rag_jobs: RAGJobManager = Depends(get_rag_jobs),
) -> dict[str, Any]:
    chroma = store.health()
    if request_user(request).role != "admin":
        # Researchers need availability and collection counts to load the
        # workspace. Paths, endpoints, tenant/database names, error details,
        # provider configuration, and generation defaults remain admin-only.
        public_chroma = {
            key: chroma.get(key)
            for key in ("available", "mode", "heartbeat_ok", "collection_count")
            if key in chroma
        }
        return {
            "ok": True,
            "version": APP_VERSION,
            "git_commit": APP_GIT_COMMIT or None,
            "chroma": public_chroma,
        }

    ollama = llm_status("ollama")
    return {
        "ok": True,
        "version": APP_VERSION,
        "git_commit": APP_GIT_COMMIT or None,
        "chroma": chroma,
        "chroma_path": settings.chroma_path,
        "chroma_mode": chroma.get("mode") or settings.chroma_mode,
        "embedding_provider": settings.embedding_provider,
        "ollama": ollama,
        "ollama_model": settings.ollama_model,
        "ollama_embed_model": settings.ollama_embed_model,
        "openai_compat_base_url": settings.openai_compat_base_url,
        "openai_compat_model": settings.openai_compat_model,
        "rag_concurrency": rag_jobs.concurrency_status(),
        "rag_defaults": {
            "k": settings.rag_default_k,
            "fetch_k": settings.rag_default_fetch_k,
            "rerank_top_n": settings.rag_default_rerank_top_n,
            "lambda_mult": settings.rag_default_lambda_mult,
            "rrf_k": settings.rag_default_rrf_k,
            "query_decomposition_num_predict": settings.rag_default_query_num_predict,
            "evidence_record_char_limit": settings.rag_default_record_char_limit,
            "evidence_total_char_limit": settings.rag_default_total_char_limit,
            "cross_encoder_model": settings.rag_cross_encoder_model,
        },
        "llm_defaults": {
            "num_ctx": 16384,
            "metadata_num_predict": settings.llm_metadata_num_predict,
            "text_num_predict": settings.llm_text_num_predict,
            "temperature": 0.0,
            "top_k": 0,
            "top_p": 1.0,
            "repeat_penalty": 1.1,
            "think": False,
            "keep_alive": settings.ollama_keep_alive,
            "max_fields": settings.llm_max_fields,
        },
    }


@router.get("/api/config")
def config(
    request: Request,
    store: ChromaStore = Depends(get_store),
) -> dict[str, Any]:
    require_admin(request)
    return {
        "version": APP_VERSION,
        "git_commit": APP_GIT_COMMIT or None,
        "defaults": {
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.ollama_embed_model,
            "chat_provider": "ollama",
            "chat_model": settings.ollama_model,
            "ollama_base_url": settings.ollama_base_url,
            "openai_base_url": settings.openai_compat_base_url,
            "openai_model": settings.openai_compat_model,
        },
        "chroma": store.health(),
    }
