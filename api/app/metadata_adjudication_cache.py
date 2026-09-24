# Copyright 2026 Aaron John Schlosser, PhD.
"""Best-effort local memory for human metadata suggestions."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .system_store import system_store


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
    decision: str = "value",
    field_id: str | None = None,
) -> None:
    if decision not in {"value", "absence", "correction"}:
        raise ValueError("Unsupported adjudication decision.")
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
    if decision == "absence":
        values = []
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
        "decision": decision,
        "field_id": field_id or field,
    }
    system_store.put_adjudication_cache(
        key, record_id, field, cardinality, digest, payload
    )


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



def clear(*, record_id: str | None = None, field: str | None = None) -> int:
    return system_store.clear_adjudication_cache(record_id=record_id, field=field)
