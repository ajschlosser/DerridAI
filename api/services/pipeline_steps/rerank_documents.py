import time
from services.pipeline import PipelineStepContext, PipelineStepResult
from utils.generate_citation_strings import generate_citation_strings
from utils.generate_context_string import generate_context_string
from clients.rag import RAGClient
from logging_config import logging
from utils.get_language_status import get_language_status
from functools import wraps

LOG = logging.getLogger(__name__)

def pipeline_step(func):
    @wraps(func)
    async def wrapper(context, last_result) -> PipelineStepResult:
        new_result = await func(context, last_result)
        return PipelineStepResult(
            result={
                **last_result.result,
                **new_result
            },
            execution_time=0.0
        )
    return wrapper

@pipeline_step
async def rerank_documents(
    context: PipelineStepContext,
    last_result: PipelineStepResult,
) -> dict:
    start = time.perf_counter()
    docs = last_result.result.get("p_results", [])
    rag_client: RAGClient | None = context.state.get("rag_client")
    if not isinstance(rag_client, RAGClient):
        return last_result.result
    # materials_languages: list[Languages] = last_result.result.get("materials_languages", [])
    # en_enabled, fr_enabled = get_language_status(materials_languages)
    q = last_result.result.get("query_metadata", {})
    prompt_query = q.get("prompt_query", "")
    prompt_query_fr = q.get("prompt_query_fr", "")

    rerank_prompt = prompt_query + "\n" + prompt_query_fr

    LOG.debug("First document before reranking: %s", docs[0].metadata.get("record_id", ""))
    LOG.debug("Last document before reranking: %s", docs[-1].metadata.get("record_id", ""))
    p_results = rag_client.rerank_documents(rerank_prompt, docs, top_n=24)
    LOG.debug("First document AFTER reranking: %s", p_results[0].metadata.get("record_id", ""))
    LOG.debug("Last document AFTER reranking: %s", p_results[-1].metadata.get("record_id", ""))

    return {
        "p_results": p_results
    }
    
    return PipelineStepResult(
        result={
            **last_result.result,
            "p_results": p_results,
        },
        execution_time=time.perf_counter() - start
    )