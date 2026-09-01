import os
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
from contextlib import asynccontextmanager
from time import time
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import ResponseValidationError
from clients.llm import LLMClient   
from services.nlp import NLPService
from clients.rag import RAGClient
from schemas.schemas import QueryRequest, JobStatusResponse, JobStartResponse
from services.jobs import redis_client, create_job, get_job, run_query_job
from utils.extract_query_metadata import QueryMetadataExtractor
from logging_config import configure_logging
configure_logging()
import logging
LOG = logging.getLogger(__name__)
import traceback

DEBUG = True
CURRENT_VERSION = "0.1.0"
LOG.debug(f"Starting DerridAI API version {CURRENT_VERSION}...")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag_client = RAGClient()
    app.state.llm_client = LLMClient()
    app.state.nlp_service = NLPService()
    app.state.metadata_extractor = QueryMetadataExtractor(app.state.nlp_service)
    LOG.info("Initialized application state with RAG client, LLM client, and NLP service.")
    yield
    await redis_client.aclose()

# Initialize the FastAPI application instance
app = FastAPI(
    lifespan=lifespan,
    title="DerridAI Query API",
    description="DerridAI Query API",
    version=CURRENT_VERSION
)

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "api_version": CURRENT_VERSION}

@app.post(f"/v{CURRENT_VERSION}/query", response_model=JobStartResponse)
async def process_query(request: QueryRequest, background_tasks: BackgroundTasks):
    job_id = await create_job()
    LOG.debug(f"Received query request: {request.model_dump_json(indent=2)}")
    background_tasks.add_task(
        run_query_job,
        job_id,
        request,
        app.state.rag_client,
        app.state.llm_client,
        app.state.nlp_service,
        app.state.metadata_extractor,
    )
    return JobStartResponse(job_id=job_id)

@app.get(f"/v{CURRENT_VERSION}/query/{{job_id}}", response_model=JobStatusResponse)
async def get_query_result(job_id: str):
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return JobStatusResponse(job_id=job_id, status=job["status"], result=job["result"])

@app.exception_handler(ResponseValidationError)
async def response_validation_handler(request: Request, exc: ResponseValidationError):
    LOG.exception("Response validation failed for %s", request.url)
    if DEBUG:
        return JSONResponse(status_code=500, content={"error": "response_validation_error", "detail": exc.errors()})
    return JSONResponse(status_code=500, content={"error": "internal_server_error"})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    LOG.exception("Unhandled exception for %s", request.url)
    if DEBUG:
        return JSONResponse(status_code=500, content={"error": type(exc).__name__, "detail": str(exc), "traceback": traceback.format_exc()})
    return JSONResponse(status_code=500, content={"error": "internal_server_error"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8081, reload=True, reload_excludes=["*.pyc", "data/**", "__pycache__/**","*.log"])