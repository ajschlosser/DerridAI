import sys
import os
# Add the project root to the python path
# This allows us to import 'api' and 'utils' correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import json
from langchain_chroma import Chroma
from langchain_core.documents import Document

DEFAULT_EMBEDDING_MODEL = "bge-m3:latest"

from langchain_ollama import OllamaEmbeddings

embeddings = OllamaEmbeddings(
    model=DEFAULT_EMBEDDING_MODEL,
    base_url="http://localhost:11434",
)

test_embedding = embeddings.embed_query("test")
print(f"DEBUG: Current embedding dimension: {len(test_embedding)}")

client = Chroma(
    persist_directory="../data/stores/chroma_db_local-derrida9_new_primary_en",
    embedding_function=embeddings,
)
collection = client._collection

def sync_jsonl_to_db(jsonl_path):
    batch_size = 1000  # Adjust based on your average record size
    batch_ids = []
    batch_metadatas = []
    batch_docs = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            record_id = data.get("record_id")
            if not record_id:
                print(f"Warning: Skipping line without record_id: {line[:50]}...")
                continue
            print(f"Syncing record_id: {record_id} to ChromaDB...")
            metadata = {
                "text_length": len(data["text"]),
                **data,
            }
            metadata = {k: v for k, v in metadata.items() if v}
            batch_ids.append(record_id)
            batch_metadatas.append(metadata)
            batch_docs.append(data.get("text", ""))
            doc =  Document(
                page_content=data["text"],
                metadata=metadata,
            )

            if len(batch_ids) >= batch_size:
                print(f"Uploaded batch of {len(batch_ids)} records.")
                collection.upsert(
                    ids=batch_ids,
                    metadatas=batch_metadatas,
                    documents=batch_docs
                )
                batch_ids = []
                batch_metadatas = []
                batch_docs = []
    # Insert any remaining records that didn't fill up the last batch
    if batch_ids:
        collection.upsert(
            ids=batch_ids,
            metadatas=batch_metadatas,
            documents=batch_docs
        )
        print(f"Uploaded final batch of {len(batch_ids)} records.")
    print("Sync complete.")
    exit(0)

#sync_jsonl_to_db("../data/base/derrida9_new_primary_fr.jsonl")

def sync_single_record_to_db(jsonl_path, target_record_id):
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            record_id = data.get("record_id")
            if record_id == target_record_id:
                print(f"Syncing record_id: {record_id} to ChromaDB...")
                metadata = {
                    "text_length": len(data["text"]),
                    **data,
                }
                metadata = {k: v for k, v in metadata.items() if v}
                doc =  Document(
                    page_content=data["text"],
                    metadata=metadata,
                )
                collection.upsert(
                    ids=[record_id],
                    metadatas=[metadata],
                    documents=[data.get("text", "")]
                )
                print(f"Record {record_id} synced successfully.")
                return
        print(f"Record {target_record_id} not found in the JSONL file.")

sync_single_record_to_db("../data/base/derrida7_ids.jsonl", "derrida-signature-derrida-01446")