# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""Backend-neutral persistence failure vocabulary.

Domain/orchestration code must not branch on adapter-specific exceptions.
Adapters translate their native transient failures into these exceptions so
callers can apply retry, interruption, and backpressure policies without
knowing whether storage is SQLite, PostgreSQL, or another implementation.
"""

from __future__ import annotations


class PersistenceError(RuntimeError):
    """Base class for durable-storage failures visible above an adapter."""


class TransientPersistenceError(PersistenceError):
    """A retryable storage failure such as temporary write contention."""


class PersistenceBusyError(TransientPersistenceError):
    """The storage backend cannot currently admit the requested write."""
