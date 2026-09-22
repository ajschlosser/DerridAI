# runtime.js decomposition: hand-off

Temporary file. **Delete it before the effort ends** (last commit of the last PR). It exists so another agent (Codex, Copilot,
another Claude) can continue if the current one stops.

## Goal and hard requirements (from the owner)

Decompose `web/src/runtime/runtime.js` (a legacy runtime: one mutable `state`, imperative HTML-string renderers, services and the
Vue-facing API; 10,472 lines at the start, **2,376 now**) toward modern Vue patterns.

- **No functionality changes or loss. No layout, UI or UX changes.** Rendered markup and computed styles stay identical.
- A behavior change is allowed only to fix an obvious bug, and only after checking: probe the current behavior, add a test that
  fails without the fix, keep the fix in its own commit.
- Human-readable code: run Prettier on every new or edited TS/Vue file (`runtime.js` itself is dense on purpose; do not reformat
  it, that would bury the moves).
- Commit and push often; pull master periodically; one tranche per branch (`claude/runtime-refactor-N`), cut from master after the
  previous PR merged (if it did not, merge it in). The owner merges PRs. Keep chat and token use small.
- Before calling anything done: typecheck, lint, unit, the DOM baseline, the full e2e suite and the Storybook build pass.

## State of the code

`web/src/runtime/runtime.js` is now thin: it owns `const state = createRuntimeState()`, a set of
`const {a,b}=createX({state, ...helper lambdas})` calls, small shared helpers, and one big `export {...}` block that Vue code
imports (do not change export names). Everything else lives in `web/src/domain/*.ts` as verbatim moves:

- **Pure helpers:** citations, recordValues, urlState, recordQuery, researchPayloads, html (`esc`, `icon`), runtimeConstants,
  dashboardCharts, recordHistory, providerRequest, pastedRecord, httpErrors, recordFormatting, recordPayloads, workMetadata,
  touchupFields, reviewPresentation, operationsDock.
- **Factories** (`createX(deps)`; `deps.state` is the runtime state object, other deps are helper lambdas): operationPresenters,
  fieldFormatting, corpusAnalytics, searchFacets, recordPresenters, providerProfilesService, searchWorkspace, recordsWorkspace,
  recordWorkspace, worksWorkspace, annotationsWorkspace, researchWorkspace, jobsWorkspace, backupWorkspace, operationDock (toasts
  and the floating operation dock), and the renderers and dialogs: **dashboardRenderer, responseCacheRenderer,
  pdfExplorerRenderer, jobDialogs, workDialogs, recordDialogs**.
- **State:** `state/jobsState.ts`, `state/workspaceState.ts` (shallow-reactive groups bound onto `runtime.state` with
  `bindJobsState`/`bindSharedState`; Pinia stores in `stores/jobs.ts`, `stores/workspace.ts`; the runtime bumps a `version`
  counter where it already notifies, e.g. `invalidateCorpusCache()` calls `touchCorpus()`). Vue views refresh by watching
  `corpusState.version` and `activeFileId`. Gotcha: a `computed` that returns the same array does not notify; return a count.
- **Deleted:** the legacy Record, Annotations, List, Global, Compare, Faq, Rag and Works renderers (no route reaches them).
  `renderView()` dispatches only `home` (dashboard), `pdf` (PDF Explorer) and `responsecache`. `RuntimeSurface.vue` mounts `#main`
  for exactly those three (see `views/DashboardView.vue`, `PdfWorkspaceView.vue`, `ResearchView.vue`).

## Session 5 status (branch `claude/runtime-refactor-19`, stopped here — see below)

Since this file was last written (PR #86 merged), all of section A's remaining clusters have been extracted, each in its
own commit, each verified with unit tests, build, the 131-scenario baseline and the full 270-test e2e suite before
committing: modalDialogs, navigation, workspacePersistence, evidenceSelection, recordEditing, dbPresenceUpsert,
operationsPanelBridge, pdfLinking, appLifecycle, compareLibrary. `runtime.js` is now **2,376 lines** (was 3,421 at the
start of this session; 10,472 at the very start).

**Section A (mechanical cluster moves) is essentially done.** What's left in `runtime.js` is mostly: `translateLegacyDom`
and the collapsible MutationObserver (deliberately kept until the last legacy view is gone, see section B), the small
shared runtime helpers (`tr`, `trf`, `esc`-adjacent wiring, `shell()`, `setShellRefreshHook`), `getShellSnapshot`,
`translatedNavLabel`/`translatedSectionLabel`, `currentContext`, and glue that is not worth its own factory. Skim
`runtime.js` top to bottom before assuming there's another clean cluster; most of what's left is either tiny or
DOM/render-coupled and belongs with section B instead.

**New gotcha found this session, added below too:** a cluster move can silently introduce a **TDZ (temporal dead zone)
crash** even when `extract_factory.sh` reports no errors and `tsc`/eslint are clean, if some *other*, earlier factory
call in `runtime.js` references one of the moved names directly (not wrapped in a lambda) — e.g.
`const {...} = createX({state, api, persistPrefs, ...})` instead of `persistPrefs:(...args)=>persistPrefs(...args)`.
This compiles fine (both are function-typed) but throws `Cannot access 'NAME' before initialization` at runtime,
because the new call site is much later in the file than the old one was. **`npx vitest run` will fail dozens of
unrelated test files at import** — that's the signal. Grep for it before trusting a clean typecheck:

```bash
N=$(grep -n "=create<Factory>(" src/runtime/runtime.js | cut -d: -f1)
for n in fn1 fn2 ...; do
  head -$N src/runtime/runtime.js | grep -nE "[,{ ]$n[,}:]" | grep -v ":(\.\.\.args)=>$n(\.\.\.args)"
done
```//run this after every extraction, before `npx vitest run`. It caught two live bugs this session (one in
`providerProfiles`'s call, one in `searchFacets`'s call, both referencing `recordDbStatus` unwrapped).

