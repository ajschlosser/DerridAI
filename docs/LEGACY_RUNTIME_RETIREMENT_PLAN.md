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

- [ ] Step 3 routes and dialogs
- [ ] Step 4 state slices and deletion

Notes for the next session:

- Step 1 is implemented but **uncommitted** in the worktree as of 2026-10-01; commit, open the PR against
  `master`, and tick 1.7 after CI.
- Validation run so far: `vue-tsc` (app and tests), full Vitest (230 files, 1389 tests), the new Playwright
  spec, `tests/test_release_consistency.py`, Prettier on touched files. Not run: Storybook build, Docker,
  the full e2e suite.
- Known behavior change: the Back/Forward tooltip now names the previous _route title_ instead of the old
  runtime view label, and Back now follows real browser history (including query-only changes such as
  a table-state URL), where the runtime used to keep its own 50-entry snapshot list.
- Remaining navigation debt after Step 1: `state.view` is still written by the runtime and follows the router
  only for paths in `pathViewMap`; native-only routes (e.g. `/languages`) leave it unchanged. The runtime's
  own `popstate` listener still exists alongside the router's.
- Local setup: the worktree's `web/node_modules` came from a fresh `npm ci` (the main checkout's copy was
  stale and lacked `@tanstack/vue-query`).
