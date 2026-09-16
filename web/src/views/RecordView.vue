<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import * as runtime from "../legacy/runtime.js";
import { useI18nStore } from "../stores/i18n";
import { useShellStore } from "../stores/shell";
import RecordWorkspaceHeader from "../components/record/RecordWorkspaceHeader.vue";
import RecordReadingPane from "../components/record/RecordReadingPane.vue";
import RecordInspector from "../components/record/RecordInspector.vue";
import RecordEditSheet from "../components/record/RecordEditSheet.vue";
import type { RecordWorkspaceSnapshot } from "../types/record";

const i18n=useI18nStore();
const shell=useShellStore();
const route=useRoute();
const snapshot=ref<RecordWorkspaceSnapshot>({available:false,mode:"workspace"});
const loading=ref(true);
const error=ref("");
const editOpen=ref(false);
const inspectorCollapsed=ref(false);
const inspectorWidth=ref(Math.max(310,Math.min(440,Number(localStorage.getItem("derridai.record.inspectorWidth")||360)||360)));
const dragging=ref(false);
const annotationDialog=ref<HTMLDialogElement|null>(null);
const annotationQuote=ref("");
const annotationNote=ref("");
const annotationTags=ref("");
const annotationField=ref("text");
const annotationError=ref("");

const record=computed(()=>snapshot.value.record||{});
const work=computed(()=>String(record.value.work||record.value.document_title||i18n.t('record.untitled','Untitled record')));
const author=computed(()=>String(record.value.document_author||''));
const year=computed<string|number|null>(()=>{const value=record.value.publication_year??record.value.year??null;return typeof value==='string'||typeof value==='number'?value:null});
const positionLabel=computed(()=>snapshot.value.total&&snapshot.value.current_index!=null?i18n.tf('record.position_of','{current} of {total}',{current:snapshot.value.current_index+1,total:snapshot.value.total}):'');
const badges=computed(()=>{
  const out:Array<{text:string;tone?:string}>=[];
  if(record.value.region_type)out.push({text:String(record.value.region_type)});
  if(record.value.primary_text===false)out.push({text:i18n.t('record.secondary_text','Secondary text')});else if(record.value.primary_text===true)out.push({text:i18n.t('record.primary_text','Primary text')});
  if(record.value.document_is_translation)out.push({text:i18n.t('record.translation','Translation')});
  if(record.value.needs_review)out.push({text:i18n.t('record.needs_review','Needs review'),tone:'warn'});
  if(snapshot.value.mode==='database')out.push({text:i18n.t('record.database_record','Database record')});
  else if(snapshot.value.file_name)out.push({text:String(snapshot.value.file_name)});
  return out;
});

async function load(){
  loading.value=true;error.value='';
  try{snapshot.value=await runtime.getRecordWorkspaceSnapshot() as RecordWorkspaceSnapshot}
  catch(exc){error.value=exc instanceof Error?exc.message:String(exc)}
  finally{loading.value=false}
}
async function refreshAfter(action:()=>Promise<unknown>|unknown){try{await action();await load()}catch(exc){runtime.notifyToast(exc instanceof Error?exc.message:String(exc),{tone:'danger'})}}
async function previous(){await refreshAfter(()=>runtime.recordWorkspaceNavigate(-1))}
async function next(){await refreshAfter(()=>runtime.recordWorkspaceNavigate(1))}
function setFind(value:string){snapshot.value={...snapshot.value,find_query:value};runtime.setRecordWorkspaceFind(value)}
async function toggleEvidence(){await refreshAfter(()=>runtime.toggleCurrentRecordEvidence())}
async function toggleReview(){await refreshAfter(()=>runtime.toggleCurrentRecordReviewSelection())}
async function saveChanges(changes:Record<string,unknown>){await refreshAfter(()=>runtime.saveCurrentRecordChanges(changes));editOpen.value=false}
async function quickChange(changes:Record<string,unknown>){await refreshAfter(()=>runtime.saveCurrentRecordChanges(changes))}
function metadataSearch(field:string,value:string,contains=false){runtime.searchCurrentRecordMetadata(field,value,{contains})}
function openAnnotation(selection?:{field:string;quote:string}){annotationField.value=selection?.field||'text';annotationQuote.value=selection?.quote||'';annotationNote.value='';annotationTags.value='';annotationError.value='';void nextTick(()=>{if(annotationDialog.value&&!annotationDialog.value.open)annotationDialog.value.showModal();annotationDialog.value?.querySelector<HTMLTextAreaElement>('#recordAnnotationNote')?.focus()})}
function closeAnnotation(){annotationDialog.value?.close()}
async function saveAnnotation(){annotationError.value='';try{await runtime.addCurrentRecordAnnotation({field:annotationField.value,quote:annotationQuote.value,note:annotationNote.value,tags:annotationTags.value.split(',').map(v=>v.trim()).filter(Boolean)});closeAnnotation();await load()}catch(exc){annotationError.value=exc instanceof Error?exc.message:String(exc)}}
async function removeAnnotation(id:string){await refreshAfter(()=>runtime.removeCurrentRecordAnnotation(id))}
async function action(name:string,payload:Record<string,unknown>={}){await refreshAfter(()=>runtime.currentRecordPrimaryAction(name,payload))}
function startResize(event:PointerEvent){if(window.innerWidth<1180)return;dragging.value=true;(event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);document.body.classList.add('record-resizing');window.addEventListener('pointermove',resize);window.addEventListener('pointerup',stopResize,{once:true})}
function resize(event:PointerEvent){if(!dragging.value)return;const workspace=document.querySelector('.record-workspace-grid')?.getBoundingClientRect();if(!workspace)return;const width=Math.max(310,Math.min(440,workspace.right-event.clientX));inspectorWidth.value=width}
function stopResize(){dragging.value=false;document.body.classList.remove('record-resizing');window.removeEventListener('pointermove',resize);localStorage.setItem('derridai.record.inspectorWidth',String(Math.round(inspectorWidth.value)))}
function keyboardResize(event:KeyboardEvent){
  if(window.innerWidth<1180)return;
  let next=inspectorWidth.value;
  if(event.key==='ArrowLeft')next+=24;else if(event.key==='ArrowRight')next-=24;else if(event.key==='Home')next=310;else if(event.key==='End')next=440;else return;
  event.preventDefault();inspectorWidth.value=Math.max(310,Math.min(440,next));localStorage.setItem('derridai.record.inspectorWidth',String(Math.round(inspectorWidth.value)));
}

