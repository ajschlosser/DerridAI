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
from collections.abc import Callable
from difflib import SequenceMatcher
from typing import Any

from .retrieval_selection import mmr_select

METHOD = "deterministic-lexical-v1"
EVIDENCE_MODES = ("with_value", "backfill")
DEFAULT_EVIDENCE_MODE = "with_value"
BACKFILL_MIN_SCORE = 0.5
BACKFILL_MAX_BLOCKS = 2
SEMANTIC_METHOD = "local-semantic-v1"
SEMANTIC_MIN_SCORE = 0.35
CROSS_ENCODER_METHOD = "cross-encoder-rerank-v1"
MMR_METHOD = "mmr-similarity-v1"
CASCADE_MAX_BLOCKS = BACKFILL_MAX_BLOCKS
CASCADE_MMR_LAMBDA = 0.72


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


def evidence_cascade_llm_enabled(request: dict[str, Any] | None = None) -> bool:
    """Whether the evidence cascade's last-resort LLM stage may run for this build.

    A request's own flag wins over the setting, so one build can opt out without changing the deployment
    default. The LLM stage is the only cascade stage that costs an extra provider call per unresolved field.
    """
    from .config import settings

    value = (request or {}).get("evidence_cascade_llm_enabled")
    if isinstance(value, bool):
        return value
    return bool(settings.metadata_evidence_cascade_llm_enabled)


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


def semantic_query(field_metadata: Any, value: Any) -> str:
    """Build a field-aware embedding query without assigning meaning to field names."""
    if isinstance(field_metadata, dict):
        metadata = field_metadata
    elif hasattr(field_metadata, "model_dump"):
        metadata = field_metadata.model_dump(mode="json")
    else:
        metadata = {}
    values = metadata.get("values")
    allowed = []
    if isinstance(values, list):
        allowed = [
            str(item.get("value") if isinstance(item, dict) else item).strip()
            for item in values
        ]
        allowed = [item for item in allowed if item]
    instruction = str(metadata.get("instruction") or "").strip()
    if allowed:
        instruction = instruction.replace("{values}", ", ".join(allowed))
    parts = [
        f"Field: {str(metadata.get('label') or metadata.get('name') or '').strip()}",
        f"Type: {str(metadata.get('type') or '').strip()}",
        f"Instruction: {instruction}",
        f"Group context: {str(metadata.get('group_label') or '').strip()}",
        f"Proposed value: {'; '.join(_flatten(value))}",
    ]
    if allowed:
        parts.append("Allowed values: " + ", ".join(allowed))
    return "\n".join(part for part in parts if part.split(":", 1)[-1].strip())[:4000]


def _signal(
    score: float | None,
    method: str,
    reason: str,
    *,
    status: str = "available",
) -> dict[str, Any]:
    return {
        "score": round(max(0.0, min(1.0, score)), 4) if score is not None else None,
        "method": method,
        "reason": reason,
        "status": status,
    }


