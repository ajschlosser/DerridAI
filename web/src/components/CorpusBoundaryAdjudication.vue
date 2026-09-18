<script setup lang="ts">
import { computed } from "vue";
import type { CorpusRecord } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";

const props=defineProps<{record:CorpusRecord;canPrevious:boolean;canNext:boolean;busy?:boolean}>();
const emit=defineEmits<{(event:"adjudicate",direction:"previous"|"next"):void}>();
const i18n=useI18nStore();
const prior=computed(()=>props.record.boundary_llm_before||null);
const next=computed(()=>props.record.boundary_llm_after||null);
function label(decision?:string){return i18n.t(`pdf_corpus.boundary_llm.${decision||"not_checked"}`,decision||i18n.t("pdf_corpus.boundary_not_checked","Not checked"))}
function confidence(value?:number){return typeof value==="number"?`${Math.round(value*100)}%`:i18n.t("pdf_corpus.confidence_unknown","Unknown")}
</script>

<template>
  <section class="boundary-adjudication" :aria-label="i18n.t('pdf_corpus.boundary_second_reader','Boundary second reader')">
    <header>
      <div>
        <span class="eyebrow">{{i18n.t('pdf_corpus.boundary_second_reader','Boundary second reader')}}</span>
        <p>{{i18n.t('pdf_corpus.boundary_second_reader_help','Use the LLM as a second reader for ambiguous record seams. It can recommend a nearby source-block boundary, but it never moves text automatically.')}}</p>
      </div>
    </header>
    <div class="boundary-grid">
      <article :class="['boundary-card',{'is-unavailable':!canPrevious}]">
        <div><b>{{i18n.t('pdf_corpus.previous_boundary','Previous boundary')}}</b><span v-if="prior">{{label(prior.decision)}} · {{confidence(prior.confidence)}}</span><span v-else>{{i18n.t('pdf_corpus.boundary_not_checked','Not checked')}}</span></div>
        <p v-if="prior?.reason">{{prior.reason}}</p>
        <p v-if="prior?.suggested_after_block_id&&prior.decision!=='keep'" class="recommendation">{{i18n.tf('pdf_corpus.boundary_suggested_seam','Suggested seam: after {block}',{block:prior.suggested_after_block_id})}}</p>
        <UiButton size="small" variant="soft" :disabled="busy||!canPrevious" @click="emit('adjudicate','previous')">{{i18n.t('pdf_corpus.check_with_llm','Check with LLM')}}</UiButton>
      </article>
      <article :class="['boundary-card',{'is-unavailable':!canNext}]">
        <div><b>{{i18n.t('pdf_corpus.next_boundary','Next boundary')}}</b><span v-if="next">{{label(next.decision)}} · {{confidence(next.confidence)}}</span><span v-else>{{i18n.t('pdf_corpus.boundary_not_checked','Not checked')}}</span></div>
        <p v-if="next?.reason">{{next.reason}}</p>
        <p v-if="next?.suggested_after_block_id&&next.decision!=='keep'" class="recommendation">{{i18n.tf('pdf_corpus.boundary_suggested_seam','Suggested seam: after {block}',{block:next.suggested_after_block_id})}}</p>
        <UiButton size="small" variant="soft" :disabled="busy||!canNext" @click="emit('adjudicate','next')">{{i18n.t('pdf_corpus.check_with_llm','Check with LLM')}}</UiButton>
      </article>
    </div>
  </section>
</template>

<style scoped>
.boundary-adjudication{display:grid;gap:.75rem;padding:1rem;border:1px solid var(--border,#d6d9df);border-radius:12px;background:var(--surface-raised,#fff)}
.boundary-adjudication header p{margin:.25rem 0 0;color:var(--text-muted,#59606c);font-size:.875rem;line-height:1.45}.eyebrow{font-size:.75rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--text-muted,#59606c)}
.boundary-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem}.boundary-card{display:grid;align-content:start;gap:.5rem;padding:.75rem;border:1px solid var(--border,#d6d9df);border-radius:10px;background:var(--surface,#fff)}.boundary-card>div{display:flex;justify-content:space-between;gap:.75rem;align-items:baseline;flex-wrap:wrap}.boundary-card span{font-size:.8125rem;color:var(--text-muted,#59606c)}.boundary-card p{margin:0;font-size:.875rem;line-height:1.45}.boundary-card .recommendation{font-weight:600}.is-unavailable{opacity:.72}
@media (max-width:760px){.boundary-grid{grid-template-columns:1fr}}
</style>
