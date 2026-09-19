# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import json
import logging
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


from fastapi import FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from .auth import SESSION_COOKIE, AuthUser, auth_store, role_has_capability
from .chroma_store import ChromaStore, StoreAlreadyExistsError
from .config import settings
from .jobs import LLMJobManager, LLMToolJobManager, RAGJobManager, UpsertJobManager
from .llm_tools import run_pdf_llm, run_rag_grade
from .researcher_view import sanitize_rag_job, sanitize_records_payload, summarize_record
from .llm import TouchupFailure, llm_status, propose_touchup, warmup_model
from .models import (
    AnnotationCreateRequest,
    ResearcherProviderStatusRequest,
    BulkUpsert,
    ChromaPathUpdate,
    EmbeddingPreflightRequest,
    DeriveLanguageStoresRequest,
    LLMJobCreate,
    LLMToolJobCreate,
    LLMResultResolutionRequest,
    LLMJobRejectRequest,
    LLMStatusRequest,
    LLMWarmupRequest,
    PdfLlmRequest,
    PdfCorpusBuildCreate,
    PdfPageLabelsPatch,
    PdfCorpusManifestPatch,
    PdfCorpusRecordPatch,
    PdfCorpusRecordTextPatch,
    PdfCorpusEvidencePatch,
    PdfCorpusRecordAccept,
    PdfCorpusRecordDisposition, PdfCorpusReviewDecision, PdfCorpusMetadataDecision,
    PdfCorpusBulkDisposition, PdfCorpusBulkMetadataPatch,
    PdfCorpusRecordMerge,
    PdfCorpusRecordSplit,
    PdfCorpusRecordRerun,
    PdfCorpusProviderSwitch,
    PdfCorpusPublishRequest,
    RAGRunRequest,
    RAGGradeRequest,
    RAGConcurrencyUpdate,
    RecordStatusRequest,
    UpsertJobCreate,
    RecordUpsert,
    SearchRequest,
    StoreCreate,
    StoreDriftRequest,
    StoreEmbeddingUpdate,
    StoreLanguageUpdate,
    StoreProtectionUpdate,
    StoredRecordPatch,
    TouchupRequest,
    TouchupResponse,
    AuthBootstrapRequest,
    AuthLoginRequest,
    UserCreateRequest,
    UserUpdateRequest,
    RoleCreateRequest,
    RolePermissionsUpdate,
    ResearcherProviderProfilesUpdate,
    LanguageDictionaryUpdate,
    LanguageInstallRequest,
)
from .pdf_tools import extract_pdf_text
from .corpus_builder import CORPUS_PROFILES, pdf_corpus_builds, pdf_corpus_repository
from .system_store import system_store, normalize_locale_code
from .i18n_translation import translate_english_dictionary
from .content_filter import enforce_researcher_text

logger = logging.getLogger(__name__)

app = FastAPI(title="DerridAI Corpus API", version="0.52.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(_request: Request, exc: RequestValidationError):
    # Keep Pydantic internals out of the product UI. The client gets a stable
    # machine code and a concise field list; full details remain available to
    # server logs for diagnosis.
    errors = exc.errors()
    fields = []
    for error in errors:
        loc = [str(part) for part in error.get("loc", ()) if str(part) not in {"body", "query", "path"}]
        label = ".".join(loc) if loc else "request"
        if label not in fields:
            fields.append(label)
    logger.warning("Request validation failed for %s: %s", getattr(_request, "url", "request"), errors)
    message = "Some submitted data is invalid. Review the highlighted fields and try again."
    if fields:
        message += " Fields: " + ", ".join(fields[:8]) + ("…" if len(fields) > 8 else "")
    return JSONResponse(status_code=422, content={"detail": message, "code": "request_validation_error", "fields": fields[:50]})


def _non_admin_route_allowed(role: str, path: str, method: str) -> bool:
    """Map non-admin HTTP routes to explicit capabilities.

    Admin is implicitly allowed everywhere. New API surfaces are therefore
    non-admin-denied until they are deliberately added here, matching the
    product rule that new functionality is admin-only by default.
    """
    method = method.upper()
    if path in {"/api/health", "/api/config"} and method == "GET":
        return True
    if path.startswith("/api/i18n/languages") and method == "GET":
        return role_has_capability(role, "i18n.read")
    if path == "/api/system/researcher-providers" and method == "GET":
        return role_has_capability(role, "providers.researcher.use")
    if path == "/api/annotations" and method == "GET":
        return role_has_capability(role, "annotations.read")
    if path == "/api/annotations" and method == "POST":
        return role_has_capability(role, "annotations.write")
    if path.startswith("/api/annotations/") and method == "DELETE":
        return role_has_capability(role, "annotations.write")
    if path == "/api/stores" and method == "GET":
        return role_has_capability(role, "corpus.read")
    if path.startswith("/api/stores/"):
        parts = [part for part in path.split("/") if part]
        if method == "GET" and "export" not in parts and role_has_capability(role, "corpus.read"):
            if len(parts) == 3:
                return True
            if len(parts) == 4 and parts[3] in {"records", "works"}:
                return True
            if len(parts) >= 5 and parts[3] == "records" and parts[4] != "status":
                return True
        if method == "POST" and len(parts) == 4 and parts[3] == "search":
            return role_has_capability(role, "corpus.search")
    if path == "/api/jobs" and method == "GET":
        return role_has_capability(role, "rag.jobs.own")
    if path == "/api/jobs/rag" and method == "POST":
        return role_has_capability(role, "rag.run")
    if path == "/api/jobs/rag/concurrency" and method == "GET":
        return role_has_capability(role, "rag.run")
    if path.startswith("/api/jobs/"):
        parts = [part for part in path.split("/") if part]
        # A user who may start Research must be able to read the one job they
        # just started so the workspace can surface completion. Ownership is
        # still enforced by _researcher_job_access; history/list, cancel and
        # delete remain independently controlled by rag.jobs.own.
        if len(parts) == 3 and method == "GET":
            return role_has_capability(role, "rag.run") or role_has_capability(role, "rag.jobs.own")
        if len(parts) == 3 and method == "DELETE":
            return role_has_capability(role, "rag.jobs.own")
        if len(parts) == 4 and parts[3] == "cancel" and method == "POST":
            return role_has_capability(role, "rag.jobs.own")
    return False


@app.middleware("http")
async def authentication_middleware(request: Request, call_next):
    path = request.url.path
    public_auth = {"/api/auth/status", "/api/auth/bootstrap", "/api/auth/login", "/api/auth/logout", "/api/auth/me"}
    public_i18n = request.method.upper() == "GET" and (
        path == "/api/i18n/languages" or path.startswith("/api/i18n/languages/")
    )
    if not path.startswith("/api/") or path == "/api/live" or path in public_auth or public_i18n:
        return await call_next(request)
    user = auth_store.user_for_session(request.cookies.get(SESSION_COOKIE))
    if user is None:
        return JSONResponse(status_code=401, content={"detail": "Authentication required."})
    request.state.user = user
    if user.role != "admin" and not _non_admin_route_allowed(user.role, path, request.method):
        return JSONResponse(status_code=403, content={"detail": "Your role does not have permission to use this API feature."})
    return await call_next(request)


def _request_user(request: Request) -> AuthUser:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def _require_admin(request: Request) -> AuthUser:
    user = _request_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user


def _stamp_record_activity(record: dict[str, Any], username: str) -> dict[str, Any]:
    """Attach the initiating user to audit entries that arrived without one.

    The browser already stamps normal edits. This server-side pass keeps audit
    provenance intact for direct API clients and older frontends as well.
    """
    copy_record = dict(record)
    updates = copy_record.get("updates")
    if isinstance(updates, list):
        stamped = []
        for update in updates:
            if isinstance(update, dict):
                item = dict(update)
                item.setdefault("initiated_by", username)
                stamped.append(item)
            else:
                stamped.append(update)
        copy_record["updates"] = stamped
    return copy_record


def _session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=14 * 24 * 60 * 60,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )


@app.get("/api/auth/status")
def auth_status(request: Request):
    user = auth_store.user_for_session(request.cookies.get(SESSION_COOKIE))
    return {
        "bootstrap_required": auth_store.bootstrap_required(),
        "authenticated": user is not None,
        "user": user.public() if user else None,
    }


@app.post("/api/auth/bootstrap")
def auth_bootstrap(body: AuthBootstrapRequest, response: Response):
    try:
        user = auth_store.bootstrap_admin(body.username, body.password)
        user = auth_store.record_login(user.id)
        token = auth_store.create_session(user.id)
        _session_cookie(response, token)
        return {"user": user.public(), "bootstrap_required": False}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/login")
