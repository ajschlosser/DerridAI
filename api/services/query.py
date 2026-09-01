from __future__ import annotations
import asyncio
import re
import time
from typing import TYPE_CHECKING
from clients.llm import LLMClient
from clients.rag import RAGClient
from clients.db import RedisClient
from services.nlp import NLPService
from schemas.schemas import DerridAIQueryMetadata, QueryRequest, GenericResponse
from utils.get_language_status import get_language_status
from utils.generate_citation_strings import generate_citation_strings
from utils.generate_context_string import generate_context_string
from utils.extract_query_metadata import QueryMetadataExtractor
from templates.query_template import query_template
from templates.focused_prompt_template import focused_prompt_template as prompt_template
import logging
from utils.request_id import request_id
from services.pipeline_steps.get_query_metadata import get_query_metadata
from services.pipeline_steps.get_query_details_via_llm import get_query_details_via_llm
from services.pipeline_steps.basic_rag_lookup import basic_rag_lookup
from services.pipeline_steps.get_retrieval_context import get_retrieval_context
from services.pipeline_steps.invoke_llm_with_prompt import invoke_llm_with_prompt
from services.pipeline_steps.bind_sources import bind_sources
from services.pipeline import PipelineStep, PipelineStepContext, PipelineStepResult

if TYPE_CHECKING:
    from services.jobs import JobService

LOG = logging.getLogger(__name__)

async def handle_query(
        request: QueryRequest,
        rag_client: RAGClient,
        llm_client: LLMClient,
        redis_client: RedisClient,
        nlp_service: NLPService,
        job_service: JobService,
        metadata_extractor: QueryMetadataExtractor,
        job_id: str,
) -> GenericResponse:
    LOG.debug("Decomposing prompt: %s", request.prompt)
    start = time.perf_counter()

    steps = [
        PipelineStep(
            fn=get_query_metadata,
            context=PipelineStepContext(
                request=request,
                state={
                    "get_language_status": get_language_status,
                    "nlp_service": nlp_service,
                    "job_service": job_service,
                    "metadata_extractor": metadata_extractor,
                }
            ),
            name="Get query metadata via NLP service",
        ),
        PipelineStep(
            fn=get_query_details_via_llm,
            context=PipelineStepContext(
                request=request,
                state={
                    "prompt": request.prompt,
                    "llm_client": llm_client,
                    "job_service": job_service,
                }
            ),
            name="Get query details via LLM",
        ),
        PipelineStep(
            fn=basic_rag_lookup,
            context=PipelineStepContext(
                request=request,
                state={
                    "rag_client": rag_client,
                    "job_service": job_service,
                }
            ),
            name="Basic RAG lookup",
        ),
        PipelineStep(
            fn=get_retrieval_context,
            context=PipelineStepContext(
                request=request,
                state={
                    "job_service": job_service,
                }
            ),
            name="Get retrieval context",
        ),
        PipelineStep(
            fn=invoke_llm_with_prompt,
            context=PipelineStepContext(
                request=request,
                state={
                    "llm_client": llm_client,
                    "job_service": job_service,
                }
            ),
            name="Invoke LLM with prompt",
        ),
        PipelineStep(
            fn=bind_sources,
            context=PipelineStepContext(
                request=request,
                state={
                    "job_service": job_service,
                }
            ),
            name="Bind sources",
        ),
    ]

    step_results = PipelineStepResult(result={}, execution_time=0.0)
    for step in steps:
        LOG.info("Executing pipeline step #%d '%s' with ID '%s'...", step.position, step.name, step.id)
        step_results = await step.execute(step_results)
        LOG.info("Finished in %.4f seconds execution of pipeline step #%d '%s' with ID '%s'.", time.perf_counter() - start, step.position, step.name, step.id)

    p_results = step_results.result["p_results"]
    b_results = step_results.result["b_results"]
    d_results = step_results.result["d_results"]
    q = step_results.result["query_metadata"]
    r = step_results.result["p_response"]

    # Report results
    LOG.info("Original query: %s", q)
    total_elapsed = time.perf_counter() - start
    LOG.info("Total time elapsed: %.4f seconds", total_elapsed)
    LOG.info(rag_client.get_config_string())
    LOG.info(llm_client.get_config_string())
    LOG.info(f"initial mmr and similarity results: {len(b_results)} | total after deduplication: {len(d_results)} | total after reranking: {len(p_results)}")

    response = GenericResponse(content=q | { "response": r, "request_id": request_id.get() }, results=[p_results])

    return response