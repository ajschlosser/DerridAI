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
    """Raised when a provider/model does not produce a usable locale dictionary."""

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
            "terminology where applicable, prefer natural Québec software-interface vocabulary, avoid France-only wording "
            "and unnecessary English calques, and follow Canadian French typography. "
        )
    return ""


def _chunk_dictionary(
    dictionary: Mapping[str, str],
    *,
    max_items: int = 24,
    max_chars: int = 6_500,
) -> list[dict[str, str]]:
    """Create deliberately small batches.

    Translation models are much more reliable when the constrained JSON task is
    short.  Earlier builds used ~14k-character / 56-key batches, which caused a
    single truncated or malformed response to invalidate a large portion of the
    dictionary.  These smaller batches also make resume checkpoints useful.
    """
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


def _translation_prompt(code: str, batch: Mapping[str, str], *, retry: bool = False) -> str:
    retry_note = (
        "This is a repair pass because an earlier attempt omitted, copied, or damaged one or more values. "
        "Translate the values; do not copy English prose unless the value is a protected product name, acronym, URL, shortcut, or code. "
        if retry else ""
    )
    return (
        "You are translating the DerridAI software interface from canonical English. "
        f"The target locale is {code}. Translate every natural-language VALUE in the JSON object into {code}. "
        + _locale_style(code)
        + retry_note
        + "Keep every key exactly unchanged. Do not omit keys and do not add keys. Preserve DerridAI, placeholders such as "
        "{count}, technical acronyms such as API/RAG/LLM, model names, URLs, keyboard shortcuts, and markup. "
        "Keep the original meaning, modality, punctuation intent, and concise interface tone. Do not explain your work. "
        "Return only one JSON object with exactly the same keys and string values.\n\nSOURCE (en-US):\n"
        + json.dumps(dict(batch), ensure_ascii=False)
    )


def _extract_translation_json(text: str) -> dict[str, Any]:
    """Parse constrained translation JSON with conservative local repairs.

    Some OpenAI-compatible/local models wrap JSON in prose or emit a trailing
    comma despite JSON mode.  We accept only an object and never infer missing
    translations, but harmless syntax repairs keep a good batch from being lost.
    """
    try:
        return _extract_json(text)
    except Exception:
        value = str(text or "").strip()
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
        value = re.sub(r"\s*```$", "", value)
        start, end = value.find("{"), value.rfind("}")
        if start >= 0 and end > start:
            value = value[start : end + 1]
        repaired = re.sub(r",\s*([}\]])", r"\1", value)
        parsed = json.loads(repaired)
        if not isinstance(parsed, dict):
            raise ValueError("provider returned a non-object JSON payload")
        return parsed


