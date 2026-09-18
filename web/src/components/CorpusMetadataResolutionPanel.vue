<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import type { CorpusRecord } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";

const props=defineProps<{record:CorpusRecord;regionTypes:string[];discourseRoles:string[];busy?:boolean;savingField?:string;savedField?:string}>();
const emit=defineEmits<{resolve:[field:string,value:unknown];source:[field:string]}>();
const requiredFields=new Set(["region_type","primary_text","discourse_role"]);
const i18n=useI18nStore();
const draft=reactive<Record<string,unknown>>({});
const reviewOrder=["region_type","primary_text","discourse_role","speaker","position_holder","target","stance","proposition_status","claim_scope"];
const unresolved=computed(()=>new Set([...(props.record.metadata_incomplete_fields||[]),...(props.record.metadata_review_fields||[])]));
const fields=computed(()=>reviewOrder.filter(field=>props.record.metadata_field_status?.[field]||props.record[field]!==undefined||unresolved.value.has(field)));
watch(()=>[props.record.record_id,props.record.record_revision,...fields.value],()=>{for(const field of fields.value)draft[field]=props.record[field]??""},{immediate:true});
function options(field:string){if(field==="region_type")return props.regionTypes;if(field==="discourse_role")return props.discourseRoles;return []}
function status(field:string){return props.record.metadata_field_status?.[field]||{}}
function save(field:string){emit("resolve",field,draft[field])}
function confirmAbsent(field:string){emit("resolve",field,null)}
function displayValue(field:string){const value=props.record[field];if(value===true)return i18n.t("ui.yes","Yes");if(value===false)return i18n.t("ui.no","No");if(Array.isArray(value))return value.join(", ")||"—";return value===null||value===undefined||value===""?"—":String(value)}
</script>

<template>
  <section class="metadata-review" aria-labelledby="metadata-review-title">
    <header class="metadata-head">
      <div><h3 id="metadata-review-title">{{i18n.t('pdf_corpus.metadata_tab','Metadata')}}</h3><p>{{i18n.t('pdf_corpus.metadata_inline_help','Metadata is reviewed with the record. Only uncertain fields require an explicit decision.')}}</p></div>
      <span class="review-status" :data-state="unresolved.size?'attention':'ready'">{{unresolved.size?i18n.tf('pdf_corpus.metadata_decisions_count','{count} decision(s)',{count:unresolved.size}):i18n.t('pdf_corpus.metadata_ready','Ready')}}</span>
    </header>

    <div v-if="fields.length" class="metadata-table" role="list">
      <article v-for="field in fields" :key="field" class="metadata-row" :class="{unresolved:unresolved.has(field)}" role="listitem" :data-unresolved-field="unresolved.has(field)?'true':undefined">
        <div class="metadata-summary">
          <div class="field-label"><b>{{i18n.t(`record.${field}`,field.replace(/_/g,' '))}}</b><span class="source-badge">{{i18n.t(`pdf_corpus.metadata_field_status.${status(field).status||'unresolved'}`,String(status(field).status||'unresolved').replace(/_/g,' '))}}</span></div>
          <div class="field-value">{{displayValue(field)}}</div>
          <button type="button" class="evidence-link" @click="emit('source',field)">{{i18n.t('pdf_corpus.view_evidence','Evidence')}}</button>
        </div>

        <div v-if="unresolved.has(field)" class="decision-editor">
          <p v-if="status(field).reason" class="decision-reason">{{status(field).reason}}</p>
          <div class="decision-controls">
            <select v-if="field==='region_type'||field==='discourse_role'" v-model="draft[field]" class="control" :aria-label="i18n.t(`record.${field}`,field)"><option value="" disabled>{{i18n.t('pdf_corpus.choose_value','Choose a value…')}}</option><option v-for="value in options(field)" :key="value" :value="value">{{i18n.t(`record.enum.${field}.${value}`,value.replace(/_/g,' '))}}</option></select>
            <fieldset v-else-if="field==='primary_text'" class="boolean-choice"><legend class="sr-only">{{i18n.t('record.primary_text','Primary text')}}</legend><label><input v-model="draft[field]" type="radio" :name="`primary-text-${record.record_id}`" :value="true"> <span>{{i18n.t('ui.yes','Yes')}}</span></label><label><input v-model="draft[field]" type="radio" :name="`primary-text-${record.record_id}`" :value="false"> <span>{{i18n.t('ui.no','No')}}</span></label></fieldset>
            <input v-else v-model="draft[field]" class="control" :aria-label="i18n.t(`record.${field}`,field)">
            <button type="button" class="btn primary" :disabled="busy||draft[field]===''||draft[field]===undefined||(requiredFields.has(field)&&draft[field]===null)" @click="save(field)">{{savingField===field?i18n.t('pdf_corpus.saving_decision','Saving…'):i18n.t('pdf_corpus.confirm_field_value','Confirm')}}</button>
            <button v-if="!requiredFields.has(field)" type="button" class="btn" :disabled="busy" @click="confirmAbsent(field)">{{i18n.t('pdf_corpus.confirm_no_value','No supported value')}}</button>
          </div>
          <div class="decision-meta"><span v-if="status(field).confidence!==undefined">{{i18n.t('pdf_corpus.confidence','Confidence')}} {{Math.round(Number(status(field).confidence||0)*100)}}%</span><span v-if="savedField===field" class="saved" role="status">{{i18n.t('pdf_corpus.decision_saved','Saved')}}</span></div>
        </div>
      </article>
    </div>
    <div v-else class="resolved" role="status">{{i18n.t('pdf_corpus.metadata_record_resolved','No metadata decisions are required for this record.')}}</div>
  </section>
