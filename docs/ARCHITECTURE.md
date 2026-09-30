<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Architecture overview

This document describes the current `master` architecture. For user-visible behavior see [USER_GUIDE.md](USER_GUIDE.md); for scholarly rationale and implemented-versus-intended distinctions see [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).

## Runtime processes

- **web** — Vue 3 single-page application built by Vite and served by nginx. It proxies `/api/` to the API; Storybook is an opt-in development surface.
- **api** — one FastAPI process. `api/app/main.py` is intentionally a minimal ASGI entrypoint; `application.py` constructs the app, registers middleware/exception handling, and composes domain routers from `api/app/routers/`. Shared services are constructed in `services.py`.
- **LLM providers** — Ollama or OpenAI-compatible endpoints reached through named provider profiles.
- **Chroma** — embedded `PersistentClient` by default or an HTTP Chroma server. Chroma stores derived search/vector projections and operational caches; it is not the canonical scholarly record store.
- **document-nlp (optional)** — an isolated BookNLP adapter enabled through the `document-nlp` Compose profile. It receives bounded reviewed document text, returns derived linguistic annotations, has no corpus authority, and never downloads model weights at runtime. The API falls back gracefully when it is absent.

Background corpus/job orchestration runs in the API process. There is no external durable queue service. The optional Document Intelligence worker is a replaceable analysis provider, not a job coordinator or canonical store.

### Transports

The browser talks to the API over three deliberately separate transports, all served by the same process and proxied under `/api/`:

- **REST** (`/api/...`) owns every command and mutation: uploads, review decisions, claim validation, job creation/cancellation, schema/provider/user administration, publication, backup/restore.
- **GraphQL** (`POST /api/graphql`) is a read-only, cELF-aware query façade over shared read services (`celf_queries/`). No mutations, no subscriptions. See [GRAPHQL.md](GRAPHQL.md).
- **WebSocket** (`WS /api/ws/events`) is an authenticated realtime notification plane for job, corpus-build and model-activity progress. It is never canonical state; clients resynchronize from REST/GraphQL. See [REALTIME.md](REALTIME.md).

## Backend boundaries

| Area                                       | Current ownership                                                                                                                                                                                                                                                                       |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Application composition                    | `main.py`, `application.py`, `middleware.py`, `route_policy.py`, `response_filters.py`, `validation_handlers.py`                                                                                                                                                                        |
| HTTP routes                                | `routers/{admin,annotations,auth,chroma,corpus,health,i18n,jobs,llm,sources,stores,system,system_data}.py`                                                                                                                                                                              |
| cELF reads / GraphQL                       | `celf_queries/` (transport-independent read services shared with REST), `graphql/` (query-only Strawberry schema, permissions, request-scoped loaders)                                                                                                                                  |
| Realtime                                   | `realtime/` (WebSocket endpoint, protocol, broker, subscriptions, observer), `operation_events.py` (transport-neutral change notes)                                                                                                                                                     |
| Corpus orchestration                       | `corpus_builder.py` plus focused `corpus_*` modules for lifecycle, manifest workflow, segmentation, enrichment, review, quality, publication, and schema/profile behavior                                                                                                               |
| Source discovery / acquisition             | `source_capture.py`, `source_provider.py`, `source_identity.py`, `source_wikidata.py`, `source_gutenberg.py`, `source_wikisource.py`, `source_reconcile.py`, `source_registry.py`, `capture_store.py`                                                                                   |
| Source extraction                          | `corpus_extraction.py`, `source_media.py`, `source_text.py`, `source_audio.py`, `source_safety.py`, `source_quality.py`, `source_kinds.py`                                                                                                                                              |
| Document intelligence / content graph      | `document_intelligence.py`, optional `booknlp-worker/`, `semantic_content_graph.py`; derived whole-document annotations and content relationships, separate from cELF Research Object Graph                                                                                             |
| Metadata schemas and progressive precedent | `metadata_schema.py`, `metadata_schema_store.py`, `metadata_exemplars.py`, `metadata_exemplar_projection.py`, `metadata_exemplar_retrieval.py`, `metadata_memory.py`, `metadata_adjudication_cache.py`                                                                                  |
| Durable provenance / Research memory       | `provenance_memory.py`, `system_store.py`, related Research/job persistence                                                                                                                                                                                                             |
| Search/vector storage                      | `chroma_store.py`, `chroma_connection.py`, `system_chroma_console.py`                                                                                                                                                                                                                   |
| Pipelines                                  | `pipelines/`: `models.py` and `registry.py` (typed contracts, server-owned strategies), `purposes.py` (workflow contracts per purpose), `workflows.py` (one runtime adapter per purpose), `service.py`/`manager.py` (validation, assignment, catalog), per-feature adapters and tracing |
| Research/RAG                               | `rag.py`, `researcher_view.py`, bibliography/evaluation helpers                                                                                                                                                                                                                         |
| Background jobs                            | `job_capture.py`, `job_llm.py`, `job_rag.py`, `job_tools.py`, `job_upsert.py`; `job_state.py` owns shared durable state; `jobs.py` is a compatibility export layer                                                                                                                      |
| Providers/tools                            | `llm.py`, `llm_tools.py`, `provider_profile_options.py`, translation/content-policy helpers                                                                                                                                                                                             |
| Auth/system persistence                    | `auth.py`, `persistence.py`, `system_store.py`, `database_backend.py`                                                                                                                                                                                                                   |

