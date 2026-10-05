<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { chromaApi } from "../../api/chroma";
import { pipelinesApi } from "../../api/pipelines";
import { pipelineKey } from "../../domain/pipelinePresentation";
import { researchSourceCollections } from "../../domain/vectorCollections";
import { useI18nStore } from "../../stores/i18n";
import type {
  EvidencePipelineComparisonResult,
  PipelineDefinition,
  ResearchPipelineComparisonResult,
} from "../../types/pipelines";
import type { VectorCollection } from "../../types/vector";
import PipelineComparisonResult from "./PipelineComparisonResult.vue";
import PipelineEvidenceComparisonResult from "./PipelineEvidenceComparisonResult.vue";
import UiButton from "../ui/UiButton.vue";

const props = defineProps<{
  pipelines: PipelineDefinition[];
}>();
const emit = defineEmits<{ openPipeline: [key: string] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);

type CompareMode = "research" | "evidence_suggestion" | "evidence_recovery";

const mode = ref<CompareMode>("research");
const prompt = ref("");
const collection = ref("");
const fieldValue = ref("");
const fieldName = ref("");
const sourceDocumentId = ref("");
const blocksJson = ref("[]");
const leftKey = ref("");
const rightKey = ref("");
const collections = ref<VectorCollection[]>([]);
const collectionsLoaded = ref(false);
const collectionsLoading = ref(false);
const running = ref(false);
const error = ref("");
const researchResult = ref<ResearchPipelineComparisonResult | null>(null);
const evidenceResult = ref<EvidencePipelineComparisonResult | null>(null);

const researchPipelines = computed(() =>
  props.pipelines.filter(
    (pipeline) =>
      pipeline.purpose === "research" &&
      pipeline.status !== "disabled" &&
      pipeline.runtime_support?.supported !== false,
  ),
);

const evidencePipelines = computed(() => {
  const purpose = mode.value === "evidence_recovery" ? "evidence_recovery" : "evidence_suggestion";
  return props.pipelines.filter(
    (pipeline) =>
      pipeline.purpose === purpose &&
      pipeline.status !== "disabled" &&
      pipeline.runtime_support?.supported !== false,
  );
});

const selectablePipelines = computed(() =>
  mode.value === "research" ? researchPipelines.value : evidencePipelines.value,
);

const heading = computed(() => {
  if (mode.value === "evidence_suggestion") {
    return t("pipelines.compare_title_suggestion", "Test and compare reviewer-evidence pipelines");
  }
  if (mode.value === "evidence_recovery") {
    return t("pipelines.compare_title_recovery", "Test and compare evidence-recovery pipelines");
  }
  return t("pipelines.compare_title", "Test and compare Research pipelines");
});

const help = computed(() => {
  if (mode.value === "evidence_suggestion") {
    return t(
      "pipelines.compare_help_suggestion",
      "This dry run executes the same reviewer-evidence retrieval, optional MMR, and support/provenance gates on one field value and the same source blocks. It does not bind evidence or write corpus state. The result describes differences; it does not declare either pipeline better.",
    );
  }
  if (mode.value === "evidence_recovery") {
    return t(
      "pipelines.compare_help_recovery",
      "This dry run walks each recovery cascade on one field value and the same source blocks without calling a language model or persisting a trace. The result describes differences; it does not declare either pipeline better.",
    );
  }
  return t(
    "pipelines.compare_help",
    "This dry run executes real retrieval, reranking, diversity, provenance, and context-packing stages, then stops before answer generation. Query decomposition is disabled in this first comparison mode so both sides receive the same question. The result describes differences; it does not declare either pipeline better.",
  );
});

const parsedBlocks = computed(() => {
  try {
    const parsed = JSON.parse(blocksJson.value);
    if (!Array.isArray(parsed) || !parsed.length) return null;
    const blocks = parsed
      .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
      .map((item) => ({
        block_id: String(item.block_id || ""),
        text: String(item.text || ""),
        source_unit_id: item.source_unit_id != null ? String(item.source_unit_id) : undefined,
      }))
      .filter((item) => item.block_id);
    return blocks.length ? blocks : null;
  } catch {
    return null;
  }
});

const statusMessage = computed(() => {
  if (running.value) return t("pipelines.compare_status_running", "Comparing pipelines.");
  if (error.value) return t("pipelines.compare_status_error", "Comparison failed.");
  if (researchResult.value || evidenceResult.value)
    return t("pipelines.compare_status_complete", "Comparison complete.");
  return t("pipelines.compare_status_idle", "Ready to compare.");
});

const parsedValue = computed(() => {
  const raw = fieldValue.value.trim();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
});

const disabledReason = computed(() => {
  if (running.value) return "";
  if (!selectablePipelines.value.length) {
    return mode.value === "research"
      ? t(
          "pipelines.compare_reason_no_pipelines",
          "No executable Research pipelines are available.",
        )
      : t(
          "pipelines.compare_reason_no_evidence_pipelines",
          "No executable evidence pipelines of this kind are available.",
        );
  }
  if (mode.value === "research") {
    if (!prompt.value.trim())
      return t("pipelines.compare_reason_question", "Enter a research question first.");
    if (!collection.value)
      return t("pipelines.compare_reason_collection", "Choose a corpus collection first.");
    return "";
  }
  if (parsedValue.value == null)
    return t(
      "pipelines.compare_reason_value",
      "Enter the field value both pipelines should score.",
    );
  if (!fieldName.value.trim())
    return t("pipelines.compare_reason_field", "Enter the field name first.");
  if (!parsedBlocks.value)
    return t(
      "pipelines.compare_reason_blocks",
      "Provide a JSON array of source blocks with block_id values.",
    );
  return "";
});

