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

Checkpoint: 2026-10-03. Branch: `feat/progressive-loading-remaining`, based on freshly fetched master `86deeaf3` after #468 merged.

## Current checkpoint

Works, Record detail, route feedback, Vector Stores and Search are implemented. Research is merged in #468. Response Library now has independent archive/reader states, retained same-resource content, local errors/retry, scope protection and cached revisit behavior. Detailed evidence and historical checkpoints are in [PROGRESSIVE_LOADING_UX_PLAN.md](PROGRESSIVE_LOADING_UX_PLAN.md).

Response Library validation: ten focused cases pass (six initially failed against master); 23 tests passed across Response Library, Research and database empty states. App/SDK and test TypeScript, touched-file ESLint, production/Storybook builds and six Python locale tests passed. Two Response Library production-browser cases passed, including request counts, retained answer DOM, narrow-screen axe scans; the existing Research browser case passed too. This does not establish production speedups or full plan completion.

## Resume

1. Continue with Records at the Vue composable/runtime-adapter boundary. Do not extend runtime renderers or overlap Corpus Builder queues, reconciliation, persistence or enrichment. The current adapter calls `ensureCorpusWorkspaceLoaded`; that runtime function catches read failures internally, so a truthful failure state may require extracting a minimal Vue-owned hydration service rather than simply adding a spinner.
2. Complete baseline/readiness measurements and explicit cache/refresh policies across the implemented surfaces: cold/warm/back navigation, request counts, rapid selections, partial failure, offline/cancellation and authorization changes.
3. Keep Corpus Builder/source-preview changes deferred while its performance work is active; document any necessary boundary before implementing.
4. Finish remaining P2 route inventory and cross-route accessibility/localization/layout audit (light/dark, zoom, dense long labels and narrow widths). Do not declare completion until the plan's acceptance checks are evidenced.

This checkout has local pinned frontend dependencies. Browser checks use ports 5298/6298. Bundled Python ran locale tests; full change-aware preflight is still to be recorded.
