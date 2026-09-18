<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { ReviewQueue } from "../types/corpus";
const props=withDefaults(defineProps<{modelValue:ReviewQueue;total:number;ready:number;issues:number;metadata:number;topology:number;sourceProblems?:number;accepted:number;rejected:number;disabled?:boolean}>(),{sourceProblems:0,disabled:false});
const emit=defineEmits<{"update:modelValue":[value:ReviewQueue]}>();
const i18n=useI18nStore();
const tabs:Array<{id:ReviewQueue;key:string;fallback:string}>=[
  {id:"all",key:"pdf_corpus.queue_all",fallback:"All"},
  {id:"ready",key:"pdf_corpus.queue_ready",fallback:"Ready"},
  {id:"issues",key:"pdf_corpus.queue_issues",fallback:"Needs attention"},
  {id:"metadata",key:"pdf_corpus.queue_metadata",fallback:"Metadata"},
  {id:"topology",key:"pdf_corpus.queue_topology",fallback:"Topology"},
  {id:"source",key:"pdf_corpus.queue_source",fallback:"Source problem"},
  {id:"accepted",key:"pdf_corpus.queue_accepted",fallback:"Accepted"},
  {id:"rejected",key:"pdf_corpus.queue_rejected",fallback:"Rejected"},
];
function tabCount(id:ReviewQueue):number{
  switch(id){
    case "all": return props.total;
    case "ready": return props.ready;
    case "issues": return props.issues;
    case "metadata": return props.metadata;
    case "topology": return props.topology;
    case "source": return props.sourceProblems;
    case "accepted": return props.accepted;
    case "rejected": return props.rejected;
  }
}

const visibleTabs=computed(()=>tabs.filter(tab=>{
  if(["metadata","topology","source"].includes(tab.id))return tabCount(tab.id)>0||props.modelValue===tab.id;
  return true;
}));
function onKeydown(event:KeyboardEvent,current:ReviewQueue){
  if(!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;
  const ids=visibleTabs.value.map(tab=>tab.id);
  const currentIndex=Math.max(0,ids.indexOf(current));
  let next=currentIndex;
  if(event.key==="Home")next=0;
  else if(event.key==="End")next=ids.length-1;
  else if(event.key==="ArrowRight")next=(currentIndex+1)%ids.length;
  else next=(currentIndex-1+ids.length)%ids.length;
  event.preventDefault();
  const value=ids[next];
  emit("update:modelValue",value);
  queueMicrotask(()=>document.querySelector<HTMLButtonElement>(`[data-review-queue="${value}"]`)?.focus());
}
</script>

<template>
  <div class="queue-tabs" role="toolbar" :aria-label="i18n.t('pdf_corpus.review_queue','Review queue')">
    <button v-for="tab in visibleTabs" :key="tab.id" type="button" class="queue-tab"
      :data-review-queue="tab.id" :aria-pressed="modelValue===tab.id" :tabindex="modelValue===tab.id?0:-1" :disabled="disabled"
      @keydown="onKeydown($event,tab.id)" @click="emit('update:modelValue',tab.id)">
      <span>{{i18n.t(tab.key,tab.fallback)}}</span><strong>{{tabCount(tab.id)}}</strong>
    </button>
  </div>
</template>

<style scoped>
.queue-tabs{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.queue-tab{min-height:40px;border:1px solid transparent;border-radius:999px;background:transparent;color:var(--muted);padding:7px 11px;display:flex;align-items:center;gap:7px;cursor:pointer;font-size:13px;font-weight:700}.queue-tab strong{min-width:22px;padding:2px 6px;border-radius:999px;background:var(--soft);color:var(--text);font-size:11px;text-align:center}.queue-tab[aria-pressed="true"]{background:var(--card);border-color:var(--line);color:var(--text);box-shadow:0 1px 2px rgb(0 0 0/.04)}.queue-tab:focus-visible{outline:3px solid var(--accent);outline-offset:2px}.queue-tab:disabled{opacity:.55;cursor:not-allowed}
</style>
