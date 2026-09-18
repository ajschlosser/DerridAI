<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";

const props=withDefaults(defineProps<{selectedCount:number;totalCount:number;disabled?:boolean}>(),{disabled:false});
const emit=defineEmits<{apply:[payload:{changes:Record<string,unknown>;applyToAll:boolean}];close:[]} >();
const i18n=useI18nStore();
const applyToAll=ref(false);
const active=reactive<Record<string,boolean>>({});
const values=reactive<Record<string,string>>({});
const query=ref("");
const titleEl=ref<HTMLElement|null>(null);
const groups=[
  {key:"identity",label:"pdf_corpus.bulk_group_identity",fallback:"Identity & publication",fields:["work","document_title","document_author","translator","publisher","publication_place","publication_year","edition","isbn","document_language"]},
  {key:"discourse",label:"pdf_corpus.bulk_group_discourse",fallback:"Discourse & attribution",fields:["region_type","region_author","speaker","position_holder","target","discourse_role","proposition_status","stance","claim_scope"]},
  {key:"indexing",label:"pdf_corpus.bulk_group_indexing",fallback:"Semantic indexing",fields:["topics","concepts","persons","works_referenced"]},
] as const;
const listFields=new Set(["topics","concepts","persons","works_referenced","document_language"]);
const filteredGroups=computed(()=>{
  const q=query.value.trim().toLowerCase();
  if(!q)return groups;
  return groups.map(group=>({...group,fields:group.fields.filter(field=>i18n.t(`record.${field}`,field.replaceAll('_',' ')).toLowerCase().includes(q))})).filter(group=>group.fields.length);
});
const changes=computed(()=>{
  const result:Record<string,unknown>={};
  for(const group of groups)for(const field of group.fields){
    if(!active[field])continue;
    const raw=(values[field]||"").trim();
    if(listFields.has(field))result[field]=raw?raw.split(/[,\n]/).map(v=>v.trim()).filter(Boolean):[];
    else if(field==="publication_year")result[field]=raw&&/^\d{4}$/.test(raw)?Number(raw):(raw||null);
    else result[field]=raw||null;
  }
  return result;
});
const activeCount=computed(()=>Object.keys(changes.value).length);
function apply(){if(activeCount.value)emit("apply",{changes:changes.value,applyToAll:applyToAll.value})}
function toggleGroup(fields:readonly string[],checked:boolean){for(const field of fields)active[field]=checked}
function keydown(event:KeyboardEvent){if(event.key==='Escape')emit('close')}
onMounted(()=>{window.addEventListener('keydown',keydown);titleEl.value?.focus({preventScroll:true})});
onBeforeUnmount(()=>window.removeEventListener('keydown',keydown));
</script>

<template><Teleport to="body"><div class="bulk-backdrop" @mousedown.self="emit('close')"><section class="bulk-dialog" role="dialog" aria-modal="true" aria-labelledby="bulk-metadata-title">
  <header class="bulk-head"><div><h2 id="bulk-metadata-title" ref="titleEl" tabindex="-1">{{i18n.t('pdf_corpus.bulk_metadata_title','Bulk edit record metadata')}}</h2><p>{{i18n.t('pdf_corpus.bulk_metadata_help_v48','Choose only the fields you intend to change. Unselected fields are never sent or overwritten.')}}</p></div><UiButton size="small" :label="i18n.t('ui.close','Close')" @click="emit('close')"/></header>
  <div class="bulk-toolbar"><label class="scope"><input v-model="applyToAll" type="checkbox" :disabled="disabled"><span><b>{{i18n.t('pdf_corpus.bulk_apply_all','Apply to every record')}}</b><small>{{i18n.tf('pdf_corpus.bulk_scope_description','{selected} selected · {total} total records',{selected:selectedCount,total:totalCount})}}</small></span></label><label class="search"><span class="sr-only">{{i18n.t('ui.search','Search')}}</span><input v-model="query" class="control" type="search" :placeholder="i18n.t('pdf_corpus.bulk_search_fields','Search metadata fields…')"></label></div>
  <div class="bulk-scroll">
    <section v-for="group in filteredGroups" :key="group.key" class="field-group"><header><h3>{{i18n.t(group.label,group.fallback)}}</h3><div><button type="button" class="link-button" @click="toggleGroup(group.fields,true)">{{i18n.t('ui.select_all','Select all')}}</button><span aria-hidden="true">·</span><button type="button" class="link-button" @click="toggleGroup(group.fields,false)">{{i18n.t('ui.clear','Clear')}}</button></div></header><div class="field-list"><label v-for="field in group.fields" :key="field" class="field-row" :data-active="active[field]?'true':'false'"><span class="field-toggle"><input v-model="active[field]" type="checkbox" :disabled="disabled"><span>{{i18n.t(`record.${field}`,field.replaceAll('_',' '))}}</span></span><textarea v-if="listFields.has(field)" v-model="values[field]" rows="2" class="control" :disabled="disabled||!active[field]" :aria-label="i18n.tf('pdf_corpus.bulk_value_for','Value for {field}',{field:i18n.t(`record.${field}`,field)})" :placeholder="i18n.t('pdf_corpus.bulk_list_hint','Comma- or line-separated values')"></textarea><input v-else v-model="values[field]" class="control" :disabled="disabled||!active[field]" :aria-label="i18n.tf('pdf_corpus.bulk_value_for','Value for {field}',{field:i18n.t(`record.${field}`,field)})"></label></div></section>
    <p v-if="!filteredGroups.length" class="empty">{{i18n.t('pdf_corpus.bulk_no_fields','No metadata fields match that search.')}}</p>
  </div>
  <footer><div><b>{{i18n.tf('pdf_corpus.bulk_changes_count','{count} field(s) will change',{count:activeCount})}}</b><span>{{applyToAll?i18n.tf('pdf_corpus.bulk_scope_all','Will update all {count} records',{count:totalCount}):i18n.tf('pdf_corpus.bulk_scope_selected','Will update {count} selected records',{count:selectedCount})}}</span></div><div class="actions"><UiButton :label="i18n.t('ui.cancel','Cancel')" @click="emit('close')"/><UiButton variant="primary" :label="i18n.t('pdf_corpus.apply_bulk_metadata','Apply metadata changes')" :disabled="disabled||(!applyToAll&&selectedCount===0)||activeCount===0" @click="apply"/></div></footer>
