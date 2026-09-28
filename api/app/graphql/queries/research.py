# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import strawberry
from starlette.concurrency import run_in_threadpool
from strawberry.types import Info

from ...celf_queries import claims as claim_queries
from ...celf_queries import research_runs as run_queries
from ..errors import translate
from ..permissions import classify, require_admin, require_authenticated
from ..types.research import GeneratedClaim
from ..types.research_run import ResearchRun

# Mirrors REST: /api/derridai/claims/* is administrator-only today. The service
# is owner-scoped regardless, so opening this to a capability later is a policy
# change, not a new query path.
classify("generated_claim", "admin")
# Owner-scoped like REST GET /api/jobs/{id}: administrators, or the researcher
# who owns the run; anyone else's run reads as not found.
classify("research_run", "owner_or_admin")


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

    @strawberry.field(description="One Research run with its answer and cited evidence.")
    async def research_run(self, info: Info, run_id: str) -> ResearchRun:
        context = require_authenticated(info)
        try:
            job = await run_in_threadpool(run_queries.research_run, context.access, run_id)
        except Exception as exc:
            raise translate(exc) from exc
        return ResearchRun.from_job(job)
