# Relational Graph, Diagram, and Map Normalization Plan

Status: implementation plan  
Branch: `task/graph-normalization`  
Base: `master` at `ab124be64b9631347f022be71f51e1d6fcba506a`  
Scope: normalize all relational diagram/map/graph displays in the DerridAI web application.

## 1. Goal

DerridAI currently has several independently evolved graph, map, and diagram implementations. They share common interaction needs but implement pan, zoom, node dragging, edge routing, selection, resizing, accessibility, controls, and styling differently.

The goal of this work is to create a reusable relational-visualization component system that:

- gives every relational canvas a consistent interaction model;
- preserves domain-specific semantics and data contracts;
- keeps layout and viewport state separate from authoritative scholarly/corpus data;
- allows each visualization to retain the layout and rendering style appropriate to its domain;
- substantially reduces duplicated pointer, zoom, pan, selection, edge, and accessibility logic;
- provides Storybook and automated-test coverage for the shared interaction contract.

The result should be one relational interaction system with explicit layout/rendering configurations, rather than several unrelated mini graph engines.

## 2. Non-goals and semantic constraints

This normalization is a UI/presentation-layer abstraction. It must not introduce a universal persisted `Relation` domain object or flatten cELF provenance, semantic relations, workflow routing, or application-specific relationships into one authoritative schema.

Shared node and edge types are view models only. Domain adapters continue to own the meaning of:

- cELF provenance/object relationships;
- semantic graph predicates, authority, observational/semantic relation classes, and evidence state;
- pipeline `next` and fallback routing;
- record-neighborhood membership and linked-record traversal;
- any future domain-specific relation types.

Viewport state is never corpus metadata. Node coordinates, pan, zoom, selection, container size, and manual layout overrides must remain presentation/workspace state.

## 3. Current relational surfaces

### 3.1 Semantic map canvas

Files:

- `web/src/components/semantic/SemanticMapCanvas.vue`
- `web/src/components/semantic/SemanticMapFrame.vue`
- `web/src/domain/semanticMap.ts`

Purpose: small free-form concept/topic/person/record map.

Current behavior:

- background click-and-drag panning;
- draggable nodes;
- keyboard panning;
- zoom/reset controls;
- deterministic ring-style initial placement.

Gaps:

- no shared viewport primitive;
- no shared resize behavior;
- local pan/drag/zoom implementation;
- local toolbar/control styling;
- different node/edge presentation from other relational surfaces.

### 3.2 Corpus semantic content graph

Files:

- `web/src/components/corpus-builder/CorpusSemanticGraphPanel.vue`
- `web/src/domain/semanticGraphLayout.ts`

Purpose: bounded view over the corpus semantic graph using deterministic force layout.

Current behavior:

- background pan;
- wheel zoom;
- keyboard pan/zoom/reset;
- selection and hover highlighting;
- double-click focus;
- density and relation filtering;
- inspector and legend;
- deterministic force layout.

Gaps:

- nodes cannot be manually dragged/repositioned;
- viewport logic is bespoke;
- fixed aspect-ratio assumptions;
- graph toolbar and sizing differ from other maps;
- large inline component duplicates concerns that should be subcomponents/composables.

### 3.3 Record semantic map

Files:

- `web/src/components/corpus-builder/CorpusRecordSemanticMap.vue`
- `web/src/features/corpus-builder/domain/semanticMap.ts`

Purpose: radial map of a record, local semantic nodes, outward relations, and walkable neighborhoods.

Current behavior:

- deterministic radial layout;
- zoom controls and wheel zoom;
- breadcrumb/trail traversal;
- node activation;
- semantic and membership edge styles.

Gaps:

- no background panning;
- no node dragging;
- fixed `820 x 600` drawing;
- scrolling is used as navigation on narrow panels;
- no shared viewport/resize contract.

### 3.4 Research object / traceability diagram

Files:

- `web/src/components/record/ResearchObjectDiagram.vue`
- `web/src/components/record/RecordTraceabilityExplorer.vue`
- `web/src/types/researchObjectGraph.ts`

Purpose: cELF-oriented provenance and relationship map across source, record, metadata, evidence, and research-output lanes.

Current behavior:

