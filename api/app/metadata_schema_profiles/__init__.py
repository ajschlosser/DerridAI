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
