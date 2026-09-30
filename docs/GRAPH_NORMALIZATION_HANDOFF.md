<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# Graph Normalization Implementation Handoff

Snapshot date: 2026-09-29  
Branch: `task/graph-normalization`  
Pull request: #307 — Normalize relational maps, diagrams, and graph interactions  
Implementation source head reviewed for this handoff: `233dd50269bb48a322326967e9780cd1c23e292b`

This document is a handoff for the graph/map/diagram normalization work described in
[`docs/GRAPH_NORMALIZATION_PLAN.md`](./GRAPH_NORMALIZATION_PLAN.md). It reports the implementation state that exists on the branch; it does not replace the architectural plan or the user-facing behavior documented in `docs/USER_GUIDE.md`.

## Current state

The core normalization architecture is implemented and the five principal relational surfaces have been migrated onto the shared interaction model. The branch is not ready to merge yet because current `master` has advanced substantially since the last branch synchronization and the most recent completed CI run still contains failures.

At the time of this handoff:

- branch source head reviewed: `233dd50269bb48a322326967e9780cd1c23e292b`;
- current `master`: `9df99a4351be645304c30fd1ef7dffa1842fb653`;
- GitHub reports the branch as diverged from current `master`;
- the branch comparison reports approximately 100 commits ahead and 149 commits behind current `master`;
- PR #307 is open;
- the last completed full quality-gate run was against commit `e427f80620...`, not the latest branch head.

Because the repository is receiving concurrent work, refresh these numbers before making the next merge/rebase or before interpreting CI failures.

## What is implemented

### Shared relation foundation

The branch now has presentation-only relation contracts and common interaction/state machinery:

- `web/src/domain/relations/types.ts`
- `web/src/domain/relations/geometry.ts`
- `web/src/domain/relations/presets.ts`
- `web/src/composables/relations/useRelationViewport.ts`
- `web/src/composables/relations/useRelationNodeDrag.ts`
- `web/src/composables/relations/useRelationResize.ts`
- `web/src/composables/relations/useRelationSelection.ts`
- `web/src/composables/relations/useRelationLayoutState.ts`

The geometry layer owns graph/screen coordinate conversion, pan/zoom calculations, pointer-anchored zoom, bounds, fit-to-content, and zoom-aware node movement. Manual positions are maintained as presentation overrides rather than being written back into domain objects.

The five normalized surface presets are represented explicitly:

- `semantic-free`
- `semantic-network`
- `semantic-radial`
- `provenance-lanes`
- `pipeline-dag`

These presets describe presentation and interaction configuration only. They do not replace semantic graph, cELF, pipeline, or Record relation contracts.

### Shared components

Implemented relation primitives include:

- `UiRelationViewport.vue`
- `UiRelationWorkspace.vue`
- `UiRelationToolbar.vue`
- `UiRelationResizeHandle.vue`
- `UiRelationNodeShell.vue`
- `UiRelationCardNode.vue`
- `UiRelationChipNode.vue`
- `UiRelationDotNode.vue`
- `UiRelationEdge.vue`
- `UiRelationEdgeLabel.vue`

The shared viewport provides the common pan/zoom/fit/reset/resize coordinate space. Node dragging and keyboard nudging are separated from domain activation/selection behavior.

### Migrated relational surfaces

The following actual relation displays are now on the shared interaction model:

1. `SemanticMapCanvas.vue` / `SemanticMapFrame.vue`
   - free/ring semantic term map;
   - draggable chips;
   - background pan;
   - zoom, fit, reset;
   - resize and keyboard node movement.

2. `PipelineGraphDiagram.vue`
   - DAG layout retained;
   - horizontal/vertical orientation retained;
   - draggable card nodes;
   - live edge rerouting;
   - background pan, zoom, fit, reset, resize.

3. `ResearchObjectDiagram.vue`
   - provenance lanes retained;
   - draggable cards;
   - background pan, zoom, fit, reset, resize;
   - connected edge rerouting;
   - the former SVG `foreignObject` application-card rendering has been removed in favor of ordinary HTML relation cards plus SVG edges.

4. `CorpusRecordSemanticMap.vue`
   - radial layout retained as deterministic base layout;
   - trail/breadcrumb navigation retained;
   - draggable SVG nodes;
   - background pan, zoom, fit, reset, resize;
   - edge endpoints follow manual node movement.

