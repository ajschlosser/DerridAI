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

"""POST /api/graphql. No GET queries, uploads, subscriptions or (by default) IDE."""
from __future__ import annotations

from strawberry.fastapi import GraphQLRouter

from ..config import settings
from .context import get_context
from .schema import schema

graphql_router: GraphQLRouter = GraphQLRouter(
    schema,
    path="/api/graphql",
    graphql_ide="graphiql" if settings.graphql_ide_enabled else None,
    allow_queries_via_get=False,
    multipart_uploads_enabled=False,
    subscription_protocols=(),
    context_getter=get_context,
    tags=["graphql"],
)
