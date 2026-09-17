<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusBuild } from "../api/pdfCorpus";
const props=defineProps<{build:CorpusBuild;busy?:boolean}>();
const emit=defineEmits<{retryMetadata:[];publish:[];reviewMetadata:[]}>();
const i18n=useI18nStore();
const metadataRemaining=computed(()=>Math.max(0,Number(props.build.metadata_total||0)-Number(props.build.metadata_completed||0)));
const published=computed(()=>Boolean(props.build.publication));
const rejected=computed(()=>Number(props.build.rejected_count||0));
const ready=computed(()=>props.build.status==="ready"&&!published.value);
</script>
<template>
  <section v-if="build.record_count>0 && (build.accepted_count+Number(build.rejected_count||0))>=build.record_count" class="completion-card" :data-state="published?'published':ready?'ready':'blocked'" aria-labelledby="review-completion-title">
    <div class="completion-copy"><span class="eyebrow">{{i18n.t('pdf_corpus.review_complete','Record review complete')}}</span><h3 id="review-completion-title">{{published?i18n.t('pdf_corpus.published_revision','Published revision'):rejected>0?i18n.t('pdf_corpus.resolve_rejections_title','Resolve rejected records'):ready?i18n.t('pdf_corpus.ready_to_publish','Ready to publish'):i18n.t('pdf_corpus.finish_metadata_before_publish','Finish metadata before publishing')}}</h3><p>{{published?i18n.t('pdf_corpus.published_completion_help','The immutable JSONL snapshot is ready to download. Editing this draft will create a new unpublished revision.'):rejected>0?i18n.tf('pdf_corpus.rejections_blocking_help','{count} rejected record(s) must be corrected, removed, or reopened before publication.',{count:rejected}):ready?i18n.t('pdf_corpus.ready_completion_help','Record review, source validation, and required metadata gates have passed.'):i18n.tf('pdf_corpus.metadata_blocking_help','Record review is complete, but {count} record(s) still have publication-critical metadata to resolve.',{count:metadataRemaining})}}</p></div>
    <dl><div><dt>{{i18n.t('pdf_corpus.accepted_label','Accepted')}}</dt><dd>{{build.accepted_count||0}}</dd></div><div><dt>{{i18n.t('pdf_corpus.rejected','Rejected')}}</dt><dd>{{build.rejected_count||0}}</dd></div><div><dt>{{i18n.t('pdf_corpus.metadata_remaining','Metadata remaining')}}</dt><dd>{{metadataRemaining}}</dd></div><div><dt>{{i18n.t('pdf_corpus.source_coverage','Source coverage')}}</dt><dd>{{Math.round(Number(build.validation?.coverage??0)*100)}}%</dd></div></dl>
    <div v-if="!published" class="completion-actions"><button v-if="metadataRemaining>0 && rejected===0" type="button" class="btn" @click="emit('reviewMetadata')" :disabled="busy">{{i18n.t('pdf_corpus.review_metadata_issues','Review metadata issues')}}</button><button v-if="metadataRemaining>0 && rejected===0" type="button" class="btn" @click="emit('retryMetadata')" :disabled="busy">{{i18n.t('pdf_corpus.retry_incomplete_metadata','Retry incomplete metadata')}}</button><button v-if="ready" type="button" class="btn primary" @click="emit('publish')" :disabled="busy">{{i18n.t('pdf_corpus.finalize_publish','Finalize & publish')}}</button></div>
  </section>
</template>
<style scoped>
.completion-card{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(280px,.8fr) auto;gap:18px;align-items:center;padding:16px;border:1px solid var(--line);border-radius:12px;background:var(--soft)}.completion-card[data-state="ready"],.completion-card[data-state="published"]{background:#edf8f1}.eyebrow{font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:800}.completion-card h3{margin:2px 0 4px;font-size:15px}.completion-card p{margin:0;font-size:10px;line-height:1.5;color:var(--muted)}dl{display:grid;grid-template-columns:repeat(2,minmax(110px,1fr));gap:7px;margin:0}dl div{padding:8px;border-inline-start:2px solid var(--line)}dt{font-size:8px;color:var(--muted)}dd{margin:2px 0 0;font-size:12px;font-weight:800}.completion-actions{display:grid;gap:7px}@media(max-width:1000px){.completion-card{grid-template-columns:1fr}.completion-actions{display:flex;flex-wrap:wrap}}@media(max-width:600px){dl{grid-template-columns:1fr 1fr}.completion-actions{display:grid}}
</style>
