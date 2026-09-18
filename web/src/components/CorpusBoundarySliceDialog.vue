<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { useI18nStore } from "../stores/i18n";

const props=defineProps<{text:string;canPrevious:boolean;canNext:boolean;busy?:boolean}>();
const emit=defineEmits<{close:[];slice:[direction:"previous"|"next",offset:number]}>();
const i18n=useI18nStore();
const textarea=ref<HTMLTextAreaElement|null>(null);
const offset=ref(Math.max(1,Math.min(props.text.length-1,Math.floor(props.text.length/2))));
const before=computed(()=>props.text.slice(0,offset.value).trim());
const after=computed(()=>props.text.slice(offset.value).trim());
function capture(){const el=textarea.value;if(!el)return;const next=Number(el.selectionStart||0);if(next>0&&next<props.text.length)offset.value=next}
function apply(direction:"previous"|"next"){if(offset.value<=0||offset.value>=props.text.length)return;emit('slice',direction,offset.value)}
onMounted(()=>void nextTick(()=>{textarea.value?.focus();textarea.value?.setSelectionRange(offset.value,offset.value)}));
</script>
<template>
<div class="slice-backdrop" role="presentation" @mousedown.self="emit('close')">
  <section class="slice-dialog" role="dialog" aria-modal="true" aria-labelledby="slice-title">
    <header><div><span class="eyebrow">{{i18n.t('pdf_corpus.boundary_edit','Boundary edit')}}</span><h2 id="slice-title">{{i18n.t('pdf_corpus.slice_record','Slice record')}}</h2><p>{{i18n.t('pdf_corpus.slice_record_help','Place the caret where this record should begin or end, then move the misplaced text to the neighboring record. Both records remain in review and the operation can be undone.')}}</p></div><button class="btn" type="button" @click="emit('close')">{{i18n.t('ui.close','Close')}}</button></header>
    <label class="slice-label"><span>{{i18n.t('pdf_corpus.slice_point','Slice point')}}</span><textarea ref="textarea" :value="text" readonly @click="capture" @keyup="capture" :aria-describedby="'slice-instructions'"></textarea></label>
    <p id="slice-instructions" class="instructions">{{i18n.t('pdf_corpus.slice_point_help','Click between characters to choose the boundary. The preview below shows what would move.')}}</p>
    <div class="preview-grid">
      <article><b>{{i18n.t('pdf_corpus.before_slice','Before slice')}}</b><p>{{before||'—'}}</p></article>
      <article><b>{{i18n.t('pdf_corpus.after_slice','After slice')}}</b><p>{{after||'—'}}</p></article>
    </div>
    <footer><button class="btn" type="button" :disabled="busy||!canPrevious||!before||!after" @click="apply('previous')">← {{i18n.t('pdf_corpus.move_before_previous','Move before slice to previous record')}}</button><button class="btn primary" type="button" :disabled="busy||!canNext||!before||!after" @click="apply('next')">{{i18n.t('pdf_corpus.move_after_next','Move after slice to next record')}} →</button></footer>
  </section>
</div>
</template>
<style scoped>
.slice-backdrop{position:fixed;inset:0;z-index:12000;background:rgba(15,23,42,.58);display:grid;place-items:center;padding:24px}.slice-dialog{width:min(960px,96vw);max-height:92vh;overflow:auto;background:var(--card);color:var(--text);border:1px solid var(--line);border-radius:14px;box-shadow:0 24px 70px rgba(0,0,0,.28);padding:18px;display:grid;gap:14px}.slice-dialog>header{display:flex;justify-content:space-between;gap:18px;align-items:flex-start}.slice-dialog h2{margin:2px 0 6px;font-size:1.25rem}.slice-dialog header p,.instructions{margin:0;color:var(--muted);font-size:.875rem;line-height:1.5}.eyebrow{font-size:.8125rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:800}.slice-label{display:grid;gap:7px;font-weight:750}.slice-label textarea{width:100%;min-height:260px;resize:vertical;padding:14px;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--text);font:16px/1.65 Georgia,serif}.preview-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.preview-grid article{border:1px solid var(--line);border-radius:10px;padding:11px;background:var(--soft);min-width:0}.preview-grid b{font-size:.875rem}.preview-grid p{margin:7px 0 0;max-height:140px;overflow:auto;white-space:pre-wrap;font-size:.875rem;line-height:1.5}.slice-dialog footer{display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap}.slice-dialog :is(button,textarea):focus-visible{outline:3px solid var(--accent);outline-offset:2px}@media(max-width:720px){.slice-backdrop{padding:10px}.preview-grid{grid-template-columns:1fr}.slice-dialog>header{flex-direction:column}.slice-dialog footer{flex-direction:column;align-items:stretch}}
</style>
