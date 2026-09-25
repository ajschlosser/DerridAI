<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
# Static-analysis follow-ups

This is the current registry for intentional Ruff, mypy, ESLint, and TypeScript debt that remains visible in source/config suppressions. It is not a snapshot of line numbers from a past release.

When adding a suppression, give it a narrow reason and either attach it to an existing item below or add a new tracked item. When the underlying debt is removed, remove both the suppression and the registry item.

## Backend

- **SA-01 — legacy compact Python statements.** Expand E701/E702-style compact statements module-by-module with behavior-preserving diffs rather than mixing repository-wide formatting into feature work.
- **SA-02 — strict optional typing.** `mypy.ini` still has `strict_optional = False`; enable it only after nullable dictionary/payload boundaries are explicitly typed.
- **SA-07 — enrichment/checkpoint contracts.** Continue replacing broad dictionary payloads in enrichment/checkpoint orchestration with precise typed models where doing so clarifies real boundaries.
- **SA-18 — strict zip checks.** Enable Ruff `B905` only where equal-length invariants have been established; do not mechanically add `strict=True` to code whose truncation semantics are intentional.
- **SA-19 — Python formatting.** Apply `ruff format` in reviewed module-sized tranches together with SA-01 cleanup rather than as a noisy whole-repository rewrite.

Completed 0.61-era typing items and the old `main.py`-specific debt are preserved in git/release history and are no longer listed as open work.

## Frontend

- **SA-10 — remaining runtime compatibility code.** Remove unused runtime exports/callbacks only after tracing bridge/event consumers and preserving characterization coverage.
- **SA-12 — best-effort browser fallbacks.** Audit persistence/refresh/clipboard/teardown catches. User-relevant failures should be actionable; genuinely harmless cleanup failures may remain suppressed with a local explanation.
- **SA-13 — unused setup bindings.** Remove compatibility bindings as their owning workflows become Vue/domain-owned instead of disabling the rule broadly.
- **SA-14 — legacy regex/string escapes.** Simplify only with fixtures that pin matching/serialization semantics.
- **SA-15 — OCR Unicode character classes.** Verify character-class changes against real extraction/text-cleanup fixtures before changing semantics.
- **SA-16 — sparse Storybook fixtures.** Replace repeated `as any` story fixtures with reusable typed partial-data builders where that reduces noise without forcing stories to fabricate irrelevant domain state.

The former SA-11 “missing runtime symbol” inventory is retired: those exact names/locations no longer describe current source. A new undefined/stale-reference defect should fail lint/typecheck or receive a new issue tied to its current code path rather than resurrecting the historical item.

## Gate ownership

- Ruff is configured in `ruff.toml`.
- mypy is configured in `mypy.ini`.
- frontend lint/type gates are defined in `web/package.json` and TypeScript/ESLint config.
- repository-wide Prettier ownership is defined by `web/package.json`, `web/.prettierrc`, and the root `.prettierignore`; generated legacy DOM snapshots are excluded because formatting would alter characterization baselines.
- CI orchestration and path/shard behavior live in `.github/workflows/frontend.yml`.
- Accessibility regressions belong to Playwright/axe and focused semantic tests, not static-analysis suppressions.

Do not copy the historical suppression/line-number inventory back into this file; source-local comments are the precise location record and git history preserves the original audit.
