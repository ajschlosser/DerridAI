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

"""Resolver-level authorization.

``POST /api/graphql`` is a single HTTP route, so route policy alone cannot
authorize individual reads. Every root field declares one of these checks;
:func:`app.graphql.schema.assert_root_fields_classified` fails startup and
tests if a root field is added without a classification (default deny).
"""
from __future__ import annotations

from typing import Any

from strawberry.types import Info

from .context import GraphQLContext
from .errors import Forbidden

# Root field name -> the check it enforces. Adding a root field without an
# entry here is rejected by the schema self-check.
ROOT_FIELD_POLICY: dict[str, str] = {}


def classify(field_name: str, policy: str) -> None:
    ROOT_FIELD_POLICY[field_name] = policy


def context_of(info: Info[Any, Any]) -> GraphQLContext:
    return info.context


def require_authenticated(info: Info[Any, Any]) -> GraphQLContext:
    context = context_of(info)
    if context.access is None:
        raise Forbidden("Authentication required.")
    return context


def require_admin(info: Info[Any, Any]) -> GraphQLContext:
    context = require_authenticated(info)
    if not context.access.is_admin:
        raise Forbidden("Administrator access required.")
    return context


def require_capability(info: Info[Any, Any], capability: str) -> GraphQLContext:
    context = require_authenticated(info)
    if not context.access.can(capability):
        raise Forbidden(f"Missing capability: {capability}")
    return context


def require_owner_or_admin(info: Info[Any, Any], owner: str | None) -> GraphQLContext:
    """Owner-scoped rows: administrators see all; others only their own or unowned rows."""
    context = require_authenticated(info)
    if context.access.is_admin or owner in (None, "", context.access.username):
        return context
    raise Forbidden("Not permitted.")
