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

"""Request-scoped DataLoaders for genuinely batchable cELF relationships.

A new :class:`RequestLoaders` is built for every GraphQL request with that
request's :class:`AccessContext` baked in, so cached objects can never cross
requests or users. There is deliberately no module-level loader or cache.
"""
from __future__ import annotations

from typing import Any

from starlette.concurrency import run_in_threadpool
from strawberry.dataloader import DataLoader

from ..celf_queries import claims as claim_queries
from ..celf_queries import corpus_records as corpus_queries
from ..celf_queries.access import AccessContext


class RequestLoaders:
    def __init__(self, access: AccessContext) -> None:
        self.access = access
        self.batch_calls: dict[str, int] = {"claims": 0, "support_bindings": 0, "corpus_build_records": 0}
        self.claims: DataLoader[str, dict[str, Any] | None] = DataLoader(load_fn=self._load_claims, max_batch_size=500)
        self.support_bindings_by_claim: DataLoader[str, list[dict[str, Any]]] = DataLoader(
            load_fn=self._load_support_bindings,
            max_batch_size=500,
        )
        # A build's stored Records, loaded once per request however many fields
        # (queue page, one Record, facets, rows) read them. Never presented here.
        self.corpus_build_records: DataLoader[str, list[dict[str, Any]] | None] = DataLoader(
            load_fn=self._load_corpus_build_records,
            max_batch_size=8,
        )

    async def _load_claims(self, keys: list[str]) -> list[dict[str, Any] | None]:
        self.batch_calls["claims"] += 1
        return await run_in_threadpool(claim_queries.generated_claims_by_ids, self.access, list(keys))

    async def _load_support_bindings(self, keys: list[str]) -> list[list[dict[str, Any]]]:
        self.batch_calls["support_bindings"] += 1
        return await run_in_threadpool(claim_queries.support_bindings_by_claim_ids, self.access, list(keys))

    async def _load_corpus_build_records(self, keys: list[str]) -> list[list[dict[str, Any]] | None]:
        self.batch_calls["corpus_build_records"] += 1
        return await run_in_threadpool(corpus_queries.load_build_records, self.access, list(keys))
