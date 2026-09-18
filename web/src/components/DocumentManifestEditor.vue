<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";
import UiField from "./ui/UiField.vue";
import UiStatusBadge from "./ui/UiStatusBadge.vue";

const props=withDefaults(defineProps<{manifest?:Record<string,unknown>;disabled?:boolean;affectedRecords?:number}>(),{manifest:()=>({}),disabled:false,affectedRecords:0});
const emit=defineEmits<{save:[changes:Record<string,unknown>]} >();
const i18n=useI18nStore();

type FieldDef={key:string;label:string;type?:"text"|"number"|"textarea";wide?:boolean;hint?:string};
type GroupDef={key:string;title:string;description:string;fields:FieldDef[]};
const groups=computed<GroupDef[]>(()=>[
  {key:"identity",title:i18n.t('pdf_corpus.manifest_identity_group','Work identity'),description:i18n.t('pdf_corpus.manifest_identity_help','Identify the work and the people responsible for this edition.'),fields:[
    {key:"title",label:i18n.t('pdf_corpus.manifest_title','Title')},{key:"short_title",label:i18n.t('pdf_corpus.manifest_short_title','Short title')},{key:"original_title",label:i18n.t('pdf_corpus.manifest_original_title','Original title')},{key:"document_author",label:i18n.t('pdf_corpus.manifest_author','Document author')},{key:"translator",label:i18n.t('pdf_corpus.manifest_translator','Translator')},{key:"document_type",label:i18n.t('pdf_corpus.manifest_type','Document type')}
  ]},
  {key:"publication",title:i18n.t('pdf_corpus.manifest_publication_group','Publication'),description:i18n.t('pdf_corpus.manifest_publication_help','Edition-level bibliographic details used by inherited record metadata and citations.'),fields:[
    {key:"publisher",label:i18n.t('pdf_corpus.manifest_publisher','Publisher')},{key:"publication_place",label:i18n.t('pdf_corpus.manifest_place','Publication place')},{key:"publication_year",label:i18n.t('pdf_corpus.manifest_year','Publication year'),type:"number"},{key:"edition",label:i18n.t('pdf_corpus.manifest_edition','Edition')},{key:"isbn",label:i18n.t('pdf_corpus.manifest_isbn','ISBN')}
  ]},
  {key:"language",title:i18n.t('pdf_corpus.manifest_language_group','Language and translation'),description:i18n.t('pdf_corpus.manifest_language_help','Language facts inform citation, translation, and corpus metadata.'),fields:[
    {key:"language",label:i18n.t('pdf_corpus.manifest_language','Document language')},{key:"original_language",label:i18n.t('pdf_corpus.manifest_original_language','Original language')}
  ]},
  {key:"structure",title:i18n.t('pdf_corpus.manifest_structure_group','Document structure'),description:i18n.t('pdf_corpus.manifest_structure_help','Physical PDF page bounds help distinguish main text from front and back matter.'),fields:[
    {key:"main_text_start_page",label:i18n.t('pdf_corpus.manifest_main_start','Main text starts on physical PDF page'),type:"number"},{key:"main_text_end_page",label:i18n.t('pdf_corpus.manifest_main_end','Main text ends on physical PDF page'),type:"number"},{key:"notes",label:i18n.t('pdf_corpus.manifest_notes','Source-supported notes'),type:"textarea",wide:true}
  ]}
]);
const fieldKeys=computed(()=>groups.value.flatMap(group=>group.fields.map(field=>field.key)));
const draft=reactive<Record<string,string>>({});
const baseline=reactive<Record<string,string>>({});
const translationDraft=ref("");const translationBaseline=ref("");
watch(()=>props.manifest,()=>{for(const field of fieldKeys.value){const value=String(props.manifest?.[field]??"");draft[field]=value;baseline[field]=value}const value=props.manifest?.document_is_translation;translationDraft.value=typeof value==="boolean"?(value?"yes":"no"):"";translationBaseline.value=translationDraft.value},{immediate:true,deep:true});
const dirtyFields=computed(()=>fieldKeys.value.filter(field=>draft[field]!==baseline[field]));
const dirty=computed(()=>dirtyFields.value.length>0||translationDraft.value!==translationBaseline.value);
const changedCount=computed(()=>dirtyFields.value.length+(translationDraft.value!==translationBaseline.value?1:0));
function normalized(field:string,raw:string):unknown{const value=raw.trim();if(field==="main_text_start_page"||field==="main_text_end_page")return value?Number(value):null;if(field==="publication_year")return value&&/^\d{4}$/.test(value)?Number(value):(value||null);return value||null}
function save(){const changes:Record<string,unknown>={};for(const field of fieldKeys.value)if(draft[field]!==baseline[field])changes[field]=normalized(field,draft[field]||"");if(translationDraft.value!==translationBaseline.value)changes.document_is_translation=translationDraft.value==="yes"?true:translationDraft.value==="no"?false:null;if(Object.keys(changes).length)emit("save",changes)}
function reset(){for(const field of fieldKeys.value)draft[field]=baseline[field];translationDraft.value=translationBaseline.value}
</script>

