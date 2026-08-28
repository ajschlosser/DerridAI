from client import RAG_LLM
from pathlib import Path
import json

from langchain_core.documents import Document

print("Starting")
client = RAG_LLM()
store = client.store("derrida8_primary_fr")

    
def _load_new_records(source_file: Path) -> list[Document]:
    """Return documents from source_file whose IDs are not in Chroma."""
    collection = store._collection
    print("Loading records")
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

    print("Found %d existing records in the database" % len(db_ids))

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
                    **record
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

    print("Found %d new records to index" % len(new_documents))
    return new_documents

new_docs = _load_new_records(Path("./data/derrida8_primary_fr.jsonl"))
total_docs = len(new_docs)

if not new_docs:
    print("No new records found.")
    exit(0)
else:
    print("Found %d new records." % total_docs)

batch_size = 1000
total_indexed = 0
for i in range(0, total_docs, batch_size):
    batch_docs = new_docs[i:i + batch_size]
    batch_ids = [doc.metadata["record_id"] for doc in batch_docs]

    print(f"Indexing batch {i // batch_size + 1}/{(total_docs + batch_size - 1) // batch_size} ({len(batch_docs)} records) {total_indexed}/{total_docs}...")
    store.add_documents(
        documents=batch_docs,
        ids=batch_ids,
    )
    total_indexed += len(batch_docs)
print(f"Total indexed records: {total_indexed}")