<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import type { CorpusRecord } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";

const props=withDefaults(defineProps<{selectedCount:number;totalCount:number;records?:CorpusRecord[];regionTypes?:string[];discourseRoles?:string[];disabled?:boolean}>(),{records:()=>[],regionTypes:()=>[],discourseRoles:()=>[],disabled:false});
const emit=defineEmits<{apply:[payload:{changes:Record<string,unknown>;applyToAll:boolean}];close:[]} >();
const i18n=useI18nStore();
const applyToAll=ref(false);
const active=reactive<Record<string,boolean>>({});
const values=reactive<Record<string,string>>({});
const query=ref("");
const titleEl=ref<HTMLElement|null>(null);
const groups=[
  {key:"identity",label:"pdf_corpus.bulk_group_identity",fallback:"Identity & publication",fields:["work","document_title","document_author","translator","publisher","publication_place","publication_year","edition","isbn","document_language"]},
  {key:"discourse",label:"pdf_corpus.bulk_group_discourse",fallback:"Discourse & attribution",fields:["region_type","region_author","speaker","position_holder","target","discourse_role","proposition_status","stance","claim_scope","primary_text"]},
  {key:"indexing",label:"pdf_corpus.bulk_group_indexing",fallback:"Semantic indexing",fields:["topics","concepts","persons","works_referenced"]},
] as const;
const listFields=new Set(["topics","concepts","persons","works_referenced","document_language"]);
const booleanFields=new Set(["primary_text"]);
const enumValues=computed<Record<string,string[]>>(()=>({region_type:props.regionTypes||[],discourse_role:props.discourseRoles||[]}));
const filteredGroups=computed(()=>{const q=query.value.trim().toLowerCase();if(!q)return groups;return groups.map(group=>({...group,fields:group.fields.filter(field=>i18n.t(`record.${field}`,field.replaceAll('_',' ')).toLowerCase().includes(q))})).filter(group=>group.fields.length)});
const suggestions=computed(()=>{
  const out:Record<string,string[]>={};
  for(const group of groups)for(const field of group.fields){
    const seen=new Set<string>();
    for(const row of props.records||[]){const value=(row as Record<string,unknown>)[field];if(Array.isArray(value)){for(const item of value)if(String(item||'').trim())seen.add(String(item).trim())}else if(value!==null&&value!==undefined&&String(value).trim())seen.add(String(value).trim())}
    out[field]=Array.from(seen).sort((a,b)=>a.localeCompare(b)).slice(0,80);
  }
  return out;
});
const changes=computed(()=>{const result:Record<string,unknown>={};for(const group of groups)for(const field of group.fields){if(!active[field])continue;const raw=(values[field]||"").trim();if(booleanFields.has(field))result[field]=raw==="true"?true:raw==="false"?false:null;else if(listFields.has(field))result[field]=raw?raw.split(/[,\n]/).map(v=>v.trim()).filter(Boolean):[];else if(field==="publication_year")result[field]=raw&&/^\d{4}$/.test(raw)?Number(raw):(raw||null);else result[field]=raw||null}return result});
const activeCount=computed(()=>Object.keys(changes.value).length);
function apply(){if(activeCount.value)emit("apply",{changes:changes.value,applyToAll:applyToAll.value})}
function toggleGroup(fields:readonly string[],checked:boolean){for(const field of fields)active[field]=checked}
function keydown(event:KeyboardEvent){if(event.key==='Escape')emit('close')}
onMounted(()=>{window.addEventListener('keydown',keydown);titleEl.value?.focus({preventScroll:true})});
onBeforeUnmount(()=>window.removeEventListener('keydown',keydown));
</script>

