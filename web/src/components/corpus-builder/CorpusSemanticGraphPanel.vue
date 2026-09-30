<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
/**
 * Semantic content map.
 *
 * A corpus graph can hold tens of thousands of entities. The panel never asks
 * for the whole projection: it requests a bounded, ranked *view* (the overview
 * or one entity's neighbourhood) and a paged index, and states plainly when
 * the drawing is partial.
 */
import { computed, onBeforeUnmount, ref, watch } from "vue";
import UiRelationDotNode from "../relations/UiRelationDotNode.vue";
import UiRelationEdge from "../relations/UiRelationEdge.vue";
import UiRelationToolbar from "../relations/UiRelationToolbar.vue";
import UiRelationViewport from "../relations/UiRelationViewport.vue";
import { useRelationLayoutState } from "../../composables/relations/useRelationLayoutState";
import { useRelationNodeDrag } from "../../composables/relations/useRelationNodeDrag";
import { relationBoundsForPoints } from "../../domain/relations/geometry";
import { RELATION_SURFACE_PRESETS } from "../../domain/relations/presets";
import type { RelationViewportState } from "../../domain/relations/types";
import {
  corpusBuildsApi,
  type DocumentIntelligenceRun,
  type SemanticContentGraph,
  type SemanticContentGraphView,
  type SemanticGraphViewEdge,
  type SemanticGraphViewNode,
  type SemanticGraphViewRelation,
  type SemanticIndexSort,
  type SemanticRelationKindFilter,
} from "../../api/corpus";
import { readDocumentIntelligence } from "../../features/corpus-builder/api/documentIntelligenceReads";
import { layoutGraph, nodeRadius, type LayoutPoint } from "../../domain/semanticGraphLayout";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{
  buildId: string;
  summary?: SemanticContentGraph["summary"] | null;
  disabled?: boolean;
}>();
const emit = defineEmits<{ refreshed: [] }>();
const i18n = useI18nStore();

const surfacePreset = RELATION_SURFACE_PRESETS.semanticNetwork;
const WIDTH = 960;
const HEIGHT = 560;
const DENSITIES = [40, 80, 150, 250] as const;
const INDEX_PAGE = 50;
const LABEL_BUDGET = 18;
const RELATION_OPTIONS: Array<{ kind: SemanticRelationKindFilter; key: string }> = [
  { kind: "all", key: "pdf_corpus.semantic_graph_relations_all" },
  { kind: "semantic", key: "pdf_corpus.semantic_graph_relations_semantic_short" },
  { kind: "observational", key: "pdf_corpus.semantic_graph_relations_observational_short" },
];

const view = ref<SemanticContentGraphView | null>(null);
const intelligence = ref<DocumentIntelligenceRun | null>(null);
const loading = ref(false);
const rerunning = ref(false);
const error = ref("");
const opened = ref(false);

const entityQuery = ref("");
const debouncedQuery = ref("");
const selectedTypes = ref<string[]>([]);
const relationKind = ref<SemanticRelationKindFilter>("all");
const density = ref<number>(80);
const minMentions = ref(0);
const focusId = ref("");
const focusTrail = ref<Array<{ id: string; label: string }>>([]);
const selectedNodeId = ref("");
const hoveredNodeId = ref("");
const showAllLabels = ref(false);
const indexOffset = ref(0);
const indexSort = ref<SemanticIndexSort>("mentions");

let controller: AbortController | null = null;
let queryTimer: ReturnType<typeof setTimeout> | null = null;
let requestSeq = 0;

async function load() {
  if (!props.buildId) return;
  controller?.abort();
  const own = new AbortController();
  controller = own;
  const seq = ++requestSeq;
  loading.value = true;
  error.value = "";
  try {
    const next = await corpusBuildsApi.semanticContentGraphView(
      props.buildId,
      {
        q: debouncedQuery.value.trim() || undefined,
        types: selectedTypes.value.length ? selectedTypes.value : undefined,
        relation_kind: relationKind.value,
        focus: focusId.value || undefined,
        node_limit: density.value,
        edge_limit: Math.min(1200, density.value * 5),
        min_mentions: minMentions.value || undefined,
        index_offset: indexOffset.value,
        index_limit: INDEX_PAGE,
        index_sort: indexSort.value,
      },
      { signal: own.signal },
    );
    if (seq !== requestSeq) return;
    view.value = next;
    if (focusId.value && !next.focus) {
      focusId.value = "";
      focusTrail.value = [];
    }
  } catch (exc) {
    if (own.signal.aborted || seq !== requestSeq) return;
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    if (seq === requestSeq) loading.value = false;
  }
}

async function loadIntelligence() {
  intelligence.value = await readDocumentIntelligence(props.buildId).catch(() => null);
}

async function rerun() {
  if (!props.buildId || rerunning.value) return;
  rerunning.value = true;
  error.value = "";
  try {
    const result = await corpusBuildsApi.rerunDocumentIntelligence(props.buildId);
    intelligence.value = result.document_intelligence;
    emit("refreshed");
    await load();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    rerunning.value = false;
  }
}

function onToggle(event: Event) {
  const open = (event.currentTarget as HTMLDetailsElement).open;
  opened.value = open;
  if (open && !view.value) {
    void load();
    void loadIntelligence();
  }
}

watch(entityQuery, (value) => {
  if (queryTimer) clearTimeout(queryTimer);
  queryTimer = setTimeout(() => {
    debouncedQuery.value = value;
  }, 250);
});

watch([debouncedQuery, selectedTypes, relationKind, density, minMentions, indexSort], () => {
  indexOffset.value = 0;
  if (opened.value) void load();
});
watch([focusId, indexOffset], () => {
  if (opened.value) void load();
});

watch(
  () => props.buildId,
  () => {
    controller?.abort();
    view.value = null;
    intelligence.value = null;
    entityQuery.value = "";
    debouncedQuery.value = "";
    selectedTypes.value = [];
    relationKind.value = "all";
    minMentions.value = 0;
    focusId.value = "";
    focusTrail.value = [];
    selectedNodeId.value = "";
    indexOffset.value = 0;
    if (opened.value) {
      void load();
      void loadIntelligence();
    }
  },
);

onBeforeUnmount(() => {
  controller?.abort();
  if (queryTimer) clearTimeout(queryTimer);
});

/* ---------- Types, colour and sizing ---------- */

