<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# Contributing

Read [AGENTS.md](AGENTS.md) for conventions (i18n parity, accessibility, provenance rules, roles, release-note format) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the code is organized.

## Setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r api/requirements.txt -r api/requirements-dev.txt pytest
cd web && npm install --no-audit --no-fund
```

Backend tests need no environment setup: `tests/conftest.py` points storage at a temporary directory (and leaves any value CI has already set alone). **Do not `export` `CHROMA_DATA_ROOT`, `AUTH_DB_PATH`, `SYSTEM_DB_PATH`, or `CHROMA_PATH` in your shell.** `docker-compose.yml` interpolates the same names, so an exported test path is picked up by the next `docker compose up` and the API container crash-loops on a host path that does not exist inside it.

## CI gates

`.github/workflows/frontend.yml` runs five jobs (backend lint, backend types, frontend lint, backend, frontend); all must pass. Run them locally from the repository root unless noted.

| Job | Command |
| --- | --- |
| Backend lint | `pip install -r api/requirements-dev.txt && ruff check api/app tests` |
| Backend types | `mypy` (config in `mypy.ini`; `check_untyped_defs` is on) |
| Frontend lint | `cd web && npm run lint` (ESLint, zero warnings) |
| Backend tests | `python -m compileall -q api/app && pytest -q` |
| Frontend typecheck | `cd web && npm run typecheck` (strict vue-tsc) |
| Frontend unit | `cd web && npm run test:unit` (Vitest) |
| Production build | `cd web && npm run build` |
| Storybook build | `cd web && npm run build-storybook` |
| Composed UI, opacity, WCAG 2.2 AA (light and dark) | `cd web && npx playwright install chromium && npm run test:e2e` (Playwright + axe) |

`cd web && npm run test:frontend` chains typecheck, unit, build, Storybook build, and e2e. The e2e run also serves the production build on port 5199 to render the real Vue views against a mock API (`web/tests/e2e/support`), so run `npm run build` first. If port 6006 or 5199 is busy, set `STORYBOOK_PORT` or `APP_PORT`; do not weaken a gate to get past a local problem.

## Working rules

- Keep changes focused; one concern per commit with a descriptive message.
- Add a regression test for each behavior change. Test behavior, not text; do not hard-code the release version in tests.
- Do not suppress an exception silently where it can affect segmentation, metadata, attribution, citation, evidence binding, or durable operation state: surface it as a build warning, failed status, or propagated error. If a swallow is genuinely harmless, comment why.
- Suppressions for Ruff, mypy, or ESLint need a justification and an entry in `docs/STATIC_ANALYSIS_FOLLOWUPS.md`.
- Release notes go in `docs/notes/<version>.md` and are indexed in `CHANGELOG.md`, not the README. When cutting a release, bump every declared version (see AGENTS.md), create an annotated git tag `v<version>` on that bump commit, and push the tag. `tests/test_release_consistency.py` verifies the declared strings and notes file; the tag is the git object that makes the release retrievable.
- Never commit `.env`, `data/`, or provider API keys.
