# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Citation formatting shared by Corpus Builder and Research without retrieval imports."""

from __future__ import annotations

import re
from typing import Any

from .bibliography import _mla_author_name, _mla_citation
from .research_semantics import (
    SPEAKER_ID,
    semantic_text,
    source_author,
    source_work_label,
)


def _citation_strings(record: dict[str, Any]) -> tuple[str, str]:
    author = source_author(record) or semantic_text(record, SPEAKER_ID)
    work = source_work_label(record)
    edition = str(record.get("edition") or "")
    year = record.get("year") or ""
    page_start = record.get("page_start")
    page_end = record.get("page_end")
    translator = str(record.get("translator") or "")

    last = author.split()[-1] if author.split() else author
    if page_start is None:
        pages = ""
    elif page_end is None or page_end == page_start:
        pages = str(page_start)
    else:
        pages = f"{page_start}-{page_end}"
    timed_spans = [span for span in record.get("source_spans") or []
                   if span.get("locator_kind") == "time"]
    if timed_spans:
        from .source_audio import _timestamp_label

        pages = "; ".join(
            _timestamp_label(float(span["start"]), float(span["end"]))
            + (f" [{span['speaker']}]" if span.get("speaker") else "")
            for span in timed_spans
        )
    if year:
        citation_head = " ".join(part for part in (last, str(year)) if part).strip()
    elif last and work:
        # Author-only page citations are ambiguous when a Research answer uses
        # multiple works by the same author. Without a year, retain the work
        # title in the inline citation rather than fabricating bibliographic data.
        citation_head = f"{last}, {work}"
    else:
        citation_head = last
    if pages:
        inline = f"{citation_head}: {pages}" if citation_head else pages
    else:
        inline = citation_head

    parts = author.split()
    reversed_name = (
        f"{parts[-1]}, {' '.join(parts[:-1])}"
        if len(parts) > 1 else author
    )
    full = (
        # No author is assumed: when the record names none, the citation simply omits it.
        f"{reversed_name + '. ' if reversed_name else ''}{work}."
        f"{f' {translator} trans.' if translator else ''}"
        f"{f' {edition}.' if edition else ''}"
        f"{f' {year}.' if year else ''}"
    )
    return inline.strip(), re.sub(r"\s+", " ", full).strip()


def _markdown_italic(value: str) -> str:
    """Mark a title for italics unless its own characters would break the markup."""
    text = value.strip()
    if not text or "*" in text or text[0] == "_" or text[-1] == "_":
        return text
    return f"*{text}*"


def _mla_metadata(record: dict[str, Any]) -> dict[str, Any]:
    publisher = str(record.get("publisher") or "").strip()
    edition = str(record.get("edition") or "").strip()
    return {
        "source_type": record.get("source_type") or record.get("document_type") or "book",
        "document_author": source_author(record),
        "document_title": source_work_label(record),
        "translator": record.get("translator"),
        "editor": record.get("editor"),
        # Ingestion stores the publisher as the edition when no edition is known.
        "edition": "" if edition and edition == publisher else edition,
        "publisher": publisher,
        "publication_year": record.get("publication_year") or record.get("year"),
        "container_title": record.get("container_title") or record.get("book_title"),
        "journal_title": record.get("journal_title"),
        "volume": record.get("volume"),
        "issue": record.get("issue"),
        "doi": record.get("doi"),
        "url": record.get("url"),
    }


def mla_works_cited_entry(record: dict[str, Any]) -> str:
    """One MLA 9 Works Cited entry from recorded metadata; titles carry Markdown italics.

    Values are formatted, never corrected: a wrong recorded year stays visible for review.
    """
    return re.sub(r"\s+", " ", _mla_citation(_mla_metadata(record), emphasis=_markdown_italic)).strip()


def _mla_locator(record: dict[str, Any]) -> str:
    timed = [span for span in record.get("source_spans") or [] if span.get("locator_kind") == "time"]
    if timed:
        from .source_audio import _timestamp_label

        return "; ".join(_timestamp_label(float(span["start"]), float(span["end"])) for span in timed)
    start, end = record.get("page_start"), record.get("page_end")
    if start is None:
        return ""
    return str(start) if end is None or end == start else f"{start}\u2013{end}"


def mla_in_text(record: dict[str, Any], *, include_title: bool) -> str:
    """MLA 9 parenthetical citation: author and locator, adding the title when one
    author has several cited works or the Record names no author."""
    author = source_author(record)
    last = author.split()[-1] if author.split() else ""
    title = source_work_label(record)
    head = last
    if title and (include_title or not last):
        italic = _markdown_italic(title)
        head = f"{last}, {italic}" if last else italic
    locator = _mla_locator(record)
    body = " ".join(part for part in (head, locator) if part)
    # Nothing recorded to cite: no citation rather than an empty "()".
    return f"({body})" if body else ""


def _sort_key(entry: str) -> str:
    plain = entry.replace("*", "").casefold()
    return re.sub(r"^(a|an|the)\s+", "", plain)


def mla_works_cited(records: list[dict[str, Any]], extra: list[str] | tuple[str, ...] = ()) -> list[str]:
    """Alphabetical MLA 9 Works Cited, one entry per work, with three hyphens for a
    repeated author. ``extra`` entries (recorded citations whose Record is not
    available) are sorted in as written."""
    seen: set[str] = set()
    entries: list[tuple[str, str, str]] = [(_sort_key(entry), "", entry) for entry in dict.fromkeys(extra) if entry]
    for record in records:
        entry = mla_works_cited_entry(record)
        key = str(record.get("canonical_work_id") or entry)
        if not entry or key in seen or entry in {item[2] for item in entries}:
            continue
        seen.add(key)
        author = source_author(record)
        prefix = (_mla_author_name(author).rstrip(". ") + ". ") if author else ""
        entries.append((_sort_key(entry), prefix, entry))
    entries.sort(key=lambda item: item[0])
    out: list[str] = []
    previous = None
    for _, prefix, entry in entries:
        if prefix and prefix == previous and entry.startswith(prefix):
            out.append("---. " + entry[len(prefix):])
        else:
            out.append(entry)
        previous = prefix or None
    return out
