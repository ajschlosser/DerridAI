<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { cleanupText, type TextCleanupRule } from '../domain/textCleanup';
import { useI18nStore } from '../stores/i18n';
import UiButton from './ui/UiButton.vue';
const props=defineProps<{text:string;recurringLines?:string[];documentTerms?:string[]} >();
const emit=defineEmits<{apply:[text:string];close:[]}>();
const i18n=useI18nStore();
const selected=ref<Set<TextCleanupRule>>(new Set(['page_numbers','repeated_short_lines','line_hyphenation','paragraph_lines','empty_lines','ocr_artifacts','whitespace']));
const title=ref<HTMLElement|null>(null);
const dialog=ref<HTMLElement|null>(null);
const priorActive=ref<HTMLElement|null>(null);
const result=computed(()=>cleanupText(props.text,selected.value,props.recurringLines||[],props.documentTerms||[]));
const rules:Array<{key:TextCleanupRule;label:string;help:string}>=[
 {key:'page_numbers',label:'pdf_corpus.cleanup_page_numbers',help:'pdf_corpus.cleanup_page_numbers_help'},
 {key:'repeated_short_lines',label:'pdf_corpus.cleanup_repeated_lines',help:'pdf_corpus.cleanup_repeated_lines_help'},
 {key:'line_hyphenation',label:'pdf_corpus.cleanup_hyphenation',help:'pdf_corpus.cleanup_hyphenation_help'},
 {key:'paragraph_lines',label:'pdf_corpus.cleanup_paragraph_lines',help:'pdf_corpus.cleanup_paragraph_lines_help'},
 {key:'empty_lines',label:'pdf_corpus.cleanup_empty_lines',help:'pdf_corpus.cleanup_empty_lines_help'},
 {key:'ocr_artifacts',label:'pdf_corpus.cleanup_ocr_artifacts',help:'pdf_corpus.cleanup_ocr_artifacts_help'},
 {key:'whitespace',label:'pdf_corpus.cleanup_whitespace',help:'pdf_corpus.cleanup_whitespace_help'},
];
function toggle(key:TextCleanupRule,checked:boolean){const next=new Set(selected.value);checked?next.add(key):next.delete(key);selected.value=next}
function focusables(){return dialog.value?Array.from(dialog.value.querySelectorAll<HTMLElement>('button:not([disabled]),input:not([disabled]),summary,[tabindex]:not([tabindex="-1"])')).filter(node=>node.offsetParent!==null):[]}
function keydown(event:KeyboardEvent){
 if(event.key==='Escape'){event.preventDefault();emit('close');return}
 if(event.key!=='Tab')return;const nodes=focusables();if(nodes.length<2)return;const first=nodes[0],last=nodes[nodes.length-1];
 if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
}
onMounted(()=>{priorActive.value=document.activeElement as HTMLElement|null;window.addEventListener('keydown',keydown);title.value?.focus({preventScroll:true})});
onBeforeUnmount(()=>{window.removeEventListener('keydown',keydown);priorActive.value?.focus?.({preventScroll:true})});
</script>
<template><Teleport to="body"><div class="cleanup-backdrop" @mousedown.self="emit('close')"><section ref="dialog" class="cleanup-dialog" role="dialog" aria-modal="true" aria-labelledby="cleanup-title" aria-describedby="cleanup-help">
<header><div><span class="eyebrow">{{i18n.t('pdf_corpus.text_cleanup_eyebrow','Reviewed text')}}</span><h2 id="cleanup-title" ref="title" tabindex="-1">{{i18n.t('pdf_corpus.text_cleanup_title','Clean extracted text')}}</h2><p id="cleanup-help">{{i18n.t('pdf_corpus.text_cleanup_help','Preview reversible cleanup of common extraction noise. The immutable extracted source is never changed.')}}</p></div><UiButton size="small" :label="i18n.t('ui.close','Close')" @click="emit('close')"/></header>
<div class="cleanup-body"><fieldset><legend>{{i18n.t('pdf_corpus.cleanup_rules','Cleanup options')}}</legend><label v-for="rule in rules" :key="rule.key"><input type="checkbox" :checked="selected.has(rule.key)" @change="toggle(rule.key,($event.target as HTMLInputElement).checked)"><span><b>{{i18n.t(rule.label,rule.key)}}</b><small>{{i18n.t(rule.help,'')}}</small></span></label></fieldset>
<section class="cleanup-summary" aria-live="polite"><b>{{i18n.tf('pdf_corpus.cleanup_change_count','{count} cleanup change(s) detected',{count:result.changes})}}</b><span v-if="result.removed.length">{{i18n.tf('pdf_corpus.cleanup_removed_count','{count} repeated/page-number line(s) would be removed',{count:result.removed.length})}}</span></section>
<div class="preview-grid"><section><h3>{{i18n.t('pdf_corpus.cleanup_before','Before')}}</h3><pre>{{text}}</pre></section><section><h3>{{i18n.t('pdf_corpus.cleanup_after','After')}}</h3><pre>{{result.text}}</pre></section></div>
<details v-if="result.removed.length"><summary>{{i18n.t('pdf_corpus.cleanup_removed_lines','Removed lines')}}</summary><ul><li v-for="(line,index) in result.removed.slice(0,30)" :key="`${line}-${index}`">{{line||'—'}}</li></ul></details></div>
<footer><span>{{i18n.t('pdf_corpus.cleanup_source_preserved','Original extracted text remains preserved for audit and comparison.')}}</span><div><UiButton :label="i18n.t('ui.cancel','Cancel')" @click="emit('close')"/><UiButton variant="primary" :label="i18n.t('pdf_corpus.apply_cleanup','Apply to reviewed text')" :disabled="result.text===text" @click="emit('apply',result.text)"/></div></footer>
</section></div></Teleport></template>
<style scoped>
.cleanup-backdrop{position:fixed;inset:0;z-index:32000;display:grid;place-items:center;padding:20px;background:rgb(15 23 42/.78);backdrop-filter:blur(6px)}.cleanup-dialog{width:min(1100px,calc(100vw - 28px));max-height:92vh;display:grid;grid-template-rows:auto minmax(0,1fr) auto;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:18px;box-shadow:0 32px 100px rgb(0 0 0/.42);overflow:hidden}.cleanup-dialog>header,.cleanup-dialog>footer{padding:18px 20px;background:var(--card);display:flex;justify-content:space-between;gap:16px}.cleanup-dialog>header{border-bottom:1px solid var(--line)}.cleanup-dialog>footer{border-top:1px solid var(--line);align-items:center}.cleanup-dialog h2{font-size:1.25rem;margin:3px 0}.cleanup-dialog header p{margin:5px 0 0;color:var(--muted);font-size:.875rem;line-height:1.5}.eyebrow{font-size:.8125rem;letter-spacing:.08em;text-transform:uppercase;font-weight:800;color:var(--muted)}.cleanup-body{overflow:auto;padding:18px 20px;display:grid;gap:16px}.cleanup-body fieldset{border:0;padding:0;margin:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.cleanup-body legend{font-weight:800;margin-bottom:8px}.cleanup-body label{display:flex;align-items:flex-start;gap:9px;padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--card)}.cleanup-body input{width:18px;height:18px;margin-top:2px}.cleanup-body label span{display:grid;gap:2px}.cleanup-body label small{font-size:.8125rem;color:var(--muted);line-height:1.4}.cleanup-summary{display:flex;gap:12px;flex-wrap:wrap;padding:10px 12px;background:var(--soft);border-radius:9px;font-size:.875rem}.preview-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.preview-grid section{min-width:0}.preview-grid h3{font-size:.9375rem;margin:0 0 6px}.preview-grid pre{margin:0;max-height:350px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--card);font:inherit;font-size:.875rem;line-height:1.55}.cleanup-body details{font-size:.875rem}.cleanup-body summary{min-height:40px;cursor:pointer;font-weight:750}.cleanup-dialog footer>span{color:var(--muted);font-size:.8125rem;line-height:1.4}.cleanup-dialog footer>div{display:flex;gap:8px}:is(button,input,summary):focus-visible{outline:3px solid var(--accent);outline-offset:2px}@media(max-width:760px){.cleanup-backdrop{padding:6px}.cleanup-dialog{width:100%;max-height:98vh;border-radius:12px}.cleanup-body fieldset,.preview-grid{grid-template-columns:1fr}.cleanup-dialog>header,.cleanup-dialog>footer{flex-direction:column;align-items:stretch}}
</style>
