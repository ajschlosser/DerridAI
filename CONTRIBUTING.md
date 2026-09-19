<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# Contributing

Read [AGENTS.md](AGENTS.md) for conventions (i18n parity, accessibility, provenance rules, roles, release-note format) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the code is organized.

## Setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r api/requirements.txt -r api/requirements-dev.txt pytest
cd web && npm install --no-audit --no-fund
```

Backend tests write to disk, so point them at a scratch directory (CI uses `/tmp/derridai-data`):

```bash
export CHROMA_DATA_ROOT=$PWD/.test-data CHROMA_PATH=$PWD/.test-data/chroma
export AUTH_DB_PATH=$PWD/.test-data/.home/derridai-auth.sqlite3
export SYSTEM_DB_PATH=$PWD/.test-data/.home/derridai-system.sqlite3
mkdir -p .test-data/.home
```

## CI gates

`.github/workflows/frontend.yml` runs six jobs; all must pass. Run them locally from the repository root unless noted.

| Job | Command |
| --- | --- |
| Backend lint | `pip install ruff==0.16.8 && ruff check api/app` |
| Backend types | `mypy` (config in `mypy.ini`) |
| Frontend lint | `cd web && npm run lint` (ESLint, zero warnings) |
| Backend tests | `python -m compileall -q api/app && pytest -q` |
| Frontend typecheck | `cd web && npm run typecheck` (strict vue-tsc) |
| Frontend unit | `cd web && npm run test:unit` (Vitest) |
| Production build | `cd web && npm run build` |
| Storybook build | `cd web && npm run build-storybook` |
| Composed UI, opacity, WCAG 2.0 AA | `cd web && npx playwright install chromium && npm run test:e2e` (Playwright + axe) |

`cd web && npm run test:frontend` chains typecheck, unit, build, Storybook build, and e2e. If port 6006 is busy, use a Playwright config that points at another Storybook port; do not weaken a gate to get past a local problem.

## Working rules

- Keep changes focused; one concern per commit with a descriptive message.
- Add a regression test for each behavior change. Test behavior, not text; do not hard-code the release version in tests.
- Do not suppress an exception silently where it can affect segmentation, metadata, attribution, citation, evidence binding, or durable operation state: surface it as a build warning, failed status, or propagated error. If a swallow is genuinely harmless, comment why.
- Suppressions for Ruff, mypy, or ESLint need a justification and an entry in `docs/STATIC_ANALYSIS_FOLLOWUPS.md`.
- Release notes go in `docs/notes/<version>.md` and are indexed in `CHANGELOG.md`, not the README. When cutting a release, bump every declared version (see AGENTS.md); `tests/test_release_consistency.py` verifies them.
- Never commit `.env`, `data/`, or provider API keys.
