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
    parse_natural_language_find_query
)

from models import (
    get_embeddings
)

from store import (
    database_exists,
    delete_vector_store,
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
    if args.force_rebuild:
        delete_vector_store(DB_PATH)

    vector_store = get_store()
    if database_exists(DB_PATH):
        LOG.info("Loading existing vector store from '%s'...", DB_PATH)
        LOG.info("Vector store loaded.")
    else:
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

    author_map = {
        "derrida": "Jacques Derrida",
        "heidegger": "Martin Heidegger"
    }

    detected_author = None
    if not args.author:  # Only auto-detect if user didn't explicitly pass --author via CLI
        for keyword, canonical_author in author_map.items():
            if keyword in args.query.lower():
                detected_author = canonical_author
                LOG.info("Detected author reference '%s'. Automatically filtering search to author: '%s'", keyword, canonical_author)
                break

    # ---------------------------------------------------------------------------
    # Dynamic filter configuration
    # ---------------------------------------------------------------------------
    raw_filters = {}
    if args.record_type and args.record_type.lower() != "all":
        raw_filters["record_type"] = args.record_type
    if args.author:
        raw_filters["author"] = args.author
    # elif detected_author:
    #     raw_filters["author"] = detected_author
    if args.title:
        raw_filters["source_title"] = args.title

    # Clean out any keys with None values
    filter_dict = {k: v for k, v in raw_filters.items() if v is not None}

    search_kwargs = {"k": K_VALUE, "fetch_k": FETCH_K_VALUE, "lambda_mult": LAMBDA_MULT_VALUE}
    
    if filter_dict:
        if len(filter_dict) == 1:
            # Single condition can be passed directly
            search_kwargs["filter"] = filter_dict
        else:
            # Multiple conditions REQUIRE Chroma's explicit $and operator wrapper
            search_kwargs["filter"] = {
                "$and": [{k: v} for k, v in filter_dict.items()]
            }
        LOG.info("Applied search filters: %s", search_kwargs["filter"])

    # ---------------------------------------------------------------------------
    # LLM setup
    # ---------------------------------------------------------------------------
    LOG.info(f"Initializing local LLM '{args.model}'.")
    llm = ChatOllama(
        model=args.model,
        base_url=OLLAMA_SERVER_URL,
        temperature=CHAT_TEMPERATURE,
    )

    # ---------------------------------------------------------------------------
    # Retriever configuration
    # ---------------------------------------------------------------------------
    LOG.info("Configuring retriever with k=%d", K_VALUE)
    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs,
    )

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
    LOG.info("Executing query: %s", user_query)


    # ---------------------------------------------------------------------------
    # Smart Natural Language Parser
    # ---------------------------------------------------------------------------
    parsed_intent = parse_natural_language_find_query(user_query, llm)
    
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

    keyword_map = {
        # Your original entries
        "death": "Gift of Death",
        "presence": "Of Grammatology",
        "Rousseau": "Of Grammatology",
        "differance": "Of Grammatology",
        "différance": "Of Grammatology",
        "'play'": "Structure, Sign, and Play in the Discourse of the Human Sciences",

        # Spectres of Marx
        "Marx": "Spectres of Marx",
        "Marx,": "Spectres of Marx",
        "specter": "Spectres of Marx",
        "spectres": "Spectres of Marx",
        "ghost": "Spectres of Marx",
        "haunt": "Spectres of Marx",
        "haunting": "Spectres of Marx",
        "hauntology": "Spectres of Marx",
        "messianism": "Spectres of Marx",
        "messianic": "Spectres of Marx",
        "inheritance": "Spectres of Marx",
        "democracy": "Spectres of Marx",
        "democrat": "Spectres of Marx",
        "globalization": "Spectres of Marx",
        "capital": "Spectres of Marx",
        "capitalism": "Spectres of Marx",
        "spirit": "Spectres of Marx",

        # Monolingualism of the Other; or, The Prosthesis of Origin
        "language": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "linguistic": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "monolingualism": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "monolingual": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "other": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "translation": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "translating": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "foreign": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "mother tongue": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "mother-tongue": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "tongue": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "writing": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "bilingual": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "bilingualism": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "idiom": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "accent": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "colonial": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "colonialism": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "algeria": "Monolingualism of the Other; or, The Prosthesis of Origin",
        "france": "",

        # Writing and Difference
        "difference": "Writing and Difference",
        "trace": "Writing and Difference",
        "grammatology": "Writing and Difference",
        "structure": "Writing and Difference",
        "sign": "Writing and Difference",
        "signification": "Writing and Difference",
        "text": "Writing and Difference",
        "textual": "Writing and Difference",
        "iterability": "Writing and Difference",
        "supplement": "Writing and Difference",
        "archive": "Writing and Difference",
        "mimesis": "Writing and Difference",
        "iterable": "Writing and Difference",

        # (kept from your earlier map additions)
        "différance": "Writing and Difference",
        "differance": "Writing and Difference",

        # Dissemination
        "dissemination": "Dissemination",
        "disseminate": "Dissemination",
        "dispersal": "Dissemination",
        "sprouting": "Dissemination",
        "polysemy": "Dissemination",
        "ambiguity": "Dissemination",
        "equivocation": "Dissemination",
        "equivocal": "Dissemination",
        "multiplicity": "Dissemination",
        "plurality": "Dissemination",
        "refraction": "Dissemination",
        "scatter": "Dissemination",
        "spreading": "Dissemination",
        "propagation": "Dissemination",
        "relay": "Dissemination",
        "absence": "Dissemination",
        "permutation": "Dissemination",

        # Signature phrase labels you started with
        "play": "Structure, Sign, and Play in the Discourse of the Human Sciences",
        "structure, sign, and play in the discourse of the human sciences": "Structure, Sign, and Play in the Discourse of the Human Sciences",
        "center": "Structure, Sign, and Play in the Discourse of the Human Sciences",
        "decentering": "Structure, Sign, and Play in the Discourse of the Human Sciences",
        "event": "Structure, Sign, and Play in the Discourse of the Human Sciences",
        "bricolage": "Structure, Sign, and Play in the Discourse of the Human Sciences",
        "structure": "Writing and Difference",  # note: overwrites above if you kept both
        "sign": "Writing and Difference",       # note: overwrites above if you kept both
        "text": "Writing and Difference",

        # Glas
        "glas": "Glas",
        "glasses": "Glas",
        "margins": "Glas",
        "margin": "Glas",
        "page": "Glas",
        "colophon": "Glas",
        "column": "Glas",
        "columns": "Glas",
        "name": "Glas",
        "names": "Glas",
        "proper name": "Glas",
        "monument": "Glas",
        "epitaph": "Glas",
        "eulogy": "Glas",
        "father": "Glas",
        "son": "Glas",
        "Hegel": "Glas",
        "Genet": "Glas",
        "blanchot": "Glas",
        "mourning": "Glas",
        "death": "Glas",  # if you want “death” to hit Glas too; otherwise remove

        # Margins of Philosophy
        "margins of philosophy": "Margins of Philosophy",
        "margins": "Margins of Philosophy",
        "margin": "Margins of Philosophy",
        "philosophy": "Margins of Philosophy",
        "outside": "Margins of Philosophy",
        "outside the text": "Margins of Philosophy",
        "edge": "Margins of Philosophy",
        "border": "Margins of Philosophy",
        "threshold": "Margins of Philosophy",
        "limit": "Margins of Philosophy",
        "supplement": "Margins of Philosophy",
        "writing": "Margins of Philosophy",
        "text": "Margins of Philosophy",
        "commentary": "Margins of Philosophy",
        "comment": "Margins of Philosophy",
        "gloss": "Margins of Philosophy",
        "translation": "Margins of Philosophy",
        "method": "Margins of Philosophy",
        "metaphysics": "Margins of Philosophy",
        "deconstruction": "Margins of Philosophy",
        "deconstruct": "Margins of Philosophy",
        "interruption": "Margins of Philosophy",
        "rupture": "Margins of Philosophy",
        "rhetoric": "Margins of Philosophy",
        "style": "Margins of Philosophy"
    }
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