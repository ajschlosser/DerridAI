# Copyright 2026 Aaron John Schlosser, PhD.
"""Bounded Gutenberg catalog lookup and exact-edition plain-text acquisition."""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from .source_safety import MAX_SOURCE_BYTES

_WIKISOURCE_RATE_LOCK = threading.Lock()
_WIKISOURCE_LAST_REQUEST = 0.0
logger = logging.getLogger(__name__)


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


def search_wikisource(query: str, limit: int = 12) -> list[dict[str, Any]]:
    """Search Wikisource through the public MediaWiki API.

    The API is intentionally called only after an explicit user search.  The
    endpoint is rate-limited by MediaWiki and requests identify this client.
    """
    text = str(query or "").strip()
    if not text:
        return []
    limit = max(1, min(30, int(limit)))
    global _WIKISOURCE_LAST_REQUEST
    with _WIKISOURCE_RATE_LOCK:
        elapsed = time.monotonic() - _WIKISOURCE_LAST_REQUEST
        if elapsed < 0.2:
            time.sleep(0.2 - elapsed)
        _WIKISOURCE_LAST_REQUEST = time.monotonic()
    response = httpx.get(
        "https://en.wikisource.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": text,
            "srlimit": limit,
            "srnamespace": 0,
            "format": "json",
            "formatversion": 2,
        },
        headers={"User-Agent": "DerridAI/1.0 (local scholarly research tool)"},
        timeout=httpx.Timeout(30.0, connect=10.0),
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("query", {}).get("search", [])
    return [
        {
            "source": "wikisource",
            "title": str(item.get("title") or ""),
            "page_id": int(item["pageid"]),
            "snippet": re.sub(r"<[^>]+>", "", str(item.get("snippet") or "")),
            "url": f"https://en.wikisource.org/wiki/{str(item.get('title') or '').replace(' ', '_')}",
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


def _gutendex_etext(etext_id: int) -> tuple[str, dict[str, Any]]:
    response = httpx.get(
        f"https://gutendex.com/books/{int(etext_id)}",
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
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {
        "www.gutenberg.org",
        "gutenberg.org",
    }:
        raise ValueError("Unsupported Gutenberg source URL.")
    if not re.search(rf"/(?:ebooks|files|epub)/{etext_id}(?:[/.]|$)", parsed.path):
        raise ValueError("Gutenberg file URL does not identify the selected edition.")
    # Do not follow a redirect or guess a filename: either could change the source.
    chunks = []
    size = 0
    with httpx.stream("GET", url, timeout=60.0, follow_redirects=False) as download:
        download.raise_for_status()
        for chunk in download.iter_bytes():
            size += len(chunk)
            if size > MAX_SOURCE_BYTES:
                raise ValueError("Gutenberg text exceeds ingestion size limit.")
            chunks.append(chunk)
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
    with httpx.stream(
        "GET", parsed.geturl(), timeout=45.0, follow_redirects=True
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
