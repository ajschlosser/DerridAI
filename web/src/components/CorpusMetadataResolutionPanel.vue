<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import type { CorpusRecord } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";

const props=defineProps<{record:CorpusRecord;regionTypes:string[];discourseRoles:string[];busy?:boolean}>();
const emit=defineEmits<{resolve:[field:string,value:unknown];source:[field:string]}>();
const requiredFields=new Set(["region_type","primary_text","discourse_role"]);
const i18n=useI18nStore();
const draft=reactive<Record<string,unknown>>({});
const reviewOrder=["region_type","primary_text","discourse_role","speaker","position_holder","target","stance","proposition_status","claim_scope"];
const unresolved=computed(()=>new Set([...(props.record.metadata_incomplete_fields||[]),...(props.record.metadata_review_fields||[])]));
const fields=computed(()=>reviewOrder.filter(field=>props.record.metadata_field_status?.[field]||props.record[field]!==undefined));
watch(()=>[props.record.record_id,...fields.value],()=>{for(const field of fields.value)draft[field]=props.record[field]??""},{immediate:true});
function options(field:string){if(field==="region_type")return props.regionTypes;if(field==="discourse_role")return props.discourseRoles;return []}
function status(field:string){return props.record.metadata_field_status?.[field]||{}}
function save(field:string){emit("resolve",field,draft[field])}
function confirmAbsent(field:string){emit("resolve",field,null)}
</script>

<template>
  <section class="resolution-panel" aria-labelledby="metadata-resolution-record-title">
    <header>
      <div><span class="eyebrow">{{i18n.t('pdf_corpus.record_metadata_review','Record metadata review')}}</span><h3 id="metadata-resolution-record-title">{{record.record_id}}</h3><p>{{i18n.t('pdf_corpus.metadata_record_review_help','Review the LLM-proposed record metadata together with the text. Uncertain fields must be resolved before the record can be accepted; accepting the record confirms the remaining proposals.')}}</p></div>
      <strong>{{unresolved.size}} {{i18n.t('pdf_corpus.fields_to_resolve','fields to resolve')}}</strong>
    </header>
    <div v-if="fields.length" class="field-list">
      <article v-for="field in fields" :key="field" class="field-card" :data-unresolved-field="unresolved.has(field)?'true':undefined">
        <div class="field-head"><div><span class="field-name">{{i18n.t(`record.${field}`,field.replace(/_/g,' '))}}</span><span class="status">{{i18n.t(`pdf_corpus.metadata_field_status.${status(field).status||'unresolved'}`,String(status(field).status||'unresolved').replace(/_/g,' '))}}</span></div><button type="button" class="link-button" @click="emit('source',field)">{{i18n.t('pdf_corpus.view_source_evidence','View source evidence')}}</button></div>
        <p v-if="status(field).reason" class="reason">{{status(field).reason}}</p>
        <div class="provenance"><span>{{i18n.t('pdf_corpus.method','Method')}}: <b>{{status(field).method||'—'}}</b></span><span v-if="status(field).confidence!==undefined">{{i18n.t('pdf_corpus.confidence','Confidence')}}: <b>{{Math.round(Number(status(field).confidence||0)*100)}}%</b></span></div>
        <div v-if="unresolved.has(field)" class="editor">
          <select v-if="field==='region_type'||field==='discourse_role'" v-model="draft[field]" class="control" :aria-label="i18n.t(`record.${field}`,field)"><option value="" disabled>{{i18n.t('pdf_corpus.choose_value','Choose a value…')}}</option><option v-for="value in options(field)" :key="value" :value="value">{{i18n.t(`record.enum.${field}.${value}`,value.replace(/_/g,' '))}}</option></select>
          <fieldset v-else-if="field==='primary_text'" class="tri-state" :aria-describedby="`primary-text-help-${record.record_id}`"><legend class="sr-only">{{i18n.t('record.primary_text','Primary text')}}</legend><label><input v-model="draft[field]" type="radio" :name="`primary-text-${record.record_id}`" :value="true" @change="save(field)"> <span>{{i18n.t('ui.yes','Yes')}}</span></label><label><input v-model="draft[field]" type="radio" :name="`primary-text-${record.record_id}`" :value="false" @change="save(field)"> <span>{{i18n.t('ui.no','No')}}</span></label><span :id="`primary-text-help-${record.record_id}`" class="tri-state-help">{{i18n.t('pdf_corpus.primary_text_help','Choose whether this record belongs to the substantive work rather than front/back matter or publishing apparatus.')}}</span></fieldset>
          <input v-else v-model="draft[field]" class="control" :aria-label="i18n.t(`record.${field}`,field)">
          <div class="editor-actions"><button v-if="field!=='primary_text'" type="button" class="btn primary" :disabled="busy||draft[field]===''||draft[field]===null||draft[field]===undefined" @click="save(field)">{{i18n.t('pdf_corpus.confirm_field_value','Confirm value')}}</button><button v-if="!requiredFields.has(field)" type="button" class="btn" :disabled="busy" @click="confirmAbsent(field)">{{i18n.t('pdf_corpus.confirm_no_value','Confirm no supported value')}}</button></div>
        </div>
        <div v-else class="proposal-ok"><b>{{record[field]===null||record[field]===undefined||record[field]===''?i18n.t('pdf_corpus.not_identified','Not identified'):String(record[field])}}</b><span>{{i18n.t('pdf_corpus.confirmed_on_accept','This proposal will be human-confirmed when you accept the record.')}}</span></div>
      </article>
    </div>
    <div v-else class="resolved" role="status">{{i18n.t('pdf_corpus.metadata_record_resolved','All required metadata fields for this record are resolved.')}}</div>
  </section>
