<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
const props=defineProps<{stage?:string;status?:string;hasAsset?:boolean;hasManifest?:boolean;acceptedCount?:number;recordCount?:number}>();
const i18n=useI18nStore();
const steps=computed(()=>{
  const stage=String(props.stage||"");const status=String(props.status||"");let current=props.hasAsset?1:0;
  if(props.hasManifest||["segmenting","reconciling","enriching","review","ready","published"].includes(stage))current=2;
  if(["enriching","review","ready","published"].includes(stage))current=3;
  if(["review","ready","published"].includes(stage)||["awaiting_review","ready","published"].includes(status))current=4;
  if(status==="published")current=5;
  if(status==="blocked")current=2;
  const items=[[1,"pdf_corpus.workflow.source","Source"],[2,"pdf_corpus.workflow.analyze","Analyze"],[3,"pdf_corpus.workflow.build","Build records"],[4,"pdf_corpus.workflow.review","Review"],[5,"pdf_corpus.workflow.publish","Publish"]] as const;
  return items.map(([number,key,fallback])=>({number,label:i18n.t(key,fallback),state:number<current?"complete":number===current?"current":"upcoming"}));
});
</script>
<template><nav class="workflow" :aria-label="i18n.t('pdf_corpus.workflow.label','Corpus build workflow')"><ol><li v-for="step in steps" :key="step.number" :data-state="step.state" :aria-current="step.state==='current'?'step':undefined"><span class="marker" aria-hidden="true">{{step.state==='complete'?'✓':step.number}}</span><span class="step-copy"><b>{{step.label}}</b><small>{{step.state==='complete'?i18n.t('pdf_corpus.workflow.complete','Complete'):step.state==='current'?i18n.t('pdf_corpus.workflow.current','Current'):i18n.t('pdf_corpus.workflow.upcoming','Upcoming')}}</small></span></li></ol></nav></template>
<style scoped>.workflow{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:9px 12px}.workflow ol{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}.workflow li{min-width:0;display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:9px;color:var(--muted)}.workflow li[data-state="current"]{background:var(--soft);color:var(--text)}.workflow li[data-state="complete"]{color:var(--text)}.marker{display:grid;place-items:center;inline-size:24px;block-size:24px;flex:0 0 24px;border:1px solid var(--line);border-radius:50%;font-size:9px;font-weight:800}.workflow li[data-state="current"] .marker{border-color:var(--accent);box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 15%,transparent)}.step-copy{display:grid;gap:1px;min-width:0}.step-copy b{font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.step-copy small{font-size:8px;color:var(--muted)}@media(max-width:820px){.workflow ol{grid-template-columns:1fr 1fr}}@media(max-width:480px){.workflow ol{grid-template-columns:1fr}}</style>