const typeFacets = computed(() => view.value?.facets.types || []);
const typeHue = computed(() => {
  const map = new Map<string, number>();
  typeFacets.value.forEach((facet, i) => map.set(facet.type, (i % 6) + 1));
  return map;
});
function hueClass(type: string) {
  return `hue-${typeHue.value.get(type) || 6}`;
}
function toggleType(type: string) {
  selectedTypes.value = selectedTypes.value.includes(type)
    ? selectedTypes.value.filter((value) => value !== type)
    : [...selectedTypes.value, type];
}
const hasFilters = computed(
  () =>
    Boolean(entityQuery.value) ||
    selectedTypes.value.length > 0 ||
    relationKind.value !== "all" ||
    minMentions.value > 0,
);
function clearFilters() {
  entityQuery.value = "";
  debouncedQuery.value = "";
  selectedTypes.value = [];
  relationKind.value = "all";
  minMentions.value = 0;
}

/* ---------- Layout ---------- */

const nodes = computed<SemanticGraphViewNode[]>(() => view.value?.view.nodes || []);
const edges = computed<SemanticGraphViewEdge[]>(() => view.value?.view.edges || []);
const nodesById = computed(() => new Map(nodes.value.map((node) => [node.id, node])));
const maxMentions = computed(() =>
  Math.max(1, ...nodes.value.map((node) => node.mention_count || 0)),
);
const maxEdgeCount = computed(() => Math.max(1, ...edges.value.map((edge) => edge.count || 1)));

const automaticPositions = computed<Map<string, LayoutPoint>>(() =>
  layoutGraph(
    nodes.value.map((node) => ({ id: node.id, weight: node.mention_count })),
    edges.value.map((edge) => ({ source: edge.source, target: edge.target, weight: edge.count })),
    { width: WIDTH, height: HEIGHT, pinned: view.value?.focus?.node.id },
  ),
);
const layoutState = useRelationLayoutState();
const positions = computed<Map<string, LayoutPoint>>(() => {
  const next = new Map<string, LayoutPoint>();
  for (const node of nodes.value) {
    const fallback = automaticPositions.value.get(node.id) || { x: WIDTH / 2, y: HEIGHT / 2 };
    next.set(node.id, layoutState.positionFor(node.id, fallback));
  }
  return next;
});
const layoutIdentity = computed(() =>
  JSON.stringify({
    focus: view.value?.query.focus || "",
    query: view.value?.query.query || "",
    types: view.value?.query.types || [],
    relationKind: view.value?.query.relation_kind || "all",
    nodeLimit: view.value?.query.node_limit || density.value,
    minMentions: view.value?.query.min_mentions || 0,
    nodes: nodes.value.map((node) => node.id),
  }),
);

const adjacency = computed(() => {
  const map = new Map<string, Set<string>>();
  for (const edge of edges.value) {
    if (!map.has(edge.source)) map.set(edge.source, new Set());
    if (!map.has(edge.target)) map.set(edge.target, new Set());
    map.get(edge.source)!.add(edge.target);
    map.get(edge.target)!.add(edge.source);
  }
  return map;
});

/** Hover wins over selection for transient highlight; either dims unrelated nodes. */
const highlightId = computed(() => hoveredNodeId.value || selectedNodeId.value);
const highlightSet = computed(() => {
  if (!highlightId.value || !nodesById.value.has(highlightId.value)) return null;
  return new Set([highlightId.value, ...(adjacency.value.get(highlightId.value) || [])]);
});

const labelledIds = computed(() => {
  if (showAllLabels.value) return new Set(nodes.value.map((node) => node.id));
  const ids = new Set(nodes.value.slice(0, LABEL_BUDGET).map((node) => node.id));
  if (view.value?.focus) ids.add(view.value.focus.node.id);
  for (const id of highlightSet.value || []) ids.add(id);
  return ids;
});

type DrawnNode = SemanticGraphViewNode & { x: number; y: number; r: number };
const drawnNodes = computed<DrawnNode[]>(() =>
  nodes.value
    .map((node) => {
      const point = positions.value.get(node.id) || { x: WIDTH / 2, y: HEIGHT / 2 };
      return { ...node, ...point, r: nodeRadius(node.mention_count, maxMentions.value) };
    })
    // Paint small nodes last so they are never hidden under large ones.
    .sort((a, b) => b.r - a.r),
);

function edgePath(edge: SemanticGraphViewEdge) {
  const a = positions.value.get(edge.source);
  const b = positions.value.get(edge.target);
  if (!a || !b) return "";
  // A slight curve separates reciprocal relations and reads better than straight spokes.
  const mx = (a.x + b.x) / 2 + (b.y - a.y) * 0.08;
  const my = (a.y + b.y) / 2 - (b.x - a.x) * 0.08;
  return `M${a.x},${a.y} Q${mx},${my} ${b.x},${b.y}`;
}
function edgeWidth(edge: SemanticGraphViewEdge) {
  return 0.75 + 2.25 * Math.sqrt((edge.count || 1) / maxEdgeCount.value);
}
function edgeActive(edge: SemanticGraphViewEdge) {
  return (
    !highlightId.value || edge.source === highlightId.value || edge.target === highlightId.value
  );
}

const contentBounds = computed(() =>
  relationBoundsForPoints(
    drawnNodes.value.flatMap((node) => [
      { x: node.x - node.r, y: node.y - node.r },
      { x: node.x + node.r, y: node.y + node.r },
    ]),
    48,
  ),
);

/* ---------- Shared viewport and node movement ---------- */

const viewport = ref<InstanceType<typeof UiRelationViewport> | null>(null);
const viewportState = ref<RelationViewportState>({ pan: { x: 0, y: 0 }, zoom: 1 });
const draggedNodeId = ref("");

const nodeDrag = useRelationNodeDrag({
  getZoom: () => viewportState.value.zoom,
  onMove: (point) => {
    if (draggedNodeId.value) layoutState.setPosition(draggedNodeId.value, point);
  },
});

function onViewportChange(state: RelationViewportState) {
  viewportState.value = state;
}

function fitView() {
  viewport.value?.fitView(contentBounds.value);
}

function resetLayout() {
  layoutState.clearPositions();
  viewport.value?.resetView();
}

