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

"""Vector-store (Chroma projection) record reads shared by REST and GraphQL.

Reachable by any account with the ``corpus.read`` capability, including
Researchers, so researcher-text protection is enforced here rather than left
to callers. Hidden/system collections and ``_response_cache`` read as
:class:`NotFound` for non-administrators, matching REST (``store.list_stores``
already excludes them from listings; this closes the same door on direct
name-based reads).
"""
from __future__ import annotations

from typing import Any

from ..config import settings
from ..researcher_view import sanitize_records_payload, summarize_record
from ..services import store
from .access import AccessContext, NotFound

_RESPONSE_CACHE_PUBLIC = "_response_cache"
_HIDDEN_METADATA_KEY = "derridai_hidden_system_collection"


def _guard(access: AccessContext, store_name: str) -> None:
    if access.is_admin:
        return
    if store_name == _RESPONSE_CACHE_PUBLIC:
        raise NotFound(f"Store {store_name!r} was not found.")
    try:
        info = store.get_store(store_name)
    except Exception as exc:
        raise NotFound(f"Store {store_name!r} was not found.") from exc
    metadata = info.get("metadata") if isinstance(info.get("metadata"), dict) else {}
    if bool(metadata.get(_HIDDEN_METADATA_KEY)):
        raise NotFound(f"Store {store_name!r} was not found.")


def records_page(
    access: AccessContext,
    store_name: str,
    *,
    limit: int = 100,
    offset: int = 0,
    work: str | None = None,
    sort_field: str | None = None,
    sort_dir: str = "asc",
    filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    _guard(access, store_name)
    result = store.get_records(
        store_name,
        limit=limit,
        offset=offset,
        work=work,
        sort_field=sort_field,
        sort_dir=sort_dir,
        filters=filters,
        include_updates=False,
    )
    if access.is_admin:
        return result
    return sanitize_records_payload(result, max_chars=settings.researcher_text_max_chars)


def record(
    access: AccessContext,
    store_name: str,
    chroma_id: str,
    *,
    include_updates: bool = False,
) -> dict[str, Any] | None:
    _guard(access, store_name)
    allow_updates = include_updates and access.is_admin
    found = store.get_record(store_name, chroma_id, include_updates=allow_updates)
    if found is None:
        return None
    if access.is_admin:
        return found
    return summarize_record(found, max_chars=settings.researcher_text_max_chars)


def works(access: AccessContext, store_name: str) -> list[dict[str, Any]]:
    _guard(access, store_name)
    return store.work_stats(store_name)
