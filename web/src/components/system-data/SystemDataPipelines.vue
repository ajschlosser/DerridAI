<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import PipelineDefinitionsWorkspace from "../pipelines/PipelineDefinitionsWorkspace.vue";
import PipelineExecutionsWorkspace from "../pipelines/PipelineExecutionsWorkspace.vue";
import PipelineOperationsWorkspace from "../pipelines/PipelineOperationsWorkspace.vue";
import PipelineStrategiesWorkspace from "../pipelines/PipelineStrategiesWorkspace.vue";
import PipelineStudioHelpDialog from "../pipelines/PipelineStudioHelpDialog.vue";
import UiButton from "../ui/UiButton.vue";
import UiLoadingState from "../ui/UiLoadingState.vue";
import UiNoticeStack, { type Notice } from "../ui/UiNoticeStack.vue";
import UiPageHeader from "../ui/UiPageHeader.vue";
import UiTabs from "../ui/UiTabs.vue";
import {
  usePipelineStudioNavigation,
  emptyRunFilters,
  type PipelineRunFilters,
  type PipelineStudioSection,
} from "../../features/pipelines/composables/usePipelineStudioNavigation";
import { pipelinesApi } from "../../api/pipelines";
import { pipelineKey } from "../../domain/pipelinePresentation";
import { defaultPipelineKey } from "../../domain/pipelineStudioPresentation";
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

const i18n = useI18nStore();
const catalog = ref<PipelineCatalog | null>(null);
const runs = ref<PipelineRunTrace[]>([]);
const focusedRun = ref<PipelineRunTrace | null>(null);
const metrics = ref<PipelineOperationalMetrics | null>(null);
const loading = ref(true);
const error = ref("");
const runTotal = ref(0);
const runLimit = 25;
const draft = ref<PipelineDefinition | null>(null);
const validation = ref<PipelineValidationResponse | null>(null);
const saving = ref(false);
const assigning = ref(false);
const cloning = ref(false);
const helpOpen = ref(false);

const {
  section,
  selectedPipelineKey: selectedKey,
  pipelineWorkflow: workflow,
  pipelineFilters,
  strategyFilters,
  selectedStrategyId: selectedStrategy,
  selectedRunId: selectedTraceId,
  operationsSection,
  runFilters,
  runOffset,
  selectSection,
  selectPipeline,
  selectWorkflow,
  setPipelineFilters,
  setStrategyFilters,
  selectStrategy,
  selectRun: selectTrace,
  selectOperationsSection,
  syncRouteState,
} = usePipelineStudioNavigation(() => {
  if (catalog.value)
    void loadRuns().catch((exc) => {
      error.value = exc instanceof Error ? exc.message : String(exc);
    });
});

const t = (key: string, fallback: string) => i18n.t(key, fallback);

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
      selectedKey.value = defaultPipelineKey(nextCatalog);
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

