# Copyright 2026 Aaron John Schlosser, PhD.
"""Authenticated WebSocket realtime operations plane (see docs/REALTIME.md).

The socket delivers notifications about work that is durably tracked
elsewhere. It never creates, mutates, or stores canonical state; commands stay
on REST, and every client can resynchronize from REST/GraphQL snapshots.
"""
