<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import CorpusFieldOwnershipBadge from "./CorpusFieldOwnershipBadge.vue";

const props=defineProps<{
  field:string; value:unknown; status?:Record<string,unknown>; options?:string[]; required?:boolean;
  boolean?:boolean; number?:boolean; array?:boolean; busy?:boolean; saving?:boolean; saved?:boolean; open?:boolean;
  constraint?:{value:unknown;reason:string}|null; calibratedAcceptance?:{reviewed:number;acceptanceRate:number}|null;
}>();
const emit=defineEmits<{save:[value:unknown];source:[];dirty:[dirty:boolean]}>();
const i18n=useI18nStore();
const editing=ref(Boolean(props.open));
const draft=ref<unknown>("");
const confidence=computed(()=>typeof props.status?.confidence==='number'&&Number.isFinite(props.status.confidence)?Number(props.status.confidence):null);
const isLlm=computed(()=>String(props.status?.method||'').includes('llm')&&props.value!==undefined&&props.value!==null&&props.value!=="");
function editableValue(){const value=props.constraint?.value ?? props.value;return Array.isArray(value)?value.join(', '):value??''}
watch(()=>[props.field,props.value,props.constraint?.value],()=>{draft.value=editableValue()},{immediate:true});
watch(()=>props.open,value=>{if(value)editing.value=true});
watch(isLlm,value=>{if(value)editing.value=true},{immediate:true});
function normalized(){if(props.array)return String(draft.value||'').split(/[\n,]/).map(v=>v.trim()).filter(Boolean);if(props.number&&draft.value!=="")return Number(draft.value);return draft.value}
function save(){emit('save',normalized());emit('dirty',false);editing.value=true}
function markDirty(){emit('dirty',true)}
function display(value:unknown){if(value===true)return i18n.t('ui.yes','Yes');if(value===false)return i18n.t('ui.no','No');if(Array.isArray(value))return value.join(', ')||'—';return value===null||value===undefined||value===''?'—':String(value)}
const confidenceLabel=computed(()=>confidence.value===null?i18n.t('pdf_corpus.confidence_not_reported','Confidence not reported'):i18n.tf('pdf_corpus.confidence_percent','Confidence: {percent}%',{percent:Math.round(confidence.value*100)}));
</script>

<template>
<article class="metadata-field" :data-attention="status?.status==='unresolved'||status?.status==='invalid'?'true':'false'">
  <div class="field-topline">
    <div class="field-name"><b>{{i18n.t(`record.${field}`,field.replaceAll('_',' '))}}</b><CorpusFieldOwnershipBadge :status="String(status?.status||'')" :method="String(status?.method||'')"/></div>
    <div class="field-actions"><button type="button" class="link-button" @click="emit('source')">{{i18n.t('pdf_corpus.view_evidence','Evidence')}}</button><button type="button" class="btn small" :disabled="busy" @click="editing=!editing;if(!editing)emit('dirty',false)">{{editing?i18n.t('ui.done','Done'):i18n.t('ui.edit','Edit')}}</button></div>
  </div>
  <div v-if="!editing" class="field-current">{{display(value)}}</div>
  <div v-else class="field-editor">
    <p v-if="status?.reason" class="field-reason">{{status.reason}}</p>
    <div v-if="constraint" class="constraint" role="status"><b>{{i18n.t('pdf_corpus.deterministic_suggestion','Deterministic rule')}}</b><span>{{constraint.reason}}</span></div>
    <div class="editor-row">
      <select v-if="options?.length" v-model="draft" class="control" @change="markDirty"><option value="" disabled>{{i18n.t('pdf_corpus.choose_value','Choose a value…')}}</option><option v-for="option in options" :key="option" :value="option">{{i18n.t(`record.enum.${field}.${option}`,option.replaceAll('_',' '))}}</option></select>
      <fieldset v-else-if="boolean" class="boolean-choice"><legend class="sr-only">{{i18n.t(`record.${field}`,field)}}</legend><label><input v-model="draft" type="radio" :name="`${field}-value`" :value="true" @change="markDirty"><span>{{i18n.t('ui.yes','Yes')}}</span></label><label><input v-model="draft" type="radio" :name="`${field}-value`" :value="false" @change="markDirty"><span>{{i18n.t('ui.no','No')}}</span></label></fieldset>
      <input v-else v-model="draft" class="control" :type="number?'number':'text'" :aria-label="i18n.t(`record.${field}`,field)" @input="markDirty">
      <button type="button" class="btn primary" :disabled="busy||draft===''||draft===undefined||(required&&draft===null)" @click="save">{{saving?i18n.t('pdf_corpus.saving_decision','Saving…'):i18n.t('pdf_corpus.save_field_value','Save value')}}</button>
      <button v-if="!required" type="button" class="btn" :disabled="busy" @click="emit('save',null)">{{i18n.t('pdf_corpus.confirm_no_value','No supported value')}}</button>
    </div>
    <div class="field-meta">
      <span v-if="isLlm" class="proposal">{{i18n.t('pdf_corpus.llm_suggestion_prefilled','LLM suggestion prefilled — verify before saving')}}</span>
      <span>{{confidenceLabel}}</span>
      <span v-if="calibratedAcceptance&&calibratedAcceptance.reviewed>=3">{{i18n.tf('pdf_corpus.calibrated_acceptance','Historically accepted {percent}% of the time ({count} reviews)',{percent:Math.round(calibratedAcceptance.acceptanceRate*100),count:calibratedAcceptance.reviewed})}}</span>
      <span v-if="saved" class="saved" role="status">{{i18n.t('pdf_corpus.decision_saved_editable','Saved — you can keep editing this value')}}</span>
    </div>
  </div>
</article>
</template>

<style scoped>
.metadata-field{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:14px;display:grid;gap:10px}.metadata-field[data-attention="true"]{border-inline-start:4px solid var(--warning,#a16207)}.field-topline{display:flex;justify-content:space-between;gap:12px;align-items:center}.field-name{display:flex;gap:8px;align-items:center;flex-wrap:wrap;text-transform:none}.field-current{font-size:.9375rem;line-height:1.5;overflow-wrap:anywhere}.field-actions,.editor-row,.field-meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.field-editor{display:grid;gap:10px;padding-top:10px;border-top:1px solid var(--line)}.field-reason{margin:0;color:var(--muted);font-size:.875rem;line-height:1.5}.constraint{display:grid;gap:2px;padding:9px 10px;border-radius:9px;background:var(--soft);font-size:.875rem}.constraint b{font-size:.8125rem}.control{min-width:min(280px,100%);min-height:42px}.boolean-choice{display:flex;gap:12px;border:0;padding:0;margin:0}.boolean-choice label{display:flex;gap:6px;align-items:center;min-height:40px}.field-meta{font-size:.8125rem;color:var(--muted)}.proposal{font-weight:750;color:var(--text)}.saved{color:var(--success,#166534);font-weight:700}.link-button{border:0;background:none;color:var(--accent);font:inherit;font-weight:700;min-height:36px;cursor:pointer}:is(button,input,select):focus-visible{outline:3px solid var(--accent);outline-offset:2px}@media(max-width:680px){.field-topline{align-items:flex-start;flex-direction:column}.field-actions{width:100%}.editor-row{align-items:stretch;flex-direction:column}.control{width:100%}}
</style>
