<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# DerridAI

[English](README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Русский](README.ru.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md)

DerridAI is a local-first Docker application for building, auditing, and querying scholarly corpora of philosophical texts. It ingests PDF, text/RTF/DOCX, image, audio, URL, and Project Gutenberg sources into provenance-preserving scholarly records; supports human/LLM review and evidence-bound metadata enrichment; builds derived ChromaDB search projections; and runs an evidence-grounded retrieval-augmented generation (RAG) pipeline over the result.

Current version: **0.80.0 — Beverly** ([release notes](docs/notes/0.80.0.md)).

## Features

- **Corpus Builder** — a sequenced Source → Structure/transcription → LLM & enrichment → Record construction → Review workflow whose controls adapt to the selected medium. Extraction is bounded and provenance-preserving; reviewer-owned structure/text revisions and evidence remain auditable.
- **Record review** — JSONL workspaces with audit history, bulk/work-level metadata editing, diffs, source/evidence navigation, and human/LLM field ownership. Canonical `FieldAssertion` records preserve value provenance, authority, evidence, and stable field identity while schema-defined metadata flows through review, Search, Record Inspector, touch-up, and Research presentation.
- **LLM review and tools** — foreground, background, and background Auto-improve runs against named Ollama or OpenAI-compatible provider profiles, each with its own concurrency limit and warmup state.
- **Vector stores** — persistent ChromaDB collections on the local filesystem or a running Chroma server, with English/French language mirrors, background upserts, and JSONL round-tripping.
- **RAG Research** — hybrid retrieval, cross-encoder reranking, language routing, selected-evidence mode, streamed/cancellable generation, response/claim provenance memory, a cached Response Library, and LLM grading.
- **Roles** — Admin and Researcher accounts; researchers see summarized evidence text and cannot mutate corpora.
- **Backup & restore** — one ZIP holding workspaces, audit history, provider profiles, corpus source assets, and every Chroma collection with its embeddings.
- **Bilingual and accessible** — English and Canadian French are first-class locales with enforced key parity. Keyboard access, visible focus, responsive/reflow behavior, forced-colors support, and WCAG 2.2 AA are acceptance criteria.

See the [User Guide](docs/USER_GUIDE.md) for the full feature reference.

## Architecture

| Service     | Stack                                                               | Notes                                                                                                                                        |
| ----------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `web`       | Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js, served by nginx | Proxies `/api/` to the API; Storybook is available as an opt-in dev service                                                                  |
| `api`       | Python 3.12, FastAPI, ChromaDB, PyMuPDF, sentence-transformers      | Authoritative corpus/build files and SQLite auth/system/provenance state live under `./data`; Chroma holds derived search/result projections |
| LLM backend | Ollama (default) or any OpenAI-compatible endpoint                  | Runs on the host or elsewhere; not part of the default compose stack                                                                         |

For code ownership and persistence boundaries, see [Architecture](docs/ARCHITECTURE.md).

## Getting started

These steps are the supported clean-checkout path. They are intentionally explicit so a new developer can repeat them without relying on an existing DerridAI data directory or shell environment.

### 1. Prerequisites

Install Git, Docker Engine/Desktop with the `docker compose` command, and an LLM endpoint. The default configuration expects Ollama on the host.

The default Ollama models are:

```text
gemma4:e2b
bge-m3:latest
```

If you use a different Ollama model or an OpenAI-compatible provider, change `.env` before starting DerridAI.

### 2. Clone and configure

```bash
git clone https://github.com/ajschlosser/DerridAI.git
cd DerridAI
cp .env.example .env
```

PowerShell equivalent:

```powershell
Copy-Item .env.example .env
```

On Docker Desktop with WSL, set `HOST_UID` and `HOST_GID` in `.env` to the output of `id -u` and `id -g`. This keeps bind-mounted Chroma/SQLite files owned by your host user.

Do not export DerridAI test-storage variables such as `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH`, or `CHROMA_PATH` globally in your shell. Compose interpolates exported variables before values from the file are passed into the container.

### 3. Make the configured models available

For Ollama already running on the host:

```bash
ollama pull gemma4:e2b
ollama pull bge-m3:latest
```

The default `.env.example` uses:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

