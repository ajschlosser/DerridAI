# Copyright 2026 Aaron John Schlosser, PhD.
"""Wikidata person resolution and work/edition identity lookup for Corpus Capture.

Only supported Wikibase APIs are used (``wbsearchentities``, ``wbgetentities`` and
CirrusSearch ``haswbstatement``). The user always chooses the person; nothing here
picks one of several matches, and no model is consulted.
"""
from __future__ import annotations

import re
from typing import Any

from .source_identity import AuthorCandidate, CaptureError, CaptureErrorCode, ResolvedAuthor, SourceCandidate
from .source_provider import ProviderHttp

API = "https://www.wikidata.org/w/api.php"
HUMAN = "Q5"
_QID = re.compile(r"^Q[1-9]\d{0,11}$")
# External identifiers worth keeping on the resolved person (property → name).
EXTERNAL_IDS = {"P1938": "gutenberg_author", "P214": "viaf", "P244": "loc", "P227": "gnd", "P268": "bnf"}
# Wikidata properties for bibliographic relationships.
P_INSTANCE, P_AUTHOR, P_LANGUAGE, P_TRANSLATOR, P_EDITION_OF, P_PUBLISHED, P_PUBLISHER = (
    "P31", "P50", "P407", "P655", "P629", "P577", "P123",
)
P_GUTENBERG_EBOOK = "P2034"


def valid_qid(value: str) -> bool:
    return bool(_QID.match(str(value or "")))


def _claim_values(entity: dict[str, Any], prop: str) -> list[Any]:
    values = []
    for claim in (entity.get("claims") or {}).get(prop) or []:
        snak = claim.get("mainsnak") or {}
        if snak.get("snaktype") != "value":
            continue
        value = (snak.get("datavalue") or {}).get("value")
        if isinstance(value, dict) and "id" in value:
            values.append(str(value["id"]))
        elif isinstance(value, dict) and "time" in value:
            values.append(str(value["time"]))
        elif value is not None:
            values.append(value)
    return values


def _year(time_value: str | None) -> int | None:
    match = re.match(r"^([+-])(\d{1,6})-", str(time_value or ""))
    if not match:
        return None
    year = int(match.group(2))
    return -year if match.group(1) == "-" else year


def _label(entity: dict[str, Any], languages: list[str], kind: str = "labels") -> str:
    values = entity.get(kind) or {}
    for code in [*languages, "en", "mul"]:
        if code in values:
            return str(values[code].get("value") or "")
    first = next(iter(values.values()), None)
    return str(first.get("value") or "") if isinstance(first, dict) else ""


def wikisource_sitelinks(entity: dict[str, Any]) -> dict[str, str]:
    """Wikisource project code → author page title, from the person's sitelinks."""
    out: dict[str, str] = {}
    for site, link in (entity.get("sitelinks") or {}).items():
        title = str((link or {}).get("title") or "")
        if not title:
            continue
        if site == "sourceswiki":
            out["mul"] = title
        elif site.endswith("wikisource"):
            code = site[: -len("wikisource")].replace("_", "-")
            if re.fullmatch(r"[a-z][a-z0-9-]{1,15}", code):
                out[code] = title
    return out


def author_candidate(entity: dict[str, Any], languages: list[str]) -> AuthorCandidate:
    aliases: list[str] = []
    for code in [*languages, "en", "de", "fr"]:
        for alias in (entity.get("aliases") or {}).get(code) or []:
            if alias.get("value") and alias["value"] not in aliases:
                aliases.append(str(alias["value"]))
    for label in (entity.get("labels") or {}).values():
        value = str(label.get("value") or "")
        if value and value not in aliases:
            aliases.append(value)
    label = _label(entity, languages)
    return AuthorCandidate(
        wikidata_qid=str(entity.get("id")),
        label=label,
        description=_label(entity, languages, "descriptions"),
        aliases=[alias for alias in aliases if alias != label][:40],
        birth_year=_year(next(iter(_claim_values(entity, "P569")), None)),
        death_year=_year(next(iter(_claim_values(entity, "P570")), None)),
        wikisource_sitelinks=wikisource_sitelinks(entity),
    )


