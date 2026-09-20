# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import copy
import re
import threading
from datetime import UTC
from typing import Any

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
            "annotations": [],
            "languages": {code: dict(language) for code, language in BUILT_IN_LANGUAGES.items()},
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
        if user_id is not None:
            rows = [row for row in rows if int(row.get("user_id") or 0) == int(user_id)]
        return rows

    def add_annotation(self, value: dict[str, Any]) -> dict[str, Any]:
        import uuid
        from datetime import datetime
        item = copy.deepcopy(value if isinstance(value, dict) else {})
        item["id"] = str(item.get("id") or uuid.uuid4())
        item["created_at"] = str(item.get("created_at") or datetime.now(UTC).isoformat())
        item["tags"] = [str(tag).strip() for tag in item.get("tags") or [] if str(tag).strip()]
        with self._lock:
            self.repository.put_annotation(item)
        return item

    def delete_annotation(self, annotation_id: str, *, user_id: int | None = None, admin: bool = False) -> bool:
        annotation_id = str(annotation_id or "").strip()
        with self._lock:
            return self.repository.delete_annotation(annotation_id, user_id=user_id, admin=admin)

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
        credential-bearing administrative artifact.
        """
        with self._lock:
            return copy.deepcopy(self._read())

    def reset_to_fresh_install(self) -> dict[str, Any]:
        """Restore shipped locales and drop profiles, annotations, and job history."""
        with self._lock:
            self._write(self._default())
        cleared_jobs = SQLiteJobRepository(self.path).clear_all()
        return {
            "languages": ["en-US", "fr-CA"],
            "profiles": 0,
            "annotations": 0,
            "cleared_jobs": cleared_jobs,
        }

    def restore_snapshot(self, payload: dict[str, Any]) -> None:
        """Restore a current-format server-owned configuration snapshot."""
        if not isinstance(payload, dict):
            raise ValueError("System configuration backup is invalid.")
        profiles = payload.get("researcher_provider_profiles", [])
        languages = payload.get("languages", {})
        if not isinstance(profiles, list) or not isinstance(languages, dict):
            raise ValueError("System configuration backup is invalid.")
        with self._lock:
            self._write(copy.deepcopy(payload))
            self._ensure()


system_store = SystemStore()
