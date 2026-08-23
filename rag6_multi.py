#!/usr/bin/env python3

# Copyright 2026 Aaron John Schlosser, PhD

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://apache.org

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""rag6_multi.py -- Retrieval-augmented generation demo with CLI controls and progress logs."""

# STANDARD LIBRARIES
import math
import json
import difflib
import argparse

# LLM
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.document_transformers import LongContextReorder
from langchain_chroma import Chroma
from langchain_core.documents import Document

# LOGGING
import logging
import sys
from pathlib import Path

# TYPING
from dataclasses import dataclass
from typing import Dict, Any, Optional

from prompts import (
    review_prompt_template,
    initial_prompt_template,
    query_improvement_template,
    initial_retrieval_prompt_template,
)

from typings import (
    LangChainConfig
)

from defaults import (
    CHAT_TEMPERATURE,
    LAMBDA_MULT_VALUE,
    K_VALUE,
    FETCH_K_VALUE,
    keys
)

from logger import Logger

# CLI ARGUMENTS
parser = argparse.ArgumentParser(description="RAG Pipeline for Philosophical Texts")
parser.add_argument(
    "--prompt",
    "-p",
    "--query",
    "-q",
    type=str,
    default="What does Derrida say about presence?",
    help="Question to ask the RAG pipeline.",
)
args = parser.parse_args()

LOG = Logger.setup()

# LANGCHAIN CLIENT WRAPPER
class LangChainClient:
    """
    A thin wrapper that builds a LangChain chat model, an embeddings model,
    and a Chroma vector store based on a user‑supplied configuration.

    Parameters
    ----------
    config : Optional[LangChainConfig] = None
        A typed configuration object.  If omitted, defaults from the module
        constants are used.
    """
    def __init__(self, config: Optional[LangChainConfig] = None):
        cfg = config or LangChainConfig.from_defaults()
        LOG.info("Initializing LangChainClient with configuration: %s", cfg)
        LOG.info(f"""\n
