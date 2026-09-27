# Copyright 2026 Aaron John Schlosser, PhD.
"""Precedent retrieval kept from metadata enrichment, for the reviewer's precedents panel.

Enrichment already retrieves reviewed precedents for every field to build its prompt. This
module keeps that result on the record so Record Review does not repeat the semantic search,
and ranks the record's *own* source blocks against each precedent's reviewed evidence so a
reviewer who adopts a precedent's value has a shortlist of where this record may support it.

What is stored on the record is references only: exemplar IDs, similarities, and block IDs
of this record. A precedent's value and evidence text belong to another record and are
never stored here. When the panel is read, every reference is joined back to the canonical
exemplars rebuilt for the current reviewer, so a precedent that changed, was withdrawn, or
is hidden from this reviewer (a pending blind second opinion) is counted as stale, never shown
from a stale copy. Candidate blocks are advisory and bind nothing.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .evidence_suggestions import rank_blocks_for_texts, record_source_blocks
from .metadata_exemplars import prompt_example

CACHE_KEY = "metadata_precedents_cache"
# Bump when the stored shape or its meaning changes; other versions are ignored and recomputed live.
CACHE_VERSION = 1
CANDIDATE_LIMIT = 3


def precedent_mode(field: str, items: list[dict[str, Any]], telemetry: dict[str, Any]) -> str:
    """How this field's precedents were found: the vector index, lexical overlap, or not at all."""
    if field in (telemetry.get("fields_served") or []):
        return "semantic"
    return "lexical" if items else "none"


def rank_candidates(
    items: list[dict[str, Any]],
    record: dict[str, Any],
    blocks_by_id: dict[str, dict[str, Any]],
    *,
    embed: Callable[[list[str]], list[list[float]]] | None = None,
) -> list[list[dict[str, Any]]]:
    """This record's blocks most similar to each precedent's reviewed evidence (one list per item)."""
    queries = [str(item.get("evidence") or "").strip() for item in items]
    wanted = [index for index, query in enumerate(queries) if query]
    out: list[list[dict[str, Any]]] = [[] for _ in items]
    blocks = record_source_blocks(record, blocks_by_id)
    if not wanted or not blocks:
        return out
    ranked, _method = rank_blocks_for_texts(
        [queries[index] for index in wanted], blocks, embed=embed, limit=CANDIDATE_LIMIT
    )
    for index, picks in zip(wanted, ranked):
        out[index] = picks
    return out


def build_precedents_cache(
    fields: Iterable[str],
    examples: dict[str, list[dict[str, Any]]],
    telemetry: dict[str, Any],
    record: dict[str, Any],
    blocks_by_id: dict[str, dict[str, Any]],
    *,
    computed_at: str,
    embed: Callable[[list[str]], list[list[float]]] | None = None,
) -> dict[str, Any]:
    """The stored form of one enrichment pass's precedent retrieval for ``record``.

    A field whose precedents include one without a stable exemplar identity (older reviews
    with no bound evidence) is left out, so the panel recomputes it live instead of showing
    something it could not re-verify.
    """
    stored: dict[str, Any] = {}
    for field in dict.fromkeys(str(name) for name in fields if str(name)):
        items = [item for item in examples.get(field) or [] if isinstance(item, dict)]
        if any(not str(item.get("exemplar_id") or "") for item in items):
            continue
        candidates = rank_candidates(items, record, blocks_by_id, embed=embed)
        refs = []
        for item, picks in zip(items, candidates):
            ref: dict[str, Any] = {
                "exemplar_id": str(item["exemplar_id"]),
                "similarity": item.get("similarity"),
                "candidate_source_units": picks,
            }
            if isinstance(item.get("match"), dict):
                ref["match"] = item["match"]
            refs.append(ref)
        stored[field] = {"mode": precedent_mode(field, items, telemetry), "refs": refs}
    return {
        "version": CACHE_VERSION,
        "computed_at": computed_at,
        "fallback_reason": str(telemetry.get("fallback_reason") or ""),
        "fields": stored,
    }


def cached_field(record: dict[str, Any], field: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """The stored entry for ``field`` and its cache, or None when it must be computed live."""
    cache = record.get(CACHE_KEY)
    if not isinstance(cache, dict) or cache.get("version") != CACHE_VERSION:
        return None
    entry = (cache.get("fields") or {}).get(field)
    if not isinstance(entry, dict) or not isinstance(entry.get("refs"), list):
        return None
    return entry, cache


def own_candidates(record: dict[str, Any], candidates: Any) -> list[dict[str, Any]]:
    """Keep only candidates that are still blocks of this record (it may have been re-segmented)."""
    members = set(map(str, record.get("source_block_ids") or []))
    return [
        dict(item)
        for item in candidates or []
        if isinstance(item, dict) and str(item.get("block_id") or "") in members
    ]


def resolve_cached_precedents(
    entry: dict[str, Any],
    canonical_by_id: dict[str, dict[str, Any]],
    record: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    """Join stored references to current canonical exemplars; returns (items, stale count)."""
    items: list[dict[str, Any]] = []
    stale = 0
    for ref in entry.get("refs") or []:
        if not isinstance(ref, dict):
            continue
        exemplar = canonical_by_id.get(str(ref.get("exemplar_id") or ""))
        if exemplar is None:
            stale += 1
            continue
        similarity = ref.get("similarity")
        item = prompt_example(
            exemplar,
            similarity=float(similarity) if isinstance(similarity, (int, float)) else None,
        )
        if isinstance(ref.get("match"), dict):
            item["match"] = ref["match"]
        item["candidate_source_units"] = own_candidates(record, ref.get("candidate_source_units"))
        items.append(item)
    return items, stale
