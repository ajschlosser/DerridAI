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
    code: str,
    source: Mapping[str, str],
    translated: Mapping[str, Any],
    batch_number: int,
    batch_count: int,
) -> dict[str, str]:
    missing = [key for key in source if key not in translated]
    if missing:
        sample = ", ".join(missing[:4])
        raise LanguageTranslationError(
            f"The selected model/provider could not translate {code}: translation batch "
            f"{batch_number} of {batch_count} omitted {len(missing)} required key(s)"
            f" ({sample}). Try a translation-capable model or increase its context/output limit."
        )

    clean: dict[str, str] = {}
    for key, source_text in source.items():
        value = translated.get(key)
        if not isinstance(value, str) or not value.strip():
            raise LanguageTranslationError(
                f"The selected model/provider could not translate {code}: key {key!r} returned "
                "an empty or non-text value. Try another translation-capable model/provider."
            )
        source_slots = sorted(_PLACEHOLDER_RE.findall(source_text))
        target_slots = sorted(_PLACEHOLDER_RE.findall(value))
        if source_slots != target_slots:
            raise LanguageTranslationError(
                f"The selected model/provider produced an unsafe translation for {code}: "
                f"placeholder(s) changed in {key!r}. No language was installed."
            )
        clean[key] = value.strip()
    return clean


def _translation_signal(source: Mapping[str, str], translated: Mapping[str, str]) -> tuple[int, int]:
    candidates = 0
    changed = 0
    for key, source_text in source.items():
        text = source_text.strip()
        if len(text) < 5 or not _WORD_RE.search(text) or _PROTECTED_ONLY_RE.fullmatch(text):
            continue
        candidates += 1
        if translated.get(key, "").strip().casefold() != text.casefold():
            changed += 1
    return changed, candidates


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
) -> tuple[dict[str, str], dict[str, int]]:
    """Translate the canonical English dictionary in bounded, validated batches.

    Nothing is persisted here. Callers save only after every batch validates, so a
    truncated/refused response can never create a mostly-English installed locale.
    """

    source = {str(key): str(value) for key, value in dictionary.items()}
    if not source:
        raise LanguageTranslationError("The canonical English interface dictionary is empty.")
    if not str(model or "").strip():
        raise LanguageTranslationError("Select a model to translate the language dictionary.")

    batches = _chunk_dictionary(source)
    translated_all: dict[str, str] = {}
    completed = 0
    total = len(source)

    for index, batch in enumerate(batches, start=1):
        if cancelled and cancelled():
            raise InterruptedError("Language translation cancelled.")
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
            clean = _validate_batch(
                code=code,
                source=batch,
                translated=parsed,
                batch_number=index,
                batch_count=len(batches),
            )
        except InterruptedError:
            raise
        except LanguageTranslationError:
            raise
        except Exception as exc:
            raise LanguageTranslationError(
                f"The selected model/provider was unable to translate {code}: {exc}"
            ) from exc

        translated_all.update(clean)
        completed += len(batch)
        if progress:
            progress(
                completed,
                total,
                f"Translated {completed:,} of {total:,} English interface strings",
            )

    changed, candidates = _translation_signal(source, translated_all)
    primary_language = code.split("-", 1)[0].lower()
    if primary_language != "en" and candidates >= 20:
        unchanged_ratio = 1.0 - (changed / candidates)
        if unchanged_ratio >= 0.82:
            raise LanguageTranslationError(
                f"The selected model/provider did not produce a usable {code} translation: "
                f"{round(unchanged_ratio * 100)}% of translatable English strings were returned "
                "unchanged. No language was installed. Try another translation-capable model/provider."
            )

    return translated_all, {
        "key_count": total,
        "changed_count": changed,
        "candidate_count": candidates,
        "batch_count": len(batches),
    }
