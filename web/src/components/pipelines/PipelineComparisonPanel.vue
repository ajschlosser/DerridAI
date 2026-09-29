<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { chromaApi } from "../../api/chroma";
import { pipelinesApi } from "../../api/pipelines";
import { pipelineKey } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  ResearchPipelineComparisonResult,
} from "../../types/pipelines";
import type { VectorCollection } from "../../types/vector";
import UiTooltip from "../ui/UiTooltip.vue";

const props = defineProps<{
  pipelines: PipelineDefinition[];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

const prompt = ref("");
const collection = ref("");
const leftKey = ref("");
const rightKey = ref("");
const collections = ref<VectorCollection[]>([]);
const collectionsLoaded = ref(false);
const collectionsLoading = ref(false);
const running = ref(false);
const error = ref("");
const result = ref<ResearchPipelineComparisonResult | null>(null);

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

function initializeChoices() {
  if (!leftKey.value && researchPipelines.value.length) {
    leftKey.value = pipelineKey(researchPipelines.value[0]);
  }
  if (!rightKey.value && researchPipelines.value.length) {
    rightKey.value = pipelineKey(researchPipelines.value[1] || researchPipelines.value[0]);
  }
}

onMounted(initializeChoices);

async function loadCollections() {
  if (collectionsLoaded.value || collectionsLoading.value) return;
  collectionsLoading.value = true;
  error.value = "";
  try {
    collections.value = await chromaApi.collections();
    collectionsLoaded.value = true;
    if (!collection.value && collections.value.length) {
      collection.value = collections.value[0].name;
    }
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    collectionsLoading.value = false;
  }
}

function onToggle(event: Event) {
  const details = event.currentTarget as HTMLDetailsElement | null;
  if (details?.open) void loadCollections();
}

async function runComparison() {
  const left = definition(leftKey.value);
  const right = definition(rightKey.value);
  if (!left || !right || !prompt.value.trim() || !collection.value || running.value) return;

  running.value = true;
  error.value = "";
  result.value = null;
  try {
    result.value = await pipelinesApi.compareResearch({
      request: {
        prompt: prompt.value.trim(),
        source_collection: collection.value,
        // Keep the first comparison mode retrieval-focused and reproducible.
        // The backend therefore does not need a generation provider/model.
        query_decomposition: false,
      },
      left: { pipeline_id: left.pipeline_id, version: left.version },
      right: { pipeline_id: right.pipeline_id, version: right.version },
    });
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
  <details class="comparison-panel" @toggle="onToggle">
    <summary>
      <span>
        <strong>{{ t("pipelines.compare_title", "Test and compare Research pipelines") }}</strong>
        <small>
          {{
            t(
              "pipelines.compare_summary",
              "Run two saved Research recipes against the same question and corpus without generating an answer or changing corpus data.",
            )
          }}
        </small>
      </span>
    </summary>

    <div class="comparison-body">
      <p class="comparison-help">
        {{
          t(
            "pipelines.compare_help",
            "This dry run executes real retrieval, reranking, diversity, provenance, and context-packing stages, then stops before answer generation. Query decomposition is disabled in this first comparison mode so both sides receive the same question. The result describes differences; it does not declare either pipeline better.",
          )
        }}
      </p>

      <p v-if="error" class="comparison-error" role="alert">{{ error }}</p>

      <div class="comparison-form">
        <label class="prompt-field">
          <span>{{ t("pipelines.compare_question", "Research question") }}</span>
          <textarea
            v-model="prompt"
            rows="3"
            :placeholder="
              t(
                'pipelines.compare_question_placeholder',
                'Enter the same research question you want both pipelines to retrieve evidence for.',
              )
            "
          />
        </label>

        <label>
          <span>{{ t("pipelines.compare_collection", "Corpus collection") }}</span>
          <select v-model="collection" :disabled="collectionsLoading">
            <option value="" disabled>
              {{
                collectionsLoading
                  ? t("common.loading", "Loading…")
                  : t("pipelines.compare_choose_collection", "Choose a collection")
              }}
            </option>
            <option v-for="item in collections" :key="item.name" :value="item.name">
              {{ item.name }}
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

      <div class="comparison-actions">
        <button
          class="btn primary"
          type="button"
          :disabled="
            running ||
            !prompt.trim() ||
            !collection ||
            !leftKey ||
            !rightKey ||
            researchPipelines.length < 1
          "
          @click="runComparison"
        >
          {{
            running
              ? t("pipelines.comparing", "Comparing…")
              : t("pipelines.compare_action", "Run dry comparison")
          }}
        </button>
        <span>
          {{
            t(
              "pipelines.compare_nonpersistent",
              "No Research job, response-memory entry, or pipeline trace is saved.",
            )
          }}
        </span>
      </div>

      <template v-if="result">
        <section class="comparison-overview" aria-labelledby="pipeline-comparison-result-title">
          <div>
            <span class="metric-label">
              {{ t("pipelines.compare_candidate_overlap", "Candidate-pool overlap") }}
              <UiTooltip
                :text="
                  t(
                    'pipelines.compare_candidate_overlap_help',
                    'This compares the unique candidate Record IDs presented to reranking on both sides. It shows whether the retrieval stages found the same material before later ranking and provenance checks.',
                  )
                "
              />
            </span>
            <strong id="pipeline-comparison-result-title">
              {{ percent(result.comparison.candidate_overlap.jaccard_overlap) }}
            </strong>
            <small>
              {{ result.comparison.candidate_overlap.shared_count }} /
              {{ result.comparison.candidate_overlap.union_count }}
              {{ t("pipelines.compare_shared_union", "shared / distinct records") }}
            </small>
          </div>
          <div>
            <span class="metric-label">
              {{ t("pipelines.compare_overlap", "Final evidence overlap") }}
              <UiTooltip
                :text="
                  t(
                    'pipelines.compare_overlap_help',
                    'Jaccard overlap compares the final evidence record IDs selected by both pipelines: shared records divided by all distinct records. It measures similarity between outputs, not scholarly quality.',
                  )
                "
              />
            </span>
            <strong>{{ percent(result.comparison.jaccard_overlap) }}</strong>
            <small>
              {{ result.comparison.shared_count }} /
              {{ result.comparison.union_count }}
              {{ t("pipelines.compare_shared_union", "shared / distinct records") }}
            </small>
          </div>
          <div>
            <span>{{ t("pipelines.compare_left_time", "Pipeline A time") }}</span>
            <strong>{{ seconds(result.left.elapsed_seconds) }}</strong>
          </div>
          <div>
            <span>{{ t("pipelines.compare_right_time", "Pipeline B time") }}</span>
            <strong>{{ seconds(result.right.elapsed_seconds) }}</strong>
          </div>
        </section>

        <div class="side-grid">
          <section>
            <h4>
              {{ result.left.pipeline.name }} · v{{ result.left.pipeline.pipeline_version }}
            </h4>
            <p>
              {{
                t(
                  "pipelines.compare_flow",
                  "Candidates: pre-rerank → reranked → final evidence",
                )
              }}
              <strong>
                {{ result.left.candidates.pre_rerank.count }}
                →
                {{ result.left.candidates.post_rerank.count }}
                →
                {{ result.left.evidence.length }}
              </strong>
            </p>
            <p>
              {{
                t(
                  "pipelines.compare_resources",
                  "Context: {context} characters · Cross-encoder calls: {calls}",
                )
                  .replace("{context}", String(result.left.context_characters ?? "—"))
                  .replace("{calls}", String(result.left.resource_use.cross_encoder_calls))
              }}
            </p>
            <ol>
              <li v-for="item in result.left.evidence" :key="item.record_id">
                <code>{{ item.record_id }}</code>
                <span>{{ item.work || item.citation || "—" }}</span>
              </li>
            </ol>
          </section>

          <section>
            <h4>
              {{ result.right.pipeline.name }} · v{{ result.right.pipeline.pipeline_version }}
            </h4>
            <p>
              {{
                t(
                  "pipelines.compare_flow",
                  "Candidates: pre-rerank → reranked → final evidence",
                )
              }}
              <strong>
                {{ result.right.candidates.pre_rerank.count }}
                →
                {{ result.right.candidates.post_rerank.count }}
                →
                {{ result.right.evidence.length }}
              </strong>
            </p>
            <p>
              {{
                t(
                  "pipelines.compare_resources",
                  "Context: {context} characters · Cross-encoder calls: {calls}",
                )
                  .replace("{context}", String(result.right.context_characters ?? "—"))
                  .replace("{calls}", String(result.right.resource_use.cross_encoder_calls))
              }}
            </p>
            <ol>
              <li v-for="item in result.right.evidence" :key="item.record_id">
                <code>{{ item.record_id }}</code>
                <span>{{ item.work || item.citation || "—" }}</span>
              </li>
            </ol>
          </section>
        </div>

        <section class="difference-grid" aria-label="Pipeline comparison differences">
          <div>
            <h4>{{ t("pipelines.compare_only_left", "Only in Pipeline A") }}</h4>
            <p v-if="!result.comparison.left_only_record_ids.length">
              {{ t("pipelines.compare_none", "None") }}
            </p>
            <code v-for="recordId in result.comparison.left_only_record_ids" :key="recordId">
              {{ recordId }}
            </code>
          </div>
          <div>
            <h4>{{ t("pipelines.compare_only_right", "Only in Pipeline B") }}</h4>
            <p v-if="!result.comparison.right_only_record_ids.length">
              {{ t("pipelines.compare_none", "None") }}
            </p>
            <code v-for="recordId in result.comparison.right_only_record_ids" :key="recordId">
              {{ recordId }}
            </code>
          </div>
        </section>

        <section v-if="result.comparison.rank_changes.length" class="rank-table">
          <h4>{{ t("pipelines.compare_rank_changes", "Rank changes among shared records") }}</h4>
          <div class="table-shell">
            <table>
              <thead>
                <tr>
                  <th scope="col">{{ t("pipelines.compare_record", "Record") }}</th>
                  <th scope="col">{{ t("pipelines.compare_left", "Pipeline A") }}</th>
                  <th scope="col">{{ t("pipelines.compare_right", "Pipeline B") }}</th>
                  <th scope="col">{{ t("pipelines.compare_rank_delta", "Rank change") }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in result.comparison.rank_changes" :key="row.record_id">
                  <td><code>{{ row.record_id }}</code></td>
                  <td>{{ row.left_rank }}</td>
                  <td>{{ row.right_rank }}</td>
                  <td>{{ row.rank_delta > 0 ? `+${row.rank_delta}` : row.rank_delta }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </div>
  </details>
</template>

<style scoped>
.comparison-panel {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}
.comparison-panel > summary {
  cursor: pointer;
  padding: 14px 16px;
}
.comparison-panel > summary > span {
  display: grid;
  gap: 3px;
}
.comparison-panel summary small,
.comparison-help,
.comparison-actions > span,
.side-grid p,
.difference-grid p {
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.5;
}
.comparison-body {
  display: grid;
  gap: 14px;
  padding: 0 16px 16px;
}
.comparison-help {
  max-width: 900px;
  margin: 0;
}
.comparison-error {
  margin: 0;
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
}
.comparison-form {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.comparison-form label {
  display: grid;
  gap: 5px;
}
.comparison-form label > span {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 750;
}
.prompt-field {
  grid-column: 1 / -1;
}
.comparison-form textarea,
.comparison-form select {
  width: 100%;
}
.comparison-actions {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
}
.comparison-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.comparison-overview > div {
  display: grid;
  gap: 4px;
  padding: 10px 11px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.comparison-overview span,
.metric-label {
  color: var(--muted);
  font-size: 0.75rem;
}
.metric-label {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.side-grid,
.difference-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.side-grid > section,
.difference-grid > div,
.rank-table {
  padding: 11px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
}
.side-grid h4,
.difference-grid h4,
.rank-table h4 {
  margin: 0 0 7px;
  font-size: 0.82rem;
}
.side-grid p {
  margin: 0 0 8px;
}
.side-grid ol {
  display: grid;
  gap: 5px;
  margin: 0;
  padding-left: 22px;
}
.side-grid li {
  padding-left: 2px;
}
.side-grid li span {
  display: block;
  color: var(--muted);
  font-size: 0.75rem;
}
.difference-grid > div {
  display: flex;
  align-content: flex-start;
  flex-wrap: wrap;
  gap: 5px;
}
.difference-grid h4,
.difference-grid p {
  flex-basis: 100%;
}
.difference-grid p {
  margin: 0;
}
.difference-grid code {
  padding: 3px 6px;
  border-radius: 6px;
  background: var(--soft);
}
.table-shell {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
}
table {
  width: 100%;
  min-width: 520px;
  border-collapse: collapse;
  font-size: 0.76rem;
}
th,
td {
  padding: 7px 8px;
  border-bottom: 1px solid var(--line);
  text-align: left;
}
th {
  background: var(--soft);
  color: var(--muted);
}
tbody tr:last-child td {
  border-bottom: 0;
}
@media (max-width: 820px) {
  .comparison-form,
  .comparison-overview,
  .side-grid,
  .difference-grid {
    grid-template-columns: 1fr;
  }
}
</style>
