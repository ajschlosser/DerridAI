# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import copy
import os
import re
import threading
from datetime import UTC, datetime
from typing import Any

from .config import settings as app_settings
from .locales.en_us import EN_US as DEFAULT_EN_US
from .locales.fr_ca import FR_CA as DEFAULT_FR_CA
from .persistence import SQLiteJobRepository, system_repository

_LOCALE_RE = re.compile(
    r"^(?P<language>[A-Za-z]{2,3})(?:-(?P<script>[A-Za-z]{4}))?(?:-(?P<region>[A-Za-z]{2}|[0-9]{3}))?(?:-(?P<variants>[A-Za-z0-9][A-Za-z0-9-]{0,24}))?$"
)

def normalize_locale_code(code: str) -> str:
    """Normalize the common BCP 47 forms used for interface locales.

    Supports language-only tags plus optional script, region, and variants, for
    example ``de``, ``pt-BR`` and ``zh-Hant-TW``. The parser remains deliberately
    conservative rather than accepting arbitrary private-use tags.
    """
    value = str(code or "").strip().replace("_", "-")
    match = _LOCALE_RE.fullmatch(value)
    if not match:
        raise ValueError("Language code must be a valid BCP 47 locale such as de-DE, pt-BR, or zh-Hant-TW.")
    parts = [match.group("language").lower()]
    script = match.group("script")
    region = match.group("region")
    variants = match.group("variants")
    if script:
        parts.append(script.title())
    if region:
        parts.append(region.upper() if region.isalpha() else region)
    if variants:
        parts.extend(part.lower() for part in variants.split("-") if part)
    return "-".join(parts)

# Built-in languages are seed data: their name and flag are stored with the language like any
# other, and nothing branches on a locale code to decide how a flag looks.
BUILT_IN_LANGUAGES: dict[str, dict[str, Any]] = {
    "en-US": {"name": "English", "flag": "🇺🇸", "dictionary": DEFAULT_EN_US},
    "fr-CA": {"name": "Français", "flag": "🇨🇦", "dictionary": DEFAULT_FR_CA},
}