// Health → Executions: only the workflow filter is server-supported, so nothing finer is implied.
async function viewExecutions(category: string) {
  runFilters.value = { ...emptyRunFilters(), category };
  runOffset.value = 0;
  selectedTraceId.value = "";
  error.value = "";
  section.value = "executions";
  try {
    await loadRuns();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
  syncRouteState("push");
}

function viewStrategy(strategyId: string) {
  selectStrategy(strategyId);
  selectSection("strategies");
}

function openConfiguration(key: string) {
  selectPipeline(key);
}

const studioTabs = computed(() => [
  { id: "pipelines", label: t("pipelines.studio_pipelines", "Pipelines") },
  { id: "strategies", label: t("pipelines.studio_strategies", "Strategies") },
  { id: "executions", label: t("pipelines.studio_executions", "Executions") },
  { id: "operations", label: t("pipelines.studio_operations", "Operations") },
]);
const notices = computed<Notice[]>(() =>
  error.value ? [{ id: "pipeline-error", tone: "error", text: error.value }] : [],
);

onMounted(() => {
  void load();
});
</script>

<template>
  <div class="pipeline-studio">
    <UiPageHeader
      :kicker="t('pipelines.studio_kicker', 'AI & Automation')"
      :title="t('pipelines.title', 'Pipeline Studio')"
      :description="
        t(
          'pipelines.help',
          'Inspect, version, compare, and monitor the pipelines DerridAI uses for retrieval, evidence, metadata, memory, and corpus processing.',
        )
      "
      title-id="pipeline-studio-title"
      :actions-label="t('pipelines.studio_actions', 'Pipeline Studio actions')"
    >
      <template #actions>
        <UiButton
          icon="refresh"
          :label="t('common.refresh', 'Refresh')"
          :disabled="loading"
          @click="load"
        />
        <UiButton
          icon="help"
          :label="t('pipelines.help_button', 'Help')"
          :expanded="helpOpen"
          @click="helpOpen = true"
        />
      </template>
      <template #meta>
        <div class="pipeline-studio-nav">
          <UiTabs
            :tabs="studioTabs"
            :model-value="section"
            :tablist-label="t('pipelines.title', 'Pipeline Studio')"
            id-prefix="pipeline"
            @update:model-value="selectSection($event as PipelineStudioSection)"
          />
        </div>
      </template>
    </UiPageHeader>

    <UiNoticeStack
      v-if="notices.length"
      :items="notices"
      :label="t('pipelines.studio_notices', 'Pipeline Studio messages')"
      @dismiss="error = ''"
    />
    <UiLoadingState
      v-if="loading && !catalog"
      :label="t('pipelines.loading', 'Loading pipelines…')"
    />

    <template v-else-if="catalog">
      <PipelineDefinitionsWorkspace
        v-if="section === 'pipelines'"
        :pipelines="pipelines"
        :strategies="strategies"
        :assignments="assignments"
        :purposes="purposes"
        :vocabulary="vocabulary"
        :selected-key="selectedKey"
        :workflow="workflow"
        :filters="pipelineFilters"
        :selected-pipeline="selectedPipeline"
        :selected-purpose="selectedPurpose"
        :selected-assignment="selectedAssignment"
        :assigned="isSelectedAssigned"
        :can-assign="canAssignSelected"
        :assigning="assigning"
        :cloning="cloning"
        :draft="draft"
        :draft-purpose="purposeFor(draft)"
        :validation="validation"
        :saving="saving"
        @select="selectPipeline"
        @update:workflow="selectWorkflow"
        @update:filters="setPipelineFilters"
        @update:draft="draft = $event"
        @clone="beginClone"
        @assign="assignSelected"
        @reset-assignment="resetSelectedAssignment"
        @cancel="draft = null"
        @validate="validateDraft"
        @save="saveDraft"
      />

      <PipelineStrategiesWorkspace
        v-else-if="section === 'strategies'"
        :strategies="strategies"
        :pipelines="pipelines"
        :purposes="purposes"
        :vocabulary="vocabulary"
        :selected-strategy-id="selectedStrategy"
        :filters="strategyFilters"
        @select-strategy="selectStrategy"
        @open-pipeline="selectPipeline"
        @update:filters="setStrategyFilters"
      />

      <PipelineExecutionsWorkspace
        v-else-if="section === 'executions'"
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

      <PipelineOperationsWorkspace
        v-else
        :operation="operationsSection"
        :pipelines="pipelines"
        :metrics="metrics"
        :strategies="strategies"
        :purposes="purposes"
        :vocabulary="vocabulary"
        @update:operation="selectOperationsSection"
        @view-executions="viewExecutions"
        @view-strategy="viewStrategy"
        @open-pipeline="selectPipeline"
      />
    </template>

    <PipelineStudioHelpDialog :open="helpOpen" @close="helpOpen = false" />
  </div>
</template>

<style scoped>
.pipeline-studio {
  --pipeline-studio-sticky-top: calc(var(--ref-topbar, 60px) + var(--space-3));
  --pipeline-studio-pane-max-height: min(
    calc(100dvh - var(--pipeline-studio-sticky-top) - var(--space-3)),
    960px
  );
  display: grid;
  gap: var(--space-4);
}
.pipeline-studio-nav {
  margin-top: var(--space-2);
}
</style>
