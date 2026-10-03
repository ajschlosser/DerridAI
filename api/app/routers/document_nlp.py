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

"""Administrator commands for Document Intelligence language packs."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .. import document_nlp_packs as packs
from ..http_auth import require_admin
from ..services import document_nlp_pack_jobs

router = APIRouter(tags=["document-intelligence"])


class PackFile(BaseModel):
    role: str = Field(max_length=16)
    filename: str = Field(max_length=200)
    url: str = Field(max_length=2000)
    sha256: str = Field(max_length=64)
    size: int | None = None


class PackEntry(BaseModel):
    pack_id: str = Field(max_length=64)
    language: str = Field(max_length=3)
    engine: str = Field(max_length=64)
    label: str = Field(default="", max_length=200)
    source_url: str = Field(default="", max_length=2000)
    license: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=500)
    requires: list[str] = Field(default_factory=list, max_length=10)
    files: list[PackFile] = Field(min_length=1, max_length=len(packs.ROLES))


def _listing() -> dict[str, Any]:
    items = packs.list_packs()
    for item in items:
        item["active_job"] = document_nlp_pack_jobs.active_for(item["pack_id"])
    return {"packs": items, "models_dir": str(packs.models_root())}


@router.get("/api/document-nlp/packs")
def list_language_packs(request: Request) -> dict[str, Any]:
    require_admin(request)
    return _listing()


@router.post("/api/document-nlp/packs")
def add_language_pack(request: Request, body: PackEntry) -> dict[str, Any]:
    require_admin(request)
    try:
        packs.add_custom_pack(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _listing()


@router.delete("/api/document-nlp/packs/{pack_id}")
def remove_language_pack(request: Request, pack_id: str) -> dict[str, Any]:
    require_admin(request)
    if document_nlp_pack_jobs.active_for(pack_id):
        raise HTTPException(status_code=409, detail="Cancel the install before removing this pack.")
    try:
        packs.uninstall_pack(pack_id)
        packs.remove_custom_pack(pack_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Language pack not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _listing()


@router.post("/api/document-nlp/packs/{pack_id}/install")
def install_language_pack(request: Request, pack_id: str) -> dict[str, Any]:
    user = require_admin(request)
    try:
        return document_nlp_pack_jobs.start(pack_id, owner=user.username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Language pack not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/api/document-nlp/packs/{pack_id}/install")
def uninstall_language_pack(request: Request, pack_id: str) -> dict[str, Any]:
    require_admin(request)
    if document_nlp_pack_jobs.active_for(pack_id):
        raise HTTPException(status_code=409, detail="Cancel the install before removing its files.")
    try:
        packs.uninstall_pack(pack_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Language pack not found.") from exc
    return _listing()
