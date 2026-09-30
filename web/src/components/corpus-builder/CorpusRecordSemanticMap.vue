<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
/**
 * Semantic map of the Record under review, and a walk through the build's Semantic Content Graph from it.
 *
 * The walk is a trail of steps: a Record step shows that Record's nodes, relations and linked Records; a node step
 * shows the node's relations and the Records it occurs in. Every node, relation and linked Record is a step the
 * reviewer can take, and the trail keeps the way back. Everything shown is derived navigation state: a shared node is
 * not evidence of a shared claim, and POS/NER terms are exact spans, not metadata values.
 */
import { computed, ref, watch } from "vue";
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
  type RecordSemanticMap,
  type RecordSemanticMapNode,
  type SemanticContentGraphEdge,
  type SemanticLayerStatus,
  type SemanticNodeNeighborhood,
} from "../../api/corpus";
import {
  radialLayout,
  segmentText,
  type Point,
} from "../../features/corpus-builder/domain/semanticMap";
import { useI18nStore } from "../../stores/i18n";

type Step = { kind: "record"; id: string } | { kind: "node"; id: string; label: string };

const props = withDefaults(
  defineProps<{
    buildId: string;
    record: { record_id: string; text?: string; record_revision?: number };
    disabled?: boolean;
    idPrefix?: string;
  }>(),
  { disabled: false, idPrefix: "record" },
);
const emit = defineEmits<{ openRecord: [recordId: string]; refreshed: [] }>();
const i18n = useI18nStore();

const surfacePreset = RELATION_SURFACE_PRESETS.semanticRadial;
const MAX_TRAIL = 30;
const MAX_INNER = 24;
const MAX_OUTER = 16;
const SIZE = { width: 820, height: 600 };
const LAYERS = ["entity", "quotation", "ner", "pos"] as const;

const trail = ref<Step[]>([]);
const maps = ref<Record<string, RecordSemanticMap>>({});
const neighborhoods = ref<Record<string, SemanticNodeNeighborhood>>({});
const previews = ref<Record<string, string>>({});
const loading = ref(false);
const rerunning = ref(false);
const error = ref("");
const shownLayers = ref<Set<string>>(new Set(LAYERS));
const includeTerms = ref(false);

const current = computed<Step | null>(() => trail.value[trail.value.length - 1] || null);
const currentMap = computed(() =>
  current.value?.kind === "record" ? maps.value[current.value.id] || null : null,
);
const currentNeighborhood = computed(() =>
  current.value?.kind === "node" ? neighborhoods.value[current.value.id] || null : null,
);
const isOwnRecord = computed(
  () => current.value?.kind === "record" && current.value.id === props.record.record_id,
);

// Responses requested before a reset belong to an older text/graph and are dropped.
let generation = 0;
const inflight = new Set<string>();

function reset() {
  generation += 1;
  inflight.clear();
  trail.value = props.record.record_id ? [{ kind: "record", id: props.record.record_id }] : [];
  maps.value = {};
  neighborhoods.value = {};
  error.value = "";
}

async function load(step: Step | null) {
  if (!step || !props.buildId) return;
  if (step.kind === "record" ? maps.value[step.id] : neighborhoods.value[step.id]) return;
  const key = `${step.kind}:${step.id}`;
  if (inflight.has(key)) return;
  const requested = generation;
  inflight.add(key);
  loading.value = true;
  error.value = "";
  try {
    if (step.kind === "record") {
      const value = await corpusBuildsApi.recordSemanticMap(props.buildId, step.id);
      if (requested !== generation) return;
      maps.value = { ...maps.value, [step.id]: value };
      for (const row of value.linked_records) previews.value[row.record_id] = row.preview;
    } else {
      const value = await corpusBuildsApi.semanticGraphNode(props.buildId, step.id);
      if (requested !== generation) return;
      neighborhoods.value = { ...neighborhoods.value, [step.id]: value };
      for (const row of value.records) previews.value[row.record_id] = row.preview;
    }
  } catch (exc) {
    if (requested === generation) error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    inflight.delete(key);
    if (requested === generation) loading.value = inflight.size > 0;
  }
}

// A different Record, or an edit to this one, can change the graph: start the walk again.
watch(
  () => [props.buildId, props.record.record_id, props.record.text, props.record.record_revision],
  () => {
    reset();
    void load(current.value);
  },
  { immediate: true },
);
watch(current, (step) => void load(step));

function walk(step: Step) {
  const last = current.value;
  if (last && last.kind === step.kind && last.id === step.id) return;
  trail.value = [...trail.value, step].slice(-MAX_TRAIL);
}
function walkToNode(node: { id: string; label: string }) {
  walk({ kind: "node", id: node.id, label: node.label });
}
function walkToMention(nodeId: string, surface: string) {
  if (!nodeId) return;
  const node = currentMap.value?.nodes.find((item) => item.id === nodeId);
  walkToNode({ id: nodeId, label: node?.label || surface });
}
function walkToRecord(recordId: string) {
  walk({ kind: "record", id: recordId });
}
function back() {
  if (trail.value.length > 1) trail.value = trail.value.slice(0, -1);
}
function jump(index: number) {
  trail.value = trail.value.slice(0, index + 1);
}

