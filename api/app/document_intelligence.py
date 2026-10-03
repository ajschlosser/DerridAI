# Copyright 2026 Aaron John Schlosser, PhD.
"""Provider-neutral whole-document linguistic intelligence for Corpus Builder.

Document intelligence is a derived, rebuildable projection.  It may suggest entity
identity, coreference clusters, quotation speakers, and other linguistic structure,
but it is never source evidence and never makes a FieldAssertion authoritative.

The module deliberately normalizes provider output into DerridAI-owned structures so
BookNLP, spaCy, or a future multilingual analyzer can be replaced without changing the
scholarly corpus contract.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from typing import Any
from urllib.parse import urlparse

from .corpus_document_context import record_fingerprint
from .nlp_annotations import language_code, load_pipeline

DOCUMENT_INTELLIGENCE_VERSION = 2
MAX_DOCUMENT_CHARS = 4_000_000
MAX_PROMPT_ENTITIES = 16
BOOKNLP_TIMEOUT_SECONDS = 900


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_entity_label(values: list[str]) -> str:
    cleaned = [re.sub(r"\s+", " ", str(value or "")).strip() for value in values]
    cleaned = [value for value in cleaned if value]
    if not cleaned:
        return ""
    counts = Counter(value.casefold() for value in cleaned)
    return max(
        cleaned,
        key=lambda value: (
            counts[value.casefold()],
            bool(re.search(r"\s", value)),
            len(value),
        ),
    )


def _entity_key(text: str, entity_type: str) -> str:
    normalized = re.sub(r"[^\w]+", " ", text.casefold(), flags=re.UNICODE).strip()
    return f"{entity_type}:{normalized}"


def document_text_for_records(
    records: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Return conserved record text plus a deterministic global/local offset map.

    The two-newline separator belongs to no Record.  Provider annotations that cross
    it are kept at document level but are not projected onto a Record.
    """
    pieces: list[str] = []
    spans: list[dict[str, Any]] = []
    cursor = 0
    for record in records:
        text = str(record.get("text") or "")
        if pieces:
            pieces.append("\n\n")
            cursor += 2
        start = cursor
        pieces.append(text)
        cursor += len(text)
        spans.append(
            {
                "record_id": str(record.get("record_id") or ""),
                "record_revision": int(record.get("record_revision") or 0),
                "start": start,
                "end": cursor,
                "text_sha256": _sha256(text),
                "source_fingerprint": record_fingerprint(record),
                "source_unit_ids": [
                    str(value)
                    for value in (
                        record.get("source_unit_ids")
                        or [
                            span.get("source_unit_id")
                            for span in (record.get("source_spans") or [])
                            if isinstance(span, dict) and span.get("source_unit_id")
                        ]
                    )
                    if value
                ],
            }
        )
    return "".join(pieces), spans


# spaCy covers every language (with a multilingual fallback); BookNLP only enhances
# English when its optional worker is configured, so Automatic is the default.
DEFAULT_DOCUMENT_NLP_PROVIDER = "auto"


def booknlp_url_for(code: str) -> str:
    """The BookNLP-contract worker configured for a language, or ``""`` when there is none.

    Each language routes to its own worker (``DOCUMENT_NLP_BASE_URL_FR`` and so on), so a
    French or German literary pipeline can serve the same normalized contract. The generic
    ``DOCUMENT_NLP_BASE_URL`` serves only the languages listed in ``DOCUMENT_NLP_LANGUAGES``
    (default ``en``, which is all upstream BookNLP models cover).
    """
    code = str(code or "").strip().lower()
    if not code:
        return ""
    specific = str(os.environ.get(f"DOCUMENT_NLP_BASE_URL_{code.upper()}") or "").strip()
    if specific:
        return specific
    languages = {
        item.strip().lower()
        for item in str(os.environ.get("DOCUMENT_NLP_LANGUAGES") or "en").split(",")
        if item.strip()
    }
    # A BookNLP pack an administrator installed for a language is served by the generic worker.
    from .document_nlp_packs import installed_languages

    languages |= installed_languages("booknlp")
    generic = str(os.environ.get("DOCUMENT_NLP_BASE_URL") or "").strip()
    return generic if code in languages else ""


