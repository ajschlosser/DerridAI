<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { useI18nStore } from "../../stores/i18n";
import { useSemanticMapStore } from "../../stores/semanticMap";
import {
  SEMANTIC_MAP_PLACEMENTS,
  buildSemanticMap,
  type SemanticMapPlacement,
  type SemanticMapSource,
} from "../../domain/semanticMap";
import * as runtime from "../../runtime/runtime.js";
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

const i18n = useI18nStore();
const map = useSemanticMapStore();
const route = useRoute();
const canvas = ref<InstanceType<typeof SemanticMapCanvas> | null>(null);

const graph = computed(() => buildSemanticMap(props.sources, props.focusId));
const placementLabel: Record<SemanticMapPlacement, string> = {
  sidebar: "Sidebar",
  record: "Above the record",
  modal: "Large dialog",
  page: "Dedicated view",
};

function choose(next: SemanticMapPlacement) {
  map.setPlacement(next);
  if (next === "page") {
    if (route.name !== "semanticmap") runtime.navigateView("semanticmap");
    return;
  }
  if (route.name === "semanticmap") runtime.navigateView("record");
}

function kindLabel(kind: string) {
  return i18n.t(`semantic_map.kind.${kind}`, kind);
}
</script>

<template>
  <section
    class="semantic-map-frame"
    :class="`variant-${variant}`"
    :aria-label="i18n.t('semantic_map.title', 'Semantic map')"
  >
    <header class="semantic-map-toolbar">
      <div>
        <h2>{{ i18n.t("semantic_map.title", "Semantic map") }}</h2>
        <p>
          {{
            i18n.tf("semantic_map.count", "{count} terms", { count: graph.nodes.length })
          }}
        </p>
      </div>
      <div class="semantic-map-toolbar-actions">
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
        <div class="semantic-map-zoom" role="group" :aria-label="i18n.t('semantic_map.zoom', 'Zoom')">
          <button type="button" @click="canvas?.zoomBy(1 / 1.15)">
            {{ i18n.t("semantic_map.zoom_out", "Zoom out") }}
          </button>
          <button type="button" @click="canvas?.zoomBy(1.15)">
            {{ i18n.t("semantic_map.zoom_in", "Zoom in") }}
          </button>
          <button type="button" @click="canvas?.resetView()">
            {{ i18n.t("semantic_map.reset", "Reset view") }}
          </button>
        </div>
        <button v-if="showClose" type="button" class="semantic-map-close" @click="map.disable()">
          {{ i18n.t("semantic_map.close", "Close map") }}
        </button>
      </div>
    </header>
    <SemanticMapCanvas ref="canvas" :graph="graph" />
    <details v-if="graph.nodes.length" class="semantic-map-index">
      <summary>{{ i18n.t("semantic_map.node_list", "Terms on this map") }}</summary>
      <ul>
        <li v-for="node in graph.nodes" :key="node.id">
          <span>{{ kindLabel(node.kind) }}</span> {{ node.label }}
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
.semantic-map-toolbar h2 {
  margin: 0;
  font-size: 1rem;
  line-height: 1.3;
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
.semantic-map-placements,
.semantic-map-zoom {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.semantic-map-frame button {
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
.semantic-map-placements button.selected {
  background: var(--surface-selected);
  border-color: var(--border-interactive);
}
.semantic-map-frame button:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-interactive);
  outline-offset: var(--focus-ring-offset);
}
.variant-record :deep(.semantic-map-canvas) {
  height: 280px;
}
.variant-sidebar :deep(.semantic-map-canvas) {
  flex: 1;
  min-height: 280px;
}
.variant-modal :deep(.semantic-map-canvas),
.variant-page :deep(.semantic-map-canvas) {
  flex: 1;
  min-height: 420px;
}
.semantic-map-index {
  font-size: 12px;
}
.semantic-map-index summary {
  cursor: pointer;
}
.semantic-map-index ul {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  max-height: 120px;
  overflow: auto;
}
.semantic-map-index span {
  color: var(--text-tertiary);
}
</style>
