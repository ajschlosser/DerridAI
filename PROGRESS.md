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
npx vue-tsc --noEmit && npx eslint src --max-warnings 0 && npx vitest run   # 454 unit tests at last count
npm run build
npx playwright test -c playwright.legacy.config.ts                          # DOM baseline, 6 tests
```

Full end-to-end suite (137 tests, about 8.5 minutes; use ports that are free, Storybook is started for it):

```bash
APP_PORT=15199 STORYBOOK_PORT=16006 npx playwright test --project=chromium-desktop --workers=2
```

Full e2e: 144 passed at the last commit of session 2 (branch `claude/runtime-refactor-2`, merged with `development`). Unit: 403. Typecheck and lint clean.
the final build at the last commit of this session (corpusAnalytics). Unit: 382 passed. Typecheck and lint clean.

### The DOM baseline (`tests/e2e/legacy-dom-baseline.spec.ts`, 115 scenarios)

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

Findings while building it: the stale `wireOperationsPanel()` call that threw on every dashboard render was FIXED in
c172814 (a test now guards it). Still open, same class (`// eslint-disable-next-line no-undef -- SA-11` backlog in
`runtime.js`, five sites): e.g. `openSharedAnnotationRecord` (dashboard latest server annotation click) is not defined.
Also: Review / Auto-improve needs-review open a
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
- `checkHealth`, `warmupProviderProfile` (the response cache renderer moved to `domain/responseCacheRenderer.ts`; the dashboard renderer moved to `domain/dashboardRenderer.ts`; its `openSharedAnnotationRecord` call is still undefined, as before): DOM buttons, toasts, modals. (Backup/restore moved to `domain/backupWorkspace.ts`.)
- Legacy annotations renderers (`renderAnnotations`, `annotationItemHtml`, ...): `renderView` still dispatches to them
  although `/annotations` is Vue-native now. Do not delete without proving they are unreachable (e2e + DOM baseline).
- Modals (`openMergeDialog`, `openSubsetBuilder`, `openLlmTaskLauncher`, `legacyOpenTouchup`, ...), `renderDashboard`, `renderPdf`,
  `renderRag`/`renderFaq`, `renderCompare`, `renderList`/`renderRecord` legacy paths.

## style.css audit (branch `claude/runtime-refactor-12`)

`docs/STYLE_AUDIT.md` has the findings and the recommended order; `scripts/runtime-refactor/style_audit.py` (numbers, writes
`/tmp/style_lists.json`) and `style_prune.py` (removes rules that can never match) reproduce them. Done: 613 dead rules removed
(5,176 -> 4,514 lines) with 60/60 baseline scenarios (computed styles unchanged) and 199/199 e2e. Next for CSS: move the 306
Vue-only classes into scoped component styles, one view at a time, then extract a base layer for the ~200 shared classes; runtime-only
classes move with their renderer when it is replaced.

### Job polling extracted (branch `claude/runtime-refactor-16`, includes -15 which was not yet merged)

`domain/jobsWorkspace.ts` (`createJobsWorkspace({state, ...21 helper lambdas})`, 12 functions: `refreshJobs`, `startJobPolling`,
`pauseRuntime`, `pruneClientJobState`, `removeFinishedJob`, `clearFinishedOperations`, `syncUpsertJobReceipts`,
`cancelBackgroundJob`, `submitBackgroundLlmJob`, `registerExternalJob`, `maybeDesktopNotify`, `syncJobProgressToasts`). The two module
objects those functions share (`jobCompletionNotified`, `completedJobToastTimers`) now live inside the factory. The operation dock and
toast DOM code (`ensureJobProgressCard`, `showOperationProgress`, `progressStack`, `updateOperationStackCount`, ...) stays in the
runtime and is passed in. Six new baseline scenarios (`jobs-*`; 115 total) use `liveJobs()`, a stateful jobs endpoint fixture (listing,
deleting, clearing, cancelling change later listings; a running job finishes after N listings) and a `dock` target
(`#operationProgressStack`); recorded before the move. `tests/frontend/jobs-workspace.test.ts`. `runtime.js` is 7,571 lines.
Remaining runtime chunks: backup/restore (`downloadFullBackup`/`restoreFullBackup`, DOM buttons + modals + toasts), `checkHealth`,
the operation dock/toast DOM code, the modals, and the legacy renderers (dashboard, PDF Explorer, dead Record/Compare/FAQ/RAG
pages).

