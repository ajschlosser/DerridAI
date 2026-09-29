<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import PipelineDefinitionBrowser from "../pipelines/PipelineDefinitionBrowser.vue";
import PipelineDefinitionDetail from "../pipelines/PipelineDefinitionDetail.vue";
import PipelineExecutionHistory from "../pipelines/PipelineExecutionHistory.vue";
import PipelineVersionEditorPanel from "../pipelines/PipelineVersionEditorPanel.vue";
import { pipelinesApi } from "../../api/pipelines";
import { pipelineKey } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAssignment,
  PipelineCatalog,
  PipelineDefinition,
  PipelineRunTrace,
  PipelineValidationResponse,
} from "../../types/pipelines";

const i18n = useI18nStore();
const catalog = ref<PipelineCatalog | null>(null);
const runs = ref<PipelineRunTrace[]>([]);
const loading = ref(true);
const error = ref("");
const selectedKey = ref("");
const selectedTraceId = ref("");
const draft = ref<PipelineDefinition | null>(null);
const validation = ref<PipelineValidationResponse | null>(null);
const saving = ref(false);
const assigning = ref(false);
const cloning = ref(false);

const t = (key: string, fallback: string) => i18n.t(key, fallback);

function featureForPurpose(purpose: string) {
  const map: Record<string, string> = {
    research: "research",
    evidence_suggestion: "evidence_suggestion.reviewer",
    metadata_precedents: "metadata_precedents",
    claim_memory: "claim_memory",
    response_memory: "response_memory",
  };
  return map[purpose] || "";
}

const pipelines = computed(() => catalog.value?.pipelines || []);
const strategies = computed(() => catalog.value?.strategies || []);
const assignments = computed(() => catalog.value?.assignments || []);
const selectedPipeline = computed(() => {
  const match = pipelines.value.find((item) => pipelineKey(item) === selectedKey.value);
  return match || pipelines.value[0] || null;
});
const selectedAssignment = computed(() => {
  const pipeline = selectedPipeline.value;
  if (!pipeline) return null;
  const feature = featureForPurpose(pipeline.purpose);
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
      featureForPurpose(pipeline.purpose),
  );
});

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [nextCatalog, tracePage] = await Promise.all([
      pipelinesApi.catalog(),
      pipelinesApi.runs({ limit: 30 }),
    ]);
    catalog.value = nextCatalog;
    runs.value = tracePage.runs || [];

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

    if (
      runs.value.length &&
      (!selectedTraceId.value || !runs.value.some((item) => item.run_id === selectedTraceId.value))
    ) {
      selectedTraceId.value = runs.value[0].run_id;
    }
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
    selectedKey.value = pipelineKey(saved.pipeline);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    saving.value = false;
  }
}

async function assignSelected() {
  const pipeline = selectedPipeline.value;
  if (!pipeline || !canAssignSelected.value || assigning.value) return;

  const feature = featureForPurpose(pipeline.purpose);
  const current = assignments.value.find((item) => item.feature === feature);
  const assignment: PipelineAssignment = {
    feature,
    pipeline_id: pipeline.pipeline_id,
    pipeline_version: pipeline.version,
    scope: "system",
    scope_id: null,
    override_allowed: current?.override_allowed ?? feature === "research",
    source: "system",
  };

  assigning.value = true;
  error.value = "";
  try {
    await pipelinesApi.setAssignment(assignment);
    await load();
    selectedKey.value = pipelineKey(pipeline);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    assigning.value = false;
  }
}

async function resetSelectedAssignment() {
  const pipeline = selectedPipeline.value;
  if (!pipeline || assigning.value) return;
  const feature = featureForPurpose(pipeline.purpose);
  if (!feature) return;

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

onMounted(load);
</script>

<template>
  <div class="pipeline-workspace">
    <header class="workspace-heading">
      <div>
        <h2>{{ t("pipelines.title", "Pipeline Studio") }}</h2>
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

    <p v-if="error" class="error-banner" role="alert">{{ error }}</p>
    <div v-if="loading && !catalog" class="loading-card" role="status">
      {{ t("common.loading", "Loading…") }}
    </div>

    <template v-else-if="catalog">
      <section class="studio-grid" :aria-label="t('pipelines.definitions', 'Pipeline definitions')">
        <PipelineDefinitionBrowser
          :pipelines="pipelines"
          :assignments="assignments"
          :selected-key="selectedKey"
          @select="selectedKey = $event"
        />
        <PipelineDefinitionDetail
          v-if="selectedPipeline"
          :pipeline="selectedPipeline"
          :strategies="strategies"
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
        v-if="draft"
        v-model="draft"
        :strategies="strategies"
        :validation="validation"
        :saving="saving"
        @cancel="draft = null"
        @validate="validateDraft"
        @save="saveDraft"
      />

      <PipelineExecutionHistory
        :runs="runs"
        :selected-run-id="selectedTraceId"
        @select="selectedTraceId = $event"
      />
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
.workspace-heading h2 {
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
  grid-template-columns: minmax(220px, 0.34fr) minmax(0, 1fr);
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
