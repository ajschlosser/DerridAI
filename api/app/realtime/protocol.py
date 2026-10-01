# Copyright 2026 Aaron John Schlosser, PhD.
"""Realtime wire protocol: envelope, event taxonomy, client messages, close codes."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

PROTOCOL_VERSION = 1

CLOSE_NORMAL = 1000
CLOSE_INTERNAL = 1011
CLOSE_MALFORMED = 4400
CLOSE_UNAUTHENTICATED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_NOT_FOUND = 4404
CLOSE_POLICY = 4408

# Connection/control frames are not resource events and are never replayed.
CONTROL_EVENT_TYPES = frozenset({
    "connection.ready",
    "connection.resync_required",
    "connection.heartbeat",
    "subscription.updated",
    "pong",
    "auth.permissions_changed",
})

RESOURCE_EVENT_TYPES = frozenset({
    "job.snapshot",
    "job.created",
    "job.queued",
    "job.started",
    "job.stage_changed",
    "job.progress",
    "job.warning",
    "job.needs_attention",
    "job.cancelling",
    "job.cancelled",
    "job.completed",
    "job.failed",
    "job.removed",
    "llm.started",
    "llm.progress",
    "llm.completed",
    "corpus.build_changed",
    "corpus.stage_changed",
    "corpus.progress",
    "corpus.metadata_progress",
    "corpus.review_queue_changed",
    "corpus.record_started",
    "corpus.field_checked",
    "corpus.record_completed",
    "corpus.llm_progress",
    "llm.token",
    "activity.changed",
    "resource.changed",
})

SERVER_EVENT_TYPES = CONTROL_EVENT_TYPES | RESOURCE_EVENT_TYPES

# Superseded instances of these may be dropped under backpressure: the newest
# one carries the complete current value. Stage, warning and terminal events
# are never coalesced away.
COALESCABLE_EVENT_TYPES = frozenset({
    "job.progress",
    "llm.progress",
    "corpus.progress",
    "corpus.metadata_progress",
    "corpus.review_queue_changed",
    "activity.changed",
    "resource.changed",
})

# Hints that are never replayed after a reconnect and are the first to go under
# backpressure. Each is a discrete fact rather than a latest-value snapshot, so
# it cannot be coalesced; clients treat a gap as "reconcile from REST/GraphQL"
# (generation: wait for the final answer; per-record progress: re-read counts).
EPHEMERAL_EVENT_TYPES = frozenset({
    "llm.token",
    "corpus.record_started",
    "corpus.field_checked",
    "corpus.record_completed",
    "corpus.llm_progress",
})

CLIENT_MESSAGE_TYPES = frozenset({"subscribe", "unsubscribe", "resync", "ping"})

MAX_TOPICS_PER_CONNECTION = 64
_TOPIC_ID = r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
_TOPIC_RE = re.compile(rf"^(jobs|corpus-builds|job:{_TOPIC_ID}|corpus-build:{_TOPIC_ID}|activity:{_TOPIC_ID}|data:{_TOPIC_ID})$")


class ProtocolError(Exception):
    def __init__(self, code: int, reason: str) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason


@dataclass(frozen=True)
class Audience:
    """Who may receive an event. Checked at delivery, in addition to topic authorization."""

    owner: str | None = None
    admin_only: bool = True
    capability: str | None = None


@dataclass(frozen=True)
class Event:
    type: str
    event_id: int
    resource_type: str
    resource_id: str
    revision: int
    timestamp: str
    payload: dict[str, Any]
    topics: tuple[str, ...]
    audience: Audience = field(default_factory=Audience)

    @property
    def coalescable(self) -> bool:
        return self.type in COALESCABLE_EVENT_TYPES

    @property
    def ephemeral(self) -> bool:
        return self.type in EPHEMERAL_EVENT_TYPES

    @property
    def droppable(self) -> bool:
        """Safe to discard under backpressure without forcing a resync."""
        return self.coalescable or self.ephemeral

    @property
    def coalesce_key(self) -> tuple[str, str, str]:
        return (self.type, self.resource_type, self.resource_id)

    def envelope(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "event_id": self.event_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "revision": self.revision,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class ClientMessage:
    type: str
    topics: tuple[str, ...] = ()
    last_event_id: int | None = None


def valid_topic(topic: str) -> bool:
    return bool(_TOPIC_RE.match(topic))


def parse_client_message(raw: str | bytes, *, max_bytes: int) -> ClientMessage:
    """Validate one client frame; raise :class:`ProtocolError` with a close code."""
    size = len(raw.encode("utf-8") if isinstance(raw, str) else raw)
    if size > max_bytes:
        raise ProtocolError(CLOSE_POLICY, "message too large")
    try:
        data = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ProtocolError(CLOSE_MALFORMED, "malformed JSON") from exc
    if not isinstance(data, dict):
        raise ProtocolError(CLOSE_MALFORMED, "message must be an object")
    message_type = data.get("type")
    if message_type not in CLIENT_MESSAGE_TYPES:
        raise ProtocolError(CLOSE_MALFORMED, "unknown message type")
    topics: tuple[str, ...] = ()
    if message_type in {"subscribe", "unsubscribe"}:
        raw_topics = data.get("topics")
        if not isinstance(raw_topics, list) or not all(isinstance(item, str) for item in raw_topics):
            raise ProtocolError(CLOSE_MALFORMED, "topics must be a list of strings")
        if len(raw_topics) > MAX_TOPICS_PER_CONNECTION:
            raise ProtocolError(CLOSE_POLICY, "too many topics")
        topics = tuple(dict.fromkeys(raw_topics))
    last_event_id = data.get("last_event_id")
    if last_event_id is not None and (isinstance(last_event_id, bool) or not isinstance(last_event_id, int) or last_event_id < 0):
        raise ProtocolError(CLOSE_MALFORMED, "last_event_id must be a non-negative integer")
    return ClientMessage(type=str(message_type), topics=topics, last_event_id=last_event_id)