5. `CorpusSemanticGraphPanel.vue`
   - bounded semantic-network view and deterministic force layout retained;
   - filters, density, focus trail, relation distinctions, inspector, and index retained;
   - draggable/pinned presentation overrides added;
   - shared viewport, zoom, fit/reset, resize, and keyboard movement added;
   - edges are recomputed from current presentation positions.

### Documentation and localization

`docs/USER_GUIDE.md` now describes the normalized relationship-map interaction contract.

English and French interaction copy was added/updated in:

- `web/src/i18n/enUsDefaults.json`
- `api/app/locales/en_us.py`
- `api/app/locales/fr_ca.py`

Do not assume locale parity remains intact after bringing in current `master`; re-run the parity checks after synchronization.

### Tests and stories added or updated

Relevant frontend coverage now includes:

- `web/tests/frontend/relation-geometry.test.ts`
- `web/tests/frontend/relation-primitives.test.ts`
- `web/tests/frontend/relation-presets.test.ts`
- `web/tests/frontend/semantic-map.test.ts`
- `web/tests/frontend/pipeline-graph-component.test.ts`
- `web/tests/frontend/research-object-diagram.test.ts`
- `web/tests/frontend/corpus-record-semantic-map.test.ts`
- `web/tests/frontend/corpus-semantic-graph-panel.test.ts`
- `web/src/components/relations/UiRelationViewport.stories.ts`

The relation Storybook file also covers the shared node/edge visual primitives.

## Interaction contract now represented in code

The implementation is designed around these rules:

- dragging empty relation-surface space pans the viewport;
- dragging a node/card changes presentation coordinates and updates connected edges continuously;
- node movement is zoom-aware;
- click versus drag is separated by a movement threshold;
- Arrow keys pan a focused viewport;
- plus/minus control zoom;
- 0 resets the view;
- Alt+Arrow nudges a focused node;
- resize handles support pointer and keyboard resizing;
- Fit changes the viewport without discarding manual positions;
- Reset layout clears manual position overrides and restores the deterministic domain layout.

The authoritative model remains unchanged by these interactions. Node coordinates, pan, zoom, selection, resize state, and manual overrides remain presentation state.

## Important invariants

Do not collapse the shared relation view model into an authoritative universal relation schema.

In particular:

- cELF provenance relationships keep their own meaning and types;
- semantic graph predicates, relation kinds, authority state, and evidence bindings remain semantic-graph domain data;
- pipeline next/fallback routing remains pipeline domain data;
- record-neighborhood membership/traversal remains corpus-builder domain data;
- manual graph coordinates must never be written into Record metadata, cELF objects, semantic assertions, or pipeline definitions.

The shared system is an interaction/rendering abstraction, not a scholarly-data abstraction.

## Validation status

The latest completed full `DerridAI quality gates` run observed for this branch is run `36652986283`, at head `e427f80620...`.

That run had the following successful gates:

- repository Prettier/format check;
- backend type check;
- API contract tests;
- frontend application typecheck;
- frontend test/config typecheck;
- frontend lint;
- backend lint;
- both legacy frontend shards;
- both Playwright/composed UI shards;
- production application build within the E2E jobs;
- Storybook build within the E2E jobs;
- composed UI/WCAG checks within both E2E shards.

That run still failed:

- backend regression tests;
- frontend unit/component tests;
- the dedicated Corpus Builder WCAG 2.2 AA sweep;
- therefore the aggregate frontend job also failed.

Several commits were pushed after `e427f80620...` to fix relation accessibility prop binding, test typing, Storybook args, and interaction-help localization. The latest branch head reviewed for this handoff did not yet have a completed check run attached to it. Do not infer that the remaining failures are fixed until CI runs on the synchronized current head.

## Current blocker: master drift

The highest-priority next action is repository synchronization.

Current `master` advanced dramatically after the branch's previous merge from master. At the time of this handoff, GitHub reports the graph-normalization branch roughly 149 commits behind current `master`.

Before further feature work:

1. inspect the current `master` diff and open PRs touching the same files;
2. merge/rebase current `master` into `task/graph-normalization` without overwriting unrelated concurrent work;
3. resolve locale, tooltip/help, design-system, test, and documentation conflicts by preserving both the newer master contracts and the relation-normalization behavior;
4. rerun the entire quality-gate matrix on the resulting head.

Do not use a force push merely to simplify the history while concurrent repository work is active.

## Remaining normalization work

The central interaction migration is substantially implemented, but the original plan still contains unfinished items.

