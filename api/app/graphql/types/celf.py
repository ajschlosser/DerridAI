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

"""Normative cELF type registry (the model, not instances)."""
from __future__ import annotations

from typing import Any

import strawberry


@strawberry.type(description="A normative cELF object type.")
class CelfObjectType:
    type: str
    profile: str
    persistence: str
    label: str
    normative: bool

    @classmethod
    def from_payload(cls, item: dict[str, Any]) -> CelfObjectType:
        return cls(
            type=str(item["type"]),
            profile=str(item["profile"]),
            persistence=str(item["persistence"]),
            label=str(item["label"]),
            normative=bool(item.get("normative")),
        )


@strawberry.type(description="A normative, walkable relationship between cELF object types.")
class CelfRelationship:
    id: str
    source_type: str
    target_type: str
    relation: str
    inverse_relation: str
    source_cardinality: str
    target_cardinality: str
    profile: str
    normative: bool

    @classmethod
    def from_payload(cls, item: dict[str, Any]) -> CelfRelationship:
        return cls(
            id=str(item["id"]),
            source_type=str(item["source_type"]),
            target_type=str(item["target_type"]),
            relation=str(item["relation"]),
            inverse_relation=str(item["inverse_relation"]),
            source_cardinality=str(item["source_cardinality"]),
            target_cardinality=str(item["target_cardinality"]),
            profile=str(item["profile"]),
            normative=bool(item.get("normative")),
        )


@strawberry.type(description="The normative cELF 1.0 type graph (same payload as GET /api/derridai/model).")
class CelfModel:
    specification_version: str
    nodes: list[CelfObjectType]
    edges: list[CelfRelationship]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> CelfModel:
        return cls(
            specification_version=str(payload["specification_version"]),
            nodes=[CelfObjectType.from_payload(item) for item in payload["nodes"]],
            edges=[CelfRelationship.from_payload(item) for item in payload["edges"]],
        )
