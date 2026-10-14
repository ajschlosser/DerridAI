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

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..models import ChromaConnectionUpdate, ChromaPathUpdate
from ..services import store

router = APIRouter(tags=["chroma"])


@router.get("/api/chroma/path")
def get_chroma_path() -> dict[str, Any]:
    return store.health()


@router.put("/api/chroma/path")
def set_chroma_path(body: ChromaPathUpdate) -> dict[str, Any]:
    try:
        return store.set_path(body.path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/chroma/connection")
def get_chroma_connection() -> dict[str, Any]:
    return store.health()


@router.post("/api/chroma/connection/probe")
def probe_chroma_connection(body: ChromaConnectionUpdate) -> dict[str, Any]:
    try:
        return store.probe_connection(
            mode=body.mode,
            path=body.path,
            url=body.url,
            token=body.token,
            tenant=body.tenant,
            database=body.database,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/api/chroma/connection")
def set_chroma_connection(body: ChromaConnectionUpdate) -> dict[str, Any]:
    try:
        return store.set_connection(
            mode=body.mode,
            path=body.path,
            url=body.url,
            token=body.token,
            tenant=body.tenant,
            database=body.database,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

