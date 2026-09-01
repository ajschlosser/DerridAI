import asyncio
import re
import time
from clients.llm import LLMClient
from clients.rag import RAGClient
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
LOG = logging.getLogger(__name__)

async def handle_query(request: QueryRequest, rag_client: RAGClient, llm_client: LLMClient, nlp_service: NLPService, metadata_extractor: QueryMetadataExtractor) -> GenericResponse:
    LOG.debug("Decomposing prompt: %s", request.prompt)

    # 0. PREPROCESSING
    #===========================================
    # Get query metadata
    start = time.perf_counter()
    p = request.prompt
    p_fr = p
    q = await asyncio.to_thread(metadata_extractor.extract, p, "en")
    en, fr = get_language_status(q["prompt_languages"])
    if en:
        p_fr = nlp_service.translate(p, from_lang="en", to_lang="fr")
        q["prompt_fr"] = p_fr
        q["keywords_fr"] = nlp_service.extract_keywords(p_fr)
    elif fr:
        p_fr = p
        p = nlp_service.translate(p, from_lang="fr", to_lang="en")
        q["prompt"] = p
        q["keywords"] = nlp_service.extract_keywords(p)
    LOG.debug("Extracted filters: %s", q)
    LOG.debug("Preprocessing time: %.4f seconds", time.perf_counter() - start)

    # 1. QUERY DETAILS
    #===========================================
    t_s = time.perf_counter()
    r, _ = await llm_client.prompt(params={
        "user": query_template,
        "template": { "prompt": p, "prompt_fr": p_fr }
    }, extract_json=True)
    q: DerridAIQueryMetadata = q | r
    LOG.debug("Query details time: %.4f seconds", time.perf_counter() - t_s)

    # 2. LOOKUP
    #===========================================
    # Basic lookup
    # TODO: Implement other lookup strategies if needed
    t_s = time.perf_counter()

    async with rag_client.lookup_semaphore:
        b_results = await asyncio.to_thread(
            rag_client.basic_lookup,
            invocation_str={"en": p, "fr": p_fr},
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

    # 3. RETRIEVAL POST-PROCESSING
    # ====================================================
    # Reordering and reranking
    # TODO: Implement reranking logic for the retrieved documents
    t_s = time.perf_counter()

    # Generate and store citation strings for each document
    for doc in p_results:
        doc.metadata["inline_citation"], doc.metadata["full_citation"] = generate_citation_strings(doc)

    # Build context string
    works = {}
    for i, doc in enumerate(p_results):
        works[f"E{i}"] = doc.metadata["inline_citation"]
    LOG.debug("Reranked works: %s", works)
    context = generate_context_string(p_results)
    LOG.info(f"Context:\n{context}")
    LOG.debug("Post-processing completed in %.4f seconds", time.perf_counter() - t_s)

    # 4. PROMPTING
    # ====================================================
    # Focused prompt
    t_s = time.perf_counter()

    r, _ = await llm_client.prompt(params={
        "user": prompt_template,
        "template": {
            "prompt_query": q.get("prompt_query", ""),
            "prompt_instructions": q.get("prompt_instructions", ""),
            "context": context,
        }
    })

    # Citation attribution and source binding
    LOG.debug("Attributing citations and binding sources...")
    works_cited_str = ""
    works_cited_seen = []
    for i, doc in enumerate(p_results):
        r = re.sub(
            r"\(([^()]*)\)|\[([^\[\]]*)\]",
            lambda group: "(" + re.sub(
                r"\bE\d+\b",
                lambda reference: works.get(reference.group(), reference.group()),
                group.group(1) if group.group(1) is not None else group.group(2),
            ) + ")",
            r,
        )
        if doc.metadata["canonical_work_id"] not in works_cited_seen:
            works_cited_str += f"{len(works_cited_seen) + 1}. {doc.metadata['full_citation']}.\n"
            works_cited_seen.append(doc.metadata["canonical_work_id"])
    r += "\n\n**Works Cited**\n\n" + works_cited_str
    LOG.debug("Prompt response with sources bound: %s", r)
    LOG.debug("Prompt processing completed in %.4f seconds", time.perf_counter() - t_s)

    # 4. WRAP-UP
    # ====================================================
    # Report results
    LOG.info("Original query: %s", q)
    total_elapsed = time.perf_counter() - start
    LOG.info("Total time elapsed: %.4f seconds", total_elapsed)
    LOG.info(rag_client.get_config_string())
    LOG.info(llm_client.get_config_string())
    LOG.info(f"initial mmr and similarity results: {len(b_results)} | total after deduplication: {len(d_results)} | total after reranking: {len(p_results)}")

    response = GenericResponse(content=q | { "response": r, "request_id": request_id.get() }, results=[p_results])

    return response