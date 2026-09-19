from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, TypedDict

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from sentence_transformers import CrossEncoder

from schemas.schemas import Languages, RAGSearchTypes
from utils.provenance import deduplicate_documents, filter_documents, lexical_overlap_score

LOG = logging.getLogger(__name__)

DEFAULT_CHAT_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DEFAULT_EMBEDDING_MODEL = os.getenv("DERRIDAI_DEFAULT_EMBEDDING_MODEL", "bge-m3:latest")
DEFAULT_CROSS_ENCODER = os.getenv(
    "DERRIDAI_DEFAULT_CROSS_ENCODER", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
DEFAULT_STORE_PERSIST_DIRECTORY = os.getenv(
    "DERRIDAI_DEFAULT_STORE_PERSIST_DIRECTORY", "./data/stores/chroma_db_local-derrida9"
)
DEFAULT_STORE_COLLECTION_NAME = os.getenv("DERRIDAI_DEFAULT_STORE_COLLECTION_NAME", "langchain")
DEFAULT_K_VALUE = int(os.getenv("DERRIDAI_DEFAULT_K_VALUE", "64"))
DEFAULT_FETCH_K_VALUE = int(os.getenv("DERRIDAI_DEFAULT_FETCH_K_VALUE", "500"))
DEFAULT_LAMBDA_MULT_VALUE = float(os.getenv("DERRIDAI_DEFAULT_LAMBDA_MULT_VALUE", "0.7"))
MAX_CONCURRENT_LOOKUPS = int(os.getenv("DERRIDAI_MAX_CONCURRENT_LOOKUPS", "2"))


class RAGSimilarityFilter(TypedDict):
    k: int


class RAGMMRFilter(RAGSimilarityFilter):
    fetch_k: int
    lambda_mult: float


class RAGClient:
    def __init__(
        self,
        default_k_value: int = DEFAULT_K_VALUE,
        default_fetch_k_value: int = DEFAULT_FETCH_K_VALUE,
        default_lambda_mult_value: float = DEFAULT_LAMBDA_MULT_VALUE,
        default_persist_directory: str = DEFAULT_STORE_PERSIST_DIRECTORY,
        default_collection_name: str = DEFAULT_STORE_COLLECTION_NAME,
    ):
        self.embedding_model = DEFAULT_EMBEDDING_MODEL
        self.persist_directory = default_persist_directory
        self.collection_name = default_collection_name
        self.server_url = DEFAULT_CHAT_BASE_URL
        self.cross_encoder = DEFAULT_CROSS_ENCODER
        self.lookup_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LOOKUPS)
        self.embeddings = OllamaEmbeddings(model=self.embedding_model, base_url=self.server_url)
        self._reranker: CrossEncoder | None = None
        self.stores: dict[str, Chroma] = {}
        self.stores["defaults"] = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name=self.collection_name,
        )
        self.stores["response_cache"] = Chroma(
            persist_directory=f"{self.persist_directory}_response_cache",
            embedding_function=self.embeddings,
        )
        self.default_mmr_filter: RAGMMRFilter = {
            "k": default_k_value,
            "fetch_k": default_fetch_k_value,
            "lambda_mult": default_lambda_mult_value,
        }
        self.default_similarity_filter: RAGSimilarityFilter = {"k": default_k_value}

    @property
    def reranker(self) -> CrossEncoder:
        if self._reranker is None:
            LOG.info("Loading reranker %s", self.cross_encoder)
            self._reranker = CrossEncoder(self.cross_encoder)
        return self._reranker

    def get_config_string(self) -> str:
        return (
            f"embedding_model: {self.embedding_model} | persist_directory: {self.persist_directory} | "
            f"server_url: {self.server_url} | cross_encoder: {self.cross_encoder}"
        )

    def store(self, key: str = "") -> Chroma:
        key = key or "defaults"
        if key in self.stores:
            return self.stores[key]
        self.stores[key] = Chroma(
            collection_name=self.collection_name,
            persist_directory=f"{self.persist_directory}_{key}",
            embedding_function=self.embeddings,
        )
        return self.stores[key]

    def basic_lookup(
        self,
        invocation_str: str | dict[str, str],
        mmr_filter: RAGMMRFilter | None = None,
        similarity_filter: RAGSimilarityFilter | None = None,
        search_types: list[str] | None = None,
        languages: list[str] | None = None,
    ) -> list[Document]:
        start = time.perf_counter()
        mmr_filter = dict(mmr_filter or self.default_mmr_filter)
        similarity_filter = dict(similarity_filter or self.default_similarity_filter)
        search_types = search_types or [RAGSearchTypes.MMR.value, RAGSearchTypes.SIMILARITY.value]
        languages = languages or [Languages.ENGLISH.value, Languages.FRENCH.value]
        all_results: list[Document] = []

        for search_type in search_types:
            for language in languages:
                query = invocation_str.get(language, "") if isinstance(invocation_str, dict) else invocation_str
                if not query.strip():
                    continue
                kwargs = mmr_filter if search_type == RAGSearchTypes.MMR.value else similarity_filter
                retriever = self.store(f"primary_{language}").as_retriever(
                    search_kwargs=kwargs,
                    search_type=search_type,
                )
                results = retriever.invoke(query)
                for doc in results:
                    doc.metadata.setdefault("language", language)
                    doc.metadata["retrieval_method"] = search_type
                all_results.extend(results)

        LOG.debug("Candidate lookup completed in %.4f seconds", time.perf_counter() - start)
        return all_results

    def hybrid_lookup(
        self,
        *,
        query: str,
        query_by_language: dict[str, str],
        languages: list[str],
        canonical_work_ids: list[str] | None = None,
        limit: int = 12,
    ) -> tuple[list[Document], dict[str, int]]:
        candidates = self.basic_lookup(
            invocation_str=query_by_language,
            search_types=[RAGSearchTypes.MMR.value, RAGSearchTypes.SIMILARITY.value],
            languages=languages,
        )
        candidate_count = len(candidates)
        filtered = filter_documents(
            candidates,
            languages=languages,
            canonical_work_ids=canonical_work_ids,
        )
        deduplicated = deduplicate_documents(filtered)

        for doc in deduplicated:
            text = str(getattr(doc, "page_content", "") or doc.metadata.get("text", ""))
            work_hint = " ".join([
                str(doc.metadata.get("work", "")),
                str(doc.metadata.get("canonical_work_id", "")),
            ])
            doc.metadata["retrieval_score"] = lexical_overlap_score(query, f"{work_hint}\n{text}")

        deduplicated.sort(
            key=lambda doc: float(doc.metadata.get("retrieval_score", 0.0)),
            reverse=True,
        )
        pool = deduplicated[: max(limit * 3, limit)]

        if pool:
            try:
                pairs = [
                    [query, str(getattr(doc, "page_content", "") or doc.metadata.get("text", ""))]
                    for doc in pool
                ]
                scores = self.reranker.predict(pairs)
                for doc, score in zip(pool, scores):
                    doc.metadata["rerank_score"] = float(score)
                pool.sort(
                    key=lambda doc: (
                        float(doc.metadata.get("rerank_score", 0.0)),
                        float(doc.metadata.get("retrieval_score", 0.0)),
                    ),
                    reverse=True,
                )
            except Exception:
                LOG.exception("Cross-encoder reranking failed; retaining lexical ordering")

        selected = pool[:limit]
        return selected, {
            "candidate_count": candidate_count,
            "deduplicated_count": len(deduplicated),
            "returned_count": len(selected),
        }

    def rerank_documents(
        self,
        query: str = "",
        docs: list[Any] | None = None,
        reranker: CrossEncoder | None = None,
        top_n: int | None = None,
    ) -> list[Any]:
        docs = docs or []
        if not docs:
            return []
        reranker = reranker or self.reranker
        pairs = [
            [query, doc.page_content if hasattr(doc, "page_content") else str(doc)]
            for doc in docs
        ]
        scores = reranker.predict(pairs)
        indices = sorted(range(len(docs)), key=lambda i: float(scores[i]), reverse=True)
        return [docs[i] for i in indices[: min(top_n or len(docs), len(docs))]]