function definition(key: string) {
  return selectablePipelines.value.find((pipeline) => pipelineKey(pipeline) === key) || null;
}

function initializeChoices() {
  leftKey.value = selectablePipelines.value[0] ? pipelineKey(selectablePipelines.value[0]) : "";
  rightKey.value = selectablePipelines.value[1]
    ? pipelineKey(selectablePipelines.value[1])
    : leftKey.value;
}

watch(mode, () => {
  researchResult.value = null;
  evidenceResult.value = null;
  error.value = "";
  initializeChoices();
});

onMounted(() => {
  initializeChoices();
  void loadCollections();
});

async function loadCollections() {
  if (collectionsLoaded.value || collectionsLoading.value) return;
  collectionsLoading.value = true;
  error.value = "";
  try {
    collections.value = researchSourceCollections(await chromaApi.collections());
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
  if (!left || !right || running.value || disabledReason.value) return;

  running.value = true;
  error.value = "";
  researchResult.value = null;
  evidenceResult.value = null;
  try {
    if (mode.value === "research") {
      researchResult.value = await pipelinesApi.compareResearch({
        request: {
          prompt: prompt.value.trim(),
          source_collection: collection.value,
          query_decomposition: false,
        },
        left: { pipeline_id: left.pipeline_id, version: left.version },
        right: { pipeline_id: right.pipeline_id, version: right.version },
      });
      return;
    }
    const request = {
      value: parsedValue.value,
      blocks: parsedBlocks.value || [],
      field: fieldName.value.trim(),
      field_metadata: { name: fieldName.value.trim(), label: fieldName.value.trim() },
      source_document_id: sourceDocumentId.value.trim(),
      left: { pipeline_id: left.pipeline_id, version: left.version },
      right: { pipeline_id: right.pipeline_id, version: right.version },
    };
    evidenceResult.value =
      mode.value === "evidence_recovery"
        ? await pipelinesApi.compareEvidenceRecovery(request)
        : await pipelinesApi.compareEvidenceSuggestion(request);
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
      <h3 id="pipeline-compare-title">{{ heading }}</h3>
      <p>{{ help }}</p>
    </header>

    <fieldset class="mode-row">
      <legend>{{ t("pipelines.compare_mode", "Comparison kind") }}</legend>
      <label>
        <input v-model="mode" type="radio" value="research" />
        {{ t("pipelines.compare_mode_research", "Research") }}
      </label>
      <label>
        <input v-model="mode" type="radio" value="evidence_suggestion" />
        {{ t("pipelines.compare_mode_suggestion", "Reviewer evidence") }}
      </label>
      <label>
        <input v-model="mode" type="radio" value="evidence_recovery" />
        {{ t("pipelines.compare_mode_recovery", "Evidence recovery") }}
      </label>
    </fieldset>

    <p class="sr-only" role="status" aria-live="polite">{{ statusMessage }}</p>
    <p v-if="error" class="comparison-error" role="alert">{{ error }}</p>

    <div v-if="mode === 'research'" class="comparison-form">
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

    <div v-else class="comparison-form">
      <label class="prompt-field">
        <span>{{ t("pipelines.compare_value", "Field value") }}</span>
        <textarea
          v-model="fieldValue"
          class="control"
          rows="3"
          :placeholder="
            t(
              'pipelines.compare_value_placeholder',
              'Value both pipelines should retrieve evidence for.',
            )
          "
        />
      </label>
      <label class="prompt-field">
        <span>{{ t("pipelines.compare_blocks", "Source blocks (JSON)") }}</span>
        <textarea
          v-model="blocksJson"
          class="control"
          rows="6"
          :placeholder="t('pipelines.compare_blocks_placeholder', 'JSON array of source blocks')"
        />
      </label>
      <div class="choice-row">
        <label>
          <span>{{ t("pipelines.compare_field", "Field name") }}</span>
          <input v-model="fieldName" class="control" type="text" />
        </label>
        <label>
          <span>{{ t("pipelines.compare_source_document", "Source document ID") }}</span>
          <input
            v-model="sourceDocumentId"
            class="control"
            type="text"
            autocomplete="off"
            spellcheck="false"
          />
        </label>
        <label>
          <span>{{ t("pipelines.compare_left", "Pipeline A") }}</span>
          <select v-model="leftKey" class="control">
            <option
              v-for="pipeline in evidencePipelines"
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
              v-for="pipeline in evidencePipelines"
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
        :disabled="Boolean(disabledReason) || !leftKey || !rightKey"
        :disabled-reason="disabledReason"
        @click="runComparison"
      />
      <span>
        {{
          mode === "research"
            ? t(
                "pipelines.compare_nonpersistent",
                "No Research job, response-memory entry, or pipeline trace is saved.",
              )
            : t(
                "pipelines.compare_nonpersistent_evidence",
                "No evidence is bound and no pipeline trace is saved.",
              )
        }}
      </span>
    </div>

    <PipelineComparisonResult
      v-if="researchResult"
      :result="researchResult"
      @open-pipeline="emit('openPipeline', $event)"
    />
    <PipelineEvidenceComparisonResult
      v-if="evidenceResult"
      :result="evidenceResult"
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
.mode-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  border: 0;
}
.mode-row legend {
  padding: 0;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: var(--fw-bold);
}
.mode-row label {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--text-primary);
  font-size: 0.875rem;
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
