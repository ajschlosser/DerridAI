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

"""Deterministic detection of printed page numbers in plain-text sources.

Text converted from print often keeps page furniture: ``[32]``, ``{32}``, ``(32)``,
``Page 32``, ``- 32 -``, a bare ``32`` on its own line, a spelled-out "Page thirty-two",
Roman numerals in front matter, form feeds between pages, or a number beside a repeated
running title. Every one of those is a *candidate*. A candidate becomes a page marker only
when the candidates form a plausible sequence: increasing, mostly consecutive, and with
enough text between them to be pages (which rejects numbered lists and chapter numbers).

Pure functions, no I/O, no models. The result names the pattern, convention and confidence
so it can be shown to a reviewer and carried as provenance.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from typing import Any

DETECTOR_VERSION = 2
MAX_PAGE = 20000
_OPEN, _CLOSE = r"[\[\(\{<]", r"[\]\)\}>]"

_ROMAN = re.compile(r"^(?=[ivxlcdm]+$)m{0,3}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$", re.I)

_EN_UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
             "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
             "seventeen": 17, "eighteen": 18, "nineteen": 19}
_EN_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_FR_UNITS = {"zéro": 0, "zero": 0, "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7,
             "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15,
             "seize": 16}
_FR_TENS = {"vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50, "soixante": 60}


def roman_to_int(value: str) -> int | None:
    text = value.strip().lower()
    if not text or not _ROMAN.match(text):
        return None
    numerals = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    total = 0
    for index, char in enumerate(text):
        current = numerals[char]
        nxt = numerals[text[index + 1]] if index + 1 < len(text) else 0
        total += -current if current < nxt else current
    return total if 0 < total < 4000 else None


def words_to_int(value: str) -> int | None:
    """English or French number words up to 999 ("thirty-two", "quatre-vingt-dix-sept")."""
    words = [w.rstrip(".,") for w in re.split(r"[\s\-]+", value.strip().lower().replace("’", "'")) if w]
    words = [w for w in words if w not in {"and", "et"}]
    if not words:
        return None
    # French vigesimal: "quatre-vingt(s)" is eighty, so it must be read as one unit.
    joined = " ".join(words)
    total = 0
    if "quatre vingt" in joined:
        total += 80
        joined = joined.replace("quatre vingts", " ").replace("quatre vingt", " ")
        words = joined.split()
    for word in words:
        if word in _EN_UNITS:
            total += _EN_UNITS[word]
        elif word in _EN_TENS:
            total += _EN_TENS[word]
        elif word in _FR_UNITS:
            total += _FR_UNITS[word]
        elif word in _FR_TENS:
            total += _FR_TENS[word]
        elif word == "vingt":
            total += 20
        elif word in {"hundred", "cent", "cents"}:
            total = max(total, 1) * 100 if total < 100 else total + 100
        else:
            return None
    return total if 0 < total < 1000 else None


@dataclass
class Candidate:
    index: int            # paragraph index the marker sits in
    line: int             # absolute line index
    value: int
    style: str            # bracket | keyword | dash | bare | slash | words | inline
    roman: bool = False
    standalone: bool = True
    confidence: float = 0.5


@dataclass
class Detection:
    status: str = "not_found"          # detected | not_found | disabled
    markers: list[Candidate] = field(default_factory=list)
    convention: str = "start"          # start (marker opens the page) | end (marker closes it)
    confidence: float = 0.0
    pattern: str = ""
    reason: str = ""

    def summary(self) -> dict[str, Any]:
        return {
            "version": DETECTOR_VERSION, "status": self.status, "pattern": self.pattern,
            "convention": self.convention, "confidence": round(self.confidence, 3),
            "marker_count": len(self.markers), "reason": self.reason,
            "first": self.markers[0].value if self.markers else None,
            "last": self.markers[-1].value if self.markers else None,
        }


def _num(token: str) -> tuple[int, bool] | None:
    token = token.strip()
    if token.isdigit() and 0 < int(token) <= MAX_PAGE and len(token) <= 5:
        return int(token), False
    roman = roman_to_int(token)
    if roman is not None:
        return roman, True
    return None


_KEYWORD = r"(?:page|pages|pg|pp?|p\.?|pag|s|seite|folio|f|fol)\b\.?"
_LINE_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("bracket", re.compile(rf"^{_OPEN}\s*(?:{_KEYWORD}\s*)?(?P<n>[0-9]{{1,5}}|[ivxlcdm]{{1,8}})\s*[.,]?\s*{_CLOSE}$", re.I), 0.9),
    ("keyword", re.compile(rf"^(?:{_KEYWORD})\s*(?P<n>[0-9]{{1,5}}|[ivxlcdm]{{1,8}})(?:\s*(?:of|/|sur|von)\s*\d+)?\s*[.:]?$", re.I), 0.85),
    ("dash", re.compile(r"^[-–—·•*~_=]{1,3}\s*(?P<n>[0-9]{1,5}|[ivxlcdm]{1,8})\s*[-–—·•*~_=]{1,3}$", re.I), 0.85),
    ("slash", re.compile(r"^(?P<n>[0-9]{1,5})\s*/\s*[0-9]{1,5}$"), 0.7),
    ("bare", re.compile(r"^(?P<n>[0-9]{1,5}|[ivxlcdm]{1,8})[.]?$", re.I), 0.4),
]
_WORDS_LINE = re.compile(r"^(?:page|pg|p\.?|seite)\s+(?P<w>[A-Za-zéèêûôîï'’\- ]{3,40}?)\s*[.:]?$", re.I)
_INLINE = [
    ("inline", re.compile(rf"(?<![\w]){_OPEN}\s*(?:page|pg|pp?\.?)\s*(?P<n>[0-9]{{1,5}})\s*{_CLOSE}", re.I), 0.85),
    ("inline", re.compile(r"(?<![\w\]\)])\{(?P<n>[0-9]{1,5})\}(?![\w])"), 0.7),
]
_HEADER_NUM = re.compile(r"^(?:(?P<a>\d{1,5})\s{2,}(?P<t1>\S.{2,80})|(?P<t2>\S.{2,80}?)\s{2,}(?P<b>\d{1,5}))$")


def _lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def find_candidates(text: str) -> tuple[list[Candidate], list[str]]:
    lines = _lines(text)
    out: list[Candidate] = []
    paragraph = 0
    previous_blank = True
    for line_index, raw in enumerate(lines):
        stripped = raw.strip().strip("\f")
        if not stripped:
            if not previous_blank:
                paragraph += 1
            previous_blank = True
            continue
        found = False
        if len(stripped) <= 40:
            for style, pattern, confidence in _LINE_PATTERNS:
                match = pattern.match(stripped)
                if match:
                    parsed = _num(match.group("n"))
                    if parsed:
                        out.append(Candidate(paragraph, line_index, parsed[0], style, parsed[1], True, confidence))
                        found = True
                        break
            if not found:
                match = _WORDS_LINE.match(stripped)
                if match:
                    value = words_to_int(match.group("w"))
                    if value:
                        out.append(Candidate(paragraph, line_index, value, "words", False, True, 0.8))
                        found = True
        if not found:
            for style, pattern, confidence in _INLINE:
                for match in pattern.finditer(stripped):
                    parsed = _num(match.group("n"))
                    if parsed:
                        out.append(Candidate(paragraph, line_index, parsed[0], style, False, False, confidence))
        previous_blank = False
        # A form feed ends a physical page: the last number on the page is a footer candidate
        # (handled through the bare pattern above); nothing extra is needed here.
    return out, lines


def _running_header_candidates(lines: list[str]) -> list[Candidate]:
    """``32   THE TITLE`` / ``THE TITLE   32`` where the title repeats: the number is a folio."""
    rows: list[tuple[int, int, str]] = []
    for index, raw in enumerate(lines):
        match = _HEADER_NUM.match(raw.strip())
        if not match:
            continue
        if match.group("a") is not None:
            number, title = match.group("a"), match.group("t1")
        else:
            number, title = match.group("b"), match.group("t2")
        if not (0 < int(number) <= MAX_PAGE):
            continue
        rows.append((index, int(number), re.sub(r"\s+", " ", title.strip().casefold())))
    if len(rows) < 3:
        return []
    counts: dict[str, int] = {}
    for _i, _n, title in rows:
        counts[title] = counts.get(title, 0) + 1
    # Even/odd pages often alternate two titles (book title / chapter title): keep the two commonest.
    common = {title for title, count in sorted(counts.items(), key=lambda kv: -kv[1])[:2] if count >= 3}
    return [Candidate(0, i, n, "header", False, True, 0.8) for i, n, title in rows if title in common]



def _best_chain(
    candidates: list[Candidate],
    max_gap: int = 12,
) -> list[Candidate]:
    """Return the longest position-ordered, increasing page-number chain.

    Dynamic programming tracks the best chain ending at each candidate. Page
    values may skip by at most max_gap so missing scans do not destroy a real
    sequence, while chapter/list numbers with large jumps remain unlikely to
    qualify.
    """
    ordered_candidates = sorted(
        candidates,
        key=lambda candidate: (candidate.line, candidate.value),
    )
    candidate_count = len(ordered_candidates)
    if not candidate_count:
        return []

    chain_length_at = [1] * candidate_count
    previous_index = [-1] * candidate_count

    for current_index in range(candidate_count):
        for earlier_index in range(current_index):
            page_step = (
                ordered_candidates[current_index].value
                - ordered_candidates[earlier_index].value
            )
            proposed_length = chain_length_at[earlier_index] + 1
            if (
                1 <= page_step <= max_gap
                and proposed_length > chain_length_at[current_index]
            ):
                chain_length_at[current_index] = proposed_length
                previous_index[current_index] = earlier_index

    chain_end_index = max(
        range(candidate_count),
        key=lambda index: (
            chain_length_at[index],
            -ordered_candidates[index].line,
        ),
    )
    chain: list[Candidate] = []
    while chain_end_index != -1:
        chain.append(ordered_candidates[chain_end_index])
        chain_end_index = previous_index[chain_end_index]
    return list(reversed(chain))


def _between(
    lines: list[str],
    first_marker: Candidate,
    second_marker: Candidate,
) -> int:
    """Count prose characters between two page-marker candidates."""
    if second_marker.line == first_marker.line:
        return 0

    covered_lines = lines[first_marker.line : second_marker.line + 1]
    character_count = sum(len(line) for line in covered_lines)
    if first_marker.standalone:
        character_count -= len(lines[first_marker.line])
    if second_marker.standalone:
        character_count -= len(lines[second_marker.line])
    return character_count


def _accept(
    chain: list[Candidate],
    lines: list[str],
    total_candidates: int,
) -> tuple[bool, float, str]:
    """Decide whether a candidate chain behaves like printed pagination."""
    if len(chain) < 2:
        return False, 0.0, "too few candidates"

    strong_styles = {
        "bracket",
        "keyword",
        "dash",
        "words",
        "inline",
        "header",
        "llm",
    }
    strong_marker_count = sum(
        1 for candidate in chain if candidate.style in strong_styles
    )
    consecutive_pair_count = sum(
        1
        for first_marker, second_marker in zip(chain, chain[1:])
        if second_marker.value - first_marker.value == 1
    )
    consecutive_ratio = consecutive_pair_count / (len(chain) - 1)

    # Real pages normally contain substantial text between folios. This is the
    # main guard against accepting numbered lists or chapter headings as pages.
    text_gaps = [
        _between(lines, first_marker, second_marker)
        for first_marker, second_marker in zip(chain, chain[1:])
    ]
    median_text_gap = statistics.median(text_gaps) if text_gaps else 0
    bare_numbers_only = strong_marker_count == 0

    if bare_numbers_only:
        if (
            len(chain) < 4
            or consecutive_ratio < 0.7
            or median_text_gap < 250
        ):
            return False, 0.0, "bare numbers do not look like page numbers"
    else:
        if len(chain) < 3 and strong_marker_count < 2:
            return False, 0.0, "too few marked candidates"
        if median_text_gap < 60 and len(chain) < 6:
            return False, 0.0, "markers too close together to be pages"

    candidate_coverage = len(chain) / max(1, total_candidates)
    confidence = min(
        0.99,
        0.45
        + 0.25 * consecutive_ratio
        + 0.15 * min(1.0, len(chain) / 8)
        + 0.14 * (strong_marker_count / len(chain))
        + 0.05 * candidate_coverage,
    )
    return True, confidence, ""


def detect(text: str) -> Detection:
    """Detect printed page markers without invoking a model.

    Detection never raises for uncertain input; an unresolved sequence is
    returned as status "not_found" with a reason suitable for diagnostics.
    """
    if not text.strip():
        return Detection(reason="empty text")

    candidates, lines = find_candidates(text)
    candidates += _running_header_candidates(lines)
    if not candidates:
        return Detection(reason="no page-number patterns")

    # Roman front matter and Arabic body pagination are separate sequences.
    # Evaluate them independently instead of letting the transition between
    # numbering systems break an otherwise valid chain.
    arabic_candidates = [
        candidate for candidate in candidates if not candidate.roman
    ]
    roman_candidates = [
        candidate for candidate in candidates if candidate.roman
    ]

    best_detection: Detection | None = None
    for numbering_candidates in (arabic_candidates, roman_candidates):
        chain = _best_chain(numbering_candidates)
        accepted, confidence, reason = _accept(
            chain,
            lines,
            len(numbering_candidates),
        )
        if not accepted:
            if best_detection is None:
                best_detection = Detection(reason=reason)
            continue

        styles = sorted(
            {candidate.style for candidate in chain},
            key=lambda style: -sum(
                1 for candidate in chain if candidate.style == style
            ),
        )
        detection = Detection(
            "detected",
            chain,
            "start",
            confidence,
            styles[0],
        )
        if (
            best_detection is None
            or best_detection.status != "detected"
            or len(detection.markers) > len(best_detection.markers)
        ):
            best_detection = detection

    detection = best_detection or Detection(reason="no plausible sequence")
    if detection.status == "detected":
        detection.convention = _convention(detection, lines)
        # Both Roman front matter and Arabic body pagination can be valid. The
        # longer accepted chain wins; the shorter is ignored rather than merged
        # across two incompatible numbering systems.
    return detection

MAX_LLM_CANDIDATES = 120
_LLM_LINE = re.compile(r"(?:\d|\b(?:page|pg|p)\b|^[ivxlcdm]{1,8}[.)]?$)", re.I)



def llm_candidates(
    text: str,
    limit: int = MAX_LLM_CANDIDATES,
) -> list[dict[str, Any]]:
    """Return bounded page-furniture candidates for model classification.

    The model may classify only these existing lines; it cannot invent a page
    number or source position. When a document has too many candidates, keep
    both ends and sample the middle so prompt cost remains bounded.
    """
    lines = _lines(text)
    candidate_line_indexes = [
        line_index
        for line_index, raw_line in enumerate(lines)
        if 0 < len(raw_line.strip()) <= 48
        and _LLM_LINE.search(raw_line.strip())
    ]

    if len(candidate_line_indexes) > limit:
        edge_count = limit // 4
        head_indexes = candidate_line_indexes[:edge_count]
        tail_indexes = candidate_line_indexes[-edge_count:]
        middle_indexes = candidate_line_indexes[edge_count:-edge_count]
        middle_budget = limit - len(head_indexes) - len(tail_indexes)
        sampling_step = max(1, len(middle_indexes) // middle_budget)
        candidate_line_indexes = (
            head_indexes
            + middle_indexes[::sampling_step][:middle_budget]
            + tail_indexes
        )

    candidates: list[dict[str, Any]] = []
    for candidate_id, line_index in enumerate(candidate_line_indexes):
        preceding_text = next(
            (
                lines[context_index].strip()
                for context_index in range(
                    line_index - 1,
                    max(-1, line_index - 4),
                    -1,
                )
                if lines[context_index].strip()
            ),
            "",
        )
        following_text = next(
            (
                lines[context_index].strip()
                for context_index in range(
                    line_index + 1,
                    min(len(lines), line_index + 4),
                )
                if lines[context_index].strip()
            ),
            "",
        )
        candidates.append(
            {
                "id": candidate_id,
                "line": line_index,
                "text": lines[line_index].strip(),
                "before": preceding_text[:60],
                "after": following_text[:60],
            }
        )
    return candidates

def _value_in(line: str) -> tuple[int, bool] | None:
    for token in re.findall(r"[0-9]{1,5}|[ivxlcdm]{1,8}", line, re.I):
        parsed = _num(token)
        if parsed:
            return parsed
    words = _WORDS_LINE.match(line.strip())
    if words:
        value = words_to_int(words.group("w"))
        if value:
            return value, False
    return None



def detect_with_llm(text: str, ask: Any) -> Detection:
    """Classify page-number candidates with a model, then validate deterministically.

    ask(candidates) returns IDs of lines classified as printed page numbers.
    Model selection is only advisory: selected lines must still form a
    plausible increasing sequence with enough text between markers.
    """
    candidates = llm_candidates(text)
    if len(candidates) < 3:
        return Detection(reason="too few candidate lines for a model to judge")

    selected_candidate_ids = set(ask(candidates))
    lines = _lines(text)
    selected_markers: list[Candidate] = []
    for candidate in candidates:
        if candidate["id"] not in selected_candidate_ids:
            continue
        parsed_page_number = _value_in(candidate["text"])
        if parsed_page_number:
            value, is_roman = parsed_page_number
            selected_markers.append(
                Candidate(
                    0,
                    candidate["line"],
                    value,
                    "llm",
                    is_roman,
                    True,
                    0.7,
                )
            )

    arabic_chain = _best_chain(
        [marker for marker in selected_markers if not marker.roman]
    )
    accepted, confidence, reason = _accept(
        arabic_chain,
        lines,
        len(selected_markers),
    )
    if not accepted:
        return Detection(
            reason=f"the model's page numbers were rejected: {reason}"
        )

    detection = Detection(
        "detected",
        arabic_chain,
        "start",
        min(confidence, 0.8),
        "llm",
    )
    detection.convention = _convention(detection, lines)
    return detection

def _convention(detection: Detection, lines: list[str]) -> str:
    """Return whether markers open pages ("start") or close them ("end")."""
    markers = detection.markers
    start_marker_styles = {
        "bracket",
        "keyword",
        "inline",
        "words",
        "header",
    }
    if all(marker.style in start_marker_styles for marker in markers):
        return "start"

    text_gaps = [
        _between(lines, first_marker, second_marker)
        for first_marker, second_marker in zip(markers, markers[1:])
    ]
    median_text_gap = statistics.median(text_gaps) if text_gaps else 0
    characters_before_first_marker = sum(
        len(line) for line in lines[: markers[0].line]
    )

    # If roughly a full page of text precedes the first marker, a bare folio
    # almost certainly closes that page rather than opening the next one.
    if (
        median_text_gap
        and characters_before_first_marker >= 0.6 * median_text_gap
    ):
        return "end"
    return "start"

