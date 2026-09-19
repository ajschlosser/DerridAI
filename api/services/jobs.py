from __future__ import annotations

import json
import logging
import uuid

from clients.db import RedisClient
from clients.llm import LLMClient
from clients.rag import RAGClient
from schemas.schemas import GenericResponse, QueryRequest
from services.nlp import NLPService
from services.query import handle_query

LOG = logging.getLogger(__name__)
JOB_TTL_SECONDS = 60 * 60 * 24


class JobService:
    """Persist compact job state; phases are localization keys rather than UI prose."""

    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client

    async def _write(self, job_id: str, payload: dict) -> None:
        # RedisClient supplies the derridai:job: prefix.
        await self.redis_client.set(
            job_id,
            json.dumps(payload, ensure_ascii=False),
            ex=JOB_TTL_SECONDS,
        )

    async def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        await self._write(
            job_id,
            {"status": "pending", "phase": "queued", "result": None, "error": None},
        )
        return job_id

    async def get_job(self, job_id: str) -> dict | None:
        raw = await self.redis_client.get(job_id)
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            LOG.error("Invalid persisted job JSON for %s", job_id)
            return None
        return payload if isinstance(payload, dict) else None

    async def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        phase: str | None = None,
        result: GenericResponse | None = None,
        error: str | None = None,
    ) -> None:
        payload = await self.get_job(job_id) or {
            "status": "pending",
            "phase": "queued",
            "result": None,
            "error": None,
        }
        if status is not None:
            payload["status"] = status
        if phase is not None:
            payload["phase"] = phase
        if result is not None:
            payload["result"] = result.model_dump(mode="json")
        if error is not None:
            payload["error"] = error
        await self._write(job_id, payload)

    async def update_job_status(self, job_id: str, status: str) -> None:
        # Compatibility for older pipeline utilities.
        await self.update_job(job_id, status="running", phase=status)

    async def run_query_job(
        self,
        job_id: str,
        request: QueryRequest,
        rag_client: RAGClient,
        llm_client: LLMClient,
        nlp_service: NLPService,
    ) -> None:
        try:
            await self.update_job(job_id, status="running", phase="preparing_evidence")
            result = await handle_query(
                request=request,
                rag_client=rag_client,
                llm_client=llm_client,
                nlp_service=nlp_service,
                job_service=self,
                job_id=job_id,
            )
            await self.update_job(
                job_id,
                status="completed",
                phase="completed",
                result=result,
            )
        except Exception as exc:
            LOG.exception("Job failed: %s", job_id)
            await self.update_job(
                job_id,
                status="failed",
                phase="failed",
                error=str(exc),
            )