async function rerun() {
  if (!props.buildId || rerunning.value) return;
  rerunning.value = true;
  error.value = "";
  try {
    await corpusBuildsApi.rerunDocumentIntelligence(props.buildId);
    generation += 1;
    inflight.clear();
    maps.value = {};
    neighborhoods.value = {};
    await load(current.value);
    emit("refreshed");
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    rerunning.value = false;
  }
}

function stepLabel(step: Step) {
  return step.kind === "record"
    ? i18n.tf("pdf_corpus.semantic_map_record_step", { id: step.id })
    : step.label;
}
const LAYER_STATUSES = new Set(["ok", "stale", "missing", "unavailable"]);
const AUTHORITY_STATUSES = new Set(["human_confirmed", "unreviewed", "disputed"]);
function statusLabel(status: SemanticLayerStatus) {
  return LAYER_STATUSES.has(status)
    ? i18n.t(`pdf_corpus.semantic_map_status_${status}`)
    : String(status);
}
function authorityLabel(status?: string) {
  const value = status || "unreviewed";
  return AUTHORITY_STATUSES.has(value)
    ? i18n.t(`pdf_corpus.semantic_map_authority_${value}`)
    : value.replaceAll("_", " ");
}
function relationLabel(edge: SemanticContentGraphEdge) {
  return String(edge.predicate || "").replaceAll("_", " ");
}
function nodeTone(type: string) {
  if (type === "person" || type === "character") return "person";
  if (type === "concept" || type === "topic") return "concept";
  if (type === "work") return "work";
  if (type === "term") return "term";
  return "entity";
}
function shortLabel(value: string) {
  return value.length > 22 ? `${value.slice(0, 21)}…` : value;
}

const layerStatusNeedsRerun = computed(() => {
  const layers = currentMap.value?.layers;
  if (!layers) return false;
  return [layers.document_intelligence.status, layers.terms.status].some(
    (status) => status === "stale" || status === "missing",
  );
});

// --- the annotated text of the Record under review ------------------------------------------------------------------
const textSegments = computed(() =>
  isOwnRecord.value && currentMap.value
    ? segmentText(String(props.record.text || ""), currentMap.value.mentions, shownLayers.value)
    : [],
);
function toggleLayer(layer: string, on: boolean) {
  const next = new Set(shownLayers.value);
  if (on) next.add(layer);
  else next.delete(layer);
  shownLayers.value = next;
}

// --- the diagram ----------------------------------------------------------------------------------------------------
interface DiagramNode {
  id: string;
  label: string;
  type: string;
  ring: "center" | "inner" | "outer";
  point: Point;
  walkable: boolean;
}
interface DiagramEdge {
  id: string;
  source: string;
  target: string;
  kind: string;
  faint: boolean;
  title: string;
}

const RECORD_CENTER = "__record__";

const diagram = computed<{ centerLabel: string; nodes: DiagramNode[]; edges: DiagramEdge[] }>(
  () => {
    const empty = { centerLabel: "", nodes: [], edges: [] };
    let centerId = "";
    let centerLabel = "";
    let centerType = "record";
    let inner: RecordSemanticMapNode[] = [];
    let outer: RecordSemanticMapNode[] = [];
    let edges: SemanticContentGraphEdge[] = [];
    const attached = new Map<string, string>();
    const keep = (node: RecordSemanticMapNode) => includeTerms.value || node.type !== "term";
    if (currentMap.value) {
      const map = currentMap.value;
      centerId = RECORD_CENTER;
      centerLabel = map.record_id;
      inner = map.nodes.filter((node) => node.local && keep(node)).slice(0, MAX_INNER);
      const innerIds = new Set(inner.map((node) => node.id));
      outer = map.nodes.filter((node) => !node.local && keep(node));
      edges = map.edges;
      for (const edge of edges) {
        if (innerIds.has(edge.source) && !innerIds.has(edge.target))
          attached.set(edge.target, edge.source);
        if (innerIds.has(edge.target) && !innerIds.has(edge.source))
          attached.set(edge.source, edge.target);
      }
      const reachable = new Set(attached.keys());
      outer = outer.filter((node) => reachable.has(node.id)).slice(0, MAX_OUTER);
    } else if (currentNeighborhood.value) {
      const hood = currentNeighborhood.value;
      centerId = hood.node.id;
      centerLabel = hood.node.label;
      centerType = hood.node.type;
      inner = hood.nodes.filter(keep).slice(0, MAX_INNER);
      edges = hood.edges;
    } else return empty;

    const positions = radialLayout(
      centerId,
      inner.map((node) => node.id),
      outer.map((node) => node.id),
      SIZE,
      attached,
    );
    const nodes: DiagramNode[] = [
      {
        id: centerId,
        label: centerLabel,
        type: centerType,
        ring: "center",
        point: positions.get(centerId)!,
        walkable: false,
      },
      ...inner.map((node) => ({
        id: node.id,
        label: node.label,
        type: node.type,
        ring: "inner" as const,
        point: positions.get(node.id)!,
        walkable: true,
      })),
      ...outer.map((node) => ({
        id: node.id,
        label: node.label,
        type: node.type,
        ring: "outer" as const,
        point: positions.get(node.id)!,
        walkable: true,
      })),
    ];
    const lines: DiagramEdge[] = [];
    if (centerId === RECORD_CENTER) {
      // Membership spokes: which nodes this Record contains.
      for (const node of inner)
        lines.push({
          id: `spoke:${node.id}`,
          source: centerId,
          target: node.id,
          kind: "membership",
          faint: true,
          title: i18n.t("pdf_corpus.semantic_map_in_record"),
        });
    }
    for (const edge of edges) {
      const from = positions.get(edge.source);
      const to = positions.get(edge.target);
      if (!from || !to) continue;
      lines.push({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        kind: edge.relation_kind,
        faint: "in_record" in edge && edge.in_record === false,
        title: relationLabel(edge),
      });
    }
    return { centerLabel, nodes, edges: lines };
  },
);

