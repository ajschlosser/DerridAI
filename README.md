<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# DerridAI

DerridAI is a local-first Docker application for building, auditing, and querying scholarly corpora of philosophical texts. It ingests PDF, text/RTF/DOCX, image, audio, URL, and Project Gutenberg sources into provenance-preserving scholarly records; supports human/LLM review and evidence-bound metadata enrichment; builds derived ChromaDB search projections; and runs an evidence-grounded retrieval-augmented generation (RAG) pipeline over the result.

Current version: **0.70.0 — Amesbury** ([release notes](docs/notes/0.70.0.md)).

## Features

- **Corpus Builder** — a sequenced Source → Structure/transcription → LLM & enrichment → Record construction → Review workflow whose controls adapt to the selected medium. Extraction is bounded and provenance-preserving; reviewer-owned structure/text revisions and evidence remain auditable.
- **Record review** — JSONL workspaces with audit history, bulk/work-level metadata editing, diffs, source/evidence navigation, and human/LLM field ownership. Schema-valid model values are visible for review; calibrated autofill is a separate evidence- and reviewer-precision-aware decision.
- **LLM review and tools** — foreground, background, and background Auto-improve runs against named Ollama or OpenAI-compatible provider profiles, each with its own concurrency limit and warmup state.
- **Vector stores** — persistent ChromaDB collections on the local filesystem or a running Chroma server, with English/French language mirrors, background upserts, and JSONL round-tripping.
- **RAG Research** — hybrid retrieval, cross-encoder reranking, language routing, selected-evidence mode, streamed/cancellable generation, response/claim provenance memory, a cached Response Library, and LLM grading.
- **Roles** — Admin and Researcher accounts; researchers see summarized evidence text and cannot mutate corpora.
- **Backup & restore** — one ZIP holding workspaces, audit history, provider profiles, corpus source assets, and every Chroma collection with its embeddings.
- **Bilingual and accessible** — English and Canadian French are first-class locales with enforced key parity. Keyboard access, visible focus, responsive/reflow behavior, forced-colors support, and WCAG 2.2 AA are acceptance criteria.

See the [User Guide](docs/USER_GUIDE.md) for a full feature reference.

## Architecture

| Service | Stack | Notes |
| --- | --- | --- |
| `web` | Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js, served by nginx | Proxies `/api/` to the API; Storybook is available as an opt-in dev service |
| `api` | Python 3.12, FastAPI, ChromaDB, PyMuPDF, sentence-transformers | Authoritative corpus/build files and SQLite auth/system/provenance state live under `./data`; Chroma holds derived search/result projections |
| LLM backend | Ollama (default) or any OpenAI-compatible endpoint | Runs on the host or elsewhere; not part of the compose stack |

## Quick start

Prerequisites: Docker with Compose, and an [Ollama](https://ollama.com) server (or an OpenAI-compatible endpoint) with the default models pulled.

```bash
cp .env.example .env
docker compose up -d --build
```

Then open <http://localhost:8181>. On first launch DerridAI asks you to create the initial administrator account; no default credentials are shipped. Interactive API documentation is at <http://localhost:8000/docs>.

To rebuild after an upgrade:

```bash
docker compose down
docker compose up -d --build
```

### Configuration

Copy `.env.example` to `.env` and edit as needed. Key settings:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=bge-m3:latest
EMBEDDING_PROVIDER=ollama
```

Set `SESSION_COOKIE_SECURE=true` only when the browser reaches DerridAI through an HTTPS reverse proxy (it defaults to `false` for local HTTP). Repeated failed logins lock the username for `AUTH_LOGIN_LOCKOUT_SECONDS` (default 300) after `AUTH_LOGIN_MAX_FAILURES` (default 5).

On Docker Desktop with WSL, set `HOST_UID` and `HOST_GID` to `id -u` / `id -g` so Chroma files are not created root-owned. Additional LLM providers are configured in the app under **LLM Providers**.

### Troubleshooting

```bash
./scripts/diagnose.sh          # PowerShell: .\scripts\diagnose.ps1
./scripts/fix-data-permissions.sh   # if older releases left root-owned data
```

## Development

```bash
# Backend and release regression tests
pip install -r api/requirements.txt -r api/requirements-dev.txt
pytest -q -n auto --dist=worksteal
pytest -q -m contract tests/test_frontend_api_contract.py

# Frontend
cd web
npm ci --no-audit --no-fund
npm run lint && npm run typecheck && npm run typecheck:tests && npm run test:unit && npm run build
npm run storybook            # or: docker compose --profile dev up storybook
npm run test:e2e             # Playwright + axe-core
```

CI (`.github/workflows/frontend.yml`) runs Ruff, mypy, ESLint, parallel backend regression tests, a focused frontend/FastAPI contract gate, and the frontend static/browser/accessibility gates. See [CONTRIBUTING.md](CONTRIBUTING.md) for every gate, [tests/README.md](tests/README.md) for test taxonomy, and [AGENTS.md](AGENTS.md) for conventions.

## Documentation

- [User Guide](docs/USER_GUIDE.md) — feature reference, operations, backup, and limitations
- [Changelog](CHANGELOG.md) — release history; full notes live in [`docs/notes/`](docs/notes/)
- [Architecture overview](docs/ARCHITECTURE.md), [Project context](docs/PROJECT_CONTEXT.md), and [Contributing](CONTRIBUTING.md)
- Focused contracts: [source ingestion](docs/INGESTION_VALIDATION.md), [metadata schemas](docs/METADATA_SCHEMAS.md), [metadata memory](docs/METADATA_MEMORY.md), [design tokens](docs/DESIGN_TOKENS.md), and [fr-CA localization](docs/LOCALIZATION_FR_CA.md)
- Version-specific design/status documents and [`docs/notes/`](docs/notes/) are historical records; use the unversioned documents above for current behavior.

## License

No license file is currently included. Source files carry `Copyright 2026 Aaron John Schlosser, PhD.` The sign-in screen, account menu, and Settings → About DerridAI show `© 2026 The New England Transcendental Club of California`.
