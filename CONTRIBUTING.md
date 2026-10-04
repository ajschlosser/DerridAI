<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

# Contributing

This is the human-developer entry point for working on DerridAI. Read [AGENTS.md](AGENTS.md) when using coding agents, [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) before changing subsystem boundaries, [docs/CODE_READABILITY.md](docs/CODE_READABILITY.md) for naming/comment/refactoring conventions, and [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) before changing provenance, metadata, evidence, or scholarly semantics.

Read [docs/CODE_READABILITY.md](docs/CODE_READABILITY.md) before structural refactors. It defines the repository's naming/commenting conventions and the rule that readability changes must preserve provenance, authority, cancellation, conflict, and stale-state safeguards.

## Choose the owning area first

| Change                     | Primary guide                                                                                                                                                                             |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FastAPI/domain/persistence | [`api/README.md`](api/README.md), then [`api/app/README.md`](api/app/README.md)                                                                                                           |
| Vue application            | [`web/README.md`](web/README.md), then [`web/src/README.md`](web/src/README.md)                                                                                                           |
| Reusable frontend UI       | [`web/src/components/README.md`](web/src/components/README.md)                                                                                                                            |
| Frontend domain helpers    | [`web/src/domain/README.md`](web/src/domain/README.md)                                                                                                                                    |
| Corpus Builder             | [`web/src/features/corpus-builder/README.md`](web/src/features/corpus-builder/README.md) and [`web/src/components/corpus-builder/README.md`](web/src/components/corpus-builder/README.md) |
| Pipeline Studio            | [`api/app/pipelines/README.md`](api/app/pipelines/README.md) and [`web/src/components/pipelines/README.md`](web/src/components/pipelines/README.md)                                       |
| Tests                      | [`tests/README.md`](tests/README.md) and [`web/tests/README.md`](web/tests/README.md)                                                                                                     |

Do not start in a compatibility monolith merely because a symbol is re-exported there. Follow the local README to the module that owns the invariant.

## Supported development environment

CI is the compatibility baseline: Python 3.12, Node 22, npm via the checked-in `web/package-lock.json`, Chromium for Playwright, and Docker Compose for the full local stack. Using newer runtimes can expose dependency behavior that CI does not exercise; reproduce a CI failure on the CI versions before treating it as an application defect.

Before installing dependencies, verify that the expected tools resolve from the shell you will use for development:

```bash
python3.12 --version
node --version
npm --version
docker compose version
```

If `python3.12` is named differently on your platform, use the equivalent Python 3.12 executable consistently when creating the virtual environment.

## Bootstrap a clean checkout

From the repository root:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r api/requirements-dev.txt

cd web
npm ci --no-audit --no-fund
npx playwright install chromium
cd ..

cp .env.example .env
```

On Windows, activate the virtual environment with the shell-appropriate command and use `Copy-Item .env.example .env` in PowerShell.

`api/requirements-dev.txt` already includes runtime requirements, pytest, pytest-xdist, Ruff, and mypy. Do not install a second hand-maintained package list on top of it.

Backend tests need no storage environment setup. `tests/conftest.py` redirects application storage to temporary directories while preserving values deliberately supplied by CI. Do **not** globally export `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH`, or `CHROMA_PATH`: `docker-compose.yml` interpolates those names too, and a test-only host path can make the next container startup fail.

## Find the owning change surface

Start at the narrowest README for the area you are changing. The repository is intentionally layered; following the local ownership map is usually faster than searching outward from a large compatibility module.

- **Backend routes, reads, persistence, or domain logic:** start with [api/README.md](api/README.md) and [api/app/README.md](api/app/README.md). Put transport in `routers/`, reusable scholarly reads in `celf_queries/`, and domain behavior in the focused owning module.
- **Corpus Builder:** read both [the frontend feature map](web/src/features/corpus-builder/README.md) and [the component map](web/src/components/corpus-builder/README.md), then use [tests/README.md](tests/README.md) to locate topology, enrichment, review, or publication coverage. Do not add new domain behavior to `PdfCorpusBuilder.vue` or `corpus_builder.py` merely because those files still coordinate compatibility paths.
- **Frontend application work:** start with [web/README.md](web/README.md) and [web/src/README.md](web/src/README.md). Framework-light transformations belong in `domain/`; Vue lifecycle/state coordination belongs in composables/stores; network effects belong in `api/` or `realtime/`.
- **Research and pipelines:** use [api/app/pipelines/README.md](api/app/pipelines/README.md), [web/src/components/pipelines/README.md](web/src/components/pipelines/README.md), and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Retrieval scores are derived diagnostics; source/evidence/support binding is a separate deterministic authority concern.
- **Tests:** use [tests/README.md](tests/README.md) for pytest and [web/tests/README.md](web/tests/README.md) for Vitest/Playwright ownership. Prefer the smallest test file that owns the behavior rather than adding a new release-numbered test.
- **cELF, requirements, or provenance semantics:** read [SPECIFICATION.md](SPECIFICATION.md), [docs/requirements/README.md](docs/requirements/README.md), and [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) before changing object meanings or traceability relationships.

## Run the application

For end-to-end application work, prefer the compose stack so storage paths and service networking match production-like local behavior:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8000/api/live
```

