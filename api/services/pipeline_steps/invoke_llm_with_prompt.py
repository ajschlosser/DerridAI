import time
from templates import focused_prompt_template as prompt_template
from services.pipeline import PipelineStepContext, PipelineStepResult

async def invoke_llm_with_prompt(
    context: PipelineStepContext,
    last_result: PipelineStepResult,
) -> PipelineStepResult:
    t_s = time.perf_counter()
    await context.state["job_service"].update_job_status(last_result.result["request_id"], "[prompting]: Reifying...")
    r, _ = await context.state["llm_client"].prompt(params={
        "user": prompt_template,
        "template": {
            "prompt_query": last_result.result["query_metadata"].get("prompt_query", ""),
            "prompt_instructions": last_result.result["query_metadata"].get("prompt_instructions", ""),
            "context": last_result.result["retrieval_context"],
        }
    })
    return PipelineStepResult(
        result={
            **last_result.result,
            "p_response": r,
        },
        execution_time=time.perf_counter() - t_s
    )