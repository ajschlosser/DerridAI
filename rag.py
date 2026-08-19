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

"""rag.py – Retrieval‑augmented generation demo with CLI controls and progress logs."""

import os
import json
import difflib
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from langchain_community.document_transformers import LongContextReorder

from config import (
    CHAT_MODEL,
    CHAT_TEMPERATURE,
    OLLAMA_SERVER_URL,
    DB_PATH,
    SOURCE_TEXT,
    BATCH_SIZE,
    K_VALUE,
    FETCH_K_VALUE,
    LAMBDA_MULT_VALUE,
    args
)

from helpers import (
    get_logger,
    get_search_filters,
    keyword_map,
    parse_natural_language_find_query
)

from models import (
    get_llm_chat
)

from store import (
    database_exists,
    delete_vector_store,
    get_retriever,
    get_store
)

LOG = get_logger(__name__)

# ---------------------------------------------------------------------------
# Main Routine
# ---------------------------------------------------------------------------

def main():
    
    # ---------------------------------------------------------------------------
    # Vector store setup / rebuild logic (Batched & Streamed)
    # ---------------------------------------------------------------------------

    vector_store = get_store()
    if database_exists(DB_PATH) and not args.force_rebuild:
        LOG.info("Loading existing vector store from '%s'...", DB_PATH)
    elif args.force_rebuild or not database_exists(DB_PATH):
        # if args.force_rebuild:
        #     delete_vector_store(DB_PATH)
        LOG.info("Initializing new Chroma database at '%s'...", DB_PATH)
        
        doc_batch = []
        id_batch = []
        total_indexed = 0

        LOG.info("Streaming and indexing documents in batches of %d...", BATCH_SIZE)
        
        with open(SOURCE_TEXT, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                
                record = json.loads(line)
                doc = Document(
                    page_content=record["text"],
                    metadata={"record_id": record["id"], **record["metadata"]},
                )
                
                doc_batch.append(doc)
                id_batch.append(record["id"])

                # Whenever we hit the batch limit, send to Chroma & clear buffer
                if len(doc_batch) >= BATCH_SIZE:
                    vector_store.add_documents(documents=doc_batch, ids=id_batch)
                    total_indexed += len(doc_batch)
                    LOG.info("Indexed %d documents so far...", total_indexed)
                    doc_batch.clear()
                    id_batch.clear()

            # Flush any remaining documents in the final batch
            if doc_batch:
                vector_store.add_documents(documents=doc_batch, ids=id_batch)
                total_indexed += len(doc_batch)
                LOG.info("Indexed final batch. Total documents indexed: %d", total_indexed)

        LOG.info("Vector store creation complete.")

    # ---------------------------------------------------------------------------
    # Dynamic filter configuration
    # ---------------------------------------------------------------------------

    search_kwargs = {"k": K_VALUE, "fetch_k": FETCH_K_VALUE, "lambda_mult": LAMBDA_MULT_VALUE}
    filters = get_search_filters()
    if filters:
        search_kwargs["filter"] = filters
        LOG.info("Applied search filters: %s", search_kwargs["filter"])
    LOG.info("Search kwargs configured: %s", search_kwargs)

    # ---------------------------------------------------------------------------
    # LLM setup
    # ---------------------------------------------------------------------------
    llm = get_llm_chat()

    # ---------------------------------------------------------------------------
    # Retriever configuration
    # ---------------------------------------------------------------------------
    retriever = get_retriever(search_kwargs=search_kwargs, search_type="mmr")

    # ---------------------------------------------------------------------------
    # RAG prompt template
    # ---------------------------------------------------------------------------
    prompt_template = """
You are a scholar of the works of Jacques Derrida.

Answer the question based ONLY on the following citations.

REQUIREMENTS:
- Your response MUST have a MINIMUM of {min} sentences.
- Your response MUST have a MAXIMUM of {max} sentences.
- Your response MUST be written in the style of an academic paper with full paragraphs.
- Your response MUST be coherent and well-written.
{also}

Citations:

{context}


Question: {question}

RULES FOR ANSWERING:
- DO NOT PLAGIARIZE.
- DO NOT mention citations that DO NOT support your claims.
- DO base your answer precisely on Derrida's writing and thinking
- DO NOT cite a translator, editor, or author other than Derrida.
    * THIS IS REALLY IMPORTANT: DO NOT CITE OTHERS AS DERRIDA
    * Anything beginning with "TN." or similar is a translator's note!
    * Anyhting in a footnote might be a translator or editor's note!
- DO ground claims in the works cited
    * Check each claim against the cited work
- DO NOT invent data, like publication dates, page numbers, etc.
    * Only refer to your actual sources
- DO CHOOSE ONE MAJOR CLAIM TO MAKE. DO NOT CLAIM TOO MUCH.
"""

    if not (args.cheat):
        prompt_template += """
- DO back up every claim you make with a citation from the provided texts
- Use MLA-like citation format where possible (Author, Title, Page #)
- DO clean up typos/artifacts in cited text
- DO NOT repeatedly cite the same source in MLA format
    * If an entire paragraph is mostly one source, just cite it once at the end
- DO NOT say "Based on the provided text" or anything similar in response
- DO NOT misattribute others' thoughts and writing to Derrida
    * e.g., if Derrida is talking about Rousseau, DO NOT misattribute Rousseau's thinking to Derrida
"""
    else:
        prompt_template += """
- DO NOT add direct citations
- DO list unique texts you refer to in a bibliography at the end (MLA style)
"""
        

    prompt = ChatPromptTemplate.from_template(prompt_template)

    # ---------------------------------------------------------------------------
    # Query execution
    # ---------------------------------------------------------------------------
    user_query = args.query
    LOG.info("""
==============================================
|       BEGINNING QUERY EXECUTION            |
==============================================
""")
    LOG.info("Executing query: %s", user_query)


    # ---------------------------------------------------------------------------
    # Smart Natural Language Parser
    # ---------------------------------------------------------------------------



    #llm.invoke("You are a natural language query parser.  You will be given a user query and you will return a JSON object with the following keys: 'term', 'title', 'author', 'is_find_all', and 'specifiers'.  The 'term' key should contain the main term to search for.  The 'title' key should contain the title of the work to filter by, if any.  The 'author' key should contain the author to filter by, if any.  The 'is_find_all' key should be true if the user wants to find all mentions of the term, and false otherwise.  The 'specifiers' key should be a list of any additional keywords or specifiers that can help refine the search.  If any of these keys are not applicable, they should be set to null or an empty list as appropriate.  Return only valid JSON without any additional text or explanation.")

    checker = f"""
QUERY: {user_query}

DO NOT ANSWER THE QUESTION.

YOU MUST RESPOND WITH A SINGLE JSON OBJECT WITH THE FOLLOWING KEY(S) AND NOTHING ELSE:
- 'type': string, either 'textual' or 'factual' based on whether the query is asking for a specific fact or a more general analysis.

A query is considered 'factual' if it is asking for a specific fact that requires no interpretation. A query is considered 'textual' if it is asking for an interpretation, analysis, or discussion, etc.

e.g. '"type": "textual", "reason": "the user is asking about a concept in Derrida's thinking"' or '"type": "factual", "reason": "the user is asking for the date and place of Derrida's birth"'

NOTHING ELSE. NO 'answer' field or any additional fields. RETURN ONLY VALID JSON.  DO NOT RESPOND WITH ANYTHING ELSE.

"""

    query_details = llm.invoke(checker)

    query_details = json.loads(query_details.content)

    LOG.debug(f"The '{CHAT_MODEL}' model thinks this is a {query_details['type']} kind of query")

    if query_details['type'] == "factual":
        LOG.info("Routing query as factual: %s", query_details.get("reason"))

    else:
        LOG.info("Routing query as textual: %s", query_details.get("reason"))

    parsed_intent = parse_natural_language_find_query(user_query)
    
    is_exhaustive = args.find_all or parsed_intent.get("is_find_all", False)

    if (parsed_intent.get("specifiers")):
        specifiers = parsed_intent.get("specifiers")
        LOG.info(f"Query improved with the following keywords: {", ".join(specifiers)}")
        user_query += f"""
KEY WORDS TO INCLUDE IN SEARCH: {", ".join(specifiers)}
"""
    
    if is_exhaustive:
        target_term = args.find_all if args.find_all else parsed_intent.get("term")
        target_title = args.title if args.title else parsed_intent.get("title")
        target_author = args.author if args.author else parsed_intent.get("author")

        LOG.info("Exhaustive search routed -> Term: '%s', Title: '%s', Author: '%s'", 
                 target_term, target_title, target_author)

        if not target_term:
            LOG.warning("Exhaustive search triggered, but no target term could be identified.")
        else:
            collection = vector_store._collection

            meta_filters = {}
            if target_author:
                meta_filters["author"] = target_author
            if target_title:
                meta_filters["source_title"] = target_title
            if args.record_type and args.record_type.lower() != "all":
                meta_filters["record_type"] = args.record_type
            if query_details['type'] == "factual":
                meta_filters["record_type"] = "fact"

            where_clause = None
            if meta_filters:
                if len(meta_filters) == 1:
                    where_clause = meta_filters
                else:
                    where_clause = {"$and": [{k: v} for k, v in meta_filters.items()]}

            query_params = {"where_document": {"$contains": target_term}}
            if where_clause:
                query_params["where"] = where_clause

            results = collection.get(**query_params)
            
            matching_ids = results.get("ids", [])
            metadatas = results.get("metadatas", [])
            documents = results.get("documents", [])
            
            print(f"\n==================================================")
            print(f" MENTIONS OF '{target_term}'" + (f" IN '{target_title}'" if target_title else ""))
            print(f" Total matches found: {len(matching_ids)}")
            print(f"==================================================\n")
            
            if not matching_ids:
                print("No matching occurrences found with the given criteria.")
                return

            for idx, (doc_text, meta) in enumerate(zip(documents, metadatas), start=1):
                author = meta.get("author", "Unknown Author")
                title = meta.get("source_title", "Unknown Title")
                page = meta.get("page_number", "N/A")
                chunk_idx = meta.get("chunk_index", "N/A")
                
                print(f"{idx}. {author}, *{title}*, p. {page} (chunk {chunk_idx})")
                
                lines = doc_text.split('\n')
                snippet = " ".join([line.strip() for line in lines if target_term.lower() in line.lower()])
                if not snippet:
                    snippet = doc_text[:200] + "..."
                print(f"   Excerpt: \"{snippet.strip()}\"\n")
                
            return  # Clean exit

    preferred_source = None

    if args.keyword:
        for keyword, source in keyword_map.items():
            if keyword in user_query.lower():
                LOG.info("KEYWORD '%s' detected. Weighting heavily toward '%s'.", keyword, source)
                preferred_source = source
                break
            matches = difflib.get_close_matches(keyword, user_query, n=1, cutoff=0.75)
            if matches:
                LOG.info("Fuzzy keyword match found: '%s' closely matches '%s'.", matches[0], keyword)
                preferred_source = source
                break        

    if preferred_source and not args.title:
        primary_retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 3, "filter": {"source_title": preferred_source}}
        )
        secondary_retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 2, "filter": {"source_title": {"$ne": preferred_source}}}
        )
        
        primary_docs = primary_retriever.invoke(user_query)
        secondary_docs = secondary_retriever.invoke(user_query)
        retrieved_docs = primary_docs + secondary_docs

    if query_details['type'] == "factual":
        LOG.info("Using factual retriever for query.")
        factual_retriever = vector_store.as_retriever(
            search_kwargs={"k": 5, "filter": {"record_type": "fact"}}
        )
        retrieved_docs = factual_retriever.invoke(user_query)

    else:
        retrieved_docs = retriever.invoke(user_query)

    LOG.info("Retrieved %d documents.", len(retrieved_docs))

    # Deduplicate while preserving rank order
    seen_text = set()
    unique_docs = []
    for doc in retrieved_docs:
        if doc.page_content not in seen_text:
            seen_text.add(doc.page_content)
            unique_docs.append(doc)
    LOG.info("Of these, %d unique documents.", len(unique_docs))

    if not unique_docs:
        LOG.warning("No context found matching the query and filter criteria.")
        print("\n--- No matching results found ---")
        return

    # ---------------------------------------------------------------------------
    # Neighbor Expansion (Group & preserve internal sequence)
    # ---------------------------------------------------------------------------
    LOG.info("Fetching adjacent records for context expansion...")
    
    # We will build list of "grouped" Documents, where each group is merged into one Document
    grouped_documents = []
    collection = vector_store._collection
    total_records = 0

    for doc in unique_docs:
        rec_id = str(doc.metadata.get("record_id", ""))
        
        target_ids = []
        if "-" in rec_id:
            prefix, num_str = rec_id.rsplit("-", 1)
            if num_str.isdigit():
                numeric_id = int(num_str)
                # Build target IDs for 1 before, target, and 1 after
                target_ids = [f"{prefix}-{n}" for n in (numeric_id - 2, numeric_id - 1, numeric_id, numeric_id + 1, numeric_id + 2)]
            else:
                target_ids = [rec_id]
        else:
            target_ids = [rec_id]

        # Query Chroma for these specific adjacent IDs
        result = collection.get(where={"record_id": {"$in": target_ids}})

        if result and result["documents"]:
            # Zip and sort internal records strictly by numeric suffix
            group_records = []
            for r_text, r_meta in zip(result["documents"], result["metadatas"]):
                r_id = str(r_meta.get("record_id", ""))
                try:
                    num = int(r_id.rsplit("-", 1)[1]) if "-" in r_id else 0
                except (ValueError, IndexError):
                    num = 0
                group_records.append((num, r_text, r_meta))

            # SORT WITHIN GROUP: Keep contiguous reading order
            group_records.sort(key=lambda x: x[0])

            # Merge the ordered group records into a single cohesive string
            combined_text = "".join([r[1] for r in group_records])
            
            # Preserve primary document metadata for citations
            primary_meta = doc.metadata.copy()

            total_records = total_records + len(group_records)
            
            grouped_documents.append(
                Document(page_content=combined_text, metadata=primary_meta)
            )

    LOG.info("Created %d contiguous group blocks of %d records.", len(grouped_documents), total_records)

    # ---------------------------------------------------------------------------
    # Reorder GROUPS to optimize LLM attention
    # ---------------------------------------------------------------------------
    LOG.info("Reordering context groups with LongContextReorder...")
    reordering = LongContextReorder()
    reordered_groups = reordering.transform_documents(grouped_documents)

    # Format retrieved context with source citations
    context_str = "\n\n---\n\n".join(
        [
            f"[**{doc.metadata.get('source_title')}** by {doc.metadata.get('author')}, p. {doc.metadata.get('page_number')}]\n{doc.page_content}"
            for doc in reordered_groups
        ]
    )

    # Generate response
    LOG.info("Generating response with LLM.")
    final_prompt = prompt.format(context=context_str, question=user_query, also=args.also, min=args.min, max=args.max)
    LOG.info(f"Final prompt built: \n{final_prompt}")
    response = llm.invoke(final_prompt)
    LOG.info("LLM finished generating response.")

    if (args.thorough):
        LOG.info("Double-checking in thorough mode...")
        thorough_prompt = """
You are an academic scholar of Derrida and post-structuralism.
You are an editor for academic papers.

REQUIREMENTS:
    - Examine, below, the response to the prompt for clarity, accuracy, and thoroughness.
    - Make sure there are no misattributed ideas or fake citations.
    - Fix typos and other artifacts.
    - Structure it like an article/essay.
    - DO NOT add subheadings.
    - DO NOT remove page number/citations

GOAL:
    - Improve the response as needed, then respond with ONLY the improved response.
    - Below the response append a brief DEBUG section with any changes you made during generation to improve the result
        * For each change, provide the a/b diff
        * At very end, add your CONFIDENCE SCORE (out of 100%) signaling your confidence in your accuracy as a Derridean scholar

Prompt: {prompt}

Response: {response}
""".format(prompt=args.query, response=response)
        response = llm.invoke(thorough_prompt)

    if (args.bibliography):
        LOG.info("Adding bibliography...")
        bibliography_prompt = """
You are an academic scholar of Derrida and post-structuralism.
You are an editor for academic papers.

REQUIREMENTS:
    - DO identify every unique source in this text and add a corresponding Works Cited section at the bottom
    - DO follow MLA standards or citation format, e.g. when citing directly or indirectly use the inline (Work, Page #) format.
    - DO inline footnotes to the text that correspond to works cited.
        * e.g., "Derrida called Cheetos 'tasty' (Of Grammatology, 20)[1]."
    - DO NOT remove page numbers unless they are incorrect.

EXAMPLE:

    Derrida felt that the Beach Boys were "too good to be true" (Dissemination 54).[3]

    WORKS CITED

    1. ...
    2. ...
    3. Derrida, Jacques. Dissemination. University of Bucko Press, 1995.

TEXT:

{response}
""".format(response=response)
    LOG.info(f"Final prompt after bibliography added: {response}")
    response = llm.invoke(bibliography_prompt)


    print(f"\n--- Answer from {CHAT_MODEL} ---")
    print(response.content)

if __name__ == "__main__":
    main()