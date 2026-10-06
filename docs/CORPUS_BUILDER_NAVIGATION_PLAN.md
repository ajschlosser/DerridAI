# Corpus Builder Navigation and Workflow Smoothness Plan

## Purpose

This plan addresses the interaction friction observed in DerridAI's global navigation and especially in Corpus Builder's Setup → Build → Review → Publish workflow. The goal is to make navigation feel immediate, predictable, and browser-native without changing scholarly semantics, provenance guarantees, build lifecycle rules, or publication invariants.

The main implementation principle is to reduce the number of independent state authorities involved in one navigation action. Vue Router should own canonical application navigation. Corpus Builder should treat its route-backed state as one coherent snapshot rather than several loosely synchronized query parameters.

## Implementation status

The first implementation slice landed in PR #562. Phases 2–7 are implemented and covered by the merged frontend regression suite. The stale-chunk deployment-coherence fix described below also landed there.

Phase 1 is now resumed after the legacy-runtime retirement completed on 2026-10-04. Canonical shell navigation (desktop sidebar, mobile navigation, command palette, top-bar destinations, and the shared `derridai:navigate-native` path bridge) now asks Vue Router to navigate first. The remaining compatibility workspace state follows the settled route through the existing location-sync path instead of initiating the forward navigation. Same-route clicks only repair drift by re-deriving compatibility state from the current URL; a router-refused navigation leaves that state untouched.

Phases 8 and 9 are implemented in the continuation branch/PR #564:

- **Phase 8:** stacked sticky page chrome is removed, the phase header behaves the same in Build and Review, and restart actions now distinguish retaining the current source from choosing another source.
- **Phase 9:** reconcile-before-publish remains authoritative while publication reuses in-place build synchronization, avoids redundant full build-list reads, and aborts if the reviewer changes build context before publication begins.

Phase 10's route-commit slice landed in PR #565. Top-level routes now commit through synchronous progressive route entries, so URL/history, breadcrumbs, active navigation, and a destination-owned loading frame can update before the destination JavaScript chunk resolves. Stale-deployment recovery remains guarded and ordinary chunk failures recover in the committed destination.

Phase 10's page-local hydration audit remains active in parallel with the now-unblocked Phase 1 router-ownership cleanup. Corpus Builder now prioritizes route-critical restoration: build discovery, the route-addressed build snapshot, and requested review topology hydrate without waiting for Setup-supporting provider, corpus-profile, or source-catalog reads. Those supporting reads begin immediately and continue in parallel. This keeps a deep-linked Build/Review/Publish workspace from being held behind unrelated Setup data while preserving the same authoritative build and review reads. The remaining work is the workspace-by-workspace audit for pages and regions that still gate useful shells or independent content on all-or-nothing initial hydration.

The next page-local slice moves Operations hydration into the Vue-owned Operations panel itself. The Operations route now mounts its panel immediately instead of waiting for a jobs refresh before any destination content can appear. The panel distinguishes an unresolved first read from a confirmed empty queue, retains known operations while refreshing, and exposes a local retry state if the transport fails. The Home dashboard also mounts its Operations region independently of its unrelated dashboard refresh. Compare now renders both comparison panes and their controls before its record-library hydration completes, with loading/error state local to the library region and without prematurely claiming the library or comparison is empty. Providers was also re-audited: its profile/status source is synchronous local application state rather than a network read, so the artificial one-frame loading gate is removed and the actual provider workspace renders on the first frame.

System Data is now being converted to the same retained-refresh contract instead of using a single loading branch for every read. Advanced internal-vector inspection keeps a successful collection snapshot and read-only console mounted while a refresh runs or fails. Saved Responses and Metadata Examples distinguish the last successfully displayed query identity from the requested identity: same-query refreshes retain rows and show local Updating/stale feedback, while a changed search/filter/page shows a placeholder rather than relabeling old rows as the new results. Metadata-example counts are withheld until the requested filter identity succeeds, and record-detail state is cleared when its result identity changes.

## Current problems

### 1. Global navigation has two forward-navigation authorities

Many sidebar destinations currently route through the legacy runtime bridge before Vue Router settles the route. This produces an avoidable sequence of runtime state mutation, preference persistence, shell repaint, URL synchronization, and then router navigation.

