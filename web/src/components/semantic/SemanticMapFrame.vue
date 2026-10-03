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
import { computed, nextTick, ref } from "vue";
import { useRoute } from "vue-router";
import { useI18nStore } from "../../stores/i18n";
import { useSemanticMapStore } from "../../stores/semanticMap";
import {
  SEMANTIC_MAP_PLACEMENTS,
  buildSemanticMap,
  type SemanticMapGraph,
  type SemanticMapKind,
  type SemanticMapNode,
  type SemanticMapPlacement,
  type SemanticMapSource,
} from "../../domain/semanticMap";
import * as runtime from "../../runtime/runtime.js";
import { navigateTo } from "../../domain/sharedNavigation";
import UiRelationToolbar from "../relations/UiRelationToolbar.vue";
import UiRelationDensityControls, {
  type RelationDensity,
} from "../relations/UiRelationDensityControls.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import SemanticMapCanvas from "./SemanticMapCanvas.vue";

const props = withDefaults(
  defineProps<{
    variant: SemanticMapPlacement;
    sources?: SemanticMapSource[];
    focusId?: string;
    showClose?: boolean;
  }>(),
  { sources: () => [], focusId: "", showClose: true },
);
const emit = defineEmits<{ activate: [node: SemanticMapNode] }>();

const i18n = useI18nStore();
const map = useSemanticMapStore();
const route = useRoute();
const canvas = ref<InstanceType<typeof SemanticMapCanvas> | null>(null);
const density = ref<RelationDensity>("compact");
const query = ref("");
const selectedId = ref("");
const focusOnly = ref(false);
const kinds: SemanticMapKind[] = ["concept", "topic", "person", "record"];
const kindEnabled = ref<Record<SemanticMapKind, boolean>>({
  concept: true,
  topic: true,
  person: true,
  record: true,
});

const graph = computed(() => buildSemanticMap(props.sources, props.focusId));

const kindCounts = computed<Record<SemanticMapKind, number>>(() => {
  const counts: Record<SemanticMapKind, number> = { concept: 0, topic: 0, person: 0, record: 0 };
  graph.value.nodes.forEach((node) => {
    counts[node.kind] += 1;
  });
  return counts;
});

function neighborhoodIds(source: SemanticMapGraph, seeds: ReadonlySet<string>) {
  const ids = new Set(seeds);
  for (const edge of source.edges) {
    if (seeds.has(edge.source)) ids.add(edge.target);
    if (seeds.has(edge.target)) ids.add(edge.source);
  }
  return ids;
}

const filteredGraph = computed<SemanticMapGraph>(() => {
  const source = graph.value;
  let allowed = new Set(
    source.nodes.filter((node) => kindEnabled.value[node.kind]).map((node) => node.id),
  );

  const needle = query.value.trim().toLocaleLowerCase();
  if (needle) {
    const matches = new Set(
      source.nodes
        .filter(
          (node) => kindEnabled.value[node.kind] && node.label.toLocaleLowerCase().includes(needle),
        )
        .map((node) => node.id),
    );
    const contextual = neighborhoodIds(source, matches);
    allowed = new Set([...allowed].filter((id) => contextual.has(id)));
  }

  if (focusOnly.value && selectedId.value) {
    const focus = neighborhoodIds(source, new Set([selectedId.value]));
    allowed = new Set([...allowed].filter((id) => focus.has(id)));
  }

  const nodes = source.nodes.filter((node) => allowed.has(node.id));
  const edges = source.edges.filter((edge) => allowed.has(edge.source) && allowed.has(edge.target));
  return { nodes, edges };
});

const selectedNode = computed(
  () => graph.value.nodes.find((node) => node.id === selectedId.value) || null,
);

const selectedNeighbors = computed(() => {
  if (!selectedNode.value) return [];
  const byId = new Map(graph.value.nodes.map((node) => [node.id, node]));
  return graph.value.edges
    .flatMap((edge) => {
      if (edge.source === selectedNode.value?.id) {
        const node = byId.get(edge.target);
        return node ? [{ node, weight: edge.weight }] : [];
      }
      if (edge.target === selectedNode.value?.id) {
        const node = byId.get(edge.source);
        return node ? [{ node, weight: edge.weight }] : [];
      }
      return [];
    })
    .sort(
      (left, right) =>
        right.weight - left.weight || left.node.label.localeCompare(right.node.label),
    );
});

