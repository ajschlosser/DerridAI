from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _author_last_name(author: str) -> str:
    parts = [part for part in author.replace(",", " ").split() if part]
    return parts[-1] if parts else ""


def _author_bibliographic(author: str) -> str:
    author = author.strip()
    if not author:
        return ""
    if "," in author:
        return author
    parts = author.split()
    if len(parts) == 1:
        return author
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def _pages(metadata: dict[str, Any]) -> str:
    start = metadata.get("page_start")
    end = metadata.get("page_end")
    if start in (None, ""):
        return ""
    if end in (None, "") or str(end) == str(start):
        return str(start)
    return f"{start}-{end}"


def generate_citation_strings_from_metadata(metadata: dict[str, Any]) -> tuple[str, str]:
    """Build citations only from stored metadata; never infer missing bibliography."""

    author = _text(metadata.get("document_author") or metadata.get("author") or metadata.get("speaker"))
    work = _text(metadata.get("work") or metadata.get("title"))
    edition = _text(metadata.get("edition"))
    publisher = _text(metadata.get("publisher"))
    year = _text(metadata.get("year"))
    translator = _text(metadata.get("translator"))
    pages = _pages(metadata)

    inline_parts: list[str] = []
    last_name = _author_last_name(author)
    if last_name:
        inline_parts.append(last_name)
    if year:
        inline_parts.append(year)
    inline = " ".join(inline_parts)
    if pages:
        inline = f"{inline}: {pages}" if inline else pages

    full_parts: list[str] = []
    bibliographic_author = _author_bibliographic(author)
    if bibliographic_author:
        full_parts.append(f"{bibliographic_author}.")
    if work:
        full_parts.append(f"{work}.")
    if translator:
        full_parts.append(f"Translated by {translator}.")
    if edition:
        full_parts.append(f"{edition}.")
    if publisher:
        full_parts.append(f"{publisher}{',' if year else '.'}")
    if year:
        full_parts.append(f"{year}.")
    full = " ".join(full_parts).strip()

    if not inline:
        inline = work or _text(metadata.get("record_id")) or "source"
    if not full:
        full = work or _text(metadata.get("record_id")) or "Unspecified source"
    return inline, full


def generate_citation_strings(doc) -> tuple[str, str]:
    return generate_citation_strings_from_metadata(dict(getattr(doc, "metadata", {}) or {}))
