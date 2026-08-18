#!/usr/bin/env python3
"""rag.py – Retrieval‑augmented generation demo with CLI controls and progress logs."""

import os
import json
import logging
import argparse
import shutil
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama

EMBEDDING_MODEL = "nomic-embed-text"
CHAT_MODEL = "gpt-oss:20b"
CHAT_TEMPERATURE = 0.2
OLLAMA_SERVER_URL = "http://localhost:11434"
DB_PATH = "./chroma_db_local-tuned"
SOURCE_TEXT = "./data/derrida.jsonl"
K_VALUE = 3

# Basic log configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
LOG = logging.getLogger("rag")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_jsonl_to_docs(file_path: str) -> list[Document]:
    LOG.info("Loading JSONL documents from %s", file_path)
    documents: list[Document] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            doc = Document(
                page_content=record["text"],
                metadata={"record_id": record["id"], **record["metadata"]},
            )
            documents.append(doc)
    LOG.info("Parsed %d documents.", len(documents))
    return documents

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
    # Vector store setup / rebuild logic
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
        # Only parse JSONL when building/rebuilding DB
        docs = load_jsonl_to_docs(SOURCE_TEXT)
        doc_ids = [doc.metadata["record_id"] for doc in docs]
        LOG.info("Creating vector store with %d documents.", len(docs))
        vector_store = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            persist_directory=DB_PATH,
            ids=doc_ids,  # Enforce uniqueness
        )
        LOG.info("Vector store created.")

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

    search_kwargs = {"k": K_VALUE}
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
        search_type="similarity",
        search_kwargs=search_kwargs,
    )

    # ---------------------------------------------------------------------------
    # RAG prompt template
    # ---------------------------------------------------------------------------
    prompt_template = """
Answer the question based ONLY on the following citations.

- Note the titles and authors
- Use MLA-like citation format where possible (Author, Title, Page #)
- If quoting directly, use proper citation format
    * If you notice ANY typos/errors/artifacts in the quote, fix it
    * If you fix any quotes this way, make note of it in an editor's note
- Don't say "Based on the provided text" or anything similar in response
- Minimum of 5 sentences.

Citations:

{context}


Question: {question}
"""
    prompt = ChatPromptTemplate.from_template(prompt_template)

    # ---------------------------------------------------------------------------
    # Query execution
    # ---------------------------------------------------------------------------
    user_query = args.query
    LOG.info("Executing query: %s", user_query)
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

    # Format retrieved context with source citations
    context_str = "\n\n".join(
        [
            f"[**{doc.metadata.get('source_title')}** by {doc.metadata.get('author')}, p. {doc.metadata.get('page_number')}]\n{doc.page_content}"
            for doc in unique_docs
        ]
    )

    # Generate response
    LOG.info("Generating response with LLM.")
    final_prompt = prompt.format(context=context_str, question=user_query)
    LOG.info("Final prompt built.")
    response = llm.invoke(final_prompt)
    LOG.info("LLM finished generating response.")

    print(f"\n--- Answer from {CHAT_MODEL} ---")
    print(response.content)

if __name__ == "__main__":
    main()