# Copyright 2026 Aaron John Schlosser, PhD.
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
