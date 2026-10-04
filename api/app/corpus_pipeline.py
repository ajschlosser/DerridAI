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

"""Explicit context passed between corpus construction stages."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BuildScope:
    build: dict[str, Any]
    asset: dict[str, Any]
    manifest: dict[str, Any]
    source_blocks: list[dict[str, Any]]
    semantic_blocks: list[dict[str, Any]]
    source_quality: dict[str, Any]
    source_scope_repair: bool
    source_pages: list[dict[str, Any]] = field(default_factory=list)


def select_source_pages(
    blocks: list[dict[str, Any]],
    asset: dict[str, Any],
    source_scope: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[int]]:
    """Return the documentary blocks selected for one build without mutating the source asset.

    An empty or omitted pages list means the complete source. Explicit selections
    are validated against the extracted page representation so a typo cannot
    silently produce an incomplete corpus.
    """
    raw_pages = (source_scope or {}).get("pages") or []
    requested = sorted({
        value
        for item in raw_pages
        if not isinstance(item, bool)
        for value in [int(item)]
        if value > 0
    })
    if not requested:
        return blocks, []

    available: set[int] = set()
    for page_info in asset.get("pages") or []:
        if not isinstance(page_info, dict):
            continue
        value = page_info.get("pdf_page")
        if isinstance(value, (int, str)) and str(value).isdigit():
            available.add(int(value))
    if not available:
        for block in blocks:
            value = block.get("page")
            if isinstance(value, (int, str)) and str(value).isdigit():
                available.add(int(value))
    missing = [value for value in requested if value not in available]
    if missing:
        rendered = ", ".join(
            str(value) for index, value in enumerate(missing) if index < 10
        )
        suffix = "…" if len(missing) > 10 else ""
        raise ValueError(f"Selected source page(s) are not available: {rendered}{suffix}")

    requested_set = set(requested)
    selected = [block for block in blocks if int(block.get("page") or 0) in requested_set]
    if not selected:
        raise ValueError("The selected source pages contain no extractable SourceUnits.")
    return selected, requested
