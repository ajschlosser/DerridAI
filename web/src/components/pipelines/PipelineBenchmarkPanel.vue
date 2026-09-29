<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { chromaApi } from "../../api/chroma";
import { pipelinesApi } from "../../api/pipelines";
import { pipelineKey } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  ResearchBenchmarkCase,
  ResearchBenchmarkRun,
} from "../../types/pipelines";
import type { VectorCollection } from "../../types/vector";

const props = defineProps<{
  pipelines: PipelineDefinition[];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const cases = ref<ResearchBenchmarkCase[]>([]);
const collections = ref<VectorCollection[]>([]);
const loaded = ref(false);
const loading = ref(false);
const saving = ref(false);
const running = ref(false);
const error = ref("");
const benchmarkId = ref("");
const name = ref("");
const prompt = ref("");
const notes = ref("");
const collection = ref("");
const selectedCaseKey = ref("");
const leftKey = ref("");
const rightKey = ref("");
const result = ref<ResearchBenchmarkRun | null>(null);

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

function caseKey(item: ResearchBenchmarkCase) {
  return `${item.benchmark_id}@${item.version}`;
}

const selectedCase = computed(
  () => cases.value.find((item) => caseKey(item) === selectedCaseKey.value) || null,
);

function initializePipelines() {
  if (!leftKey.value && researchPipelines.value.length) {
    leftKey.value = pipelineKey(researchPipelines.value[0]);
  }
  if (!rightKey.value && researchPipelines.value.length) {
    rightKey.value = pipelineKey(researchPipelines.value[1] || researchPipelines.value[0]);
  }
}

onMounted(initializePipelines);

async function load() {
  if (loaded.value || loading.value) return;
  loading.value = true;
  error.value = "";
  try {
    const [casePage, collectionRows] = await Promise.all([
      pipelinesApi.benchmarkCases({ limit: 100 }),
      chromaApi.collections(),
    ]);
    cases.value = casePage.cases;
    collections.value = collectionRows;
    loaded.value = true;
    if (!selectedCaseKey.value && cases.value.length) {
      selectedCaseKey.value = caseKey(cases.value[0]);
    }
    if (!collection.value && collections.value.length) {
      collection.value = collections.value[0].name;
    }
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

function onToggle(event: Event) {
  const details = event.currentTarget as HTMLDetailsElement | null;
  if (details?.open) void load();
}

async function saveCase() {
  if (
    saving.value ||
    !benchmarkId.value.trim() ||
    !name.value.trim() ||
    !prompt.value.trim() ||
    !collection.value
  ) {
    return;
  }
  saving.value = true;
  error.value = "";
  result.value = null;
  try {
    const response = await pipelinesApi.createBenchmarkCase({
      benchmark_id: benchmarkId.value.trim(),
      name: name.value.trim(),
      request: {
        prompt: prompt.value.trim(),
        source_collection: collection.value,
        query_decomposition: false,
      },
      notes: notes.value.trim() || null,
    });
    cases.value = [response.case, ...cases.value];
    selectedCaseKey.value = caseKey(response.case);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    saving.value = false;
  }
}

async function runBenchmark() {
  const benchmark = selectedCase.value;
  const left = definition(leftKey.value);
  const right = definition(rightKey.value);
  if (!benchmark || !left || !right || running.value) return;

  running.value = true;
  error.value = "";
  result.value = null;
  try {
    const response = await pipelinesApi.runBenchmark({
      benchmark_id: benchmark.benchmark_id,
      benchmark_version: benchmark.version,
      left: { pipeline_id: left.pipeline_id, version: left.version },
      right: { pipeline_id: right.pipeline_id, version: right.version },
    });
    result.value = response.run;
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
        <strong>{{ t("pipelines.benchmark_title", "Fixed Research benchmarks") }}</strong>
        <small>
          {{
            t(
              "pipelines.benchmark_summary",
              "Save an immutable question-and-corpus case, then compare exact pipeline versions against it over time.",
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
            "Benchmark runs use the non-persistent retrieval comparison path. They save the case, collection revision metadata, exact pipeline identities, and comparison result, but they do not create a Research answer, memory entry, corpus mutation, or ordinary pipeline trace.",
          )
        }}
      </p>

      <p v-if="error" class="benchmark-error" role="alert">{{ error }}</p>

      <section class="case-editor" :aria-label="t('pipelines.benchmark_new_case', 'New benchmark case')">
        <div class="case-grid">
          <label>
            <span>{{ t("pipelines.benchmark_id", "Case ID") }}</span>
            <input
              v-model="benchmarkId"
              type="text"
              maxlength="80"
              :placeholder="t('pipelines.benchmark_id_placeholder', 'trace-core')"
            />
          </label>
          <label>
            <span>{{ t("pipelines.benchmark_name", "Case name") }}</span>
            <input
              v-model="name"
              type="text"
              maxlength="200"
              :placeholder="
                t('pipelines.benchmark_name_placeholder', 'Core trace retrieval case')
              "
            />
          </label>
          <label class="question-field">
            <span>{{ t("pipelines.compare_question", "Research question") }}</span>
            <textarea v-model="prompt" rows="3" />
          </label>
          <label>
            <span>{{ t("pipelines.compare_collection", "Corpus collection") }}</span>
            <select v-model="collection" :disabled="loading">
              <option value="" disabled>
                {{ t("pipelines.compare_choose_collection", "Choose a collection") }}
              </option>
              <option v-for="item in collections" :key="item.name" :value="item.name">
                {{ item.name }}
              </option>
            </select>
          </label>
          <label>
            <span>{{ t("pipelines.benchmark_notes", "Notes") }}</span>
            <input
              v-model="notes"
              type="text"
              maxlength="4000"
              :placeholder="
                t('pipelines.benchmark_notes_placeholder', 'What this case is intended to test')
              "
            />
          </label>
        </div>
        <button
          class="btn"
          type="button"
          :disabled="
            saving ||
            !benchmarkId.trim() ||
            !name.trim() ||
            !prompt.trim() ||
            !collection
          "
          @click="saveCase"
        >
          {{
            saving
              ? t("pipelines.benchmark_saving", "Saving…")
              : t("pipelines.benchmark_save", "Save immutable case")
          }}
        </button>
      </section>

      <section class="runner" :aria-label="t('pipelines.benchmark_runner', 'Benchmark runner')">
        <div class="runner-grid">
          <label>
            <span>{{ t("pipelines.benchmark_case", "Saved case") }}</span>
            <select v-model="selectedCaseKey" :disabled="loading || !cases.length">
              <option value="" disabled>
                {{
                  cases.length
                    ? t("pipelines.benchmark_choose_case", "Choose a benchmark case")
                    : t("pipelines.benchmark_no_cases", "No saved benchmark cases")
                }}
              </option>
              <option v-for="item in cases" :key="caseKey(item)" :value="caseKey(item)">
                {{ item.name }} · {{ item.benchmark_id }}@{{ item.version }}
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
          <strong>{{ selectedCase.name }}</strong>
          <span>
            {{ selectedCase.request.prompt || "—" }}
          </span>
          <span>
            {{
              t(
                "pipelines.benchmark_snapshot",
                "Collection: {collection} · source snapshot: {source} · embedding revision: {embedding}",
              )
                .replace("{collection}", String(selectedCase.collection_snapshot.name || "—"))
                .replace(
                  "{source}",
                  String(selectedCase.collection_snapshot.source_snapshot_hash || "unavailable"),
                )
                .replace(
                  "{embedding}",
                  String(selectedCase.collection_snapshot.embedding_revision || "unavailable"),
                )
            }}
          </span>
          <ul v-if="selectedCase.reproducibility_warnings.length" class="warning-list">
            <li v-for="warning in selectedCase.reproducibility_warnings" :key="warning">
              {{ warning }}
            </li>
          </ul>
        </div>

        <button
          class="btn primary"
          type="button"
          :disabled="running || !selectedCase || !leftKey || !rightKey"
          @click="runBenchmark"
        >
          {{
            running
              ? t("pipelines.benchmark_running", "Running benchmark…")
              : t("pipelines.benchmark_run", "Run fixed benchmark")
          }}
        </button>
      </section>

      <section v-if="result" class="benchmark-result" aria-live="polite">
        <header>
          <div>
            <strong>
              {{ result.case.name }} · {{ result.benchmark_id }}@{{ result.benchmark_version }}
            </strong>
            <span><code>{{ result.benchmark_run_id }}</code></span>
          </div>
          <span>
            {{
              t(
                "pipelines.benchmark_result_help",
                "These are descriptive retrieval measurements, not a quality score or winner.",
              )
            }}
          </span>
        </header>

        <div class="metrics">
          <div>
            <span>{{ t("pipelines.compare_candidate_overlap", "Candidate-pool overlap") }}</span>
            <strong>
              {{ percent(result.comparison.comparison.candidate_overlap.jaccard_overlap) }}
            </strong>
          </div>
          <div>
            <span>{{ t("pipelines.compare_overlap", "Final evidence overlap") }}</span>
            <strong>{{ percent(result.comparison.comparison.jaccard_overlap) }}</strong>
          </div>
          <div>
            <span>{{ t("pipelines.compare_left_time", "Pipeline A time") }}</span>
            <strong>{{ seconds(result.comparison.left.elapsed_seconds) }}</strong>
          </div>
          <div>
            <span>{{ t("pipelines.compare_right_time", "Pipeline B time") }}</span>
            <strong>{{ seconds(result.comparison.right.elapsed_seconds) }}</strong>
          </div>
        </div>

        <div class="pipeline-identities">
          <span>
            A:
            <code>
              {{ result.comparison.left.pipeline.pipeline_id }}@{{
                result.comparison.left.pipeline.pipeline_version
              }}
            </code>
            ·
            <code>{{ result.comparison.left.pipeline.pipeline_hash || "—" }}</code>
          </span>
          <span>
            B:
            <code>
              {{ result.comparison.right.pipeline.pipeline_id }}@{{
                result.comparison.right.pipeline.pipeline_version
              }}
            </code>
            ·
            <code>{{ result.comparison.right.pipeline.pipeline_hash || "—" }}</code>
          </span>
        </div>

        <ul v-if="result.reproducibility_warnings.length" class="warning-list">
          <li v-for="warning in result.reproducibility_warnings" :key="warning">{{ warning }}</li>
        </ul>
      </section>
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
.benchmark-panel > summary > span,
.benchmark-body,
.case-editor,
.runner,
.case-snapshot,
.benchmark-result,
.benchmark-result header,
.pipeline-identities {
  display: grid;
}
.benchmark-panel > summary > span {
  gap: 3px;
}
.benchmark-panel summary small,
.benchmark-help,
.case-snapshot,
.benchmark-result header > span,
.pipeline-identities,
.warning-list {
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.5;
}
.benchmark-body {
  gap: 14px;
  padding: 0 16px 16px;
}
.benchmark-help,
.benchmark-error {
  margin: 0;
}
.case-editor,
.runner,
.benchmark-result {
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
}
.case-grid,
.runner-grid,
.metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.case-grid label,
.runner-grid label {
  display: grid;
  gap: 5px;
}
.case-grid label > span,
.runner-grid label > span,
.metrics span {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
}
.question-field {
  grid-column: 1 / -1;
}
.case-grid input,
.case-grid textarea,
.case-grid select,
.runner-grid select {
  width: 100%;
}
.case-editor > .btn,
.runner > .btn {
  justify-self: start;
}
.case-snapshot {
  gap: 4px;
  padding: 10px;
  background: var(--soft);
  border-radius: 8px;
}
.warning-list {
  margin: 4px 0 0;
  padding-left: 20px;
}
.benchmark-result header {
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}
.benchmark-result header > div {
  display: grid;
  gap: 3px;
}
.metrics {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.metrics > div {
  display: grid;
  gap: 4px;
  padding: 9px 10px;
  background: var(--soft);
  border-radius: 8px;
}
.pipeline-identities {
  gap: 4px;
}
@media (max-width: 820px) {
  .case-grid,
  .runner-grid,
  .metrics,
  .benchmark-result header {
    grid-template-columns: 1fr;
  }
}
</style>
