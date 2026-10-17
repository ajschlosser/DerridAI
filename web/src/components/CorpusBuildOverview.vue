<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import type { CorpusBuild } from "../api/pdfCorpus";
import type { ReviewQueue } from "../types/corpus";
import { corpusRecordCounts } from "../domain/corpusBuildPresentation";
import { useI18nStore } from "../stores/i18n";
import CorpusMetadataLiveStatus from "./CorpusMetadataLiveStatus.vue";

const props=defineProps<{build:CorpusBuild;locked:boolean;disabled?:boolean}>();
const emit=defineEmits<{review:[queue:ReviewQueue];settle:[];cancel:[]}>();
const i18n=useI18nStore();
const counts=computed(()=>corpusRecordCounts(props.build));
const ready=computed(()=>counts.value.ready);
const running=computed(()=>['running','queued'].includes(props.build.status));
const tiles=computed(()=>[
  {id:'ready' as const,count:counts.value.ready,label:i18n.t('pdf_corpus.overview_ready','Ready to review')},
  {id:'preparing' as const,count:counts.value.preparing,label:i18n.t('pdf_corpus.overview_preparing','Waiting for metadata')},
  {id:'issues' as const,count:counts.value.issues,label:i18n.t('pdf_corpus.overview_issues','Need attention')},
]);
function canOpen(queue:ReviewQueue){
  if(props.disabled||props.locked)return false;
  const value=queue==='ready'?counts.value.ready:queue==='issues'?counts.value.issues:counts.value.total;
  return value!==null&&value>0;
}
function review(queue:ReviewQueue){if(canOpen(queue))emit('review',queue)}
</script>

<template>
  <section class="build-overview" :aria-label="i18n.t('pdf_corpus.build_overview','Build overview')">
    <div class="overview-next">
      <h3>{{ready!==null&&ready>0?i18n.tf('pdf_corpus.overview_ready_title','{count} records are ready to review',{count:ready}):ready===0?i18n.t('pdf_corpus.overview_waiting_title','No records are ready to review yet'):i18n.t('pdf_corpus.overview_unknown_title','Inspect the available records')}}</h3>
      <p v-if="locked">{{i18n.t('pdf_corpus.overview_locked','Review is unavailable during this build stage. Existing records are preserved.')}}</p>
      <p v-else-if="running">{{i18n.t('pdf_corpus.overview_background','Review available records while metadata enrichment continues.')}}</p>
      <p v-else>{{i18n.t('pdf_corpus.overview_stopped','Review available records and unresolved decisions. Publication still requires all applicable checks.')}}</p>
      <div class="overview-actions">
        <button v-if="ready!==null&&ready>0" type="button" class="btn primary" :disabled="!canOpen('ready')" @click="review('ready')">{{i18n.tf('pdf_corpus.overview_review_ready','Review {count} ready records',{count:ready})}}</button>
        <button v-if="counts.issues!==null&&counts.issues>0" type="button" class="btn" :disabled="!canOpen('issues')" @click="review('issues')">{{i18n.t('pdf_corpus.overview_review_issues','Review records needing attention')}}</button>
        <button v-if="ready===null||ready===0" type="button" class="btn" :disabled="!canOpen('all')" @click="review('all')">{{i18n.t('pdf_corpus.overview_all','Inspect all records')}}</button>
      </div>
    </div>
    <CorpusMetadataLiveStatus v-if="running&&build.stage==='enriching'" :build="build" :disabled="disabled" @settle="emit('settle')" @cancel="emit('cancel')" />
    <section class="overview-records" :aria-label="i18n.t('pdf_corpus.overview_record_status','Record status')">
      <h4>{{i18n.t('pdf_corpus.overview_record_status','Record status')}}</h4>
      <p>{{i18n.tf('pdf_corpus.overview_record_counts','{total} records · {accepted} accepted · {rejected} rejected',{total:counts.total??'—',accepted:counts.accepted??'—',rejected:counts.rejected??'—'})}}</p>
      <dl class="overview-tiles"><div v-for="tile in tiles" :key="tile.id" :data-queue="tile.id"><dt>{{tile.label}}</dt><dd><span class="tile-count">{{tile.count??'—'}}</span><button v-if="tile.id!=='preparing'" type="button" class="btn" :disabled="!canOpen(tile.id)" @click="review(tile.id)">{{i18n.t('pdf_corpus.overview_view_records','View records')}}</button></dd></div></dl>
    </section>
  </section>
</template>

<style scoped>
.build-overview{display:grid;gap:16px}.overview-next{padding:18px;border:1px solid var(--line);border-radius:10px;background:var(--card)}h3{margin:0;font-size:1.375rem;line-height:1.3}h4{margin:0;font-size:1rem}p{margin:8px 0;color:var(--muted);font-size:.875rem;line-height:1.5}.overview-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}.btn{min-height:40px;font-size:.875rem}.btn:focus-visible{outline:3px solid var(--accent);outline-offset:2px}.overview-tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:12px 0 0}.overview-tiles>div{display:flex;flex-direction:column;align-items:flex-start;gap:8px;padding:14px;border:1px solid var(--line);border-radius:9px;background:var(--card)}dt{font-size:.875rem;font-weight:700}dd{display:flex;flex-direction:column;align-items:flex-start;gap:8px;margin:0;font-size:1.75rem;font-weight:800}.overview-tiles [data-queue="issues"]{border-color:var(--tone-warn-border);background:var(--tone-warn-bg)}@media(max-width:700px){.overview-tiles{grid-template-columns:1fr}.overview-next{padding:12px}h3{font-size:1.125rem}}
</style>
