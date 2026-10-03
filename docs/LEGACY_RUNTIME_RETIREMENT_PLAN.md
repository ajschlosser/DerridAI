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

# Legacy runtime retirement plan

Copyright 2026 Aaron John Schlosser, PhD.

This document analyses how far the web client still depends on the legacy runtime
(`web/src/runtime/runtime.js` and the `web/src/domain/` modules extracted from it),
and lays out an incremental plan to retire it. **It is also the cross-session progress
tracker for that work: read "Progress log" first, and update it at the end of every
session or PR.**

It is a planning document, not a description of shipped behavior. Verify claims against
the code before relying on them (the counts below were measured on 2026-10-01).

## 1. Why this exists: sticky navigation

Users occasionally reach a state where sidebar and breadcrumb navigation stop working.
The router itself is small (`web/src/router/index.ts`, one `beforeEach` guard). The
fragility is the bridge between Vue Router and the legacy runtime, which keeps its own
notion of "where am I":

| Concern          | Router side                       | Legacy side                                                                                      |
| ---------------- | --------------------------------- | ------------------------------------------------------------------------------------------------ |
| Current location | `route`                           | `runtime.state.view` + `state.activeFileId`, `state.activeStore`, …                              |
| History          | browser history / `router.back()` | `state.navHistory`, `state.navForward`, plus `nativeBackPath` / `nativeForwardPath` in `App.vue` |
| URL              | `router.push/replace`             | `urlFromState()` / `syncUrl()` → `setUrlSyncHook` → router                                       |
| Browser back     | router's own `popstate` listener  | runtime's `popstate` listener → `applyUrlState()` + `renderView()`                               |

Mechanisms that can wedge navigation (found by reading the code; not reproduced):

1. The URL-sync hook installed in `App.vue` `startRuntime` swallows every router failure
   (`void method(target).catch(() => undefined)`). `router.push` reports aborted or
   cancelled navigations as a returned failure value, not an exception, so a rejected
   push leaves `state.view` changed and the URL unchanged, silently.
2. `navigateNative` returns early when the target equals the current URL. After the
   state drifts, the item the user is "on" does nothing when clicked.
3. `navigateTo` in `domain/navigation.ts` mutates `state.view`, persists prefs, syncs
   the URL, then calls `shell()` and `renderView()` with no guard. An exception in
   `renderView()` leaves a half-applied transition.
4. Three independent histories (router, `navHistory`, `nativeBackPath`) disagree about
   what Back means, and the breadcrumb Back button chooses between two of them.
5. The `beforeEach` guard awaits `auth.loadStatus()` while `!auth.initialized`; a hung
   status call blocks all navigation until the request times out.
6. `startRuntime` can fail after installing the hook, leaving the router working while
   legacy-backed views never render.
7. Unknown paths and failed capability checks redirect to `/` silently.

## 2. Size and shape of the legacy runtime

Measured 2026-10-01:

- `runtime/runtime.js` 3,606 lines (plain JS); `legacyCompat.js` 317;
  `vectorCollectionBridge.js` 329; `runtimeState.ts` 189; `runtimeBridge.ts` 58.
- `domain/` has 103 files, about 22,700 lines. Much of it is real logic extracted from
  the runtime (`navigation.ts`, `*Workspace.ts`) and imperative DOM dialogs
  (`jobDialogs.ts` 1,113 lines, `recordDialogs.ts` 806, `workDialogs.ts` 701,
  `modalDialogs.ts` 85).
- 29 non-test files import the runtime. Most-used members from `.vue` files:
  `notifyToast` (47 call sites), `runtime.state` (20), `navigateTo` (16),
  `persistPrefs` (14), `reviewKey` (8), `navigateView` (6).
- `renderView` has 56 references; about 40 `innerHTML` uses remain in `runtime.js` and
  `domain/`, so some UI is still imperative DOM.
- Most routes are `vueNative: true`. Roughly three named routes (home, rag,
  corpus-builder) were not marked native when measured; verify before relying on it.

## 3. What makes full removal hard

1. **Shared state.** `runtime.state` holds the view, loaded files, selection, store and
   search state, PDF state and more, and native views still read it. It must move into
   Pinia stores one slice at a time.
2. **Imperative toasts and modals.** `notifyToast` and `openMessageModal` are called
   everywhere; they need a Vue store plus host component before callers can let go.
3. **URL state contract.** `urlFromState` / `applyUrlState` / `currentTableUrlState`
   encode view, file, record, store and compressed table state (`ts=`) into shareable
   URLs. Existing links must keep working. `/pdf`, `/system-data` and
   `/response-cache` already carry redirects for older shapes.
4. **Persistence.** `persistPrefs` and the browser-local JSONL files in IndexedDB need
   an explicit new home; do not lose user data.
5. **Accessibility parity.** DOM-built dialogs implement focus trapping and
   announcements that the Vue replacements must match or improve.
6. **Test coverage.** Behavior now implicit in the runtime needs Vitest/Playwright
   coverage before each slice moves.

## 4. Plan

Each step is its own PR based on `master` (no stacked PRs). Within a step, keep
commits small. Every behavior change gets a regression test.

### Step 1 — Router owns navigation, history and the URL

Goal: remove the legacy runtime from _navigation_ and fix the sticky-navigation causes.
This is the smallest slice that eliminates the dual-history problem and is a
prerequisite for the later steps.

