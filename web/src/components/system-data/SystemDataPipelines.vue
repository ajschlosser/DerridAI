<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppIcon from "../AppIcon.vue";
import PipelineDefinitionBrowser from "../pipelines/PipelineDefinitionBrowser.vue";
import PipelineDefinitionDetail from "../pipelines/PipelineDefinitionDetail.vue";
import PipelineExecutionHistory from "../pipelines/PipelineExecutionHistory.vue";
import PipelineBenchmarkPanel from "../pipelines/PipelineBenchmarkPanel.vue";
import PipelineComparisonPanel from "../pipelines/PipelineComparisonPanel.vue";
import PipelineOperationsSummary from "../pipelines/PipelineOperationsSummary.vue";
import PipelineStrategyCatalog from "../pipelines/PipelineStrategyCatalog.vue";
import PipelineVersionEditorPanel from "../pipelines/PipelineVersionEditorPanel.vue";
import type { PipelineRunFilters } from "../pipelines/PipelineExecutionHistory.vue";
import { pipelinesApi } from "../../api/pipelines";
import { pipelineKey } from "../../domain/pipelinePresentation";
import { purposeById } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAssignment,
  PipelineCatalog,
  PipelineDefinition,
  PipelineOperationalMetrics,
  PipelineRunTrace,
  PipelineValidationResponse,
} from "../../types/pipelines";

const sections = ["pipelines", "strategies", "executions", "operations"] as const;
const i18n = useI18nStore();
const route = useRoute();
const router = useRouter();
const catalog = ref<PipelineCatalog | null>(null);
const runs = ref<PipelineRunTrace[]>([]);
const focusedRun = ref<PipelineRunTrace | null>(null);
const metrics = ref<PipelineOperationalMetrics | null>(null);
const loading = ref(true);
const error = ref("");
const section = ref<(typeof sections)[number]>("pipelines");
const selectedKey = ref("");
const workflow = ref("");
const selectedStrategy = ref("");
const selectedTraceId = ref("");
const runTotal = ref(0);
const runLimit = 25;
const runFilters = ref<PipelineRunFilters>({
  query: "",
  category: "",
  feature: "",
  pipelineId: "",
  status: "",
  owner: "",
});
const runOffset = ref(0);
const draft = ref<PipelineDefinition | null>(null);
const validation = ref<PipelineValidationResponse | null>(null);
const saving = ref(false);
const assigning = ref(false);
const cloning = ref(false);

const t = (key: string, fallback: string) => i18n.t(key, fallback);

function readRoute() {
  const requested = String(route.query.section || "");
  section.value = sections.includes(requested as (typeof sections)[number])
    ? (requested as (typeof sections)[number])
    : "pipelines";
  selectedKey.value = String(route.query.pipeline || "");
  workflow.value = String(route.query.workflow || "");
  selectedStrategy.value = String(route.query.strategy || "");
  selectedTraceId.value = String(route.query.run || "");
  runFilters.value = {
    query: String(route.query.q || ""),
    category: String(route.query.run_workflow || ""),
    feature: String(route.query.feature || ""),
    pipelineId: String(route.query.pipeline_id || ""),
    status: String(route.query.status || ""),
    owner: String(route.query.owner || ""),
  };
  runOffset.value = Math.max(0, Number(route.query.offset || 0) || 0);
}

function syncRouteState() {
  const query: Record<string, string | string[] | undefined> = {
    ...route.query,
    section: section.value === "pipelines" ? undefined : section.value,
    pipeline: selectedKey.value || undefined,
    workflow: workflow.value || undefined,
    strategy: selectedStrategy.value || undefined,
    run: selectedTraceId.value || undefined,
    q: runFilters.value.query || undefined,
    run_workflow: runFilters.value.category || undefined,
    feature: runFilters.value.feature || undefined,
    pipeline_id: runFilters.value.pipelineId || undefined,
    status: runFilters.value.status || undefined,
    owner: runFilters.value.owner || undefined,
    offset: runOffset.value ? String(runOffset.value) : undefined,
  };
  for (const key of Object.keys(query)) {
    if (query[key] === undefined || query[key] === "") delete query[key];
  }
  const current = route.query;
  const same =
    Object.keys(query).length === Object.keys(current).length &&
    Object.entries(query).every(
      ([key, value]) => String(current[key] || "") === String(value || ""),
    );
  if (!same) void router.replace({ name: "pipelines", query });
}

function selectSection(next: (typeof sections)[number]) {
  section.value = next;
  syncRouteState();
}

function selectPipeline(key: string) {
  selectedKey.value = key;
  section.value = "pipelines";
  syncRouteState();
}

