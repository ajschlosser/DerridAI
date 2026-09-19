<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# AGENTS.md

Guidance for coding agents and contributors working on DerridAI. See [README.md](README.md) for the project overview and [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for feature behavior.

## What this project is

DerridAI is a local-first Docker application for building, auditing, and querying scholarly corpora of philosophical texts (Derrida in particular). PDFs become structured JSONL records via the Corpus Builder; records are reviewed with human and LLM input, stored in ChromaDB, and queried through an evidence-grounded RAG pipeline. It is a research tool: correctness, provenance, and auditability matter more than cleverness.

## Layout

- `api/app/` — FastAPI backend (Python 3.12). Key modules: `main.py` (routes), `corpus_builder.py` (PDF → records pipeline, very large), `chroma_store.py`, `rag.py`, `jobs.py` (background operations), `llm.py` / `llm_tools.py` (Ollama and OpenAI-compatible providers), `auth.py`, `researcher_view.py`, `persistence.py` / `system_store.py` (SQLite), `locales/` (`en_us.py`, `fr_ca.py`), `config.py` (env-driven settings).
- `web/src/` — Vue 3 + TypeScript frontend: `views/`, `components/` (each with a `.stories.ts`), `stores/` (Pinia), `router/`, `api/`, `composables/`, `domain/`, `runtime/` (legacy feature renderers being migrated view by view), `types/`.
- `web/tests/frontend/` (Vitest + Vue Test Utils + happy-dom) and `web/tests/e2e/` (Playwright + axe-core).
- `tests/` — Python regression suite; one `test_NNNN_<release_name>.py` per release plus topical files, and `tests/fixtures/`.
- `docs/` — `USER_GUIDE.md`, design notes, and `docs/notes/<version>.md` release notes.
- `data/` — runtime state (Chroma, SQLite, models), git-ignored except `.gitkeep`. Never commit its contents.
- `docker-compose.yml`, `.env.example`, `scripts/` (diagnostics), `.github/workflows/frontend.yml` (CI).

## Commands

```bash
pytest -q                                   # backend + release regression tests (from repo root)
python -m compileall -q api/app             # syntax check
cd web && npm run typecheck                 # vue-tsc
cd web && npm run test:unit                 # Vitest
cd web && npm run build                     # vue-tsc + Vite
cd web && npm run build-storybook
cd web && npm run test:e2e                  # Playwright + axe (needs Chromium)
docker compose up -d --build                # full stack: web :8181, api :8000
```

Backend tests stub `chromadb` and put `api/` on `sys.path`; they do not need Docker, Ollama, or a GPU.

## Release notes and docs

- **Release notes live in `docs/notes/<version>.md`**, one file per release (e.g. `docs/notes/0.61.0.md`). Do not add release notes to `README.md`.
- Start each note with `# <version> — <Release Name>`, a short summary paragraph, then bullet-point changes. Add a `## Validation` section stating what was actually run and what could not be (for example, missing `node_modules` or Docker).
- Do not claim a build is release-ready unless the production frontend build, Storybook build, and Docker builds actually passed.
- When cutting a release, bump the version everywhere it is declared: `web/package.json`, `api/app/config.py`, both spots in `api/app/main.py`, `web/index.html`, the footer in `web/src/App.vue`, and the README's "Current version" line. `tests/test_release_consistency.py` checks that they agree and that `docs/notes/<version>.md` exists.
- Update `docs/USER_GUIDE.md` when user-visible behavior changes; it describes the current release, not history.

## Conventions

- Every source file carries `Copyright 2026 Aaron John Schlosser, PhD.` (comment header). New files should too.
- **Internationalization:** English (`en-US`) and Québec French (`fr-CA`) are first-class. Any new user-facing string must be added to both `api/app/locales` / frontend locale modules with identical key sets and placeholders; parity is regression-tested. No hard-coded UI strings.
- **Accessibility:** keyboard operability, visible focus, semantic status communication, a 12px minimum type size, and WCAG 2.0 AA. Add or update Storybook stories for new components; the a11y addon and axe tests are gates.
- **Surfaces:** floating panels use the solid/raised/overlay/glass surface tokens; overlays must be opaque and glass at least 90% opaque. No text may bleed through popovers.
- **Provenance and LLM output:**
  - Keep deterministic and LLM values both, with confidence, reason, and whether the field was actually checked.
  - LLM values above the 65% confidence threshold and schema-valid populate fields; lower-confidence values stay as `proposed_value` suggestions.
  - Reviewer-confirmed document structure is authoritative over manifest and LLM inference.
  - Validate LLM output against closed vocabularies at the backend boundary, and sanitize model wrappers (fences, separators) only when absent from the source.
  - Bump the contract or prompt version identifiers (for example `derrida-scholarly-v12`, `derridai-record-metadata-v9`) when their semantics change.
- **Roles:** Researcher accounts must never receive full corpus text or mutate data; enforce this in the API, not just the UI.
- **Background work:** long operations are cancellable jobs (`jobs.py`) with visible progress; respect per-provider concurrency limits. Job state is process-local.
- **Chroma:** one writer per persistence path. The logical `_response_cache` collection is stored physically as `derridai_response_cache` and is a system cache, not a corpus store.
- **Secrets:** `.env` is git-ignored. Backups and provider profiles can contain API keys; never log or commit them.

## Working style

- Make focused changes; do not refactor or add abstractions beyond the task. Prefer editing existing files.
- Add a regression test for each behavior change, in a new or existing `tests/test_*.py` (and Vitest/Playwright tests for frontend behavior).
- Test behavior, not text. Do not add tests that only assert a string appears in a doc or source file, and do not hard-code the release version in tests; version agreement is covered once in `tests/test_release_consistency.py`.
- Run the relevant checks before reporting done, and report honestly which checks could not run.
- Commit as the repository owner: Aaron Schlosser, PhD <aaron@aaronschlosser.com>. Only commit when asked; never push or force-push without being asked.
