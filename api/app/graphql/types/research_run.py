# Copyright 2026 Aaron John Schlosser, PhD.
"""A Research (RAG) run: its answer, cited evidence, and the claims it produced."""
from __future__ import annotations

from typing import Any

import strawberry
from starlette.concurrency import run_in_threadpool
from strawberry.scalars import JSON
from strawberry.types import Info

from .common import opt_str, str_list
from .research import GeneratedClaim


@strawberry.type(description="A Research (RAG) run: its answer and cited evidence (REST: GET /api/jobs/{id}).")
class ResearchRun:
    run_id: str
    status: str
    stage: str | None
    owner: str | None
    prompt: str | None
    provider: str | None
    model: str | None
    created_at: str | None
    started_at: str | None
    finished_at: str | None
    answer: str | None
    warnings: list[str]
    evidence: JSON = strawberry.field(
        description="Cited evidence entries. Researcher-owned runs already have record text summarized.",
    )

    @classmethod
    def from_job(cls, job: dict[str, Any]) -> ResearchRun:
        result = job.get("result") if isinstance(job.get("result"), dict) else {}
        evidence = result.get("evidence")
        return cls(
            run_id=str(job.get("id") or ""),
            status=str(job.get("status") or ""),
            stage=opt_str(job.get("stage")),
            owner=opt_str(job.get("owner")),
            prompt=opt_str(job.get("prompt")),
            provider=opt_str(job.get("provider")),
            model=opt_str(job.get("model")),
            created_at=opt_str(job.get("created_at")),
            started_at=opt_str(job.get("started_at")),
            finished_at=opt_str(job.get("finished_at")),
            answer=opt_str(result.get("answer")),
            warnings=str_list(result.get("warnings")),
            evidence=JSON(evidence if isinstance(evidence, list) else []),
        )

    @strawberry.field(description="Generated claims produced by this run (administrator-only).")
    async def generated_claims(self, info: Info) -> list[GeneratedClaim]:
        from ...celf_queries import research_runs as run_queries
        from ..permissions import require_admin

        context = require_admin(info)
        rows = await run_in_threadpool(run_queries.generated_claims_for_run, context.access, self.run_id)
        return [GeneratedClaim.from_payload(row) for row in rows]
