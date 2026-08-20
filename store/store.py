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

"""store.py – Vector store utilities for the DerridAI RAG project.

This module provides a thin wrapper around a :class:`langchain_chroma.Chroma`
instance that is shared throughout the code base.  The module is intentionally
light‑weight: it only exposes a single global store object and helper
functions for deleting the backing database and checking its existence.

The functions are annotated with type hints and include logging statements
to aid debugging.  All loggers are acquired from the project‑wide logging
facility defined in :mod:`src.derrida.logging`.
"""

from importlib.metadata import metadata
import os
import shutil
import json
from pathlib import Path
from helpers import get_logger
from config import DB_PATH, SOURCE_TEXT
from models import get_embeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

LOG = get_logger(__name__)

store = Chroma(
    persist_directory=DB_PATH,
    embedding_function=get_embeddings()
)
records_count = store._collection.count()
LOG.info(f"Vector store with {records_count} records pointed to '{DB_PATH}'.")

def _load_new_records(source_file: Path) -> list[Document]:
    """Return documents from source_file whose IDs are not in Chroma."""
    collection = store._collection

    # Load all existing DB IDs once.
    db_ids = set()
    batch_size = 10_000
    offset = 0

    while True:
        result = collection.get(
            limit=batch_size,
            offset=offset,
            include=[],
        )
        ids = result["ids"]

        if not ids:
            break

        db_ids.update(ids)
        offset += len(ids)

        if len(ids) < batch_size:
            break

    LOG.info("Found %d existing records in the database", len(db_ids))

    # Read JSON records and keep only IDs not already in the DB.
    new_documents = []

    with open(source_file, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            record = json.loads(line)
            if record.get("record_id") is not None:
                record_id = record["record_id"]
                if record_id in db_ids:
                    continue
                metadata = {
                    "text_length": len(record["text"]),
                    "record_id": record_id,
                    "work": record["work"],
                    "document_author": record["document_author"],
                    "edition": record["edition"],
                    "year": record["year"],
                    "page_start": record["page_start"],
                    "page_end": record["page_end"],
                    "region_type": record["region_type"],
                    "region_author": record["region_author"],
                    "primary_text": record["primary_text"],
                    "speaker": record["speaker"],
                    "position_holder": record["position_holder"],
                    "target": record["target"],
                    "discourse_role": record["discourse_role"],
                    "text": record["text"],
                    "concepts": record["concepts"],
                    "persons": record["persons"],
                    "works_referenced": record["works_referenced"],
                    "is_direct_quote": record["is_direct_quote"],
                    "quoted_speaker": record["quoted_speaker"],
                    "attribution_confidence": record["attribution_confidence"],
                    "extraction_quality": record["extraction_quality"]                    
                }
                # Removes [], "", and None
                metadata = {k: v for k, v in metadata.items() if v}
                new_documents.append(
                    Document(
                        page_content=record["text"],
                        metadata=metadata,
                    )
                )
            else:
                record_id = record["id"]
                if record_id in db_ids:
                    continue
                new_documents.append(
                    Document(
                        page_content=record["text"],
                        metadata={
                            "record_id": record_id,
                            **record["metadata"],
                        },
                    )
                )

    LOG.info("Found %d new records to index", len(new_documents))
    return new_documents

def add_new_records() -> None:
    """Load only the records that are not yet indexed and append them."""
    LOG.info("Loading existing records for comparison...")
    new_docs = _load_new_records(Path(SOURCE_TEXT))
    if not new_docs:
        LOG.info("No new records found: vector store already up-to-date.")
        return

    LOG.info("Adding %d new documents to the vector store... be patient...", len(new_docs))
    #vector_store = Chroma(persist_directory=DB_PATH, embedding_function=None)
    store.add_documents(
        documents=new_docs,
        ids=[doc.metadata["record_id"] for doc in new_docs],
    )
    LOG.info("Vector store update complete.")

def delete_vector_store(db_path: str = DB_PATH) -> None:
    """Delete the directory that holds the Chroma vector store.

    Parameters
    ----------
    db_path:
        Path to the directory containing the persistent store.  Defaults to
        :data:`DB_PATH` from :mod:`config`.
    """
    if os.path.exists(db_path):
        LOG.info("Deleting vector store at '%s'...", db_path)
        shutil.rmtree(db_path)
    else:
        LOG.warning("Cannot delete a vector store at '%s' that does not exist!", db_path)

def database_exists(db_path: str = DB_PATH) -> bool:
    """Return ``True`` if the persistent store directory exists and is not empty.

    This helper is used by other modules to decide whether to rebuild the
    vector store from scratch.
    """
    return os.path.exists(db_path) and os.listdir(db_path)

def get_store() -> Chroma:
    """Return the global :class:`Chroma` store instance.

    The store is created at module import time and is reused throughout the
    application.  Keeping a single shared instance simplifies lifecycle
    management and avoids unnecessary disk I/O.
    """
    return store

def get_retriever(search_kwargs: dict[str, any], search_type: str = "mmr") -> Chroma:
    LOG.info("Configuring retriever with search_type='%s' and search_kwargs=%s", search_type, search_kwargs)
    return store.as_retriever(
        search_type=search_type,
        search_kwargs=search_kwargs,
    )

LOG.info("Looking for new records...")
add_new_records()  # Ensure the store is up-to-date at startup