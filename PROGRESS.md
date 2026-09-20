# runtime.js decomposition: progress and hand-off

Temporary file for this branch (`claude/derridai-runtime-refactor-24e3c0`). Delete it before merging.

## Goal and hard requirements

Decompose `web/src/runtime/runtime.js` (10,472 lines at the start, ~600 functions, one mutable `state`
object, imperative DOM rendering) toward modern Vue patterns.

- **No functionality changes or loss.**
- **No layout, UI or UX changes.** Rendered markup must stay identical.
- Commit often and push. Run Prettier on new/changed TS files before the PR (it is fine to leave
  machine-dense code in `runtime.js` itself; do not reformat the whole file, it would bury the moves).

## Method

Every step is a **move**: function bodies are copied verbatim into a typed module and the runtime imports
them. Nothing is rewritten. Each move is proven with one of:

1. a throwaway differential test comparing the extracted function to the original source from git
   `28a6e77` (the pre-refactor master) across a wide input matrix (then deleted, not committed), and
2. a committed test with golden values or snapshots taken from that verified output.

## Done so far (runtime.js: 10,472 -> 8,996 lines after merging `development`, which added ~230 lines)

| Module | Contents |
|---|---|
| `web/src/domain/citations.ts` | MLA/inline/full citations |
| `web/src/domain/recordValues.ts` | clone/equality, stable value and FNV fingerprint, compare/sort |
| `web/src/domain/urlState.ts` | shareable-link compression (LZW + base64url); golden tokens from the old code |
| `web/src/domain/recordQuery.ts` | `parseJsonl`, `flattenValueList`, `countOccurrences`, filter/subset matchers |
| `web/src/domain/researchPayloads.ts` | Research config/generation/job/evidence/profile shaping |
| `web/src/domain/html.ts` | `esc`, `icon` |
| `web/src/domain/runtimeConstants.ts` | `FIELD_LABELS`, `viewConfig`, `TABLE_DEFAULTS`, `SEARCH_LOADED_COLUMNS` |
| `web/src/domain/dashboardCharts.ts` | line/multi-line/bar/pie charts and `statList` (SVG/HTML strings) |
| `web/src/domain/recordHistory.ts`, `providerRequest.ts`, `pastedRecord.ts`, `httpErrors.ts` | audit history + upsert delta, provider request config, Compare paste parsing, API error text |
| `web/src/domain/recordFormatting.ts`, `recordPayloads.ts` | highlight/snippet/model labels; record payloads, history summary, PDF links |
| `web/src/domain/operationPresenters.ts` | `createOperationPresenters(deps)` factory: job labels, facts, subtitles, progress (Operations panel view model) |
| `web/src/domain/fieldFormatting.ts` | `createFieldFormatting({tr})` factory: `label`, `display`, `normalizeRagGrade`, bulk/work-metadata value parsers |
| `web/src/domain/corpusAnalytics.ts` | `createCorpusAnalytics({allRows, memoCorpus})` factory: work index, top values, year series, needs-review series, audit feed |
| `web/src/domain/searchFacets.ts` | `createSearchFacets(deps)` factory: facets, filter descriptors, match reasons, list-filter matching |
| `web/src/domain/workMetadata.ts`, `touchupFields.ts`, `reviewPresentation.ts` | work metadata summary, touch-up field list, review diff sides / pretty JSON / RAG answer HTML / annotation matching |
| `web/src/services/workspaceDb.ts` | IndexedDB persistence and "delete all browser state" |
| `web/src/runtime/runtimeState.ts` | initial shape of the runtime `state` (`createRuntimeState()`) |

The runtime still owns the one `state` instance (`const state = createRuntimeState()`).

## Verification recipe (run all before each push)

From `web/`:

```bash
npx vue-tsc --noEmit && npx eslint src --max-warnings 0 && npx vitest run   # 406 unit tests at last count
npm run build
npx playwright test -c playwright.legacy.config.ts                          # DOM baseline, 6 tests
```

Full end-to-end suite (137 tests, about 8.5 minutes; use ports that are free, Storybook is started for it):

```bash
APP_PORT=15199 STORYBOOK_PORT=16006 npx playwright test --project=chromium-desktop --workers=2
```

Full e2e: 144 passed at the last commit of session 2 (branch `claude/runtime-refactor-2`, merged with `development`). Unit: 403. Typecheck and lint clean.
the final build at the last commit of this session (corpusAnalytics). Unit: 382 passed. Typecheck and lint clean.

### The DOM baseline (`tests/e2e/legacy-dom-baseline.spec.ts`)

Normalized `<main>` markup for the legacy-rendered views (home, annotations, works empty/loaded, research),
compared with committed snapshots in `tests/e2e/legacy-dom-baseline.spec.ts-snapshots/`. The snapshots were
recorded from the **pre-refactor build**; they must not be regenerated to make a refactor pass. It runs
against `dist/` through `vite preview` on port 5199 (see `playwright.legacy.config.ts`), 0 flakes in 40 runs.
Extend it (more views, dialogs, dark mode, other roles) before touching the renderers in phase 5.

## The factory pattern (for functions that need `tr`, `state` or other runtime helpers)

`scripts/runtime-refactor/mk_factory.py` copies functions verbatim into `export function createX(deps)`; the only
edits are explicit string replacements turning `state.foo` / hoisted helper calls into `deps.*` (see the call in
git history for `operationPresenters`). The runtime then does `const {a,b}=createX({tr, getStores:()=>state.stores, ...})`
right after `translateLegacyDom`. Verify with a differential test that builds the legacy functions from git
`28a6e77` with the same mocks and compares outputs over many fixtures.

