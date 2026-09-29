# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic, offline POS/NER candidates for schema fields.

spaCy runs locally with pre-installed model packages (no network at runtime). Its
output is *candidate surface forms* only: exact substrings of the record text with
offsets and the linguistic tag that matched. A candidate is not a metadata value and
not evidence of a role; a person named in a passage is not thereby its speaker,
quoted speaker or position holder. Candidates guide the LLM prompt and let a
proposed value be checked against the text; they never populate or confirm a field.

Models resolve in order: a configured/installed package (``SPACY_MODEL_<LANG>``), an
administrator-installed spaCy language pack, then the multilingual ``xx`` entity
model, whose use is named in the reported model. If none loads, annotation is
reported as ``unavailable`` (visible, not silently empty).
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

ANNOTATION_VERSION = 1
MAX_TEXT_CHARS = 20000
MAX_CANDIDATES_PER_FIELD = 12
# The large pipelines recognise philosophers' names markedly better than the small
# ones (measured on a Rousseau/Hobbes/Derrida sample); override per language with
# SPACY_MODEL_EN / _FR / _DE, for example to a smaller model on constrained hosts.
DEFAULT_MODELS = {
    "en": "en_core_web_lg",
    "fr": "fr_core_news_lg",
    "de": "de_core_news_lg",
}
# Non-English pipelines use different entity inventories; map to the shared vocabulary.
_LABEL_ALIASES = {"PER": "PERSON"}
_LABEL_SUPERSETS = {"LOC": {"LOC", "GPE", "FAC"}}

# Language names seen in record metadata; any ISO 639 code is also accepted.
_LANGUAGE_NAMES = {
    "english": "en", "french": "fr", "français": "fr", "francais": "fr", "german": "de", "deutsch": "de",
    "italian": "it", "italiano": "it", "spanish": "es", "español": "es", "espanol": "es",
    "portuguese": "pt", "português": "pt", "dutch": "nl", "nederlands": "nl", "russian": "ru",
    "polish": "pl", "catalan": "ca", "català": "ca", "danish": "da", "greek": "el", "finnish": "fi",
    "croatian": "hr", "japanese": "ja", "korean": "ko", "lithuanian": "lt", "macedonian": "mk",
    "norwegian": "nb", "romanian": "ro", "slovenian": "sl", "swedish": "sv", "ukrainian": "uk",
    "chinese": "zh", "latin": "la", "hebrew": "he", "arabic": "ar", "czech": "cs", "hungarian": "hu",
}
# Multilingual named-entity pipeline used when a language has no model of its own.
MULTILINGUAL = "xx"

_lock = threading.Lock()
_pipelines: dict[str, Any] = {}
_loaded_names: dict[str, str] = {}
_missing: set[str] = set()


def _model_name(language: str) -> str | None:
    """The model actually loaded for ``language`` or, before loading, the configured one."""
    return _loaded_names.get(language) or (
        os.environ.get(f"SPACY_MODEL_{language.upper()}") or DEFAULT_MODELS.get(language)
    )


def reset_pipelines() -> None:
    """Forget loaded and missing pipelines, e.g. after a spaCy language pack is (un)installed."""
    with _lock:
        _pipelines.clear()
        _loaded_names.clear()
        _missing.clear()


def _candidate_models(language: str) -> list[tuple[str, str]]:
    """(load target, reported name) in priority order: configured package, installed pack, multilingual."""
    from .document_nlp_packs import installed_spacy_model

    out: list[tuple[str, str]] = []
    configured = os.environ.get(f"SPACY_MODEL_{language.upper()}") or DEFAULT_MODELS.get(language)
    if configured:
        out.append((configured, configured))
    pack = installed_spacy_model(language)
    if pack:
        out.append(pack)
    if language != MULTILINGUAL:
        fallback = installed_spacy_model(MULTILINGUAL)
        out.append(
            (fallback[0], f"{fallback[1]} (multilingual fallback)") if fallback
            else ("xx_ent_wiki_sm", "xx_ent_wiki_sm (multilingual fallback)")
        )
    return out


def text_digest(text: str) -> str:
    """Identifies the text the candidates were computed from, so edits invalidate them."""
    return hashlib.sha256(text[:MAX_TEXT_CHARS].encode("utf-8")).hexdigest()


def language_code(value: Any) -> str:
    """Two-letter code for a language name or tag, else ''."""
    text = str(value or "").strip().lower().replace("_", "-")
    code = _LANGUAGE_NAMES.get(text) or text.split("-")[0]
    return code if code.isascii() and code.isalpha() and 2 <= len(code) <= 3 else ""