const activeFileId=computed(()=>shell.snapshot.files.find(file=>file.active)?.id||'');
watch([()=>route.fullPath,activeFileId,()=>shell.snapshot.activeStore],()=>{void load()});
watch(()=>i18n.locale,()=>{void load()});
function onRecordUpdated(){void load()}
onMounted(()=>{window.addEventListener('derridai:record-updated',onRecordUpdated);void load()});
onBeforeUnmount(()=>{window.removeEventListener('derridai:record-updated',onRecordUpdated);window.removeEventListener('pointermove',resize);document.body.classList.remove('record-resizing')});
</script>

<template>
  <main class="record-workspace-page" :aria-busy="loading">
    <div v-if="loading" class="record-workspace-loading"><span></span><strong>{{i18n.t('record.loading','Loading record…')}}</strong></div>
    <section v-else-if="error" class="record-workspace-empty"><h1>{{i18n.t('record.load_failed','Could not load record')}}</h1><p>{{error}}</p><button type="button" @click="load">{{i18n.t('ui.retry','Retry')}}</button></section>
    <section v-else-if="!snapshot.available" class="record-workspace-empty"><h1>{{i18n.t('record.no_record_selected','No record selected')}}</h1><p>{{snapshot.reason||i18n.t('record.no_record_help','Choose a record from Search, Works, or Records.')}}</p><div><button type="button" @click="runtime.navigateRecordWorkspace('global')">{{i18n.t('nav.search','Search')}}</button><button type="button" @click="runtime.navigateRecordWorkspace('works')">{{i18n.t('nav.works','Works')}}</button></div></section>
    <template v-else>
      <RecordWorkspaceHeader
        :work="work" :author="author" :year="year" :pages="snapshot.page_span||''" :record-id="snapshot.record_id||''" :position="positionLabel"
        :evidence-selected="snapshot.evidence_selected" :review-selected="snapshot.review_selected" :can-edit="snapshot.capabilities?.edit" :can-evidence="snapshot.capabilities?.evidence" :can-review="snapshot.capabilities?.review" :can-upsert="snapshot.capabilities?.upsert" :can-llm="snapshot.capabilities?.llm_review" :can-history="snapshot.capabilities?.history" :can-pdf="snapshot.capabilities?.pdf" :has-history="Boolean(snapshot.history_count)" :has-previous="snapshot.has_previous" :has-next="snapshot.has_next"
        @previous="previous" @next="next" @edit="editOpen=true" @evidence="toggleEvidence" @review="toggleReview" @copy-inline="runtime.copyCurrentRecordCitation('inline')" @copy-full="runtime.copyCurrentRecordCitation('full')" @copy-json="runtime.copyCurrentRecordJson()" @upsert="action('upsert')" @llm="action('llm')" @ocr="action('ocr')" @history="action('history')" @pdf="action('pdf_explorer')"
      />

      <div class="record-context-strip" :aria-label="i18n.t('record.status','Record status')">
        <span v-for="badge in badges" :key="badge.text" class="record-context-badge" :class="badge.tone">{{badge.text}}</span>
        <button v-if="snapshot.collection" type="button" class="record-context-link" @click="runtime.navigateRecordWorkspace('global')">{{i18n.t('record.collection','Collection')}}: {{snapshot.collection}}</button>
        <span class="record-context-spacer"></span>
        <button type="button" class="record-inspector-toggle" :aria-expanded="!inspectorCollapsed" @click="inspectorCollapsed=!inspectorCollapsed">{{inspectorCollapsed?i18n.t('record.show_inspector','Show inspector'):i18n.t('record.hide_inspector','Hide inspector')}}</button>
      </div>

      <section class="record-workspace-grid" :class="{'inspector-collapsed':inspectorCollapsed}" :style="{'--record-inspector-width':`${inspectorWidth}px`}">
        <RecordReadingPane :text="String(record.text||'')" :find-query="snapshot.find_query||''" :word-count="snapshot.word_count||0" :character-count="snapshot.character_count||0" :annotations="snapshot.annotations||[]" :can-annotate="snapshot.capabilities?.annotate" :summary-mode="snapshot.mode==='database'" @find="setFind" @annotate="openAnnotation"/>
        <div v-if="!inspectorCollapsed" class="record-inspector-resizer" role="separator" tabindex="0" aria-orientation="vertical" :aria-label="i18n.t('record.resize_inspector','Resize record inspector')" aria-valuemin="310" aria-valuemax="440" :aria-valuenow="Math.round(inspectorWidth)" @pointerdown="startResize" @keydown="keyboardResize"></div>
        <RecordInspector v-if="!inspectorCollapsed" :snapshot="snapshot" @search="metadataSearch" @change="quickChange" @add-annotation="openAnnotation()" @remove-annotation="removeAnnotation" @open-pdf="index=>action('open_pdf',{index})" @remove-pdf="index=>action('remove_pdf',{index})" @remove-all-pdf="action('remove_all_pdf')" @pdf-explorer="action('pdf_explorer')" @link-current-pdf="action('link_pdf')" @open-history="action('history')"/>
      </section>

      <RecordEditSheet :open="editOpen" :record="record" @close="editOpen=false" @save="saveChanges"/>

      <dialog ref="annotationDialog" class="record-annotation-dialog" aria-labelledby="recordAnnotationTitle" @cancel.prevent="closeAnnotation">
        <form method="dialog" @submit.prevent="saveAnnotation">
          <header><div><p>{{i18n.t('annotations.record_notes','Annotations')}}</p><h2 id="recordAnnotationTitle">{{i18n.t('annotations.add_note_tags','Add note / tags')}}</h2></div><button type="button" :aria-label="i18n.t('ui.close','Close')" @click="closeAnnotation">×</button></header>
          <div class="record-annotation-form">
            <blockquote v-if="annotationQuote">{{annotationQuote}}</blockquote>
            <label><span>{{i18n.t('annotations.note','Note')}}</span><textarea id="recordAnnotationNote" v-model="annotationNote" rows="5" :placeholder="i18n.t('annotations.note_placeholder','Add a note about this selection…')"></textarea></label>
            <label><span>{{i18n.t('annotations.tags','Tags')}}</span><input v-model="annotationTags" :placeholder="i18n.t('annotations.tags_placeholder','Comma-separated tags')"></label>
            <p v-if="annotationError" class="record-annotation-error" role="alert">{{annotationError}}</p>
          </div>
          <footer><button type="button" @click="closeAnnotation">{{i18n.t('ui.cancel','Cancel')}}</button><button type="submit" class="primary">{{i18n.t('annotations.save','Save annotation')}}</button></footer>
        </form>
      </dialog>
    </template>
  </main>