function onNodePointerDown(event: PointerEvent, node: DrawnNode) {
  draggedNodeId.value = node.id;
  selectedNodeId.value = node.id;
  nodeDrag.begin(event, { x: node.x, y: node.y });
}

function onNodePointerMove(event: PointerEvent) {
  nodeDrag.update(event);
}

function onNodePointerEnd(event: PointerEvent) {
  nodeDrag.end(event);
  draggedNodeId.value = "";
}

function onNodeClick(event: MouseEvent, node: DrawnNode) {
  if (nodeDrag.consumeClick(event)) return;
  selectNode(node.id);
}

function onNodeKeydown(event: KeyboardEvent, node: DrawnNode) {
  draggedNodeId.value = node.id;
  if (nodeDrag.nudge(event, { x: node.x, y: node.y })) {
    draggedNodeId.value = "";
    return;
  }
  draggedNodeId.value = "";
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    selectNode(node.id);
  }
}

watch(layoutIdentity, (next, previous) => {
  if (previous && next !== previous) {
    layoutState.clearPositions();
    viewport.value?.resetView();
  }
});

/* ---------- Selection & focus ---------- */

function selectNode(id: string) {
  selectedNodeId.value = id;
}
function focusNode(id: string, label: string) {
  if (!id || id === focusId.value) return;
  const at = focusTrail.value.findIndex((item) => item.id === id);
  focusTrail.value =
    at >= 0 ? focusTrail.value.slice(0, at + 1) : [...focusTrail.value, { id, label }].slice(-6);
  focusId.value = id;
  selectedNodeId.value = id;
  indexOffset.value = 0;
}
function backToOverview() {
  focusId.value = "";
  focusTrail.value = [];
}

const selectedNode = computed(() => {
  if (!selectedNodeId.value) return null;
  if (view.value?.focus?.node.id === selectedNodeId.value) return view.value.focus.node;
  return (
    nodesById.value.get(selectedNodeId.value) ||
    view.value?.index.items.find((node) => node.id === selectedNodeId.value) ||
    null
  );
});
const focusDetail = computed(() =>
  view.value?.focus && view.value.focus.node.id === selectedNodeId.value ? view.value.focus : null,
);
const selectedEdges = computed(() =>
  selectedNodeId.value
    ? edges.value.filter(
        (edge) => edge.source === selectedNodeId.value || edge.target === selectedNodeId.value,
      )
    : [],
);
const relationGroups = computed(() => {
  const relations = focusDetail.value?.relations || [];
  return [
    {
      kind: "semantic",
      title: i18n.t("pdf_corpus.semantic_graph_semantic_relations"),
      items: relations.filter((rel) => rel.relation_kind === "semantic"),
    },
    {
      kind: "observational",
      title: i18n.t("pdf_corpus.semantic_graph_observational_relations"),
      items: relations.filter((rel) => rel.relation_kind !== "semantic"),
    },
  ].filter((group) => group.items.length);
});

function relationLabel(predicate: string) {
  return String(predicate || "").replaceAll("_", " ");
}
function authorityLabel(status: string) {
  if (status === "human_confirmed")
    return i18n.t("pdf_corpus.semantic_graph_authority_human_confirmed");
  if (status === "disputed") return i18n.t("pdf_corpus.semantic_graph_authority_disputed");
  return i18n.t("pdf_corpus.semantic_graph_authority_unreviewed");
}
function featureText(values?: Array<{ label: string; count?: number }>) {
  return (values || [])
    .slice(0, 8)
    .map((item) => (Number(item.count || 0) > 1 ? `${item.label} ×${item.count}` : item.label))
    .join(" · ");
}
function nodeAriaLabel(node: SemanticGraphViewNode) {
  return `${node.label}, ${node.type}, ${i18n.tf("pdf_corpus.semantic_graph_mentions", {
    count: node.mention_count,
    records: node.record_count,
  })}`;
}
function relationKey(rel: SemanticGraphViewRelation) {
  return `${rel.id}:${rel.direction}`;
}

/* ---------- Status copy ---------- */

const formatter = computed(() => new Intl.NumberFormat(i18n.locale || undefined));
function n(value: number) {
  return formatter.value.format(value || 0);
}
const showingText = computed(() => {
  const v = view.value?.view;
  if (!v) return "";
  return i18n.tf("pdf_corpus.semantic_graph_showing", {
    nodes: n(v.nodes.length),
    total: n(v.candidate_nodes),
    edges: n(v.edges.length),
    edgeTotal: n(v.candidate_edges),
  });
});
const truncated = computed(() =>
  Boolean(view.value?.view.truncated_nodes || view.value?.view.truncated_edges),
);
const pageText = computed(() => {
  const index = view.value?.index;
  if (!index || !index.total) return "";
  return i18n.tf("pdf_corpus.semantic_graph_page", {
    start: n(index.offset + 1),
    end: n(Math.min(index.total, index.offset + index.items.length)),
    total: n(index.total),
  });
});
</script>