class SystemStore:
    def __init__(self) -> None:
        self.repository = system_repository
        self.path = self.repository.path
        self._lock = threading.RLock()
        self._ensure()

    def _default(self) -> dict[str, Any]:
        return {
            "researcher_provider_profiles": [],
            "settings": {},
            "annotations": [],
            "languages": {code: dict(language) for code, language in BUILT_IN_LANGUAGES.items()},
            "vector_sync_suppressions": {},
        }

    def _ensure(self) -> None:
        with self._lock:
            if self.repository.is_empty():
                self._write(self._default())

    def _read(self) -> dict[str, Any]:
        try:
            return self.repository.load()
        except Exception:
            # Preserve the previous startup behavior: a damaged/temporarily
            # unavailable store does not make localization defaults disappear.
            return self._default()

    def _write(self, data: dict[str, Any]) -> None:
        self.repository.replace(data)

    def storage_info(self) -> dict[str, Any]:
        return self.repository.describe()

    def vector_sync_suppressions(self, store_name: str) -> dict[str, str]:
        with self._lock:
            data = self._read()
            values = data.get("vector_sync_suppressions", {}).get(store_name, {})
            return dict(values) if isinstance(values, dict) else {}

    def set_vector_sync_suppression(self, store_name: str, record_id: str, fingerprint: str) -> dict[str, str]:
        with self._lock:
            data = self._read()
            all_values = data.setdefault("vector_sync_suppressions", {})
            store_values = all_values.setdefault(store_name, {})
            store_values[str(record_id)] = str(fingerprint)
            self._write(data)
            return dict(store_values)

    @staticmethod
    def _public_profile(profile: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "id", "name", "type", "base_url", "model", "model_mode", "model_kind",
            "max_concurrent_requests", "num_ctx", "num_predict", "metadata_num_predict",
            "think", "temperature", "top_k", "top_p", "min_p", "repeat_penalty", "seed",
            "mirostat", "mirostat_eta", "mirostat_tau", "keep_alive", "extra_options",
        }
        public = {key: copy.deepcopy(value) for key, value in profile.items() if key in allowed}
        public["has_api_key"] = bool(profile.get("api_key"))
        return public

    def list_annotations(self, *, user_id: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = copy.deepcopy(self.repository.list_annotations())
        for row in rows:
            row.setdefault("scope", "text" if row.get("quote") else "record")
            row.setdefault("record_id", None)
            row.setdefault("work", None)
            row.setdefault("linked_record_ids", [])
            row.setdefault("parent_id", None)
            row.setdefault("thread_id", row.get("id"))
            row.setdefault("deleted_at", None)
        if user_id is not None:
            rows = [row for row in rows if int(row.get("user_id") or 0) == int(user_id)]
        return rows

    def add_annotation(self, value: dict[str, Any]) -> dict[str, Any]:
        import uuid
        from datetime import datetime
        item = copy.deepcopy(value if isinstance(value, dict) else {})
        item["id"] = str(item.get("id") or uuid.uuid4())
        item["created_at"] = str(item.get("created_at") or datetime.now(UTC).isoformat())
        item["scope"] = str(item.get("scope") or ("text" if item.get("quote") else "record"))
        item["record_id"] = str(item["record_id"]) if item.get("record_id") else None
        item["work"] = str(item["work"]).strip() if item.get("work") else None
        item["linked_record_ids"] = [
            str(record_id).strip()
            for record_id in item.get("linked_record_ids") or []
            if str(record_id).strip()
        ]
        item["parent_id"] = str(item["parent_id"]).strip() if item.get("parent_id") else None
        item["thread_id"] = str(item.get("thread_id") or item["id"])
        item["deleted_at"] = str(item["deleted_at"]) if item.get("deleted_at") else None
        item["tags"] = [str(tag).strip() for tag in item.get("tags") or [] if str(tag).strip()]
        with self._lock:
            self.repository.put_annotation(item)
        return item

    def delete_annotation(self, annotation_id: str, *, user_id: int | None = None, admin: bool = False) -> bool:
        annotation_id = str(annotation_id or "").strip()
        with self._lock:
            rows = self.repository.list_annotations()
            target = next((row for row in rows if str(row.get("id") or "") == annotation_id), None)
            if not target or (not admin and int(target.get("user_id") or 0) != int(user_id or -1)):
                return False
            target["deleted_at"] = datetime.now(UTC).isoformat()
            target["note"] = ""
            target["quote"] = ""
            target["tags"] = []
            self.repository.put_annotation(target)
            return True

    def get_adjudication_cache(self, cache_key: str) -> dict[str, Any] | None:
        with self._lock:
            return self.repository.get_adjudication_cache(cache_key)

    def put_adjudication_cache(
        self,
        cache_key: str,
        record_id: str,
        field: str,
        cardinality: str,
        text_hash: str,
        payload: dict[str, Any],
    ) -> None:
        with self._lock:
            self.repository.put_adjudication_cache(
                cache_key, record_id, field, cardinality, text_hash, payload
            )
            self.repository.prune_adjudication_cache()

    def clear_adjudication_cache(
        self,
        *,
        record_id: str | None = None,
        field: str | None = None,
    ) -> int:
        with self._lock:
            return self.repository.clear_adjudication_cache(record_id=record_id, field=field)

    def put_memory_binding(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.repository.put_memory_binding(payload)

    def list_memory_bindings(self, **filters: Any) -> list[dict[str, Any]]:
        with self._lock:
            return self.repository.list_memory_bindings(**filters)

    def mark_semantic_memory_dirty(self, projection: str, **kwargs: Any) -> str:
        with self._lock:
            return self.repository.mark_semantic_memory_dirty(projection, **kwargs)

    def list_semantic_memory_dirty(
        self,
        projection: str | None = None,
        *,
        scope_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._lock:
            return self.repository.list_semantic_memory_dirty(
                projection,
                scope_id=scope_id,
                limit=limit,
            )

    def complete_semantic_memory_dirty(self, item_ids: list[str]) -> int:
        with self._lock:
            return self.repository.complete_semantic_memory_dirty(item_ids)

    def put_generated_claim(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.repository.put_generated_claim(payload)

    def list_generated_claims(self, **filters: Any) -> list[dict[str, Any]]:
        with self._lock:
            return self.repository.list_generated_claims(**filters)

    def put_response_memory(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.repository.put_response_memory(payload)

    def get_response_memory(self, response_id: str, *, owner: str | None = None) -> dict[str, Any] | None:
        with self._lock:
            return self.repository.get_response_memory(response_id, owner=owner)

    def record_response_memory_grade(self, response_id: str, grade: dict[str, Any]) -> bool:
        with self._lock:
            return self.repository.record_response_memory_grade(response_id, grade)

    def list_response_memory(self, **filters: Any) -> list[dict[str, Any]]:
        with self._lock:
            return self.repository.list_response_memory(**filters)

    def put_claim_support_binding(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.repository.put_claim_support_binding(payload)

    def list_claim_support_bindings(self, claim_id: str, *, owner: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            return self.repository.list_claim_support_bindings(claim_id, owner=owner)

    def list_claim_support_bindings_for_record(
        self,
        record_id: str,
        *,
        owner: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        with self._lock:
            return self.repository.list_claim_support_bindings_for_record(
                record_id,
                owner=owner,
                limit=limit,
            )

    def get_generated_claim(
        self,
        claim_id: str,
        *,
        owner: str | None = None,
    ) -> dict[str, Any] | None:
        with self._lock:
            return self.repository.get_generated_claim(claim_id, owner=owner)

    def get_generated_claims(
        self,
        claim_ids: list[str],
        *,
        owner: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        with self._lock:
            return self.repository.get_generated_claims(claim_ids, owner=owner)

    def list_claim_support_bindings_for_claims(
        self,
        claim_ids: list[str],
        *,
        owner: str | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            return self.repository.list_claim_support_bindings_for_claims(claim_ids, owner=owner)

    def set_record_build_provenance(
        self, record_id: str, build_id: str, *, work: str | None = None
    ) -> None:
        with self._lock:
            self.repository.set_record_build_provenance(record_id, build_id, work=work)

    def get_record_build_id(self, record_id: str) -> str | None:
        with self._lock:
            return self.repository.get_record_build_id(record_id)

    def list_build_ids_for_work(self, work: str) -> list[str]:
        with self._lock:
            return self.repository.list_build_ids_for_work(work)

    def list_records_for_work(self, work: str, limit: int = 200) -> list[dict[str, str]]:
        with self._lock:
            return self.repository.list_records_for_work(work, limit)

    def semantic_map_state(self, build_id: str) -> dict[str, Any]:
        with self._lock:
            return self.repository.semantic_map_state(build_id)

    def mark_semantic_map_dirty(self, build_id: str, *, reason: str = "changed") -> int:
        with self._lock:
            return self.repository.mark_semantic_map_dirty(build_id, reason=reason)

    def mark_semantic_map_clean(self, build_id: str, generation: int) -> bool:
        with self._lock:
            return self.repository.mark_semantic_map_clean(build_id, generation)

    def put_semantic_map_projection(
        self,
        scope_type: str,
        scope_id: str,
        build_id: str,
        generation: int,
        payload: dict[str, Any],
        *,
        work: str | None = None,
        audience: str = "",
    ) -> None:
        with self._lock:
            self.repository.put_semantic_map_projection(
                scope_type,
                scope_id,
                build_id,
                generation,
                payload,
                work=work,
                audience=audience,
            )

    def get_semantic_map_projection(
        self,
        scope_type: str,
        scope_id: str,
        build_id: str,
        *,
        audience: str = "",
    ) -> dict[str, Any] | None:
        with self._lock:
            return self.repository.get_semantic_map_projection(
                scope_type,
                scope_id,
                build_id,
                audience=audience,
            )

    def list_semantic_map_projections_for_work(
        self,
        work: str,
        *,
        scope_type: str = "work",
        audience: str = "",
    ) -> list[dict[str, Any]]:
        with self._lock:
            return self.repository.list_semantic_map_projections_for_work(
                work,
                scope_type=scope_type,
                audience=audience,
            )

    def embedding_defaults(self) -> dict[str, Any]:
        with self._lock:
            stored = self.repository.get_setting("embedding_defaults")
        value = stored if isinstance(stored, dict) else {}
        provider = str(value.get("embedding_provider") or app_settings.embedding_provider).strip()
        if not provider.startswith("profile:"):
            provider = provider.lower()
        model = str(value.get("embedding_model") or "").strip() or None

        # Before embedding defaults were server-owned, the browser Vector Store
        # wizard interpreted the legacy "ollama" default as the first configured
        # Ollama provider profile. Preserve that behavior for an unpersisted
        # default so background/system projections use the same endpoint/model.
        if not isinstance(stored, dict) and provider == "ollama":
            profile = next(
                (
                    item
                    for item in self.researcher_profiles(include_secrets=True)
                    if str(item.get("type") or "").strip().lower() == "ollama"
                    and str(item.get("id") or "").strip()
                ),
                None,
            )
            if profile:
                provider = f"profile:{str(profile.get('id')).strip()}"
                model = str(profile.get("model") or "").strip() or None

        if provider == "ollama" and not model:
            model = app_settings.ollama_embed_model
        if provider.startswith("profile:") and not model:
            profile_id = provider.split(":", 1)[1].strip()
            profile = self.researcher_profile(profile_id)
            model = str((profile or {}).get("model") or "").strip() or None
        return {
            "embedding_provider": provider,
            "embedding_model": model,
            "persisted": isinstance(stored, dict),
        }

    _AUDIO_SETTING = "audio_transcription"

    def audio_transcription_settings(self, *, include_key: bool = False) -> dict[str, Any]:
        """Settings for audio transcription, kept apart from chat/embedding provider profiles.

        The API key is stored server-side and never returned unless ``include_key``.
        Environment variables remain a fallback so existing deployments keep working.
        """
        with self._lock:
            stored = self.repository.get_setting(self._AUDIO_SETTING)
        value = stored if isinstance(stored, dict) else {}
        key = str(value.get("api_key") or "").strip()
        env_key = (os.getenv("OPENAI_API_KEY", "") or app_settings.openai_compat_api_key or "").strip()
        result: dict[str, Any] = {
            "base_url": str(value.get("base_url") or os.getenv("OPENAI_WHISPER_BASE_URL") or "https://api.openai.com/v1").rstrip("/"),
            "model": str(value.get("model") or os.getenv("OPENAI_WHISPER_MODEL") or "whisper-1"),
            "has_key": bool(key or env_key),
            "key_source": "settings" if key else ("environment" if env_key else "none"),
        }
        if include_key:
            result["api_key"] = key or env_key
        return result

    def set_audio_transcription_settings(
        self, *, base_url: str, model: str, api_key: str | None = None, clear_key: bool = False,
    ) -> dict[str, Any]:
        base = str(base_url or "").strip().rstrip("/")
        if not re.match(r"^https?://\S+$", base):
            raise ValueError("The transcription base URL must be an http(s) address.")
        chosen = str(model or "").strip()
        if not chosen:
            raise ValueError("Choose a transcription model.")
        with self._lock:
            current = self.repository.get_setting(self._AUDIO_SETTING)
            current = current if isinstance(current, dict) else {}
            key = "" if clear_key else (str(api_key).strip() if api_key else str(current.get("api_key") or ""))
            self.repository.put_setting(self._AUDIO_SETTING, {"base_url": base, "model": chosen, "api_key": key})
        return self.audio_transcription_settings()

    def set_embedding_defaults(self, provider: str, model: str | None = None) -> dict[str, Any]:
        normalized_provider = str(provider or "").strip()
        if not normalized_provider.startswith("profile:"):
            normalized_provider = normalized_provider.lower()
        if normalized_provider not in {"ollama", "chroma", "precomputed"} and not normalized_provider.startswith("profile:"):
            raise ValueError(
                "Embedding provider must be ollama, chroma, precomputed, or profile:<provider-id>."
            )

        normalized_model = str(model or "").strip() or None
        if normalized_provider == "ollama" and not normalized_model:
            normalized_model = app_settings.ollama_embed_model
        if normalized_provider.startswith("profile:"):
            profile_id = normalized_provider.split(":", 1)[1].strip()
            if not profile_id:
                raise ValueError("Embedding provider profile ID cannot be empty.")
            profile = self.researcher_profile(profile_id)
            if not profile:
                raise ValueError(f"Embedding provider profile {profile_id!r} was not found.")
            if not normalized_model:
                normalized_model = str(profile.get("model") or "").strip() or None
            if not normalized_model:
                raise ValueError("Select an embedding model for the provider profile.")
        if normalized_provider in {"chroma", "precomputed"}:
            normalized_model = None

        payload = {
            "embedding_provider": normalized_provider,
            "embedding_model": normalized_model,
        }
        with self._lock:
            self.repository.put_setting("embedding_defaults", payload)
        return {**copy.deepcopy(payload), "persisted": True}

    def researcher_profiles(self, *, include_secrets: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            profiles = copy.deepcopy(self.repository.list_provider_profiles())
        if include_secrets:
            return profiles
        return [self._public_profile(profile) for profile in profiles]

    def set_researcher_profiles(self, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Provider secrets are intentionally write-only in the admin UI. Preserve an
        # existing API key when an edited profile is submitted without a replacement.
        existing = {
            str(profile.get("id")): profile
            for profile in self.researcher_profiles(include_secrets=True)
            if profile.get("id")
        }
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in profiles:
            if not isinstance(raw, dict):
                continue
            profile = copy.deepcopy(raw)
            profile_id = str(profile.get("id") or "").strip()
            if not profile_id or profile_id in seen:
                continue
            if profile.get("type") not in {"ollama", "openai"}:
                continue
            profile["id"] = profile_id
            if not str(profile.get("api_key") or "").strip() and profile_id in existing:
                prior_secret = existing[profile_id].get("api_key")
                if prior_secret:
                    profile["api_key"] = prior_secret
            profile["max_concurrent_requests"] = max(1, min(64, int(profile.get("max_concurrent_requests") or (1 if profile["type"] == "ollama" else 32))))
            normalized.append(profile)
            seen.add(profile_id)
        endpoint_limits: dict[str, int] = {}
        for profile in normalized:
            if profile.get("type") != "ollama":
                continue
            endpoint = str(profile.get("base_url") or "").rstrip("/").lower()
            limit = int(profile.get("max_concurrent_requests") or 1)
            endpoint_limits[endpoint] = min(endpoint_limits.get(endpoint, limit), limit)
        for profile in normalized:
            if profile.get("type") == "ollama":
                endpoint = str(profile.get("base_url") or "").rstrip("/").lower()
                profile["max_concurrent_requests"] = endpoint_limits.get(endpoint, profile["max_concurrent_requests"])
        with self._lock:
            self.repository.replace_provider_profiles(normalized)
        return [self._public_profile(profile) for profile in normalized]

    def researcher_profile(self, profile_id: str) -> dict[str, Any] | None:
        for profile in self.researcher_profiles(include_secrets=True):
            if str(profile.get("id")) == str(profile_id):
                return profile
        return None

    @staticmethod
    def _policy_ready(value: dict[str, Any] | None) -> bool:
        from .content_filter import policy_is_ready
        return policy_is_ready((value or {}).get("content_policy") if isinstance(value, dict) else None)

    def list_languages(self) -> list[dict[str, Any]]:
        with self._lock:
            languages = copy.deepcopy(self.repository.list_languages())
        return [
            {
                "code": code,
                "name": str(value.get("name") or code),
                "flag": str(value.get("flag") or "🌐"),
                "content_policy_ready": self._policy_ready(value if isinstance(value, dict) else None),
            }
            for code, value in sorted(languages.items())
        ]

    def get_language(self, code: str) -> dict[str, Any] | None:
        try:
            code = normalize_locale_code(code)
        except ValueError:
            return None
        with self._lock:
            value = copy.deepcopy(self.repository.get_language(code))
        if code in BUILT_IN_LANGUAGES:
            built_in = BUILT_IN_LANGUAGES[code]
            merged = dict(built_in["dictionary"])
            if isinstance(value, dict) and isinstance(value.get("dictionary"), dict):
                merged.update({str(key): str(item) for key, item in value["dictionary"].items()})
            return {
                "code": code,
                "name": str((value or {}).get("name") or built_in["name"]),
                "flag": str((value or {}).get("flag") or built_in["flag"]),
                "dictionary": merged,
                "content_policy_ready": self._policy_ready(value if isinstance(value, dict) else None),
                **({"translation_report": copy.deepcopy(value.get("translation_report"))} if isinstance(value, dict) and isinstance(value.get("translation_report"), dict) else {}),
            }
        if not value:
            return None
        public = {key: item for key, item in value.items() if key != "content_policy"}
        return {"code": code, "content_policy_ready": self._policy_ready(value), **public}

    def put_language(
        self,
        code: str,
        *,
        name: str,
        flag: str,
        dictionary: dict[str, str],
        translation_report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        code = normalize_locale_code(code)
        clean = {str(key): str(value) for key, value in dictionary.items() if str(key).strip()}
        with self._lock:
            languages = self.repository.list_languages()
            previous = languages.get(code) if isinstance(languages.get(code), dict) else {}
            report = copy.deepcopy(translation_report if translation_report is not None else previous.get("translation_report"))
            # Keep the durable report useful after an administrator manually fixes
            # fallback strings. A tracked key is resolved once its target no longer
            # equals the canonical English value.
            if isinstance(report, dict) and code != "en-US":
                canonical = (languages.get("en-US") or {}).get("dictionary") or DEFAULT_EN_US
                tracked = [str(key) for key in (report.get("failed_keys") or []) if str(key)]
                unresolved = [key for key in tracked if clean.get(key, "").strip() == str(canonical.get(key, "")).strip()]
                report["failed_keys"] = unresolved
                report["failed_count"] = len(unresolved)
                report["fallback_count"] = len(unresolved)
                if isinstance(report.get("failures"), list):
                    report["failures"] = [item for item in report["failures"] if isinstance(item, dict) and str(item.get("key") or "") in unresolved]
                if not unresolved and report.get("status") == "completed_with_fallbacks":
                    report["status"] = "complete"
            language_value: dict[str, Any] = {"name": name.strip() or code, "flag": flag.strip() or "🌐", "dictionary": clean}
            if isinstance(report, dict):
                language_value["translation_report"] = report
            self.repository.put_language(code, language_value)
            # en-US is the canonical key set. When an administrator introduces a
            # new English key, make it immediately editable in every installed
            # locale as an English fallback instead of waiting for a restart.
            if code == "en-US":
                for locale_code, language in languages.items():
                    if locale_code == "en-US" or not isinstance(language, dict):
                        continue
                    target = language.setdefault("dictionary", {})
                    changed = False
                    for key, value in clean.items():
                        if key not in target:
                            target[key] = value
                            changed = True
                    if changed:
                        self.repository.put_language(locale_code, language)
        return self.get_language(code) or {}

    def delete_language(self, code: str) -> None:
        code = normalize_locale_code(code)
        if code in BUILT_IN_LANGUAGES:
            raise ValueError("Built-in languages cannot be removed.")
        with self._lock:
            if not self.repository.delete_language(code):
                raise KeyError(code)

    def get_content_policy(self, code: str) -> dict[str, Any] | None:
        try:
            code = normalize_locale_code(code)
        except ValueError:
            return None
        with self._lock:
            value = self.repository.get_language(code)
        if not isinstance(value, dict):
            return None
        policy = value.get("content_policy")
        return copy.deepcopy(policy) if isinstance(policy, dict) else None

    def put_content_policy(self, code: str, policy: dict[str, Any]) -> dict[str, Any]:
        from .content_filter import normalize_content_policy
        code = normalize_locale_code(code)
        clean = normalize_content_policy(policy, require_ready=True)
        with self._lock:
            if self.repository.get_language(code) is None and code not in BUILT_IN_LANGUAGES:
                raise KeyError(code)
            if not self.repository.put_content_policy(code, clean):
                # Built-ins may exist only as merged Python defaults until first write.
                language = self.get_language(code)
                if language is None:
                    raise KeyError(code)
                self.repository.put_language(code, {
                    "name": language.get("name") or code,
                    "flag": language.get("flag") or "🌐",
                    "dictionary": language.get("dictionary") or {},
                    "translation_report": language.get("translation_report"),
                })
                if not self.repository.put_content_policy(code, clean):
                    raise KeyError(code)
        return {"code": code, **clean}

    def list_ready_content_policies(self) -> list[dict[str, Any]]:
        with self._lock:
            languages = copy.deepcopy(self.repository.list_languages())
        ready: list[dict[str, Any]] = []
        for code, value in languages.items():
            if not isinstance(value, dict):
                continue
            policy = value.get("content_policy")
            if self._policy_ready(value):
                item = copy.deepcopy(policy)
                item["code"] = code
                ready.append(item)
        return ready

    def content_policy_summaries(self) -> list[dict[str, Any]]:
        return [
            {"code": item["code"], "content_policy_ready": bool(item.get("content_policy_ready"))}
            for item in self.list_languages()
        ]

    def snapshot(self) -> dict[str, Any]:
        """Return the complete server-owned configuration for full backups.

        Unlike the public profile API this intentionally includes provider
        secrets, because a full DerridAI backup is already documented as a
        credential-bearing administrative artifact. Pipeline definitions and
        traces live in focused tables in the same database, so they are folded
        into the logical snapshot here rather than hidden from backup/restore.
        """
        from .pipelines.store import PipelineStore

        with self._lock:
            payload = copy.deepcopy(self._read())
        payload["pipelines"] = PipelineStore(self.path).snapshot()
        return payload

    def reset_to_fresh_install(self) -> dict[str, Any]:
        """Restore shipped locales and drop operational configuration/history."""
        from .pipelines.store import PipelineStore

        with self._lock:
            self._write(self._default())
        cleared_jobs = SQLiteJobRepository(self.path).clear_all()
        cleared_pipelines = PipelineStore(self.path).clear_all()
        return {
            "languages": ["en-US", "fr-CA"],
            "profiles": 0,
            "annotations": 0,
            "cleared_jobs": cleared_jobs,
            "cleared_pipelines": cleared_pipelines,
        }

    def restore_snapshot(self, payload: dict[str, Any]) -> None:
        """Restore server-owned configuration plus pipeline operational state.

        Pipeline payloads are validated before general system configuration is
        touched. If an unexpected persistence failure occurs after validation,
        the prior logical system/pipeline snapshots are restored before the
        exception is re-raised.
        """
        from .pipelines.store import PipelineStore

        if not isinstance(payload, dict):
            raise ValueError("System configuration backup is invalid.")
        profiles = payload.get("researcher_provider_profiles", [])
        languages = payload.get("languages", {})
        if not isinstance(profiles, list) or not isinstance(languages, dict):
            raise ValueError("System configuration backup is invalid.")

        restored = copy.deepcopy(payload)
        pipeline_snapshot = restored.pop("pipelines", None)
        pipeline_store = PipelineStore(self.path)

        # Reject malformed pipeline backups before replacing any system state.
        if isinstance(pipeline_snapshot, dict):
            pipeline_store.validate_snapshot(pipeline_snapshot)

        with self._lock:
            previous_system = copy.deepcopy(self._read())
        previous_pipelines = pipeline_store.snapshot()

        try:
            with self._lock:
                self._write(restored)
                self._ensure()

            # A full restore replaces, rather than merges, operational state.
            # Older backups predate pipeline tables and therefore restore an
            # empty custom layer while code-owned built-ins remain available.
            if isinstance(pipeline_snapshot, dict):
                pipeline_store.restore_snapshot(pipeline_snapshot)
            else:
                pipeline_store.restore_snapshot(
                    {
                        "definitions": [],
                        "assignments": [],
                        "runs": [],
                        "stages": [],
                    }
                )
        except Exception:
            # Best-effort cross-domain rollback. PipelineStore restoration is
            # itself atomic; restoring the previous general system payload keeps
            # a failed full backup from leaving half of the system replaced.
            with self._lock:
                self._write(previous_system)
                self._ensure()
            pipeline_store.restore_snapshot(previous_pipelines)
            raise


system_store = SystemStore()
