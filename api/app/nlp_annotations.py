# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Deterministic, offline POS/NER candidates for schema fields.

spaCy runs locally with bundled English/French model packages and administrator-installed
language packs (no network during corpus processing). Its output is a raw *candidate
surface-form* layer: exact substrings of the record text
with offsets and the linguistic tag that matched. A raw candidate is not scholarly
authority and not evidence of a discourse role; a person named in a passage is not
thereby its speaker, quoted speaker or position holder. Candidates guide model prompts
and validation. A separate candidate resolver may promote only schema-compatible
direct-mention indexing spans into explicitly unreviewed ``derridai:nlp`` FieldAssertions;
the raw annotation layer itself never confirms a field.

The same pass keeps a bounded record-level ``terms`` layer (named entities plus
proper-noun and noun runs) for the Record semantic map. Terms are navigation aids:
exact spans with their tag, never metadata values or evidence.

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
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from .semantic_identity import SEMANTIC_IDENTITY_VERSION, entity_name_key, lexical_key

logger = logging.getLogger(__name__)

ANNOTATION_VERSION = 3
MAX_TEXT_CHARS = 20000
MAX_CANDIDATES_PER_FIELD = 12
MAX_TERMS = 60
# Universal POS runs kept as record terms. Function words are never dropped from the
# text; they only end a run, so a term is always an exact contiguous span.
TERM_POS_TAGS = ("PROPN", "NOUN")
# English and French are the built-in baseline. Other languages remain explicit,
# administrator-installed resources; SPACY_MODEL_<LANG> can still override either
# the bundled baseline or a managed pack when an operator needs a custom model.
DEFAULT_MODELS = {
    "en": "en_core_web_sm",
    "fr": "fr_core_news_sm",
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


def _engine_version() -> str:
    """Installed spaCy library version used for deterministic linguistic annotation."""
    try:
        return version("spacy")
    except PackageNotFoundError:
        return ""


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

                # The parser is not needed for tags/entities and costs time. The lemmatizer is
                # kept (rule/lookup based, cheap) for semantic identity of lexical phrases.
                pipeline = spacy.load(target, exclude=["parser"])
            except Exception as exc:  # missing package or model: try the next, never guess
                logger.info("spaCy pipeline %r unavailable for %r: %s", name, language, exc)
                continue
            _pipelines[language] = pipeline
            _loaded_names[language] = name
            return pipeline
        logger.warning("No spaCy pipeline is available for %r.", language)
        _missing.add(language)
        return None


MAX_LEMMA_CHARS = 2000


def lemma_tokens(text: str, language: Any) -> list[tuple[str, str, str]] | None:
    """(text, lemma, universal POS) for a short phrase, or None when no lemmatizer is installed."""
    code = language_code(language)
    phrase = str(text or "")
    if not code or not phrase.strip() or len(phrase) > MAX_LEMMA_CHARS:
        return None
    # The same cached pipeline as annotation, so no second model is held in memory. The
    # multilingual fallback has no lemmatizer: that reads as "unavailable", never as surface text.
    pipeline = load_pipeline(code)
    if pipeline is None or "lemmatizer" not in getattr(pipeline, "pipe_names", []):
        return None
    try:
        doc = pipeline(phrase)
    except Exception as exc:  # noqa: BLE001 - an unusable pipeline is "unavailable", never a guess
        logger.warning("spaCy lemmatization failed for %r: %s", code, exc)
        return None
    return [(str(token.text), str(token.lemma_ or ""), str(token.pos_ or "")) for token in doc]


def _entity_matches(tag: str, label: str) -> bool:
    label = _LABEL_ALIASES.get(label, label)
    return label == tag or label in _LABEL_SUPERSETS.get(tag, set())


def _pos_runs(doc: Any, wanted: set[str]) -> list[dict[str, Any]]:
    """Maximal runs of adjacent tokens whose universal POS is wanted.

    The all_stop marker lets candidate consumers reject function-word-only runs while
    preserving exact source spans. Minimal token objects without is_stop remain usable.
    """
    runs: list[dict[str, Any]] = []
    start = end = None
    tags: list[str] = []
    all_stop = True
    for token in doc:
        if token.pos_ in wanted:
            if start is None:
                start = token.idx
                all_stop = True
            end = token.idx + len(token.text)
            tags.append(token.pos_)
            all_stop = all_stop and bool(getattr(token, "is_stop", False))
        elif start is not None:
            runs.append({
                "start": start,
                "end": end,
                "tag": "+".join(dict.fromkeys(tags)),
                "all_stop": all_stop,
            })
            start = end = None
            tags = []
            all_stop = True
    if start is not None:
        runs.append({
            "start": start,
            "end": end,
            "tag": "+".join(dict.fromkeys(tags)),
            "all_stop": all_stop,
        })
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
            if run.pop("all_stop", False):
                continue
            key = (run["start"], run["end"])
            if key not in found:
                surface = text[run["start"]:run["end"]]
                if not surface.strip() or not any(char.isalpha() for char in surface):
                    continue
                found[key] = {**run, "text": surface, "source": "pos"}
    ordered = sorted(found.values(), key=lambda item: item["start"])
    return ordered[:MAX_CANDIDATES_PER_FIELD]


def record_terms(doc: Any, text: str) -> list[dict[str, Any]]:
    """Bounded NER and POS-run term spans for one record; every span is text[start:end]."""
    found: dict[tuple[int, int], dict[str, Any]] = {}
    for ent in doc.ents:
        label = _LABEL_ALIASES.get(ent.label_, ent.label_)
        found[(ent.start_char, ent.end_char)] = {
            "start": ent.start_char, "end": ent.end_char, "text": text[ent.start_char:ent.end_char],
            "source": "ner", "tag": label,
        }
    covered = [(start, end) for start, end in found]
    for tag in TERM_POS_TAGS:
        for run in _pos_runs(doc, {tag}):
            if run.pop("all_stop", False):
                continue
            key = (run["start"], run["end"])
            surface = text[run["start"]:run["end"]]
            # Named entities already describe these characters more specifically.
            if key in found or any(start <= key[0] and key[1] <= end for start, end in covered):
                continue
            if len(surface.strip()) < 3 or not any(char.isalpha() for char in surface):
                continue
            found[key] = {**run, "text": surface, "source": "pos"}
    ordered = sorted(found.values(), key=lambda item: item["start"])[:MAX_TERMS]
    for term in ordered:
        identity = _term_identity(doc, term)
        if identity:
            # Derived and rebuildable; ``text``/``start``/``end`` stay the exact source span.
            term["identity_text"] = identity
            term["identity_version"] = SEMANTIC_IDENTITY_VERSION
    return ordered


def _term_identity(doc: Any, term: dict[str, Any]) -> str:
    """A term's identity text: name identity for a person, noun/verb lemmas for a POS run.

    Omitted (empty) when the pipeline produced no lemmas, rather than guessed from surface.
    """
    if term.get("source") == "ner":
        return entity_name_key(str(term.get("text") or "")) if term.get("tag") == "PERSON" else ""
    span = doc.char_span(int(term["start"]), int(term["end"])) if hasattr(doc, "char_span") else None
    if span is None:
        return ""
    tokens = [(str(token.text), str(getattr(token, "lemma_", "") or ""), str(token.pos_ or "")) for token in span]
    if not tokens or not all(lemma for _, lemma, _ in tokens):
        return ""
    return lexical_key(tokens)


def annotate_record(record: dict[str, Any], schema: Any, *, language: str = "") -> dict[str, Any]:
    """Compute NLP candidates for tagged schema fields and the record-level term layer.

    Returns (and stores on ``record["nlp_candidates"]``) a dict with ``status``
    (``ok`` | ``unavailable`` | ``skipped``), the model name, per-field candidates,
    and ``terms``. Derived, rebuildable data: it is recomputed whenever the record
    text changes.
    """
    text = str(record.get("text") or "")
    fields = [f for f in getattr(schema, "fields", []) if getattr(f, "pos_tags", None) or getattr(f, "ner_tags", None)]
    languages = record.get("region_language") if isinstance(record.get("region_language"), list) else []
    code = language_code(language) or next((c for c in (language_code(v) for v in languages) if c), "")
    result: dict[str, Any] = {
        "version": ANNOTATION_VERSION,
        "status": "skipped",
        "engine": "spacy",
        "engine_version": _engine_version(),
        "language": code,
        "model": "",
        "fields": {},
        "terms": [],
        "text_sha256": text_digest(text),
    }
    if not text.strip():
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
    result["terms"] = record_terms(doc, bounded)
    record["nlp_candidates"] = result
    return result


def annotation_run_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build-level audit summary for record-local spaCy annotation."""
    statuses = [str(result.get("status") or "") for result in results]
    ok = [result for result in results if result.get("status") == "ok"]
    unavailable = [result for result in results if result.get("status") == "unavailable"]
    models = sorted({
        str(result.get("model") or "").strip()
        for result in ok
        if str(result.get("model") or "").strip()
    })
    languages = sorted({
        str(result.get("language") or "").strip()
        for result in results
        if str(result.get("language") or "").strip()
    })
    engine_versions = sorted({
        str(result.get("engine_version") or "").strip()
        for result in results
        if str(result.get("engine_version") or "").strip()
    })
    if ok:
        status = "ok"
    elif unavailable:
        status = "unavailable"
    elif statuses:
        status = "skipped"
    else:
        status = "not_run"
    return {
        "status": status,
        "engine": "spacy",
        "engine_version": engine_versions[0] if len(engine_versions) == 1 else "",
        "models": models,
        "languages": languages,
        "records_total": len(results),
        "records_annotated": len(ok),
        "records_unavailable": len(unavailable),
    }


def current_terms(record: dict[str, Any]) -> list[dict[str, Any]] | None:
    """The record's term layer if it was computed from the current text, else None."""
    data = record.get("nlp_candidates")
    if not isinstance(data, dict) or data.get("status") != "ok" or "terms" not in data:
        return None
    if data.get("text_sha256") != text_digest(str(record.get("text") or "")):
        return None
    return [item for item in data.get("terms") or [] if isinstance(item, dict)]

def current_field_candidates(
    record: dict[str, Any],
    field_names: list[str] | set[str] | tuple[str, ...] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Structured field candidates bound to the Record's current text digest.

    This exposes exact spans to deterministic candidate resolvers without reducing
    them to prompt-only strings. The returned dictionaries are copies so callers
    cannot mutate the rebuildable annotation projection in place.
    """
    data = record.get("nlp_candidates")
    if not isinstance(data, dict) or data.get("status") != "ok":
        return {}
    if data.get("text_sha256") != text_digest(str(record.get("text") or "")):
        return {}
    wanted = {str(name) for name in field_names} if field_names is not None else None
    fields = data.get("fields")
    if not isinstance(fields, dict):
        return {}
    return {
        str(name): [dict(item) for item in values if isinstance(item, dict)]
        for name, values in fields.items()
        if (wanted is None or str(name) in wanted) and isinstance(values, list) and values
    }

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