const placementLabel: Record<SemanticMapPlacement, string> = {
  sidebar: "Sidebar",
  record: "Above the record",
  modal: "Large dialog",
  page: "Dedicated view",
};

function choose(next: SemanticMapPlacement) {
  map.setPlacement(next);
  if (next === "page") {
    if (route.name !== "semanticmap") navigateTo("semanticmap");
    return;
  }
  if (route.name === "semanticmap") navigateTo("record");
}

function kindLabel(kind: SemanticMapKind) {
  return i18n.t(`semantic_map.kind.${kind}`, kind);
}

function chooseDensity(next: RelationDensity) {
  density.value = next;
  void nextTick(() => canvas.value?.fitView());
}

function toggleKind(kind: SemanticMapKind) {
  kindEnabled.value = { ...kindEnabled.value, [kind]: !kindEnabled.value[kind] };
  if (selectedNode.value?.kind === kind && !kindEnabled.value[kind]) {
    selectedId.value = "";
    focusOnly.value = false;
  }
}

function activate(node: SemanticMapNode) {
  selectedId.value = node.id;
  emit("activate", node);
}

function clearSelection() {
  selectedId.value = "";
  focusOnly.value = false;
}

function focusSelection() {
  if (!selectedNode.value) return;
  focusOnly.value = true;
  void nextTick(() => canvas.value?.fitView());
}

function showAllRelationships() {
  focusOnly.value = false;
  void nextTick(() => canvas.value?.fitView());
}

function selectAndCenter(node: SemanticMapNode) {
  selectedId.value = node.id;
  void nextTick(() => canvas.value?.centerNode(node.id));
}

function openSelectedRecord() {
  if (selectedNode.value?.kind !== "record") return;
  const recordId = selectedNode.value.id.slice("record:".length);
  if (recordId) runtime.openSemanticRecord?.(recordId);
}

function clearSearch() {
  query.value = "";
  void nextTick(() => canvas.value?.fitView());
}
</script>

