# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic, offline pre-fill of work-level metadata from a source's front matter.

Two kinds of evidence, labelled differently so a reviewer can tell them apart:

* ``computed``: exact patterns (an ISBN with a valid check digit, a copyright year, a line that says
  "Translated by ..."). Confidence is high because a pattern either matches or it does not.
* ``nlp_derived``: a statistical tagger's judgement (an ORG that looks like a publisher, a GPE or LOC
  beside it as the place of publication). Confidence is lower and the tagger and model are named.

Every candidate records the exact span it came from. Nothing here is a claim about the *meaning* of
a passage; it fills bibliographic blanks that the reviewer confirms. Lower-confidence alternatives are
kept beside the value that won so they can be offered as suggestions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

HEAD_CHARS = 6000
_STOPWORDS = {
    "en": {"the", "and", "of", "to", "in", "is", "that", "it", "with", "for", "as", "was", "by"},
    "fr": {"le", "la", "les", "de", "des", "et", "un", "une", "du", "que", "est", "dans", "pour", "par"},
    "de": {"der", "die", "das", "und", "ist", "nicht", "mit", "von", "zu", "den", "ein", "eine", "für"},
}
_PUBLISHER_WORDS = re.compile(
    r"\b(press|publishers?|publishing|books?|éditions?|editions|editore|editorial|verlag|gallimard|seuil|"
    r"minuit|flammarion|routledge|blackwell|harvard|oxford|cambridge|yale|princeton|chicago|stanford|"
    r"suhrkamp|fayard|puf|galilée|galilee)\b", re.I,
)
_YEAR = r"(?:1[5-9]\d{2}|20\d{2})"
_COPYRIGHT_YEAR = re.compile(
    rf"(?:©|\(c\)|copyright|copr\.?|first published|published|publié|première édition|erstveröffentlicht)"
    rf"\D{{0,40}}((?:{_YEAR})(?:\s*[,;&]\s*(?:and\s+)?(?:{_YEAR}))*)", re.I,
)
_ISBN = re.compile(r"\bISBN(?:-1[03])?\s*[:=]?\s*((?:97[89][\- ]?)?[\dX][\d\- ]{8,15}[\dX])\b", re.I)
_ROLE_LINES = [
    ("translator", re.compile(r"^(?:translated|translation)\s+(?:by|from\b.*\bby)\s+(?P<n>[^.,;\n]{3,80})", re.I | re.M)),
    ("translator", re.compile(r"^(?:traduit|traduction)\s+(?:de\s+\w+\s+)?par\s+(?P<n>[^.,;\n]{3,80})", re.I | re.M)),
    ("translator", re.compile(r"^(?:übersetzt|übersetzung)\s+von\s+(?P<n>[^.,;\n]{3,80})", re.I | re.M)),
    ("editor", re.compile(r"^(?:edited|editor|ed\.)\s*(?:by)?\s*:?\s+(?P<n>[^.,;\n]{3,80})", re.I | re.M)),
    ("editor", re.compile(r"^(?:édité|édition établie|présenté)\s+par\s+(?P<n>[^.,;\n]{3,80})", re.I | re.M)),
]
_PUBLISHED_BY = re.compile(
    r"(?:published by|publisher\s*:|publié par|édité par|éditeur\s*:|verlag\s*:|©\s*\d{4}\s+(?:by\s+)?)\s*(?P<p>[^\n,;.]{3,80})(?:[,;]\s*(?P<c>[A-ZÉ][^\n,;.]{2,40}))?",
    re.I,
)


class _Shifted:
    """A year match whose span is relative to the whole text rather than its notice."""

    def __init__(self, match: re.Match[str], offset: int) -> None:
        self._match, self._offset = match, offset

    def group(self, index: int = 0) -> str:
        return self._match.group(index)

    def span(self, index: int = 0) -> tuple[int, int]:
        a, b = self._match.span(index)
        return a + self._offset, b + self._offset


@dataclass
class Candidate:
    field: str
    value: str
    method: str
    derivation: str            # computed | nlp_derived
    confidence: float
    reason: str
    span: tuple[int, int]
    extra: dict[str, Any] = dc_field(default_factory=dict)


def guess_language(text: str) -> str:
    """en / fr / de by stopword frequency; '' when unclear. Deterministic."""
    words = re.findall(r"[^\W\d_]+", text[:4000].lower())
    if len(words) < 30:
        return ""
    scores = {code: sum(1 for w in words if w in stops) / len(words) for code, stops in _STOPWORDS.items()}
    best = max(scores, key=lambda k: scores[k])
    ordered = sorted(scores.values(), reverse=True)
    return best if ordered[0] > 0.06 and ordered[0] > 1.3 * ordered[1] else ""


