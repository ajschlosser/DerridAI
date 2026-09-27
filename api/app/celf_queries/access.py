# Copyright 2026 Aaron John Schlosser, PhD.
"""Explicit authenticated access context for cELF read services."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..auth import role_has_capability
from ..reviewer_context import reviewer_id


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