def auth_login(body: AuthLoginRequest, response: Response):
    user = auth_store.authenticate(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = auth_store.create_session(user.id)
    _session_cookie(response, token)
    return {"user": user.public()}


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response):
    auth_store.delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def auth_me(request: Request):
    user = auth_store.user_for_session(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return {"user": user.public()}


@app.get("/api/auth/users")
def auth_users(request: Request):
    _require_admin(request)
    return {"users": [user.public() for user in auth_store.list_users()]}


@app.post("/api/auth/users")
def auth_create_user(body: UserCreateRequest, request: Request):
    _require_admin(request)
    try:
        return {"user": auth_store.create_user(body.username, body.password, body.role).public()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/auth/users/{user_id}")
def auth_update_user(user_id: int, body: UserUpdateRequest, request: Request):
    current = _require_admin(request)
    if current.id == user_id and body.active is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your current session account.")
    if current.id == user_id and body.role is not None and body.role != current.role:
        raise HTTPException(status_code=400, detail="You cannot change the role of your current session account.")
    try:
        user = auth_store.update_user(user_id, role=body.role, active=body.active, password=body.password)
        return {"user": user.public()}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/auth/users/{user_id}")
def auth_delete_user(user_id: int, request: Request):
    current = _require_admin(request)
    if current.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your current session account.")
    try:
        auth_store.delete_user(user_id)
        return {"deleted": user_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/auth/roles")
def auth_roles(request: Request):
    _require_admin(request)
    roles, capabilities = auth_store.role_definitions()
    return {"roles": roles, "capabilities": capabilities}


@app.post("/api/auth/roles")
def auth_create_role(body: RoleCreateRequest, request: Request):
    _require_admin(request)
    try:
        role = auth_store.create_role(body.name, body.description, body.clone_from)
        roles, capabilities = auth_store.role_definitions()
        return {"role": role, "roles": roles, "capabilities": capabilities}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/auth/roles/{role}/permissions")
def auth_update_role_permissions(role: str, body: RolePermissionsUpdate, request: Request):
    _require_admin(request)
    try:
        permissions = auth_store.set_role_permissions(role, body.permissions)
        roles, capabilities = auth_store.role_definitions()
        return {"role": role, "permissions": permissions, "roles": roles, "capabilities": capabilities}
    except ValueError as exc:
        if "Unknown role" in str(exc):
            raise HTTPException(status_code=404, detail="Role not found.") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/auth/roles/{role}")
def auth_delete_role(role: str, request: Request):
    _require_admin(request)
    try:
        auth_store.delete_role(role)
        roles, capabilities = auth_store.role_definitions()
        return {"deleted": role, "roles": roles, "capabilities": capabilities}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Role not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

store = ChromaStore()
llm_jobs = LLMJobManager(max_workers=64)
llm_tool_jobs = LLMToolJobManager(store)
rag_jobs = RAGJobManager(store, ollama_max_concurrent=settings.rag_ollama_max_concurrent)
# Chroma writes and embedding-model calls are relatively heavy.  Serializing
# upsert jobs prevents two large work syncs from competing for CPU/RAM/VRAM and
# making the entire UI appear frozen; additional sync requests remain queued.
upsert_jobs = UpsertJobManager(store, max_workers=1)


@app.get("/api/annotations")
def list_annotations(request: Request, store_name: str | None = Query(default=None, alias="store")):
    user = _request_user(request)
    annotations = system_store.list_annotations()
    if user.role == "admin":
        return {"annotations": annotations}

    # Researcher annotations are always scoped to corpus evidence available in
    # the selected database. This prevents annotations or change context from a
    # work outside that database from leaking into the researcher workspace.
    candidate_stores: list[str] = []
    if store_name:
        candidate_stores = [store_name]
    else:
        try:
            candidate_stores = [
                str(item.get("name")) for item in store.list_stores()
                if item.get("name") and item.get("collection_role") != "language" and not str(item.get("name")).startswith("_response_cache")
            ]
        except Exception:
            candidate_stores = []
    accessible_works: dict[str, set[str]] = {}
    for name in candidate_stores:
        try:
            accessible_works[name] = {str(work) for work in store.list_works(name)}
        except Exception:
            accessible_works[name] = set()
    visible: list[dict] = []
    for item in annotations:
        item_store = str(item.get("store") or "")
        if item_store not in accessible_works:
            continue
        item_work = str(item.get("work") or "")
        if item_work and item_work not in accessible_works[item_store]:
            continue
        visible.append(item)
    return {"annotations": visible}


@app.post("/api/annotations")
def create_annotation(body: AnnotationCreateRequest, request: Request):
    user = _request_user(request)
    if user.role != "admin":
        try:
            enforce_researcher_text({"quote": body.quote, "note": body.note, "tags": body.tags})
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not body.store:
            raise HTTPException(status_code=403, detail="Researcher annotations must be attached to an accessible corpus database record.")
        try:
            accessible_record = store.get_record(body.store, body.record_id, include_updates=False)
        except Exception:
            accessible_record = None
        if accessible_record is None:
            raise HTTPException(status_code=403, detail="That record is not available in the selected corpus database.")
        if body.work and str(accessible_record.get("work") or "") != str(body.work):
            raise HTTPException(status_code=403, detail="That work is not available for this record in the selected corpus database.")
    item = body.model_dump()
    item.update({"user_id": user.id, "initiated_by": user.username, "author": user.username})
    return system_store.add_annotation(item)


@app.delete("/api/annotations/{annotation_id}")
def delete_annotation(annotation_id: str, request: Request):
    user = _request_user(request)
    deleted = system_store.delete_annotation(annotation_id, user_id=user.id, admin=user.role == "admin")
    if not deleted:
        raise HTTPException(status_code=404, detail="Annotation not found or not editable by this account.")
    return {"deleted": annotation_id}


@app.get("/api/system/researcher-providers")
def researcher_provider_profiles(request: Request):
    user = _request_user(request)
    profiles = system_store.researcher_profiles()
    if user.role != "admin":
        profiles = [{k: v for k, v in profile.items() if k not in {"base_url", "has_api_key", "api_key"}} for profile in profiles]
    return {"profiles": profiles}


@app.put("/api/system/researcher-providers")
def update_researcher_provider_profiles(body: ResearcherProviderProfilesUpdate, request: Request):
    _require_admin(request)
    return {"profiles": system_store.set_researcher_profiles(body.profiles)}


@app.get("/api/system/storage")
def system_storage_info(request: Request):
    """Describe the durable server-owned metadata store for administrators."""
    _require_admin(request)
    return system_store.storage_info()


@app.post("/api/system/researcher-providers/status")
def researcher_provider_status(body: ResearcherProviderStatusRequest, request: Request):
    _require_admin(request)
    stored = system_store.researcher_profile(body.id) if body.id else None
    api_key = body.api_key or (stored or {}).get("api_key")
    return llm_status(body.type, base_url=body.base_url or (stored or {}).get("base_url"), api_key=api_key)


@app.get("/api/i18n/languages")
def i18n_languages():
    # Read-only language metadata is public because the sign-in screen itself is
    # localized. Mutation/install endpoints remain administrator-only.
    return {"languages": system_store.list_languages()}


@app.get("/api/i18n/languages/{code}")
def i18n_language(code: str):
    # Dictionaries contain UI copy only and must be readable before login.
    value = system_store.get_language(code)
    if value is None:
        raise HTTPException(status_code=404, detail="Language dictionary not found.")
    return value


@app.put("/api/i18n/languages/{code}")
def i18n_update_language(code: str, body: LanguageDictionaryUpdate, request: Request):
    _require_admin(request)
    try:
        return system_store.put_language(code, name=body.name, flag=body.flag, dictionary=body.dictionary)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/i18n/languages/{code}")
def i18n_delete_language(code: str, request: Request):
    _require_admin(request)
    try:
        system_store.delete_language(code)
        return {"deleted": normalize_locale_code(code)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Language dictionary not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/i18n/languages/install")
def i18n_install_language(body: LanguageInstallRequest, request: Request):
    """Create a UI dictionary by translating the canonical en-US dictionary."""
    _require_admin(request)
    try:
        code = normalize_locale_code(body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if system_store.get_language(code) is not None:
        raise HTTPException(status_code=409, detail=f"Locale {code} is already installed. Edit the existing dictionary or remove it before reinstalling.")
    base = system_store.get_language("en-US") or {"dictionary": {}}
    dictionary = dict(base.get("dictionary") or {})
    model = body.model or (settings.openai_compat_model if body.provider == "openai" else settings.ollama_model)
    if not model:
        raise HTTPException(status_code=400, detail="Select a model to translate the language dictionary.")
    try:
        translated, translation_stats = translate_english_dictionary(
            code=code,
            dictionary=dictionary,
            provider=body.provider,
            model=model,
            base_url=body.base_url,
            api_key=body.api_key,
            generation=body.generation,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Language translation failed: {exc}") from exc
    return system_store.put_language(
        code,
        name=body.name or code,
        flag=body.flag or "🌐",
        dictionary=translated,
        translation_report={
            "status": "completed_with_fallbacks" if int(translation_stats.get("fallback_count") or 0) else "complete",
            "source_locale": "en-US",
            "provider": body.provider,
            "model": model,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "failed_count": int(translation_stats.get("failed_count") or 0),
            "fallback_count": int(translation_stats.get("fallback_count") or 0),
            "failed_keys": list(translation_stats.get("failed_keys") or []),
            "failures": list(translation_stats.get("failures") or [])[:250],
            "translated_count": int(translation_stats.get("translated_count") or 0),
            "key_count": int(translation_stats.get("key_count") or len(dictionary)),
        },
    )


@app.get("/api/live")
def live():
    return {"ok": True}


@app.get("/api/health")
def health():
    chroma = store.health()
    ollama = llm_status("ollama")
    return {
        "ok": True,
        "chroma": chroma,
        "chroma_path": settings.chroma_path,
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


@app.get("/api/config")
def config():
    return {
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


@app.get("/api/llm/status")
def llm_status_endpoint(
    provider: str = Query(default="ollama"),
    base_url: str | None = Query(default=None),
    api_key: str | None = Query(default=None),
):
    provider = provider.strip().lower()
    if provider not in {"ollama", "openai"}:
        raise HTTPException(status_code=400, detail="provider must be ollama or openai")
    return llm_status(
        provider,
        base_url=base_url,
        api_key=api_key,
    )


@app.post("/api/llm/status")
def llm_status_post(body: LLMStatusRequest):
    return llm_status(
        body.provider,
        base_url=body.base_url,
        api_key=body.api_key,
    )


@app.post("/api/llm/warmup")
def llm_warmup(body: LLMWarmupRequest):
    try:
        return warmup_model(
            provider=body.provider,
            model=body.model,
            base_url=body.base_url,
            api_key=body.api_key,
        )
    except TouchupFailure as exc:
        detail = {"message": exc.message}
        if exc.diagnostic:
            detail["diagnostic"] = exc.diagnostic
        raise HTTPException(status_code=exc.status_code, detail=detail) from exc


@app.post("/api/jobs/llm")
def create_llm_job(body: LLMJobCreate, request: Request):
    try:
        # ``updates`` is never part of LLM review context. Strip it even for
        # older clients so a large audit trail cannot be retained by the job.
        for item in body.items:
            item.record.pop("updates", None)
        return llm_jobs.create(body, owner=_request_user(request).username)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/rag/grade")
def grade_rag_response(body: RAGGradeRequest):
    try:
        for evidence in body.evidence:
            record = evidence.get("record") if isinstance(evidence, dict) else None
            if isinstance(record, dict):
                record.pop("updates", None)
        return run_rag_grade(body, store)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG grading failed: {exc}") from exc


@app.post("/api/pdf/llm")
def pdf_llm(body: PdfLlmRequest):
    try:
        return run_pdf_llm(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/jobs/rag/concurrency")
def get_rag_concurrency():
    return rag_jobs.concurrency_status()


@app.put("/api/jobs/rag/concurrency")
def set_rag_concurrency(body: RAGConcurrencyUpdate):
    return rag_jobs.set_ollama_limit(body.ollama_max_concurrent)


@app.post("/api/jobs/{job_id}/llm-results/resolve")
def resolve_llm_job_results(job_id: str, body: LLMResultResolutionRequest):
    try:
        manager = _job_manager_for(job_id)
        if manager is not llm_jobs:
            raise HTTPException(status_code=409, detail="Job is not an LLM review job.")
        return llm_jobs.resolve_results(
            job_id,
            action=body.action,
            items=[item.model_dump() for item in body.items],
            dismiss_job=body.dismiss_job,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/jobs/{job_id}/llm-results/reject")
def reject_llm_job_results(job_id: str, body: LLMJobRejectRequest):
    try:
        manager = _job_manager_for(job_id)
        if manager is not llm_jobs:
            raise HTTPException(status_code=409, detail="Job is not an LLM review job.")
        return llm_jobs.reject_and_dismiss(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc


@app.post("/api/jobs/llm-tool")
def create_llm_tool_job(body: LLMToolJobCreate, request: Request):
    try:
        return llm_tool_jobs.create(body, owner=_request_user(request).username)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


_PROFILE_GENERATION_INT_KEYS = {"num_ctx", "num_predict", "top_k", "seed", "mirostat"}
_PROFILE_GENERATION_FLOAT_KEYS = {"temperature", "top_p", "min_p", "repeat_penalty", "mirostat_eta", "mirostat_tau"}


def _profile_generation_options(profile: dict[str, object]) -> dict[str, object]:
    """Normalize values persisted by the provider-profile form for RAG schemas.

    Older profiles store optional controls as strings (including JSON in
    ``extra_options``). Admin runs normally pass browser-normalized values, but
    researcher runs are rebuilt from these server-owned profiles. Normalizing at
    this trust boundary keeps the static-profile security model while avoiding a
    400 when Pydantic receives ``"{}"`` where a mapping is required.
    """
    result: dict[str, object] = {}
    for key in _PROFILE_GENERATION_INT_KEYS:
        value = profile.get(key)
        if value in (None, ""):
            continue
        try:
            result[key] = int(float(str(value).strip()))
        except (TypeError, ValueError):
            continue
    for key in _PROFILE_GENERATION_FLOAT_KEYS:
        value = profile.get(key)
        if value in (None, ""):
            continue
        try:
            result[key] = float(str(value).strip())
        except (TypeError, ValueError):
            continue

    think = profile.get("think")
    if think not in (None, ""):
        if isinstance(think, bool):
            result["think"] = think
        else:
            normalized = str(think).strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                result["think"] = True
            elif normalized in {"false", "0", "no", "off"}:
                result["think"] = False
            elif normalized in {"low", "medium", "high"}:
                result["think"] = normalized

    keep_alive = profile.get("keep_alive")
    if keep_alive not in (None, ""):
        result["keep_alive"] = str(keep_alive).strip()

    extra_options = profile.get("extra_options")
    if isinstance(extra_options, dict):
        result["extra_options"] = extra_options
    elif isinstance(extra_options, str) and extra_options.strip():
        try:
            parsed = json.loads(extra_options)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict):
            result["extra_options"] = parsed

    return result


@app.post("/api/jobs/rag")
def create_rag_job(body: RAGRunRequest, request: Request):
    try:
        user = _request_user(request)
        if user.role != "admin":
            enforce_researcher_text({"prompt": body.prompt, "instructions": body.instructions})
        for selection in body.selected_evidence:
            if isinstance(selection.record, dict):
                selection.record.pop("updates", None)
        if user.role != "admin":
            # Researchers may only use administrator-approved static profiles.
            # Secrets and endpoint overrides are resolved server-side, preventing
            # arbitrary provider access from a crafted browser request.
            if not body.provider_profile_id:
                raise ValueError("Select an administrator-approved researcher LLM profile.")
            profile = system_store.researcher_profile(body.provider_profile_id)
            if profile is None:
                raise ValueError("That researcher LLM profile is not available.")

            generation = _profile_generation_options(profile)
            payload = body.model_dump()
            payload.update({
                "provider": profile.get("type") or "ollama",
                "model": profile.get("model"),
                "base_url": profile.get("base_url"),
                "api_key": profile.get("api_key"),
                "max_concurrent_requests": max(1, min(64, int(profile.get("max_concurrent_requests") or 1))),
            })
            # Always replace browser-supplied generation settings for a non-admin
            # role. Researcher/custom-role runs are defined by the approved static
            # profile, including the empty/default case.
            payload["generation"] = generation or None
            # Ollama profiles on the same normalized endpoint share one server-side
            # execution gate. The stored profiles are normalized to that endpoint's
            # lowest configured limit, so one profile cannot overrun a shared server.

            # The grader may use a different approved static profile.  The client
            # supplies only its profile id; provider URL, credentials and model
            # settings still come from the server-owned profile definition.
            if payload.get("auto_grade"):
                grade_profile_id = body.auto_grade_provider_profile_id or body.provider_profile_id
                grade_profile = system_store.researcher_profile(grade_profile_id)
                if grade_profile is None:
                    raise ValueError("That researcher auto-grade LLM profile is not available.")
                grade_generation = _profile_generation_options(grade_profile)
                payload.update({
                    "auto_grade_provider": grade_profile.get("type") or "ollama",
                    "auto_grade_model": grade_profile.get("model"),
                    "auto_grade_base_url": grade_profile.get("base_url"),
                    "auto_grade_api_key": grade_profile.get("api_key"),
                    "auto_grade_provider_profile_id": grade_profile_id,
                    "auto_grade_generation": grade_generation or None,
                })
            body = RAGRunRequest(**payload)
        return rag_jobs.create(body, owner=user.username)
    except HTTPException:
        raise
    except ValueError as exc:
        # UI payloads are validated client-side as well. A stale profile or
        # server-owned policy conflict is semantically unprocessable, not a
        # malformed HTTP request; Research therefore never degrades these into
        # an opaque 400 Bad Request.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Research could not start: {exc}") from exc


@app.post("/api/jobs/upsert")
def create_upsert_job(body: UpsertJobCreate, request: Request):
    try:
        user = _request_user(request)
        if not body.include_updates:
            for item in body.items:
                item.record.pop("updates", None)
        for item in body.items:
            for entry in item.audit_entries:
                if not entry.get("initiated_by"):
                    entry["initiated_by"] = user.username
            if item.replace_updates is not None:
                for entry in item.replace_updates:
                    if not entry.get("initiated_by"):
                        entry["initiated_by"] = user.username
        return upsert_jobs.create(body, owner=user.username)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/jobs")
def list_jobs(request: Request):
    user = _request_user(request)
    if user.role != "admin":
        jobs = [job for job in rag_jobs.list() if job.get("owner") == user.username]
    else:
        jobs = llm_jobs.list() + llm_tool_jobs.list() + rag_jobs.list() + upsert_jobs.list() + pdf_corpus_builds.list_operations()
    jobs.sort(key=lambda job: job.get("created_at", ""), reverse=True)
    return {"jobs": jobs}


def _job_manager_for(job_id: str):
    for manager in (llm_jobs, llm_tool_jobs, rag_jobs, upsert_jobs):
        try:
            manager.get(job_id)
            return manager
        except KeyError:
            continue
    try:
        pdf_corpus_repository.get_build(job_id)
        return pdf_corpus_builds
    except KeyError:
        pass
    raise KeyError(job_id)


def _researcher_job_access(user: AuthUser, manager, job_id: str) -> dict:
    job = manager.operation(job_id) if manager is pdf_corpus_builds else manager.get(job_id)
    if user.role != "admin":
        if manager is not rag_jobs or job.get("owner") != user.username:
            raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, request: Request):
    try:
        user = _request_user(request)
        manager = _job_manager_for(job_id)
        job = _researcher_job_access(user, manager, job_id)
        if user.role != "admin":
            return sanitize_rag_job(job, max_chars=settings.researcher_text_max_chars)
        return job
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str, request: Request):
    try:
        user = _request_user(request)
        manager = _job_manager_for(job_id)
        _researcher_job_access(user, manager, job_id)
        result = manager.cancel(job_id)
        if manager is pdf_corpus_builds:
            return manager.operation(job_id)
        if user.role != "admin":
            return sanitize_rag_job(result, max_chars=settings.researcher_text_max_chars)
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, request: Request):
    try:
        user = _request_user(request)
        manager = _job_manager_for(job_id)
        _researcher_job_access(user, manager, job_id)
        manager.delete(job_id)
        return {"deleted": job_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.delete("/api/jobs")
def clear_finished_jobs():
    return {
        "deleted": (
            llm_jobs.clear_finished()
            + llm_tool_jobs.clear_finished()
            + rag_jobs.clear_finished()
            + upsert_jobs.clear_finished()
            + pdf_corpus_builds.clear_finished()
        )
    }


@app.get("/api/chroma/path")
def get_chroma_path():
    return store.health()


@app.put("/api/chroma/path")
def set_chroma_path(body: ChromaPathUpdate):
    try:
        return store.set_path(body.path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _background_jobs_active() -> bool:
    return bool(
        llm_jobs.active_count()
        or llm_tool_jobs.active_count()
        or rag_jobs.active_count()
        or upsert_jobs.active_count()
        or pdf_corpus_builds.active_count()
    )


def _safe_extract_zip(archive: zipfile.ZipFile, target: Path) -> None:
    root = target.resolve()
    for info in archive.infolist():
        name = info.filename.replace("\\", "/")
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe backup member: {info.filename}")
        mode = (info.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            raise ValueError(
                f"Symbolic links are not allowed in backups: {info.filename}"
            )
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(f"Unsafe backup member: {info.filename}")
    archive.extractall(root)


def _restore_asset_paths() -> tuple[Path, Path]:
    root = (
        Path(settings.chroma_data_root)
        .expanduser()
        .resolve()
        / ".derridai_restore"
    )
    return root / "current.pdf", root / "current-pdf.json"


def _backup_temp_dir(prefix: str) -> Path:
    root = (
        Path(settings.chroma_data_root)
        .expanduser()
        .resolve()
        / ".derridai_tmp"
    )
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(root)))


@app.post("/api/admin/backup")
async def create_full_backup(
    workspace: UploadFile = File(...),
    pdf_metadata: str = Form(default="{}"),
    current_pdf: UploadFile | None = File(default=None),
):
    if _background_jobs_active():
        raise HTTPException(
            status_code=409,
            detail=(
                "Background operations are still active. Wait for them to finish "
                "or cancel them before creating a consistent full backup."
            ),
        )

    temp_root = _backup_temp_dir("backup-")
    try:
        raw_workspace = await workspace.read()
        if not raw_workspace:
            raise ValueError("Workspace payload is empty.")

        workspace_payload = json.loads(raw_workspace.decode("utf-8"))
        if not isinstance(workspace_payload, dict):
            raise ValueError("Workspace payload must be a JSON object.")
        files = workspace_payload.get("files", [])
        prefs = workspace_payload.get("prefs", {})
        if not isinstance(files, list):
            raise ValueError("Workspace files payload is invalid.")
        if not isinstance(prefs, dict):
            raise ValueError("Workspace preferences payload is invalid.")

        try:
            pdf_meta = json.loads(pdf_metadata or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("PDF metadata is invalid JSON.") from exc
        if not isinstance(pdf_meta, dict):
            pdf_meta = {}

        snapshot_root = temp_root / "snapshot"
        snapshot_root.mkdir(parents=True, exist_ok=True)

        (snapshot_root / "workspace.json").write_text(
            json.dumps(
                workspace_payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        auth_roles = auth_store.snapshot_roles()
        (snapshot_root / "roles.json").write_text(
            json.dumps(auth_roles, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        auth_users = auth_store.snapshot_users()
        (snapshot_root / "users.json").write_text(
            json.dumps(auth_users, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

        system_snapshot = system_store.snapshot()
        (snapshot_root / "system.json").write_text(
            json.dumps(system_snapshot, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

        collections = store.write_logical_backup(snapshot_root)

        pdf_corpus_source = pdf_corpus_repository.root
        pdf_corpus_backup = snapshot_root / "pdf-corpus"
        if pdf_corpus_source.exists():
            shutil.copytree(pdf_corpus_source, pdf_corpus_backup, dirs_exist_ok=True)
        pdf_corpus_inventory = pdf_corpus_repository.list_builds(offset=0, limit=100000)

        operation_snapshot = {
            "llm": llm_jobs.snapshot(),
            "llm_tool": llm_tool_jobs.snapshot(),
            "rag": rag_jobs.snapshot(),
            "upsert": upsert_jobs.snapshot(),
            "note": (
                "Only retained non-active operation records are archived. "
                "Active jobs are blocked during backup and are never restarted "
                "automatically during restore."
            ),
        }
        (snapshot_root / "operations.json").write_text(
            json.dumps(
                operation_snapshot,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        pdf_entry = None
        if current_pdf is not None and current_pdf.filename:
            asset_dir = snapshot_root / "assets"
            asset_dir.mkdir(parents=True, exist_ok=True)
            target_pdf = asset_dir / "current.pdf"
            with target_pdf.open("wb") as handle:
                while True:
                    chunk = await current_pdf.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)

            pdf_entry = {
                "file": "assets/current.pdf",
                "filename": current_pdf.filename,
                "content_type": (
                    current_pdf.content_type or "application/pdf"
                ),
                "metadata": pdf_meta,
                "size": target_pdf.stat().st_size,
            }

        app_config = (
            prefs.get("appConfig")
            if isinstance(prefs.get("appConfig"), dict)
            else {}
        )
        provider_profiles = (
            app_config.get("provider_profiles", [])
            if isinstance(app_config, dict)
            else []
        )
        contains_credentials = any(
            bool(profile.get("api_key"))
            for profile in provider_profiles
            if isinstance(profile, dict)
        ) or any(
            bool(profile.get("api_key"))
            for profile in (system_snapshot.get("researcher_provider_profiles") or [])
            if isinstance(profile, dict)
        )

        manifest = {
            "backup_type": "derridai-full-backup",
            "format_version": 1,
            "app_version": "0.52.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "workspace": {
                "file_count": len(files),
                "record_count": sum(
                    len(item.get("records") or [])
                    for item in files
                    if isinstance(item, dict)
                ),
            },
            "chroma": {
                "source_path": store.path,
                "host_path_hint": store.health().get("host_path_hint"),
                "collections": collections,
                "collection_count": len(collections),
                "record_count": sum(
                    int(item.get("count") or 0)
                    for item in collections
                ),
                "embeddings_preserved": True,
            },
            "operations": {
                "llm": len(operation_snapshot["llm"]),
                "rag": len(operation_snapshot["rag"]),
                "upsert": len(operation_snapshot["upsert"]),
            },
            "auth": {
                "user_count": len(auth_users),
                "role_count": len(auth_roles),
                "roles": [str(role.get("id") or "") for role in auth_roles],
                "sessions_included": False,
            },
            "system": {
                "researcher_provider_profile_count": len(system_snapshot.get("researcher_provider_profiles") or []),
                "language_count": len(system_snapshot.get("languages") or {}),
            },
            "current_pdf": pdf_entry,
            "pdf_corpus": {
                "build_count": int(pdf_corpus_inventory.get("total") or 0),
                "included": pdf_corpus_backup.exists(),
            },
            "contains_credentials": contains_credentials,
            "contains_auth_credentials": bool(auth_users),
            "notes": [
                (
                    "Stored Chroma vectors are backed up and restored "
                    "without re-embedding."
                ),
                (
                    "Provider API keys are included when present in "
                    "browser or server-managed researcher profiles."
                ),
                (
                    "User accounts and password hashes are included; active "
                    "session tokens are not exported."
                ),
                (
                    "Installed Ollama model files, Docker images, and "
                    "application source images are not embedded in this archive."
                ),
            ],
        }
        (snapshot_root / "manifest.json").write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        archive_path = temp_root / (
            "derridai-full-backup-"
            + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            + ".zip"
        )
        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
        ) as archive:
            for path in snapshot_root.rglob("*"):
                if path.is_file():
                    archive.write(
                        path,
                        arcname=path.relative_to(snapshot_root).as_posix(),
                    )

        return FileResponse(
            path=archive_path,
            media_type="application/zip",
            filename=archive_path.name,
            background=BackgroundTask(
                shutil.rmtree,
                temp_root,
                ignore_errors=True,
            ),
        )
    except HTTPException:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(temp_root, ignore_errors=True)
        logger.exception("Full backup creation failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/admin/restore")
async def restore_full_backup(backup: UploadFile = File(...)):
    if _background_jobs_active():
        raise HTTPException(
            status_code=409,
            detail=(
                "Background operations are still active. Cancel them and wait "
                "for them to stop before restoring a backup."
            ),
        )

    temp_root = _backup_temp_dir("restore-")
    rollback_root = _backup_temp_dir("rollback-")
    upload_path = temp_root / "backup.zip"

    try:
        with upload_path.open("wb") as handle:
            while True:
                chunk = await backup.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)

        if not zipfile.is_zipfile(upload_path):
            raise ValueError(
                "The selected file is not a valid DerridAI ZIP backup."
            )

        extract_root = temp_root / "snapshot"
        extract_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(upload_path, "r") as archive:
            _safe_extract_zip(archive, extract_root)

        manifest_path = extract_root / "manifest.json"
        workspace_path = extract_root / "workspace.json"
        if not manifest_path.exists() or not workspace_path.exists():
            raise ValueError(
                "Backup is missing manifest.json or workspace.json."
            )

        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        if manifest.get("backup_type") != "derridai-full-backup":
            raise ValueError(
                "This archive is not a DerridAI full backup."
            )
        if int(manifest.get("format_version") or 0) != 1:
            raise ValueError(
                "Unsupported DerridAI backup format: "
                f"{manifest.get('format_version')}"
            )

        workspace_payload = json.loads(
            workspace_path.read_text(encoding="utf-8")
        )
        if not isinstance(workspace_payload, dict):
            raise ValueError("Backup workspace is invalid.")
        if not isinstance(workspace_payload.get("files", []), list):
            raise ValueError("Backup workspace files are invalid.")
        if not isinstance(workspace_payload.get("prefs", {}), dict):
            raise ValueError(
                "Backup workspace preferences are invalid."
            )

        roles_payload = None
        roles_path = extract_root / "roles.json"
        if roles_path.exists():
            roles_payload = json.loads(roles_path.read_text(encoding="utf-8"))
            if not isinstance(roles_payload, list):
                raise ValueError("Backup role payload is invalid.")

        users_payload = None
        users_path = extract_root / "users.json"
        if users_path.exists():
            users_payload = json.loads(users_path.read_text(encoding="utf-8"))
            if not isinstance(users_payload, list) or not users_payload:
                raise ValueError("Backup user-account payload is invalid.")

        system_payload = None
        system_path = extract_root / "system.json"
        if system_path.exists():
            system_payload = json.loads(system_path.read_text(encoding="utf-8"))
            if not isinstance(system_payload, dict):
                raise ValueError("Backup system-configuration payload is invalid.")

        collection_inventory = (
            (manifest.get("chroma") or {}).get("collections") or []
        )
        if not isinstance(collection_inventory, list):
            raise ValueError("Backup Chroma inventory is invalid.")

        # Validate all collection payload files before touching the live store.
        root_resolved = extract_root.resolve()
        for entry in collection_inventory:
            if not isinstance(entry, dict):
                raise ValueError("Backup collection inventory is invalid.")
            relative_file = str(entry.get("file") or "")
            payload_path = (extract_root / relative_file).resolve()
            if (
                not relative_file
                or not payload_path.is_relative_to(root_resolved)
                or not payload_path.exists()
            ):
                raise ValueError(
                    "Backup collection payload is missing or unsafe: "
                    f"{relative_file}"
                )

        # Logical rollback protects the current Chroma database if restoration
        # fails after validation.
        rollback_inventory = store.write_logical_backup(
            rollback_root
        )
        rollback_roles = auth_store.snapshot_roles()
        rollback_users = auth_store.snapshot_users()
        rollback_system = system_store.snapshot()
        restored_role_count = 0
        restored_user_count = 0
        try:
            restore_result = store.restore_logical_backup(
                extract_root,
                collection_inventory,
                replace=True,
            )
            if roles_payload is not None:
                restored_role_count = auth_store.restore_roles(roles_payload)
            if users_payload is not None:
                restored_user_count = auth_store.restore_users(users_payload)
            if system_payload is not None:
                system_store.restore_snapshot(system_payload)
        except Exception:
            try:
                store.restore_logical_backup(
                    rollback_root,
                    rollback_inventory,
                    replace=True,
                )
            except Exception:
                logger.exception(
                    "Chroma rollback after failed restore also failed"
                )
            try:
                auth_store.restore_roles(rollback_roles)
                if rollback_users:
                    auth_store.restore_users(rollback_users)
            except Exception:
                logger.exception(
                    "User-account/role rollback after failed restore also failed"
                )
            try:
                system_store.restore_snapshot(rollback_system)
            except Exception:
                logger.exception(
                    "System-configuration rollback after failed restore also failed"
                )
            raise

        operations_path = extract_root / "operations.json"
        restored_operations = {
            "llm": 0,
            "llm_tool": 0,
            "rag": 0,
            "upsert": 0,
        }
        llm_jobs.clear_finished()
        llm_tool_jobs.clear_finished()
        rag_jobs.clear_finished()
        upsert_jobs.clear_finished()
        if operations_path.exists():
            operations = json.loads(
                operations_path.read_text(encoding="utf-8")
            )
            if isinstance(operations, dict):
                restored_operations["llm"] = (
                    llm_jobs.restore_snapshot(
                        operations.get("llm") or []
                    )
                )
                restored_operations["llm_tool"] = (
                    llm_tool_jobs.restore_snapshot(
                        operations.get("llm_tool") or []
                    )
                )
                restored_operations["rag"] = (
                    rag_jobs.restore_snapshot(
                        operations.get("rag") or []
                    )
                )
                restored_operations["upsert"] = (
                    upsert_jobs.restore_snapshot(
                        operations.get("upsert") or []
                    )
                )

        pdf_info = manifest.get("current_pdf")
        pdf_available = False
        restored_pdf_meta: dict = {}
        restore_pdf_path, restore_pdf_meta_path = (
            _restore_asset_paths()
        )
        restore_pdf_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        restore_pdf_path.unlink(missing_ok=True)
        restore_pdf_meta_path.unlink(missing_ok=True)

        if isinstance(pdf_info, dict) and pdf_info.get("file"):
            source_pdf = (
                extract_root / str(pdf_info["file"])
            ).resolve()
            if (
                source_pdf.is_relative_to(root_resolved)
                and source_pdf.exists()
            ):
                shutil.copy2(source_pdf, restore_pdf_path)
                restored_pdf_meta = {
                    "filename": (
                        pdf_info.get("filename")
                        or "restored.pdf"
                    ),
                    "content_type": (
                        pdf_info.get("content_type")
                        or "application/pdf"
                    ),
                    "metadata": pdf_info.get("metadata") or {},
                }
                restore_pdf_meta_path.write_text(
                    json.dumps(
                        restored_pdf_meta,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                pdf_available = True

        corpus_backup_dir = extract_root / "pdf-corpus"
        restored_pdf_corpus = False
        if corpus_backup_dir.exists() and corpus_backup_dir.is_dir():
            live_corpus_dir = pdf_corpus_repository.root
            corpus_rollback_dir = rollback_root / "pdf-corpus"
            if live_corpus_dir.exists():
                shutil.copytree(live_corpus_dir, corpus_rollback_dir, dirs_exist_ok=True)
            try:
                shutil.rmtree(live_corpus_dir, ignore_errors=True)
                shutil.copytree(corpus_backup_dir, live_corpus_dir)
                restored_pdf_corpus = True
            except Exception:
                shutil.rmtree(live_corpus_dir, ignore_errors=True)
                if corpus_rollback_dir.exists():
                    shutil.copytree(corpus_rollback_dir, live_corpus_dir)
                raise

        prefs = workspace_payload.get("prefs") or {}
        app_config = (
            prefs.get("appConfig")
            if isinstance(prefs, dict)
            else {}
        )
        if isinstance(app_config, dict):
            limit = app_config.get("ollama_rag_concurrency")
            if limit is not None:
                try:
                    rag_jobs.set_ollama_limit(int(limit))
                except (TypeError, ValueError):
                    pass

        return {
            "ok": True,
            "manifest": manifest,
            "workspace": workspace_payload,
            "chroma": restore_result,
            "operations": restored_operations,
            "roles_restored": restored_role_count,
            "users_restored": restored_user_count,
            "pdf_available": pdf_available,
            "pdf": restored_pdf_meta,
            "pdf_corpus_restored": restored_pdf_corpus,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Full backup restore failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
        shutil.rmtree(rollback_root, ignore_errors=True)


@app.get("/api/admin/restore/current-pdf")
def get_restored_current_pdf():
    pdf_path, meta_path = _restore_asset_paths()
    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No restored PDF asset is available.",
        )

    filename = "restored.pdf"
    media_type = "application/pdf"
    if meta_path.exists():
        try:
            meta = json.loads(
                meta_path.read_text(encoding="utf-8")
            )
            filename = str(meta.get("filename") or filename)
            media_type = str(
                meta.get("content_type") or media_type
            )
        except Exception:
            pass

    return FileResponse(
        pdf_path,
        media_type=media_type,
        filename=filename,
    )


@app.post("/api/admin/nuke")
def nuke():
    if llm_jobs.active_count() or llm_tool_jobs.active_count() or rag_jobs.active_count() or upsert_jobs.active_count() or pdf_corpus_builds.active_count():
        raise HTTPException(
            status_code=409,
            detail=(
                "Background operations are still running. Cancel them from the "
                "Dashboard and wait for them to stop before nuking the workspace."
            ),
        )
    try:
        cleared_jobs = (
            llm_jobs.clear_finished()
            + llm_tool_jobs.clear_finished()
            + rag_jobs.clear_finished()
            + upsert_jobs.clear_finished()
            + pdf_corpus_builds.clear_finished()
        )
        chroma_result = store.nuke()
        data_root = Path(settings.chroma_data_root).expanduser().resolve()
        for transient in (
            data_root / ".derridai_restore",
            data_root / ".derridai_tmp",
            data_root / ".home" / "pdf-corpus",
        ):
            shutil.rmtree(transient, ignore_errors=True)
        # Recreate the corpus repository directories after a destructive reset so
        # subsequent PDF uploads do not depend on process restart.
        for part in ("assets", "builds", "publications"):
            (pdf_corpus_repository.root / part).mkdir(parents=True, exist_ok=True)
        return {
            "ok": True,
            "cleared_jobs": cleared_jobs,
            "chroma": chroma_result,
        }
    except Exception as exc:
        logger.exception("Nuke operation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/pdf/extract")
async def pdf_extract(
    file: UploadFile = File(...),
    page: int | None = Query(default=None, ge=1),
):
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


@app.post("/api/pdf/assets")
async def create_pdf_asset(
    file: UploadFile = File(...),
    ocr_mode: str = Form(default="auto"),
    ocr_languages: str = Form(default="eng+fra+deu"),
):
    if ocr_mode not in {"auto", "never", "always"}:
        raise HTTPException(status_code=422, detail="ocr_mode must be auto, never, or always")
    try:
        max_bytes = settings.pdf_max_upload_mb * 1024 * 1024
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
                    detail=f"PDF exceeds the {settings.pdf_max_upload_mb} MB upload limit",
                )
            chunks.append(chunk)
        data = b"".join(chunks)
        return pdf_corpus_repository.save_asset(
            data,
            filename=file.filename or "source.pdf",
            ocr_mode=ocr_mode,
            ocr_languages=ocr_languages or "eng+fra+deu",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("PDF asset ingestion failed")
        raise HTTPException(status_code=500, detail=f"PDF asset ingestion failed: {exc}") from exc


@app.get("/api/pdf/assets")
def list_pdf_assets():
    return {"items": pdf_corpus_repository.list_assets()}


@app.get("/api/pdf/assets/{asset_id}")
def get_pdf_asset(asset_id: str):
    try:
        return pdf_corpus_repository.get_asset(asset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc




@app.patch("/api/pdf/assets/{asset_id}/page-labels")
def patch_pdf_asset_page_labels(asset_id: str, body: PdfPageLabelsPatch):
    try:
        return pdf_corpus_repository.update_page_labels(asset_id, body.labels)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/pdf/assets/{asset_id}/content")
def get_pdf_asset_content(asset_id: str):
    try:
        asset = pdf_corpus_repository.get_asset(asset_id)
        path = pdf_corpus_repository.asset_pdf_path(asset_id)
        return FileResponse(path, media_type="application/pdf", filename=asset.get("filename") or "source.pdf")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc


@app.get("/api/pdf/assets/{asset_id}/blocks")
def get_pdf_asset_blocks(
    asset_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    ids: str = Query(default="", max_length=20000),
):
    try:
        blocks = pdf_corpus_repository.load_blocks(asset_id)
        if ids.strip():
            requested = {value.strip() for value in ids.split(",") if value.strip()}
            selected = [block for block in blocks if str(block.get("block_id") or "") in requested]
            return {"items": selected, "total": len(selected), "offset": 0, "limit": len(selected)}
        return {"items": blocks[offset:offset + limit], "total": len(blocks), "offset": offset, "limit": limit}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc


@app.get("/api/pdf/corpus-profiles")
def list_pdf_corpus_profiles():
    return {"items": list(CORPUS_PROFILES.values())}


def _resolve_pdf_corpus_provider(payload: dict[str, Any]) -> dict[str, Any]:
    """Resolve server-owned researcher profiles without rejecting admin profiles.

    Administrator requests may supply an explicit provider configuration, while
    researcher-approved profiles are persisted server-side. When a profile id is known to
    the server we resolve its secrets there; otherwise an explicit provider
    configuration supplied by the authenticated admin request is used.  Secrets
    are stripped by the build manager before the public build manifest is saved.
    """
    resolved = dict(payload)
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

    profile_id = str(resolved.get("provider_profile_id") or "").strip()
    if profile_id:
        profile = system_store.researcher_profile(profile_id)
        if profile is not None:
            profile_generation = _profile_generation_options(profile) or {}
            profile_generation.update({key: value for key, value in generation_override.items() if value is not None})
            resolved.update({
                "provider": profile.get("type") or "ollama",
                "model": profile.get("model"),
                "base_url": profile.get("base_url"),
                "api_key": profile.get("api_key"),
                "generation": profile_generation or None,
                "provider_profile_id": profile_id,
            })
        elif not (resolved.get("provider") and (resolved.get("model") or resolved.get("base_url"))):
            raise ValueError("The selected LLM provider profile is not available.")

    review_profile_id = str(resolved.get("review_provider_profile_id") or "").strip()
    if review_profile_id:
        review_profile = system_store.researcher_profile(review_profile_id)
        if review_profile is not None:
            resolved["_review_provider"] = {
                "provider": review_profile.get("type") or "ollama",
                "model": review_profile.get("model"),
                "base_url": review_profile.get("base_url"),
                "api_key": review_profile.get("api_key"),
                "generation": _profile_generation_options(review_profile) or None,
                "provider_profile_id": review_profile_id,
            }
        elif isinstance(direct_review, dict) and direct_review.get("provider"):
            resolved["_review_provider"] = {**direct_review, "provider_profile_id": review_profile_id}
        else:
            raise ValueError("The selected escalation provider profile is not available.")
    elif isinstance(direct_review, dict) and direct_review.get("provider"):
        resolved["_review_provider"] = direct_review

    return {key: value for key, value in resolved.items() if value is not None}


@app.post("/api/pdf/corpus-builds")
def create_pdf_corpus_build(body: PdfCorpusBuildCreate):
    try:
        return pdf_corpus_builds.create(_resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/pdf/corpus-builds")
def list_pdf_corpus_builds(offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200), asset_id: str | None = None):
    return pdf_corpus_repository.list_builds(offset=offset, limit=limit, asset_id=asset_id)


@app.get("/api/pdf/corpus-builds/{build_id}")
def get_pdf_corpus_build(build_id: str):
    try:
        return pdf_corpus_repository.get_build(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@app.patch("/api/pdf/corpus-builds/{build_id}/provider-profile")
def patch_pdf_corpus_provider_profile(build_id: str, body: PdfCorpusProviderSwitch):
    try:
        resolved = _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        return pdf_corpus_builds.switch_provider_profile(build_id, resolved)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@app.patch("/api/pdf/corpus-builds/{build_id}/manifest")
def patch_pdf_corpus_manifest(build_id: str, body: PdfCorpusManifestPatch):
    try:
        return pdf_corpus_builds.patch_manifest(build_id, body.changes, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/pdf/corpus-builds/{build_id}/records")
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
):
    try:
        return pdf_corpus_repository.page_records(build_id, offset=offset, limit=limit, needs_review=needs_review, disposition=disposition, metadata_incomplete=metadata_incomplete, source_problem=source_problem, review_queue=review_queue, query=query)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@app.post("/api/pdf/corpus-builds/{build_id}/confirm-manifest")
def confirm_pdf_corpus_manifest(build_id: str, body: PdfCorpusRecordRerun):
    try:
        return pdf_corpus_builds.confirm_manifest(
            build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/cancel")
def cancel_pdf_corpus_build(build_id: str):
    try:
        return pdf_corpus_builds.cancel(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@app.post("/api/pdf/corpus-builds/{build_id}/settle-metadata")
def settle_pdf_corpus_metadata(build_id: str):
    try:
        return pdf_corpus_builds.settle_metadata_unresolved(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/resume")
def resume_pdf_corpus_build(build_id: str, body: PdfCorpusRecordRerun):
    try:
        return pdf_corpus_builds.resume(build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata")
def patch_pdf_corpus_record_metadata(build_id: str, record_id: str, body: PdfCorpusRecordPatch):
    try:
        return pdf_corpus_builds.patch_metadata(build_id, record_id, body.changes, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/text")
def patch_pdf_corpus_record_text(build_id: str, record_id: str, body: PdfCorpusRecordTextPatch):
    try:
        return pdf_corpus_builds.patch_record_text(build_id, record_id, body.text, body.expected_revision, body.resolve_source_issues)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata-decision")
def decide_pdf_corpus_record_metadata(build_id: str, record_id: str, body: PdfCorpusMetadataDecision):
    try:
        return pdf_corpus_builds.metadata_decision(build_id, record_id, body.field, body.value, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/evidence")
def patch_pdf_corpus_record_evidence(build_id: str, record_id: str, body: PdfCorpusEvidencePatch):
    try:
        return pdf_corpus_builds.patch_evidence(
            build_id, record_id, body.field, body.block_ids, body.confidence, body.reason, body.expected_revision
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/accept")
def accept_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusRecordAccept):
    try:
        return pdf_corpus_builds.accept_record(build_id, record_id, body.accepted, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/disposition")
def set_pdf_corpus_record_disposition(build_id: str, record_id: str, body: PdfCorpusRecordDisposition):
    try:
        return pdf_corpus_builds.set_disposition(build_id, record_id, body.disposition, body.reason, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/review-decision")
def decide_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusReviewDecision):
    try:
        return pdf_corpus_builds.review_decision(build_id, record_id, body.disposition, body.reason, body.expected_revision, body.review_queue)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/disposition")
def bulk_pdf_corpus_record_disposition(build_id: str, body: PdfCorpusBulkDisposition):
    try:
        return pdf_corpus_builds.bulk_disposition(build_id, body.disposition, body.reason, body.needs_review, body.query, body.filter_disposition, body.review_queue, body.record_ids)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/pdf/corpus-builds/{build_id}/records/metadata")
def bulk_patch_pdf_corpus_record_metadata(build_id: str, body: PdfCorpusBulkMetadataPatch):
    try:
        return pdf_corpus_builds.bulk_patch_metadata(
            build_id, body.changes, record_ids=body.record_ids, apply_to_all=body.apply_to_all,
            review_queue=body.review_queue, query=body.query,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/review/undo")
def undo_pdf_corpus_review_edit(build_id: str):
    try:
        return pdf_corpus_builds.undo_last_review_edit(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No review edit is available to undo") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/merge")
def merge_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusRecordMerge):
    try:
        return pdf_corpus_builds.merge(build_id, record_id, body.direction, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/split")
def split_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusRecordSplit):
    try:
        return pdf_corpus_builds.split(build_id, record_id, body.after_block_id, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/metadata/retry")
def retry_pdf_corpus_metadata(build_id: str, body: PdfCorpusRecordRerun):
    try:
        return pdf_corpus_builds.retry_incomplete_metadata(
            build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/rerun-metadata")
def rerun_pdf_corpus_record_metadata(build_id: str, record_id: str, body: PdfCorpusRecordRerun):
    try:
        return pdf_corpus_builds.rerun_metadata(build_id, record_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/publish")
def publish_pdf_corpus_build(build_id: str, body: PdfCorpusPublishRequest):
    try:
        return pdf_corpus_builds.publish(build_id, require_acceptance=body.require_acceptance)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/pdf/publications/{publication_id}/download")
def download_pdf_corpus_publication(publication_id: str):
    path = pdf_corpus_repository.publication_path(publication_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Publication not found")
    return FileResponse(path, media_type="application/x-ndjson", filename=f"{publication_id}.jsonl")


@app.get("/api/stores")
def list_stores():
    try:
        return {"stores": store.list_stores()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/stores")
def create_store(body: StoreCreate):
    try:
        return store.create_store(
            body.name,
            body.metadata,
            description=body.description,
            embedding_provider=body.embedding_provider,
            embedding_model=body.embedding_model,
            embedding_dimension=body.embedding_dimension,
            distance_metric=body.distance_metric,
            retrieval_mode=body.retrieval_mode,
            text_field=body.text_field,
            filter_fields=body.filter_fields,
            language_codes=body.language_codes,
            collection_role=body.collection_role,
            protected=body.protected,
        )
    except StoreAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/stores/preflight/embedding")
def preflight_embedding(body: EmbeddingPreflightRequest):
    try:
        return store.preflight_embedding(
            provider=body.embedding_provider,
            model=body.embedding_model,
            embedding_dimension=body.embedding_dimension,
            distance_metric=body.distance_metric,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/stores/{store_name}")
def get_store(store_name: str):
    try:
        return store.get_store(store_name)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/stores/{store_name}/embedding")
def update_store_embedding(
    store_name: str,
    body: StoreEmbeddingUpdate,
):
    try:
        return store.set_embedding(
            store_name,
            provider=body.embedding_provider,
            model=body.embedding_model,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/stores/{store_name}/languages")
def update_store_languages(
    store_name: str,
    body: StoreLanguageUpdate,
):
    try:
        return store.set_language_tags(
            store_name,
            language_codes=body.language_codes,
            collection_role=body.collection_role,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/stores/{store_name}/protection")
def update_store_protection(store_name: str, body: StoreProtectionUpdate):
    try:
        return store.set_protection(store_name, body.protected)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/stores/{store_name}/derive-languages")
def derive_language_stores(
    store_name: str,
    body: DeriveLanguageStoresRequest,
):
    try:
        return store.derive_language_stores(
            store_name,
            en_name=body.en_name,
            fr_name=body.fr_name,
            overwrite=body.overwrite,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/stores/{store_name}")
def delete_store(store_name: str, force: bool = Query(default=False)):
    try:
        store.delete_store(store_name, force=force)
        return {"deleted": store_name}
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/stores/{store_name}/works/{work:path}")
def delete_store_work(store_name: str, work: str):
    try:
        return store.delete_work_with_language_sync(store_name, work)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/response-cache/records")
def get_response_cache_records(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    query: str | None = Query(default=None),
):
    try:
        return store.get_response_cache_records(
            limit=limit,
            offset=offset,
            query=query,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/stores/{store_name}/records")
def get_records(
    store_name: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    work: str | None = Query(default=None),
    sort_field: str | None = Query(default=None),
    sort_dir: str = Query(default="asc"),
    filters: str | None = Query(default=None),
    include_updates: bool = Query(default=False),
):
    try:
        user = _request_user(request)
        parsed_filters: dict[str, str] = {}
        if filters:
            candidate = json.loads(filters)
            if not isinstance(candidate, dict):
                raise ValueError("filters must encode a JSON object")
            parsed_filters = {
                str(key): str(value)
                for key, value in candidate.items()
            }
        if user.role != "admin":
            enforce_researcher_text({"work": work, "filters": parsed_filters})
        allow_updates = include_updates and user.role == "admin"
        result = store.get_records(
            store_name,
            limit=limit,
            offset=offset,
            work=work,
            sort_field=sort_field,
            sort_dir=sort_dir,
            filters=parsed_filters,
            include_updates=allow_updates,
        )
        if user.role != "admin":
            return sanitize_records_payload(result, max_chars=settings.researcher_text_max_chars)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/stores/{store_name}/works")
def list_store_works(store_name: str):
    try:
        return {
            "works": store.list_works(store_name),
            "stats": store.work_stats(store_name),
        }
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/stores/{store_name}/records/status")
def record_status(store_name: str, body: RecordStatusRequest):
    try:
        return {"existing_ids": store.existing_ids(store_name, body.ids)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/stores/{store_name}/drift")
def store_drift(store_name: str, body: StoreDriftRequest):
    try:
        return store.drift_report(
            store_name,
            [item.model_dump(mode="json") for item in body.items],
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/stores/{store_name}/export")
def export_store(
    store_name: str,
    work: str | None = Query(default=None),
):
    try:
        return {
            "store": store.get_store(store_name),
            "records": store.export_records(store_name, work=work),
            "work": work,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/stores/{store_name}/records/{chroma_id:path}")
def get_record(
    store_name: str,
    chroma_id: str,
    request: Request,
    include_updates: bool = Query(default=False),
):
    try:
        user = _request_user(request)
        # Researcher responses never expose raw audit history. Admin clients can
        # request it explicitly for a history-specific operation.
        allow_updates = include_updates and user.role == "admin"
        record = store.get_record(store_name, chroma_id, include_updates=allow_updates)
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found.")
        if user.role != "admin":
            return summarize_record(record, max_chars=settings.researcher_text_max_chars)
        return record
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/stores/{store_name}/records")
def create_record(store_name: str, body: RecordUpsert, request: Request):
    try:
        user = _require_admin(request)
        record = dict(body.record)
        if not body.include_updates:
            record.pop("updates", None)
        record = _stamp_record_activity(record, user.username)
        return store.upsert_with_language_sync(
            store_name,
            [record],
            document_field=body.document_field,
            id_field=body.id_field,
            embedding_field=body.embedding_field,
            id_prefix=body.id_prefix,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/stores/{store_name}/records/{chroma_id:path}")
def patch_record(
    store_name: str,
    chroma_id: str,
    body: StoredRecordPatch,
    request: Request,
):
    try:
        user = _require_admin(request)
        entries: list[dict[str, Any]] = []
        for update in body.audit_entries:
            if not isinstance(update, dict):
                continue
            item = dict(update)
            item.setdefault("initiated_by", user.username)
            entries.append(item)
        result = store.patch_existing(
            store_name,
            chroma_id,
            dict(body.changes),
            audit_entries=entries,
            document_field=body.document_field,
            embedding_field=body.embedding_field,
        )
        mirror = store.get_record(store_name, chroma_id, include_updates=False) or {}
        mirror["_chroma_id"] = chroma_id
        language_sync = store.sync_language_children(
            store_name,
            [mirror],
            id_field="_chroma_id",
        )
        return {**result, "language_sync": language_sync}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/stores/{store_name}/records/{chroma_id:path}")
def delete_record(store_name: str, chroma_id: str):
    try:
        return store.delete_record_with_language_sync(store_name, chroma_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/stores/{store_name}/records/bulk")
def bulk_upsert(store_name: str, body: BulkUpsert, request: Request):
    try:
        user = _require_admin(request)
        records: list[dict[str, Any]] = []
        audit_entries_by_id: dict[str, list[dict[str, Any]]] = {}
        replace_updates_by_id: dict[str, list[dict[str, Any]]] = {}

        for item in body.items:
            record = dict(item.record)
            record.pop("updates", None)
            if item.chroma_id:
                record[body.id_field] = item.chroma_id
            raw_id = record.get(body.id_field)
            if raw_id is None or str(raw_id).strip() == "":
                raise ValueError(f"Bulk upsert item is missing '{body.id_field}'.")
            storage_id = str(raw_id)
            chroma_id = f"{body.id_prefix}::{storage_id}" if body.id_prefix else storage_id
            if item.audit_entries:
                audit_entries_by_id[chroma_id] = [
                    {**dict(entry), "initiated_by": entry.get("initiated_by") or user.username}
                    for entry in item.audit_entries
                ]
            if item.replace_updates is not None:
                replace_updates_by_id[chroma_id] = [
                    {**dict(entry), "initiated_by": entry.get("initiated_by") or user.username}
                    for entry in item.replace_updates
                ]
            records.append(_stamp_record_activity(record, user.username))
        return store.upsert_with_language_sync(
            store_name,
            records,
            document_field=body.document_field,
            id_field=body.id_field,
            embedding_field=body.embedding_field,
            id_prefix=body.id_prefix,
            audit_entries_by_id=audit_entries_by_id,
            replace_updates_by_id=replace_updates_by_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/stores/{store_name}/search")
def search(store_name: str, body: SearchRequest, request: Request):
    try:
        user = _request_user(request)
        if user.role != "admin":
            enforce_researcher_text({"query": body.query, "where": body.where})
        if body.mode == "filter":
            rows = store.filter_search(store_name, body.n_results, body.where)
        elif body.mode == "keyword":
            rows = store.keyword_search(store_name, body.query, body.n_results, body.where)
        elif body.mode == "lexical":
            rows = store.lexical_search(store_name, body.query, body.n_results, body.where)
        elif body.mode == "hybrid":
            rows = store.hybrid_search(store_name, body.query, body.n_results, body.where)
        elif body.mode == "mmr":
            rows = store.mmr_search(store_name, body.query, body.n_results, body.where, fetch_k=body.fetch_k, lambda_mult=body.lambda_mult)
        else:
            rows = store.search(store_name, body.query, body.n_results, body.where)
        result = {"results": rows}
        if user.role != "admin":
            return sanitize_records_payload(result, max_chars=settings.researcher_text_max_chars)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/llm/touchup", response_model=TouchupResponse)
def llm_touchup(body: TouchupRequest):
    try:
        return propose_touchup(
            body.record,
            body.fields,
            body.instructions,
            body.model,
            body.ollama,
            provider=body.provider,
            base_url=body.base_url,
            api_key=body.api_key,
        )
    except TouchupFailure as exc:
        detail: dict[str, str] = {"message": exc.message}
        if exc.diagnostic:
            detail["diagnostic"] = exc.diagnostic
        raise HTTPException(
            status_code=exc.status_code,
            detail=detail,
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected LLM touch-up failure")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unexpected LLM touch-up failure.",
                "diagnostic": str(exc),
            },
        ) from exc
