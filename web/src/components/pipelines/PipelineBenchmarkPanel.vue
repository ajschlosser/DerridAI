<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import { chromaApi } from "../../api/chroma";
import { pipelinesApi } from "../../api/pipelines";
import { pipelineKey } from "../../domain/pipelinePresentation";
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

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const loaded = ref(false);
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

function onToggle(event: Event) {
  const details = event.currentTarget as HTMLDetailsElement | null;
  if (details?.open) void loadWorkspace();
}

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

function percent(value: number) {
  return new Intl.NumberFormat(i18n.locale, {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(value);
}

function seconds(value: number | null | undefined) {
  if (value == null) return "—";
  return `${value.toFixed(value < 10 ? 2 : 1)} s`;
}
</script>

<template>
  <details class="benchmark-panel" @toggle="onToggle">
    <summary>
      <span>
        <strong>{{ t("pipelines.benchmark_title", "Benchmark Research pipelines") }}</strong>
        <small>
          {{
            t(
              "pipelines.benchmark_summary",
              "Freeze a question and corpus/index revision, then run repeatable retrieval-only A/B comparisons against that immutable case.",
            )
          }}
        </small>
      </span>
    </summary>

    <div class="benchmark-body">
      <p class="benchmark-help">
        {{
          t(
            "pipelines.benchmark_help",
            "Benchmark cases are immutable. Creating a case records the fixed question, retrieval controls, and current collection/index fingerprint. Running it later is rejected if the corpus or index has drifted. Results remain separate from Research jobs and operational traces and do not declare a winner.",
          )
        }}
      </p>

      <p v-if="error" class="benchmark-error" role="alert">{{ error }}</p>
      <p v-if="loading" class="benchmark-status" role="status">
        {{ t("common.loading", "Loading…") }}
      </p>

      <template v-else>
        <section class="case-builder" aria-labelledby="pipeline-benchmark-case-builder">
          <div>
            <h4 id="pipeline-benchmark-case-builder">
              {{ t("pipelines.benchmark_create_case", "Create fixed case") }}
            </h4>
            <p>
              {{
                t(
                  "pipelines.benchmark_create_case_help",
                  "Changing the question, retrieval settings, or corpus/index requires a new case version. Saved versions are never overwritten.",
                )
              }}
            </p>
          </div>

          <div class="case-form">
            <label>
              <span>{{ t("pipelines.benchmark_case_id", "Case ID") }}</span>
              <input
                v-model="caseId"
                type="text"
                :placeholder="
                  t('pipelines.benchmark_case_id_placeholder', 'e.g. trace-definition-001')
                "
              />
            </label>
            <label>
              <span>{{ t("pipelines.benchmark_case_version", "Case version") }}</span>
              <input v-model.number="caseVersion" type="number" min="1" step="1" />
            </label>
            <label>
              <span>{{ t("pipelines.compare_collection", "Corpus collection") }}</span>
              <select v-model="collection">
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
              <textarea v-model="prompt" rows="3" />
            </label>
            <label class="wide">
              <span>{{ t("pipelines.benchmark_instructions", "Instructions (optional)") }}</span>
              <textarea v-model="instructions" rows="2" />
            </label>
            <label class="wide">
              <span>{{ t("pipelines.benchmark_notes", "Notes (optional)") }}</span>
              <input v-model="notes" type="text" />
            </label>
          </div>

          <div class="actions">
            <button
              class="btn"
              type="button"
              :disabled="
                creating || !caseId.trim() || caseVersion < 1 || !prompt.trim() || !collection
              "
              @click="createCase"
            >
              {{
                creating
                  ? t("pipelines.benchmark_creating_case", "Creating case…")
                  : t("pipelines.benchmark_create_case_action", "Create immutable case")
              }}
            </button>
            <span>
              {{
                t(
                  "pipelines.benchmark_case_immutable",
                  "The same case ID/version cannot be replaced; use a new version after any fixture change.",
                )
              }}
            </span>
          </div>
        </section>

        <section class="run-card" aria-labelledby="pipeline-benchmark-run">
          <div>
            <h4 id="pipeline-benchmark-run">
              {{ t("pipelines.benchmark_run_title", "Run saved case") }}
            </h4>
            <p>
              {{
                t(
                  "pipelines.benchmark_run_help",
                  "Both pipelines receive the saved case exactly as recorded. Query decomposition, answer generation, grading, and memory are disabled in this retrieval-only benchmark mode.",
                )
              }}
            </p>
          </div>

          <div class="run-form">
            <label class="case-choice">
              <span>{{ t("pipelines.benchmark_saved_case", "Fixed case") }}</span>
              <select v-model="selectedCaseKey">
                <option value="" disabled>
                  {{ t("pipelines.benchmark_choose_case", "Choose a saved case") }}
                </option>
                <option
                  v-for="item in cases"
                  :key="benchmarkCaseKey(item)"
                  :value="benchmarkCaseKey(item)"
                >
                  {{ item.case_id }} · v{{ item.version }} · {{ item.source_collection }}
                </option>
              </select>
            </label>
            <label>
              <span>{{ t("pipelines.compare_left", "Pipeline A") }}</span>
              <select v-model="leftKey">
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
              <select v-model="rightKey">
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

          <div v-if="selectedCase" class="case-snapshot">
            <div>
              <span>{{ t("pipelines.benchmark_case_prompt", "Fixed question") }}</span>
              <strong>{{ selectedCase.prompt }}</strong>
            </div>
            <div>
              <span>{{
                t("pipelines.benchmark_corpus_fingerprint", "Corpus/index fingerprint")
              }}</span>
              <code>{{ selectedCase.corpus_snapshot.fingerprint }}</code>
            </div>
            <div>
              <span>{{ t("pipelines.benchmark_index_count", "Captured indexes") }}</span>
              <strong>{{ selectedCase.corpus_snapshot.collections.length }}</strong>
            </div>
          </div>

          <div class="actions">
            <button
              class="btn primary"
              type="button"
              :disabled="running || !selectedCase || !leftKey || !rightKey"
              @click="runBenchmark"
            >
              {{
                running
                  ? t("pipelines.benchmark_running", "Running benchmark…")
                  : t("pipelines.benchmark_action", "Run fixed benchmark")
              }}
            </button>
            <span>
              {{
                t(
                  "pipelines.benchmark_persistence",
                  "Only benchmark-specific diagnostics are persisted; no Research job, answer, memory entry, grade, or operational trace is created.",
                )
              }}
            </span>
          </div>
        </section>

        <section
          v-if="benchmark"
          class="benchmark-result"
          aria-labelledby="pipeline-benchmark-result"
          role="status"
        >
          <div class="result-heading">
            <div>
              <span>{{ t("pipelines.benchmark_saved", "Saved benchmark") }}</span>
              <strong id="pipeline-benchmark-result">
                {{ benchmark.case_id }} · v{{ benchmark.case_version }}
              </strong>
              <code>{{ benchmark.benchmark_run_id }}</code>
            </div>
            <div>
              <span>{{ t("pipelines.benchmark_corpus_fingerprint", "Corpus/index fingerprint") }}</span>
              <code>{{ benchmark.corpus.fingerprint }}</code>
            </div>
          </div>

          <div class="metrics">
            <div>
              <span>{{ t("pipelines.compare_candidate_overlap", "Candidate-pool overlap") }}</span>
              <strong>{{
                percent(benchmark.comparison.comparison.candidate_overlap.jaccard_overlap)
              }}</strong>
            </div>
            <div>
              <span>{{ t("pipelines.compare_overlap", "Final evidence overlap") }}</span>
              <strong>{{ percent(benchmark.comparison.comparison.jaccard_overlap) }}</strong>
            </div>
            <div>
              <span>{{ t("pipelines.compare_left_time", "Pipeline A time") }}</span>
              <strong>{{ seconds(benchmark.comparison.left.elapsed_seconds) }}</strong>
            </div>
            <div>
              <span>{{ t("pipelines.compare_right_time", "Pipeline B time") }}</span>
              <strong>{{ seconds(benchmark.comparison.right.elapsed_seconds) }}</strong>
            </div>
          </div>

          <div class="pipeline-hashes">
            <div>
              <span>{{ t("pipelines.compare_left", "Pipeline A") }}</span>
              <code>{{ benchmark.left_pipeline.pipeline_hash || "—" }}</code>
            </div>
            <div>
              <span>{{ t("pipelines.compare_right", "Pipeline B") }}</span>
              <code>{{ benchmark.right_pipeline.pipeline_hash || "—" }}</code>
            </div>
          </div>

          <div v-if="benchmark.reproducibility_warnings.length" class="warnings">
            <strong>
              {{ t("pipelines.benchmark_reproducibility_limits", "Reproducibility limits") }}
            </strong>
            <ul>
              <li v-for="warning in benchmark.reproducibility_warnings" :key="warning">
                {{ warning }}
              </li>
            </ul>
          </div>
        </section>
      </template>
    </div>
  </details>
</template>

<style scoped>
.benchmark-panel {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.benchmark-panel > summary {
  cursor: pointer;
  padding: 14px 16px;
}
.benchmark-panel > summary > span {
  display: grid;
  gap: 3px;
}
.benchmark-panel summary small,
.benchmark-help,
.case-builder p,
.run-card p,
.actions > span,
.benchmark-status,
.warnings li {
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.5;
}
.benchmark-body {
  display: grid;
  gap: 14px;
  padding: 0 16px 16px;
}
.benchmark-help,
.case-builder p,
.run-card p {
  margin: 0;
}
.benchmark-error,
.benchmark-status {
  margin: 0;
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
}
.case-builder,
.run-card,
.benchmark-result {
  display: grid;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--soft);
}
.case-builder h4,
.run-card h4 {
  margin: 0 0 3px;
  font-size: 0.86rem;
}
.case-form,
.run-form,
.metrics,
.pipeline-hashes,
.result-heading {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.case-form label,
.run-form label,
.case-snapshot > div,
.metrics > div,
.pipeline-hashes > div,
.result-heading > div {
  display: grid;
  gap: 5px;
}
.case-form label > span,
.run-form label > span,
.case-snapshot span,
.metrics span,
.pipeline-hashes span,
.result-heading span {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
}
.case-form .wide,
.run-form .case-choice {
  grid-column: 1 / -1;
}
.case-form input,
.case-form select,
.case-form textarea,
.run-form select {
  width: 100%;
}
.actions {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
}
.case-snapshot {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr) minmax(120px, 0.3fr);
  gap: 8px;
}
.case-snapshot > div,
.metrics > div,
.pipeline-hashes > div,
.result-heading > div {
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
}
.case-snapshot code,
.pipeline-hashes code,
.result-heading code {
  overflow-wrap: anywhere;
}
.result-heading {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.metrics {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.pipeline-hashes {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.warnings {
  display: grid;
  gap: 5px;
}
.warnings ul {
  margin: 0;
  padding-left: 20px;
}
@media (max-width: 820px) {
  .case-form,
  .run-form,
  .case-snapshot,
  .result-heading,
  .metrics,
  .pipeline-hashes {
    grid-template-columns: 1fr;
  }
  .case-form .wide,
  .run-form .case-choice {
    grid-column: auto;
  }
}
</style>
