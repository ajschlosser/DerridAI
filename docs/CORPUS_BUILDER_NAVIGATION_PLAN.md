# Corpus Builder Navigation and Workflow Smoothness Plan

## Purpose

This plan addresses the interaction friction observed in DerridAI's global navigation and especially in Corpus Builder's Setup → Build → Review → Publish workflow. The goal is to make navigation feel immediate, predictable, and browser-native without changing scholarly semantics, provenance guarantees, build lifecycle rules, or publication invariants.

The main implementation principle is to reduce the number of independent state authorities involved in one navigation action. Vue Router should own canonical application navigation. Corpus Builder should treat its route-backed state as one coherent snapshot rather than several loosely synchronized query parameters.

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

Each slice should leave tests green and avoid mixing unrelated UI refactors with navigation behavior.
