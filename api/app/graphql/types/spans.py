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

"""Medium-aware source locators."""
from __future__ import annotations

from typing import Any

import strawberry

from .common import opt_float, opt_int, opt_str, str_list


@strawberry.type(description="A medium-aware documentary locator. Audio spans use time and speaker, never PDF pages.")
class SourceSpan:
    source_document_id: str | None
    source_span_id: str | None
    source_unit_ids: list[str]
    locator_kind: str | None
    physical_page_start: int | None
    physical_page_end: int | None
    printed_page_start: str | None
    printed_page_end: str | None
    character_start: int | None
    character_end: int | None
    time_start: float | None
    time_end: float | None
    speaker: str | None

    @classmethod
    def from_locator(cls, locator: dict[str, Any]) -> SourceSpan:
        unit_ids = str_list(locator.get("source_unit_ids"))
        for key in ("source_unit_id", "block_id"):
            if locator.get(key) and str(locator[key]) not in unit_ids:
                unit_ids.append(str(locator[key]))
        return cls(
            source_document_id=opt_str(locator.get("source_document_id")),
            source_span_id=opt_str(locator.get("source_span_id")),
            source_unit_ids=unit_ids,
            locator_kind=opt_str(locator.get("locator_kind")),
            physical_page_start=opt_int(locator.get("physical_page_start")),
            physical_page_end=opt_int(locator.get("physical_page_end")),
            printed_page_start=opt_str(locator.get("printed_page_start")),
            printed_page_end=opt_str(locator.get("printed_page_end")),
            character_start=opt_int(locator.get("character_start")),
            character_end=opt_int(locator.get("character_end")),
            time_start=opt_float(locator.get("time_start")),
            time_end=opt_float(locator.get("time_end")),
            speaker=opt_str(locator.get("speaker")),
        )
