<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import type { CorpusRecord } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";
import CorpusFieldOwnershipBadge from "./CorpusFieldOwnershipBadge.vue";

const props=defineProps<{record:CorpusRecord;regionTypes:string[];discourseRoles:string[];busy?:boolean;savingField?:string;savedField?:string}>();
const emit=defineEmits<{resolve:[field:string,value:unknown];source:[field:string]}>();
const requiredFields=new Set(["region_type","primary_text","discourse_role"]);
const booleanFields=new Set(["primary_text","document_is_translation","is_direct_quote"]);
const numberFields=new Set(["year","publication_year"]);
const arrayFields=new Set(["document_language","original_language","semantic_function","quoted_speaker","quoted_author","quoted_work","quoted_position_holder","quoted_addressee","quoted_referent","quotation_chain","topics","concepts","persons","works_referenced"]);
const i18n=useI18nStore();
const draft=reactive<Record<string,unknown>>({});
const editing=ref("");
const inheritedFieldSet=new Set(["work","document_title","short_title","original_title","document_author","translator","edition","publication_year","publisher","publication_place","isbn","document_language","original_language","document_is_translation"]);
const fieldOrder=[
  "region_type","primary_text","discourse_role","region_author","speaker","position_holder","target","stance","proposition_status","claim_scope","semantic_function","is_direct_quote",
  "quoted_speaker","quoted_author","quoted_work","quoted_position_holder","quoted_addressee","quoted_referent","quotation_chain","topics","concepts","persons","works_referenced",
  "work","document_title","short_title","original_title","document_author","translator","edition","publication_year","publisher","publication_place","isbn","document_language","original_language","document_is_translation"
];
const unresolved=computed(()=>new Set([...(props.record.metadata_incomplete_fields||[]),...(props.record.metadata_review_fields||[])]));
const fields=computed(()=>fieldOrder.filter(field=>props.record.metadata_field_status?.[field]||props.record[field]!==undefined||unresolved.value.has(field)));
const activeFields=computed(()=>fields.value.filter(field=>!inheritedFieldSet.has(field)));
const inheritedFields=computed(()=>fields.value.filter(field=>inheritedFieldSet.has(field)));
watch(()=>[props.record.record_id,props.record.record_revision,...fields.value],()=>{for(const field of fields.value)draft[field]=Array.isArray(props.record[field])?(props.record[field] as unknown[]).join(", "):props.record[field]??"";editing.value=""},{immediate:true});
function options(field:string){if(field==="region_type")return props.regionTypes;if(field==="discourse_role")return props.discourseRoles;return []}
function status(field:string){return props.record.metadata_field_status?.[field]||{}}
function normalized(field:string){const raw=draft[field];if(arrayFields.has(field))return String(raw||"").split(",").map(v=>v.trim()).filter(Boolean);if(numberFields.has(field)&&raw!=="")return Number(raw);return raw}
function save(field:string){emit("resolve",field,normalized(field));editing.value=""}
function confirmAbsent(field:string){emit("resolve",field,null);editing.value=""}
function displayValue(field:string){const value=props.record[field];if(value===true)return i18n.t("ui.yes","Yes");if(value===false)return i18n.t("ui.no","No");if(Array.isArray(value))return value.join(", ")||"—";return value===null||value===undefined||value===""?"—":String(value)}
function isEditing(field:string){return unresolved.value.has(field)||editing.value===field}
</script>

