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
    citation_head = " ".join(part for part in (last, str(year or "")) if part).strip()
    if pages:
        inline = f"{citation_head}: {pages}" if citation_head else f"{work}: {pages}".strip(": ")
    else:
        inline = citation_head or work

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
