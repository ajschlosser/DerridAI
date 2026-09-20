<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import CorpusFieldOwnershipBadge from "./CorpusFieldOwnershipBadge.vue";
import UiCombobox from "./ui/UiCombobox.vue";
import { normalizeMetadataFieldValue } from "../domain/metadataFieldRegistry";

const props=defineProps<{
  field:string; value:unknown; status?:Record<string,unknown>; options?:string[]; required?:boolean;
  control?:"enum"|"combobox"|"multi-combobox"|"boolean"|"number"|"text"; allowCustom?:boolean; busy?:boolean; saving?:boolean; saved?:boolean; open?:boolean;
  constraint?:{value:unknown;reason:string}|null; calibratedAcceptance?:{reviewed:number;acceptanceRate:number}|null;
}>();
const emit=defineEmits<{save:[value:unknown];noValue:[];source:[];dirty:[dirty:boolean]}>();
const i18n=useI18nStore();
const editing=ref(Boolean(props.open));
const draft=ref<unknown>("");
const confidence=computed(()=>typeof props.status?.confidence==='number'&&Number.isFinite(props.status.confidence)?Number(props.status.confidence):null);
const isLlm=computed(()=>String(props.status?.method||'').includes('llm'));
const isMultiCombobox=computed(()=>props.control==='multi-combobox');
const hasValue=(value:unknown)=>!(value===undefined||value===null||value===''||(Array.isArray(value)&&!value.length));
const resolvedValue=computed(()=>{
  const status=props.status||{};
  if(status.reason_code==='deterministic_llm_disagreement'&&status.prefilled_candidate==='llm'&&hasValue(status.llm_value))return normalizeMetadataFieldValue(props.field,status.llm_value);
  if(hasValue(props.value))return normalizeMetadataFieldValue(props.field,props.value);
  if(confidence.value!==null&&confidence.value>0.65&&hasValue(status.proposed_value))return normalizeMetadataFieldValue(props.field,status.proposed_value);
  if(hasValue(props.constraint?.value))return normalizeMetadataFieldValue(props.field,props.constraint?.value);
  return normalizeMetadataFieldValue(props.field,props.value??'');
});
function editableValue(){const value=resolvedValue.value;return Array.isArray(value)?value.join(', '):value??''}
watch(()=>[props.field,props.value,props.status?.proposed_value,props.status?.llm_value,props.status?.prefilled_candidate,props.constraint?.value],()=>{draft.value=editableValue()},{immediate:true,deep:true});
watch(()=>props.open,value=>{if(value)editing.value=true});

function normalized(){
  if(props.control==='multi-combobox')return [...new Set(String(draft.value||'').split(/[\n,]/).map(v=>v.trim()).filter(Boolean))];
  if(props.control==='number'&&draft.value!=="")return Number(draft.value);
  return normalizeMetadataFieldValue(props.field,draft.value);
}
function save(){emit('save',normalized());emit('dirty',false);editing.value=true}
function markDirty(){emit('dirty',true)}
function selectFromText(){
  const selected=String(window.getSelection()?.toString()||'').trim();
  if(!selected)return;
  if(props.control==='multi-combobox'){
    const current=String(draft.value||'').split(/[,\n]/).map(v=>v.trim()).filter(Boolean);
    if(!current.includes(selected))current.push(selected);
    draft.value=current.join(', ');
  }else{draft.value=selected}
  editing.value=true;markDirty();
}
function display(value:unknown){if(value===true)return i18n.t('ui.yes','Yes');if(value===false)return i18n.t('ui.no','No');if(Array.isArray(value))return value.join(', ')||'—';return value===null||value===undefined||value===''?'—':String(value)}
const confidenceLabel=computed(()=>confidence.value===null?i18n.t('pdf_corpus.confidence_not_reported','Confidence not reported'):i18n.tf('pdf_corpus.confidence_percent','Confidence: {percent}%',{percent:Math.round(confidence.value*100)}));
</script>

