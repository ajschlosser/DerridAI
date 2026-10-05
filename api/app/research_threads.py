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

import copy
import logging
from typing import Any

from . import operation_events
from .models import RAGRunRequest
from .research_context import (
    ThreadContextPolicy,
    rank_cached_thread_context,
    select_thread_context,
)
from .research_thread_store import ResearchThreadStore, ThreadNotFound, get_thread_store
from .research_turn_results import saved_turn_result

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
        # Resolve the same immutable pipeline version/override policy as the worker.
        from .pipelines.manager import pipeline_manager
        from .pipelines.models import PipelineDefinition
        from .pipelines.overrides import resolve_pipeline_config
        from .pipelines.research import compile_research_pipeline

        definition = (pipeline_manager.get_definition(body.pipeline_id, body.pipeline_version)
                      if body.pipeline_id else PipelineDefinition.model_validate(
                          pipeline_manager.resolve("research")["pipeline"]))
        if definition is None:
            raise ValueError("Research pipeline was not found")
        effective = resolve_pipeline_config(
            definition, settings_overrides=body.settings_pipeline_overrides,
            run_overrides=body.run_pipeline_overrides,
        ).effective
        plan = compile_research_pipeline(effective)
        context_config = plan.stage_configs.get(plan.thread_context_stage_id) or {}
        policy = ThreadContextPolicy(**{key: value for key, value in context_config.items()
                                       if key in {"max_turns", "max_characters", "max_answer_characters", "include_answers"}})
        body = body.model_copy(update={"pipeline_id": definition.pipeline_id, "pipeline_version": definition.version})
        cache = getattr(jobs, "_store", None)
        context = select_thread_context(
            store, turn["turn_id"], owner, jobs.get, policy=policy,
            read_saved=(lambda prior, username: saved_turn_result(prior, username, cache)) if cache else None,
            rank_older=(lambda query, texts: rank_cached_thread_context(query, texts, body.cross_encoder_model))
            if context_config.get("semantic", True) else None,
        )
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


def run_thread_audit(turn_id: str, owner: str) -> dict[str, Any]:
    """Copy the exact attempt snapshot before binding; never select history again."""
    turn = thread_store().get_turn(turn_id, owner)
    selection = turn.get("context_selection")
    if selection is not None and selection.get("attempt") != turn["attempt"]:
        raise ValueError("Thread context snapshot belongs to another attempt")
    return {
        "version": "research-thread-run-v1",
        "thread_id": turn["thread_id"],
        "turn_id": turn["turn_id"],
        "turn_ordinal": turn["ordinal"],
        "parent_turn_id": turn.get("parent_turn_id"),
        "attempt": turn["attempt"],
        "original_question": turn["user_question"],
        "context_selection": copy.deepcopy(selection),
        "context_consumed": False,
        "warnings": list(selection.get("warnings", [])) if selection is not None else ["thread_context_snapshot_unavailable"],
    }


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
                contextualized_query=((job.get("result") or {}).get("query_metadata") or {}).get("prompt_query"),
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


def import_legacy_responses(owner: str, cache: Any, *, offset: int = 0, limit: int = 200) -> dict[str, Any]:
    """Materialize one bounded owner-scoped batch; preserve cache and provenance."""
    page = cache.get_legacy_response_summaries(owner, limit=limit, offset=offset)
    created = thread_store().materialize_legacy(owner, page["records"])
    if created:
        notify_changed()
    return {"created": len(created), "next_offset": offset + page["scanned"],
            "has_more": page["scanned"] == limit}
