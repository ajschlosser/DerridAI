<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusBuild } from "../api/pdfCorpus";
const props=defineProps<{build:CorpusBuild;busy?:boolean}>();
const emit=defineEmits<{retry:[];review:[recordId:string]}>();
const i18n=useI18nStore();
const summary=computed(()=>props.build.metadata_issue_summary||{});
const rows=computed(()=>Object.entries(summary.value.by_field||{}).sort((a,b)=>b[1]-a[1]));
const recordRows=computed(()=>summary.value.records||[]);
const model=computed(()=>String(props.build.model||"—"));
const provider=computed(()=>String((props.build.request as Record<string,unknown>|undefined)?.provider_profile_id||props.build.provider||"—"));
</script>
<template>
  <section class="metadata-issues" aria-labelledby="metadata-issues-title">
    <header><div><span class="eyebrow">{{i18n.t('pdf_corpus.metadata_enrichment','Metadata enrichment')}}</span><h3 id="metadata-issues-title">{{i18n.t('pdf_corpus.metadata_needs_attention','Metadata needs attention')}}</h3><p>{{i18n.t('pdf_corpus.metadata_issue_help','Only unresolved publication-critical fields are retried. Completed record metadata is preserved.')}}</p></div><button type="button" class="btn primary" :disabled="busy" @click="emit('retry')">{{busy?i18n.t('pdf_corpus.retrying_metadata','Retrying metadata…'):i18n.tf('pdf_corpus.retry_metadata_count','Retry {count} record(s)',{count:Number(summary.records_incomplete||0)})}}</button></header>
    <div class="metrics"><span><b>{{summary.records_incomplete||0}}</b>{{i18n.t('pdf_corpus.records_incomplete','records incomplete')}}</span><span><b>{{summary.fields_unresolved||0}}</b>{{i18n.t('pdf_corpus.fields_unresolved','fields unresolved')}}</span><span><b>{{build.metadata_completed||0}} / {{build.metadata_total||0}}</b>{{i18n.t('pdf_corpus.records_metadata_complete','records metadata-complete')}}</span></div>
    <div class="execution"><span>{{i18n.t('pdf_corpus.provider_profile','Provider profile')}}: <code>{{provider}}</code></span><span>{{i18n.t('pdf_corpus.model','Model')}}: <code>{{model}}</code></span></div>
    <div v-if="rows.length" class="field-grid"><article v-for="([field,count]) in rows" :key="field"><b>{{i18n.t(`record.${field}`,field.replace(/_/g,' '))}}</b><span>{{count}}</span></article></div>
    <details v-if="recordRows.length"><summary>{{i18n.tf('pdf_corpus.review_metadata_records','Review {count} affected record(s)',{count:recordRows.length})}}</summary><div class="record-list"><button v-for="row in recordRows" :key="String(row.record_id)" type="button" @click="row.record_id&&emit('review',String(row.record_id))"><b>{{row.record_id}}</b><span>{{(row.fields||[]).map(field=>i18n.t(`record.${field}`,field.replace(/_/g,' '))).join(', ')}}</span><small>{{i18n.t('pdf_corpus.pages','pp.')}} {{row.page_start??'—'}}–{{row.page_end??'—'}}</small></button></div></details>
  </section>
</template>
<style scoped>
.metadata-issues{display:grid;gap:11px;padding:14px;border:1px solid #d9bf76;border-radius:11px;background:#fffaf0}.metadata-issues header{display:flex;justify-content:space-between;gap:18px;align-items:flex-start}.metadata-issues h3{margin:2px 0 4px;font-size:14px}.metadata-issues p{margin:0;max-width:72ch;font-size:10px;line-height:1.45;color:#5e4a12}.eyebrow{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:#7a651e;font-weight:800}.metrics{display:flex;gap:20px;flex-wrap:wrap}.metrics span{display:flex;gap:5px;align-items:baseline;font-size:9px;color:#6d5a26}.metrics b{font-size:13px;color:var(--text)}.execution{display:flex;gap:16px;flex-wrap:wrap;font-size:9px;color:var(--muted)}.execution code{color:var(--text)}.field-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:7px}.field-grid article{display:flex;justify-content:space-between;gap:10px;padding:8px 10px;border:1px solid rgba(94,74,18,.2);border-radius:8px;background:rgba(255,255,255,.55);font-size:9px}.field-grid span{font-weight:800}.metadata-issues details{font-size:9px}.metadata-issues summary{cursor:pointer;font-weight:800}.record-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:7px;margin-top:8px}.record-list button{display:grid;gap:3px;text-align:start;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:inherit;cursor:pointer}.record-list b{font-size:9px}.record-list span,.record-list small{font-size:8px;color:var(--muted)}@media(max-width:760px){.metadata-issues header{flex-direction:column}.metadata-issues header .btn{width:100%}}
</style>
