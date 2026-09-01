import uuid
import json
import os
from contextvars import ContextVar
import logging
from schemas.schemas import QueryRequest, GenericResponse
from services.nlp import NLPService
from clients.llm import LLMClient
from clients.rag import RAGClient
from services.query import handle_query
from utils.extract_query_metadata import QueryMetadataExtractor
from utils.request_id import request_id

from redis.asyncio import Redis

LOG = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
JOB_KEY_PREFIX = "derridai:job:"
JOB_TTL_SECONDS = 60 * 60 * 24

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)


jobs: dict[str, dict] = {}

def _job_key(job_id: str) -> str:
    return f"{JOB_KEY_PREFIX}{job_id}"


async def create_job() -> str:
    job_id = str(uuid.uuid4())
    await redis_client.set(
        _job_key(job_id),
        json.dumps({"status": "pending", "result": None}),
        ex=JOB_TTL_SECONDS,
    )
    return job_id


async def get_job(job_id: str) -> dict | None:
    value = await redis_client.get(_job_key(job_id))
    return json.loads(value) if value is not None else None


async def set_job_result(job_id: str, result: GenericResponse) -> None:
    await redis_client.set(
        _job_key(job_id),
        json.dumps(
            {
                "status": "done",
                "result": result.model_dump(mode="json"),
            }
        ),
        ex=JOB_TTL_SECONDS,
    )
    
async def run_query_job(
    job_id: str,
    request: QueryRequest,
    rag_client: RAGClient,
    llm_client: LLMClient,
    nlp_service: NLPService,
    metadata_extractor: QueryMetadataExtractor
) -> None:
    request_id_token = request_id.set(job_id)
    try:
        result = await handle_query(
            request,
            rag_client,
            llm_client,
            nlp_service,
            metadata_extractor
        )
        LOG.info("Job finished: %s", job_id)
        await set_job_result(job_id, result)
    finally:
        request_id.reset(request_id_token)