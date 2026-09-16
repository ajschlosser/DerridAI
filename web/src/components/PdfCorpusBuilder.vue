<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { pdfCorpusApi, type CorpusBuild, type CorpusRecord, type PdfAsset, type SourceBlock } from "../api/pdfCorpus";
import * as runtime from "../legacy/runtime.js";

const assets=ref<PdfAsset[]>([]);
const builds=ref<CorpusBuild[]>([]);
const buildsTotal=ref(0);
const selectedAssetId=ref("");
const selectedBuildId=ref("");
const currentBuild=ref<CorpusBuild|null>(null);
const records=ref<CorpusRecord[]>([]);
const recordTotal=ref(0);
const recordOffset=ref(0);
const pageSize=50;
const selectedRecordId=ref("");
const selectedRecord=ref<CorpusRecord|null>(null);
const sourceBlocks=ref<SourceBlock[]>([]);
const reviewOnly=ref(true);
const recordQuery=ref("");
const busy=ref("");
const error=ref("");
const notice=ref("");
const uploadInput=ref<HTMLInputElement|null>(null);
const buildProvider=ref<"ollama"|"openai">("ollama");
const buildModel=ref("");
const buildBaseUrl=ref("");
const buildApiKey=ref("");
const advancedOpen=ref(false);
const metadataDraft=ref("{}");
let pollTimer:number|undefined;

const selectedAsset=computed(()=>assets.value.find(item=>item.asset_id===selectedAssetId.value)||null);
const visibleBlocks=computed(()=>{
  const ids=new Set(selectedRecord.value?.source_block_ids||[]);
  return sourceBlocks.value.filter(block=>ids.has(block.block_id));
});
const canPublish=computed(()=>Boolean(currentBuild.value && ["ready","awaiting_review"].includes(currentBuild.value.status) && currentBuild.value.needs_review_count===0 && currentBuild.value.accepted_count===currentBuild.value.record_count && (currentBuild.value.validation as any)?.valid));
const buildRunning=computed(()=>Boolean(currentBuild.value && ["queued","running"].includes(currentBuild.value.status)));
const pageNumber=computed(()=>Math.floor(recordOffset.value/pageSize)+1);
const pageCount=computed(()=>Math.max(1,Math.ceil(recordTotal.value/pageSize)));

function formatDate(value?:string|null){if(!value)return "—";try{return new Intl.DateTimeFormat(undefined,{dateStyle:"medium",timeStyle:"short"}).format(new Date(value))}catch{return value}}
function statusLabel(build:CorpusBuild){return String(build.status||"unknown").replace(/_/g," ")}
function setMessage(message:string,tone:"error"|"notice"="notice"){if(tone==="error"){error.value=message;notice.value=""}else{notice.value=message;error.value=""}}
function recordMetadata(record:CorpusRecord){
  const source=new Set(["record_id","text","text_length","page_start","page_end","pdf_file","pdf_pages","source_asset_id","source_block_ids","source_spans","boundary_evidence","metadata_evidence","accepted","updates"]);
  return Object.fromEntries(Object.entries(record).filter(([key])=>!source.has(key)));
}