**Was about to start, not done:** continuing the mechanical extraction (little left, see above) and then moving into
section B (Vue replacement of the dashboard/PDF Explorer/response cache). That first Vue-surface tranche is now
complete; the current next step is the remaining legacy surfaces listed below.

## Copilot progress through PR #93 (2026-09-22)

The work described above has since been carried forward and merged into `master`:

- The Response Cache, Dashboard, and PDF Explorer now have Vue-owned route/surface boundaries while preserving
  their legacy DOM IDs, classes, URL synchronization, dialogs, disabled states, and characterization coverage.
- The unified theme work and related provider-layout changes were merged without changing the runtime contract.
- The corpus and metadata fixes addressed indexed-value extraction, accumulated autocomplete suggestions and repeated
  array additions, slice requeueing, Corpus Builder step progression, metadata-schema preview providers, provider
  routing, invalid `generation.num_ctx`, and Ollama embedding endpoint compatibility.
- Duplicate backend locale keys that blocked lint were removed without changing the canonical translations.
- Settings persistence now sanitizes the complete IndexedDB preference payload before structured cloning. PR #93
  contains that fix and merged on 2026-09-22.
- Validation completed for the merged work included frontend tests, typecheck, lint, production build, Storybook,
  DOM baselines, and Playwright/axe. Backend quality gates passed in GitHub Actions; local Windows validation did
  not have a Python launcher.

This is the end of the first Vue-surface tranche, not the end of the runtime decomposition. `runtime.js` remains
approximately 2,376 lines and `RuntimeSurface.vue` remains the compatibility host for surfaces that have not yet
been migrated.

## What is left, in order

### A. Move the remaining runtime.js clusters (mechanical, low risk each) — mostly DONE, see Session 5 status above

All the clusters originally listed here (workspace persistence, evidence/review selection, record editing, DB
presence/upsert, navigation/URL, the operations panel + RAG progress panel, modal helpers, the compare library, PDF
linking, app lifecycle) have been extracted into their own `domain/*.ts` factories (see the module list under "State of
the code" — add: modalDialogs, navigation, workspacePersistence, evidenceSelection, recordEditing, dbPresenceUpsert,
operationsPanelBridge, pdfLinking, appLifecycle, compareLibrary). What's left in `runtime.js` is small glue and the
render/DOM-coupled code that belongs with section B (`translateLegacyDom`, the collapsible MutationObserver, `shell()`,
`getShellSnapshot`, nav label translation). Skim the file before assuming another clean cluster exists; if one does,
follow the same procedure below.

Procedure per cluster (about 10 minutes each), from `web/`:

1. `bash ../scripts/runtime-refactor/extract_factory.sh <module> <createFactory> "fn1,fn2,..." "header line 1|header line 2" [importsJSON]`
   copies the functions verbatim (`mk_factory.py`), lists the missing names from `tsc` (TS2304), builds the `Deps` type, wires a
   `const {fn1,fn2}=createX({state, helper lambdas})` call into `runtime.js`, adds `Any` annotations (`fix_any.py`) and prints
   `LET` / `MISSING` warnings. `importsJSON` maps pure helpers to the module that exports them, for example
   `{"esc":"./html","icon":"./html"}` (the default); add e.g. `dockCollapsedSummary` from `./operationsDock`. Read
   `wire_factory.py` first: it inserts the new call right after the `createDashboardRenderer(` call; if a value dependency is
   declared later in `runtime.js`, move the call to after that declaration.