For canonical routes, forward navigation should be router-first. The legacy runtime should follow a settled route only where compatibility state still needs synchronization.

### 2. Corpus Builder mixes deliberate and automatic history entries

Workspace changes use the same `router.push()` path whether the user explicitly clicks a phase or the application advances after starting a build, publishing, or resolving a blocker. Browser Back can therefore visit workflow states the user did not deliberately navigate to.

Explicit user navigation should normally push. Automatic workflow transitions should replace.

### 3. The visible workflow changes shape

The underlying model has four stable workspaces:

`Setup → Build → Review → Publish`

The header currently groups Build and Review into one top-level phase and reveals a secondary sub-navigation only while that grouped phase is active. This makes the user's mental map change as state changes.

The header should expose all four phases continuously, with clear unavailable, available, current, and complete states.

### 4. Builder / Source Explorer mode changes remount the workspace

`PdfWorkspaceView.vue` currently uses mutually exclusive `v-if` branches. Switching from Corpus Builder to Source Explorer destroys Corpus Builder. Returning remounts it and re-runs initialization, data reads, review hydration, and realtime setup.

The two sibling surfaces should preserve state across mode changes. Expensive activity should suspend while inactive and reconcile lightly when reactivated.

### 5. Builder and Explorer leak route state into one another

The full query string is currently copied when changing between Corpus Builder and Source Explorer. Builder-only state such as `workspace`, `build`, `queue`, and `record` can leak into Explorer; Explorer-specific state can leak back.

Each route should have an explicit query-state whitelist, with only intentionally shared source context crossing the boundary.

### 6. Corpus Builder route state is synchronized by several independent watchers

`PdfCorpusBuilder.vue` separately watches build, queue, record, and local review state. A Back/Forward navigation that changes more than one field can trigger overlapping reads and visible intermediate states.

Route application should be centralized and transactional for:

`{ build, workspace, queue, record }`

The controller should determine the minimum required operation and suppress stale responses.

### 7. Build switching commits partial UI state before data is ready

Selecting a historical build immediately updates some identifiers and clears review state before the authoritative build and requested review page are loaded. This can briefly mix old and new context or flash an empty workspace.

A build switch should expose a lightweight pending state and commit the new context atomically once its authoritative build snapshot is available.

### 8. Sticky page chrome is layered and inconsistent

The app top bar, Builder/Explorer mode tabs, Corpus Builder workspace header, and inner setup/review surfaces can all participate in sticky positioning. The Corpus Builder header also changes sticky behavior by workspace.

Page-level navigation should use one stable sticky contextual header with consistent offsets.

### 9. Some workflow labels do not describe their actual effect

`Start new build` preserves the selected source and persisted setup state. This is useful, but the label implies a clean slate.

The UI should distinguish:

- New build from this source
- Choose another source

### 10. Publication has duplicate final actions and redundant reconciliation

Published state exposes more than one Download JSONL action. Publication also performs several authoritative list/build refreshes around reconciliation and publication.

Publication correctness must remain authoritative, but redundant UI actions and unnecessary repeated list reads should be reduced.

### 11. Lazy route modules block the page transition itself

Top-level routes currently use Vue Router lazy components such as `component: () => import("../views/ResearchView.vue")`. Vue Router resolves those component promises before committing the navigation. A cold chunk therefore leaves the previous page active while JavaScript is downloaded and evaluated, which makes ordinary navigation feel frozen.

The route transition and the destination content load should be separate operations. Navigation should commit immediately to a lightweight synchronous route shell; that shell should progressively load the page module and then let the page progressively hydrate its own data. A slow route chunk or API read must never keep the user on the previous page.

## Deployment asset-coherence issue discovered during implementation

A separate navigation failure was reproduced from production-container logs: a long-lived browser tab can keep an older Vite entry bundle after the `web` container is rebuilt. When that old bundle later lazy-loads a route such as Providers, it requests the old hashed route chunk, which the replacement image no longer contains, producing a 404 such as:

`GET /assets/ProvidersView-<old-hash>.js → 404`

