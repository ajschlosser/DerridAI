<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import PdfWorkerUrl from "pdfjs-dist/legacy/build/pdf.worker.mjs?url";
import { useI18nStore } from "../stores/i18n";
import type { SourceBlock } from "../api/pdfCorpus";

pdfjsLib.GlobalWorkerOptions.workerSrc = PdfWorkerUrl;
const props=withDefaults(defineProps<{pdfUrl:string;page:number;pageWidth?:number;pageHeight?:number;blocks?:SourceBlock[];evidenceBlockIds?:string[]}>(),{pageWidth:0,pageHeight:0,blocks:()=>[],evidenceBlockIds:()=>[]});
const i18n=useI18nStore(); const canvas=ref<HTMLCanvasElement|null>(null); const shell=ref<HTMLElement|null>(null); const loading=ref(false); const error=ref("");
let loadingTask:pdfjsLib.PDFDocumentLoadingTask|null=null; let pdfDocument:pdfjsLib.PDFDocumentProxy|null=null; let renderTask:pdfjsLib.RenderTask|null=null; let documentGeneration=0; let renderGeneration=0; let resizeObserver:ResizeObserver|null=null;
const pageBlocks=computed(()=>props.blocks.filter(block=>Number(block.page)===Number(props.page))); const evidenceSet=computed(()=>new Set(props.evidenceBlockIds.map(String)));
function boxStyle(block:SourceBlock){const [x0=0,y0=0,x1=0,y1=0]=block.bbox||[];const width=Number(props.pageWidth||0),height=Number(props.pageHeight||0);if(!width||!height)return {display:"none"};return {insetInlineStart:`${Math.max(0,Math.min(100,(x0/width)*100))}%`,top:`${Math.max(0,Math.min(100,(y0/height)*100))}%`,width:`${Math.max(0,Math.min(100,((x1-x0)/width)*100))}%`,height:`${Math.max(0,Math.min(100,((y1-y0)/height)*100))}%`}}
async function cancelRender(){const active=renderTask;renderTask=null;if(active){try{active.cancel?.();await active.promise}catch(exc:unknown){if(!(exc instanceof Error && exc.name==="RenderingCancelledException"))throw exc}}}
// eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
async function destroyDocument(){documentGeneration+=1;renderGeneration+=1;await cancelRender().catch(()=>{});const task=loadingTask;const doc=pdfDocument;loadingTask=null;pdfDocument=null;if(task){try{await task.destroy?.()}catch{}}else if(doc){try{await doc.destroy?.()}catch{}}}
async function loadDocument(){await destroyDocument();const token=++documentGeneration;if(!props.pdfUrl)return;error.value="";loading.value=true;try{const task=pdfjsLib.getDocument({url:props.pdfUrl,withCredentials:true});loadingTask=task;const doc=await task.promise;if(token!==documentGeneration){await doc.destroy?.();return}pdfDocument=doc;await nextTick();await renderPage()}catch(exc:unknown){if(token===documentGeneration)error.value=exc instanceof Error?exc.message:String(exc)}finally{if(token===documentGeneration)loading.value=false}}
async function renderPage(){const token=++renderGeneration;error.value="";if(!pdfDocument||!canvas.value)return;loading.value=true;try{await cancelRender();const safePage=Math.min(Math.max(1,Number(props.page)||1),pdfDocument.numPages);const page=await pdfDocument.getPage(safePage);if(token!==renderGeneration)return;const available=Math.max(160,Math.min(900,shell.value?.clientWidth||700));const base=page.getViewport({scale:1});const viewport=page.getViewport({scale:available/base.width});const outputScale=Math.min(2,window.devicePixelRatio||1);const node=canvas.value;if(!node)return;node.width=Math.floor(viewport.width*outputScale);node.height=Math.floor(viewport.height*outputScale);node.style.width=`${Math.floor(viewport.width)}px`;node.style.height=`${Math.floor(viewport.height)}px`;const context=node.getContext("2d");if(!context)throw new Error("Canvas 2D context is unavailable.");const active=page.render({canvasContext:context,viewport,transform:outputScale===1?undefined:[outputScale,0,0,outputScale,0,0]});renderTask=active;await active.promise;if(renderTask===active)renderTask=null}catch(exc:unknown){if(!(exc instanceof Error && exc.name==="RenderingCancelledException")&&token===renderGeneration)error.value=exc instanceof Error?exc.message:String(exc)}finally{if(token===renderGeneration)loading.value=false}}
watch(()=>props.pdfUrl,()=>void loadDocument(),{immediate:true});watch(()=>props.page,()=>void nextTick(renderPage));onMounted(()=>{if(typeof ResizeObserver!=="undefined"&&shell.value){let timer:number|undefined;resizeObserver=new ResizeObserver(()=>{window.clearTimeout(timer);timer=window.setTimeout(()=>void renderPage(),80)});resizeObserver.observe(shell.value)}});onBeforeUnmount(async()=>{resizeObserver?.disconnect();resizeObserver=null;await destroyDocument()});
</script>

<template>
  <section ref="shell" class="pdf-evidence-viewer" :aria-label="i18n.t('pdf_corpus.source_pdf','Source PDF')">
    <div v-if="loading" class="viewer-state" role="status" aria-live="polite">{{i18n.t('pdf_corpus.pdf_loading','Rendering source page…')}}</div>
    <div v-if="error" class="viewer-state error" role="alert">{{i18n.tf('pdf_corpus.pdf_render_error','Could not render the source page: {error}',{error})}}</div>
    <div class="page-stage" :aria-busy="loading?'true':'false'">
      <canvas ref="canvas" :aria-label="i18n.tf('pdf_corpus.pdf_page_canvas','PDF page {page}',{page})"></canvas>
      <div class="block-overlay" aria-hidden="true">
        <span v-for="block in pageBlocks" :key="block.block_id" class="source-box" :class="{evidence:evidenceSet.has(block.block_id)}" :style="boxStyle(block)"></span>
      </div>
    </div>
    <p class="viewer-caption">{{i18n.tf('pdf_corpus.pdf_highlight_help','Page {page}. Highlighted boxes show the source blocks bound to the selected evidence field.',{page})}}</p>
  </section>
</template>

<style scoped>
.pdf-evidence-viewer{display:grid;gap:6px;padding:10px;background:var(--soft);border-bottom:1px solid var(--line)}.page-stage{position:relative;justify-self:center;max-width:100%;line-height:0;background:var(--card);box-shadow:0 1px 8px rgb(0 0 0 / .12)}canvas{display:block;max-width:100%;height:auto}.block-overlay{position:absolute;inset:0;pointer-events:none}.source-box{position:absolute;border:1px solid color-mix(in srgb,var(--accent) 38%,transparent);background:color-mix(in srgb,var(--accent) 7%,transparent);border-radius:2px}.source-box.evidence{border:2px solid var(--accent);background:color-mix(in srgb,var(--accent) 20%,transparent);box-shadow:0 0 0 1px color-mix(in srgb,var(--card) 80%,transparent)}.viewer-state{padding:7px 9px;border:1px solid var(--line);border-radius:7px;background:var(--card);font-size:.8125rem}.viewer-state.error{border-color:var(--tone-danger-border);color:var(--tone-danger-fg)}.viewer-caption{margin:0;font-size:.8125rem;color:var(--muted);line-height:1.4}@media(prefers-reduced-motion:reduce){.source-box{transition:none}}
</style>
