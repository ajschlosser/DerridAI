<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import CorpusSegmentationTelemetry from "./CorpusSegmentationTelemetry.vue";
import type { CorpusSegmentationTelemetry as CorpusSegmentationTelemetryData } from "../types/corpus";

const props=defineProps<{
  status:string;
  stage:string;
  progress:number;
  recordCount:number;
  reviewCount:number;
  acceptedCount:number;
  error?:string|null;
  warnings?:string[];
  validation?:Record<string,any>|null;
  llmMetrics?:{calls?:number;manifest_calls?:number;segmentation_calls?:number;metadata_calls?:number;discourse_calls?:number;quotation_calls?:number;indexing_calls?:number;retries?:number;structured_output_failures?:number;escalations?:number}|null;
  unresolvedCount?:number;
  segmentationTelemetry?:CorpusSegmentationTelemetryData|null;
}>();
const i18n=useI18nStore();
function statusLabel(){return i18n.t(`pdf_corpus.status.${props.status}`,String(props.status||"unknown").replace(/_/g," "))}
function stageLabel(){return i18n.t(`pdf_corpus.stage.${props.stage}`,String(props.stage||"unknown").replace(/_/g," "))}
const validationReady=computed(()=>Boolean(props.validation&&typeof props.validation.valid==="boolean"&&["review","ready","published"].includes(String(props.stage||""))));
const validationValid=computed(()=>props.validation?.valid===true);
const validationCoverage=computed(()=>Math.round(Number(props.validation?.coverage||0)*100));
const validationEvidenceIssues=computed(()=>Number(props.validation?.metadata_evidence_errors?.length||0));
const validationSchemaIssues=computed(()=>Number(props.validation?.metadata_schema_errors?.length||0));
const validationPageLabelIssues=computed(()=>Number(props.validation?.printed_page_label_errors?.length||0));
const validationTextFidelityIssues=computed(()=>Number(props.validation?.text_fidelity_errors?.length||0));
const validationSourceOrderIssues=computed(()=>Number(props.validation?.source_order_errors?.length||0));
const validationPageMappingIssues=computed(()=>Number(props.validation?.page_mapping_errors?.length||0));
const validationCitationIssues=computed(()=>Number(props.validation?.citation_errors?.length||0));
const stageExplanation=computed(()=>{
  const stage=String(props.stage||"");
  const map:Record<string,string>={structure:"Reading the PDF and identifying document-level structure and bibliography.",document_review:"Finalizing document-level metadata automatically before segmentation.",segmenting:"Generating plausible boundary candidates deterministically and asking the LLM only a budgeted set of small local split/keep questions.",constructing_records:"Constructing reviewable records from the conserved source topology. Advisory suspicious-boundary checks no longer block this step.",reconciling:"Finalizing topology for a build created by an older pipeline.",enriching:"Enriching each constructed record with discourse, quotation, and indexing metadata. Source text and boundaries are already preserved.",review:"Automated processing is complete. Review the proposed records.",ready:"All quality gates have passed. The corpus is ready to publish.",published:"The reviewed corpus has been finalized as JSONL and is ready to download."};
  return i18n.t(`pdf_corpus.stage_help.${stage}`,map[stage]||"Processing the current corpus-build stage.");
});
const nextStage=computed(()=>{const order=["structure","segmenting","constructing_records","enriching","review","ready","published"];const i=order.indexOf(String(props.stage||""));return i>=0&&i<order.length-1?i18n.t(`pdf_corpus.stage.${order[i+1]}`,order[i+1].replace(/_/g," ")):""});
</script>

