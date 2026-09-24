<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";

const props=defineProps<{stage?:string;status?:string;published?:boolean;hasAsset?:boolean;hasManifest?:boolean;acceptedCount?:number;recordCount?:number;blockerCount?:number;canPublish?:boolean}>();
const i18n=useI18nStore();

const currentStep=computed(()=>{
  const stage=String(props.stage||"");
  const status=String(props.status||"");
  if(props.published||status==="published")return 4;
  if(["ready"].includes(stage)||status==="ready"||Boolean(props.canPublish))return 4;
  if(["enriching","review","metadata_retry"].includes(stage)||status==="awaiting_review")return 3;
  if(["analyzing","extracting","manifest","segmenting","constructing_records","reconciling"].includes(stage)||["queued","running","awaiting_manifest_review"].includes(status))return 2;
  return 1;
});

const steps=computed(()=>{
  const items=[
    [1,"pdf_corpus.workflow.source_configure","Source & configure"],
    [2,"pdf_corpus.workflow.build_phase","Build"],
    [3,"pdf_corpus.workflow.review_short","Review"],
    [4,"pdf_corpus.workflow.publish","Publish"],
  ] as const;
  return items.map(([number,key,fallback])=>({
    number,
    label:i18n.t(key,fallback),
    state:number<currentStep.value?"complete":number===currentStep.value?"current":"upcoming",
  }));
});
</script>

<template>
  <nav class="workflow" :aria-label="i18n.t('pdf_corpus.workflow.label')">
    <ol>
      <li v-for="step in steps" :key="step.number" :data-state="step.state" :aria-current="step.state==='current'?'step':undefined">
        <span class="marker" aria-hidden="true">{{step.state==='complete'?'✓':step.number}}</span>
        <span class="step-copy">
          <b>{{step.label}}</b>
          <small>{{step.state==='complete'?i18n.t('pdf_corpus.workflow.complete'):step.state==='current'?i18n.t('pdf_corpus.workflow.current'):i18n.t('pdf_corpus.workflow.upcoming')}}</small>
        </span>
      </li>
    </ol>
  </nav>
</template>

<style scoped>
.workflow{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:10px 12px}
.workflow ol{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.workflow li{min-width:0;display:flex;align-items:center;gap:8px;padding:8px;border-radius:9px;color:var(--muted)}
.workflow li[data-state="current"]{background:var(--soft);color:var(--text)}
.workflow li[data-state="complete"]{color:var(--text)}
.marker{display:grid;place-items:center;inline-size:26px;block-size:26px;flex:0 0 26px;border:1px solid var(--line);border-radius:50%;font-size:.8125rem;font-weight:800}
.workflow li[data-state="current"] .marker{border-color:var(--accent);box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 15%,transparent)}
.step-copy{display:grid;gap:1px;min-width:0}
.step-copy b{font-size:.8125rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.step-copy small{font-size:.8125rem;color:var(--muted)}
@media(max-width:760px){.workflow ol{grid-template-columns:1fr 1fr}}
@media(max-width:480px){.workflow ol{grid-template-columns:1fr}}
</style>
