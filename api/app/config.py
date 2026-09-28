# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

APP_VERSION = "0.80.7"


_GIT_COMMIT_FILE = Path("/app/git-commit")


def resolve_git_commit() -> str:
    """Short git commit for the running build, or empty when it cannot be known.

    Order: GIT_COMMIT / SOURCE_COMMIT, a baked `/app/git-commit` file from the
    Docker image, then `git rev-parse` when the process has a checkout.
    """
    for name in ("GIT_COMMIT", "SOURCE_COMMIT"):
        raw = os.getenv(name, "").strip()
        if raw:
            return raw.split()[0][:40]
    if _GIT_COMMIT_FILE.is_file():
        value = _GIT_COMMIT_FILE.read_text(encoding="utf-8").strip().split()
        if value:
            return value[0][:40]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip()[:40]


APP_GIT_COMMIT = resolve_git_commit()


def app_version_label(version: str = APP_VERSION, commit: str = APP_GIT_COMMIT) -> str:
    """UI/API display form: ``0.62.1`` or ``0.62.1 (abc1234)``."""
    version = str(version or "").strip() or APP_VERSION
    commit = str(commit or "").strip()
    return f"{version} ({commit})" if commit else version


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


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    token = raw.strip().casefold()
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True)
class Settings:
    chroma_path: str = os.getenv("CHROMA_PATH", "/data/chroma")
    chroma_data_root: str = os.getenv("CHROMA_DATA_ROOT", "/data")
    chroma_mode: str = os.getenv("CHROMA_MODE", "embedded").strip().lower()
    chroma_base_url: str = os.getenv("CHROMA_BASE_URL", "http://chroma:8000").rstrip("/")
    chroma_token: str = os.getenv("CHROMA_TOKEN", "").strip()
    chroma_tenant: str = os.getenv("CHROMA_TENANT", "default_tenant").strip() or "default_tenant"
    chroma_database: str = os.getenv(
        "CHROMA_DATABASE", "default_database"
    ).strip() or "default_database"
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "ollama").strip().lower()
    auth_db_path: str = os.getenv("AUTH_DB_PATH", "/data/.home/derridai-auth.sqlite3")
    session_cookie_secure: bool = _bool_env("SESSION_COOKIE_SECURE", False)
    auth_login_max_failures: int = _int_env("AUTH_LOGIN_MAX_FAILURES", 5)
    auth_login_lockout_seconds: int = _int_env("AUTH_LOGIN_LOCKOUT_SECONDS", 300)
    system_db_path: str = os.getenv("SYSTEM_DB_PATH", "/data/.home/derridai-system.sqlite3")
    gutenberg_archive_path: str = os.getenv("GUTENBERG_ARCHIVE_PATH", "/data/gutenberg/txt-files.tar.zip")
    researcher_text_max_chars: int = _int_env("RESEARCHER_TEXT_MAX_CHARS", 1600)
    pdf_max_upload_mb: int = _int_env("PDF_MAX_UPLOAD_MB", 500)
    # How many metadata-enrichment runs may work at once, across all builds. One model per run.
    enrichment_max_concurrent_runs: int = _int_env("ENRICHMENT_MAX_CONCURRENT_RUNS", 1)

    # GraphQL is a read-only cELF query façade beside REST (docs/GRAPHQL.md). The
    # IDE and introspection are development aids and stay off unless opted into.
    graphql_ide_enabled: bool = _bool_env("GRAPHQL_IDE_ENABLED", False)
    graphql_introspection_enabled: bool = _bool_env("GRAPHQL_INTROSPECTION_ENABLED", False)
    graphql_max_depth: int = _int_env("GRAPHQL_MAX_DEPTH", 8)
    graphql_max_aliases: int = _int_env("GRAPHQL_MAX_ALIASES", 20)
    graphql_max_tokens: int = _int_env("GRAPHQL_MAX_TOKENS", 2000)
    # Largest client-supplied Record snapshot accepted by record_graph, in bytes.
    graphql_max_record_bytes: int = _int_env("GRAPHQL_MAX_RECORD_BYTES", 2_000_000)

    # The WebSocket realtime plane only delivers notifications (docs/REALTIME.md);
    # canonical state stays in REST/SQLite, so these bound memory, not durability.
    realtime_enabled: bool = _bool_env("REALTIME_ENABLED", True)
    realtime_max_client_message_bytes: int = _int_env("REALTIME_MAX_CLIENT_MESSAGE_BYTES", 65536)
    realtime_max_queue_events: int = _int_env("REALTIME_MAX_QUEUE_EVENTS", 256)
    realtime_replay_events: int = _int_env("REALTIME_REPLAY_EVENTS", 512)
    realtime_progress_max_hz: float = _float_env("REALTIME_PROGRESS_MAX_HZ", 8.0)
    realtime_heartbeat_seconds: float = _float_env("REALTIME_HEARTBEAT_SECONDS", 20.0)
    realtime_idle_timeout_seconds: float = _float_env("REALTIME_IDLE_TIMEOUT_SECONDS", 60.0)
    # Comma-separated browser origins allowed to open the socket in addition to the
    # request's own host. Empty means same-origin only (non-browser clients send none).
    realtime_allowed_origins: str = os.getenv("REALTIME_ALLOWED_ORIGINS", "").strip()

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
    # How a model-proposed value gets its source evidence: "with_value" (the model must cite blocks in the same
    # answer) or "backfill" (the model proposes the value; deterministic suggestion attaches blocks afterwards,
    # always pending review). See evidence_suggestions.evidence_mode.
    metadata_evidence_mode: str = os.getenv("METADATA_EVIDENCE_MODE", "with_value").strip().lower()
    api_batch_size: int = _int_env("API_BATCH_SIZE", 128)

    # Prior Research responses steer new answers only when graded at least this
    # well (0-10 overall score). Ungraded responses never steer.
    research_memory_min_grade: float = _float_env("RESEARCH_MEMORY_MIN_GRADE", 7.0)

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
    metadata_cross_encoder_enabled: bool = _bool_env(
        "METADATA_CROSS_ENCODER_ENABLED",
        True,
    )
    metadata_cross_encoder_top_k: int = min(
        32,
        _int_env("METADATA_CROSS_ENCODER_TOP_K", 8),
    )
    metadata_cross_encoder_timeout_seconds: float = _float_env(
        "METADATA_CROSS_ENCODER_TIMEOUT_SECONDS",
        15.0,
    )


settings = Settings()
