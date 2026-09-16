# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import copy
import math
import re
from collections import Counter
from typing import Any

_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’\-]{1,}")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ0-9\"“‘(])")
_SUMMARY_DELIMITER = " [...] "
_STOPWORDS = {
    "the","a","an","and","or","but","of","to","in","on","for","with","as","at","by","from","that","this","these","those","is","are","was","were","be","been","being","it","its","he","she","they","them","we","you","i","his","her","their","our","your","not","no","if","then","than","which","who","whom","what","when","where","how","why","de","la","le","les","des","du","un","une","et","ou","mais","dans","sur","pour","avec","comme","par","que","qui","ce","ces","cette","il","elle","ils","elles","nous","vous","ne","pas","au","aux","en",
}


def _terms(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        source = " ".join(str(item) for item in value)
    else:
        source = str(value)
    return [token.lower() for token in _WORD_RE.findall(source) if len(token) > 1]


def _bounded_piece(text: str, max_chars: int) -> str:
    max_chars = max(1, int(max_chars))
    compact = " ".join(str(text or "").split())
    if len(compact) <= max_chars:
        return compact
    if max_chars <= 1:
        return compact[:max_chars]
    return compact[: max_chars - 1].rstrip() + "…"


def _score_sentences(sentences: list[str], bonus_words: list[str]) -> list[tuple[float, int, str]]:
    all_words = [word.lower() for sentence in sentences for word in _WORD_RE.findall(sentence)]
    counts = Counter(word for word in all_words if word not in _STOPWORDS and len(word) > 2)
    max_count = max(counts.values(), default=1)
    bonus = {word.lower() for word in bonus_words if word}
    cue_words = {
        "therefore","thus","hence","because","however","indeed","notably","namely","consequently",
        "ainsi","donc","cependant","pourtant","notamment",
    }
    scored: list[tuple[float, int, str]] = []
    total = len(sentences)
    for index, sentence in enumerate(sentences):
        tokens = [word.lower() for word in _WORD_RE.findall(sentence)]
        if not tokens:
            continue
        frequency = sum(counts.get(word, 0) / max_count for word in tokens) / math.sqrt(len(tokens))
        bonus_score = sum(2.6 for word in tokens if word in bonus)
        cue_score = sum(0.7 for word in tokens if word in cue_words)
        position_score = 1.2 if index == 0 else 0.7 if index == 1 else 0.45 if index == total - 1 else 0.0
        scored.append((frequency + bonus_score + cue_score + position_score, index, sentence))
    return scored


def edmundson_summary(
    text: str,
    *,
    bonus_words: list[str],
    max_chars: int = 1600,
    max_sentences: int = 3,
) -> str:
    """Dependency-free Edmundson-style extractive summary for researcher views.

    The strongest 2–3 available sentences are selected using keyword frequency,
    explicit bonus terms, cue words, and sentence position. Extracts are restored
    to source order and separated with ``" [...] "`` so omitted material is always
    visually explicit. Output is bounded by ``max_chars`` and never returns more
    than three sentence extracts.
    """
    max_chars = max(1, int(max_chars))
    max_sentences = max(1, min(3, int(max_sentences)))
    compact = " ".join(str(text or "").split())
    if not compact:
        return ""
    sentences = [part.strip() for part in _SENTENCE_RE.split(compact) if part.strip()]
    if len(sentences) <= 1:
        return _bounded_piece(compact, max_chars)

    scored = _score_sentences(sentences, bonus_words)
    if not scored:
        return _bounded_piece(compact, max_chars)

    # Prefer three extracts, but use at least two when the source provides two
    # or more sentences. Selection strength and source-order rendering are separate.
    target = min(max_sentences, len(scored))
    if len(scored) >= 2:
        target = max(2, target)
    selected = sorted(sorted(scored, reverse=True)[:target], key=lambda item: item[1])
    pieces = [sentence for _, _, sentence in selected]

    joined = _SUMMARY_DELIMITER.join(pieces)
    if len(joined) <= max_chars:
        return joined

    # Prefer two complete extracts before truncating individual extracts.
    if len(pieces) > 2:
        selected_two = sorted(sorted(scored, reverse=True)[:2], key=lambda item: item[1])
        pieces = [sentence for _, _, sentence in selected_two]
        two = _SUMMARY_DELIMITER.join(pieces)
        if len(two) <= max_chars:
            return two

    delimiter_chars = len(_SUMMARY_DELIMITER) * max(0, len(pieces) - 1)
    available = max(1, max_chars - delimiter_chars)
    per_piece = max(1, available // max(1, len(pieces)))
    bounded = [_bounded_piece(piece, per_piece) for piece in pieces]
    return _SUMMARY_DELIMITER.join(bounded)[:max_chars]


def _summary_bonus_words(record: dict[str, Any]) -> list[str]:
    return _terms(record.get("topics")) + _terms(record.get("concepts")) + _terms(record.get("persons"))


def _summarize_update_history(updates: Any, *, bonus_words: list[str], max_chars: int) -> Any:
    if not isinstance(updates, list):
        return updates
    sanitized: list[Any] = []
    for raw in updates:
        if not isinstance(raw, dict):
            sanitized.append(copy.deepcopy(raw))
            continue
        entry = copy.deepcopy(raw)
        field_name = str(entry.get("field_name") or entry.get("field") or "").strip().lower()
        if field_name == "text":
            for key in ("old_value", "new_value", "value"):
                if isinstance(entry.get(key), str) and entry[key]:
                    entry[key] = edmundson_summary(
                        entry[key],
                        bonus_words=bonus_words,
                        max_chars=max_chars,
                    )
        # Handle alternate update payloads that embed field values in a map.
        changes = entry.get("changes")
        if isinstance(changes, dict) and isinstance(changes.get("text"), str):
            changes = copy.deepcopy(changes)
            changes["text"] = edmundson_summary(
                changes["text"],
                bonus_words=bonus_words,
                max_chars=max_chars,
            )
            entry["changes"] = changes
        sanitized.append(entry)
    return sanitized


def summarize_record(record: dict[str, Any], *, max_chars: int = 1600) -> dict[str, Any]:
    out = copy.deepcopy(record)
    bonus_words = _summary_bonus_words(out)
    text = str(out.get("text") or "")
    if text:
        summary = edmundson_summary(text, bonus_words=bonus_words, max_chars=max_chars)
        out["text"] = summary
        out["_researcher_text_policy"] = {
            "mode": "edmundson",
            "max_chars": max_chars,
            "max_sentences": 3,
            "delimiter": _SUMMARY_DELIMITER,
            "bonus_fields": ["topics", "concepts", "persons"],
            "source_chars": len(text),
        }
    # Audit history is admin-only and can become substantially larger than the
    # record itself.  Researcher responses retain only a tiny count so ordinary
    # browsing/search/RAG packets never ship the full history.
    updates = out.pop("updates", None)
    if isinstance(updates, list) and updates:
        out["_updates_count"] = len(updates)
    # Passage annotations are an administrator-only feature and may contain an
    # exact quote selected from the full source text. Do not expose them through
    # researcher browse/search responses, where they would bypass the summary
    # policy even though the top-level ``text`` field is reduced.
    out.pop("annotations", None)
    return out


def sanitize_records_payload(payload: dict[str, Any], *, max_chars: int = 1600) -> dict[str, Any]:
    """Sanitize record-bearing store/search responses for a researcher account."""
    out = copy.deepcopy(payload)
    records = out.get("records")
    if isinstance(records, list):
        out["records"] = [
            summarize_record(record, max_chars=max_chars) if isinstance(record, dict) else record
            for record in records
        ]
    results = out.get("results")
    if isinstance(results, list):
        sanitized_results: list[Any] = []
        for item in results:
            if isinstance(item, dict) and isinstance(item.get("record"), dict):
                next_item = copy.deepcopy(item)
                next_item["record"] = summarize_record(next_item["record"], max_chars=max_chars)
                sanitized_results.append(next_item)
            else:
                sanitized_results.append(copy.deepcopy(item))
        out["results"] = sanitized_results
    return out


def sanitize_rag_job(job: dict[str, Any], *, max_chars: int = 1600) -> dict[str, Any]:
    out = copy.deepcopy(job)
    result = out.get("result")
    if isinstance(result, dict):
        evidence = result.get("evidence")
        if isinstance(evidence, list):
            for item in evidence:
                if isinstance(item, dict) and isinstance(item.get("record"), dict):
                    item["record"] = summarize_record(item["record"], max_chars=max_chars)
                    item["text_truncated"] = True
    return out
