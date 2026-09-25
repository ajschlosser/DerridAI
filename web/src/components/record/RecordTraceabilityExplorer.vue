<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import UiCard from "../ui/UiCard.vue";
import UiDialog from "../ui/UiDialog.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import UiTabs from "../ui/UiTabs.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import ResearchObjectDiagram from "./ResearchObjectDiagram.vue";
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
const mode = ref<"trace" | "model">("trace");
const focusId = ref("");
const diagramOpen = ref(false);

type GraphNeighbor = {
  edge: ResearchObjectEdge;
  node: ResearchObjectNode;
  relation: string;
  cardinality?: string | null;
  direction: "in" | "out";
};
type RelationshipGroup = {
  id: "source" | "record" | "metadata" | "research";
  title: string;
  items: GraphNeighbor[];
};

const modeTabs = computed(() => [
  { id: "trace", label: i18n.t("traceability.this_record", "This record") },
  { id: "model", label: i18n.t("traceability.data_model", "DERRIDAI model") },
]);

const nodes = computed<ResearchObjectNode[]>(() => {
  if (mode.value === "trace") return props.graph?.nodes || [];
  return (props.model?.nodes || []).map((node) => ({
    id: `model:${node.type}`,
    object_type: node.type,
    object_id: node.type,
    label: node.label,
    summary: node.profile,
    materialization: "derived_view",
    details: {
      profile: node.profile,
      persistence: node.persistence,
      normative: node.normative,
    },
  }));
});

const edges = computed<ResearchObjectEdge[]>(() => {
  if (mode.value === "trace") return props.graph?.edges || [];
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
const rootNode = computed(() =>
  props.graph?.root_id ? props.graph.nodes.find((node) => node.id === props.graph?.root_id) || null : null,
);

function typeLabel(type: string) {
  const fallback: Record<string, string> = {
    SourceDocument: "Source document",
    SourceSpan: "Source passage",
    Record: "Corpus record",
    RecordRevision: "Record revision",
    FieldAssertion: "Metadata assertion",
    CorpusPublication: "Corpus publication",
    RetrievalRun: "Retrieval run",
    EvidenceRef: "Evidence reference",
    EvidencePacket: "Evidence packet",
    GenerationRun: "Generation run",
    GeneratedClaim: "Generated claim",
    SupportBinding: "Claim support link",
    ResearchRun: "Research run",
  };
  return i18n.t(`traceability.type.${type}`, fallback[type] || type);
}

function typeDescription(type: string) {
  const fallback: Record<string, string> = {
    SourceDocument: "The ingested document or source asset from which this material ultimately comes.",
    SourceSpan: "An exact page, passage, region, or source segment connected to the record.",
    Record: "The scholarly corpus record currently being inspected.",
    RecordRevision: "A specific version of the record, used when evidence must be pinned to an exact state.",
    FieldAssertion: "A metadata value together with how it was derived, evaluated, and reviewed.",
    CorpusPublication: "An immutable published corpus snapshot that contains or references records.",
    RetrievalRun: "A retrieval operation that selected material for possible evidentiary use.",
    EvidenceRef: "A durable pointer to the exact record revision or source passage used as evidence.",
    EvidencePacket: "The ordered evidence context supplied to a research operation.",
    GenerationRun: "The model-generation operation that produced research output.",
    GeneratedClaim: "A substantive claim identified in generated research output.",
    SupportBinding: "The explicit link between a generated claim and the evidence said to support, qualify, contrast with, quote, or attribute it.",
    ResearchRun: "The retained research operation that ties corpus state, evidence, generation, and validation together.",
  };
  return i18n.t(`traceability.description.${type}`, fallback[type] || "");
}

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
    `${connectionGroup(a.node.object_type)} ${a.relation} ${a.node.label}`.localeCompare(
      `${connectionGroup(b.node.object_type)} ${b.relation} ${b.node.label}`,
    ),
  );
});

