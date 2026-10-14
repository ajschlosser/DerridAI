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
