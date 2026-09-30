<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import PipelineFilterBar from "./PipelineFilterBar.vue";
import UiButton from "../ui/UiButton.vue";
import {
  emptyRunFilters,
  type PipelineRunFilters,
} from "../../features/pipelines/composables/usePipelineStudioNavigation";
import { pipelineRunStatusLabel } from "../../domain/pipelinePresentation";
import { purposeText, termLabel } from "../../domain/pipelineWorkflows";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineDefinition,
  PipelinePurpose,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  filters: PipelineRunFilters;
  pipelines: PipelineDefinition[];
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  resultLabel: string;
}>();
// Filtering stays submit-based: the server is queried only when the reader applies them.
const emit = defineEmits<{ apply: [filters: PipelineRunFilters] }>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const draft = ref<PipelineRunFilters>({ ...emptyRunFilters(), ...props.filters });
watch(
  () => props.filters,
  (filters) => (draft.value = { ...emptyRunFilters(), ...filters }),
  { deep: true },
);

const statuses = ["completed", "failed", "cancelled", "running"];
const pipelineIds = computed(() => [...new Set(props.pipelines.map((item) => item.pipeline_id))]);
const purposeOptions = computed(() =>
  props.purposes.filter(
    (purpose) => !draft.value.category || purpose.category === draft.value.category,
  ),
);
const advancedCount = computed(
  () => [draft.value.feature, draft.value.pipelineId, draft.value.owner].filter(Boolean).length,
);
const active = computed(() => Object.values(draft.value).some(Boolean));

function submit() {
  emit("apply", { ...draft.value });
}
function reset() {
  draft.value = emptyRunFilters();
  emit("apply", { ...draft.value });
}
</script>

<template>
  <PipelineFilterBar
    class="trace-filters"
    :label="t('pipelines.filter_executions', 'Filter executions')"
    has-advanced
    :advanced-count="advancedCount"
    :can-reset="active"
    :result-label="resultLabel"
    @submit="submit"
    @reset="reset"
  >
    <template #search>
      <label>
        <span>{{ t("pipelines.query", "Query") }}</span>
        <input
          v-model="draft.query"
          class="control"
          type="search"
          :placeholder="t('pipelines.query_placeholder', 'Run ID, pipeline, feature, or owner')"
        />
      </label>
    </template>
    <template #primary>
      <label>
        <span>{{ t("pipelines.used_for", "Used for") }}</span>
        <select v-model="draft.category" class="control" @change="draft.feature = ''">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="term in vocabulary.categories" :key="term.id" :value="term.id">
            {{ termLabel(term, t) }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.status", "Status") }}</span>
        <select v-model="draft.status" class="control">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="status in statuses" :key="status" :value="status">
            {{ pipelineRunStatusLabel(status, t) }}
          </option>
        </select>
      </label>
    </template>
    <template #advanced>
      <label>
        <span>{{ t("pipelines.filter_purpose", "Purpose") }}</span>
        <select v-model="draft.feature" class="control">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option
            v-for="purpose in purposeOptions"
            :key="purpose.purpose_id"
            :value="purpose.consuming_feature"
          >
            {{ purposeText(purpose, "label", t) }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.pipeline", "Pipeline") }}</span>
        <select v-model="draft.pipelineId" class="control">
          <option value="">{{ t("pipelines.filter_all", "All") }}</option>
          <option v-for="pipelineId in pipelineIds" :key="pipelineId" :value="pipelineId">
            {{ pipelineId }}
          </option>
        </select>
      </label>
      <label>
        <span>{{ t("pipelines.owner", "Owner") }}</span>
        <input v-model="draft.owner" class="control" type="search" autocomplete="off" />
      </label>
    </template>
    <template #actions>
      <UiButton
        type="submit"
        variant="primary"
        :label="t('pipelines.apply_filters', 'Apply filters')"
      />
      <slot name="menu" />
    </template>
  </PipelineFilterBar>
</template>
