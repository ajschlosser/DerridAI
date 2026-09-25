<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type {
  DerridaiNormativeModel,
  ResearchObjectEdge,
  ResearchObjectGraph,
  ResearchObjectNode,
} from "../../types/researchObjectGraph";

const props = withDefaults(
  defineProps<{
    graph?: ResearchObjectGraph | null;
    model?: DerridaiNormativeModel | null;
    loading?: boolean;
    error?: string;
  }>(),
  { graph: null, model: null, loading: false, error: "" },
);
const i18n = useI18nStore();
const mode = ref<"instance" | "model">("instance");
const focusId = ref("");
const history = ref<string[]>([]);
const historyIndex = ref(-1);

const nodes = computed<ResearchObjectNode[]>(() => {
  if (mode.value === "instance") return props.graph?.nodes || [];
  return (props.model?.nodes || []).map((node) => ({
    id: `model:${node.type}`,
    object_type: node.type,
    object_id: node.type,
    label: node.label,
    summary: `${node.profile} · ${node.persistence.replaceAll("_", " ")}`,
    materialization: "derived_view",
    details: { profile: node.profile, persistence: node.persistence, normative: node.normative },
  }));
});

const edges = computed<ResearchObjectEdge[]>(() => {
  if (mode.value === "instance") return props.graph?.edges || [];
  return (props.model?.edges || []).map((edge) => ({
    id: `model:${edge.id}`,
    source: `model:${edge.source_type}`,
    target: `model:${edge.target_type}`,
    relation: edge.relation,
    inverse_relation: edge.inverse_relation,
    normative: edge.normative,
    source_cardinality: edge.source_cardinality,
    target_cardinality: edge.target_cardinality,
    profile: edge.profile,
  }));
});

const nodeMap = computed(() => new Map(nodes.value.map((node) => [node.id, node])));
const focus = computed(() => nodeMap.value.get(focusId.value) || null);
const canBack = computed(() => historyIndex.value > 0);
const canForward = computed(
  () => historyIndex.value >= 0 && historyIndex.value < history.value.length - 1,
);

type GraphNeighbor = {
  edge: ResearchObjectEdge;
  node: ResearchObjectNode;
  relation: string;
  cardinality?: string | null;
  direction: "in" | "out";
};

const neighbors = computed<GraphNeighbor[]>(() => {
  const current = focus.value;
  if (!current) return [];
  const result: GraphNeighbor[] = [];
  for (const edge of edges.value) {
    if (edge.source === current.id) {
      const node = nodeMap.value.get(edge.target);
      if (node) {
        result.push({
          edge,
          node,
          relation: edge.relation,
          cardinality: edge.source_cardinality,
          direction: "out",
        });
      }
    } else if (edge.target === current.id) {
      const node = nodeMap.value.get(edge.source);
      if (node) {
        result.push({
          edge,
          node,
          relation: edge.inverse_relation,
          cardinality: edge.target_cardinality,
          direction: "in",
        });
      }
    }
  }
  return result.sort((a, b) =>
    `${a.relation} ${a.node.label}`.localeCompare(`${b.relation} ${b.node.label}`),
  );
});

const visibleHistory = computed(() =>
  history.value.map((id, index) => ({ id, index, node: nodeMap.value.get(id) })).filter((item) => item.node),
);

function setHistoryRoot(id: string) {
  focusId.value = id;
  history.value = id ? [id] : [];
  historyIndex.value = id ? 0 : -1;
}

function defaultFocus() {
  if (mode.value === "instance") {
    return props.graph?.root_id && nodeMap.value.has(props.graph.root_id)
      ? props.graph.root_id
      : nodes.value[0]?.id || "";
  }
  const instanceType =
    props.graph?.nodes.find((node) => node.id === props.graph?.root_id)?.object_type || "Record";
  const preferred = `model:${instanceType}`;
  return nodeMap.value.has(preferred) ? preferred : nodes.value[0]?.id || "";
}

function reset() {
  setHistoryRoot(defaultFocus());
}

function walk(id: string) {
  if (!nodeMap.value.has(id) || id === focusId.value) return;
  history.value = history.value.slice(0, historyIndex.value + 1);
  history.value.push(id);
  historyIndex.value = history.value.length - 1;
  focusId.value = id;
}

function goBack() {
  if (!canBack.value) return;
  historyIndex.value -= 1;
  focusId.value = history.value[historyIndex.value];
}