## Helper scripts (`scripts/runtime-refactor/`)

Run from `web/`. `splice.py <module> <fn1,fn2,...>` removes verbatim functions from `runtime.js` and adds the
import (you write the TS module by hand or with `mv_fn.py`). `mv_fn.py` copies functions verbatim into a new
`src/domain/<module>.ts` with typed signatures. `purity.py` lists functions that use no state/DOM/API (the
extraction candidates), largest first, with the helpers they call.

## Next steps (in order)

1. **More extraction with the factory pattern.** Still in `runtime.js` and mechanically movable (run
   `purity.py`, and a variant that also allows `tr`/`state` reads, to list them): the search-facet functions
   (`searchFacetRawValues`, `searchFacetMatches`, `buildSearchFacets`, need `recordDbStatus`), list filtering
   (`rowMatchesListFilters`, `recordsListCell`, `getRecordsListSnapshot`), `operationsBridge`, subset/bulk-edit
   helpers, the compare-library helpers, provider profile management (`ensureProviderProfiles`,
   `providerRequestConfig` callers), backup/restore (`downloadFullBackup`/`restoreFullBackup`, DOM/toast-coupled,
   inject `toast`/`openMessageModal`), job polling (`refreshJobs`, `startJobPolling`).
2. **State to Pinia** behind getter/setter proxies on `runtime.state` so unmigrated code keeps working:
   jobs first, then search, records list, vector stores, compare, PDF, research. Keep re-render triggers
   as they are; do not make `state` deeply reactive without checking `SettingsView`, which reads it directly.
   `runtimeState.ts` already gives the state one typed home.
3. **Routing**: extract `urlFromState`/`applyUrlState`/`currentTableUrlState` as pure functions with
   round-trip tests against links from the old build (`urlState.ts` already holds the encoding); only then move
   `popstate` ownership to `vue-router`.
4. **Replace imperative renderers with Vue**, one view or dialog per commit, only when the DOM baseline
   for it exists and the new component reproduces the same markup, classes, ids and aria attributes.
   Extend `legacy-dom-baseline.spec.ts` first (dialogs, dark mode, more data). Keep `translateLegacyDom` and the
   collapsible `MutationObserver` until the last legacy view is gone.
5. Delete `runtimeBridge.ts`, `RuntimeSurface.vue` and the export block only when nothing consumes them.
   Analysis found 21 exports with no consumer outside the runtime (e.g. the `touchup*` family, `viewPathMap`,
   `pathViewMap`); confirm with e2e before removing any.

Time zone note: dashboard date keys use local midnight then `toISOString()`, so they depend on the browser's
time zone (unchanged legacy behavior). Tests that touch them pin `TZ=UTC`.

## Working rules added in session 2

- Branch from `origin/development` (work branch `claude/runtime-refactor-2`); `git fetch` and merge `development`
  regularly, other work touches `runtime.js` (e.g. Works became Vue-native and dropped out of the DOM baseline).
- Write human-readable code: run Prettier on every new file (it expands the dense legacy one-liners) and give
  extracted params real types instead of `any` where cheap.
- `scripts/runtime-refactor/deps.py fn1,fn2` lists the runtime names and state fields a group uses; use it to
  choose groups before extracting.

## Blocker found on `origin/development` (not from this branch)

At `e9f42f3` the merged tree does not build: `runtime.js` has duplicate names in its `export {}` block ("Duplicate
export state/viewConfig/..."), `WorksView.vue` declares `selectWork` twice, `useWorksWorkspace.ts` calls runtime
functions that are not exported (`populateAllWorksMetadata`, ...), and `router/index.ts` has an unused import.
Unit tests pass except `works-view.test.ts`. Because of this the last extraction (`recordPresenters`) has unit +
differential verification but no e2e run. Fix these on `development` first, then run the full e2e.

## Gotchas learned

- `mk_factory.py` must not indent function bodies: lines inside multi-line template literals must stay
  byte-identical (an earlier version added 2 spaces and a differential test caught it).

- Factory call sites in `runtime.js` must come after the `const` helpers they receive (`label`, `display`, ...):
  passing a `const` declared later throws "Cannot access X before initialization" and breaks ~26 test files at
  import. Hoisted `function` declarations are safe; wrap later consts as `uid:()=>uid()`.

- `pkill -f <word>` kills your own shell if the word is in the command line. Kill by PID from `ss -ltnp`.
- Some editors/tools convert the `\u0000` escape into a literal NUL byte in source. Check new TS files with
  `python3 -c "print(open(p,'rb').read().count(b'\x00'))"`.
- `countOccurrences(text, [])` loops forever (legacy bug, unreachable with real input; left as is on purpose).
- Playwright: the legacy runtime restores the saved workspace on start-up; loading a JSONL too early races
  with the restore. The baseline waits for network idle and 1s first. The runtime also wraps disabled controls
  in a tooltip span at a timing-dependent moment; the baseline normalizes that away.
- `Math.random` is used by the dashboard's random record; the baseline pins it to 0.
- `npm ci` is needed in a fresh worktree. The default Playwright config expects free ports 6006 and 5199, or
  set `APP_PORT`/`STORYBOOK_PORT` (which also disables reuse of running servers).
- The repo's `.prettierrc` sets printWidth 100. `runtime.js` and most existing files are not Prettier-clean.