</section></div></Teleport></template>

<style scoped>
.bulk-backdrop{position:fixed;inset:0;z-index:1100;display:grid;place-items:center;padding:20px;background:rgba(15,23,42,.5)}.bulk-dialog{width:min(980px,calc(100vw - 28px));max-height:min(90vh,920px);display:grid;grid-template-rows:auto auto minmax(0,1fr) auto;overflow:hidden;border:1px solid var(--line);border-radius:16px;background:var(--card);box-shadow:0 28px 90px rgba(15,23,42,.26)}.bulk-head,.bulk-toolbar,footer{padding:16px 18px}.bulk-head{display:flex;justify-content:space-between;gap:18px;border-bottom:1px solid var(--line)}h2{margin:0;font-size:1.25rem}.bulk-head p{margin:5px 0 0;color:var(--muted);font-size:.875rem;line-height:1.5}.bulk-toolbar{display:grid;grid-template-columns:minmax(0,1fr) minmax(220px,320px);gap:14px;align-items:center;background:var(--soft);border-bottom:1px solid var(--line)}.scope{display:flex;gap:10px;align-items:flex-start}.scope input{width:20px;height:20px;margin-top:2px}.scope>span{display:grid;gap:2px}.scope b{font-size:.875rem}.scope small{font-size:.8125rem;color:var(--muted)}.bulk-scroll{overflow:auto;padding:16px 18px;overscroll-behavior:contain}.field-group+ .field-group{margin-top:18px}.field-group>header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px}.field-group h3{margin:0;font-size:.9375rem}.field-group>header>div{display:flex;gap:7px;align-items:center;font-size:.8125rem;color:var(--muted)}.link-button{border:0;background:none;padding:4px;color:var(--accent);font:inherit;font-weight:700;cursor:pointer}.field-list{display:grid;grid-template-columns:1fr 1fr;gap:8px}.field-row{display:grid;grid-template-columns:minmax(150px,.75fr) minmax(160px,1fr);gap:10px;align-items:center;padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--card)}.field-row[data-active="true"]{border-color:color-mix(in srgb,var(--accent) 45%,var(--line));background:color-mix(in srgb,var(--accent) 4%,var(--card))}.field-toggle{display:flex;gap:8px;align-items:flex-start;font-size:.8125rem;font-weight:700}.field-toggle input{width:18px;height:18px;flex:none}.field-row textarea{resize:vertical;min-height:64px}.empty{padding:20px;text-align:center;color:var(--muted)}footer{display:flex;justify-content:space-between;gap:16px;align-items:center;border-top:1px solid var(--line);background:var(--card)}footer>div:first-child{display:grid;gap:2px}footer b{font-size:.875rem}footer span{font-size:.8125rem;color:var(--muted)}.actions{display:flex;gap:8px}:is(button,input,textarea):focus-visible{outline:3px solid var(--accent);outline-offset:2px}@media(max-width:760px){.bulk-backdrop{padding:6px}.bulk-dialog{width:100%;max-height:97vh}.bulk-toolbar,.field-list{grid-template-columns:1fr}.field-row{grid-template-columns:1fr}.bulk-head,footer{align-items:stretch;flex-direction:column}.actions>*{flex:1}}
</style>
