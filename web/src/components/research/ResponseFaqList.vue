<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResponseFaqRecord } from "../../types/research";

withDefaults(defineProps<{records?:ResponseFaqRecord[];selectedId?:string}>(),{records:()=>[],selectedId:""});
const emit=defineEmits<{select:[record:ResponseFaqRecord]} >();
const i18n=useI18nStore();

function recordKey(record:ResponseFaqRecord,index:number){return String(record.record_id||`${record.question||"response"}-${record.created_at||index}`)}
function dateLabel(value?:string){
  if(!value)return "";
  try{return new Intl.DateTimeFormat(i18n.locale,{dateStyle:"medium"}).format(new Date(value))}
  catch{return value}
}
function gradeValue(record:ResponseFaqRecord){
  const grade=record.grade as Record<string,unknown>|undefined;
  const result=(grade?.result&&typeof grade.result==="object"?grade.result:grade) as Record<string,unknown>|undefined;
  const raw=result?.overall??result?.score;
  return raw==null?"":String(raw);
}
function evidenceCount(record:ResponseFaqRecord){return Number(record.evidence_count??record.evidence?.length??0)}
</script>

<template>
  <nav class="response-library-list" :aria-label="i18n.t('faq.saved_responses','Saved responses')">
    <button
      v-for="(record,index) in records"
      :key="recordKey(record,index)"
      type="button"
      :class="{active:selectedId===recordKey(record,index)}"
      :aria-current="selectedId===recordKey(record,index)?'true':undefined"
      @click="emit('select',record)"
    >
      <span class="response-library-list-question">{{record.question||i18n.t('faq.untitled_question','Untitled question')}}</span>
      <span class="response-library-list-meta">
        <span v-if="record.created_at">{{dateLabel(record.created_at)}}</span>
        <span v-if="record.model">{{record.model}}</span>
        <span><AppIcon name="books"/>{{evidenceCount(record)}}</span>
        <span v-if="gradeValue(record)" class="grade"><AppIcon name="spark"/>{{gradeValue(record)}}/10</span>
      </span>
    </button>
  </nav>
</template>

<style scoped>
.response-library-list{display:grid;gap:3px;padding:1px}.response-library-list>button{width:100%;min-width:0;display:grid;gap:7px;border:1px solid transparent;border-radius:10px;background:transparent;padding:11px 12px;color:#2e4057;text-align:left;cursor:pointer}.response-library-list>button:hover{border-color:#e1e7ec;background:#f8fafb}.response-library-list>button.active{border-color:#cadbd1;background:var(--ui-accent-soft,#edf7f0);box-shadow:inset 3px 0 0 var(--ui-accent,#3c8d62)}.response-library-list-question{font-size:13.5px;font-weight:760;line-height:1.4;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden}.response-library-list-meta{display:flex;align-items:center;gap:6px 9px;flex-wrap:wrap;color:#7a8798;font-size:10.5px}.response-library-list-meta>span{display:inline-flex;align-items:center;gap:4px;min-width:0;max-width:100%}.response-library-list-meta svg{width:11px;height:11px}.response-library-list-meta .grade{color:#3f6650;font-weight:800}.response-library-list>button:focus-visible{outline:3px solid var(--ui-accent-focus);outline-offset:1px}
</style>
