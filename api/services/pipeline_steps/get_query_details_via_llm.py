import time
from services.pipeline import PipelineStepContext, PipelineStepResult
from logging_config import logging
from templates.query_template import query_template
LOG = logging.getLogger(__name__)

async def get_query_details_via_llm(
    context: PipelineStepContext,
    last_result: PipelineStepResult,
) -> PipelineStepResult:
    start = time.perf_counter()
    result = {"query_metadata": {}}
    r, _ = await context.state["llm_client"].prompt(params={
        "user": query_template,
        "template": { "prompt": context.state["prompt"], "prompt_fr": "" }
    }, extract_json=True)
    if not isinstance(r, dict):
        raise ValueError("The query-details model response was not valid JSON.")
    result["query_metadata"]["prompt_query"] = r.get("prompt_query", "")
    result["query_metadata"]["prompt_query_fr"] = r.get("prompt_query_fr", "")
    result["query_metadata"]["prompt_instructions"] = r.get("prompt_instructions", "")
    LOG.debug("Query details time: %.4f seconds", time.perf_counter() - start)
    return PipelineStepResult(
        result={
            **last_result.result,
            **result
        },
        execution_time=time.perf_counter() - start
    )