### Shared subcomponents still not implemented as dedicated components

The planned component inventory included the following, which do not currently exist as dedicated relation components:

- `UiRelationEdgeLayer`
- `UiRelationInspector`
- `UiRelationLegend`
- `UiRelationBreadcrumbs`
- `UiRelationAccessibleIndex`

Do not add these merely to satisfy a filename checklist. Add them only where they remove real duplication or solve an accessibility/consistency issue. Of these, the accessible non-spatial node/relation index is the most important outstanding architectural item for dense graphs.

### Accessibility work still requiring verification

The dense semantic graph can expose many focusable SVG nodes. The original plan called for a roving-focus or equivalent strategy plus a searchable/non-spatial accessible index. That work is not complete as a shared primitive.

The dedicated Corpus Builder accessibility sweep failed in the last completed CI run. Inspect that failure after synchronizing with current `master`; do not assume it is caused solely by graph normalization.

### Expand/fullscreen behavior

Resize is implemented. A standardized expand/fullscreen action, called for in the original plan for dense graphs, is not yet established as a shared relation-workspace feature.

### Presentation-state persistence

Manual positions are presentation-only and resettable, but durable per-workspace/user persistence was intentionally deferred. Keep it deferred unless there is a concrete product requirement; session-local state is the safer merge scope.

### End-to-end interaction tests

Unit/component tests cover the relation behaviors directly. Existing E2E shards passed on the last completed run, but the original plan called for explicit browser-level coverage of:

- dragging a background;
- dragging a node at non-100% zoom;
- live edge following;
- pointer resize;
- keyboard resize;
- Fit;
- Reset layout;
- pipeline orientation after manual placement;
- semantic focus navigation after node movement.

Add a small representative Playwright set after the branch is synchronized and the component/unit suite is green. Avoid duplicating every component test in Playwright.

### Storybook coverage

Shared relation stories exist and existing domain components already have Storybook coverage, but verify the five preset/configuration families against:

- dense state;
- French/long strings;
- dark mode;
- high contrast/forced colors;
- reduced motion;
- narrow containers.

Do this through existing story infrastructure rather than creating redundant stories for every small state.

## Recommended next sequence

1. Synchronize `task/graph-normalization` with the latest `master`.
2. Run the full quality gates on the synchronized head.
3. Fix failing frontend unit/component tests first; they are the fastest signal for interaction regressions.
4. Fix the dedicated Corpus Builder WCAG sweep.
5. Investigate the backend regression failure and determine whether it is branch-related or newly introduced by master; do not label it unrelated without evidence.
6. Confirm EN/FR key parity and placeholders.
7. Add the minimum representative Playwright interaction coverage.
8. Decide whether `UiRelationAccessibleIndex`/roving focus must land in this PR or in a tightly scoped follow-up; if it remains required for WCAG/readability, keep it in this PR.
9. Re-run production build, Storybook, all frontend tests, WCAG scans, backend tests, and API contracts.
10. Update PR #307 validation text with commands/results actually observed.
11. Only then treat the branch as merge-ready.

## Files most likely to conflict with current master

Because recent repository work includes tooltip/help/accessibility changes, pay particular attention to:

- `api/app/locales/en_us.py`
- `api/app/locales/fr_ca.py`
- `web/src/i18n/enUsDefaults.json`
- `docs/USER_GUIDE.md`
- `web/src/components/corpus-builder/CorpusRecordSemanticMap.vue`
- `web/src/components/corpus-builder/CorpusSemanticGraphPanel.vue`
- `web/src/components/pipelines/PipelineGraphDiagram.vue`
- `web/src/components/record/ResearchObjectDiagram.vue`
- `web/src/components/semantic/SemanticMapCanvas.vue`
- `web/src/components/semantic/SemanticMapFrame.vue`

The safest conflict-resolution rule is: keep the newest master accessibility/design-system/help contract, then reapply the shared relation interaction behavior without restoring duplicated pan/zoom/drag code.

## PR handoff

PR #307 already describes the intended normalized interaction contract. Before requesting review, update its Validation section to reflect the synchronized final head and the actual passing/failing gates.

Useful references:

- Plan: `docs/GRAPH_NORMALIZATION_PLAN.md`
- Current user behavior: `docs/USER_GUIDE.md`, “Relationship-map controls”
- Pull request: #307
- Last completed full quality-gate run reviewed in this handoff: `36652986283`

The branch should be handed forward as an active implementation branch, not as completed work.
