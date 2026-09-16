<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";

const props=withDefaults(defineProps<{manifest?:Record<string,unknown>;disabled?:boolean}>(),{manifest:()=>({}),disabled:false});
const emit=defineEmits<{save:[changes:Record<string,unknown>]} >();
const i18n=useI18nStore();
const fields=["title","short_title","original_title","document_author","translator","publisher","publication_place","publication_year","edition","isbn","language","original_language","document_type","main_text_start_page","main_text_end_page","notes"] as const;
const draft=reactive<Record<string,string>>({});
const translationDraft=ref("");
watch(()=>props.manifest,()=>{for(const field of fields)draft[field]=String(props.manifest?.[field]??"");const value=props.manifest?.document_is_translation;translationDraft.value=typeof value==="boolean"?(value?"yes":"no"):""},{immediate:true,deep:true});
function save(){
  const changes:Record<string,unknown>={};
  for(const field of fields){
    const raw=(draft[field]||"").trim();
    if(field==="main_text_start_page"||field==="main_text_end_page")changes[field]=raw?Number(raw):null;
    else if(field==="publication_year")changes[field]=raw&&/^\d{4}$/.test(raw)?Number(raw):(raw||null);
    else changes[field]=raw||null;
  }
  changes.document_is_translation=translationDraft.value==="yes"?true:translationDraft.value==="no"?false:null;
  emit("save",changes);
}
</script>

<template>
  <section class="manifest-editor" :aria-label="i18n.t('pdf_corpus.document_manifest','Document manifest')">
    <div class="manifest-grid">
      <label><span>{{i18n.t('pdf_corpus.manifest_title','Title')}}</span><input v-model="draft.title" class="control" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_short_title','Short title')}}</span><input v-model="draft.short_title" class="control" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_original_title','Original title')}}</span><input v-model="draft.original_title" class="control" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_author','Document author')}}</span><input v-model="draft.document_author" class="control" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_translator','Translator')}}</span><input v-model="draft.translator" class="control" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_publisher','Publisher')}}</span><input v-model="draft.publisher" class="control" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_place','Publication place')}}</span><input v-model="draft.publication_place" class="control" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_year','Publication year')}}</span><input v-model="draft.publication_year" class="control" inputmode="numeric" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_edition','Edition')}}</span><input v-model="draft.edition" class="control" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_isbn','ISBN')}}</span><input v-model="draft.isbn" class="control" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_language','Document language')}}</span><input v-model="draft.language" class="control" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_original_language','Original language')}}</span><input v-model="draft.original_language" class="control" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_translation','Translation status')}}</span><select v-model="translationDraft" class="control" :disabled="disabled"><option value="">{{i18n.t('pdf_corpus.manifest_unknown','Unknown')}}</option><option value="yes">{{i18n.t('ui.yes','Yes')}}</option><option value="no">{{i18n.t('ui.no','No')}}</option></select></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_type','Document type')}}</span><input v-model="draft.document_type" class="control" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_main_start','Main text starts on physical PDF page')}}</span><input v-model="draft.main_text_start_page" class="control" type="number" min="1" :disabled="disabled"></label>
      <label><span>{{i18n.t('pdf_corpus.manifest_main_end','Main text ends on physical PDF page')}}</span><input v-model="draft.main_text_end_page" class="control" type="number" min="1" :disabled="disabled"></label>
      <label class="wide"><span>{{i18n.t('pdf_corpus.manifest_notes','Source-supported notes')}}</span><textarea v-model="draft.notes" class="control" rows="3" :disabled="disabled"></textarea></label>
    </div>
    <div class="manifest-actions"><p>{{i18n.t('pdf_corpus.manifest_help','These values are inherited deterministically by records. Saving regenerates inherited metadata and citations and reopens affected records for review.')}}</p><button type="button" class="btn small" :disabled="disabled" @click="save">{{i18n.t('pdf_corpus.save_manifest','Save document manifest')}}</button></div>
  </section>
</template>

<style scoped>
.manifest-editor{display:grid;gap:10px;padding-top:8px}.manifest-grid{display:grid;grid-template-columns:repeat(3,minmax(150px,1fr));gap:9px}.manifest-grid label{display:grid;gap:4px}.manifest-grid label>span{font-size:9px;font-weight:750;color:var(--muted)}.manifest-grid .wide{grid-column:1/-1}.manifest-grid textarea{resize:vertical;min-height:66px}.manifest-actions{display:flex;justify-content:space-between;gap:14px;align-items:flex-end}.manifest-actions p{margin:0;max-width:760px;font-size:9px;line-height:1.45;color:var(--muted)}.control:focus-visible,.btn:focus-visible{outline:3px solid var(--accent);outline-offset:2px}@media(max-width:900px){.manifest-grid{grid-template-columns:1fr 1fr}}@media(max-width:600px){.manifest-grid{grid-template-columns:1fr}.manifest-grid .wide{grid-column:auto}.manifest-actions{align-items:stretch;flex-direction:column}}
</style>