function connectionGroup(type: string): RelationshipGroup["id"] {
  if (["SourceDocument", "SourceSpan", "CorpusPublication"].includes(type)) return "source";
  if (["Record", "RecordRevision"].includes(type)) return "record";
  if (type === "FieldAssertion") return "metadata";
  return "research";
}

const relationshipGroups = computed<RelationshipGroup[]>(() => {
  const labels: Record<RelationshipGroup["id"], string> = {
    source: i18n.t("traceability.group_source", "Source lineage"),
    record: i18n.t("traceability.group_record", "Record state"),
    metadata: i18n.t("traceability.group_metadata", "Metadata & review"),
    research: i18n.t("traceability.group_research", "Research use"),
  };
  return (["source", "record", "metadata", "research"] as RelationshipGroup["id"][])
    .map((id) => ({
      id,
      title: labels[id],
      items: neighbors.value.filter((item) => connectionGroup(item.node.object_type) === id),
    }))
    .filter((group) => group.items.length);
});

const sourceNodes = computed(() =>
  nodes.value.filter((node) => ["SourceDocument", "SourceSpan", "CorpusPublication"].includes(node.object_type)),
);
const assertionNodes = computed(() => nodes.value.filter((node) => node.object_type === "FieldAssertion"));
const researchNodes = computed(() =>
  nodes.value.filter((node) =>
    ["RetrievalRun", "EvidenceRef", "EvidencePacket", "SupportBinding", "GenerationRun", "GeneratedClaim", "ResearchRun"].includes(
      node.object_type,
    ),
  ),
);

const sourceSummary = computed(() => {
  const documents = sourceNodes.value.filter((node) => node.object_type === "SourceDocument").length;
  const spans = sourceNodes.value.filter((node) => node.object_type === "SourceSpan").length;
  if (!documents && !spans) return i18n.t("traceability.none_retained", "None retained");
  return [
    documents ? i18n.tf("traceability.document_count", { count: documents }) : "",
    spans ? i18n.tf("traceability.passage_count", { count: spans }) : "",
  ]
    .filter(Boolean)
    .join(" · ");
});

const metadataSummary = computed(() =>
  assertionNodes.value.length
    ? i18n.tf("traceability.assertion_count", { count: assertionNodes.value.length })
    : i18n.t("traceability.none_retained", "None retained"),
);

const researchSummary = computed(() => {
  const claims = researchNodes.value.filter((node) => node.object_type === "GeneratedClaim").length;
  const bindings = researchNodes.value.filter((node) => node.object_type === "SupportBinding").length;
  if (!claims && !bindings) return i18n.t("traceability.no_claim_use", "No retained claim use");
  return [
    claims ? i18n.tf("traceability.claim_count", { count: claims }) : "",
    bindings ? i18n.tf("traceability.binding_count", { count: bindings }) : "",
  ]
    .filter(Boolean)
    .join(" · ");
});

const scopeLabel = computed(() =>
  i18n.tf("traceability.scope_count", {
    objects: nodes.value.length,
    relationships: edges.value.length,
  }),
);

function defaultFocus() {
  if (mode.value === "trace") {
    return props.graph?.root_id && nodeMap.value.has(props.graph.root_id)
      ? props.graph.root_id
      : nodes.value[0]?.id || "";
  }
  const preferredType = rootNode.value?.object_type || "Record";
  const preferred = `model:${preferredType}`;
  return nodeMap.value.has(preferred) ? preferred : nodes.value[0]?.id || "";
}

function selectFocus(id: string) {
  if (nodeMap.value.has(id)) focusId.value = id;
}

function resetFocus() {
  focusId.value = defaultFocus();
}

function presentDetail(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") {
    const text = JSON.stringify(value);
    return text.length > 180 ? `${text.slice(0, 177)}…` : text;
  }
  return String(value).replaceAll("_", " ");
}

function detailLabel(key: string) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusTone(status: string | null | undefined): "neutral" | "info" | "success" | "warning" | "danger" {
  const value = String(status || "").toLowerCase();
  if (["validated", "human_confirmed", "verified", "present"].includes(value)) return "success";
  if (["stale", "disputed", "unresolved"].includes(value)) return "warning";
  if (["rejected", "invalid", "evaluation_failed"].includes(value)) return "danger";
  return value ? "info" : "neutral";
}