const layoutState = useRelationLayoutState();
const viewport = ref<InstanceType<typeof UiRelationViewport> | null>(null);
const viewportState = ref<RelationViewportState>({ pan: { x: 0, y: 0 }, zoom: 1 });

const positionedNodes = computed<DiagramNode[]>(() =>
  diagram.value.nodes.map((node) => ({
    ...node,
    point: layoutState.positionFor(node.id, node.point),
  })),
);
const positionMap = computed(
  () => new Map(positionedNodes.value.map((node) => [node.id, node.point])),
);
const diagramEdges = computed(() =>
  diagram.value.edges
    .map((edge) => {
      const from = positionMap.value.get(edge.source);
      const to = positionMap.value.get(edge.target);
      return from && to ? { ...edge, from, to } : null;
    })
    .filter((edge): edge is DiagramEdge & { from: Point; to: Point } => Boolean(edge)),
);
const contentBounds = computed(() =>
  relationBoundsForPoints(
    positionedNodes.value.map((node) => node.point),
    72,
  ),
);

const localNodesByType = computed(() => {
  const groups = new Map<string, RecordSemanticMapNode[]>();
  for (const node of currentMap.value?.nodes || []) {
    if (!node.local) continue;
    const bucket = groups.get(node.type) || [];
    bucket.push(node);
    groups.set(node.type, bucket);
  }
  return Array.from(groups.entries()).sort(([left], [right]) =>
    left === "term" ? 1 : right === "term" ? -1 : left.localeCompare(right),
  );
});

function neighborOf(edge: SemanticContentGraphEdge) {
  const hood = currentNeighborhood.value;
  if (!hood) return null;
  const otherId = edge.source === hood.node.id ? edge.target : edge.source;
  return hood.nodes.find((node) => node.id === otherId) || null;
}
function recordPreview(recordId: string) {
  return previews.value[recordId] || "";
}

// --- shared viewport and node movement --------------------------------------------------------------------------
const draggedNodeId = ref("");
const nodeDrag = useRelationNodeDrag({
  getZoom: () => viewportState.value.zoom,
  onMove: (point) => {
    if (draggedNodeId.value) layoutState.setPosition(draggedNodeId.value, point);
  },
});

function linePath(from: Point, to: Point) {
  return `M ${from.x} ${from.y} L ${to.x} ${to.y}`;
}

function onViewportChange(state: RelationViewportState) {
  viewportState.value = state;
}

function fitMap() {
  viewport.value?.fitView(contentBounds.value);
}

function resetMapLayout() {
  layoutState.clearPositions();
  viewport.value?.resetView();
}

watch(current, () => resetMapLayout());

function onNodePointerDown(event: PointerEvent, node: DiagramNode) {
  draggedNodeId.value = node.id;
  nodeDrag.begin(event, node.point);
}

function onNodePointerMove(event: PointerEvent) {
  nodeDrag.update(event);
}

function onNodePointerEnd(event: PointerEvent) {
  nodeDrag.end(event);
  draggedNodeId.value = "";
}

function onNodeClick(event: MouseEvent, node: DiagramNode) {
  event.stopPropagation();
  if (nodeDrag.consumeClick(event)) return;
  if (node.walkable) walkToNode(node);
}

function onNodeKeydown(event: KeyboardEvent, node: DiagramNode) {
  draggedNodeId.value = node.id;
  if (nodeDrag.nudge(event, node.point)) {
    draggedNodeId.value = "";
    return;
  }
  draggedNodeId.value = "";
  if (!node.walkable) return;
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    walkToNode(node);
  }
}
</script>

