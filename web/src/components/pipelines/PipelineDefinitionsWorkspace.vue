<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { ref } from "vue";
import PipelineDefinitionNavigator from "./PipelineDefinitionNavigator.vue";
import PipelineDefinitionDetail from "./PipelineDefinitionDetail.vue";
import PipelineNewDialog from "./PipelineNewDialog.vue";
import PipelineVersionEditorPanel from "./PipelineVersionEditorPanel.vue";
import UiButton from "../ui/UiButton.vue";
import type { PipelineDefinitionFilters } from "../../features/pipelines/composables/usePipelineStudioNavigation";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAnalysis,
  PipelineAssignment,
  PipelineDefinition,
  PipelinePurpose,
  PipelineStrategy,
  PipelineStrategyLatency,
  PipelineValidationResponse,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

const props = defineProps<{
  pipelines: PipelineDefinition[];
  strategies: PipelineStrategy[];
  assignments: PipelineAssignment[];
  purposes: PipelinePurpose[];
  vocabulary: PipelineWorkflowVocabulary;
  selectedKey: string;
  workflow: string;
  filters: PipelineDefinitionFilters;
  selectedPipeline: PipelineDefinition | null;
  selectedPurpose: PipelinePurpose | null;
  selectedAssignment: PipelineAssignment | null;
  assigned: boolean;
  canAssign: boolean;
  assigning: boolean;
  cloning: boolean;
  /** True while a blank draft is being prepared. */
  creating?: boolean;
  draft: PipelineDefinition | null;
  draftPurpose: PipelinePurpose | null;
  validation: PipelineValidationResponse | null;
  saving: boolean;
  analysis?: PipelineAnalysis | null;
  analysisLoading?: boolean;
  analysisError?: string;
  strategyLatency?: Record<string, PipelineStrategyLatency> | null;
}>();

const emit = defineEmits<{
  select: [key: string];
  "update:workflow": [category: string];
  "update:filters": [filters: PipelineDefinitionFilters];
  "update:draft": [draft: PipelineDefinition];
  clone: [];
  create: [purposeId: string];
  assign: [];
  resetAssignment: [];
  cancel: [];
  validate: [];
  save: [];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
const newOpen = ref(false);

function create(purposeId: string) {
  newOpen.value = false;
  emit("create", purposeId);
}
</script>

<template>
  <div
    id="pipeline-panel-pipelines"
    class="pipeline-definitions"
    role="tabpanel"
    aria-labelledby="pipeline-tab-pipelines"
  >
    <div v-if="!draft" class="pipeline-definitions-actions">
      <UiButton
        variant="primary"
        icon="plus"
        :label="t('pipelines.new_pipeline', 'New pipeline')"
        :disabled="creating"
        @click="newOpen = true"
      />
    </div>

    <section
      v-if="!draft"
      class="pipeline-definitions-workspace"
      :aria-label="t('pipelines.definitions', 'Pipeline definitions')"
    >
      <PipelineDefinitionNavigator
        :pipelines="pipelines"
        :assignments="assignments"
        :purposes="purposes"
        :vocabulary="vocabulary"
        :selected-key="selectedKey"
        :workflow="workflow"
        :filters="filters"
        @select="emit('select', $event)"
        @update:workflow="emit('update:workflow', $event)"
        @update:filters="emit('update:filters', $event)"
      />
      <PipelineDefinitionDetail
        v-if="selectedPipeline"
        :pipeline="selectedPipeline"
        :strategies="strategies"
        :purpose="selectedPurpose"
        :purposes="purposes"
        :vocabulary="vocabulary"
        :assignment="selectedAssignment"
        :assigned="assigned"
        :can-assign="canAssign"
        :assigning="assigning"
        :cloning="cloning"
        @clone="emit('clone')"
        @assign="emit('assign')"
        @reset-assignment="emit('resetAssignment')"
      />
    </section>

    <PipelineVersionEditorPanel
      v-if="draft"
      :model-value="draft"
      :strategies="strategies"
      :purpose="draftPurpose"
      :vocabulary="vocabulary"
      :validation="validation"
      :saving="saving"
      :analysis="analysis"
      :analysis-loading="analysisLoading"
      :analysis-error="analysisError"
      :strategy-latency="strategyLatency"
      @update:model-value="emit('update:draft', $event)"
      @cancel="emit('cancel')"
      @validate="emit('validate')"
      @save="emit('save')"
    />

    <PipelineNewDialog
      v-if="newOpen"
      :purposes="purposes"
      :vocabulary="vocabulary"
      :initial="props.selectedPurpose?.purpose_id"
      :busy="creating"
      @close="newOpen = false"
      @create="create"
    />
  </div>
</template>

<style scoped>
.pipeline-definitions {
  display: grid;
  gap: var(--space-4);
}
.pipeline-definitions-actions {
  display: flex;
  justify-content: flex-end;
}
.pipeline-definitions-workspace {
  display: grid;
  grid-template-columns: minmax(320px, 380px) minmax(0, 1fr);
  gap: var(--space-4);
  align-items: start;
}
@media (max-width: 960px) {
  .pipeline-definitions-workspace {
    grid-template-columns: 1fr;
  }
}
</style>
