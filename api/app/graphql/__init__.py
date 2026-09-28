# Copyright 2026 Aaron John Schlosser, PhD.
"""Read-only, cELF-aware GraphQL query façade (see docs/GRAPHQL.md).

GraphQL composes cELF/provenance reads. It has no Mutation or Subscription
root: commands stay on REST and live operational events use the WebSocket
realtime plane. Resolvers stay thin and call :mod:`app.celf_queries`.
"""
