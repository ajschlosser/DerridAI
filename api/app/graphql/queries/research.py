# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import strawberry
from starlette.concurrency import run_in_threadpool
from strawberry.types import Info

from ...celf_queries import claims as claim_queries
from ..errors import translate
from ..permissions import classify, require_admin
from ..types.research import GeneratedClaim

# Mirrors REST: /api/derridai/claims/* is administrator-only today. The service
# is owner-scoped regardless, so opening this to a capability later is a policy
# change, not a new query path.
classify("generated_claim", "admin")


@strawberry.type
class ResearchQueries:
    @strawberry.field(description="One owner-scoped generated claim.")
    async def generated_claim(self, info: Info, claim_id: str) -> GeneratedClaim:
        context = require_admin(info)
        try:
            payload = await run_in_threadpool(claim_queries.get_generated_claim, context.access, claim_id)
        except Exception as exc:
            raise translate(exc) from exc
        return GeneratedClaim.from_payload(payload)
