from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from typing import Any

from .models import OllamaTouchupOptions
from .rag import _extract_json, chat_complete

_PLACEHOLDER_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
_WORD_RE = re.compile(r"[A-Za-z]{3,}")
_PROTECTED_ONLY_RE = re.compile(r"^(?:[A-Z0-9_.:/+\- ]+|DerridAI)$")


class LanguageTranslationError(ValueError):
    """Raised when a provider/model does not produce a usable locale dictionary.

    ``partial_dictionary`` intentionally contains only translations that passed
    structural safety checks.  The job manager can retain it and resume a later
    operation without retranslating completed strings.
    """

    def __init__(
        self,
        message: str,
        *,
        partial_dictionary: Mapping[str, str] | None = None,
        failed_keys: list[str] | None = None,
        failures: list[dict[str, str]] | None = None,
        stats: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.partial_dictionary = dict(partial_dictionary or {})
        self.failed_keys = list(failed_keys or [])
        self.failures = list(failures or [])
        self.stats = dict(stats or {})


class LanguageTranslationInterrupted(InterruptedError):
    """Cancellation carrying the validated work completed before interruption."""

    def __init__(
        self,
        message: str,
        *,
        partial_dictionary: Mapping[str, str] | None = None,
        failed_keys: list[str] | None = None,
        failures: list[dict[str, str]] | None = None,
        stats: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.partial_dictionary = dict(partial_dictionary or {})
        self.failed_keys = list(failed_keys or [])
        self.failures = list(failures or [])
        self.stats = dict(stats or {})


def _locale_style(code: str) -> str:
    if code == "fr-CA":
        return (
            "Use professional Canadian French as written in Québec. Follow Office québécois de la langue française (OQLF) "
            "terminology where applicable, prefer natural Québec software-"
            "interface vocabulary, avoid France-only wording and unnecessary English calques, and "
            "follow Canadian French typography. "
        )
    return ""


def _chunk_dictionary(
    dictionary: Mapping[str, str],
    *,
    max_items: int = 56,
    max_chars: int = 14_000,
) -> list[dict[str, str]]:
    batches: list[dict[str, str]] = []
    current: dict[str, str] = {}
    current_chars = 2
    for key, value in dictionary.items():
        pair_chars = len(key) + len(value) + 8
        if current and (len(current) >= max_items or current_chars + pair_chars > max_chars):
            batches.append(current)
            current = {}
            current_chars = 2
        current[str(key)] = str(value)
        current_chars += pair_chars
    if current:
        batches.append(current)
    return batches


def _translation_prompt(code: str, batch: Mapping[str, str]) -> str:
    return (
        "You are translating the DerridAI software interface from canonical U.S. English. "
        f"Translate every natural-language VALUE in the JSON object into locale {code}. "
        + _locale_style(code)
        + "Keep every key exactly unchanged. Do not omit keys and do not add keys. Preserve "
        "DerridAI, placeholders such as {count}, technical acronyms such as API/RAG/LLM, model "
        "names, URLs, keyboard shortcuts, and markup. Keep the original meaning, modality, and "
        "concise interface tone. Do not explain your work. Return only one JSON object with exactly "
        "the same keys.\n\nSOURCE (en-US):\n"
        + json.dumps(dict(batch), ensure_ascii=False)
    )


def _validate_batch(
    *,
    source: Mapping[str, str],
    translated: Mapping[str, Any],
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Return safe translations and per-key failures instead of failing the batch.

    A single damaged string should not throw away an otherwise useful translation
    run.  The caller decides whether the aggregate failure ratio is acceptable.
    """

    clean: dict[str, str] = {}
    failures: list[dict[str, str]] = []
    for key, source_text in source.items():
        if key not in translated:
            failures.append({"key": key, "reason": "missing key"})
            continue
        value = translated.get(key)
        if not isinstance(value, str) or not value.strip():
            failures.append({"key": key, "reason": "empty or non-text value"})
            continue
        source_slots = sorted(_PLACEHOLDER_RE.findall(source_text))
        target_slots = sorted(_PLACEHOLDER_RE.findall(value))
        if source_slots != target_slots:
            failures.append({"key": key, "reason": "placeholder(s) changed"})
            continue
        clean[key] = value.strip()
    return clean, failures


def _translation_signal(source: Mapping[str, str], translated: Mapping[str, str]) -> tuple[int, int, list[str]]:
    candidates = 0
    changed = 0
    unchanged_keys: list[str] = []
    for key, source_text in source.items():
        text = source_text.strip()
        if len(text) < 5 or not _WORD_RE.search(text) or _PROTECTED_ONLY_RE.fullmatch(text):
            continue
        candidates += 1
        if translated.get(key, "").strip().casefold() != text.casefold():
            changed += 1
        else:
            unchanged_keys.append(key)
    return changed, candidates, unchanged_keys


def _safe_resume_dictionary(
    source: Mapping[str, str],
    resume_dictionary: Mapping[str, str] | None,
) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, value in (resume_dictionary or {}).items():
        if key not in source or not isinstance(value, str) or not value.strip():
            continue
        if sorted(_PLACEHOLDER_RE.findall(source[key])) != sorted(_PLACEHOLDER_RE.findall(value)):
            continue
        clean[key] = value.strip()
    return clean


def translate_english_dictionary(
    *,
    code: str,
    dictionary: Mapping[str, str],
    provider: str,
    model: str,
    base_url: str | None,
    api_key: str | None,
    generation: OllamaTouchupOptions | None = None,
    cancelled: Callable[[], bool] | None = None,
    progress: Callable[[int, int, str], None] | None = None,
    resume_dictionary: Mapping[str, str] | None = None,
    retry_keys: list[str] | None = None,
    max_failure_ratio: float = 0.10,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Translate the canonical English dictionary in bounded, resumable batches.

    Valid translations are retained as the run progresses.  Fewer than 10% of
    keys may fail structural/provider validation; those keys fall back to
    canonical English and are reported to the caller.  A 10% or larger failure
    ratio remains a failed run,
    but the validated partial dictionary is attached to the exception so a later
    job can resume from it rather than starting over.
    """

    source = {str(key): str(value) for key, value in dictionary.items()}
    if not source:
        raise LanguageTranslationError("The canonical English interface dictionary is empty.")
    if not str(model or "").strip():
        raise LanguageTranslationError("Select a model to translate the language dictionary.")

    translated_all = _safe_resume_dictionary(source, resume_dictionary)
    retry_set = {str(key) for key in (retry_keys or []) if str(key) in source}
    if retry_set:
        # A prior run can mark strings as unsafe/effectively untranslated even if
        # it retained their raw text. Force those keys back through translation.
        for key in retry_set:
            translated_all.pop(key, None)

    pending = {key: value for key, value in source.items() if key not in translated_all}
    batches = _chunk_dictionary(pending)
    total = len(source)
    completed = len(translated_all)
    failures: list[dict[str, str]] = []

    def stats_payload(*, changed: int = 0, candidates: int = 0) -> dict[str, Any]:
        failed_keys = sorted({item["key"] for item in failures if item.get("key")})
        return {
            "key_count": total,
            "translated_count": len(translated_all),
            "failed_count": len(failed_keys),
            "failed_keys": failed_keys,
            "failures": failures[:250],
            "changed_count": changed,
            "candidate_count": candidates,
            "batch_count": len(batches),
            "resumed_count": max(0, total - len(pending)),
        }

    for index, batch in enumerate(batches, start=1):
        if cancelled and cancelled():
            current_stats = stats_payload()
            raise LanguageTranslationInterrupted(
                "Language translation cancelled. The completed portion can be resumed.",
                partial_dictionary=translated_all,
                failed_keys=current_stats["failed_keys"],
                failures=failures,
                stats=current_stats,
            )
        if progress:
            progress(
                completed,
                total,
                f"Translating English interface strings · batch {index} of {len(batches)}",
            )
        prompt = _translation_prompt(code, batch)
        batch_json = json.dumps(batch, ensure_ascii=False)
        try:
            raw = chat_complete(
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
                prompt=prompt,
                options=generation,
                json_mode=True,
                max_tokens=max(1400, min(9000, int(len(batch_json) * 1.8))),
                cancelled=cancelled,
            )
            parsed = _extract_json(raw)
            if not isinstance(parsed, Mapping):
                raise ValueError("provider returned a non-object JSON payload")
            clean, batch_failures = _validate_batch(source=batch, translated=parsed)
            translated_all.update(clean)
            failures.extend(batch_failures)
        except InterruptedError:
            current_stats = stats_payload()
            raise LanguageTranslationInterrupted(
                "Language translation cancelled. The completed portion can be resumed.",
                partial_dictionary=translated_all,
                failed_keys=current_stats["failed_keys"],
                failures=failures,
                stats=current_stats,
            )
        except Exception as exc:
            reason = str(exc) or exc.__class__.__name__
            failures.extend({"key": key, "reason": f"batch failed: {reason}"} for key in batch)

        completed = len(translated_all) + len({item["key"] for item in failures if item.get("key")})
        if progress:
            progress(
                min(total, completed),
                total,
                f"Processed {min(total, completed):,} of {total:,} English interface strings",
            )

    # Detect providers that returned structurally valid English instead of a
    # translation. Mark those strings for retry so a resumed run does not skip
    # them merely because JSON validation succeeded.
    changed, candidates, unchanged_keys = _translation_signal(source, translated_all)
    primary_language = code.split("-", 1)[0].lower()
    effectively_untranslated = False
    if primary_language != "en" and candidates >= 20:
        unchanged_ratio = 1.0 - (changed / candidates)
        if unchanged_ratio >= 0.82:
            effectively_untranslated = True
            existing_failed = {item["key"] for item in failures if item.get("key")}
            for key in unchanged_keys:
                if key not in existing_failed:
                    failures.append({"key": key, "reason": "returned unchanged English"})
                    translated_all.pop(key, None)

    failed_keys = sorted({item["key"] for item in failures if item.get("key")})
    failure_ratio = len(failed_keys) / total if total else 0.0
    stats = stats_payload(changed=changed, candidates=candidates)
    stats["failure_ratio"] = failure_ratio
    stats["fallback_count"] = len(failed_keys)

    if failure_ratio >= max_failure_ratio or effectively_untranslated:
        reason_counts: dict[str, int] = {}
        for item in failures:
            reason = item.get("reason") or "translation failure"
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        leading_reason = max(reason_counts, key=reason_counts.get) if reason_counts else "translation failure"
        if effectively_untranslated:
            message = (
                f"The selected model/provider did not produce a usable {code} translation: "
                f"{len(failed_keys)} of {total} keys need retry because the model returned mostly unchanged English. "
                "The completed portion was retained; retry with a stronger translation-capable model/provider."
            )
        else:
            message = (
                f"The selected model/provider could not safely translate {code}: {len(failed_keys)} of {total} keys "
                f"failed ({round(failure_ratio * 100)}%; most common issue: {leading_reason}). "
                "10% or more failed, so the locale was not installed. The completed portion was retained and can be resumed."
            )
        raise LanguageTranslationError(
            message,
            partial_dictionary=translated_all,
            failed_keys=failed_keys,
            failures=failures,
            stats=stats,
        )

    # A small number of failed keys should not block installation. Canonical
    # English is a deliberate, visible fallback and the failure list is returned
    # so the UI can tell the administrator exactly what remains to localize.
    final_dictionary = dict(translated_all)
    for key in failed_keys:
        final_dictionary[key] = source[key]
    stats["translated_count"] = len(translated_all)
    stats["installed_count"] = len(final_dictionary)
    stats["warning"] = (
        f"Installed with {len(failed_keys)} English fallback string(s) that could not be translated safely."
        if failed_keys
        else ""
    )
    return final_dictionary, stats