- lane layout;
- card nodes;
- curved edges;
- edge labels for active relationships;
- focus, neighbor, and contextual states;
- static scroll container.

Gaps:

- no background panning;
- no zoom;
- no node dragging;
- no resize;
- node cards are HTML buttons inside SVG `foreignObject`, complicating reuse and accessibility;
- relation-card and connector presentation in `RecordTraceabilityExplorer` is separate from the full relationship map vocabulary.

### 3.5 Pipeline graph diagram

Files:

- `web/src/components/pipelines/PipelineGraphDiagram.vue`
- `web/src/domain/pipelineGraph.ts`
- `web/src/components/pipelines/PipelineStageConnections.vue`

Purpose: directed pipeline/workflow graph with execution-state overlays.

Current behavior:

- horizontal and vertical layouts;
- draggable card nodes;
- live edge rerouting when nodes move;
- selected-stage inspector;
- execution and fallback edge styling.

Gaps:

- no background panning;
- no zoom or fit-to-view;
- no resizable viewport;
- bespoke node drag implementation;
- bespoke controls and relation presentation.

## 4. Target component architecture

Create a new component family under:

`web/src/components/relations/`

Suggested structure:

```
relations/
  UiRelationWorkspace.vue
  UiRelationViewport.vue
  UiRelationToolbar.vue
  UiRelationResizeHandle.vue

  nodes/
    UiRelationNodeShell.vue
    UiRelationCardNode.vue
    UiRelationDotNode.vue
    UiRelationChipNode.vue

  edges/
    UiRelationEdgeLayer.vue
    UiRelationEdge.vue
    UiRelationEdgeLabel.vue

  UiRelationInspector.vue
  UiRelationLegend.vue
  UiRelationBreadcrumbs.vue
  UiRelationAccessibleIndex.vue
```

Create shared interaction composables under:

`web/src/composables/relations/`

Suggested files:

```
useRelationViewport.ts
useRelationNodeDrag.ts
useRelationSelection.ts
useRelationResize.ts
useRelationLayoutState.ts
```

Create shared view-model/layout contracts under:

`web/src/domain/relations/`

Suggested files:

```
types.ts
geometry.ts
layouts/
  freeLayout.ts
  forceLayout.ts
  radialLayout.ts
  laneLayout.ts
  dagLayout.ts
```

Existing domain layout code should initially be adapted, not rewritten gratuitously. The migration should move algorithms only when doing so removes real duplication or establishes a clean reusable contract.

## 5. Shared view-model contract

The shared node/edge model is transient UI data.

Example:

```ts
export interface RelationViewNode<T = unknown> {
  id: string;
  x: number;
  y: number;
  draggable?: boolean;
  locked?: boolean;
  selected?: boolean;
  metadata: T;
}

export interface RelationViewEdge<T = unknown> {
  id: string;
  source: string;
  target: string;
  directed?: boolean;
  label?: string;
  metadata: T;
}
```

Domain components adapt their own data into this representation. They do not replace their existing domain types with it.

## 6. Shared interaction contract

Every actual relation map/diagram/graph must support the following unless a configuration explicitly disables an action for a documented reason.

### 6.1 Background panning

- Click-and-drag on empty canvas space pans the map.
- Pointer capture must keep the drag stable when the pointer leaves the element.
- The cursor is `grab` at rest and `grabbing` while panning.
- Touch dragging pans the viewport.
- Scrollbars are not the primary navigation mechanism for graph content.

### 6.2 Node/card dragging

- Every visual node/card is draggable by default.
- Nodes can be marked `locked` only when a domain surface has a specific reason.
- Connected edges redraw continuously while a node moves.
- Dragging modifies presentation coordinates only.
- A movement threshold, approximately 4 CSS pixels, distinguishes click from drag.
- Pointer-down followed by no meaningful movement remains a selection click.
- Dragging at non-100% zoom must convert screen deltas into graph-space deltas correctly.

### 6.3 Zoom

All canvases support:

- mouse wheel / trackpad zoom;
- toolbar zoom in;
- toolbar zoom out;
- keyboard `+` / `-`;
- Fit to content;
- Reset layout/view.

Where practical, wheel zoom should anchor around the pointer rather than always around canvas center.

