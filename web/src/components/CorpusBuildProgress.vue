<script setup lang="ts">
import { useI18nStore } from "../stores/i18n";

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
  llmMetrics?:{calls?:number;retries?:number;structured_output_failures?:number;escalations?:number}|null;
}>();
const i18n=useI18nStore();
function statusLabel(){return i18n.t(`pdf_corpus.status.${props.status}`,String(props.status||"unknown").replace(/_/g," "))}
function stageLabel(){return i18n.t(`pdf_corpus.stage.${props.stage}`,String(props.stage||"unknown").replace(/_/g," "))}
</script>

<template>
  <section class="corpus-build-progress" :aria-label="i18n.t('pdf_corpus.build_progress','Corpus build progress')" aria-live="polite">
    <div class="build-status-line"><span class="pill">{{statusLabel()}}</span><span>{{i18n.t('pdf_corpus.stage','Stage')}}: {{stageLabel()}}</span><span>{{props.recordCount}} {{i18n.t('pdf_corpus.records','records')}}</span><span>{{props.reviewCount}} {{i18n.t('pdf_corpus.need_review','need review')}}</span><span>{{props.acceptedCount}} {{i18n.t('pdf_corpus.accepted','accepted')}}</span></div>
    <div v-if="props.llmMetrics&&Number(props.llmMetrics.calls||0)>0" class="llm-metrics"><span>{{props.llmMetrics.calls||0}} {{i18n.t('pdf_corpus.llm_calls','LLM calls')}}</span><span v-if="props.llmMetrics.retries">{{props.llmMetrics.retries}} {{i18n.t('pdf_corpus.llm_retries','retries')}}</span><span v-if="props.llmMetrics.structured_output_failures">{{props.llmMetrics.structured_output_failures}} {{i18n.t('pdf_corpus.structured_failures','structured-output corrections')}}</span><span v-if="props.llmMetrics.escalations">{{props.llmMetrics.escalations}} {{i18n.t('pdf_corpus.escalations','escalations')}}</span></div>
    <div class="progress-track" role="progressbar" :aria-label="i18n.t('pdf_corpus.build_progress','Corpus build progress')" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="Math.round((props.progress||0)*100)"><span :style="{width:`${Math.round((props.progress||0)*100)}%`}"></span></div>
    <div v-if="props.error" class="build-warning" role="alert"><b>{{i18n.t('pdf_corpus.build_error','Build error')}}</b><span>{{props.error}}</span></div>
    <details v-if="props.warnings?.length" class="warnings"><summary>{{i18n.tf('pdf_corpus.warnings_count','{count} build warning(s)',{count:props.warnings.length})}}</summary><ul><li v-for="warning in props.warnings" :key="warning">{{warning}}</li></ul></details>
    <div v-if="props.validation" class="validation-strip" :class="{invalid:!props.validation.valid}"><b>{{props.validation.valid?i18n.t('pdf_corpus.validation_passed','Validation passed'):i18n.t('pdf_corpus.validation_attention','Validation needs attention')}}</b><span>{{Math.round(Number(props.validation.coverage||0)*100)}}% {{i18n.t('pdf_corpus.source_coverage','source coverage')}}</span><span v-if="props.validation.metadata_evidence_errors?.length">{{props.validation.metadata_evidence_errors.length}} {{i18n.t('pdf_corpus.evidence_issues','evidence issue(s)')}}</span><span v-if="props.validation.metadata_schema_errors?.length">{{props.validation.metadata_schema_errors.length}} {{i18n.t('pdf_corpus.schema_issues','metadata schema issue(s)')}}</span><span v-if="props.validation.printed_page_label_errors?.length">{{props.validation.printed_page_label_errors.length}} {{i18n.t('pdf_corpus.page_label_issues','printed-page issue(s)')}}</span></div>
    <details v-if="props.validation&&!props.validation.valid" class="validation-details"><summary>{{i18n.t('pdf_corpus.validation_details','Validation details')}}</summary><ul>
      <li v-if="props.validation.text_fidelity_errors?.length">{{props.validation.text_fidelity_errors.length}} {{i18n.t('pdf_corpus.text_fidelity_issues','text-fidelity issue(s)')}}</li>
      <li v-if="props.validation.source_order_errors?.length">{{props.validation.source_order_errors.length}} {{i18n.t('pdf_corpus.source_order_issues','source-order issue(s)')}}</li>
      <li v-if="props.validation.page_mapping_errors?.length">{{props.validation.page_mapping_errors.length}} {{i18n.t('pdf_corpus.page_mapping_issues','page-mapping issue(s)')}}</li>
      <li v-if="props.validation.metadata_schema_errors?.length">{{props.validation.metadata_schema_errors.length}} {{i18n.t('pdf_corpus.schema_issues','metadata schema issue(s)')}}</li>
      <li v-if="props.validation.citation_errors?.length">{{props.validation.citation_errors.length}} {{i18n.t('pdf_corpus.citation_issues','citation issue(s)')}}</li>
    </ul></details>
  </section>
</template>

<style scoped>
.corpus-build-progress{display:grid;gap:9px}.build-status-line,.validation-strip,.llm-metrics{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:9px;color:var(--muted)}.pill{border:1px solid var(--line);border-radius:999px;padding:3px 7px;text-transform:uppercase;font-weight:800;letter-spacing:.04em}.progress-track{height:7px;border-radius:999px;background:var(--soft);overflow:hidden}.progress-track span{display:block;height:100%;background:var(--accent);transition:width .25s}.build-warning{display:grid;gap:3px;padding:9px;border:1px solid #c96b6b;border-radius:8px;background:#fff2f2;color:#7d2222;font-size:10px}.warnings,.validation-details{font-size:10px}.warnings summary,.validation-details summary{cursor:pointer;font-weight:700}.validation-details ul{margin:6px 0 0;padding-inline-start:20px}.validation-strip{padding:7px 9px;border-radius:8px;background:#edf8f1}.validation-strip.invalid{background:#fff6e5;color:#604300}@media(prefers-reduced-motion:reduce){.progress-track span{transition:none}}
</style>
