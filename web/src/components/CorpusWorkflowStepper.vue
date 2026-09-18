<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
const props=defineProps<{stage?:string;status?:string;published?:boolean;hasAsset?:boolean;hasManifest?:boolean;acceptedCount?:number;recordCount?:number;blockerCount?:number;canPublish?:boolean}>();
const i18n=useI18nStore();
const steps=computed(()=>{
  const stage=String(props.stage||"");const status=String(props.status||"");
  let current=props.hasAsset?2:1;
  if(props.hasManifest||["analyzing","extracting","manifest","segmenting","reconciling","enriching","review","ready","published"].includes(stage))current=3;
  if(["segmenting","reconciling"].includes(stage))current=4;
  if(["enriching","review"].includes(stage)||["awaiting_review"].includes(status))current=5;
  if(stage==="ready"||status==="ready")current=Number(props.blockerCount||0)>0?6:7;
  if(props.canPublish&&status!=="published")current=7;
  if(props.published||status==="published")current=7;
  if(status==="blocked")current=Math.max(3,Math.min(current,6));
  const items=[
    [1,"pdf_corpus.workflow.load","Load PDF"],
    [2,"pdf_corpus.workflow.configure","Configure"],
    [3,"pdf_corpus.workflow.initialize","Initialize"],
    [4,"pdf_corpus.workflow.segment","Segment"],
    [5,"pdf_corpus.workflow.review","Collaborative review"],
    [6,"pdf_corpus.workflow.resolve","Resolve exceptions"],
    [7,"pdf_corpus.workflow.publish","Publish"],
  ] as const;
  return items.map(([number,key,fallback])=>({number,label:i18n.t(key,fallback),state:number<current?"complete":number===current?"current":"upcoming"}));
});
</script>
<template><nav class="workflow" :aria-label="i18n.t('pdf_corpus.workflow.label','Corpus build workflow')"><ol><li v-for="step in steps" :key="step.number" :data-state="step.state" :aria-current="step.state==='current'?'step':undefined"><span class="marker" aria-hidden="true">{{step.state==='complete'?'✓':step.number}}</span><span class="step-copy"><b>{{step.label}}</b><small>{{step.state==='complete'?i18n.t('pdf_corpus.workflow.complete','Complete'):step.state==='current'?i18n.t('pdf_corpus.workflow.current','Current'):i18n.t('pdf_corpus.workflow.upcoming','Upcoming')}}</small></span></li></ol></nav></template>
<style scoped>.workflow{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:9px 12px}.workflow ol{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px}.workflow li{min-width:0;display:flex;align-items:center;gap:7px;padding:6px;border-radius:9px;color:var(--muted)}.workflow li[data-state="current"]{background:var(--soft);color:var(--text)}.workflow li[data-state="complete"]{color:var(--text)}.marker{display:grid;place-items:center;inline-size:24px;block-size:24px;flex:0 0 24px;border:1px solid var(--line);border-radius:50%;font-size:.8125rem;font-weight:800}.workflow li[data-state="current"] .marker{border-color:var(--accent);box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 15%,transparent)}.step-copy{display:grid;gap:1px;min-width:0}.step-copy b{font-size:.8125rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.step-copy small{font-size:.8125rem;color:var(--muted)}@media(max-width:1100px){.workflow ol{grid-template-columns:repeat(4,1fr)}}@media(max-width:700px){.workflow ol{grid-template-columns:1fr 1fr}}@media(max-width:480px){.workflow ol{grid-template-columns:1fr}}</style>
