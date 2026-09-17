<script setup lang="ts">
import { computed, useId } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusSegmentationTelemetry as CorpusSegmentationTelemetryData } from "../types/corpus";

const props=defineProps<CorpusSegmentationTelemetryData>();
const i18n=useI18nStore();
const headingId=`segmentation-telemetry-${useId()}`;
const helpId=`${headingId}-help`;
const items=computed(()=>[
  {key:"pdf_corpus.boundary_candidates",fallback:"Candidates",value:Number(props.candidateCount||0)},
  {key:"pdf_corpus.deterministic_splits",fallback:"Deterministic splits",value:Number(props.deterministicSplits||0)},
  {key:"pdf_corpus.llm_adjudications",fallback:"LLM adjudications",value:Number(props.llmAdjudications||0)},
  {key:"pdf_corpus.llm_batch_calls",fallback:"LLM batch calls",value:Number(props.llmBatchCalls||0)},
  {key:"pdf_corpus.llm_splits",fallback:"LLM splits",value:Number(props.llmSplits||0)},
  {key:"pdf_corpus.size_optimized_splits",fallback:"Size-optimized boundaries",value:Number(props.sizeOptimizedSplits??props.provisionalSplits??0)},
  {key:"pdf_corpus.absolute_safety_splits",fallback:"Absolute safety splits",value:Number(props.absoluteSafetySplits||0)},
  {key:"pdf_corpus.boundary_review_required",fallback:"Review-required boundaries",value:Number(props.reviewCount||0)},
]);
const description=computed(()=>i18n.t("pdf_corpus.segmentation_telemetry_help","Most transitions are resolved deterministically. LLM work is limited to a small ambiguous subset; uncertainty, omission, and classifier failure resolve conservatively to KEEP."));
</script>

<template>
  <section class="segmentation-telemetry" :aria-labelledby="headingId" :aria-describedby="helpId">
    <div class="telemetry-heading">
      <h3 :id="headingId">{{i18n.t('pdf_corpus.segmentation_telemetry','Segmentation decisions')}}</h3>
      <span :id="helpId">{{description}}</span>
    </div>
    <dl>
      <template v-for="item in items" :key="item.key">
        <div class="metric">
          <dt>{{i18n.t(item.key,item.fallback)}}</dt>
          <dd>{{item.value}}</dd>
        </div>
      </template>
    </dl>
    <p v-if="Number(props.budgetSkipped||0)>0 || Number(props.classifierFailures||0)>0" class="telemetry-note">
      <span v-if="Number(props.budgetSkipped||0)>0">{{i18n.tf('pdf_corpus.boundary_budget_skipped','{count} lower-value candidate(s) resolved to KEEP by the LLM budget.',{count:Number(props.budgetSkipped||0)})}}</span>
      <span v-if="Number(props.classifierFailures||0)>0">{{i18n.tf('pdf_corpus.boundary_failures_kept','{count} classifier failure(s) resolved to KEEP.',{count:Number(props.classifierFailures||0)})}}</span>
    </p>
  </section>
</template>

<style scoped>
.segmentation-telemetry{display:grid;gap:8px;padding:10px 11px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}
.telemetry-heading{display:grid;gap:2px}.telemetry-heading h3{margin:0;font-size:10px}.telemetry-heading span,.telemetry-note{font-size:9px;line-height:1.45;color:var(--muted)}
dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(112px,1fr));gap:6px;margin:0}.metric{display:grid;gap:2px;min-width:0;padding:7px 8px;border:1px solid var(--line);border-radius:8px;background:var(--card)}dt{font-size:8px;color:var(--muted)}dd{margin:0;font-size:15px;font-weight:800;font-variant-numeric:tabular-nums}.telemetry-note{display:flex;gap:10px;flex-wrap:wrap;margin:0}@media(max-width:640px){dl{grid-template-columns:1fr 1fr}}
</style>