### 6.4 Resize

Every relation workspace is resizable.

Requirements:

- pointer-accessible resize handle;
- keyboard-accessible resize handle;
- sensible min/max width and height;
- no dependence on CSS `resize` alone;
- expanded/fullscreen mode for dense or detailed graphs;
- responsive behavior that preserves usability at narrow widths.

### 6.5 Keyboard interaction

When the viewport itself has focus:

- Arrow keys pan.
- Shift+Arrow pans by a larger increment.
- `+` / `-` zoom.
- `0` fits or resets view according to the toolbar action naming.
- Escape clears transient selection where applicable.

When a node has focus:

- Enter/Space selects or activates according to the domain's existing semantic action.
- `Alt+Arrow` nudges the node.
- `Alt+Shift+Arrow` nudges by a larger increment.
- Keyboard node movement has the same coordinate and edge-update semantics as pointer dragging.

### 6.6 Selection and activation

Selection must remain distinct from navigation/activation.

Examples:

- single click: select/highlight node;
- drag: reposition node;
- double click: allowed for domain navigation such as semantic-neighborhood focus;
- explicit action or Enter/Space: domain-appropriate activation.

The shared primitive must not hard-code the meaning of activation.

## 7. Layout and user overrides

Automatic layout, manual node placement, and viewport transform are separate layers:

```
domain graph
  -> automatic layout
  -> user node-position overrides
  -> viewport pan/zoom transform
  -> screen
```

Rules:

- automatic layout is deterministic for the same input when the current algorithm is deterministic;
- manual movement creates a position override rather than mutating domain data;
- Reset layout clears manual overrides and reruns/reapplies the automatic layout;
- Fit view changes the viewport without clearing manual layout;
- zoom does not change graph-space node positions;
- graph identity/revision changes may invalidate presentation overrides.

For the force-directed semantic graph, manual drag should effectively pin the moved node in presentation state until reset/re-layout.

## 8. Optional persistence of presentation state

Presentation state may be persisted in a workspace/user-preference store, keyed by stable graph identity and revision, for example:

```
<surface-id>:<graph-identity>:<graph-revision>
```

Potential persisted values:

- workspace width/height;
- zoom;
- pan;
- expanded state;
- manual node-position overrides.

Do not write these values into cELF objects, Record metadata, semantic-graph nodes, pipeline definitions, or scholarly provenance.

Persistence should be introduced after the shared interaction model is stable. The first migration may keep state session-local to minimize scope.

## 9. Rendering strategy

Do not force all graphs into one SVG-only renderer.

### 9.1 HTML node layer + SVG edge layer

Use for:

- pipeline DAG;
- cELF provenance/traceability cards;
- small semantic chip/card maps.

Advantages:

- ordinary accessible buttons/cards;
- simpler text layout;
- direct reuse of design-system primitives;
- easier drag handles and focus treatment;
- avoids SVG `foreignObject` for application UI.

### 9.2 SVG node + SVG edge layer

Use for:

- dense semantic network dots;
- other future high-node-count visualizations.

The shared viewport and coordinate system must work with both rendering modes.

## 10. Visual configurations

Implement explicit configuration profiles instead of ad hoc behavior.

### 10.1 `semantic-free`

Used by the small semantic map.

- deterministic ring/free placement;
- chip/card node renderer;
- simple line edges;
- manual node dragging;
- background pan;
- zoom/fit/reset;
- record/sidebar/modal/page workspace variants.

### 10.2 `semantic-network`

Used by the corpus semantic graph.

- deterministic force layout;
- SVG dot nodes and labels;
- weighted/curved relation edges;
- hover neighborhood highlighting;
- selection and inspector;
- density and filtering controls;
- double-click focus;
- node dragging/pinning.

### 10.3 `semantic-radial`

Used by the record semantic map.

- center/inner/outer radial layout;
- record center node plus semantic nodes;
- membership/semantic/observational edges;
- breadcrumb/trail traversal;
- draggable nodes after initial radial layout;
- pan/zoom/fit/reset.

### 10.4 `provenance-lanes`

Used by the research-object/traceability map.

