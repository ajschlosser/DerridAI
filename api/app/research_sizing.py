# Copyright 2026 Aaron John Schlosser, PhD.
"""Record-size-aware Research retrieval and context expansion.

Automatic sizing is deliberately an execution policy, not source authority. It
adapts derived retrieval work to corpus segmentation while leaving canonical
Records, provenance, citation binding, and the configured evidence budget
unchanged.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

AUTO_REFERENCE_RECORD_CHARS = 1750
AUTO_MAX_SCALE = 4.0
AUTO_MAX_RETRIEVE_K = 500
AUTO_MAX_FETCH_K = 5000
AUTO_TARGET_CONTEXT_CHARS = 3000
AUTO_MAX_NEIGHBOR_RADIUS = 2
AUTO_NEIGHBOR_BUDGET_FRACTION = 0.35
AUTO_MAX_REGION_RECORDS = 3
AUTO_MAX_REGION_TEXT_CHARS = 4500


def _text_chars(record: Mapping[str, Any]) -> int:
    value = record.get("text_length")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 0
    return parsed if parsed > 0 else len(" ".join(str(record.get("text") or "").split()))


def automatic_collection_sizing(
    *,
    count: int,
    median_record_chars: int | float | None,
    requested_k: int,
    semantic_fetch_k: int,
    lexical_fetch_k: int,
    mmr_limit: int,
) -> dict[str, Any]:
    """Scale candidate depth by robust Record size while preserving hard bounds.

    The caller's configured values remain floors. Automatic sizing only grows
    candidate depth for collections whose median Record is shorter than the
    Corpus Builder reference size; it never makes a manual configuration less
    exhaustive.
    """

    bounded_count = max(0, int(count))
    try:
        median = max(1.0, float(median_record_chars or AUTO_REFERENCE_RECORD_CHARS))
    except (TypeError, ValueError):
        median = float(AUTO_REFERENCE_RECORD_CHARS)

    scale = max(
        1.0,
        min(AUTO_MAX_SCALE, float(AUTO_REFERENCE_RECORD_CHARS) / median),
    )
    requested = max(1, int(requested_k))
    effective_k = min(
        bounded_count or AUTO_MAX_RETRIEVE_K,
        AUTO_MAX_RETRIEVE_K,
        max(requested, int(math.ceil(requested * scale))),
    )
    semantic_base = max(1, int(semantic_fetch_k))
    lexical_base = max(1, int(lexical_fetch_k))
    # Grow the fetched pool only as far as the enlarged result count can use.
    # With the default k=64/fetch_k=500, even a 4x size correction therefore
    # moves fetch_k only to 512 rather than 2000.
    semantic_target = max(
        effective_k,
        semantic_base,
        min(int(math.ceil(semantic_base * scale)), effective_k * 2),
    )
    lexical_target = max(
        effective_k,
        lexical_base,
        min(int(math.ceil(lexical_base * scale)), effective_k * 2),
    )
    semantic = min(
        bounded_count or AUTO_MAX_FETCH_K,
        AUTO_MAX_FETCH_K,
        semantic_target,
    )
    lexical = min(
        bounded_count or AUTO_MAX_FETCH_K,
        AUTO_MAX_FETCH_K,
        lexical_target,
    )
    mmr = min(
        effective_k,
        AUTO_MAX_RETRIEVE_K,
        max(1, int(math.ceil(max(1, int(mmr_limit)) * scale))),
    )
    return {
        "median_record_chars": int(round(median)),
        "scale": round(scale, 4),
        "k": effective_k,
        "semantic_fetch_k": semantic,
        "lexical_fetch_k": lexical,
        "mmr_limit": mmr,
    }


def _source_document_id(record: Mapping[str, Any]) -> str:
    return str(
        record.get("source_document_id")
        or record.get("source_asset_id")
        or ""
    ).strip()


def _record_id(record: Mapping[str, Any]) -> str:
    return str(record.get("record_id") or record.get("_chroma_id") or "").strip()


def _sequence_number(record: Mapping[str, Any]) -> int | None:
    for field in ("record_ordinal", "ordinal", "record_index", "sequence"):
        raw = record.get(field)
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    match = re.search(r"(\d+)$", _record_id(record))
    return int(match.group(1)) if match else None


def _record_order_key(record: Mapping[str, Any]) -> tuple[int, float, int, str]:
    """Return a stable documentary ordering key for same-document neighbors."""

    sequence = _sequence_number(record)
    spans = record.get("source_spans")
    if isinstance(spans, list):
        starts = [
            float(span["start"])
            for span in spans
            if isinstance(span, Mapping) and span.get("start") is not None
        ]
        if starts:
            return (0, min(starts), sequence or 0, _record_id(record))

    page = record.get("page_start")
    try:
        if page is not None:
            return (1, float(page), sequence or 0, _record_id(record))
    except (TypeError, ValueError):
        pass

    if sequence is not None:
        return (2, float(sequence), sequence, _record_id(record))
    return (3, 0.0, 0, _record_id(record))


def _region_chunks(
    rows: Sequence[tuple[int, Mapping[str, Any], int]],
) -> list[tuple[int, list[tuple[int, Mapping[str, Any], int]]]]:
    pending = list(rows)
    chunks: list[tuple[int, list[tuple[int, Mapping[str, Any], int]]]] = []
    while pending:
        chunk: list[tuple[int, Mapping[str, Any], int]] = []
        chars = 0
        while pending and len(chunk) < AUTO_MAX_REGION_RECORDS:
            record = (
                pending[0][1].get("record")
                if isinstance(pending[0][1].get("record"), Mapping)
                else {}
            )
            candidate_chars = _text_chars(record)
            if chunk and chars + candidate_chars > AUTO_MAX_REGION_TEXT_CHARS:
                break
            chunk.append(pending.pop(0))
            chars += candidate_chars
        chunks.append((min(row[0] for row in chunk), chunk))
    return chunks


def collapse_adjacent_candidates(
    candidates: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Collapse short, consecutive same-document hits into bounded rerank regions.

    One real Record remains the ranking anchor. The cross-encoder sees the
    ordered region text, while every constituent Record is retained on the
    anchor so context expansion can restore it with its own identity later.
    Long Records are intentionally left alone.
    """

    if not candidates:
        return [], {"input_count": 0, "output_count": 0, "collapsed_records": 0}

    indexed = [(index, item) for index, item in enumerate(candidates)]
    grouped: dict[tuple[str, str], list[tuple[int, Mapping[str, Any], int]]] = {}
    singles: list[tuple[int, list[tuple[int, Mapping[str, Any], int]]]] = []

    for index, item in indexed:
        record = item.get("record") if isinstance(item.get("record"), Mapping) else {}
        source_id = _source_document_id(record)
        sequence = _sequence_number(record)
        collection = str(item.get("collection") or "")
        if (
            bool(item.get("selected_evidence"))
            or not source_id
            or sequence is None
            or _text_chars(record) >= AUTO_REFERENCE_RECORD_CHARS
        ):
            singles.append((index, [(index, item, sequence or -1)]))
            continue
        grouped.setdefault((collection, source_id), []).append((index, item, sequence))

    regions: list[tuple[int, list[tuple[int, Mapping[str, Any], int]]]] = list(singles)
    for rows in grouped.values():
        rows.sort(key=lambda row: (row[2], row[0]))
        run: list[tuple[int, Mapping[str, Any], int]] = []
        previous: int | None = None
        for row in rows:
            sequence = row[2]
            if previous is not None and sequence != previous + 1:
                regions.extend(_region_chunks(run))
                run = []
            run.append(row)
            previous = sequence
        regions.extend(_region_chunks(run))

    collapsed: list[dict[str, Any]] = []
    collapsed_records = 0
    for _priority, members in sorted(regions, key=lambda region: region[0]):
        representative_index, representative_item, _ = min(members, key=lambda row: row[0])
        representative = dict(representative_item)
        if len(members) > 1:
            ordered = sorted(
                members,
                key=lambda row: _record_order_key(
                    row[1].get("record")
                    if isinstance(row[1].get("record"), Mapping)
                    else {}
                ),
            )
            member_rows = [dict(row[1]) for row in ordered]
            representative["_automatic_region_members"] = member_rows
            representative["_rerank_text"] = "\n\n".join(
                str(
                    (
                        row.get("record")
                        if isinstance(row.get("record"), Mapping)
                        else {}
                    ).get("text")
                    or ""
                ).strip()
                for row in member_rows
                if str(
                    (
                        row.get("record")
                        if isinstance(row.get("record"), Mapping)
                        else {}
                    ).get("text")
                    or ""
                ).strip()
            )[:AUTO_MAX_REGION_TEXT_CHARS]
            representative["automatic_region_size"] = len(member_rows)
            collapsed_records += len(member_rows) - 1
        representative["_automatic_original_rank"] = representative_index
        collapsed.append(representative)

    return collapsed, {
        "input_count": len(candidates),
        "output_count": len(collapsed),
        "collapsed_records": collapsed_records,
    }