<template>
  <section class="corpus-build-progress" :aria-label="i18n.t('pdf_corpus.build_progress','Corpus build progress')" aria-live="polite">
    <div class="build-status-line"><span class="pill">{{statusLabel()}}</span><span>{{i18n.t('pdf_corpus.stage','Stage')}}: {{stageLabel()}}</span><span>{{props.recordCount}} {{i18n.t('pdf_corpus.records','records')}}</span><span>{{props.reviewCount}} {{i18n.t('pdf_corpus.need_review','need review')}}</span><span>{{props.acceptedCount}} {{i18n.t('pdf_corpus.accepted','accepted')}}</span></div>
    <div v-if="Number(props.unresolvedCount||0)>0" class="unresolved-line" role="status"><b>{{props.unresolvedCount}}</b> {{i18n.t('pdf_corpus.unresolved_regions','boundary decision(s) to review')}}</div>
    <div class="stage-explanation"><b>{{stageLabel()}}</b><span>{{stageExplanation}}</span><small v-if="nextStage">{{i18n.t('pdf_corpus.next_stage','Next')}}: {{nextStage}}</small></div>
    <CorpusSegmentationTelemetry v-if="props.segmentationTelemetry" v-bind="props.segmentationTelemetry" />
    <div v-if="props.llmMetrics&&Number(props.llmMetrics.calls||0)>0" class="llm-metrics"><span><b>{{props.llmMetrics.calls||0}}</b> {{i18n.t('pdf_corpus.llm_calls','LLM calls')}}</span><span v-if="props.llmMetrics.manifest_calls">{{props.llmMetrics.manifest_calls}} {{i18n.t('pdf_corpus.manifest_calls','document analysis')}}</span><span v-if="props.llmMetrics.segmentation_calls">{{props.llmMetrics.segmentation_calls}} {{i18n.t('pdf_corpus.segmentation_calls','segmentation')}}</span><span v-if="props.llmMetrics.metadata_calls">{{props.llmMetrics.metadata_calls}} {{i18n.t('pdf_corpus.metadata_calls','record enrichment')}}</span><span v-if="props.llmMetrics.retries">{{props.llmMetrics.retries}} {{i18n.t('pdf_corpus.llm_retries','retries')}}</span><span v-if="props.llmMetrics.structured_output_failures">{{props.llmMetrics.structured_output_failures}} {{i18n.t('pdf_corpus.structured_failures','structured-output corrections')}}</span><span v-if="props.llmMetrics.escalations">{{props.llmMetrics.escalations}} {{i18n.t('pdf_corpus.escalations','escalations')}}</span></div>
    <div class="progress-track" role="progressbar" :aria-label="i18n.t('pdf_corpus.build_progress','Corpus build progress')" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="Math.round((props.progress||0)*100)" :aria-valuetext="i18n.tf('pdf_corpus.progress_percent','{percent}% complete',{percent:Math.round((props.progress||0)*100)})"><span :style="{width:`${Math.round((props.progress||0)*100)}%`}"></span></div>
    <div v-if="props.error" class="build-warning" role="alert"><b>{{i18n.t('pdf_corpus.build_error','Build error')}}</b><span>{{props.error}}</span></div>
    <details v-if="props.warnings?.length" class="warnings"><summary>{{i18n.tf('pdf_corpus.warnings_count','{count} build warning(s)',{count:props.warnings.length})}}</summary><ul><li v-for="warning in props.warnings" :key="warning">{{warning}}</li></ul></details>
    <div v-if="validationReady" class="validation-strip" :class="{invalid:!validationValid}"><b>{{validationValid?i18n.t('pdf_corpus.validation_passed','Validation passed'):i18n.t('pdf_corpus.validation_attention','Validation needs attention')}}</b><span>{{validationCoverage}}% {{i18n.t('pdf_corpus.source_coverage','source coverage')}}</span><span v-if="validationEvidenceIssues">{{validationEvidenceIssues}} {{i18n.t('pdf_corpus.evidence_issues','evidence issue(s)')}}</span><span v-if="validationSchemaIssues">{{validationSchemaIssues}} {{i18n.t('pdf_corpus.schema_issues','metadata schema issue(s)')}}</span><span v-if="validationPageLabelIssues">{{validationPageLabelIssues}} {{i18n.t('pdf_corpus.page_label_issues','printed-page issue(s)')}}</span></div>
    <details v-if="validationReady&&!validationValid" class="validation-details"><summary>{{i18n.t('pdf_corpus.validation_details','Validation details')}}</summary><ul>
      <li v-if="validationTextFidelityIssues">{{validationTextFidelityIssues}} {{i18n.t('pdf_corpus.text_fidelity_issues','text-fidelity issue(s)')}}</li>
      <li v-if="validationSourceOrderIssues">{{validationSourceOrderIssues}} {{i18n.t('pdf_corpus.source_order_issues','source-order issue(s)')}}</li>
      <li v-if="validationPageMappingIssues">{{validationPageMappingIssues}} {{i18n.t('pdf_corpus.page_mapping_issues','page-mapping issue(s)')}}</li>
      <li v-if="validationSchemaIssues">{{validationSchemaIssues}} {{i18n.t('pdf_corpus.schema_issues','metadata schema issue(s)')}}</li>
      <li v-if="validationCitationIssues">{{validationCitationIssues}} {{i18n.t('pdf_corpus.citation_issues','citation issue(s)')}}</li>
    </ul></details>
  </section>
</template>

<style scoped>
.corpus-build-progress{display:grid;gap:9px}.stage-explanation{display:grid;grid-template-columns:max-content 1fr max-content;gap:10px;align-items:center;padding:8px 10px;border-radius:8px;background:var(--soft);font-size:.8125rem}.stage-explanation span{color:var(--muted);line-height:1.4}.stage-explanation small{color:var(--muted);white-space:nowrap}.unresolved-line{padding:7px 9px;border-radius:8px;background:#fff6e5;color:#604300;font-size:.8125rem}.build-status-line,.validation-strip,.llm-metrics{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:.8125rem;color:var(--muted)}.pill{border:1px solid var(--line);border-radius:999px;padding:3px 7px;text-transform:uppercase;font-weight:800;letter-spacing:.04em}.progress-track{height:7px;border-radius:999px;background:var(--soft);overflow:hidden}.progress-track span{display:block;height:100%;background:var(--accent);transition:width .25s}.build-warning{display:grid;gap:3px;padding:9px;border:1px solid #c96b6b;border-radius:8px;background:#fff2f2;color:#7d2222;font-size:.8125rem}.warnings,.validation-details{font-size:.8125rem}.warnings summary,.validation-details summary{cursor:pointer;font-weight:700}.validation-details ul{margin:6px 0 0;padding-inline-start:20px}.validation-strip{padding:7px 9px;border-radius:8px;background:#edf8f1}.validation-strip.invalid{background:#fff6e5;color:#604300}@media(prefers-reduced-motion:reduce){.progress-track span{transition:none}}
</style>