def _call_booknlp(
    text: str,
    *,
    language: str,
    source_document_id: str,
    profile: str,
    include_events: bool,
    base_url: str,
) -> dict[str, Any]:
    parsed_base = urlparse(base_url)
    if parsed_base.scheme not in {"http", "https"} or not parsed_base.hostname:
        raise ValueError("Document NLP provider URL must use http or https.")
    url = base_url.rstrip("/") + "/analyze"
    payload = json.dumps(
        {
            "text": text,
            "language": language,
            "document_id": source_document_id,
            "profile": profile,
            "include_events": include_events,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(  # noqa: S310 - URL scheme/host validated above
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = max(
        30,
        min(
            3600,
            int(os.environ.get("DOCUMENT_NLP_TIMEOUT_SECONDS") or BOOKNLP_TIMEOUT_SECONDS),
        ),
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - validated HTTP(S) provider
        body = response.read(MAX_DOCUMENT_CHARS * 12 + 5_000_000)
    parsed = json.loads(body.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Document NLP provider returned a non-object response.")
    return parsed


def _spacy_document_annotations(text: str, language: str) -> dict[str, Any]:
    """Fallback whole-document NER.

    Exact normalized surface forms form conservative clusters.  This intentionally
    does not pretend to provide BookNLP-style pronominal coreference or quotation
    attribution.
    """
    code = language_code(language)
    if not code:
        return {
            "status": "unavailable",
            "provider": "spacy",
            "reason": "language_not_supported",
            "entities": [],
            "quotations": [],
            "characters": [],
        }
    pipeline = load_pipeline(code)
    if pipeline is None:
        return {
            "status": "unavailable",
            "provider": "spacy",
            "reason": "model_not_installed",
            "entities": [],
            "quotations": [],
            "characters": [],
        }
    # spaCy's default max_length is one million.  Raising this per document avoids
    # truncating a book while retaining DerridAI's own bounded input contract.
    if len(text) > int(getattr(pipeline, "max_length", 1_000_000)):
        pipeline.max_length = len(text) + 100
    doc = pipeline(text)
    grouped: dict[str, list[Any]] = defaultdict(list)
    for ent in doc.ents:
        entity_type = "PERSON" if ent.label_ == "PER" else str(ent.label_ or "")
        grouped[_entity_key(ent.text, entity_type)].append((ent, entity_type))
    entities: list[dict[str, Any]] = []
    clusters: dict[str, dict[str, Any]] = {}
    for index, values in enumerate(grouped.values(), start=1):
        labels = [str(ent.text) for ent, _ in values]
        cluster_id = f"spacy-{index}"
        canonical = _canonical_entity_label(labels)
        entity_type = values[0][1]
        clusters[cluster_id] = {
            "cluster_id": cluster_id,
            "canonical": canonical,
            "aliases": list(dict.fromkeys(labels)),
            "entity_type": entity_type,
        }
        for ent, _ in values:
            entities.append(
                {
                    "cluster_id": cluster_id,
                    "start_char": int(ent.start_char),
                    "end_char": int(ent.end_char),
                    "text": str(ent.text),
                    "mention_type": "named",
                    "entity_type": entity_type,
                }
            )
    return {
        "status": "ok",
        "provider": "spacy",
        "model": getattr(pipeline, "meta", {}).get("name") or "",
        "provider_version": getattr(pipeline, "meta", {}).get("version") or "",
        "capabilities": ["entities"],
        "entities": entities,
        "entity_clusters": list(clusters.values()),
        "quotations": [],
        "characters": [],
    }


def _normalize_provider_result(result: dict[str, Any]) -> dict[str, Any]:
    entities = [item for item in (result.get("entities") or []) if isinstance(item, dict)]
    quotations = [item for item in (result.get("quotations") or []) if isinstance(item, dict)]
    characters = [item for item in (result.get("characters") or []) if isinstance(item, dict)]

    aliases: dict[str, list[str]] = defaultdict(list)
    types: dict[str, str] = {}
    for item in entities:
        cluster_id = str(item.get("cluster_id") or "")
        text = str(item.get("text") or "").strip()
        if cluster_id and text:
            aliases[cluster_id].append(text)
        if cluster_id and item.get("entity_type"):
            types[cluster_id] = str(item.get("entity_type"))
    for character in characters:
        cluster_id = str(character.get("cluster_id") or "")
        values = character.get("aliases") if isinstance(character.get("aliases"), list) else []
        for value in values:
            if str(value or "").strip():
                aliases[cluster_id].append(str(value).strip())

    existing = {
        str(item.get("cluster_id") or ""): item
        for item in (result.get("entity_clusters") or [])
        if isinstance(item, dict) and item.get("cluster_id")
    }
    clusters: list[dict[str, Any]] = []
    for cluster_id in sorted(set(aliases) | set(existing)):
        source = existing.get(cluster_id, {})
        names = list(dict.fromkeys([*aliases.get(cluster_id, []), *(source.get("aliases") or [])]))
        clusters.append(
            {
                "cluster_id": cluster_id,
                "canonical": str(source.get("canonical") or "") or _canonical_entity_label(names),
                "aliases": names,
                "entity_type": str(source.get("entity_type") or types.get(cluster_id) or ""),
            }
        )

    normalized_entities: list[dict[str, Any]] = []
    for item in entities:
        try:
            start, end = int(item.get("start_char")), int(item.get("end_char"))
        except (TypeError, ValueError):
            continue
        if start < 0 or end <= start:
            continue
        normalized_entities.append(
            {
                "cluster_id": str(item.get("cluster_id") or ""),
                "start_char": start,
                "end_char": end,
                "text": str(item.get("text") or ""),
                "mention_type": str(item.get("mention_type") or ""),
                "entity_type": str(item.get("entity_type") or ""),
            }
        )

    normalized_quotes: list[dict[str, Any]] = []
    for item in quotations:
        try:
            start, end = int(item.get("start_char")), int(item.get("end_char"))
        except (TypeError, ValueError):
            continue
        if start < 0 or end <= start:
            continue
        normalized_quotes.append(
            {
                "start_char": start,
                "end_char": end,
                "text": str(item.get("text") or ""),
                "speaker_cluster_id": str(item.get("speaker_cluster_id") or ""),
                "speaker_text": str(item.get("speaker_text") or ""),
            }
        )

    return {
        **{
            key: value for key, value in result.items()
            if key not in {
                "version", "source_document_id", "text_sha256", "text_length", "record_spans",
                "profile", "selected_provider", "document_context_epoch", "analysis_id", "stale",
            }
        },
        "entities": normalized_entities,
        "entity_clusters": clusters,
        "quotations": normalized_quotes,
        "characters": characters,
    }


def analyze_document(
    records: list[dict[str, Any]],
    *,
    source_document_id: str,
    language: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    """Run the selected whole-document analyzer and return normalized annotations."""
    profile = str(request.get("document_intelligence_profile") or "scholarly")
    selected_provider = str(request.get("document_nlp_provider") or DEFAULT_DOCUMENT_NLP_PROVIDER)
    include_events = bool(request.get("document_nlp_include_events"))
    text, record_spans = document_text_for_records(records)
    run: dict[str, Any] = {
        "version": DOCUMENT_INTELLIGENCE_VERSION,
        "status": "skipped" if profile == "none" else "queued",
        "profile": profile,
        "selected_provider": selected_provider,
        "source_document_id": source_document_id,
        "text_sha256": _sha256(text),
        "text_length": len(text),
        "record_spans": record_spans,
        "entities": [],
        "entity_clusters": [],
        "quotations": [],
        "characters": [],
        "warnings": [],
    }
    if profile == "none":
        return run
    if not text.strip():
        run.update(status="skipped", reason="empty_document")
        return run
    if len(text) > MAX_DOCUMENT_CHARS:
        run.update(
            status="unavailable",
            reason="document_too_large",
            warnings=[f"Document intelligence is bounded to {MAX_DOCUMENT_CHARS} characters."],
        )
        return run

    code = language_code(language)
    # Provider endpoints are administrator/runtime configuration, not build-request
    # input. This avoids turning corpus requests into arbitrary server-side fetches.
    # Route on the language tag itself: a worker may serve a language no local
    # spaCy model covers (``language_code`` only knows the installed ones).
    tag = str(language or "").strip().lower().replace("_", "-").split("-")[0]
    route_code = code or (tag if re.fullmatch(r"[a-z]{2,3}", tag) else "")
    booknlp_url = booknlp_url_for(route_code)
    should_try_booknlp = selected_provider in {"auto", "booknlp"} and bool(booknlp_url)
    if selected_provider == "booknlp" and not should_try_booknlp:
        # An explicit BookNLP request must not silently become a spaCy run: the
        # reviewer asked for coreference/quotation attribution spaCy cannot give.
        any_worker = bool(str(os.environ.get("DOCUMENT_NLP_BASE_URL") or "").strip())
        reason = "language_unsupported" if any_worker else "provider_not_configured"
        run.update(status="unavailable", provider="booknlp", reason=reason)
        run["warnings"].append(
            f"No BookNLP worker is configured for language '{route_code or 'unknown'}'"
            f" (set DOCUMENT_NLP_BASE_URL_{(route_code or 'XX').upper()} to a worker for it)."
            if any_worker
            else "BookNLP was requested but DOCUMENT_NLP_BASE_URL is not configured on the API."
        )
        return run
    if should_try_booknlp:
        try:
            provider_result = _call_booknlp(
                text,
                language=route_code,
                source_document_id=source_document_id,
                profile=profile,
                include_events=include_events,
                base_url=booknlp_url,
            )
            normalized = _normalize_provider_result(provider_result)
            run.update(normalized)
            run.update(
                status="ok",
                provider="booknlp",
                capabilities=list(
                    normalized.get("capabilities")
                    or ["entities", "coreference", "quotations", "speaker_attribution"]
                ),
            )
            return run
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
            run["warnings"].append(f"BookNLP unavailable: {exc}")
            if selected_provider == "booknlp":
                run.update(status="unavailable", provider="booknlp", reason="provider_unavailable")
                return run

    fallback = _spacy_document_annotations(text, language)
    fallback = _normalize_provider_result(fallback)
    run.update(fallback)
    run["warnings"] = [*run.get("warnings", []), *(fallback.get("warnings") or [])]
    if fallback.get("status") == "ok":
        run["provider"] = "spacy"
    return run


def project_annotations_to_records(
    records: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> dict[str, int]:
    """Attach compact, hash-bound projections to intersecting Records."""
    text, current_spans = document_text_for_records(records)
    binding_fields = ("record_id", "start", "end", "text_sha256", "source_fingerprint")
    bound_spans = [
        {key: span.get(key) for key in binding_fields}
        for span in analysis.get("record_spans") or [] if isinstance(span, dict)
    ]
    expected_spans = [{key: span[key] for key in binding_fields} for span in current_spans]
    if analysis.get("stale") or (
        analysis.get("text_sha256") and analysis["text_sha256"] != _sha256(text)
    ) or (
        int(analysis.get("version") or 1) >= 2 and bound_spans != expected_spans
    ):
        analysis["stale"] = True
        for record in records:
            record.pop("document_intelligence", None)
        return {"entity_mentions": 0, "quotations": 0, "events": 0}
    spans = [
        item for item in (analysis.get("record_spans") or [])
        if isinstance(item, dict) and item.get("record_id")
    ]
    span_by_id = {str(item["record_id"]): item for item in spans}
    clusters = {
        str(item.get("cluster_id") or ""): item
        for item in (analysis.get("entity_clusters") or [])
        if isinstance(item, dict)
    }
    entities = [item for item in (analysis.get("entities") or []) if isinstance(item, dict)]
    quotations = [item for item in (analysis.get("quotations") or []) if isinstance(item, dict)]
    events = [item for item in (analysis.get("events") or []) if isinstance(item, dict)]
    entity_total = quote_total = event_total = 0

    for record in records:
        record_id = str(record.get("record_id") or "")
        mapped = span_by_id.get(record_id)
        if not mapped:
            record.pop("document_intelligence", None)
            continue
        start, end = int(mapped.get("start") or 0), int(mapped.get("end") or 0)
        local_entities: list[dict[str, Any]] = []
        for item in entities:
            item_start, item_end = int(item.get("start_char") or -1), int(item.get("end_char") or -1)
            if item_start < start or item_end > end:
                continue
            cluster = clusters.get(str(item.get("cluster_id") or ""), {})
            local_entities.append(
                {
                    "entity_id": str(item.get("cluster_id") or ""),
                    "label": str(cluster.get("canonical") or item.get("text") or ""),
                    "text": str(item.get("text") or ""),
                    "entity_type": str(item.get("entity_type") or cluster.get("entity_type") or ""),
                    "mention_type": str(item.get("mention_type") or ""),
                    "start": item_start - start,
                    "end": item_end - start,
                }
            )
        local_quotes: list[dict[str, Any]] = []
        for item in quotations:
            item_start, item_end = int(item.get("start_char") or -1), int(item.get("end_char") or -1)
            if item_start < start or item_end > end:
                continue
            speaker_id = str(item.get("speaker_cluster_id") or "")
            speaker_cluster = clusters.get(speaker_id, {})
            local_quotes.append(
                {
                    "start": item_start - start,
                    "end": item_end - start,
                    "speaker_entity_id": speaker_id,
                    "speaker": str(
                        speaker_cluster.get("canonical")
                        or item.get("speaker_text")
                        or ""
                    ),
                    "text": str(item.get("text") or ""),
                }
            )
        local_events: list[dict[str, Any]] = []
        for item in events:
            try:
                item_start = int(item.get("start_char"))
                item_end = int(item.get("end_char"))
            except (TypeError, ValueError):
                continue
            if item_start < start or item_end > end:
                continue
            local_events.append(
                {
                    "start": item_start - start,
                    "end": item_end - start,
                    "text": str(item.get("text") or ""),
                    "lemma": str(item.get("lemma") or ""),
                    "token_id": item.get("token_id"),
                }
            )
        entity_total += len(local_entities)
        quote_total += len(local_quotes)
        event_total += len(local_events)
        record["document_intelligence"] = {
            "version": DOCUMENT_INTELLIGENCE_VERSION,
            "document_sha256": analysis.get("text_sha256"),
            "document_context_epoch": analysis.get("document_context_epoch"),
            "analysis_id": analysis.get("analysis_id"),
            "record_text_sha256": _sha256(str(record.get("text") or "")),
            "record_source_fingerprint": record_fingerprint(record),
            "provider": analysis.get("provider"),
            "provider_version": analysis.get("provider_version"),
            "model": analysis.get("model"),
            "profile": analysis.get("profile"),
            "status": analysis.get("status"),
            "entities": local_entities,
            "quotations": local_quotes,
            "events": local_events,
        }
    return {
        "entity_mentions": entity_total,
        "quotations": quote_total,
        "events": event_total,
    }



def record_annotations_current(record: dict[str, Any]) -> bool:
    data = record.get("document_intelligence")
    if not isinstance(data, dict) or data.get("stale"):
        return False
    if data.get("record_text_sha256") != _sha256(str(record.get("text") or "")):
        return False
    return (
        int(data.get("version") or 1) < 2
        or data.get("record_source_fingerprint") == record_fingerprint(record)
    )


def current_quotations(record: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Current Record quotation projections, or None when unavailable/stale.

    This is a routing signal only. Document Intelligence is derived advisory state,
    not source evidence and not a metadata assertion.
    """
    data = record.get("document_intelligence")
    if not isinstance(data, dict) or data.get("status") != "ok":
        return None
    if not record_annotations_current(record):
        return None
    return [item for item in (data.get("quotations") or []) if isinstance(item, dict)]


def prompt_hints(record: dict[str, Any], field_names: list[str]) -> dict[str, Any]:
    """Small candidate packet for metadata prompts; never evidence."""
    data = record.get("document_intelligence")
    if not isinstance(data, dict) or data.get("status") != "ok":
        return {}
    if not record_annotations_current(record):
        return {}
    entities = [
        item for item in (data.get("entities") or [])
        if isinstance(item, dict) and item.get("label")
    ]
    persons = list(
        dict.fromkeys(
            str(item["label"])
            for item in entities
            if str(item.get("entity_type") or "").upper() in {"PER", "PERSON"}
        )
    )[:MAX_PROMPT_ENTITIES]
    all_entities = list(dict.fromkeys(str(item["label"]) for item in entities))[:MAX_PROMPT_ENTITIES]
    quote_speakers = list(
        dict.fromkeys(
            str(item.get("speaker") or "")
            for item in (data.get("quotations") or [])
            if isinstance(item, dict) and str(item.get("speaker") or "").strip()
        )
    )[:MAX_PROMPT_ENTITIES]
    result: dict[str, Any] = {}
    fields = set(field_names)
    if persons and fields & {
        "persons", "speaker", "position_holder", "target", "quoted_speaker",
        "quoted_author", "quoted_position_holder", "quoted_addressee",
    }:
        result["person_candidates"] = persons
    if quote_speakers and fields & {
        "quoted_speaker", "quoted_author", "quoted_position_holder", "speaker",
    }:
        result["quotation_speaker_candidates"] = quote_speakers
    if all_entities and fields & {"target", "quoted_referent", "persons"}:
        result["entity_candidates"] = all_entities
    return result
