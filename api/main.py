from __future__ import annotations

import os
import traceback
from contextlib import asynccontextmanager

os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse

from clients.db import RedisClient
from clients.llm import LLMClient
from clients.rag import RAGClient
from logging_config import configure_logging
from schemas.schemas import AppCapabilities, JobStartResponse, JobStatusResponse, QueryRequest
from services.jobs import JobService
from services.nlp import NLPService
from utils.request_id import request_id

configure_logging()
import logging

LOG = logging.getLogger(__name__)

CURRENT_VERSION = "0.58.6"
LEGACY_VERSION = "0.1.0"
RELEASE_NAME = "Risky Rabbit"
DEBUG = os.getenv("DERRIDAI_DEBUG", "0").strip().lower() in {"1", "true", "yes"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag_client = RAGClient()
    app.state.llm_client = LLMClient()
    app.state.redis_client = RedisClient()
    app.state.job_service = JobService(app.state.redis_client)
    app.state.nlp_service = NLPService()
    LOG.info("Initialized DerridAI %s - %s", CURRENT_VERSION, RELEASE_NAME)
    yield
    await app.state.redis_client.redis.aclose()


app = FastAPI(
    lifespan=lifespan,
    title="DerridAI Research API",
    description="Evidence-grounded Derrida research with structured provenance and hybrid retrieval.",
    version=CURRENT_VERSION,
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "api_version": CURRENT_VERSION, "release_name": RELEASE_NAME}


@app.get(f"/v{CURRENT_VERSION}/capabilities", response_model=AppCapabilities)
async def capabilities():
    return AppCapabilities(api_version=CURRENT_VERSION)


async def _start_query(request: QueryRequest, background_tasks: BackgroundTasks):
    job_id = await app.state.job_service.create_job()
    background_tasks.add_task(
        app.state.job_service.run_query_job,
        job_id,
        request,
        app.state.rag_client,
        app.state.llm_client,
        app.state.nlp_service,
    )
    return JobStartResponse(job_id=job_id)


@app.post(f"/v{CURRENT_VERSION}/query", response_model=JobStartResponse)
@app.post(f"/v{LEGACY_VERSION}/query", response_model=JobStartResponse, include_in_schema=False)
async def process_query(request: QueryRequest, background_tasks: BackgroundTasks):
    return await _start_query(request, background_tasks)


async def _query_result(job_id: str):
    job = await app.state.job_service.get_job(job_id)
    if job is None:
        raise HTTPException(404, detail={"code": "job_not_found", "job_id": job_id})
    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "pending"),
        phase=job.get("phase"),
        result=job.get("result"),
        error=job.get("error"),
    )


@app.get(f"/v{CURRENT_VERSION}/query/{{job_id}}", response_model=JobStatusResponse)
@app.get(
    f"/v{LEGACY_VERSION}/query/{{job_id}}",
    response_model=JobStatusResponse,
    include_in_schema=False,
)
async def get_query_result(job_id: str):
    return await _query_result(job_id)


def _request_id() -> str | None:
    try:
        return request_id.get()
    except LookupError:
        return None


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "request_validation_error",
            "request_id": _request_id(),
            "detail": exc.errors(),
        },
    )


@app.exception_handler(ResponseValidationError)
async def response_validation_handler(request: Request, exc: ResponseValidationError):
    LOG.exception("Response validation failed for %s", request.url)
    payload = {"error": "response_validation_error", "request_id": _request_id()}
    if DEBUG:
        payload["detail"] = exc.errors()
    return JSONResponse(status_code=500, content=payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    LOG.exception("Unhandled exception for %s", request.url)
    payload = {"error": "internal_server_error", "request_id": _request_id()}
    if DEBUG:
        payload["detail"] = str(exc)
        payload["traceback"] = traceback.format_exc()
    return JSONResponse(status_code=500, content=payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        reload_excludes=["*.pyc", "data/**", "__pycache__/**", "*.log"],
    )