<template>
<article class="metadata-field" :data-attention="status?.status==='unresolved'||status?.status==='invalid'?'true':'false'">
  <div class="field-topline">
    <div class="field-name"><b>{{i18n.t(`record.${field}`,field.replaceAll('_',' '))}}</b><CorpusFieldOwnershipBadge :status="String(status?.status||'')" :method="String(status?.method||'')"/></div>
    <div class="field-actions"><button type="button" class="link-button" @click="emit('source')">{{i18n.t('pdf_corpus.view_evidence','Evidence')}}</button><button type="button" class="btn small" :disabled="busy" @click="editing=!editing;if(!editing)emit('dirty',false)">{{editing?i18n.t('ui.done','Done'):i18n.t('ui.edit','Edit')}}</button></div>
  </div>
  <div v-if="!editing" class="field-current">{{display(resolvedValue)}}</div>
  <div v-else class="field-editor">
    <div v-if="status?.reason_code==='deterministic_llm_disagreement'" class="disagreement" role="status"><b>{{i18n.t('pdf_corpus.metadata_disagreement','Deterministic and LLM suggestions disagree')}}</b><span>{{i18n.tf('pdf_corpus.deterministic_value','Deterministic: {value}',{value:String(status?.deterministic_value??'—')})}}</span><span>{{i18n.tf('pdf_corpus.llm_value','LLM: {value}',{value:String(status?.llm_value??value??'—')})}}<template v-if="typeof status?.llm_confidence==='number'"> · {{Math.round(Number(status.llm_confidence)*100)}}%</template></span><small v-if="status?.deterministic_reason">{{status.deterministic_reason}}</small><small v-if="status?.llm_reason">{{status.llm_reason}}</small></div><p v-else-if="status?.reason" class="field-reason">{{status.reason}}</p>
    <div v-if="constraint" class="constraint" role="status"><b>{{i18n.t('pdf_corpus.deterministic_suggestion','Deterministic rule')}}</b><span>{{constraint.reason}}</span></div>
    <div class="value-control">
      <select v-if="control==='enum'" v-model="draft" class="control" :aria-label="i18n.t(`record.${field}`,field.replaceAll('_',' '))" @change="markDirty"><option value="" disabled>{{i18n.t('pdf_corpus.choose_value','Choose a value…')}}</option><option v-for="option in options||[]" :key="option" :value="option">{{i18n.t(`record.enum.${field}.${option}`,option.replaceAll('_',' '))}}</option></select>
      <fieldset v-else-if="control==='boolean'" class="boolean-choice"><legend class="sr-only">{{i18n.t(`record.${field}`,field)}}</legend><label><input v-model="draft" type="radio" :name="`${field}-value`" :value="true" @change="markDirty"><span>{{i18n.t('ui.yes','Yes')}}</span></label><label><input v-model="draft" type="radio" :name="`${field}-value`" :value="false" @change="markDirty"><span>{{i18n.t('ui.no','No')}}</span></label></fieldset>
      <UiCombobox v-else-if="control==='combobox'" :model-value="String(draft??'')" :options="options||[]" :label="i18n.t(`record.${field}`,field)" @update:model-value="value=>{draft=value;markDirty()}"/>
      <UiCombobox v-else-if="isMultiCombobox" :model-value="String(draft??'')" :options="options||[]" :label="i18n.t(`record.${field}`,field)" :multiple="true" @update:model-value="value=>{draft=value;markDirty()}"/>
      <input v-else v-model="draft" class="control" :type="control==='number'?'number':'text'" :list="isMultiCombobox&&options?.length?`${field}-suggestions`:undefined" :aria-label="i18n.t(`record.${field}`,field)" @input="markDirty"><datalist v-if="isMultiCombobox&&options?.length" :id="`${field}-suggestions`"><option v-for="option in [...new Set((options||[]).map(v=>String(v).trim()).filter(Boolean))]" :key="option" :value="option"/></datalist>
    </div>
    <div class="editor-actions">
      <button type="button" class="btn primary" :disabled="busy||draft===''||draft===undefined||(required&&draft===null)" @click="save">{{saving?i18n.t('pdf_corpus.saving_decision','Saving…'):i18n.t('pdf_corpus.save_field_value','Save value')}}</button>
      <button type="button" class="btn" :disabled="busy" @click="emit('noValue')">{{i18n.t('pdf_corpus.confirm_no_value','No supported value')}}</button>
      <button v-if="control==='combobox'||control==='multi-combobox'||control==='text'" type="button" class="btn subtle" :disabled="busy" @click="selectFromText">{{i18n.t('pdf_corpus.select_from_text','Select from text')}}</button>
    </div>
    <p v-if="control==='combobox'||control==='multi-combobox'||control==='text'" class="selection-help">{{i18n.t('pdf_corpus.select_from_text_help','Highlight text in the record, then choose Select from text. String fields are replaced; list fields append the selection.')}}</p>
    <div class="field-meta">
      <span v-if="isLlm&&hasValue(resolvedValue)" class="proposal">{{status?.auto_populated?i18n.t('pdf_corpus.llm_suggestion_autofilled','LLM value auto-filled from a >65% confidence suggestion'):i18n.t('pdf_corpus.llm_suggestion_prefilled','LLM suggestion prefilled — verify before saving')}}</span>
      <span v-if="status?.llm_checked===true">{{i18n.t('pdf_corpus.llm_field_checked','LLM checked this field')}}</span>
      <span v-else-if="status?.llm_checked===false&&status?.llm_skip_reason">{{i18n.tf('pdf_corpus.llm_field_not_checked','LLM not checked: {reason}',{reason:String(status?.llm_skip_reason)})}}</span>
      <span v-if="status?.raw_llm_value&&status?.raw_llm_value!==resolvedValue">{{i18n.tf('pdf_corpus.llm_value_normalized','LLM returned “{raw}”; normalized to “{value}”.',{raw:String(status?.raw_llm_value),value:String(resolvedValue)})}}</span>
      <span>{{confidenceLabel}}</span>
      <span v-if="calibratedAcceptance&&calibratedAcceptance.reviewed>=3">{{i18n.tf('pdf_corpus.calibrated_acceptance','Historically accepted {percent}% of the time ({count} reviews)',{percent:Math.round(calibratedAcceptance.acceptanceRate*100),count:calibratedAcceptance.reviewed})}}</span>
      <span v-if="saved" class="saved" role="status">{{i18n.t('pdf_corpus.decision_saved_editable','Saved — you can keep editing this value')}}</span>
    </div>
  </div>
