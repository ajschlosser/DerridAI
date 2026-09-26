# Copyright 2026 Aaron John Schlosser, PhD.
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

DETECTOR_VERSION = 1
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


def _best_chain(cands: list[Candidate], max_gap: int = 12) -> list[Candidate]:
    """Longest increasing chain by value with bounded jumps, ordered by position."""
    ordered = sorted(cands, key=lambda c: (c.line, c.value))
    n = len(ordered)
    if not n:
        return []
    best = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            step = ordered[i].value - ordered[j].value
            if 1 <= step <= max_gap and best[j] + 1 > best[i]:
                best[i], prev[i] = best[j] + 1, j
    end = max(range(n), key=lambda k: (best[k], -ordered[k].line))
    chain: list[Candidate] = []
    while end != -1:
        chain.append(ordered[end])
        end = prev[end]
    return list(reversed(chain))


def _between(lines: list[str], a: Candidate, b: Candidate) -> int:
    """Characters of text between two markers (inline markers share a line with prose)."""
    if b.line == a.line:
        return 0
    return sum(len(x) for x in lines[a.line:b.line + 1]) - (len(lines[a.line]) if a.standalone else 0) - (len(lines[b.line]) if b.standalone else 0)


def _accept(chain: list[Candidate], lines: list[str], total_candidates: int) -> tuple[bool, float, str]:
    if len(chain) < 2:
        return False, 0.0, "too few candidates"
    strong = sum(1 for c in chain if c.style in {"bracket", "keyword", "dash", "words", "inline", "header", "llm"})
    consecutive = sum(1 for a, b in zip(chain, chain[1:]) if b.value - a.value == 1)
    ratio = consecutive / (len(chain) - 1)
    # Text volume between markers: pages hold text; numbered lists and chapter numbers do not.
    gaps = [_between(lines, a, b) for a, b in zip(chain, chain[1:])]
    median_gap = statistics.median(gaps) if gaps else 0
    bare_only = strong == 0
    if bare_only:
        if len(chain) < 4 or ratio < 0.7 or median_gap < 250:
            return False, 0.0, "bare numbers do not look like page numbers"
    else:
        if len(chain) < 3 and strong < 2:
            return False, 0.0, "too few marked candidates"
        if median_gap < 60 and len(chain) < 6:
            return False, 0.0, "markers too close together to be pages"
    coverage = len(chain) / max(1, total_candidates)
    confidence = min(0.99, 0.45 + 0.25 * ratio + 0.15 * min(1.0, len(chain) / 8) + 0.14 * (strong / len(chain)) + 0.05 * coverage)
    return True, confidence, ""


def detect(text: str) -> Detection:
    """Detect page markers in ``text``. Never raises; returns status ``not_found`` if unsure."""
    if not text.strip():
        return Detection(reason="empty text")
    candidates, lines = find_candidates(text)
    candidates += _running_header_candidates(lines)
    if not candidates:
        return Detection(reason="no page-number patterns")
    # Arabic and Roman sequences are separate: front matter is numbered in Roman numerals.
    arabic = [c for c in candidates if not c.roman]
    roman = [c for c in candidates if c.roman]
    best: Detection | None = None
    for group in (arabic, roman):
        chain = _best_chain(group)
        ok, confidence, reason = _accept(chain, lines, len(group))
        if not ok:
            if best is None:
                best = Detection(reason=reason)
            continue
        styles = sorted({c.style for c in chain}, key=lambda s: -sum(1 for c in chain if c.style == s))
        detection = Detection("detected", chain, "start", confidence, styles[0])
        if best is None or best.status != "detected" or len(detection.markers) > len(best.markers):
            best = detection
    detection = best or Detection(reason="no plausible sequence")
    if detection.status == "detected":
        detection.convention = _convention(detection, lines)
        # A Roman front-matter sequence and an Arabic body sequence can both exist; the longer wins here
        # and the shorter is intentionally ignored rather than guessed at.
    return detection


MAX_LLM_CANDIDATES = 120
_LLM_LINE = re.compile(r"(?:\d|\b(?:page|pg|p)\b|^[ivxlcdm]{1,8}[.)]?$)", re.I)


def llm_candidates(text: str, limit: int = MAX_LLM_CANDIDATES) -> list[dict[str, Any]]:
    """Short lines that *might* be page furniture, with a little context, for a model to classify.

    The model only chooses among these lines; it never supplies a number or a position. Sampling keeps the
    first and last lines and spreads the rest, so a long text costs a bounded prompt.
    """
    lines = _lines(text)
    picked = [
        i for i, raw in enumerate(lines)
        if 0 < len(raw.strip()) <= 48 and _LLM_LINE.search(raw.strip())
    ]
    if len(picked) > limit:
        head, tail = picked[: limit // 4], picked[-(limit // 4):]
        middle = picked[limit // 4: -(limit // 4)]
        step = max(1, len(middle) // (limit - len(head) - len(tail)))
        picked = head + middle[::step][: limit - len(head) - len(tail)] + tail
    out = []
    for n, i in enumerate(picked):
        before = next((lines[j].strip() for j in range(i - 1, max(-1, i - 4), -1) if lines[j].strip()), "")
        after = next((lines[j].strip() for j in range(i + 1, min(len(lines), i + 4)) if lines[j].strip()), "")
        out.append({"id": n, "line": i, "text": lines[i].strip(), "before": before[:60], "after": after[:60]})
    return out


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
    """Let a model pick the page-number lines, then hold its answer to the same sequence rules.

    ``ask(candidates)`` returns the ids of lines that are printed page numbers. A model's say-so is not
    enough: the chosen lines must still form an increasing, mostly consecutive sequence with real text
    between them, so a hallucinated answer cannot invent page numbers.
    """
    candidates = llm_candidates(text)
    if len(candidates) < 3:
        return Detection(reason="too few candidate lines for a model to judge")
    chosen = set(ask(candidates))
    lines = _lines(text)
    picked: list[Candidate] = []
    for item in candidates:
        if item["id"] not in chosen:
            continue
        parsed = _value_in(item["text"])
        if parsed:
            picked.append(Candidate(0, item["line"], parsed[0], "llm", parsed[1], True, 0.7))
    arabic = _best_chain([c for c in picked if not c.roman])
    ok, confidence, reason = _accept(arabic, lines, len(picked))
    if not ok:
        return Detection(reason=f"the model's page numbers were rejected: {reason}")
    detection = Detection("detected", arabic, "start", min(confidence, 0.8), "llm")
    detection.convention = _convention(detection, lines)
    return detection


def _convention(detection: Detection, lines: list[str]) -> str:
    """Does a marker open its page (bracket/keyword styles) or close it (a bare footer folio)?"""
    markers = detection.markers
    if all(m.style in {"bracket", "keyword", "inline", "words", "header"} for m in markers):
        return "start"
    gaps = [_between(lines, a, b) for a, b in zip(markers, markers[1:])]
    median_gap = statistics.median(gaps) if gaps else 0
    head = sum(len(x) for x in lines[: markers[0].line])
    # If the text before the first folio is a full page, folios are footers.
    return "end" if median_gap and head >= 0.6 * median_gap else "start"