1.1. **Router-owned history.** Add `web/src/router/navigationHistory.ts`: a small
module that reads Vue Router's `history.state` (`back`, `forward`, `position`) to
expose `canGoBack`, `canGoForward`, `back()`, `forward()`, and a bounded
path → label record fed by `router.afterEach`, so the breadcrumb can still say
"Back to <page>". Delete `nativeBackPath` / `nativeForwardPath` and the
`triggerBack` / `triggerForward` branches in `App.vue`.
1.2. **Remove the runtime's history.** Delete `state.navHistory`, `state.navForward`,
`goBack`, `goForward`, `triggerBack`, `triggerForward`, and the
`canGoBack/canGoForward/backLabel/forwardLabel` fields in the shell snapshot and
`stores/shell.ts`. Stop persisting them in `workspacePersistence.ts` (old stored
values are simply ignored on load). Back/forward restores table state because the
URL already carries it (`ts=`), and the runtime's `popstate` handler applies it.
1.3. **Never swallow a failed navigation.** In the URL-sync hook, inspect the value
returned by `router.push/replace`. For a failure (aborted, cancelled, redirected
away from the requested target), reconcile the runtime from the router's current
location through one runtime entry point (`syncFromLocation`: `applyUrlState` +
`persistPrefs` + `shell` + `renderView`, the same work the `popstate` handler
does) and log the failure with `console.warn`. Unexpected exceptions are logged,
not discarded.
1.4. **Reconcile on every settled route change.** A `router.afterEach` that, when the
route's legacy view differs from `state.view`, calls `syncFromLocation`. This makes
the router the authority and `state.view` a follower, so drift heals itself.
1.5. **Equality early-return.** `navigateNative` may only short-circuit when both the
router location and the runtime view already match the target.
1.6. Tests: Vitest for the history module (labels, bounds, position edge cases), the
hook's failure handling, and the equality rule; Playwright smoke that back/forward
and sidebar navigation keep working after a rejected navigation.
1.7. Docs: `docs/USER_GUIDE.md` only if Back/Forward user-visible behavior changes;
release note under `docs/notes/<version>.md` when the release is cut.

Out of scope for step 1: moving `state.view` out of the runtime, the `popstate`
double-listener (both listeners remain until step 4), toasts, dialogs, state slices.

### Step 2 — Toasts and modals as Vue services

Replace `notifyToast` and `openMessageModal` with a Pinia store and host component
(`role="status"` / `role="alertdialog"` semantics, focus return). Keep the runtime
functions as thin shims forwarding to the store, then migrate the ~47 call sites and
delete the shims.

### Step 3 — Remaining routes and dialog families

Make `home`, `rag`, and `corpus-builder` (and any other non-native view found by the
audit) Vue-native, and port `domain/*Dialogs.ts` family by family
(`modalDialogs`, `workDialogs`, `recordDialogs`, `jobDialogs`). Each family: write the
Vue component with a Storybook story, port behavior and focus management, delete the
imperative code, and keep an e2e check.

### Step 4 — State slices to Pinia, then delete the runtime

Move `state` slices one at a time (files/selection, store/search, PDF, preferences),
each behind a typed store with the same persistence keys. Replace
`urlFromState`/`applyUrlState` with route-query handling that still accepts every
existing URL shape. Remove the runtime's `popstate` listener, `renderView`, then
`runtime.js`, `legacyCompat.js`, `vectorCollectionBridge.js` and `runtimeBridge.ts`.

### Risks

- Old bookmarks and shared links (`?view=`, `ts=`, `/pdf`, …) must keep resolving.
- IndexedDB / localStorage migrations must not discard browser-local corpora or prefs.
- Labels for Back/Forward previously came from runtime view names; they now come from
  route metadata, so every route needs a title key (most already have one).

## 5. How to continue in a new session

1. Read the progress log below, then `git log` on the task branch.
2. Re-measure the figures in section 2 before relying on them.
3. Work the next unchecked item; update the log and tick the boxes in the same commit.
4. Base each PR on `master`; name merge-order dependencies in the PR body.

## 6. Progress log

Task branch for Step 1: `task/router-single-source-of-truth`
(worktree `../DerridAI-router-truth`, created from `origin/master`).

- [x] 2026-10-01 — Analysis and plan written (this document).
- [x] Step 1.1 router-owned history module (`web/src/router/navigationHistory.ts`, created per `App.vue` from `useRouter()`)
- [x] Step 1.2 remove runtime history (`navHistory`/`navForward`, `goBack`/`goForward`, `triggerBack`/`triggerForward`, shell snapshot fields, persisted prefs keys)
- [x] Step 1.3 URL-sync hook surfaces failures and reconciles (`runtime.syncFromLocation`)
- [x] Step 1.4 reconcile on settled route change (`router.afterEach` in `App.vue` using `runtime.viewForPath`)
- [x] Step 1.5 equality early-return tightened (`navigateNative`)
- [x] Step 1.6 tests: `tests/frontend/navigation-history.test.ts`, `tests/frontend/sidebar-startup.test.ts` (new describe), `tests/e2e/navigation-history.spec.ts`
- [x] Step 1.7 Step 1 merged as PR #405 (no USER_GUIDE change; release note when the version is cut)
- [ ] Step 2 toasts and modals (branch `task/toast-modal-vue-services`, worktree `../DerridAI-toasts`)
  - [x] 2.1 `toast` is a shim over the existing `composables/notifications` host (`AppNotifications.vue`); tone inference, hover/focus pause, bounded stack
  - [x] 2.2 `openMessageModal` is a shim over `composables/messageDialog` + `MessageDialogHost.vue` (native modal `<dialog role="alertdialog">`, queued, focus returns to the opener); Vitest + Storybook story
  - [x] 2.3a all `.vue` callers (views, `SystemDataResponses`, `PdfExplorerSurface`) call `toast` (`composables/notifications`) and `openMessageDialog` directly; `toast` keeps the legacy loose tone names. Not carried over: the legacy French `translateDynamicUiValue` pass over toast text (native callers already pass translated strings).
  - [x] 2.3b `openMessageModal` is gone: domain modules, `runtime.js` and `vectorCollectionBridge.js` import `openMessageDialog` directly; the `modalDialogs` shim and `runtimeBridge` export are deleted.
  - [x] 2.3c the hard-coded English toast strings in `domain/*` and `runtime.js` are keyed (`runtime.toast.*`, reusing `dynamic.*` keys that already existed), in en-US and fr-CA. Only three of them were translated before (cleared history, cleaned records, exported records); the rest showed English in fr-CA.
  - [x] 2.3d the injected `toast`/`notifyToast` is gone: every caller imports `toast` from `composables/notifications`, and `operationDock`, `runtime.js`, `runtimeBridge.ts` no longer define or forward it. The helper no longer infers a tone from English wording; every call states its tone (success/info/warning/danger). Remaining strings (job progress, cancellation detail, copy-JSON label, record fallbacks) are keyed in en-US and fr-CA.
  - [x] Accessibility of `AppNotifications.vue`: named polite live region (`aria-atomic=false`, additions only), tone announced in text plus a non-colour symbol (WCAG 1.4.1), Escape dismisses, error notifications do not auto-dismiss (2.2.1), 24px close target. Storybook story added; axe (WCAG 2.2 AA tags) clean in light and dark on that story.
  - Known unrelated failures: the 15 `legacy-dom-baseline` snapshots were already stale on master (the "Automatic sizing" control); the `corpus-builder-theme-sweep` a11y specs need a Storybook index service this environment lacks.

  - Known differences: toasts now stack (up to 5) instead of replacing one another, and the bold HTTP-status styling is gone. `legacy-dom-baseline` snapshots for settings/research were already stale on master (the "Automatic sizing" control); not regenerated here.