<template>
  <section class="record-semantic-map" :aria-labelledby="`${idPrefix}-semantic-map-title`">
    <header class="semantic-map-head">
      <div>
        <h3 :id="`${idPrefix}-semantic-map-title`">
          {{ i18n.t("pdf_corpus.semantic_map_heading") }}
        </h3>
        <p>{{ i18n.t("pdf_corpus.semantic_map_help") }}</p>
      </div>
    </header>

    <nav
      v-if="trail.length > 1"
      class="semantic-map-trail"
      :aria-label="i18n.t('pdf_corpus.semantic_map_trail')"
    >
      <button type="button" class="btn small" @click="back">
        {{ i18n.t("pdf_corpus.semantic_map_back") }}
      </button>
      <ol>
        <li v-for="(step, index) in trail" :key="`${index}-${step.kind}-${step.id}`">
          <button
            v-if="index < trail.length - 1"
            type="button"
            class="trail-step"
            @click="jump(index)"
          >
            {{ stepLabel(step) }}
          </button>
          <span v-else aria-current="step" class="trail-step current">{{ stepLabel(step) }}</span>
        </li>
      </ol>
    </nav>

    <p v-if="loading" class="semantic-map-status" role="status">{{ i18n.t("ui.loading") }}</p>
    <p v-else-if="error" class="semantic-map-status error" role="alert">{{ error }}</p>

    <!-- Record step -------------------------------------------------------------------------------------------- -->
    <template v-if="currentMap">
      <div
        class="semantic-map-layers"
        :aria-label="i18n.t('pdf_corpus.semantic_map_layers')"
        role="group"
      >
        <span :data-status="currentMap.layers.document_intelligence.status">
          <b>{{ i18n.t("pdf_corpus.semantic_map_layer_document") }}</b>
          {{ statusLabel(currentMap.layers.document_intelligence.status) }}
          <small v-if="currentMap.layers.document_intelligence.provider">
            · {{ currentMap.layers.document_intelligence.provider }}
          </small>
        </span>
        <span :data-status="currentMap.layers.terms.status">
          <b>{{ i18n.t("pdf_corpus.semantic_map_layer_terms") }}</b>
          {{ statusLabel(currentMap.layers.terms.status) }}
        </span>
        <button
          v-if="layerStatusNeedsRerun"
          type="button"
          class="btn small secondary"
          :disabled="disabled || rerunning"
          @click="rerun"
        >
          {{
            rerunning
              ? i18n.t("pdf_corpus.document_intelligence_rerunning")
              : i18n.t("pdf_corpus.document_intelligence_rerun")
          }}
        </button>
      </div>
      <p v-if="layerStatusNeedsRerun" class="semantic-map-status warning">
        {{ i18n.t("pdf_corpus.semantic_map_status_note") }}
      </p>
      <p class="semantic-map-summary">
        {{
          i18n.tf("pdf_corpus.semantic_map_summary", {
            local: currentMap.summary.local_nodes,
            links: currentMap.summary.linked_records,
          })
        }}
      </p>

      <section
        v-if="isOwnRecord && props.record.text"
        class="annotated-text"
        :aria-labelledby="`${idPrefix}-semantic-annotated-title`"
      >
        <div class="annotated-text-head">
          <h4 :id="`${idPrefix}-semantic-annotated-title`">
            {{ i18n.t("pdf_corpus.semantic_map_annotated_text") }}
          </h4>
          <fieldset class="layer-toggles">
            <legend>{{ i18n.t("pdf_corpus.semantic_map_show_layers") }}</legend>
            <label v-for="layer in LAYERS" :key="layer" :data-layer="layer">
              <input
                type="checkbox"
                :checked="shownLayers.has(layer)"
                @change="toggleLayer(layer, ($event.target as HTMLInputElement).checked)"
              />
              {{ i18n.t(`pdf_corpus.semantic_map_layer_${layer}`) }}
            </label>
          </fieldset>
        </div>
        <p class="annotated-text-body">
          <template v-for="segment in textSegments" :key="segment.start">
            <button
              v-if="segment.mention?.node_id"
              type="button"
              class="mention"
              :data-layer="segment.mention.layer"
              :title="
                segment.mention.speaker
                  ? i18n.tf('pdf_corpus.semantic_map_quotation_speaker', {
                      speaker: segment.mention.speaker,
                    })
                  : segment.mention.tag
              "
              :aria-label="
                i18n.tf('pdf_corpus.semantic_map_walk_to', {
                  label: `${segment.text} (${segment.mention.tag || segment.mention.layer})`,
                })
              "
              @click="walkToMention(segment.mention.node_id || '', segment.text)"
            >
              {{ segment.text }}<small>{{ segment.mention.tag || segment.mention.layer }}</small>
            </button>
            <mark
              v-else-if="segment.mention"
              class="mention"
              :data-layer="segment.mention.layer"
              :title="segment.mention.tag"
              >{{ segment.text
              }}<small>{{ segment.mention.tag || segment.mention.layer }}</small></mark
            >
            <template v-else>{{ segment.text }}</template>
          </template>
        </p>
      </section>
      <p v-else-if="!isOwnRecord && recordPreview(currentMap.record_id)" class="record-preview">
        {{ recordPreview(currentMap.record_id) }}
      </p>
      <div v-if="!isOwnRecord" class="record-step-actions">
        <button type="button" class="btn small" @click="emit('openRecord', currentMap.record_id)">
          {{ i18n.t("pdf_corpus.semantic_map_open_record") }}
        </button>
      </div>
    </template>

    <!-- Node step ---------------------------------------------------------------------------------------------- -->
    <header v-else-if="currentNeighborhood" class="node-step-head">
      <p class="node-kind" :data-tone="nodeTone(currentNeighborhood.node.type)">
        {{
          i18n.tf("pdf_corpus.semantic_map_node_meta", {
            type: currentNeighborhood.node.type,
            records: currentNeighborhood.total_records,
          })
        }}
      </p>
      <h4>{{ currentNeighborhood.node.label }}</h4>
      <p v-if="currentNeighborhood.node.aliases?.length" class="node-aliases">
        {{ currentNeighborhood.node.aliases.join(" · ") }}
      </p>
      <p v-if="currentNeighborhood.node.tags?.length" class="node-aliases">
        {{ currentNeighborhood.node.tags.join(" · ") }}
      </p>
    </header>

    <div v-if="diagram.nodes.length > 1" class="semantic-map-canvas-wrap">
      <UiRelationViewport
        ref="viewport"
        class="semantic-map-viewport"
        :accessible-label="
          i18n.tf('pdf_corpus.semantic_map_accessible_label', { label: diagram.centerLabel })
        "
        :help-text="
          i18n.t(
            'pdf_corpus.semantic_map_interaction_help',
            'Drag the background to pan. Drag any node to reposition it. Arrow keys pan, plus and minus zoom, and 0 resets the view. Hold Alt and use an arrow key to move a focused node.',
          )
        "
        :resize-label="i18n.t('pdf_corpus.semantic_map_resize', 'Resize record semantic map')"
        :initial-center="{ x: SIZE.width / 2, y: SIZE.height / 2 }"
        :content-bounds="contentBounds"
        :content-width="SIZE.width"
        :content-height="SIZE.height"
        :min-zoom="surfacePreset.minZoom"
        :max-zoom="surfacePreset.maxZoom"
        :resize-axis="surfacePreset.resizeAxis"
        @viewport-change="onViewportChange"
      >
        <svg
          class="semantic-map-canvas"
          :viewBox="`0 0 ${SIZE.width} ${SIZE.height}`"
          :width="SIZE.width"
          :height="SIZE.height"
        >
          <g>
            <UiRelationEdge
              v-for="edge in diagramEdges"
              :key="edge.id"
              :path="linePath(edge.from, edge.to)"
              :title="edge.title"
              :class="['map-edge', edge.kind, { faint: edge.faint }]"
            />
          </g>
          <g
            v-for="node in positionedNodes"
            :key="node.id"
            :transform="`translate(${node.point.x}, ${node.point.y})`"
            :class="['map-node', node.ring]"
            :data-tone="node.ring === 'center' && currentMap ? 'record' : nodeTone(node.type)"
            :role="node.walkable ? 'button' : 'group'"
            tabindex="0"
            :aria-label="
              node.walkable
                ? i18n.tf('pdf_corpus.semantic_map_walk_to', {
                    label: `${node.label}, ${node.type}`,
                  })
                : node.label
            "
            @pointerdown.stop="onNodePointerDown($event, node)"
            @pointermove.stop="onNodePointerMove"
            @pointerup.stop="onNodePointerEnd"
            @pointercancel.stop="onNodePointerEnd"
            @click="onNodeClick($event, node)"
            @keydown="onNodeKeydown($event, node)"
          >
            <template v-if="node.ring === 'center' && currentMap">
              <rect x="-8" y="-6" width="16" height="12" rx="3" />
              <text x="0" y="22" text-anchor="middle">
                {{ shortLabel(node.label) }}
              </text>
            </template>
            <UiRelationDotNode
              v-else
              :radius="node.ring === 'center' ? 7 : node.ring === 'inner' ? 5 : 4"
              :label="shortLabel(node.label)"
              show-label
              :label-offset="node.ring === 'center' ? 8 : 6"
            />
          </g>
        </svg>
      </UiRelationViewport>
      <div class="semantic-map-legend">
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
        <span v-if="currentMap"
          ><i class="legend-line faint" />{{ i18n.t("pdf_corpus.semantic_map_outward") }}</span
        >
        <label v-if="currentMap" class="include-terms">
          <input v-model="includeTerms" type="checkbox" />
          {{ i18n.t("pdf_corpus.semantic_map_include_terms") }}
        </label>
        <UiRelationToolbar
          class="semantic-map-zoom"
          :accessible-label="i18n.t('pdf_corpus.semantic_map_controls', 'Semantic map controls')"
          :zoom-out-label="i18n.t('pdf_corpus.semantic_graph_zoom_out')"
          :zoom-in-label="i18n.t('pdf_corpus.semantic_graph_zoom_in')"
          :fit-label="i18n.t('pdf_corpus.semantic_graph_zoom_fit')"
          :reset-label="i18n.t('pdf_corpus.semantic_map_reset_layout', 'Reset map layout')"
          @zoom-out="viewport?.zoomBy(1 / 1.25)"
          @zoom-in="viewport?.zoomBy(1.25)"
          @fit="fitMap"
          @reset="resetMapLayout"
        />
      </div>
    </div>
    <p
      v-else-if="
        (currentMap && !currentMap.nodes.length) ||
        (currentNeighborhood &&
          !currentNeighborhood.nodes.length &&
          !currentNeighborhood.records.length)
      "
      class="semantic-map-status"
    >
      {{ i18n.t("pdf_corpus.semantic_map_empty") }}
    </p>

    <!-- Record step lists -------------------------------------------------------------------------------------- -->
    <div v-if="currentMap" class="semantic-map-lists">
      <section v-if="localNodesByType.length" :aria-labelledby="`${idPrefix}-semantic-local-title`">
        <h4 :id="`${idPrefix}-semantic-local-title`">
          {{ i18n.t("pdf_corpus.semantic_map_in_record") }}
        </h4>
        <dl class="node-groups">
          <template v-for="[type, nodes] in localNodesByType" :key="type">
            <dt>{{ type }}</dt>
            <dd>
              <button
                v-for="node in nodes"
                :key="node.id"
                type="button"
                class="node-chip"
                :data-tone="nodeTone(node.type)"
                @click="walkToNode(node)"
              >
                {{ node.label }}<small>{{ node.record_count || 1 }}</small>
              </button>
            </dd>
          </template>
        </dl>
      </section>

      <section :aria-labelledby="`${idPrefix}-semantic-linked-title`">
        <h4 :id="`${idPrefix}-semantic-linked-title`">
          {{ i18n.t("pdf_corpus.semantic_map_linked_records") }}
        </h4>
        <p class="help">{{ i18n.t("pdf_corpus.semantic_map_linked_records_help") }}</p>
        <p v-if="!currentMap.linked_records.length" class="semantic-map-status">
          {{ i18n.t("pdf_corpus.semantic_map_no_links") }}
        </p>
        <ul v-else class="record-links">
          <li v-for="link in currentMap.linked_records" :key="link.record_id">
            <div class="record-link-head">
              <b>{{ link.record_id }}</b>
              <small>{{
                i18n.tf("pdf_corpus.semantic_map_shared", { count: link.shared_node_count })
              }}</small>
            </div>
            <p>{{ link.preview }}</p>
            <div class="record-link-shared">
              <button
                v-for="node in link.shared_nodes"
                :key="node.id"
                type="button"
                class="node-chip"
                :data-tone="nodeTone(node.type)"
                @click="walkToNode(node)"
              >
                {{ node.label }}
              </button>
            </div>
            <div class="record-link-actions">
              <button type="button" class="btn small" @click="walkToRecord(link.record_id)">
                {{ i18n.t("pdf_corpus.semantic_map_explore_record") }}
              </button>
              <button
                type="button"
                class="btn small secondary"
                @click="emit('openRecord', link.record_id)"
              >
                {{ i18n.t("pdf_corpus.semantic_map_open_record") }}
              </button>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <!-- Node step lists ---------------------------------------------------------------------------------------- -->
    <div v-else-if="currentNeighborhood" class="semantic-map-lists">
      <section :aria-labelledby="`${idPrefix}-semantic-relations-title`">
        <h4 :id="`${idPrefix}-semantic-relations-title`">
          {{
            i18n.tf("pdf_corpus.semantic_map_relations", {
              shown: currentNeighborhood.edges.length,
              total: currentNeighborhood.total_edges,
            })
          }}
        </h4>
        <p v-if="!currentNeighborhood.edges.length" class="semantic-map-status">
          {{ i18n.t("pdf_corpus.semantic_map_no_relations") }}
        </p>
        <ul v-else class="relation-list">
          <li
            v-for="edge in currentNeighborhood.edges"
            :key="edge.id"
            :data-kind="edge.relation_kind"
          >
            <span class="relation-line">
              <span v-if="edge.target === currentNeighborhood.node.id" aria-hidden="true">←</span>
              <b>{{ relationLabel(edge) }}</b>
              <span v-if="edge.source === currentNeighborhood.node.id" aria-hidden="true">→</span>
              <button
                v-if="neighborOf(edge)"
                type="button"
                class="node-chip"
                :data-tone="nodeTone(neighborOf(edge)!.type)"
                @click="walkToNode(neighborOf(edge)!)"
              >
                {{ neighborOf(edge)!.label }}
              </button>
            </span>
            <small>
              {{
                edge.relation_kind === "semantic"
                  ? `${i18n.t("pdf_corpus.semantic_graph_semantic")} · ${authorityLabel(edge.authority_status)}`
                  : i18n.t("pdf_corpus.semantic_graph_observational")
              }}
              ·
              {{
                i18n.tf("pdf_corpus.semantic_map_relation_records", {
                  count: edge.record_ids?.length || 0,
                })
              }}
            </small>
          </li>
        </ul>
      </section>
      <section :aria-labelledby="`${idPrefix}-semantic-node-records-title`">
        <h4 :id="`${idPrefix}-semantic-node-records-title`">
          {{
            i18n.tf("pdf_corpus.semantic_map_records_for_node", {
              shown: currentNeighborhood.records.length,
              total: currentNeighborhood.total_records,
            })
          }}
        </h4>
        <ul class="record-links">
          <li v-for="row in currentNeighborhood.records" :key="row.record_id">
            <div class="record-link-head">
              <b>{{ row.record_id }}</b>
              <small v-if="row.record_id === props.record.record_id">{{
                i18n.t("pdf_corpus.semantic_map_current_record")
              }}</small>
            </div>
            <p>{{ row.preview }}</p>
            <div class="record-link-actions">
              <button type="button" class="btn small" @click="walkToRecord(row.record_id)">
                {{ i18n.t("pdf_corpus.semantic_map_explore_record") }}
              </button>
              <button
                v-if="row.record_id !== props.record.record_id"
                type="button"
                class="btn small secondary"
                @click="emit('openRecord', row.record_id)"
              >
                {{ i18n.t("pdf_corpus.semantic_map_open_record") }}
              </button>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <p
      v-if="currentMap?.epistemic_note || currentNeighborhood?.epistemic_note"
      class="semantic-map-note"
    >
      {{ currentMap?.epistemic_note || currentNeighborhood?.epistemic_note }}
    </p>
  </section>
