# Copyright 2026 Aaron John Schlosser, PhD.
"""Operation-specific request schemas for Corpus Capture and the Sources workspace."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ProviderId = Literal["gutenberg", "wikisource"]
RoleId = Literal["author", "coauthor", "translator", "editor", "contributor", "about_author"]


class CaptureOptionsBody(BaseModel):
    providers: list[ProviderId] = Field(default_factory=lambda: ["gutenberg", "wikisource"], min_length=1, max_length=2)
    roles: list[RoleId] = Field(default_factory=lambda: ["author", "coauthor"], min_length=1, max_length=6)
    include_translations: bool = True
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
    wikidata_qid: str = Field(pattern=r"^Q[1-9]\d{0,11}$")
    options: CaptureOptionsBody = Field(default_factory=CaptureOptionsBody)
    start_discovery: bool = True
    ui_language: str = Field(default="en", pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")


class CaptureSelectionPatch(BaseModel):
    # None = every candidate in the capture.
    candidate_ids: list[str] | None = Field(default=None, max_length=5000)
    selected: bool


class SourceBulkDelete(BaseModel):
    source_document_ids: list[str] = Field(min_length=1, max_length=500)