### Research workspace + Response Library extracted (branch `claude/runtime-refactor-15`, includes -14 which was not yet merged)

`domain/researchWorkspace.ts` (`createResearchWorkspace({state, ...26 helper lambdas})`, 20 functions: the Research snapshot,
config, evidence, running/grading/re-running, job commands, `getResponseFaqPage`, `gradeResponseFaqRecord`,
`rerunResponseFaqRecord`, `rememberRagPrompt`/`rememberRagRun`, `prepareRagRerun`). 11 new baseline scenarios (`research-*`,
`faq-*`, `styles-research-evidence-light`; 109 total) recorded from the pre-move build in their own commit; the spec gained a
`path` option to open a Vue-native route directly (needs `main`, not `#main`). `tests/frontend/research-workspace.test.ts`.
`runtime.js` is 7,794 lines. `shellRefreshHook` is a reassigned `let`, so it is passed as a lambda like the other helpers.
Machine load matters: when other processes (a Storybook from another checkout, orphaned Playwright browsers) push the load
average up, baseline scenarios time out at 30 s in random places; check `uptime`, kill orphans (`/tmp/killall_pw.sh` pattern:
`chrome-headless-shell`, `playwright test`), and run with `--workers=3`. Never `pkill -f` a word that appears in your own command.

### Annotations workspace extracted (branch `claude/runtime-refactor-14`)