Alternatively, use the optional compose Ollama service:

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull gemma4:e2b
docker compose exec ollama ollama pull bge-m3:latest
```

Then set `OLLAMA_BASE_URL=http://ollama:11434` in `.env`.

### 4. Validate the compose configuration and start DerridAI

```bash
docker compose config --quiet
docker compose up -d --build
```

The default bindings are application <http://localhost:8181>, API <http://127.0.0.1:8000>, and API documentation <http://127.0.0.1:8000/docs>.

On first launch, DerridAI asks you to create the initial administrator account. No default credentials are shipped.

### 5. Verify the installation

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

The live endpoint should return JSON containing `"ok": true`, the application version, and the baked git commit when available. The `web` and `api` services should report healthy in `docker compose ps`.

For a broader local diagnostic:

```bash
./scripts/diagnose.sh
```

PowerShell:

```powershell
.\scripts\diagnose.ps1
```

### 6. Stop or rebuild

Stop the application without deleting the bind-mounted `./data` directory:

```bash
docker compose down
```

Rebuild after pulling changes:

```bash
docker compose down
docker compose up -d --build
```

If an older release left root-owned files under `data/`, run `./scripts/fix-data-permissions.sh` on supported Unix-like hosts.

## Developer setup

CI uses Python 3.12 and Node 22; use those versions locally when reproducing failures.

Backend/test environment:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements-dev.txt
```

Frontend environment:

```bash
cd web
npm ci --no-audit --no-fund
npx playwright install chromium
cd ..
```

Run the fast local quality gates from the repository root:

```bash
ruff check api/app tests scripts/check_frontend_api_contract.py
mypy
pytest -q -n auto --dist=worksteal --ignore=tests/test_frontend_api_contract.py
pytest -q -m contract tests/test_frontend_api_contract.py

cd web
npm run format:repo:check
npm run lint
npm run typecheck
npm run typecheck:tests
npm run test:unit
npm run build
```

Use `npm run format:repo` from `web/` to format every Prettier-supported source, configuration, and documentation file in the repository. Generated legacy DOM snapshot HTML is intentionally excluded.

For browser coverage, Storybook, CI parity, and contribution rules, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Repository map

- `api/app/` — FastAPI application, corpus ingestion/review, provenance, persistence, RAG, providers, and background jobs.
- `web/src/` — Vue application, reusable components, domain modules, stores, and the shrinking legacy runtime compatibility layer.
- `tests/` — backend/regression/contract tests.
- `web/tests/frontend/` — Vitest component/domain tests.
- `web/tests/e2e/` — Playwright application, Storybook, accessibility, and legacy characterization coverage.
- `docs/` — current architecture/domain contracts plus historical release notes under `docs/notes/`.
- `data/` — local runtime state; git-ignored except placeholders. Never commit its contents.

## Documentation

Start with the documents that describe current behavior:

- [User Guide](docs/USER_GUIDE.md) — feature reference, operations, backup, and limitations
- [Architecture](docs/ARCHITECTURE.md) — runtime boundaries, authority, persistence, and data flow
- [Project context](docs/PROJECT_CONTEXT.md) — scholarly rationale and implemented-versus-intended capabilities
- [Contributing](CONTRIBUTING.md) — human developer setup, quality gates, and change rules
- [AGENTS.md](AGENTS.md) — additional rules for coding agents
- Focused contracts: [source ingestion](docs/INGESTION_VALIDATION.md), [metadata schemas](docs/METADATA_SCHEMAS.md), [FieldAssertion migration](docs/FIELD_ASSERTION_MIGRATION.md), [metadata memory](docs/METADATA_MEMORY.md), [design tokens](docs/DESIGN_TOKENS.md), and [fr-CA localization](docs/LOCALIZATION_FR_CA.md)

Release history is in [CHANGELOG.md](CHANGELOG.md) and `docs/notes/<version>.md`. Version-specific release notes are historical records; they are not current architecture or backlog documents.

## License

No license file is currently included. Source files carry `Copyright 2026 Aaron John Schlosser, PhD.` The sign-in screen, account menu, and Settings → About DerridAI show `© 2026 The New England Transcendental Club of California`.
