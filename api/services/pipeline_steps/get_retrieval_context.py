import time
from services.pipeline import PipelineStepContext, PipelineStepResult
from utils.generate_citation_strings import generate_citation_strings
from utils.generate_context_string import generate_context_string
from logging_config import logging

LOG = logging.getLogger(__name__)

async def get_retrieval_context(
    context: PipelineStepContext,
    last_result: PipelineStepResult,
) -> PipelineStepResult:
    t_s = time.perf_counter()
    p_results = last_result.result["p_results"]
    for doc in p_results:
        doc.metadata["inline_citation"], doc.metadata["full_citation"] = generate_citation_strings(doc)

    # Build context string
    works = {}
    for i, doc in enumerate(p_results):
        works[f"E{i}"] = doc.metadata["inline_citation"]
    LOG.debug("Reranked works: %s", works)
    retrieval_context = generate_context_string(p_results)
    LOG.info(f"Retrieval context:\n{retrieval_context}")
    LOG.debug("Post-processing completed in %.4f seconds", time.perf_counter() - t_s)
    await context.state["job_service"].update_job_status(last_result.result["request_id"], "[retrieval post-processing]: Always already post-processing...")
    return PipelineStepResult(
        result={
            **last_result.result,
            "retrieval_context": retrieval_context,
            "works": works,
        },
        execution_time=time.perf_counter() - t_s
    )