<template>
  <section
    class="semantic-map-frame"
    :class="`variant-${variant}`"
    :aria-label="i18n.t('semantic_map.title', 'Semantic map')"
  >
    <header class="semantic-map-toolbar">
      <div class="semantic-map-title-block">
        <h2 class="semantic-map-heading">
          {{ i18n.t("semantic_map.title", "Semantic map") }}
          <UiTooltip
            :text="
              i18n.t(
                'semantic_map.cooccurrence_help',
                'A derived view of terms and Records that occur together. Spatial proximity is exploratory, not an authoritative scholarly assertion.',
              )
            "
            placement="bottom"
          />
        </h2>
        <p>
          {{
            i18n.tf("semantic_map.count", "{count} terms", {
              count: filteredGraph.nodes.length,
            })
          }}
          <span v-if="filteredGraph.nodes.length !== graph.nodes.length">
            / {{ graph.nodes.length }}
          </span>
        </p>
      </div>

      <div class="semantic-map-toolbar-actions">
        <UiRelationToolbar
          :accessible-label="i18n.t('semantic_map.zoom', 'Map controls')"
          :zoom-out-label="i18n.t('semantic_map.zoom_out', 'Zoom out')"
          :zoom-in-label="i18n.t('semantic_map.zoom_in', 'Zoom in')"
          :fit-label="i18n.t('semantic_map.fit', 'Fit map')"
          :reset-label="i18n.t('semantic_map.reset', 'Reset layout')"
          @zoom-out="canvas?.zoomBy(1 / 1.15)"
          @zoom-in="canvas?.zoomBy(1.15)"
          @fit="canvas?.fitView()"
          @reset="canvas?.resetView()"
        />

        <details class="semantic-map-view-menu">
          <summary>{{ i18n.t("semantic_map.view", "View") }}</summary>
          <div class="semantic-map-view-menu-content">
            <fieldset>
              <legend>{{ i18n.t("semantic_map.spacing", "Map spacing") }}</legend>
              <UiRelationDensityControls
                :model-value="density"
                :accessible-label="i18n.t('semantic_map.spacing', 'Map spacing')"
                :labels="{
                  compact: i18n.t('semantic_map.spacing_compact', 'Compact spacing'),
                  standard: i18n.t('semantic_map.spacing_standard', 'Standard spacing'),
                  wide: i18n.t('semantic_map.spacing_wide', 'Wide spacing'),
                }"
                @update:model-value="chooseDensity"
              />
            </fieldset>
            <fieldset>
              <legend>{{ i18n.t("semantic_map.placement", "Where to show the map") }}</legend>
              <div
                class="semantic-map-placements"
                role="radiogroup"
                :aria-label="i18n.t('semantic_map.placement', 'Where to show the map')"
              >
                <button
                  v-for="item in SEMANTIC_MAP_PLACEMENTS"
                  :key="item"
                  type="button"
                  role="radio"
                  :aria-checked="map.placement === item"
                  :class="{ selected: map.placement === item }"
                  @click="choose(item)"
                >
                  {{ i18n.t(`semantic_map.placement.${item}`, placementLabel[item]) }}
                </button>
              </div>
            </fieldset>
          </div>
        </details>

        <button v-if="showClose" type="button" class="semantic-map-close" @click="map.disable()">
          {{ i18n.t("semantic_map.close", "Close map") }}
        </button>
      </div>
    </header>

    <div class="semantic-map-explore-controls">
      <div class="semantic-map-search">
        <label class="sr-only" :for="`semantic-map-search-${variant}`">
          {{ i18n.t("semantic_map.search", "Find a term or Record") }}
        </label>
        <input
          :id="`semantic-map-search-${variant}`"
          v-model="query"
          type="search"
          :placeholder="i18n.t('semantic_map.search', 'Find a term or Record')"
          @keydown.escape="clearSearch"
        />
        <button v-if="query" type="button" @click="clearSearch">
          {{ i18n.t("common.clear", "Clear") }}
        </button>
      </div>

      <div
        class="semantic-map-kind-filters"
        role="group"
        :aria-label="i18n.t('semantic_map.filter_types', 'Show node types')"
      >
        <button
          v-for="kind in kinds"
          :key="kind"
          type="button"
          :aria-pressed="kindEnabled[kind]"
          :class="{ selected: kindEnabled[kind] }"
          @click="toggleKind(kind)"
        >
          {{ kindLabel(kind) }}
          <span aria-hidden="true">{{ kindCounts[kind] }}</span>
        </button>
      </div>

      <button
        v-if="selectedNode && !focusOnly"
        type="button"
        class="semantic-map-focus-action"
        @click="focusSelection"
      >
        {{ i18n.t("semantic_map.focus_selection", "Focus on selection") }}
      </button>
      <button
        v-if="focusOnly"
        type="button"
        class="semantic-map-focus-action"
        @click="showAllRelationships"
      >
        {{ i18n.t("semantic_map.show_all", "Show all") }}
      </button>
    </div>

    <details class="semantic-map-about">
      <summary>{{ i18n.t("semantic_map.about", "About this map") }}</summary>
      <p>
        {{
          i18n.t(
            "semantic_map.signal_caveat",
            "This is a derived co-occurrence view. Node placement, distance, and line strength help exploration but do not themselves establish an authoritative semantic relation.",
          )
        }}
      </p>
    </details>

    <div class="semantic-map-workspace" :class="{ 'has-selection': selectedNode }">
      <SemanticMapCanvas
        ref="canvas"
        :graph="filteredGraph"
        :density="density"
        :selected-id="selectedId"
        @activate="activate"
      />

      <aside
        v-if="selectedNode"
        class="semantic-map-inspector"
        :aria-label="i18n.t('semantic_map.inspector', 'Selection details')"
      >
        <div class="semantic-map-inspector-heading">
          <div>
            <span class="semantic-map-kind">{{ kindLabel(selectedNode.kind) }}</span>
            <h3>{{ selectedNode.label }}</h3>
          </div>
          <button
            type="button"
            class="semantic-map-inspector-close"
            :aria-label="i18n.t('semantic_map.clear_selection', 'Clear selection')"
            @click="clearSelection"
          >
            ×
          </button>
        </div>

        <dl class="semantic-map-inspector-stats">
          <div>
            <dt>{{ i18n.t("semantic_map.occurrences", "Occurrences") }}</dt>
            <dd>{{ selectedNode.weight }}</dd>
          </div>
          <div>
            <dt>{{ i18n.t("semantic_map.connections", "Connections") }}</dt>
            <dd>{{ selectedNeighbors.length }}</dd>
          </div>
        </dl>

        <button
          v-if="selectedNode.kind === 'record'"
          type="button"
          class="semantic-map-open-record"
          @click="openSelectedRecord"
        >
          {{ i18n.t("semantic_map.open_record", "Open Record") }}
        </button>

        <div v-if="selectedNeighbors.length" class="semantic-map-neighbors">
          <h4>{{ i18n.t("semantic_map.connected", "Connected nodes") }}</h4>
          <ul>
            <li v-for="item in selectedNeighbors" :key="item.node.id">
              <button type="button" @click="selectAndCenter(item.node)">
                <span>{{ item.node.label }}</span>
                <small>{{ kindLabel(item.node.kind) }} · {{ item.weight }}</small>
              </button>
            </li>
          </ul>
        </div>
      </aside>
    </div>

    <details v-if="filteredGraph.nodes.length" class="semantic-map-index">
      <summary>
        {{ i18n.t("semantic_map.node_list", "Terms on this map") }}
        ({{ filteredGraph.nodes.length }})
      </summary>
      <ul>
        <li v-for="node in filteredGraph.nodes" :key="node.id">
          <button
            type="button"
            :aria-current="node.id === selectedId ? 'true' : undefined"
            @click="selectAndCenter(node)"
          >
            <span>{{ kindLabel(node.kind) }}</span> {{ node.label }}
          </button>
        </li>
      </ul>
    </details>
  </section>
