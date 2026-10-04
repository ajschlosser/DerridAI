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

This is the human-developer entry point for working on DerridAI. Read [AGENTS.md](AGENTS.md) when using coding agents, [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) before changing subsystem boundaries, and [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) before changing provenance, metadata, evidence, or scholarly semantics.

Read [docs/CODE_READABILITY.md](docs/CODE_READABILITY.md) before structural refactors. It defines the repository's naming/commenting conventions and the rule that readability changes must preserve provenance, authority, cancellation, conflict, and stale-state safeguards.

## Choose the owning area first

| Change | Primary guide |
| --- | --- |
| FastAPI/domain/persistence | [`api/README.md`](api/README.md), then [`api/app/README.md`](api/app/README.md) |
| Vue application | [`web/README.md`](web/README.md), then [`web/src/README.md`](web/src/README.md) |
| Reusable frontend UI | [`web/src/components/README.md`](web/src/components/README.md) |
| Frontend domain helpers | [`web/src/domain/README.md`](web/src/domain/README.md) |
| Corpus Builder | [`web/src/features/corpus-builder/README.md`](web/src/features/corpus-builder/README.md) and [`web/src/components/corpus-builder/README.md`](web/src/components/corpus-builder/README.md) |
| Pipeline Studio | [`api/app/pipelines/README.md`](api/app/pipelines/README.md) and [`web/src/components/pipelines/README.md`](web/src/components/pipelines/README.md) |
| Tests | [`tests/README.md`](tests/README.md) and [`web/tests/README.md`](web/tests/README.md) |

Do not start in a compatibility monolith merely because a symbol is re-exported there. Follow the local README to the module that owns the invariant.

## Supported development environment

CI is the compatibility baseline: Python 3.12, Node 22, npm via the checked-in `web/package-lock.json`, Chromium for Playwright, and Docker Compose for the full local stack. Using newer runtimes can expose dependency behavior that CI does not exercise; reproduce a CI failure on the CI versions before treating it as an application defect.

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