The decomposition is intentional: do not move ordinary routes back into `main.py`, background implementations back into `jobs.py`, or extracted corpus logic back into one manager merely to reduce import count.

## Sources and corpus build flow

Corpus Builder is source-media aware rather than PDF-only. Source acquisition and corpus building are deliberately separate: acquiring or registering a SourceDocument does not start a build.

1. **Discover/acquire sources (optional).** Corpus Capture resolves a researcher-selected person through Wikidata, discovers Project Gutenberg/Wikisource candidates through provider adapters, reconciles work/edition identity, and records coverage. The researcher selects candidates before acquisition. Successful acquisition registers ordinary SourceDocument assets; the capture itself remains acquisition bookkeeping.
2. **Register and validate source.** Uploads, URLs, single-library imports, and Corpus Capture acquisitions converge on the same source-registration path. Enforce format-specific byte/resource limits and reject unsafe active content before expensive extraction.
3. **Extract/transcribe.** Preserve the immutable extracted source and extractor/tool/version provenance. PDF extraction may use OCR; audio may use transcription/diarization; text/document/image/library paths have their own adapters.
4. **Normalize source spans.** Build source units with medium-appropriate coordinates. Pages/printed folios are meaningful for paged documents; audio evidence uses time ranges/speakers.
5. **Structure and segment.** Reviewer-confirmed structure is authoritative. Semantic boundary proposals are validated for text conservation and coherent source mapping.
6. **Enrich.** Metadata-family tasks combine deterministic facts, optional run guidance, and bounded evidence-bound reviewed precedents. Model output is a proposal until schema/provenance checks pass.
7. **Review.** Reviewer edits are revisioned and preserve field/evidence provenance. The frontend applies ordinary review edits optimistically while serializing conflicting same-record persistence and handling rejection/rebase/rollback.
8. **Publish/index.** Validated records are serialized for publication. Vector indexes are explicit derived projections that can be rebuilt from authoritative records.

Corpus Capture discovery/acquisition jobs run through `job_capture.py` and the shared operation ledger. `capture_store.py` persists captures, candidates, and provider snapshots in System SQLite. Those rows are not corpus content: registered sources remain canonical SourceDocument assets, and `source_capture_links` is a many-to-many provenance association so one source can be reached by multiple captures without making a capture ID part of source identity. Interrupted capture workers are marked interrupted/failed rather than silently replayed after restart.

The Sources workspace is a compact projection over canonical source assets plus capture links and build summaries. `source_registry.py` never exposes source text or blocks in its table rows; the projection can be rebuilt from source/build state.

