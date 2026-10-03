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

Checkpoint: 2026-10-03. Branch: `codex/annotations-progressive-loading`, based on freshly fetched master `f6554817` after #470 merged.

## Current checkpoint

Annotations now retains its toolbar during initial reads and its loaded feed during refresh/failure, with region skeletons, Updating, out-of-date failure and Retry. Vue rejects superseded completions and clears queued searches on disposal. Workspace reads expose shared-annotation/store-discovery errors instead of silently reporting success. Authorization-denied errors clear retained feed content. The 15-second shared-read cache and other refresh callers retain their existing contracts. This is a scoped P2 increment, not completion of the readiness or scope/cache matrix.

Validation: 12 focused tests pass; four new Vue regressions failed against unchanged master. Dependency-selected validation passed 965/967 tests in 148 suites; two unrelated timeout cases passed in a one-worker rerun (51 tests). App/SDK/test TypeScript, touched-file ESLint, production and Storybook builds passed. Browser validation and preflight results are recorded in the detailed plan below.

Works, Record detail, route feedback, Vector Stores and Search are implemented. Research is merged in #468. Records initial hydration now has placeholders, truthful local failure/retry, concurrent-read sharing, and retained loaded rows. Response Library now has independent archive/reader states, retained same-resource content, local errors/retry, scope protection and cached revisit behavior. Detailed evidence and historical checkpoints are in [PROGRESSIVE_LOADING_UX_PLAN.md](PROGRESSIVE_LOADING_UX_PLAN.md).

Response Library validation: ten focused cases pass (six initially failed against master); 23 tests passed across Response Library, Research and database empty states. App/SDK and test TypeScript, touched-file ESLint, production/Storybook builds and six Python locale tests passed. Two Response Library production-browser cases passed, including request counts, retained answer DOM, narrow-screen axe scans; the existing Research browser case passed too. This does not establish production speedups or full plan completion.

## Resume

1. Records initial hydration is implemented. Its broader scope/cache/selection/readiness matrix remains open. The typed coordinator is `web/src/domain/corpusWorkspaceHydration.ts`; the existing export adapter still reduces failures to null, so the view reports generic unavailability. Avoid extending runtime renderers or overlapping Corpus Builder queues, reconciliation, persistence or enrichment.
2. Complete baseline/readiness measurements and explicit cache/refresh policies across the implemented surfaces: cold/warm/back navigation, request counts, rapid selections, partial failure, offline/cancellation and authorization changes.
3. Keep Corpus Builder/source-preview changes deferred while its performance work is active; document any necessary boundary before implementing.
4. Continue P2 boundaries with Providers/Languages, then the remaining route inventory and cross-route accessibility/localization/layout audit (light/dark, zoom, dense long labels and narrow widths). Do not declare completion until the plan's acceptance checks are evidenced.

This checkout has local pinned frontend dependencies. Browser checks use ports 5298/6298. Bundled Python ran locale tests; change-aware preflight passed frontend lint/types/selected tests/build and Python syntax, but backend lint/types/regressions could not run because Ruff, mypy and pytest-xdist are absent. The documented preflight override is used for that tooling limitation.

Records checkpoint validation: 149 dependency-selected suites (965 tests) passed; six coordinator cases and the 16-case Records view suite passed, with overlap. App/SDK/test TypeScript, touched-file lint, locale tests and production/Storybook builds passed. Five existing Records/Response Library browser cases passed; the new delayed/retry Records browser case passed separately. New loading/error axe scans are clean. The populated Records table retains the pre-existing empty filter-row selection/action headers (one axe violation, two nodes); a label fix was requested and awaits the user's choice. This exception is explicit in the browser test, not a disabled rule.

Annotations has a pre-existing `nested-interactive` axe violation: Open work overview buttons are inside two group summaries in the browser fixture. The test pins that exact exception; new toolbar/error feedback is scanned separately. A fix was requested under the ask-before-unrelated-bug-fix instruction and remains pending. Full authorization-scope isolation, upstream cancellation and cross-route timing/geometry audits remain open.

Final Annotations validation: all three production-browser cases passed, including retained same-group DOM after retry and exactly two requests; new toolbar/error axe scans are clean, with the two existing nested-summary nodes explicitly pinned. Eight Python locale/accessibility-floor tests passed using an isolated temporary directory (the default shared pytest temp directory was inaccessible). Change-aware repository preflight passed: repository frontend lint, app/test typechecks, 12 directly changed tests, 148 dependency-selected suites (967 tests), formatting and production build. Backend gates were not selected for this frontend-only change; no override was required. Production/Storybook builds and browser checks were also run separately. These counts overlap earlier runs.
