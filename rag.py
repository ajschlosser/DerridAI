#!/usr/bin/env python3
"""rag.py – Retrieval‑augmented generation demo with progress logs.

This version adds `logging` statements (INFO level) to reveal the
progress of data loading, model initialisation, vector‑store creation
and query generation.  Existing behaviour is untouched – only log
messages are emitted.
"""

import json
import logging
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama

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

docs = load_jsonl_to_docs("./data/grammatology.jsonl")
LOG.info("Finished loading documents.")

# ---------------------------------------------------------------------------
# Embedding model
# ---------------------------------------------------------------------------
LOG.info("Loading embedding model 'gpt-oss:20b'.")
embeddings = OllamaEmbeddings(
    model="gpt-oss:20b",
    base_url="http://localhost:11434",  # Adjust if running on a remote port/host
)

# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------
LOG.info("Creating vector store with %d documents.", len(docs))
vector_store = Chroma.from_documents(
    documents=docs, embedding=embeddings, persist_directory="./chroma_db_local"
)
LOG.info("Vector store created.")

# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------
LOG.info("Initializing local LLM 'gpt-oss:20b'.")
llm = ChatOllama(
    model="gpt-oss:20b",
    base_url="http://localhost:11434",
    temperature=0.2,  # Low temperature for factual synthesis
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
prompt_template = """Answer the question based ONLY on the following philosophical context:\n\n{context}\n\nQuestion: {question}\nAnswer:"""
prompt = ChatPromptTemplate.from_template(prompt_template)

# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------
user_query = "How does Derrida view Rousseau's understanding of formal composition vs sensory content?"
LOG.info("Executing query: %s", user_query)
retrieved_docs = retriever.invoke(user_query)
LOG.info("Retrieved %d documents.", len(retrieved_docs))

# Format retrieved context with source citations
context_str = "\n\n".join(
    [
        f"[{doc.metadata.get('source_title')}, p. {doc.metadata.get('page_number')}]\n{doc.page_content}"
        for doc in retrieved_docs
    ]
)

# Generate response
LOG.info("Generating response with LLM.")
final_prompt = prompt.format(context=context_str, question=user_query)
response = llm.invoke(final_prompt)
LOG.info("LLM finished generating response.")

print("--- Answer from gpt-oss:20b ---")
print(response.content)
