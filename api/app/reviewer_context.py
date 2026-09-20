# Copyright 2026 Aaron John Schlosser, PhD.
"""Who is making the request, for stamping human decisions in the enrichment ledger.

The id is `user-<number>`, not a name, so an exported ledger can be analysed and shared without
naming reviewers. A context variable carries it from the authentication middleware to wherever a
decision is logged, without threading a parameter through every review function. Background
model work has no reviewer, so its events carry none.
"""

from __future__ import annotations

from contextvars import ContextVar

current_reviewer: ContextVar[str] = ContextVar("current_reviewer", default="")


def reviewer_id(user_id: int) -> str:
    return f"user-{user_id}"
