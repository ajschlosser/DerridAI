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
from typing import Callable, Optional

from typings import (
    LangChainConfig,
    StoreConfig,
)

from defaults import (
    BATCH_SIZE, 
    SOURCE_TEXT,
)

LOG = Logger.setup()

pipeline_id = 0

# class Store:
#     def __init__(self, config: Options[StoreConfig] ):
#         self.persist_directory = persist_directory

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
        self.vector_store_primary_en = Chroma(
            persist_directory=cfg.store.persist_directory + '_derrida8_primary_en',
            embedding_function=self.embedding_model,
        )
        self.vector_store_primary_fr = Chroma(
            persist_directory=cfg.store.persist_directory + '_derrida8_primary_fr',
            embedding_function=self.embedding_model,
        )
        self.response_vector_store = Chroma(
            persist_directory=cfg.store.persist_directory + '_responses',
            embedding_function=self.embedding_model,
        )
        LOG.info("LangChainClient initialized successfully.")

    def invoke(self, prompt: str):
        LOG.info(f"Invoking chat model [{self.chat_model.model}] with prompt")
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

    def add_record_to_response_store(self, record: dict) -> None:
        """Add a single record to the response vector store."""
        LOG.info("Adding record to response store: %s", record)
        collection_length = len(self.response_vector_store._collection.get()["ids"])
        record["metadata"]["record_id"] = str(collection_length + 1)
        self.response_vector_store.add_documents(
            documents=[Document(
                page_content=record["text"],
                metadata=record["metadata"],
            )],
            ids=[str(collection_length + 1)],
        )

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

DEFAULT_CHAT_MODEL = "phi4:14b"
DEFAULT_CHAT_TEMPERATURE = 0.4
DEFAULT_CHAT_BASE_URL = "http://localhost:11434"
DEFAULT_CHAT_TIMEOUT = 45.0
DEFAULT_EMBEDDING_MODEL = "bge-m3:latest"
DEFAULT_STORE_PERSIST_DIRECTORY = "./chroma_db_local7"

embeddings = OllamaEmbeddings(
    model=DEFAULT_EMBEDDING_MODEL,
    base_url=DEFAULT_CHAT_BASE_URL,
)

class RAG_LLM:
    chats = {}
    embeddings = {}
    stores = {}
    key = "defaults"
    def __init__(self):
        self.chats["defaults"] = ChatOllama(
            model=DEFAULT_CHAT_MODEL,
            temperature=DEFAULT_CHAT_TEMPERATURE,
            base_url=DEFAULT_CHAT_BASE_URL,
            timeout=DEFAULT_CHAT_TIMEOUT,
        )
        self.stores["defaults"] = Chroma(
            persist_directory=DEFAULT_STORE_PERSIST_DIRECTORY,
            embedding_function=embeddings,
        )

    def switch(self, key: str):
        self.key = key

    def chat(self, key: str = None):
        return self.chats[key if key else self.key]

    def store(self, key: str = None):
        key = key if key else self.key
        store = self.stores.get(key, None)
        if store:
            return store
        elif key:
            self.stores[key] = Chroma(
                persist_directory=f"{DEFAULT_STORE_PERSIST_DIRECTORY}_{key}",
                embedding_function=embeddings,
            )
            self.key = key
            return self.stores[key]
    def embeddings(self, key: str = None):
        return embeddings