</template>

<style scoped>
.record-workspace-page{display:grid;gap:12px;padding:16px 18px 28px;max-width:1600px;margin:0 auto}.record-workspace-loading,.record-workspace-empty{min-height:360px;display:grid;place-items:center;align-content:center;gap:12px;text-align:center}.record-workspace-loading span{width:34px;height:34px;border:3px solid #dce5df;border-top-color:var(--ui-accent,#3c8d62);border-radius:50%;animation:record-spin .8s linear infinite}.record-workspace-empty h1{margin:0;font:600 26px/1.2 Georgia,"Times New Roman",serif}.record-workspace-empty p{max-width:600px;margin:0;color:#6d7989;line-height:1.55}.record-workspace-empty>div{display:flex;gap:8px}.record-workspace-empty button{min-height:38px;border:1px solid #d8e1dc;border-radius:9px;background:#fff;padding:0 12px;color:#355043;font-weight:800;cursor:pointer}.record-context-strip{min-height:38px;display:flex;align-items:center;gap:7px;flex-wrap:wrap;padding:0 4px}.record-context-badge,.record-context-link{display:inline-flex;width:auto;max-width:100%;min-height:28px;align-items:center;border:1px solid #dce5df;border-radius:999px;background:#f7faf8;padding:4px 9px;color:#53665a;font-size:11.5px;font-weight:750;white-space:normal;overflow-wrap:anywhere}.record-context-badge.warn{border-color:#eed8a6;background:#fff8e7;color:#815f1f}.record-context-link{cursor:pointer}.record-context-spacer{flex:1}.record-inspector-toggle{min-height:30px;border:0;background:transparent;padding:0 6px;color:#557064;font-size:11.5px;font-weight:800;cursor:pointer}.record-workspace-grid{position:relative;display:grid;grid-template-columns:minmax(0,1fr) 6px minmax(310px,var(--record-inspector-width,360px));gap:12px;align-items:start;min-width:0}.record-workspace-grid.inspector-collapsed{grid-template-columns:minmax(0,1fr)}.record-inspector-resizer{align-self:stretch;width:6px;min-height:460px;border:0;border-radius:999px;background:transparent;cursor:col-resize;position:relative}.record-inspector-resizer:after{content:"";position:absolute;left:3px;top:36px;bottom:36px;width:2px;border-radius:2px;background:#dce4df}.record-inspector-resizer:hover:after,.record-inspector-resizer:focus-visible:after{background:var(--ui-accent,#3c8d62)}.record-inspector-resizer:focus-visible{outline:3px solid color-mix(in srgb,var(--ui-accent,#3c8d62) 42%,#fff);outline-offset:1px}.record-annotation-dialog{width:min(560px,calc(100vw - 32px));max-width:none;border:0;border-radius:16px;padding:0;background:#fff;box-shadow:0 24px 80px rgba(15,23,42,.22)}.record-annotation-dialog::backdrop{background:rgba(15,23,42,.38);backdrop-filter:blur(2px)}.record-annotation-dialog header{display:flex;justify-content:space-between;gap:14px;align-items:start;padding:18px 20px;border-bottom:1px solid #e4e9e6}.record-annotation-dialog header p{margin:0;color:#5c7667;font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.07em}.record-annotation-dialog h2{margin:3px 0 0;font:600 21px/1.2 Georgia,"Times New Roman",serif}.record-annotation-dialog header button{width:36px;height:36px;border:1px solid #dce4df;border-radius:9px;background:#fff;font-size:20px;cursor:pointer}.record-annotation-form{display:grid;gap:14px;padding:18px 20px}.record-annotation-form blockquote{margin:0;padding:11px 12px;border-left:3px solid var(--ui-accent,#3c8d62);border-radius:0 8px 8px 0;background:#f7f9f8;color:#39483f;font:13px/1.55 Georgia,"Times New Roman",serif}.record-annotation-form label{display:grid;gap:6px}.record-annotation-form label span{color:#526258;font-size:11.5px;font-weight:800}.record-annotation-form textarea,.record-annotation-form input{width:100%;border:1px solid #d8e1dc;border-radius:9px;padding:9px 10px;font:13px/1.45 system-ui,sans-serif}.record-annotation-form textarea{resize:vertical}.record-annotation-error{margin:0;padding:9px 10px;border-radius:8px;background:#fff1f1;color:#9a3333;font-size:12px}.record-annotation-dialog footer{display:flex;justify-content:flex-end;gap:8px;padding:13px 20px;border-top:1px solid #e4e9e6;background:#fbfcfb}.record-annotation-dialog footer button{min-height:38px;border:1px solid #d7e0da;border-radius:9px;background:#fff;padding:0 12px;color:#385044;font-weight:800;cursor:pointer}.record-annotation-dialog footer .primary{border-color:var(--ui-accent,#3c8d62);background:var(--ui-accent,#3c8d62);color:#fff}button:focus-visible,textarea:focus-visible,input:focus-visible{outline:3px solid color-mix(in srgb,var(--ui-accent,#3c8d62) 42%,#fff);outline-offset:2px}@keyframes record-spin{to{transform:rotate(360deg)}}@media(max-width:1180px){.record-workspace-page{padding:12px 14px 26px}.record-workspace-grid{grid-template-columns:1fr;gap:14px}.record-inspector-resizer{display:none}}@media(max-width:640px){.record-workspace-page{padding:10px 9px 24px}}@media(prefers-reduced-motion:reduce){.record-workspace-loading span{animation:none}}
</style>