def expand_context_neighbors(
    anchors: Sequence[Mapping[str, Any]],
    *,
    load_document_records: Callable[[str, str], Sequence[Mapping[str, Any]]],
    total_char_limit: int,
    target_context_chars: int = AUTO_TARGET_CONTEXT_CHARS,
    max_radius: int = AUTO_MAX_NEIGHBOR_RADIUS,
    neighbor_budget_fraction: float = AUTO_NEIGHBOR_BUDGET_FRACTION,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Top up short ranking anchors with nearby same-document Records.

    Anchors always come first in the returned list. Added Records are separate
    evidence candidates with explicit acquisition provenance and consume a
    bounded share of the existing evidence budget.
    """

    anchor_rows: list[dict[str, Any]] = []
    anchor_keys: set[tuple[str, str]] = set()
    for item in anchors:
        row = dict(item)
        row["selection_role"] = "retrieved_anchor"
        row.pop("_rerank_text", None)
        record = row.get("record") if isinstance(row.get("record"), Mapping) else {}
        anchor_keys.add((str(row.get("collection") or ""), _record_id(record)))
        anchor_rows.append(row)

    budget = max(0, int(max(0, total_char_limit) * max(0.0, min(1.0, neighbor_budget_fraction))))
    used_chars = 0
    neighbors: list[dict[str, Any]] = []
    neighbor_keys: set[tuple[str, str]] = set()
    document_cache: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    load_failures: list[str] = []

    def append_neighbor(
        source: Mapping[str, Any],
        *,
        anchor: Mapping[str, Any],
        distance: int,
        reason: str,
    ) -> bool:
        nonlocal used_chars
        collection = str(anchor.get("collection") or source.get("collection") or "")
        record = source.get("record") if isinstance(source.get("record"), Mapping) else source
        if not isinstance(record, Mapping):
            return False
        record_id = _record_id(record)
        key = (collection, record_id)
        if not record_id or key in anchor_keys or key in neighbor_keys:
            return False
        chars = _text_chars(record)
        if budget and used_chars + chars > budget:
            return False
        row = dict(source) if isinstance(source.get("record"), Mapping) else {
            "id": record.get("_chroma_id") or record_id,
            "collection": collection,
            "record": dict(record),
        }
        row["collection"] = collection
        row["selection_role"] = "context_neighbor"
        anchor_record = (
            anchor.get("record") if isinstance(anchor.get("record"), Mapping) else {}
        )
        row["neighbor_of"] = _record_id(anchor_record)
        row["neighbor_distance"] = max(1, int(distance))
        row["neighbor_reason"] = reason
        row["retrieval_hits"] = [
            {
                "collection": collection,
                "search_type": "context_neighbor",
                "rank": max(1, int(distance)),
            }
        ]
        row.pop("_rerank_text", None)
        row.pop("_automatic_region_members", None)
        neighbors.append(row)
        neighbor_keys.add(key)
        used_chars += chars
        return True

    for anchor in anchor_rows:
        record = anchor.get("record") if isinstance(anchor.get("record"), Mapping) else {}
        source_id = _source_document_id(record)
        collection = str(anchor.get("collection") or "")
        if not source_id or not collection or collection == "selected_workspace":
            continue

        local_chars = _text_chars(record)
        anchor_sequence = _sequence_number(record)

        region_members = anchor.get("_automatic_region_members")
        if isinstance(region_members, list):
            for member in region_members:
                member_record = (
                    member.get("record") if isinstance(member, Mapping) and isinstance(member.get("record"), Mapping)
                    else {}
                )
                distance = (
                    abs((_sequence_number(member_record) or 0) - (anchor_sequence or 0))
                    if anchor_sequence is not None and _sequence_number(member_record) is not None
                    else 1
                )
                if append_neighbor(
                    member,
                    anchor=anchor,
                    distance=max(1, distance),
                    reason="collapsed_region",
                ):
                    local_chars += _text_chars(member_record)
        anchor.pop("_automatic_region_members", None)

        if local_chars >= target_context_chars or used_chars >= budget:
            continue

        cache_key = (collection, source_id)
        if cache_key not in document_cache:
            try:
                document_cache[cache_key] = list(load_document_records(collection, source_id))
            except Exception as exc:  # Context expansion must never abort an otherwise valid Research run.
                document_cache[cache_key] = []
                load_failures.append(f"{collection}:{source_id}:{type(exc).__name__}")
        records = document_cache[cache_key]
        if not records:
            continue

        ordered = sorted(records, key=_record_order_key)
        anchor_id = _record_id(record)
        anchor_index = next(
            (index for index, candidate in enumerate(ordered) if _record_id(candidate) == anchor_id),
            None,
        )
        if anchor_index is None:
            continue

        for radius in range(1, max(0, int(max_radius)) + 1):
            for offset in (-radius, radius):
                index = anchor_index + offset
                if index < 0 or index >= len(ordered):
                    continue
                candidate = ordered[index]
                if append_neighbor(
                    candidate,
                    anchor=anchor,
                    distance=radius,
                    reason="adjacent_record",
                ):
                    local_chars += _text_chars(candidate)
                if local_chars >= target_context_chars or used_chars >= budget:
                    break
            if local_chars >= target_context_chars or used_chars >= budget:
                break

    return anchor_rows + neighbors, {
        "anchor_count": len(anchor_rows),
        "neighbor_count": len(neighbors),
        "neighbor_characters": used_chars,
        "neighbor_character_budget": budget,
        "target_context_chars": int(target_context_chars),
        "max_neighbor_radius": int(max_radius),
        "document_reads": len(document_cache),
        "load_failures": load_failures[:20],
    }
