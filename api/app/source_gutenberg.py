# Copyright 2026 Aaron John Schlosser, PhD.
"""Bounded Gutenberg catalog lookup and exact-edition plain-text acquisition."""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from datetime import UTC, datetime
from html import escape, unescape
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

import httpx

from .source_safety import MAX_SOURCE_BYTES

_WIKISOURCE_RATE_LOCK = threading.Lock()
_WIKISOURCE_LAST_REQUEST = 0.0
logger = logging.getLogger(__name__)
# Wikimedia asks API clients to identify the tool and a way to reach its maintainers.
_USER_AGENT = "DerridAI/1.0 (https://github.com/ajschlosser/DerridAI; local scholarly research tool)"


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


# Wikisource editions a search may target (a closed list: the language becomes part of the host name).
WIKISOURCE_LANGUAGES = ("en", "fr", "de", "it", "es", "pt", "la", "el", "ru", "pl", "nl", "sv", "he", "ar", "zh", "ja")


def search_wikisource(query: str, limit: int = 12, language: str = "en") -> list[dict[str, Any]]:
    """Search one language edition of Wikisource through the public MediaWiki API.

    The API is intentionally called only after an explicit user search.  The
    endpoint is rate-limited by MediaWiki and requests identify this client.
    """
    text = str(query or "").strip()
    if not text:
        return []
    if language not in WIKISOURCE_LANGUAGES:
        raise ValueError(f"Unsupported Wikisource language: {language}")
    host = f"https://{language}.wikisource.org"
    limit = max(1, min(30, int(limit)))
    global _WIKISOURCE_LAST_REQUEST
    with _WIKISOURCE_RATE_LOCK:
        elapsed = time.monotonic() - _WIKISOURCE_LAST_REQUEST
        if elapsed < 0.2:
            time.sleep(0.2 - elapsed)
        _WIKISOURCE_LAST_REQUEST = time.monotonic()
    response = httpx.get(
        f"{host}/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": text,
            "srlimit": limit,
            "srnamespace": 0,
            "srprop": "snippet|wordcount",
            "format": "json",
            "formatversion": 2,
        },
        headers={"User-Agent": _USER_AGENT},
        timeout=httpx.Timeout(30.0, connect=10.0),
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("query", {}).get("search", [])
    return [
        {
            "source": "wikisource",
            "language": language,
            "title": str(item.get("title") or ""),
            "page_id": int(item["pageid"]),
            "snippet": unescape(re.sub(r"<[^>]+>", "", str(item.get("snippet") or ""))).strip(),
            "word_count": int(item.get("wordcount") or 0),
            "url": f"{host}/wiki/{quote(str(item.get('title') or '').replace(' ', '_'))}",
        }
        for item in results
        if isinstance(item, dict) and item.get("title") and item.get("pageid")
    ]


def load_gutenberg_etext(etext_id: int) -> tuple[str, dict[str, Any]]:
    etext_id = int(etext_id)
    if etext_id < 1:
        raise ValueError("Choose a Project Gutenberg text.")
    try:
        from .gutenberg_catalogue import gutenberg_offline

        offline_status = gutenberg_offline.status()
        if offline_status.get("ready"):
            local = gutenberg_offline.text(etext_id)
            if local is not None:
                return local
            raise ValueError(
                f"Project Gutenberg text {etext_id} is not present in the completed local collection."
            )
        if offline_status.get("search_ready"):
            raise ValueError(
                "The Project Gutenberg catalogue is searchable, but the local text "
                "collection has not finished downloading and unpacking."
            )
    except ValueError:
        raise
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


_WIKISOURCE_HOST = re.compile(r"^([a-z\-]+\.)?wikisource\.org$", re.IGNORECASE)


def _wikisource_page_title(parsed: Any) -> str:
    """Page title for a /wiki/<Title> or ?title=<Title> Wikisource URL, else ''."""
    host = (parsed.hostname or "").lower()
    if not _WIKISOURCE_HOST.match(host):
        return ""
    if parsed.path.startswith("/wiki/"):
        return unquote(parsed.path[len("/wiki/"):]).replace("_", " ").strip()
    match = re.search(r"(?:^|&)title=([^&]+)", parsed.query or "")
    return unquote(match.group(1).replace("+", " ")).replace("_", " ").strip() if match else ""


# A work's main page is often only its title page and contents; the text is on subpages (Title/Chapter I, …).
MAX_WIKISOURCE_SUBPAGES = 400


def _wikisource_parse(parsed: Any, title: str) -> tuple[str, str]:
    """(resolved title, rendered HTML) for one page through the MediaWiki parse API, rate-limited like search."""
    global _WIKISOURCE_LAST_REQUEST
    with _WIKISOURCE_RATE_LOCK:
        elapsed = time.monotonic() - _WIKISOURCE_LAST_REQUEST
        if elapsed < 0.2:
            time.sleep(0.2 - elapsed)
        _WIKISOURCE_LAST_REQUEST = time.monotonic()
    response = httpx.get(
        f"{parsed.scheme}://{parsed.netloc}/w/api.php",
        params={
            "action": "parse",
            "page": title,
            "prop": "text",
            "redirects": 1,
            "disableeditsection": 1,
            "disabletoc": 1,
            "format": "json",
            "formatversion": 2,
        },
        headers={"User-Agent": _USER_AGENT},
        timeout=httpx.Timeout(45.0, connect=10.0),
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload.get("error"), dict):
        raise ValueError(f"Wikisource: {payload['error'].get('info') or 'page not found'}")
    parse = payload.get("parse") or {}
    html = str(parse.get("text") or "")
    if not html:
        raise ValueError("Wikisource returned no page content.")
    return str(parse.get("title") or title), html


def wikisource_subpage_titles(html: str, root_title: str) -> list[str]:
    """Subpages of `root_title` linked from its page, in reading order, each once (the work's contents)."""
    prefix = root_title.replace(" ", "_") + "/"
    seen: set[str] = set()
    titles: list[str] = []
    for href in re.findall(r'href="/wiki/([^"#?]+)', html):
        name = unquote(href.replace("&amp;", "&"))
        if not name.startswith(prefix) or name in seen:
            continue
        seen.add(name)
        titles.append(name.replace("_", " "))
    return titles[:MAX_WIKISOURCE_SUBPAGES]


def fetch_wikisource_page(parsed: Any, title: str, *, max_bytes: int) -> tuple[bytes, str, str]:
    """Fetch a Wikisource work through the MediaWiki API (never by scraping /wiki/).

    Wikimedia rejects anonymous page scraping; the parse API is the supported route. When the page is a work's
    title/contents page, its subpages are fetched in the order the contents list them and kept, each in a section
    that names the page it came from, so the whole work is imported rather than its table of contents.
    """
    resolved, html = _wikisource_parse(parsed, title)
    parts = [html]
    total = len(html.encode("utf-8"))
    for subpage in wikisource_subpage_titles(html, resolved):
        sub_title, sub_html = _wikisource_parse(parsed, subpage)
        section = f'<section data-wikisource-page="{escape(sub_title, quote=True)}">{sub_html}</section>'
        total += len(section.encode("utf-8"))
        if total > max_bytes:
            raise ValueError(
                "This Wikisource work exceeds the upload size limit; import its parts (subpages) separately."
            )
        parts.append(section)
    data = "\n".join(parts).encode("utf-8")
    if len(data) > max_bytes:
        raise ValueError("The URL exceeds the upload size limit.")
    safe = re.sub(r"[^\w.\- ]+", "_", resolved).strip().replace(" ", "_") or "wikisource"
    return data, f"{safe}.html", "text/html; charset=utf-8"


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
