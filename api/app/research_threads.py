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

"""Research thread service: starts runs inside threads and mirrors job outcomes onto turns.

A thread is conversational continuity only. Every turn still produces its own
independently auditable ResearchRun (the job), so this module never touches the
prompt, the evidence packet, or response memory. It links identities and freezes
server-owned advisory context selections before starting a job.
"""
from __future__ import annotations

import logging
from typing import Any

from . import operation_events
from .models import RAGRunRequest
from .research_context import select_thread_context
from .research_thread_store import ResearchThreadStore, ThreadNotFound, get_thread_store

logger = logging.getLogger(__name__)

RESOURCE = "research_threads"


def thread_store() -> ResearchThreadStore:
    return get_thread_store()


def notify_changed() -> None:
    operation_events.note_resource_changed(RESOURCE)


def start_run(
    jobs: Any,
    body: RAGRunRequest,
    *,
    owner: str,
    thread_id: str | None = None,
    retry_turn_id: str | None = None,
) -> dict[str, Any]:
    """Persist (or reuse) the turn for ``body`` and start its Research job.

    The client supplies only identifiers: prior thread content is always loaded
    server-side. A repeated idempotency key returns the original turn's job
    instead of creating another run.
    """
    store = thread_store()
    thread_id = thread_id or body.thread_id
    if retry_turn_id:
        turn = store.get_turn(retry_turn_id, owner)
        if body.prompt.strip() != turn["user_question"]:
            raise ValueError("A retry must resubmit the turn's original question.")
        turn = store.retry_turn(retry_turn_id, owner)
    else:
        if thread_id is None:
            thread_id = store.create_thread(owner)["thread_id"]
        turn, created = store.append_turn(
            thread_id,
            owner,
            body.prompt,
            user_instructions=body.instructions,
            idempotency_key=body.idempotency_key,
        )
        if not created and turn["job_id"]:
            return _with_thread(jobs.get(turn["job_id"]), turn)
    body = body.model_copy(update={"thread_id": turn["thread_id"]})
    try:
        # Stored for audit only in this checkpoint; generation still receives
        # no historical content until the separate prompt contract lands.
        context = select_thread_context(store, turn["turn_id"], owner, jobs.get)
        store.save_context_selection(turn["turn_id"], owner, context.snapshot())
        job = jobs.create(body, owner=owner, turn_id=turn["turn_id"])
    except Exception as exc:
        store.end_turn(turn["turn_id"], owner, status="failed", error=str(exc))
        notify_changed()
        raise
    notify_changed()
    return _with_thread(job, store.get_turn(turn["turn_id"], owner))


def _with_thread(job: dict[str, Any], turn: dict[str, Any]) -> dict[str, Any]:
    return {**job, "thread_id": turn["thread_id"], "turn_id": turn["turn_id"]}


def bind_job(turn_id: str, owner: str, job_id: str) -> None:
    thread_store().bind_job(turn_id, owner, job_id=job_id, research_run_id=job_id)


def sync_turn_from_job(job: dict[str, Any]) -> None:
    """Mirror a finished job's outcome onto its turn. Never raises into the job."""
    turn_id = job.get("turn_id")
    owner = str(job.get("owner") or "")
    if not turn_id or not owner:
        return
    status = job.get("status")
    store = thread_store()
    try:
        if status == "completed":
            cache = job.get("response_cache")
            record_id = cache.get("record_id") if isinstance(cache, dict) else None
            store.complete_turn(
                turn_id,
                owner,
                research_run_id=job["id"],
                response_record_id=str(record_id or job["id"]),
            )
        elif status in ("failed", "cancelled"):
            store.end_turn(
                turn_id,
                owner,
                status=status,
                error=job.get("error_message") or job.get("stage_detail"),
            )
        else:
            return
    except ThreadNotFound:
        pass  # thread deleted while the run was in flight; the run itself is unaffected
    except Exception:  # noqa: BLE001 - linkage must never break a finished run
        logger.exception("Could not link Research job %s to turn %s", job.get("id"), turn_id)
        return
    notify_changed()
