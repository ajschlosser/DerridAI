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

# Progressive loading UX progress

Checkpoint: 2026-10-02. Branch: `feat/progressive-loading-search`, based on `origin/master` `401ca637` (after #440 merged).

## Completed

- Works and Record detail retain useful content during refresh, distinguish initial loading from refresh, and reject stale selections.
- Delayed route-module feedback retains the current page and offers retry/reload after import failures.
- Vector Stores collections load independently of health/provider discovery. Refresh failures retain the collection rail; provider failures are local and dependent controls wait. Cached revisits and unsaved settings are preserved.
- Vector data and retrieval panels have separate request identities. Browse is keyed by collection, work, and page; search is keyed by collection, submitted query, and mode. Stale responses are dropped. Same-identity refresh keeps rows; a failed refresh is marked stale. A new page, collection, or query does not show the previous rows as current. Initial failure has a local Retry. A successful empty search is distinct from the idle prompt.
- Search renders its title and a placeholder frame before the first workspace read, then keeps the header, command surface, filters, and results mounted across refreshes. A failed refresh retains the workspace with a local alert and Retry; only a first read with nothing on screen, or withdrawn authorization (401/403), replaces the page. Every workspace read carries a request identity, so a superseded route, locale, scope, store, or saved-view read cannot overwrite a newer one.
- Search result identity is explicit. The results region tracks which submitted corpus-database query the visible rows belong to; editing the query box names that query instead of letting the rows read as current, and submitting a different query clears them and shows a local searching state. `search_error` is now part of the Search workspace snapshot, so a failed corpus-database search is reported as a failure with Retry and claims no result count, rather than appearing as zero matches.
- Implementation: `9d079838`, `8728c5a5`, `15a320ba`. Earlier master `27b754c3` merged cleanly as `6f4c4010`, including the latest Vue job-review dialog migration. No Corpus Builder implementation or legacy runtime files are changed relative to master.

## Validation and limitations

- Before the final master merge: full frontend lint, app/test typechecks, 1,524 unit tests, production build, and Storybook build passed. Targeted browser coverage passed all 24 distinct cases across route feedback, Works, Record, and Vector Stores after correcting one test locator. Six locale/accessibility-floor tests passed.
- After the final merge: application typecheck and 54 focused tests across route loading/history, job-review dialog, Works and Vector Stores passed. Full browser/build checks have not been repeated after that merge.
- Full preflight was attempted but was not green: bundled Python lacks Ruff, mypy, pytest-xdist and FastAPI. Its stale-base warning was addressed by the final merge. Two formatting warnings were addressed by Prettier (line-ending normalization only, no source diff). Earlier Windows polling-ratchet failures are fixed upstream; all current frontend unit tests passed. The repository's documented `DERRIDAI_SKIP_PREFLIGHT=1` push override is used for the disclosed backend environment limitations.
- Data-table and search increment: 20 Vector Stores unit tests passed. Application `vue-tsc`, touched-file ESLint, and the production frontend build passed. `vector-progressive-loading.spec.ts` passed 4 production-browser cases on ports 5297/6297. Python was not on PATH, so locale parity and full preflight were not run.
- Search increment (branch `feat/progressive-loading-search` off `401ca637`): seven new unit cases in `web/tests/frontend/search-progressive-loading.test.ts` all failed against the unchanged implementation and pass now. The full frontend unit suite passed (255 files, 1,560 tests, no unhandled errors); the first run surfaced an unhandled render error in `database-empty-states.test.ts` caused by deriving the empty-corpus branch one tick after the snapshot, which is fixed by making `noDatabase` a computed. Application and SDK `vue-tsc`, test typecheck, ESLint on the touched files, the production build, and the Storybook build passed. `search-progressive-loading.spec.ts`, `search-scroll.spec.ts`, `progressive-loading.spec.ts`, `route-loading.spec.ts`, `vector-progressive-loading.spec.ts`, and `empty-states.spec.ts` passed 18 production-browser cases on ports 5297/6297, including an axe scan of the failed-search state.
- Search increment limitations: no Python interpreter was available in this checkout, so `pytest`, the locale-parity tests, and `scripts/preflight.sh` could not run. Locale parity was instead checked mechanically with Node: `en_us.py` and `fr_ca.py` both hold 9,198 keys with no missing or duplicated key, `enUsDefaults.json` matches `EN_US`, and the four new keys carry identical English text and the same `{query}` / `{message}` placeholders in both languages. `npm run format:repo:check` reported "All matched files use Prettier code style" but then failed on an `EPERM` scanning `.pytest_cache`, a local permission issue unrelated to the change. The new browser cases were not re-run against the pre-change build; the unit suite carries that comparison.
- Synthetic delays prove interaction behavior, not production latency improvements. Existing bundle-size warnings remain. No release-readiness or complete plan claim.

## Resume

1. Fetch master, merge if needed, and reread `CORPUS_BUILDER_PERFORMANCE_PLAN.md` and `CORPUS_BUILDER_PERFORMANCE_PROGRESS.md`. Keep builder queues, reconciliation, persistence, and enrichment out of scope while performance work continues. On 2026-10-02 the branch already contained `origin/master` `27b754c3`; no builder implementation files were changed.
2. Continue the baseline/readiness matrix in `PROGRESSIVE_LOADING_UX_PLAN.md`: cold/warm/back navigation, rapid selection, partial failure, offline/cancellation, zoom, narrow themes and long labels. Record readiness and request counts separately.
3. Vector data-table and retrieval-search identities are implemented. A browse is keyed by collection, work, and page; a search is keyed by collection, submitted query, and mode. Superseded responses are ignored. Same-identity refresh keeps rows and marks a failed refresh stale. A new page, collection, or query does not present the previous rows as the current result. Initial failure is a local error with Retry. A successful empty search is distinct from the idle prompt.
4. Search is implemented (frame before the first read, retained workspace across refresh and refresh failure, request identity on every read, submitted-query result identity, and a failed corpus-database search that is never reported as zero matches). Next: Research, Response Library, Records, and the remaining route inventory. Finish the cross-route audit before declaring the plan complete.
5. Use the isolated checkout `C:\Users\aaron\Documents\Codex\2026-10-02\get\work\DerridAI`. Frontend dependencies are installed under `web`. Browser validation used `APP_PORT=5297`, `STORYBOOK_PORT=6297`, `CI=1`, and a rebuilt app. Python is not on PATH in this checkout, so locale-parity and full preflight still need to run somewhere with the project venv before any CI-readiness claim.

The previous session stopped at the user's 80% usage threshold before the data-table increment. That threshold applied to that session only.
