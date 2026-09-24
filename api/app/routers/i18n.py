# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from ..config import settings
from ..content_filter import admin_content_policy_view, public_content_policy_mirror
from ..content_policy_generation import generate_policy_for_installed_language
from ..http_auth import request_user, require_admin
from ..i18n_translation import translate_english_dictionary
from ..models import (
    LanguageContentPolicyUpdate,
    LanguageDictionaryUpdate,
    LanguageInstallRequest,
)
from ..system_store import normalize_locale_code, system_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["internationalization"])


@router.get("/api/i18n/languages")
def i18n_languages() -> dict[str, Any]:
    # Read-only language metadata is public because the sign-in screen itself is
    # localized. Mutation/install endpoints remain administrator-only.
    return {"languages": system_store.list_languages()}


@router.get("/api/i18n/languages/{code}")
def i18n_language(code: str) -> dict[str, Any]:
    # Dictionaries contain UI copy only and must be readable before login.
    value = system_store.get_language(code)
    if value is None:
        raise HTTPException(status_code=404, detail="Language dictionary not found.")
    return value


@router.put("/api/i18n/languages/{code}")
def i18n_update_language(code: str, body: LanguageDictionaryUpdate, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        return system_store.put_language(code, name=body.name, flag=body.flag, dictionary=body.dictionary)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/api/i18n/languages/{code}")
def i18n_delete_language(code: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        system_store.delete_language(code)
        return {"deleted": normalize_locale_code(code)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Language dictionary not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/i18n/languages/install")
def i18n_install_language(body: LanguageInstallRequest, request: Request) -> dict[str, Any]:
    """Create a UI dictionary by translating the canonical en-US dictionary."""
    require_admin(request)
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
    saved = system_store.put_language(
        code,
        name=body.name or code,
        flag=body.flag or "🌐",
        dictionary=translated,
        translation_report={
            "status": "completed_with_fallbacks" if int(translation_stats.get("fallback_count") or 0) else "complete",
            "source_locale": "en-US",
            "provider": body.provider,
            "model": model,
            "completed_at": datetime.now(UTC).isoformat(),
            "failed_count": int(translation_stats.get("failed_count") or 0),
            "fallback_count": int(translation_stats.get("fallback_count") or 0),
            "failed_keys": list(translation_stats.get("failed_keys") or []),
            "failures": list(translation_stats.get("failures") or [])[:250],
            "translated_count": int(translation_stats.get("translated_count") or 0),
            "key_count": int(translation_stats.get("key_count") or len(dictionary)),
        },
    )
    try:
        system_store.put_content_policy(
            code,
            generate_policy_for_installed_language(
                code=code,
                provider=body.provider,
                model=model,
                base_url=body.base_url,
                api_key=body.api_key,
                generation=body.generation,
            ),
        )
    except Exception:
        logger.warning(
            "Content policy generation failed during language install for %s",
            code,
            exc_info=True,
        )
    return system_store.get_language(code) or saved


@router.get("/api/i18n/content-policy")
def i18n_active_content_policy(request: Request) -> dict[str, Any]:
    """Hashed union of ready locale policies for the researcher client mirror."""
    request_user(request)
    return public_content_policy_mirror(system_store.list_ready_content_policies())


@router.get("/api/i18n/languages/{code}/content-policy")
def i18n_language_content_policy(code: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        normalized = normalize_locale_code(code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if system_store.get_language(normalized) is None:
        raise HTTPException(status_code=404, detail="Language dictionary not found.")
    return admin_content_policy_view(system_store.get_content_policy(normalized), code=normalized)


@router.put("/api/i18n/languages/{code}/content-policy")
def i18n_update_content_policy(code: str, body: LanguageContentPolicyUpdate, request: Request) -> dict[str, Any]:
    require_admin(request)
    try:
        normalized = normalize_locale_code(code)
        return system_store.put_content_policy(
            normalized,
            {
                "blocked_terms": body.blocked_terms,
                "contextual_terms": body.contextual_terms,
                "source": "admin-edited",
            },
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Language dictionary not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

