import asyncio
import os
import time
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from sentence_transformers import CrossEncoder
from services import nlp
import logging
LOG = logging.getLogger(__name__)

DEFAULT_CHAT_MODEL = "phi4:14b"
DEFAULT_CHAT_TEMPERATURE = 0.4
DEFAULT_CHAT_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://host.docker.internal:11434",
)
DEFAULT_CHAT_TIMEOUT = 120.0
DEFAULT_EMBEDDING_MODEL = "bge-m3:latest"
DEFAULT_CROSS_ENCODER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_STORE_PERSIST_DIRECTORY = "./data/stores/chroma_db_local-derrida9"
DEFAULT_REASONING_FLAG = False

DEFAULT_K_VALUE = 64
DEFAULT_FETCH_K_VALUE = 500
DEFAULT_LAMBDA_MULT_VALUE = 0.7

MAX_CONCURRENT_GENERATIONS = 2

class RAGClient:
    embeddings: OllamaEmbeddings
    stores: dict[str, Chroma] = {}
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    persist_directory: str = DEFAULT_STORE_PERSIST_DIRECTORY
    server_url: str = DEFAULT_CHAT_BASE_URL
    cross_encoder: str = DEFAULT_CROSS_ENCODER
    reranker: CrossEncoder = CrossEncoder(DEFAULT_CROSS_ENCODER)
    def __init__(self):
        LOG.debug(f"Initializing RAGClient... embedding model: {self.embedding_model} | persist directory: {self.persist_directory} | server url: {self.server_url} | cross encoder: {self.cross_encoder}")
        self.lookup_semaphore = asyncio.Semaphore(
            MAX_CONCURRENT_GENERATIONS
        )
        self.embeddings = OllamaEmbeddings(
            model=self.embedding_model,
            base_url=self.server_url,
        )
        self.stores["defaults"] = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
        )
        self.stores["response_cache"] = Chroma(
            persist_directory=f"{self.persist_directory}_response_cache",
            embedding_function=self.embeddings,
        )

    def get_config_string(self) -> str:
        return f"embedding_model: {self.embedding_model} | persist_directory: {self.persist_directory} | server_url: {self.server_url} | cross_encoder: {self.cross_encoder}"

    def store(self, key: str = "") -> Chroma:
        key = key if key else "defaults"
        store = self.stores.get(key, None)

        # Return the store if it exists
        if store:
            return store

        # Otherwise, create it
        elif key:
            self.stores[key] = Chroma(
                persist_directory=f"{self.persist_directory}_{key}",
                embedding_function=self.embeddings,
            )
            self.key = key
            return self.stores[key]
        return self.store("defaults")

    def basic_lookup(
        self,
        invocation_str: str | dict[str, str],
        mmr_filter: dict = { "k": DEFAULT_K_VALUE, "fetch_k": DEFAULT_FETCH_K_VALUE, "lambda_mult": DEFAULT_LAMBDA_MULT_VALUE },
        similarity_filter: dict = { "k": DEFAULT_K_VALUE },
        search_types: list[str] = ["mmr", "similarity"],
        languages: list[str] = ["en", "fr"],
        split: bool = True,
    ) -> list[Document]:
        start_time = time.perf_counter()
        all_results = []
        if split:
            mmr_filter["k"] = mmr_filter["k"] // 2
            similarity_filter["k"] = similarity_filter["k"] // 2
        for search_type in search_types:
            for lang in languages:
                LOG.debug(f"Starting search for type: {search_type} in language: {lang}")                
                retriever = self.store(f"primary_{lang}").as_retriever(
                    search_kwargs=mmr_filter if search_type == "mmr" else similarity_filter,
                    search_type=search_type,
                )
                LOG.debug(f"Invoking {search_type} retriever with query: {invocation_str}")
                if isinstance(invocation_str, dict):
                    invocation_str = invocation_str.get(lang, "")
                results = retriever.invoke(invocation_str)
                LOG.debug(f"Total {search_type} results: {len(results)}")
                all_results += results
        LOG.debug("Basic lookup completed in %.4f seconds", time.perf_counter() - start_time)
        return all_results