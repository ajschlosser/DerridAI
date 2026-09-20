<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import type { CorpusRecord } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";
import { usableOptions } from "../domain/metadataValues";
import type { MetadataSchema } from "../api/metadataSchemas";
import UiButton from "./ui/UiButton.vue";
import UiField from "./ui/UiField.vue";
import MetadataFormSection from "./MetadataFormSection.vue";
import MetadataFormFooter from "./MetadataFormFooter.vue";

// Change one or more fields on many records at once. It reads and looks like Edit document metadata: fields in
// titled groups, a field is changed simply by giving it a value, and the footer says in words what will change.
// A field left empty is left alone; "Clear this field" is the deliberate way to blank it on every record.
const props=withDefaults(defineProps<{selectedCount:number;totalCount:number;records?:CorpusRecord[];regionTypes?:string[];discourseRoles?:string[];disabled?:boolean;schema?:MetadataSchema|null}>(),{records:()=>[],regionTypes:()=>[],discourseRoles:()=>[],disabled:false,schema:null});
const emit=defineEmits<{apply:[payload:{changes:Record<string,unknown>;applyToAll:boolean}];close:[]} >();
const i18n=useI18nStore();
const applyToAll=ref(false);
const values=reactive<Record<string,string>>({});
const cleared=reactive<Record<string,boolean>>({});
const query=ref("");
const titleEl=ref<HTMLElement|null>(null);
// Document details (title, author, publisher…) are set once for the whole document in Edit document metadata and
// inherited by every record. They stay here for the rarer case of overriding them on chosen records.
type BulkGroup={key:string;label:string;fallback:string;help:string;helpFallback:string;fields:string[]};
const legacyGroups:BulkGroup[]=[
  {key:"discourse",label:"pdf_corpus.bulk_group_discourse",fallback:"Discourse & attribution",help:"pdf_corpus.bulk_group_discourse_help",helpFallback:"Who is speaking, what the passage does, and what it is about.",fields:["region_type","region_author","speaker","position_holder","target","discourse_role","proposition_status","stance","claim_scope","primary_text"]},
  {key:"indexing",label:"pdf_corpus.bulk_group_indexing",fallback:"Semantic indexing",help:"pdf_corpus.bulk_group_indexing_help",helpFallback:"Topics, concepts, people and works the passages mention.",fields:["topics","concepts","persons","works_referenced"]},
  {key:"identity",label:"pdf_corpus.bulk_group_identity",fallback:"Document details on these records",help:"pdf_corpus.bulk_group_identity_help",helpFallback:"These are inherited from Edit document metadata. Change them here only to override them on the chosen records.",fields:["work","document_title","document_author","translator","publisher","publication_place","publication_year","edition","isbn","document_language"]},
] as unknown as BulkGroup[];
const identityGroup=legacyGroups.find(group=>group.key==="identity")!;
// With a schema, the groups and fields are the schema's (the locked core first, in the discourse group); document details stay last.
const groups=computed<BulkGroup[]>(()=>props.schema?[
  ...props.schema.groups.map(group=>({key:group.key,label:group.label,fallback:group.label,help:"pdf_corpus.bulk_schema_group_help",helpFallback:"",fields:[...(group.key==="discourse"?["region_type","primary_text","discourse_role"]:[]),...props.schema!.fields.filter(field=>field.group===group.key).map(field=>field.name)]})),
  identityGroup,
]:legacyGroups);
const schemaFieldMap=computed(()=>Object.fromEntries((props.schema?.fields||[]).map(field=>[field.name,field])));
const listFields=computed(()=>props.schema?new Set([...(props.schema.fields.filter(f=>f.type==="list").map(f=>f.name)),"document_language"]):new Set(["topics","concepts","persons","works_referenced","document_language"]));
const booleanFields=computed(()=>props.schema?new Set(["primary_text",...props.schema.fields.filter(f=>f.type==="boolean").map(f=>f.name)]):new Set(["primary_text"]));
const enumValues=computed<Record<string,string[]>>(()=>({region_type:props.regionTypes||[],discourse_role:props.discourseRoles||[],...Object.fromEntries((props.schema?.fields||[]).filter(f=>f.type==="choice"&&f.strict).map(f=>[f.name,f.values.map(v=>v.value)]))}));
const name=(field:string)=>i18n.t(`record.${field}`,schemaFieldMap.value[field]?.label||field.replaceAll('_',' '));
const filteredGroups=computed(()=>{const q=query.value.trim().toLowerCase();if(!q)return groups.value;return groups.value.map(group=>({...group,fields:group.fields.filter(field=>name(field).toLowerCase().includes(q))})).filter(group=>group.fields.length)});
// Existing corpus values to autocomplete from, without placeholders such as "null".
const suggestions=computed(()=>{
  const out:Record<string,string[]>={};
  for(const group of groups.value)for(const field of group.fields){
    const seen:unknown[]=[];
    for(const row of props.records||[]){const value=(row as Record<string,unknown>)[field];if(Array.isArray(value))seen.push(...value);else seen.push(value)}
    out[field]=usableOptions(seen).sort((a,b)=>a.localeCompare(b)).slice(0,80);
  }
  return out;
});
function valueFor(field:string):unknown{
  const raw=(values[field]||"").trim();
  if(cleared[field])return listFields.value.has(field)?[]:null;
  if(booleanFields.value.has(field))return raw==="true"?true:raw==="false"?false:undefined;
  if(!raw)return undefined;
  if(listFields.value.has(field))return raw.split(/[,\n]/).map(v=>v.trim()).filter(Boolean);
  if(field==="publication_year")return /^\d{4}$/.test(raw)?Number(raw):raw;
  return raw;
}
const changes=computed(()=>{const result:Record<string,unknown>={};for(const group of groups.value)for(const field of group.fields){const value=valueFor(field);if(value!==undefined)result[field]=value}return result});
const activeCount=computed(()=>Object.keys(changes.value).length);
function apply(){if(activeCount.value)emit("apply",{changes:changes.value,applyToAll:applyToAll.value})}
function reset(){for(const key of Object.keys(values))delete values[key];for(const key of Object.keys(cleared))delete cleared[key];applyToAll.value=false}
function keydown(event:KeyboardEvent){if(event.key==='Escape')emit('close')}
onMounted(()=>{window.addEventListener('keydown',keydown);titleEl.value?.focus({preventScroll:true})});
onBeforeUnmount(()=>window.removeEventListener('keydown',keydown));
</script>

