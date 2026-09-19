<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";

const props=withDefaults(defineProps<{
  sourceFilename?:string;
  pageCount?:number;
  blockCount?:number;
  structureSummary?:string;
  providerLabel?:string;
  modelLabel?:string;
  enrichmentMode?:"fast"|"deep";
  targetChars?:number;
  toleranceChars?:number;
  contextSafe?:boolean;
  activeBuildCount?:number;
  canStart?:boolean;
  busy?:boolean;
  warnings?:string[];
}>(),{sourceFilename:"",pageCount:0,blockCount:0,structureSummary:"",providerLabel:"",modelLabel:"",enrichmentMode:"fast",targetChars:0,toleranceChars:0,contextSafe:true,activeBuildCount:0,canStart:false,busy:false,warnings:()=>[]});
const emit=defineEmits<{build:[]} >();
const i18n=useI18nStore();
const ready=computed(()=>Boolean(props.sourceFilename&&props.canStart&&props.contextSafe));
const modeLabel=computed(()=>props.enrichmentMode==="deep"?i18n.t("pdf_corpus.enrichment_deep","Deep scholarly enrichment"):i18n.t("pdf_corpus.enrichment_fast","Fast corpus build"));
const sizing=computed(()=>props.targetChars?i18n.tf("pdf_corpus.readiness.sizing","{target} ± {tolerance} characters",{target:props.targetChars.toLocaleString(),tolerance:props.toleranceChars.toLocaleString()}):"—");
</script>

<template>
  <section class="build-readiness" :data-ready="ready?'true':'false'" aria-labelledby="build-readiness-title">
    <div class="readiness-copy">
      <div class="readiness-heading">
        <span class="eyebrow">{{i18n.t('pdf_corpus.readiness.eyebrow','Build summary')}}</span>
        <h3 id="build-readiness-title">{{ready?i18n.t('pdf_corpus.readiness.ready','Ready to build'):i18n.t('pdf_corpus.readiness.not_ready','Complete setup to build')}}</h3>
      </div>
      <dl>
        <div><dt>{{i18n.t('pdf_corpus.readiness.source','Source')}}</dt><dd>{{sourceFilename||i18n.t('pdf_corpus.choose_source_prompt','Choose a source PDF to continue.')}}<small v-if="sourceFilename">{{pageCount}} {{i18n.t('pdf_corpus.pages','pages')}} · {{blockCount}} {{i18n.t('pdf_corpus.blocks','blocks')}}</small></dd></div>
        <div><dt>{{i18n.t('pdf_corpus.readiness.structure','Structure')}}</dt><dd>{{structureSummary||i18n.t('pdf_corpus.readiness.structure_unset','Automatic defaults; review recommended')}}</dd></div>
        <div><dt>{{i18n.t('pdf_corpus.readiness.enrichment','Enrichment')}}</dt><dd>{{modeLabel}}</dd></div>
        <div><dt>{{i18n.t('pdf_corpus.readiness.llm','LLM')}}</dt><dd>{{providerLabel||i18n.t('pdf_corpus.provider_default','Provider default')}}<small v-if="modelLabel">{{modelLabel}}</small></dd></div>
        <div><dt>{{i18n.t('pdf_corpus.readiness.record_size','Record target')}}</dt><dd>{{sizing}}</dd></div>
      </dl>
      <div v-if="!contextSafe" class="readiness-alert" role="alert">{{i18n.t('pdf_corpus.context_unsafe','Context budget is too small')}}</div>
      <ul v-if="warnings.length" class="readiness-warnings" :aria-label="i18n.t('pdf_corpus.readiness.warnings','Setup notes')"><li v-for="warning in warnings" :key="warning">{{warning}}</li></ul>
      <p v-if="activeBuildCount" class="capacity-note">{{i18n.tf('pdf_corpus.active_build_capacity','{count} active build(s). Starting another build is independent and uses the selected provider profile capacity.',{count:activeBuildCount})}}</p>
    </div>
    <button type="button" class="btn primary build-action" :disabled="!ready||busy" @click="emit('build')">{{busy?i18n.t('pdf_corpus.starting','Starting…'):i18n.t(activeBuildCount?'pdf_corpus.start_another_build':'pdf_corpus.build_records',activeBuildCount?'Start another build':'Build record set')}}</button>
  </section>
</template>

<style scoped>
.build-readiness{position:sticky;bottom:12px;z-index:12;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:center;padding:16px 18px;border:1px solid var(--line);border-radius:14px;background:color-mix(in srgb,var(--card) 96%,transparent);box-shadow:0 14px 36px rgb(15 23 42 / .12);backdrop-filter:blur(10px)}
.readiness-copy{display:grid;gap:11px;min-width:0}.readiness-heading{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}.readiness-heading h3{margin:0;font-size:1rem}.eyebrow{font-size:.75rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:800}
dl{display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));gap:10px;margin:0}dl>div{min-width:0;display:grid;gap:2px;padding-inline-end:10px;border-inline-end:1px solid var(--line)}dl>div:last-child{border-inline-end:0}dt{font-size:.75rem;color:var(--muted);font-weight:800;text-transform:uppercase;letter-spacing:.04em}dd{min-width:0;margin:0;font-size:.875rem;font-weight:750;overflow-wrap:anywhere}dd small{display:block;margin-top:2px;color:var(--muted);font-size:.8125rem;font-weight:500}.readiness-alert{padding:8px 10px;border-radius:8px;background:#fff2f2;color:#7d2222;font-size:.8125rem;font-weight:750}.readiness-warnings{margin:0;padding-inline-start:20px;color:var(--muted);font-size:.8125rem;line-height:1.45}.capacity-note{margin:0;color:var(--muted);font-size:.8125rem}.build-action{min-width:160px;min-height:46px;font-weight:800}
@media(max-width:1100px){.build-readiness{position:static;grid-template-columns:1fr}dl{grid-template-columns:repeat(2,minmax(0,1fr))}dl>div{border-inline-end:0;border-bottom:1px solid var(--line);padding-bottom:8px}.build-action{width:100%}}
@media(max-width:620px){dl{grid-template-columns:1fr}.build-readiness{padding:14px}.readiness-heading{display:grid;gap:3px}}
</style>
