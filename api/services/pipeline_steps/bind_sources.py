import time
import re
from services.pipeline import PipelineStepContext, PipelineStepResult

from logging_config import logging
LOG = logging.getLogger(__name__)

async def bind_sources(
        context: PipelineStepContext,
        last_result: PipelineStepResult,
) -> PipelineStepResult:
    r = last_result.result["p_response"]
    p_results = last_result.result["p_results"]
    t_s = time.perf_counter()
    # Citation attribution and source binding
    LOG.debug("Attributing citations and binding sources...")
    works_cited_str = ""
    works_cited_seen = []
    for i, doc in enumerate(p_results):
        bound_r = re.sub(
            r"\(([^()]*)\)|\[([^\[\]]*)\]",
            lambda group: "(" + re.sub(
                r"\bE\d+\b",
                lambda reference: last_result.result["works"].get(reference.group(), reference.group()),
                group.group(1) if group.group(1) is not None else group.group(2),
            ) + ")",
            r,
        )
        if r != bound_r:
            r = bound_r
            if doc.metadata["canonical_work_id"] not in works_cited_seen:
                works_cited_str += f"{len(works_cited_seen) + 1}. {doc.metadata['full_citation']}.\n"
                works_cited_seen.append(doc.metadata["canonical_work_id"])
    r += "\n\n**Works Cited**\n\n" + works_cited_str
    LOG.debug("Prompt response with sources bound: %s", r)
    LOG.debug("Prompt processing completed in %.4f seconds", time.perf_counter() - t_s)
    return PipelineStepResult(
        result={
            **last_result.result,
            "p_response": r,
            "responses": last_result.result.get("responses", []) + [r], # allows recursion
        },
        execution_time=time.perf_counter() - t_s
    )