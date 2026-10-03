# Progressive loading UX progress

Checkpoint: 2026-10-02. Branch: `feat/progressive-loading-ux`.

## Completed

- Works and Record detail retain useful content during refresh, distinguish initial loading from refresh, and reject stale selections.
- Delayed route-module feedback retains the current page and offers retry/reload after import failures.
- Vector Stores collections load independently of health/provider discovery. Refresh failures retain the collection rail; provider failures are local and dependent controls wait. Cached revisits and unsaved settings are preserved.
- Implementation: `9d079838`, `8728c5a5`, `15a320ba`. Current master `27b754c3` merged cleanly as `6f4c4010`, including the latest Vue job-review dialog migration. No Corpus Builder implementation or legacy runtime files are changed relative to master.

## Validation and limitations

- Before the final master merge: full frontend lint, app/test typechecks, 1,524 unit tests, production build, and Storybook build passed. Targeted browser coverage passed all 24 distinct cases across route feedback, Works, Record, and Vector Stores after correcting one test locator. Six locale/accessibility-floor tests passed.
- After the final merge: application typecheck and 54 focused tests across route loading/history, job-review dialog, Works and Vector Stores passed. Full browser/build checks have not been repeated after that merge.
- Full preflight was attempted but was not green: bundled Python lacks Ruff, mypy, pytest-xdist and FastAPI. Its stale-base warning was addressed by the final merge. Two formatting warnings were addressed by Prettier (line-ending normalization only, no source diff). Earlier Windows polling-ratchet failures are fixed upstream; all current frontend unit tests passed. The repository's documented `DERRIDAI_SKIP_PREFLIGHT=1` push override is used for the disclosed backend environment limitations.
- Synthetic delays prove interaction behavior, not production latency improvements. Existing bundle-size warnings remain. No release-readiness or complete plan claim.

## Resume

1. Fetch master, merge if needed, and reread `CORPUS_BUILDER_PERFORMANCE_PLAN.md` and `CORPUS_BUILDER_PERFORMANCE_PROGRESS.md`. Keep builder queues, reconciliation, persistence, and enrichment out of scope while performance work continues.
2. Continue the baseline/readiness matrix in `PROGRESSIVE_LOADING_UX_PLAN.md`: cold/warm/back navigation, rapid selection, partial failure, offline/cancellation, zoom, narrow themes and long labels. Record readiness and request counts separately.
3. Next bounded implementation: Vector data-table/search request identities and local pending/error/empty states. Collection-level isolation is complete; these subpanels are not.
4. Then Search, Research, Response Library, Records and remaining route inventory. Finish the cross-route audit before declaring the plan complete.
5. Use the isolated checkout `C:\Users\aaron\Documents\Codex\2026-10-02\get\work\DerridAI`. Frontend dependencies are installed under `web`. Browser validation used `APP_PORT=5297`, `STORYBOOK_PORT=6297`, `CI=1`, built app/Storybook artifacts, and the `route-loading`, `progressive-loading`, `vector-progressive-loading`, and `works` Playwright specs. Configure a complete backend environment before expecting full preflight to pass.

The user clarified the stopping threshold as **20% remaining (80% used)** in the five-hour window. This handoff is prepared at 76% used to leave room for commit/push verification; do not start another increment during this wrap-up.
