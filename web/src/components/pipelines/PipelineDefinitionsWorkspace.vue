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
  exporting?: boolean;
  importing?: boolean;
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
  export: [];
  import: [event: Event];
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
const importInput = ref<HTMLInputElement | null>(null);

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
    <div class="pipeline-definitions-actions">
      <UiButton
        variant="primary"
        icon="plus"
        :label="t('pipelines.new_pipeline', 'New pipeline')"
        :disabled="creating || Boolean(draft)"
        :disabled-reason="
          draft
            ? t(
                'pipelines.new_pipeline_while_editing',
                'Finish or cancel the version you are editing first.',
              )
            : ''
        "
        @click="newOpen = true"
      />
      <input
        ref="importInput"
        type="file"
        accept="application/json,.json"
        class="sr-only"
        :disabled="importing || Boolean(draft)"
        @change="emit('import', $event)"
      />
      <UiButton
        icon="upload"
        :label="
          importing
            ? t('pipelines.importing', 'Importing…')
            : t('pipelines.import_pipeline', 'Import pipeline…')
        "
        :disabled="importing || Boolean(draft)"
        :disabled-reason="
          draft
            ? t(
                'pipelines.import_while_editing',
                'Finish or cancel the version you are editing before importing another pipeline.',
              )
            : ''
        "
        @click="importInput?.click()"
      />
    </div>

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
        :exporting="exporting"
        @clone="emit('clone')"
        @export="emit('export')"
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
