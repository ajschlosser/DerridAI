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

# Frontend State Ownership and Interaction Performance Migration

This is the working contract for removing application-wide work from local UI interactions. It complements
[ARCHITECTURE.md](ARCHITECTURE.md) and the legacy-runtime retirement work rather than replacing either document.

The immediate defect is interaction latency: typing, navigation, and other local UI operations can synchronously trigger
workspace-wide persistence, shell recomputation, corpus scans, URL serialization, or imperative DOM work. The architectural
defect underneath it is ownership: native Vue pages still share a compatibility-era flattened mutable state object and
global refresh/persistence functions.

The migration target is domain ownership. A component owns ephemeral presentation state; a composed page or feature
controller owns its domain state and commands; narrow application services own persistence, transport, and cross-domain
projections. The application shell consumes small derived projections and must never inspect or recompute an entire feature
domain to render chrome.

## Non-negotiable invariants

1. A local input event must not trigger a whole-application refresh, whole-workspace serialization, corpus-wide scan, or
   synchronous route rewrite.
2. Shell work must be O(1) with respect to loaded corpus size. Corpus-derived counts used by chrome are maintained by their
   owning domain and exposed as small projections.
3. `App.vue` owns authentication/session, router composition, application chrome, notifications, and globally visible
   operation summaries. It does not own Research, Records, Compare, PDF, metadata-review, or LLM-workflow state.
4. Feature pages interact with typed feature stores/controllers. Native Vue views must not import a writable
   `sharedUrlState.state` god object.
5. Pinia stores are ownership boundaries, not `toRefs()` facades over mutable compatibility singletons. Mutations,
   invariants, selectors, and persistence triggers belong to the owning store/controller.
6. Persistence is domain-scoped. A Research draft save serializes Research draft state, not Search/Records/Compare/jobs/etc.
7. URL state is domain-scoped and asynchronous with respect to typing. Shareable URL updates may be debounced or committed
   on meaningful state transitions; they are never required before the current input can paint.
8. Domain/read-model selectors are side-effect free. Reading a Records snapshot must not initiate presence refreshes,
   persistence, navigation, or network work.
9. Background jobs publish job-domain state. Job code must not directly rewrite unrelated page DOM or force a shell/page
   repaint.
10. Compatibility bridges may remain temporarily, but new native Vue code must not add dependencies on `shell()`,
    `renderView()`, global `persistPrefs()`, or writable `sharedUrlState.state`.
11. Every behavior change receives regression coverage. Performance claims require measured browser evidence rather than
    synthetic loading-state tests alone.
12. Preserve all existing provenance, authorization, cancellation, stale-response, i18n, and WCAG 2.2 AA contracts.

## Current high-cost coupling to remove

The initial census found these concrete paths:

- Research prompt/instructions -> `updateResearchConfig()` -> global `persistPrefs()` -> shell refresh.
- `shell.sync()` -> `getShellSnapshot()` -> `pendingUpsertRows()` -> potentially corpus-wide filtering/fingerprinting.
- Native route settlement -> `repaintAfterLocationChange()` -> shell refresh -> `renderView()` -> second shell refresh.
- Search query keystroke -> global state mutation -> global persistence -> synchronous URL JSON/LZW encoding and route replace.
- Records query -> full active-file map/filter/sort/flagged/column projection after an 80 ms debounce.
- Compare editor keystroke -> parse/compare derivation plus global workspace persistence.
- `workspacePrefs()` -> recursive clone/serialization of unrelated domains behind one global debounce timer.
- Corpus-wide `version` counters -> broad recomputation by every consumer watching the same generation.
- Realtime job reconciliation -> synchronous watchers, imperative DOM updates, upsert receipt work, and global persistence.
- Semantic map host -> route-wide watch -> source rebuilding; administrator source enumeration currently flattens all records
  before enforcing its 400-record cap.
- Root `App.vue` -> static ownership/mounting of many feature dialogs and workflows, weakening feature boundaries and
  route-level code splitting.

## Target ownership model

