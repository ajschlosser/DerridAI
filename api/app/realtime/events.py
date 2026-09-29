# Copyright 2026 Aaron John Schlosser, PhD.
"""Observe shared job/corpus state and publish normalized public events.

One observer thread reads the same live job state that REST snapshots expose
(``PersistentJobStateMixin.realtime_job_summaries``) plus transport-neutral
corpus/model-activity notes, diffs it against what it last published, and
emits events through the broker. Because it samples at most
``REALTIME_PROGRESS_MAX_HZ`` times per second, every resource's progress rate
is bounded without any worker knowing sockets exist, and a publishing failure
can never stall or fail a job.
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterable
from typing import Any

from .. import operation_events
from ..config import settings
from .broker import EventBroker
from .protocol import Audience

logger = logging.getLogger("derridai.realtime")

STATUS_EVENTS = {
    "queued": "job.queued",
    "running": "job.started",
    "cancelling": "job.cancelling",
    "cancelled": "job.cancelled",
    "completed": "job.completed",
    "failed": "job.failed",
    "interrupted": "job.failed",
    "blocked": "job.needs_attention",
}

_CORPUS_SUMMARY_KEYS = (
    "id",
    "type",
    "status",
    "raw_status",
    "stage",
    "stage_detail",
    "record_count",
    "review_count",
    "metadata_tasks_total",
    "metadata_tasks_completed",
    "metadata_tasks_failed",
    "metadata_tasks_skipped",
    "metadata_tasks_running",
    "metadata_tasks_queued",
    "unresolved_regions",
    "progress",
    "total",
    "completed",
    "failed",
    "cancel_requested",
    "created_at",
    "started_at",
    "finished_at",
)
TERMINAL_JOB_STATUSES = frozenset({"completed", "failed", "cancelled", "interrupted"})
_METADATA_KEYS = tuple(key for key in _CORPUS_SUMMARY_KEYS if key.startswith("metadata_tasks_"))

METADATA_NOTE_EVENTS = {
    "record_started": "corpus.record_started",
    "field_checked": "corpus.field_checked",
    "record_completed": "corpus.record_completed",
}
# One llm.token event carries at most this much text; a longer pending draft is
# split into several sequence-numbered events.
MAX_TOKEN_EVENT_CHARS = 4096


def job_event_types(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[str]:
    """Public event types for one job transition, in delivery order."""
    if previous is None:
        return ["job.created"]
    events: list[str] = []
    if current.get("stage") != previous.get("stage"):
        events.append("job.stage_changed")
    if int(current.get("warnings_count") or 0) > int(previous.get("warnings_count") or 0):
        events.append("job.warning")
    if current.get("status") != previous.get("status"):
        events.append(STATUS_EVENTS.get(str(current.get("status")), "job.progress"))
    if not events and current != previous:
        events.append("job.progress")
    return events


def corpus_event_types(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[str]:
    if previous is None:
        return ["corpus.build_changed"]
    events: list[str] = []
    if current.get("stage") != previous.get("stage"):
        events.append("corpus.stage_changed")
    if (current.get("status"), current.get("raw_status"), current.get("cancel_requested")) != (
        previous.get("status"), previous.get("raw_status"), previous.get("cancel_requested"),
    ):
        events.append("corpus.build_changed")
    if any(current.get(key) != previous.get(key) for key in _METADATA_KEYS):
        events.append("corpus.metadata_progress")
    if current.get("review_count") != previous.get("review_count"):
        events.append("corpus.review_queue_changed")
    if not events and current != previous:
        events.append("corpus.progress")
    return events


def model_activity_event_type(previous: dict[str, Any] | None, current: dict[str, Any]) -> str | None:
    before = int((previous or {}).get("calls_in_flight") or 0)
    after = int(current.get("calls_in_flight") or 0)
    if before == 0 and after > 0:
        return "llm.started"
    if before > 0 and after == 0:
        return "llm.completed"
    if after > 0 and current != previous:
        return "llm.progress"
    return None


def _job_audience(summary: dict[str, Any]) -> Audience:
    # Only Research (RAG) jobs are visible to their non-admin owner, matching
    # GET /api/jobs. Every other job type is administrator-only.
    if summary.get("type") == "rag":
        return Audience(owner=summary.get("owner"), admin_only=False, capability="rag.jobs.own")
    return Audience(admin_only=True)


def _public_job(summary: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in summary.items() if key not in {"owner", "dismissed"}}


def _default_managers() -> tuple[Any, ...]:
    from ..services import (
    capture_jobs,
    document_nlp_pack_jobs,
    llm_jobs,
    llm_tool_jobs,
    rag_jobs,
    upsert_jobs,
)

    return (llm_jobs, llm_tool_jobs, rag_jobs, upsert_jobs, capture_jobs, document_nlp_pack_jobs)


class RealtimeObserver:
    def __init__(
        self,
        broker: EventBroker,
        *,
        managers: Callable[[], Iterable[Any]] = _default_managers,
        interval: float | None = None,
    ) -> None:
        self.broker = broker
        self._managers = managers
        hz = max(0.5, float(settings.realtime_progress_max_hz or 8.0))
        self.interval = interval if interval is not None else 1.0 / hz
        self._jobs: dict[str, dict[str, Any]] = {}
        self._builds: dict[str, dict[str, Any]] = {}
        self._activity: dict[str, dict[str, Any]] = {}
        self._background: dict[str, dict[str, Any]] = {}
        self._generation_seq: dict[str, int] = {}
        self.metadata_notes_dropped = 0
        self._primed = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="derridai-realtime-observer")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                logger.exception("Realtime observer tick failed; continuing")
            self._stop.wait(self.interval)

    # -- sampling ----------------------------------------------------------
    def _current_jobs(self) -> dict[str, dict[str, Any]]:
        current: dict[str, dict[str, Any]] = {}
        for manager in self._managers():
            try:
                summaries = manager.realtime_job_summaries()
            except Exception:
                logger.exception("Could not sample %s for realtime events", type(manager).__name__)
                continue
            for summary in summaries:
                if summary.get("id") and not summary.get("dismissed"):
                    current[str(summary["id"])] = summary
        return current

    def tick(self) -> None:
        current = self._current_jobs()
        if not self._primed:
            # Start from the state that exists now; clients bootstrap from REST.
            self._jobs = current
            self._primed = True
        else:
            self._publish_job_diff(current)
        notes = operation_events.drain()
        for build_id, raw in notes.builds.items():
            self._publish_build(build_id, raw)
        for build_id, state in notes.model_activity.items():
            self._publish_activity(build_id, state)
        self.metadata_notes_dropped += notes.metadata_dropped
        for note in notes.metadata:
            self._publish_metadata_note(note)
        for job_id, buffer in notes.generation.items():
            self._publish_generation(job_id, buffer)
        for note in notes.corpus_generation:
            self._publish_corpus_generation(note)
        for kind, summary in notes.activity.items():
            self._publish_background_activity(kind, summary)

    def _publish_job(self, event_type: str, summary: dict[str, Any], *, previous_status: Any = None) -> None:
        job_id = str(summary.get("id"))
        payload: dict[str, Any] = {"job": _public_job(summary)}
        if previous_status is not None:
            payload["previous_status"] = previous_status
        self.broker.publish(
            event_type,
            resource_type="job",
            resource_id=job_id,
            payload=payload,
            topics=("jobs", f"job:{job_id}"),
            audience=_job_audience(summary),
        )

    def _publish_job_diff(self, current: dict[str, dict[str, Any]]) -> None:
        for job_id, summary in current.items():
            previous = self._jobs.get(job_id)
            for event_type in job_event_types(previous, summary):
                self._publish_job(event_type, summary, previous_status=(previous or {}).get("status"))
            if str(summary.get("status")) in TERMINAL_JOB_STATUSES:
                self._generation_seq.pop(job_id, None)
        for job_id in set(self._jobs) - set(current):
            self._generation_seq.pop(job_id, None)
            gone = self._jobs[job_id]
            self._publish_job("job.removed", {key: gone.get(key) for key in ("id", "type", "owner")})
        self._jobs = current

    def _publish_build(self, build_id: str, raw: dict[str, Any]) -> None:
        summary = {key: raw.get(key) for key in _CORPUS_SUMMARY_KEYS if key in raw}
        summary["id"] = build_id
        previous = self._builds.get(build_id)
        self._builds[build_id] = summary
        admin = Audience(admin_only=True)
        for event_type in corpus_event_types(previous, summary):
            self.broker.publish(
                event_type,
                resource_type="corpus_build",
                resource_id=build_id,
                payload={"build": summary},
                topics=("corpus-builds", f"corpus-build:{build_id}"),
                audience=admin,
            )
        # Corpus builds also appear as rows in the global Operations feed.
        job_summary = {**summary, "type": "pdf_corpus", "owner": None}
        if raw.get("operation_hidden"):
            if previous is not None:
                self._publish_job("job.removed", {"id": build_id, "type": "pdf_corpus", "owner": None})
            return
        previous_job = None if previous is None else {**previous, "type": "pdf_corpus", "owner": None}
        event_types = ["job.snapshot"] if previous_job is None else job_event_types(previous_job, job_summary)
        for event_type in event_types:
            self._publish_job(event_type, job_summary, previous_status=(previous or {}).get("status"))

    def _publish_activity(self, build_id: str, state: dict[str, Any]) -> None:
        previous = self._activity.get(build_id)
        self._activity[build_id] = state
        event_type = model_activity_event_type(previous, state)
        if event_type is None:
            return
        self.broker.publish(
            event_type,
            resource_type="corpus_build",
            resource_id=build_id,
            payload={"activity": dict(state)},
            topics=("corpus-builds", f"corpus-build:{build_id}"),
            audience=Audience(admin_only=True),
        )

    def _publish_metadata_note(self, note: dict[str, Any]) -> None:
        event_type = METADATA_NOTE_EVENTS.get(str(note.get("kind")))
        build_id = str(note.get("build_id") or "")
        if event_type is None or not build_id:
            return
        # Identifiers, family, terminal state and precedent counts only: never
        # field values, evidence or model output. Sent on the build's own topic,
        # not the global feed, because only a watching view can use them.
        payload = {key: value for key, value in note.items() if key not in {"build_id", "kind"}}
        self.broker.publish(
            event_type,
            resource_type="corpus_build",
            resource_id=build_id,
            payload={"metadata": payload},
            topics=(f"corpus-build:{build_id}",),
            audience=Audience(admin_only=True),
        )

    def _publish_corpus_generation(self, note: dict[str, Any]) -> None:
        """Publish text-free model progress; raw Corpus Builder output never crosses WebSocket."""
        build_id = str(note.get("build_id") or "")
        call_id = str(note.get("call_id") or "")
        if not build_id or not call_id:
            return
        self.broker.publish(
            "corpus.llm_progress",
            resource_type="corpus_build",
            resource_id=build_id,
            payload={
                "generation": {
                    "call_id": call_id,
                    "seq": int(note.get("seq") or 0),
                    "chars": int(note.get("chars") or 0),
                    "gap": bool(note.get("gap")),
                    "final": bool(note.get("final")),
                },
            },
            topics=(f"corpus-build:{build_id}",),
            audience=Audience(admin_only=True),
        )

    def _publish_generation(self, job_id: str, buffer: operation_events.GenerationBuffer) -> None:
        """Forward streamed Research draft text on ``job:<id>`` only, to whoever may read that job."""
        text = "".join(buffer.chunks)
        pieces = [text[index:index + MAX_TOKEN_EVENT_CHARS] for index in range(0, len(text), MAX_TOKEN_EVENT_CHARS)]
        if buffer.finished and not pieces:
            pieces = [""]
        audience = Audience(owner=buffer.owner, admin_only=False, capability="rag.jobs.own")
        for index, piece in enumerate(pieces):
            seq = self._generation_seq.get(job_id, 0) + 1
            self._generation_seq[job_id] = seq
            last = index == len(pieces) - 1
            self.broker.publish(
                "llm.token",
                resource_type="job",
                resource_id=job_id,
                payload={
                    "generation": {
                        "seq": seq,
                        "delta": piece,
                        # Text was dropped before this delta: the client must stop
                        # appending and wait for the final answer.
                        "gap": bool(buffer.gap and index == 0),
                        "final": bool(buffer.finished and last),
                    },
                },
                topics=(f"job:{job_id}",),
                audience=audience,
            )
        if buffer.finished:
            self._generation_seq.pop(job_id, None)

    def _publish_background_activity(self, kind: str, summary: dict[str, Any]) -> None:
        if self._background.get(kind) == summary:
            return
        self._background[kind] = dict(summary)
        self.broker.publish(
            "activity.changed",
            resource_type="activity",
            resource_id=kind,
            payload={"activity": dict(summary)},
            topics=(f"activity:{kind}",),
            audience=Audience(admin_only=True),
        )
