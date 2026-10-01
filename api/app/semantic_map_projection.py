# Copyright 2026 Aaron John Schlosser, PhD.
"""Cheap identities for rebuildable semantic-map projections.

Semantic maps are System Data, not corpus content.  Their generation token is
advanced by corpus writers, so opening a map never has to hash or walk the full
corpus merely to discover whether a saved projection is still current.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

SEMANTIC_PROJECTION_VERSION = 1

# Everything consumed by the Semantic Content Graph or the Record term/document
# layers belongs here. Review disposition, UI state, and other editorial workflow
# fields are intentionally excluded so accepting a Record does not invalidate its
# semantic map.
_SEMANTIC_RECORD_FIELDS = (
    "record_id",
    "text",
    "language",
    "speaker",
    "position_holder",
    "target",
    "stance",
    "persons",
    "concepts",
    "works_referenced",
    "topics",
    "quoted_speaker",
    "quoted_author",
    "quoted_work",
    "nlp_candidates",
    "document_intelligence",
    "field_assertions",
    "metadata_field_status",
    "metadata_evidence",
)


def _digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def semantic_record_digest(record: dict[str, Any]) -> str:
    """Digest only fields that can change semantic-map content."""
    return _digest({field: record.get(field) for field in _SEMANTIC_RECORD_FIELDS})


def semantic_records_digest(records: list[dict[str, Any]]) -> str:
    """Stable build-wide map digest, intended for write paths rather than reads."""
    return _digest(
        [
            (str(record.get("record_id") or ""), semantic_record_digest(record))
            for record in records
        ]
    )


def text_record_digest(record: dict[str, Any]) -> str:
    return _digest(
        {
            "record_id": str(record.get("record_id") or ""),
            "text": str(record.get("text") or ""),
        }
    )


def text_records_digest(records: list[dict[str, Any]]) -> str:
    return _digest(
        [
            (str(record.get("record_id") or ""), text_record_digest(record))
            for record in records
        ]
    )


def semantic_map_source(record: dict[str, Any]) -> dict[str, Any]:
    """Small source payload consumed by the existing work-map visual layout."""
    def values(name: str) -> list[str]:
        value = record.get(name)
        raw = value if isinstance(value, list) else str(value or "").replace(";", ",").split(",")
        out: list[str] = []
        seen: set[str] = set()
        for item in raw:
            label = str(item or "").strip()
            key = label.casefold()
            if label and key not in seen:
                seen.add(key)
                out.append(label)
        return out

    return {
        "id": str(record.get("record_id") or ""),
        "work": str(record.get("work") or record.get("document_title") or "").strip(),
        "concepts": values("concepts"),
        "topics": values("topics"),
        "persons": values("persons"),
    }


WORK_MAP_MAX_NODES = 64
WORK_MAP_MAX_TERMS_PER_RECORD = 6


def _work_map_node_id(kind: str, label: str, identity: str = "") -> str:
    key = identity or label
    return f"{kind}:{key.lower()}"


def _balanced_work_terms(source: dict[str, Any]) -> list[tuple[str, str]]:
    buckets = [
        ("concept", list(source.get("concepts") or [])),
        ("topic", list(source.get("topics") or [])),
        ("person", list(source.get("persons") or [])),
    ]
    indexes = [0, 0, 0]
    out: list[tuple[str, str]] = []
    while len(out) < WORK_MAP_MAX_TERMS_PER_RECORD:
        advanced = False
        for bucket_index, (kind, values) in enumerate(buckets):
            if len(out) >= WORK_MAP_MAX_TERMS_PER_RECORD:
                break
            index = indexes[bucket_index]
            if index >= len(values):
                continue
            indexes[bucket_index] += 1
            label = str(values[index] or "").strip()
            if label:
                out.append((kind, label))
            advanced = True
        if not advanced:
            break
    return out


def work_semantic_topology(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Persist the work map's weighted nodes/edges while leaving layout to the UI.

    This mirrors the existing browser topology so the visual treatment remains
    unchanged, but co-occurrence relationships are calculated once and saved.
    """
    work_counts: dict[str, int] = {}
    for source in sources:
        key = str(source.get("work") or "").strip().lower()
        if key:
            work_counts[key] = work_counts.get(key, 0) + 1
    duplicate_works = {key for key, count in work_counts.items() if count > 1}

    weights: dict[str, dict[str, Any]] = {}
    links: dict[str, dict[str, Any]] = {}

    def touch(kind: str, label: str, identity: str = "") -> str:
        node_id = _work_map_node_id(kind, label, identity)
        current = weights.get(node_id)
        if current is None:
            weights[node_id] = {
                "id": node_id,
                "label": label,
                "kind": kind,
                "weight": 1,
            }
        else:
            current["weight"] = int(current.get("weight") or 0) + 1
        return node_id

    def link(left: str, right: str) -> None:
        if not left or not right or left == right:
            return
        source_id, target_id = sorted((left, right))
        key = f"{source_id}|{target_id}"
        current = links.get(key)
        if current is None:
            links[key] = {
                "id": key,
                "source": source_id,
                "target": target_id,
                "weight": 1,
            }
        else:
            current["weight"] = int(current.get("weight") or 0) + 1

    for source in sources:
        term_ids = [touch(kind, label) for kind, label in _balanced_work_terms(source)]
        for index, left in enumerate(term_ids):
            for right in term_ids[index + 1 :]:
                link(left, right)

        record_id = str(source.get("id") or "")
        if not record_id:
            continue
        work = str(source.get("work") or "").strip()
        label = work or record_id or "Record"
        if work and work.lower() in duplicate_works:
            suffix = record_id[-8:] if len(record_id) > 8 else record_id
            label = f"{work} · {suffix}"
        record_node = touch("record", label, record_id)
        for term_id in term_ids:
            link(record_node, term_id)

    ranked = sorted(
        weights.values(),
        key=lambda row: (-int(row.get("weight") or 0), str(row.get("label") or "").casefold()),
    )
    nodes = ranked[:WORK_MAP_MAX_NODES]
    kept = {str(node["id"]) for node in nodes}
    edges = [
        edge
        for edge in links.values()
        if edge["source"] in kept and edge["target"] in kept
    ]
    return {"nodes": nodes, "edges": edges}