function goForward() {
  if (!canForward.value) return;
  historyIndex.value += 1;
  focusId.value = history.value[historyIndex.value];
}

function jump(index: number) {
  if (index < 0 || index >= history.value.length) return;
  historyIndex.value = index;
  focusId.value = history.value[index];
}

function switchMode(next: "instance" | "model") {
  if (mode.value === next) return;
  const priorType = focus.value?.object_type;
  mode.value = next;
  const preferred =
    next === "model" && priorType && nodeMap.value.has(`model:${priorType}`)
      ? `model:${priorType}`
      : defaultFocus();
  setHistoryRoot(preferred);
}

watch(
  () => [props.graph?.root_id, props.graph?.nodes?.length, props.model?.nodes?.length],
  () => {
    if (!focusId.value || !nodeMap.value.has(focusId.value)) reset();
  },
  { immediate: true },
);
</script>

<template>
  <section class="object-graph" aria-labelledby="objectGraphTitle">
    <header class="object-graph-head">
      <div>
        <p>{{ i18n.t("traceability.kicker", "Research object graph") }}</p>
        <h2 id="objectGraphTitle">{{ i18n.t("traceability.title", "Traceability") }}</h2>
      </div>
      <div class="object-graph-modes" :aria-label="i18n.t('traceability.mode', 'Graph mode')">
        <button
          type="button"
          :class="{ active: mode === 'instance' }"
          :aria-pressed="mode === 'instance'"
          @click="switchMode('instance')"
        >
          {{ i18n.t("traceability.instance", "Instance") }}
        </button>
        <button
          type="button"
          :class="{ active: mode === 'model' }"
          :aria-pressed="mode === 'model'"
          :disabled="!model"
          @click="switchMode('model')"
        >
          {{ i18n.t("traceability.model", "Model") }}
        </button>
      </div>
    </header>

    <p class="object-graph-help">
      {{
        i18n.t(
          "traceability.help",
          "Select any connected object to make it the new focus. Your path is history, not a limit on the graph.",
        )
      }}
    </p>

    <div v-if="loading" class="object-graph-state" role="status">
      {{ i18n.t("traceability.loading", "Loading traceability…") }}
    </div>
    <div v-else-if="error" class="object-graph-state error" role="alert">{{ error }}</div>
    <div v-else-if="!focus" class="object-graph-state">
      {{ i18n.t("traceability.empty", "No traceability relationships are available for this object yet.") }}
    </div>

    <template v-else>
      <nav class="object-graph-history" :aria-label="i18n.t('traceability.walk_history', 'Traversal history')">
        <div class="object-graph-history-actions">
          <button type="button" :disabled="!canBack" @click="goBack">
            {{ i18n.t("common.previous", "Previous") }}
          </button>
          <button type="button" :disabled="!canForward" @click="goForward">
            {{ i18n.t("common.next", "Next") }}
          </button>
        </div>
        <ol>
          <li v-for="item in visibleHistory" :key="`${item.index}-${item.id}`">
            <button
              type="button"
              :aria-current="item.index === historyIndex ? 'location' : undefined"
              @click="jump(item.index)"
            >
              {{ item.node?.object_type }}
            </button>
          </li>
        </ol>
      </nav>

      <article class="object-graph-focus" :data-object-id="focus.id">
        <div class="object-graph-focus-type">{{ focus.object_type }}</div>
        <h3>{{ focus.label }}</h3>
        <p v-if="focus.summary">{{ focus.summary }}</p>
        <div class="object-graph-badges">
          <span v-if="focus.materialization">{{ focus.materialization.replaceAll("_", " ") }}</span>
          <span v-if="focus.status">{{ focus.status.replaceAll("_", " ") }}</span>
        </div>
      </article>

      <section class="object-graph-neighbors" aria-labelledby="objectGraphNeighbors">
        <div class="object-graph-section-title">
          <h3 id="objectGraphNeighbors">{{ i18n.t("traceability.connections", "Connections") }}</h3>
          <span>{{ neighbors.length }}</span>
        </div>
        <ul v-if="neighbors.length">
          <li v-for="item in neighbors" :key="item.edge.id">
            <div>
              <small>
                {{ item.relation }}
                <template v-if="item.cardinality"> · {{ item.cardinality }}</template>
              </small>
              <b>{{ item.node.object_type }}</b>
              <span>{{ item.node.label }}</span>
              <em v-if="!item.edge.normative">{{ i18n.t("traceability.application_link", "DerridAI link") }}</em>
            </div>
            <button
              type="button"
              :data-object-id="item.node.id"
              :aria-label="`${i18n.t('traceability.walk_to', 'Walk to')} ${item.node.label}`"
              @click="walk(item.node.id)"
            >
              {{ i18n.t("traceability.open", "Open") }}
            </button>
          </li>
        </ul>
        <p v-else class="object-graph-none">
          {{ i18n.t("traceability.no_connections", "No connected objects are retained from this focus.") }}
        </p>
      </section>
    </template>
  </section>
