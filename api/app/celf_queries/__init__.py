# Copyright 2026 Aaron John Schlosser, PhD.
"""Transport-independent cELF read services.

REST routers and GraphQL resolvers both call these functions so authorization,
owner scoping, blind-review presentation, support-binding resolution, and cELF
object mapping have one implementation. Nothing here imports FastAPI request
objects, Strawberry, or WebSocket code; callers pass an explicit
:class:`~app.celf_queries.access.AccessContext`.
"""
