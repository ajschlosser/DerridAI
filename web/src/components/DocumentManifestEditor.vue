<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";
import UiField from "./ui/UiField.vue";

const props=withDefaults(defineProps<{manifest?:Record<string,unknown>;disabled?:boolean}>(),{manifest:()=>({}),disabled:false});
const emit=defineEmits<{save:[changes:Record<string,unknown>]} >();
const i18n=useI18nStore();
const fields=["title","short_title","original_title","document_author","translator","publisher","publication_place","publication_year","edition","isbn","language","original_language","document_type","main_text_start_page","main_text_end_page","notes"] as const;
const draft=reactive<Record<string,string>>({});
const baseline=reactive<Record<string,string>>({});
const translationDraft=ref("");const translationBaseline=ref("");
watch(()=>props.manifest,()=>{for(const field of fields){const value=String(props.manifest?.[field]??"");draft[field]=value;baseline[field]=value}const value=props.manifest?.document_is_translation;translationDraft.value=typeof value==="boolean"?(value?"yes":"no"):"";translationBaseline.value=translationDraft.value},{immediate:true,deep:true});
const dirty=computed(()=>fields.some(field=>draft[field]!==baseline[field])||translationDraft.value!==translationBaseline.value);
function normalized(field:string,raw:string):unknown{const value=raw.trim();if(field==="main_text_start_page"||field==="main_text_end_page")return value?Number(value):null;if(field==="publication_year")return value&&/^\d{4}$/.test(value)?Number(value):(value||null);return value||null}
function save(){const changes:Record<string,unknown>={};for(const field of fields)if(draft[field]!==baseline[field])changes[field]=normalized(field,draft[field]||"");if(translationDraft.value!==translationBaseline.value)changes.document_is_translation=translationDraft.value==="yes"?true:translationDraft.value==="no"?false:null;if(Object.keys(changes).length)emit("save",changes)}
function reset(){for(const field of fields)draft[field]=baseline[field];translationDraft.value=translationBaseline.value}
</script>