def get_entities(http: ProviderHttp, ids: list[str], *, props: str, languages: list[str] | None = None) -> dict[str, dict[str, Any]]:
    """Batched ``wbgetentities`` (50 ids per call, the API's limit)."""
    found: dict[str, dict[str, Any]] = {}
    wanted = [qid for qid in dict.fromkeys(ids) if valid_qid(qid)]
    for start in range(0, len(wanted), 50):
        http.check_cancelled()
        params: dict[str, Any] = {"action": "wbgetentities", "ids": "|".join(wanted[start : start + 50]), "props": props, "format": "json", "formatversion": 2}
        if languages:
            params["languages"] = "|".join(dict.fromkeys([*languages, "en", "mul"]))
            params["languagefallback"] = 1
        payload = http.get_json(API, params)
        for qid, entity in (payload.get("entities") or {}).items():
            if isinstance(entity, dict) and "missing" not in entity:
                found[str(qid)] = entity
    return found


def search_authors(http: ProviderHttp, query: str, *, language: str = "en", limit: int = 10) -> list[AuthorCandidate]:
    """People matching ``query``. Non-humans (paintings, ships, works) are filtered out by P31=Q5."""
    text = str(query or "").strip()
    if not text:
        return []
    ui = (language or "en").split("-", 1)[0].lower()
    payload = http.get_json(API, {"action": "wbsearchentities", "search": text, "language": ui, "uselang": ui, "type": "item", "limit": max(1, min(20, limit * 2)), "format": "json", "formatversion": 2})
    ids = [str(item.get("id")) for item in payload.get("search") or [] if isinstance(item, dict)]
    entities = get_entities(http, ids, props="labels|descriptions|aliases|claims|sitelinks", languages=[ui])
    people = [author_candidate(entities[qid], [ui]) for qid in ids if qid in entities and HUMAN in _claim_values(entities[qid], P_INSTANCE)]
    return people[:limit]


def resolve_author(http: ProviderHttp, qid: str, *, language: str = "en") -> ResolvedAuthor:
    if not valid_qid(qid):
        raise CaptureError(CaptureErrorCode.AUTHOR_NOT_FOUND, "Choose a person from the search results.")
    ui = (language or "en").split("-", 1)[0].lower()
    entity = get_entities(http, [qid], props="labels|descriptions|aliases|claims|sitelinks", languages=[ui]).get(qid)
    if entity is None:
        raise CaptureError(CaptureErrorCode.AUTHOR_NOT_FOUND, "Wikidata has no such person.")
    if HUMAN not in _claim_values(entity, P_INSTANCE):
        raise CaptureError(CaptureErrorCode.IDENTITY_MISMATCH, "The chosen Wikidata item is not a person.")
    candidate = author_candidate(entity, [ui])
    external = {name: str(values[0]) for prop, name in EXTERNAL_IDS.items() if (values := _claim_values(entity, prop))}
    return ResolvedAuthor(
        identity_id=f"wikidata:{qid}",
        canonical_name=candidate.label,
        wikidata_qid=qid,
        aliases=candidate.aliases,
        description=candidate.description,
        birth_year=candidate.birth_year,
        death_year=candidate.death_year,
        external_ids=external,
        wikisource_sitelinks=candidate.wikisource_sitelinks,
    )


