<script setup lang="ts">
import PdfEvidenceViewer from './PdfEvidenceViewer.vue';
import { useI18nStore } from '../stores/i18n';
import type { SourceBlock } from '../api/pdfCorpus';
const props=withDefaults(defineProps<{pdfUrl?:string;page:number;pageCount?:number;pageWidth?:number;pageHeight?:number;blocks?:SourceBlock[];evidenceBlockIds?:string[];canPrevious?:boolean;canNext?:boolean;showPdfExplorer?:boolean}>(),{pdfUrl:'',pageCount:0,pageWidth:0,pageHeight:0,blocks:()=>[],evidenceBlockIds:()=>[],canPrevious:false,canNext:false,showPdfExplorer:true});
const emit=defineEmits<{openViewer:[];openPdfExplorer:[];previous:[];next:[]}>();
const i18n=useI18nStore();
</script>
<template>
<section class="source-summary" :aria-label="i18n.t('pdf_corpus.source_context','Source context')">
  <header class="source-summary-head">
    <div><b>{{i18n.t('pdf_corpus.source_context','Source context')}}</b><span>{{pageCount?i18n.tf('pdf_corpus.pdf_page_of','PDF page {page} of {total}',{page,total:pageCount}):i18n.tf('pdf_corpus.pdf_page','PDF page {page}',{page})}}</span></div>
  </header>
  <div v-if="pageCount>1" class="source-page-nav" :aria-label="i18n.t('pdf_corpus.source_page_navigation','Source page navigation')">
    <button type="button" class="btn small" :disabled="!canPrevious" @click="emit('previous')">← {{i18n.t('ui.previous','Previous')}}</button>
    <span aria-live="polite">{{page}} / {{pageCount}}</span>
    <button type="button" class="btn small" :disabled="!canNext" @click="emit('next')">{{i18n.t('ui.next','Next')}} →</button>
  </div>
  <div v-if="pdfUrl" class="source-thumbnail"><PdfEvidenceViewer :pdf-url="pdfUrl" :page="page" :page-width="pageWidth" :page-height="pageHeight" :blocks="blocks" :evidence-block-ids="evidenceBlockIds" /></div>
  <div v-else class="source-unavailable">{{i18n.t('pdf_corpus.source_loading_or_unavailable','Source blocks are loading or unavailable.')}}</div>
  <div class="source-summary-actions">
    <button type="button" class="btn primary" @click="emit('openViewer')">{{i18n.t('pdf_corpus.open_source_viewer','Open source viewer')}}</button>
    <button v-if="showPdfExplorer" type="button" class="btn" @click="emit('openPdfExplorer')">{{i18n.t('pdf_corpus.open_pdf_explorer','Open in PDF Explorer')}}</button>
  </div>
</section>
</template>
<style scoped>
.source-summary{min-width:0;display:grid;gap:10px;padding:12px;background:var(--card);border-bottom:1px solid var(--line)}.source-summary-head>div{display:flex;justify-content:space-between;gap:8px;align-items:baseline;flex-wrap:wrap}.source-summary-head span,.source-page-nav{color:var(--muted);font-size:.8125rem}.source-page-nav,.source-summary-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.source-page-nav{justify-content:space-between}.source-thumbnail{min-width:0;max-width:100%;overflow:hidden;border:1px solid var(--line);border-radius:9px;background:var(--soft)}.source-thumbnail :deep(.pdf-evidence-viewer){padding:8px;border-bottom:0}.source-thumbnail :deep(.page-stage){max-height:340px;overflow:hidden}.source-thumbnail :deep(canvas){max-height:340px;object-fit:contain}.source-thumbnail :deep(.viewer-caption){display:none}.source-summary-actions .btn{flex:1 1 140px;white-space:normal}.source-unavailable{padding:12px;border:1px dashed var(--line);border-radius:8px;color:var(--muted);font-size:.8125rem}.source-summary :is(button):focus-visible{outline:3px solid var(--accent);outline-offset:2px}
</style>
