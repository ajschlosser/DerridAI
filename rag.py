#!/usr/bin/env python3
"""rag.py – Retrieval‑augmented generation demo with progress logs.

"""

import os
import json
import logging
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama

EMBEDDING_MODEL="nomic-embed-text"
CHAT_MODEL="qwen3.5:4b"
CHAT_TEMPERATURE=0.2
OLLAMA_SERVER_URL="http://localhost:11434"
DB_PATH="./chroma_db_local"
SOURCE_TEXT="./data/grammatology-pruned.jsonl"

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
# Load data
# ---------------------------------------------------------------------------

docs = load_jsonl_to_docs(SOURCE_TEXT)
# Extract primary record IDs to enforce uniqueness in Chroma
doc_ids = [doc.metadata["record_id"] for doc in docs]
LOG.info("Finished loading documents.")

# ---------------------------------------------------------------------------
# Embedding model
# ---------------------------------------------------------------------------
LOG.info(f"Loading embedding model {EMBEDDING_MODEL}.")
embeddings = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=OLLAMA_SERVER_URL,  # Adjust if running on a remote port/host
)

# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------

if os.path.exists(DB_PATH) and os.listdir(DB_PATH):
    LOG.info("Loading existing vector store from '%s'...", DB_PATH)
    vector_store = Chroma(
        persist_directory=DB_PATH,
        embedding_function=embeddings
    )
    LOG.info("Vector store loaded.")
else:
    LOG.info("Creating vector store with %d documents.", len(docs))
    vector_store = Chroma.from_documents(
        documents=docs, embedding=embeddings, persist_directory=DB_PATH, ids=doc_ids
    )
    LOG.info("Vector store created.")

# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------
LOG.info(f"Initializing local LLM '{CHAT_MODEL}'.")
llm = ChatOllama(
    model=CHAT_MODEL,
    base_url=OLLAMA_SERVER_URL,
    temperature=CHAT_TEMPERATURE,  # Low temperature for factual synthesis
)

# ---------------------------------------------------------------------------
# Retriever configuration
# ---------------------------------------------------------------------------
LOG.info("Configuring retriever with k=3 and filter primary_source.")
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3, "filter": {"record_type": "primary_source"}},
)

# ---------------------------------------------------------------------------
# RAG prompt template
# ---------------------------------------------------------------------------
prompt_template = """Answer the question based ONLY on the following citations (note the titles and authors; use MLA citation format where possible):\n\n{context}\n\nQuestion: {question}\nAnswer:"""
prompt = ChatPromptTemplate.from_template(prompt_template)

# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------
user_query = "What is Of Grammatology about?"
LOG.info("Executing query: %s", user_query)
retrieved_docs = retriever.invoke(user_query)
LOG.info("Retrieved %d documents.", len(retrieved_docs))
# Use a set to track seen page content and preserve rank order
seen_text = set()
unique_docs = []
for doc in retrieved_docs:
    if doc.page_content not in seen_text:
        seen_text.add(doc.page_content)
        unique_docs.append(doc)
LOG.info("Of these, %d unique documents.", len(unique_docs))

# Format retrieved context with source citations
context_str = "\n\n".join(
    [
        f"[**{doc.metadata.get('source_title')}** by {doc.metadata.get('author')}, p. {doc.metadata.get('page_number')}]\n{doc.page_content}"
        for doc in unique_docs
    ]
)

# Generate response
LOG.info("Generating response with LLM.")
#$LOG.info(f"Context: {context_str}\nQuestion: {user_query}")
final_prompt = prompt.format(context=context_str, question=user_query)
LOG.info(f"Final prompt: {final_prompt}")
response = llm.invoke(final_prompt)
LOG.info("LLM finished generating response.")

print(f"--- Answer from {CHAT_MODEL} ---")
print(response.content)