</template>

<style scoped>
.object-graph {
  display: grid;
  gap: 14px;
  min-width: 0;
}
.object-graph-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.object-graph-head p,
.object-graph-focus-type {
  margin: 0;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.055em;
  text-transform: uppercase;
}
.object-graph-head h2,
.object-graph-focus h3,
.object-graph-section-title h3 {
  margin: 2px 0 0;
  color: var(--text-2);
}
.object-graph-head h2 {
  font-size: 1.0625rem;
}
.object-graph-modes {
  display: flex;
  gap: 3px;
  padding: 3px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
}
.object-graph-modes button,
.object-graph-history button,
.object-graph-neighbors button {
  min-height: 30px;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  color: var(--text-2);
  font: inherit;
  font-size: 0.75rem;
  font-weight: 750;
  cursor: pointer;
}
.object-graph-modes button.active {
  border-color: var(--line);
  background: var(--surface-card);
  box-shadow: var(--shadow-card);
}
.object-graph-modes button:disabled,
.object-graph-history button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.object-graph-help,
.object-graph-none,
.object-graph-state {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.5;
}
.object-graph-state {
  padding: 14px;
  border: 1px dashed var(--line);
  border-radius: var(--radius-control);
}
.object-graph-state.error {
  color: var(--tone-danger-fg);
}
.object-graph-history {
  display: grid;
  gap: 7px;
}
.object-graph-history-actions {
  display: flex;
  gap: 5px;
}
.object-graph-history-actions button {
  border-color: var(--line);
  background: var(--surface-card);
  padding: 0 9px;
}
.object-graph-history ol {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin: 0;
  padding: 0;
  list-style: none;
}
.object-graph-history li:not(:last-child)::after {
  content: "›";
  margin-left: 4px;
  color: var(--muted);
}
.object-graph-history button[aria-current="location"] {
  color: var(--ui-accent);
  text-decoration: underline;
  text-underline-offset: 3px;
}
.object-graph-focus {
  display: grid;
  gap: 5px;
  padding: 13px;
  border: 1px solid var(--line);
  border-radius: var(--radius-card);
  background: var(--surface-raised);
}
.object-graph-focus h3 {
  font-size: 0.9375rem;
  overflow-wrap: anywhere;
}
.object-graph-focus > p {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.object-graph-badges {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}
.object-graph-badges span,
.object-graph-neighbors em {
  width: max-content;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 2px 6px;
  color: var(--muted);
  font-size: 0.6875rem;
  font-style: normal;
  font-weight: 700;
}
.object-graph-neighbors {
  display: grid;
  gap: 8px;
}
.object-graph-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.object-graph-section-title h3 {
  font-size: 0.8125rem;
}
.object-graph-section-title > span {
  min-width: 23px;
  height: 23px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--soft);
  font-size: 0.6875rem;
  font-weight: 800;
}
.object-graph-neighbors ul {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.object-graph-neighbors li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
  padding: 9px 9px 9px 10px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-card);
}
.object-graph-neighbors li > div {
  min-width: 0;
  display: grid;
  gap: 2px;
}
.object-graph-neighbors small,
.object-graph-neighbors span {
  color: var(--muted);
  font-size: 0.75rem;
  overflow-wrap: anywhere;
}
.object-graph-neighbors b {
  color: var(--text-2);
  font-size: 0.75rem;
}
.object-graph-neighbors button {
  border-color: var(--line);
  background: var(--surface-raised);
  padding: 0 9px;
}
button:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ui-accent, #3c8d62) 42%, var(--card));
  outline-offset: 2px;
}
@media (max-width: 520px) {
  .object-graph-head {
    display: grid;
  }
  .object-graph-modes {
    width: max-content;
  }
}
</style>
