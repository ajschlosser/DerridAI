# Works Workspace UX Redesign — Implementation Handoff

**Repository:** `ajschlosser/DerridAI`  
**Prepared:** 2026-09-30  
**Authoritative default branch at handoff:** `master` @ `790d72c7b99e45ada8822b178ef4cf6c0b09ee94`

## Objective

Redesign and refactor DerridAI’s Works page so it behaves like a coherent corpus-library workspace rather than a collection of loosely related corpus-management commands.

The target experience should be:

> Works is the corpus library. Users browse, understand, inspect, and act on works. Infrastructure, enrichment, publication, and synchronization remain available, but they are contextual and progressively disclosed rather than competing with the library itself.

This is primarily an information-architecture, workflow, and interaction redesign. Do not treat it as a styling-only task.

Before making changes, update from the current remote `master` and re-check any open PRs touching Works, Search, Records, shared UI primitives, routing, semantic maps, Work insights, or corpus-management behavior.

## Current implementation to understand first

The principal files are:

- `web/src/views/WorksView.vue`
- `web/src/components/works/WorksWorkspaceHeader.vue`
- `web/src/components/works/WorksLibraryCard.vue`
- `web/src/components/works/WorksOverviewCard.vue`
- `web/src/components/works/WorksInsightCard.vue`
- `web/src/components/works/CreateSiteDialog.vue`
- `web/src/composables/useWorksWorkspace.ts`
- `web/src/domain/worksWorkspace.ts`
- `web/src/types/works.ts`
- `web/src/state/workspaceState.ts`
- `web/src/domain/workspacePersistence.ts`
- `web/src/domain/navigation.ts`

Relevant shared UI includes:

- `web/src/components/ui/UiPageHeader.vue`
- `web/src/components/ui/UiMenu.vue`
- `web/src/components/ui/UiDialog.vue`
- `web/src/components/ui/UiStatusBadge.vue`
- `web/src/components/ui/UiTooltip.vue`
- `web/src/components/ui/UiButton.vue`

Use Records and Search as the strongest nearby examples of current workspace conventions:

- `web/src/views/RecordsView.vue`
- `web/src/components/records/RecordsWorkspaceHeader.vue`
- `web/src/views/SearchView.vue`
- `web/src/components/search/SearchWorkspaceHeader.vue`

Also read before implementation:

- `SPECIFICATION.md`
- `docs/requirements/GLOBAL_REQUIREMENTS.md`
- `docs/requirements/RECORDS_WORKS_AND_CORPORA.md`
- `docs/requirements/UX_ACCESSIBILITY_AND_I18N.md`
- `docs/ARCHITECTURE.md`
- `docs/USER_GUIDE.md`

The relevant product requirements include task-oriented navigation, canonical route-backed workspace state, consistent dense-data interaction conventions, progressive disclosure, understandable consequences for consequential actions, WCAG 2.2 AA, and preserving the distinction between authoritative corpus state, browser workspace state, and derived vector/index state.

## Current UX problems this work must solve

The Works page has a strong feature set but lacks a sufficiently coherent interaction model.

The main issues are:

- Admin Works uses a bespoke `WorksWorkspaceHeader`, while Records and Search use `UiPageHeader`; researcher Works switches back to the shared header, so Works is inconsistent both with neighboring workspaces and with itself.
- The header exposes unrelated operations at the same visual level: JSONL loading, JSONL separation, metadata enrichment, publication/site export, synchronization, database selection, and corpus metrics.
- The page forces users to reason about browser-loaded corpus state and the selected corpus/vector database simultaneously without enough structural separation.
- `Sync` is visually more prominent than review-oriented scholarly work on each card.
- Clicking a work inserts a large overview above the library, changing page geometry and forcing `WorksView.vue` to preserve absolute `window.scrollY`; this does not preserve the user’s spatial relationship to the selected card.
- The work-card surface is mouse-clickable through an `<article>` handler but is not itself a native keyboard-operable control.
- Work insights are useful but currently compete with browsing and detail inspection instead of behaving as subordinate analysis.
- The library offers title search but lacks sufficiently strong sorting/filtering/view-density support for large corpora.
- Admin and researcher Works have substantially different information architectures.

The redesign should fix the workflow and information architecture first; styling should support that structure rather than merely decorate the existing complexity.

## Target information architecture

