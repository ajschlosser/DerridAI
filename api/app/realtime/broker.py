# Copyright 2026 Aaron John Schlosser, PhD.
"""Central in-process event broker.

Publishers (the observer thread) call :meth:`EventBroker.publish` from any
thread. The broker stamps ``event_id``/``revision``, keeps a bounded replay
ring, and fans events out to authorized, subscribed connections through their
bounded queues. It is not persistence: restarting the API forgets every event,
and clients recover from REST.
"""
from __future__ import annotations

import asyncio
import itertools
import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..config import settings
from .coalescing import OutgoingQueue
from .protocol import Audience, Event

logger = logging.getLogger("derridai.realtime")


@dataclass
class Subscriber:
    """One authenticated socket's delivery state (transport-agnostic)."""

    username: str
    role: str
    capabilities: frozenset[str] = frozenset()
    connection_id: str = ""
    user_id: int | None = None
    topics: set[str] = field(default_factory=set)
    queue: OutgoingQueue = field(default_factory=lambda: OutgoingQueue(settings.realtime_max_queue_events))
    loop: asyncio.AbstractEventLoop | None = None
    wake: asyncio.Event | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def may_receive(self, event: Event) -> bool:
        if not self.topics.intersection(event.topics):
            return False
        return audience_allows(event.audience, username=self.username, is_admin=self.is_admin, capabilities=self.capabilities)

    def notify(self) -> None:
        if self.loop is None or self.wake is None:
            return
        try:
            self.loop.call_soon_threadsafe(self.wake.set)
        except RuntimeError:
            # The socket's loop has closed; unregister will follow.
            pass


def audience_allows(audience: Audience, *, username: str, is_admin: bool, capabilities: frozenset[str]) -> bool:
    if is_admin:
        return True
    if audience.admin_only:
        return False
    if audience.capability and audience.capability not in capabilities:
        return False
    return audience.owner is not None and audience.owner == username


class EventBroker:
    def __init__(self, *, replay_events: int | None = None) -> None:
        self._lock = threading.Lock()
        self._event_ids = itertools.count(1)
        self._last_event_id = 0
        self._revisions: dict[tuple[str, str], int] = {}
        self._replay_capacity = max(1, int(replay_events or settings.realtime_replay_events))
        self._replay: deque[Event] = deque(maxlen=self._replay_capacity)
        # Event IDs skipped by ephemeral hints are still covered. This advances
        # only when a replayable event is evicted from the bounded ring.
        self._replay_coverage_start = 0
        self._subscribers: dict[str, Subscriber] = {}
        self.publish_failures = 0

    # -- connections -------------------------------------------------------
    def register(self, subscriber: Subscriber) -> None:
        with self._lock:
            self._subscribers[subscriber.connection_id] = subscriber

    def unregister(self, subscriber: Subscriber) -> None:
        with self._lock:
            self._subscribers.pop(subscriber.connection_id, None)

    def subscribers(self) -> list[Subscriber]:
        with self._lock:
            return list(self._subscribers.values())

    @property
    def last_event_id(self) -> int:
        with self._lock:
            return self._last_event_id

    # -- publishing --------------------------------------------------------
    def publish(
        self,
        event_type: str,
        *,
        resource_type: str,
        resource_id: str,
        payload: dict[str, Any],
        topics: tuple[str, ...],
        audience: Audience,
    ) -> Event | None:
        """Stamp and deliver one event. Never raises into the publisher."""
        try:
            with self._lock:
                key = (resource_type, resource_id)
                revision = self._revisions.get(key, 0) + 1
                self._revisions[key] = revision
                event_id = next(self._event_ids)
                self._last_event_id = event_id
                event = Event(
                    type=event_type,
                    event_id=event_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    revision=revision,
                    timestamp=datetime.now(UTC).isoformat(),
                    payload=payload,
                    topics=topics,
                    audience=audience,
                )
                if not event.ephemeral:
                    # Ephemeral hints are never replayed: after a reconnect the
                    # client reconciles from REST/GraphQL instead.
                    if len(self._replay) == self._replay_capacity:
                        self._replay_coverage_start = max(
                            self._replay_coverage_start,
                            self._replay[0].event_id + 1,
                        )
                    self._replay.append(event)
                targets = [sub for sub in self._subscribers.values() if sub.may_receive(event)]
            for subscriber in targets:
                subscriber.queue.put(event)
                subscriber.notify()
            return event
        except Exception:
            self.publish_failures += 1
            logger.exception("Realtime publish failed for %s %s", resource_type, event_type)
            return None

    def forget_resource(self, resource_type: str, resource_id: str) -> None:
        with self._lock:
            self._revisions.pop((resource_type, resource_id), None)

    # -- subscriptions and replay -------------------------------------------
    def add_topics(self, subscriber: Subscriber, topics: set[str]) -> None:
        with self._lock:
            subscriber.topics.update(topics)

    def _replay_locked(self, subscriber: Subscriber, last_event_id: int) -> list[Event] | None:
        if last_event_id >= self._last_event_id:
            return []
        if last_event_id + 1 < self._replay_coverage_start:
            return None
        return [event for event in self._replay if event.event_id > last_event_id and subscriber.may_receive(event)]

    def replay_since(self, subscriber: Subscriber, last_event_id: int) -> list[Event] | None:
        """Events after ``last_event_id`` visible to ``subscriber``; ``None`` if the gap is not covered."""
        with self._lock:
            return self._replay_locked(subscriber, last_event_id)

    def resume(self, subscriber: Subscriber, last_event_id: int) -> bool:
        """Re-queue everything after ``last_event_id`` in ``event_id`` order.

        Runs under the broker lock, so no live event can be stamped between the
        replay and the queue rebuild; pending items are replaced because the
        replay already contains every visible event newer than the client's
        position. Returns ``False`` when the ring no longer covers the gap.
        """
        with self._lock:
            replay = self._replay_locked(subscriber, last_event_id)
            if replay is None:
                return False
            subscriber.queue.clear()
            for event in replay:
                subscriber.queue.put(event)
        subscriber.notify()
        return True


broker = EventBroker()