=================
| CONFIGURATION |
=================
MODEL: {cfg.chat.model}
TEMPERATURE: {cfg.chat.temperature}
BASE_URL: {cfg.chat.base_url}
EMBEDDING_MODEL: {cfg.embedding.model}
DB_PATH: {cfg.store.persist_directory}
        """)
        self.chat_model = ChatOllama(
            model=cfg.chat.model,
            temperature=cfg.chat.temperature,
            base_url=cfg.chat.base_url,
            timeout=45.0, # 45s
        )
        self.embedding_model = OllamaEmbeddings(
            model=cfg.embedding.model,
            base_url=cfg.embedding.base_url,
        )
        self.vector_store = Chroma(
            persist_directory=cfg.store.persist_directory,
            embedding_function=self.embedding_model,
        )
        LOG.info("LangChainClient initialized successfully.")
    def invoke(self, prompt: str):
        LOG.info(f"Invoking chat model [{self.chat_model.model}] with prompt: {prompt}")
        return self.chat_model.invoke(prompt)
    def create_retriever(self, search_kwargs: dict, search_type: str = "mmr"):
        LOG.info(f"Creating retriever with search_kwargs: {search_kwargs} and search_type: {search_type}")
        self.retrievers = getattr(self, "retrievers", [])
        retriever = self.vector_store.as_retriever(search_kwargs=search_kwargs, search_type=search_type)
        self.retrievers.append(retriever)
        return retriever

# MAIN FUNCTION
def main():
    client = LangChainClient()


    # LOG.info("Formatted prompt: %s", formatted_prompt)

    # Initial query processing
    a_query_improvement_prompt = ChatPromptTemplate.from_template(query_improvement_template)
    a_formatted_query_improvement_prompt = a_query_improvement_prompt.format(prompt=args.prompt)
    a_query_details = client.invoke(a_formatted_query_improvement_prompt)
    a_prompt_options = json.loads(a_query_details.content)
    LOG.info("Chat model response: %s", a_prompt_options)


    if a_prompt_options.get("is_fetch_query"):
        LOG.info("User is asking for appearances of specific content in the source materials: '%s'", a_prompt_options["fetch_query_content"])
        fetched_results = client.vector_store.get(where_document={"$or": [{ "$contains": a_prompt_options["fetch_query_content"]}, { "$contains": a_prompt_options.get("fetch_query_content_fr")}]})

        if len(fetched_results["ids"]) == 0:
            LOG.info("No results found for the fetch query.")
            or_conditions = [{"$contains": keyword} for keyword in a_prompt_options["keywords"]]
            if a_prompt_options.get("keywords_fr"):
                or_conditions_fr = [{"$contains": keyword} for keyword in a_prompt_options.get("keywords_fr")]
                #or_conditions.extend([{"$contains": keyword} for keyword in or_conditions_fr])
            else:
                or_conditions_fr = []
            fetched_keword_results = client.vector_store.get(where_document={"$and": or_conditions})
            fetched_keword_results_fr = client.vector_store.get(where_document={"$and": or_conditions_fr})
            combined_results = {
                "ids": fetched_keword_results["ids"] + fetched_keword_results_fr["ids"],
                "metadatas": fetched_keword_results["metadatas"] + fetched_keword_results_fr["metadatas"],
                "documents": fetched_keword_results["documents"] + fetched_keword_results_fr["documents"]
            }
            LOG.info("Fetched keyword results: %d", len(fetched_keword_results["ids"]))
            if len(fetched_keword_results["ids"]) == 0:
                LOG.info("No results found for the keyword fetch query.")
            fetched_results = combined_results
            
        ids = fetched_results["ids"]
        metadatas = fetched_results["metadatas"]
        docs = fetched_results["documents"]
        LOG.info("Fetched results: %d", len(ids))

        cleaned_results = [
            {
                "author": m.get("document_author"),
                "section_author": m.get("section_author"),
                "work": m.get("work"),
                "edition": m.get("edition"),
                "year": m.get("year"),
                "text": d,
                "pagination": f"{m.get('page_start') if (not m.get('page_end') or m.get('page_end') == m.get('page_start')) else f'{m.get('page_start')}-{m.get('page_end')}'}",
                "citation_inline": f"({m.get('section_author', m.get('document_author', m.get('work'))).split(' ')[1]} {m.get('year')}, {m.get('page_start') if (not m.get('page_end') or m.get('page_end') == m.get('page_start')) else f'{m.get('page_start')}-{m.get('page_end')}'})"
            } for m, d in zip(metadatas, docs)
        ]

        output = {
            "prompt": args.prompt,
            "bibliography": [],
            "results": cleaned_results,
            "total": len(cleaned_results)
        }

        for doc in cleaned_results:
            # if doc.get('page_start') and doc.get('page_end') and doc.get('page_start') is not doc.get('page_end'):
            #     page_number = f"{doc.get('page_start', '')}-{doc.get('page_end', '')}"
            # else:
            #     page_number = f"{doc.get('page_start', '')}"

            author = doc.get('author', '')
            if doc.get('section_author') and doc.get('section_author') != author:
                author = doc.get('section_author')
            author_reversed = f"{author.split(' ')[-1]}, {author.split(' ')[0]}"
            
            citation = f"{author_reversed}. {doc.get('work', '')}. {doc.get('edition', '')}. {doc.get('year', '')}"
            LOG.info("Generated citation: %s", citation)
            if citation not in output["bibliography"]:
                output["bibliography"].append(citation)

        LOG.info("Fetched results content: %s", output)
        return output
    else:
        LOG.info("User is asking for a general answer, not specific appearances.")

    # Initial filtering and retriever creation
    initial_search_kwargs = {
        "k": K_VALUE,
        "fetch_k": FETCH_K_VALUE,
        "lambda_mult": LAMBDA_MULT_VALUE,
        "filter": { "$and": [{"text_length": {"$gt": 500}}] }
    }
    LOG.info("Initial search kwargs: %s", initial_search_kwargs)
    if a_prompt_options["materials_language"]:
        LOG.info("Filtering by materials language: %s", a_prompt_options["materials_language"])
        initial_search_kwargs["filter"]["$and"].append({
            "document_language": {
                "$in": a_prompt_options["materials_language"]
            }
        })
    else:
        LOG.info("No materials language specified, not adding language filter.")
        initial_search_kwargs["filter"] = { "text_length": {"$gt": 500} }

    initial_retriever = client.create_retriever(search_kwargs=initial_search_kwargs, search_type="mmr")
    secondary_retriever = client.create_retriever(search_kwargs={ "k": K_VALUE, "filter": { "text_length": {"$gt": 500}}}, search_type="similarity")

    # Initial retrieval using the created retriever
    b_initial_retrieval_prompt = ChatPromptTemplate.from_template(initial_retrieval_prompt_template)
    b_formatted_initial_retrieval_prompt = b_initial_retrieval_prompt.format(
        prompt_query=a_prompt_options["prompt_query"],
        prompt_query_fr=a_prompt_options["prompt_query_fr"],
        keywords=json.dumps(a_prompt_options["keywords"]),
        keywords_fr=json.dumps(a_prompt_options["keywords_fr"])
    )
    LOG.info("Formatted initial retrieval prompt: %s", b_formatted_initial_retrieval_prompt)
    candidates = initial_retriever.invoke(b_formatted_initial_retrieval_prompt)
    additional_candidates = secondary_retriever.invoke(b_formatted_initial_retrieval_prompt)

    canonical_candidates = []
    if (a_prompt_options["keywords"] or a_prompt_options["keywords_fr"]):
        LOG.info("Retrieving canonical works by keyword: %s", a_prompt_options["keywords"])

        canonical_work_ids = []
        canonical_work_ids_fr = []

        for keyword in a_prompt_options["keywords"]:
            if keyword.lower() in keys.get("en_us", {}):
                canonical_work_ids.append(keys["en_us"][keyword.lower()])
        for keyword in a_prompt_options["keywords_fr"]:
            if keyword.lower() in keys.get("fr_fr", {}):
                canonical_work_ids_fr.append(keys["fr_fr"][keyword.lower()])

        combined_work_ids = [item for sublist in (canonical_work_ids + canonical_work_ids_fr) for item in sublist]
        #combined_work_ids = canonical_work_ids + canonical_work_ids_fr
        LOG.info("Combined canonical work IDs: %s", combined_work_ids)

        canonical_work_retriever = client.create_retriever(
            search_kwargs={
                "k": K_VALUE,
                "filter": {
                    "canonical_work_id": {
                        "$in": combined_work_ids
                    }
                }
            }, search_type="similarity")
        canonical_candidates = canonical_work_retriever.invoke(b_formatted_initial_retrieval_prompt)


    combined_candidates = candidates + additional_candidates + canonical_candidates
    LOG.info("Retrieved %d candidates using MMR and similarity search.", len(combined_candidates))
    if not combined_candidates:
        LOG.warning("No context found matching the query and filter criteria.")
        print("\n--- No matching results found ---")
        return

    
    # Filter out candidates whose document_language is not in materials_language
    combined_candidates = [
        doc for doc in combined_candidates if doc.metadata.get("document_language", "fr_fr") in a_prompt_options["materials_language"]
    ]
    LOG.info("Filtered candidates based on materials_language: %s", a_prompt_options["materials_language"])
    LOG.info("Unique candidates after filtering: %d", len(combined_candidates))

    seen = set()
    unique_candidates = []
    for doc in combined_candidates:
        chunk_id = doc.metadata.get("record_id")

        if chunk_id not in seen:
            seen.add(chunk_id)
            unique_candidates.append(doc)

    LOG.info("Filtered to %d unique candidates after removing duplicates.", len(unique_candidates))

    # Reorder the retrieved context groups to prioritize the most relevant and coherent evidence blocks
    LOG.info("Reordering context groups with LongContextReorder...")
    reordering = LongContextReorder()
    reordered_groups = reordering.transform_documents(unique_candidates)

    context = "\n============================================\n".join(
        f"""// EVIDENCE_BLOCK_ID: 00-{i} | ID: {doc.metadata.get("canonical_work_id", "N/A")} | Length: {doc.metadata.get("text_length", "N/A")}
{json.dumps(doc.metadata)}
"""
        for i, doc in enumerate(reordered_groups)
    )

    LOG.info("Constructed evidence, source, and citation context blocks: %s", context)

    prompt = ChatPromptTemplate.from_template(initial_prompt_template)
    final_prompt = prompt.format(context=context, prompt=a_prompt_options)
    LOG.info("Final prompt: %s", final_prompt)

    # Invoke the final prompt with the chat model
    response = client.invoke(final_prompt)
    LOG.info(f"""
