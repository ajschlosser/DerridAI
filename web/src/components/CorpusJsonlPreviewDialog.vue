<script setup lang="ts">
import UiDialog from './ui/UiDialog.vue';
import UiButton from './ui/UiButton.vue';
import { useI18nStore } from '../stores/i18n';
const props=defineProps<{open:boolean;jsonl:string;validationErrors?:string[];unresolvedFields?:string[];wouldPublish?:boolean;busy?:boolean}>();
const emit=defineEmits<{close:[]}>();
const i18n=useI18nStore();
async function copy(){try{await navigator.clipboard.writeText(props.jsonl)}catch{/* browser permission */}}
function download(){const blob=new Blob([props.jsonl+'\n'],{type:'application/x-ndjson;charset=utf-8'});const href=URL.createObjectURL(blob);const a=document.createElement('a');a.href=href;a.download='record-preview.jsonl';a.click();URL.revokeObjectURL(href)}
</script>
<template>
<UiDialog :open="open" size="xlarge" :title="i18n.t('pdf_corpus.jsonl_preview_title')" :description="i18n.t('pdf_corpus.jsonl_preview_help')" :close-label="i18n.t('ui.close')" @close="emit('close')">
  <div class="preview-status" :data-ready="wouldPublish?'true':'false'" role="status">
    <b>{{wouldPublish?i18n.t('pdf_corpus.jsonl_ready'):i18n.t('pdf_corpus.jsonl_not_ready')}}</b>
    <span v-if="unresolvedFields?.length">{{i18n.tf('pdf_corpus.jsonl_unresolved', {count:unresolvedFields.length})}}: {{unresolvedFields.join(', ')}}</span>
    <span v-if="validationErrors?.length">{{i18n.tf('pdf_corpus.jsonl_validation_errors', {count:validationErrors.length})}}</span>
  </div>
  <ul v-if="validationErrors?.length" class="validation-list"><li v-for="item in validationErrors" :key="item">{{item}}</li></ul>
  <pre class="json-preview" tabindex="0" :aria-label="i18n.t('pdf_corpus.jsonl_preview_title')">{{jsonl}}</pre>
  <template #footer><span class="footer-note">{{i18n.t('pdf_corpus.jsonl_preview_exact')}}</span><div class="actions"><UiButton :label="i18n.t('pdf_corpus.copy_jsonl')" @click="copy"/><UiButton variant="primary" :label="i18n.t('pdf_corpus.download_jsonl_preview')" @click="download"/></div></template>
</UiDialog>
</template>
<style scoped>
.preview-status{display:grid;gap:4px;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--soft);font-size:.875rem;line-height:1.45}.preview-status[data-ready="true"]{border-color:var(--tone-ok-edge);background:var(--tone-ok-bg)}.validation-list{margin:0;padding-inline-start:22px;color:var(--warning,#7c5700);font-size:.875rem;line-height:1.45}.json-preview{margin:14px 0 0;max-height:58vh;overflow:auto;padding:14px;border:1px solid var(--line);border-radius:10px;background:var(--soft);white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace}.footer-note{font-size:.8125rem;color:var(--muted)}.actions{display:flex;gap:8px;flex-wrap:wrap}@media(max-width:700px){.actions{width:100%;flex-direction:column}}
</style>