<template>
  <section class="metadata-review" aria-labelledby="metadata-review-title">
    <header class="metadata-head">
      <div><h3 id="metadata-review-title">{{i18n.t('pdf_corpus.metadata_tab','Metadata')}}</h3><p>{{i18n.t('pdf_corpus.metadata_inline_help_v46','Record metadata is always inspectable. Inherited document metadata can be deliberately overridden for this record; human decisions outrank later automatic enrichment.')}}</p></div>
      <span class="review-status" :data-state="unresolved.size?'attention':'ready'">{{unresolved.size?i18n.tf('pdf_corpus.metadata_decisions_count','{count} decision(s)',{count:unresolved.size}):i18n.t('pdf_corpus.metadata_ready','Ready')}}</span>
    </header>

    <div v-if="activeFields.length" class="metadata-table" role="list">
      <article v-for="field in activeFields" :key="field" class="metadata-row" :class="{unresolved:unresolved.has(field)}" role="listitem" :data-unresolved-field="unresolved.has(field)?'true':undefined">
        <div class="metadata-summary">
          <div class="field-label"><b>{{i18n.t(`record.${field}`,field.replace(/_/g,' '))}}</b><CorpusFieldOwnershipBadge :status="String(status(field).status||'')" :method="String(status(field).method||'')" /></div>
          <div class="field-value">{{displayValue(field)}}</div>
          <div class="field-actions"><button type="button" class="evidence-link" @click="emit('source',field)">{{i18n.t('pdf_corpus.view_evidence','Evidence')}}</button><button type="button" class="btn small" :disabled="busy" @click="editing=editing===field?'':field">{{isEditing(field)?i18n.t('ui.cancel','Cancel'):i18n.t('ui.edit','Edit')}}</button></div>
        </div>

        <div v-if="isEditing(field)" class="decision-editor">
          <p v-if="status(field).reason" class="decision-reason">{{status(field).reason}}</p>
          <div class="decision-controls">
            <select v-if="field==='region_type'||field==='discourse_role'" v-model="draft[field]" class="control" :aria-label="i18n.t(`record.${field}`,field)"><option value="" disabled>{{i18n.t('pdf_corpus.choose_value','Choose a value…')}}</option><option v-for="value in options(field)" :key="value" :value="value">{{i18n.t(`record.enum.${field}.${value}`,value.replace(/_/g,' '))}}</option></select>
            <fieldset v-else-if="booleanFields.has(field)" class="boolean-choice"><legend class="sr-only">{{i18n.t(`record.${field}`,field)}}</legend><label><input v-model="draft[field]" type="radio" :name="`${field}-${record.record_id}`" :value="true"> <span>{{i18n.t('ui.yes','Yes')}}</span></label><label><input v-model="draft[field]" type="radio" :name="`${field}-${record.record_id}`" :value="false"> <span>{{i18n.t('ui.no','No')}}</span></label></fieldset>
            <input v-else v-model="draft[field]" class="control" :type="numberFields.has(field)?'number':'text'" :aria-label="i18n.t(`record.${field}`,field)">
            <button type="button" class="btn primary" :disabled="busy||draft[field]===''||draft[field]===undefined||(requiredFields.has(field)&&draft[field]===null)" @click="save(field)">{{savingField===field?i18n.t('pdf_corpus.saving_decision','Saving…'):i18n.t('pdf_corpus.save_field_value','Save value')}}</button>
            <button v-if="!requiredFields.has(field)" type="button" class="btn" :disabled="busy" @click="confirmAbsent(field)">{{i18n.t('pdf_corpus.confirm_no_value','No supported value')}}</button>
          </div>
          <div class="decision-meta"><span v-if="status(field).confidence!==undefined">{{i18n.t('pdf_corpus.confidence','Confidence')}} {{Math.round(Number(status(field).confidence||0)*100)}}%</span><span v-if="savedField===field" class="saved" role="status">{{i18n.t('pdf_corpus.decision_saved','Saved')}}</span></div>
        </div>
      </article>
    </div>
    <details v-if="inheritedFields.length" class="inherited-metadata">
      <summary>{{i18n.t('pdf_corpus.inherited_metadata_section','Inherited document metadata')}} <span>{{inheritedFields.length}}</span></summary>
      <p>{{i18n.t('pdf_corpus.inherited_metadata_help','These values come from the document manifest. Edit the document metadata below to change the default for inheriting records, or deliberately override a field for this record.')}}</p>
      <div class="metadata-table" role="list">
        <article v-for="field in inheritedFields" :key="field" class="metadata-row" role="listitem">
          <div class="metadata-summary"><div class="field-label"><b>{{i18n.t(`record.${field}`,field.replace(/_/g,' '))}}</b><CorpusFieldOwnershipBadge :status="String(status(field).status||'inherited')" :method="String(status(field).method||'manifest')" /></div><div class="field-value">{{displayValue(field)}}</div><div class="field-actions"><button type="button" class="btn small" :disabled="busy" @click="editing=editing===field?'':field">{{isEditing(field)?i18n.t('ui.cancel','Cancel'):i18n.t('pdf_corpus.override_value','Override')}}</button></div></div>
          <div v-if="isEditing(field)" class="decision-editor"><div class="decision-controls"><input v-model="draft[field]" class="control" :type="numberFields.has(field)?'number':'text'" :aria-label="i18n.t(`record.${field}`,field)"><button type="button" class="btn primary" :disabled="busy" @click="save(field)">{{i18n.t('pdf_corpus.save_field_value','Save value')}}</button></div></div>
        </article>
      </div>
    </details>
    <div v-if="!fields.length" class="resolved" role="status">{{i18n.t('pdf_corpus.metadata_record_resolved','No record metadata is available yet.')}}</div>
  </section>