def load_pipeline(language: str) -> Any | None:
    """Lazily load (and cache) the pipeline for ``language``; None if unavailable."""
    if language in _pipelines:
        return _pipelines[language]
    if language in _missing:
        return None
    with _lock:
        if language in _pipelines:
            return _pipelines[language]
        for target, name in _candidate_models(language):
            try:
                import spacy

                # The parser and lemmatizer are not needed for tags/entities and cost time.
                pipeline = spacy.load(target, exclude=["parser", "lemmatizer"])
            except Exception as exc:  # missing package or model: try the next, never guess
                logger.info("spaCy pipeline %r unavailable for %r: %s", name, language, exc)
                continue
            _pipelines[language] = pipeline
            _loaded_names[language] = name
            return pipeline
        logger.warning("No spaCy pipeline is available for %r.", language)
        _missing.add(language)
        return None


def _entity_matches(tag: str, label: str) -> bool:
    label = _LABEL_ALIASES.get(label, label)
    return label == tag or label in _LABEL_SUPERSETS.get(tag, set())


def _pos_runs(doc: Any, wanted: set[str]) -> list[dict[str, Any]]:
    """Maximal runs of adjacent tokens whose universal POS is wanted (e.g. PROPN PROPN)."""
    runs: list[dict[str, Any]] = []
    start = end = None
    tags: list[str] = []
    for token in doc:
        if token.pos_ in wanted:
            if start is None:
                start = token.idx
            end = token.idx + len(token.text)
            tags.append(token.pos_)
        elif start is not None:
            runs.append({"start": start, "end": end, "tag": "+".join(dict.fromkeys(tags))})
            start = end = None
            tags = []
    if start is not None:
        runs.append({"start": start, "end": end, "tag": "+".join(dict.fromkeys(tags))})
    return runs


def field_candidates(doc: Any, text: str, *, pos_tags: list[str], ner_tags: list[str]) -> list[dict[str, Any]]:
    """Candidate spans for one field, deduplicated and bounded. Every span is text[start:end]."""
    found: dict[tuple[int, int], dict[str, Any]] = {}
    if ner_tags:
        for ent in doc.ents:
            if any(_entity_matches(tag, ent.label_) for tag in ner_tags):
                found[(ent.start_char, ent.end_char)] = {
                    "start": ent.start_char, "end": ent.end_char, "text": text[ent.start_char:ent.end_char],
                    "source": "ner", "tag": _LABEL_ALIASES.get(ent.label_, ent.label_),
                }
    if pos_tags:
        for run in _pos_runs(doc, set(pos_tags)):
            key = (run["start"], run["end"])
            if key not in found:
                found[key] = {**run, "text": text[run["start"]:run["end"]], "source": "pos"}
    ordered = sorted(found.values(), key=lambda item: item["start"])
    return ordered[:MAX_CANDIDATES_PER_FIELD]


def annotate_record(record: dict[str, Any], schema: Any, *, language: str = "") -> dict[str, Any]:
    """Compute NLP candidates for the schema fields that declare POS/NER tags.

    Returns (and stores on ``record["nlp_candidates"]``) a dict with ``status``
    (``ok`` | ``unavailable`` | ``skipped``), the model name, and per-field candidates.
    Derived, rebuildable data: it is recomputed whenever the record text changes.
    """
    text = str(record.get("text") or "")
    fields = [f for f in getattr(schema, "fields", []) if getattr(f, "pos_tags", None) or getattr(f, "ner_tags", None)]
    languages = record.get("region_language") if isinstance(record.get("region_language"), list) else []
    code = language_code(language) or next((c for c in (language_code(v) for v in languages) if c), "")
    result: dict[str, Any] = {
        "version": ANNOTATION_VERSION, "status": "skipped", "language": code, "model": "", "fields": {},
        "text_sha256": text_digest(text),
    }
    if not fields or not text.strip():
        record["nlp_candidates"] = result
        return result
    if not code:
        result["status"] = "unavailable"
        result["reason"] = "language_not_supported"
        record["nlp_candidates"] = result
        return result
    pipeline = load_pipeline(code)
    if pipeline is None:
        result.update(status="unavailable", reason="model_not_installed", model=_model_name(code) or "")
        record["nlp_candidates"] = result
        return result
    bounded = text[:MAX_TEXT_CHARS]
    doc = pipeline(bounded)
    result.update(status="ok", model=_model_name(code) or "")
    for field in fields:
        candidates = field_candidates(doc, bounded, pos_tags=list(field.pos_tags), ner_tags=list(field.ner_tags))
        if candidates:
            result["fields"][field.name] = candidates
    record["nlp_candidates"] = result
    return result


def prompt_hints(record: dict[str, Any], field_names: list[str]) -> dict[str, list[str]]:
    """Candidate surface forms for the given fields, for a prompt. Empty when not ok."""
    data = record.get("nlp_candidates")
    if not isinstance(data, dict) or data.get("status") != "ok":
        return {}
    if data.get("text_sha256") != text_digest(str(record.get("text") or "")):
        return {}  # the text changed since annotation; offsets and surface forms are stale
    fields = data.get("fields") or {}
    return {
        name: list(dict.fromkeys(item["text"] for item in fields[name]))
        for name in field_names
        if fields.get(name)
    }
