<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# AGENTS.md

Guidance for coding agents and contributors working on DerridAI. See [README.md](README.md) for the project overview, [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for feature behavior, and [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) for the scholarly rationale and which capabilities are implemented versus intended.

## What this project is

DerridAI is a local-first Docker application for building, auditing, and querying scholarly corpora of philosophical texts (Derrida in particular). PDFs become structured JSONL records via the Corpus Builder; records are reviewed with human and LLM input, stored in ChromaDB, and queried through an evidence-grounded RAG pipeline. It is a research tool: correctness, provenance, and auditability matter more than cleverness.

## Layout

- `api/app/` — FastAPI backend (Python 3.12). Key modules: `main.py` (routes), `corpus_builder.py` (PDF → records pipeline, very large), `chroma_store.py`, `rag.py`, `jobs.py` (background operations), `llm.py` / `llm_tools.py` (Ollama and OpenAI-compatible providers), `auth.py`, `researcher_view.py`, `persistence.py` / `system_store.py` (SQLite), `locales/` (`en_us.py`, `fr_ca.py`), `config.py` (env-driven settings).
- `web/src/` — Vue 3 + TypeScript frontend: `views/`, `components/` (each with a `.stories.ts`), `stores/` (Pinia), `router/`, `api/`, `composables/`, `domain/`, `runtime/` (legacy feature renderers being migrated view by view), `types/`.
- `web/tests/frontend/` (Vitest + Vue Test Utils + happy-dom) and `web/tests/e2e/` (Playwright + axe-core).
- `tests/` — Python regression suite; topical `test_<subject>.py` files (named for the behavior under test, not a release; see `tests/README.md`), and `tests/fixtures/`.
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
- When cutting a release, bump the version everywhere it is declared: `web/package.json`, `api/app/config.py`, `web/index.html`, and the README's "Current version" line. The API constructor, backup manifest, App.vue footer, and AuthScreen read those values (and the build's git commit) rather than duplicating the string. `tests/test_release_consistency.py` checks that they agree and that `docs/notes/<version>.md` exists.
- **Tag the same commit.** After the bump commit exists and `APP_VERSION` on that commit is the new version, create an annotated tag `v<version>` with the notes title (for example `v0.62.3` / `0.62.3 - Vigilant Viper`) and push it: `git tag -a "v$VERSION" -m "$VERSION - $NAME"` then `git push origin "v$VERSION"`. Do not skip the tag, do not retag a name that already exists, and do not point `vX.Y.Z` at a tree whose declared version is something else. Notes without a matching `v*` tag are not a finished release.
- Update `docs/USER_GUIDE.md` when user-visible behavior changes; it describes the current release, not history.

## Conventions

- Every source file carries `Copyright 2026 Aaron John Schlosser, PhD.` (comment header). New files should too.
- **Internationalization:** English (`en-US`) and French (`fr-CA`) are first-class. Any new user-facing string must be added to both `api/app/locales` / frontend locale modules with identical key sets and placeholders; parity is regression-tested. No hard-coded UI strings.
- **Accessibility:** keyboard operability, visible focus, semantic status communication, a 12px minimum type size, and WCAG 2.0 AA. Add or update Storybook stories for new components; the a11y addon and axe tests are gates.
- **Surfaces:** floating panels use the solid/raised/overlay/glass surface tokens; overlays must be opaque and glass at least 90% opaque. No text may bleed through popovers.
- **Scholarly provenance is the core requirement.** The chain is source → passage → speaker → position holder → stance → proposition → exact evidence → citation → claim. Preserve it.
  - Never flatten `speaker`, `quoted_speaker`, and `position_holder` into "Derrida says". A passage Derrida wrote often states another philosopher's position, and editors' or translators' text is not Derrida's.
  - Never invent evidence, quotations, or citations. Citations and page numbers come from record IDs and metadata through deterministic code, not from the LLM.
  - Treat wrong attribution, fabricated quotes, wrong work or page, dropped negation, and editorial text taken as Derrida's as high-severity failures, not minor quality issues.
  - Preserve edition, translation, and page information. Keep the corpus authoritative; vector stores are derived data.
- **Provenance and LLM output:**
  - Keep deterministic and LLM values both, with confidence, reason, and whether the field was actually checked.
  - LLM values above the 65% confidence threshold and schema-valid populate fields; lower-confidence values stay as `proposed_value` suggestions.
  - Reviewer-confirmed document structure is authoritative over manifest and LLM inference.
  - Validate LLM output against closed vocabularies at the backend boundary, and sanitize model wrappers (fences, separators) only when absent from the source.
  - LLM output is untrusted until validated. Deterministic code owns IDs, citations, page lookup, exact-quote checks, schema checks, dedup, and embedding compatibility; prefer it over another LLM prompt.
  - Unresolved or uncertain results (segmentation, metadata, attribution, thin evidence) stay visible and marked for review. Never manufacture certainty, and never silently swallow errors that can affect correctness.
  - Segmentation must conserve text: no text lost, invented, duplicated, or reordered.
  - Preprocessing is conservative. Do not strip stopwords or aggressively normalize; negations and qualifiers (*not, without, if, only*) can carry the proposition.
  - Bump the contract or prompt version identifiers (for example `derrida-scholarly-v12`, `derridai-record-metadata-v9`) when their semantics change.
- **Roles:** Researcher accounts must never receive full corpus text or mutate data; enforce this in the API, not just the UI.
- **Only send what is needed** in API requests, LLM prompts, and updates (for example, a PATCH carries only the changed field). Use operation-specific schemas rather than one giant record payload.
- **Reproducibility:** RAG runs keep enough state to inspect and rerun them. Grades stay attached to their run and record the grader model; warn on self-grading.
- **Background work:** long operations are cancellable jobs (`jobs.py`) with visible progress; respect per-provider concurrency limits. Job state is process-local.
- **Chroma:** one writer per persistence path. The logical `_response_cache` collection is stored physically as `derridai_response_cache` and is a system cache, not a corpus store.
- **Secrets:** `.env` is git-ignored. Backups and provider profiles can contain API keys; never log or commit them.

## Working style

- Inspect the actual code before asserting how something works. `docs/PROJECT_CONTEXT.md` mixes implemented and intended design; when the code and a description disagree, say so and do not treat intended design as implemented.
- Make focused changes; do not refactor or add abstractions beyond the task. Prefer editing existing files.
- Add a regression test for each behavior change, in a new or existing `tests/test_*.py` (and Vitest/Playwright tests for frontend behavior).
- Test behavior, not text. Do not add tests that only assert a string appears in a doc or source file, and do not hard-code the release version in tests; version agreement is covered once in `tests/test_release_consistency.py`.
- Run the relevant checks before reporting done, and report honestly which checks could not run.
- Commit as the repository owner: Aaron Schlosser, PhD <aaron@aaronschlosser.com>. Only commit when asked; never push or force-push without being asked.
