# Copyright 2026 Aaron John Schlosser, PhD.
"""Bounded per-connection outgoing queue with coalescing and overflow detection."""
from __future__ import annotations

import threading
from collections import deque

from .protocol import Event


class OutgoingQueue:
    """Thread-safe bounded queue.

    * A newer coalescable event replaces its pending predecessor for the same
      resource and type. The replacement is appended at the tail, never swapped
      in place, so delivery order still follows ``event_id``.
    * When full, the oldest droppable event (coalescable progress or an
      ephemeral hint such as a generation delta) is dropped first.
    * If nothing can be dropped the queue overflows: pending events are
      discarded and the consumer must tell the client to resynchronize from
      REST. Terminal and warning events are therefore never silently lost.
    """

    def __init__(self, max_events: int) -> None:
        self.max_events = max(4, int(max_events))
        self._items: deque[Event] = deque()
        self._lock = threading.Lock()
        self.overflowed = False
        self.coalesced = 0
        self.dropped = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    def put(self, event: Event) -> None:
        with self._lock:
            if event.coalescable:
                key = event.coalesce_key
                for index, pending in enumerate(self._items):
                    if pending.coalesce_key == key:
                        del self._items[index]
                        self.coalesced += 1
                        break
            if len(self._items) >= self.max_events:
                for index, pending in enumerate(self._items):
                    if pending.droppable:
                        del self._items[index]
                        self.dropped += 1
                        break
                else:
                    self.dropped += len(self._items)
                    self._items.clear()
                    self.overflowed = True
            self._items.append(event)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self.overflowed = False

    def drain(self) -> tuple[list[Event], bool]:
        """Take every pending event plus whether an overflow happened since last drain."""
        with self._lock:
            items = list(self._items)
            self._items.clear()
            overflowed = self.overflowed
            self.overflowed = False
        return items, overflowed