</template>

<style scoped>
.metadata-review{padding:14px;background:var(--card)}.metadata-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:10px}.metadata-head h3{margin:0 0 3px;font-size:16px}.metadata-head p{margin:0;max-width:72ch;font-size:13px;line-height:1.5;color:var(--muted)}.review-status{flex:none;padding:5px 9px;border-radius:999px;background:#edf8f1;color:#285c39;font-size:.8125rem;font-weight:800}.review-status[data-state="attention"]{background:#fff4d6;color:#6a5100}.metadata-table{border:1px solid var(--line);border-radius:10px;overflow:hidden}.metadata-row{background:var(--card);border-bottom:1px solid var(--line)}.metadata-row:last-child{border-bottom:0}.metadata-row.unresolved{background:#fffaf0}.metadata-summary{display:grid;grid-template-columns:minmax(210px,.9fr) minmax(120px,1fr) auto;gap:12px;align-items:center;padding:10px 12px}.field-label{display:flex;align-items:center;gap:7px;min-width:0;flex-wrap:wrap}.field-label b{font-size:13px}.field-value{font-size:13px;overflow-wrap:anywhere}.field-actions{display:flex;gap:7px;align-items:center}.evidence-link{border:0;background:transparent;color:var(--accent);font-size:.8125rem;text-decoration:underline;cursor:pointer;min-height:36px}.decision-editor{padding:0 12px 12px}.decision-reason{margin:0 0 8px;font-size:13px;line-height:1.5;color:#675116}.decision-controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.control{min-height:40px;min-width:200px;font-size:14px}.boolean-choice{display:flex;gap:14px;margin:0;padding:7px 10px;border:1px solid var(--line);border-radius:8px}.boolean-choice label{display:flex;gap:6px;align-items:center;font-size:13px;font-weight:700}.boolean-choice input{inline-size:18px;block-size:18px}.decision-meta{display:flex;gap:12px;margin-top:7px;font-size:.8125rem;color:var(--muted)}.decision-meta .saved{color:#28653b;font-weight:800}.inherited-metadata{margin-top:14px;border-top:1px solid var(--line);padding-top:12px}.inherited-metadata>summary{cursor:pointer;font-size:.875rem;font-weight:750}.inherited-metadata>summary span{margin-inline-start:6px;color:var(--muted)}.inherited-metadata>p{font-size:.8125rem;line-height:1.5;color:var(--muted)}.resolved{padding:12px;border:1px solid #b8d9c5;border-radius:8px;background:#edf8f1;font-size:13px}.small{min-height:36px}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}@media(max-width:760px){.metadata-summary{grid-template-columns:1fr}.metadata-head{display:grid}.decision-controls{align-items:stretch}.control{width:100%}.field-actions{justify-content:flex-start}}
</style>