function selectTrace(runId: string) {
  selectedTraceId.value = runId;
  syncRouteState();
}

function selectWorkflow(category: string) {
  workflow.value = category;
  syncRouteState();
}

function selectStrategy(strategyId: string) {
  selectedStrategy.value = strategyId;
  syncRouteState();
}

const pipelines = computed(() => catalog.value?.pipelines || []);
const strategies = computed(() => catalog.value?.strategies || []);
const assignments = computed(() => catalog.value?.assignments || []);
const purposes = computed(() => catalog.value?.purposes || []);
const vocabulary = computed(
  () =>
    catalog.value?.vocabulary || {
      categories: [],
      guarantees: [],
      phases: [],
      scholarly_effects: [],
      effect_notes: [],
    },
);
function purposeFor(pipeline: PipelineDefinition | null) {
  return pipeline ? purposeById(purposes.value, pipeline.purpose) : null;
}
const selectedPurpose = computed(() => purposeFor(selectedPipeline.value));
const selectedPipeline = computed(() => {
  const match = pipelines.value.find((item) => pipelineKey(item) === selectedKey.value);
  return match || pipelines.value[0] || null;
});
const selectedAssignment = computed(() => {
  const feature = selectedPurpose.value?.consuming_feature;
  if (!feature) return null;
  return assignments.value.find((item) => item.feature === feature) || null;
});
const isSelectedAssigned = computed(() => {
  const pipeline = selectedPipeline.value;
  const assignment = selectedAssignment.value;
  return Boolean(
    pipeline &&
      assignment &&
      assignment.pipeline_id === pipeline.pipeline_id &&
      assignment.pipeline_version === pipeline.version,
  );
});
const canAssignSelected = computed(() => {
  const pipeline = selectedPipeline.value;
  return Boolean(
    pipeline &&
      pipeline.status === "active" &&
      pipeline.runtime_support?.supported &&
      selectedPurpose.value,
  );
});

