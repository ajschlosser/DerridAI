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

"""Per-request GraphQL context: never shared across requests or users."""
from __future__ import annotations

from fastapi import Request
from strawberry.fastapi import BaseContext

from ..celf_queries.access import AccessContext
from ..http_auth import request_user
from .loaders import RequestLoaders


class GraphQLContext(BaseContext):
    def __init__(self, access: AccessContext, loaders: RequestLoaders) -> None:
        super().__init__()
        self.access = access
        self.loaders = loaders


async def get_context(request: Request) -> GraphQLContext:
    """Build the context from the session the HTTP middleware authenticated."""
    access = AccessContext.for_user(request_user(request))
    return GraphQLContext(access=access, loaders=RequestLoaders(access))