watch(
  () => [props.graph?.root_id, props.graph?.nodes?.length, props.model?.nodes?.length],
  () => {
    if (!focusId.value || !nodeMap.value.has(focusId.value)) resetFocus();
  },
  { immediate: true },
);

watch(mode, () => resetFocus());
</script>

<template>
  <section class="traceability-explorer" aria-labelledby="traceabilityHeading">
    <header class="traceability-head">
      <div>
        <p>{{ i18n.t("traceability.kicker", "Source-to-claim provenance") }}</p>
        <h2 id="traceabilityHeading">
          {{
            mode === "trace"
              ? i18n.t("traceability.title_record", "Trace this record")
              : i18n.t("traceability.title_model", "Explore the DERRIDAI model")
          }}
        </h2>
      </div>
      <UiTooltip
        :text="
          mode === 'trace'
            ? i18n.t(
                'traceability.trace_help',
                'This view shows provenance actually retained for the selected record. It does not infer missing links.',
              )
            : i18n.t(
                'traceability.model_help',
                'This view shows the object types and relationships allowed by DERRIDAI 1.0. It is a model, not this record’s stored data.',
              )
        "
        :label="i18n.t('traceability.about_view', 'About this view')"
        placement="bottom"
      />
    </header>

    <UiTabs
      v-model="mode"
      :tabs="modeTabs"
      :tablist-label="i18n.t('traceability.mode', 'Traceability view')"
      id-prefix="traceability-view"
    />

    <div v-if="loading" class="traceability-state" role="status">
      <strong>{{ i18n.t("traceability.loading_title", "Building the trace…") }}</strong>
      <span>{{ i18n.t("traceability.loading", "Loading retained provenance relationships.") }}</span>
    </div>
    <div v-else-if="error" class="traceability-state error" role="alert">
      <strong>{{ i18n.t("traceability.error_title", "Trace unavailable") }}</strong>
      <span>{{ error }}</span>
    </div>
    <div v-else-if="!focus" class="traceability-state">
      <strong>{{ i18n.t("traceability.empty_title", "Nothing to trace yet") }}</strong>
      <span>{{
        i18n.t(
          "traceability.empty",
          "This record does not currently expose retained provenance relationships.",
        )
      }}</span>
    </div>

    <template v-else>
      <section class="traceability-orientation" aria-labelledby="traceabilityOrientation">
        <div class="traceability-scope">
          <UiStatusBadge
            :label="
              mode === 'trace'
                ? i18n.t('traceability.bounded_trace', 'Bounded record trace')
                : i18n.t('traceability.normative_model', 'Normative model')
            "
            tone="info"
          />
          <span>{{ scopeLabel }}</span>
        </div>
        <p id="traceabilityOrientation">
          {{
            mode === "trace"
              ? i18n.t(
                  "traceability.scope_help",
                  "This is a finite map of the provenance currently loaded for this record. Selecting an object changes the focus; it does not extend the graph.",
                )
              : i18n.t(
                  "traceability.model_scope_help",
                  "This is the finite DERRIDAI 1.0 relationship model. Selecting an object highlights the relationships allowed for that type.",
                )
          }}
        </p>
      </section>

      <section v-if="mode === 'trace'" class="traceability-overview" aria-label="Trace summary">
        <div class="trace-stage">
          <small>{{ i18n.t("traceability.stage_source", "Where it came from") }}</small>
          <strong>{{ i18n.t("traceability.source_lineage", "Source lineage") }}</strong>
          <span>{{ sourceSummary }}</span>
        </div>
        <div class="trace-connector" aria-hidden="true">↓</div>
        <div class="trace-stage record">
          <small>{{ i18n.t("traceability.stage_record", "What you are inspecting") }}</small>
          <strong>{{ i18n.t("traceability.current_record", "This corpus record") }}</strong>
          <span>{{ rootNode?.summary || rootNode?.label || "—" }}</span>
        </div>
        <div class="trace-branch" aria-hidden="true">
          <span>↙</span><span>↘</span>
        </div>
        <div class="trace-branch-cards">
          <div class="trace-stage">
            <small>{{ i18n.t("traceability.stage_metadata", "How metadata was established") }}</small>
            <strong>{{ i18n.t("traceability.metadata_review", "Metadata & review") }}</strong>
            <span>{{ metadataSummary }}</span>
          </div>
          <div class="trace-stage">
            <small>{{ i18n.t("traceability.stage_research", "How it was later used") }}</small>
            <strong>{{ i18n.t("traceability.research_use", "Research use") }}</strong>
            <span>{{ researchSummary }}</span>
          </div>
        </div>
      </section>

      <div class="traceability-map-action">
        <div>
          <strong>{{ i18n.t("traceability.visual_map", "Visual relationship map") }}</strong>
          <span>{{
            i18n.t(
              "traceability.visual_map_help",
              "See every retained object and relationship at once. Click any node to inspect its direct links.",
            )
          }}</span>
        </div>
        <UiButton
          size="small"
          icon="chart"
          :label="i18n.t('traceability.open_map', 'Open map')"
          @click="diagramOpen = true"
        />
      </div>

      <UiCard as="article" class="traceability-focus-card">
        <div class="focus-head">
          <div>
            <small>{{ i18n.t("traceability.selected_object", "Selected object") }}</small>
            <h3>{{ typeLabel(focus.object_type) }}</h3>
          </div>
          <UiButton
            v-if="focus.id !== defaultFocus()"
            variant="ghost"
            size="small"
            :label="i18n.t('traceability.back_to_record', 'Back to record')"
            @click="resetFocus"
          />
        </div>
        <p class="focus-name">{{ focus.label }}</p>
        <p v-if="focus.summary" class="focus-summary">{{ focus.summary }}</p>
        <p class="focus-explanation">{{ typeDescription(focus.object_type) }}</p>
        <div class="focus-badges">
          <UiStatusBadge
            v-if="focus.status"
            :label="presentDetail(focus.status)"
            :tone="statusTone(focus.status)"
          />
          <UiStatusBadge
            v-if="!focus.status && mode === 'model'"
            :label="String(focus.details?.profile || 'DERRIDAI')"
            tone="neutral"
          />
        </div>

        <details class="technical-details">
          <summary>{{ i18n.t("traceability.technical_details", "Technical details") }}</summary>
          <dl>
            <div>
              <dt>{{ i18n.t("traceability.object_type", "Object type") }}</dt>
              <dd><code>{{ focus.object_type }}</code></dd>
            </div>
            <div>
              <dt>{{ i18n.t("traceability.object_id", "Object ID") }}</dt>
              <dd><code>{{ focus.object_id }}</code></dd>
            </div>
            <div v-if="focus.materialization">
              <dt>{{ i18n.t("traceability.materialization", "Representation") }}</dt>
              <dd>{{ presentDetail(focus.materialization) }}</dd>
            </div>
            <div v-for="(value, key) in focus.details || {}" :key="String(key)">
              <dt>{{ detailLabel(String(key)) }}</dt>
              <dd>{{ presentDetail(value) }}</dd>
            </div>
          </dl>
        </details>
      </UiCard>

      <section class="traceability-connections" aria-labelledby="traceabilityConnections">
        <div class="section-head">
          <div>
            <small>{{ i18n.t("traceability.direct_relationships", "Direct relationships") }}</small>
            <h3 id="traceabilityConnections">
              {{ i18n.tf("traceability.connected_count", { count: neighbors.length }) }}
            </h3>
          </div>
          <span>{{ neighbors.length }}</span>
        </div>

        <div v-if="relationshipGroups.length" class="relationship-groups">
          <section v-for="group in relationshipGroups" :key="group.id" class="relationship-group">
            <h4>{{ group.title }}</h4>
            <button
              v-for="item in group.items"
              :key="item.edge.id"
              type="button"
              class="relationship-row"
              :data-object-id="item.node.id"
              @click="selectFocus(item.node.id)"
            >
              <span class="relationship-copy">
                <small>{{ item.relation }}</small>
                <strong>{{ typeLabel(item.node.object_type) }}</strong>
                <span>{{ item.node.label }}</span>
              </span>
              <span class="relationship-arrow" aria-hidden="true">→</span>
            </button>
          </section>
        </div>
        <p v-else class="traceability-none">
          {{
            i18n.t(
              "traceability.no_connections",
              "No direct relationships are retained from this object in the current scope.",
            )
          }}
        </p>
      </section>
    </template>

    <UiDialog
      :open="diagramOpen"
      size="xlarge"
      :title="
        mode === 'trace'
          ? i18n.t('traceability.map_title_record', 'Record relationship map')
          : i18n.t('traceability.map_title_model', 'DERRIDAI relationship model')
      "
      :description="
        mode === 'trace'
          ? i18n.t(
              'traceability.map_description_record',
              'A finite map of the provenance retained for this record. Solid lines are DERRIDAI relationships; dashed lines are DerridAI application links.',
            )
          : i18n.t(
              'traceability.map_description_model',
              'The normative DERRIDAI 1.0 object model. Select a node to highlight its direct relationships.',
            )
      "
      :close-label="i18n.t('ui.close')"
      @close="diagramOpen = false"
    >
      <div class="diagram-dialog-content">
        <ResearchObjectDiagram
          :nodes="nodes"
          :edges="edges"
          :focus-id="focusId"
          :aria-label="i18n.t('traceability.diagram_label', 'Traceability relationship diagram')"
          @focus="selectFocus"
        />
        <section v-if="focus" class="diagram-selection">
          <div>
            <small>{{ i18n.t("traceability.selected_object", "Selected object") }}</small>
            <strong>{{ typeLabel(focus.object_type) }} · {{ focus.label }}</strong>
            <p>{{ typeDescription(focus.object_type) }}</p>
          </div>
          <UiStatusBadge
            :label="i18n.tf('traceability.connected_count', { count: neighbors.length })"
            tone="neutral"
          />
        </section>
        <div class="diagram-legend" aria-label="Diagram legend">
          <span><i class="solid"></i>{{ i18n.t("traceability.legend_normative", "DERRIDAI relationship") }}</span>
          <span><i class="dashed"></i>{{ i18n.t("traceability.legend_application", "DerridAI application link") }}</span>
          <span><i class="focus"></i>{{ i18n.t("traceability.legend_focus", "Selected object and direct links") }}</span>
        </div>
      </div>
    </UiDialog>
  </section>
