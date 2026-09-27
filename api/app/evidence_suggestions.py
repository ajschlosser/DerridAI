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


PRECEDENT_SEMANTIC_METHOD = "precedent-semantic-v1"
PRECEDENT_LEXICAL_METHOD = "precedent-lexical-v1"
_SPAN_LOCATION_KEYS = ("source_unit_id", "page", "pdf_page", "printed_page_label", "start", "end", "speaker")


def record_source_blocks(record: dict[str, Any], blocks_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """This record's own source blocks, in record order, with only the location keys its medium has.

    Membership comes from ``source_block_ids``; a block that is not listed there is never a candidate,
    so nothing ranked here can bind evidence outside the record under review.
    """
    spans = {
        str(span.get("block_id")): span
        for span in record.get("source_spans") or []
        if isinstance(span, dict) and span.get("block_id")
    }
    out: list[dict[str, Any]] = []
    for block_id in dict.fromkeys(map(str, record.get("source_block_ids") or [])):
        block = blocks_by_id.get(block_id)
        text = str((block or {}).get("text") or "")
        if not text.strip():
            continue
        unit: dict[str, Any] = {"block_id": block_id, "text": text}
        location = {**(block or {}), **spans.get(block_id, {})}
        unit.update({key: location[key] for key in _SPAN_LOCATION_KEYS if location.get(key) not in (None, "")})
        out.append(unit)
    return out


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


def rank_blocks_for_texts(
    queries: list[str],
    blocks: list[dict[str, Any]],
    *,
    embed: Any = None,
    limit: int = 3,
) -> tuple[list[list[dict[str, Any]]], str]:
    """Rank the record's blocks against each query text (a precedent's reviewed evidence).

    The query is only a search key: its text is never copied into the result. Each candidate names one
    of ``blocks`` by ID with its score and method. ``embed`` (texts -> vectors) gives semantic ranking;
    without it, or if it fails, a conservative token-overlap score is used and the method says so.
    Returns one ranked list per query, and the method used.
    """
    if not queries or not blocks:
        return [[] for _ in queries], PRECEDENT_LEXICAL_METHOD
    scores: list[list[float]] | None = None
    method = PRECEDENT_SEMANTIC_METHOD
    if embed is not None:
        try:
            vectors = embed([*queries, *(str(block["text"]) for block in blocks)])
            if len(vectors) == len(queries) + len(blocks):
                query_vectors = [list(map(float, v)) for v in vectors[: len(queries)]]
                block_vectors = [list(map(float, v)) for v in vectors[len(queries):]]
                scores = [[_cosine(q, b) for b in block_vectors] for q in query_vectors]
        except Exception:  # noqa: BLE001 - ranking is advisory; lexical ranking below stays available
            scores = None
    if scores is None:
        method = PRECEDENT_LEXICAL_METHOD
        block_tokens = [set(_tokens(str(block["text"]))) for block in blocks]
        scores = []
        for query in queries:
            wanted = set(_tokens(query))
            scores.append([
                (len(wanted & toks) / len(wanted | toks)) if (wanted | toks) else 0.0 for toks in block_tokens
            ])
    ranked: list[list[dict[str, Any]]] = []
    for row in scores:
        order = sorted(range(len(blocks)), key=lambda index: (-row[index], index))
        picks = []
        for index in order[: max(0, int(limit))]:
            score = max(0.0, min(1.0, row[index]))
            if score <= 0:
                continue
            unit = {key: value for key, value in blocks[index].items() if key != "text"}
            picks.append({**unit, "score": round(score, 4), "method": method})
        ranked.append(picks)
    return ranked, method


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
