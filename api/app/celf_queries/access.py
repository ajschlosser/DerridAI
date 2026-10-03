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

"""Explicit authenticated access context for cELF read services."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from ..auth import role_has_capability
from ..reviewer_context import current_reviewer, reviewer_id


class AccessDenied(Exception):
    """The authenticated caller lacks the capability for this read."""


class NotFound(Exception):
    """The object does not exist or is not visible to the caller.

    Callers must not distinguish the two cases: another user's claim is reported
    exactly like a missing one so identifiers cannot be probed.
    """


class InvalidQuery(ValueError):
    """The caller supplied an argument the service cannot accept."""


@dataclass(frozen=True)
class AccessContext:
    """Who is reading, derived only from the server-side session."""

    username: str
    role: str
    user_id: int | None = None

    @classmethod
    def for_user(cls, user: Any) -> AccessContext:
        return cls(
            username=str(user.username),
            role=str(user.role),
            user_id=getattr(user, "id", None),
        )

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def owner(self) -> str | None:
        """Owner filter for owner-scoped rows; administrators see every owner."""
        return None if self.is_admin else self.username

    @property
    def reviewer(self) -> str:
        """Blind-review identity used to hide sealed first answers."""
        return reviewer_id(self.user_id) if self.user_id is not None else ""

    def can(self, capability: str) -> bool:
        return self.is_admin or role_has_capability(self.role, capability)

    def require_admin(self) -> None:
        if not self.is_admin:
            raise AccessDenied("Administrator access required.")

    def require(self, capability: str) -> None:
        if not self.can(capability):
            raise AccessDenied(f"Missing capability: {capability}")


@contextmanager
def reviewer_scope(access: AccessContext) -> Iterator[None]:
    """Present Records as this caller's blind-review identity sees them.

    Services set it explicitly rather than trusting whichever context variable
    the transport happened to leave behind (thread pools, tests, future jobs).
    """
    token = current_reviewer.set(access.reviewer or current_reviewer.get())
    try:
        yield
    finally:
        current_reviewer.reset(token)
