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

from fastapi import APIRouter, HTTPException, Request

from ..gutenberg_catalogue import gutenberg_offline
from ..http_auth import request_user

router = APIRouter(tags=["gutenberg"])


@router.get("/api/gutenberg/status")
def gutenberg_status(request: Request) -> dict:
    request_user(request)
    return gutenberg_offline.status()


@router.post("/api/gutenberg/catalogue/refresh")
def refresh_catalogue(request: Request) -> dict:
    request_user(request)
    try:
        return gutenberg_offline.start_catalogue_refresh()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Catalogue refresh failed: {exc}") from exc


@router.post("/api/gutenberg/archive/{action}")
def archive_action(action: str, request: Request) -> dict:
    request_user(request)
    try:
        # start/resume only schedules the durable archive worker. Downloading
        # must never run inside the request handler: the client may disconnect or
        # refresh while the server continues the resumable operation.
        return gutenberg_offline.set_archive_status(action)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Archive operation failed: {exc}") from exc
