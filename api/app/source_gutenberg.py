# Copyright 2026 Aaron John Schlosser, PhD.
"""Project Gutenberg search and plain-text loading via pygutenberg, then Gutendex."""
from __future__ import annotations

import importlib
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from .source_text import decode_plain_text

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


def _pygutenberg_client() -> Any | None:
    for module_name in ("pygutenberg", "gutenberg"):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        factory = getattr(module, "GutenbergAPI", None) or getattr(module, "Gutenberg", None)
        if callable(factory):
            try:
                return factory()
            except Exception:
                continue
        if any(callable(getattr(module, name, None)) for name in ("search", "search_books", "get_book_text")):
            return module
    return None


def search_project_gutenberg(query: str, limit: int = 12) -> list[dict[str, Any]]:
    """Search Project Gutenberg through pygutenberg, then the Gutendex API it wraps.

    Installed packages expose `search`, `search_books`, or only a Gutendex base
    URL. An empty or failed client result falls through to the public catalog
    so a missing method does not hide texts that can still be loaded.
    """
    text = str(query or "").strip()
    if not text:
        return []
    limit = max(1, min(30, int(limit)))
    client = _pygutenberg_client()
    raw = _search_with_client(client, text) if client is not None else None
    hits = _coerce_gutenberg_results(raw)
    if not hits:
        hits = _gutendex_search(text, limit)
    return hits[:limit]


def load_gutenberg_etext(etext_id: int) -> tuple[str, dict[str, Any]]:
    etext_id = int(etext_id)
    if etext_id < 1:
        raise ValueError("Choose a Project Gutenberg text.")
    client = _pygutenberg_client()
    text = _text_with_client(client, etext_id) if client is not None else ""
    meta = _metadata_with_client(client, etext_id) if client is not None else {}
    catalog = _catalog_from_any(meta, etext_id)
    if not str(text or "").strip() or not catalog.get("title"):
        remote_text, remote_catalog = _gutendex_etext(etext_id)
        text = text or remote_text
        catalog = {**remote_catalog, **{key: value for key, value in catalog.items() if value}}
    if not str(text or "").strip():
        raise ValueError(f"Project Gutenberg text {etext_id} has no plain-text file.")
    catalog.setdefault("gutenberg_id", etext_id)
    catalog.setdefault("publisher", "Project Gutenberg")
    catalog.setdefault("document_type", "book")
    return str(text), catalog


def _search_with_client(client: Any, query: str) -> Any:
    for name in ("search", "search_books", "find", "query"):
        fn = getattr(client, name, None)
        if not callable(fn):
            continue
        try:
            return fn(query)
        except TypeError:
            try:
                return fn(search=query)
            except Exception:
                continue
        except Exception:
            continue
    base = getattr(client, "instance_url", None) or getattr(client, "base_url", None)
    if base:
        return _gutendex_search(query, 12, base=str(base).rstrip("/"))
    return None


def _text_with_client(client: Any, etext_id: int) -> str:
    for name in ("get_book_text", "get_text", "load_etext", "text"):
        fn = getattr(client, name, None)
        if not callable(fn):
            continue
        try:
            value = fn(etext_id)
        except Exception:
            continue
        if isinstance(value, bytes):
            return decode_plain_text(value)
        if isinstance(value, str):
            return value
    return ""


def _metadata_with_client(client: Any, etext_id: int) -> dict[str, Any]:
    for name in ("get_book_metadata", "get_metadata", "metadata"):
        fn = getattr(client, name, None)
        if not callable(fn):
            continue
        try:
            value = fn(etext_id)
        except Exception:
            continue
        if isinstance(value, dict):
            return value
    return {}


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
    hit = normalize_gutenberg_hit({**meta, "id": meta.get("id") or etext_id}) or {"etext_id": etext_id, "title": "", "author": "", "language": ""}
    return {
        "gutenberg_id": etext_id,
        "title": hit.get("title") or str(meta.get("title") or ""),
        "document_author": hit.get("author") or "",
        "language": hit.get("language") or "",
        "publisher": "Project Gutenberg",
        "document_type": "book",
    }


def _gutendex_search(query: str, limit: int, base: str = "https://gutendex.com") -> list[dict[str, Any]]:
    response = httpx.get(f"{base}/books", params={"search": query}, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    payload = response.json()
    return _coerce_gutenberg_results(payload)[:limit]


def _gutendex_etext(etext_id: int) -> tuple[str, dict[str, Any]]:
    response = httpx.get(f"https://gutendex.com/books/{int(etext_id)}", timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    payload = response.json()
    catalog = _catalog_from_any(payload if isinstance(payload, dict) else {}, etext_id)
    formats = payload.get("formats") if isinstance(payload, dict) else {}
    url = ""
    if isinstance(formats, dict):
        for key, value in formats.items():
            if "text/plain" in str(key) and isinstance(value, str):
                url = value
                break
    if not url:
        url = f"https://www.gutenberg.org/files/{etext_id}/{etext_id}-0.txt"
    text_response = httpx.get(url, timeout=60.0, follow_redirects=True)
    text_response.raise_for_status()
    return text_response.text, catalog


def fetch_source_url(url: str, *, max_bytes: int) -> tuple[bytes, str, str]:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Source URL must be an http(s) address.")
    with httpx.stream("GET", parsed.geturl(), timeout=45.0, follow_redirects=True) as response:
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
        name += ".html" if "html" in kind else ".txt" if kind.startswith("text/") else ".bin"
    return b"".join(chunks), name, content_type