`domain/annotationsWorkspace.ts` (`createAnnotationsWorkspace({state, ...19 helper lambdas})`, 13 functions: gathering local and
shared annotations, describing them for the view, and every command `annotationsService` sends). Eight Annotations baseline
scenarios (`annotations-*`, `styles-annotations-light`; 98 total) recorded from the pre-move build in their own commit; the
scenario `records` option loads custom records (annotated ones) instead of the default sample. `tests/frontend/annotations-workspace.test.ts`.
`runtime.js` is 8,120 lines. `annotationsService` is still a thin delegate to the runtime (its functions now come from the factory);
converting it to call the factory directly comes with the composable conversion. Merged master (Copilot PR #81) into this branch.
Known flakes seen once each and not reproducible on rerun: a Corpus Builder dark-mode axe sweep (`corpus-builder-theme-sweep`,
slow, 7+ minutes) and one `styles-app-shell-*` computed-style snapshot in 1 of ~6 runs (investigate if it recurs: likely timing of
the shell's activity badges).

### CSS move (branch `claude/runtime-refactor-13`)

`style_move.py` (see `docs/STYLE_AUDIT.md`, "Progress") moved 207 rules from `style.css` into 15 components' scoped styles; 90
computed-style/DOM baseline scenarios (desktop, tablet, phone, light/dark) unchanged, full e2e and Storybook build green.
Excluded on purpose: `CommandSearch.vue` (moving its rules changed the search box's look). Copilot's PR #81 (Corpus Builder,
no `style.css`/runtime/e2e changes) uses none of the classes whose rules were pruned earlier. Next for CSS: hand-resolve the
classes whose rules span several components (merge duplicates, then move the group), then extract the shared base layer.

### Stale-view fixes found by probing (branch `claude/runtime-refactor-12`)

Probe method: open the view, import a file (distinct content: identical content is de-duplicated by content hash), see whether
the view notices. Found and fixed (each with an e2e test verified to fail without the fix, in `legacy-dom-baseline.spec.ts`,
"views follow the loaded corpus"): Records (rail file count; earlier commit), Compare (picker kept "No matching records" /
"Load JSONL files first"), Vector Stores (sync buttons stayed disabled). Works and Search already updated; Annotations and
Record View showed nothing to update in the same probe. Pattern: watch `corpusState.version` + `activeFileId`. Gotcha: do not
return the same array from a `computed` and expect re-renders (an unchanged array notifies nobody); return a count/boolean.

## Pinia migration (session 5, branch `claude/runtime-refactor-5`)

Pattern (behavior-preserving): move a group of `state.*` fields into a shallow-reactive object in `web/src/state/`, bind
accessors for those fields onto the runtime `state` (`bindJobsState`), so runtime code is unchanged and still gets the very
same plain arrays/objects back, and expose the object through a Pinia store in `web/src/stores/`. The state is shallow on
purpose: the runtime mutates in place, so Vue learns about changes through a `version` counter that the runtime bumps where
it already notifies (`notifyOperationsChanged` -> `touchJobs()`).

- DONE: jobs (`jobs`, `jobsLastFetched`, `jobApplied`, `upsertJobApplied`) -> `state/jobsState.ts`, `stores/jobs.ts`
  (`useJobsStore`: `jobs`, `lastFetched`, `version`, `activeJobs`). Nothing in Vue reads it yet; `OperationsPanel` still
  uses the bridge. Unit tests: `tests/frontend/jobs-state.test.ts`.
- DONE: the Operations panel bridge now subscribes through the store's `version` (synchronous watcher) instead of a
  private listener set.
- DONE: per-view groups -> `state/workspaceState.ts` (`vectorState` 26 fields, `compareState` 8, `searchState` 14, each
  with a `version` for in-place edits) bound onto the runtime `state` with `bindSharedState`; Pinia views in
  `stores/workspace.ts` (`useVectorStore`, `useCompareStore`, `useSearchStore`). Unit tests pin every original initial value
  (`tests/frontend/workspace-state.test.ts`). `VectorStoresView` needed `as unknown as` on its `runtime.state` cast (types only).
- DONE (branch `claude/runtime-refactor-6`): `VectorStoresView` and `CompareView` read and write the shared fields through
  `useVectorStore` / `useCompareStore` instead of casting `runtime.state`; non-shared fields go through a separate
  `runtimeState` cast. Their unit tests reset the shared state (`createVectorState()` / `createCompareState()`).
  Deliberately NOT done: replacing the views' local refs (`filter`, `tab`, `storePage`, `searchMode`, `activeName`, ...)
  with store-bound refs. Those refs are copied into the runtime only in `persistWorkspace()`, and some logic depends on that
  timing: e.g. `VectorStoresView` `load()` tests `!workspace.storeSearchMode` AFTER `persistWorkspace()` has already written
  "hybrid", so that branch is dead today; binding `searchMode` directly would wake it and change behavior. Do that only with
  a test pinning the intended behavior first.
- DONE (branch `claude/runtime-refactor-7`): the Search workspace logic left `runtime.js`: `domain/searchWorkspace.ts`
  (`createSearchWorkspace({state, ...50 helper lambdas})`, 34 functions: snapshot/results/facets/columns building and every
  command `SearchView` sends). Verbatim move; runtime keeps thin destructured consts, exports unchanged. Params of these
  legacy functions are typed `Any` on purpose (never typed before). Guarded by 7 new baseline scenarios for the Search view
  (`search-*`, recorded from the PRE-move build: stash src, build, record, pop, rebuild, compare) plus
  `tests/frontend/search-workspace.test.ts`. The baseline nav click is now scoped to `nav, aside` (the top bar has its own
  "Search" button). `SearchView` itself still polls `runtime.getSearchWorkspaceSnapshot()`; next is turning that into store
  fields + computed inside a composable now that the logic is isolated.
- DONE (branch `claude/runtime-refactor-8`, from master after PR #77): the Records workspace logic left `runtime.js`:
  `domain/recordsWorkspace.ts` (`createRecordsWorkspace({state, ...43 helper lambdas})`, 20 functions: the list snapshot and
  every command `useRecordsWorkspace` sends). Seven Records-view baseline scenarios (`records-*`, 115 scenarios total) were
  recorded from the PRE-move build in a separate commit, then compared against the moved code; `tests/frontend/records-workspace.test.ts`
  pins the commands. `runtime.js` is 8,565 lines. The baseline spec pins `timezoneId: "UTC"`, `locale: "en-US"` (CI runs in UTC).
- DONE (branch `claude/runtime-refactor-9`): the Record workspace logic left `runtime.js`: `domain/recordWorkspace.ts`
  (`createRecordWorkspace({state, ...helper lambdas})`, 15 functions: the record snapshot, navigation, and every
  `*CurrentRecord*` / `*RecordWorkspace*` command). Nine Record-view baseline scenarios (`record-*`, 52 total) recorded from the
  PRE-move build in their own commit, then compared against the moved code (52/52, 3 runs); `tests/frontend/record-workspace.test.ts`.
  Note for extractions: after Prettier expands a dense `try{...}catch{}` the `eslint-disable no-empty` directive no longer
  lines up; replace the empty catch with a commented one. `runtime.js` is 8,424 lines.
- DONE (branch `claude/runtime-refactor-10`, from master after PR #78): the Works workspace logic left `runtime.js`:
  `domain/worksWorkspace.ts` (`createWorksWorkspace({state, ...37 helper lambdas})`, 22 functions: work descriptions, the
  workspace snapshot/preparation, and every command `useWorksWorkspace` sends). Seven more Works baseline scenarios
  (`works-*`, `dialog-works-*`; 59 total) were recorded from the PRE-move build in their own commit and compared (59/59, 3 runs);
  `tests/frontend/works-workspace.test.ts`. Baseline gotchas: the per-work "Open N records" buttons are stat links whose
  accessible name starts "Open N records for ..."; each work card has its own Actions menu. `runtime.js` is 8,274 lines.
- DONE (branch `claude/runtime-refactor-11`, includes runtime-refactor-10 which was NOT yet merged to master when this branch
  was cut, so merge order is 10 then 11): `files` and `activeFileId` moved into `state/workspaceState.ts` `corpusState`, and
  `worksSearch` / `workOverview` into `worksState`; `useCorpusStore` and `useWorksStore` added. `invalidateCorpusCache()` (called
  after every corpus edit) now also calls `touchCorpus()`, so `corpusState.version` changes whenever the loaded corpus does.
  Nothing in Vue reads these yet (198/198 e2e, 59/59 baseline, 438 unit).
- DECIDED (owner: behavior changes are fine if they fix obvious bugs, but check first): I checked before changing anything by
  importing a file while each view was open (probe, then a permanent e2e test). Works and Search already update; **Records did
  not** (toast "Loaded 1 records" but the rail kept saying "Local JSONL 1 files" until you left and came back), which is an
  obvious bug. Fixed in `useRecordsWorkspace`: it now re-reads its snapshot when `corpusState.version` or `activeFileId`
  changes (only once a snapshot has been loaded). Guarded by `tests/frontend/records-workspace-refresh.test.ts` and the e2e test
  "Records lists a file imported while it is open" (verified to fail without the fix). RecordView showed no visible staleness
  in the same probe, so it is unchanged. Check any further conversion the same way: probe the current behavior first, convert
  only where it is stale or wrong.

## Next steps: the risky phase (needs owner go-ahead)

1. DONE (session 4): the DOM + computed-style baseline above (115 scenarios). Extend it for anything not covered before touching it.
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


## Session 4 summary (branches -16 to -18)

runtime.js: 7,571 -> ~3,560 lines. Moved verbatim into `domain/*` factories: backupWorkspace, dashboardRenderer,
responseCacheRenderer, pdfExplorerRenderer, jobDialogs, workDialogs, recordDialogs, operationDock. Deleted the legacy
Record/Annotations/List/Global/Compare/Faq/Rag/Works renderers (no route reaches them). The baseline now has 131 scenarios,
including a `runtime` target (`#main`) and PDF Explorer scenarios (the old pdf-explorer scenarios snapshotted the
Corpus Builder by mistake).

Found, not fixed (behavior kept):
- Clicking the "PDF Explorer" tab while a build is selected in the Corpus Builder does not open the Explorer (the
  builder's URL sync rewrites `mode`); the baseline opens it through a popstate instead.
- `operationDock.updateOperationStackCount` passes `{active,failed,finished}` to `dockCollapsedSummary`, which reads
  `activeCount/failedCount/finishedCount`, so the collapsed dock label always sees zeros.
- The dashboard's latest-annotation click calls an undefined `openSharedAnnotationRecord`.

Left in runtime.js: state/persistence, evidence and selection, navigation/URL, the operations panel, corpus-builds home
card, modals (`openMessageModal`), compare library, translation of legacy DOM. Next: move those clusters the same way
(`/tmp`-style helper: mk_factory.py + tsc TS2304 names; pass values by value only if declared before the call site), then
replace the dashboard, PDF Explorer and response cache with Vue views, one per commit.
