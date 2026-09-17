from __future__ import annotations

from typing import Any

def _mla_author_name(value: str | None) -> str:
    name = str(value or "").strip()
    if not name or "," in name:
        return name
    parts = name.split()
    if len(parts) < 2:
        return name
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def _mla_citation(metadata: dict[str, Any]) -> str:
    """Render common MLA 9 containers for books, journal articles, and chapters."""
    source_type = str(metadata.get("source_type") or metadata.get("document_type") or metadata.get("work_type") or "book").casefold().replace("-", "_").replace(" ", "_")
    author = metadata.get("document_author") or metadata.get("author")
    title = metadata.get("document_title") or metadata.get("title")
    year = metadata.get("publication_year") or metadata.get("year")
    publisher = metadata.get("publisher")
    pages = metadata.get("pages") or metadata.get("page_range")
    doi = str(metadata.get("doi") or "").strip()
    url = str(metadata.get("url") or "").strip()
    opening = (_mla_author_name(author).rstrip(". ") + ". ") if author else ""

    if source_type in {"article", "journal_article", "article_journal", "journal"}:
        article = f'“{str(title).strip().strip(chr(34))}.”' if title else ""
        journal = str(metadata.get("journal_title") or metadata.get("container_title") or "").strip()
        parts = []
        if journal: parts.append(journal)
        if metadata.get("volume") not in (None, ""): parts.append(f"vol. {metadata.get('volume')}")
        if metadata.get("issue") not in (None, ""): parts.append(f"no. {metadata.get('issue')}")
        if year not in (None, ""): parts.append(str(year))
        if pages: parts.append(f"pp. {str(pages).replace('–','-')}")
        if doi: parts.append(doi if doi.startswith("http") else f"https://doi.org/{doi.removeprefix('doi:').strip()}")
        elif url: parts.append(url)
        tail = ", ".join(parts).rstrip(". ") + ("." if parts else "")
        return " ".join(part for part in [opening.strip(), article, tail] if part).strip()

    if source_type in {"chapter", "book_chapter", "chapter_in_book", "entry"}:
        chapter = f'“{str(title).strip().strip(chr(34))}.”' if title else ""
        container = str(metadata.get("container_title") or metadata.get("book_title") or "").strip()
        parts = []
        if container: parts.append(container)
        editor = str(metadata.get("editor") or "").strip()
        if editor: parts.append(f"edited by {editor}")
        translator = str(metadata.get("translator") or "").strip()
        if translator: parts.append(f"translated by {translator}")
        if publisher: parts.append(str(publisher).strip())
        if year not in (None, ""): parts.append(str(year))
        if pages: parts.append(f"pp. {str(pages).replace('–','-')}")
        tail = ", ".join(parts).rstrip(". ") + ("." if parts else "")
        return " ".join(part for part in [opening.strip(), chapter, tail] if part).strip()

    # Default: standalone book / monograph.
    opening_parts = []
    if author: opening_parts.append(_mla_author_name(str(author)).rstrip(". ") + ".")
    if title: opening_parts.append(str(title).strip().rstrip(". ") + ".")
    publication = []
    if metadata.get("translator"): publication.append(f"Translated by {str(metadata.get('translator')).strip()}")
    if metadata.get("editor"): publication.append(f"Edited by {str(metadata.get('editor')).strip()}")
    if metadata.get("edition"): publication.append(str(metadata.get("edition")).strip())
    if publisher: publication.append(str(publisher).strip())
    if year not in (None, ""): publication.append(str(year).strip())
    tail = ", ".join(part for part in publication if part)
    if tail: tail = tail.rstrip(". ") + "."
    return " ".join([*opening_parts, tail] if tail else opening_parts).strip()


def _mla_book_citation(*, author: str | None, title: str | None, translator: str | None = None, edition: str | None = None, publisher: str | None = None, year: int | str | None = None) -> str:
    return _mla_citation({
        "source_type": "book", "document_author": author, "document_title": title,
        "translator": translator, "edition": edition, "publisher": publisher, "publication_year": year,
    })


