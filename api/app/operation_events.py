# Copyright 2026 Aaron John Schlosser, PhD.
"""Transport-neutral change notes from long-running domain work.

Domain code (the corpus repository, the model-call tracker) records *that*
something changed here, cheaply and without knowing about sockets. The
realtime observer drains these notes at a bounded rate and turns them into
public events. Nothing here is canonical state: losing a note only delays a
client's refresh, and every client can resynchronize from REST.
"""
from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()
_corpus_builds: dict[str, dict[str, Any]] = {}
_model_activity: dict[str, dict[str, Any]] = {}


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


def drain() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Take every pending note (latest per build wins)."""
    with _lock:
        builds = dict(_corpus_builds)
        activity = dict(_model_activity)
        _corpus_builds.clear()
        _model_activity.clear()
    return builds, activity
