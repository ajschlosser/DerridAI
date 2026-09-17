<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import type { CorpusRecord } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";

const props=defineProps<{record:CorpusRecord;regionTypes:string[];discourseRoles:string[];busy?:boolean}>();
const emit=defineEmits<{resolve:[field:string,value:unknown];source:[field:string]}>();
const i18n=useI18nStore();
const draft=reactive<Record<string,unknown>>({});
const fields=computed(()=>props.record.metadata_incomplete_fields||[]);
watch(()=>[props.record.record_id,...fields.value],()=>{for(const field of fields.value)draft[field]=props.record[field]??""},{immediate:true});
function options(field:string){if(field==="region_type")return props.regionTypes;if(field==="discourse_role")return props.discourseRoles;return []}
function status(field:string){return props.record.metadata_field_status?.[field]||{}}
function save(field:string){let value=draft[field];if(field==="primary_text")value=value==="true"||value===true;emit("resolve",field,value)}
</script>

<template>
  <section class="resolution-panel" aria-labelledby="metadata-resolution-record-title">
    <header>
      <div><span class="eyebrow">{{i18n.t('pdf_corpus.metadata_issue_queue','Metadata issue queue')}}</span><h3 id="metadata-resolution-record-title">{{record.record_id}}</h3><p>{{i18n.t('pdf_corpus.metadata_record_help','Resolve only the required fields shown below. Structural acceptance of this record is tracked separately.')}}</p></div>
      <strong>{{fields.length}} {{i18n.t('pdf_corpus.fields_to_resolve','fields to resolve')}}</strong>
    </header>
    <div v-if="fields.length" class="field-list">
      <article v-for="field in fields" :key="field" class="field-card">
        <div class="field-head"><div><span class="field-name">{{i18n.t(`record.${field}`,field.replace(/_/g,' '))}}</span><span class="status">{{i18n.t(`pdf_corpus.metadata_field_status.${status(field).status||'unresolved'}`,String(status(field).status||'unresolved').replace(/_/g,' '))}}</span></div><button type="button" class="link-button" @click="emit('source',field)">{{i18n.t('pdf_corpus.view_source_evidence','View source evidence')}}</button></div>
        <p v-if="status(field).reason" class="reason">{{status(field).reason}}</p>
        <div class="provenance"><span>{{i18n.t('pdf_corpus.method','Method')}}: <b>{{status(field).method||'—'}}</b></span><span v-if="status(field).confidence!==undefined">{{i18n.t('pdf_corpus.confidence','Confidence')}}: <b>{{Math.round(Number(status(field).confidence||0)*100)}}%</b></span></div>
        <div class="editor">
          <select v-if="field==='region_type'||field==='discourse_role'" v-model="draft[field]" class="control" :aria-label="i18n.t(`record.${field}`,field)"><option value="" disabled>{{i18n.t('pdf_corpus.choose_value','Choose a value…')}}</option><option v-for="value in options(field)" :key="value" :value="value">{{i18n.t(`record.enum.${field}.${value}`,value.replace(/_/g,' '))}}</option></select>
          <select v-else-if="field==='primary_text'" v-model="draft[field]" class="control" :aria-label="i18n.t('record.primary_text','Primary text')"><option value="" disabled>{{i18n.t('pdf_corpus.choose_value','Choose a value…')}}</option><option value="true">{{i18n.t('ui.yes','Yes')}}</option><option value="false">{{i18n.t('ui.no','No')}}</option></select>
          <input v-else v-model="draft[field]" class="control" :aria-label="i18n.t(`record.${field}`,field)">
          <button type="button" class="btn primary" :disabled="busy||draft[field]===''" @click="save(field)">{{i18n.t('pdf_corpus.confirm_field_value','Confirm value')}}</button>
        </div>
      </article>
    </div>
    <div v-else class="resolved" role="status">{{i18n.t('pdf_corpus.metadata_record_resolved','All required metadata fields for this record are resolved.')}}</div>
  </section>
</template>

<style scoped>
.resolution-panel{display:grid;gap:12px;padding:14px;border-top:1px solid var(--line);background:var(--soft)}header{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}header h3{margin:2px 0 3px;font-size:13px}header p{margin:0;max-width:72ch;font-size:9px;color:var(--muted);line-height:1.45}header>strong{font-size:10px;white-space:nowrap}.eyebrow{font-size:8px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:800}.field-list{display:grid;gap:9px}.field-card{display:grid;gap:8px;padding:11px;border:1px solid var(--line);border-radius:9px;background:var(--card)}.field-head{display:flex;justify-content:space-between;gap:12px}.field-head>div{display:flex;gap:7px;align-items:center}.field-name{font-size:11px;font-weight:800}.status{padding:2px 6px;border-radius:999px;background:#fff5d8;font-size:8px;color:#684f00}.link-button{border:0;background:transparent;color:var(--accent);font-size:9px;text-decoration:underline;cursor:pointer}.reason{margin:0;font-size:9px;line-height:1.45;color:var(--muted)}.provenance{display:flex;gap:12px;flex-wrap:wrap;font-size:8px;color:var(--muted)}.editor{display:grid;grid-template-columns:minmax(180px,1fr) auto;gap:8px}.control{min-height:34px}.resolved{padding:12px;border:1px solid #b8d9c5;border-radius:8px;background:#edf8f1;font-size:10px}@media(max-width:640px){header{display:grid}.editor{grid-template-columns:1fr}.field-head{display:grid}}
</style>
