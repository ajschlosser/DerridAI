# Copyright 2026 Aaron John Schlosser, PhD.
"""Closed registry of data resources that clients can follow for invalidation.

``resource.changed`` on ``data:<key>`` says only that the REST/GraphQL read for
``<key>`` is stale; it never carries values. The frontend maps each key to the
query keys it refetches (``web/src/realtime/resourceKeys.ts``); a contract test
keeps the two lists identical. Register a key here before any domain code notes
it with ``operation_events.note_resource_changed``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .broker import Subscriber
from .protocol import Audience


@dataclass(frozen=True)
class DataResource:
    audience: Audience = field(default_factory=lambda: Audience(admin_only=True))

    def allows(self, subscriber: Subscriber) -> bool:
        # Must match who may read the resource's REST route; widen with the route.
        return subscriber.is_admin


DATA_RESOURCES: dict[str, DataResource] = {
    "users": DataResource(),
    "roles": DataResource(),
    "pipelines": DataResource(),
    "pipeline_runs": DataResource(),
}
