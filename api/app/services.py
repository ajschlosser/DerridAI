# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

from .capture_store import CaptureStore
from .chroma_store import ChromaStore
from .config import settings
from .data_retention import RetentionScheduler, RetentionService
from .job_capture import CaptureJobManager
from .job_document_nlp import DocumentNlpPackJobManager
from .job_llm import LLMJobManager
from .job_rag import RAGJobManager
from .job_tools import LLMToolJobManager
from .job_upsert import UpsertJobManager
from .source_capture import CorpusCaptureService

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

# Corpus Capture: durable capture state lives in the system database; source
# registration goes through the ordinary Corpus Builder SourceDocument path.
capture_store = CaptureStore()
capture_service = CorpusCaptureService(capture_store)
capture_jobs = CaptureJobManager(capture_service)
# Administrator-installed Document Intelligence language packs.
document_nlp_pack_jobs = DocumentNlpPackJobManager()


def _response_cache_collection():
    """The Response Library collection, or None before the first saved response."""
    try:
        return store.client.get_collection(name=store._RESPONSE_CACHE_STORAGE)
    except Exception as exc:
        if store._is_missing_collection_error(exc):
            return None
        raise


def _known_trace_features() -> list[str]:
    from .pipelines.defaults import BUILT_IN_ASSIGNMENTS

    return [assignment.feature for assignment in BUILT_IN_ASSIGNMENTS]


def _retention_service() -> RetentionService:
    from .persistence import system_repository
    from .pipelines.store import pipeline_store

    return RetentionService(
        settings_repository=system_repository,
        pipeline_database=pipeline_store.database,
        job_managers=lambda: [llm_jobs, llm_tool_jobs, rag_jobs, upsert_jobs, capture_jobs, document_nlp_pack_jobs],
        response_cache_collection=_response_cache_collection,
        known_trace_features=_known_trace_features,
    )


# Operational-data retention: configured in Settings, applied hourly and on demand.
retention_service = _retention_service()
retention_scheduler = RetentionScheduler(lambda: retention_service)