</template>

<style scoped>
.semantic-map-frame {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  height: 100%;
  color: var(--text-primary);
}
.semantic-map-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.semantic-map-title-block {
  min-width: 0;
}
.semantic-map-toolbar h2 {
  margin: 0;
  font-size: 1rem;
  line-height: 1.3;
}
.semantic-map-heading {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.semantic-map-toolbar p {
  margin: 2px 0 0;
  color: var(--text-tertiary);
  font-size: 12px;
}
.semantic-map-toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.semantic-map-frame button,
.semantic-map-view-menu summary {
  min-height: 34px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  color: var(--text-primary);
  padding: 4px 8px;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}
.semantic-map-frame button:focus-visible,
.semantic-map-view-menu summary:focus-visible,
.semantic-map-about summary:focus-visible,
.semantic-map-index summary:focus-visible,
.semantic-map-search input:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.semantic-map-view-menu {
  position: relative;
}
.semantic-map-view-menu > summary {
  display: flex;
  align-items: center;
  list-style: none;
}
.semantic-map-view-menu > summary::-webkit-details-marker {
  display: none;
}
.semantic-map-view-menu-content {
  position: absolute;
  z-index: 20;
  inset-block-start: calc(100% + 6px);
  inset-inline-end: 0;
  width: min(360px, 88vw);
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  box-shadow: var(--shadow-overlay);
}
.semantic-map-view-menu fieldset {
  margin: 0;
  padding: 0;
  border: 0;
}
.semantic-map-view-menu fieldset + fieldset {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}
.semantic-map-view-menu legend {
  margin-bottom: 6px;
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 700;
}
.semantic-map-placements {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.semantic-map-placements button.selected,
.semantic-map-kind-filters button.selected {
  background: var(--surface-selected);
  border-color: var(--border-interactive);
}
.semantic-map-explore-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.semantic-map-search {
  display: flex;
  min-width: min(280px, 100%);
  flex: 1 1 280px;
}
.semantic-map-search input {
  width: 100%;
  min-height: 36px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  color: var(--text-primary);
  padding: 6px 10px;
  font: inherit;
  font-size: 0.8125rem;
}
.semantic-map-search button {
  margin-inline-start: 6px;
}
.semantic-map-kind-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.semantic-map-kind-filters button {
  color: var(--text-secondary);
}
.semantic-map-kind-filters button.selected {
  color: var(--text-primary);
}
.semantic-map-kind-filters span {
  margin-inline-start: 4px;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}
.semantic-map-focus-action {
  white-space: nowrap;
}
.semantic-map-about {
  color: var(--text-secondary);
  font-size: 12px;
}
.semantic-map-about summary,
.semantic-map-index summary {
  width: fit-content;
  cursor: pointer;
  color: var(--text-secondary);
}
.semantic-map-about p {
  max-width: 78ch;
  margin: 6px 0 0;
  padding: 8px 10px;
  border-inline-start: 3px solid var(--border-interactive);
  background: var(--surface-inset);
  line-height: 1.45;
}
.semantic-map-workspace {
  display: grid;
  min-height: 0;
  flex: 1;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
}
.semantic-map-workspace.has-selection {
  grid-template-columns: minmax(0, 1fr) minmax(240px, 300px);
}
.semantic-map-inspector {
  min-width: 0;
  overflow: auto;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.semantic-map-inspector-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.semantic-map-inspector-heading h3 {
  margin: 3px 0 0;
  font-size: 0.95rem;
  overflow-wrap: anywhere;
}
.semantic-map-kind {
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 750;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.semantic-map-inspector-close {
  min-width: 34px;
  padding: 0;
  font-size: 1rem;
}
.semantic-map-inspector-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin: 12px 0;
}
.semantic-map-inspector-stats div {
  padding: 8px;
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.semantic-map-inspector-stats dt {
  color: var(--text-tertiary);
  font-size: 0.75rem;
}
.semantic-map-inspector-stats dd {
  margin: 2px 0 0;
  font-size: 0.95rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.semantic-map-open-record {
  width: 100%;
  border-color: var(--border-interactive) !important;
}
.semantic-map-neighbors {
  margin-top: 14px;
}
.semantic-map-neighbors h4 {
  margin: 0 0 6px;
  font-size: 0.75rem;
}
.semantic-map-neighbors ul,
.semantic-map-index ul {
  margin: 0;
  padding: 0;
  list-style: none;
}
.semantic-map-neighbors ul {
  display: grid;
  gap: 4px;
  max-height: 320px;
  overflow: auto;
}
.semantic-map-neighbors button {
  display: flex;
  width: 100%;
  height: auto;
  min-height: 40px;
  flex-direction: column;
  align-items: flex-start;
  text-align: start;
}
.semantic-map-neighbors small {
  margin-top: 2px;
  color: var(--text-tertiary);
}
.variant-record .semantic-map-workspace {
  min-height: 280px;
}
.variant-record :deep(.semantic-map-canvas) {
  min-height: 280px;
}
.variant-sidebar .semantic-map-workspace {
  min-height: 280px;
}
.variant-sidebar :deep(.semantic-map-canvas) {
  min-height: 280px;
}
.variant-modal .semantic-map-workspace,
.variant-page .semantic-map-workspace {
  min-height: 420px;
}
.variant-modal :deep(.semantic-map-canvas),
.variant-page :deep(.semantic-map-canvas) {
  min-height: 420px;
}
.semantic-map-index {
  font-size: 12px;
}
.semantic-map-index ul {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  max-height: 120px;
  overflow: auto;
}
.semantic-map-index button {
  min-height: 30px;
}
.semantic-map-index button[aria-current="true"] {
  border-color: var(--border-interactive);
  background: var(--surface-selected);
}
.semantic-map-index span {
  color: var(--text-tertiary);
}
@media (max-width: 900px) {
  .semantic-map-workspace.has-selection {
    grid-template-columns: minmax(0, 1fr);
  }
  .semantic-map-inspector {
    max-height: 280px;
  }
}
@media (forced-colors: active) {
  .semantic-map-view-menu-content,
  .semantic-map-inspector {
    border-color: CanvasText;
  }
}
</style>