This is not route-state jank; it is a deployment/cache-coherence failure that makes navigation appear broken.

The fix is part of this work and has two layers:

1. nginx serves `index.html` with no-cache/no-store semantics while continuing to serve content-hashed `/assets/` files as long-lived immutable resources.
2. the frontend installs one-shot stale-chunk recovery for Vite preload/dynamic-import failures. A long-lived tab reloads once to obtain the current HTML/chunk graph, with a sessionStorage guard preventing reload loops.

Acceptance criteria:

- a newly loaded page cannot reuse an old HTML shell after a web-image replacement;
- an already-open tab self-recovers once when a lazy route references a removed chunk;
- ordinary API/application errors never trigger a reload;
- repeated stale-chunk failures within the recovery window do not create a reload loop.

## Implementation phases

## Phase 1 — Router-first global navigation

### Scope

Files:

- `web/src/App.vue`
- `web/src/domain/appNavigation.ts`
- relevant shell/navigation tests

### Work

1. Route canonical sidebar destinations directly through Vue Router.
2. Keep the legacy runtime bridge only for destinations that still require legacy rendering/state behavior.
3. Prefer route objects / named routes where practical.
4. Preserve capability checks, recent/favorite behavior, mobile navigation, command palette behavior, and navigation feedback.
5. Ensure the compatibility runtime follows the settled router route rather than initiating canonical navigation.

### Acceptance criteria

- A sidebar click to a canonical Vue route performs one router navigation.
- Native browser link/navigation semantics are preserved where practical.
- Active sidebar state still follows the canonical route.
- Back/Forward remains correct.
- Legacy-only views continue to function.

## Phase 2 — Corpus Builder history semantics

### Scope

Files:

- `web/src/features/corpus-builder/composables/useCorpusWorkspaceNavigation.ts`
- `web/src/components/PdfCorpusBuilder.vue`
- workspace navigation tests

### Work

1. Add an explicit navigation mode to `switchWorkspace()`: `push` for deliberate navigation, `replace` for automatic workflow transitions.
2. Use `replace` after:
   - build start;
   - automatic return to publication readiness;
   - automatic workflow progression;
   - other application-driven phase changes.

3. Keep `push` for user-clicked phase navigation.
4. Add browser-history regression tests.

### Acceptance criteria

- Browser Back visits deliberate user navigation, not automatic lifecycle hops.
- Deep links to all four workspaces still restore correctly.
- No publication/review state is lost.

## Phase 3 — Stable four-stage Corpus Builder navigation

### Scope

Files:

- `web/src/components/corpus-builder/CorpusBuilderWorkspaceHeader.vue`
- `web/src/features/corpus-builder/domain/workspace.ts`
- Storybook and frontend tests
- i18n resources as required

### Work

1. Render Setup, Build, Review, Publish as four stable phase controls.
2. Remove the Build/Review grouped phase and contextual sub-navigation.
3. Retain complete/current/available/unavailable semantics.
4. Keep unavailable steps visible but disabled with appropriate accessible state.
5. Ensure narrow layouts remain usable.

### Acceptance criteria

- The workflow has the same visible shape in every phase.
- Every workspace has a stable location in the navigation.
- WCAG keyboard/focus behavior remains intact.

## Phase 4 — Builder/Explorer route-state boundaries

### Scope

Files:

- `web/src/views/PdfWorkspaceView.vue`
- `web/src/components/PdfCorpusBuilder.vue`
- route/query helper module
- frontend tests

### Work

1. Define explicit query whitelists for Corpus Builder and Source Explorer.
2. Preserve only intentionally shared source context across the two routes.
3. Stop copying arbitrary route query state between them.
4. Remove obsolete `mode=builder` writes from canonical Corpus Builder navigation.
5. Preserve legacy `/pdf?mode=` redirects for compatibility.

### Acceptance criteria

- Builder-only query state does not appear on Source Explorer URLs.
- Explorer-only query state does not appear on Corpus Builder URLs.
- Existing deep links continue to resolve.
- No sensitive/transient state is added to URLs.

## Phase 5 — Preserve Builder/Explorer workspace state

### Scope

Files:

