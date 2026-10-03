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

"""Keep corpus record boundaries on sentence ends.

PDF blocks are layout units: a block, a column or a page can stop in the middle of a sentence, and
a language model that proposes record boundaries can pick any of them. A record is a unit people
quote and cite, so it must not start or stop mid-sentence. This module is the deterministic check
that enforces that after segmentation, whatever proposed the boundaries.

A boundary "after block B" is clean when B ends a sentence (or is not running text, such as a
heading) and the block after it does not continue one. An unclean boundary is moved to the nearest
clean one between its neighbours; if there is none it is dropped, which joins the two records. The build's record ceiling is authoritative: a boundary is moved only to a point that keeps both
records within `hard_max_chars`, and dropped only when the joined record stays within it. Otherwise
it is kept where it is and reported, so a reviewer sees a record that ends mid-sentence rather than
one that silently outgrows the size the build asked for.

What this cannot know with certainty: punctuation can be ambiguous, and text with no sentence
punctuation at all (verse, lists, OCR noise, or languages whose written conventions do not expose
reliable sentence marks in the source) may have no deterministic sentence end to find. The shared
language profile therefore uses conservative continuation and abbreviation rules, and the size cap
remains authoritative rather than manufacturing a linguistic boundary.
"""

from __future__ import annotations

from typing import Any

from .language_segmentation import (
    ends_sentence_text,
    looks_like_heading_line,
    split_sentences,
    starts_mid_sentence_text,
)

_RUNNING_TEXT = {"body", "paragraph", "text"}


def _block_language(block: dict[str, Any], fallback: str | None = None) -> str | None:
    value = str(block.get("thread_language") or "").strip()
    return value or fallback


def ends_sentence(block: dict[str, Any], language: str | None = None) -> bool:
    """True when a block can be the last block of a record."""
    language = _block_language(block, language)
    text = str(block.get("text") or "").rstrip()
    if not text:
        return True
    if str(block.get("type") or "body") not in _RUNNING_TEXT:
        return True
    if looks_like_heading_line(text, language):
        return True
    return ends_sentence_text(text, language)


def starts_mid_sentence(block: dict[str, Any], language: str | None = None) -> bool:
    language = _block_language(block, language)
    text = str(block.get("text") or "")
    if str(block.get("type") or "body") not in _RUNNING_TEXT:
        return False
    return starts_mid_sentence_text(text, language)


def clean_boundary(
    left: dict[str, Any],
    right: dict[str, Any],
    language: str | None = None,
) -> bool:
    left_language = _block_language(left, language)
    right_language = _block_language(right, language)
    if not ends_sentence(left, left_language) or starts_mid_sentence(right, right_language):
        return False
    left_text = str(left.get("text") or "").rstrip()
    right_text = str(right.get("text") or "").lstrip()
    same_language = (
        not left_language
        or not right_language
        or left_language.casefold() == right_language.casefold()
    )
    if (
        same_language
        and left_text.endswith(".")
        and right_text
        and str(left.get("type") or "body") in _RUNNING_TEXT
        and str(right.get("type") or "body") in _RUNNING_TEXT
    ):
        # A block-final period may be an abbreviation ("Dr.") rather than a
        # sentence boundary. Re-run the shared lossless splitter across the seam;
        # only accept the seam when the first sentence really ends with the
        # complete left block.
        probe = f"{left_text} {right_text}"
        sentences = split_sentences(probe, left_language or right_language)
        if not sentences or sentences[0].strip() != left_text:
            return False
    return True


def snap_boundaries_to_sentences(
    blocks: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
    hard_max_chars: int = 12000,
    *,
    language: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return boundaries that fall on sentence ends, plus a report of what changed.

    `boundaries` are dicts with `after_block_id`; other keys travel with a boundary that is kept or
    moved. The last block of the document always ends a record whatever it says.
    """
    index_of = {str(block.get("block_id")): i for i, block in enumerate(blocks)}
    cuts = sorted({index_of[str(b["after_block_id"])] for b in boundaries if str(b.get("after_block_id")) in index_of})
    evidence = {index_of[str(b["after_block_id"])]: b for b in boundaries if str(b.get("after_block_id")) in index_of}
    lengths = [len(str(block.get("text") or "")) for block in blocks]
    last = len(blocks) - 1
    report: dict[str, Any] = {"moved": [], "merged": [], "unavoidable": []}

    def clean(i: int) -> bool:
        return i >= last or clean_boundary(blocks[i], blocks[i + 1], language)

    def span(start: int, end: int) -> int:
        """Characters in blocks start..end inclusive, counted as records count them (units joined by a blank line)."""
        return sum(lengths[start : end + 1]) + 2 * max(0, end - start)

    result: list[int] = []
    origin: dict[int, int] = {}
    previous = -1
    for position, cut in enumerate(cuts):
        following = cuts[position + 1] if position + 1 < len(cuts) else last
        if cut >= last:
            continue
        if clean(cut):
            result.append(cut)
            origin[cut] = cut
            previous = cut
            continue
        # Nearest clean boundary strictly between the neighbouring cuts that keeps both records within the ceiling.
        candidates = [
            i for i in range(previous + 1, min(following, last))
            if clean(i)
            and span(previous + 1, i) <= hard_max_chars
            and span(i + 1, following) <= hard_max_chars
        ]
        if candidates:
            target = min(candidates, key=lambda i: (abs(i - cut), i - cut))
            result.append(target)
            origin[target] = cut
            previous = target
            report["moved"].append({"from": str(blocks[cut]["block_id"]), "to": str(blocks[target]["block_id"])})
            continue
        # None: drop it, joining this record to the next, unless that makes it too large.
        if span(previous + 1, following) <= hard_max_chars:
            report["merged"].append({"dropped": str(blocks[cut]["block_id"])})
            continue
        result.append(cut)
        origin[cut] = cut
        previous = cut
        report["unavoidable"].append({"after_block_id": str(blocks[cut]["block_id"]), "reason": "sentence_longer_than_record_limit"})

    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for i in result:
        if i in seen:
            continue
        seen.add(i)
        base = dict(evidence.get(origin[i], {}))
        base["after_block_id"] = str(blocks[i]["block_id"])
        if origin[i] != i:
            base["moved_to_sentence_end_from"] = str(blocks[origin[i]]["block_id"])
        out.append(base)
    return out, report
