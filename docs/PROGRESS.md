# Progressive loading UX progress

Checkpoint: 2026-10-02. Branch: `feat/progressive-loading-ux`.

## Completed

- Works and Record detail retain useful content during refresh, distinguish initial loading from refresh, and reject stale selections.
- Delayed route-module feedback retains the current page and offers retry/reload after import failures.
- Vector Stores collections load independently of health/provider discovery. Refresh failures retain the collection rail; provider failures are local and dependent controls wait. Cached revisits and unsaved settings are preserved.
- Vector data and retrieval panels have separate request identities. Browse is keyed by collection, work, and page; search is keyed by collection, submitted query, and mode. Stale responses are dropped. Same-identity refresh keeps rows; a failed refresh is marked stale. A new page, collection, or query does not show the previous rows as current. Initial failure has a local Retry. A successful empty search is distinct from the idle prompt.
- Implementation: `9d079838`, `8728c5a5`, `15a320ba`. Current master `27b754c3` merged cleanly as `6f4c4010`, including the latest Vue job-review dialog migration. No Corpus Builder implementation or legacy runtime files are changed relative to master.

## Validation and limitations

- Before the final master merge: full frontend lint, app/test typechecks, 1,524 unit tests, production build, and Storybook build passed. Targeted browser coverage passed all 24 distinct cases across route feedback, Works, Record, and Vector Stores after correcting one test locator. Six locale/accessibility-floor tests passed.
- After the final merge: application typecheck and 54 focused tests across route loading/history, job-review dialog, Works and Vector Stores passed. Full browser/build checks have not been repeated after that merge.
- Full preflight was attempted but was not green: bundled Python lacks Ruff, mypy, pytest-xdist and FastAPI. Its stale-base warning was addressed by the final merge. Two formatting warnings were addressed by Prettier (line-ending normalization only, no source diff). Earlier Windows polling-ratchet failures are fixed upstream; all current frontend unit tests passed. The repository's documented `DERRIDAI_SKIP_PREFLIGHT=1` push override is used for the disclosed backend environment limitations.
- Data-table and search increment: 20 Vector Stores unit tests passed. Application `vue-tsc`, touched-file ESLint, and the production frontend build passed. `vector-progressive-loading.spec.ts` passed 4 production-browser cases on ports 5297/6297. Python was not on PATH, so locale parity and full preflight were not run.
- Synthetic delays prove interaction behavior, not production latency improvements. Existing bundle-size warnings remain. No release-readiness or complete plan claim.

## Resume

1. Fetch master, merge if needed, and reread `CORPUS_BUILDER_PERFORMANCE_PLAN.md` and `CORPUS_BUILDER_PERFORMANCE_PROGRESS.md`. Keep builder queues, reconciliation, persistence, and enrichment out of scope while performance work continues. On 2026-10-02 the branch already contained `origin/master` `27b754c3`; no builder implementation files were changed.
2. Continue the baseline/readiness matrix in `PROGRESSIVE_LOADING_UX_PLAN.md`: cold/warm/back navigation, rapid selection, partial failure, offline/cancellation, zoom, narrow themes and long labels. Record readiness and request counts separately.
3. Vector data-table and retrieval-search identities are implemented. A browse is keyed by collection, work, and page; a search is keyed by collection, submitted query, and mode. Superseded responses are ignored. Same-identity refresh keeps rows and marks a failed refresh stale. A new page, collection, or query does not present the previous rows as the current result. Initial failure is a local error with Retry. A successful empty search is distinct from the idle prompt.
4. Next: Search, Research, Response Library, Records, and the remaining route inventory. Finish the cross-route audit before declaring the plan complete.
5. Use the isolated checkout `C:\Users\aaron\Documents\Codex\2026-10-02\get\work\DerridAI`. Frontend dependencies are installed under `web`. Browser validation used `APP_PORT=5297`, `STORYBOOK_PORT=6297`, `CI=1`, a rebuilt app, the existing Storybook artifact, and `vector-progressive-loading.spec.ts`. Python was not on PATH, so locale-parity and full preflight were not run.

The previous session stopped at the user's 80% usage threshold before this data-table increment. That threshold applied to that session only.
