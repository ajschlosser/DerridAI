from utils.generate_citation_strings import generate_citation_strings
from clients.rag import RAGClient
from clients.llm import LLMClient
from services.nlp import NLPService
from schemas.schemas import QueryRequest
from utils.extract_query_metadata import QueryMetadataExtractor
from utils.get_language_status import get_language_status
from services.pipeline import PipelineStep, PipelineStepContext, PipelineStepResult
import time
from services.pipeline_steps.get_query_metadata import get_query_metadata
from services.pipeline_steps.get_query_details_via_llm import get_query_details_via_llm
from services.pipeline_steps.basic_rag_lookup import basic_rag_lookup
from services.pipeline_steps.get_retrieval_context import get_retrieval_context
from services.pipeline_steps.invoke_llm_with_prompt import invoke_llm_with_prompt
from services.pipeline_steps.bind_sources import bind_sources
from logging_config import logging, configure_logging
import argparse
print("...")
args = argparse.ArgumentParser()
args.add_argument("-p", "--prompt", type=str, default="defaults", help="The prompt for DerriDAI to use")
args = args.parse_args()

configure_logging(logging.DEBUG, "derridai-test.api.log")

LOG = logging.getLogger(__name__)

LOG.info("Starting rag_test.py")

nlp_service: NLPService = NLPService()

LOG.info("Initialized NLPService")

class DummyJobService:
    async def update_job_status(self, id, msg):
        pass

job_service = DummyJobService()

