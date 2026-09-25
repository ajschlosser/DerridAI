<script setup lang="ts">
import ResearchAnswerWorkspace from "./ResearchAnswerWorkspace.vue";
import ResearchEvidencePanel from "./ResearchEvidencePanel.vue";
import type { ResearchEvidenceSelection, ResearchJob, ResearchResult } from "../../types/research";

withDefaults(
  defineProps<{
    job?: ResearchJob | null;
    result?: ResearchResult | null;
    selectedEvidence?: ResearchEvidenceSelection[];
    activeEvidenceIndex?: number;
    busy?: boolean;
    canGrade?: boolean;
    canRemoveSelected?: boolean;
    researcher?: boolean;
  }>(),
  {
    job: null,
    result: null,
    selectedEvidence: () => [],
    activeEvidenceIndex: 0,
    busy: false,
    canGrade: true,
    canRemoveSelected: false,
    researcher: false,
  },
);

const emit = defineEmits<{
  copy: [];
  grade: [];
  rerun: [];
  details: [];
  evidence: [index: number];
  selectEvidence: [index: number];
  removeSelected: [key: string];
  clearSelected: [];
}>();
</script>

<template>
  <div class="research-workspace-grid research-result-presentation">
    <ResearchAnswerWorkspace
      :job="job"
      :result="result"
      :busy="busy"
      :can-grade="canGrade"
      @copy="emit('copy')"
      @grade="emit('grade')"
      @rerun="emit('rerun')"
      @details="emit('details')"
      @evidence="emit('evidence', $event)"
    />
    <ResearchEvidencePanel
      :selected-evidence="selectedEvidence"
      :result-evidence="result?.evidence || []"
      :active-index="activeEvidenceIndex"
      :can-remove="canRemoveSelected"
      :researcher="researcher"
      @select="emit('selectEvidence', $event)"
      @remove="emit('removeSelected', $event)"
      @clear="emit('clearSelected')"
    />
  </div>
</template>