The application is at <http://localhost:8181>. See the README for Ollama/model setup and optional compose profiles.

For frontend iteration against an API already listening on `127.0.0.1:8000`:

```bash
cd web
npm run dev
```

Vite proxies `/api` to that API. Storybook can run directly with `npm run storybook` or through `docker compose --profile dev up storybook`.

## Formatting and static analysis

Formatting is intentionally split by language/tool ownership.

From `web/`, run:

```bash
npm run format:repo
npm run format:repo:check
```

`format:repo` runs the pinned Prettier version over every Prettier-supported source, configuration, and documentation file in the repository. Generated legacy DOM snapshot HTML and build/runtime artifacts are excluded in `.prettierignore`; do not reformat those snapshots manually. The existing `npm run format` command remains frontend-directory-only for focused work.

Python static analysis remains separate:

```bash
ruff check api/app tests scripts/check_frontend_api_contract.py scripts/check_frontend_graphql_contract.py
mypy
```

Python formatting/style debt tracked in [docs/STATIC_ANALYSIS_FOLLOWUPS.md](docs/STATIC_ANALYSIS_FOLLOWUPS.md) is separate from Prettier. Do not mechanically rewrite Python modules in a feature PR just to reduce style debt; make those changes as deliberate, reviewable formatting/refactor work.

## Readability and documentation conventions

Human readability is a maintained quality attribute, not a cleanup phase reserved for later.

- **Name the domain concept.** Prefer `record_revision`, `boundary_block_id`, `selectedVersion`, or `normalizedQuery` over `data`, `item`, `x`, or `v` when the value survives beyond a tiny mathematical/indexing loop. Conventional coordinates and short loop indexes are fine when their meaning is immediate.
- **Python follows normal docstring conventions.** Modules, public classes/functions, and non-obvious private algorithms should use PEP 257-style docstrings. Describe the contract, invariant, or reason for the algorithm rather than narrating each statement.
- **TypeScript uses JSDoc where the contract is not obvious from the type.** Exported algorithms, transformations with authority/provenance implications, and compatibility shims should explain their semantics and failure assumptions. Local comments should explain why a branch exists, not restate the syntax.
- **Flatten difficult control flow.** Prefer guard clauses, named predicates, and small helpers to deeply nested conditionals or nested ternaries. Do not split a function merely to reduce line count when the extraction would hide the invariant or create a dependency cycle.
- **Comment state reconstruction, heuristics, and provenance boundaries.** A future reader should be able to tell why ordering, confidence thresholds, rollback logic, deterministic fallbacks, or source-conservation checks are safe.
- **Keep compatibility debt explicit.** Existing `Loose`/broad-dictionary boundaries and runtime bridges may be necessary, but new code should use precise local types and focused dependencies when practical. Do not keep “moved verbatim” comments after materially refactoring the code.
- **Avoid stale comments.** When behavior changes, update or remove nearby rationale, diagrams, README paths, and gotchas in the same change.

## Test commands

Backend/release regression:

```bash
python -m compileall -q api/app
pytest -q -n auto --dist=worksteal --ignore=tests/test_frontend_api_contract.py --ignore=tests/test_frontend_graphql_contract.py
```

Frontend/FastAPI (REST) and frontend/GraphQL operation contracts, checked independently:

```bash
pytest -q -m contract tests/test_frontend_api_contract.py
pytest -q -m contract tests/test_frontend_graphql_contract.py
```

Frontend static/unit/build:

```bash
cd web
npm run lint
npm run typecheck
npm run typecheck:tests
npm run test:unit
npm run build:ci
npm run build-storybook
```

Browser suites:

```bash
cd web
npm run test:e2e:legacy
npm run test:e2e
npm run test:e2e:a11y
```

The Storybook suites run against the static build, as CI does, so run `npm run build-storybook` (and `npm run build` for the app suites) first; the configs fail fast if it is missing. They never reuse a server that is already listening: if port 6006 or 5199 is busy, set `STORYBOOK_PORT` or `APP_PORT`; do not weaken a test gate to work around a local port collision.

See [tests/README.md](tests/README.md) for pytest markers, test taxonomy, and focused test guidance.

For normal local handoff, `scripts/preflight.sh` derives the required gates from the diff, checks branch freshness against `origin/master`, verifies generated artifacts when relevant, and runs the applicable backend/frontend static and unit checks. Playwright/browser work stays in CI by design.

```bash
scripts/preflight.sh
```

Use the explicit commands above when debugging one gate or when your platform cannot run the shell script.

