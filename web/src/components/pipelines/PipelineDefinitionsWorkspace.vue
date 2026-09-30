<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import PipelineDefinitionNavigator from "./PipelineDefinitionNavigator.vue";
import PipelineDefinitionDetail from "./PipelineDefinitionDetail.vue";
import PipelineVersionEditorPanel from "./PipelineVersionEditorPanel.vue";
import type { PipelineDefinitionFilters } from "../../features/pipelines/composables/usePipelineStudioNavigation";
import { useI18nStore } from "../../stores/i18n";
import type {
  PipelineAssignment,
  PipelineDefinition,
  PipelinePurpose,
  PipelineStrategy,
  PipelineValidationResponse,
  PipelineWorkflowVocabulary,
} from "../../types/pipelines";

defineProps<{
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
  draft: PipelineDefinition | null;
  draftPurpose: PipelinePurpose | null;
  validation: PipelineValidationResponse | null;
  saving: boolean;
}>();

const emit = defineEmits<{
  select: [key: string];
  "update:workflow": [category: string];
  "update:filters": [filters: PipelineDefinitionFilters];
  "update:draft": [draft: PipelineDefinition];
  clone: [];
  assign: [];
  resetAssignment: [];
  cancel: [];
  validate: [];
  save: [];
}>();

const i18n = useI18nStore();
const t = (key: string, fallback: string) => i18n.t(key, fallback);
</script>

<template>
  <div
    id="pipeline-panel-pipelines"
    class="pipeline-definitions"
    role="tabpanel"
    aria-labelledby="pipeline-tab-pipelines"
  >
    <section
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
      @update:model-value="emit('update:draft', $event)"
      @cancel="emit('cancel')"
      @validate="emit('validate')"
      @save="emit('save')"
    />
  </div>
</template>

<style scoped>
.pipeline-definitions {
  display: grid;
  gap: var(--space-4);
}
.pipeline-definitions-workspace {
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr);
  gap: var(--space-4);
  align-items: start;
}
@media (max-width: 960px) {
  .pipeline-definitions-workspace {
    grid-template-columns: 1fr;
  }
}
</style>