def suggest_evidence_blocks_semantic(
    value: Any,
    blocks: list[dict[str, Any]],
    *,
    field_metadata: Any,
    source_document_id: str,
    projection: Any,
    limit: int = 5,
    provider: str | None = None,
    model: str | None = None,
    query: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Combine deterministic lexical and local source-unit semantic signals.

    The projection is derived state only. Any projection/provider failure returns
    lexical results and a visible fallback status; it can never suppress or
    override lexical suggestions.
    """
    lexical = suggest_evidence_blocks(value, blocks, limit=len(blocks), min_score=0.2)
    lexical_by_id = {item["block_id"]: item for item in lexical}
    status = {"semantic": "available", "reason": ""}
    semantic_by_id: dict[str, dict[str, Any]] = {}
    try:
        if not blocks or not _flatten(value):
            raise ValueError("No proposed value or source blocks are available.")
        query_text = query or semantic_query(field_metadata, value)
        projection.sync(
            source_document_id,
            blocks,
            provider=provider,
            model=model,
            prune=False,
        )
        unit_ids = [str(block.get("source_unit_id") or block.get("block_id") or "") for block in blocks]
        vectors = projection.embeddings_for(
            source_document_id,
            unit_ids,
            provider=provider,
            model=model,
        )
        query_vector = projection.embed_query(query_text, provider=provider, model=model)
        for block in blocks:
            block_id = str(block.get("block_id") or "")
            unit_id = str(block.get("source_unit_id") or block_id)
            vector = vectors.get(unit_id)
            score = _cosine(query_vector, vector or [])
            if block_id and vector and score >= SEMANTIC_MIN_SCORE:
                semantic_by_id[block_id] = {
                    "score": score,
                    "reason": "Semantically resembles the proposed value for this field.",
                    "method": SEMANTIC_METHOD,
                }
    except Exception as exc:  # noqa: BLE001 - semantic advice must never block lexical advice
        status = {
            "semantic": "fallback",
            "reason": f"Local semantic retrieval failed; lexical suggestions remain available: {exc}",
        }
    candidate_ids = set(lexical_by_id) | set(semantic_by_id)
    rows: list[dict[str, Any]] = []
    for block in blocks:
        block_id = str(block.get("block_id") or "")
        if block_id not in candidate_ids:
            continue
        lexical_item = lexical_by_id.get(block_id)
        semantic_item = semantic_by_id.get(block_id)
        lexical_signal = _signal(
            lexical_item["score"] if lexical_item else None,
            lexical_item["method"] if lexical_item else METHOD,
            lexical_item["reason"] if lexical_item else "No deterministic text overlap found.",
            status="available" if lexical_item else "no_match",
        )
        semantic_signal = _signal(
            semantic_item["score"] if semantic_item else None,
            semantic_item["method"] if semantic_item else SEMANTIC_METHOD,
            semantic_item["reason"] if semantic_item else status["reason"] or "No local semantic match reached the suggestion threshold.",
            status="available" if semantic_item else ("fallback" if status["semantic"] == "fallback" else "no_match"),
        )
        combined_score = max(lexical_signal["score"] or 0.0, semantic_signal["score"] or 0.0)
        primary = semantic_item if semantic_item and (not lexical_item or semantic_item["score"] > lexical_item["score"]) else lexical_item
        row = {
            "block_id": block_id,
            **(
                {"source_unit_id": str(block.get("source_unit_id"))}
                if block.get("source_unit_id")
                else {}
            ),
            # Existing consumers use these top-level fields; keep them as the
            # strongest signal while exposing both signals independently below.
            "score": round(combined_score, 4),
            "method": primary["method"] if primary else METHOD,
            "reason": primary["reason"] if primary else "",
            "lexical_score": lexical_signal["score"],
            "lexical_method": lexical_signal["method"],
            "lexical_reason": lexical_signal["reason"],
            "semantic_score": semantic_signal["score"],
            "semantic_method": semantic_signal["method"],
            "semantic_reason": semantic_signal["reason"],
            "semantic_status": semantic_signal["status"],
            "signals": {"lexical": lexical_signal, "semantic": semantic_signal},
        }
        rows.append(row)
    rows.sort(key=lambda item: (-item["score"], item["block_id"]))
    return rows[: max(1, limit)], status


PRECEDENT_SEMANTIC_METHOD = "precedent-semantic-v1"
PRECEDENT_LEXICAL_METHOD = "precedent-lexical-v1"
_SPAN_LOCATION_KEYS = ("source_unit_id", "page", "pdf_page", "printed_page_label", "start", "end", "speaker")


def record_source_blocks(record: dict[str, Any], blocks_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """This record's own source blocks, in record order, with only the location keys its medium has.

    Membership comes from ``source_unit_ids`` (falling back to ``source_block_ids``);
    a unit that is not listed there is never a candidate,
    so nothing ranked here can bind evidence outside the record under review.
    """
    spans = {
        str(span.get("block_id")): span
        for span in record.get("source_spans") or []
        if isinstance(span, dict) and span.get("block_id")
    }
    out: list[dict[str, Any]] = []
    unit_ids = record.get("source_unit_ids") or record.get("source_block_ids") or []
    for block_id in dict.fromkeys(map(str, unit_ids)):
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


def _cascade_entry(picks: list[dict[str, Any]], method: str, reason: str) -> dict[str, Any]:
    """The shape every cascade stage returns: advisory, untrusted, never auto-resolving.

    Confidence is always unreported and the entry is always marked ``backfilled``, exactly like
    ``backfill_field_evidence`` (which this supersedes as the general case): both flags together keep a
    cascade-bound field out of ``autofill()`` and always queued for human review, no matter which stage won.
    """
    return {
        "block_ids": [item["block_id"] for item in picks],
        "confidence": None,
        "reason": reason,
        "backfilled": True,
        "method": method,
        "score": picks[0].get("score"),
        # Keep stage-specific scores separate. These are operational ranking
        # signals only; none of them turns a suggestion into reviewed evidence.
        "score_details": [
            {
                key: item[key]
                for key in (
                    "block_id",
                    "score",
                    "lexical_score",
                    "semantic_score",
                    "cross_encoder_score",
                    "mmr_score",
                )
                if key in item
            }
            for item in picks
        ],
    }


def _mmr_select(
    rows: list[dict[str, Any]], *, limit: int, lambda_mult: float = CASCADE_MMR_LAMBDA
) -> list[dict[str, Any]]:
    """Select evidence candidates while preserving relevance and MMR scores separately."""

    return mmr_select(
        rows,
        limit=limit,
        lambda_mult=lambda_mult,
        relevance=lambda row: float(row.get("score") or 0.0),
        vector=lambda row: row.get("vector"),
    )

def suggest_evidence_cascade(
    value: Any,
    blocks: list[dict[str, Any]],
    *,
    field: str,
    field_metadata: Any,
    source_document_id: str,
    projection: Any,
    provider: str | None = None,
    model: str | None = None,
    llm_choice: Callable[[str], dict[str, Any]] | None = None,
    limit: int = CASCADE_MAX_BLOCKS,
) -> dict[str, Any] | None:
    """Ordered fallback for a value with no usable evidence: lexical -> cross-encoder rerank -> MMR/
    similarity -> LLM. Only this record's own blocks are ever candidates (the caller supplies them).

    Each stage is tried only when the one before it found nothing usable; the first stage to produce a
    candidate wins. Every result comes back through ``_cascade_entry`` (advisory, unconfirmed). Returns
    ``None`` when nothing at any stage supports the value, or there is nothing to search.
    """
    from .config import settings

    if not blocks or not _flatten(value):
        return None

    lexical = suggest_evidence_blocks(value, blocks, limit=limit, min_score=BACKFILL_MIN_SCORE)
    if lexical:
        return _cascade_entry(
            lexical, METHOD,
            f"Suggested by the evidence cascade's deterministic match ({lexical[0]['reason']}).",
        )

    candidates: list[dict[str, Any]] = []
    try:
        query = semantic_query(field_metadata, value)
        projection.sync(source_document_id, blocks, provider=provider, model=model, prune=False)
        unit_ids = [str(b.get("source_unit_id") or b.get("block_id") or "") for b in blocks]
        vectors = projection.embeddings_for(source_document_id, unit_ids, provider=provider, model=model)
        query_vector = projection.embed_query(query, provider=provider, model=model)
        for block in blocks:
            block_id = str(block.get("block_id") or "")
            unit_id = str(block.get("source_unit_id") or block_id)
            vector = vectors.get(unit_id)
            if block_id and vector:
                candidates.append({
                    "block_id": block_id, "text": str(block.get("text") or ""),
                    "vector": vector, "score": _cosine(query_vector, vector),
                })
    except Exception:  # noqa: BLE001 - later stages must still be reachable
        candidates = []
    candidates.sort(key=lambda row: -row["score"])

    if candidates and settings.metadata_cross_encoder_enabled:
        from .cross_encoder import predict_scores

        top = candidates[: max(1, settings.metadata_cross_encoder_top_k)]
        scores, _telemetry = predict_scores(
            [(query, row["text"]) for row in top],
            model_name=settings.rag_cross_encoder_model,
            timeout_seconds=settings.metadata_cross_encoder_timeout_seconds,
        )
        if scores:
            ranked = sorted(zip(top, scores), key=lambda pair: -pair[1])
            picks = [
                {
                    "block_id": row["block_id"],
                    "score": round(float(score), 4),
                    "semantic_score": round(float(row.get("score") or 0.0), 4),
                    "cross_encoder_score": round(float(score), 4),
                }
                for row, score in ranked[:limit]
                if score > 0
            ]
            if picks:
                return _cascade_entry(
                    picks, CROSS_ENCODER_METHOD,
                    f"Suggested by the evidence cascade's cross-encoder rerank (top score {picks[0]['score']:.3f}).",
                )

    if candidates and candidates[0]["score"] >= SEMANTIC_MIN_SCORE:
        selected = _mmr_select(candidates, limit=limit)
        picks = [
            {
                "block_id": row["block_id"],
                "score": round(float(row["score"]), 4),
                "semantic_score": round(float(row["score"]), 4),
                "mmr_score": round(float(row.get("mmr_score") or 0.0), 4),
            }
            for row in selected
        ]
        return _cascade_entry(
            picks,
            MMR_METHOD,
            (
                "Suggested by the evidence cascade's maximum marginal relevance "
                f"selection (top semantic score {picks[0]['score']:.3f}; "
                f"MMR objective {picks[0]['mmr_score']:.3f})."
            ),
        )

    if llm_choice is not None:
        try:
            picks = validate_llm_choice(llm_choice(llm_prompt(field, value, blocks)), blocks, value, limit=limit)
        except Exception:  # noqa: BLE001 - the cascade must never fail a build
            picks = []
        if picks:
            return _cascade_entry(
                picks, LLM_METHOD,
                f"Suggested by the evidence cascade's model choice ({picks[0].get('reason') or 'no reason given'}).",
            )

    return None
