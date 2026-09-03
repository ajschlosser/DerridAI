import asyncio
import os
import time
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from sentence_transformers import CrossEncoder
from typing import TypedDict
from schemas.schemas import RAGSearchTypes, Languages
import logging
LOG = logging.getLogger(__name__)

DEFAULT_CHAT_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://host.docker.internal:11434",
)
DEFAULT_EMBEDDING_MODEL = os.getenv(
    "DERRIDAI_DEFAULT_EMBEDDING_MODEL",
    "bge-m3:latest",
)
DEFAULT_CROSS_ENCODER = os.getenv(
    "DERRIDAI_DEFAULT_CROSS_ENCODER",
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
)

DEFAULT_STORE_PERSIST_DIRECTORY = os.getenv(
    "DERRIDAI_DEFAULT_STORE_PERSIST_DIRECTORY",
    "./data/stores/chroma_db_local-derrida9"
)
DEFAULT_K_VALUE = int(os.getenv("DERRIDAI_DEFAULT_K_VALUE", 64))
DEFAULT_FETCH_K_VALUE = int(os.getenv("DERRIDAI_DEFAULT_FETCH_K_VALUE", 500))
DEFAULT_LAMBDA_MULT_VALUE = float(os.getenv("DERRIDAI_DEFAULT_LAMBDA_MULT_VALUE", 0.7))

MAX_CONCURRENT_GENERATIONS = 2

class RAGSimilarityFilter(TypedDict):
    k: int

class RAGMMRFilter(RAGSimilarityFilter):
    k: int
    fetch_k: int
    lambda_mult: float

class RAGClient:
    embeddings: OllamaEmbeddings
    stores: dict[str, Chroma] = {}
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    persist_directory: str = DEFAULT_STORE_PERSIST_DIRECTORY
    server_url: str = DEFAULT_CHAT_BASE_URL
    cross_encoder: str = DEFAULT_CROSS_ENCODER
    reranker: CrossEncoder = CrossEncoder(DEFAULT_CROSS_ENCODER)
    default_mmr_filter: RAGMMRFilter
    default_similarity_filter: RAGSimilarityFilter
    def __init__(self,
        default_k_value: int = DEFAULT_K_VALUE,
        default_fetch_k_value: int = DEFAULT_FETCH_K_VALUE,
        default_lambda_mult_value: float = DEFAULT_LAMBDA_MULT_VALUE,
    ):
        self.default_k_value = default_k_value
        self.default_fetch_k_value = default_fetch_k_value
        self.default_lambda_mult_value = default_lambda_mult_value
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

        self.default_mmr_filter: RAGMMRFilter = {
            "k": self.default_k_value,
            "fetch_k": self.default_fetch_k_value,
            "lambda_mult": self.default_lambda_mult_value,
        }
        self.default_similarity_filter: RAGSimilarityFilter = {
            "k": self.default_k_value,
        }

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
            return self.stores[key]
        return self.store("defaults")

    def basic_lookup(
        self,
        invocation_str: str | dict[str, str],
        mmr_filter: RAGMMRFilter | None = None,
        similarity_filter: RAGSimilarityFilter | None = None,
        search_types: list[RAGSearchTypes] = [RAGSearchTypes.MMR, RAGSearchTypes.SIMILARITY],
        languages: list[Languages] = [Languages.ENGLISH, Languages.FRENCH],
        split: bool = True,
    ) -> list[Document]:
        start_time = time.perf_counter()
        mmr_filter = mmr_filter if mmr_filter else self.default_mmr_filter
        similarity_filter = similarity_filter if similarity_filter else self.default_similarity_filter
        all_results = []
        # TODO: Implement any preprocessing or adjustments to the filters based on the split flag
        # if split:
        #     mmr_filter["k"] = mmr_filter["k"] // 2
        #     similarity_filter["k"] = similarity_filter["k"] // 2
        for search_type in search_types:
            for lang in languages:
                LOG.debug(f"Starting search for type: {search_type} in language: {lang}")                
                retriever = self.store(f"primary_{lang}").as_retriever(
                    search_kwargs=mmr_filter if search_type == "mmr" else similarity_filter,
                    search_type=search_type,
                )
                LOG.debug(f"Invoking {search_type} retriever with query: {invocation_str}")
                if isinstance(invocation_str, dict):
                    invocation_str = invocation_str.get(str(lang), "")
                results = retriever.invoke(invocation_str)
                LOG.debug(f"Total {search_type} results: {len(results)}")
                all_results += results
        LOG.debug("Basic lookup completed in %.4f seconds", time.perf_counter() - start_time)
        return all_results

    def rerank_documents(self,
            query: str = "",
            docs: list[dict] = [],
            reranker: CrossEncoder | None = None,
            top_n: int | None = None
    ) -> list[dict]:
        start = time.perf_counter()
        reranker = reranker if reranker else self.reranker

        def str_cast(doc):
            if hasattr(doc, "page_content"):
                return doc.page_content
            else:
                return doc

        pairs: list[list[str | dict]] = [
            [query, str_cast(doc)]
            for doc in docs
        ]
        scores = reranker.predict(pairs)
        ranked_indices: list[int] = sorted(
            range(len(docs)),
            key=lambda i: float(scores[i]),
            reverse=True
        )
        idx = min(top_n if top_n else len(docs), len(docs))
        LOG.debug("Reranking completed in %.2f seconds", time.perf_counter() - start)
        return [docs[i] for i in ranked_indices[:idx]]