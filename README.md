<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# DerridAI

DerridAI is a local-first Docker application for building, auditing, and querying scholarly corpora of philosophical texts. It turns source PDFs into structured JSONL records, reviews and enriches those records with local or OpenAI-compatible LLMs, manages persistent ChromaDB vector collections, and runs an evidence-grounded retrieval-augmented generation (RAG) pipeline over the result.

Current version: **0.60.0 — Testy Titmouse** ([release notes](docs/notes/0.60.0.md)).

## Features

- **Corpus Builder** — a sequenced Source → Document structure → LLM & enrichment → Record construction → Build workflow that extracts, segments, and enriches records from PDFs, with reviewer-owned document structure and auditable field provenance.
- **Record review** — JSONL workspaces with full audit history, bulk and work-level metadata editing, red/green diffs, source-PDF linking, and human/LLM field ownership (high-confidence LLM proposals populate fields; lower-confidence ones stay as suggestions).
- **LLM review and tools** — foreground, background, and background Auto-improve runs against named Ollama or OpenAI-compatible provider profiles, each with its own concurrency limit and warmup state.
- **Vector stores** — persistent ChromaDB collections with English/French language mirrors, background upserts, and JSONL round-tripping.
- **RAG Research** — hybrid retrieval, cross-encoder reranking, language routing, streamed and cancellable generation, a cached Response Library, and LLM grading of answers.
- **Roles** — Admin and Researcher accounts; researchers see summarized evidence text and cannot mutate corpora.
- **Backup & restore** — one ZIP holding workspaces, audit history, provider profiles, PDFs, and every Chroma collection with its embeddings.
- **Bilingual and accessible** — English and Québec French are first-class locales with enforced key parity. Keyboard access, visible focus, and WCAG 2.0 AA are release requirements.

See the [User Guide](docs/USER_GUIDE.md) for a full feature reference.

## Architecture

| Service | Stack | Notes |
| --- | --- | --- |
| `web` | Vue 3, TypeScript, Pinia, Vue Router, Vite, PDF.js, served by nginx | Proxies `/api/` to the API; Storybook is available as an opt-in dev service |
| `api` | Python 3.12, FastAPI, ChromaDB, PyMuPDF, sentence-transformers | Persistent state lives under `./data` (Chroma, SQLite auth/system stores, model cache) |
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

On Docker Desktop with WSL, set `HOST_UID` and `HOST_GID` to `id -u` / `id -g` so Chroma files are not created root-owned. Additional LLM providers are configured in the app under **LLM Providers**.

### Troubleshooting

```bash
./scripts/diagnose.sh          # PowerShell: .\scripts\diagnose.ps1
./scripts/fix-data-permissions.sh   # if older releases left root-owned data
```

## Development

```bash
# Backend and release regression tests
pip install -r api/requirements.txt pytest
pytest -q

# Frontend
cd web
npm install
npm run typecheck && npm run test:unit && npm run build
npm run storybook            # or: docker compose --profile dev up storybook
npm run test:e2e             # Playwright + axe-core
```

CI (`.github/workflows/frontend.yml`) runs the backend tests and the full frontend gate. See [AGENTS.md](AGENTS.md) for contributor and coding-agent conventions.

## Documentation

- [User Guide](docs/USER_GUIDE.md) — feature reference, operations, backup, and limitations
- [Release notes](docs/notes/) — one file per release, e.g. [0.60.0](docs/notes/0.60.0.md)
- Design notes: [Storage](docs/STORAGE_0.36.1.md), [Shareable state and data model](docs/SHAREABLE_STATE_AND_DATA_MODEL_0.36.2.md), [Search workspace](docs/SEARCH_WORKSPACE_0.36.10.md), [Packet reduction](docs/PACKET_REDUCTION_0.30.11.md), [fr-CA localization](docs/LOCALIZATION_FR_CA.md)

## License

No license file is currently included. Source files carry `Copyright 2026 Aaron John Schlosser, PhD.` The UI footer reads `© 2026 The New England Transcendental Club of California`.
