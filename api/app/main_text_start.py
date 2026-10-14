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

"""Infer the first page of a PDF's main text from the document's own structure.

Main text is the canonical text by the main author, after prefaces, prologues, editors'
introductions and the like. An author's own introduction is not automatically main text, so
"Introduction" is never treated as a start marker here.

Each clue is deterministic and votes for one PDF page with a weight. Clues that agree on a page
combine as independent evidence (1 - product of (1 - weight)); a rival page backed by real evidence
lowers the result. A value is offered only at CONFIDENCE_THRESHOLD or above, and always with the
clues that produced it so a person can review it. The weights are starting estimates, not measured
probabilities: scripts/evaluate_main_text_start.py measures precision against reviewer-confirmed
layouts, and the weights should be adjusted from that, not from intuition.
"""

from __future__ import annotations

import re
from typing import Any

CONFIDENCE_THRESHOLD = 0.9

WEIGHTS = {
    "outline_first_chapter": 0.75,
    "first_chapter_heading": 0.65,
    "page_numbering_restarts": 0.5,
    "front_matter_ends": 0.45,
    "outline_after_front_matter": 0.5,
}

_NUMBER_WORDS = r"(?:one|two|first|i|1)"
_FIRST_CHAPTER = re.compile(rf"^\s*(?:chapter|chap\.|chapitre|part|book|livre|partie)\s+{_NUMBER_WORDS}\b[\s.:—–-]*(?:.{{0,80}})?$", re.I)
# "1. Title", "1 Title", "I. Title", "One" as a heading of its own. A bare capital I needs its full stop, or "I think" would match.
_NUMBERED_FIRST = re.compile(r"^\s*(?:(?:1|one|first)(?:[.):—–-]|\s)\s*(?![a-z\d]).{0,80}|I[.):—–-]\s*\S.{0,80})$")
_INTRO = re.compile(r"^\s*(?:introduction|prologue|prolog|foreword|preface|avant-propos|pr[eé]face)\b", re.I)
_BARE_FIRST = re.compile(r"^\s*(?:1|i|one)[.)]?\s*$", re.I)
_FRONT_HEADING = re.compile(
    r"^\s*(?:contents|table of contents|table des mati[eè]res|preface|pr[eé]face|foreword|avant-propos|acknowledg\w+|"
    r"remerciements|prologue|list of (?:illustrations|figures|abbreviations)|abbreviations|note on \w+|editor.?s? (?:note|introduction)|"
    r"translator.?s? (?:note|introduction)|dedication|epigraph)\b",
    re.I,
)
_ROMAN = re.compile(r"^[ivxlcdm]+$", re.I)


def _page_lines(blocks: list[dict[str, Any]]) -> dict[int, list[str]]:
    pages: dict[int, list[str]] = {}
    for block in blocks:
        if block.get("type") == "header_footer":
            continue
        text = " ".join(str(block.get("text") or "").split())
        if text:
            pages.setdefault(int(block.get("page") or 0), []).append(text)
    return pages


def _looks_like_contents(lines: list[str]) -> bool:
    """A contents page is mostly short lines that end in a page number."""
    if len(lines) < 4:
        return False
    numbered = sum(bool(re.search(r"(?:\s|\.)(?:\d{1,4}|[ivxlc]{1,6})$", line, re.I)) and len(line) < 120 for line in lines)
    return numbered / len(lines) >= 0.5