<template><Teleport to="body"><div class="bulk-backdrop" @mousedown.self="emit('close')"><section class="bulk-dialog" role="dialog" aria-modal="true" aria-labelledby="bulk-metadata-title" aria-describedby="bulk-metadata-help">
  <header class="bulk-head"><div><span class="eyebrow">{{i18n.t('pdf_corpus.bulk_edit_eyebrow','Record metadata')}}</span><h2 id="bulk-metadata-title" ref="titleEl" tabindex="-1">{{i18n.t('pdf_corpus.bulk_metadata_title','Bulk edit record metadata')}}</h2><p id="bulk-metadata-help">{{i18n.t('pdf_corpus.bulk_metadata_help_v481','Select fields to change, then choose an existing corpus value or enter a new one. Unselected fields are untouched.')}}</p></div><UiButton size="small" :label="i18n.t('ui.close','Close')" @click="emit('close')"/></header>
  <div class="bulk-toolbar"><fieldset class="scope"><legend>{{i18n.t('pdf_corpus.bulk_scope','Scope')}}</legend><label><input v-model="applyToAll" :value="false" type="radio" name="bulk-scope" :disabled="disabled"><span><b>{{i18n.t('pdf_corpus.bulk_selected_records','Selected records')}}</b><small>{{i18n.tf('pdf_corpus.bulk_selected_count','{count} selected',{count:selectedCount})}}</small></span></label><label><input v-model="applyToAll" :value="true" type="radio" name="bulk-scope" :disabled="disabled"><span><b>{{i18n.t('pdf_corpus.bulk_apply_all','Apply to every record')}}</b><small>{{i18n.tf('pdf_corpus.bulk_total_count','{count} total records',{count:totalCount})}}</small></span></label></fieldset><label class="search"><span>{{i18n.t('pdf_corpus.bulk_find_field','Find a field')}}</span><input v-model="query" class="control" type="search" :placeholder="i18n.t('pdf_corpus.bulk_search_fields','Search metadata fields…')"></label></div>
  <div class="bulk-scroll">
    <section v-for="group in filteredGroups" :key="group.key" class="field-group"><header><h3>{{i18n.t(group.label,group.fallback)}}</h3><div><button type="button" class="link-button" @click="toggleGroup(group.fields,true)">{{i18n.t('ui.select_all','Select all')}}</button><span aria-hidden="true">·</span><button type="button" class="link-button" @click="toggleGroup(group.fields,false)">{{i18n.t('ui.clear','Clear')}}</button></div></header><div class="field-list">
      <div v-for="field in group.fields" :key="field" class="field-row" :data-active="active[field]?'true':'false'"><label class="field-toggle"><input v-model="active[field]" type="checkbox" :disabled="disabled"><span>{{i18n.t(`record.${field}`,field.replaceAll('_',' '))}}</span></label><div class="field-input">
        <select v-if="enumValues[field]?.length" v-model="values[field]" class="control" :disabled="disabled||!active[field]" :aria-label="i18n.tf('pdf_corpus.bulk_value_for','Value for {field}',{field:i18n.t(`record.${field}`,field)})"><option value="">{{i18n.t('pdf_corpus.choose_value','Choose a value…')}}</option><option v-for="option in enumValues[field]" :key="option" :value="option">{{i18n.t(`record.enum.${field}.${option}`,option.replaceAll('_',' '))}}</option></select>
        <select v-else-if="booleanFields.has(field)" v-model="values[field]" class="control" :disabled="disabled||!active[field]"><option value="">{{i18n.t('pdf_corpus.choose_value','Choose a value…')}}</option><option value="true">{{i18n.t('ui.yes','Yes')}}</option><option value="false">{{i18n.t('ui.no','No')}}</option></select>
        <template v-else><input v-model="values[field]" class="control" :list="`bulk-values-${field}`" :disabled="disabled||!active[field]" :aria-label="i18n.tf('pdf_corpus.bulk_value_for','Value for {field}',{field:i18n.t(`record.${field}`,field)})" :placeholder="listFields.has(field)?i18n.t('pdf_corpus.bulk_list_hint','Comma- or line-separated values'):i18n.t('pdf_corpus.bulk_value_placeholder','Choose an existing value or type a new one')"><datalist :id="`bulk-values-${field}`"><option v-for="option in suggestions[field]||[]" :key="option" :value="option"/></datalist><small v-if="suggestions[field]?.length">{{i18n.tf('pdf_corpus.bulk_existing_values','{count} existing value(s) available for autocomplete',{count:suggestions[field].length})}}</small></template>
      </div></div>
    </div></section>
    <p v-if="!filteredGroups.length" class="empty">{{i18n.t('pdf_corpus.bulk_no_fields','No metadata fields match that search.')}}</p>
  </div>
  <footer><div><b>{{i18n.tf('pdf_corpus.bulk_changes_count','{count} field(s) will change',{count:activeCount})}}</b><span>{{applyToAll?i18n.tf('pdf_corpus.bulk_scope_all','Will update all {count} records',{count:totalCount}):i18n.tf('pdf_corpus.bulk_scope_selected','Will update {count} selected records',{count:selectedCount})}}</span></div><div class="actions"><UiButton :label="i18n.t('ui.cancel','Cancel')" @click="emit('close')"/><UiButton variant="primary" :label="i18n.t('pdf_corpus.apply_bulk_metadata','Apply metadata changes')" :disabled="disabled||(!applyToAll&&selectedCount===0)||activeCount===0" @click="apply"/></div></footer>
