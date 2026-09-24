# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

from .chroma_store import ChromaStore
from .config import settings
from .jobs import LLMJobManager, LLMToolJobManager, RAGJobManager, UpsertJobManager

# Process-wide service objects. Keeping construction in one module makes route
# ownership explicit while preserving the application's current singleton
# lifecycle and test monkeypatch behavior.
store = ChromaStore()
llm_jobs = LLMJobManager(max_workers=64)
llm_tool_jobs = LLMToolJobManager(store)
rag_jobs = RAGJobManager(
    store,
    ollama_max_concurrent=settings.rag_ollama_max_concurrent,
)

# Chroma writes and embedding-model calls are relatively heavy. Serializing
# upsert jobs prevents large syncs from competing for CPU/RAM/VRAM and making
# the UI appear frozen; additional sync requests remain queued.
upsert_jobs = UpsertJobManager(store, max_workers=1)
