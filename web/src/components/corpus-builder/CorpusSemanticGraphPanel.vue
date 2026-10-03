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

<script setup lang="ts">
/**
 * Semantic content map.
 *
 * A corpus graph can hold tens of thousands of entities. The panel never asks
 * for the whole projection: it requests a bounded, ranked *view* (the overview
 * or one entity's neighbourhood) and a paged index, and states plainly when
 * the drawing is partial.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
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
  type SemanticIndexSort,
  type SemanticRelationKindFilter,
} from "../../api/corpus";
import { readDocumentIntelligence } from "../../features/corpus-builder/api/documentIntelligenceReads";
import { layoutGraph, nodeRadius, type LayoutPoint } from "../../domain/semanticGraphLayout";
import { useI18nStore } from "../../stores/i18n";
import {
  SEMANTIC_INDEX_PAGE as INDEX_PAGE,
  authorityLabel as authorityText,
  relationLabel,
} from "../../domain/semanticGraphLabels";
import UiLoadingState from "../ui/UiLoadingState.vue";
import SemanticGraphEntityIndex from "./SemanticGraphEntityIndex.vue";
import SemanticGraphInspector from "./SemanticGraphInspector.vue";

const props = defineProps<{
  buildId: string;
  summary?: SemanticContentGraph["summary"] | null;
  disabled?: boolean;
  /** Shown inside the semantic dialog: always open, no disclosure summary, loads on mount. */
  embedded?: boolean;
}>();
const emit = defineEmits<{ refreshed: [] }>();
const i18n = useI18nStore();

const surfacePreset = RELATION_SURFACE_PRESETS.semanticNetwork;
const WIDTH = 960;
const HEIGHT = 560;
const DENSITIES = [40, 80, 150, 250] as const;
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

onMounted(() => {
  if (!props.embedded) return;
  opened.value = true;
  void load();
  void loadIntelligence();
});

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
const rovingNodeId = ref("");

watch(
  drawnNodes,
  (next) => {
    if (!next.length) {
      rovingNodeId.value = "";
      return;
    }
    if (next.some((node) => node.id === rovingNodeId.value)) return;
    const preferred =
      (selectedNodeId.value && next.some((node) => node.id === selectedNodeId.value)
        ? selectedNodeId.value
        : "") ||
      (focusId.value && next.some((node) => node.id === focusId.value) ? focusId.value : "") ||
      next[0].id;
    rovingNodeId.value = preferred;
  },
  { immediate: true },
);

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
  rovingNodeId.value = node.id;
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

function moveRovingFocus(event: KeyboardEvent) {
  if (event.altKey || event.ctrlKey || event.metaKey) return false;
  const forward = event.key === "ArrowRight" || event.key === "ArrowDown";
  const backward = event.key === "ArrowLeft" || event.key === "ArrowUp";
  if (!forward && !backward && event.key !== "Home" && event.key !== "End") return false;

  const current = event.currentTarget as SVGGElement | null;
  const items = current?.parentElement
    ? Array.from(current.parentElement.querySelectorAll<SVGGElement>(".graph-node"))
    : [];
  const currentIndex = current ? items.indexOf(current) : -1;
  if (currentIndex < 0 || !items.length) return false;

  const nextIndex =
    event.key === "Home"
      ? 0
      : event.key === "End"
        ? items.length - 1
        : forward
          ? (currentIndex + 1) % items.length
          : (currentIndex - 1 + items.length) % items.length;
  const next = items[nextIndex];
  const nextId = next.dataset.nodeId || "";
  if (!nextId) return false;

  event.preventDefault();
  event.stopPropagation();
  rovingNodeId.value = nextId;
  hoveredNodeId.value = nextId;
  void nextTick(() => next.focus());
  return true;
}

function onNodeFocus(id: string) {
  rovingNodeId.value = id;
  hoveredNodeId.value = id;
}

