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