<template>
  <form class="manifest-editor" :aria-label="i18n.t('pdf_corpus.document_manifest','Document manifest')" @submit.prevent="save">
    <section class="manifest-impact" aria-labelledby="manifest-impact-title">
      <div><span class="eyebrow">{{i18n.t('pdf_corpus.document_defaults','Document defaults')}}</span><h3 id="manifest-impact-title">{{i18n.t('pdf_corpus.document_defaults_title','One edit, inherited consistently')}}</h3><p>{{i18n.t('pdf_corpus.manifest_help','These values are inherited deterministically by records. Saving regenerates inherited metadata and citations while preserving explicit record overrides.')}}</p></div>
      <UiStatusBadge v-if="props.affectedRecords>0" tone="info" :label="i18n.tf('pdf_corpus.document_defaults_records','{count} records inherit document defaults',{count:props.affectedRecords})" :show-dot="false"/>
    </section>

    <section v-for="group in groups" :key="group.key" class="manifest-section" :aria-labelledby="`manifest-${group.key}`">
      <header><h3 :id="`manifest-${group.key}`">{{group.title}}</h3><p>{{group.description}}</p></header>
      <div class="manifest-grid">
        <UiField v-for="field in group.fields" :key="field.key" :wide="field.wide" :label="field.label" :hint="field.hint||''">
          <textarea v-if="field.type==='textarea'" v-model="draft[field.key]" class="control" rows="4" :disabled="props.disabled"></textarea>
          <input v-else v-model="draft[field.key]" class="control" :type="field.type==='number'?'number':'text'" :inputmode="field.type==='number'?'numeric':undefined" :min="field.type==='number'?1:undefined" :disabled="props.disabled">
        </UiField>
        <UiField v-if="group.key==='language'" :label="i18n.t('pdf_corpus.manifest_translation','Translation status')">
          <select v-model="translationDraft" class="control" :disabled="props.disabled"><option value="">{{i18n.t('pdf_corpus.manifest_unknown','Unknown')}}</option><option value="yes">{{i18n.t('ui.yes','Yes')}}</option><option value="no">{{i18n.t('ui.no','No')}}</option></select>
        </UiField>
      </div>
    </section>

    <footer class="manifest-actions" aria-live="polite">
      <div class="manifest-change-summary"><b>{{dirty?i18n.tf('pdf_corpus.manifest_changes_count','{count} unsaved change(s)',{count:changedCount}):i18n.t('pdf_corpus.manifest_no_changes','No unsaved changes')}}</b><span v-if="dirty&&props.affectedRecords">{{i18n.tf('pdf_corpus.manifest_propagation_preview','Saving updates inherited values for up to {count} records; explicit record overrides remain unchanged.',{count:props.affectedRecords})}}</span></div>
      <div class="manifest-action-buttons"><UiButton :label="i18n.t('ui.reset','Reset')" :disabled="props.disabled||!dirty" @click="reset"/><UiButton type="submit" variant="primary" :label="i18n.t('pdf_corpus.save_manifest_changes','Save document changes')" :disabled="props.disabled||!dirty"/></div>
    </footer>
  </form>
</template>

<style scoped>
.manifest-editor{display:grid;gap:18px;max-width:900px;margin:0 auto}.manifest-impact{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;padding:14px 16px;border:1px solid var(--line);border-radius:12px;background:var(--panel-2,var(--soft))}.manifest-impact>div{display:grid;gap:4px}.eyebrow{font-size:.8125rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:800}.manifest-impact h3,.manifest-section h3{margin:0;font-size:1rem}.manifest-impact p,.manifest-section header p{margin:0;color:var(--muted);font-size:.875rem;line-height:1.5}.manifest-section{display:grid;gap:12px}.manifest-section>header{display:grid;gap:4px;padding-bottom:8px;border-bottom:1px solid var(--line)}.manifest-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 16px}.manifest-grid .wide{grid-column:1/-1}.manifest-grid textarea{resize:vertical;min-height:96px}.control{width:100%;min-height:42px}.manifest-actions{position:sticky;bottom:-20px;z-index:3;display:flex;justify-content:space-between;align-items:center;gap:16px;margin:2px -22px -20px;padding:14px 22px;border-top:1px solid var(--line);background:var(--panel);box-shadow:0 -10px 24px rgba(20,30,24,.05)}.manifest-change-summary{display:grid;gap:3px;min-width:0}.manifest-change-summary b{font-size:.875rem}.manifest-change-summary span{color:var(--muted);font-size:.8125rem;line-height:1.4}.manifest-action-buttons{display:flex;gap:8px;flex:none}@media(max-width:700px){.manifest-impact{align-items:stretch;flex-direction:column}.manifest-grid{grid-template-columns:1fr}.manifest-actions{position:static;margin:0;padding:14px 0 0;align-items:stretch;flex-direction:column}.manifest-action-buttons{display:grid;grid-template-columns:1fr 1fr}.manifest-action-buttons :deep(.ui-button-wrap),.manifest-action-buttons :deep(.ui-button){width:100%}}
.manifest-editor :is(input,select,textarea):focus-visible{outline:3px solid var(--focus-ring,var(--accent));outline-offset:2px}
</style>