- `web/src/views/PdfWorkspaceView.vue`
- `web/src/components/PdfCorpusBuilder.vue`
- `web/src/components/PdfExplorerSurface.vue`
- lifecycle tests

### Work

1. Preserve sibling workspace component state across Builder/Explorer switches.
2. Suspend expensive polling/followers while a surface is inactive.
3. Reconcile only what is necessary when reactivated.
4. Preserve:
   - selected build and record;
   - review queue/filter state;
   - expanded setup section;
   - pane sizes;
   - scroll position where practical.

5. Ensure background work that should continue independently of the page remains server-owned.

### Acceptance criteria

- Switching to Explorer and back does not perform a cold Corpus Builder initialization.
- Realtime subscriptions do not duplicate while a surface is inactive.
- Returning to Builder restores the previous interaction context.

## Phase 6 — Transactional Corpus Builder route controller

### Scope

Files:

- `web/src/components/PdfCorpusBuilder.vue`
- new composable under `web/src/features/corpus-builder/composables/`
- route-state/domain tests

### Work

1. Replace independent route watchers for build/queue/record with one route-state application path.
2. Parse the full route snapshot before doing work.
3. Compute the minimum transition:
   - build changed → load build once, then requested queue/record;
   - queue changed → refresh queue once;
   - record changed → load/select record only;
   - workspace-only change → no unnecessary record reload.

4. Add request-generation protection so stale async results cannot overwrite newer navigation.
5. Keep local-to-route synchronization centralized and idempotent.

### Acceptance criteria

- One Back/Forward action produces one coherent route-state transition.
- No duplicate record page reads caused by the same route change.
- Slow responses from superseded route states are ignored.
- Route synchronization does not create loops.

## Phase 7 — Atomic build switching

### Scope

Files:

- `web/src/components/PdfCorpusBuilder.vue`
- `web/src/components/CorpusBuildHistoryMenu.vue`
- relevant tests

### Work

1. Add explicit build-switch pending state.
2. Keep the current content stable while the next build is fetched, or show a bounded opening state.
3. Commit build/source/review context together after the authoritative build is available.
4. Close the build history popover on selection.
5. Avoid unnecessary full review refreshes when the requested build has no review topology.

### Acceptance criteria

- No frame renders a new build ID with old build content.
- Build history closes after selection.
- Build switching cannot be overwritten by a slower prior selection.

## Phase 8 — Sticky chrome and workflow labeling

### Scope

Files:

- `web/src/views/PdfWorkspaceView.vue`
- `web/src/components/corpus-builder/CorpusBuilderWorkspaceHeader.vue`
- Corpus Builder styles and tests

### Work

1. Reduce overlapping sticky navigation layers.
2. Use shared shell offsets for all remaining sticky surfaces.
3. Keep header behavior stable across Build and Review.
4. Rename/restructure the new-build action so its effect is explicit.
5. Avoid duplicate primary actions such as Download JSONL after publication.

### Acceptance criteria

- No overlapping sticky surfaces at supported widths.
- Entering Review does not materially reflow page-level navigation.
- New-build actions accurately describe whether the source is retained.

## Phase 9 — Publication transition cleanup

### Scope

Files:

- `web/src/features/corpus-builder/composables/useCorpusPublication.ts`
- `web/src/components/corpus-builder/CorpusPublishWorkspace.vue`
- publication tests

### Work

1. Retain the authoritative reconcile-before-publish invariant.
2. Apply returned authoritative state locally when safe.
3. Reduce redundant list/build refreshes while keeping one final reconciliation.
4. Keep blocker repair links exact and preserve `fixContext`.
5. Present one primary download action after publication.

### Acceptance criteria

- Publication never races outstanding review writes.
- Publish blockers remain authoritative and directly actionable.
- Published state is visible without redundant full refresh churn.

## Phase 10 — Immediate navigation with progressive route loading

### Scope

Files:

- `web/src/router/index.ts`
- new progressive-route helper under `web/src/router/`
- shared route loading/error UI under `web/src/components/shell/`
- route/navigation tests
- individual workspaces only where they still withhold their visible shell until data hydration completes

### Work

