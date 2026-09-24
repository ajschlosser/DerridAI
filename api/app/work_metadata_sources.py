# Copyright 2026 Aaron John Schlosser, PhD.
"""Source-type policy and lightweight metadata adapters for Works enrichment."""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

import httpx


SOURCE_TYPE_ALIASES = {
    "monograph": "book",
    "edited_book": "book",
    "book_length": "book",
    "journal": "journal_article",
    "article": "journal_article",
    "article_journal": "journal_article",
    "book_chapter": "chapter",
    "chapter_in_book": "chapter",
    "reference_entry": "chapter",
    "dissertation": "thesis",
    "website": "web",
    "webpage": "web",
    "podcast": "audio",
    "photograph": "image",
    "moving_image": "video",
}

SOURCE_TYPE_LABELS = {
    "book": "book or monograph",
    "journal_article": "journal article",
    "chapter": "book chapter or reference entry",
    "thesis": "thesis or dissertation",
    "web": "webpage",
    "audio": "audio",
    "image": "image",
    "video": "video",
    "archival": "archival item",
    "unknown": "unresolved source type",
}

CATALOG_FIELDS = {
    "source_type",
    "document_type",
    "document_title",
    "short_title",
    "original_title",
    "document_author",
    "container_title",
    "journal_title",
    "editor",
    "edition",
    "volume",
    "issue",
    "pages",
    "year",
    "publication_year",
    "publisher",
    "publication_place",
    "translator",
    "document_language",
    "original_language",
    "document_is_translation",
    "isbn",
    "doi",
    "url",
    "full_citation",
    "cover_url",
}


def canonical_source_type(value: Any) -> str:
    normalized = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    if not normalized:
        return "unknown"
    return SOURCE_TYPE_ALIASES.get(normalized, normalized if normalized in SOURCE_TYPE_LABELS else "unknown")


def source_type_label(value: Any) -> str:
    return SOURCE_TYPE_LABELS.get(canonical_source_type(value), SOURCE_TYPE_LABELS["unknown"])


def source_types_for_metadata(metadata: dict[str, Any] | None) -> list[str]:
    metadata = metadata or {}
    values = metadata.get("source_types")
    if isinstance(values, list):
        types = [canonical_source_type(item) for item in values if str(item or "").strip()]
    else:
        types = [canonical_source_type(metadata.get("source_type") or metadata.get("document_type"))]
    return list(dict.fromkeys(types or ["unknown"]))


def catalogue_sources_for(source_type: Any) -> list[str]:
    kind = canonical_source_type(source_type)
    if kind == "journal_article":
        return ["Crossref", "OpenAlex", "Open Library"]
    if kind == "chapter":
        return ["Crossref", "Open Library"]
    if kind == "thesis":
        return ["Crossref", "OpenAlex"]
    if kind == "book":
        return ["Open Library", "Google Books", "Crossref"]
    if kind == "web":
        return ["Source webpage metadata"]
    return ["Embedded source metadata"]


def is_catalogue_supported(source_type: Any) -> bool:
    return canonical_source_type(source_type) in {"book", "journal_article", "chapter", "thesis"}


def applicable_fields_for(source_type: Any) -> set[str]:
    kind = canonical_source_type(source_type)
    common = {
        "source_type",
        "document_type",
        "document_title",
        "short_title",
        "document_author",
        "document_language",
        "original_language",
        "year",
        "publication_year",
        "publisher",
        "url",
    }
    if kind == "book":
        return common | {"original_title", "editor", "edition", "publication_place", "translator", "isbn", "cover_url", "full_citation"}
    if kind in {"journal_article", "chapter", "thesis"}:
        return common | {"container_title", "journal_title", "editor", "volume", "issue", "pages", "publication_place", "translator", "doi", "full_citation"}
    if kind == "web":
        return common | {"original_title", "full_citation"}
    if kind in {"audio", "image", "video"}:
        return common | {"original_title"}
    return common


class _PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {str(key).casefold(): str(value or "").strip() for key, value in attrs}
        if tag.casefold() == "title" and not self.title:
            self.meta["_title_pending"] = ""
        if tag.casefold() != "meta":
            return
        key = attrs_map.get("property") or attrs_map.get("name") or attrs_map.get("itemprop")
        content = attrs_map.get("content")
        if key and content:
            self.meta[key.casefold()] = content

    def handle_data(self, data: str) -> None:
        if "_title_pending" in self.meta:
            self.meta["_title_pending"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title" and "_title_pending" in self.meta:
            self.title = self.meta.pop("_title_pending").strip()


def web_page_candidate(metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Read declared webpage metadata without treating page text as scholarly fact."""
    url = str(metadata.get("url") or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    response = httpx.get(
        url,
        timeout=10.0,
        follow_redirects=True,
        headers={"User-Agent": "DerridAI (source metadata lookup)"},
    )
    response.raise_for_status()
    parser = _PageMetadataParser()
    parser.feed(response.text[:2_000_000])
    values = parser.meta
    title = values.get("og:title") or values.get("twitter:title") or values.get("dc.title") or parser.title
    author = values.get("author") or values.get("article:author") or values.get("dc.creator")
    published = values.get("article:published_time") or values.get("date") or values.get("dc.date")
    candidate = {
        "source_type": "web",
        "document_type": "web",
        "document_title": title or None,
        "short_title": title or None,
        "document_author": author or None,
        "publication_year": published[:4] if published and published[:4].isdigit() else None,
        "url": str(response.url),
        "_catalog_source": "Source webpage metadata",
    }
    return {key: value for key, value in candidate.items() if value not in (None, "")}
