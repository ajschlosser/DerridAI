

import time
import asyncio
from services.pipeline import PipelineStepContext, PipelineStepResult, PipelineStep
from logging_config import logging
from utils.request_id import request_id
LOG = logging.getLogger(__name__)

async def get_query_metadata(
    context: PipelineStepContext,
    last_result: PipelineStepResult,
) -> PipelineStepResult:
    start = time.perf_counter()
    p = context.request.prompt
    p_fr = p
    q = await asyncio.to_thread(context.state["metadata_extractor"].extract, p, "en") #needs refactoring
    en, fr = context.state["get_language_status"](q["prompt_languages"])
    if en:
        p_fr = context.state["nlp_service"].translate(p, from_lang="en", to_lang="fr")
        q["prompt_fr"] = p_fr
        q["keywords_fr"] = context.state["nlp_service"].extract_keywords(p_fr)
    elif fr:
        p_fr = p
        p = context.state["nlp_service"].translate(p, from_lang="fr", to_lang="en")
        q["prompt"] = p
        q["keywords"] = context.state["nlp_service"].extract_keywords(p)
    LOG.debug("Extracted filters: %s", q)
    LOG.debug("Preprocessing time: %.4f seconds", time.perf_counter() - start)
    r_id = request_id.get()
    await context.state["job_service"].update_job_status(r_id, "[preprocessing]: Deconstructing binary oppositions...")
    return PipelineStepResult(
        result={
            **last_result.result,
            "prompt": p,
            "prompt_fr": p_fr,
            "query_metadata": q,
            "request_id": r_id
        },
        execution_time=time.perf_counter() - start
    )