async function loadRuns() {
  const tracePage = await pipelinesApi.runs({
    category: runFilters.value.category || undefined,
    feature: runFilters.value.feature || undefined,
    owner: runFilters.value.owner || undefined,
    pipelineId: runFilters.value.pipelineId || undefined,
    status: runFilters.value.status || undefined,
    query: runFilters.value.query || undefined,
    limit: runLimit,
    offset: runOffset.value,
  });
  runs.value = tracePage.runs || [];
  runTotal.value = tracePage.total ?? runs.value.length;
  if (selectedTraceId.value && !runs.value.some((item) => item.run_id === selectedTraceId.value)) {
    try {
      focusedRun.value = (await pipelinesApi.run(selectedTraceId.value)).run;
    } catch {
      focusedRun.value = null;
      selectedTraceId.value = runs.value[0]?.run_id || "";
    }
  } else if (!selectedTraceId.value && runs.value.length) {
    selectedTraceId.value = runs.value[0].run_id;
    focusedRun.value = runs.value[0];
  } else {
    focusedRun.value = runs.value.find((item) => item.run_id === selectedTraceId.value) || null;
  }
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [nextCatalog, nextMetrics] = await Promise.all([
      pipelinesApi.catalog(),
      pipelinesApi.metrics({ limit: 250 }),
    ]);
    catalog.value = nextCatalog;
    metrics.value = nextMetrics;
    await loadRuns();

    if (
      !selectedKey.value ||
      !nextCatalog.pipelines.some((item) => pipelineKey(item) === selectedKey.value)
    ) {
      const assignedResearch = nextCatalog.assignments.find((item) => item.feature === "research");
      const preferred = nextCatalog.pipelines.find(
        (item) =>
          item.pipeline_id === assignedResearch?.pipeline_id &&
          item.version === assignedResearch?.pipeline_version,
      );
      const fallback = preferred || nextCatalog.pipelines[0];
      selectedKey.value = fallback ? pipelineKey(fallback) : "";
    }
    syncRouteState();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

async function beginClone() {
  const source = selectedPipeline.value;
  if (!source || cloning.value) return;

  cloning.value = true;
  error.value = "";
  try {
    const prepared = await pipelinesApi.cloneDraft(source.pipeline_id, source.version);
    draft.value = prepared.pipeline;
    validation.value = null;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    cloning.value = false;
  }
}

async function validateDraft() {
  if (!draft.value) return;
  validation.value = await pipelinesApi.validate(draft.value);
}

async function saveDraft() {
  if (!draft.value || saving.value) return;
  saving.value = true;
  error.value = "";
  try {
    const checked = await pipelinesApi.validate(draft.value);
    validation.value = checked;
    if (!checked.validation.valid) return;
    const saved = await pipelinesApi.createDefinition(draft.value);
    draft.value = null;
    await load();
    selectPipeline(pipelineKey(saved.pipeline));
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    saving.value = false;
  }
}

async function assignSelected() {
  const pipeline = selectedPipeline.value;
  const purpose = selectedPurpose.value;
  if (!pipeline || !purpose || !canAssignSelected.value || assigning.value) return;

  const feature = purpose.consuming_feature;
  const current = assignments.value.find((item) => item.feature === feature);
  const assignment: PipelineAssignment = {
    feature,
    pipeline_id: pipeline.pipeline_id,
    pipeline_version: pipeline.version,
    scope: purpose.assignment_scope,
    scope_id: null,
    override_allowed: current?.override_allowed ?? purpose.override_allowed,
    source: "system",
  };

  assigning.value = true;
  error.value = "";
  try {
    await pipelinesApi.setAssignment(assignment);
    await load();
    selectPipeline(pipelineKey(pipeline));
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    assigning.value = false;
  }
}

async function resetSelectedAssignment() {
  const feature = selectedPurpose.value?.consuming_feature;
  if (!feature || assigning.value) return;

  assigning.value = true;
  error.value = "";
  try {
    await pipelinesApi.resetAssignment(feature);
    await load();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    assigning.value = false;
  }
}

async function applyRunFilters(filters: PipelineRunFilters) {
  runFilters.value = filters;
  runOffset.value = 0;
  selectedTraceId.value = "";
  error.value = "";
  try {
    await loadRuns();
    syncRouteState();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}

async function changeRunPage(offset: number) {
  runOffset.value = offset;
  error.value = "";
  try {
    await loadRuns();
    syncRouteState();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}

async function deleteRun(runId: string) {
  if (
    !window.confirm(
      t(
        "pipelines.delete_run_confirm",
        "Delete this execution from history? The saved pipeline version is not affected.",
      ),
    )
  ) {
    return;
  }
  error.value = "";
  try {
    await pipelinesApi.deleteRun(runId);
    if (selectedTraceId.value === runId) selectedTraceId.value = "";
    await Promise.all([
      loadRuns(),
      pipelinesApi.metrics({ limit: 250 }).then((next) => (metrics.value = next)),
    ]);
    syncRouteState();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}

async function clearHistory() {
  if (
    !window.confirm(
      t(
        "pipelines.clear_history_confirm",
        "Delete every execution trace? Pipeline definitions and assignments stay in place.",
      ),
    )
  ) {
    return;
  }
  error.value = "";
  try {
    await pipelinesApi.clearRuns();
    selectedTraceId.value = "";
    focusedRun.value = null;
    runOffset.value = 0;
    await Promise.all([
      loadRuns(),
      pipelinesApi.metrics({ limit: 250 }).then((next) => (metrics.value = next)),
    ]);
    syncRouteState();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}

function openConfiguration(key: string) {
  selectPipeline(key);
}

const sectionLabels = computed<Record<(typeof sections)[number], string>>(() => ({
  pipelines: t("pipelines.studio_pipelines", "Pipelines"),
  strategies: t("pipelines.studio_strategies", "Strategies"),
  executions: t("pipelines.studio_executions", "Executions"),
  operations: t("pipelines.studio_operations", "Operations"),
}));

watch(
  () => route.query,
  () => {
    const previous = JSON.stringify({
      filters: runFilters.value,
      offset: runOffset.value,
      section: section.value,
    });
    readRoute();
    const next = JSON.stringify({
      filters: runFilters.value,
      offset: runOffset.value,
      section: section.value,
    });
    if (previous !== next && catalog.value)
      void loadRuns().catch((exc) => {
        error.value = exc instanceof Error ? exc.message : String(exc);
      });
  },
);

onMounted(() => {
  readRoute();
  void load();
});
</script>

<template>
  <div class="pipeline-workspace">
    <header class="workspace-heading">
      <div>
        <h1>{{ t("pipelines.title", "Pipeline Studio") }}</h1>
        <p>
          {{
            t(
              "pipelines.help",
              "Inspect and version the registered retrieval, reranking, validation, and model chains DerridAI can execute.",
            )
          }}
        </p>
      </div>
      <button class="btn" type="button" :disabled="loading" @click="load">
        <AppIcon name="refresh" />
        {{ t("common.refresh", "Refresh") }}
      </button>
    </header>

    <section class="concept-guide" aria-labelledby="pipeline-guide-title">
      <div>
        <strong id="pipeline-guide-title">
          {{ t("pipelines.plain_intro_title", "A pipeline is DerridAI’s research recipe") }}
        </strong>
        <p>
          {{
            t(
              "pipelines.plain_intro",
              "It is a saved sequence of steps that determines how DerridAI finds candidate passages, orders them, checks provenance, prepares evidence, and—when applicable—asks a language model to produce or evaluate an answer.",
            )
          }}
        </p>
      </div>
      <div class="plain-language-guide">
        <h2>{{ t("pipelines.key_terms", "Key terms in plain language") }}</h2>
        <p class="guide-note">
          {{
            t(
              "pipelines.key_terms_help",
              "Use these quick definitions to read the diagram and understand what the pipeline can and cannot guarantee.",
            )
          }}
        </p>
        <dl>
          <div>
            <dt>{{ t("pipelines.used_for", "Used for") }}</dt>
            <dd>
              {{
                t(
                  "pipelines.term_used_for_help",
                  "What the whole pipeline is for—Research, Evidence, Search, Metadata, Memory or Corpus processing—and which part of DerridAI runs it. A version keeps its purpose for life.",
                )
              }}
            </dd>
          </div>
          <div>
            <dt>{{ t("pipelines.term_stage", "Stage") }}</dt>
            <dd>
              {{
                t(
                  "pipelines.term_stage_help",
                  "One step in the recipe, such as retrieving passages, reranking them, checking provenance, or generating an answer.",
                )
              }}
            </dd>
          </div>
          <div>
            <dt>{{ t("pipelines.term_strategy", "Strategy") }}</dt>
            <dd>
              {{
                t(
                  "pipelines.term_strategy_help",
                  "The approved operation a stage performs. In technical terms, it is a registered server-side implementation with a known input, output, and configuration schema.",
                )
              }}
            </dd>
          </div>
          <div>
            <dt>{{ t("pipelines.scholarly_effect", "Scholarly effect") }}</dt>
            <dd>
              {{
                t(
                  "pipelines.term_scholarly_effect_help",
                  "What a stage establishes about evidence, support or provenance. Retrieval, reranking and diversity only order candidates; they never make a passage evidence.",
                )
              }}
            </dd>
          </div>
          <div>
            <dt>{{ t("pipelines.term_edge", "Connection / edge") }}</dt>
            <dd>
              {{
                t(
                  "pipelines.term_edge_help",
                  "A direction from one stage to another. Normal edges describe the usual path; fallback edges describe what to do when a stage is empty, unavailable, timed out, or fails.",
                )
              }}
            </dd>
          </div>
          <div>
            <dt>{{ t("pipelines.term_assignment", "Assignment") }}</dt>
            <dd>
              {{
                t(
                  "pipelines.term_assignment_help",
                  "The version DerridAI uses by default for a feature. Saving a new version does not change the assignment; activation is a separate, explicit step.",
                )
              }}
            </dd>
          </div>
          <div>
            <dt>{{ t("pipelines.term_trace", "Execution trace") }}</dt>
            <dd>
              {{
                t(
                  "pipelines.term_trace_help",
                  "An audit record of what actually ran: the exact version, stage path, fallbacks, models, candidate counts, and timings. This lets you distinguish the intended recipe from the runtime history.",
                )
              }}
            </dd>
          </div>
        </dl>
      </div>
    </section>

    <p v-if="error" class="error-banner" role="alert">{{ error }}</p>
    <div v-if="loading && !catalog" class="loading-card" role="status">
      {{ t("common.loading", "Loading…") }}
    </div>

    <template v-else-if="catalog">
      <div class="studio-tabs" role="tablist" :aria-label="t('pipelines.title', 'Pipeline Studio')">
        <button
          v-for="item in sections"
          :id="`pipeline-tab-${item}`"
          :key="item"
          type="button"
          role="tab"
          :aria-selected="section === item"
          :aria-controls="`pipeline-panel-${item}`"
          :class="{ selected: section === item }"
          @click="selectSection(item)"
        >
          {{ sectionLabels[item] }}
        </button>
      </div>

      <section
        v-if="section === 'pipelines'"
        id="pipeline-panel-pipelines"
        class="studio-grid"
        role="tabpanel"
        aria-labelledby="pipeline-tab-pipelines"
        :aria-label="t('pipelines.definitions', 'Pipeline definitions')"
      >
        <PipelineDefinitionBrowser
          :pipelines="pipelines"
          :assignments="assignments"
          :purposes="purposes"
          :vocabulary="vocabulary"
          :selected-key="selectedKey"
          :workflow="workflow"
          @select="selectPipeline"
          @update:workflow="selectWorkflow"
        />
        <PipelineDefinitionDetail
          v-if="selectedPipeline"
          :pipeline="selectedPipeline"
          :strategies="strategies"
          :purpose="selectedPurpose"
          :purposes="purposes"
          :vocabulary="vocabulary"
          :assignment="selectedAssignment"
          :assigned="isSelectedAssigned"
          :can-assign="canAssignSelected"
          :assigning="assigning"
          :cloning="cloning"
          @clone="beginClone"
          @assign="assignSelected"
          @reset-assignment="resetSelectedAssignment"
        />
      </section>

      <PipelineVersionEditorPanel
        v-if="draft && section === 'pipelines'"
        v-model="draft"
        :strategies="strategies"
        :purpose="purposeFor(draft)"
        :vocabulary="vocabulary"
        :validation="validation"
        :saving="saving"
        @cancel="draft = null"
        @validate="validateDraft"
        @save="saveDraft"
      />

      <section
        v-else-if="section === 'strategies'"
        id="pipeline-panel-strategies"
        role="tabpanel"
        aria-labelledby="pipeline-tab-strategies"
      >
        <PipelineStrategyCatalog
          :strategies="strategies"
          :pipelines="pipelines"
          :purposes="purposes"
          :vocabulary="vocabulary"
          :selected-strategy-id="selectedStrategy"
          @select-strategy="selectStrategy"
          @open-pipeline="selectPipeline"
        />
      </section>

      <section
        v-else-if="section === 'executions'"
        id="pipeline-panel-executions"
        role="tabpanel"
        aria-labelledby="pipeline-tab-executions"
      >
        <PipelineExecutionHistory
          :runs="runs"
          :pipelines="pipelines"
          :purposes="purposes"
          :vocabulary="vocabulary"
          :strategies="strategies"
          :selected-run-id="selectedTraceId"
          :focused-run="focusedRun"
          :total="runTotal"
          :limit="runLimit"
          :offset="runOffset"
          :filters="runFilters"
          @select="selectTrace"
          @apply="applyRunFilters"
          @page="changeRunPage"
          @delete-run="deleteRun"
          @clear-history="clearHistory"
          @open-configuration="openConfiguration"
        />
      </section>

      <section
        v-else
        id="pipeline-panel-operations"
        class="operations-stack"
        role="tabpanel"
        aria-labelledby="pipeline-tab-operations"
      >
        <PipelineComparisonPanel :pipelines="pipelines" />
        <PipelineBenchmarkPanel :pipelines="pipelines" />
        <PipelineOperationsSummary
          v-if="metrics"
          :metrics="metrics"
          :strategies="strategies"
          :purposes="purposes"
          :vocabulary="vocabulary"
        />
      </section>
    </template>
  </div>
</template>

<style scoped>
.pipeline-workspace {
  display: grid;
  gap: 18px;
}
.workspace-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.workspace-heading h1 {
  margin: 0;
  font-size: 1.25rem;
}
.workspace-heading p {
  max-width: 780px;
  margin: 5px 0 0;
  color: var(--muted);
  line-height: 1.5;
}
.workspace-heading :deep(svg) {
  width: 15px;
  height: 15px;
}
.concept-guide {
  display: grid;
  gap: 9px;
  padding: 13px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--soft);
}
.concept-guide > div {
  display: grid;
  gap: 3px;
}
.concept-guide strong,
.concept-guide summary {
  font-size: 0.82rem;
}
.concept-guide p,
.concept-guide dd {
  margin: 0;
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.5;
}
.plain-language-guide {
  display: grid;
  gap: 8px;
  padding-top: 4px;
}
.plain-language-guide h2 {
  margin: 0;
  font-size: 0.82rem;
  font-weight: 750;
}
.guide-note {
  margin: 0;
}
.plain-language-guide dl {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  margin: 0;
}
.plain-language-guide dl > div {
  display: grid;
  gap: 2px;
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
}
.plain-language-guide dt {
  font-size: 0.77rem;
  font-weight: 750;
}
.error-banner,
.loading-card {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--soft);
}
.error-banner {
  border-color: color-mix(in srgb, var(--line) 60%, currentColor);
}
.studio-grid {
  display: grid;
  grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}
.studio-tabs {
  display: flex;
  gap: 6px;
  padding: 4px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--soft);
}
.studio-tabs button {
  min-height: 36px;
  padding: 6px 12px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 0.82rem;
  cursor: pointer;
}
.studio-tabs button.selected {
  background: var(--card);
  font-weight: 750;
}
.studio-tabs button:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}
.operations-stack {
  display: grid;
  gap: 14px;
}
@media (max-width: 960px) {
  .studio-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 680px) {
  .workspace-heading {
    display: grid;
  }
}
</style>