</template>

<style scoped>
.traceability-explorer {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}
.traceability-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}
.traceability-head p,
.focus-head small,
.section-head small,
.trace-stage small,
.diagram-selection small {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.045em;
  text-transform: uppercase;
}
.traceability-head h2 {
  margin: 2px 0 0;
  color: var(--text-primary);
  font-size: var(--fs-lg);
  line-height: var(--lh-tight);
}
.traceability-state {
  display: grid;
  gap: 4px;
  padding: var(--space-4);
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.traceability-state strong {
  color: var(--text-primary);
}
.traceability-state.error {
  border-color: var(--tone-danger-edge);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.traceability-orientation {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.traceability-scope {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.traceability-scope > span {
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.traceability-orientation p {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.traceability-overview {
  display: grid;
  justify-items: stretch;
}
.trace-stage {
  display: grid;
  gap: 3px;
  padding: 10px 11px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
}
.trace-stage.record {
  border-color: var(--border-interactive);
  background: var(--surface-selected);
}
.trace-stage strong {
  color: var(--text-primary);
  font-size: var(--fs-sm);
}
.trace-stage span {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  line-height: var(--lh-normal);
}
.trace-connector {
  height: 24px;
  display: grid;
  place-items: center;
  color: var(--text-tertiary);
  font-size: 1rem;
}
.trace-branch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  height: 25px;
  color: var(--text-tertiary);
  font-size: 1rem;
  text-align: center;
}
.trace-branch-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 7px;
}
.traceability-map-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 11px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
}
.traceability-map-action > div {
  min-width: 0;
  display: grid;
  gap: 2px;
}
.traceability-map-action strong {
  color: var(--text-primary);
  font-size: var(--fs-sm);
}
.traceability-map-action span {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  line-height: var(--lh-normal);
}
.traceability-focus-card {
  display: grid;
  gap: 8px;
}
.focus-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: flex-start;
}
.focus-head h3 {
  margin: 2px 0 0;
  color: var(--text-primary);
  font-size: var(--fs-md);
}
.focus-name {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--fs-base);
  font-weight: var(--fw-semibold);
  overflow-wrap: anywhere;
}
.focus-summary,
.focus-explanation {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.focus-explanation {
  color: var(--text-secondary);
}
.focus-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.technical-details {
  border-top: 1px solid var(--border-subtle);
  padding-top: 8px;
}
.technical-details summary {
  width: max-content;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  cursor: pointer;
}
.technical-details dl {
  display: grid;
  gap: 0;
  margin: 8px 0 0;
}
.technical-details dl > div {
  display: grid;
  grid-template-columns: minmax(104px, 0.7fr) minmax(0, 1fr);
  gap: 8px;
  padding: 6px 0;
  border-top: 1px solid var(--border-subtle);
}
.technical-details dt,
.technical-details dd {
  min-width: 0;
  margin: 0;
  font-size: var(--fs-xs);
  overflow-wrap: anywhere;
}
.technical-details dt {
  color: var(--text-tertiary);
}
.technical-details dd {
  color: var(--text-secondary);
}
.technical-details code {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
}
.traceability-connections {
  display: grid;
  gap: 9px;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.section-head h3 {
  margin: 2px 0 0;
  color: var(--text-primary);
  font-size: var(--fs-base);
}
.section-head > span {
  min-width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
}
.relationship-groups {
  display: grid;
  gap: 12px;
}
.relationship-group {
  display: grid;
  gap: 5px;
}
.relationship-group h4 {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.035em;
  text-transform: uppercase;
}
.relationship-row {
  width: 100%;
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  padding: 8px 10px;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
}
.relationship-row:hover {
  border-color: var(--border-interactive);
  background: var(--surface-hover);
}
.relationship-row:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.relationship-copy {
  min-width: 0;
  display: grid;
  gap: 2px;
}
.relationship-copy small {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
}
.relationship-copy strong {
  color: var(--text-primary);
  font-size: var(--fs-sm);
}
.relationship-copy > span {
  min-width: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  overflow-wrap: anywhere;
}
.relationship-arrow {
  color: var(--accent-fg);
  font-size: 1rem;
}
.traceability-none {
  margin: 0;
  padding: 10px 11px;
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-control);
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.diagram-dialog-content {
  display: grid;
  gap: var(--space-4);
}
.diagram-selection {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.diagram-selection > div {
  min-width: 0;
  display: grid;
  gap: 3px;
}
.diagram-selection strong {
  color: var(--text-primary);
  font-size: var(--fs-base);
  overflow-wrap: anywhere;
}
.diagram-selection p {
  margin: 0;
  max-width: 72ch;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.diagram-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 18px;
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
}
.diagram-legend span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.diagram-legend i {
  width: 26px;
  height: 0;
  border-top: 2px solid var(--border-strong);
}
.diagram-legend i.dashed {
  border-top-style: dashed;
}
.diagram-legend i.focus {
  border-top-color: var(--accent);
  border-top-width: 3px;
}
@media (max-width: 380px) {
  .trace-branch-cards {
    grid-template-columns: 1fr;
  }
  .trace-branch {
    display: none;
  }
  .traceability-map-action,
  .diagram-selection {
    align-items: stretch;
    flex-direction: column;
  }
  .technical-details dl > div {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
</style>
