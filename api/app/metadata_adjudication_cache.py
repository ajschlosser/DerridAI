# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Best-effort local memory for human metadata suggestions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
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
    value_key: Callable[[Any], str | None] | None = None,
) -> None:
    """Remember a reviewer's decision for this exact Record text and field.

    ``latest_value`` is exactly what the reviewer chose. With ``value_key`` (the field's
    semantic identity), a prior value equivalent to one already remembered is not added
    again, and ``latest_canonical_key`` / ``prior_value_keys`` record the identities.
    Rows written without keys still load and are keyed on the next write.
    """
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

    def identity(item: Any) -> str:
        derived = value_key(item) if value_key is not None else None
        return derived or _value_key(item)

    known = {identity(previous) for previous in prior_values}
    values = value if cardinality == "list" else [value]
    if decision == "absence":
        values = []
    for item in values:
        if item is None:
            continue
        item_key = identity(item)
        if item_key in known:
            continue
        known.add(item_key)
        prior_values.append(item)
    prior_values = prior_values[-50:]
    payload = {
        "latest_value": value,
        "prior_values": prior_values,
        "cardinality": cardinality,
        "schema_version": schema_version,
        "decision": decision,
        "field_id": field_id or field,
    }
    if value_key is not None:
        payload["prior_value_keys"] = [identity(item) for item in prior_values]
        if value not in (None, "", []) and not isinstance(value, list):
            payload["latest_canonical_key"] = identity(value)
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