- semantic lanes;
- card nodes;
- curved, labelled relationships;
- cELF normative/application distinction;
- selected/neighbor/context states;
- pan/zoom/fit/reset;
- draggable nodes with lane-preserving or free-move behavior decided during implementation.

Default approach: allow free manual movement after lane layout while retaining lane backgrounds as orientation guides.

### 10.5 `pipeline-dag`

Used by pipeline definition and execution diagrams.

- horizontal/vertical DAG layout;
- card nodes;
- directed arrow edges;
- edge-kind styles for normal and fallback routes;
- execution-state overlays;
- selected-stage inspector;
- draggable nodes;
- background pan;
- zoom/fit/reset.

## 11. Shared subcomponents

### 11.1 `UiRelationWorkspace`

Responsibilities:

- outer composition;
- toolbar slot/default toolbar;
- viewport;
- optional inspector;
- legend;
- empty/loading/error states;
- responsive sizing;
- expanded/fullscreen mode.

It must not know domain semantics.

### 11.2 `UiRelationViewport`

Responsibilities:

- graph-space/screen-space transforms;
- pan;
- zoom;
- pointer capture;
- wheel handling;
- keyboard viewport handling;
- fit-to-content;
- resize integration;
- exposing current transform/state to child renderers.

This is the central normalization primitive.

### 11.3 `UiRelationNodeShell`

Responsibilities:

- node selection;
- pointer drag;
- click-vs-drag threshold;
- keyboard nudging;
- focus/hover state;
- locked/disabled handling;
- emitting graph-space position changes.

Appearance is supplied by card/dot/chip components.

### 11.4 Node variants

`UiRelationCardNode`

- pipeline stages;
- provenance/cELF objects;
- future card-based relation diagrams.

`UiRelationDotNode`

- dense semantic graph.

`UiRelationChipNode`

- compact concept/topic/person maps.

### 11.5 Edge components

`UiRelationEdgeLayer`

- one SVG layer shared by HTML-node graphs;
- handles shared coordinate system and clipping.

`UiRelationEdge`

- line/path rendering;
- optional direction marker;
- selected/active/dimmed states;
- domain-supplied style/tone metadata.

`UiRelationEdgeLabel`

- reusable edge-label background and text;
- hides or reduces labels based on density/selection policy supplied by the wrapper.

### 11.6 `UiRelationToolbar`

Common controls:

- Zoom out;
- Zoom percentage/status;
- Zoom in;
- Fit;
- Reset layout;
- Expand/collapse.

Domain wrappers can add controls such as orientation, label visibility, density, relation filters, and semantic-layer toggles through slots.

### 11.7 `UiRelationResizeHandle`

- visible affordance;
- pointer resize;
- keyboard resize;
- localized accessible label/instructions;
- min/max enforcement.

### 11.8 `UiRelationInspector`

A shell only. Domain components supply inspector contents.

### 11.9 `UiRelationLegend`

Standard spacing, typography, line/dot/card legend primitives, and forced-colors treatment while allowing domain-specific labels.

### 11.10 `UiRelationAccessibleIndex`

Provides a non-spatial representation of nodes and direct relations for keyboard/screen-reader use.

For dense graphs, this should prevent the visual canvas from forcing hundreds of independent tab stops.

## 12. Accessibility requirements

The migration must improve accessibility rather than merely preserve pointer behavior.

Requirements:

- avoid `role="application"` as a default unless a specific component has a documented need;
- use a labelled focusable region for the canvas;
- expose concise keyboard instructions via `aria-describedby`;
- provide a list/index representation of graph content;
- use roving focus or equivalent for dense node sets;
- announce selection changes where necessary;
- provide keyboard equivalents for pan, zoom, node movement, resizing, fit, and reset;
- ensure focus indication works in normal, dark, high-contrast, and forced-colors modes;
- honor reduced-motion preferences;
- do not communicate relation/state meaning by color alone;
- preserve at least the current accessible names and node metadata;
- ensure touch targets and toolbar controls meet current design-system sizing standards.

## 13. Styling normalization

The relation component family should use the current semantic design tokens consistently.

Migration targets include replacing graph-local aliases/usages where appropriate with the current design-system vocabulary, including:

