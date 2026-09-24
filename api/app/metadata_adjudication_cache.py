# Copyright 2026 Aaron John Schlosser, PhD.
"""Best-effort local memory for human metadata suggestions."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from .chroma_store import ChromaStore
from .system_store import system_store

logger = logging.getLogger(__name__)
_semantic_store: ChromaStore | None = None
_semantic_memory_disabled = False

def _text_hash(text: str) -> str:
    return hashlib.sha512(str(text or "").encode("utf-8")).hexdigest()


def cache_key(
    *,
    record_id: str,
    text: str,
    field: str,
    cardinality: str,
    schema_version: str = "",
) -> tuple[str, str]:
    digest = _text_hash(text)
    scope = "|".join(
        ("sha512", str(record_id), digest, str(schema_version), str(field), str(cardinality))
    )
    return hashlib.sha512(scope.encode("utf-8")).hexdigest(), digest


def remember(
    *,
    record_id: str,
    text: str,
    field: str,
    value: Any,
    schema_version: str = "",
) -> None:
    cardinality = "list" if isinstance(value, list) else "single"
    key, digest = cache_key(
        record_id=record_id,
        text=text,
        field=field,
        cardinality=cardinality,
        schema_version=schema_version,
    )
    prior = system_store.get_adjudication_cache(key) or {}
    prior_values = list(prior.get("prior_values") or [])
    values = value if cardinality == "list" else [value]
    for item in values:
        if item is None:
            continue
        if any(_value_key(item) == _value_key(previous) for previous in prior_values):
            continue
        prior_values.append(item)
    payload = {
        "latest_value": value,
        "prior_values": prior_values[-50:],
        "cardinality": cardinality,
        "schema_version": schema_version,
    }
    system_store.put_adjudication_cache(
        key, record_id, field, cardinality, digest, payload
    )
    try:
        global _semantic_memory_disabled, _semantic_store
        if _semantic_memory_disabled:
            return
        _semantic_store = _semantic_store or ChromaStore()
        _semantic_store.remember_metadata_memory(
            record_id=record_id,
            text=text,
            field=field,
            value=value,
            schema_version=schema_version,
        )
    except Exception as exc:
        _semantic_memory_disabled = True
        logger.warning("Could not index metadata reviewer memory: %s", exc)


def _value_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def suggestions(
    *,
    record_id: str,
    text: str,
    field: str,
    cardinality: str,
    schema_version: str = "",
) -> dict[str, Any] | None:
    key, _ = cache_key(
        record_id=record_id,
        text=text,
        field=field,
        cardinality=cardinality,
        schema_version=schema_version,
    )
    return system_store.get_adjudication_cache(key)


def semantic_suggestions(
    *,
    record_id: str,
    text: str,
    field: str,
    schema_version: str = "",
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Return diverse semantic examples without making them authoritative."""
    try:
        global _semantic_memory_disabled, _semantic_store
        if _semantic_memory_disabled:
            return []
        _semantic_store = _semantic_store or ChromaStore()
        return _semantic_store.metadata_memory_suggestions(
            text=text,
            field=field,
            schema_version=schema_version,
            exclude_record_id=record_id,
            n_results=limit,
        )
    except Exception as exc:
        _semantic_memory_disabled = True
        logger.warning("Could not retrieve metadata reviewer memory: %s", exc)
        return []


def clear(*, record_id: str | None = None, field: str | None = None) -> int:
    count = system_store.clear_adjudication_cache(record_id=record_id, field=field)
    try:
        global _semantic_memory_disabled, _semantic_store
        if not _semantic_memory_disabled:
            _semantic_store = _semantic_store or ChromaStore()
            _semantic_store.clear_metadata_memory(record_id=record_id, field=field)
    except Exception as exc:
        logger.warning("Could not clear metadata reviewer memory: %s", exc)
    return count