</template>

<style scoped>
.metadata-review{padding:14px;background:var(--card)}.metadata-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:10px}.metadata-head h3{margin:0 0 3px;font-size:16px}.metadata-head p{margin:0;max-width:58ch;font-size:13px;line-height:1.5;color:var(--muted)}.review-status{flex:none;padding:5px 9px;border-radius:999px;background:#edf8f1;color:#285c39;font-size:12px;font-weight:800}.review-status[data-state="attention"]{background:#fff4d6;color:#6a5100}.metadata-table{border:1px solid var(--line);border-radius:10px;overflow:hidden}.metadata-row{background:var(--card);border-bottom:1px solid var(--line)}.metadata-row:last-child{border-bottom:0}.metadata-row.unresolved{background:#fffaf0}.metadata-summary{display:grid;grid-template-columns:minmax(150px,.8fr) minmax(120px,1fr) auto;gap:12px;align-items:center;padding:10px 12px}.field-label{display:flex;align-items:center;gap:7px;min-width:0}.field-label b{font-size:12px}.source-badge{padding:2px 6px;border-radius:999px;background:var(--soft);font-size:9px;color:var(--muted);white-space:nowrap}.field-value{font-size:12px;overflow-wrap:anywhere}.evidence-link{border:0;background:transparent;color:var(--accent);font-size:11px;text-decoration:underline;cursor:pointer;min-height:32px}.decision-editor{padding:0 12px 12px}.decision-reason{margin:0 0 8px;font-size:13px;line-height:1.5;color:#675116}.decision-controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.control{min-height:38px;min-width:180px;font-size:12px}.boolean-choice{display:flex;gap:14px;margin:0;padding:7px 10px;border:1px solid var(--line);border-radius:8px}.boolean-choice label{display:flex;gap:6px;align-items:center;font-size:12px;font-weight:700}.boolean-choice input{inline-size:18px;block-size:18px}.decision-meta{display:flex;gap:12px;margin-top:7px;font-size:10px;color:var(--muted)}.decision-meta .saved{color:#28653b;font-weight:800}.resolved{padding:12px;border:1px solid #b8d9c5;border-radius:8px;background:#edf8f1;font-size:12px}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}@media(max-width:700px){.metadata-summary{grid-template-columns:1fr}.metadata-head{display:grid}.decision-controls{align-items:stretch}.control{width:100%}}
</style>