function onNodeKeydown(event: KeyboardEvent, node: DrawnNode) {
  draggedNodeId.value = node.id;
  if (nodeDrag.nudge(event, { x: node.x, y: node.y })) {
    draggedNodeId.value = "";
    return;
  }
  draggedNodeId.value = "";
  if (moveRovingFocus(event)) return;
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
  rovingNodeId.value = id;
}
function focusNode(id: string, label: string) {
  if (!id || id === focusId.value) return;
  const at = focusTrail.value.findIndex((item) => item.id === id);
  focusTrail.value =
    at >= 0 ? focusTrail.value.slice(0, at + 1) : [...focusTrail.value, { id, label }].slice(-6);
  focusId.value = id;
  selectedNodeId.value = id;
  rovingNodeId.value = id;
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
function nodeAriaLabel(node: SemanticGraphViewNode) {
  return `${node.label}, ${node.type}, ${i18n.tf("pdf_corpus.semantic_graph_mentions", {
    count: node.mention_count,
    records: node.record_count,
  })}`;
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
</script>

<template>
  <details
    class="semantic-graph-panel"
    :class="{ embedded: props.embedded }"
    :open="props.embedded || undefined"
    @toggle="onToggle"
  >
    <summary v-if="!props.embedded">
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
          {{ loading && !view ? i18n.t("pdf_corpus.semantic_graph_loading") : showingText }}
        </p>
      </div>
      <p v-if="truncated && !focusId" class="graph-banner info">
        {{ i18n.t("pdf_corpus.semantic_graph_truncated_hint") }}
      </p>
      <UiLoadingState
        v-if="loading && !view"
        variant="skeleton"
        :skeleton-count="4"
        :label="i18n.t('pdf_corpus.semantic_graph_loading')"
      />
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
              :style="{ '--map-zoom': viewportState.zoom }"
              :viewBox="`0 0 ${WIDTH} ${HEIGHT}`"
              :width="WIDTH"
              :height="HEIGHT"
            >
              <g class="graph-edges" aria-hidden="true">
                <UiRelationEdge
                  v-for="edge in edges"
                  :key="edge.id"
                  :path="edgePath(edge)"
                  :width="edgeWidth(edge) / viewportState.zoom"
                  :title="`${relationLabel(edge.predicate)} · ${authorityText(edge.authority_status, i18n.t)}`"
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
                  :transform="`translate(${node.x}, ${node.y}) scale(${1 / viewportState.zoom})`"
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
                  :data-node-id="node.id"
                  :tabindex="node.id === rovingNodeId ? 0 : -1"
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
                  @focus="onNodeFocus(node.id)"
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

        <SemanticGraphInspector
          :selected-node="selectedNode"
          :focus-detail="focusDetail"
          :selected-edges="selectedEdges"
          :nodes-by-id="nodesById"
          :focus-id="focusId"
          :hue-class="hueClass"
          @clear="selectedNodeId = ''"
          @focus="focusNode"
          @select="selectNode"
        />
      </div>

      <!-- Paged entity index: the accessible, complete route to every entity -->
      <SemanticGraphEntityIndex
        v-if="view"
        v-model:sort="indexSort"
        v-model:offset="indexOffset"
        :index="view.index"
        :node-total="view.summary.nodes || 0"
        :loading="loading"
        :selected-node-id="selectedNodeId"
        :hue-class="hueClass"
        @focus="focusNode"
      />

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
.semantic-graph-panel.embedded {
  border: 0;
  border-radius: 0;
  background: transparent;
}
.semantic-graph-panel.embedded .semantic-graph-body {
  padding: 0;
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
  stroke-dasharray: calc(4px / var(--map-zoom, 1)) calc(4px / var(--map-zoom, 1));
  opacity: 0.35;
}
.graph-edge.disputed {
  stroke: var(--tone-danger-border);
  stroke-dasharray: calc(1px / var(--map-zoom, 1)) calc(3px / var(--map-zoom, 1));
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
