<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusBuild } from "../api/pdfCorpus";
const props=defineProps<{build:CorpusBuild}>();
const i18n=useI18nStore();
const reviewed=computed(()=>Number(props.build.accepted_count||0)+Number(props.build.rejected_count||0));
const remaining=computed(()=>Math.max(0,Number(props.build.record_count||0)-reviewed.value));
const metadataRemaining=computed(()=>Math.max(0,Number(props.build.metadata_total||0)-Number(props.build.metadata_completed||0)));
const nextKey=computed(()=>{
  if(["queued","running"].includes(props.build.status))return ["pdf_corpus.next_wait_build","Corpus construction is running."];
  if(remaining.value>0||Number(props.build.needs_review_count||0)>0)return ["pdf_corpus.next_review_records","Review the remaining proposed records."];
  if(Number(props.build.rejected_count||0)>0)return ["pdf_corpus.next_resolve_rejections","Resolve or reopen rejected records before publication."];
  if(metadataRemaining.value>0)return ["pdf_corpus.next_finish_metadata","Complete or retry incomplete metadata before publication."];
  if(props.build.publication)return ["pdf_corpus.next_published","This revision is published. Download it or edit the draft to create a new revision."];
  return ["pdf_corpus.next_publish","Quality gates have passed. Review the publication summary and publish the JSONL."];
});
</script>
<template>
  <section class="lifecycle-card" aria-labelledby="corpus-lifecycle-title">
    <div class="lifecycle-heading"><div><span class="eyebrow">{{i18n.t('pdf_corpus.workflow','Workflow')}}</span><h3 id="corpus-lifecycle-title">{{i18n.t('pdf_corpus.what_next','What happens next?')}}</h3></div><strong>{{Math.round(Number(build.progress||0)*100)}}%</strong></div>
    <div class="lifecycle-metrics"><span><b>{{reviewed}}</b>{{i18n.t('pdf_corpus.reviewed','reviewed')}}</span><span><b>{{remaining}}</b>{{i18n.t('pdf_corpus.remaining','remaining')}}</span><span><b>{{metadataRemaining}}</b>{{i18n.t('pdf_corpus.metadata_remaining','metadata remaining')}}</span></div>
    <p>{{i18n.t(nextKey[0],nextKey[1])}}</p>
  </section>
</template>
<style scoped>
.lifecycle-card{display:grid;gap:9px;padding:12px 14px;border:1px solid var(--line);border-radius:11px;background:var(--soft)}.lifecycle-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.lifecycle-heading h3{font-size:13px;margin:2px 0 0}.lifecycle-heading>strong{font-size:18px}.eyebrow{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em}.lifecycle-metrics{display:flex;gap:16px;flex-wrap:wrap}.lifecycle-metrics span{display:flex;align-items:baseline;gap:5px;font-size:9px;color:var(--muted)}.lifecycle-metrics b{font-size:12px;color:var(--text)}p{margin:0;font-size:10px;line-height:1.45;color:var(--muted)}
</style>
