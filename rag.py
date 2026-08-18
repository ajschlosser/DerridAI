#!/usr/bin/env python3
"""rag.py – Retrieval‑augmented generation demo with CLI controls and progress logs."""

import os
import json
import logging
import argparse
import shutil
import difflib
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.document_transformers import LongContextReorder

EMBEDDING_MODEL = "nomic-embed-text"
CHAT_MODEL = "gpt-oss:20b"
CHAT_TEMPERATURE = 0.2
OLLAMA_SERVER_URL = "http://localhost:11434"
DB_PATH = "./chroma_db_local-tuned"
SOURCE_TEXT = "./data/derrida3.jsonl"
BATCH_SIZE = 1500  # Prevents Ollama tokenizer OOM crashes
K_VALUE = 3
FETCH_K_VALUE = 30
LAMBDA_MULT_VALUE = 0.5

# Basic log configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
LOG = logging.getLogger("rag")

# ---------------------------------------------------------------------------
# Main Routine
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="RAG Pipeline for Philosophical Texts")
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default="What does Derrida say about presence?",
        help="Question to ask the RAG pipeline.",
    )
    parser.add_argument(
        "--author",
        type=str,
        help="Filter search by author (e.g. 'Jacques Derrida').",
    )
    parser.add_argument(
        "--title",
        type=str,
        help="Filter search by source title (e.g. 'Of Grammatology').",
    )
    parser.add_argument(
        "--record-type",
        type=str,
        default="primary_source",
        help="Filter search by record_type (default: 'primary_source'). Pass 'all' to disable filter.",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild the Chroma vector store from JSONL source data.",
    )
    parser.add_argument(
        "--cheat",
        default=False,
        type=bool,
        help="Whether or not to cite sources."
    )
    parser.add_argument(
        "--keyword",
        default=False,
        type=bool,
        help="Whether or not certain keywords give weight to certain texts."
    )
    parser.add_argument(
        "--min",
        default=5,
        type=int,
        help="Minimum number of sentences in response."
    )
    parser.add_argument(
        "--max",
        default=5,
        type=int,
        help="Maximum number of sentences in response."
    )
    parser.add_argument(
        "--also",
        default="- You must double-check your work at the end.",
        type=str,
        help="Any additional wording to add to the prompt."
    )
    args = parser.parse_args()

    # ---------------------------------------------------------------------------
    # Embedding model
    # ---------------------------------------------------------------------------
    LOG.info(f"Loading embedding model {EMBEDDING_MODEL}.")
    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_SERVER_URL,
        keep_alive="-1",  # Keep in memory to eliminate cold-start latency
    )

    # ---------------------------------------------------------------------------
    # Vector store setup / rebuild logic (Batched & Streamed)
    # ---------------------------------------------------------------------------
    if args.force_rebuild and os.path.exists(DB_PATH):
        LOG.info("Force rebuild requested. Removing existing database at '%s'...", DB_PATH)
        shutil.rmtree(DB_PATH)

    if os.path.exists(DB_PATH) and os.listdir(DB_PATH):
        LOG.info("Loading existing vector store from '%s'...", DB_PATH)
        vector_store = Chroma(
            persist_directory=DB_PATH,
            embedding_function=embeddings
        )
        LOG.info("Vector store loaded.")
    else:
        LOG.info("Initializing new Chroma database at '%s'...", DB_PATH)
        vector_store = Chroma(
            persist_directory=DB_PATH,
            embedding_function=embeddings
        )
        
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
    filter_dict = {}
    if args.record_type and args.record_type.lower() != "all":
        filter_dict["record_type"] = args.record_type
    if args.author:
        filter_dict["author"] = args.author
    if args.title:
        filter_dict["source_title"] = args.title

    search_kwargs = {
        "k": K_VALUE,
        "fetch_k": FETCH_K_VALUE,
        "lambda_mult": LAMBDA_MULT_VALUE
    }
    if filter_dict:
        search_kwargs["filter"] = filter_dict
        LOG.info("Applied search filters: %s", filter_dict)

    # ---------------------------------------------------------------------------
    # LLM setup
    # ---------------------------------------------------------------------------
    LOG.info(f"Initializing local LLM '{CHAT_MODEL}'.")
    llm = ChatOllama(
        model=CHAT_MODEL,
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
- Base your answer precisely on Derrida's writing and thinking
- DO NOT PLAGIARIZE. DOUBLE CHECK.
- DO ensure that you are not citing a translator, editor, or author other than Derrida.
    * THIS IS REALLY IMPORTANT: DO NOT CITE OTHERS AS DERRIDA
    * Anything beginning with "TN." or similar is a translator's note!
    * Anyhting in a footnote might be a translator or editor's note!
"""

    if not (args.cheat):
        prompt_template += """
- Use MLA-like citation format where possible (Author, Title, Page #)
- DO clean up typos/artifacts in cited text
- DO NOT say "Based on the provided text" or anything similar in response
- DO make sure you are CORRECTLY attributing thoughts and ideas to Derrida
- DO NOT misattribute others' thoughts and writing to Derrida
    * e.g., if Derrida is talking about Rousseau, DO NOT misattribute Rousseau's thinking to Derrida
"""
    else:
        prompt_template += "- DO NOT add direct citations, but you can mention texts you refer to"
        

    prompt = ChatPromptTemplate.from_template(prompt_template)

    # ---------------------------------------------------------------------------
    # Query execution
    # ---------------------------------------------------------------------------
    user_query = args.query
    LOG.info("Executing query: %s", user_query)
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
        "france": "Monolingualism of the Other; or, The Prosthesis of Origin",

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
            search_kwargs={"k": 1, "filter": {"source_title": preferred_source}}
        )
        secondary_retriever = vector_store.as_retriever(
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
            combined_text = "\n\n".join([r[1] for r in group_records])
            
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

    print(f"\n--- Answer from {CHAT_MODEL} ---")
    print(response.content)

if __name__ == "__main__":
    main()