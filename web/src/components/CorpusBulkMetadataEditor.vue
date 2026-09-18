<script setup lang="ts">
import { computed, reactive } from "vue";
import { useI18nStore } from "../stores/i18n";

const props=withDefaults(defineProps<{selectedCount:number;totalCount:number;disabled?:boolean}>(),{disabled:false});
const emit=defineEmits<{apply:[payload:{changes:Record<string,unknown>;applyToAll:boolean}];close:[]}>();
const i18n=useI18nStore();
const applyToAll=reactive({value:false});
const active=reactive<Record<string,boolean>>({});
const values=reactive<Record<string,string>>({});
const fields=[
  "work","document_title","document_author","translator","publisher","publication_place","publication_year","edition","isbn","document_language",
  "language","region_type","region_author","speaker","position_holder","target","discourse_role","proposition_status","stance","claim_scope",
  "topics","concepts","persons","works_referenced"
] as const;
const listFields=new Set(["topics","concepts","persons","works_referenced"]);
const changes=computed(()=>{
  const result:Record<string,unknown>={};
  for(const field of fields){
    if(!active[field])continue;
    const raw=(values[field]||"").trim();
    if(listFields.has(field))result[field]=raw?raw.split(/[,\n]/).map(v=>v.trim()).filter(Boolean):[];
    else if(field==="publication_year")result[field]=raw&&/^\d{4}$/.test(raw)?Number(raw):(raw||null);
    else result[field]=raw||null;
  }
  return result;
});
function apply(){if(!Object.keys(changes.value).length)return;emit("apply",{changes:changes.value,applyToAll:applyToAll.value})}
</script>

<template>
  <section class="bulk-editor" role="dialog" aria-modal="false" :aria-labelledby="'bulk-metadata-title'">
    <header><div><h3 id="bulk-metadata-title">{{i18n.t('pdf_corpus.bulk_metadata_title','Bulk edit record metadata')}}</h3><p>{{i18n.t('pdf_corpus.bulk_metadata_help','Only checked fields are changed. Existing values in every other field are left untouched.')}}</p></div><button type="button" class="btn small" @click="$emit('close')">{{i18n.t('ui.close','Close')}}</button></header>
    <label class="scope"><input v-model="applyToAll.value" type="checkbox" :disabled="disabled"><span>{{i18n.tf('pdf_corpus.bulk_metadata_all_records','Apply to all {count} records instead of the {selected} selected records',{count:totalCount,selected:selectedCount})}}</span></label>
    <div class="field-grid">
      <label v-for="field in fields" :key="field" class="field-row">
        <input v-model="active[field]" type="checkbox" :disabled="disabled">
        <span>{{i18n.t(`record.${field}`,field.replaceAll('_',' '))}}</span>
        <textarea v-if="listFields.has(field)" v-model="values[field]" rows="2" class="control" :disabled="disabled||!active[field]" :aria-label="i18n.tf('pdf_corpus.bulk_value_for','Value for {field}',{field:i18n.t(`record.${field}`,field)})"></textarea>
        <input v-else v-model="values[field]" class="control" :disabled="disabled||!active[field]" :aria-label="i18n.tf('pdf_corpus.bulk_value_for','Value for {field}',{field:i18n.t(`record.${field}`,field)})">
      </label>
    </div>
    <footer><span>{{applyToAll.value?i18n.tf('pdf_corpus.bulk_scope_all','Will update all {count} records',{count:totalCount}):i18n.tf('pdf_corpus.bulk_scope_selected','Will update {count} selected records',{count:selectedCount})}}</span><button type="button" class="btn primary" :disabled="disabled||(!applyToAll.value&&selectedCount===0)||Object.keys(changes).length===0" @click="apply">{{i18n.t('pdf_corpus.apply_bulk_metadata','Apply metadata changes')}}</button></footer>
  </section>
</template>

<style scoped>
.bulk-editor{display:grid;gap:14px;padding:16px;border:1px solid var(--line);border-radius:12px;background:var(--card)}header,footer{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}h3{margin:0;font-size:1rem}p{margin:4px 0 0;color:var(--muted);font-size:.875rem;line-height:1.5}.scope{display:flex;gap:9px;align-items:flex-start;font-size:.875rem}.scope input,.field-row>input{inline-size:18px;block-size:18px;flex:none}.field-grid{display:grid;grid-template-columns:repeat(2,minmax(260px,1fr));gap:10px}.field-row{display:grid;grid-template-columns:20px minmax(130px,.7fr) minmax(160px,1fr);gap:8px;align-items:center;padding:8px;border:1px solid var(--line);border-radius:8px}.field-row>span{font-size:.8125rem;font-weight:650}.control{width:100%;min-height:36px}.field-row textarea{resize:vertical}footer{align-items:center;border-top:1px solid var(--line);padding-top:12px}footer span{font-size:.8125rem;color:var(--muted)}:is(button,input,textarea):focus-visible{outline:3px solid var(--accent);outline-offset:2px}@media(max-width:850px){.field-grid{grid-template-columns:1fr}.field-row{grid-template-columns:20px 1fr}.field-row .control{grid-column:2}header,footer{flex-direction:column;align-items:stretch}}
</style>