2. A helper that is a value (array, Map, object) rather than a function needs care. If only the cluster uses it, move the const
   into the new module (`WORK_METADATA_FIELDS`, `EDITOR_GROUPS`). If others use it, move the factory call after the const and pass
   it by value (`fileTimers`, `corpusCache`). A reassigned `let` (`urlSyncHook`, `shellRefreshHook`) must be passed as a getter
   (`getUrlSyncHook:()=>urlSyncHook`) when the code reads it as a value; a lambda wrapper is only right when it is called.
3. Fix leftovers by hand: `catch (error: Any)`, `let x: Any`, `new Set<Any>()`, `const changes: Any = {}`, unused-variable lint
   (prefix `_` or a one-line `eslint-disable-next-line` with a reason), then `npx prettier --write` the new file.
4. Verify (see Verification), commit, push. One cluster per commit. If the baseline does not cover the cluster, add scenarios
   first, in their own commit, recorded from the pre-move build.
5. Afterwards `python3 ../scripts/runtime-refactor/dead_functions.py` removes top-level functions nothing references (run it only
   after deleting a caller; it deliberately ignores the `export {}` block).

### B. Replace the three legacy views with Vue (risky; one view per commit)

Order: response cache (smallest), then the dashboard, then the PDF Explorer.

- Build a Vue component that produces the same DOM as the current renderer (class names, element order, ids used by tests), route
  it in `router/index.ts` instead of `RuntimeSurface`, and delete the renderer factory. Move that view's runtime-only CSS from
  `style.css` into the component's `<style scoped>` in the same commit (see `docs/STYLE_AUDIT.md` and `style_move.py`).
- The baseline must stay **unchanged**: the `home-*`, `styles-home-*`, `response-cache-*` and `pdf-explorer-*` scenarios. The harness
  already strips `data-v-*` and normalizes whitespace and comments; do not re-record snapshots to make a change pass.
- Dashboard: it fetches through the runtime (`refreshStores`, `refreshServerAnnotations`, `dashboardRecordPreview`), shows jobs via
  `renderOperationsPanel` and `mountOperationsPanelHost`, and a corpus builds card. Read from the existing Pinia stores
  (`useJobsStore`, `useCorpusStore`) and the runtime exports; the operations panel is already a Vue component mounted by
  `runtime/operationsPanelHost.ts`.
- PDF Explorer: uses PDF.js (`state.pdf.doc`), a canvas render token, text extraction (`extractPdfPageSmart` with an API fallback),
  record linking and LLM helpers. Keep the DOM ids (`pdfInput`, `openPdf`, `pdfPrev`, `pdfNext`, `pdfPageInput`, `extractPage`,
  `linkCurrentPdf`, ...): the baseline scenarios drive them.
- When the last legacy view is gone: delete `RuntimeSurface.vue`, `translateLegacyDom`, the MutationObserver, the collapsible
  enhancer, `legacyCompat.js`, unused `runtimeBridge.ts` exports, and shrink the `export {}` block.

### C. State and services to Vue idioms

Turn the `*Workspace` factories into composables that read Pinia stores instead of polling `runtime.get*Snapshot()`, and make
`annotationsService` call its factory directly. Do this per view, and only where a probe shows stale or wrong behavior (import a
file with distinct content while the view is open; see whether it updates). Do not bind view-local refs to store fields without a
test pinning the intended behavior first (`VectorStoresView.load()` has a branch that is dead today and would wake up).

### D. Styles (`web/src/style.css`, see `docs/STYLE_AUDIT.md`)

After each renderer is replaced its classes move into the component. Then: hand-resolve classes styled in several places (merge
duplicate selectors, then move the group), extract a small shared base layer (`btn`, `badge`, `chip`, `card`, forms) next to
`styles/tokens.css`, then normalize breakpoints, replace hard-coded colors with tokens, and only then reduce `!important`.
`CommandSearch.vue` is excluded from automatic moves (moving its rules changed its look).

### E. End of effort

Delete `PROGRESS.md`. Keep `docs/STYLE_AUDIT.md` only if CSS work continues.

## Verification (run all before each push; from `web/`)

```bash
npx vue-tsc --noEmit && npx eslint src && npx vitest run                     # 459 unit tests at last count
npx vite build
APP_PORT=5299 npx playwright test -c playwright.legacy.config.ts --workers=3  # DOM baseline, 131 scenarios, about 3 min
APP_PORT=15199 STORYBOOK_PORT=16006 npx playwright test --project=chromium-desktop --workers=2   # full e2e, 270 tests, about 13 min
```

Also run the Storybook build once per PR. `npx eslint .` reports errors in other people's `tests/frontend/corpus-builder-*.test.ts`
(pre-existing); lint what you touch. `npx prettier --check` flags `src/views/PdfWorkspaceView.vue` (existing compact style; leave it).

### The DOM baseline (`tests/e2e/legacy-dom-baseline.spec.ts`, snapshots next to it)