async function refreshAssets(){const result=await pdfCorpusApi.listAssets();assets.value=result.items;if(!selectedAssetId.value&&assets.value[0])selectedAssetId.value=assets.value[0].asset_id}
async function refreshBuilds(){const result=await pdfCorpusApi.listBuilds(0,100);builds.value=result.items;buildsTotal.value=result.total;if(!selectedBuildId.value&&builds.value[0])selectedBuildId.value=builds.value[0].build_id}
async function refreshBuild(){
  if(!selectedBuildId.value){currentBuild.value=null;return}
  try{currentBuild.value=await pdfCorpusApi.build(selectedBuildId.value)}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error");return}
  if(currentBuild.value?.asset_id&&!selectedAssetId.value)selectedAssetId.value=currentBuild.value.asset_id;
}
async function refreshRecords(reset=false){
  if(reset)recordOffset.value=0;
  if(!selectedBuildId.value){records.value=[];recordTotal.value=0;return}
  const result=await pdfCorpusApi.records(selectedBuildId.value,recordOffset.value,pageSize,reviewOnly.value,recordQuery.value);
  records.value=result.items;recordTotal.value=result.total;
  if(selectedRecordId.value){selectedRecord.value=records.value.find(row=>row.record_id===selectedRecordId.value)||null}
  if(!selectedRecord.value&&records.value[0])selectRecord(records.value[0]);
}
async function refreshBlocks(){
  if(!selectedAssetId.value||!selectedRecord.value?.source_block_ids?.length){sourceBlocks.value=[];return}
  const result=await pdfCorpusApi.blocks(selectedAssetId.value,0,Math.min(1000,selectedRecord.value.source_block_ids.length),selectedRecord.value.source_block_ids);sourceBlocks.value=result.items
}
async function refreshAll(){await Promise.all([refreshAssets(),refreshBuilds()]);await refreshBuild();await refreshRecords(true)}
function selectRecord(record:CorpusRecord){selectedRecordId.value=record.record_id;selectedRecord.value=record;metadataDraft.value=JSON.stringify(recordMetadata(record),null,2);void refreshBlocks()}

