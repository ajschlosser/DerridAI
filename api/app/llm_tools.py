from __future__ import annotations

from typing import Any, Callable
import copy
import json
import re
import unicodedata

import httpx
from datetime import datetime, timezone

from .chroma_store import ChromaStore
from .config import settings
from .models import PdfLlmRequest, RAGGradeRequest, WorkMetadataRequest, WorkMetadataSeed
from .rag import _extract_json, chat_complete


def _model_for(provider: str, model: str | None) -> str:
    return model or (
        settings.openai_compat_model
        if provider == "openai"
        else settings.ollama_model
    )


def run_pdf_llm(
    body: PdfLlmRequest,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    model = _model_for(body.provider, body.model)
    source = (
        f"PDF file: {body.pdf_file or ''}\n"
        f"PDF title: {body.pdf_title or ''}\n"
        f"PDF author: {body.pdf_author or ''}\n"
        f"PDF page: {body.pdf_page or ''}\n"
    )

    if body.mode == "clean_text":
        if not body.raw_text.strip():
            raise ValueError("No extractable PDF text is available to clean.")
        prompt = f"""Clean the following PDF text extraction conservatively.

{source}

TEXT:
{body.raw_text}

Return only cleaned source text. Preserve wording, punctuation, quotations,
paragraph order, capitalization, philosophical terminology, foreign-language
text, and meaningful line breaks. Repair only obvious extraction artifacts.
Do not paraphrase, summarize, translate, modernize, or add missing prose."""
        cleaned = chat_complete(
            provider=body.provider, model=model, base_url=body.base_url,
            api_key=body.api_key, prompt=prompt, options=body.generation,
            json_mode=False,
            max_tokens=(body.generation.num_predict if body.generation and body.generation.num_predict else 8192),
            cancelled=cancelled,
        )
        return {"mode": body.mode, "text": cleaned, "model": model}

    if body.mode == "draft_record":
        if not body.raw_text.strip():
            raise ValueError("No extractable PDF text is available for draft-record creation.")
        prompt = f"""Create a DRAFT DerridAI corpus record from this source page.

{source}

SOURCE TEXT:
{body.raw_text}

Return exactly one JSON object. Populate only source-supported fields.
Preserve quotation provenance and flat corpus fields. text must preserve the
cleaned source text rather than summarize it. Set needs_review=true,
updates=[], and use supplied PDF context. Do not invent edition/year/citation data."""
        raw = chat_complete(
            provider=body.provider, model=model, base_url=body.base_url,
            api_key=body.api_key, prompt=prompt, options=body.generation,
            json_mode=True,
            max_tokens=(body.generation.num_predict if body.generation and body.generation.num_predict else 8192),
            cancelled=cancelled,
        )
        record = _extract_json(raw)
        record["text"] = str(record.get("text") or body.raw_text)
        record["text_length"] = len(record["text"])
        record["needs_review"] = True
        record["review_reason"] = record.get("review_reason") or "Draft record generated from PDF page by LLM."
        if body.pdf_file:
            record["pdf_file"] = body.pdf_file
        if body.pdf_page:
            record["pdf_pages"] = [body.pdf_page]
        record["updates"] = []
        return {"mode": body.mode, "record": record, "model": model}

    # Linking is a ranking task, not a bulk export. Build the provider prompt
    # against the configured context window instead of sending a fixed-size
    # candidate packet. This is especially important for 4k/8k Ollama models,
    # where an oversized request is rejected upstream as HTTP 400.
    candidates = body.candidates[:48]
    if not candidates:
        raise ValueError("No candidate records were supplied.")

    configured_ctx = (
        int(body.generation.num_ctx)
        if body.generation and body.generation.num_ctx
        else 16384
    )
    # A conservative characters/token estimate plus headroom for instructions
    # and the JSON answer. The hard ceiling also keeps large-context models from
    # making this small ranking task needlessly expensive.
    input_char_budget = max(8000, min(40000, int(configured_ctx * 2.6)))
    page_char_budget = min(12000, max(3500, int(input_char_budget * 0.42)))
    page_text = body.raw_text[:page_char_budget]

    candidate_budget = max(3500, input_char_budget - len(page_text) - 2500)
    candidate_blocks: list[str] = []
    candidate_chars = 0
    retained_candidates: list[dict[str, Any]] = []
    for item in candidates:
        block = (
            f"KEY={item.get('key','')}\nrecord_id={item.get('record_id','')}\n"
            f"work={item.get('work','')}\npages={item.get('pages','')}\n"
            f"citation={item.get('citation','')}\n"
            f"text={str(item.get('text',''))[:600]}"
        )
        block_cost = len(block) + 2
        if retained_candidates and candidate_chars + block_cost > candidate_budget:
            break
        candidate_blocks.append(block)
        retained_candidates.append(item)
        candidate_chars += block_cost

    # Always retain the strongest pre-ranked candidate even at tiny contexts.
    if not retained_candidates:
        retained_candidates = [candidates[0]]
        item = candidates[0]
        candidate_blocks = [
            f"KEY={item.get('key','')}\nrecord_id={item.get('record_id','')}\n"
            f"work={item.get('work','')}\npages={item.get('pages','')}\n"
            f"citation={item.get('citation','')}\n"
            f"text={str(item.get('text',''))[:400]}"
        ]
    candidate_text = "\n\n".join(candidate_blocks)

    prompt = f"""Match this PDF page to one existing corpus record.

{source}

PDF PAGE TEXT:
{page_text}

CANDIDATE RECORDS:
{candidate_text}

Return exactly one JSON object:
{{"key":"candidate KEY or empty string","record_id":"matched record ID or empty string","confidence":0.0,"reason":"short explanation"}}
Prefer exact page/citation/work/text correspondence. Do not choose a record
merely because it discusses the same concept. Return empty IDs if unsupported."""
    raw = chat_complete(
        provider=body.provider, model=model, base_url=body.base_url,
        api_key=body.api_key, prompt=prompt, options=body.generation,
        json_mode=True, max_tokens=768, cancelled=cancelled,
    )
    match = _extract_json(raw)
    valid_keys = {str(item.get("key") or "") for item in retained_candidates}
    if str(match.get("key") or "") not in valid_keys:
        match["key"] = ""
        match["record_id"] = ""
    return {"mode": body.mode, "match": match, "model": model}




def _catalog_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        value = value.get("name") or value.get("title") or value.get("value") or ""
    return str(value).strip()


def _first_catalog_value(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            text = _catalog_text(item)
            if text:
                return text
        return ""
    return _catalog_text(value)


def _normalize_catalog_match(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _year_from_publish_date(value: Any) -> int | None:
    text = _first_catalog_value(value)
    match = re.search(r"\b(1[5-9]\d{2}|20\d{2}|2100)\b", text)
    return int(match.group(1)) if match else None


def _language_code(value: Any) -> str:
    key = _catalog_text(value)
    token = key.rsplit("/", 1)[-1].lower()
    return {
        "eng": "en", "en": "en", "fre": "fr", "fra": "fr", "fr": "fr",
        "ger": "de", "deu": "de", "de": "de", "spa": "es", "es": "es",
        "ita": "it", "it": "it", "por": "pt", "pt": "pt",
    }.get(token, token)


def _edition_translator(entry: dict[str, Any]) -> str:
    names: list[str] = []
    for item in entry.get("contributors") or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").casefold()
        if "translat" not in role:
            continue
        name = _catalog_text(item.get("name"))
        if name and name not in names:
            names.append(name)
    return ", ".join(names)


from .bibliography import _mla_citation, _mla_book_citation

def _edition_metadata(
    *,
    doc: dict[str, Any],
    edition: dict[str, Any] | None,
    author: str,
) -> dict[str, Any]:
    edition = edition or {}
    title = _catalog_text(edition.get("title")) or _catalog_text(doc.get("title"))
    publishers = edition.get("publishers") or doc.get("publisher") or []
    places = edition.get("publish_places") or []
    translator = _edition_translator(edition)
    year = _year_from_publish_date(edition.get("publish_date"))
    if year is None:
        years = doc.get("publish_year") or []
        if isinstance(years, list) and years:
            try:
                year = int(sorted(int(v) for v in years if str(v).isdigit())[-1])
            except Exception:
                year = None
    if year is None:
        try:
            year = int(doc.get("first_publish_year")) if doc.get("first_publish_year") else None
        except Exception:
            year = None
    isbn = _first_catalog_value(edition.get("isbn_13")) or _first_catalog_value(edition.get("isbn_10")) or _first_catalog_value(doc.get("isbn"))
    edition_name = _catalog_text(edition.get("edition_name"))
    languages = edition.get("languages") or []
    language = _language_code(languages[0]) if languages else _language_code((doc.get("language") or [""])[0] if isinstance(doc.get("language"), list) else doc.get("language"))
    covers = edition.get("covers") or []
    cover_id = None
    if covers:
        try:
            cover_id = int(covers[0])
        except Exception:
            cover_id = None
    if not cover_id and doc.get("cover_i"):
        try:
            cover_id = int(doc.get("cover_i"))
        except Exception:
            cover_id = None
    work_key = _catalog_text(doc.get("key"))
    edition_key = _catalog_text(edition.get("key"))
    publisher = _first_catalog_value(publishers)
    place = _first_catalog_value(places)
    full_citation = _mla_book_citation(
        author=author,
        title=title,
        translator=translator,
        edition=edition_name,
        publisher=publisher,
        year=year,
    )
    return {
        "source_type": "book",
        "document_type": "book",
        "document_title": title or None,
        "short_title": title or None,
        "document_author": author or None,
        "edition": edition_name or None,
        "year": year,
        "publication_year": year,
        "publisher": publisher or None,
        "publication_place": place or None,
        "translator": translator or None,
        "document_language": language or None,
        "document_is_translation": True if translator else None,
        "isbn": isbn or None,
        "full_citation": full_citation or None,
        "cover_url": f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None,
        "_openlibrary_work_key": work_key or None,
        "_openlibrary_edition_key": edition_key or None,
    }


def _score_catalog_doc(seed: WorkMetadataSeed, doc: dict[str, Any]) -> int:
    current = seed.current_metadata or {}
    wanted_title = _normalize_catalog_match(current.get("document_title") or current.get("work") or seed.work)
    title = _normalize_catalog_match(doc.get("title"))
    score = 0
    if wanted_title and title == wanted_title:
        score += 12
    elif wanted_title and (wanted_title in title or title in wanted_title):
        score += 7
    wanted_author = _normalize_catalog_match(current.get("document_author"))
    authors = _normalize_catalog_match(" ".join(doc.get("author_name") or []))
    if wanted_author and wanted_author in authors:
        score += 7
    wanted_isbn = re.sub(r"[^0-9Xx]", "", str(current.get("isbn") or ""))
    if wanted_isbn:
        doc_isbns = {re.sub(r"[^0-9Xx]", "", str(v)) for v in (doc.get("isbn") or [])}
        if wanted_isbn in doc_isbns:
            score += 20
    wanted_year = str(current.get("publication_year") or current.get("year") or "")
    if wanted_year and wanted_year in {str(v) for v in (doc.get("publish_year") or [])}:
        score += 5
    wanted_publisher = _normalize_catalog_match(current.get("publisher"))
    pubs = _normalize_catalog_match(" ".join(doc.get("publisher") or []))
    if wanted_publisher and wanted_publisher in pubs:
        score += 4
    if doc.get("cover_i"):
        score += 1
    return score


def _score_catalog_edition(current: dict[str, Any], edition: dict[str, Any]) -> int:
    score = 0
    wanted_isbn = re.sub(r"[^0-9Xx]", "", str(current.get("isbn") or ""))
    if wanted_isbn:
        edition_isbns = {
            re.sub(r"[^0-9Xx]", "", str(v))
            for v in [*(edition.get("isbn_10") or []), *(edition.get("isbn_13") or [])]
        }
        if wanted_isbn in edition_isbns:
            score += 30
    wanted_year = str(current.get("publication_year") or current.get("year") or "")
    year = _year_from_publish_date(edition.get("publish_date"))
    if wanted_year and year and wanted_year == str(year):
        score += 10
    wanted_publisher = _normalize_catalog_match(current.get("publisher"))
    publishers = _normalize_catalog_match(" ".join(_catalog_text(v) for v in edition.get("publishers") or []))
    if wanted_publisher and wanted_publisher in publishers:
        score += 8
    wanted_translator = _normalize_catalog_match(current.get("translator"))
    translator = _normalize_catalog_match(_edition_translator(edition))
    if wanted_translator and wanted_translator in translator:
        score += 8
    if edition.get("covers"):
        score += 2
    return score


def _openlibrary_candidates(seed: WorkMetadataSeed) -> list[dict[str, Any]]:
    current = seed.current_metadata or {}
    query_parts = [seed.work, current.get("document_author")]
    query = " ".join(str(value).strip() for value in query_parts if str(value or "").strip())
    fields = "key,title,author_name,first_publish_year,publisher,publish_year,isbn,language,cover_i,edition_key"
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        response = client.get("https://openlibrary.org/search.json", params={"q": query, "limit": 8, "fields": fields})
        response.raise_for_status()
        docs = list((response.json() or {}).get("docs") or [])
        docs.sort(key=lambda doc: _score_catalog_doc(seed, doc), reverse=True)
        candidates: list[dict[str, Any]] = []
        for doc in docs[:4]:
            work_key = _catalog_text(doc.get("key"))
            editions: list[dict[str, Any]] = []
            if work_key:
                try:
                    edition_response = client.get(f"https://openlibrary.org{work_key}/editions.json", params={"limit": 30})
                    edition_response.raise_for_status()
                    editions = list((edition_response.json() or {}).get("entries") or [])
                except httpx.HTTPError:
                    editions = []
            editions.sort(key=lambda item: _score_catalog_edition(current, item), reverse=True)
            author = ", ".join(str(v).strip() for v in doc.get("author_name") or [] if str(v).strip())
            if editions:
                for edition in editions[:3]:
                    candidates.append(_edition_metadata(doc=doc, edition=edition, author=author))
            else:
                candidates.append(_edition_metadata(doc=doc, edition=None, author=author))
        return candidates[:10]


def _crossref_candidates(seed: WorkMetadataSeed) -> list[dict[str, Any]]:
    current = seed.current_metadata or {}
    query = str(current.get("document_title") or seed.work).strip()
    author = str(current.get("document_author") or "").strip()
    params = {"query.bibliographic": query, "rows": 8}
    if author:
        params["query.author"] = author
    with httpx.Client(timeout=20.0, follow_redirects=True, headers={"User-Agent": "DerridAI/0.48.1 (bibliographic metadata lookup)"}) as client:
        response = client.get("https://api.crossref.org/works", params=params)
        response.raise_for_status()
        items = list((((response.json() or {}).get("message") or {}).get("items") or []))
    out: list[dict[str, Any]] = []
    for item in items:
        title = _first_catalog_value(item.get("title"))
        container = _first_catalog_value(item.get("container-title"))
        authors = []
        for person in item.get("author") or []:
            if isinstance(person, dict):
                name = " ".join(str(person.get(k) or "").strip() for k in ("given", "family") if str(person.get(k) or "").strip())
                if name: authors.append(name)
        issued = (((item.get("issued") or {}).get("date-parts") or [[None]])[0] or [None])[0]
        kind = str(item.get("type") or "").casefold()
        source_type = "journal_article" if "journal" in kind else "book_chapter" if kind in {"book-chapter", "reference-entry"} else "book" if kind in {"book", "monograph", "edited-book"} else kind.replace("-", "_") or "article"
        metadata = {
            "source_type": source_type,
            "document_type": source_type,
            "document_title": title or None,
            "short_title": title or None,
            "document_author": ", ".join(authors) or None,
            "container_title": container or None,
            "journal_title": (container or None) if source_type == "journal_article" else None,
            "publisher": _catalog_text(item.get("publisher")) or None,
            "publication_year": issued,
            "year": issued,
            "volume": _catalog_text(item.get("volume")) or None,
            "issue": _catalog_text(item.get("issue")) or None,
            "pages": _catalog_text(item.get("page")) or None,
            "doi": _catalog_text(item.get("DOI")) or None,
            "url": _catalog_text(item.get("URL")) or None,
            "isbn": _first_catalog_value(item.get("ISBN")) or None,
        }
        metadata["full_citation"] = _mla_citation(metadata) or None
        metadata["_catalog_source"] = "Crossref"
        out.append(metadata)
    return out


def _google_books_candidates(seed: WorkMetadataSeed) -> list[dict[str, Any]]:
    current = seed.current_metadata or {}
    query = str(current.get("document_title") or seed.work).strip()
    author = str(current.get("document_author") or "").strip()
    q = f'intitle:"{query}"' + (f'+inauthor:"{author}"' if author else "")
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        response = client.get("https://www.googleapis.com/books/v1/volumes", params={"q": q, "maxResults": 8, "printType": "books"})
        response.raise_for_status()
        items = list((response.json() or {}).get("items") or [])
    out: list[dict[str, Any]] = []
    for item in items:
        info = item.get("volumeInfo") or {}
        year = _year_from_publish_date(info.get("publishedDate"))
        identifiers = {str(x.get("type") or ""): str(x.get("identifier") or "") for x in info.get("industryIdentifiers") or [] if isinstance(x, dict)}
        metadata = {
            "source_type": "book", "document_type": "book",
            "document_title": _catalog_text(info.get("title")) or None,
            "short_title": _catalog_text(info.get("title")) or None,
            "document_author": ", ".join(str(v).strip() for v in info.get("authors") or [] if str(v).strip()) or None,
            "publisher": _catalog_text(info.get("publisher")) or None,
            "publication_year": year, "year": year,
            "document_language": _catalog_text(info.get("language")) or None,
            "isbn": identifiers.get("ISBN_13") or identifiers.get("ISBN_10") or None,
            "cover_url": ((info.get("imageLinks") or {}).get("thumbnail") or (info.get("imageLinks") or {}).get("smallThumbnail")),
            "url": _catalog_text(info.get("infoLink")) or None,
            "_catalog_source": "Google Books",
        }
        metadata["full_citation"] = _mla_citation(metadata) or None
        out.append(metadata)
    return out


def _multi_catalog_candidates(seed: WorkMetadataSeed) -> tuple[list[dict[str, Any]], list[str]]:
    """Try format-appropriate bibliographic sources instead of stopping at Open Library."""
    current = seed.current_metadata or {}
    source_type = str(current.get("source_type") or current.get("document_type") or "").casefold()
    attempted_sources: list[str] = []
    result_sources: list[str] = []
    candidates: list[dict[str, Any]] = []
    lookups = []
    if any(token in source_type for token in ("article", "journal", "chapter")):
        lookups = [("Crossref", _crossref_candidates), ("Open Library", _openlibrary_candidates), ("Google Books", _google_books_candidates)]
    else:
        lookups = [("Open Library", _openlibrary_candidates), ("Google Books", _google_books_candidates), ("Crossref", _crossref_candidates)]
    for name, lookup in lookups:
        attempted_sources.append(name)
        try:
            found = lookup(seed)
        except httpx.HTTPError:
            found = []
        if found:
            result_sources.append(name)
            for item in found:
                item = dict(item)
                item.setdefault("_catalog_source", name)
                candidates.append(item)
        # Always consult at least two catalogue families. If neither gives a
        # useful candidate pool, continue to the third rather than treating a
        # noisy Open Library title match as authoritative.
        if len(attempted_sources) >= 2 and len(candidates) >= 8:
            break
    # Keep the attempted-source list for audit even when a service returned no
    # result; callers can separately infer result sources from candidate provenance.
    return candidates[:16], attempted_sources


def _candidate_public(candidate: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in candidate.items() if not key.startswith("_") and value not in (None, "", [])}


def run_work_metadata_lookup(
    seed: WorkMetadataSeed,
    request: WorkMetadataRequest,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    if cancelled and cancelled():
        raise InterruptedError()
    candidates, catalog_sources = _multi_catalog_candidates(seed)
    if cancelled and cancelled():
        raise InterruptedError()
    if not candidates:
        return {
            "work": seed.work,
            "current_metadata": seed.current_metadata,
            "changes": {},
            "rationale": {},
            "catalog_source": ", ".join(catalog_sources) or "Open Library / Google Books / Crossref",
            "message": "No matching bibliographic catalogue result was found across the configured public catalogues.",
        }

    compact = [_candidate_public(item) for item in candidates]
    model = _model_for(request.provider, request.model)
    prompt = f"""You are matching a DerridAI work to bibliographic catalogue records.

WORK LABEL:
{seed.work}

CURRENT METADATA:
{json.dumps(seed.current_metadata or {}, ensure_ascii=False, indent=2)}

BIBLIOGRAPHIC CANDIDATES (Open Library, Google Books, and/or Crossref):
{json.dumps(compact, ensure_ascii=False, indent=2)}

Return exactly one JSON object:
{{"candidate_index":0,"confidence":0.0,"reason":"short explanation"}}

Choose the single catalogue candidate that best matches the work and, when present,
the current edition, publisher, year, ISBN, language, or translator. Do not choose a
candidate merely because its title contains similar words. If no candidate is reliable,
return candidate_index=-1. Confidence is 0.0 to 1.0. Do not return bibliographic values;
DerridAI will copy them deterministically from the selected catalogue record."""
    raw = chat_complete(
        provider=request.provider,
        model=model,
        base_url=request.base_url,
        api_key=request.api_key,
        prompt=prompt,
        options=request.generation,
        json_mode=True,
        max_tokens=384,
        cancelled=cancelled,
    )
    choice = _extract_json(raw)
    try:
        index = int(choice.get("candidate_index", -1))
    except Exception:
        index = -1
    if index < 0 or index >= len(candidates):
        return {
            "work": seed.work,
            "current_metadata": seed.current_metadata,
            "changes": {},
            "rationale": {},
            "catalog_source": ", ".join(catalog_sources) or "Public catalogues",
            "catalog_sources_tried": catalog_sources,
            "message": str(choice.get("reason") or "The LLM did not identify a sufficiently reliable catalogue match."),
            "confidence": choice.get("confidence"),
            "model": model,
        }

    selected = candidates[index]
    public = _candidate_public(selected)
    changes: dict[str, Any] = {}
    rationale: dict[str, str] = {}
    current = seed.current_metadata or {}
    for field, proposed in public.items():
        if field not in {
            "source_type", "document_type", "document_title", "short_title", "original_title",
            "document_author", "container_title", "journal_title", "editor", "edition",
            "volume", "issue", "pages", "year", "publication_year", "publisher",
            "publication_place", "translator", "document_language", "original_language",
            "document_is_translation", "isbn", "doi", "url", "full_citation", "cover_url",
        }:
            continue
        if proposed in (None, "", []):
            continue
        current_value = current.get(field)
        if str(current_value or "").strip() == str(proposed or "").strip():
            continue
        changes[field] = proposed
        rationale[field] = f"{selected.get('_catalog_source') or 'Public catalogue'} metadata from the LLM-selected record."

    return {
        "work": seed.work,
        "current_metadata": seed.current_metadata,
        "changes": changes,
        "rationale": rationale,
        "confidence": choice.get("confidence"),
        "match_reason": str(choice.get("reason") or ""),
        "catalog_source": selected.get("_catalog_source") or ", ".join(catalog_sources) or "Public catalogue",
        "catalog_sources_tried": catalog_sources,
        "catalog_match": public,
        "openlibrary_work_key": selected.get("_openlibrary_work_key"),
        "openlibrary_edition_key": selected.get("_openlibrary_edition_key"),
        "model": model,
    }


def run_work_metadata_batch(
    body: WorkMetadataRequest,
    *,
    cancelled: Callable[[], bool] | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    proposals: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    total = len(body.works)
    for index, seed in enumerate(body.works, start=1):
        if cancelled and cancelled():
            raise InterruptedError()
        if progress:
            progress(index - 1, total, f"Looking up {seed.work}")
        try:
            proposals.append(run_work_metadata_lookup(seed, body, cancelled=cancelled))
        except InterruptedError:
            raise
        except Exception as exc:
            errors.append({"work": seed.work, "error": str(exc)})
            proposals.append({
                "work": seed.work,
                "current_metadata": seed.current_metadata,
                "changes": {},
                "rationale": {},
                "error": str(exc),
            })
        if progress:
            progress(index, total, f"Processed {index} of {total} works")
    return {"proposals": proposals, "errors": errors, "total": total, "failed": len(errors), "model": _model_for(body.provider, body.model)}


def _normalize_rag_grade_payload(value: Any) -> dict[str, Any]:
    """Normalize grader output into the application's canonical audit shape.

    ``categories``, free-form analysis, and ``raw_output`` preserve the complete
    audit trail while top-level score fields support current UI summaries.
    """
    original = copy.deepcopy(value)
    if isinstance(value, dict):
        grade = value.get("grade") if isinstance(value.get("grade"), dict) else value
        if isinstance(grade.get("result"), dict) and not any(
            key in grade for key in ("overall", "query_relevance", "summary", "categories")
        ):
            grade = grade["result"]
    else:
        grade = {"summary": "" if value is None else str(value)}

    scores = grade.get("scores") if isinstance(grade.get("scores"), dict) else {}
    supplied_categories = grade.get("categories") if isinstance(grade.get("categories"), dict) else {}
    score_keys = (
        "query_relevance", "source_binding", "claim_traceability",
        "attribution_source_discrimination", "claim_evidence_fidelity",
        "conceptual_precision", "coverage", "interpretive_usefulness",
        "overall",
    )

    def category_raw(key: str) -> Any:
        if key in grade:
            return grade.get(key)
        if key in supplied_categories:
            return supplied_categories.get(key)
        return scores.get(key)

    def score_value(key: str):
        raw = category_raw(key)
        if isinstance(raw, dict):
            raw = raw.get("score", raw.get("value", raw.get("rating")))
        if raw is None or raw == "":
            return None
        try:
            numeric = float(raw)
            return int(numeric) if numeric.is_integer() else numeric
        except (TypeError, ValueError):
            return raw

    def list_value(raw: Any) -> list[str]:
        if raw is None or raw == "":
            return []
        if isinstance(raw, list):
            out: list[str] = []
            for item in raw:
                out.extend(list_value(item))
            return out
        if isinstance(raw, dict):
            return [f"{key}: {item}" for key, item in raw.items()]
        return [str(raw)]

    normalized = {key: score_value(key) for key in score_keys}
    normalized["summary"] = str(
        grade.get("summary")
        or grade.get("overall_summary")
        or grade.get("assessment")
        or ""
    )
    normalized["analysis"] = str(
        grade.get("analysis")
        or grade.get("overall_analysis")
        or grade.get("reasoning")
        or grade.get("rationale")
        or ""
    )
    normalized["strengths"] = list_value(grade.get("strengths", grade.get("strength")))
    normalized["weaknesses"] = list_value(grade.get("weaknesses", grade.get("weakness")))
    normalized["unsupported_or_risky_claims"] = list_value(
        grade.get(
            "unsupported_or_risky_claims",
            grade.get("risky_claims", grade.get("unsupported_claims")),
        )
    )

    categories: dict[str, dict[str, Any]] = {}
    for key in score_keys:
        raw = category_raw(key)
        if isinstance(raw, dict):
            detail = copy.deepcopy(raw)
        else:
            detail = {}
        detail["score"] = normalized.get(key)
        if detail.get("analysis") is None:
            for alias in ("reasoning", "rationale", "explanation", "notes"):
                if detail.get(alias) not in (None, ""):
                    detail["analysis"] = detail.get(alias)
                    break
        categories[key] = detail
    normalized["categories"] = categories
    normalized["raw_output"] = original
    return normalized


def run_rag_grade(
    body: RAGGradeRequest,
    store: ChromaStore,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    evidence = body.evidence[:40]
    evidence_text = "\n\n".join(
        f"[{item.get('evidence_id', f'E{index}')}] "
        f"{(item.get('record') or {}).get('work', '')} "
        f"{item.get('inline_citation', '')}\n"
        f"{str((item.get('record') or {}).get('text', ''))[:3500]}"
        for index, item in enumerate(evidence)
    )
    prompt = f"""You are grading an evidence-grounded philosophical RAG answer.

QUESTION:
{body.question}

ANSWER:
{body.answer}

EVIDENCE:
{evidence_text}

Return JSON only. Include a `categories` object containing query_relevance,
source_binding, claim_traceability, attribution_source_discrimination,
claim_evidence_fidelity, conceptual_precision, coverage, and
interpretive_usefulness. Each category must contain an integer `score` from 0-10
and a concise `analysis` explaining the score against the supplied evidence. Also
include `overall` as an object with `score` and `analysis`, plus top-level
`strengths`, `weaknesses`, `unsupported_or_risky_claims`, `summary`, and
`analysis`. Preserve source-role distinctions: distinguish Derrida's claims from
quoted, attributed, reconstructed, questioned, criticized, or endorsed positions."""
    raw = chat_complete(
        provider=body.provider, model=_model_for(body.provider, body.model),
        base_url=body.base_url, api_key=body.api_key, prompt=prompt,
        options=body.generation, json_mode=True, max_tokens=4096,
        cancelled=cancelled,
    )
    grade = _normalize_rag_grade_payload(_extract_json(raw))
    cache_summary = None
    cache_error = None
    if body.response_record_id:
        try:
            cached = store.update_response_cache_grade(
                body.response_record_id,
                grade,
                provider=body.provider,
                model=body.model,
                generation_provider=body.generation_provider,
                generation_model=body.generation_model,
            )
            cache_summary = {
                "record_id": body.response_record_id,
                "grade_history_count": len(cached.get("grades") or []),
                "updated_at": cached.get("updated_at"),
            }
        except Exception as exc:
            # The grade itself is valuable even if cache persistence fails. Do
            # not turn an otherwise successful background grading operation into
            # an unviewable failed job. Surface persistence failure separately.
            cache_error = str(exc)
    return {
        "grade": grade,
        "response_cache": cache_summary,
        "response_cache_error": cache_error,
    }