</template>

<style scoped>
.resolution-panel{display:grid;gap:12px;padding:14px;border-top:1px solid var(--line);background:var(--soft)}header{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}header h3{margin:2px 0 3px;font-size:13px}header p{margin:0;max-width:72ch;font-size:9px;color:var(--muted);line-height:1.45}header>strong{font-size:10px;white-space:nowrap}.eyebrow{font-size:8px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:800}.field-list{display:grid;gap:9px}.field-card{display:grid;gap:8px;padding:11px;border:1px solid var(--line);border-radius:9px;background:var(--card)}.field-head{display:flex;justify-content:space-between;gap:12px}.field-head>div{display:flex;gap:7px;align-items:center}.field-name{font-size:11px;font-weight:800}.status{padding:2px 6px;border-radius:999px;background:#fff5d8;font-size:8px;color:#684f00}.link-button{border:0;background:transparent;color:var(--accent);font-size:9px;text-decoration:underline;cursor:pointer}.reason{margin:0;font-size:9px;line-height:1.45;color:var(--muted)}.provenance{display:flex;gap:12px;flex-wrap:wrap;font-size:8px;color:var(--muted)}.editor{display:grid;grid-template-columns:minmax(180px,1fr) auto;gap:8px}.editor-actions{display:flex;gap:6px;flex-wrap:wrap}.control{min-height:34px}.tri-state{margin:0;padding:8px 10px;border:1px solid var(--line);border-radius:8px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}.tri-state label{display:flex;align-items:center;gap:5px;font-size:10px;font-weight:700;cursor:pointer}.tri-state input{inline-size:18px;block-size:18px}.tri-state-help{flex-basis:100%;font-size:8px;color:var(--muted);line-height:1.45}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.proposal-ok{display:grid;gap:3px;padding:9px 10px;border-radius:8px;background:var(--soft);font-size:9px}.proposal-ok span{color:var(--muted)}.resolved{padding:12px;border:1px solid #b8d9c5;border-radius:8px;background:#edf8f1;font-size:10px}@media(max-width:640px){header{display:grid}.editor{grid-template-columns:1fr}.field-head{display:grid}}
</style>
