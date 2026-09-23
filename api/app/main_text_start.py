# Copyright 2026 Aaron John Schlosser, PhD.
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

WEIGHTS = {"outline_first_chapter": 0.75, "first_chapter_heading": 0.65, "page_numbering_restarts": 0.5, "front_matter_ends": 0.45, "outline_after_front_matter": 0.5}

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


def _clues(pages: dict[int, list[str]], labels: dict[int, str | None], outline: list[tuple[int, str]], page_count: int) -> list[dict[str, Any]]:
    clues: list[dict[str, Any]] = []
    contents_pages = {p for p, lines in pages.items() if _looks_like_contents(lines) or any(_FRONT_HEADING.match(x) and re.match(r"^\s*(?:table|contents)", x, re.I) for x in lines[:3])}

    for page, title in outline:
        if 1 <= page <= page_count and (_FIRST_CHAPTER.match(title) or _NUMBERED_FIRST.match(title)):
            clues.append({"page": page, "kind": "outline_first_chapter", "detail": f'Bookmark "{title.strip()}" points to PDF page {page}.'})
            break

    entries = [(p, t) for p, t in outline if 1 <= p <= page_count]
    last_front = max((i for i, (p, t) in enumerate(entries) if p <= max(1, page_count // 3) and _FRONT_HEADING.match(t)), default=None)
    if last_front is not None:
        # The first bookmark after the front matter, skipping an introduction (which may or may not be main text).
        after = next(((p, t) for p, t in entries[last_front + 1 :] if not _INTRO.match(t) and p > entries[last_front][0]), None)
        if after is not None:
            clues.append({"page": after[0], "kind": "outline_after_front_matter", "detail": f'Bookmark "{after[1].strip()}" is the first after the front matter (PDF page {after[0]}.'})

    for page in sorted(pages):
        if page in contents_pages:
            continue
        lines = pages[page]
        head = [x for x in lines[:4]]
        hit = next((x for x in head if _FIRST_CHAPTER.match(x) or _NUMBERED_FIRST.match(x)), None)
        if hit is None and len(head) >= 2 and re.match(r"^\s*(?:chapter|chapitre)\s*$", head[0], re.I) and _BARE_FIRST.match(head[1]):
            hit = f"{head[0]} {head[1]}"
        if hit:
            clues.append({"page": page, "kind": "first_chapter_heading", "detail": f'"{hit[:60]}" appears as a heading on PDF page {page}.'})
            break

    first_arabic = next((p for p in sorted(labels) if str(labels[p] or "") == "1"), None)
    if first_arabic:
        earlier = [labels[p] for p in sorted(labels) if p < first_arabic and labels[p]]
        if earlier and sum(bool(_ROMAN.match(str(x))) for x in earlier) >= 2:
            clues.append({"page": first_arabic, "kind": "page_numbering_restarts", "detail": f"Roman numerals give way to page 1 on PDF page {first_arabic}."})

    front = [p for p in sorted(pages) if p <= max(1, page_count // 3) and pages[p] and (_FRONT_HEADING.match(pages[p][0]) or p in contents_pages)]
    if front:
        run_end = front[0]
        for p in front[1:]:
            if p - run_end <= 3:  # allow a page or two of running front matter between headings
                run_end = p
        # Only the last front-matter heading's section is known to end at the next heading-bearing page.
        following = next((p for p in sorted(pages) if p > run_end and p not in contents_pages and not _FRONT_HEADING.match(pages[p][0])
                          and any(_looks_like_heading(x) for x in pages[p][:2])), None)
        if following:
            clues.append({"page": following, "kind": "front_matter_ends", "detail": f'Front matter ({", ".join(pages[p][0][:24] for p in front[:3])}) ends before PDF page {following}.'})
    return clues


def _looks_like_heading(text: str) -> bool:
    return len(text) < 60 and not text.rstrip().endswith((",", ";", ".", "?", "!", ":")) and bool(re.match(r"^[A-Z0-9“\"]", text))


def infer_main_text_start(
    blocks: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    outline: list[tuple[int, str]] | None = None,
) -> dict[str, Any]:
    """Return {"page", "confidence", "clues", "offered"} for the best candidate.

    `page` and `confidence` describe the best candidate even when it is below the threshold, so the
    evaluation script can measure calibration; `offered` says whether it may be shown as a value.
    """
    page_count = len(pages)
    labels = {int(p["pdf_page"]): (str(p["printed_page_label"]) if p.get("printed_page_label") else None) for p in pages}
    clues = _clues(_page_lines(blocks), labels, list(outline or []), page_count)
    by_page: dict[int, list[dict[str, Any]]] = {}
    for clue in clues:
        by_page.setdefault(int(clue["page"]), []).append(clue)
    if not by_page:
        return {"page": None, "confidence": 0.0, "clues": [], "offered": False}

    def confidence(items: list[dict[str, Any]]) -> float:
        remaining = 1.0
        for item in items:
            remaining *= 1 - WEIGHTS[item["kind"]]
        return 1 - remaining

    scored = sorted(((confidence(v), p) for p, v in by_page.items()), reverse=True)
    best_confidence, best_page = scored[0]
    if len(scored) > 1:
        # Disagreement is evidence against the leader: discount by the strength of the strongest rival.
        best_confidence *= 1 - 0.5 * scored[1][0]
    best_confidence = round(best_confidence, 3)
    return {
        "page": best_page,
        "confidence": best_confidence,
        "clues": by_page[best_page],
        "offered": best_confidence >= CONFIDENCE_THRESHOLD,
    }
