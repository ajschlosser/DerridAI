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

"""Research thread routes: owner-scoped navigation and follow-up turns.

Thread and turn payloads are shells (identifiers, question text, status and
linkage). Evidence and answers are read through the existing Research result
and Response Library routes, so listing a thread never ships evidence packets.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from .. import research_threads
from ..http_auth import request_user
from ..models import RAGRunRequest
from ..research_thread_store import ThreadNotFound
from .jobs import start_research_run

router = APIRouter(tags=["research-threads"])


class ThreadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, max_length=200)


class ThreadPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, max_length=200)
    archived: bool | None = None


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Research thread not found.")


@router.get("/api/research/threads")
def list_threads(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
    include_archived: bool = False,
) -> dict[str, Any]:
    owner = request_user(request).username
    threads = research_threads.thread_store().list_threads(
        owner, limit=limit, offset=offset, search=search, include_archived=include_archived
    )
    return {"threads": threads}


@router.post("/api/research/threads", status_code=201)
def create_thread(body: ThreadCreate, request: Request) -> dict[str, Any]:
    thread = research_threads.thread_store().create_thread(
        request_user(request).username, title=body.title
    )
    research_threads.notify_changed()
    return thread


@router.get("/api/research/threads/{thread_id}")
def get_thread(thread_id: str, request: Request) -> dict[str, Any]:
    try:
        return research_threads.thread_store().get_thread(thread_id, request_user(request).username)
    except ThreadNotFound as exc:
        raise _not_found() from exc


@router.patch("/api/research/threads/{thread_id}")
def patch_thread(thread_id: str, body: ThreadPatch, request: Request) -> dict[str, Any]:
    owner = request_user(request).username
    store = research_threads.thread_store()
    try:
        thread = store.get_thread(thread_id, owner)
        if body.title is not None:
            thread = store.rename_thread(thread_id, owner, body.title)
        if body.archived is not None:
            thread = store.set_archived(thread_id, owner, body.archived)
    except ThreadNotFound as exc:
        raise _not_found() from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    research_threads.notify_changed()
    return {key: value for key, value in thread.items() if key != "turns"}


@router.delete("/api/research/threads/{thread_id}", status_code=204)
def delete_thread(thread_id: str, request: Request) -> None:
    try:
        research_threads.thread_store().delete_thread(thread_id, request_user(request).username)
    except ThreadNotFound as exc:
        raise _not_found() from exc
    research_threads.notify_changed()


@router.post("/api/research/threads/{thread_id}/turns")
def append_turn(thread_id: str, body: RAGRunRequest, request: Request) -> dict[str, Any]:
    """Start the next question of an existing thread (runs through the normal Research validation)."""
    return start_research_run(body, request, thread_id=thread_id)


@router.get("/api/research/threads/{thread_id}/turns/{turn_id}")
def get_turn(thread_id: str, turn_id: str, request: Request) -> dict[str, Any]:
    try:
        turn = research_threads.thread_store().get_turn(turn_id, request_user(request).username)
    except ThreadNotFound as exc:
        raise _not_found() from exc
    if turn["thread_id"] != thread_id:
        raise _not_found()
    return turn


@router.post("/api/research/threads/{thread_id}/turns/{turn_id}/retry")
def retry_turn(thread_id: str, turn_id: str, body: RAGRunRequest, request: Request) -> dict[str, Any]:
    """Re-run a failed or cancelled turn in place: same visible question, next attempt."""
    try:
        turn = research_threads.thread_store().get_turn(turn_id, request_user(request).username)
    except ThreadNotFound as exc:
        raise _not_found() from exc
    if turn["thread_id"] != thread_id:
        raise _not_found()
    return start_research_run(body, request, thread_id=thread_id, retry_turn_id=turn_id)
