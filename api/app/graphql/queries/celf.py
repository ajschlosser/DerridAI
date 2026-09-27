# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import strawberry
from strawberry.types import Info

from ...derridai_model import normative_model
from ..permissions import classify, require_authenticated
from ..types.celf import CelfModel

classify("celf_model", "authenticated")


@strawberry.type
class CelfQueries:
    @strawberry.field(description="The normative cELF type graph (REST: GET /api/derridai/model).")
    def celf_model(self, info: Info) -> CelfModel:
        require_authenticated(info)
        return CelfModel.from_payload(normative_model())