Initial prompt: {a_prompt_options["prompt"]}
Instructions taken from prompt: {a_prompt_options["prompt_instructions"]}
Query taken from prompt: {a_prompt_options["prompt_query"]}
""")
    LOG.info(f"""
Model response:
{response.content}
k: {K_VALUE} | retrieved_candidates: {len(combined_candidates)}
unique_candidates: {len(unique_candidates)} | lambda_mult: {LAMBDA_MULT_VALUE}
chat_temperature: {CHAT_TEMPERATURE}
""")

#     LOG.info("Reviewing response...")

#     review_prompt = ChatPromptTemplate.from_template(review_prompt_template)
#     review_prompt = review_prompt.format(response_content=response.content, context=context)
#     reviewed = client.invoke(review_prompt)
#     LOG.info("Initial prompt: %s", args.prompt)
#     LOG.info("Reviewed response: %s", reviewed.content)

#     final_prompt = f"""
#         Please provide a final, polished response based on the reviewed content.

#         You are responding to the original PROMPT.

#         You are revising the DRAFT RESPONSE based on the CLAIMS.

#         Revise any claim with revised_claim.text fields.

#         Drop any claim with a claim_confidence < 0.9

#         Drop any claim with an attribution_confidence < 0.9

#         Use the claim data to map claims to page numbers (Author, Work, #) and for the Works Cited section.

#         Never infer or reconstruct bibliographic roles.

#         Preserve exactly:
#         - work_author
#         - contribution_author
#         - contribution_role
#         - editor
#         - translator
#         - publisher
#         - publication_year

#         Do not use pronouns for source authors; use surnames.

#         [CLAIMS]
#             {reviewed.content}
#         [/CLAIMS]

#         [DRAFT RESPONSE]
#             {response.content}
#         [/DRAFT RESPONSE]

#         [PROMPT]
#             {args.prompt}
#         [/PROMPT]

#         Your response should be in the form of an encyclopedia entry or academic essay.
# """
#     #LOG.info("After review final prompt: %s", final_prompt)
#     final_response = client.invoke(final_prompt)

    #LOG.info("Final response: %s", final_response.content)

if __name__ == "__main__":
    main()