<template><Teleport to="body"><div class="bulk-backdrop" @mousedown.self="emit('close')"><form class="bulk-dialog" role="dialog" aria-modal="true" aria-labelledby="bulk-metadata-title" aria-describedby="bulk-metadata-help" @submit.prevent="apply">
  <header class="bulk-head">
    <div><span class="eyebrow">{{i18n.t('pdf_corpus.bulk_edit_eyebrow','Record metadata')}}</span><h2 id="bulk-metadata-title" ref="titleEl" tabindex="-1">{{i18n.t('pdf_corpus.bulk_metadata_title','Bulk edit record metadata')}}</h2><p id="bulk-metadata-help">{{i18n.t('pdf_corpus.bulk_metadata_help_v482','Give a field a value to set it on every record in scope. Fields you leave empty are not touched.')}}</p></div>
    <button type="button" class="bulk-close" :aria-label="i18n.t('ui.close','Close')" @click="emit('close')">×</button>
  </header>
  <div class="bulk-scroll">
    <MetadataFormSection :title="i18n.t('pdf_corpus.bulk_scope','Scope')" :description="i18n.t('pdf_corpus.bulk_scope_help','Which records these changes apply to.')">
      <fieldset class="bulk-scope wide">
        <label><input v-model="applyToAll" :value="false" type="radio" name="bulk-scope" :disabled="disabled"><span><b>{{i18n.t('pdf_corpus.bulk_selected_records','Selected records')}}</b><small>{{i18n.tf('pdf_corpus.bulk_selected_count','{count} selected',{count:selectedCount})}}</small></span></label>
        <label><input v-model="applyToAll" :value="true" type="radio" name="bulk-scope" :disabled="disabled"><span><b>{{i18n.t('pdf_corpus.bulk_apply_all','Apply to every record')}}</b><small>{{i18n.tf('pdf_corpus.bulk_total_count','{count} total records',{count:totalCount})}}</small></span></label>
      </fieldset>
      <UiField class="wide" :label="i18n.t('pdf_corpus.bulk_find_field','Find a field')"><input v-model="query" class="control" type="search" :placeholder="i18n.t('pdf_corpus.bulk_search_fields','Search metadata fields…')"></UiField>
    </MetadataFormSection>

    <MetadataFormSection v-for="group in filteredGroups" :key="group.key" :title="i18n.t(group.label,group.fallback)" :description="i18n.t(group.help,group.helpFallback)">
      <UiField v-for="field in group.fields" :key="field" :label="name(field)">
        <select v-if="enumValues[field]?.length" v-model="values[field]" class="control" :disabled="disabled||cleared[field]"><option value="">{{i18n.t('pdf_corpus.bulk_leave_unchanged','Leave unchanged')}}</option><option v-for="option in enumValues[field]" :key="option" :value="option">{{i18n.t(`record.enum.${field}.${option}`,option.replaceAll('_',' '))}}</option></select>
        <select v-else-if="booleanFields.has(field)" v-model="values[field]" class="control" :disabled="disabled||cleared[field]"><option value="">{{i18n.t('pdf_corpus.bulk_leave_unchanged','Leave unchanged')}}</option><option value="true">{{i18n.t('ui.yes','Yes')}}</option><option value="false">{{i18n.t('ui.no','No')}}</option></select>
        <template v-else><input v-model="values[field]" class="control" :list="`bulk-values-${field}`" :disabled="disabled||cleared[field]" :placeholder="listFields.has(field)?i18n.t('pdf_corpus.bulk_list_hint','Comma- or line-separated values'):i18n.t('pdf_corpus.bulk_leave_unchanged','Leave unchanged')"><datalist :id="`bulk-values-${field}`"><option v-for="option in suggestions[field]||[]" :key="option" :value="option"/></datalist></template>
        <span class="bulk-clear"><input :id="`bulk-clear-${field}`" v-model="cleared[field]" type="checkbox" :disabled="disabled"><label :for="`bulk-clear-${field}`">{{i18n.t('pdf_corpus.bulk_clear_field','Clear this field on every record in scope')}}</label></span>
      </UiField>
    </MetadataFormSection>
    <p v-if="!filteredGroups.length" class="empty">{{i18n.t('pdf_corpus.bulk_no_fields','No metadata fields match that search.')}}</p>
  </div>
  <MetadataFormFooter class="bulk-footer" :summary="activeCount?i18n.tf('pdf_corpus.bulk_changes_count','{count} field(s) will change',{count:activeCount}):i18n.t('pdf_corpus.bulk_no_changes','No changes yet')" :detail="applyToAll?i18n.tf('pdf_corpus.bulk_scope_all','Will update all {count} records',{count:totalCount}):i18n.tf('pdf_corpus.bulk_scope_selected','Will update {count} selected records',{count:selectedCount})">
    <UiButton :label="i18n.t('ui.cancel','Cancel')" @click="emit('close')"/><UiButton :label="i18n.t('ui.reset','Reset')" :disabled="disabled||(!activeCount&&!applyToAll)" @click="reset"/><UiButton type="submit" variant="primary" :label="i18n.t('pdf_corpus.bulk_apply','Apply changes')" :disabled="disabled||!activeCount||(!applyToAll&&selectedCount<1)"/>
  </MetadataFormFooter>
