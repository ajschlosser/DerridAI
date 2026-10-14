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

"""Public GraphQL errors; every other exception is masked."""
from __future__ import annotations

from graphql.error import GraphQLError

from ..celf_queries.access import AccessDenied, InvalidQuery, NotFound
from ..corpus_queue_projection import QueueCursorError, StaleQueueCursor


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


class StaleCursor(PublicError):
    code = "STALE_QUEUE_CURSOR"


PUBLIC_EXCEPTIONS: tuple[type[Exception], ...] = (PublicError, AccessDenied, NotFound, InvalidQuery)


def translate(exc: Exception) -> Exception:
    """Map a domain exception onto the public error it should surface as."""
    if isinstance(exc, PublicError):
        return exc
    if isinstance(exc, StaleQueueCursor):
        return StaleCursor(str(exc))
    if isinstance(exc, QueueCursorError):
        return BadRequest(str(exc))
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
