from logger import Logger

# STANDARD LIBRARIES
import json

# LLM
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.documents import Document
from langchain_chroma import Chroma
from pathlib import Path

# TYPING
from typing import Optional

from typings import (
    LangChainConfig
)

from defaults import (
    BATCH_SIZE, 
    SOURCE_TEXT,
)

LOG = Logger.setup()

# LANGCHAIN CLIENT WRAPPER
class LangChainClient:
    """
    A thin wrapper that builds a LangChain chat model, an embeddings model,
    and a Chroma vector store based on a user‑supplied configuration.

    Parameters
    ----------
    config : Optional[LangChainConfig] = None
        A typed configuration object.  If omitted, defaults from the module
        constants are used.
    """
    def __init__(self, config: Optional[LangChainConfig] = None):
        cfg = config or LangChainConfig.from_defaults()
        LOG.info("Initializing LangChainClient with configuration: %s", cfg)
        LOG.info(f"""\n
=================
| CONFIGURATION |
=================
MODEL: {cfg.chat.model}
TEMPERATURE: {cfg.chat.temperature}
BASE_URL: {cfg.chat.base_url}
EMBEDDING_MODEL: {cfg.embedding.model}
DB_PATH: {cfg.store.persist_directory}
        """)
        self.chat_model = ChatOllama(
            model=cfg.chat.model,
            temperature=cfg.chat.temperature,
            base_url=cfg.chat.base_url,
            timeout=45.0, # 45s
        )
        self.embedding_model = OllamaEmbeddings(
            model=cfg.embedding.model,
            base_url=cfg.embedding.base_url,
        )
        self.vector_store = Chroma(
            persist_directory=cfg.store.persist_directory,
            embedding_function=self.embedding_model,
        )
        LOG.info("LangChainClient initialized successfully.")
    def invoke(self, prompt: str):
        LOG.info(f"Invoking chat model [{self.chat_model.model}] with prompt: {prompt}")
        return self.chat_model.invoke(prompt)
    def create_retriever(self, search_kwargs: dict, search_type: str = "mmr"):
        LOG.info(f"Creating retriever with search_kwargs: {search_kwargs} and search_type: {search_type}")
        self.retrievers = getattr(self, "retrievers", [])
        retriever = self.vector_store.as_retriever(search_kwargs=search_kwargs, search_type=search_type)
        self.retrievers.append(retriever)
        return retriever
    def _load_new_records(self, source_file: Path) -> list[Document]:
        """Return documents from source_file whose IDs are not in Chroma."""
        collection = self.vector_store._collection

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

        LOG.info("Found %d new records to index", len(new_documents))
        return new_documents

    def add_new_records(self, batch_size: int = BATCH_SIZE) -> None:
        """Load only the records that are not yet indexed and append them in batches."""
        LOG.info("Loading existing records for comparison...")
        new_docs = self._load_new_records(Path(SOURCE_TEXT))
        if not new_docs:
            LOG.info("No new records found: vector store already up-to-date.")
            return

        total_docs = len(new_docs)
        LOG.info("Adding %d new documents to the vector store in batches of %d...", total_docs, batch_size)

        for i in range(0, total_docs, batch_size):
            batch_docs = new_docs[i:i + batch_size]
            batch_ids = [doc.metadata["record_id"] for doc in batch_docs]
            
            LOG.info(f"Indexing batch {i // batch_size + 1}/{(total_docs + batch_size - 1) // batch_size} ({len(batch_docs)} records)...")
            self.vector_store.add_documents(
                documents=batch_docs,
                ids=batch_ids,
            )

        LOG.info("Vector store update complete.")