- surfaces;
- borders;
- text hierarchy;
- selected/hover/focus states;
- tone/status tokens;
- radius and elevation;
- motion tokens.

Raw bespoke controls should migrate to existing UI primitives such as `UiButton`, `UiTooltip`, and `UiStatusBadge` when they fit.

Do not convert domain-specific semantic distinctions into generic status colors if doing so would lose meaning.

## 14. Migration strategy

Keep existing domain component filenames and public interfaces wherever practical. Convert them into adapters/wrappers over the relation primitives. This reduces route, selector, Storybook, and regression risk.

### Phase 0 — Baseline and characterization

Before changing behavior:

- inventory current selectors/events used by tests;
- record Storybook cases;
- add focused characterization tests where current behavior is insufficiently protected;
- identify any open PRs touching the same graph components before each migration phase.

### Phase 1 — Shared foundation

Implement:

- view-model types;
- geometry helpers;
- `useRelationViewport`;
- `useRelationNodeDrag`;
- `useRelationResize`;
- `useRelationSelection`;
- `UiRelationViewport`;
- `UiRelationNodeShell`;
- `UiRelationToolbar`;
- `UiRelationResizeHandle`;
- base Storybook stories and tests.

Pilot: `SemanticMapCanvas.vue`.

Acceptance for the pilot:

- existing drag behavior preserved;
- background pan preserved;
- zoom/reset preserved;
- resize added;
- keyboard node movement added;
- no semantic-map domain logic moved into the generic component.

### Phase 2 — Pipeline graph

Migrate `PipelineGraphDiagram.vue`.

Preserve:

- horizontal/vertical orientation;
- execution-state node styling;
- fallback edge kinds;
- inspector;
- edge rerouting after node movement.

Add:

- background pan;
- wheel/button/keyboard zoom;
- fit;
- reset layout;
- resize/expand.

This phase validates HTML card nodes + SVG edges.

### Phase 3 — Research object / traceability map

Migrate `ResearchObjectDiagram.vue`.

Preserve:

- lane grouping;
- cELF object/type labels;
- normative vs application relationship styles;
- selected/neighbor/context highlighting;
- active edge labels.

Change:

- move HTML node cards out of SVG `foreignObject`;
- use shared card node shell;
- add background pan, zoom, fit, reset, resize, and node drag.

Normalize relation-card and legend styling in `RecordTraceabilityExplorer.vue` using non-canvas relation subcomponents where useful.

### Phase 4 — Record semantic radial map

Migrate `CorpusRecordSemanticMap.vue`.

Preserve:

- radial initial layout;
- center/inner/outer semantics;
- trail/breadcrumb navigation;
- mention-layer controls;
- linked-record and neighborhood behavior;
- semantic/observational/membership relation distinctions.

Add:

- background pan;
- node drag;
- fit/reset;
- shared resize behavior;
- remove reliance on fixed 820x600 scrolling as primary navigation.

### Phase 5 — Corpus semantic network

Migrate `CorpusSemanticGraphPanel.vue` last because it is the largest and densest surface.

Preserve:

- bounded server-side graph view;
- deterministic force layout;
- filtering;
- density;
- relation kinds;
- query/focus trail;
- inspector;
- edge authority/relation presentation;
- truncation messaging;
- index/pagination.

Add:

- node drag/pinning;
- shared viewport;
- shared toolbar controls;
- resize;
- accessible-index integration;
- shared selection/focus primitives where appropriate.

Break the current monolithic component into logical subcomponents while preserving API behavior.

### Phase 6 — Cleanup

After all consumers migrate:

- remove duplicated pan/zoom/drag code;
- remove redundant graph-specific CSS;
- remove obsolete geometry helpers;
- remove no-longer-used control implementations;
- consolidate Storybook fixtures/helpers;
- update architecture/user documentation where interaction behavior is described.

## 15. Testing plan

### 15.1 Unit tests

Cover:

- graph-space <-> screen-space conversion;
- zoom limits;
- zoom anchor behavior;
- pan calculations;
- pointer drag threshold;
- node movement at zoom levels below/above 100%;
- pointer capture cleanup;
- resize min/max bounds;
- keyboard resize;
- keyboard node nudging;
- manual node overrides;
- reset-layout behavior;
- fit-to-content bounds;
- edge endpoint/path recomputation.

