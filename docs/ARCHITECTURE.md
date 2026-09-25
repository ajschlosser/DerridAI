<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# Architecture overview

This document describes the current `master` architecture. For user-visible behavior see [USER_GUIDE.md](USER_GUIDE.md); for scholarly rationale and implemented-versus-intended distinctions see [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).

## Runtime processes

- **web** — Vue 3 single-page application built by Vite and served by nginx. It proxies `/api/` to the API; Storybook is an opt-in development surface.
- **api** — one FastAPI process. `api/app/main.py` is intentionally a minimal ASGI entrypoint; `application.py` constructs the app, registers middleware/exception handling, and composes domain routers from `api/app/routers/`. Shared services are constructed in `services.py`.
- **LLM providers** — Ollama or OpenAI-compatible endpoints reached through named provider profiles.
- **Chroma** — embedded `PersistentClient` by default or an HTTP Chroma server. Chroma stores derived search/vector projections and operational caches; it is not the canonical scholarly record store.

Background work runs in the API process. There is no external worker/queue service.

## Backend boundaries

| Area | Current ownership |
| --- | --- |
| Application composition | `main.py`, `application.py`, `middleware.py`, `route_policy.py`, `response_filters.py`, `validation_handlers.py` |
| HTTP routes | `routers/{admin,annotations,auth,chroma,corpus,health,i18n,jobs,llm,stores,system,system_data}.py` |
| Corpus orchestration | `corpus_builder.py` plus focused `corpus_*` modules for lifecycle, manifest workflow, segmentation, enrichment, review, quality, publication, and schema/profile behavior |
| Source ingestion | `corpus_extraction.py`, `source_media.py`, `source_text.py`, `source_audio.py`, `source_gutenberg.py`, `source_safety.py`, `source_quality.py`, `source_kinds.py` |
| Metadata schemas and progressive precedent | `metadata_schema.py`, `metadata_schema_store.py`, `metadata_exemplars.py`, `metadata_exemplar_projection.py`, `metadata_exemplar_retrieval.py`, `metadata_memory.py`, `metadata_adjudication_cache.py` |
| Durable provenance / Research memory | `provenance_memory.py`, `system_store.py`, related Research/job persistence |
| Search/vector storage | `chroma_store.py`, `chroma_connection.py`, `system_chroma_console.py` |
| Research/RAG | `rag.py`, `researcher_view.py`, bibliography/evaluation helpers |
| Background jobs | `job_llm.py`, `job_rag.py`, `job_tools.py`, `job_upsert.py`; `job_state.py` owns shared durable state; `jobs.py` is a compatibility export layer |
| Providers/tools | `llm.py`, `llm_tools.py`, `provider_profile_options.py`, translation/content-policy helpers |
| Auth/system persistence | `auth.py`, `persistence.py`, `system_store.py`, `database_backend.py` |

The decomposition is intentional: do not move ordinary routes back into `main.py`, background implementations back into `jobs.py`, or extracted corpus logic back into one manager merely to reduce import count.

## Sources and corpus build flow

Corpus Builder is source-media aware rather than PDF-only.

1. **Register and validate source.** Enforce format-specific byte/resource limits and reject unsafe active content before expensive extraction.
2. **Extract/transcribe.** Preserve the immutable extracted source and extractor/tool/version provenance. PDF extraction may use OCR; audio may use transcription/diarization; text/document/image/Gutenberg paths have their own adapters.
3. **Normalize source spans.** Build source units with medium-appropriate coordinates. Pages/printed folios are meaningful for paged documents; audio evidence uses time ranges/speakers.
4. **Structure and segment.** Reviewer-confirmed structure is authoritative. Semantic boundary proposals are validated for text conservation and coherent source mapping.
5. **Enrich.** Metadata-family tasks combine deterministic facts, optional run guidance, and bounded evidence-bound reviewed precedents. Model output is a proposal until schema/provenance checks pass.
6. **Review.** Reviewer edits are revisioned and preserve field/evidence provenance. The frontend applies ordinary review edits optimistically while serializing conflicting same-record persistence and handling rejection/rebase/rollback.
7. **Publish/index.** Validated records are serialized for publication. Vector indexes are explicit derived projections that can be rebuilt from authoritative records.

