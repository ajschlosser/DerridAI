import time
import asyncio
from services.pipeline import PipelineStepContext, PipelineStepResult
from logging_config import logging
LOG = logging.getLogger(__name__)

async def basic_rag_lookup(
    context: PipelineStepContext,
    last_result: PipelineStepResult,
) -> PipelineStepResult:
    t_s = time.perf_counter()
    async with context.state["rag_client"].lookup_semaphore:
        b_results = await asyncio.to_thread(
            context.state["rag_client"].basic_lookup,
            invocation_str={"en": last_result.result["prompt"], "fr": last_result.result["prompt_fr"]},
            search_types=["mmr", "similarity"],
            languages=["en", "fr"],
            split=True,
        )

    # Deduplication
    s_ids = []
    d_results = []
    for doc in b_results:
        id = doc.metadata.get("record_id")
        if id not in s_ids:
            s_ids.append(id)
            d_results.append(doc)
    LOG.debug("Total results after deduplication: %d", len(d_results))
    p_results = d_results

    LOG.debug("Lookup time: %.4f seconds", time.perf_counter() - t_s)
    await context.state["job_service"].update_job_status(last_result.result["request_id"], "[lookup]: Challenging the privileging of presence...")
    return PipelineStepResult(
        result={
            **last_result.result,
            "b_results": b_results,
            "d_results": d_results,
            "p_results": p_results,
        },
        execution_time=time.perf_counter() - t_s
    )