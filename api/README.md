# DerridAI API

The `api/` tree is DerridAI's FastAPI backend. It owns server-side authorization, source ingestion, canonical corpus/review operations, durable system/provenance state, derived Chroma projections, provider integration, RAG, and background-operation orchestration.

Use the root [README](../README.md) for installation and first-run setup. Use [CONTRIBUTING](../CONTRIBUTING.md) for the supported Python/Node versions and quality gates. This file is the backend code map.

## Application composition

The backend is intentionally split by responsibility:

- `app/main.py` — minimal ASGI entrypoint.
- `app/application.py` — constructs FastAPI, middleware, exception handling, and router composition.
- `app/routers/` — HTTP transport grouped by domain. Keep ordinary route handlers here rather than growing `main.py`.
- `app/services.py` — shared service construction.
- `app/config.py` — environment-backed runtime configuration and build/version identity.

Interactive OpenAPI documentation is available at `/docs` on a running API. The unauthenticated liveness endpoint is `GET /api/live`; administrator diagnostics are exposed separately through authenticated health/config surfaces.

## Domain ownership

| Area                                    | Primary modules                                                                                                                                                             |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Corpus orchestration                    | `corpus_builder.py` plus focused `corpus_*` lifecycle, manifest, segmentation, enrichment, review, quality, publication, and schema/profile modules                         |
| Source ingestion                        | `corpus_extraction.py`, `source_media.py`, `source_text.py`, `source_audio.py`, `source_gutenberg.py`, `source_safety.py`, `source_quality.py`, `source_kinds.py`           |
| Canonical field state                   | `field_assertions.py` and record/revision review code                                                                                                                       |
| Metadata schemas and reviewed precedent | `metadata_schema*.py`, `metadata_exemplars.py`, `metadata_exemplar_projection.py`, `metadata_exemplar_retrieval.py`, `metadata_memory.py`, `metadata_adjudication_cache.py` |
| Provenance / Research memory            | `provenance_memory.py`, `system_store.py`                                                                                                                                   |
| Search/vector storage                   | `chroma_store.py`, `chroma_connection.py`, `system_chroma_console.py`                                                                                                       |
| Research/RAG                            | `rag.py`, `researcher_view.py`, bibliography/evaluation helpers                                                                                                             |
| Background operations                   | `job_llm.py`, `job_rag.py`, `job_tools.py`, `job_upsert.py`; shared durable behavior in `job_state.py`; `jobs.py` is a compatibility export layer                           |
| Providers and LLM tools                 | `llm.py`, `llm_tools.py`, provider-profile and translation/content-policy helpers                                                                                           |
| Auth and server-owned persistence       | `auth.py`, `persistence.py`, `system_store.py`, `database_backend.py`                                                                                                       |
| Localization                            | `locales/` and language/content-policy services                                                                                                                             |

The decomposition is deliberate. A compatibility import from a large module is not a reason to put new implementation logic back into that module.

## Data authority

Do not treat every persisted database as equivalent.

- Reviewed records, revisions, field assertions, review decisions, exact evidence bindings, and source identities are canonical scholarly state.
- SQLite stores authentication separately from server-owned application/provenance/job state.
- Chroma corpus indexes, metadata-exemplar indexes, and other semantic/vector projections are derived and rebuildable.
- Metadata precedent memory and Research response/claim memory have different authority and lifecycle semantics even when both use retrieval.
- Active background execution is in-process. Job snapshots/history are durably mirrored to SQLite; interrupted queued/running/cancelling jobs are marked failed after restart rather than silently replayed.

See [Architecture](../docs/ARCHITECTURE.md) and [Metadata memory](../docs/METADATA_MEMORY.md) before changing these boundaries.

## Source ingestion

Source files and remote content are untrusted inert data. The backend supports PDF, text/RTF/DOCX, images, audio, URL, and Project Gutenberg ingestion with medium-specific extraction and evidence coordinates.

Never execute document-provided macros, scripts, fields, active objects, relationships, or commands. Keep byte/resource/decompression/image/audio/tool limits in front of expensive processing and preserve extractor/tool/version provenance. See [Source ingestion safety and fidelity](../docs/INGESTION_VALIDATION.md).

## Local development

Create the Python environment from the repository root:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements-dev.txt
```

For an application runtime, prefer the root Compose workflow so storage paths and service networking match the supported local deployment:

```bash
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
curl -fsS http://127.0.0.1:8000/api/live
```

Backend tests do not require Docker, Ollama, a GPU, or a real Chroma service; test configuration redirects storage to isolated temporary paths.

## Validation

From the repository root:

```bash
ruff check api/app tests scripts/check_frontend_api_contract.py
mypy
python -m compileall -q api/app
pytest -q -n auto --dist=worksteal --ignore=tests/test_frontend_api_contract.py
pytest -q -m contract tests/test_frontend_api_contract.py
```

Focused test taxonomy and fixture guidance are in [tests/README.md](../tests/README.md).

## Backend change rules

- Enforce authorization and role boundaries in the API even when the frontend also hides a capability.
- Treat LLM output as untrusted proposals until deterministic schema, provenance, evidence, and vocabulary checks accept it.
- Preserve speaker → position holder → stance → proposition → evidence/source relationships. Do not flatten quoted/analyzed positions into the primary author's claims.
- Preserve revision/source identity when binding evidence or memory; stale bindings must surface as stale/unresolved rather than rebinding silently.
- Keep segmentation text-conserving and preprocessing conservative.
- Keep long operations cancellable, observable, and bounded.
- Add a regression test for behavior changes and run the smallest relevant gate set before handoff.
- Do not add new active architecture guidance to version-specific release notes; update the unversioned contract document and use release notes only to record what changed.