def _isbn_valid(digits: str) -> bool:
    if len(digits) == 10:
        total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(digits))
        return total % 11 == 0
    if len(digits) == 13 and digits.isdigit():
        return sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(digits)) % 10 == 0
    return False


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .,:;-–—\t")


def computed_candidates(text: str) -> list[Candidate]:
    out: list[Candidate] = []
    for match in _ISBN.finditer(text):
        digits = re.sub(r"[^0-9Xx]", "", match.group(1)).upper()
        if _isbn_valid(digits):
            out.append(Candidate("isbn", digits, "pattern:isbn", "computed", 0.97,
                                 "ISBN with a valid check digit.", match.span(1)))
    years = [(int(y.group(0)), y) for m in _COPYRIGHT_YEAR.finditer(text) for y in re.finditer(_YEAR, m.group(1))
             for y in [_Shifted(y, m.start(1))]]
    if years:
        # The earliest year named beside "published"/"©" is the first publication; later ones are reprints.
        year, match = min(years, key=lambda item: item[0])
        out.append(Candidate("publication_year", str(year), "pattern:copyright_year", "computed", 0.9,
                             "Year beside a copyright or publication notice.", match.span(0)))
        seen = {year}
        for other, other_match in years:
            if other not in seen:
                seen.add(other)
                out.append(Candidate("publication_year", str(other), "pattern:copyright_year", "computed", 0.55,
                                     "A later year in the same notices (likely a reprint or edition).", other_match.span(0)))
    for name, pattern in _ROLE_LINES:
        for match in pattern.finditer(text):
            person = _clean(match.group("n"))
            if person and len(person.split()) <= 6:
                out.append(Candidate(name, person, f"pattern:{name}_line", "computed", 0.88,
                                     f"A line that says who the {name} is.", match.span("n")))
                break
    published = _PUBLISHED_BY.search(text)
    if published:
        publisher = _clean(published.group("p"))
        if publisher and len(publisher) <= 60:
            out.append(Candidate("publisher", publisher, "pattern:published_by", "computed", 0.85,
                                 "A 'published by' notice.", published.span("p")))
            if published.group("c"):
                out.append(Candidate("publication_place", _clean(published.group("c")), "pattern:published_by_place", "computed", 0.7,
                                     "A place written right after the publisher's name.", published.span("c")))
    return out


def nlp_candidates(text: str, language: str) -> list[Candidate]:
    """Publisher and place of publication from a statistical tagger's ORG / GPE / LOC entities."""
    from . import nlp_annotations

    code = nlp_annotations.language_code(language) or guess_language(text)
    pipeline = nlp_annotations.load_pipeline(code) if code else None
    if pipeline is None:
        return []
    doc = pipeline(text[:HEAD_CHARS])
    model = nlp_annotations._model_name(code) or ""
    method = f"nlp:spacy:{model}"
    entities = [e for e in doc.ents if e.label_ == "ORG"]
    named = [e for e in entities if _PUBLISHER_WORDS.search(e.text)]
    if not named:
        return []
    places = [e for e in doc.ents if e.label_ in {"GPE", "LOC"}]
    out: list[Candidate] = []
    publisher = max(named, key=lambda e: len(e.text))
    # Earlier mentions often drop the last word ("The Johns Hopkins University" ... "... University Press").
    mentions = [e for e in entities if e.text in publisher.text or publisher.text in e.text]
    out.append(Candidate("publisher", _clean(publisher.text), f"{method}:org_publisher_word", "nlp_derived", 0.72,
                         "An organisation whose name looks like a publisher.", (publisher.start_char, publisher.end_char)))

    def gap(place: Any) -> int:
        return min(
            max(0, place.start_char - m.end_char, m.start_char - place.end_char) for m in mentions
        )

    # Title pages print the publisher's place with its name; the nearest place, first in reading order on a tie.
    near = sorted((p for p in places if gap(p) <= 120), key=lambda p: (gap(p), p.start_char))
    if near:
        best = near[0]
        out.append(Candidate("publication_place", _clean(best.text), f"{method}:place_near_publisher", "nlp_derived", 0.7,
                             f"A place named within {gap(best)} characters of the publisher “{_clean(publisher.text)}”.",
                             (best.start_char, best.end_char), {"publisher": _clean(publisher.text)}))
        for other in near[1:3]:
            out.append(Candidate("publication_place", _clean(other.text), f"{method}:place_near_publisher", "nlp_derived", 0.5,
                                 "Another place near the publisher.", (other.start_char, other.end_char)))
    return out


def extract(text: str, *, language: str = "", use_nlp: bool = True) -> list[Candidate]:
    """Candidates from the front matter of ``text`` (never raises)."""
    head = text[:HEAD_CHARS]
    found = computed_candidates(head)
    if use_nlp:
        try:
            found += nlp_candidates(head, language)
        except Exception:  # a broken model removes hints, never the ingest
            pass
    return found