def gutenberg_edition_items(http: ProviderHttp, etext_ids: list[str]) -> dict[str, str]:
    """Project Gutenberg eBook id → Wikidata edition item, through P2034 (batched OR queries)."""
    out: dict[str, str] = {}
    ids = [value for value in dict.fromkeys(etext_ids) if str(value).isdigit()]
    for start in range(0, len(ids), 25):
        http.check_cancelled()
        chunk = ids[start : start + 25]
        query = "haswbstatement:" + "|".join(f"{P_GUTENBERG_EBOOK}={value}" for value in chunk)
        try:
            payload = http.get_json(API, {"action": "query", "list": "search", "srsearch": query, "srlimit": 50, "srprop": "", "format": "json", "formatversion": 2})
        except CaptureError as exc:
            if exc.code == CaptureErrorCode.CANCELLED:
                raise
            continue
        qids = [str(item.get("title")) for item in (payload.get("query") or {}).get("search") or []]
        entities = get_entities(http, qids, props="claims")
        for qid, entity in entities.items():
            for value in _claim_values(entity, P_GUTENBERG_EBOOK):
                if str(value) in chunk:
                    out.setdefault(str(value), qid)
    return out


def language_codes(http: ProviderHttp, language_items: list[str]) -> dict[str, str]:
    """Wikidata language item → BCP 47-style code, via P305 (IETF tag) then P218 (ISO 639-1)."""
    entities = get_entities(http, language_items, props="claims")
    out: dict[str, str] = {}
    for qid, entity in entities.items():
        code = next(iter(_claim_values(entity, "P305")), None) or next(iter(_claim_values(entity, "P218")), None)
        if code:
            out[qid] = str(code).lower()
    return out


def apply_work_identities(http: ProviderHttp, candidates: list[SourceCandidate], author_qid: str | None) -> None:
    """Fill work/edition ids, original language, and relationship from Wikidata statements only.

    * An item with P629 (edition or translation of) is an edition; its target is the canonical work.
    * An item without P629 is treated as the work itself.
    * The relationship is ``translation`` only when both the work's language and the edition's
      language are stated and differ; ``original_language_edition`` when they agree. Otherwise unknown.
    * If the work or edition names authors (P50) and the resolved person is not among them, the
      candidate is flagged ``identity_mismatch`` for review rather than silently kept or dropped.
    """
    items = [c.wikidata_edition_id for c in candidates if c.wikidata_edition_id]
    if not items:
        return
    editions = get_entities(http, items, props="claims")
    works_needed = [value for entity in editions.values() for value in _claim_values(entity, P_EDITION_OF)[:1]]
    works = get_entities(http, works_needed, props="claims") if works_needed else {}
    language_items = {
        value for entity in [*editions.values(), *works.values()] for value in _claim_values(entity, P_LANGUAGE)
    }
    codes = language_codes(http, sorted(language_items)) if language_items else {}
    for candidate in candidates:
        edition = editions.get(str(candidate.wikidata_edition_id or ""))
        if edition is None:
            continue
        work_id = next(iter(_claim_values(edition, P_EDITION_OF)), None)
        work = works.get(str(work_id)) if work_id else edition
        if work_id:
            candidate.wikidata_work_id = str(work_id)
        else:
            candidate.wikidata_work_id = candidate.wikidata_edition_id
            candidate.wikidata_edition_id = None
        work = work or {}
        original = [codes[q] for q in _claim_values(work, P_LANGUAGE) if q in codes]
        edition_langs = [codes[q] for q in _claim_values(edition, P_LANGUAGE) if q in codes]
        if len(original) == 1:
            candidate.original_language = original[0]
        doc = edition_langs or candidate.document_languages
        if candidate.original_language and doc:
            candidate.relationship_to_work = "original_language_edition" if candidate.original_language in doc else "translation"
        year = _year(next(iter(_claim_values(edition, P_PUBLISHED)), None))
        if year is not None and candidate.publication_year is None:
            candidate.publication_year = year
        authors = set(_claim_values(work, P_AUTHOR)) | set(_claim_values(edition, P_AUTHOR))
        if author_qid and authors and author_qid not in authors:
            candidate.identity_confidence = "needs_review"
            candidate.discovery_evidence = {**candidate.discovery_evidence, "identity_mismatch": sorted(authors)}
