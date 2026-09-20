<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusBuild } from "../api/pdfCorpus";
const props=defineProps<{build:CorpusBuild}>();
const i18n=useI18nStore();
const pipeline=computed(()=>props.build.pipeline_state?.stages||{});
const readiness=computed(()=>props.build.publication_readiness||{});
const reviewed=computed(()=>Number(readiness.value.records_reviewed??(Number(props.build.accepted_count||0)+Number(props.build.rejected_count||0))));
const metadataRemaining=computed(()=>Number(readiness.value.metadata_records_remaining??Math.max(0,Number(props.build.metadata_total||0)-Number(props.build.metadata_completed||0))));
function stateFor(id:string,fallback:string){return String((pipeline.value[id] as Record<string,unknown>|undefined)?.state||fallback)}
const steps=computed(()=>[
  {id:"extraction",label:i18n.t("pdf_corpus.pipeline.extract","Extract source"),state:stateFor("extraction",Number(props.build.source_block_count||0)>0?"complete":"waiting"),detail:i18n.tf("pdf_corpus.pipeline.extract_detail_count","{count} source blocks available",{count:Number(props.build.source_block_count||0)})},
  {id:"construction",label:i18n.t("pdf_corpus.pipeline.construct","Construct records"),state:stateFor("construction",Number(props.build.record_count||0)>0?"complete":"waiting"),detail:i18n.tf("pdf_corpus.pipeline.records_created","{count} records created",{count:Number(props.build.record_count||0)})},
  {id:"enrichment",label:i18n.t("pdf_corpus.pipeline.enrich","Enrich metadata"),state:stateFor("enrichment",metadataRemaining.value===0?"complete":"attention"),detail:metadataRemaining.value?i18n.tf("pdf_corpus.pipeline.metadata_remaining","{count} record(s) still need required metadata",{count:metadataRemaining.value}):i18n.t("pdf_corpus.pipeline.metadata_complete","Required metadata resolved")},
  {id:"review",label:i18n.t("pdf_corpus.pipeline.review","Review records"),state:stateFor("review",reviewed.value>=Number(props.build.record_count||0)&&Number(props.build.record_count||0)>0?"complete":"attention"),detail:i18n.tf("pdf_corpus.pipeline.review_progress","{done} of {total} reviewed",{done:reviewed.value,total:Number(props.build.record_count||0)})},
  {id:"validation",label:i18n.t("pdf_corpus.pipeline.validate","Validate corpus"),state:stateFor("validation",props.build.validation?.valid?"complete":"blocked"),detail:props.build.validation?.valid?i18n.t("pdf_corpus.pipeline.validation_passed","Source, metadata, and schema checks passed"):i18n.t("pdf_corpus.pipeline.validation_wait","Validation has unresolved blockers")},
  {id:"publication",label:i18n.t("pdf_corpus.pipeline.publish","Publish snapshot"),state:stateFor("publication",props.build.publication?"complete":readiness.value.can_publish?"active":"blocked"),detail:props.build.publication?i18n.t("pdf_corpus.pipeline.published","Immutable JSONL snapshot published"):readiness.value.can_publish?i18n.t("pdf_corpus.pipeline.ready_publish","Ready for deliberate publication"):i18n.t("pdf_corpus.pipeline.publish_wait","Waiting for required gates")},
]);
const nextLabel=computed(()=>i18n.t(`pdf_corpus.next_action.${String(readiness.value.next_action||'inspect')}`,String(readiness.value.next_action||"inspect").replace(/_/g," ")));
</script>
<template>
  <section class="lifecycle-card" aria-labelledby="corpus-lifecycle-title">
    <header><div><span class="eyebrow">{{i18n.t('pdf_corpus.workflow','Workflow')}}</span><h3 id="corpus-lifecycle-title">{{i18n.t('pdf_corpus.pipeline_title','Corpus pipeline')}}</h3></div><strong>{{Math.round(Number(build.progress||0)*100)}}%</strong></header>
    <ol class="pipeline" aria-label="Corpus pipeline stages"><li v-for="step in steps" :key="step.id" :data-state="step.state"><span class="marker" aria-hidden="true"></span><div><b>{{step.label}}</b><small>{{step.detail}}</small></div></li></ol>
    <div class="next-action" role="status"><b>{{i18n.t('pdf_corpus.next_step','Next step')}}</b><span>{{nextLabel}}</span></div>
  </section>
</template>
<style scoped>
.lifecycle-card{display:grid;gap:11px;padding:13px 14px;border:1px solid var(--line);border-radius:11px;background:var(--soft)}header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}header h3{font-size:0.8125rem;margin:2px 0 0}header>strong{font-size:1.125rem}.eyebrow{font-size:.8125rem;color:var(--muted);text-transform:uppercase;letter-spacing:.07em}.pipeline{list-style:none;display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:7px;margin:0;padding:0}.pipeline li{display:grid;grid-template-columns:10px minmax(0,1fr);gap:7px;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--card)}.pipeline .marker{width:8px;height:8px;margin-top:2px;border-radius:50%;background:#969696}.pipeline li[data-state="complete"] .marker{background:#287a4c}.pipeline li[data-state="active"] .marker{background:var(--accent)}.pipeline li[data-state="attention"] .marker{background:#a57914}.pipeline li[data-state="blocked"] .marker{background:#a13f3f}.pipeline li div{display:grid;gap:2px;min-width:0}.pipeline b{font-size:.8125rem}.pipeline small{font-size:.8125rem;line-height:1.35;color:var(--muted)}.next-action{display:flex;gap:8px;align-items:baseline;padding-top:2px;font-size:.8125rem}.next-action b{white-space:nowrap}.next-action span{color:var(--muted)}@media(max-width:1200px){.pipeline{grid-template-columns:repeat(3,1fr)}}@media(max-width:700px){.pipeline{grid-template-columns:1fr}.next-action{display:grid}}
</style>
