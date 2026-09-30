<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { chromaApi } from "../../api/chroma";
import { pipelinesApi } from "../../api/pipelines";
import { pipelineKey } from "../../domain/pipelinePresentation";
import { useI18nStore } from "../../stores/i18n";
import type { PipelineDefinition, ResearchPipelineComparisonResult } from "../../types/pipelines";
import type { VectorCollection } from "../../types/vector";
import PipelineComparisonResult from "./PipelineComparisonResult.vue";
import UiButton from "../ui/UiButton.vue";

const props = defineProps<{
  pipelines: PipelineDefinition[];
}>();
const emit = defineEmits<{ openPipeline: [key: string] }>();

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

const disabledReason = computed(() => {
  if (running.value) return "";
  if (!researchPipelines.value.length)
    return t(
      "pipelines.compare_reason_no_pipelines",
      "No executable Research pipelines are available.",
    );
  if (!prompt.value.trim())
    return t("pipelines.compare_reason_question", "Enter a research question first.");
  if (!collection.value)
    return t("pipelines.compare_reason_collection", "Choose a corpus collection first.");
  return "";
});

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

onMounted(() => {
  initializeChoices();
  void loadCollections();
});

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
</script>

<template>
  <section class="comparison-workspace" aria-labelledby="pipeline-compare-title">
    <header class="workspace-heading">
      <h3 id="pipeline-compare-title">
        {{ t("pipelines.compare_title", "Test and compare Research pipelines") }}
      </h3>
      <p>
        {{
          t(
            "pipelines.compare_help",
            "This dry run executes real retrieval, reranking, diversity, provenance, and context-packing stages, then stops before answer generation. Query decomposition is disabled in this first comparison mode so both sides receive the same question. The result describes differences; it does not declare either pipeline better.",
          )
        }}
      </p>
    </header>

    <p v-if="error" class="comparison-error" role="alert">{{ error }}</p>

    <div class="comparison-form">
      <label class="prompt-field">
        <span>{{ t("pipelines.compare_question", "Research question") }}</span>
        <textarea
          v-model="prompt"
          class="control"
          rows="3"
          :placeholder="
            t(
              'pipelines.compare_question_placeholder',
              'Enter the same research question you want both pipelines to retrieve evidence for.',
            )
          "
        />
      </label>

      <div class="choice-row">
        <label>
          <span>{{ t("pipelines.compare_collection", "Corpus collection") }}</span>
          <select v-model="collection" class="control" :disabled="collectionsLoading">
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
    </div>

    <div class="comparison-actions">
      <UiButton
        variant="primary"
        :label="
          running
            ? t('pipelines.comparing', 'Comparing…')
            : t('pipelines.compare_action', 'Run dry comparison')
        "
        :disabled="
          running ||
          !prompt.trim() ||
          !collection ||
          !leftKey ||
          !rightKey ||
          researchPipelines.length < 1
        "
        :disabled-reason="disabledReason"
        @click="runComparison"
      />
      <span>
        {{
          t(
            "pipelines.compare_nonpersistent",
            "No Research job, response-memory entry, or pipeline trace is saved.",
          )
        }}
      </span>
    </div>

    <PipelineComparisonResult
      v-if="result"
      :result="result"
      @open-pipeline="emit('openPipeline', $event)"
    />
  </section>
</template>

<style scoped>
.comparison-workspace {
  display: grid;
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
.comparison-error {
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--tone-danger-edge);
  border-radius: var(--radius-control);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
  font-size: 0.875rem;
}
.comparison-form {
  display: grid;
  gap: var(--space-3);
}
.comparison-form label {
  display: grid;
  gap: var(--space-1);
}
.comparison-form label > span {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}
.comparison-form .control {
  width: 100%;
}
.choice-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}
.comparison-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
@media (max-width: 860px) {
  .choice-row {
    grid-template-columns: 1fr;
  }
}
</style>
