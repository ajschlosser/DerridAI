# Copyright 2026 Aaron John Schlosser, PhD.
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