async function upload(file?:File|null){
  if(!file)return;
  busy.value="upload";setMessage("");
  try{const asset=await pdfCorpusApi.uploadAsset(file,"auto");await refreshAssets();selectedAssetId.value=asset.asset_id;await refreshBlocks();setMessage(`Source ingested: ${asset.page_count} pages · ${asset.block_count} source blocks${asset.ocr_pages?` · OCR on ${asset.ocr_pages} pages`:""}.`)}
  catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}
  finally{busy.value=""}
}
async function useCurrentPdf(){const file=(runtime.state as any)?.pdf?.file as File|undefined;if(!file){setMessage("Open a PDF in Explorer first, or choose a source PDF here.","error");return}await upload(file)}
async function startBuild(){
  if(!selectedAssetId.value)return;
  busy.value="build";setMessage("");
  try{
    const payload:Record<string,unknown>={asset_id:selectedAssetId.value,profile_id:"derrida-scholarly-v1",provider:buildProvider.value};
    if(buildModel.value.trim())payload.model=buildModel.value.trim();
    if(buildBaseUrl.value.trim())payload.base_url=buildBaseUrl.value.trim();
    if(buildApiKey.value)payload.api_key=buildApiKey.value;
    const build=await pdfCorpusApi.createBuild(payload);selectedBuildId.value=build.build_id;currentBuild.value=build;await refreshBuilds();startPolling();setMessage("Corpus build started. You can leave this page; progress is persisted server-side.")
  }catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}
  finally{busy.value=""}
}
function startPolling(){stopPolling();pollTimer=window.setInterval(async()=>{if(!selectedBuildId.value)return;await refreshBuild();if(!buildRunning.value){stopPolling();await refreshBuilds();await refreshRecords(true)}},1400)}
function stopPolling(){if(pollTimer!==undefined){clearInterval(pollTimer);pollTimer=undefined}}
async function chooseBuild(build:CorpusBuild){selectedBuildId.value=build.build_id;selectedAssetId.value=build.asset_id;selectedRecordId.value="";selectedRecord.value=null;sourceBlocks.value=[];await refreshBuild();await refreshRecords(true);if(buildRunning.value)startPolling()}
async function toggleAccept(){if(!currentBuild.value||!selectedRecord.value)return;busy.value="record";try{const row=await pdfCorpusApi.accept(currentBuild.value.build_id,selectedRecord.value.record_id,!selectedRecord.value.accepted);selectedRecord.value=row;await refreshBuild();await refreshRecords()}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function saveMetadata(){if(!currentBuild.value||!selectedRecord.value)return;let changes:Record<string,unknown>;try{changes=JSON.parse(metadataDraft.value)}catch{setMessage("Metadata must be a valid JSON object.","error");return}busy.value="record";try{const row=await pdfCorpusApi.patchMetadata(currentBuild.value.build_id,selectedRecord.value.record_id,changes);selectedRecord.value=row;metadataDraft.value=JSON.stringify(recordMetadata(row),null,2);await refreshBuild();await refreshRecords();setMessage("Metadata saved. Source-bound text and provenance were not modified.")}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function merge(direction:"previous"|"next"){if(!currentBuild.value||!selectedRecord.value)return;busy.value="record";try{await pdfCorpusApi.merge(currentBuild.value.build_id,selectedRecord.value.record_id,direction);selectedRecordId.value="";selectedRecord.value=null;await refreshBuild();await refreshRecords(true);setMessage(`Merged with ${direction} record; the merged boundary now requires review.`)}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function split(afterBlockId:string){if(!currentBuild.value||!selectedRecord.value)return;busy.value="record";try{await pdfCorpusApi.split(currentBuild.value.build_id,selectedRecord.value.record_id,afterBlockId);selectedRecordId.value="";selectedRecord.value=null;await refreshBuild();await refreshRecords(true);setMessage("Record split at the selected semantic source boundary. Both records require review.")}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function rerunMetadata(){if(!currentBuild.value||!selectedRecord.value)return;busy.value="record";try{const payload:Record<string,unknown>={provider:buildProvider.value};if(buildModel.value.trim())payload.model=buildModel.value.trim();if(buildBaseUrl.value.trim())payload.base_url=buildBaseUrl.value.trim();if(buildApiKey.value)payload.api_key=buildApiKey.value;const row=await pdfCorpusApi.rerunMetadata(currentBuild.value.build_id,selectedRecord.value.record_id,payload);selectedRecord.value=row;metadataDraft.value=JSON.stringify(recordMetadata(row),null,2);await refreshBuild();await refreshRecords();setMessage("Interpretive metadata rerun. Primary source text remained unchanged.")}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function publish(){if(!currentBuild.value)return;busy.value="publish";try{const result=await pdfCorpusApi.publish(currentBuild.value.build_id);await refreshBuild();await refreshBuilds();setMessage(`Published ${result.record_count} records · SHA-256 ${result.sha256.slice(0,12)}…`);window.location.href=pdfCorpusApi.publicationUrl(result.publication_id)}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function cancelBuild(){if(!currentBuild.value)return;await pdfCorpusApi.cancel(currentBuild.value.build_id);setMessage("Cancellation requested.");startPolling()}
async function previousPage(){if(recordOffset.value<=0)return;recordOffset.value=Math.max(0,recordOffset.value-pageSize);await refreshRecords()}
async function nextPage(){if(recordOffset.value+pageSize>=recordTotal.value)return;recordOffset.value+=pageSize;await refreshRecords()}

watch(selectedAssetId,()=>{sourceBlocks.value=[];if(selectedRecord.value)void refreshBlocks()});
watch([reviewOnly,recordQuery],()=>{void refreshRecords(true)});
onMounted(()=>{void refreshAll().then(()=>{if(buildRunning.value)startPolling()}).catch(exc=>setMessage(exc instanceof Error?exc.message:String(exc),"error"))});
onBeforeUnmount(stopPolling);
</script>

<template>
  <section class="corpus-builder" aria-label="PDF Corpus Builder">
    <header class="builder-header">
      <div>
        <span class="eyebrow">PDF Explorer · Corpus Builder</span>
        <h1>Build auditable records from source PDFs</h1>
        <p>Semantic boundaries are proposed by an LLM; source text, page provenance, IDs, validation, and publication remain deterministic.</p>
      </div>
      <div class="header-actions">
        <button class="btn" @click="useCurrentPdf" :disabled="busy!==''">Use current Explorer PDF</button>
        <button class="btn primary" @click="uploadInput?.click()" :disabled="busy!==''">{{busy==='upload'?'Extracting…':'Choose source PDF'}}</button>
        <input ref="uploadInput" class="sr-only" type="file" accept="application/pdf,.pdf" @change="upload(($event.target as HTMLInputElement).files?.[0])">
      </div>
    </header>

    <div v-if="error" class="builder-message error" role="alert">{{error}}</div>
    <div v-else-if="notice" class="builder-message" role="status">{{notice}}</div>

    <section class="builder-setup" aria-label="Build configuration">
      <div class="setup-source">
        <label>Source asset
          <select v-model="selectedAssetId" class="control">
            <option value="">Choose a persisted PDF…</option>
            <option v-for="asset in assets" :key="asset.asset_id" :value="asset.asset_id">{{asset.filename}} · {{asset.page_count}} pp · {{asset.block_count}} blocks</option>
          </select>
        </label>
        <small v-if="selectedAsset">SHA-256 {{selectedAsset.sha256.slice(0,16)}}… · {{selectedAsset.ocr_pages}} OCR page(s) · persisted {{formatDate(selectedAsset.created_at)}}</small>
      </div>
      <div class="setup-model">
        <label>Segmentation & metadata provider
          <select v-model="buildProvider" class="control"><option value="ollama">Ollama</option><option value="openai">OpenAI-compatible</option></select>
        </label>
        <label>Model <input v-model="buildModel" class="control" placeholder="Provider default"></label>
      </div>
      <details :open="advancedOpen" class="advanced-config" @toggle="advancedOpen=($event.currentTarget as HTMLDetailsElement).open">
        <summary>Advanced provider settings</summary>
        <div class="advanced-grid"><label>Base URL <input v-model="buildBaseUrl" class="control" placeholder="Provider default"></label><label>API key <input v-model="buildApiKey" class="control" type="password" autocomplete="off" placeholder="Not persisted in build manifest"></label></div>
      </details>
      <button class="btn primary build-button" @click="startBuild" :disabled="!selectedAssetId||busy!==''||buildRunning">{{busy==='build'?'Starting…':'Build record set'}}</button>
    </section>

    <div class="builder-workspace">
      <aside class="build-rail" aria-label="Corpus builds">
        <div class="rail-title"><div><b>Corpus builds</b><span>{{buildsTotal}} total</span></div><button class="icon-button" title="Refresh builds" @click="refreshBuilds">↻</button></div>
        <button v-for="build in builds" :key="build.build_id" class="build-row" :class="{active:build.build_id===selectedBuildId}" @click="chooseBuild(build)">
          <span class="status-dot" :data-status="build.status"></span>
          <span><b>{{build.source_filename||build.build_id}}</b><small>{{statusLabel(build)}} · {{build.record_count||0}} records</small><small>{{formatDate(build.created_at)}}</small></span>
        </button>
        <div v-if="!builds.length" class="rail-empty">No builds yet.</div>
      </aside>

      <main class="build-main">
        <section v-if="currentBuild" class="build-summary">
          <div class="summary-top">
            <div><span class="eyebrow">{{currentBuild.profile_id}}</span><h2>{{currentBuild.source_filename}}</h2><p>{{currentBuild.build_id}} · {{currentBuild.provider}} / {{currentBuild.model||'provider default'}}</p></div>
            <div class="summary-actions"><button v-if="buildRunning" class="btn" @click="cancelBuild">Cancel</button><a v-if="currentBuild.publication" class="btn" :href="pdfCorpusApi.publicationUrl(currentBuild.publication.publication_id)">Download JSONL</a><button class="btn primary" :disabled="!canPublish||busy!==''" @click="publish">{{busy==='publish'?'Publishing…':'Publish JSONL'}}</button></div>
          </div>
          <div class="build-status-line"><span class="pill" :data-status="currentBuild.status">{{statusLabel(currentBuild)}}</span><span>{{currentBuild.stage}}</span><span>{{Math.round((currentBuild.progress||0)*100)}}%</span><span>{{currentBuild.record_count}} records</span><span>{{currentBuild.needs_review_count}} need review</span><span>{{currentBuild.accepted_count}} accepted</span></div>
          <div class="progress-track" aria-label="Build progress"><span :style="{width:`${Math.round((currentBuild.progress||0)*100)}%`}"></span></div>
          <div v-if="currentBuild.error" class="builder-message error">{{currentBuild.error}}</div>
          <div class="provenance-strip"><span>Source <code>{{currentBuild.source_sha256?.slice(0,12)}}…</code></span><span>Schema {{currentBuild.schema_version}}</span><span>Segmentation {{currentBuild.segmentation_prompt_version}}</span><span>Metadata {{currentBuild.metadata_prompt_version}}</span><span v-if="currentBuild.validation?.coverage!==undefined">Coverage {{Math.round(Number(currentBuild.validation?.coverage)*10000)/100}}%</span></div>
        </section>

        <section v-if="currentBuild && !buildRunning" class="review-toolbar">
          <label class="check"><input v-model="reviewOnly" type="checkbox"> Needs review only</label>
          <input v-model="recordQuery" class="control" placeholder="Filter generated records…">
          <span>{{recordTotal}} matching records</span>
          <div class="pager"><button class="btn small" :disabled="recordOffset<=0" @click="previousPage">Previous</button><span>{{pageNumber}} / {{pageCount}}</span><button class="btn small" :disabled="recordOffset+pageSize>=recordTotal" @click="nextPage">Next</button></div>
        </section>

        <section v-if="currentBuild && !buildRunning" class="review-grid">
          <div class="source-pane">
            <div class="pane-head"><b>Source PDF</b><span v-if="selectedRecord">pp. {{selectedRecord.page_start}}–{{selectedRecord.page_end}}</span></div>
            <iframe v-if="currentBuild.asset_id" class="source-pdf" :src="pdfCorpusApi.assetContentUrl(currentBuild.asset_id)+'#page='+(selectedRecord?.page_start||1)" title="Source PDF"></iframe>
            <div v-if="selectedRecord" class="source-blocks">
              <article v-for="(block,index) in visibleBlocks" :key="block.block_id" class="source-block" :class="{'evidence-block':Object.values(selectedRecord.metadata_evidence||{}).some(info=>(info.block_ids||[]).includes(block.block_id))}">
                <header><span>{{block.block_id}} · p.{{block.page}} · {{block.type}}</span><span>{{block.extraction_method}} · {{Math.round(block.confidence*100)}}%</span></header>
                <p>{{block.text}}</p>
                <button v-if="index<visibleBlocks.length-1" class="split-button" @click="split(block.block_id)" :disabled="busy!==''">Split after this block</button>
              </article>
            </div>
          </div>

          <div class="records-pane">
            <div class="pane-head"><b>Generated records</b><span>{{recordOffset+1}}–{{Math.min(recordOffset+pageSize,recordTotal)}} of {{recordTotal}}</span></div>
            <button v-for="record in records" :key="record.record_id" class="record-row" :class="{active:record.record_id===selectedRecordId}" @click="selectRecord(record)">
              <span class="record-state" :data-state="record.needs_review?'review':record.accepted?'accepted':'ready'"></span>
              <span><b>{{record.record_id}}</b><small>pp. {{record.page_start}}–{{record.page_end}} · {{record.text_length.toLocaleString()}} chars</small><small>{{record.needs_review?(record.review_reason||'Needs review'):record.accepted?'Accepted':'Ready for acceptance'}}</small></span>
            </button>
            <div v-if="!records.length" class="rail-empty">No records match this review filter.</div>
          </div>

          <aside class="inspector-pane">
            <template v-if="selectedRecord">
              <div class="pane-head"><b>{{selectedRecord.record_id}}</b><span>{{selectedRecord.needs_review?'Needs review':selectedRecord.accepted?'Accepted':'Ready'}}</span></div>
              <div class="inspector-actions"><button class="btn small" @click="merge('previous')" :disabled="busy!==''">Merge previous</button><button class="btn small" @click="merge('next')" :disabled="busy!==''">Merge next</button><button class="btn small" @click="rerunMetadata" :disabled="busy!==''">Rerun metadata</button><button class="btn small primary" @click="toggleAccept" :disabled="busy!==''">{{selectedRecord.accepted?'Reopen':'Accept'}}</button></div>
              <details open><summary>Immutable source text</summary><div class="record-text">{{selectedRecord.text}}</div></details>
              <details open><summary>Interpretive metadata</summary><p class="help">Only model/human-owned metadata is editable here. Text, pages, source spans, and record IDs are protected server-side.</p><textarea v-model="metadataDraft" class="metadata-json" spellcheck="false"></textarea><button class="btn small" @click="saveMetadata" :disabled="busy!==''">Save metadata</button></details>
              <details open><summary>Field evidence</summary><div v-if="Object.keys(selectedRecord.metadata_evidence||{}).length" class="evidence-list"><div v-for="(info,field) in selectedRecord.metadata_evidence" :key="field"><b>{{field}}</b><span>{{Math.round(Number(info.confidence||0)*100)}}% · {{(info.block_ids||[]).join(', ')||'no source block bound'}}</span><small>{{info.reason}}</small></div></div><p v-else class="help">No field evidence recorded.</p></details>
            </template>
            <div v-else class="inspector-empty">Select a generated record to inspect its source binding and metadata.</div>
          </aside>
        </section>

        <section v-else-if="!currentBuild" class="builder-empty"><h2>No corpus build selected</h2><p>Persist a PDF source and start a semantic corpus build, or choose a historical build from the rail.</p></section>
      </main>
    </div>
  </section>
</template>

<style scoped>
.corpus-builder{padding:20px 22px 32px;display:grid;gap:14px}.builder-header{display:flex;justify-content:space-between;gap:24px;align-items:flex-end}.builder-header h1{font-size:26px;margin:3px 0 6px}.builder-header p{margin:0;max-width:850px;color:var(--muted);line-height:1.5}.eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);font-weight:700}.header-actions,.summary-actions,.inspector-actions,.pager{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.builder-message{padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--soft);font-size:12px}.builder-message.error{border-color:#c96b6b;background:#fff2f2;color:#7d2222}.builder-setup{display:grid;grid-template-columns:minmax(260px,1.5fr) minmax(300px,1fr) auto;gap:12px;align-items:end;border:1px solid var(--line);background:var(--card);border-radius:14px;padding:14px}.setup-source,.setup-model{display:grid;gap:6px}.setup-model{grid-template-columns:160px 1fr}.builder-setup label{display:grid;gap:5px;font-size:10px;font-weight:700;color:var(--muted)}.builder-setup small{font-size:9px;color:var(--muted)}.advanced-config{grid-column:1/-1}.advanced-config summary{cursor:pointer;font-size:10px;font-weight:700}.advanced-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px}.build-button{height:36px}.builder-workspace{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:720px;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--card)}.build-rail{border-right:1px solid var(--line);background:var(--soft);padding:10px;overflow:auto}.rail-title,.pane-head{display:flex;justify-content:space-between;align-items:center;gap:8px}.rail-title{padding:6px 4px 10px}.rail-title>div{display:grid}.rail-title b,.pane-head b{font-size:11px}.rail-title span,.pane-head span{font-size:9px;color:var(--muted)}.icon-button{border:0;background:transparent;cursor:pointer;font-size:18px}.build-row{width:100%;border:1px solid transparent;background:transparent;border-radius:10px;padding:9px;display:grid;grid-template-columns:10px 1fr;gap:9px;text-align:left;cursor:pointer}.build-row:hover,.build-row.active{background:var(--card);border-color:var(--line)}.build-row span:last-child{display:grid;gap:2px;min-width:0}.build-row b{font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.build-row small{font-size:8px;color:var(--muted)}.status-dot,.record-state{width:8px;height:8px;border-radius:50%;background:#999;margin-top:3px}.status-dot[data-status="ready"],.status-dot[data-status="published"],.record-state[data-state="accepted"]{background:#3a9c64}.status-dot[data-status="running"],.status-dot[data-status="queued"]{background:#cf9b2d}.status-dot[data-status="failed"],.record-state[data-state="review"]{background:#c65353}.build-main{min-width:0;display:grid;align-content:start}.build-summary{padding:15px 16px;border-bottom:1px solid var(--line);display:grid;gap:10px}.summary-top{display:flex;justify-content:space-between;gap:18px}.summary-top h2{margin:2px 0;font-size:18px}.summary-top p{margin:0;font-size:9px;color:var(--muted)}.build-status-line,.provenance-strip{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:9px;color:var(--muted)}.pill{border:1px solid var(--line);border-radius:999px;padding:3px 7px;text-transform:uppercase;font-weight:800;letter-spacing:.04em}.progress-track{height:5px;border-radius:999px;background:var(--soft);overflow:hidden}.progress-track span{display:block;height:100%;background:var(--accent);transition:width .25s}.provenance-strip code{font-size:8px}.review-toolbar{display:grid;grid-template-columns:auto minmax(180px,1fr) auto auto;gap:10px;align-items:center;padding:9px 12px;border-bottom:1px solid var(--line);font-size:9px}.check{display:flex;gap:6px;align-items:center}.review-grid{display:grid;grid-template-columns:minmax(360px,1.2fr) minmax(240px,.65fr) minmax(300px,.85fr);min-height:650px}.source-pane,.records-pane,.inspector-pane{min-width:0;overflow:auto;max-height:76vh}.source-pane,.records-pane{border-right:1px solid var(--line)}.pane-head{position:sticky;top:0;z-index:3;background:var(--card);padding:9px 11px;border-bottom:1px solid var(--line)}.source-pdf{width:100%;height:410px;border:0;border-bottom:1px solid var(--line)}.source-blocks{display:grid;gap:8px;padding:10px}.source-block{border:1px solid var(--line);border-radius:9px;padding:9px;position:relative}.source-block.evidence-block{box-shadow:inset 3px 0 0 var(--accent)}.source-block header{display:flex;justify-content:space-between;gap:8px;font-size:8px;color:var(--muted)}.source-block p{white-space:pre-wrap;font:13px/1.52 Georgia,serif;margin:7px 0}.split-button{display:block;width:100%;border:0;border-top:1px dashed var(--line);background:transparent;color:var(--muted);font-size:8px;padding:5px;cursor:pointer}.record-row{width:100%;border:0;border-bottom:1px solid var(--line);background:transparent;padding:10px;display:grid;grid-template-columns:10px 1fr;gap:8px;text-align:left;cursor:pointer}.record-row:hover,.record-row.active{background:var(--soft)}.record-row span:last-child{display:grid;gap:3px}.record-row b{font-size:10px}.record-row small{font-size:8px;color:var(--muted)}.inspector-pane details{border-bottom:1px solid var(--line);padding:10px 12px}.inspector-pane summary{font-size:10px;font-weight:800;cursor:pointer}.inspector-actions{padding:9px 11px;border-bottom:1px solid var(--line)}.record-text{white-space:pre-wrap;font:13px/1.55 Georgia,serif;margin-top:9px}.metadata-json{width:100%;min-height:230px;resize:vertical;font:10px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;border:1px solid var(--line);border-radius:8px;padding:8px;background:var(--bg);color:var(--text);margin:7px 0}.help{font-size:9px;color:var(--muted);line-height:1.45}.evidence-list{display:grid;gap:8px;margin-top:8px}.evidence-list>div{display:grid;gap:2px;padding:7px;background:var(--soft);border-radius:7px}.evidence-list b{font-size:9px}.evidence-list span,.evidence-list small{font-size:8px;color:var(--muted)}.rail-empty,.inspector-empty,.builder-empty{padding:26px 14px;color:var(--muted);font-size:10px}.builder-empty{min-height:420px;display:grid;place-content:center;text-align:center}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
@media(max-width:1250px){.review-grid{grid-template-columns:1fr .72fr}.inspector-pane{grid-column:1/-1;border-top:1px solid var(--line);max-height:none}.source-pane,.records-pane{max-height:65vh}}@media(max-width:900px){.builder-header{align-items:flex-start;flex-direction:column}.builder-setup{grid-template-columns:1fr}.setup-model,.advanced-grid{grid-template-columns:1fr}.advanced-config{grid-column:auto}.builder-workspace{grid-template-columns:1fr}.build-rail{border-right:0;border-bottom:1px solid var(--line);max-height:220px}.review-toolbar{grid-template-columns:1fr 1fr}.review-grid{grid-template-columns:1fr}.source-pane,.records-pane{border-right:0;border-bottom:1px solid var(--line);max-height:none}.source-pdf{height:55vh}}
</style>
