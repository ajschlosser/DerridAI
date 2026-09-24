<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# Architecture overview

This describes the code as it exists in 0.62.19. For feature behavior see the [User Guide](USER_GUIDE.md); for storage history see [STORAGE_0.36.1.md](STORAGE_0.36.1.md).

## Processes

- **web** — Vue 3 single-page app built by Vite and served by nginx (`web/nginx.conf`), which proxies `/api/` to the API. Storybook is an opt-in `dev` compose profile.
- **api** — one FastAPI process exposed through `api/app/main.py`. `api/app/application.py` builds the application, composes domain `APIRouter`s from `api/app/routers/`, and registers cross-cutting middleware/exception handling. Process-wide Chroma and job-manager services are constructed in `api/app/services.py`. Background work runs on threads inside this process; there is no external queue or worker service.
- **LLM backend** — Ollama or an OpenAI-compatible endpoint, reached over HTTP through provider profiles (`llm.py`). Optional compose profile `ollama`.
- **Chroma backend** — embedded `PersistentClient` by default, or `HttpClient` to a running server (optional compose profile `chroma`, or `CHROMA_BASE_URL` like `OLLAMA_BASE_URL`).

## Backend modules (`api/app/`)

| Module | Responsibility |
| --- | --- |
| `main.py`, `application.py` | Minimal ASGI entrypoint plus FastAPI application factory and router composition. |
| `middleware.py`, `route_policy.py`, `response_filters.py`, `validation_handlers.py` | Cross-cutting API authentication/capability enforcement, second-opinion response privacy, and stable validation-error handling. |
| `auth.py` | `AuthStore` over SQLite: users, roles/permissions, hashed session tokens, failed-login throttle. PBKDF2 password hashes. |
| `persistence.py`, `system_store.py` | SQLite repositories for provider profiles, annotations, languages, and the `jobs` table; locale dictionary store. |
| `chroma_store.py` | ChromaDB access: collections, language mirrors, hybrid search, and the response cache (public name `_response_cache`, stored as `derridai_response_cache`). Distinguishes an absent cache collection from storage errors. Embedded `PersistentClient` or HTTP `HttpClient` (`chroma_connection.py`). |
| `rag.py` | Retrieval, reranking (cross-encoder with lexical fallback that reports a warning), generation, evidence assembly. |
| `jobs.py`, `job_state.py`, `job_llm.py`, `job_rag.py`, `job_tools.py`, `job_upsert.py` | Compatibility exports plus focused background-job managers for LLM review, RAG, LLM tools/translation, and Chroma upserts. Shared durable checkpoint/error behavior lives in `job_state.py`; job state is mirrored to the SQLite `jobs` table. |
| `llm.py`, `llm_tools.py`, `i18n_translation.py`, `content_policy_generation.py`, `bibliography.py` | Provider calls, tool workflows (catalog lookup, grading), locale translation, researcher text-policy generation, bibliographic helpers. |
| `corpus_builder.py` | PDF → records pipeline: `PdfCorpusRepository` (file persistence) and `PdfCorpusBuildManager` (stages, checkpoints, enrichment, review mutation). |
| `corpus_metadata.py` | Pure metadata vocabularies, normalization, and human/LLM ownership rules. |
| `corpus_pipeline.py` | `BuildScope` and related explicit stage context. |
| `corpus_publication.py` | Pure publication validation and serialization. |
| `researcher_view.py` | Evidence redaction for Researcher accounts. |

`corpus_builder.py` re-exports names moved into `corpus_metadata.py` and `corpus_publication.py`, so existing imports keep working.

## Persistence

All paths derive from `CHROMA_DATA_ROOT` (default `/data`, mounted from `./data`).

| Data | Location | Notes |
| --- | --- | --- |
| Vector collections, response cache | `CHROMA_PATH` (`/data/chroma`) when `CHROMA_MODE=embedded`; otherwise a Chroma HTTP server (`CHROMA_BASE_URL`) | Embedded: `PersistentClient`, one writer per path. HTTP: `HttpClient` to the compose `chroma` profile or a host-run server. |
| Users, roles, sessions, login failures | `AUTH_DB_PATH` (SQLite) | Session tokens are stored hashed; the throttle table is keyed by lower-cased username. |
| Provider profiles, annotations, languages, jobs | `SYSTEM_DB_PATH` (SQLite) | WAL journaling. Created directly; no migrations. |
| PDF assets, builds, checkpoints, publications | `<CHROMA_DATA_ROOT>/.home/pdf-corpus/{assets,builds,publications}` | JSON/JSONL files written atomically (temp file, `fsync`, `os.replace`). Builds hold `records.jsonl` and `checkpoints/<name>.json`. |
| Chroma upsert request spool | `UPSERT_JOB_SPOOL_PATH` (default beside the system DB) | Lets queued vector builds survive as inspectable files; LLM job bodies are deliberately not spooled. |
| Browser workspace and preferences | IndexedDB/localStorage | Isolated per account role in the browser. |

Job state is process-local first: on restart, jobs left `queued`, `running`, or `cancelling` are marked `failed` (interrupted) and never replayed automatically. Failures to persist job checkpoints or collection status are recorded on the job rather than discarded.

## Corpus build flow

1. **Source** — `save_asset` hashes the PDF (`pdf-<sha256[:24]>`), extracts blocks with PyMuPDF (OCR when needed), and stores the PDF, metadata, and `*.blocks.jsonl`. Page-label lookup failures become asset warnings.
2. **Build** — the manager prepares a `BuildScope` (manifest, source and semantic blocks, source-quality assessment), constructs segmentation topology (boundary decisions with second-reader checks), schedules per-record enrichment, then finalizes and validates.
3. **Enrichment** — per record: source-quality gate, task preparation, metadata-family execution, reconciliation. Reviewer-owned fields are re-read live before each family runs and are never overwritten; if ownership cannot be read the family stops with a failed status. LLM values above the 65% confidence threshold and schema-valid populate fields; lower ones stay as `proposed_value`.
4. **Checkpoints and review** — stage results are checkpointed so a failed build is resumable; records are saved under a lock while reviewers edit. Status ledgers and `warnings` on the build record what degraded.
5. **Publication** — validated records are serialized to JSONL and can be upserted into a Chroma collection as a background job.

## Authentication and roles

Sessions are random tokens set in an HttpOnly, `SameSite=Lax` cookie (`derridai_session`, 14 days); `Secure` follows `SESSION_COOKIE_SECURE`. `AuthStore.authenticate` runs inside a `BEGIN IMMEDIATE` transaction, does equivalent password-hash work for unknown users, and locks a username key for `AUTH_LOGIN_LOCKOUT_SECONDS` after `AUTH_LOGIN_MAX_FAILURES` failures; success clears the counter. The throttle is per username, not per IP. Admin and Researcher roles are enforced in the API; researchers receive redacted evidence and cannot mutate corpora.

## Frontend (`web/src/`)

Vue 3 + Pinia + Vue Router. `views/` and `components/` (each with a Storybook story), `stores/` for state, `api/` for typed API calls, `domain/` for pure rule modules with Vitest coverage (corpus lifecycle, review rules), and `runtime/` for legacy feature renderers still being migrated view by view.

## Known limits

Single API process; job state is not shared across processes. `chroma_store.py` and `corpus_builder.py` remain large. See [STATIC_ANALYSIS_FOLLOWUPS.md](STATIC_ANALYSIS_FOLLOWUPS.md) for tracked typing and lint debt.
