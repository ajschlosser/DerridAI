<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue';
import { useI18nStore } from '../stores/i18n';
import DocumentManifestEditor from './DocumentManifestEditor.vue';
import UiButton from './ui/UiButton.vue';
const props=withDefaults(defineProps<{manifest?:Record<string,unknown>;disabled?:boolean}>(),{manifest:()=>({}),disabled:false});
const emit=defineEmits<{save:[changes:Record<string,unknown>];close:[]}>();
const i18n=useI18nStore();
const titleEl=ref<HTMLElement|null>(null);
function keydown(event:KeyboardEvent){if(event.key==='Escape')emit('close')}
onMounted(()=>{window.addEventListener('keydown',keydown);titleEl.value?.focus({preventScroll:true})});
onBeforeUnmount(()=>window.removeEventListener('keydown',keydown));
</script>
<template><Teleport to="body"><div class="modal-backdrop" @mousedown.self="emit('close')"><section class="manifest-dialog" role="dialog" aria-modal="true" aria-labelledby="manifest-dialog-title"><header><div><h2 id="manifest-dialog-title" ref="titleEl" tabindex="-1">{{i18n.t('pdf_corpus.edit_document_metadata','Edit document metadata')}}</h2><p>{{i18n.t('pdf_corpus.document_metadata_dialog_help','Edit document-level defaults once. Records inherit these values unless they have an explicit human override.')}}</p></div><UiButton size="small" :label="i18n.t('ui.close','Close')" @click="emit('close')"/></header><div class="dialog-scroll"><DocumentManifestEditor :manifest="props.manifest" :disabled="props.disabled" @save="emit('save',$event)" /></div></section></div></Teleport></template>
<style scoped>.modal-backdrop{position:fixed;inset:0;z-index:1100;display:grid;place-items:center;padding:24px;background:rgba(15,23,42,.5)}.manifest-dialog{width:min(980px,calc(100vw - 32px));max-height:min(88vh,900px);display:grid;grid-template-rows:auto minmax(0,1fr);overflow:hidden;border:1px solid var(--line);border-radius:16px;background:var(--card);box-shadow:0 24px 80px rgba(15,23,42,.24)}header{display:flex;justify-content:space-between;gap:18px;padding:18px 20px;border-bottom:1px solid var(--line)}h2{margin:0;font-size:1.25rem}header p{margin:5px 0 0;color:var(--muted);font-size:.875rem;line-height:1.5}.dialog-scroll{overflow:auto;padding:18px 20px;overscroll-behavior:contain}@media(max-width:650px){.modal-backdrop{padding:8px}.manifest-dialog{width:100%;max-height:96vh}header{padding:14px}.dialog-scroll{padding:14px}}</style>