</article>
</template>

<style scoped>
.metadata-field{min-width:0;border:1px solid var(--line);border-radius:12px;background:var(--card);padding:14px;display:grid;gap:10px}.metadata-field[data-attention="true"]{border-inline-start:4px solid var(--warning,#a16207)}.field-topline{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.field-name{min-width:0;display:flex;gap:8px;align-items:center;flex-wrap:wrap}.field-actions,.field-meta,.editor-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.field-current{font-size:.9375rem;line-height:1.5;overflow-wrap:anywhere}.field-editor{min-width:0;display:grid;gap:10px;padding-top:10px;border-top:1px solid var(--line)}.value-control{min-width:0;display:grid;grid-template-columns:minmax(0,1fr)}.value-control>*{min-width:0;max-width:100%}.editor-actions{align-items:stretch}.editor-actions .btn{min-height:40px}.editor-actions .subtle{order:3}.selection-help{margin:0;color:var(--muted);font-size:.8125rem;line-height:1.4}.field-reason{margin:0;color:var(--muted);font-size:.875rem;line-height:1.5}.disagreement{display:grid;gap:3px;padding:10px;border:1px solid var(--warning,#a16207);border-radius:9px;background:var(--soft);font-size:.875rem}.disagreement small{color:var(--muted);line-height:1.4}.constraint{display:grid;gap:2px;padding:9px 10px;border-radius:9px;background:var(--soft);font-size:.875rem}.constraint b{font-size:.8125rem}.control{width:100%;min-width:0;min-height:42px}.boolean-choice{display:flex;gap:16px;flex-wrap:wrap;border:0;padding:0;margin:0}.boolean-choice label{display:flex;gap:6px;align-items:center;min-height:40px}.field-meta{font-size:.8125rem;color:var(--muted)}.proposal{font-weight:750;color:var(--text)}.saved{color:var(--success,#166534);font-weight:700}.link-button{border:0;background:none;color: var(--accent-fg);font:inherit;font-weight:700;min-height:36px;cursor:pointer}:is(button,input,select):focus-visible{outline:3px solid var(--accent);outline-offset:2px}@media(max-width:520px){.field-topline{flex-direction:column}.field-actions,.editor-actions{width:100%}.editor-actions .btn{flex:1 1 100%}}
</style>