<template>
  <details class="semantic-graph-panel" @toggle="onToggle">
    <summary>
      <span>
        <b>{{ i18n.t("pdf_corpus.semantic_graph_title") }}</b>
        <small>{{
          i18n.tf("pdf_corpus.semantic_graph_summary", {
            nodes: n(props.summary?.nodes || 0),
            edges: n(props.summary?.edges || 0),
          })
        }}</small>
      </span>
    </summary>

    <div class="semantic-graph-body">
      <header class="semantic-graph-heading">
        <div>
          <h3>{{ i18n.t("pdf_corpus.semantic_graph_heading") }}</h3>
          <p>{{ i18n.t("pdf_corpus.semantic_graph_help") }}</p>
        </div>
        <button
          v-if="intelligence?.stale"
          class="btn secondary"
          type="button"
          :disabled="props.disabled || rerunning"
          @click="rerun"
        >
          {{
            rerunning
              ? i18n.t("pdf_corpus.document_intelligence_rerunning")
              : i18n.t("pdf_corpus.document_intelligence_rerun")
          }}
        </button>
      </header>

      <p v-if="intelligence?.stale" class="graph-banner warning" role="status">
        {{ i18n.t("pdf_corpus.document_intelligence_stale") }}
      </p>

      <!-- Filter toolbar -->
      <div
        class="graph-toolbar"
        role="group"
        :aria-label="i18n.t('pdf_corpus.semantic_graph_filter')"
      >
        <label class="toolbar-field search" for="semantic-graph-search">
          <span>{{ i18n.t("pdf_corpus.semantic_graph_search") }}</span>
          <input
            id="semantic-graph-search"
            v-model="entityQuery"
            class="control"
            type="search"
            autocomplete="off"
            :placeholder="i18n.t('pdf_corpus.semantic_graph_search_placeholder')"
          />
        </label>
        <div class="toolbar-field">
          <span id="semantic-graph-relations-label">{{
            i18n.t("pdf_corpus.semantic_graph_relations_filter")
          }}</span>
          <div class="segmented" role="radiogroup" aria-labelledby="semantic-graph-relations-label">
            <button
              v-for="option in RELATION_OPTIONS"
              :key="option.kind"
              type="button"
              role="radio"
              :aria-checked="relationKind === option.kind"
              :class="{ active: relationKind === option.kind }"
              @click="relationKind = option.kind"
            >
              {{ i18n.t(option.key) }}
            </button>
          </div>
        </div>
        <label class="toolbar-field narrow" for="semantic-graph-min-mentions">
          <span>{{ i18n.t("pdf_corpus.semantic_graph_min_mentions") }}</span>
          <input
            id="semantic-graph-min-mentions"
            v-model.number="minMentions"
            class="control"
            type="number"
            min="0"
            step="1"
            inputmode="numeric"
          />
        </label>
        <label class="toolbar-field narrow" for="semantic-graph-density">
          <span>{{ i18n.t("pdf_corpus.semantic_graph_density") }}</span>
          <select id="semantic-graph-density" v-model.number="density" class="control">
            <option v-for="value in DENSITIES" :key="value" :value="value">
              {{ i18n.tf("pdf_corpus.semantic_graph_density_option", { count: value }) }}
            </option>
          </select>
        </label>
        <button v-if="hasFilters" class="btn ghost clear" type="button" @click="clearFilters">
          {{ i18n.t("pdf_corpus.semantic_graph_clear_filters") }}
        </button>
      </div>

      <div
        v-if="typeFacets.length"
        class="type-chips"
        role="group"
        :aria-label="i18n.t('pdf_corpus.semantic_graph_types')"
      >
        <button
          v-for="facet in typeFacets"
          :key="facet.type"
          type="button"
          :class="[
            'type-chip',
            hueClass(facet.type),
            { active: selectedTypes.includes(facet.type) },
          ]"
          :aria-pressed="selectedTypes.includes(facet.type)"
          @click="toggleType(facet.type)"
        >
          <i class="swatch" aria-hidden="true" />
          <span>{{ facet.type }}</span>
          <small>{{ n(facet.count) }}</small>
        </button>
      </div>

      <!-- Breadcrumb + result status -->
      <div class="graph-statusbar">
        <nav :aria-label="i18n.t('pdf_corpus.semantic_graph_breadcrumb')" class="breadcrumb">
          <ol>
            <li>
              <button v-if="focusId" type="button" class="crumb" @click="backToOverview">
                {{ i18n.t("pdf_corpus.semantic_graph_overview") }}
              </button>
              <span v-else aria-current="page">{{
                i18n.t("pdf_corpus.semantic_graph_overview")
              }}</span>
            </li>
            <li v-for="(crumb, i) in focusTrail" :key="crumb.id">
              <button
                v-if="i < focusTrail.length - 1"
                type="button"
                class="crumb"
                @click="focusNode(crumb.id, crumb.label)"
              >
                {{ crumb.label }}
              </button>
              <span v-else aria-current="page">{{ crumb.label }}</span>
            </li>
          </ol>
        </nav>
        <p class="result-count" role="status" aria-live="polite">
          <span v-if="loading && view" class="spinner" aria-hidden="true" />
          {{ loading && !view ? i18n.t("ui.loading") : showingText }}
        </p>
      </div>
      <p v-if="truncated && !focusId" class="graph-banner info">
        {{ i18n.t("pdf_corpus.semantic_graph_truncated_hint") }}
      </p>
      <p v-if="error" class="graph-banner error" role="alert">{{ error }}</p>

      <div v-if="view" class="graph-layout">
        <div class="graph-stage" :class="{ busy: loading }">
          <UiRelationToolbar
            class="graph-controls"
            :accessible-label="i18n.t('pdf_corpus.semantic_graph_accessible_label')"
            :zoom-out-label="i18n.t('pdf_corpus.semantic_graph_zoom_out')"
            :zoom-in-label="i18n.t('pdf_corpus.semantic_graph_zoom_in')"
            :fit-label="i18n.t('pdf_corpus.semantic_graph_zoom_fit')"
            :reset-label="i18n.t('pdf_corpus.semantic_graph_reset_layout', 'Reset graph layout')"
            @zoom-out="viewport?.zoomBy(1 / 1.25)"
            @zoom-in="viewport?.zoomBy(1.25)"
            @fit="fitView"
            @reset="resetLayout"
          >
            <template #after>
              <label class="labels-toggle">
                <input v-model="showAllLabels" type="checkbox" />
                <span>{{ i18n.t("pdf_corpus.semantic_graph_labels_toggle") }}</span>
              </label>
            </template>
          </UiRelationToolbar>

          <p v-if="!nodes.length && !loading" class="graph-empty">
            {{
              hasFilters
                ? i18n.t("pdf_corpus.semantic_graph_no_matches")
                : i18n.t("pdf_corpus.semantic_graph_empty")
            }}
          </p>

          <UiRelationViewport
            v-else
            ref="viewport"
            class="graph-viewport"
            :accessible-label="i18n.t('pdf_corpus.semantic_graph_accessible_label')"
            :help-text="
              i18n.t(
                'pdf_corpus.semantic_graph_keyboard_help',
                'Drag the background to pan. Drag a node to reposition it. Arrow keys pan, plus and minus zoom, and 0 resets the view. Hold Alt and use an arrow key to move a focused node.',
              )
            "
            :resize-label="
              i18n.t('pdf_corpus.semantic_graph_resize', 'Resize semantic content graph')
            "
            :initial-center="{ x: WIDTH / 2, y: HEIGHT / 2 }"
            :content-bounds="contentBounds"
            :content-width="WIDTH"
            :content-height="HEIGHT"
            :min-zoom="surfacePreset.minZoom"
            :max-zoom="surfacePreset.maxZoom"
            :resize-axis="surfacePreset.resizeAxis"
            @viewport-change="onViewportChange"
            @keydown.esc="selectedNodeId = ''"
          >
            <svg
              class="graph-canvas"
              :viewBox="`0 0 ${WIDTH} ${HEIGHT}`"
              :width="WIDTH"
              :height="HEIGHT"
            >
              <g class="graph-edges" aria-hidden="true">
                <UiRelationEdge
                  v-for="edge in edges"
                  :key="edge.id"
                  :path="edgePath(edge)"
                  :width="edgeWidth(edge)"
                  :title="`${relationLabel(edge.predicate)} · ${authorityLabel(edge.authority_status)}`"
                  :class="[
                    'graph-edge',
                    edge.relation_kind,
                    edge.authority_status,
                    { dim: !edgeActive(edge), lit: highlightId && edgeActive(edge) },
                  ]"
                />
              </g>
              <g class="graph-nodes">
                <g
                  v-for="node in drawnNodes"
                  :key="node.id"
                  :transform="`translate(${node.x}, ${node.y})`"
                  :class="[
                    'graph-node',
                    hueClass(node.type),
                    {
                      selected: node.id === selectedNodeId,
                      focus: node.id === view.focus?.node.id,
                      dim: highlightSet && !highlightSet.has(node.id),
                    },
                  ]"
                  role="button"
                  tabindex="0"
                  :aria-label="nodeAriaLabel(node)"
                  :aria-pressed="node.id === selectedNodeId"
                  @click.stop="onNodeClick($event, node)"
                  @dblclick.stop="focusNode(node.id, node.label)"
                  @pointerdown.stop="onNodePointerDown($event, node)"
                  @pointermove.stop="onNodePointerMove"
                  @pointerup.stop="onNodePointerEnd"
                  @pointercancel.stop="onNodePointerEnd"
                  @pointerenter="hoveredNodeId = node.id"
                  @pointerleave="hoveredNodeId = ''"
                  @focus="hoveredNodeId = node.id"
                  @blur="hoveredNodeId = ''"
                  @keydown="onNodeKeydown($event, node)"
                >
                  <UiRelationDotNode
                    :radius="node.r"
                    :label="node.label.length > 32 ? `${node.label.slice(0, 31)}…` : node.label"
                    :show-label="labelledIds.has(node.id)"
                  />
                </g>
              </g>
            </svg>
          </UiRelationViewport>

          <footer class="graph-legend">
            <span
              v-for="facet in typeFacets.slice(0, 6)"
              :key="facet.type"
              :class="hueClass(facet.type)"
            >
              <i class="swatch" aria-hidden="true" />{{ facet.type }}
            </span>
            <span
              ><i class="legend-line semantic" aria-hidden="true" />{{
                i18n.t("pdf_corpus.semantic_graph_semantic")
              }}</span
            >
            <span
              ><i class="legend-line observational" aria-hidden="true" />{{
                i18n.t("pdf_corpus.semantic_graph_observational")
              }}</span
            >
            <span
              ><i class="legend-line disputed" aria-hidden="true" />{{
                i18n.t("pdf_corpus.semantic_graph_legend_disputed")
              }}</span
            >
            <span
              ><i class="legend-size" aria-hidden="true" />{{
                i18n.t("pdf_corpus.semantic_graph_legend_size")
              }}</span
            >
          </footer>
          <p id="semantic-graph-keyboard-help" class="graph-hint">
            {{ i18n.t("pdf_corpus.semantic_graph_keyboard_help") }}
          </p>
        </div>

        <aside class="graph-inspector" :aria-label="i18n.t('pdf_corpus.semantic_graph_inspector')">
          <template v-if="selectedNode">
            <div class="inspector-head">
              <p :class="['type-pill', hueClass(selectedNode.type)]">
                <i class="swatch" aria-hidden="true" />{{ selectedNode.type }}
              </p>
              <button
                type="button"
                class="icon-btn small"
                :aria-label="i18n.t('pdf_corpus.semantic_graph_clear_selection')"
                :title="i18n.t('pdf_corpus.semantic_graph_clear_selection')"
                @click="selectedNodeId = ''"
              >
                ×
              </button>
            </div>
            <h4>{{ selectedNode.label }}</h4>
            <p v-if="selectedNode.aliases?.length" class="graph-aliases">
              {{ selectedNode.aliases.join(" · ") }}
            </p>
            <dl class="stat-row">
              <div>
                <dt>{{ i18n.t("pdf_corpus.semantic_graph_mentions_short") }}</dt>
                <dd>{{ n(selectedNode.mention_count) }}</dd>
              </div>
              <div>
                <dt>{{ i18n.t("pdf_corpus.semantic_graph_records_short") }}</dt>
                <dd>{{ n(selectedNode.record_count) }}</dd>
              </div>
              <div>
                <dt>{{ i18n.t("pdf_corpus.semantic_graph_connections_short") }}</dt>
                <dd>{{ n(selectedNode.degree) }}</dd>
              </div>
            </dl>
            <button
              v-if="selectedNode.id !== focusId"
              type="button"
              class="btn primary focus-btn"
              :aria-label="
                i18n.tf('pdf_corpus.semantic_graph_focus_on', { label: selectedNode.label })
              "
              @click="focusNode(selectedNode.id, selectedNode.label)"
            >
              {{ i18n.t("pdf_corpus.semantic_graph_focus_action") }}
            </button>

            <div v-if="focusDetail?.node.character_profile" class="character-profile">
              <h5>{{ i18n.t("pdf_corpus.semantic_graph_character_profile") }}</h5>
              <dl>
                <template v-if="focusDetail.node.character_profile.actions_as_agent?.length">
                  <dt>{{ i18n.t("pdf_corpus.semantic_graph_actions_agent") }}</dt>
                  <dd>{{ featureText(focusDetail.node.character_profile.actions_as_agent) }}</dd>
                </template>
                <template v-if="focusDetail.node.character_profile.actions_as_patient?.length">
                  <dt>{{ i18n.t("pdf_corpus.semantic_graph_actions_patient") }}</dt>
                  <dd>{{ featureText(focusDetail.node.character_profile.actions_as_patient) }}</dd>
                </template>
                <template v-if="focusDetail.node.character_profile.possessions?.length">
                  <dt>{{ i18n.t("pdf_corpus.semantic_graph_possessions") }}</dt>
                  <dd>{{ featureText(focusDetail.node.character_profile.possessions) }}</dd>
                </template>
                <template v-if="focusDetail.node.character_profile.modifiers?.length">
                  <dt>{{ i18n.t("pdf_corpus.semantic_graph_modifiers") }}</dt>
                  <dd>{{ featureText(focusDetail.node.character_profile.modifiers) }}</dd>
                </template>
              </dl>
              <small>{{ i18n.t("pdf_corpus.semantic_graph_character_profile_note") }}</small>
            </div>

            <template v-if="focusDetail">
              <p class="relations-count">
                {{
                  i18n.tf("pdf_corpus.semantic_graph_relations_count", {
                    shown: n(focusDetail.relations.length),
                    total: n(focusDetail.relations_total),
                  })
                }}
              </p>
              <section v-for="group in relationGroups" :key="group.kind" class="relation-group">
                <h5>{{ group.title }}</h5>
                <ul class="relation-list">
                  <li v-for="rel in group.items" :key="relationKey(rel)">
                    <div class="relation-line">
                      <span class="predicate">
                        <span aria-hidden="true">{{
                          rel.direction === "outgoing" ? "→" : "←"
                        }}</span>
                        <span class="visually-hidden">{{
                          rel.direction === "outgoing"
                            ? i18n.t("pdf_corpus.semantic_graph_direction_outgoing")
                            : i18n.t("pdf_corpus.semantic_graph_direction_incoming")
                        }}</span>
                        {{ relationLabel(rel.predicate) }}
                      </span>
                      <button
                        type="button"
                        :class="['entity-link', hueClass(rel.other_type)]"
                        @click="focusNode(rel.other_id, rel.other_label)"
                      >
                        {{ rel.other_label }}
                      </button>
                    </div>
                    <div class="relation-meta">
                      <span
                        v-if="rel.relation_kind === 'semantic'"
                        :class="['badge', rel.authority_status]"
                      >
                        {{ authorityLabel(rel.authority_status) }}
                      </span>
                      <small>{{
                        i18n.tf("pdf_corpus.semantic_graph_occurrences", {
                          count: n(rel.count),
                          records: n(rel.record_count),
                        })
                      }}</small>
                      <small v-if="rel.evidence_ref_count">{{
                        i18n.tf("pdf_corpus.semantic_graph_evidence_refs", {
                          count: n(rel.evidence_ref_count),
                        })
                      }}</small>
                      <small v-if="rel.observed_verbs.length">{{
                        i18n.tf("pdf_corpus.semantic_graph_observed_verbs", {
                          verbs: rel.observed_verbs.join(" · "),
                        })
                      }}</small>
                    </div>
                  </li>
                </ul>
              </section>
            </template>
            <ul v-else-if="selectedEdges.length" class="relation-list compact">
              <li v-for="edge in selectedEdges.slice(0, 12)" :key="edge.id">
                <div class="relation-line">
                  <span class="predicate">{{ relationLabel(edge.predicate) }}</span>
                  <button
                    type="button"
                    class="entity-link"
                    @click="selectNode(edge.source === selectedNode.id ? edge.target : edge.source)"
                  >
                    {{
                      nodesById.get(edge.source === selectedNode.id ? edge.target : edge.source)
                        ?.label
                    }}
                  </button>
                </div>
              </li>
            </ul>
          </template>
          <div v-else class="inspector-empty">
            <p>{{ i18n.t("pdf_corpus.semantic_graph_select_node") }}</p>
          </div>
        </aside>
      </div>

      <!-- Paged entity index: the accessible, complete route to every entity -->
      <section v-if="view" class="entity-index" aria-labelledby="semantic-graph-entity-index-title">
        <div class="entity-index-heading">
          <div>
            <h4 id="semantic-graph-entity-index-title">
              {{ i18n.t("pdf_corpus.semantic_graph_entity_index") }}
            </h4>
            <p>
              {{
                i18n.tf("pdf_corpus.semantic_graph_entity_index_count", {
                  shown: n(view.index.total),
                  total: n(view.summary.nodes || 0),
                })
              }}
            </p>
          </div>
          <label class="toolbar-field narrow" for="semantic-graph-index-sort">
            <span>{{ i18n.t("pdf_corpus.semantic_graph_sort") }}</span>
            <select id="semantic-graph-index-sort" v-model="indexSort" class="control">
              <option value="mentions">
                {{ i18n.t("pdf_corpus.semantic_graph_sort_mentions") }}
              </option>
              <option value="degree">{{ i18n.t("pdf_corpus.semantic_graph_sort_degree") }}</option>
              <option value="records">
                {{ i18n.t("pdf_corpus.semantic_graph_sort_records") }}
              </option>
              <option value="label">{{ i18n.t("pdf_corpus.semantic_graph_sort_label") }}</option>
            </select>
          </label>
        </div>
        <div class="entity-index-table-wrap">
          <table class="entity-index-table">
            <thead>
              <tr>
                <th scope="col">{{ i18n.t("pdf_corpus.semantic_graph_entity") }}</th>
                <th scope="col">{{ i18n.t("pdf_corpus.semantic_graph_type") }}</th>
                <th scope="col" class="num">
                  {{ i18n.t("pdf_corpus.semantic_graph_mentions_short") }}
                </th>
                <th scope="col" class="num">
                  {{ i18n.t("pdf_corpus.semantic_graph_records_short") }}
                </th>
                <th scope="col" class="num">
                  {{ i18n.t("pdf_corpus.semantic_graph_connections_short") }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="node in view.index.items"
                :key="node.id"
                :class="{ selected: node.id === selectedNodeId }"
              >
                <td>
                  <button type="button" class="entity-link" @click="focusNode(node.id, node.label)">
                    {{ node.label }}
                  </button>
                  <small v-if="node.aliases?.length">{{
                    node.aliases.slice(0, 4).join(" · ")
                  }}</small>
                </td>
                <td>
                  <span :class="['type-pill', hueClass(node.type)]"
                    ><i class="swatch" aria-hidden="true" />{{ node.type }}</span
                  >
                </td>
                <td class="num">{{ n(node.mention_count) }}</td>
                <td class="num">{{ n(node.record_count) }}</td>
                <td class="num">{{ n(node.degree) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="view.index.total > INDEX_PAGE" class="pager">
          <button
            type="button"
            class="btn secondary"
            :disabled="indexOffset === 0 || loading"
            @click="indexOffset = Math.max(0, indexOffset - INDEX_PAGE)"
          >
            {{ i18n.t("pdf_corpus.semantic_graph_prev_page") }}
          </button>
          <span>{{ pageText }}</span>
          <button
            type="button"
            class="btn secondary"
            :disabled="indexOffset + INDEX_PAGE >= view.index.total || loading"
            @click="indexOffset += INDEX_PAGE"
          >
            {{ i18n.t("pdf_corpus.semantic_graph_next_page") }}
          </button>
        </div>
      </section>

      <p v-if="view?.epistemic_note" class="graph-epistemic-note">
        {{ view.epistemic_note }}
      </p>
    </div>
  </details>
</template>

<style scoped>
.semantic-graph-panel {
  container-type: inline-size;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--card);
  overflow: clip;
}
.semantic-graph-panel > summary {
  cursor: pointer;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid transparent;
}
.semantic-graph-panel[open] > summary {
  border-bottom-color: var(--line);
}
.semantic-graph-panel > summary span {
  display: grid;
  gap: 2px;
}
.semantic-graph-panel > summary small,
.semantic-graph-heading p,
.graph-aliases,
.graph-epistemic-note,
.graph-hint,
.result-count,
.relations-count {
  color: var(--muted);
}
.semantic-graph-body {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
}
.semantic-graph-heading {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  align-items: start;
}
.semantic-graph-heading h3,
.semantic-graph-heading p,
.graph-inspector h4,
.graph-inspector p {
  margin: 0;
}
.semantic-graph-heading p {
  max-width: 72ch;
  margin-top: 2px;
}

/* Toolbar */
.graph-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: end;
  padding: var(--space-3);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-inset);
}
.toolbar-field {
  display: grid;
  gap: 4px;
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  color: var(--muted);
}
.toolbar-field.search {
  flex: 1 1 260px;
}
.toolbar-field.narrow .control {
  width: 9rem;
}
.segmented {
  display: inline-flex;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--surface-raised);
}
.segmented button {
  border: 0;
  padding: 6px 12px;
  background: transparent;
  color: var(--text);
  font: inherit;
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  cursor: pointer;
}
.segmented button + button {
  border-inline-start: 1px solid var(--line);
}
.segmented button.active {
  background: var(--surface-selected);
  color: var(--accent-fg);
}
.segmented button:focus-visible,
.type-chip:focus-visible,
.icon-btn:focus-visible,
.crumb:focus-visible,
.entity-link:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}
.btn.clear {
  align-self: end;
}

