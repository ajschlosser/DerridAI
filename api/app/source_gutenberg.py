# Copyright 2026 Aaron John Schlosser, PhD.
"""Bounded Gutenberg catalog lookup and exact-edition plain-text acquisition."""

from __future__ import annotations

import hashlib
import logging
import re
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from .source_identity import (
    CaptureError,
    CaptureErrorCode,
    CaptureOptions,
    ContributionRole,
    PersonName,
    ResolvedAuthor,
    SourceCandidate,
    WorkRelationship,
    normalize_languages,
)
from .source_provider import USER_AGENT, AcquiredSource, DiscoveryReport, ProgressCallback, ProviderHttp
from .source_safety import MAX_SOURCE_BYTES

# Wikisource moved to its own provider module; these names stay importable from here.
from .source_wikisource import (  # noqa: F401
    MAX_WIKISOURCE_SUBPAGES,
    WIKISOURCE_LANGUAGES,
    _wikisource_parse,
    fetch_wikisource_page,
    search_wikisource,
    wikisource_subpage_titles,
)
from .source_wikisource import wikisource_page_title as _wikisource_page_title

logger = logging.getLogger(__name__)
_USER_AGENT = USER_AGENT


def normalize_gutenberg_hit(item: dict[str, Any]) -> dict[str, Any] | None:
    etext_id = item.get("id") or item.get("etext_id") or item.get("gutenberg_id")
    try:
        etext_id = int(etext_id)
    except (TypeError, ValueError):
        return None
    title = str(item.get("title") or "").strip()
    authors = item.get("authors") or item.get("author") or []
    if isinstance(authors, str):
        author = authors
    elif isinstance(authors, list) and authors:
        first = authors[0]
        author = first.get("name") if isinstance(first, dict) else str(first)
    else:
        author = ""
    languages = item.get("languages") or item.get("language") or []
    if isinstance(languages, str):
        language = languages
    elif isinstance(languages, list) and languages:
        language = str(languages[0])
    else:
        language = ""
    return {
        "etext_id": etext_id,
        "title": title,
        "author": human_author_name(str(author or "")),
        "language": language,
    }


def human_author_name(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name).strip()
    if cleaned.count(",") == 1:
        last, first = [part.strip() for part in cleaned.split(",", 1)]
        if first and last:
            return f"{first} {last}".strip()
    return cleaned


def search_project_gutenberg(query: str, limit: int = 12) -> list[dict[str, Any]]:
    """Return catalog candidates without choosing or substituting an edition."""
    text = str(query or "").strip()
    if not text:
        return []
    limit = max(1, min(30, int(limit)))
    try:
        from .gutenberg_catalogue import gutenberg_offline
        if gutenberg_offline.status()["search_ready"]:
            return gutenberg_offline.search(text, limit)
    except Exception:
        logger.warning("Local Gutenberg search unavailable; using Gutendex", exc_info=True)
    return _gutendex_search(text, limit)


def load_gutenberg_etext(etext_id: int) -> tuple[str, dict[str, Any]]:
    etext_id = int(etext_id)
    if etext_id < 1:
        raise ValueError("Choose a Project Gutenberg text.")
    try:
        from .gutenberg_catalogue import gutenberg_offline

        # Local exact eText first; otherwise one verified, bounded download of that eText.
        # The full local collection is optional and never a precondition for importing one book.
        if gutenberg_offline.status().get("ready"):
            local = gutenberg_offline.text(etext_id)
            if local is not None:
                return local
    except Exception:
        logger.warning("Local Gutenberg text unavailable; using remote edition", exc_info=True)
    # Use one bounded catalog/download path for imports. Optional clients cannot
    # reliably expose the selected URL, encoding, timeout, or response identity.
    text, catalog = _gutendex_etext(etext_id)
    if not text.strip():
        raise ValueError(f"Project Gutenberg text {etext_id} has no plain-text file.")
    return text, catalog