## CI gates

`.github/workflows/frontend.yml` keeps the historical `frontend` aggregate check while dispatching independent work in parallel.

| Gate                        | Command / responsibility                                                                |
| --------------------------- | --------------------------------------------------------------------------------------- |
| Repository format           | `cd web && npm run format:repo:check` for Prettier-supported tracked source/docs/config |
| Backend lint                | `ruff check api/app tests scripts/check_frontend_*_contract.py`                         |
| Backend types               | `mypy` using `mypy.ini`                                                                 |
| Frontend lint               | `cd web && npm run lint`                                                                |
| Backend tests               | compile Python, then parallel pytest excluding the focused contract test                |
| Frontend / FastAPI contract | live FastAPI OpenAPI routes versus frontend requests                                    |
| Frontend / GraphQL contract | frontend `.graphql` operations validated against the live Strawberry schema             |
| Frontend static             | typecheck app/tests, unit tests, production build, Storybook build                      |
| Legacy DOM regression       | sharded characterization suite                                                          |
| Composed UI / app E2E       | sharded production/Storybook Playwright coverage                                        |
| WCAG 2.2 AA sweep           | focused Playwright/axe accessibility coverage                                           |

Browser jobs share the Chromium cache while avoiding concurrent writes. Composed coverage runs against built artifacts rather than development servers so CI tests what is actually shipped.

## Change rules

- Keep a change focused and make commit messages describe the concern, not the implementation session.
- Add regression coverage for behavior changes. Test behavior, not the presence of source/doc strings.
- Preserve provenance. Do not silently swallow failures that can affect segmentation, metadata, attribution, citation, evidence binding, or durable operation state.
- Keep generated/derived projections distinct from canonical scholarly state. Chroma indexes, caches, metadata-exemplar projections, and Research-memory indexes are rebuildable; reviewed records/evidence/revisions are authoritative.
- Enforce Researcher permissions at the API boundary, not only in Vue.
- Treat source files as untrusted inert data. Never execute embedded document content.
- Maintain English/Canadian-French key parity and WCAG 2.2 AA behavior for UI changes.
- A Ruff, mypy, or ESLint suppression needs a narrow source comment and an entry in [docs/STATIC_ANALYSIS_FOLLOWUPS.md](docs/STATIC_ANALYSIS_FOLLOWUPS.md).
- Release notes go in `docs/notes/<version>.md` and are indexed in `CHANGELOG.md`; do not put release notes in the README.
- Never commit `.env`, `data/`, API keys, provider credentials, generated build output, or local browser/test artifacts.

## Common contributor traps

- `web/src/runtime/runtime.js` is a compatibility layer. New feature logic belongs in typed domain/composable/component modules when an owning boundary already exists.
- `api/app/corpus_builder.py` and `api/app/chroma_store.py` remain large compatibility/orchestration surfaces. Prefer focused `corpus_*`, `source_*`, pipeline, query, or store modules rather than adding another unrelated responsibility.
- Chroma and browser caches are derived/rebuildable. Do not use them as a shortcut around canonical Records, revisions, FieldAssertions, review decisions, or evidence bindings.
- GraphQL is read-only. Commands and mutations belong in REST; realtime messages notify clients to refetch and are not canonical state.
- Generated GraphQL/SDK/site assets must be changed through their generators. A hand edit may appear correct locally and still fail the freshness gate.
- The default host-provider URLs use `host.docker.internal`; Compose maps that name to the host gateway so the same documented setup works on Docker Desktop and native Docker Engine.
- Playwright/Storybook suites use built artifacts and dedicated ports. Build first, and change the configured test port when one is occupied rather than reusing an arbitrary running dev server.
- Legacy DOM snapshots are characterization artifacts. Regenerate them only for a reviewed, intentional behavior change, and do not reformat them.
- English and Canadian-French frontend keys are parity-checked. Adding a visible string to only one locale will fail validation.
- REST and GraphQL contract tests are separate from the broad backend pytest run. Transport/schema changes need both focused contract files even when the general suite is green.

## Before handing a change to another developer

Run the smallest set of checks that covers the change, then report exactly what ran. For a cross-cutting change, the expected local handoff is:

```bash
cd web && npm run format:repo:check && npm run lint && npm run typecheck && npm run typecheck:tests && npm run test:unit
cd ..
ruff check api/app tests scripts/check_frontend_api_contract.py scripts/check_frontend_graphql_contract.py
mypy
pytest -q -n auto --dist=worksteal --ignore=tests/test_frontend_api_contract.py --ignore=tests/test_frontend_graphql_contract.py
pytest -q -m contract tests/test_frontend_api_contract.py
pytest -q -m contract tests/test_frontend_graphql_contract.py
```

Add the relevant build/Storybook/Playwright gates when frontend rendering or browser behavior changed. If a required check could not be run, state why in the PR instead of implying that it passed.