The compatibility storage namespace still contains `.home/pdf-corpus`; that path name is historical and must not be interpreted as a PDF-only product contract.

## Metadata and memory authority

DerridAI has multiple kinds of “memory”; they must not be flattened into one database concept.

- **Canonical scholarly state:** reviewed records/RecordRevisions, field assertions and review decisions, exact evidence bindings, source identity.
- **Metadata exemplars:** evidence-bound reviewed precedents derived from canonical review state. Their semantic index is rebuildable. Corrections preserve rejected values as negative evidence; confirmed absence is reusable only when explicitly evidence-bound. Selection is driven entirely by the schema's retrieval policy (`enabled`, `max_items`, `min_similarity`, `include_corrections`, `include_confirmed_absence`, `max_corrections`, `match_field_ids`): positives and corrections have separate quotas, and `match_field_ids` names other fields by stable identity whose _reviewed_ values a precedent should share. Each exemplar carries a schema-agnostic `reviewed_values` snapshot of its record; a condition is compared only when both sides are reviewed (never guessed), agreeing precedents rank first, and contradicting ones are dropped. No field name is special-cased (`metadata_exemplars.py`, `metadata_exemplar_retrieval.py`, `corpus_editorial_memory.py`). Record Review reads the same selection read-only through `metadata_precedents`.
- **Research response/claim memory:** prior Research responses, generated claims, and support bindings, owned by `research_memory.py` and `claim_memory.py`. SQLite rows are authoritative; `derridai_response_memory` (eligible responses, keyed on the question) and `derridai_validated_claims` (reviewer-validated claims with deterministic citations) are derived projections kept current through the `semantic_memory_outbox` and rebuilt when empty. A response is eligible only when graded at or above `RESEARCH_MEMORY_MIN_GRADE`. A claim is eligible for validation and the validated-claim projection only when at least one usable support binding identifies a Record; unsupported legacy rows are dropped during projection/retrieval rather than becoming trusted prose. Projection hits are re-joined to authoritative rows, and validated-claim support is checked against the run's evidence packet before it reaches the prompt. The Research answer surface exposes the same authoritative claim-validation operation used by Record Traceability, while refreshing retained-run statuses from SQLite. Claim memory remains separate from metadata exemplar retrieval; the only bridge is a read-only Record Review cross-reference (`validated_claims_citing`), which never suggests metadata.
- **Reviewer decisions:** `apply_metadata_decisions` in `corpus_review_actions.py` is the single domain operation for one or many field decisions on a record (human assertion, dispute resolution, reviewed-decision provenance, then derived adjudication memory). Routers only delegate; claim validation likewise runs through `claim_memory.apply_claim_validation`.
- **Exact adjudication cache:** deterministic/same-context assistance; it is not a substitute for evidence-bound semantic precedent.
- **Response cache:** operational RAG cache/Response Library infrastructure, not corpus truth.
- **Chroma projections:** search/vector indexes and internal semantic projections. Deleting/rebuilding them must not delete canonical review/provenance data.

Support/exemplar resolution is revision-aware. When the referenced source revision/evidence can no longer be resolved, the binding is marked stale/unresolvable rather than silently rebound to newer text.

## Persistence

All paths derive from `CHROMA_DATA_ROOT` (default `/data`).

