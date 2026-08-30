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

"""db.py -- Ad-hoc ChromaDB exploration: similarity search, MMR, and get() filters.

Run interactively:

    python3 -i db.py

Then use the helpers below, e.g.:

    search("hospitality")
    get(where={"document_language": {"$contains": "fr_fr"}})
    get(where_document={"$contains": "hospitality"})
"""

import json
import argparse
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from defaults import EMBEDDING_MODEL, OLLAMA_BASE_URL

parser = argparse.ArgumentParser(description="DB")
parser.add_argument("-d", "--db", type=str, default="db")

embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)
args = parser.parse_args()
DB_PATH = args.db

vector_store = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
collection = vector_store._collection

print(f"Connected to '{DB_PATH}' ({collection.count()} records).")


def search(query: str, k: int = 10, filter: dict | None = None):
    """Similarity search; returns a list of (Document, score) tuples."""
    return vector_store.similarity_search_with_score(query, k=k, filter=filter)


def mmr(query: str, k: int = 10, fetch_k: int = 50, lambda_mult: float = 0.5, filter: dict | None = None):
    """Maximal marginal relevance search; returns a list of Documents."""
    results = vector_store.max_marginal_relevance_search(
        query, k=k, fetch_k=fetch_k, lambda_mult=lambda_mult, filter=filter
    )
    return results


def get(where: dict | None = None, where_document: dict | None = None, limit: int | None = None):
    """Raw metadata/content filter; returns the {ids, documents, metadatas} dict."""
    return vector_store.get(where=where, where_document=where_document, limit=limit)


def show(results):
    """Pretty-print search() or mmr() results."""
    for item in results:
        doc, score = item if isinstance(item, tuple) else (item, None)
        header = f"[{score:.4f}] " if score is not None else ""
        print(f"{header}{json.dumps(doc.metadata, ensure_ascii=False)[:200]}")
        print(doc.page_content[:300])
        print("-" * 80)


if __name__ == "__main__":
    import code

    banner = (
        "Available: search(query), mmr(query), "
        "get(where=..., where_document=...), show(results)"
    )
    code.interact(banner=banner, local=dict(globals(), **locals()))
