<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# Contributing

Read [AGENTS.md](AGENTS.md) for conventions (i18n parity, accessibility, provenance rules, roles, release-note format) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the code is organized.

## Setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r api/requirements.txt -r api/requirements-dev.txt pytest
cd web && npm ci --no-audit --no-fund
```

Backend tests need no environment setup: `tests/conftest.py` points storage at a temporary directory (and leaves any value CI has already set alone). **Do not `export` `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH`, or `CHROMA_PATH` in your shell.** `docker-compose.yml` interpolates the same names, so an exported test path is picked up by the next `docker compose up` and the API container crash-loops on a host path that does not exist inside it.

## CI gates

`.github/workflows/frontend.yml` keeps the historical `frontend` required check, but that check now aggregates independent frontend gates so expensive browser coverage runs concurrently and failures surface earlier. A changed-path classifier skips backend compute for frontend-only changes and frontend compute for backend-only changes; workflow and shared-script changes deliberately exercise both sides.

| Gate | Command / responsibility |
| --- | --- |
| Backend lint | `pip install -r api/requirements-dev.txt && ruff check api/app tests` |
| Backend types | `pip install mypy==2.3.1 && mypy` (config in `mypy.ini`; `check_untyped_defs` is on; runtime/ML dependencies are not installed) |
| Frontend lint | `cd web && npm run lint` (ESLint, zero warnings) |
| Backend tests | Runtime requirements except the optional cross-encoder package, then `python -m compileall -q api/app && pytest -q`; reranker-unavailable behavior is exercised through the existing fallback path |
| Frontend static | `cd web && npm run typecheck && npm run test:unit && npm run build:ci && npm run build-storybook` |
| Legacy DOM regression | `cd web && npm run build:ci && npm run test:e2e:legacy`; CI shards the characterization suite across two runners |
| Composed UI / app E2E | `cd web && npm run build:ci && npm run build-storybook && npm run test:e2e` |
| Corpus Builder WCAG 2.2 AA sweep | `cd web && npm run build-storybook && npm run test:e2e:a11y` |

Install Chromium once for local browser runs with `cd web && npx playwright install chromium`. `npm run test:frontend` chains all frontend gates for a complete local pass.

In CI, both composed browser coverage and the legacy DOM characterization suite are sharded. Browser jobs restore the shared Chromium cache, while only one designated E2E shard populates a cold cache, avoiding simultaneous cache writes. Composed coverage runs against the built Storybook rather than Storybook's development server. The global Playwright project uses desktop Chromium once; tests that require laptop/mobile geometry set the viewport explicitly. Static Storybook builds disable the addon's automatic axe pass because Playwright owns the CI axe scan, avoiding two concurrent accessibility engines examining the same story.

The e2e run also serves the production build on port 5199 to render the real Vue views against a mock API (`web/tests/e2e/support`). For an individual local browser command, build the artifact it needs first. If port 6006 or 5199 is busy, set `STORYBOOK_PORT` or `APP_PORT`; do not weaken a gate to get past a local problem.

## Working rules

- Keep changes focused; one concern per commit with a descriptive message.
- Add a regression test for each behavior change. Test behavior, not text; do not hard-code the release version in tests.
- Do not suppress an exception silently where it can affect segmentation, metadata, attribution, citation, evidence binding, or durable operation state: surface it as a build warning, failed status, or propagated error. If a swallow is genuinely harmless, comment why.
- Suppressions for Ruff, mypy, or ESLint need a justification and an entry in `docs/STATIC_ANALYSIS_FOLLOWUPS.md`.
- Release notes go in `docs/notes/<version>.md` and are indexed in `CHANGELOG.md`, not the README. When cutting a release, bump every declared version (see AGENTS.md), create an annotated git tag `v<version>` on that bump commit, and push the tag. `tests/test_release_consistency.py` verifies the declared strings and notes file; the tag is the git object that makes the release retrievable.
- Never commit `.env`, `data/`, or provider API keys.