</section></div></Teleport></template>

<style scoped>
.bulk-backdrop{position:fixed;inset:0;z-index:30000;display:grid;place-items:center;padding:20px;background:rgb(15 23 42 / .72);backdrop-filter:blur(8px)}.bulk-dialog{isolation:isolate;width:min(960px,calc(100vw - 28px));max-height:min(92vh,920px);display:grid;grid-template-rows:auto auto minmax(0,1fr) auto;overflow:hidden;border:1px solid var(--line);border-radius:18px;background:var(--bg);color:var(--text);box-shadow:0 32px 100px rgb(0 0 0 / .38)}.bulk-head,.bulk-toolbar,footer{padding:18px 20px}.bulk-head{display:flex;justify-content:space-between;gap:18px;border-bottom:1px solid var(--line);background:var(--card)}.eyebrow{font-size:.8125rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:800}h2{margin:3px 0 0;font-size:1.25rem}.bulk-head p{margin:6px 0 0;max-width:72ch;color:var(--muted);font-size:.875rem;line-height:1.5}.bulk-toolbar{display:grid;grid-template-columns:minmax(0,1fr) minmax(240px,320px);gap:18px;align-items:end;background:var(--soft);border-bottom:1px solid var(--line)}.scope{display:flex;gap:10px;margin:0;padding:0;border:0}.scope legend,.search>span{display:block;margin-bottom:6px;font-size:.8125rem;font-weight:800;color:var(--muted)}.scope label{display:flex;gap:9px;align-items:flex-start;min-width:180px;padding:9px 11px;border:1px solid var(--line);border-radius:9px;background:var(--card)}.scope input{width:18px;height:18px;margin-top:2px}.scope label>span{display:grid;gap:2px}.scope b{font-size:.875rem}.scope small,.field-input small{font-size:.8125rem;color:var(--muted)}.bulk-scroll{overflow:auto;padding:18px 20px;overscroll-behavior:contain;background:var(--bg)}.field-group+.field-group{margin-top:20px}.field-group>header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:9px}.field-group h3{margin:0;font-size:1rem}.field-group>header>div{display:flex;gap:7px;align-items:center;font-size:.8125rem;color:var(--muted)}.link-button{min-height:36px;border:0;background:none;padding:4px 7px;color:var(--accent);font:inherit;font-weight:700;cursor:pointer}.field-list{display:grid;grid-template-columns:1fr 1fr;gap:10px}.field-row{display:grid;gap:9px;padding:12px;border:1px solid var(--line);border-radius:11px;background:var(--card)}.field-row[data-active="true"]{border-color:color-mix(in srgb,var(--accent) 45%,var(--line));box-shadow:inset 3px 0 0 var(--accent)}.field-toggle{display:flex;gap:8px;align-items:center;font-size:.875rem;font-weight:750}.field-toggle input{width:18px;height:18px;flex:none}.field-input{display:grid;gap:4px}.control{min-height:42px}.empty{padding:24px;text-align:center;color:var(--muted)}footer{display:flex;justify-content:space-between;gap:16px;align-items:center;border-top:1px solid var(--line);background:var(--card)}footer>div:first-child{display:grid;gap:2px}footer b{font-size:.875rem}footer span{font-size:.8125rem;color:var(--muted)}.actions{display:flex;gap:8px}:is(button,input,select):focus-visible{outline:3px solid var(--accent);outline-offset:2px}@media(max-width:760px){.bulk-backdrop{padding:6px}.bulk-dialog{width:100%;max-height:98vh;border-radius:12px}.bulk-toolbar,.field-list{grid-template-columns:1fr}.scope{display:grid;grid-template-columns:1fr}.bulk-head,footer{align-items:stretch;flex-direction:column}.actions>*{flex:1}}
</style>