def _validate_batch(
    *,
    source: Mapping[str, str],
    translated: Mapping[str, Any],
) -> tuple[dict[str, str], list[dict[str, str]]]:
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
    """Translate canonical English with checkpoints, repair retries and fallbacks.

    The pipeline never throws away validated work.  Batch failures are bisected
    into smaller retry batches down to individual strings, malformed JSON gets a
    conservative syntax repair pass, and mostly-unchanged English receives one
    explicit repair pass.  Fewer than ``max_failure_ratio`` failures install as
    tracked English fallbacks; larger failures remain resumable.
    """

    source = {str(key): str(value) for key, value in dictionary.items()}
    if not source:
        raise LanguageTranslationError("The canonical English interface dictionary is empty.")
    if not str(model or "").strip():
        raise LanguageTranslationError("Select a model to translate the language dictionary.")

    translated_all = _safe_resume_dictionary(source, resume_dictionary)
    retry_set = {str(key) for key in (retry_keys or []) if str(key) in source}
    for key in retry_set:
        translated_all.pop(key, None)

    pending = {key: value for key, value in source.items() if key not in translated_all}
    batches = _chunk_dictionary(pending)
    total = len(source)
    initial_resumed = len(translated_all)
    failure_by_key: dict[str, str] = {}
    attempts = 0

    def failure_list() -> list[dict[str, str]]:
        return [{"key": key, "reason": reason} for key, reason in sorted(failure_by_key.items())]

    def stats_payload(*, changed: int = 0, candidates: int = 0) -> dict[str, Any]:
        failures = failure_list()
        return {
            "key_count": total,
            "translated_count": len(translated_all),
            "failed_count": len(failures),
            "failed_keys": [item["key"] for item in failures],
            "failures": failures[:250],
            "changed_count": changed,
            "candidate_count": candidates,
            "batch_count": len(batches),
            "attempt_count": attempts,
            "resumed_count": initial_resumed,
        }

    def interrupted() -> None:
        current = stats_payload()
        raise LanguageTranslationInterrupted(
            "Language translation cancelled. The completed portion can be resumed.",
            partial_dictionary=translated_all,
            failed_keys=current["failed_keys"],
            failures=current["failures"],
            stats=current,
        )

    def translate_single_plain(key: str, source_text: str) -> bool:
        """Last-resort path for providers that cannot honor JSON mode reliably.

        We still validate placeholders and never infer a translation locally.  A
        one-string request is intentionally simple enough for small/local chat
        models that truncate or decorate structured JSON responses.
        """
        nonlocal attempts
        if cancelled and cancelled():
            interrupted()
        attempts += 1
        prompt = (
            f"Translate the following DerridAI interface string from English into {code}. "
            + _locale_style(code)
            + "Preserve placeholders such as {count}, product names, URLs, shortcuts, markup, and punctuation intent. "
              "Return only the translated text itself: no JSON, no quotation marks, no explanation.\n\n"
            + source_text
        )
        try:
            raw = chat_complete(
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
                prompt=prompt,
                options=generation,
                json_mode=False,
                max_tokens=max(256, min(1200, len(source_text) * 5 + 128)),
                cancelled=cancelled,
            )
            value = str(raw or "").strip()
            value = re.sub(r"^```(?:text)?\s*", "", value, flags=re.I)
            value = re.sub(r"\s*```$", "", value).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1].strip()
            if not value:
                return False
            if sorted(_PLACEHOLDER_RE.findall(source_text)) != sorted(_PLACEHOLDER_RE.findall(value)):
                return False
            translated_all[key] = value
            failure_by_key.pop(key, None)
            return True
        except InterruptedError:
            interrupted()
        except Exception:
            return False
        return False

    def translate_batch(batch: Mapping[str, str], *, retry: bool = False, depth: int = 0) -> None:
        nonlocal attempts
        if not batch:
            return
        if cancelled and cancelled():
            interrupted()
        attempts += 1
        prompt = _translation_prompt(code, batch, retry=retry)
        batch_json = json.dumps(dict(batch), ensure_ascii=False)
        try:
            raw = chat_complete(
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
                prompt=prompt,
                options=generation,
                json_mode=True,
                max_tokens=max(1800, min(10000, int(len(batch_json) * 3.2))),
                cancelled=cancelled,
            )
            parsed = _extract_translation_json(raw)
            # Common local-model wrappers are harmless when they contain the
            # exact requested key/value object. Accept them rather than forcing
            # every key through individual retries.
            for wrapper in ("translations", "translation", "dictionary", "result", "output"):
                nested = parsed.get(wrapper) if isinstance(parsed, dict) else None
                if isinstance(nested, dict) and any(key in nested for key in batch):
                    parsed = nested
                    break
            clean, batch_failures = _validate_batch(source=batch, translated=parsed)
            for key, value in clean.items():
                translated_all[key] = value
                failure_by_key.pop(key, None)
            failed_subset = {item["key"]: batch[item["key"]] for item in batch_failures if item.get("key") in batch}
            for item in batch_failures:
                if item.get("key"):
                    failure_by_key[item["key"]] = item.get("reason") or "translation failure"
            # Structural defects are retried immediately in a much smaller task.
            if failed_subset:
                if depth < 3:
                    if len(failed_subset) > 1:
                        items = list(failed_subset.items())
                        mid = max(1, len(items) // 2)
                        translate_batch(dict(items[:mid]), retry=True, depth=depth + 1)
                        translate_batch(dict(items[mid:]), retry=True, depth=depth + 1)
                    else:
                        translate_batch(failed_subset, retry=True, depth=depth + 1)
                elif len(failed_subset) == 1:
                    key, source_text = next(iter(failed_subset.items()))
                    translate_single_plain(key, source_text)
        except InterruptedError:
            interrupted()
        except Exception as exc:
            reason = str(exc) or exc.__class__.__name__
            # A transport/JSON failure on a multi-key batch should not condemn
            # the entire batch. Bisect it and retry; an individual key gets one
            # further structured retry and then a plain-text fallback for models
            # that are competent translators but unreliable JSON emitters.
            if len(batch) > 1 and depth < 4:
                items = list(batch.items())
                mid = max(1, len(items) // 2)
                translate_batch(dict(items[:mid]), retry=True, depth=depth + 1)
                translate_batch(dict(items[mid:]), retry=True, depth=depth + 1)
            elif len(batch) == 1:
                key, source_text = next(iter(batch.items()))
                if depth < 2:
                    translate_batch(batch, retry=True, depth=depth + 1)
                elif not translate_single_plain(key, source_text):
                    failure_by_key[key] = f"translation failed: {reason}"
            else:
                for key in batch:
                    failure_by_key[key] = f"translation failed: {reason}"

    for index, batch in enumerate(batches, start=1):
        if progress:
            progress(
                len(translated_all),
                total,
                f"Translating English interface strings · batch {index} of {len(batches)}",
            )
        translate_batch(batch)
        processed = min(total, len(translated_all) + len(failure_by_key))
        if progress:
            progress(processed, total, f"Processed {processed:,} of {total:,} English interface strings")

    # If the model structurally succeeded but mostly copied English, retry those
    # exact strings in very small, explicit repair batches before declaring the
    # model unsuitable for translation.
    changed, candidates, unchanged_keys = _translation_signal(source, translated_all)
    primary_language = code.split("-", 1)[0].lower()
    if primary_language != "en" and candidates >= 20 and changed / candidates <= 0.18 and unchanged_keys:
        for batch in _chunk_dictionary({key: source[key] for key in unchanged_keys}, max_items=8, max_chars=2200):
            for key in batch:
                translated_all.pop(key, None)
            translate_batch(batch, retry=True)
        changed, candidates, unchanged_keys = _translation_signal(source, translated_all)

    effectively_untranslated = False
    if primary_language != "en" and candidates >= 20:
        unchanged_ratio = 1.0 - (changed / candidates)
        if unchanged_ratio >= 0.82:
            effectively_untranslated = True
            for key in unchanged_keys:
                translated_all.pop(key, None)
                failure_by_key[key] = "returned unchanged English"

    failed_keys = sorted(failure_by_key)
    failure_ratio = len(failed_keys) / total if total else 0.0
    stats = stats_payload(changed=changed, candidates=candidates)
    stats["failure_ratio"] = failure_ratio
    stats["fallback_count"] = len(failed_keys)

    if failure_ratio >= max_failure_ratio or effectively_untranslated:
        failures = failure_list()
        reason_counts: dict[str, int] = {}
        for item in failures:
            reason = item.get("reason") or "translation failure"
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        leading_reason = max(reason_counts, key=reason_counts.get) if reason_counts else "translation failure"
        if effectively_untranslated:
            message = (
                f"The selected model/provider did not produce a usable {code} translation: "
                f"{len(failed_keys)} of {total} keys still need retry because the model returned mostly unchanged English. "
                "Validated translations were retained; resume with a stronger translation-capable model/provider."
            )
        else:
            message = (
                f"The selected model/provider could not safely translate {code}: {len(failed_keys)} of {total} keys "
                f"failed ({round(failure_ratio * 100)}%; most common issue: {leading_reason}). "
                "Validated translations were retained and the operation can be resumed without starting over."
            )
        raise LanguageTranslationError(
            message,
            partial_dictionary=translated_all,
            failed_keys=failed_keys,
            failures=failures,
            stats=stats,
        )

    final_dictionary = dict(translated_all)
    for key in failed_keys:
        final_dictionary[key] = source[key]
    stats["translated_count"] = len(translated_all)
    stats["installed_count"] = len(final_dictionary)
    stats["warning"] = (
        f"Installed with {len(failed_keys)} English fallback string(s) that could not be translated safely."
        if failed_keys else ""
    )
    return final_dictionary, stats
