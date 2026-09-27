# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic suggestions of which source blocks likely evidence a field value.

Suggestions are advisory: they never bind evidence. A reviewer must still submit
the chosen block IDs through the evidence patch. Every suggestion carries the
deterministic method and score so it is never mistaken for reviewed evidence.
Text is compared conservatively (case/whitespace/punctuation only); no stopword
removal, so negations and qualifiers are preserved in the overlap measure.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

METHOD = "deterministic-lexical-v1"
EVIDENCE_MODES = ("with_value", "backfill")
DEFAULT_EVIDENCE_MODE = "with_value"
BACKFILL_MIN_SCORE = 0.5
BACKFILL_MAX_BLOCKS = 2


def evidence_mode(request: dict[str, Any] | None = None) -> str:
    """How model-proposed values get evidence: a request's ``evidence_mode`` wins over the setting.

    ``with_value`` (default): the model must cite blocks in the same answer as the value.
    ``backfill``: the model proposes the value only; deterministic suggestion attaches blocks afterwards.
    An unrecognised value falls back to the default rather than silently weakening the requirement.
    """
    from .config import settings

    for candidate in ((request or {}).get("evidence_mode"), settings.metadata_evidence_mode):
        if str(candidate or "").strip().lower() in EVIDENCE_MODES:
            return str(candidate).strip().lower()
    return DEFAULT_EVIDENCE_MODE


def backfill_field_evidence(value: Any, blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Evidence for a value the model proposed without any, or None when no block supports it well enough.

    Never trusted: confidence is unreported (so the field stays pending review and cannot autofill) and the entry
    says it was attached after the fact, with the deterministic score.
    """
    picks = suggest_evidence_blocks(value, blocks, limit=BACKFILL_MAX_BLOCKS, min_score=BACKFILL_MIN_SCORE)
    if not picks:
        return None
    return {
        "block_ids": [item["block_id"] for item in picks],
        "confidence": None,
        "reason": f"Suggested after the value was proposed ({picks[0]['reason']}); not cited by the model.",
        "backfilled": True,
        "method": METHOD,
        "score": picks[0]["score"],
    }
_TOKEN = re.compile(r"\w+", re.UNICODE)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).casefold()
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(_fold(text))


def _flatten(value: Any) -> list[str]:
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, dict):
        return [part for item in value.values() for part in _flatten(item)]
    if isinstance(value, (list, tuple, set)):
        return [part for item in value for part in _flatten(item)]
    text = str(value).strip()
    return [text] if text else []


def suggest_evidence_blocks(
    value: Any,
    blocks: list[dict[str, Any]],
    *,
    limit: int = 5,
    min_score: float = 0.2,
) -> list[dict[str, Any]]:
    """Rank candidate blocks (each with ``block_id`` and ``text``) for a field value."""
    needles = _flatten(value)
    if not needles or not blocks:
        return []
    docs = [(str(b.get("block_id")), str(b.get("text") or "")) for b in blocks if b.get("block_id")]
    doc_tokens = [set(_tokens(text)) for _, text in docs]
    df = Counter(tok for toks in doc_tokens for tok in toks)
    n = max(len(docs), 1)
    scored: list[dict[str, Any]] = []
    for (block_id, text), toks in zip(docs, doc_tokens):
        folded = " ".join(_tokens(text))
        best, reason = 0.0, ""
        for needle in needles:
            n_tokens = _tokens(needle)
            if not n_tokens:
                continue
            phrase = " ".join(n_tokens)
            if phrase in folded:
                score, why = 1.0, "value appears verbatim (ignoring case and punctuation)"
            else:
                weights = {t: math.log(1 + n / (1 + df.get(t, 0))) for t in set(n_tokens)}
                total = sum(weights.values()) or 1.0
                coverage = sum(w for t, w in weights.items() if t in toks) / total
                score, why = 0.85 * coverage, f"{round(coverage * 100)}% of the value's terms occur in this block"
                if len(phrase) <= 400 and coverage > 0.5:
                    ratio = SequenceMatcher(None, phrase, folded[: max(len(phrase) * 6, 200)]).find_longest_match(
                        0, len(phrase), 0, min(len(folded), max(len(phrase) * 6, 200))
                    ).size / len(phrase)
                    if ratio > 0.6:
                        score = min(0.95, score + 0.1 * ratio)
            if score > best:
                best, reason = score, why
        if best >= min_score:
            scored.append({"block_id": block_id, "score": round(best, 3), "reason": reason, "method": METHOD})
    scored.sort(key=lambda item: (-item["score"], item["block_id"]))
    return scored[: max(1, limit)]


LLM_METHOD = "llm-evidence-choice-v1"
_PROMPT_BLOCK_CHARS = 1200


def llm_prompt(field: str, value: Any, blocks: list[dict[str, Any]]) -> str:
    """A closed-choice prompt: the model may only name block IDs listed here."""
    listing = "\n".join(
        f'[{b.get("block_id")}] {str(b.get("text") or "")[:_PROMPT_BLOCK_CHARS]}' for b in blocks
    )
    shown = "; ".join(_flatten(value)) or "(empty)"
    return (
        f'A reviewer must bind evidence for the metadata field "{field}" whose value is: {shown}\n'
        "Below are the source blocks of one record. Choose the smallest set of blocks whose text directly "
        "supports that value (the block that states it, not merely one on the same topic). Do not choose a block "
        "whose only support is an editor's or translator's note unless the value is about that note. If no block "
        "supports the value, return an empty list. Never invent block IDs.\n\n"
        f'{listing}\n\nAnswer as JSON: {{"block_ids": ["id"], "reason": "one sentence"}}'
    )


def validate_llm_choice(
    result: dict[str, Any], blocks: list[dict[str, Any]], value: Any, *, limit: int = 5
) -> list[dict[str, Any]]:
    """Keep only IDs that are real candidate blocks, deduplicated and in the model's order.

    A chosen block that the deterministic scorer finds unrelated is still returned (the
    model may read a paraphrase) but flagged ``lexical_support: false`` so review stays cautious.
    """
    known = {str(b.get("block_id")) for b in blocks}
    lexical = {item["block_id"] for item in suggest_evidence_blocks(value, blocks, limit=len(blocks), min_score=0.2)}
    reason = str(result.get("reason") or "").strip()
    out: list[dict[str, Any]] = []
    for raw in result.get("block_ids") or []:
        block_id = str(raw)
        if block_id in known and all(o["block_id"] != block_id for o in out):
            out.append({"block_id": block_id, "reason": reason, "lexical_support": block_id in lexical})
    return out[: max(1, limit)]
