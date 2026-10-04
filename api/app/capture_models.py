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

"""Operation-specific request schemas for Corpus Capture and the Sources workspace."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ProviderId = Literal["gutenberg", "wikisource"]
RoleId = Literal["author", "coauthor", "translator", "editor", "contributor", "about_author"]


def _default_providers() -> list[ProviderId]:
    return ["gutenberg", "wikisource"]


def _default_roles() -> list[RoleId]:
    return ["author", "coauthor"]


class CaptureOptionsBody(BaseModel):
    providers: list[ProviderId] = Field(default_factory=_default_providers, min_length=1, max_length=2)
    roles: list[RoleId] = Field(default_factory=_default_roles, min_length=1, max_length=6)
    include_translations: bool = True
    include_originals: bool = True
    # None/empty = every available language.
    languages: list[str] | None = Field(default=None, max_length=100)

    @field_validator("languages")
    @classmethod
    def _codes(cls, value: list[str] | None) -> list[str] | None:
        if not value:
            return None
        cleaned = [item.strip().lower() for item in value]
        if any(not re.fullmatch(r"[a-z]{2,3}(-[a-z0-9]{2,8})*", item) for item in cleaned):
            raise ValueError("languages must be BCP 47 language codes")
        return cleaned


class CaptureCreate(BaseModel):
    # New clients send a provider-neutral identity. wikidata_qid remains a
    # compatibility field for existing API clients and stored tests.
    identity_id: str | None = Field(default=None, min_length=3, max_length=200)
    wikidata_qid: str | None = Field(default=None, pattern=r"^Q[1-9]\d{0,11}$")
    options: CaptureOptionsBody = Field(default_factory=CaptureOptionsBody)
    start_discovery: bool = True
    ui_language: str = Field(default="en", pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")

    @model_validator(mode="after")
    def _identity(self) -> "CaptureCreate":
        if self.identity_id is None and self.wikidata_qid:
            self.identity_id = f"wikidata:{self.wikidata_qid}"
        if not self.identity_id:
            raise ValueError("Choose an author identity.")
        if self.identity_id.startswith("wikidata:"):
            qid = self.identity_id.split(":", 1)[1]
            if not re.fullmatch(r"Q[1-9]\d{0,11}", qid):
                raise ValueError("Invalid Wikidata author identity.")
            if self.wikidata_qid and self.wikidata_qid != qid:
                raise ValueError("Author identity and Wikidata QID disagree.")
            self.wikidata_qid = qid
        elif not re.fullmatch(r"gutenberg:\d+:\d+", self.identity_id):
            raise ValueError("Unsupported author identity.")
        return self


class CaptureSelectionPatch(BaseModel):
    # None = every candidate in the capture.
    candidate_ids: list[str] | None = Field(default=None, max_length=5000)
    selected: bool


class SourceBulkDelete(BaseModel):
    source_document_ids: list[str] = Field(min_length=1, max_length=500)