async def handle_query(
        request: QueryRequest = QueryRequest(prompt="Talk to me about Derrida and hospitality. What does hospitality mean to Derrida and what is its place in the constellation of his thought? Do not be repetitious in your response. Vary your prose and avoid clichés."),
        rag_client: RAGClient = RAGClient(
            default_k_value = 24,
            default_fetch_k_value = 500,
            default_lambda_mult_value= 0.5

        ),
        llm_client: LLMClient = LLMClient(
            model="gemma4:e2b",
            mirostat_eta=0.5,
            mirostat_tau=0.005,
            temperature=0.005,
        ),
        nlp_service: NLPService = nlp_service,
        metadata_extractor: QueryMetadataExtractor = QueryMetadataExtractor(nlp_service),
        job_id: str = "test_job_id",
) -> None:
    LOG.debug("Decomposing prompt: %s", request.prompt)
    start = time.perf_counter()

    async def tidy(
            context: PipelineStepContext,
            last_result: PipelineStepResult,
    ) -> PipelineStepResult:
        start = time.perf_counter()
        r, _ = await context.state["llm_client"].prompt(params={
            "user": """
            You are a meticulous editor.
            You have been given a draft of an academic paper.
            Your task is to edit the paper for clarity, conciseness, and coherence.
            You should also ensure that the paper adheres to academic standards and conventions
            Please provide a revised version of the paper that is polished and ready for submission.  

            The paper in question:

            {paper}

            Requirements:
            - Do not delete or remove any content from the paper.
            - Do not add any new content to the paper.
            - Do not change the meaning of any content in the paper.
            - Do not change the structure of the paper.
            - Remove repetitious phrases.
            - Add coherent phrasing.

            Return value:
            - Return only the edited paper, nothing else, no notes, no commentary.
            
            """,
            "template": {
                "paper": last_result.result.get("p_results", ""),
            }
        })
        LOG.info("Paper so far: %s", r)
        return PipelineStepResult(
            result={
                **last_result.result,
                "paper": r,
                "final_paper": r
            },
            execution_time=time.perf_counter() - start
        )

    async def build_monograph(
            context: PipelineStepContext,
            last_result: PipelineStepResult,
    ) -> PipelineStepResult:
        start = time.perf_counter()
        r, _ = await context.state["llm_client"].prompt(params={
            "user": """
                You are writing a long academic paper (20-30 pages).
                
                You started writing in response to this prompt: {prompt_query}.

                You were given instructions, if any: {prompt_instructions}
                
                Your first response was: {p_response}

                So far, in total, you have written the following for your paper:

                {paper}

                In the above, please remove any false summaries ("In conclusion...")

                Continue with the next full section.

                You must continue to draw from these sources:

                {sources}

                Guidelines:
                - Respond only with the intended output, no paratext or commentary or reasoning.
                - Do not create subheadings or subsections.
                - Do not create numbered sections.
                - Do not attempt to create chapters.
                - Just focus on the prose and analysis.
                - Do not repeat yourself. Every section must introduce a concept, idea, or thesis not yet in the paper.

                Citation rules:
                - Tag every claim with an evidence ID from the evidence block above. i.e. [E0], [E1], etc.

                Requirements:
                - Respond with the next section of your paper
            """,
            "template": {
                "prompt_query": last_result.result["query_metadata"].get("prompt_query", ""),
                "prompt_instructions": last_result.result["query_metadata"].get("prompt_instructions", ""),
                "paper": last_result.result.get("paper", ""),
                "p_response": last_result.result.get("p_response", ""),
                "sources": last_result.result.get("retrieval_context", ""),
            }
        })
        new_paper = last_result.result.get("paper", "") + "\n" + last_result.result.get("p_response", "")
        LOG.info("Paper so far: %s", new_paper)
        return PipelineStepResult(
            result={
                **last_result.result,
                "paper": new_paper,
                "p_response": r
            },
            execution_time=time.perf_counter() - start
        )

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
        # PipelineStep(
        #     fn=invoke_llm_with_prompt,
        #     context=PipelineStepContext(
        #         request=request,
        #         state={
        #             "llm_client": llm_client,
        #             "job_service": job_service,
        #         }
        #     ),
        #     name="Invoke LLM with prompt",
        # ),
        # PipelineStep(
        #     fn=bind_sources,
        #     context=PipelineStepContext(
        #         request=request,
        #         state={
        #             "exclude_works_cited": True,
        #             "job_service": job_service,
        #         }
        #     ),
        #     name="Bind sources",
        # ),
        {
            "iterations": 25,
            "steps": [
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
                            "exclude_works_cited": True,
                            "job_service": job_service,
                        }
                    ),
                    name="Bind sources",
                ),
            ]
        },
    ]

    step_results = PipelineStepResult(result={}, execution_time=0.0)
    for step in steps:
        if isinstance(step, dict) and "steps" in step:
            iterations = step.get("iterations", 1)
            for iteration in range(iterations):
                LOG.info("Starting iteration %d of %d for nested pipeline steps...", iteration + 1, iterations)
                for nested_step in step["steps"]:
                    LOG.info("Executing nested pipeline step #%d '%s' with ID '%s'...", nested_step.position, nested_step.name, nested_step.id)
                    step_results = await nested_step.execute(step_results)
                    LOG.info("Finished in %.4f seconds execution of nested pipeline step #%d '%s' with ID '%s'.", time.perf_counter() - start, nested_step.position, nested_step.name, nested_step.id)
        elif isinstance(step, PipelineStep):
            LOG.info("Executing pipeline step #%d '%s' with ID '%s'...", step.position, step.name, step.id)
            step_results = await step.execute(step_results)
            LOG.info("Finished in %.4f seconds execution of pipeline step #%d '%s' with ID '%s'.", time.perf_counter() - start, step.position, step.name, step.id)

    p_results = step_results.result["p_results"]
    b_results = step_results.result["b_results"]
    d_results = step_results.result["d_results"]
    q = step_results.result["query_metadata"]
    r = step_results.result["p_response"]
    LOG.info("Pipeline execution completed in %.4f seconds", time.perf_counter() - start)
    LOG.info("Results: %s", step_results.result)
    # Report results
    LOG.info("Original query: %s", q)
    total_elapsed = time.perf_counter() - start
    LOG.info("Total time elapsed: %.4f seconds", total_elapsed)
    LOG.info(rag_client.get_config_string())
    LOG.info(llm_client.get_config_string())
    LOG.info(f"initial mmr and similarity results: {len(b_results)} | total after deduplication: {len(d_results)} | total after reranking: {len(p_results)}")

    exit(0)

async def main():
    LOG.info("Starting RAG test script...")
    result = await handle_query()
    LOG.info("Result: %s", result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())