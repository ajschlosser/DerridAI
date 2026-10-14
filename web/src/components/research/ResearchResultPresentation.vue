<script setup lang="ts">
import { computed, ref } from "vue";
import ResearchAnswerWorkspace from "./ResearchAnswerWorkspace.vue";
import ResearchEvidencePanel from "./ResearchEvidencePanel.vue";
import type { ResearchEvidenceSelection, ResearchJob, ResearchResult } from "../../types/research";

const props=withDefaults(defineProps<{
  job?:ResearchJob|null;
  result?:ResearchResult|null;
  selectedEvidence?:ResearchEvidenceSelection[];
  activeEvidenceIndex?:number;
  busy?:boolean;
  canGrade?:boolean;
  canRemoveSelected?:boolean;
  researcher?:boolean;
}>(),{
  job:null,
  result:null,
  selectedEvidence:()=>[],
  activeEvidenceIndex:0,
  busy:false,
  canGrade:true,
  canRemoveSelected:false,
  researcher:false,
});

const emit=defineEmits<{
  copy:[];
  grade:[];
  rerun:[];
  details:[];
  evidence:[index:number];
  selectEvidence:[index:number];
  removeSelected:[key:string];
  clearSelected:[];
}>();
// Citations for the evidence item being previewed (hover/focus) or, failing
// that, the item open in the inspector are highlighted in the answer.
const previewIndex=ref<number|null>(null);
const highlightIndex=computed(()=>props.result?.evidence?.length?(previewIndex.value??props.activeEvidenceIndex):null);
</script>

<template>
  <div class="research-workspace-grid research-result-presentation">
    <ResearchAnswerWorkspace
      :job="job"
      :result="result"
      :busy="busy"
      :can-grade="canGrade"
      :highlight-index="highlightIndex"
      @copy="emit('copy')"
      @grade="emit('grade')"
      @rerun="emit('rerun')"
      @details="emit('details')"
      @evidence="emit('evidence',$event)"
    />
    <ResearchEvidencePanel
      :selected-evidence="selectedEvidence"
      :result-evidence="result?.evidence||[]"
      :active-index="activeEvidenceIndex"
      :answer="result?.answer||''"
      :can-remove="canRemoveSelected"
      :researcher="researcher"
      @select="emit('selectEvidence',$event)"
      @preview="previewIndex=$event"
      @remove="emit('removeSelected',$event)"
      @clear="emit('clearSelected')"
    />
  </div>
</template>