The page should become four visually and conceptually distinct layers:

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Corpus                                                              │
│ Works                                              [Add files] [⋯]   │
│ Browse and manage works in the current corpus workspace.             │
└──────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────┬──────────────────────────────────────┐
│ Loaded workspace              │ Corpus database                      │
│ 4 source files · 3,218 records│ derrida_primary · 3,102 records      │
│ Browser-loaded corpus         │ Derived searchable/indexed state     │
│                               │ [Change database] [Sync changes]      │
└───────────────────────────────┴──────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ Search works…   [Filters]   Sort: Title A–Z   [Cards | Compact]      │
│ 64 works · 7 need review                                            │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┬────────────────────────────────┐
│ Work library                        │ Selected work                  │
│                                     │                                │
│ [work]                              │ cover                          │
│ [work]                              │ title / author / year          │
│ [work]                              │ review state / DB state        │
│ [work]                              │ records / metadata / insights  │
│                                     │ actions                        │
└─────────────────────────────────────┴────────────────────────────────┘
```

On narrow screens, do not insert a giant selected-work overview above the library and move the entire page downward. Use an accessible modal/detail treatment based on the existing `UiDialog` foundation or another already-established responsive inspector pattern. Do not invent a new generic drawer primitive unless there is a clear reuse case beyond Works.

# Implementation plan

## Phase 1 — Baseline, conflicts, and regression protection

Before editing UI:

1. Pull the latest `master`.
2. Inspect open PRs for overlapping changes.
3. Run the existing Works unit/frontend/E2E tests using the repository’s documented commands.
4. Capture baseline behavior for admin Works with corpus loaded, admin Works with no corpus loaded, search/filter state, selected work, actions menu, researcher Works, dark theme, narrow viewport, and French.
5. Preserve existing domain behavior unless explicitly changed below.

Do not rewrite enrichment, publication, semantic-map, annotation, synchronization, or corpus-authority behavior merely as part of this UX work.

## Phase 2 — Normalize the page header

`WorksWorkspaceHeader.vue` should stop being a bespoke hero and become a thin Works-specific composition around `UiPageHeader`.

The admin and researcher variants should use the same visual page-header grammar.

Target content:

- kicker: Corpus
- title: Works
- concise description focused on the task, not implementation details
- no giant bespoke Works heading
- no Works-only gradient hero card
- no metric-card dashboard embedded in the page title area

For admin mode, expose at most one direct high-frequency action plus one menu in the page header.

Recommended hierarchy:

- direct action: **Add files**
- secondary `UiMenu`: **More actions**

Move these lower-frequency operations into the menu:

- Separate works into JSONL
- Populate metadata for all works
- Create research site

Do not put **Sync all works** in this menu. Synchronization belongs with the corpus-database context because it changes derived/indexed state, not the browser-loaded corpus library itself.

Use `UiMenu`, not a new custom actions-menu implementation.

Keep disabled reasons using the established `reason` capability on `UiMenuItem` or existing tooltip patterns. Users must still be able to understand why an unavailable operation cannot run.

## Phase 3 — Introduce an explicit corpus-context strip

Create a focused Works component, for example:

`web/src/components/works/WorksCorpusContext.vue`

Its purpose is to make the two data domains impossible to confuse.

### Left: Loaded workspace

Show:

- source-file count;
- total loaded Records;
- a short explanation that this is the browser-loaded corpus/workspace;
- no vector-database terminology.

Example copy concept:

> Loaded workspace  
> 4 source files · 3,218 records  
> These are the corpus files currently open in this browser workspace.

### Right: Corpus database

Show:

- selected corpus/vector database name;
- its record count;
- explicit language that it is the searchable/indexed derived database;
- database selector or change control;
- synchronization state/action.

Rename the current user-facing **Sync target** concept. It is too implementation-oriented.

Use language such as **Corpus database**, **Indexed corpus database**, or **Search database**, choosing terminology consistent with the rest of DerridAI after checking current copy.

Make it explicit that changing the selected database does not change the currently loaded JSONL workspace.

This component should own the database selector currently embedded in `WorksWorkspaceHeader`.

**Sync all works** should become a contextual action here, preferably labeled around its effect rather than its implementation if existing copy permits, e.g. **Sync workspace to database**.

If synchronization is disabled, preserve the explanatory reason.

## Phase 4 — Fix Works snapshot semantics before building more UI on top

`web/src/domain/worksWorkspace.ts` currently mixes total and filtered semantics in ways that will make a richer toolbar fragile.

Clean up the typed Works snapshot contract.

At minimum distinguish:

- total works;
- visible/filtered works;
- total records;
- source-file count;
- selected work;
- search/filter/sort state;
- active database context.

Do not derive the page-wide source-file count from `snapshot.works`, because `snapshot.works` is filtered by the title query. A page-level corpus metric should not change merely because someone searches for one work.

Also normalize admin/researcher meanings. `totalWorks` should mean the same thing in both modes. Do not let it mean “filtered result count” for one role and “entire corpus count” for another.

Prefer explicit fields such as:

```ts
totalWorks
visibleWorks
totalRecords
sourceFileCount
```

rather than overloading one number.

If useful for the redesigned library, also expose a total unresolved/review count derived from the constituent Works, but do not invent new authority semantics. This is aggregation of existing record review state only.

Strengthen `web/src/types/works.ts` while doing this. Avoid introducing additional `any`/`Loose` usage.

Do not move scholarly or corpus authority into the UI layer.

## Phase 5 — Add a real library toolbar

Extract the library controls from `WorksView.vue` into a dedicated component, for example:

`WorksLibraryToolbar.vue`

The toolbar should contain:

- search;
- filter access;
- sort;
- view density/mode;
- result summary.

Search should remain route-backed through the existing Works workspace state.

Add useful sorting choices:

- Title A–Z
- Title Z–A
- Record count, highest first
- Needs review, highest first
- Year, where sufficiently defined

Use the real data already available. Do not create fake fields solely to support sorting.

Add filters through progressive disclosure rather than a row of permanent controls. Useful candidates include:

- Needs review
- database/sync status
- author
- publication year

For database status, first inspect the actual `workDbStatus()` status kinds and use those stable values. Do not hard-code guessed statuses.

Add a simple **Cards / Compact** presentation toggle if it can be implemented cleanly. The existing card view is appropriate for small libraries; a compact mode is important for large corpora.

Keep all meaningful workspace state in the Works URL where safe and appropriate.

The current route already persists:

- `q` for Works search;
- `w` for selected work.

Extend the existing route/state infrastructure rather than introducing component-local URL manipulation.

Any new safe workspace state such as sort/filter/view mode should:

- survive reload;
- work with back/forward;
- work in copied URLs;
- not encode sensitive/transient data.

Update `workspaceState.ts`, `workspacePersistence.ts`, `navigation.ts`, and associated tests as required.

## Phase 6 — Redesign the work-card hierarchy

`WorksLibraryCard.vue` should become primarily a library object, not a mini administration console.

The visual priority should be:

1. work identity;
2. author/year/bibliographic context;
3. scholarly attention state;
4. record count;
5. database state;
6. secondary operations.

The current prominent per-card **Sync** button should no longer visually outrank review and Records navigation.

Recommended card structure:

```text
[cover]  Glas                              [Needs review: 12]
         Jacques Derrida · 1974
         Galilée

         418 records
         Database: Synced

         [Open records]              [⋯]