def _clues(
    pages: dict[int, list[str]],
    labels: dict[int, str | None],
    outline: list[tuple[int, str]],
    page_count: int,
) -> list[dict[str, Any]]:
    """Collect deterministic clues that vote for a main-text start page."""
    clues: list[dict[str, Any]] = []
    contents_page_numbers = {
        page_number
        for page_number, page_lines in pages.items()
        if _looks_like_contents(page_lines)
        or any(
            _FRONT_HEADING.match(line)
            and re.match(r"^\s*(?:table|contents)", line, re.I)
            for line in page_lines[:3]
        )
    }

    # A first-chapter bookmark is the strongest structural clue because it is
    # explicit document navigation rather than a typography inference.
    for page_number, title in outline:
        if (
            1 <= page_number <= page_count
            and (_FIRST_CHAPTER.match(title) or _NUMBERED_FIRST.match(title))
        ):
            clues.append(
                {
                    "page": page_number,
                    "kind": "outline_first_chapter",
                    "detail": (
                        f'Bookmark "{title.strip()}" points to PDF page '
                        f"{page_number}."
                    ),
                }
            )
            break

    valid_outline_entries = [
        (page_number, title)
        for page_number, title in outline
        if 1 <= page_number <= page_count
    ]
    last_front_matter_index = max(
        (
            index
            for index, (page_number, title) in enumerate(valid_outline_entries)
            if page_number <= max(1, page_count // 3)
            and _FRONT_HEADING.match(title)
        ),
        default=None,
    )
    if last_front_matter_index is not None:
        last_front_matter_page = valid_outline_entries[last_front_matter_index][0]
        # Skip an Introduction because an author's own introduction is not
        # automatically the start of the canonical main text.
        first_after_front_matter = next(
            (
                (page_number, title)
                for page_number, title in valid_outline_entries[
                    last_front_matter_index + 1 :
                ]
                if not _INTRO.match(title)
                and page_number > last_front_matter_page
            ),
            None,
        )
        if first_after_front_matter is not None:
            page_number, title = first_after_front_matter
            clues.append(
                {
                    "page": page_number,
                    "kind": "outline_after_front_matter",
                    "detail": (
                        f'Bookmark "{title.strip()}" is the first after the '
                        f"front matter (PDF page {page_number})."
                    ),
                }
            )

    for page_number in sorted(pages):
        if page_number in contents_page_numbers:
            continue
        page_lines = pages[page_number]
        heading_lines = page_lines[:4]
        first_chapter_heading = next(
            (
                line
                for line in heading_lines
                if _FIRST_CHAPTER.match(line) or _NUMBERED_FIRST.match(line)
            ),
            None,
        )
        if (
            first_chapter_heading is None
            and len(heading_lines) >= 2
            and re.match(
                r"^\s*(?:chapter|chapitre)\s*$",
                heading_lines[0],
                re.I,
            )
            and _BARE_FIRST.match(heading_lines[1])
        ):
            first_chapter_heading = f"{heading_lines[0]} {heading_lines[1]}"
        if first_chapter_heading:
            clues.append(
                {
                    "page": page_number,
                    "kind": "first_chapter_heading",
                    "detail": (
                        f'"{first_chapter_heading[:60]}" appears as a heading '
                        f"on PDF page {page_number}."
                    ),
                }
            )
            break

    first_arabic_page = next(
        (
            page_number
            for page_number in sorted(labels)
            if str(labels[page_number] or "") == "1"
        ),
        None,
    )
    if first_arabic_page:
        earlier_labels = [
            labels[page_number]
            for page_number in sorted(labels)
            if page_number < first_arabic_page and labels[page_number]
        ]
        roman_label_count = sum(
            bool(_ROMAN.match(str(label))) for label in earlier_labels
        )
        if earlier_labels and roman_label_count >= 2:
            clues.append(
                {
                    "page": first_arabic_page,
                    "kind": "page_numbering_restarts",
                    "detail": (
                        "Roman numerals give way to page 1 on PDF page "
                        f"{first_arabic_page}."
                    ),
                }
            )

    front_matter_pages = [
        page_number
        for page_number in sorted(pages)
        if page_number <= max(1, page_count // 3)
        and pages[page_number]
        and (
            _FRONT_HEADING.match(pages[page_number][0])
            or page_number in contents_page_numbers
        )
    ]
    if front_matter_pages:
        front_matter_run_end = front_matter_pages[0]
        for page_number in front_matter_pages[1:]:
            # Allow one or two running front-matter pages between headings.
            if page_number - front_matter_run_end <= 3:
                front_matter_run_end = page_number

        # We only know that the last front-matter section has ended once a
        # subsequent page supplies its own heading-like structural evidence.
        following_heading_page = next(
            (
                page_number
                for page_number in sorted(pages)
                if page_number > front_matter_run_end
                and page_number not in contents_page_numbers
                and not _FRONT_HEADING.match(pages[page_number][0])
                and any(
                    _looks_like_heading(line)
                    for line in pages[page_number][:2]
                )
            ),
            None,
        )
        if following_heading_page:
            front_matter_labels = ", ".join(
                pages[page_number][0][:24]
                for page_number in front_matter_pages[:3]
            )
            clues.append(
                {
                    "page": following_heading_page,
                    "kind": "front_matter_ends",
                    "detail": (
                        f"Front matter ({front_matter_labels}) ends before PDF "
                        f"page {following_heading_page}."
                    ),
                }
            )
    return clues

def _looks_like_heading(text: str) -> bool:
    return len(text) < 60 and not text.rstrip().endswith((",", ";", ".", "?", "!", ":")) and bool(re.match(r"^[A-Z0-9“\"]", text))


def infer_main_text_start(
    blocks: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    outline: list[tuple[int, str]] | None = None,
) -> dict[str, Any]:
    """Return the best main-text start candidate and its supporting clues.

    Page and confidence describe the best candidate even below the display
    threshold so the evaluation script can measure calibration. Offered
    indicates whether the candidate is strong enough to present as a proposed
    value for human review.
    """
    page_count = len(pages)
    printed_label_by_pdf_page = {
        int(page["pdf_page"]): (
            str(page["printed_page_label"])
            if page.get("printed_page_label")
            else None
        )
        for page in pages
    }
    clues = _clues(
        _page_lines(blocks),
        printed_label_by_pdf_page,
        list(outline or []),
        page_count,
    )
    clues_by_page: dict[int, list[dict[str, Any]]] = {}
    for clue in clues:
        clues_by_page.setdefault(int(clue["page"]), []).append(clue)

    if not clues_by_page:
        return {
            "page": None,
            "confidence": 0.0,
            "clues": [],
            "offered": False,
        }

    def combined_confidence(page_clues: list[dict[str, Any]]) -> float:
        """Combine agreeing clues as independent pieces of evidence."""
        remaining_uncertainty = 1.0
        for clue in page_clues:
            remaining_uncertainty *= 1 - WEIGHTS[clue["kind"]]
        return 1 - remaining_uncertainty

    scored_pages = sorted(
        (
            (combined_confidence(page_clues), page_number)
            for page_number, page_clues in clues_by_page.items()
        ),
        reverse=True,
    )
    best_confidence, best_page = scored_pages[0]
    if len(scored_pages) > 1:
        # Disagreement is evidence against the leader. Discount it by half the
        # strength of the strongest independently supported rival page.
        strongest_rival_confidence = scored_pages[1][0]
        best_confidence *= 1 - 0.5 * strongest_rival_confidence

    best_confidence = round(best_confidence, 3)
    return {
        "page": best_page,
        "confidence": best_confidence,
        "clues": clues_by_page[best_page],
        "offered": best_confidence >= CONFIDENCE_THRESHOLD,
    }
