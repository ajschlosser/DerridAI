<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# AGENTS.md

Guidance for coding agents and contributors working on DerridAI. See [README.md](README.md) for the project overview, [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for feature behavior, and [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) for the scholarly rationale and which capabilities are implemented versus intended.

## Multi-agent collaboration

Copilot, Claude, Cursor/Grok, and ChatGPT/Codex may work on this repository concurrently. Treat the working tree, shared APIs, schemas, prompts, and documentation as shared contracts:

- Inspect current changes before editing; preserve unrelated work and never reset, rewrite, or delete another agent's changes.
- Keep commits focused and communicate cross-cutting contract changes in the relevant code or documentation. Avoid drive-by formatting and speculative refactors.
- Prefer small, composable changes that are easy to review and merge. Resolve conflicts by preserving behavior and provenance, not by choosing one agent's version wholesale.
- Do not assume an agent's plan or documentation reflects implementation; verify the actual code and tests.
- Coordinate changes to generated files, migrations, release metadata, locale parity, and public API schemas so only one authoritative edit is made.

## What this project is

DerridAI is a local-first Docker application for building, auditing, and querying scholarly corpora of philosophical texts (Derrida in particular). Corpus Builder accepts multiple source-media kinds (including PDF, text/RTF/DOCX, images, audio, URLs, and Project Gutenberg), preserves source/extractor provenance, and turns source spans into reviewable scholarly records. Canonical corpus/review state remains authoritative; Chroma collections, embeddings, caches, and semantic-memory indexes are derived/rebuildable projections used by Search, Research, and metadata enrichment. It is a research tool: correctness, provenance, and auditability matter more than cleverness.

## Layout

- `api/app/` — FastAPI backend (Python 3.12). `main.py` is only the ASGI entrypoint; `application.py` builds the app and composes `routers/`. Corpus building is split across `corpus_builder.py` plus focused `corpus_*` and `source_*` modules. Background managers live in `job_llm.py`, `job_rag.py`, `job_tools.py`, and `job_upsert.py`; `jobs.py` is a compatibility export layer and `job_state.py` owns shared durable checkpoint/error behavior. Metadata memory/provenance lives in `metadata_*` and `provenance_memory.py`. Other major boundaries include `chroma_store.py`, `rag.py`, `llm.py` / `llm_tools.py`, `auth.py`, `researcher_view.py`, `persistence.py` / `system_store.py`, `locales/`, and `config.py`.
- `web/src/` — Vue 3 + TypeScript frontend: `views/`, `components/` (with Storybook coverage where applicable), `stores/` (Pinia), `router/`, `api/`, `composables/`, `domain/`, `runtime/` (remaining compatibility/runtime orchestration), `types/`.
- `web/tests/frontend/` (Vitest + Vue Test Utils + happy-dom) and `web/tests/e2e/` (Playwright + axe-core).
- `tests/` — Python regression suite; topical `test_<subject>.py` files (named for the behavior under test, not a release; see `tests/README.md`), and `tests/fixtures/`.
- `docs/` — current architecture/domain contracts plus `docs/notes/<version>.md` historical release notes. Do not create one-off progress/status documents when an authoritative current document or release note can carry the information.
- `data/` — runtime state (Chroma, SQLite, models), git-ignored except `.gitkeep`. Never commit its contents.
- `docker-compose.yml`, `.env.example`, `scripts/` (diagnostics, and `migrate-css-tokens.py` for moving styles onto design tokens), `.github/workflows/frontend.yml` (CI).

## Commands

```bash
pytest -q -n auto --dist=worksteal         # backend + release regression tests (from repo root)
pytest -q -m contract tests/test_frontend_api_contract.py
python -m compileall -q api/app             # syntax check
cd web && npm run format:repo:check         # repository-wide Prettier check
cd web && npm run typecheck                 # vue-tsc
cd web && npm run typecheck:tests           # test/config TypeScript
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
- When cutting a release, bump the version everywhere it is declared: `web/package.json`, `api/app/config.py`, `web/index.html`, and the README's "Current version" line. The API constructor, backup manifest, AppBuildInfo (sign-in, user menu, and Settings), and AuthScreen read those values (and the build's git commit) rather than duplicating the string. `tests/test_release_consistency.py` checks that they agree and that `docs/notes/<version>.md` exists.
- **Tag the same commit.** After the bump commit exists and `APP_VERSION` on that commit is the new version, create an annotated tag `v<version>` with the notes title (for example `v0.62.3` / `0.62.3 - Vigilant Viper`) and push it: `git tag -a "v$VERSION" -m "$VERSION - $NAME"` then `git push origin "v$VERSION"`. Do not skip the tag, do not retag a name that already exists, and do not point `vX.Y.Z` at a tree whose declared version is something else. Notes without a matching `v*` tag are not a finished release.
- Update `docs/USER_GUIDE.md` when user-visible behavior changes; it describes current behavior, not history.
- Treat versioned design/status documents and `docs/notes/` as historical records. Current architecture and operating contracts belong in `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/USER_GUIDE.md`, `SPECIFICATION.md`, or a focused unversioned contract document. Do not create a new progress/status file when an existing authoritative document can be updated.

## Conventions

- Every source file carries `Copyright 2026 Aaron John Schlosser, PhD.` (comment header). New files should too.
- **Internationalization:** English (`en-US`) and French (`fr-CA`) are first-class. Any new user-facing string must be added to both `api/app/locales` / frontend locale modules with identical key sets and placeholders; parity is regression-tested. No hard-coded UI strings.
- **Accessibility:** keyboard operability, visible focus, semantic status communication, a 12px minimum type size, and WCAG 2.2 AA in light and dark. Colours, type sizes and status styles come from tokens (`web/src/styles/tokens.css`, see `docs/DESIGN_TOKENS.md`); do not add literal hex colours to component styles, which a Vitest ratchet enforces. Add or update Storybook stories for new components; the a11y addon and axe tests are gates.
- **Surfaces:** floating panels use the solid/raised/overlay/glass surface tokens; overlays must be opaque and glass at least 90% opaque. No text may bleed through popovers.
- **Scholarly provenance is the core requirement.** The chain is source → passage → speaker → position holder → stance → proposition → exact evidence → citation → claim. Preserve it.
  - Never flatten `speaker`, `quoted_speaker`, and `position_holder` into "Derrida says". A passage Derrida wrote often states another philosopher's position, and editors' or translators' text is not Derrida's.
  - Never invent evidence, quotations, or citations. Citations and page numbers come from record IDs and metadata through deterministic code, not from the LLM.
  - Treat wrong attribution, fabricated quotes, wrong work or page, dropped negation, and editorial text taken as Derrida's as high-severity failures, not minor quality issues.
  - Preserve edition, translation, and page information. Keep the corpus authoritative; vector stores are derived data.
- **Provenance and LLM output:**
  - Keep deterministic and LLM values both, with confidence, reason, and whether the field was actually checked.
  - Every schema-valid non-empty LLM value is populated so a reviewer can inspect it; population is not verification. Missing/low confidence can keep the field pending review, while `autofilled=true` is reserved for calibrated autofill (90% blended confidence by default, valid cited evidence, and no suspension from poor reviewer precision).
  - Reviewer-confirmed document structure is authoritative over manifest and LLM inference.
  - Validate LLM output against closed vocabularies at the backend boundary, and sanitize model wrappers (fences, separators) only when absent from the source.
  - LLM output is untrusted until validated. Deterministic code owns IDs, citations, page lookup, exact-quote checks, schema checks, dedup, and embedding compatibility; prefer it over another LLM prompt.
  - Unresolved or uncertain results (segmentation, metadata, attribution, thin evidence) stay visible and marked for review. Never manufacture certainty, and never silently swallow errors that can affect correctness.
  - Segmentation must conserve text: no text lost, invented, duplicated, or reordered.
  - Preprocessing is conservative. Do not strip stopwords or aggressively normalize; negations and qualifiers (_not, without, if, only_) can carry the proposition.
  - Bump the contract or prompt version identifiers (for example `derrida-scholarly-v12`, `derridai-record-metadata-v9`) when their semantics change.
- **Source ingestion and media fidelity:**
  - Treat uploaded/remote source content as inert data. Never execute embedded document content, macros, scripts, fields, external relationships, or active objects.
  - Enforce bounded bytes, decompression/expansion, image pixels, audio duration, probe/transcription time, nesting/depth, and supported-format/codec limits before expensive processing.
  - Preserve immutable extracted source plus extractor/tool/version provenance. Human cleanup/transcription revisions are reviewable revisions, not silent rewrites of extraction history.
  - Model evidence coordinates according to the source medium. PDFs may use physical/printed pages; audio uses time ranges/speakers; text, image, URL, and Gutenberg sources must not inherit meaningless PDF-only controls or page semantics.
- **Metadata memory and progressive retrieval:**
  - Canonical reviewed records/RecordRevisions, field assertions, review decisions, and bound evidence are authoritative. Metadata exemplars and their Chroma/embedding projection are derived and rebuildable.
  - Never promote unresolved or unreviewed model output into trusted precedent. Corrections may preserve a rejected model value as negative evidence; reviewer-confirmed absence is reusable only when explicit reviewed source evidence is bound to the no-value decision.
  - Metadata-schema retrieval policy is field/group scoped. The active contract is `enabled`, `max_items`, `min_similarity`, `include_corrections`, and `include_confirmed_absence`; do not revive migrated legacy routing flags.
  - Metadata exemplar memory is separate from Research response/claim memory. Do not route one into the other merely because both use retrieval or a vector projection.
  - Resolve precedent/support bindings against stable record/revision/source identities and surface stale or unresolvable bindings instead of silently substituting newer text.
- **Roles:** Researcher accounts must never receive full corpus text or mutate data; enforce this in the API, not just the UI.
- **Only send what is needed** in API requests, LLM prompts, and updates (for example, a PATCH carries only the changed field). Use operation-specific schemas rather than one giant record payload.
- **Reproducibility:** RAG runs keep enough state to inspect and rerun them. Grades stay attached to their run and record the grader model; warn on self-grading.
- **Background work:** long operations are cancellable jobs with visible progress; respect per-provider concurrency limits. Active execution is process-local, but job snapshots/history are durably mirrored to SQLite. After restart, interrupted queued/running/cancelling work is marked failed rather than silently replayed. Keep job-specific behavior in the owning `job_*.py` manager instead of growing `jobs.py`.
- **Chroma:** one writer per persistence path. The logical `_response_cache` collection is stored physically as `derridai_response_cache` and is a system cache, not a corpus store.
- **Secrets:** `.env` is git-ignored. Backups and provider profiles can contain API keys; never log or commit them.

## Working style

- Inspect the actual code before asserting how something works. `docs/PROJECT_CONTEXT.md` mixes implemented and intended design; when the code and a description disagree, say so and do not treat intended design as implemented.
- Make focused changes; do not refactor or add abstractions beyond the task. Prefer editing existing files.
- Add a regression test for each behavior change, in a new or existing `tests/test_*.py` (and Vitest/Playwright tests for frontend behavior).
- Test behavior, not text. Do not add tests that only assert a string appears in a doc or source file, and do not hard-code the release version in tests; version agreement is covered once in `tests/test_release_consistency.py`.
- Run the relevant checks before reporting done, and report honestly which checks could not run. For handoff/documentation work, keep README and CONTRIBUTING setup commands executable from a clean checkout and keep the repository-wide Prettier check green.
- Commit as the repository owner: Aaron Schlosser, PhD <aaron@aaronschlosser.com>. Only commit when asked; never push or force-push without being asked.

## Saving tokens and execution time

- Act on the first reasonable plan. Do not re-derive settled decisions or narrate options that will not be taken.
- Prefer scripts and one combined command over repeated hand edits and small commands.
- Limit command output with `tail`, `grep -E`, `cut -c1-160`, and `head`. Read large files by line range and verify current sizes rather than relying on historical monolith counts.
- Run long jobs in the background and poll once. Do not use short sleep-poll loops.
- After an edit succeeds, do not re-read the entire file; inspect only when validation or an uncertain merge requires it.
- Write tests once against the legacy behavior, then make a focused implementation change rather than iterating through avoidable failures.
- Batch type-check fixes, preferably with one scripted transformation when signatures share the same cause.
- If the work is consuming substantial context or tokens, preserve a concise hand-off in the relevant issue/PR or authoritative document instead of creating a repository-level progress log.

## Design and engineering principles

- Prefer simple, explicit designs with one source of truth, narrow interfaces, stable contracts, and deterministic behavior.
- Separate domain logic from transport, persistence, presentation, and provider integrations; keep side effects at boundaries.
- Make invalid states difficult to represent: validate at boundaries, use precise schemas and types, and fail explicitly with actionable errors.
- Preserve backward compatibility deliberately. Version migrations, API/schema changes, prompt contracts, and persisted data; document intentional breaks.
- Favor idempotent, cancellable, observable operations with bounded resource use. Never hide errors that affect data integrity, provenance, security, or user decisions.
- Design for secure defaults: least privilege, server-side authorization, strict input validation, safe secret handling, dependency hygiene, and no sensitive data in logs.
- Treat accessibility, internationalization, responsive behavior, and keyboard operation as acceptance criteria, not polish.
- Optimize only after measuring. Prefer readable code, deterministic tests, and maintainable abstractions over cleverness or premature caching.
- Keep changes reversible and auditable: meaningful names, focused diffs, regression coverage for behavior, and documentation for user-visible or operational changes.