| Data                                                                                      | Storage                             | Authority / restart behavior                                                                                       |
| ----------------------------------------------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Users, roles, sessions, login throttle                                                    | Auth SQLite                         | Authoritative auth state                                                                                           |
| Provider profiles, annotations, languages, job snapshots/history, provenance/memory state | System SQLite                       | Durable application state; annotations retain scope, linked targets, thread parentage, and deleted-root tombstones |
| Source assets, build/review checkpoints, publications                                     | Files under DerridAI data root      | Authoritative corpus/build artifacts; atomic writes where applicable                                               |
| Document Intelligence / Semantic Content Graph checkpoints                                | Files under DerridAI data root      | Derived/rebuildable build projections; never canonical publication state                                           |
| Corpus Capture state, candidates, source/capture links                                    | System SQLite                       | Durable acquisition/provenance bookkeeping; not corpus content                                                     |
| Vector/search collections                                                                 | Chroma embedded path or HTTP server | Derived/rebuildable from canonical data                                                                            |
| Metadata exemplar semantic projection                                                     | Internal Chroma/system projection   | Derived/rebuildable; hidden from ordinary research collections                                                     |
| Response cache                                                                            | Chroma/system cache role            | Operational cache, not corpus truth                                                                                |
| Upsert request spool                                                                      | `UPSERT_JOB_SPOOL_PATH`             | Durable queued vector-build request material                                                                       |
| Browser workspaces/preferences                                                            | IndexedDB/localStorage              | Per-origin/browser UI state                                                                                        |

Active job execution is process-local, but job snapshots/history are mirrored to SQLite. On restart, work left `queued`, `running`, or `cancelling` is marked failed/interrupted rather than automatically replayed; completed history remains inspectable. Job state is not coordinated across multiple API processes.

## Document Intelligence

Corpus Builder runs provider-neutral whole-document linguistic analysis after deterministic reviewed-text cleanup and before record-level metadata enrichment. The default implementation can use local spaCy or the optional isolated BookNLP worker. Entity/coreference/quotation output is hash-bound to the analyzed text, projected onto Records as advisory context, and excluded from canonical publication JSONL.

The derived **Semantic Content Graph** is separate from the cELF **Research Object Graph**. The former models characters/people/concepts/works/topics and content relationships for navigation and analysis; the latter models scholarly object/provenance relationships. Observational content edges (for example co-occurrence) are explicitly weaker than evidence-aware semantic edges projected from current metadata assertions. See [DOCUMENT_INTELLIGENCE.md](DOCUMENT_INTELLIGENCE.md).

## Pipeline semantics

Three separate, server-owned dimensions describe a pipeline:

- **Pipeline purpose** (`purposes.py`) is the application/research workflow contract: its workflow category (Research, Evidence, Search, Metadata, Memory, Corpus processing), the feature that consumes it, its input, output and authority semantics, and its required guarantees.
- **Strategy family** (`StageFamily`) is the computational role of one stage: retrieval, reranking, diversity, selection, context packing, generation and so on.
- **Scholarly effect** (`ScholarlyEffect`) says what, if anything, a stage establishes about evidence, support or provenance. Retrieval, fusion, reranking, diversity and selection are `advisory`: relevance never establishes support. Only `eligibility_gate` and `provenance_gate` stages validate anything, and that validation is computational, not reviewer or scholarly authority.

One strategy can serve several purposes (semantic retrieval, cross-encoder reranking and MMR each appear in more than one workflow) without becoming, say, an "evidence strategy". `workflows.py` maps each purpose to exactly one runtime adapter; compiling a graph with it is the runtime-support check, and its strategy allowlist is the source of the per-purpose `strategy_fit` served in the catalog. Structural validity (`PipelineService.validate`) and runtime executability stay separate, so structurally valid graphs outside an adapter's subset can be saved as inspect-only versions. The catalog (`GET /api/system/pipelines`) serves purposes, closed vocabularies with locale keys, strategies (with `scholarly_effect`, `phase` and `effect_note`), definitions and assignments; the frontend keeps no purpose, category or compatibility table of its own.

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
- `api/graphql/` holds the typed GraphQL client and checked-in operation documents; `realtime/` holds the single WebSocket connection manager and `followResource()`;
- semantic tokens in `styles/tokens.css` and accessible primitives are the styling/interaction contract.

## Known constraints

- The application still assumes one API process for in-flight job execution and mutable embedded-storage coordination.
- The realtime broker and its replay ring are in-memory in that one process; a restart forgets events and clients resynchronize from REST.
- `chroma_store.py`, `corpus_builder.py`, and some frontend compatibility/style surfaces remain large; refactor them only along verified domain seams with regression coverage.
- Historical versioned design documents describe the release that created them, not the current architecture.