<template>
  <section class="manifest-editor" :aria-label="i18n.t('pdf_corpus.document_manifest','Document manifest')">
    <p class="manifest-intro">{{i18n.t('pdf_corpus.manifest_help','These values are inherited deterministically by records. Saving regenerates inherited metadata and citations while preserving explicit record overrides.')}}</p>
    <fieldset><legend>{{i18n.t('pdf_corpus.manifest_identity_group','Work identity')}}</legend><div class="manifest-grid">
      <UiField :label="i18n.t('pdf_corpus.manifest_title','Title')"><input v-model="draft.title" class="control" :disabled="disabled"></UiField>
      <UiField :label="i18n.t('pdf_corpus.manifest_short_title','Short title')"><input v-model="draft.short_title" class="control" :disabled="disabled"></UiField>
      <UiField :label="i18n.t('pdf_corpus.manifest_original_title','Original title')"><input v-model="draft.original_title" class="control" :disabled="disabled"></UiField>
      <UiField :label="i18n.t('pdf_corpus.manifest_author','Document author')"><input v-model="draft.document_author" class="control" :disabled="disabled"></UiField>
      <UiField :label="i18n.t('pdf_corpus.manifest_translator','Translator')"><input v-model="draft.translator" class="control" :disabled="disabled"></UiField>
      <UiField :label="i18n.t('pdf_corpus.manifest_type','Document type')"><input v-model="draft.document_type" class="control" :disabled="disabled"></UiField>
    </div></fieldset>
    <fieldset><legend>{{i18n.t('pdf_corpus.manifest_publication_group','Publication')}}</legend><div class="manifest-grid">
      <UiField :label="i18n.t('pdf_corpus.manifest_publisher','Publisher')"><input v-model="draft.publisher" class="control" :disabled="disabled"></UiField>
      <UiField :label="i18n.t('pdf_corpus.manifest_place','Publication place')"><input v-model="draft.publication_place" class="control" :disabled="disabled"></UiField>
      <UiField :label="i18n.t('pdf_corpus.manifest_year','Publication year')"><input v-model="draft.publication_year" class="control" inputmode="numeric" :disabled="disabled"></UiField>
      <UiField :label="i18n.t('pdf_corpus.manifest_edition','Edition')"><input v-model="draft.edition" class="control" :disabled="disabled"></UiField>
      <UiField :label="i18n.t('pdf_corpus.manifest_isbn','ISBN')"><input v-model="draft.isbn" class="control" :disabled="disabled"></UiField>
    </div></fieldset>
    <fieldset><legend>{{i18n.t('pdf_corpus.manifest_language_group','Language and translation')}}</legend><div class="manifest-grid">
      <UiField :label="i18n.t('pdf_corpus.manifest_language','Document language')"><input v-model="draft.language" class="control" :disabled="disabled"></UiField>
      <UiField :label="i18n.t('pdf_corpus.manifest_original_language','Original language')"><input v-model="draft.original_language" class="control" :disabled="disabled"></UiField>
      <UiField :label="i18n.t('pdf_corpus.manifest_translation','Translation status')"><select v-model="translationDraft" class="control" :disabled="disabled"><option value="">{{i18n.t('pdf_corpus.manifest_unknown','Unknown')}}</option><option value="yes">{{i18n.t('ui.yes','Yes')}}</option><option value="no">{{i18n.t('ui.no','No')}}</option></select></UiField>
    </div></fieldset>
    <fieldset><legend>{{i18n.t('pdf_corpus.manifest_structure_group','Document structure')}}</legend><div class="manifest-grid">
      <UiField :label="i18n.t('pdf_corpus.manifest_main_start','Main text starts on physical PDF page')"><input v-model="draft.main_text_start_page" class="control" type="number" min="1" :disabled="disabled"></UiField>
      <UiField :label="i18n.t('pdf_corpus.manifest_main_end','Main text ends on physical PDF page')"><input v-model="draft.main_text_end_page" class="control" type="number" min="1" :disabled="disabled"></UiField>
      <UiField wide :label="i18n.t('pdf_corpus.manifest_notes','Source-supported notes')"><textarea v-model="draft.notes" class="control" rows="3" :disabled="disabled"></textarea></UiField>
    </div></fieldset>
    <div class="manifest-actions"><span v-if="dirty" role="status">{{i18n.t('pdf_corpus.manifest_unsaved','Unsaved document metadata changes')}}</span><span v-else>{{i18n.t('pdf_corpus.manifest_no_changes','No unsaved changes')}}</span><div><UiButton size="small" :label="i18n.t('ui.reset','Reset')" :disabled="disabled||!dirty" @click="reset"/><UiButton size="small" variant="primary" :label="i18n.t('pdf_corpus.save_manifest','Save document manifest')" :disabled="disabled||!dirty" @click="save"/></div></div>
  </section>
</template>

<style scoped>
.manifest-editor{display:grid;gap:12px}.manifest-intro{margin:0;color:var(--muted);font-size:.875rem;line-height:1.5}fieldset{margin:0;padding:12px;border:1px solid var(--line);border-radius:10px}legend{padding:0 6px;font-size:.875rem;font-weight:750}.manifest-grid{display:grid;grid-template-columns:repeat(3,minmax(150px,1fr));gap:10px}.manifest-grid .wide{grid-column:1/-1}.manifest-grid textarea{resize:vertical;min-height:76px}.manifest-actions{display:flex;justify-content:space-between;gap:14px;align-items:center}.manifest-actions>span{font-size:.8125rem;color:var(--muted)}.manifest-actions>div{display:flex;gap:8px}.control:focus-visible,.btn:focus-visible{outline:3px solid var(--accent);outline-offset:2px}@media(max-width:900px){.manifest-grid{grid-template-columns:1fr 1fr}}@media(max-width:600px){.manifest-grid{grid-template-columns:1fr}.manifest-grid .wide{grid-column:auto}.manifest-actions{align-items:stretch;flex-direction:column}}
</style>