def _coerce_gutenberg_results(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        raw = raw.get("results") or raw.get("books") or raw.get("items") or []
    if not isinstance(raw, list):
        return []
    hits = []
    for item in raw:
        if isinstance(item, dict):
            hit = normalize_gutenberg_hit(item)
            if hit and hit.get("title"):
                hits.append(hit)
    return hits


def _catalog_from_any(meta: dict[str, Any], etext_id: int) -> dict[str, Any]:
    selected_id = meta.get("id") or meta.get("etext_id") or meta.get("gutenberg_id")
    if selected_id is None or int(selected_id) != etext_id:
        raise ValueError("Gutenberg returned a different or unidentified edition.")
    hit = normalize_gutenberg_hit({**meta, "id": selected_id}) or {
        "etext_id": etext_id,
        "title": "",
        "author": "",
        "language": "",
    }
    return {
        "gutenberg_id": etext_id,
        "title": hit.get("title") or str(meta.get("title") or ""),
        "document_author": hit.get("author") or "",
        "language": hit.get("language") or "",
        "publisher": "Project Gutenberg",
        "document_type": "book",
    }


def _gutendex_search(
    query: str, limit: int, base: str = "https://gutendex.com"
) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = httpx.get(
                f"{base}/books",
                params={"search": query, "page": 1},
                timeout=httpx.Timeout(45.0, connect=10.0),
                follow_redirects=True,
            )
            response.raise_for_status()
            payload = response.json()
            return _coerce_gutenberg_results(payload)[:limit]
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.25)
    if last_error is not None:
        # Preserve the transport exception so callers can classify a timeout or
        # network failure consistently; the API boundary adds the user-facing
        # 502 context.
        raise last_error
    return []


def _verified_gutenberg_file_url(url: str, etext_id: int) -> str:
    """The https form of a gutenberg.org file URL for this edition; anything else is refused."""
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or parsed.hostname not in {"www.gutenberg.org", "gutenberg.org"}:
        raise ValueError("Unsupported Gutenberg source URL.")
    if not re.search(rf"/(?:ebooks|files|epub)/{etext_id}(?:[/.]|$)", parsed.path):
        raise ValueError("Gutenberg file URL does not identify the selected edition.")
    return parsed._replace(scheme="https").geturl()


