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

"""Transport-neutral change notes from long-running domain work.

Domain code (the corpus repository, the model-call tracker, Research generation,
the metadata executor, untracked background activity) records *that* something
changed here, cheaply and without knowing about sockets. The realtime observer
drains these notes at a bounded rate and turns them into public events. Nothing
here is canonical state: losing a note only delays a client's refresh, and every
client can resynchronize from REST or GraphQL.

Every note is bounded. Latest-wins notes (build summaries, model activity,
activity summaries) keep one entry per resource; discrete notes (per-record
metadata progress) live in a fixed-size ring that counts what it had to drop;
generation text is capped per Research job and marks a gap instead of growing. Corpus
Builder generation notes contain counters only; raw drafts stay behind authenticated REST.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any

# Per-job generation text waiting for the next observer tick. A client that
# cannot keep up sees a sequence gap and waits for the final answer instead.
MAX_PENDING_GENERATION_CHARS = 32_000
# Discrete per-record metadata notes kept between observer ticks.
MAX_METADATA_NOTES = 512
# Field identifiers carried by one metadata note (a family rarely has more).
MAX_NOTE_FIELD_IDS = 32

METADATA_NOTE_KINDS = frozenset({"record_started", "field_checked", "record_completed"})
METADATA_FAMILY_STATES = frozenset({"complete", "failed", "skipped", "needs_review", "retry_pending"})

_lock = threading.Lock()
_corpus_builds: dict[str, dict[str, Any]] = {}
_model_activity: dict[str, dict[str, Any]] = {}
_activity: dict[str, dict[str, Any]] = {}
_metadata_notes: deque[dict[str, Any]] = deque(maxlen=MAX_METADATA_NOTES)
_metadata_dropped = 0
_generation: dict[str, GenerationBuffer] = {}
_resources: set[str] = set()
_corpus_generation: dict[tuple[str, str], dict[str, Any]] = {}


@dataclass
class GenerationBuffer:
    """Text generated since the last drain for one Research job."""

    owner: str | None
    chunks: list[str] = field(default_factory=list)
    chars: int = 0
    gap: bool = False
    finished: bool = False


@dataclass(frozen=True)
class Drained:
    builds: dict[str, dict[str, Any]]
    model_activity: dict[str, dict[str, Any]]
    activity: dict[str, dict[str, Any]]
    metadata: list[dict[str, Any]]
    metadata_dropped: int
    generation: dict[str, GenerationBuffer]
    corpus_generation: list[dict[str, Any]]
    resources: frozenset[str] = frozenset()


def note_resource_changed(resource: str) -> None:
    """Record that a registered data resource (``realtime/resources.py``) changed.

    Key-level invalidation only: no ids, values or text. Repeated notes between
    observer ticks collapse into one, and clients refetch over REST.
    """
    if not resource:
        return
    try:
        with _lock:
            _resources.add(str(resource))
    except Exception:  # noqa: BLE001, S110 - notifications must never break a mutation
        pass


def note_corpus_build(summary: dict[str, Any]) -> None:
    """Record the latest operation summary for a corpus build (never raises)."""
    try:
        build_id = str(summary.get("id") or summary.get("build_id") or "")
        if build_id:
            with _lock:
                _corpus_builds[build_id] = summary
    except Exception:  # noqa: BLE001, S110 - notifications must never break a save
        pass


def note_model_activity(build_id: str, calls: list[dict[str, Any]]) -> None:
    """Record safe operational model-call state for a build (no prompts or text)."""
    if not build_id:
        return
    try:
        oldest = min(calls, key=lambda call: call.get("started_token", 0)) if calls else None
        state = {
            "calls_in_flight": len(calls),
            "task": oldest.get("task") if oldest else None,
            "provider": oldest.get("provider") if oldest else None,
            "model": oldest.get("model") if oldest else None,
        }
        with _lock:
            _model_activity[build_id] = state
    except Exception:  # noqa: BLE001, S110 - notifications must never break a model call
        pass


def note_activity(kind: str, summary: dict[str, Any]) -> None:
    """Latest bounded summary of background work that is not a tracked job.

    ``summary`` must already be public (no text, paths, errors or secrets); the
    observer publishes it as-is on ``activity:<kind>``.
    """
    if not kind:
        return
    try:
        with _lock:
            _activity[str(kind)] = dict(summary)
    except Exception:  # noqa: BLE001, S110 - notifications must never break the activity
        pass


def note_record_metadata(
    build_id: str,
    record_id: str,
    kind: str,
    *,
    family: str | None = None,
    state: str | None = None,
    field_ids: list[str] | tuple[str, ...] | None = None,
    precedents_used: int | None = None,
) -> None:
    """Per-record metadata progress: which record/family/fields, never values or evidence."""
    global _metadata_dropped
    if not build_id or not record_id or kind not in METADATA_NOTE_KINDS:
        return
    try:
        note: dict[str, Any] = {"build_id": str(build_id), "record_id": str(record_id), "kind": kind}
        if family:
            note["family"] = str(family)[:80]
        if state in METADATA_FAMILY_STATES:
            note["state"] = state
        if field_ids:
            note["field_ids"] = [str(item)[:120] for item in list(field_ids)[:MAX_NOTE_FIELD_IDS]]
        if precedents_used is not None:
            note["precedents_used"] = max(0, int(precedents_used))
        with _lock:
            if len(_metadata_notes) == _metadata_notes.maxlen:
                _metadata_dropped += 1
            _metadata_notes.append(note)
    except Exception:  # noqa: BLE001, S110 - notifications must never break enrichment
        pass


def note_generation_delta(job_id: str, text: str, *, owner: str | None) -> None:
    """Append streamed Research text for one job; bounded, marks a gap when full."""
    if not job_id or not text:
        return
    try:
        with _lock:
            buffer = _generation.get(job_id)
            if buffer is None:
                buffer = _generation[job_id] = GenerationBuffer(owner=owner)
            room = MAX_PENDING_GENERATION_CHARS - buffer.chars
            if room <= 0:
                buffer.gap = True
                return
            piece = text if len(text) <= room else text[:room]
            buffer.gap = buffer.gap or len(piece) < len(text)
            buffer.chunks.append(piece)
            buffer.chars += len(piece)
    except Exception:  # noqa: BLE001, S110 - notifications must never break generation
        pass


def note_corpus_generation_progress(
    build_id: str,
    call_id: str,
    *,
    seq: int,
    chars: int,
    gap: bool = False,
    final: bool = False,
) -> None:
    """Record text-free live progress for one Corpus Builder model call.

    The raw draft is intentionally NOT placed on the realtime plane. An administrator
    who explicitly opens Model activity reads it through the authenticated REST endpoint.
    """
    if not build_id or not call_id:
        return
    try:
        with _lock:
            _corpus_generation[(str(build_id), str(call_id))] = {
                "build_id": str(build_id),
                "call_id": str(call_id),
                "seq": max(0, int(seq)),
                "chars": max(0, int(chars)),
                "gap": bool(gap),
                "final": bool(final),
            }
    except Exception:  # noqa: BLE001, S110 - notifications must never break generation
        pass

def note_generation_finished(job_id: str, *, owner: str | None) -> None:
    """The draft stream ended (the final answer is then read over REST/GraphQL)."""
    if not job_id:
        return
    try:
        with _lock:
            buffer = _generation.get(job_id)
            if buffer is None:
                buffer = _generation[job_id] = GenerationBuffer(owner=owner)
            buffer.finished = True
    except Exception:  # noqa: BLE001, S110
        pass


def drain() -> Drained:
    """Take every pending note (latest per resource wins for summaries)."""
    global _metadata_dropped
    with _lock:
        drained = Drained(
            builds=dict(_corpus_builds),
            model_activity=dict(_model_activity),
            activity=dict(_activity),
            metadata=list(_metadata_notes),
            metadata_dropped=_metadata_dropped,
            generation=dict(_generation),
            corpus_generation=list(_corpus_generation.values()),
            resources=frozenset(_resources),
        )
        _corpus_builds.clear()
        _model_activity.clear()
        _activity.clear()
        _metadata_notes.clear()
        _metadata_dropped = 0
        _generation.clear()
        _corpus_generation.clear()
        _resources.clear()
    return drained