The compatibility storage namespace still contains `.home/pdf-corpus`; that path name is historical and must not be interpreted as a PDF-only product contract.

## Metadata and memory authority

DerridAI has multiple kinds of “memory”; they must not be flattened into one database concept.

- **Canonical scholarly state:** reviewed records/RecordRevisions, field assertions and review decisions, exact evidence bindings, source identity.
- **Metadata exemplars:** evidence-bound reviewed precedents derived from canonical review state. Their semantic index is rebuildable. Corrections preserve rejected values as negative evidence; confirmed absence is reusable only when explicitly evidence-bound.
- **Research response/claim memory:** prior Research responses, generated claims, and support bindings. It is separate from metadata exemplar retrieval.
- **Exact adjudication cache:** deterministic/same-context assistance; it is not a substitute for evidence-bound semantic precedent.
- **Response cache:** operational RAG cache/Response Library infrastructure, not corpus truth.
- **Chroma projections:** search/vector indexes and internal semantic projections. Deleting/rebuilding them must not delete canonical review/provenance data.

Support/exemplar resolution is revision-aware. When the referenced source revision/evidence can no longer be resolved, the binding is marked stale/unresolvable rather than silently rebound to newer text.

## Persistence

All paths derive from `CHROMA_DATA_ROOT` (default `/data`).

| Data | Storage | Authority / restart behavior |
| --- | --- | --- |
| Users, roles, sessions, login throttle | Auth SQLite | Authoritative auth state |
| Provider profiles, annotations, languages, job snapshots/history, provenance/memory state | System SQLite | Durable application state |
| Source assets, build/review checkpoints, publications | Files under DerridAI data root | Authoritative corpus/build artifacts; atomic writes where applicable |
| Vector/search collections | Chroma embedded path or HTTP server | Derived/rebuildable from canonical data |
| Metadata exemplar semantic projection | Internal Chroma/system projection | Derived/rebuildable; hidden from ordinary research collections |
| Response cache | Chroma/system cache role | Operational cache, not corpus truth |
| Upsert request spool | `UPSERT_JOB_SPOOL_PATH` | Durable queued vector-build request material |
| Browser workspaces/preferences | IndexedDB/localStorage | Per-origin/browser UI state |

Active job execution is process-local, but job snapshots/history are mirrored to SQLite. On restart, work left `queued`, `running`, or `cancelling` is marked failed/interrupted rather than automatically replayed; completed history remains inspectable. Job state is not coordinated across multiple API processes.

## Search and Research

Search can operate over browser-loaded records or server-backed corpus/vector collections. Research composes dense/lexical/MMR retrieval, deduplication and optional reranking, or can skip retrieval and synthesize from researcher-selected evidence. Evidence packets carry source identity and citation metadata into generation. Deterministic code owns stable IDs/citation resolution wherever the stored data can answer exactly.

System Data exposes administrative inspection of application/system datasets, including metadata exemplars/memory and restricted system-Chroma querying, without presenting internal vector collections as scholarly corpora.

## Frontend

`web/src/` is Vue 3 + TypeScript with Pinia and Vue Router:

- `views/` owns page composition;
- `components/` owns reusable UI/Storybook surfaces;
- `api/` owns typed transport contracts;
- `domain/` owns pure rules/formatting;
- `composables/` and `stores/` own reusable stateful behavior;
- `runtime/` is a remaining compatibility/orchestration boundary, not the preferred home for new feature logic;
- semantic tokens in `styles/tokens.css` and accessible primitives are the styling/interaction contract.

## Known constraints

- The application still assumes one API process for in-flight job execution and mutable embedded-storage coordination.
- `chroma_store.py`, `corpus_builder.py`, and some frontend compatibility/style surfaces remain large; refactor them only along verified domain seams with regression coverage.
- Historical versioned design documents describe the release that created them, not the current architecture.
