<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResponseFaqRecord } from "../../types/research";

const props=withDefaults(defineProps<{records?:ResponseFaqRecord[];selectedId?:string;search?:string}>(),{records:()=>[],selectedId:"",search:""});
const emit=defineEmits<{select:[record:ResponseFaqRecord]} >();
const i18n=useI18nStore();

type HighlightPart={text:string;match:boolean};
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
function escapeRegex(value:string){return value.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")}
function highlightParts(value:string):HighlightPart[]{
  const text=value||i18n.t('faq.untitled_question','Untitled question');
  const terms=props.search.trim().split(/\s+/).map(term=>term.trim()).filter(term=>term.length>1).slice(0,8);
  if(!terms.length)return [{text,match:false}];
  const matcher=new RegExp(`(${terms.map(escapeRegex).join("|")})`,`gi`);
  return text.split(matcher).filter(Boolean).map(part=>({text:part,match:terms.some(term=>part.localeCompare(term,undefined,{sensitivity:"accent"})===0)}));
}
</script>

<template>
  <nav class="response-library-list" :aria-label="i18n.t('faq.saved_responses','Saved responses')">
    <button
      v-for="(record,index) in records"
      :key="recordKey(record,index)"
      type="button"
      :class="{active:selectedId===recordKey(record,index)}"
      :aria-current="selectedId===recordKey(record,index)?'true':undefined"
      :aria-label="record.question||i18n.t('faq.untitled_question','Untitled question')"
      @click="emit('select',record)"
    >
      <span class="response-library-question-icon" aria-hidden="true">Q</span>
      <span class="response-library-list-main">
        <span class="response-library-list-question">
          <template v-for="(part,partIndex) in highlightParts(record.question||'')" :key="partIndex"><mark v-if="part.match">{{part.text}}</mark><template v-else>{{part.text}}</template></template>
        </span>
        <span class="response-library-list-meta">
          <span v-if="record.created_at">{{dateLabel(record.created_at)}}</span>
          <span v-if="record.model" class="model">{{record.model}}</span>
          <span><AppIcon name="books"/>{{evidenceCount(record)}} {{i18n.t('faq.evidence_short','evidence')}}</span>
          <span v-if="gradeValue(record)" class="grade"><AppIcon name="spark"/>{{gradeValue(record)}}/10</span>
        </span>
      </span>
      <span class="response-library-open" aria-hidden="true">›</span>
    </button>
  </nav>
</template>

<style scoped>
.response-library-list{display:grid;gap:5px;padding:1px}.response-library-list>button{width:100%;min-width:0;display:grid;grid-template-columns:32px minmax(0,1fr) 18px;gap:10px;align-items:start;border:1px solid var(--line);border-radius:11px;background:var(--card);padding:12px 11px;color:var(--text-2);text-align:left;cursor:pointer;box-shadow:0 1px 2px rgba(15,23,42,.02)}.response-library-list>button:hover{border-color:var(--line);background:var(--card)}.response-library-list>button.active{border-color:var(--tone-ok-edge);background:var(--ui-accent-soft,#edf7f0);box-shadow:inset 3px 0 0 var(--ui-accent,#3c8d62)}.response-library-question-icon{width:30px;height:30px;display:grid;place-items:center;margin-top:1px;border-radius:9px;background:var(--soft);color:var(--text-2);font-size:.8125rem;font-weight:850}.response-library-list>button.active .response-library-question-icon{background:var(--card);color: var(--accent-fg)}.response-library-list-main{min-width:0;display:grid;gap:7px}.response-library-list-question{color:var(--text);font-size:0.9375rem;font-weight:790;line-height:1.38;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden}.response-library-list-question mark{border-radius:3px;background:#fff0a8;color:inherit;padding:0 1px}.response-library-list-meta{display:flex;align-items:center;gap:5px 9px;flex-wrap:wrap;color:var(--muted);font-size:.8125rem}.response-library-list-meta>span{display:inline-flex;align-items:center;gap:4px;min-width:0;max-width:100%}.response-library-list-meta .model{max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.response-library-list-meta svg{width:11px;height:11px}.response-library-list-meta .grade{color:var(--tone-ok-fg);font-weight:800}.response-library-open{align-self:center;color:#9aa7b5;font-size:1.375rem;line-height:1}.response-library-list>button:hover .response-library-open,.response-library-list>button.active .response-library-open{color: var(--accent-fg)}.response-library-list>button:focus-visible{outline:3px solid var(--ui-accent-focus);outline-offset:1px}@media(max-width:520px){.response-library-list>button{grid-template-columns:26px minmax(0,1fr) 14px;padding:10px 9px;gap:8px}.response-library-question-icon{width:25px;height:25px;border-radius:7px}.response-library-list-question{font-size:0.875rem}.response-library-list-meta .model{max-width:150px}}
</style>
