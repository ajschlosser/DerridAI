# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from ..config import APP_GIT_COMMIT, APP_VERSION, settings
from ..http_auth import request_user, require_admin
from ..llm import llm_status
from ..services import rag_jobs, store
from ..system_store import system_store

router = APIRouter(tags=["system"])


@router.get("/api/live")
def live() -> dict[str, Any]:
    return {"ok": True, "version": APP_VERSION, "git_commit": APP_GIT_COMMIT or None}


@router.get("/api/health")
def health(request: Request) -> dict[str, Any]:
    chroma = store.health()
    if request_user(request).role != "admin":
        # Researchers need availability and collection counts to load the
        # workspace. Paths, endpoints, tenant/database names, error details,
        # provider configuration, and internal generation defaults are admin
        # diagnostics and should stay server-side.
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
    embedding_defaults = system_store.embedding_defaults()
    return {
        "ok": True,
        "version": APP_VERSION,
        "git_commit": APP_GIT_COMMIT or None,
        "chroma": chroma,
        "chroma_path": settings.chroma_path,
        "chroma_mode": chroma.get("mode") or settings.chroma_mode,
        "embedding_provider": embedding_defaults["embedding_provider"],
        "embedding_model": embedding_defaults.get("embedding_model"),
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
def config(request: Request) -> dict[str, Any]:
    require_admin(request)
    embedding_defaults = system_store.embedding_defaults()
    return {
        "version": APP_VERSION,
        "git_commit": APP_GIT_COMMIT or None,
        "defaults": {
            "embedding_provider": embedding_defaults["embedding_provider"],
            "embedding_model": embedding_defaults.get("embedding_model"),
            "chat_provider": "ollama",
            "chat_model": settings.ollama_model,
            "ollama_base_url": settings.ollama_base_url,
            "openai_base_url": settings.openai_compat_base_url,
            "openai_model": settings.openai_compat_model,
        },
        "chroma": store.health(),
    }

