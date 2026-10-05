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

"""Owned turn result recovery; caches are artifacts, never thread authority."""
from __future__ import annotations

import copy
from typing import Any

from .research_thread_store import ThreadNotFound


def saved_turn_result(turn: dict[str, Any], owner: str, cache: Any) -> dict[str, Any]:
    record_id = turn.get("response_record_id")
    if not record_id:
        raise KeyError("No saved answer artifact")
    try:
        record = cache.get_record("_response_cache", record_id)
    except Exception as exc:
        if getattr(cache, "_is_missing_collection_error", lambda _: False)(exc):
            raise KeyError("Saved answer collection is unavailable") from exc
        raise
    if not isinstance(record, dict):
        raise KeyError("Saved answer artifact is unavailable")
    audit = record.get("research_thread")
    # A legacy singleton is authorized by its SQLite materialization link,
    # exact owner/run/question and first attempt, never by a client-provided ID.
    legacy = False
    if audit is None:
        from .research_threads import thread_store
        thread = thread_store().get_thread(turn["thread_id"], owner)
        legacy = (thread.get("originating_response_record_id") == record_id
                  and turn["ordinal"] == 1 and turn["attempt"] == 1)
    # Unowned entries remain in the administrative archive; never invent ownership.
    if (
        record.get("record_id") != record_id
        or record.get("owner") != owner
        or record.get("response_id") != turn.get("research_run_id")
        or (not legacy and (
            not isinstance(audit, dict)
            or audit.get("thread_id") != turn["thread_id"]
            or audit.get("turn_id") != turn["turn_id"]
            or audit.get("attempt") != turn["attempt"]
        ))
        or record.get("question") != turn["user_question"]
    ):
        raise ThreadNotFound(turn["turn_id"])
    from .pipelines.store import pipeline_store
    trace = pipeline_store.get_run(str(turn["research_run_id"]))
    if trace is not None and trace.owner != owner:
        raise ThreadNotFound(turn["turn_id"])
    return {
        "id": turn["research_run_id"], "owner": owner, "turn_id": turn["turn_id"],
        "thread_id": turn["thread_id"], "status": "completed", "prompt": turn["user_question"],
        "result": copy.deepcopy({
            "prompt": record["question"], "answer": record.get("text") or "",
            "raw_answer": record.get("raw_answer") or "", "evidence": record.get("evidence") or [],
            "provider": record.get("provider"), "model": record.get("model"),
            "query_metadata": record.get("query_metadata") or {},
            "retrieval": record.get("retrieval") or {}, "stages": record.get("pipeline_stages") or [],
            "warnings": record.get("warnings") or [], "elapsed_seconds": record.get("elapsed_seconds"),
            "research_thread": audit,
            "pipeline": record.get("pipeline") or {},
            "prompt_contract": record.get("prompt_contract"),
            "query_contract": record.get("query_contract"),
            "pipeline_trace": trace.model_dump(mode="json") if trace else None,
            "auto_grade": record.get("grade"), "response_cache": {"record_id": record_id},
        }),
        "result_source": "saved_response",
    }


def owned_turn_result(turn: dict[str, Any], owner: str, jobs: Any, cache: Any) -> dict[str, Any]:
    if turn["status"] != "completed":
        raise KeyError("Turn has no completed answer")
    job = None
    if turn.get("job_id"):
        try:
            job = jobs.get(turn["job_id"])
        except KeyError:
            pass
    if job is not None:
        if (job.get("id") != turn["job_id"] or job.get("owner") != owner
                or job.get("turn_id") != turn["turn_id"] or job.get("status") != "completed"):
            raise ThreadNotFound(turn["turn_id"])
        result = job.get("result")
        if isinstance(result, dict) and result.get("answer"):
            return job
    return saved_turn_result(turn, owner, cache)