/* Categorical hues */
.hue-1 {
  --hue: var(--viz-cat-1);
}
.hue-2 {
  --hue: var(--viz-cat-2);
}
.hue-3 {
  --hue: var(--viz-cat-3);
}
.hue-4 {
  --hue: var(--viz-cat-4);
}
.hue-5 {
  --hue: var(--viz-cat-5);
}
.hue-6 {
  --hue: var(--viz-cat-6);
}
.swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--hue, var(--accent));
  flex: none;
}
.type-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.type-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface-raised);
  color: var(--text);
  font: inherit;
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  text-transform: capitalize;
  cursor: pointer;
  transition: background var(--motion-fast) var(--ease-standard);
}
.type-chip small {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.type-chip:hover {
  background: var(--surface-hover);
}
.type-chip.active {
  border-color: var(--hue);
  background: var(--surface-selected);
  box-shadow: inset 0 0 0 1px var(--hue);
}
.type-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  text-transform: capitalize;
}

/* Status bar */
.graph-statusbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2) var(--space-4);
}
.breadcrumb ol {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: var(--fs-sm, var(--fs-xs));
}
.breadcrumb li + li::before {
  content: "›";
  margin-inline-end: 4px;
  color: var(--muted);
}
.breadcrumb [aria-current="page"] {
  font-weight: var(--fw-semibold);
}
.crumb {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--accent-fg);
  font: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
  cursor: pointer;
}
.result-count {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: var(--fs-xs);
  font-variant-numeric: tabular-nums;
}
.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--line-strong);
  border-top-color: var(--accent-fg);
  border-radius: 50%;
  animation: spin 800ms linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.graph-banner {
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid;
  border-radius: var(--radius-md);
  font-size: var(--fs-xs);
}
.graph-banner.info {
  color: var(--tone-info-fg);
  background: var(--tone-info-bg);
  border-color: var(--tone-info-border);
}
.graph-banner.warning {
  color: var(--tone-warn-fg);
  background: var(--tone-warn-bg);
  border-color: var(--tone-warn-border);
}
.graph-banner.error {
  color: var(--tone-danger-fg);
  background: var(--tone-danger-bg);
  border-color: var(--tone-danger-border);
}

