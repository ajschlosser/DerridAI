<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResponseFaqRecord } from "../../types/research";

const props=defineProps<{record:ResponseFaqRecord;evidenceCount:number;grade?:string|number|null}>();
const emit=defineEmits<{browse:[]}>();
const i18n=useI18nStore();
function formatDate(value?:string){if(!value)return "";try{return new Intl.DateTimeFormat(i18n.locale,{dateStyle:"medium",timeStyle:"short"}).format(new Date(value))}catch{return value}}
</script>

<template>
  <section class="response-selection-bar" :aria-label="i18n.t('faq.current_response','Current saved response')">
    <div class="response-selection-main">
      <span class="section-label">{{i18n.t('faq.cached_result','Cached result')}}</span>
      <h2>{{record.question||i18n.t('faq.untitled_question','Untitled question')}}</h2>
      <div class="response-selection-meta">
        <span v-if="record.created_at"><AppIcon name="history"/>{{formatDate(record.created_at)}}</span>
        <span v-if="record.provider||record.model"><AppIcon name="spark"/>{{record.provider||i18n.t('research.provider','Provider')}}<template v-if="record.model"> · {{record.model}}</template></span>
        <span><AppIcon name="books"/>{{evidenceCount}} {{i18n.t('research.evidence_records','evidence records')}}</span>
        <span v-if="grade!=null" class="grade"><AppIcon name="spark"/>{{i18n.t('faq.saved_grade','Saved grade')}} {{grade}}/10</span>
      </div>
    </div>
    <button type="button" class="response-selection-browse" @click="emit('browse')"><AppIcon name="search"/>{{i18n.t('faq.browse_archive','Browse saved research')}}</button>
  </section>
</template>

<style scoped>
.response-selection-bar{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:center;padding:14px 16px;border:1px solid #dfe6ec;border-radius:14px;background:linear-gradient(135deg,#fbfcfd,#fff 64%);box-shadow:0 4px 16px rgba(15,23,42,.035)}.response-selection-main{min-width:0}.response-selection-main h2{margin:3px 0 7px;color:#24364d;font:600 clamp(17px,1.5vw,21px)/1.28 Georgia,"Times New Roman",serif;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden}.response-selection-meta{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.response-selection-meta>span{display:inline-flex;align-items:center;gap:5px;min-height:27px;padding:3px 7px;border:1px solid #e1e7ec;border-radius:999px;background:#fff;color:#64748b;font-size:11px}.response-selection-meta svg{width:12px;height:12px}.response-selection-meta .grade{border-color:#cadfd2;background:#f5fbf7;color:#3f6650;font-weight:780}.response-selection-browse{min-height:40px;display:flex;align-items:center;justify-content:center;gap:7px;border:1px solid #cedbd3;border-radius:10px;background:#fff;padding:0 12px;color:#315441;font-weight:780;cursor:pointer;white-space:nowrap}.response-selection-browse svg{width:16px;height:16px}.response-selection-browse:focus-visible{outline:3px solid var(--ui-accent-focus);outline-offset:2px}@media(max-width:760px){.response-selection-bar{grid-template-columns:1fr}.response-selection-browse{width:100%}}
</style>
