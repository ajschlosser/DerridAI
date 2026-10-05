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

"""Closed registry of data resources that clients can follow for invalidation.

``resource.changed`` on ``data:<key>`` says only that the REST/GraphQL read for
``<key>`` is stale; it never carries values. The frontend maps each key to the
query keys it refetches (``web/src/realtime/resourceKeys.ts``); a contract test
keeps the two lists identical. Register a key here before any domain code notes
it with ``operation_events.note_resource_changed``.
"""
from __future__ import annotations

from dataclasses import dataclass

from .broker import Subscriber
from .protocol import Audience


@dataclass(frozen=True)
class DataResource:
    """One followable resource. Administrators always may; ``capability`` also admits holders.

    Set ``capability`` to the capability the resource's REST read route requires
    (``route_policy.py``) for non-administrators, and never otherwise: the key carries no
    values, but who may learn that something changed must match who may read it.
    """

    capability: str | None = None

    @property
    def audience(self) -> Audience:
        if self.capability:
            return Audience(admin_only=False, capability=self.capability, capability_only=True)
        return Audience(admin_only=True)

    def allows(self, subscriber: Subscriber) -> bool:
        if subscriber.is_admin:
            return True
        return bool(self.capability) and self.capability in subscriber.capabilities



def follows_any_resource(subscriber: Subscriber) -> bool:
    """Whether the subscriber may follow at least one data resource."""
    return any(spec.allows(subscriber) for spec in DATA_RESOURCES.values())


DATA_RESOURCES: dict[str, DataResource] = {
    "users": DataResource(),
    "roles": DataResource(),
    "pipelines": DataResource(),
    "pipeline_runs": DataResource(),
    "pipeline_benchmarks": DataResource(),
    # GET /api/stores and its record reads require corpus.read (route_policy.py).
    "vector_collections": DataResource(capability="corpus.read"),
    "metadata_exemplars": DataResource(),
    "response_library": DataResource(),
    # GET /api/research/threads requires rag.run (route_policy.py); the key carries no ids or text.
    "research_threads": DataResource(capability="rag.run"),
    "corpus_records": DataResource(capability="corpus.read"),
}
