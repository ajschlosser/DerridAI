# Copyright 2026 Aaron John Schlosser, PhD.
"""Public GraphQL errors; every other exception is masked."""
from __future__ import annotations

from graphql.error import GraphQLError

from ..celf_queries.access import AccessDenied, InvalidQuery, NotFound


class PublicError(Exception):
    """An error whose message is safe to show to the caller.

    ``code`` is surfaced as ``extensions.code`` so clients branch on a stable
    value instead of parsing (localizable) messages.
    """

    code = "BAD_REQUEST"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.extensions = {"code": self.code}


class Forbidden(PublicError):
    code = "FORBIDDEN"


class NotFoundError(PublicError):
    code = "NOT_FOUND"


class BadRequest(PublicError):
    code = "BAD_REQUEST"


class Unavailable(PublicError):
    code = "UNAVAILABLE"


PUBLIC_EXCEPTIONS: tuple[type[Exception], ...] = (PublicError, AccessDenied, NotFound, InvalidQuery)


def translate(exc: Exception) -> Exception:
    """Map a domain exception onto the public error it should surface as."""
    if isinstance(exc, PublicError):
        return exc
    if isinstance(exc, AccessDenied):
        return Forbidden(str(exc) or "Forbidden")
    if isinstance(exc, NotFound):
        return NotFoundError(str(exc) or "Not found")
    if isinstance(exc, InvalidQuery):
        return BadRequest(str(exc) or "Invalid query")
    return exc


def should_mask_error(error: GraphQLError) -> bool:
    """Mask internal exceptions; keep validation and deliberate public errors."""
    original = getattr(error, "original_error", None)
    if original is None:
        # Parse/validation errors (unknown fields, depth limits) describe the
        # caller's own document and are safe to return.
        return False
    return not isinstance(original, PUBLIC_EXCEPTIONS)
