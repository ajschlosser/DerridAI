<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  corpusBuildsApi,
  type DocumentIntelligenceRun,
  type SemanticContentGraph,
  type SemanticContentGraphEdge,
  type SemanticContentGraphNode,
} from "../../api/corpus";
import { readDocumentIntelligence } from "../../features/corpus-builder/api/documentIntelligenceReads";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{
  buildId: string;
  summary?: SemanticContentGraph["summary"] | null;
  disabled?: boolean;
}>();
const emit = defineEmits<{ refreshed: [] }>();
const i18n = useI18nStore();

const graph = ref<SemanticContentGraph | null>(null);
const intelligence = ref<DocumentIntelligenceRun | null>(null);
const loading = ref(false);
const rerunning = ref(false);
const error = ref("");
const selectedType = ref("all");
const entityQuery = ref("");
const selectedNodeId = ref("");

const nodeTypes = computed(() => {
  const values = new Set((graph.value?.nodes || []).map((node) => node.type).filter(Boolean));
  return Array.from(values).sort();
});

const filteredNodes = computed(() => {
  const query = entityQuery.value.trim().toLocaleLowerCase();
  return (graph.value?.nodes || []).filter((node) => {
    if (selectedType.value !== "all" && node.type !== selectedType.value) return false;
    if (!query) return true;
    return [node.label, ...(node.aliases || [])].some((value) =>
      String(value || "")
        .toLocaleLowerCase()
        .includes(query),
    );
  });
});
const visibleNodes = computed(() => filteredNodes.value.slice(0, 36));

const visibleNodeIds = computed(() => new Set(visibleNodes.value.map((node) => node.id)));
const visibleEdges = computed(() =>
  (graph.value?.edges || [])
    .filter(
      (edge) => visibleNodeIds.value.has(edge.source) && visibleNodeIds.value.has(edge.target),
    )
    .slice(0, 90),
);

type PositionedNode = SemanticContentGraphNode & { x: number; y: number };
const positionedNodes = computed<PositionedNode[]>(() => {
  const byType = new Map<string, SemanticContentGraphNode[]>();
  for (const node of visibleNodes.value) {
    const bucket = byType.get(node.type) || [];
    bucket.push(node);
    byType.set(node.type, bucket);
  }
  const groups = Array.from(byType.entries());
  const width = 760;
  return groups.flatMap(([type, nodes], column) => {
    const x = groups.length <= 1 ? 450 : 70 + (column * width) / Math.max(1, groups.length - 1);
    const height = 330;
    return nodes.map((node, row) => ({
      ...node,
      x,
      y: nodes.length <= 1 ? 215 : 50 + (row * height) / Math.max(1, nodes.length - 1),
      type,
    }));
  });
});
const positions = computed(() => new Map(positionedNodes.value.map((node) => [node.id, node])));

const selectedNode = computed(
  () => graph.value?.nodes.find((node) => node.id === selectedNodeId.value) || null,
);
const selectedRelations = computed(() => {
  if (!selectedNodeId.value) return [];
  return (graph.value?.edges || [])
    .filter((edge) => edge.source === selectedNodeId.value || edge.target === selectedNodeId.value)
    .slice(0, 16);
});

function relationLabel(edge: SemanticContentGraphEdge) {
  return String(edge.predicate || "").replaceAll("_", " ");
}

function featureText(values?: Array<{ label: string; count?: number }>) {
  return (values || [])
    .slice(0, 8)
    .map((item) => (Number(item.count || 0) > 1 ? `${item.label} ×${item.count}` : item.label))
    .join(" · ");
}

function observationVerbs(edge: SemanticContentGraphEdge) {
  return Array.from(
    new Set(
      (edge.observations || []).map((item) => String(item.verb || "").trim()).filter(Boolean),
    ),
  )
    .slice(0, 8)
    .join(" · ");
}