~~~text
App
|- auth/session
|- router
|- application chrome
|  |- navigation projection
|  |- layout projection
|  |- notifications
|  `- active-operation summary
`- RouterView
   `- Feature page
      |- feature store/controller
      |- feature persistence adapter
      |- feature URL-state adapter
      |- feature query/API layer
      `- feature components
         `- ephemeral component state
~~~

Cross-domain data is exposed as explicit read-only projections or commands. A feature never reaches into another feature's
mutable state to make its own UI current.

## Two-agent division

The work is intentionally split so two agents can proceed concurrently with minimal file overlap.

### Agent A - shell, routing, global projections, and background UI

Primary ownership:

- `web/src/App.vue`
- `web/src/components/shell/**`
- `web/src/router/**`
- `web/src/stores/shell.ts`
- `web/src/domain/shellSnapshot.ts`
- `web/src/domain/sharedNavigation.ts`
- shell/navigation-focused tests
- later: operations/global semantic-map integration where the work is truly application chrome

Agent A must not edit Research/Search/Compare feature state unless a narrow interface is required. When a feature needs to
publish chrome data, Agent A defines the projection contract and Agent B implements the feature-side producer.

Work order:

- [x] A1. Make settled native navigation perform exactly one shell refresh and one preference scheduling action.
- [x] A2. Add immediate sidebar navigation intent state (`pendingNavId` or equivalent) that is visible before route work,
      keyboard accessible, and cleared on route settle/failure.
- [x] A3. Decompose the shell snapshot into stable navigation/layout/context and independent counters/status projections.
- [x] A4. Remove `pendingUpsertRows()` and every corpus-size-dependent selector from shell render paths.
- [x] A5. Replace shell polling/recomputation of corpus/job counts with domain-maintained read-only summary projections.
- [x] A6. Remove direct DOM updates for the global operations button; render the badge from the jobs/operations projection.
- [x] A7. Make semantic-map source refresh depend on semantic-map inputs rather than every `route.fullPath` change, and avoid
      corpus-wide `flatMap` allocation when enforcing bounded source limits.
- [x] A8. Reduce root `App.vue` feature ownership by moving feature-only dialog/workflow hosts under their owning routes or
      lazy feature hosts.

### Agent B - feature state ownership, input paths, persistence, and URL state

Primary ownership:

- `web/src/views/ResearchView.vue`
- `web/src/components/research/**`
- `web/src/domain/researchWorkspace.ts`
- Research-focused stores/services/tests
- `web/src/domain/prefsPersistence.ts`
- `web/src/domain/sharedWorkspaceStorage.ts`
- Search/Records/Compare state and persistence paths
- feature-specific persistence and URL-state adapters

Agent B must not redesign shell rendering or router chrome. Where feature state must be shown globally, publish a narrow
projection for Agent A.

Work order:

- [x] B1. Remove Research configuration/draft mutations from shell invalidation.
- [x] B2. Keep Research prompt/instructions component/page-owned on the input path; stop global workspace serialization while
      typing. Preserve draft restoration through a Research-specific repository if draft persistence remains desired.
- [x] B3. Split global preference persistence into domain repositories/timers, starting with Research, layout, Search,
      Records, and Compare. Retain migration reads from the existing `prefs` object until all domains move.
- [x] B4. Stop Search keystrokes from synchronously compressing/replacing URL state. Make query rendering immediate and URL
      persistence delayed/meaningful.
- [x] B5. Make Records projections incremental/cached where feasible and side-effect free. Move presence refresh to an
      explicit async effect keyed to visible rows.
- [x] B6. Stop Compare editor keystrokes from serializing unrelated workspace state; avoid duplicate compare derivations per
      render.
- [ ] B7. Replace broad corpus `version` consumers with narrower structure/content/review/evidence invalidation or normalized
      reactive state.
- [x] B8. Retire native-view imports of writable `sharedUrlState.state`, replacing them with feature stores/controllers.

### Shared integration points

Only one agent edits a shared integration file at a time. Coordinate these explicitly:

- `web/src/state/workspaceState.ts`: Agent B owns the state-model migration; Agent A may request read-only summary types.
- `web/src/domain/sharedWorkspaceStorage.ts`: Agent B owns persistence semantics; Agent A consumes `refreshShell()` only until
  the shell no longer needs the bridge.
- `web/src/domain/sharedUrlState.ts` / `urlStateCodec.ts`: Agent B owns feature URL-state extraction; Agent A owns only router
  integration.
- `docs/ARCHITECTURE.md`: update after a tranche changes the implemented architecture, not before.
- `docs/USER_GUIDE.md`: update only when visible interaction behavior changes.

## Delivery tranches

### Tranche 1 - remove proven interaction-path global work

Acceptance:

- Research typing no longer invokes shell refresh.
- Native route settlement invokes one shell refresh, not two.
- Sidebar gets immediate pending feedback.
- Instrumentation records input-to-paint and click-to-first-paint around Research/sidebar paths.
- Regression tests pin the absence of global invalidation.

Implementation status on `task/frontend-state-ownership-performance`: Agent A's A1-A8 tranche is complete. Shell navigation,
route/file context, and application-status projections now invalidate independently; corpus/store aggregates are cached
behind domain invalidation and cheap collection-identity checks, while active-store, health, and evidence primitives stay
live. Job reconciliation no longer rewrites shell DOM. Feature dialogs and the touch-up workflow are now activated through
small feature-owned request refs and lazy hosts instead of being statically owned by `App.vue`. B1, B2, B4, B5, and B6 are complete. Records snapshot reads are side-effect free, visible-row presence refresh is an
explicit async effect, and corpus-derived row metadata is cached by corpus generation with prefix-query narrowing for
ordinary typing. Research configuration now has its own domain preference record in addition to its composer-draft record. Search,
Records/list, layout, review/evidence, vector, jobs, Settings, Works, and record-view preferences use independent records
and timers; Compare keeps its bounded feature draft record. Legacy `workspace` reads remain as a migration fallback,
but these native feature paths no longer default to whole-workspace serialization. Bounded User Timing
measures record Research prompt/instruction input-to-next-frame latency and sidebar navigation intent-to-next-frame latency.
Repository validation has not yet been run in this environment.

This tranche should be small enough to review independently and should land before larger store/persistence work.

### Tranche 2 - O(1) shell

Acceptance:

- `getShellSnapshot()` no longer calls `allRows()`, `needsReviewItems()`, `pendingUpsertRows()`, or any equivalent
  corpus-size-dependent selector.
- Active jobs, loaded corpus totals, review counts, pending-upsert counts, and selected-evidence counts are maintained by
  their owning domains and consumed as constant-time projections.
- Changing a Research/Search/Compare draft does not replace shell navigation arrays or recompute unrelated shell state.

### Tranche 3 - domain persistence

Acceptance:

- The monolithic `workspacePrefs()` write is no longer the default persistence path for native Vue features.
- Research, Search, Records, Compare, layout, and job bookkeeping have independent dirty state/timers/repositories.
- Backward-compatible restore reads migrate legacy `prefs` values without data loss.
- A persistence write is bounded by the size of the owning domain, not the entire workspace.

### Tranche 4 - feature-owned URL state and selectors

Acceptance:

- Search/Records typing paints before URL-state work.
- URL compression is not executed per keypress.
- Records read-model construction is pure; presence/network work is explicit and cancellable.
- Feature selectors invalidate only for dependencies they actually read.

### Tranche 5 - remove the compatibility god object from native Vue

Acceptance:

- Native Vue views do not import writable `sharedUrlState.state`.
- Feature Pinia stores/controllers own actions and invariants rather than exposing only refs.
- Broad `version` counters are retired or limited to compatibility-only consumers.
- Cross-feature interactions use explicit commands/projections.

### Tranche 6 - background/global UI cleanup

Acceptance:

- Jobs/realtime code does not query or mutate unrelated page DOM.
- Operations chrome is declaratively rendered from a bounded jobs projection.
- Semantic-map refreshes are dependency-scoped and bounded without full-corpus intermediate allocations.
- Feature dialogs/workflows are lazy and route/domain-owned where practical.

## Performance instrumentation and budgets

Add User Timing marks/measures or an equivalent small instrumentation helper around:

- Research input event -> next frame boundary (`derridai.research.prompt.input_to_frame` and
  `derridai.research.instructions.input_to_frame`)
- sidebar pointer/keyboard activation -> pending visual frame
  (`derridai.navigation.intent_to_frame`)
- pending visual paint -> route commit
- route commit -> destination shell paint
- `getShellSnapshot()`
- pending-upsert projection computation
- preference snapshot construction/serialization
- Records snapshot construction

Test with at least small, 10k-record, and large-corpus fixtures plus an active background-job case. Synthetic unit tests verify
that expensive functions are not called from forbidden paths; browser measurements establish latency.

Initial budgets:

- sidebar intent feedback: < 50 ms p95
- ordinary Research typing: < 50 ms p95 input-to-paint, with no app-attributable long task
- warm navigation destination shell/skeleton: about 100 ms p95 where browser/hardware permits
- shell projection work: effectively constant as corpus size grows

These are engineering budgets, not claims about the current application. Record measured baselines before claiming an
improvement.

## Testing strategy

Each tranche should include focused Vitest tests first, then the dependency-selected preflight surface. Browser tests should
cover interaction timing/feedback semantics without brittle wall-clock assertions: assert the pending state paints before a
deferred route/page operation resolves, and use explicit instrumentation for benchmark reporting.

Do not use additional debouncing, skeletons, or prefetching as substitutes for removing synchronous global work. Those can
improve presentation after ownership/invalidation is correct, but they do not fix main-thread contention.

## Completion criteria

The migration is complete when a developer can answer all of the following from code structure alone:

- Which domain owns this state?
- Which component/store is allowed to mutate it?
- What exact persistence record does it write?
- What exact URL state does it own, if any?
- Which narrow projections can other domains read?
- What invalidates each projection?
- Can this operation scale with corpus size?
- Can this input paint before persistence, navigation, network, or corpus computation?

If an interaction still requires "refresh the shell" or "persist the workspace" without naming the affected domain, the
migration is not complete.