def _gutendex_etext(etext_id: int) -> tuple[str, dict[str, Any]]:
    response = httpx.get(
        f"https://gutendex.com/books/{int(etext_id)}/",
        timeout=30.0,
        follow_redirects=False,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Invalid Gutenberg metadata.")
    catalog = _catalog_from_any(payload, etext_id)
    if not catalog.get("title"):
        raise ValueError("Gutenberg edition metadata lacks a title.")
    formats = payload.get("formats") or {}
    choices = sorted(
        (key, value)
        for key, value in formats.items()
        if str(key).split(";", 1)[0] == "text/plain" and isinstance(value, str)
    )
    if not choices:
        raise ValueError("Selected Gutenberg edition has no plain-text file.")
    mime, url = next(
        (item for item in choices if "utf-8" in item[0].lower()), choices[0]
    )
    url = _verified_gutenberg_file_url(url, etext_id)
    # Do not follow redirects blindly or guess a filename: either could change the source. Gutenberg answers a format
    # URL (/ebooks/1342.txt.utf-8) with one redirect to its cache file (/cache/epub/1342/pg1342.txt); that one hop is
    # followed only when it stays on gutenberg.org and still names the same edition.
    chunks: list[bytes] = []
    size = 0
    for hop in range(2):
        with httpx.stream("GET", url, timeout=60.0, follow_redirects=False) as download:
            if download.is_redirect and hop == 0:
                url = _verified_gutenberg_file_url(
                    str(download.url.join(download.headers.get("location", ""))), etext_id
                )
                continue
            download.raise_for_status()
            for chunk in download.iter_bytes():
                size += len(chunk)
                if size > MAX_SOURCE_BYTES:
                    raise ValueError("Gutenberg text exceeds ingestion size limit.")
                chunks.append(chunk)
            break
    data = b"".join(chunks)
    match = re.search(r"charset=([^; ]+)", mime, re.I)
    encoding = match.group(1).strip('"') if match else "utf-8-sig"
    try:
        text = data.decode(encoding)
    except (LookupError, UnicodeDecodeError) as exc:
        raise ValueError("Gutenberg text encoding could not be verified.") from exc
    catalog.update(
        {
            "source_url": url,
            "catalog_url": str(response.url),
            "edition": f"Project Gutenberg eBook #{etext_id}",
            "source_sha256": hashlib.sha256(data).hexdigest(),
            "encoding": encoding,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "catalog_record": payload,
        }
    )
    return text, catalog


def fetch_source_url(url: str, *, max_bytes: int) -> tuple[bytes, str, str]:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Source URL must be an http(s) address.")
    wiki_title = _wikisource_page_title(parsed)
    if wiki_title:
        return fetch_wikisource_page(parsed, wiki_title, max_bytes=max_bytes)
    with httpx.stream(
        "GET", parsed.geturl(), timeout=45.0, follow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
    ) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("The URL exceeds the upload size limit.")
            chunks.append(chunk)
    name = unquote(Path(parsed.path).name) or "source"
    if "." not in name:
        kind = content_type.split(";", 1)[0].lower()
        name += (
            ".html"
            if "html" in kind
            else ".txt"
            if kind.startswith("text/")
            else ".bin"
        )
    return b"".join(chunks), name, content_type


# --- Corpus Capture provider -------------------------------------------------------------

GUTENDEX_MAX_PAGES = 10


def candidate_from_catalogue_row(row: dict[str, Any], author: ResolvedAuthor) -> SourceCandidate:
    """One catalogue item → a provider candidate. Roles come from the catalogue, never from titles."""
    contributors = [dict(item) for item in row.get("contributors") or []]
    matched = row.get("matched_contributor") or {}
    role = str(matched.get("role") or ContributionRole.UNKNOWN)
    authors = [item for item in contributors if item.get("role") == "author"]
    if role == "author" and len(authors) > 1:
        role = ContributionRole.COAUTHOR
    translators = [str(item.get("name")) for item in contributors if item.get("role") == "translator"]
    editors = [str(item.get("name")) for item in contributors if item.get("role") == "editor"]
    etext_id = int(row["etext_id"])
    issued = str(row.get("issued") or "")
    return SourceCandidate(
        provider="gutenberg",
        provider_item_id=str(etext_id),
        title=str(row.get("title") or "").replace("\n", " — ").replace("\r", "").strip(),
        source_uri=f"https://www.gutenberg.org/ebooks/{etext_id}",
        catalog_uri=f"https://www.gutenberg.org/ebooks/{etext_id}",
        contribution_role=role,
        provider_author_identity=str(matched.get("name") or ""),
        document_author="; ".join(human_author_name(str(item.get("name"))) for item in authors),
        contributors=[{k: item.get(k) for k in ("name", "role", "raw_role", "birth_year", "death_year")} for item in contributors],
        document_languages=list(row.get("languages") or []),
        translators=[human_author_name(name) for name in translators],
        editors=[human_author_name(name) for name in editors],
        edition=f"Project Gutenberg eBook #{etext_id}",
        publisher="Project Gutenberg",
        # A named translator is catalogue evidence of a translation; without one the relation stays unknown.
        relationship_to_work=WorkRelationship.TRANSLATION if translators and role in {"author", "coauthor"} else WorkRelationship.UNKNOWN,
        discovery_method=str(row.get("discovery_method") or "gutenberg_catalogue_contributor"),
        discovery_evidence={
            "matched_name": matched.get("name"),
            "matched_birth_year": matched.get("birth_year"),
            "matched_death_year": matched.get("death_year"),
            "date_evidence": bool(row.get("date_evidence")),
            "issued": issued,
            "authors_cell": row.get("authors_raw"),
        },
        identity_confidence=str(row.get("identity_confidence") or "needs_review"),
        rights_status=row.get("rights_status"),
        rights_source=row.get("rights_source"),
    )


def gutendex_rows_for_author(http: ProviderHttp, author: ResolvedAuthor) -> tuple[list[dict[str, Any]], bool]:
    """Fallback when the local catalogue is not indexed: Gutendex search, then the same identity rules."""
    names = [PersonName.parse(name) for name in author.names()]
    surname = next((name.surname for name in names if name.surname), "")
    if not surname:
        return [], True
    url: str | None = "https://gutendex.com/books"
    params: dict[str, Any] | None = {"search": surname}
    rows: list[dict[str, Any]] = []
    for _page in range(GUTENDEX_MAX_PAGES):
        if not url:
            return rows, True
        payload = http.get_json(url, params)
        params = None
        for item in payload.get("results") or []:
            if not isinstance(item, dict) or not str(item.get("media_type") or "Text").lower().startswith("text"):
                continue
            people = [{"name": p.get("name"), "role": "author", "raw_role": "", "birth_year": p.get("birth_year"), "death_year": p.get("death_year")} for p in item.get("authors") or [] if isinstance(p, dict)]
            people += [{"name": p.get("name"), "role": "translator", "raw_role": "Translator", "birth_year": p.get("birth_year"), "death_year": p.get("death_year")} for p in item.get("translators") or [] if isinstance(p, dict)]
            matched = None
            confidence = "needs_review"
            for person in people:
                parsed = PersonName.parse(str(person.get("name") or ""))
                if not any(parsed.surname == n.surname and parsed.first_given and parsed.first_given == n.first_given for n in names) and parsed.full not in {n.full for n in names}:
                    continue
                if person.get("birth_year") is not None and author.birth_year is not None:
                    if person["birth_year"] != author.birth_year:
                        continue
                    confidence = "exact"
                matched = person
                break
            if not matched:
                continue
            rows.append({
                "etext_id": item.get("id"),
                "title": item.get("title"),
                "languages": normalize_languages(item.get("languages") or []),
                "contributors": people,
                "matched_contributor": matched,
                "identity_confidence": confidence,
                "date_evidence": confidence == "exact",
                "discovery_method": "gutendex_search_identity_filtered",
                # Gutendex reports Project Gutenberg's own copyright flag; it is a provider assertion only.
                "rights_status": None if item.get("copyright") is None else ("provider_not_copyrighted_us" if item.get("copyright") is False else "provider_copyrighted"),
                "rights_source": "gutendex" if item.get("copyright") is not None else None,
            })
        next_url = payload.get("next")
        url = str(next_url) if next_url else None
    return rows, url is None


class GutenbergProvider:
    provider_id = "gutenberg"

    def __init__(self, http: ProviderHttp, catalogue: Any = None) -> None:
        self.http = http
        if catalogue is None:
            from .gutenberg_catalogue import gutenberg_offline

            catalogue = gutenberg_offline
        self.catalogue = catalogue

    def enumerate_author_sources(
        self, author: ResolvedAuthor, options: CaptureOptions, report: DiscoveryReport, progress: ProgressCallback
    ) -> Iterator[SourceCandidate]:
        progress("discovering_gutenberg", {"done": 0, "total": 1})
        status = self.catalogue.status()
        if status.get("search_ready"):
            rows = self.catalogue.sources_for_author(author.names(), birth_year=author.birth_year, death_year=author.death_year)
            report.catalog_version = "pg_catalog.csv"
            report.catalog_refreshed_at = (status.get("catalogue") or {}).get("refreshed_at")
            report.endpoint = "local catalogue"
        else:
            report.warnings = [*(report.warnings or []), "gutenberg_catalogue_not_indexed_used_gutendex"]
            report.endpoint = "https://gutendex.com/books"
            rows, complete = gutendex_rows_for_author(self.http, author)
            report.pagination_complete = complete
        report.projects_searched.append("gutenberg")
        report.identities_used.extend(author.names())
        wanted = {str(role) for role in options.roles}
        skipped_types = 0
        for row in rows:
            item_type = str(row.get("item_type") or "Text")
            if item_type and item_type.lower() != "text":
                skipped_types += 1
                continue
            candidate = candidate_from_catalogue_row(row, author)
            role = str(candidate.contribution_role)
            if role not in wanted:
                continue
            if not options.include_translations and candidate.relationship_to_work == WorkRelationship.TRANSLATION:
                continue
            if options.languages and not set(candidate.document_languages) & set(options.languages):
                continue
            if report.result_count >= options.max_candidates_per_provider:
                report.warnings = [*(report.warnings or []), "candidate_limit_reached"]
                break
            report.result_count += 1
            yield candidate
        if skipped_types:
            report.warnings = [*(report.warnings or []), f"non_text_items_skipped:{skipped_types}"]
        progress("discovering_gutenberg", {"done": 1, "total": 1})

    def fetch_source(self, candidate: SourceCandidate, *, max_bytes: int) -> AcquiredSource:
        etext_id = int(candidate.provider_item_id)
        try:
            text, catalog = load_gutenberg_etext(etext_id)
        except httpx.TimeoutException as exc:
            raise CaptureError(CaptureErrorCode.NETWORK_TIMEOUT, "Project Gutenberg did not answer in time.") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 404:
                raise CaptureError(CaptureErrorCode.SOURCE_NOT_FOUND, f"Project Gutenberg has no eText {etext_id}.") from exc
            code = CaptureErrorCode.RATE_LIMITED if status == 429 else CaptureErrorCode.PROVIDER_UNAVAILABLE if status >= 500 else CaptureErrorCode.ACQUISITION_FAILED
            raise CaptureError(code, f"Project Gutenberg answered HTTP {status}.") from exc
        except httpx.TransportError as exc:
            raise CaptureError(CaptureErrorCode.PROVIDER_UNAVAILABLE, "Could not reach Project Gutenberg.") from exc
        except ValueError as exc:
            message = str(exc)
            code = (
                CaptureErrorCode.SOURCE_TOO_LARGE if "size limit" in message
                else CaptureErrorCode.IDENTITY_MISMATCH if "different" in message or "does not identify" in message
                else CaptureErrorCode.UNSUPPORTED_SOURCE if "Unsupported" in message or "no plain-text" in message
                else CaptureErrorCode.ACQUISITION_FAILED
            )
            raise CaptureError(code, message) from exc
        data = text.encode("utf-8")
        if len(data) > max_bytes:
            raise CaptureError(CaptureErrorCode.SOURCE_TOO_LARGE, "The Gutenberg text exceeds the ingestion size limit.")
        catalog = {k: v for k, v in catalog.items() if k != "catalog_record"}
        catalog.update({
            "provider": "gutenberg",
            "gutenberg_id": etext_id,
            "document_author": candidate.document_author or catalog.get("document_author") or "",
            "translator": "; ".join(candidate.translators) or None,
            "language": (candidate.document_languages or [catalog.get("language") or ""])[0],
            "document_languages": candidate.document_languages,
            "source_sha256": catalog.get("source_sha256") or hashlib.sha256(data).hexdigest(),
        })
        safe = re.sub(r"[^\w.\- ]+", "_", str(catalog.get("title") or etext_id)).strip()[:120] or str(etext_id)
        return AcquiredSource(data=data, filename=f"{safe}.txt", content_type="text/plain", source_uri=candidate.source_uri, catalog_metadata=catalog)
