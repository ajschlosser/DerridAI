# Copyright 2026 Aaron John Schlosser, PhD.
"""Small coercion helpers for mapping stored payloads onto typed fields."""
from __future__ import annotations

from typing import Any


def opt_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def opt_int(value: Any) -> int | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def opt_float(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item not in (None, "")]
