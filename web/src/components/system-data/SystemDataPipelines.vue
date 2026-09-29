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
import PipelineVersionEditorPanel from "../pipelines/PipelineVersionEditorPanel.vue";
import { pipelinesApi } from "../../api/pipelines";
import { pipelineKey } from "../../domain/pipelinePresentation";
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
const route = useRoute();
const router = useRouter();
const catalog = ref<PipelineCatalog | null>(null);
const runs = ref<PipelineRunTrace[]>([]);
const metrics = ref<PipelineOperationalMetrics | null>(null);
const loading = ref(true);
const error = ref("");
const selectedKey = ref(String(route.query.pipeline || ""));
const selectedTraceId = ref(String(route.query.run || ""));
const draft = ref<PipelineDefinition | null>(null);
const validation = ref<PipelineValidationResponse | null>(null);
const saving = ref(false);
const assigning = ref(false);
const cloning = ref(false);

const t = (key: string, fallback: string) => i18n.t(key, fallback);

function syncRouteState() {
  void router.replace({
    name: "pipelines",
    query: {
      ...route.query,
      pipeline: selectedKey.value || undefined,
      run: selectedTraceId.value || undefined,
    },
  });
}

function selectPipeline(key: string) {
  selectedKey.value = key;
  syncRouteState();
}

function selectTrace(runId: string) {
  selectedTraceId.value = runId;
  syncRouteState();
}

function featureForPurpose(purpose: string) {
  const map: Record<string, string> = {
    research: "research",
    evidence_suggestion: "evidence_suggestion.reviewer",
    evidence_recovery: "evidence_recovery",
    vector_store_search: "vector_store_search",
    metadata_prefill: "metadata_prefill",
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
    const [nextCatalog, tracePage, nextMetrics] = await Promise.all([
      pipelinesApi.catalog(),
      pipelinesApi.runs({ limit: 30 }),
      pipelinesApi.metrics({ limit: 250 }),
    ]);
    catalog.value = nextCatalog;
    runs.value = tracePage.runs || [];
    metrics.value = nextMetrics;

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
    selectPipeline(pipelineKey(pipeline));
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

watch(
  () => [route.query.pipeline, route.query.run],
  ([pipeline, run]) => {
    const nextPipeline = String(pipeline || "");
    const nextRun = String(run || "");
    if (
      nextPipeline &&
      nextPipeline !== selectedKey.value &&
      pipelines.value.some((item) => pipelineKey(item) === nextPipeline)
    )
      selectedKey.value = nextPipeline;
    if (
      nextRun &&
      nextRun !== selectedTraceId.value &&
      runs.value.some((item) => item.run_id === nextRun)
    )
      selectedTraceId.value = nextRun;
  },
);

onMounted(load);
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
      <details>
        <summary>{{ t("pipelines.key_terms", "Key terms in plain language") }}</summary>
        <dl>
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
      </details>
    </section>

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
          @select="selectPipeline"
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

      <PipelineComparisonPanel :pipelines="pipelines" />

      <PipelineBenchmarkPanel :pipelines="pipelines" />

      <PipelineOperationsSummary v-if="metrics" :metrics="metrics" />

      <PipelineExecutionHistory
        :runs="runs"
        :selected-run-id="selectedTraceId"
        @select="selectTrace"
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
.concept-guide summary {
  cursor: pointer;
  font-weight: 750;
}
.concept-guide dl {
  display: grid;
  gap: 8px;
  margin: 10px 0 0;
}
.concept-guide dl > div {
  display: grid;
  gap: 2px;
}
.concept-guide dt {
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