- [ ] Step 3 dialogs, family by family (routes are already Vue views; `vueNative` is unread metadata)
  - [x] `workDialogs`: mixed-values dialog (`MixedWorkValuesDialog.vue` + `composables/mixedWorkValuesDialog.ts`)
  - [x] `workDialogs`: remove-work dialog (`RemoveWorkDialog.vue`; the deletion stays in the legacy forwarder as a `confirm` callback)
  - [x] `workDialogs`: separate-works dialog (`SeparateWorksDialog.vue`, same `confirm` callback pattern)
  - [x] `workDialogs`: metadata editor (`WorkMetadataEditorDialog.vue`; `workMetadataControl` HTML became `workMetadataControlSpec`, and control values stay strings for `parseWorkMetadataValue`)
  - [x] `workDialogs`: LLM metadata lookup dialog (`WorkMetadataLlmDialog.vue` + `composables/workMetadataLlmDialog.ts`; reuses `ProviderProfileSelect`; the job request stays in the legacy forwarder as a `start` callback; baseline `dialog-works-populate-all` retired)
  - [x] `workDialogs`: proposal-result dialog (`WorkMetadataProposalDialog.vue` + `composables/workMetadataProposalDialog.ts`; value parsing, grouping and `applyRecordChanges` stay in the forwarder's `apply` callback; `workflowProviderSelectHtml`/`workflowProviderSummaryHtml` deleted from the runtime). `workDialogs` is now fully ported
  - [x] `recordDialogs`: merge-files dialog (`MergeFilesDialog.vue` + `composables/mergeFilesDialog.ts`; the merge itself stays in the forwarder's `merge` callback; `mergeDialogHtml` and baseline `dialog-merge` retired)
  - [x] `recordDialogs`: bulk field editor (`BulkFieldEditorDialog.vue` + `composables/bulkFieldEditorDialog.ts`; the component owns scope/field/value state and prefill, the forwarder supplies `inspect` and an `apply` callback that parses, confirms and writes; `bulkFieldEditorHtml` deleted). Its "only different" checkbox was never read by the legacy handler (an edit always skips unchanged records) and is kept as it was
  - [x] `recordDialogs`: OCR cleanup (`OcrCleanupDialog.vue` + `composables/ocrCleanupDialog.ts`; scope resolution and the confirmation stay in the forwarder's `choose` callback; `ocrCleanupDialogHtml` and baseline `dialog-ocr-cleanup` retired)
  - [x] `recordDialogs`: record history browser (`RecordHistoryDialog.vue` + `composables/recordHistoryDialog.ts`; the component owns the version cursor, the forwarder supplies live `versions`, and `restore` / `restoreOriginal` / `clear` callbacks that do the restore, confirmation, refresh and toasts; `recordHistoryDialogHtml` deleted. Disabled-reason hints are `title`s now, not `decorateDisabledControls`)
  - [x] `recordDialogs`: record editor and store record editor (one `RecordFieldEditorDialog.vue` + `composables/recordFieldEditorDialog.ts`; the pure field-kind/parse rules live in `domain/recordEditorFields.ts`; the forwarders supply `save`, which diffs against the record and applies or PATCHes. `fieldEditor`/`parseEditor`, `recordDialogMarkup.ts` and baseline `record-edit-sheet` retired. The on/off label of a boolean now uses `ui.on`/`ui.off` instead of hard-coded English "Enabled/Disabled")
  - [x] `recordDialogs`: upsert queue (`UpsertQueueDialog.vue` + `composables/upsertQueueDialog.ts`; the forwarder supplies plain-data `items()` (re-read after a removal), `remove` and `sync`. The change list is a disclosure button with `aria-expanded`; unchecked state now survives removing a record). `recordDialogs` is now fully ported
  - [x] `jobDialogs`: record preview (`RecordPreviewDialog.vue` + `composables/recordPreviewDialog.ts`; the forwarder formats labels and values, the component only renders; the "copy" button keeps `data-copy-row-key` for the page-level handler; `recordPreviewMarkup.ts` deleted)
  - [x] `jobDialogs`: LLM tool result (`LlmToolResultDialog.vue` + `composables/llmToolResultDialog.ts`; the forwarder builds a typed body and one optional follow-up `action`, which runs after the dialog closes; `llmToolResultBody`/`llmToolResultDialogHtml` are gone. The grade view still arrives as escaped `gradeHtml` from the shared renderer)
  - [x] `jobDialogs`: PDF draft record (`PdfDraftRecordDialog.vue` + `composables/pdfDraftRecordDialog.ts`; the component owns the JSON text and destinations, the forwarder's `save` validates, writes and resolves true to close, so a rejected draft keeps its edits; `pdfDraftRecordHtml` is gone)
  - [x] `jobDialogs`: job details (`JobDetailsDialog.vue` + `composables/jobDetailsDialog.ts`; the forwarder composes plain-data facts, events and JSON summaries, and supplies `onCancel` / `openResult` callbacks that run after the dialog closes; baselines `dialog-job-details-0..2` retired)
  - [x] `jobDialogs`: job results review (`JobReviewDialog.vue` + `composables/jobReviewDialog.ts`; the forwarder builds a plain-data `JobReviewView` and republishes it through the returned handle on every refresh, realtime event or resolution. The component owns the selection (indices into the rows, kept across republishes, default is every field but `text`); `apply` / `rejectSelected` / `discard` stay in the forwarder and resolve true when they changed something. Diffs still arrive as escaped HTML from `reviewDiffSides`. `jobReviewMarkup.ts` and baseline `dialog-job-results-review` retired; the footer buttons lost their icons)
  - [x] `jobDialogs`: LLM task launcher (`LlmTaskLauncherDialog.vue` + `composables/llmTaskLauncherDialog.ts`; the component owns the profile choice, run mode and generation fields (reloaded from the profile on change) and the warm-up status, the forwarder supplies plain-data `profiles`, `warm`, `manageProviders` and a `run` callback that parses, validates and starts the job or foreground call, resolving true to close, so a refused run keeps the edits; `llmToolMarkup.ts` deleted; it had no legacy baseline). The warm and provider buttons lost their icons
  - [x] `jobDialogs`: touch-up already opens through the `derridai:open-touchup` event to a Vue host, so nothing remains to port. `jobDialogs` is now fully ported; `showAppModal` is no longer injected into it
- [ ] Step 4 state slices and deletion (branch `task/state-slice-preferences`, worktree `../DerridAI-state-slices`, based on master)
  - Pattern: a shallow-reactive group in `state/workspaceState.ts`, bound onto the runtime `state` with `bindSharedState` (so the runtime and the persistence keys are unchanged) and exposed to Vue through a store in `stores/workspace.ts`. Vector, compare, search, works and corpus slices were already moved this way.
  - [x] shell layout preferences (`layoutState` / `useLayoutStore`: `sidebarCollapsed`, `collectionsCollapsed`, `operationToastsMinimized`, `operationStackPosition`, `collapsedPanels`). `App.vue` reads the sidebar flag from the store, so `sidebarCollapsed` left the shell snapshot. Persisted prefs keys are unchanged
  - [x] annotations (`annotationsState` / `useAnnotationsStore`) and FAQ (`faqState` / `useFaqStore`) slices; persistence keys unchanged
  - [x] table lists (`listState` / `useListsStore`: `selected`, `searches`, `listFilters`, `pages`, `pageSize`, `sorts`, `tableColumns`)
  - [x] configuration (`configState` / `useConfigStore`: `ragConfig`, `appConfig`, `llmConfig`), PDF Explorer (`pdfState` / `usePdfStore`) and review selection (`reviewState` / `useReviewStore`: `reviewSelection`, `selectedEvidence`)
  - [x] URL contract pinned by `tests/frontend/url-state-contract.test.ts` (path/`?view=`, file/record, store params, raw/compressed `ts=`, round trip, router-owned sub-paths). Finding: a known path wins over `?view=`, which only applies on a path with no view of its own
  - [x] service status (`statusState` / `useStatusStore`: `health`, `llmStatus`, `researcherProviderProfiles`, `providerStatuses`, `providerWarmups`, `warmup`); runtime, domain and persistence code unchanged
  - [x] record view (`recordViewState` / `useRecordViewStore`: researcher record/compare ids, `dashboardMetricIndex`, `lastViewedRecord`, `recordFind*`) and upsert progress (`upsertProgressState` / `useUpsertProgressStore`: `foregroundUpsert*`, `upsertState`, `upsertIgnored`, `operationProgress`)
  - [ ] remaining plain fields on `createRuntimeState` are `view`, `userContext`, `jobsPollTimer`, `storageReady` and translations
  - [x] URL codec split out of `navigation.ts`: `domain/urlStateCodec.ts` (`urlFromState`, `applyUrlState`, table-state read/write; needs only `state`, `activeFile`, `selectedIndex`, `dbSearchWhere`) and `domain/viewPaths.ts` (view↔path maps; still re-exported from `navigation`). `syncUrl`/`navigateTo` remain in `navigation.ts` because they call `shell`/`renderView`/`persistPrefs`
  - [x] the runtime's `popstate` listener is gone: `router/runtimeLocationSync.ts` resyncs the runtime after every settled router navigation that came from browser history (`history.listen` type `pop`, so same-view `ts=` changes still apply) or that lands on a different runtime view; guards and redirects now settle before the runtime repaints
  - [x] the router side applies URLs without the runtime: `view` is a shared slice (`navigationState` / `useNavigationStore`), `bindWorkspaceGroups` binds every shared group onto any object, and `domain/sharedUrlState.ts` exports `sharedUrlStateCodec` over it (the runtime's `createNavigation` is handed the same codec). `runtimeLocationSync` in `App.vue` now calls `sharedUrlStateCodec.applyUrlState()` and then `runtime.repaintAfterLocationChange()` (persist, shell, `renderView`). `?view=` and `ts=` links are untouched: the codec is the same code
  - [x] the URL-sync hook (router push/replace, failure reconciliation) left `App.vue` for `router/runtimeUrlSync.ts` (`createRuntimeUrlSyncHook`), unit-tested directly in `tests/frontend/runtime-url-sync.test.ts`
  - [x] `renderView` audit (2026-10-02, not yet acted on). It is a shell refresh, a `syncUrl({ replace: true })` normalisation, and three DOM passes on `#main` (`enhanceCollapsibles`, `decorateDisabledControls`, `translateLegacyDom`). Only `DashboardView`, `PdfExplorerSurface` and `SystemDataView` render `#main`; every other route skips the passes. The passes are **not dead**: `DashboardView` and `PdfExplorerSurface` call `decorateDisabledControls` / `enhanceCollapsibles` themselves, `vectorCollectionBridge` and `runtime.js` decorate dialogs, and `translateLegacyDom` is the only fr-CA path for legacy-built labels (it returns early in en-US). `decorateDisabledControls` carries hard-coded English reasons keyed on legacy element ids, so porting it must key and translate them (en-US and fr-CA). Replacement plan: a view-owned composable that runs the passes on mount and after updates, then delete the `renderView` calls; do not delete the functions before every `#main` view has its own call. Check the legacy-DOM baselines for each view first
  - [x] `renderView` no longer runs the three DOM passes. `DashboardView` now calls `enhanceCollapsibles` (so its collapse toggles appear after every refresh, not only after a `renderView`) and `decorateDisabledControls`; `PdfExplorerSurface` also calls `translateLegacyDom` (exported from the runtime). `SystemDataView` calls none: its content is Vue-native and its only pass was incidental. No test mounts `DashboardView`, so the Dashboard call is unit-untested; full Vitest (258 files) and typecheck pass; e2e and the legacy DOM baselines were not run, and the `pdf-explorer-*` baselines contain `ui-collapse` markup that may shift
  - [x] `decorateDisabledControls` reasons (and the two `dbUnavailableReason` strings) are keyed `runtime.disabled.*` in en-US and fr-CA; covered by `tests/frontend/disabled-control-reasons.test.ts`. Note: a full `vitest run` rewrites the licence header out of `web/tests/frontend/__snapshots__/*.snap`; restore them with `git checkout` before committing
  - [x] validation of the DOM-pass change: `npm run build` then `npm run test:e2e:legacy` (72 tests, including the `pdf-explorer-*` baselines and the dashboard disabled-control decoration) all pass
  - [ ] next: move `syncUrl`/`navigateTo` onto the router. Finding (2026-10-02): `urlFromState` already reads only shared slices plus `location`, and `sharedUrlStateCodec` exposes it without the runtime, so a router-side `navigateToView` (set the slices, `router.push(codec.urlFromState())`) is possible. Three runtime helpers still block it: `canAccessPage` (needs the auth user and capabilities), `persistPrefs` and `shell` (the shell snapshot refresh). `canAccessPage` is now ported: `domain/pageAccess.ts` (`canAccessView`, `userHasCapability`, `pageCapabilities`) is pure and tested in `tests/frontend/page-access.test.ts`, and the runtime delegates to it. `persistPrefs` (IndexedDB-backed, inside `workspacePersistence`) and `shell` (persist plus the shell refresh hook) remain. A router-side `navigateToView` built before they move would only re-wrap `createNavigation`'s `navigateTo` with the same injected dependencies and give Vue callers nothing new, so port those two first; `state.view` must stay set eagerly because the URL is derived from it (they still need `shell`/`renderView`/`persistPrefs`), then `renderView` and the runtime files
  - [x] `persistPrefs`, `workspacePrefs`, `flushWorkspacePrefs`, `shell` and `setShellRefreshHook` left the runtime: `domain/prefsPersistence.ts` (the debounced save, needs only state and a `put`) and `domain/sharedWorkspaceStorage.ts` (the one `workspaceDb` connection, `workspaceDbName`, the shared-state save, `shell`). `userContext` and `storageReady` became a shared `sessionState` slice, so the runtime and the router side see the same values. Also fixes the runtime clearing a different `prefsTimer` than the one the save used when the workspace database was deleted. Covered by `tests/frontend/shared-workspace-storage.test.ts`; typecheck and full Vitest pass. The legacy e2e run (build then `test:e2e:legacy`) reported 64 passed and several failures in `legacy-dom-baseline` (record-add-evidence, research-remove/clear-evidence, and the "views follow the loaded corpus" group); they were **not** investigated or compared against master before the user said to stop running Playwright locally. Treat them as unverified; let CI say
  - Local hooks and `scripts/preflight.sh` no longer run any Playwright suite (the `DERRIDAI_PREFLIGHT_BROWSER` opt-in is removed); CI owns browser, accessibility and publication acceptance
  - [x] `navigateTo`, `syncUrl`, `urlFromState`, `applyUrlState`, `navSnapshot` and the URL-sync hook left the runtime: `domain/sharedNavigation.ts` builds `createNavigation` over the shared state (`sessionState` for `canAccessView`, the shared `persistPrefs`/`shell`), and the runtime imports that one instance and installs `setRenderViewHook(renderView)` for the legacy part (unmount operations panel, URL normalisation). Vue code can now import `navigateTo` directly instead of `runtime.navigateTo`. `createNavigation` also now returns `getUrlSyncHook`, which the runtime destructured but was always `undefined`. Typecheck and Vitest pass (seven load-sensitive tests timed out in the full run and pass alone)
  - [x] Vue callers of `runtime.persistPrefs` / `runtime.navigateTo` (DashboardView, VectorStoresView, CompareView, SettingsView, LlmReviewWorkspace, PdfExplorerSurface) import `persistPrefs` and `navigateTo` from the shared modules; the two view tests no longer mock `persistPrefs`. Typecheck and full Vitest pass; no Playwright run
  - [x] `runtime.navigateView` is gone (it was `navigateTo(view, { href })`): App.vue, SettingsView, RecordView and SemanticMapFrame call `navigateTo` from `domain/sharedNavigation`; the bridge export is deleted and the four tests mock `sharedNavigation`. Typecheck and full Vitest pass; no Playwright
  - [x] `renderView` left the runtime: it is now `renderView` in `domain/sharedNavigation.ts` (unmount operations panel unless home, guard access, normalise the URL, refresh the shell on native routes), and `setRenderViewHook` is deleted. Covered by `tests/frontend/render-view.test.ts`; typecheck and full Vitest (264 files) pass; no Playwright run
  - [x] import census (2026-10-03): 29 non-test files still import `runtime.js`. `reviewKey` and `isEvidenceSelected` are now plain exports of `domain/evidenceSelection.ts`, and `PdfExplorerSurface.vue` no longer calls them through the runtime
  - [x] provider profiles left the runtime: `api` is `domain/legacyApi.ts`, `warmupProviderProfile` is `domain/providerWarmup.ts` (split from `appLifecycle`), and `domain/sharedProviderProfiles.ts` builds `createProviderProfiles` over the shared state (the runtime uses that same instance). `getProviderProfilesForUi` / `getDefaultProviderProfileId` are imported directly by six Vue callers. The service's `warmupProviderProfile` dependency is now typed as taking an id, which is what it always passed
  - [x] `openDatabaseCreationFromResearch` left the runtime: `domain/databaseCreationRequest.ts` sets the shared `vectorState` flag and dispatches the navigate event; ResearchView, SearchView and DashboardView import it, and the runtime hands the same function to the search and dashboard workspaces. Census (2026-10-03): `pauseRuntime` lives in `jobsWorkspace` with heavy deps and `getResearchJob` needs `researchJobForUi` plus `state.jobs`, so they need their own slices.
  - [x] role and URL helpers left the runtime for Vue callers: `domain/sharedSession.ts` (`isResearcher`, `hasCapability`, `canAccessPage`, also used by the runtime), `domain/searchQuery.ts` (`createUpdateSearchQuery`, used by `searchWorkspace` and by `domain/sharedSearchQuery.ts` for `SearchView`), and `syncUrl` / `formatTimestamp` imported directly by `DashboardView`, `PdfExplorerSurface` and `SystemDataResponses` (the bridge export is deleted). Remaining: `getResearchJob`, `pauseRuntime`, `refreshStores`, `enhanceCollapsibles`, `persistCurrentPdfAsset`, `triggerImport`/`triggerOperations`.
  - [x] `enhanceCollapsibles` (`domain/collapsiblePanels.ts`), `persistCurrentPdfAsset` (`domain/pdfAssetPersistence.ts`), `refreshStores` (`domain/sharedStores.ts`, also used by the runtime), `getResearchJob` (`domain/researchJobLookup.ts` factory shared by `researchWorkspace`; `domain/sharedResearchJobs.ts` binds it to `jobsState`) and `triggerOperations` (now `navigateTo("home")`) left the runtime for Vue callers; their bridge/runtime exports are deleted.
  - [x] `applyAppearance` (`domain/sharedAppearance.ts`, over the shared `appConfig` slice; `SettingsView` imports it) and `selectedIndex` (already exported by `domain/sharedUrlState.ts`; `PdfExplorerSurface` imports it, and the runtime now uses that same function) left the runtime. Covered by `tests/frontend/shared-appearance.test.ts`. Census (2026-10-03): the other small members (`getSearchShareHref`, `listSemanticMapSources`, `getCompareRecord`/`ensureCompareLibrary`, `registerExternalJob`, `navigateRecordWorkspace`, `openAnnotationsWorkspaceRecord`, `updateResearchConfig`) each close over a workspace factory built with runtime-owned dependencies; take them one workspace at a time, as `sharedProviderProfiles` did.
  - [x] the corpus cache left the runtime: `domain/corpusCache.ts` owns `corpusCache`, `invalidateCorpusCache`, `allRows`, `memoCorpus` and the fingerprint cache (`recordFingerprint`), over the shared `files` slice; the runtime imports them. Covered by `tests/frontend/corpus-cache.test.ts`. This also fixes `createDbPresenceUpsert`, which was handed `corpusCache` wrapped as a function, so its `corpusCache.version` cache key component was always `undefined`. Next for Compare: `getCompareRecord`/`ensureCompareLibrary` still need `recordOptionLabel` (record presenters), `researcherDbRecords` (search workspace) and `loadStorePage` (runtime); build those over shared state first.
  - [x] the Compare library left the runtime: `domain/sharedCompareLibrary.ts` builds `createCompareLibrary` over the shared state (the runtime uses that instance), and `CompareView` imports `getCompareLibrary`, `getCompareRecord` and `ensureCompareLibrary` from it. Its dependencies moved first: `domain/recordOptionLabel.ts` (pure; also used by `PdfExplorerSurface`), and `domain/sharedStoreRecords.ts` (`researcherDbRecords`, now removed from the search workspace, and `loadStorePage`). The runtime's exports of those five members are deleted. Covered by `tests/frontend/shared-compare-library.test.ts`. `CompareView` no longer imports the runtime: see the next entry.
  - [x] translations are a shared slice (`translationState`, in `sharedGroups`; `createRuntimeState` no longer declares them, and `setTranslationDictionary` writes the same slice). `domain/sharedTranslate.ts` exposes `tr`/`trf` over it. `domain/clipboardCopy.ts` holds `copyJsonToClipboard` and `copyCitation` (`modalDialogs.ts` and `evidenceSelection`'s copy are deleted; the runtime and `searchWorkspace`/`recordsWorkspace` receive the same functions). `CompareView` takes the researcher's picks from `useRecordViewStore` and `storeRecords` from the shared state, so it imports nothing from `runtime.js`. Covered by `tests/frontend/shared-translate.test.ts` and `clipboard-copy.test.ts`. Remaining `translations` readers in the runtime (`getLocale`, `relativeTimeLabel`) already go through the bound state.
  - [ ] next: `pauseRuntime` and `triggerImport` stay. `pauseRuntime` closes over the jobs workspace's private polling and resync timers, and `triggerImport` calls `importFiles`, which depends on runtime-owned `persistFileNow`, `invalidateCorpusCache` and `parseJsonl`. Both need the owning workspace (jobs; app lifecycle with file persistence) built over the shared state first, as `sharedProviderProfiles` was. Then re-count the remaining `runtime.*` members used by Vue code.
  - [x] census for `triggerImport` / `pauseRuntime` (2026-10-03, PR #465 merged; nothing moved). `importFiles` lives in `createAppLifecycle`, which takes 23 runtime-owned helpers; of those, `persistFileNow` is the gate (it also feeds backup, annotations and Records). `persistFileNow` comes from `createWorkspacePersistence`, whose inputs are mostly shared already (`workspaceDb` for `idbPut`/`idbGet`/`idbGetAll`, `invalidateCorpusCache`, `ensureProviderProfiles`, `applyUiTheme` over `state`); `serializableFile` is a one-line wrapper over `serializableRecordsFile`. The blocker is `restoreCurrentPdfAsset`, which needs `loadPdfMetadata` from `createPdfLinking`, whose deps (`allRows`, `applyRecordChanges`, `pdfLinks`, `normalizePdfLinkChanges`, `renderView`) are themselves runtime-owned. `pauseRuntime` needs `createJobsWorkspace` and its 20 helpers (`api`, `jobLabel`, `ensureJobProgressCard`, operations-panel refreshers, `reviewItemFromKey`, `touchupRecordPayload`, …). Suggested order: (1) `restoreCurrentPdfAsset` out of the runtime, with `loadPdfMetadata` split from `createPdfLinking` (it needs only pdf.js and `tr`); (2) a shared `persistFileNow`; (3) a shared app lifecycle for `importFiles`; (4) the operations-panel refreshers, then the jobs workspace.
  - [x] step 1 of that order: `loadPdfMetadata` is `domain/pdfMetadata.ts` (it never used `createPdfLinking`'s dependencies; `PdfExplorerSurface` imports it) and `restoreCurrentPdfAsset` is in `domain/pdfAssetPersistence.ts` over the shared `workspaceDb`; the runtime imports the latter. Covered by `tests/frontend/pdf-asset-restore.test.ts`. Next: a shared `persistFileNow`.
  - [x] step 2: `domain/sharedWorkspacePersistence.ts` builds `createWorkspacePersistence` over the shared state, `workspaceDb`, corpus cache, provider profiles and translations; the runtime imports `persistFileNow`, `persistFile`, `restoreWorkspace` and `fileTimers` from it. Covered by `tests/frontend/shared-workspace-persistence.test.ts`. Note: `createWorkspacePersistence` still builds its own, unused `createPrefsPersistence` (the runtime and Vue use `sharedWorkspaceStorage`'s); remove that when touching it. Next: step 3, a shared app lifecycle for `importFiles` (still needs `applyCompressedTableUrlState`, `clearFileDerivedState`, `idbDelete`, `refreshStoreWorks`, `stableJsonlFileIdentity`, `updateSystemCard`, `renderView`, `parseJsonl`).
  - [x] step 3: `importFiles` and `closeFile` left `createAppLifecycle` (now only warm-up and `checkHealth`) for `domain/fileLifecycle.ts`; `domain/sharedFileLifecycle.ts` builds it over the shared state and exports `importFiles`, `closeFile` and `triggerImport` (gated on `corpus.manage`, as `canUse("manageCorpus")` was). `stableJsonlFileIdentity` and `clearFileDerivedState` are plain modules (`jsonlIdentity.ts`, `fileDerivedState.ts`; the runtime keeps a one-line `clearFileDerivedState` wrapper for `workDialogs`). `App.vue` imports `triggerImport` directly; the runtime and bridge exports are deleted. Covered by `tests/frontend/file-lifecycle.test.ts`. Remaining for `pauseRuntime`: the jobs workspace (operations-panel refreshers, `api`, `jobLabel`, `ensureJobProgressCard`, `reviewItemFromKey`, `touchupRecordPayload`, `announceOperationDock`, `updateDbStatusElements`, `updateOperationStackCount`).
  - [x] `pauseRuntime` left the runtime's public surface: `domain/jobsPause.ts` holds the pause the jobs workspace registers (stops fallback polling, the resync timer and the realtime socket), and `App.vue` imports it; the runtime and bridge exports are deleted. Covered by `tests/frontend/jobs-pause.test.ts`. The jobs workspace itself still takes ten runtime-owned DOM helpers (`ensureJobProgressCard`, `updateOperationStackCount`, `refreshOperationsPanelOnly`, …), so it is not yet built over shared state. Typecheck and the affected Vitest files pass; no Playwright run.
  - [x] five leaf helpers left the runtime's public surface for `DashboardView` and `PdfExplorerSurface`: `compactNumber` (imported from `numberFormatting`), `defaultProviderProfile` / `providerDisplayName` (exported by `sharedProviderProfiles`), `relativeTime` (`domain/sharedRelativeTime.ts`) and `applyUiTheme` (`domain/sharedUiTheme.ts`). Covered by `tests/frontend/shared-leaf-helpers.test.ts`. Census (2026-10-03): the jobs workspace cannot be built over shared state yet because `operationDock`, `operationsPanelBridge`, job presenters and `dbPresenceUpsert` form a cycle with it (the dock calls `cancelBackgroundJob`, `removeFinishedJob`, `clearFinishedOperations`); breaking that cycle needs its own design step. Full Vitest (276 files) and both typechecks pass; no Playwright run.
  - [x] backup left the runtime: `domain/sharedBackup.ts` builds `createBackupWorkspace` over the shared state, database, workspace persistence and provider profiles, and owns `deleteWorkspaceDatabase` / `deleteAllDerridaiBrowserState`; `SettingsView` imports `backupContainsCredentials`, `downloadFullBackup`, `restoreFullBackup` and `deleteAllDerridaiBrowserState` from it, and the runtime exports are deleted. `settings-view.test.ts` mocks the new module. Full Vitest and both typechecks pass; no Playwright run.
  - [x] the provider-profile UI surface left the runtime for Vue callers: `sharedProviderProfiles` now exports the remaining `*ForUi` functions (save/add/remove/default/test/warm, warm-on-start, statuses, warm-ups, request config) and `syncResearcherProviderProfiles` (moved out of `runtime.js`). `ProvidersView` and `useCorpusProviderConfiguration` no longer import the runtime; their tests mock `sharedProviderProfiles`. Full Vitest and both typechecks pass; no Playwright run.
  - [x] census for the Search workspace (2026-10-03; nothing moved). `createSearchWorkspace` takes about 50 runtime-owned helpers. Roughly 30 come from five factories: `createSearchFacets` (needs `recordDbStatus`), `createEvidenceSelection` (needs `recordDbStatus`, `localRecordKey`, `storeReceipt`, `ragEvidenceRecordPayload`), `createDbPresenceUpsert`, `createRecordPresenters` (needs `recordDbStatus`) and the record dialogs (`openBulkFieldEditor`, `openStoreRecordEditor`, `openTouchup`). Everything funnels through `createDbPresenceUpsert`, which needs the jobs cluster (`startJobPolling`, `syncJobProgressToasts`, `refreshOperationsPanelOnly`) plus `candidateChromaIds`, `corpusStoreExists`, `dbUnavailableReason`, `hasCorpusDb`, `localRecordKey`, `notifyVectorStoresChanged`, `recordFingerprint`, `storeReceipt`, `upsertAuditDelta`, `upsertRecordPayload` and `workIndex`. So the order is: (1) break the jobs/dock/panel cycle with a late-binding facade like `domain/jobsPause.ts`, (2) shared `dbPresenceUpsert`, (3) shared `searchFacets`, `evidenceSelection` and `recordPresenters`, (4) the three record dialogs, (5) the Search workspace and its 29 `SearchView` calls. Each step is its own PR-sized slice.

Notes for the next session:

- Step 2 is complete on branch `task/migrate-toast-modal-callers` (worktree `../DerridAI-toasts`, four commits after
  `origin/master` at e84d5e0c). It is **not pushed and has no PR**: push it, open the PR against `master`, and
  tick Step 2 in the list above after CI.
- Validation run: `vue-tsc` (app and tests), full Vitest (233 files, 1402 tests), production and Storybook builds,
  the locale/release Python tests, the legacy e2e suite, and axe (WCAG 2.2 AA tags, light and dark) on the
  Notifications story. Not run: Docker, the full e2e suite.
- Open question: 15 `legacy-dom-baseline` snapshots (research-\*, backup/restore) were already stale on master
  (the "Automatic sizing" Settings control). Decide whether to regenerate them, delete the ones whose surface is
  already Vue-native, or leave them until Step 3 retires each dialog family. Check whether CI runs
  `test:e2e:legacy` as a blocking job first.
- Next: Step 3 (make `home`, `rag` and `corpus-builder` Vue-native, port `domain/*Dialogs.ts` family by family),
  retiring each family's snapshots with it.
- Navigation debt from Step 1 is unchanged: `state.view` still follows the router only for paths in
  `pathViewMap`, (the runtime's own `popstate` listener was removed in Step 4; see `router/runtimeLocationSync.ts`).
- `npm run format:repo:check` reports unrelated files in this environment (generated `sdk/dist`, `.pytest_cache`).
- Never run Prettier over `web/tests/e2e/**/*-snapshots`; it fails on them and rewrites some.
- Step 3 correction (2026-10-01): `home`, `rag` and `corpus-builder` already render Vue views; what keeps them tied to
  the runtime is their `runtime.*` / `runtime.state` reads (Step 4). Step 3 is therefore the imperative dialogs only.
  Pattern used for the first slice: a composable holds the request, a host component mounted in `App.vue` renders it
  in a native modal `<dialog>`, and the legacy function stays as a thin forwarder until its callers move.
- Legacy e2e gotchas: `vite preview` serves `web/dist`, so run `npm run build` first; port 5199 may be held by a stale
  server from another worktree (use `APP_PORT=<free port>`). A ported dialog's baseline is retired by adding `contains`
  to its scenario, listing the name in `nonSnapshotScenarios` (`scripts/check-legacy-snapshots.mjs`) and deleting the
  `.html`; done for the separate-works, edit-metadata and remove-work dialogs.
