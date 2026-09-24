# Copyright 2026 Aaron John Schlosser, PhD.
"""Language-agnostic illegibility scoring for extracted record text.

0 means the tokens still look like writing-system words. 100 means the text is
illegible in any language. Tokens are not looked up in a dictionary: bilingual
pages, names, and coinages must be able to pass, while OCR soup must not.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from pydantic import BaseModel, Field

DEFAULT_NOISE_THRESHOLD = 45
LLM_CONFIDENCE_FLOOR = 0.65
TEXT_NOISE_PROMPT_VERSION = "derridai-text-noise-v1"

# Scripts that write vowels (or matres) often enough that a long vowelless token
# is almost never a word. Hebrew/Arabic and CJK are excluded from this test.
_VOWEL_CHARS = set(
    "aeiouyàáâäãåāăąèéêëēėęìíîïīįòóôöõōøùúûüūůýÿœæı"
    "αάεέηήιίϊΐοόυύϋΰωώ"
    "аеёиоуыэюя"
)
_TOKEN_SPLIT = re.compile(r"\s+")
_WRAP_PUNCT = "«»“”\"'‘’()[]{}<>„‚"
_TRAILING_PUNCT = ".,;:!?…»”\"'’)]}"
_LEADING_PUNCT = "«“\"'‘([{"
_OK_INTERIOR = {"-", "‐", "‑", "'", "’", "ʼ", "."}  # hyphen, apostrophe, abbreviation dot
_LLM_MID_BAND = (20.0, 80.0)


class TextNoiseLlmResult(BaseModel):
    """Closed schema for the optional second-reader pass."""

    noise: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(default="", max_length=500)


TEXT_NOISE_LLM_PROMPT = (
    "You score whether extracted scholarly text is still readable as words in any "
    "human language. Do not identify a language and do not correct the text. "
    "Return JSON with noise (0=perfectly legible, 100=illegible), confidence 0..1, "
    "and a short reason. OCR letter substitutions, mixed digits inside words, and "
    "punctuation inside tokens are high noise. Names, bilingual pages, and "
    "philosophical coinages are low noise when the letters still form words."
)


def blend_noise_scores(
    deterministic: float,
    llm_score: float | None = None,
    llm_confidence: float | None = None,
) -> float:
    """Keep the deterministic floor; an LLM may only raise noise."""
    score = max(0.0, min(100.0, float(deterministic)))
    if llm_score is None or llm_confidence is None:
        return score
    if float(llm_confidence) < LLM_CONFIDENCE_FLOOR:
        return score
    return max(score, max(0.0, min(100.0, float(llm_score))))


def should_ask_llm(deterministic_score: float) -> bool:
    """Skip obvious clean text and already-maximal garbage to bound provider cost."""
    low, high = _LLM_MID_BAND
    return low <= float(deterministic_score) <= high


def _letters(token: str) -> str:
    return "".join(ch for ch in token if ch.isalpha())


def _script_key(ch: str) -> str:
    name = unicodedata.name(ch, "")
    return name.split(" ")[0] if name else ""


def _is_malformed_token(raw: str) -> tuple[bool, str | None]:
    """Return whether a whitespace token fails the 'word in any language' shape test."""
    token = raw.strip().strip(_WRAP_PUNCT)
    while token and token[0] in _LEADING_PUNCT:
        token = token[1:]
    while token and token[-1] in _TRAILING_PUNCT:
        token = token[:-1]
    if len(token) < 2:
        return False, None
    if token.isdigit():
        return False, None
    letters = _letters(token)
    has_digit = any(ch.isdigit() for ch in token)
    if letters and has_digit:
        return True, "letter_digit_mix"
    scripts = { _script_key(ch) for ch in letters if _script_key(ch) }
    if len(scripts) > 1 and not scripts <= {"LATIN", "GREEK"}:
        # Latin+Greek appears in this corpus; Latin+CJK in one token is OCR debris.
        if "CJK" in scripts or "HIRAGANA" in scripts or "KATAKANA" in scripts:
            return True, "mixed_scripts"
    for ch in token:
        if ch.isalnum() or ch in _OK_INTERIOR or unicodedata.category(ch) in {"Mn", "Mc"}:
            continue
        if unicodedata.category(ch).startswith("P") or unicodedata.category(ch).startswith("S"):
            return True, "interior_punct"
        if unicodedata.category(ch) == "Cc":
            return True, "control"
    if len(letters) >= 5:
        vowel_scripts = {"LATIN", "GREEK", "CYRILLIC"}
        if scripts and scripts <= vowel_scripts:
            vowels = sum(1 for ch in letters.casefold() if ch in _VOWEL_CHARS)
            if vowels / len(letters) < 0.12:
                return True, "no_sonorant"
    return False, None


def _case_chaos(raw: str) -> bool:
    """Many mid-word capitals are OCR, not a title or a German noun."""
    letters = [ch for ch in raw if ch.isalpha()]
    if len(letters) < 5:
        return False
    internal_caps = sum(1 for ch in letters[1:] if ch.isupper())
    flips = sum(1 for a, b in zip(letters, letters[1:]) if a.isupper() != b.isupper())
    return internal_caps >= 2 or flips >= 3


def score_text_noise(text: str) -> dict[str, Any]:
    """Score one record body. Always deterministic."""
    original = unicodedata.normalize("NFC", str(text or ""))
    compact = "".join(ch for ch in original if not ch.isspace())
    tokens = [part for part in _TOKEN_SPLIT.split(original) if part.strip()]
    malformed = 0
    malformed_chars = 0
    reasons: list[str] = []
    chaos = 0
    for token in tokens:
        dirty, reason = _is_malformed_token(token)
        if dirty:
            malformed += 1
            malformed_chars += len(token)
            if reason and reason not in reasons:
                reasons.append(reason)
        elif _case_chaos(token):
            chaos += 1
            malformed_chars += len(token)
            if "case_chaos" not in reasons:
                reasons.append("case_chaos")
    token_ratio = (malformed + chaos) / max(1, len(tokens))
    char_ratio = malformed_chars / max(1, len(compact))
    replacement = compact.count("\ufffd")
    controls = sum(1 for ch in compact if unicodedata.category(ch) == "Cc")
    alpha = sum(1 for ch in compact if ch.isalpha())
    alpha_ratio = alpha / max(1, len(compact))
    lines = [line.strip() for line in original.splitlines() if line.strip()]
    micro = sum(1 for line in lines if len(line) <= 2)
    micro_ratio = micro / max(1, len(lines)) if lines else 0.0

    # Token malformation dominates. Sparse/corrupt/glyph cases lift the floor so
    # existing trash heuristics still contribute to the same 0–100 scale.
    # Weight by characters so a few long OCR-soup tokens dominate a page of
    # short real words (the usual facing-page failure mode).
    score = 100.0 * min(1.0, max(token_ratio * 1.5, char_ratio * 2.4))
    if len(compact) < 24:
        score = max(score, 80.0)
        reasons.append("very_low_text_density")
    if replacement >= 2 or controls:
        score = max(score, 90.0)
        reasons.append("corrupt_characters")
    if compact and alpha_ratio < 0.25:
        score = max(score, 85.0)
        reasons.append("low_alphabetic_density")
    if lines and micro_ratio >= 0.65:
        score = max(score, 88.0)
        reasons.append("micro_line_fragmentation")
    score = round(max(0.0, min(100.0, score)), 1)
    return {
        "score": score,
        "deterministic_score": score,
        "dirty_token_ratio": round(token_ratio, 4),
        "malformed_token_count": malformed,
        "token_count": len(tokens),
        "reasons": reasons,
        "method": "deterministic",
    }


def fuse_record_noise(
    text_report: dict[str, Any],
    raster_score: float | None,
    *,
    llm_score: float | None = None,
    llm_confidence: float | None = None,
    threshold: float = DEFAULT_NOISE_THRESHOLD,
) -> dict[str, Any]:
    """Combine text, optional raster, and optional LLM into one record score."""
    deterministic = float(text_report.get("deterministic_score") or text_report.get("score") or 0)
    if raster_score is not None:
        deterministic = max(deterministic, float(raster_score))
    blended = blend_noise_scores(deterministic, llm_score, llm_confidence)
    reasons = list(text_report.get("reasons") or [])
    if raster_score is not None and float(raster_score) >= threshold and "low_raster_quality" not in reasons:
        reasons.append("low_raster_quality")
    if blended >= threshold and "high_text_noise" not in reasons:
        reasons.append("high_text_noise")
    method = "deterministic"
    if llm_score is not None:
        method = "deterministic+llm"
    report = dict(text_report)
    report.update({
        "score": round(blended, 1),
        "deterministic_score": round(deterministic, 1),
        "raster_score": None if raster_score is None else round(float(raster_score), 1),
        "llm_score": None if llm_score is None else round(float(llm_score), 1),
        "llm_confidence": None if llm_confidence is None else round(float(llm_confidence), 4),
        "threshold": float(threshold),
        "unusable": blended >= float(threshold),
        "reasons": reasons,
        "method": method,
    })
    return report


def raster_score_for_pages(record: dict[str, Any], pages: list[dict[str, Any]] | None) -> float | None:
    """Typical raster noise across the pages this record spans; None if unavailable.

    A single damaged page is retained in page-level source diagnostics, but must
    not make an otherwise readable multi-page record unusable by itself.
    """
    if not pages:
        return None
    wanted = {int(value) for value in (record.get("pdf_pages") or []) if isinstance(value, int)}
    scores: list[float] = []
    for page in pages:
        page_no = int(page.get("pdf_page") or 0)
        if wanted and page_no not in wanted:
            continue
        raster = page.get("raster") if isinstance(page.get("raster"), dict) else None
        if not raster:
            continue
        try:
            scores.append(float(raster.get("noise")))
        except (TypeError, ValueError):
            continue
    if not scores:
        return None
    scores.sort()
    middle = len(scores) // 2
    if len(scores) % 2:
        return scores[middle]
    return (scores[middle - 1] + scores[middle]) / 2


def median_score(records: list[dict[str, Any]]) -> float | None:
    scores: list[float] = []
    for record in records:
        noise = record.get("text_noise") if isinstance(record.get("text_noise"), dict) else None
        if not noise:
            continue
        try:
            scores.append(float(noise.get("score")))
        except (TypeError, ValueError):
            continue
    if not scores:
        return None
    scores.sort()
    mid = len(scores) // 2
    if len(scores) % 2:
        return round(scores[mid], 1)
    return round((scores[mid - 1] + scores[mid]) / 2, 1)


def threshold_from_records(records: list[dict[str, Any]]) -> float:
    for record in records:
        noise = record.get("text_noise") if isinstance(record.get("text_noise"), dict) else None
        if noise and noise.get("threshold") is not None:
            try:
                return float(noise["threshold"])
            except (TypeError, ValueError):
                break
    return float(DEFAULT_NOISE_THRESHOLD)


def annotate_records(
    records: list[dict[str, Any]],
    *,
    pages: list[dict[str, Any]] | None = None,
    threshold: float = DEFAULT_NOISE_THRESHOLD,
) -> None:
    """Write ``text_noise`` onto each record from text + page raster."""
    for record in records:
        text_report = score_text_noise(str(record.get("text") or ""))
        raster = raster_score_for_pages(record, pages)
        record["text_noise"] = fuse_record_noise(text_report, raster, threshold=threshold)
