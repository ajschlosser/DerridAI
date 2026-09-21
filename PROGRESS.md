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

## Done so far (runtime.js: 10,472 -> 8,803 lines; master 0.62.19 build 4675429 is the base of session 3)

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
| `web/src/domain/providerProfilesService.ts` | `createProviderProfiles({state, api, persistPrefs, uid, isResearcher, warmupProviderProfile})`: provider profile list, defaults, statuses, `*ForUi` helpers |
| `web/src/services/workspaceDb.ts` | IndexedDB persistence and "delete all browser state" |
| `web/src/runtime/runtimeState.ts` | initial shape of the runtime `state` (`createRuntimeState()`) |

The runtime still owns the one `state` instance (`const state = createRuntimeState()`).

## Verification recipe (run all before each push)

From `web/`:

```bash
npx vue-tsc --noEmit && npx eslint src --max-warnings 0 && npx vitest run   # 412 unit tests at last count
npm run build
npx playwright test -c playwright.legacy.config.ts                          # DOM baseline, 6 tests
```

Full end-to-end suite (137 tests, about 8.5 minutes; use ports that are free, Storybook is started for it):

```bash
APP_PORT=15199 STORYBOOK_PORT=16006 npx playwright test --project=chromium-desktop --workers=2
```

Full e2e: 144 passed at the last commit of session 2 (branch `claude/runtime-refactor-2`, merged with `development`). Unit: 403. Typecheck and lint clean.
the final build at the last commit of this session (corpusAnalytics). Unit: 382 passed. Typecheck and lint clean.

### The DOM baseline (`tests/e2e/legacy-dom-baseline.spec.ts`, 27 scenarios)

Snapshots in `tests/e2e/legacy-dom-baseline.spec.ts-snapshots/` were recorded from the pre-risky-phase build
(master 0.62.19 + provider-profiles); they must not be regenerated to make a refactor pass. Run with
`npm run build && npx playwright test -c playwright.legacy.config.ts` (starts `vite preview` on 5199; start one
yourself for fast repeat runs). 15 consecutive runs of all 27 passed with no flakes.

- **Dashboard (the only view still drawn through `RuntimeSurface`):** empty, loaded, researcher role, with jobs,
  metric carousel next / next-twice.
- **Other runtime-drawn surfaces:** PDF Explorer (empty); `research-empty` is a Vue page kept from the first baseline.
- **Runtime-built `<dialog>`s:** merge files (needs a second file), create subset, clean OCR artifacts, export JSONL,
  collection wizard (source step, retrieval step), Works: populate-all-metadata and separate-works, job details for an LLM
  review / PDF build / RAG job, and LLM review results (records resolved through the file's content-hash id, see
  `SAMPLE_FILE_ID`). Job dialogs read `/api/jobs/{id}`, hence `jobFixtures()`.
- **Computed styles** (`styles-*.txt`; per element: color, background, border, font, padding, margin ... no
  layout-dependent values): dashboard light/dark, researcher dashboard dark, PDF Explorer, and the subset, job-results
  and wizard dialogs in dark. DOM alone cannot see CSS/theme regressions. Dark uses `page.emulateMedia({colorScheme})`
  (the localStorage pref is not honored by the legacy runtime).
- Normalization: tooltip wrappers on disabled controls removed (markup) or looked through (styles), UUIDs and dates
  masked, `Math.random` pinned to 0, fixed clock, reduced motion, markup must be stable for 800 ms before capture.
  Add scenarios by appending to `scenarios` (`steps`, `fixtures`, `role`, `scheme`, `target: "dialog"`, `styles: true`)
  and record with `--update-snapshots=missing` (Playwright reports the first write as a failure; rerun).