async function load() {
  if (!props.buildId || loading.value) return;
  loading.value = true;
  error.value = "";
  try {
    const [nextGraph, nextIntelligence] = await Promise.all([
      corpusBuildsApi.semanticContentGraph(props.buildId),
      readDocumentIntelligence(props.buildId).catch(() => null),
    ]);
    graph.value = nextGraph;
    intelligence.value = nextIntelligence;
    if (selectedNodeId.value && !nextGraph.nodes.some((node) => node.id === selectedNodeId.value))
      selectedNodeId.value = "";
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

async function rerun() {
  if (!props.buildId || rerunning.value) return;
  rerunning.value = true;
  error.value = "";
  try {
    const result = await corpusBuildsApi.rerunDocumentIntelligence(props.buildId);
    intelligence.value = result.document_intelligence;
    graph.value = result.semantic_content_graph;
    emit("refreshed");
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    rerunning.value = false;
  }
}

function onToggle(event: Event) {
  if ((event.currentTarget as HTMLDetailsElement).open && !graph.value) void load();
}

watch(
  () => props.buildId,
  () => {
    graph.value = null;
    intelligence.value = null;
    selectedNodeId.value = "";
    selectedType.value = "all";
    entityQuery.value = "";
  },
);
</script>

<template>
  <details class="semantic-graph-panel" @toggle="onToggle">
    <summary>
      <span>
        <b>{{ i18n.t("pdf_corpus.semantic_graph_title") }}</b>
        <small>{{
          i18n.tf("pdf_corpus.semantic_graph_summary", {
            nodes: props.summary?.nodes || 0,
            edges: props.summary?.edges || 0,
          })
        }}</small>
      </span>
    </summary>
    <div class="semantic-graph-body">
      <div class="semantic-graph-heading">
        <div>
          <h3>{{ i18n.t("pdf_corpus.semantic_graph_heading") }}</h3>
          <p>{{ i18n.t("pdf_corpus.semantic_graph_help") }}</p>
        </div>
        <div class="semantic-graph-actions">
          <label for="semantic-graph-search">
            <span>{{ i18n.t("pdf_corpus.semantic_graph_search") }}</span>
            <input
              id="semantic-graph-search"
              v-model="entityQuery"
              class="control"
              type="search"
              :placeholder="i18n.t('pdf_corpus.semantic_graph_search_placeholder')"
            />
          </label>
          <label for="semantic-graph-type-filter">
            <span>{{ i18n.t("pdf_corpus.semantic_graph_filter") }}</span>
            <select id="semantic-graph-type-filter" v-model="selectedType" class="control">
              <option value="all">{{ i18n.t("pdf_corpus.semantic_graph_all_types") }}</option>
              <option v-for="type in nodeTypes" :key="type" :value="type">
                {{ type }}
              </option>
            </select>
          </label>
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
        </div>
      </div>

      <p v-if="intelligence?.stale" class="graph-status warning" role="status">
        {{ i18n.t("pdf_corpus.document_intelligence_stale") }}
      </p>
      <p v-if="loading" class="graph-status" role="status">
        {{ i18n.t("ui.loading") }}
      </p>
      <p v-else-if="error" class="graph-status error" role="alert">{{ error }}</p>
      <p v-else-if="graph && !graph.nodes.length" class="graph-status">
        {{ i18n.t("pdf_corpus.semantic_graph_empty") }}
      </p>

      <div v-if="graph?.nodes.length" class="graph-layout">
        <div class="graph-canvas-wrap">
          <svg
            class="graph-canvas"
            viewBox="0 0 900 430"
            role="img"
            :aria-label="i18n.t('pdf_corpus.semantic_graph_accessible_label')"
          >
            <g class="graph-edges" aria-hidden="true">
              <line
                v-for="edge in visibleEdges"
                :key="edge.id"
                :x1="positions.get(edge.source)?.x"
                :y1="positions.get(edge.source)?.y"
                :x2="positions.get(edge.target)?.x"
                :y2="positions.get(edge.target)?.y"
                :class="['graph-edge', edge.relation_kind]"
              >
                <title>{{ relationLabel(edge) }}</title>
              </line>
            </g>
            <g
              v-for="node in positionedNodes"
              :key="node.id"
              :transform="`translate(${node.x}, ${node.y})`"
              :class="['graph-node', { selected: node.id === selectedNodeId }]"
              role="button"
              tabindex="0"
              :aria-label="`${node.label}, ${node.type}`"
              @click="selectedNodeId = node.id"
              @keydown.enter.prevent="selectedNodeId = node.id"
              @keydown.space.prevent="selectedNodeId = node.id"
            >
              <circle r="8" />
              <text x="13" y="4">{{ node.label.slice(0, 28) }}</text>
            </g>
          </svg>
          <div class="graph-legend" aria-hidden="true">
            <span
              ><i class="legend-line semantic" />{{
                i18n.t("pdf_corpus.semantic_graph_semantic")
              }}</span
            >
            <span
              ><i class="legend-line observational" />{{
                i18n.t("pdf_corpus.semantic_graph_observational")
              }}</span
            >
          </div>
        </div>

        <aside class="graph-inspector" :aria-label="i18n.t('pdf_corpus.semantic_graph_inspector')">
          <template v-if="selectedNode">
            <p class="graph-node-kind">{{ selectedNode.type }}</p>
            <h4>{{ selectedNode.label }}</h4>
            <p v-if="selectedNode.aliases?.length" class="graph-aliases">
              {{ selectedNode.aliases.join(" · ") }}
            </p>
            <p>
              {{
                i18n.tf("pdf_corpus.semantic_graph_mentions", {
                  count: selectedNode.mention_count || 0,
                  records: selectedNode.record_ids?.length || 0,
                })
              }}
            </p>
            <div
              v-if="selectedNode.character_profile"
              class="character-profile"
              :aria-label="i18n.t('pdf_corpus.semantic_graph_character_profile')"
            >
              <h5>{{ i18n.t("pdf_corpus.semantic_graph_character_profile") }}</h5>
              <dl>
                <template v-if="selectedNode.character_profile.actions_as_agent?.length">
                  <dt>{{ i18n.t("pdf_corpus.semantic_graph_actions_agent") }}</dt>
                  <dd>{{ featureText(selectedNode.character_profile.actions_as_agent) }}</dd>
                </template>
                <template v-if="selectedNode.character_profile.actions_as_patient?.length">
                  <dt>{{ i18n.t("pdf_corpus.semantic_graph_actions_patient") }}</dt>
                  <dd>{{ featureText(selectedNode.character_profile.actions_as_patient) }}</dd>
                </template>
                <template v-if="selectedNode.character_profile.possessions?.length">
                  <dt>{{ i18n.t("pdf_corpus.semantic_graph_possessions") }}</dt>
                  <dd>{{ featureText(selectedNode.character_profile.possessions) }}</dd>
                </template>
                <template v-if="selectedNode.character_profile.modifiers?.length">
                  <dt>{{ i18n.t("pdf_corpus.semantic_graph_modifiers") }}</dt>
                  <dd>{{ featureText(selectedNode.character_profile.modifiers) }}</dd>
                </template>
              </dl>
              <small>{{ i18n.t("pdf_corpus.semantic_graph_character_profile_note") }}</small>
            </div>
            <ul v-if="selectedRelations.length" class="relation-list">
              <li v-for="edge in selectedRelations" :key="edge.id">
                <b>{{ relationLabel(edge) }}</b>
                <span>
                  {{
                    graph.nodes.find(
                      (node) =>
                        node.id === (edge.source === selectedNode?.id ? edge.target : edge.source),
                    )?.label || ""
                  }}
                </span>
                <small>{{
                  edge.relation_kind === "semantic"
                    ? i18n.t("pdf_corpus.semantic_graph_semantic")
                    : i18n.t("pdf_corpus.semantic_graph_observational")
                }}</small>
                <small v-if="observationVerbs(edge)" class="relation-observation">
                  {{
                    i18n.tf("pdf_corpus.semantic_graph_observed_verbs", {
                      verbs: observationVerbs(edge),
                    })
                  }}
                </small>
              </li>
            </ul>
          </template>
          <p v-else>{{ i18n.t("pdf_corpus.semantic_graph_select_node") }}</p>
        </aside>
      </div>

      <section
        v-if="graph?.nodes.length"
        class="entity-index"
        aria-labelledby="semantic-graph-entity-index-title"
      >
        <div class="entity-index-heading">
          <div>
            <h4 id="semantic-graph-entity-index-title">
              {{ i18n.t("pdf_corpus.semantic_graph_entity_index") }}
            </h4>
            <p>
              {{
                i18n.tf("pdf_corpus.semantic_graph_entity_index_count", {
                  shown: filteredNodes.length,
                  total: graph.nodes.length,
                })
              }}
            </p>
          </div>
        </div>
        <div class="entity-index-table-wrap">
          <table class="entity-index-table">
            <thead>
              <tr>
                <th scope="col">{{ i18n.t("pdf_corpus.semantic_graph_entity") }}</th>
                <th scope="col">{{ i18n.t("pdf_corpus.semantic_graph_type") }}</th>
                <th scope="col">{{ i18n.t("pdf_corpus.semantic_graph_mentions_short") }}</th>
                <th scope="col">{{ i18n.t("pdf_corpus.semantic_graph_records_short") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="node in filteredNodes" :key="node.id">
                <td>
                  <button type="button" class="entity-link" @click="selectedNodeId = node.id">
                    {{ node.label }}
                  </button>
                  <small v-if="node.aliases?.length">{{ node.aliases.join(" · ") }}</small>
                </td>
                <td>{{ node.type }}</td>
                <td>{{ node.mention_count || 0 }}</td>
                <td>{{ node.record_ids?.length || 0 }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <p v-if="graph?.epistemic_note" class="graph-epistemic-note">
        {{ graph.epistemic_note }}
      </p>
    </div>
  </details>
</template>

<style scoped>
.semantic-graph-panel {
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
.graph-status {
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
  align-items: end;
}
.semantic-graph-heading h3,
.semantic-graph-heading p,
.graph-inspector h4,
.graph-inspector p {
  margin: 0;
}
.semantic-graph-actions {
  display: flex;
  gap: var(--space-2);
  align-items: end;
}
.semantic-graph-actions label {
  display: grid;
  gap: 4px;
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.graph-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 0.3fr);
  gap: var(--space-3);
  min-height: 360px;
}
.graph-canvas-wrap {
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-raised);
  overflow: auto;
}
.graph-canvas {
  display: block;
  width: 100%;
  min-width: 720px;
  min-height: 360px;
}
.graph-edge {
  stroke: var(--border-strong);
  stroke-width: 1.25;
  opacity: 0.65;
}
.graph-edge.observational {
  stroke-dasharray: 5 5;
  opacity: 0.45;
}
.graph-node {
  cursor: pointer;
}
.graph-node circle {
  fill: var(--accent);
  stroke: var(--surface-raised);
  stroke-width: 2;
}
.graph-node text {
  fill: var(--text);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.graph-node:focus {
  outline: none;
}
.graph-node:focus circle,
.graph-node.selected circle {
  stroke: var(--focus-ring);
  stroke-width: 4;
}
.graph-legend {
  display: flex;
  gap: var(--space-3);
  padding: 0 var(--space-3) var(--space-3);
  color: var(--muted);
  font-size: var(--fs-xs);
}
.graph-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.legend-line {
  display: inline-block;
  width: 28px;
  border-top: 2px solid var(--border-strong);
}
.legend-line.observational {
  border-top-style: dashed;
}
.graph-inspector {
  padding: var(--space-3);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-raised);
}
.graph-node-kind {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: var(--fs-xs);
  color: var(--muted);
}
.character-profile {
  display: grid;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--line);
}
.character-profile h5,
.character-profile dl,
.character-profile dd {
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
.character-profile small,
.relation-observation {
  color: var(--muted);
}
.relation-list {
  display: grid;
  gap: var(--space-2);
  margin: var(--space-3) 0 0;
  padding: 0;
  list-style: none;
}
.relation-list li {
  display: grid;
  gap: 2px;
  padding-block: var(--space-2);
  border-top: 1px solid var(--line);
}
.relation-list small {
  color: var(--muted);
}
.entity-index {
  display: grid;
  gap: var(--space-2);
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
  max-height: 360px;
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
.entity-index-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--surface-raised);
  font-weight: var(--fw-semibold);
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
  color: var(--accent);
  font: inherit;
  font-weight: var(--fw-semibold);
  text-align: start;
  cursor: pointer;
}
.entity-link:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.graph-epistemic-note {
  margin: 0;
  font-size: var(--fs-xs);
  line-height: var(--lh-body);
}
.graph-status.warning {
  color: var(--tone-warn-fg);
}
.graph-status.error {
  color: var(--tone-danger-fg);
}
@container (max-width: 820px) {
  .graph-layout {
    grid-template-columns: 1fr;
  }
  .semantic-graph-heading {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