/* Stage */
.graph-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 320px);
  gap: var(--space-3);
}
.graph-stage {
  position: relative;
  display: grid;
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-raised);
  overflow: hidden;
}
.graph-stage.busy .graph-viewport {
  opacity: 0.6;
  transition: opacity var(--motion-base) var(--ease-standard);
}
.graph-controls {
  position: absolute;
  top: var(--space-2);
  inset-inline-end: var(--space-2);
  z-index: 1;
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 4px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-overlay);
  box-shadow: var(--elev-1, none);
}
.icon-btn {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm, 6px);
  background: transparent;
  color: var(--text);
  font: inherit;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}
.icon-btn:hover {
  background: var(--surface-hover);
}
.icon-btn.small {
  width: 24px;
  height: 24px;
}
.labels-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding-inline: 6px;
  font-size: var(--fs-xs);
  color: var(--muted);
}
.graph-viewport {
  width: 100%;
  height: min(560px, 70vh);
  min-height: 360px;
}
.graph-canvas {
  position: absolute;
  inset: 0;
  display: block;
  width: 960px;
  max-width: none;
  height: 560px;
  overflow: visible;
}
.graph-empty {
  display: grid;
  place-items: center;
  min-height: 360px;
  margin: 0;
  color: var(--muted);
}
.graph-edge {
  fill: none;
  stroke: var(--border-strong);
  opacity: 0.5;
  transition: opacity var(--motion-fast) var(--ease-standard);
}
.graph-edge.semantic {
  stroke: var(--accent-fg);
  opacity: 0.7;
}
.graph-edge.observational {
  stroke-dasharray: 4 4;
  opacity: 0.35;
}
.graph-edge.disputed {
  stroke: var(--tone-danger-border);
  stroke-dasharray: 1 3;
  opacity: 0.85;
}
.graph-edge.dim {
  opacity: 0.06;
}
.graph-edge.lit {
  opacity: 0.95;
}
.graph-node {
  cursor: grab;
  touch-action: none;
  transition: opacity var(--motion-fast) var(--ease-standard);
}
.graph-node.dim {
  opacity: 0.18;
}
.graph-node {
  --relation-node-dot: var(--hue, var(--accent));
  --relation-node-dot-border: var(--surface-raised);
  --relation-node-label: var(--text);
  --relation-node-label-halo: var(--surface-raised);
  --relation-node-halo: transparent;
  --relation-node-halo-opacity: 1;
}
.graph-node.focus {
  --relation-node-halo: var(--hue, var(--accent));
  --relation-node-halo-opacity: 0.45;
}
.graph-node.selected,
.graph-node:focus-visible {
  --relation-node-halo: var(--focus-ring);
  --relation-node-halo-opacity: 1;
}
.graph-node:focus {
  outline: none;
}
.graph-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  padding: var(--space-2) var(--space-3);
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: var(--fs-xs);
}
.graph-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-transform: none;
}
.legend-line {
  display: inline-block;
  width: 24px;
  border-top: 2px solid var(--border-strong);
}
.legend-line.semantic {
  border-top-color: var(--accent-fg);
}
.legend-line.observational {
  border-top-style: dashed;
}
.legend-line.disputed {
  border-top: 2px dotted var(--tone-danger-border);
}
.legend-size {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 1.5px solid var(--muted);
  border-radius: 50%;
  box-shadow:
    inset 0 0 0 3px var(--surface-raised),
    inset 0 0 0 5px var(--muted);
}
.graph-hint {
  margin: 0;
  padding: 0 var(--space-3) var(--space-2);
  font-size: var(--fs-xs);
}

