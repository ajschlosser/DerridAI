<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusBuild } from "../api/pdfCorpus";
const props=defineProps<{build:CorpusBuild}>();
const i18n=useI18nStore();
const reviewed=computed(()=>Number(props.build.accepted_count||0)+Number(props.build.rejected_count||0));
const remaining=computed(()=>Math.max(0,Number(props.build.record_count||0)-reviewed.value));
const metadataRemaining=computed(()=>Math.max(0,Number(props.build.metadata_total||0)-Number(props.build.metadata_completed||0)));
const published=computed(()=>Boolean(props.build.publication));
const running=computed(()=>["queued","running"].includes(String(props.build.status||"")));
const steps=computed(()=>[
  {id:"extract",label:i18n.t("pdf_corpus.pipeline.extract","Extract source"),state:"complete",detail:i18n.t("pdf_corpus.pipeline.extract_detail","PDF text and page geometry available")},
  {id:"construct",label:i18n.t("pdf_corpus.pipeline.construct","Construct records"),state:Number(props.build.record_count||0)>0?"complete":running.value?"active":"waiting",detail:Number(props.build.record_count||0)>0?i18n.tf("pdf_corpus.pipeline.records_created","{count} records created",{count:Number(props.build.record_count||0)}):i18n.t("pdf_corpus.pipeline.construct_wait","Waiting for corpus topology")},
  {id:"enrich",label:i18n.t("pdf_corpus.pipeline.enrich","Enrich metadata"),state:metadataRemaining.value===0&&Number(props.build.metadata_total||0)>0?"complete":props.build.stage==="enriching"?"active":Number(props.build.record_count||0)>0?"attention":"waiting",detail:Number(props.build.metadata_total||0)>0?i18n.tf("pdf_corpus.pipeline.metadata_progress","{done} of {total} metadata-complete",{done:Number(props.build.metadata_completed||0),total:Number(props.build.metadata_total||0)}):i18n.t("pdf_corpus.pipeline.enrich_wait","Waiting for records")},
  {id:"review",label:i18n.t("pdf_corpus.pipeline.review","Validate records"),state:remaining.value===0&&Number(props.build.record_count||0)>0?"complete":Number(props.build.record_count||0)>0?"attention":"waiting",detail:Number(props.build.record_count||0)>0?i18n.tf("pdf_corpus.pipeline.review_progress","{done} of {total} reviewed",{done:reviewed.value,total:Number(props.build.record_count||0)}):i18n.t("pdf_corpus.pipeline.review_wait","Waiting for records")},
  {id:"publish",label:i18n.t("pdf_corpus.pipeline.publish","Publish snapshot"),state:published.value?"complete":props.build.status==="ready"?"active":"waiting",detail:published.value?i18n.t("pdf_corpus.pipeline.published","Immutable JSONL snapshot published"):props.build.status==="ready"?i18n.t("pdf_corpus.pipeline.ready_publish","Ready for deliberate publication"):i18n.t("pdf_corpus.pipeline.publish_wait","Waiting for validation gates")},
]);
const nextKey=computed(()=>{
  if(running.value)return ["pdf_corpus.next_wait_build","Corpus construction is running."];
  if(remaining.value>0||Number(props.build.needs_review_count||0)>0)return ["pdf_corpus.next_review_records","Review the remaining proposed records."];
  if(Number(props.build.rejected_count||0)>0)return ["pdf_corpus.next_resolve_rejections","Resolve or reopen rejected records before publication."];
  if(metadataRemaining.value>0)return ["pdf_corpus.next_finish_metadata","Resolve the metadata issue queue before publication."];
  if(published.value)return ["pdf_corpus.next_published","This revision is published. Download it or edit the draft to create a new revision."];
  return ["pdf_corpus.next_publish","Quality gates have passed. Publish the JSONL when ready."];
});
</script>
<template>
  <section class="lifecycle-card" aria-labelledby="corpus-lifecycle-title">
    <header><div><span class="eyebrow">{{i18n.t('pdf_corpus.workflow','Workflow')}}</span><h3 id="corpus-lifecycle-title">{{i18n.t('pdf_corpus.pipeline_title','Corpus pipeline')}}</h3></div><strong>{{Math.round(Number(build.progress||0)*100)}}%</strong></header>
    <ol class="pipeline" aria-label="Corpus pipeline stages"><li v-for="step in steps" :key="step.id" :data-state="step.state"><span class="marker" aria-hidden="true"></span><div><b>{{step.label}}</b><small>{{step.detail}}</small></div></li></ol>
    <div class="next-action"><b>{{i18n.t('pdf_corpus.next_step','Next step')}}</b><span>{{i18n.t(nextKey[0],nextKey[1])}}</span></div>
  </section>
</template>
<style scoped>
.lifecycle-card{display:grid;gap:11px;padding:13px 14px;border:1px solid var(--line);border-radius:11px;background:var(--soft)}header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}header h3{font-size:13px;margin:2px 0 0}header>strong{font-size:18px}.eyebrow{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em}.pipeline{list-style:none;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:7px;margin:0;padding:0}.pipeline li{display:grid;grid-template-columns:10px minmax(0,1fr);gap:7px;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--card)}.pipeline .marker{width:8px;height:8px;margin-top:2px;border-radius:50%;background:#969696}.pipeline li[data-state="complete"] .marker{background:#287a4c}.pipeline li[data-state="active"] .marker{background:var(--accent)}.pipeline li[data-state="attention"] .marker{background:#a57914}.pipeline li div{display:grid;gap:2px;min-width:0}.pipeline b{font-size:9px}.pipeline small{font-size:8px;line-height:1.35;color:var(--muted)}.next-action{display:flex;gap:8px;align-items:baseline;padding-top:2px;font-size:10px}.next-action b{white-space:nowrap}.next-action span{color:var(--muted)}@media(max-width:1000px){.pipeline{grid-template-columns:repeat(2,1fr)}}@media(max-width:600px){.pipeline{grid-template-columns:1fr}.next-action{display:grid}}
</style>
