<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiStatusBadge from "./ui/UiStatusBadge.vue";
const props=withDefaults(defineProps<{contribution?:Record<string,unknown>;editorialExamplesUsed?:number}>(),{contribution:()=>({}),editorialExamplesUsed:0});
const i18n=useI18nStore();
const calls=computed(()=>Number(props.contribution.family_calls||0));
const useful=computed(()=>Number(props.contribution.llm_fields_usable||0));
const review=computed(()=>Number(props.contribution.llm_fields_review||0));
const minutes=computed(()=>Number(props.contribution.elapsed_ms||0)/60000);
const usefulPerMinute=computed(()=>Number(props.contribution.useful_fields_per_minute||0));
const tone=computed<"neutral"|"info"|"success"|"warning">(()=>calls.value<1?"neutral":useful.value>review.value?"success":useful.value>0?"info":"warning");
const label=computed(()=>calls.value<1?i18n.t('pdf_corpus.llm_effectiveness_waiting','Waiting for model contributions'):useful.value>0?i18n.tf('pdf_corpus.llm_effectiveness_useful','{count} useful model field(s)',{count:useful.value}):i18n.t('pdf_corpus.llm_effectiveness_none','No useful model fields yet'));
</script>
<template>
  <details class="llm-effectiveness">
    <summary>
      <div class="llm-summary-copy"><span class="eyebrow">{{i18n.t('pdf_corpus.llm_contribution','LLM contribution')}}</span><b>{{i18n.t('pdf_corpus.llm_effectiveness_title','Automation effectiveness')}}</b><small>{{i18n.tf('pdf_corpus.llm_effectiveness_summary','{calls} family call(s) · {minutes} min model time',{calls,minutes:minutes.toFixed(1)})}}</small></div>
      <div class="llm-summary-metrics"><UiStatusBadge :tone="tone" :label="label"/><span><b>{{usefulPerMinute.toFixed(1)}}</b> {{i18n.t('pdf_corpus.useful_fields_per_minute','useful fields/min')}}</span></div>
    </summary>
    <div class="llm-details">
      <p>{{i18n.t('pdf_corpus.llm_effectiveness_help','These metrics measure what automation actually contributed, not merely whether requests completed.')}}</p>
      <dl>
        <div><dt>{{i18n.t('pdf_corpus.llm_usable_fields','Useful LLM fields')}}</dt><dd>{{useful}}</dd></div>
        <div><dt>{{i18n.t('pdf_corpus.llm_review_fields','LLM fields needing review')}}</dt><dd>{{review}}</dd></div>
        <div><dt>{{i18n.t('pdf_corpus.inherited_fields','Inherited fields')}}</dt><dd>{{Number(contribution.inherited_fields||0)}}</dd></div>
        <div><dt>{{i18n.t('pdf_corpus.deterministic_fields','Deterministic fields')}}</dt><dd>{{Number(contribution.deterministic_fields||0)}}</dd></div>
        <div><dt>{{i18n.t('pdf_corpus.human_fields','Human-confirmed/override fields')}}</dt><dd>{{Number(contribution.human_fields||0)}}</dd></div>
        <div><dt>{{i18n.t('pdf_corpus.editorial_examples_used','Human-confirmed examples reused')}}</dt><dd>{{editorialExamplesUsed}}</dd></div>
      </dl>
    </div>
  </details>
</template>
<style scoped>
.llm-effectiveness{border:1px solid var(--line);border-radius:12px;background:var(--panel);overflow:hidden}.llm-effectiveness>summary{list-style:none;cursor:pointer;min-height:64px;display:flex;justify-content:space-between;align-items:center;gap:18px;padding:12px 16px}.llm-effectiveness>summary::-webkit-details-marker{display:none}.llm-effectiveness>summary:hover{background:var(--panel-2,var(--soft))}.llm-summary-copy{min-width:0;display:grid;gap:2px}.llm-summary-copy b{font-size:.9375rem}.llm-summary-copy small{font-size:.8125rem;color:var(--muted)}.eyebrow{font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:800}.llm-summary-metrics{display:flex;align-items:center;gap:14px;flex-wrap:wrap;justify-content:flex-end}.llm-summary-metrics>span{font-size:.8125rem;color:var(--muted)}.llm-summary-metrics>span b{color:var(--text);font-size:.9375rem}.llm-details{display:grid;gap:12px;padding:14px 16px 16px;border-top:1px solid var(--line);background:var(--panel-2,var(--soft))}.llm-details p{margin:0;max-width:75ch;color:var(--muted);font-size:.875rem;line-height:1.5}.llm-details dl{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:0}.llm-details dl>div{padding:10px;border:1px solid var(--line);border-radius:9px;background:var(--panel)}.llm-details dt{font-size:.8125rem;color:var(--muted);line-height:1.35}.llm-details dd{margin:4px 0 0;font-size:1.125rem;font-weight:800}.llm-effectiveness>summary:focus-visible{outline:3px solid var(--focus-ring,var(--accent));outline-offset:-3px}@media(max-width:760px){.llm-effectiveness>summary{align-items:flex-start;flex-direction:column}.llm-summary-metrics{justify-content:flex-start}.llm-details dl{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