/* Inspector */
.graph-inspector {
  display: grid;
  align-content: start;
  gap: var(--space-2);
  max-height: 78vh;
  overflow: auto;
  padding: var(--space-3);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-raised);
}
.inspector-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.inspector-empty {
  display: grid;
  place-items: center;
  min-height: 200px;
  color: var(--muted);
  text-align: center;
}
.graph-inspector h4 {
  font-size: var(--fs-lg, 1.125rem);
  overflow-wrap: anywhere;
}
.stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
  margin: var(--space-1, 4px) 0;
}
.stat-row div {
  padding: var(--space-2);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-inset);
}
.stat-row dt {
  font-size: var(--fs-xs);
  color: var(--muted);
}
.stat-row dd {
  margin: 0;
  font-weight: var(--fw-semibold);
  font-variant-numeric: tabular-nums;
}
.focus-btn {
  justify-self: start;
}
.character-profile {
  display: grid;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--line);
}
.character-profile h5,
.character-profile dl,
.character-profile dd,
.relation-group h5 {
  margin: 0;
}
.character-profile dl {
  display: grid;
  gap: var(--space-2);
}
.character-profile dt {
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  color: var(--muted);
}
.character-profile dd {
  overflow-wrap: anywhere;
}
.character-profile small {
  color: var(--muted);
}
.relations-count {
  padding-top: var(--space-2);
  border-top: 1px solid var(--line);
  font-size: var(--fs-xs);
}
.relation-group {
  display: grid;
  gap: var(--space-1, 4px);
}
.relation-group h5 {
  font-size: var(--fs-xs);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
}
.relation-list {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
}
.relation-list li {
  display: grid;
  gap: 4px;
  padding-block: var(--space-2);
  border-top: 1px solid var(--line);
}
.relation-line {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: baseline;
}
.predicate {
  font-size: var(--fs-xs);
  color: var(--muted);
}
.relation-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  align-items: center;
}
.relation-meta small {
  color: var(--muted);
  font-size: var(--fs-xs);
}
.badge {
  padding: 1px 8px;
  border: 1px solid;
  border-radius: 999px;
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  color: var(--tone-warn-fg);
  background: var(--tone-warn-bg);
  border-color: var(--tone-warn-border);
}
.badge.human_confirmed {
  color: var(--tone-ok-fg);
  background: var(--tone-ok-bg);
  border-color: var(--tone-ok-border);
}
.badge.disputed {
  color: var(--tone-danger-fg);
  background: var(--tone-danger-bg);
  border-color: var(--tone-danger-border);
}