```

or, if selecting a work opens the inspector:

```text
[cover]  Glas
         Jacques Derrida · 1974
         418 records · 12 need review      [⋯]
```

Clicking/selecting the work should be a proper keyboard-operable control.

Do not keep the current pattern where the `<article>` has a mouse click handler but no equivalent interactive semantics.

Use one of these approaches:

- make the identity/content area an actual button;
- make the title/identity an actual link/button;
- otherwise explicitly implement correct interactive semantics and keyboard handling.

Prefer native controls over ARIA simulation.

The card action menu should contain secondary work operations:

- populate metadata;
- edit metadata;
- review flagged records;
- auto-improve;
- semantic map;
- sync this work;
- remove work.

The destructive remove action must remain clearly distinguishable and preserve any existing confirmation flow.

Do not duplicate the same action both as a top-level card button and inside the menu without a strong reason.

The review count should remain directly actionable and lead to the underlying Records requiring review, as required by `PRD-WRK-004`.

## Phase 7 — Replace the page-jumping overview with a stable inspector

This is the most important interaction change.

Currently selecting a card renders a very large `WorksOverviewCard` above the toolbar/library. `WorksView.vue` then saves `window.scrollY`, changes state, and scrolls back to the same absolute Y coordinate.

Remove that workaround.

The selected work should no longer change the vertical geometry above the library.

Desktop target:

```text
library                       inspector
--------------------------   --------------------------
work                         selected work
work                         metadata
work                         citation
work                         insights
work                         actions
```

The inspector should:

- be persistent beside the library at sufficiently wide widths;
- use a bounded/sticky region where practical;
- scroll internally when content is long;
- not push the work list downward;
- expose a close/deselect control;
- restore a coherent focus target when closed;
- preserve selected work in the URL.

On narrow screens:

- selecting a work opens an accessible detail surface using `UiDialog` or another existing well-tested overlay convention;
- Escape closes it;
- focus is trapped/restored correctly by the existing foundation;
- scrolling the library should not be destroyed;
- closing returns the user to the work they selected.

Do not build a home-grown focus trap.

The detail content can continue to reuse `WorksOverviewCard`, but refactor that component so it behaves as inspector content rather than a page-within-a-page.

It should not contain an additional giant page-level `<h1>` if the page already has the Works title. The selected Work name should use the heading level appropriate to the inspector hierarchy.

## Phase 8 — Reorganize work details around user intent

The selected-work inspector should emphasize three things.

### Overview

Show:

- cover;
- Work title;
- author;
- publication year;
- bibliographic metadata;
- citation;
- total Records;
- number needing review;
- annotations where applicable;
- database status.

Primary scholarly actions should include:

- Open records
- Review records, when unresolved Records exist
- Edit metadata

### Insights

Keep Work insights, but do not make a large analytical dashboard unavoidable.

Use progressive disclosure or a clearly subordinate section.

The current clarification that these counts come from populated metadata in loaded Records rather than the vector index should remain.

Empty states must remain explicit. Do not imply that an empty insight card means a processing failure unless that is actually known.

### Secondary operations

Place actions such as:

- Populate metadata with LLM
- Semantic map
- View annotations
- Sync to database

in a secondary action area/menu.

Do not let infrastructure operations visually dominate the scholarly object.

## Phase 9 — Make admin and researcher Works variants structurally consistent

Do not maintain two substantially different page architectures.

Admin and researcher modes should share:

- the same `UiPageHeader` foundation;
- the same library-toolbar grammar;
- the same work-selection behavior;
- the same card identity hierarchy;
- the same inspector layout.

Capabilities should determine which controls appear.

Researcher mode should remain read-oriented and must not expose admin corpus-management actions.

If researcher Works are sourced from the database rather than browser-loaded JSONL, make the context strip reflect that truth instead of pretending the same data source applies. Reuse layout, not false semantics.

## Phase 10 — Remove remaining Works-specific presentation anti-patterns

As part of the redesign:

- remove the bespoke Works hero gradient if no longer needed;
- use semantic design tokens rather than raw one-off color mixes where existing tokens suffice;
- align spacing, radius, typography, focus states, and toolbar behavior with Records/Search;
- avoid `!important` unless an existing architectural constraint genuinely requires it;
- do not introduce fixed colors;
- test dark/high-contrast/forced-colors behavior;
- use the existing shared button/menu/dialog/status components rather than reproducing them locally.

Do not attempt to make Works look visually identical to Records. The library can remain visually distinct. The goal is shared interaction grammar and design-system consistency.

# Runtime and architecture constraints

`useWorksWorkspace.ts` is explicitly described as a transitional boundary over the legacy runtime.

Do not increase coupling to `runtime.js`.

If new view state or behavior is required, prefer adding typed functionality to:

- `domain/worksWorkspace.ts`
- `composables/useWorksWorkspace.ts`
- typed Works state/types

and let `runtime.js` remain a thin compatibility/export layer where necessary.

Do not move new UI logic into legacy string-rendering functions.

Where older presenter HTML still exists for compatibility or snapshots, keep it behaviorally compatible or retire it only if it is provably dead and tests confirm that removal is safe.

Continue the broader project direction of decomposing monoliths and reducing legacy runtime ownership.

# Accessibility requirements

Treat WCAG 2.2 AA as a release requirement, not a best-effort goal.

Verify all of the following:

- Work selection is keyboard accessible.
- Focus is visible.
- Menu interactions work with keyboard.
- Inspector/dialog close behavior restores focus.
- Selected state is not communicated by color alone.
- Review/sync statuses include text, not merely colored dots.
- Search/filter/sort controls have accessible names.
- Result-count changes are understandable without disruptive announcements.
- Disabled actions communicate the reason.
- Empty/loading/error states are programmatically meaningful.
- Cards do not contain invalid nested interactive controls.
- Heading levels remain coherent after the page/inspector refactor.
- `prefers-reduced-motion` is honored.
- 200% and 400% zoom do not make the workspace unusable.
- narrow/mobile layouts do not require accidental horizontal scrolling.
- forced-colors mode retains boundaries and focus indication.
- long French strings do not overlap, truncate consequential text, or hide controls.

Use existing accessibility primitives and test infrastructure where possible.

# i18n requirements

All new user-visible copy must be translation-key driven.

Maintain exact English/French key parity.

Use professional Canadian French consistent with the rest of the application.

Do not concatenate translated fragments in ways that assume English word order.

Pay particular attention to:

- corpus-context explanations;
- database/sync copy;
- result summaries;
- sort labels;
- filter names;
- inspector labels;
- action-menu labels;
- empty states.

Update the User Guide where the Works workflow materially changes.

# Testing plan

At minimum update/add coverage around:

- `web/tests/frontend/works-view.test.ts`
- `web/tests/frontend/works-workspace.test.ts`
- `web/tests/frontend/works-overview-card.test.ts`
- `web/tests/e2e/works.spec.ts`

Also update route/persistence tests if new Works state is added.

Add targeted tests for:

- page uses shared header grammar;
- admin and researcher layouts remain capability-correct;
- page totals do not change merely because a search filter is entered;
- visible result count does change correctly;
- selected work remains URL-backed;
- sorting state restores from URL;
- filter state restores from URL;
- back/forward restores previous Works state;
- clicking a Work does not move the library vertically because of an inserted overview card;
- card selection is keyboard-operable;
- review count opens the correct record subset;
- database sync remains functional;
- disabled sync reasons remain visible;
- global actions continue to call the existing runtime/domain commands;
- researcher mode does not expose admin actions;
- semantic map still opens for the correct Work;
- site creation still exports selected Works;
- work removal still uses the existing confirmation path;
- French strings render cleanly;
- no WCAG 2.2 AA violations in the header, library card, toolbar, inspector, and narrow dialog state.

Storybook should cover the meaningful component states, including:

- Works header;
- context strip;
- toolbar;
- normal work card;
- selected work card;
- work needing review;
- unsynchronized/database-unavailable state;
- long title;
- missing cover;
- mixed bibliographic value;
- inspector;
- empty library;
- French/long-string state;
- dark mode/high contrast where the Storybook infrastructure supports it.

Do not add giant snapshot suites simply to freeze markup. Prefer semantic interaction/accessibility assertions.

# Required regressions to avoid

Do not break:

- existing corpus file loading;
- JSONL separation;
- metadata population;
- human metadata authority;
- annotation navigation;
- work-specific record filtering;
- review-flagged navigation;
- database selection;
- per-work sync;
- sync-all behavior;
- semantic maps;
- static-site creation;
- researcher work browsing;
- URL restoration;
- permissions/capability gating.

No redesign is complete if it merely hides a currently available function.

# Definition of done

The task is complete only when all of the following are true:

1. Works uses the same high-level workspace grammar as Records and Search.
2. A user can immediately distinguish loaded corpus state from indexed/database state.
3. The page header no longer contains five unrelated operations competing for attention.
4. Sync controls live with database context.
5. Work cards prioritize scholarly identity and review state over infrastructure.
6. Work selection is natively keyboard accessible.
7. Selecting a Work does not insert a giant overview above the library and disorient scrolling.
8. A stable desktop inspector and accessible narrow-screen detail flow replace the current layout shift.
9. Search, useful filtering, sorting, and compact browsing support both small and large corpora.
10. Safe Works state is route-backed and survives refresh/back/forward.
11. Page-wide metrics have stable semantics independent of filtering.
12. Admin and researcher variants share one coherent visual/interaction system.
13. All new UI is fully localized.
14. WCAG 2.2 AA checks pass.
15. Storybook represents the new components and important states.
16. Existing Works/domain behavior remains covered and passing.
17. No new legacy-runtime coupling is introduced.
18. All repository CI checks pass.

# Scope discipline

Do not turn this task into a rewrite of corpus storage, cELF semantics, vector-store behavior, metadata enrichment, or publication architecture.

Refactor domain/view-state boundaries where necessary to produce a clean Works workspace, but preserve authoritative data semantics.

If implementation reveals a larger architectural issue that cannot safely be solved in this change, document it as a follow-up instead of burying an unrelated rewrite in the PR.

# Expected delivery

Implement this on a dedicated branch from the latest `master`. Keep commits logically separated so the review history shows the migration clearly—for example: typed snapshot/state cleanup, shared header/context, library toolbar/card changes, inspector migration, accessibility/i18n/tests.

The PR description should include:

- the previous workflow problems;
- the new information architecture;
- screenshots at desktop and narrow widths;
- admin and researcher screenshots;
- light/dark examples;
- details of URL-state changes;
- accessibility verification performed;
- tests run;
- any deliberately deferred follow-ups.