Findings while building it: **existing bug** `ReferenceError: wireOperationsPanel is not defined` is thrown on every
dashboard render (`runtime.js` `renderDashboard`; the function was removed by commit 2c51149 "Rebuild the Home
Operations panel as a Vue component" but one call remains). It aborts the rest of that wiring line. The baseline records
behavior as-is; fixing it is a behavior change, so raise it with the owner. Also: Review / Auto-improve needs-review open a
Vue dialog (`.ui-dialog`), the Records Columns dialog and record edit sheet are Vue; "Open result" on a RAG job navigates
to the Vue Research page rather than opening a dialog.

Not covered (add before touching them): bulk-edit and upsert-queue dialogs, works-metadata editor / review-flagged /
auto-improve / remove-work (need a selected work), Delete-collection and other confirm modals, other job types
(upsert, llm_tool), the legacy Record/Search/Compare/Annotations renderers (unreachable from the UI, but `renderView`
still dispatches to them).

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

## Session 3 (branch `claude/runtime-refactor-3`, from master 0.62.19)

Low-risk pure/near-pure extraction is essentially exhausted. Technique used for state-reading services: pass the
runtime `state` object itself as a dependency (`createX({state, api, ...})`) so bodies stay verbatim; wrap later-declared
consts as lambdas (`uid:()=>uid()`). What is left in `runtime.js` is DOM-, timer- or render-coupled:

- Job polling/notifications (`refreshJobs`, `startJobPolling`, `syncJobProgressToasts`, `cancelBackgroundJob`,
  `removeFinishedJob`, `syncUpsertJobReceipts`): touch the operations dock, RAG panel and home card renderers.
- Backup/restore (`downloadFullBackup`/`restoreFullBackup`), `checkHealth`, `warmupProviderProfile`: DOM buttons, toasts, modals.
- Legacy annotations renderers (`renderAnnotations`, `annotationItemHtml`, ...): `renderView` still dispatches to them
  although `/annotations` is Vue-native now. Do not delete without proving they are unreachable (e2e + DOM baseline).
- Modals (`openMergeDialog`, `openSubsetBuilder`, `openLlmTaskLauncher`, `legacyOpenTouchup`, ...), `renderDashboard`, `renderPdf`,
  `renderRag`/`renderFaq`, `renderCompare`, `renderList`/`renderRecord` legacy paths.

## Next steps: the risky phase (needs owner go-ahead)

1. DONE (session 4): the DOM + computed-style baseline above (27 scenarios). Extend it for anything not covered before touching it.
2. State to Pinia behind getter/setter proxies on `runtime.state` (jobs first). Keep re-render triggers unchanged.
3. Routing: pure URL-state functions (`urlFromState`, `applyUrlState`, `currentTableUrlState`) with round-trip tests, then
   move `popstate` to `vue-router`.
4. Replace renderers one view/dialog per commit, only against a clean DOM-baseline diff.
5. Remove `runtimeBridge.ts`, `RuntimeSurface.vue`, and dead exports only when nothing consumes them
   (21 exports had no consumer outside the runtime at last count).

Time zone note: dashboard date keys use local midnight then `toISOString()`, so they depend on the browser's
time zone (unchanged legacy behavior). Tests that touch them pin `TZ=UTC`.

## Working rules added in session 2

- Branch from `origin/development` (work branch `claude/runtime-refactor-2`); `git fetch` and merge `development`
  regularly, other work touches `runtime.js` (e.g. Works became Vue-native and dropped out of the DOM baseline).
- Write human-readable code: run Prettier on every new file (it expands the dense legacy one-liners) and give
  extracted params real types instead of `any` where cheap.
- `scripts/runtime-refactor/deps.py fn1,fn2` lists the runtime names and state fields a group uses; use it to
  choose groups before extracting.

## Upstream breakage found and repaired (commit fe3322e)

`origin/development` (e9f42f3) did not build: a botched conflict resolution left 111 duplicate names in `runtime.js`'s
`export {}` block, interleaved two versions of `WorksView.vue` (with corrupted characters and a BOM), dropped seven Works
functions that `useWorksWorkspace.ts` calls, and routed `/works` back to the legacy view. Repaired here by keeping the
union of exports, restoring the Vue-native WorksView from 5319bc9 and the seven functions verbatim from it, routing
`/works` to `WorksView`, and dropping Annotations (now Vue-native) from the legacy DOM baseline. After the repair:
typecheck 0 errors, lint clean, 410 unit tests, build ok, 142 e2e (incl. 3 baseline views) passing.
Watch for BOMs / mojibake after Windows-side merges.

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