/* Entity index */
.entity-index {
  display: grid;
  gap: var(--space-2);
}
.entity-index-heading {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: var(--space-3);
}
.entity-index-heading h4,
.entity-index-heading p {
  margin: 0;
}
.entity-index-heading p {
  margin-top: 2px;
  color: var(--muted);
  font-size: var(--fs-xs);
}
.entity-index-table-wrap {
  max-height: 420px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
}
.entity-index-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-xs);
}
.entity-index-table th,
.entity-index-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--line);
  text-align: start;
  vertical-align: top;
}
.entity-index-table .num {
  text-align: end;
  font-variant-numeric: tabular-nums;
}
.entity-index-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--surface-raised);
  font-weight: var(--fw-semibold);
}
.entity-index-table tbody tr:hover,
.entity-index-table tbody tr.selected {
  background: var(--surface-hover);
}
.entity-index-table td:first-child {
  min-width: 220px;
}
.entity-index-table td:first-child small {
  display: block;
  margin-top: 2px;
  color: var(--muted);
}
.entity-link {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--accent-fg);
  font: inherit;
  font-weight: var(--fw-semibold);
  text-align: start;
  cursor: pointer;
}
.entity-link:hover {
  text-decoration: underline;
}
.pager {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--fs-xs);
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.graph-epistemic-note {
  margin: 0;
  font-size: var(--fs-xs);
  line-height: var(--lh-body);
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation: none;
  }
  .graph-edge,
  .graph-node,
  .type-chip {
    transition: none;
  }
}
@container (max-width: 820px) {
  .graph-layout {
    grid-template-columns: 1fr;
  }
  .semantic-graph-heading,
  .entity-index-heading {
    align-items: stretch;
    flex-direction: column;
  }
  .graph-inspector {
    max-height: none;
  }
}
</style>