### 15.2 Component tests

For shared primitives:

- pointer pan;
- node drag;
- click without drag;
- selection;
- locked node;
- wheel zoom;
- toolbar zoom;
- fit;
- reset;
- resize;
- expanded mode;
- keyboard interaction;
- accessible labels and help text.

### 15.3 Storybook

Each layout/configuration should include:

- normal graph;
- selected node;
- moved/manual-layout node;
- empty;
- loading where relevant;
- error where relevant;
- dense graph;
- long labels;
- French/long-string stress;
- narrow/mobile container;
- dark mode;
- high contrast;
- forced colors;
- reduced motion.

### 15.4 Playwright

Representative end-to-end coverage must verify:

- background drag pans;
- node drag moves a card/dot;
- connected edge follows a dragged node;
- node drag remains correct at non-100% zoom;
- resize handle changes viewport dimensions;
- keyboard resize works;
- zoom controls work;
- Fit works;
- Reset layout restores automatic placement;
- orientation changes continue working for pipelines;
- semantic focus navigation continues working;
- traceability node selection continues working;
- accessibility scans remain clean.

## 16. Performance constraints

The normalization must not make dense semantic graphs materially slower.

Guidelines:

- keep high-node-count rendering in SVG rather than hundreds of HTML cards;
- avoid deep reactive object replacement on every pointermove where local mutable presentation state is safe;
- use requestAnimationFrame for pointer-driven transform updates if profiling shows excessive reactive rendering;
- do not rerun force/radial/DAG automatic layout during ordinary panning or zooming;
- do not rerun automatic layout on every node drag;
- recompute only the edges affected by a moved node when that materially improves performance;
- preserve the server-side bounded-view strategy of the semantic graph.

Performance changes should be measured with the existing maximum density scenario.

## 17. i18n requirements

All new user-facing text must use the i18n store.

Shared relation strings should use a consistent namespace, for example:

`relations.*`

Likely keys include:

- pan/drag help;
- zoom in/out;
- fit;
- reset layout;
- expand/collapse;
- resize help;
- selected node;
- relation index;
- keyboard help;
- node movement help.

Existing domain-specific terminology remains in its current namespace where appropriate.

## 18. Definition of done

This project is complete when:

1. Every actual relational map, graph, or diagram supports background click-and-drag panning.
2. Every graph supports wheel/buttons/keyboard zoom plus Fit and Reset layout.
3. Every relation workspace is pointer-resizable and keyboard-resizable.
4. Every visual node/card is draggable unless explicitly marked locked.
5. Connected edges update continuously while nodes move.
6. Manual positions do not mutate authoritative domain/corpus/cELF data.
7. Manual placement survives ordinary selection/inspection changes and is removed only by explicit reset or graph-identity invalidation.
8. Shared toolbar, cursor, focus, resize, empty/loading/error, and responsive behavior is consistent.
9. Domain-specific relation meaning remains domain-specific.
10. Existing deterministic layouts remain deterministic before presentation overrides.
11. All five configurations have representative Storybook coverage.
12. Playwright covers pan, node drag, resize, fit/reset, keyboard interaction, and domain-specific regression paths.
13. Unit tests cover shared geometry and interaction state.
14. All new copy is localized.
15. High-contrast/forced-colors and dark-mode behavior is verified.
16. No viewport or layout state leaks into cELF, Record metadata, pipeline definitions, or scholarly provenance.
17. The previous independent pan/zoom/drag implementations are removed once all consumers use the shared primitives.

## 19. Initial implementation sequence

The first implementation commit after this plan should:

1. add shared view-model/geometry types;
2. add `useRelationViewport`;
3. add `useRelationNodeDrag`;
4. add `useRelationResize`;
5. add `UiRelationViewport` and `UiRelationResizeHandle`;
6. add unit and Storybook coverage;
7. migrate `SemanticMapCanvas.vue` as the pilot without changing its domain API.

After the pilot passes frontend CI and accessibility checks, proceed to Pipeline Graph Diagram, Research Object Diagram, Record Semantic Map, and Corpus Semantic Graph Panel in that order.
