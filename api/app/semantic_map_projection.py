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