</template>

<style scoped>
.record-semantic-map {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
}
.semantic-map-head h3,
.semantic-map-head p,
.semantic-map-lists h4,
.annotated-text h4,
.node-step-head h4,
.node-step-head p,
.record-links p {
  margin: 0;
}
.semantic-map-head p,
.semantic-map-summary,
.semantic-map-note,
.semantic-map-status,
.node-aliases,
.help {
  color: var(--muted);
  font-size: var(--fs-xs);
  margin: 0;
}
.semantic-map-status.warning {
  color: var(--tone-warn-fg);
}
.semantic-map-status.error {
  color: var(--tone-danger-fg);
}
.semantic-map-trail {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  min-width: 0;
}
.semantic-map-trail ol {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: var(--fs-xs);
}
.semantic-map-trail li + li::before {
  content: "›";
  margin-inline-end: 4px;
  color: var(--muted);
}
.trail-step {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--accent);
  font: inherit;
  cursor: pointer;
}
.trail-step.current {
  color: var(--text);
  font-weight: var(--fw-semibold);
}
.semantic-map-layers {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
  font-size: var(--fs-xs);
}
.semantic-map-layers > span {
  padding: 2px var(--space-2);
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
}
.semantic-map-layers > span[data-status="ok"] {
  border-color: var(--tone-ok-border);
}
.semantic-map-layers > span[data-status="stale"],
.semantic-map-layers > span[data-status="missing"] {
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
}
.annotated-text {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
}
.annotated-text-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-2);
  align-items: center;
}
.layer-toggles {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  border: 0;
  font-size: var(--fs-xs);
}
.layer-toggles legend {
  float: left;
  margin-inline-end: var(--space-1);
  padding: 0;
  font-weight: var(--fw-semibold);
}
.layer-toggles label,
.include-terms {
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
  margin: 0;
  font-weight: var(--fw-regular);
}
.layer-toggles input,
.include-terms input {
  margin: 0;
}
.annotated-text-body {
  margin: 0;
  max-height: 280px;
  overflow: auto;
  line-height: 1.9;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.mention {
  padding: 0 2px;
  border: 0;
  border-bottom: 2px solid var(--tone-info-border);
  border-radius: 2px;
  background: var(--tone-info-bg);
  color: var(--text);
  font: inherit;
  cursor: default;
}
button.mention {
  cursor: pointer;
}
button.mention:focus-visible,
.node-chip:focus-visible,
.trail-step:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}
.mention small {
  margin-inline-start: 2px;
  color: var(--muted);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.mention[data-layer="quotation"] {
  background: var(--tone-warn-bg);
  border-bottom-color: var(--tone-warn-border);
}
.mention[data-layer="pos"] {
  background: transparent;
  border-bottom: 2px dotted var(--border-strong);
}
.mention[data-layer="entity"] {
  background: var(--tone-ok-bg);
  border-bottom-color: var(--tone-ok-border);
}
.record-preview {
  margin: 0;
  color: var(--muted);
  font-style: italic;
}
.node-step-head {
  display: grid;
  gap: 2px;
}
.node-kind {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: var(--fs-xs);
  color: var(--muted);
}
.semantic-map-canvas-wrap {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}
.semantic-map-viewport {
  width: 100%;
  height: 600px;
  min-height: 320px;
}
.semantic-map-canvas {
  position: absolute;
  inset: 0;
  display: block;
  width: 820px;
  max-width: none;
  height: 600px;
  overflow: visible;
}
.map-edge {
  --relation-edge-stroke: var(--border-strong);
  --relation-edge-opacity: 1;
  stroke-width: 1.4;
}
.map-edge.observational {
  stroke-dasharray: 5 5;
  --relation-edge-opacity: 0.6;
}
.map-edge.membership {
  --relation-edge-stroke: var(--line);
  stroke-width: 1;
}
.map-edge.faint {
  --relation-edge-opacity: 0.35;
}
.map-node {
  --relation-node-dot: var(--muted);
  --relation-node-dot-border: var(--surface-raised);
  --relation-node-dot-border-width: 2;
  --relation-node-label: var(--text);
  --relation-node-label-halo: var(--surface-raised);
}
.map-node rect {
  fill: var(--muted);
  stroke: var(--surface-raised);
  stroke-width: 2;
}
.map-node[data-tone="person"] {
  --relation-node-dot: var(--tone-info-edge);
}
.map-node[data-tone="concept"] {
  --relation-node-dot: var(--accent);
}
.map-node[data-tone="work"] {
  --relation-node-dot: var(--tone-ok-edge);
}
.map-node[data-tone="entity"] {
  --relation-node-dot: var(--tone-warn-edge);
}
.map-node[data-tone="record"] rect {
  fill: var(--text);
}
.map-node.outer {
  --relation-node-dot-opacity: 0.7;
}
.map-node > text {
  fill: var(--text);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  paint-order: stroke;
  stroke: var(--surface-raised);
  stroke-width: 3px;
}
.map-node {
  cursor: grab;
  touch-action: none;
}
.map-node[role="button"] {
  cursor: grab;
}
.map-node:focus {
  outline: none;
}
.map-node:focus-visible {
  --relation-node-dot-border: var(--focus-ring);
  --relation-node-dot-border-width: 4;
}
.semantic-map-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  padding: var(--space-2) 0 0;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}
.semantic-map-legend span,
.include-terms {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.semantic-map-zoom {
  margin-inline-start: auto;
}
.legend-line {
  display: inline-block;
  width: 28px;
  border-top: 2px solid var(--border-strong);
}
.legend-line.observational {
  border-top-style: dashed;
}
.legend-line.faint {
  opacity: 0.35;
}
.semantic-map-lists {
  display: grid;
  gap: var(--space-4);
}
.semantic-map-lists section {
  display: grid;
  gap: var(--space-2);
}
.node-groups {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: var(--space-2) var(--space-3);
  margin: 0;
}
.node-groups dt {
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  color: var(--muted);
}
.node-groups dd {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 0;
}
.node-chip {
  display: inline-flex;
  gap: 4px;
  align-items: baseline;
  padding: 2px var(--space-2);
  border: 1px solid var(--line);
  border-inline-start: 3px solid var(--border-strong);
  border-radius: var(--radius-control);
  background: var(--card);
  color: var(--text);
  font: inherit;
  font-size: var(--fs-xs);
  cursor: pointer;
}
.node-chip small {
  color: var(--muted);
}
.node-chip[data-tone="person"] {
  border-inline-start-color: var(--tone-info-edge);
}
.node-chip[data-tone="concept"] {
  border-inline-start-color: var(--accent);
}
.node-chip[data-tone="work"] {
  border-inline-start-color: var(--tone-ok-edge);
}
.node-chip[data-tone="entity"] {
  border-inline-start-color: var(--tone-warn-edge);
}
.record-links,
.relation-list {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.record-links li,
.relation-list li {
  display: grid;
  gap: 4px;
  padding-block: var(--space-2);
  border-top: 1px solid var(--line);
}
.record-links p {
  color: var(--muted);
  font-size: var(--fs-xs);
}
.record-link-head,
.relation-line {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
}
.record-link-head small,
.relation-list small {
  color: var(--muted);
  font-size: var(--fs-xs);
}
.record-link-shared,
.record-link-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.relation-list li[data-kind="observational"] b {
  font-weight: var(--fw-regular);
  font-style: italic;
}
</style>
