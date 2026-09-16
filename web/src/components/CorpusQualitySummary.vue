<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
const props=defineProps<{build:Record<string,any>}>();
const i18n=useI18nStore();
const validation=computed(()=>props.build.validation||{});
const coverage=computed(()=>Math.round(Number(validation.value.coverage||0)*100));
const unresolved=computed(()=>Number(props.build.segmentation_unresolved_regions?.length||0));
const metadataDone=computed(()=>Number(props.build.metadata_completed||0));
const metadataTotal=computed(()=>Number(props.build.metadata_total||props.build.record_count||0));
</script>
<template>
  <section class="quality" :aria-labelledby="`quality-${build.build_id||'current'}`">
    <div class="quality-head"><div><b :id="`quality-${build.build_id||'current'}`">{{i18n.t('pdf_corpus.quality.title','Build quality')}}</b><small>{{i18n.t('pdf_corpus.quality.help','Quality gates summarize semantic topology, metadata completion, and source fidelity before publication.')}}</small></div></div>
    <dl>
      <div><dt>{{i18n.t('pdf_corpus.quality.segmentation','Segmentation')}}</dt><dd><b>{{Number(build.boundary_count||0).toLocaleString()}}</b> {{i18n.t('pdf_corpus.quality.boundaries','validated boundaries')}}<span :data-tone="unresolved?'warning':'ok'">{{unresolved?i18n.tf('pdf_corpus.quality.unresolved','{count} unresolved',{count:unresolved}):i18n.t('pdf_corpus.quality.resolved','Resolved')}}</span></dd></div>
      <div><dt>{{i18n.t('pdf_corpus.quality.metadata','Metadata')}}</dt><dd><b>{{metadataDone.toLocaleString()}} / {{metadataTotal.toLocaleString()}}</b> {{i18n.t('pdf_corpus.quality.records_complete','records complete')}}<span :data-tone="Number(build.needs_review_count||0)?'warning':'ok'">{{i18n.tf('pdf_corpus.quality.need_review','{count} need review',{count:Number(build.needs_review_count||0)})}}</span></dd></div>
      <div><dt>{{i18n.t('pdf_corpus.quality.source','Source fidelity')}}</dt><dd><b>{{validation.coverage==null?'—':`${coverage}%`}}</b> {{i18n.t('pdf_corpus.quality.accounted','accounted for')}}<span :data-tone="validation.valid===false?'warning':validation.valid===true?'ok':'neutral'">{{validation.valid===true?i18n.t('pdf_corpus.quality.passed','Validation passed'):validation.valid===false?i18n.t('pdf_corpus.quality.attention','Needs attention'):i18n.t('pdf_corpus.quality.pending','Pending')}}</span></dd></div>
    </dl>
  </section>
</template>
<style scoped>
.quality{border:1px solid var(--line);border-radius:10px;padding:10px 12px;display:grid;gap:9px;background:var(--card)}.quality-head>div{display:grid;gap:2px}.quality-head b{font-size:10px}.quality-head small{font-size:8px;color:var(--muted)}dl{margin:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}dl>div{border-inline-start:2px solid var(--line);padding-inline-start:9px;display:grid;gap:3px}dt{font-size:8px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:800}dd{margin:0;display:grid;gap:2px;font-size:8px;color:var(--muted)}dd>b{font-size:13px;color:var(--text)}dd span{font-weight:700}dd span[data-tone="ok"]::before{content:"✓ ";}dd span[data-tone="warning"]::before{content:"! ";}@media(max-width:720px){dl{grid-template-columns:1fr}}
</style>