1. Keep each top-level Vue Router route component synchronous so the route, breadcrumb, active navigation item and page shell commit without waiting for a code-split chunk.
2. Move the existing dynamic `import()` calls inside a shared progressive route wrapper.
3. Render a destination-owned loading skeleton immediately while the page module downloads.
4. Preserve one-shot stale-deployment recovery for missing hashed chunks.
5. Show an inline recovery state for ordinary transient module-load failures after the route has already committed. Because browsers can cache a failed ES-module fetch for the lifetime of the document, explicit Retry reloads the already-committed destination instead of pretending that repeating the same `import()` is a reliable retry.
6. Keep page-specific API/data hydration inside each destination. Audit pages that still hide their entire visible shell behind an initial `await` or all-or-nothing `Promise.all`, and convert those to header/controls-first progressive loading.
7. Prefer intent preloading for likely destinations later, but do not make prefetch a correctness requirement for fast navigation.

### Acceptance criteria

- Clicking a top-level destination changes the canonical route and shell before its JavaScript chunk resolves.
- The committed destination shell receives a browser paint before a cached/heavy page module is allowed to mount, so synchronous setup work cannot visually hold the previous page in place.
- The previous page is not retained merely because the destination chunk or API is slow.
- A cold destination shows an immediate loading skeleton owned by the destination route.
- Once the module is loaded, its page can continue loading data progressively without blocking route state.
- A transient chunk failure is recoverable from the committed destination; explicit Retry reloads that destination rather than returning to the previous page.
- A stale-deployment chunk failure still self-recovers through the existing guarded reload path.
- Back/Forward has the same immediate-commit behavior.

## Testing strategy

Add or update tests for:

- router-first sidebar navigation;
- browser history after automatic Corpus Builder transitions;
- four stable workspace phases;
- Builder/Explorer query-state isolation;
- cached Builder/Explorer activation/deactivation;
- transactional route application for simultaneous build/queue/record changes;
- stale response suppression during rapid Back/Forward or build switching;
- build history pending/close behavior;
- sticky header accessibility and focus visibility;
- publication refresh counts and authoritative final state.
- production-bundle navigation with a destination route chunk deliberately held or failed, asserting that URL/breadcrumb/loading shell commit before release and recovery occurs in place.

A focused E2E workflow should cover:

1. Enter Corpus Builder from the sidebar.
2. Configure a source and start a build.
3. Navigate Build → Review → Publish.
4. Enter a blocker remediation flow and return to Publish.
5. Switch Builder → Source Explorer → Builder.
6. Open another historical build.
7. Use browser Back/Forward through the sequence.
8. Confirm no unexpected remount, query leakage, duplicate read burst, or lost review context.

## Performance/UX budgets

The implementation should target:

- no full Corpus Builder cold initialization when toggling Builder/Explorer after first mount;
- at most one authoritative build read for one build-route transition;
- at most one review-page read for one queue-route transition;
- no record-page read for workspace-only navigation;
- no duplicate realtime subscription after sibling workspace reactivation;
- no automatic lifecycle transition added to browser history unless it represents a deliberate user navigation;
- no visible old/new build context mixture during build switching.
- top-level route state, breadcrumbs and active navigation commit independently of destination chunk resolution;
- route-module loading displays destination-owned progressive feedback instead of retaining the previous page;
- cached page modules cannot skip the destination-shell paint and monopolize the navigation frame with synchronous setup;
- destination API hydration is not a prerequisite for rendering that destination's page shell.

## Non-goals

This work does not change:

- cELF semantics;
- evidence/provenance representation;
- metadata schema meaning;
- build enrichment algorithms;
- review authority rules;
- publication validation rules;
- server-side job ownership.

## Delivery sequence

The work should be committed in small reviewable slices:

1. documentation + route/history semantics;
2. stable four-phase header;
3. global router-first navigation;
4. Builder/Explorer query isolation;
5. transactional Corpus Builder route state;
6. preserved sibling workspace state;
7. atomic build switching and sticky/publish polish;
8. final regression/E2E coverage and documentation update.
9. immediate route commit + progressive page-module loading;
10. workspace-by-workspace audit for any remaining all-or-nothing initial hydration.

Each slice should leave tests green and avoid mixing unrelated UI refactors with navigation behavior.
