<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { chromaApi } from "../../api/chroma";
import { pipelinesApi } from "../../api/pipelines";
import { pipelineKey } from "../../domain/pipelinePresentation";
import PipelineBenchmarkCaseList from "./PipelineBenchmarkCaseList.vue";
import PipelineComparisonResult from "./PipelineComparisonResult.vue";
import UiButton from "../ui/UiButton.vue";
import UiDialog from "../ui/UiDialog.vue";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  ResearchPipelineBenchmarkCase,
  ResearchPipelineBenchmarkRun,
} from "../../types/pipelines";
import type { VectorCollection } from "../../types/vector";

const props = defineProps<{
  pipelines: PipelineDefinition[];
}>();
const emit = defineEmits<{ openPipeline: [key: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const loaded = ref(false);
const createOpen = ref(false);
const loading = ref(false);
const creating = ref(false);
const running = ref(false);
const error = ref("");

const collections = ref<VectorCollection[]>([]);
const cases = ref<ResearchPipelineBenchmarkCase[]>([]);
const selectedCaseKey = ref("");

const caseId = ref("");
const caseVersion = ref(1);
const prompt = ref("");
const instructions = ref("");
const collection = ref("");
const notes = ref("");

const leftKey = ref("");
const rightKey = ref("");
const benchmark = ref<ResearchPipelineBenchmarkRun | null>(null);

const researchPipelines = computed(() =>
  props.pipelines.filter(
    (pipeline) =>
      pipeline.purpose === "research" &&
      pipeline.status !== "disabled" &&
      pipeline.runtime_support?.supported !== false,
  ),
);

function definition(key: string) {
  return researchPipelines.value.find((pipeline) => pipelineKey(pipeline) === key) || null;
}

function benchmarkCaseKey(item: ResearchPipelineBenchmarkCase) {
  return `${item.case_id}@${item.version}`;
}

const selectedCase = computed(
  () => cases.value.find((item) => benchmarkCaseKey(item) === selectedCaseKey.value) || null,
);

function initializePipelineChoices() {
  if (!leftKey.value && researchPipelines.value.length) {
    leftKey.value = pipelineKey(researchPipelines.value[0]);
  }
  if (!rightKey.value && researchPipelines.value.length) {
    rightKey.value = pipelineKey(researchPipelines.value[1] || researchPipelines.value[0]);
  }
}

async function loadWorkspace() {
  if (loaded.value || loading.value) return;
  loading.value = true;
  error.value = "";
  initializePipelineChoices();
  try {
    const [availableCollections, casePage] = await Promise.all([
      chromaApi.collections(),
      pipelinesApi.researchBenchmarkCases({ limit: 200 }),
    ]);
    collections.value = availableCollections;
    cases.value = casePage.cases;
    if (!collection.value && collections.value.length) {
      collection.value = collections.value[0].name;
    }
    if (!selectedCaseKey.value && cases.value.length) {
      selectedCaseKey.value = benchmarkCaseKey(cases.value[0]);
    }
    loaded.value = true;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

onMounted(() => void loadWorkspace());

async function createCase() {
  if (
    creating.value ||
    !caseId.value.trim() ||
    !prompt.value.trim() ||
    !collection.value ||
    caseVersion.value < 1
  ) {
    return;
  }

  creating.value = true;
  error.value = "";
  benchmark.value = null;
  try {
    const response = await pipelinesApi.createResearchBenchmarkCase({
      case_id: caseId.value.trim(),
      version: caseVersion.value,
      prompt: prompt.value.trim(),
      instructions: instructions.value.trim() || null,
      source_collection: collection.value,
      query_decomposition: false,
      notes: notes.value.trim() || null,
    });
    const saved = response.case;
    cases.value = [
      saved,
      ...cases.value.filter((item) => benchmarkCaseKey(item) !== benchmarkCaseKey(saved)),
    ];
    selectedCaseKey.value = benchmarkCaseKey(saved);
    createOpen.value = false;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    creating.value = false;
  }
}

async function runBenchmark() {
  const selected = selectedCase.value;
  const left = definition(leftKey.value);
  const right = definition(rightKey.value);
  if (!selected || !left || !right || running.value) return;

  running.value = true;
  error.value = "";
  benchmark.value = null;
  try {
    const response = await pipelinesApi.runResearchBenchmark({
      case_id: selected.case_id,
      case_version: selected.version,
      left: { pipeline_id: left.pipeline_id, version: left.version },
      right: { pipeline_id: right.pipeline_id, version: right.version },
    });
    benchmark.value = response.benchmark;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    running.value = false;
  }
}

const runDisabledReason = computed(() => {
  if (running.value) return "";
  if (!selectedCase.value)
    return t("pipelines.benchmark_reason_case", "Choose a saved benchmark case first.");
  if (!researchPipelines.value.length)
    return t(
      "pipelines.compare_reason_no_pipelines",
      "No executable Research pipelines are available.",
    );
  return "";
});
const createDisabledReason = computed(() => {
  if (creating.value) return "";
  if (!caseId.value.trim())
    return t("pipelines.benchmark_reason_case_id", "Enter a case ID first.");
  if (caseVersion.value < 1)
    return t("pipelines.benchmark_reason_version", "The case version must be at least 1.");
  if (!prompt.value.trim())
    return t("pipelines.compare_reason_question", "Enter a research question first.");
  if (!collection.value)
    return t("pipelines.compare_reason_collection", "Choose a corpus collection first.");
  return "";
});
</script>

<template>
  <section class="benchmark-workspace" aria-labelledby="pipeline-benchmark-title">
    <header class="workspace-heading">
      <div>
        <h3 id="pipeline-benchmark-title">
          {{ t("pipelines.benchmark_title", "Benchmark Research pipelines") }}
        </h3>
        <p>
          {{
            t(
              "pipelines.benchmark_help",
              "Benchmark cases are immutable. Creating a case records the fixed question, retrieval controls, and current collection/index fingerprint. Running it later is rejected if the corpus or index has drifted. Results remain separate from Research jobs and operational traces and do not declare a winner.",
            )
          }}
        </p>
      </div>
      <UiButton
        icon="plus"
        variant="primary"
        :label="t('pipelines.benchmark_new_case', 'New benchmark case')"
        :disabled="loading"
        @click="createOpen = true"
      />
    </header>

    <p v-if="error" class="benchmark-error" role="alert">{{ error }}</p>
    <p v-if="loading" class="benchmark-status" role="status">
      {{ t("common.loading", "Loading…") }}
    </p>

    <div v-else class="benchmark-layout">
      <PipelineBenchmarkCaseList
        :cases="cases"
        :selected-key="selectedCaseKey"
        @select="
          selectedCaseKey = $event;
          benchmark = null;
        "
      />

      <section class="selected-case" aria-labelledby="pipeline-benchmark-run">
        <template v-if="selectedCase">
          <header>
            <p class="case-kicker">{{ t("pipelines.benchmark_saved_case", "Fixed case") }}</p>
            <h4 id="pipeline-benchmark-run">
              {{ selectedCase.case_id }} · v{{ selectedCase.version }}
            </h4>
          </header>
          <dl class="case-snapshot">
            <div>
              <dt>{{ t("pipelines.benchmark_case_prompt", "Fixed question") }}</dt>
              <dd>{{ selectedCase.prompt }}</dd>
            </div>
            <div>
              <dt>{{ t("pipelines.benchmark_corpus_fingerprint", "Corpus/index fingerprint") }}</dt>
              <dd>
                <code>{{ selectedCase.corpus_snapshot.fingerprint }}</code>
              </dd>
            </div>
            <div>
              <dt>{{ t("pipelines.benchmark_index_count", "Captured indexes") }}</dt>
              <dd>{{ selectedCase.corpus_snapshot.collections.length }}</dd>
            </div>
          </dl>
          <p class="run-help">
            {{
              t(
                "pipelines.benchmark_run_help",
                "Both pipelines receive the saved case exactly as recorded. Query decomposition, answer generation, grading, and memory are disabled in this retrieval-only benchmark mode.",
              )
            }}
          </p>

          <div class="run-form">
            <label>
              <span>{{ t("pipelines.compare_left", "Pipeline A") }}</span>
              <select v-model="leftKey" class="control">
                <option
                  v-for="pipeline in researchPipelines"
                  :key="pipelineKey(pipeline)"
                  :value="pipelineKey(pipeline)"
                >
                  {{ pipeline.name }} · v{{ pipeline.version }}
                </option>
              </select>
            </label>
            <label>
              <span>{{ t("pipelines.compare_right", "Pipeline B") }}</span>
              <select v-model="rightKey" class="control">
                <option
                  v-for="pipeline in researchPipelines"
                  :key="pipelineKey(pipeline)"
                  :value="pipelineKey(pipeline)"
                >
                  {{ pipeline.name }} · v{{ pipeline.version }}
                </option>
              </select>
            </label>
          </div>

          <div class="actions">
            <UiButton
              variant="primary"
              :label="
                running
                  ? t('pipelines.benchmark_running', 'Running benchmark…')
                  : t('pipelines.benchmark_action', 'Run fixed benchmark')
              "
              :disabled="running || !selectedCase || !leftKey || !rightKey"
              :disabled-reason="runDisabledReason"
              @click="runBenchmark"
            />
            <span>
              {{
                t(
                  "pipelines.benchmark_persistence",
                  "Only benchmark-specific diagnostics are persisted; no Research job, answer, memory entry, grade, or operational trace is created.",
                )
              }}
            </span>
          </div>

          <PipelineComparisonResult
            v-if="benchmark"
            :result="benchmark.comparison"
            :benchmark-meta="{
              benchmarkRunId: benchmark.benchmark_run_id,
              caseId: benchmark.case_id,
              caseVersion: benchmark.case_version,
              corpusFingerprint: benchmark.corpus.fingerprint,
              warnings: benchmark.reproducibility_warnings,
            }"
            @open-pipeline="emit('openPipeline', $event)"
          />
        </template>
        <p v-else class="empty">
          {{ t("pipelines.benchmark_choose_case", "Choose a saved case") }}
        </p>
      </section>
    </div>

    <UiDialog
      :open="createOpen"
      :title="t('pipelines.benchmark_create_case', 'Create fixed case')"
      :description="
        t(
          'pipelines.benchmark_create_case_help',
          'Changing the question, retrieval settings, or corpus/index requires a new case version. Saved versions are never overwritten.',
        )
      "
      :close-label="t('common.close', 'Close')"
      @close="createOpen = false"
    >
      <div class="case-form">
        <label>
          <span>{{ t("pipelines.benchmark_case_id", "Case ID") }}</span>
          <input
            v-model="caseId"
            class="control"
            type="text"
            :placeholder="t('pipelines.benchmark_case_id_placeholder', 'e.g. trace-definition-001')"
          />
        </label>
        <label>
          <span>{{ t("pipelines.benchmark_case_version", "Case version") }}</span>
          <input v-model.number="caseVersion" class="control" type="number" min="1" step="1" />
        </label>
        <label>
          <span>{{ t("pipelines.compare_collection", "Corpus collection") }}</span>
          <select v-model="collection" class="control">
            <option value="" disabled>
              {{ t("pipelines.compare_choose_collection", "Choose a collection") }}
            </option>
            <option v-for="item in collections" :key="item.name" :value="item.name">
              {{ item.name }}
            </option>
          </select>
        </label>
        <label class="wide">
          <span>{{ t("pipelines.compare_question", "Research question") }}</span>
          <textarea v-model="prompt" class="control" rows="3" />
        </label>
        <label class="wide">
          <span>{{ t("pipelines.benchmark_instructions", "Instructions (optional)") }}</span>
          <textarea v-model="instructions" class="control" rows="2" />
        </label>
        <label class="wide">
          <span>{{ t("pipelines.benchmark_notes", "Notes (optional)") }}</span>
          <input v-model="notes" class="control" type="text" />
        </label>
        <p class="wide immutable-note">
          {{
            t(
              "pipelines.benchmark_case_immutable",
              "The same case ID/version cannot be replaced; use a new version after any fixture change.",
            )
          }}
        </p>
      </div>
      <template #footer>
        <UiButton :label="t('common.cancel', 'Cancel')" @click="createOpen = false" />
        <UiButton
          variant="primary"
          :label="
            creating
              ? t('pipelines.benchmark_creating_case', 'Creating case…')
              : t('pipelines.benchmark_create_case_action', 'Create immutable case')
          "
          :disabled="creating || !!createDisabledReason"
          :disabled-reason="createDisabledReason"
          @click="createCase"
        />
      </template>
    </UiDialog>
  </section>
</template>

<style scoped>
.benchmark-workspace {
  display: grid;
  gap: var(--space-4);
}
.workspace-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.workspace-heading h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.125rem;
}
.workspace-heading p {
  max-width: var(--measure);
  margin: var(--space-1) 0 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}
.benchmark-error,
.benchmark-status {
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  font-size: 0.875rem;
}
.benchmark-error {
  border-color: var(--tone-danger-edge);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.benchmark-layout {
  display: grid;
  grid-template-columns: minmax(220px, 300px) minmax(0, 1fr);
  gap: var(--space-4);
  align-items: start;
}
.selected-case {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.case-kicker {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.selected-case h4 {
  margin: var(--space-1) 0 0;
  color: var(--text-primary);
  font-size: 1.25rem;
}
.case-snapshot {
  display: grid;
  gap: var(--space-3);
  margin: 0;
}
.case-snapshot dt,
.run-form label > span,
.case-form label > span {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}
.case-snapshot dd {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
.case-snapshot code {
  font-size: 0.75rem;
}
.run-help,
.actions > span,
.empty,
.immutable-note {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}
.run-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}
.run-form label,
.case-form label {
  display: grid;
  gap: var(--space-1);
}
.run-form .control,
.case-form .control {
  width: 100%;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}
.case-form {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}
.case-form .wide {
  grid-column: 1 / -1;
}
@media (max-width: 960px) {
  .benchmark-layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .case-form,
  .run-form {
    grid-template-columns: 1fr;
  }
}
</style>
