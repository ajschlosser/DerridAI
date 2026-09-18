# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import os
from dataclasses import dataclass

APP_VERSION = "0.48.1"


def _float_env(name: str, default: float) -> float:
    try:
        return max(0.1, float(os.getenv(name, str(default))))
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    chroma_path: str = os.getenv("CHROMA_PATH", "/data/chroma")
    chroma_data_root: str = os.getenv("CHROMA_DATA_ROOT", "/data")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "ollama").strip().lower()
    auth_db_path: str = os.getenv("AUTH_DB_PATH", "/data/.home/derridai-auth.sqlite3")
    system_db_path: str = os.getenv("SYSTEM_DB_PATH", "/data/.home/derridai-system.sqlite3")
    researcher_text_max_chars: int = _int_env("RESEARCHER_TEXT_MAX_CHARS", 1600)
    pdf_max_upload_mb: int = _int_env("PDF_MAX_UPLOAD_MB", 500)

    ollama_base_url: str = os.getenv(
        "OLLAMA_BASE_URL",
        "http://host.docker.internal:11434",
    ).rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3:latest")

    openai_compat_base_url: str = os.getenv(
        "OPENAI_COMPAT_BASE_URL",
        "http://host.docker.internal:3001/v1",
    ).rstrip("/")
    openai_compat_model: str = os.getenv("OPENAI_COMPAT_MODEL", "auto")
    openai_compat_api_key: str = os.getenv("OPENAI_COMPAT_API_KEY", "")

    ollama_connect_timeout_seconds: float = _float_env(
        "OLLAMA_CONNECT_TIMEOUT_SECONDS",
        8.0,
    )
    ollama_status_timeout_seconds: float = _float_env(
        "OLLAMA_STATUS_TIMEOUT_SECONDS",
        5.0,
    )
    ollama_timeout_seconds: float = _float_env(
        "OLLAMA_TIMEOUT_SECONDS",
        1800.0,
    )
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "10m").strip()

    openai_connect_timeout_seconds: float = _float_env(
        "OPENAI_CONNECT_TIMEOUT_SECONDS",
        10.0,
    )
    openai_timeout_seconds: float = _float_env(
        "OPENAI_TIMEOUT_SECONDS",
        1800.0,
    )

    llm_max_text_chars: int = _int_env("LLM_MAX_TEXT_CHARS", 50000)
    llm_metadata_num_predict: int = _int_env(
        "LLM_METADATA_NUM_PREDICT",
        768,
    )
    llm_text_num_predict: int = _int_env(
        "LLM_TEXT_NUM_PREDICT",
        4096,
    )
    llm_max_fields: int = _int_env("LLM_MAX_FIELDS", 12)
    api_batch_size: int = _int_env("API_BATCH_SIZE", 128)

    rag_default_k: int = _int_env("RAG_DEFAULT_K", 64)
    rag_default_fetch_k: int = _int_env("RAG_DEFAULT_FETCH_K", 500)
    rag_default_rerank_top_n: int = _int_env("RAG_DEFAULT_RERANK_TOP_N", 24)
    rag_default_lambda_mult: float = _float_env("RAG_DEFAULT_LAMBDA_MULT", 0.7)
    rag_default_rrf_k: int = _int_env("RAG_DEFAULT_RRF_K", 60)
    rag_default_query_num_predict: int = _int_env(
        "RAG_DEFAULT_QUERY_NUM_PREDICT",
        768,
    )
    rag_default_record_char_limit: int = _int_env(
        "RAG_DEFAULT_RECORD_CHAR_LIMIT",
        12000,
    )
    rag_default_total_char_limit: int = _int_env(
        "RAG_DEFAULT_TOTAL_CHAR_LIMIT",
        120000,
    )
    rag_ollama_max_concurrent: int = _int_env(
        "RAG_OLLAMA_MAX_CONCURRENT",
        1,
    )
    rag_auto_grade_max_attempts: int = _int_env(
        "RAG_AUTO_GRADE_MAX_ATTEMPTS",
        2,
    )
    rag_auto_grade_retry_delay_seconds: float = _float_env(
        "RAG_AUTO_GRADE_RETRY_DELAY_SECONDS",
        1.5,
    )
    rag_cross_encoder_model: str = os.getenv(
        "RAG_CROSS_ENCODER_MODEL",
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
    )
    rag_model_cache: str = os.getenv("RAG_MODEL_CACHE", "/data/models")


settings = Settings()