131 scenarios: normalized markup (`*.html`) and computed styles (`styles-*.txt`; light, dark, tablet, phone) for the dashboard, PDF
Explorer, response cache, every Vue view that talks to the runtime, the runtime-built dialogs, the operation dock and the backup
and restore flows. Scenario options: `nav` (click a sidebar item), `path` (open a Vue-native route directly), `load` (import the
sample JSONL), `records`, `role`, `scheme`, `viewport`, `fixtures` (API mocks; `liveJobs()` is a stateful jobs endpoint), `steps`,
`target` (`main`, `runtime` = `#main`, `dialog`, `app`, `dock`), `styles: true`.

- UTC and en-US pinned, `Math.random=0`, fixed clock, reduced motion; `data-v-*`, UUIDs, dates and the `Build <hash>` text masked.
- **Never regenerate snapshots to make a change pass.** New scenarios are recorded from the pre-change build in their own commit
  (`--update-snapshots=missing`; Playwright reports the first write as a failure, so rerun). The only snapshot changed for a bug fix
  so far is `jobs-dock-running`.
- Not covered (add before touching): hover and focus states, the bulk-edit and upsert-queue dialogs, the works-metadata editor and
  remove-work, confirm modals other than backup, restore and response cache, job types outside `RAG_JOBS`/`JOBS`, Research streaming.
- The PDF Explorer scenarios click the sidebar's "Corpus Builder", then the "PDF Explorer" tab (`inPdfExplorer`); the PDF is
  generated by `samplePdf()` in the spec.

## Gotchas learned (things that cost time)

- **Port 5199 may already be served by another session's build.** With `reuseExistingServer` the baseline then tests the wrong code
  (unrelated snapshot diffs everywhere). Use `APP_PORT=5299` (or any free port) and stop your own server afterwards with
  `scripts/runtime-refactor/kill_port.sh <port>`. Never `pkill -f` a word that appears in your own command line.
- Machine load (orphan Chromium, another Storybook) causes 30 s timeouts in random scenarios: check `uptime`, kill orphans, use
  `--workers=3`.
- Factory call sites must come after the `const`s they receive by value; hoisted `function`s are safe, later `const`s need a lambda.
  TDZ errors break dozens of unit test files at import.
  **This also happens if an *earlier* factory call references the moved name directly instead of as a lambda** — grep for it
  after every extraction (see Session 5 status above for the exact command); a clean `tsc`/eslint does not catch it, only
  `npx vitest run` failing many unrelated files does.
- `mk_factory.py` never indents bodies (template literals must stay byte-identical).
- After Prettier expands a dense `try{}catch{}`, an `eslint-disable no-empty` comment no longer lines up: use a commented empty catch.
  Prettier also breaks Python `str.replace` patterns aimed at formatted code: use regex or line-based edits.
- Some tools turn a ` ` escape into a literal NUL byte; check new files for it.
- Import de-duplicates by content hash: identical JSONL content does not import twice.
- The runtime restores the saved workspace at start-up; loading a JSONL too early races with it (the baseline waits for network idle).
- The direct URL `/pdf?mode=explorer` renders the dashboard (the runtime's view comes from in-app navigation); reach the Explorer
  through the sidebar, then the tab.
- Do not `git stash` (the stack is shared across worktrees) and do not `git checkout origin/master --`; use a WIP commit.
- Copilot works in parallel on `ajschlosser-unified-web-theme` (UiPageHeader, tokens, `style.css`). It touches no runtime file, but
  when it merges the Vue-view baseline snapshots (page headers) will change: re-record those from the pre-change build in a separate
  commit, and expect `style.css` conflicts with any CSS move.
- Dashboard date keys use local midnight then `toISOString()`, so tests pin `TZ=UTC`.
- `countOccurrences(text, [])` loops forever (legacy bug, unreachable with real input; left on purpose).

## Helper scripts (`scripts/runtime-refactor/`)

`extract_factory.sh` (one-command cluster move), `mk_factory.py`, `wire_factory.py`, `fix_any.py`, `dead_functions.py`,
`kill_port.sh`, `deps.py` (names and state fields a group uses), `purity.py`, `mv_fn.py`, `splice.py` (older pure-helper moves),
`style_audit.py`, `style_prune.py`, `style_move.py` (CSS; see `docs/STYLE_AUDIT.md`).

## Merged PRs and next branch

PR #86 (`claude/runtime-refactor-18`) delivered the dashboard, PDF Explorer and response cache renderers, three dialog
factories, the operation dock, backup/restore and response-cache coverage, and three runtime bug fixes. The follow-up
theme and bug-fix work merged through PRs #90, #91, #92, and #93.

The next runtime tranche must be cut from the latest `master` and should begin with one remaining legacy surface,
preferably Corpus Builder or Tools, after confirming its current DOM baseline. Do not combine that migration with
unrelated CSS cleanup or provider changes. Preserve the existing runtime exports and delete compatibility code only
after every dependent surface has moved.