</form></div></Teleport></template>

<style scoped>
.bulk-backdrop{position:fixed;inset:0;z-index:30000;display:grid;place-items:center;padding:20px;background:color-mix(in srgb,var(--text) 72%,transparent);backdrop-filter:blur(8px)}
.bulk-dialog{isolation:isolate;inline-size:min(900px,calc(100vw - 28px));max-block-size:min(92vh,920px);display:grid;grid-template-rows:auto minmax(0,1fr) auto;overflow:hidden;border:1px solid var(--line);border-radius:18px;background:var(--bg);color:var(--text);box-shadow:0 32px 100px rgb(0 0 0 / .38)}
.bulk-head{display:flex;justify-content:space-between;gap:18px;padding:18px 22px;border-bottom:1px solid var(--line);background:var(--card)}
.eyebrow{font-size:.8125rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:800}
h2{margin:3px 0 0;font-size:1.25rem}.bulk-head p{margin:6px 0 0;max-inline-size:72ch;color:var(--muted);font-size:.875rem;line-height:1.5}
.bulk-close{align-self:flex-start;inline-size:40px;block-size:40px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--text);font-size:1.5rem;line-height:1;cursor:pointer}
.bulk-scroll{overflow:auto;display:grid;align-content:start;gap:22px;padding:18px 22px 22px;overscroll-behavior:auto}
.bulk-scope{display:flex;flex-wrap:wrap;gap:10px;margin:0;padding:0;border:0}
.bulk-scope label{display:flex;gap:9px;align-items:flex-start;min-inline-size:200px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card)}
.bulk-scope input{inline-size:18px;block-size:18px;margin-top:2px}.bulk-scope label>span{display:grid;gap:2px}.bulk-scope b{font-size:.875rem}.bulk-scope small{font-size:.8125rem;color:var(--muted)}
.bulk-clear{display:flex;gap:8px;align-items:center;margin-top:2px;font-size:.8125rem;color:var(--muted)}.bulk-clear input{inline-size:16px;block-size:16px;flex:none}
.control{inline-size:100%;min-block-size:42px}.empty{padding:24px;text-align:center;color:var(--muted)}
.bulk-footer{padding:14px 22px;background:var(--card)}
:is(button,input,select):focus-visible{outline:3px solid var(--focus-ring);outline-offset:2px}
@media(max-width:760px){.bulk-backdrop{padding:6px}.bulk-dialog{inline-size:100%;max-block-size:98vh;border-radius:12px}}
</style>
