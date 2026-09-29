# Copyright 2026 Aaron John Schlosser, PhD.
"""Read-only built-in domain metadata schema profiles."""

from __future__ import annotations

from ..metadata_schema import DEFAULT_SCHEMA_ID, MetadataSchema, default_schema
from .fiction import FICTION_SCHEMA_ID, fiction_schema
from .nonfiction import NONFICTION_SCHEMA_ID, nonfiction_schema

BUILTIN_SCHEMA_IDS = frozenset(
    {DEFAULT_SCHEMA_ID, FICTION_SCHEMA_ID, NONFICTION_SCHEMA_ID}
)


def builtin_schemas() -> tuple[MetadataSchema, ...]:
    """Return built-ins in UI order, preserving the historical default first."""

    return default_schema(), fiction_schema(), nonfiction_schema()


def builtin_schema(schema_id: str) -> MetadataSchema | None:
    """Return a fresh built-in schema instance by ID without constructing unrelated profiles."""

    if schema_id == DEFAULT_SCHEMA_ID:
        return default_schema()
    if schema_id == FICTION_SCHEMA_ID:
        return fiction_schema()
    if schema_id == NONFICTION_SCHEMA_ID:
        return nonfiction_schema()
    return None


__all__ = [
    "BUILTIN_SCHEMA_IDS",
    "FICTION_SCHEMA_ID",
    "NONFICTION_SCHEMA_ID",
    "builtin_schema",
    "builtin_schemas",
    "fiction_schema",
    "nonfiction_schema",
]
