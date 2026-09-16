<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { pdfCorpusApi, type CorpusBuild, type CorpusRecord, type PdfAsset, type SourceBlock } from "../api/pdfCorpus";
import { systemApi, type ProviderProfile } from "../api/system";
import { useI18nStore } from "../stores/i18n";
import ProviderProfileSelect from "./ProviderProfileSelect.vue";
import CorpusBuildProgress from "./CorpusBuildProgress.vue";
import FieldEvidenceList from "./FieldEvidenceList.vue";
import PdfEvidenceViewer from "./PdfEvidenceViewer.vue";
import PdfPageLabelEditor from "./PdfPageLabelEditor.vue";
import DocumentManifestEditor from "./DocumentManifestEditor.vue";
import * as runtime from "../legacy/runtime.js";

const i18n=useI18nStore();
const assets=ref<PdfAsset[]>([]);
const builds=ref<CorpusBuild[]>([]);
const buildsTotal=ref(0);
const providerProfiles=ref<ProviderProfile[]>([]);
const serverProviderIds=ref<Set<string>>(new Set());
const selectedProviderId=ref("");
const selectedReviewProviderId=ref("");
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
const selectedEvidenceField=ref("");
const selectedPdfPage=ref(1);
const reviewOnly=ref(true);
const recordQuery=ref("");
const busy=ref("");
const error=ref("");
const notice=ref("");
const uploadInput=ref<HTMLInputElement|null>(null);
const statusRegion=ref<HTMLElement|null>(null);
const manualProvider=ref<"ollama"|"openai">("ollama");
const manualModel=ref("");
const manualBaseUrl=ref("");
const manualApiKey=ref("");
const advancedOpen=ref(false);
const metadataDraft=ref("{}");
let pollTimer:number|undefined;

const selectedAsset=computed(()=>assets.value.find(item=>item.asset_id===selectedAssetId.value)||null);
const evidenceBlockIds=computed(()=>{
  if(!selectedRecord.value)return new Set<string>();
  if(selectedEvidenceField.value){
    const info=selectedRecord.value.metadata_evidence?.[selectedEvidenceField.value];
    return new Set((info?.block_ids||[]).map(String));
  }
  return new Set(Object.values(selectedRecord.value.metadata_evidence||{}).flatMap(info=>(info.block_ids||[]).map(String)));
});
const evidenceCandidateFields=computed(()=>{
  const record=selectedRecord.value;
  if(!record)return [];
  const candidates=["speaker","position_holder","target","stance","proposition_status","quoted_speaker","quoted_author","quoted_work","quoted_position_holder","quoted_addressee","quoted_referent","quotation_chain"];
  return candidates.filter(field=>{const value=record[field];return Array.isArray(value)?value.length>0:value!==null&&value!==undefined&&value!==""});
});
const visibleBlocks=computed(()=>{
  const ids=new Set(selectedRecord.value?.source_block_ids||[]);
  return sourceBlocks.value.filter(block=>ids.has(block.block_id));
});
const canPublish=computed(()=>Boolean(currentBuild.value && ["ready","awaiting_review"].includes(currentBuild.value.status) && currentBuild.value.needs_review_count===0 && currentBuild.value.accepted_count===currentBuild.value.record_count && currentBuild.value.validation?.valid));
const buildRunning=computed(()=>Boolean(currentBuild.value && ["queued","running"].includes(currentBuild.value.status)));
const canResume=computed(()=>Boolean(currentBuild.value?.resumable && ["failed","interrupted","cancelled"].includes(String(currentBuild.value.status))));
const pageNumber=computed(()=>Math.floor(recordOffset.value/pageSize)+1);
const pageCount=computed(()=>Math.max(1,Math.ceil(recordTotal.value/pageSize)));
const sourcePdfUrl=computed(()=>selectedAssetId.value?pdfCorpusApi.assetContentUrl(selectedAssetId.value):"");
const recordPdfPages=computed(()=>Array.from(new Set((selectedRecord.value?.pdf_pages||[]).map(Number).filter(value=>value>0))).sort((a,b)=>a-b));
const selectedPdfPageIndex=computed(()=>Math.max(0,recordPdfPages.value.indexOf(selectedPdfPage.value)));
const selectedPageMeta=computed(()=>selectedAsset.value?.pages?.find(page=>Number(page.pdf_page)===Number(selectedPdfPage.value))||null);
const selectedPageBlocks=computed(()=>visibleBlocks.value.filter(block=>Number(block.page)===Number(selectedPdfPage.value)));
const evidenceIdsArray=computed(()=>Array.from(evidenceBlockIds.value));
function directProfilePayload(profileId:string){
  const config=(runtime as any).getProviderRequestConfigForUi?.(profileId,{textReview:false}) as Record<string,unknown>|null;
  if(!config)return null;
  const ollama=config.ollama;
  return {
    provider_profile_id:profileId,
    provider:config.provider,
    model:config.model,
    base_url:config.base_url,
    api_key:config.api_key,
    generation:ollama&&typeof ollama==="object"?ollama:undefined,
  };
}
const providerPayload=computed<Record<string,unknown>>(()=>{
  if(selectedProviderId.value){
    const primary=directProfilePayload(selectedProviderId.value)||{provider_profile_id:selectedProviderId.value};
    const payload:Record<string,unknown>={...primary};
    // A server-owned researcher profile can be resolved by id alone. Browser-owned
    // administrator profiles include their explicit connection settings so the PDF
    // build does not depend on the separate Researcher Profiles allow-list.
    if(serverProviderIds.value.has(selectedProviderId.value)){
      for(const key of ["provider","model","base_url","api_key","generation"])delete payload[key];
    }
    if(selectedReviewProviderId.value&&selectedReviewProviderId.value!==selectedProviderId.value){
      payload.review_provider_profile_id=selectedReviewProviderId.value;
      if(!serverProviderIds.value.has(selectedReviewProviderId.value)){
        const review=directProfilePayload(selectedReviewProviderId.value);
        if(review){
          const {provider_profile_id: _profileId,...reviewConfig}=review;
          payload.review_provider=reviewConfig;
        }
      }
    }
    return payload;
  }
  const payload:Record<string,unknown>={provider:manualProvider.value};
  if(manualModel.value.trim())payload.model=manualModel.value.trim();
  if(manualBaseUrl.value.trim())payload.base_url=manualBaseUrl.value.trim();
  if(manualApiKey.value)payload.api_key=manualApiKey.value;
  return payload;
});

function formatDate(value?:string|null){if(!value)return "—";try{return new Intl.DateTimeFormat(i18n.locale||undefined,{dateStyle:"medium",timeStyle:"short"}).format(new Date(value))}catch{return value}}
function statusLabel(build:CorpusBuild){return i18n.t(`pdf_corpus.status.${String(build.status||"unknown")}`,String(build.status||"unknown").replace(/_/g," "))}
function setMessage(message:string,tone:"error"|"notice"="notice"){if(tone==="error"){error.value=message;notice.value=""}else{notice.value=message;error.value=""};void nextTick(()=>statusRegion.value?.focus())}
function recordMetadata(record:CorpusRecord){
  const protectedFields=new Set([
    "record_id","record_revision","text","text_length","page_start","page_end","pdf_file","pdf_pages","source_asset_id","source_block_ids","source_spans","boundary_evidence","metadata_evidence","accepted","updates","metadata_complete",
    "work","document_title","short_title","original_title","canonical_work_id","document_author","translator","edition","year","publication_year","publisher","publication_place","isbn","document_language","original_language","document_is_translation",
    "primary_text","inline_citation","full_citation","attribution_confidence","semantic_classification_confidence","extraction_quality"
  ]);
  return Object.fromEntries(Object.entries(record).filter(([key])=>!protectedFields.has(key)));
}
function manageProviders(){window.dispatchEvent(new CustomEvent("derridai:navigate-native",{detail:{path:"/providers",legacyView:"providers"}}))}

async function refreshProviders(){
  const runtimeProfiles=((runtime as any).getProviderProfilesForUi?.()||[]) as ProviderProfile[];
  let serverProfiles:ProviderProfile[]=[];
  try{serverProfiles=(await systemApi.researcherProviders()).profiles||[]}catch{serverProfiles=[]}
  serverProviderIds.value=new Set(serverProfiles.map(profile=>profile.id));
  const merged=new Map<string,ProviderProfile>();
  // Runtime profiles are the source of truth for administrators; researcher
  // profiles from the server fill in when the native view mounts before legacy
  // runtime bootstrap has completed. Prefer the richer runtime copy on conflicts.
  for(const profile of serverProfiles)merged.set(profile.id,profile);
  for(const profile of runtimeProfiles)merged.set(profile.id,profile);
  providerProfiles.value=Array.from(merged.values());
  const defaultId=String((runtime as any).getDefaultProviderProfileId?.()||"");
  if(!providerProfiles.value.some(profile=>profile.id===selectedProviderId.value)){
    selectedProviderId.value=providerProfiles.value.find(profile=>profile.id===defaultId)?.id||providerProfiles.value[0]?.id||"";
  }
}
async function refreshAssets(){const result=await pdfCorpusApi.listAssets();assets.value=result.items;if(!selectedAssetId.value&&assets.value[0])selectedAssetId.value=assets.value[0].asset_id}
async function refreshBuilds(){const result=await pdfCorpusApi.listBuilds(0,100);builds.value=result.items;buildsTotal.value=result.total;if(!selectedBuildId.value&&builds.value[0])selectedBuildId.value=builds.value[0].build_id}
async function refreshBuild(){if(!selectedBuildId.value){currentBuild.value=null;return}try{currentBuild.value=await pdfCorpusApi.build(selectedBuildId.value)}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error");return}if(currentBuild.value?.asset_id)selectedAssetId.value=currentBuild.value.asset_id;const request=currentBuild.value?.request||{};if(typeof request.provider_profile_id==="string"&&providerProfiles.value.some(profile=>profile.id===request.provider_profile_id))selectedProviderId.value=request.provider_profile_id;if(typeof request.review_provider_profile_id==="string"&&providerProfiles.value.some(profile=>profile.id===request.review_provider_profile_id))selectedReviewProviderId.value=request.review_provider_profile_id}
async function refreshRecords(reset=false){if(reset)recordOffset.value=0;if(!selectedBuildId.value){records.value=[];recordTotal.value=0;return}const result=await pdfCorpusApi.records(selectedBuildId.value,recordOffset.value,pageSize,reviewOnly.value,recordQuery.value);records.value=result.items;recordTotal.value=result.total;if(selectedRecordId.value)selectedRecord.value=records.value.find(row=>row.record_id===selectedRecordId.value)||null;if(!selectedRecord.value&&records.value[0])selectRecord(records.value[0])}
async function refreshBlocks(){if(!selectedAssetId.value||!selectedRecord.value?.source_block_ids?.length){sourceBlocks.value=[];return}const result=await pdfCorpusApi.blocks(selectedAssetId.value,0,Math.min(1000,selectedRecord.value.source_block_ids.length),selectedRecord.value.source_block_ids);sourceBlocks.value=result.items}
async function refreshAll(){await Promise.all([refreshProviders(),refreshAssets(),refreshBuilds()]);await refreshBuild();await refreshRecords(true)}
function selectRecord(record:CorpusRecord){selectedRecordId.value=record.record_id;selectedRecord.value=record;selectedEvidenceField.value="";selectedPdfPage.value=Number(record.pdf_pages?.[0]||1);metadataDraft.value=JSON.stringify(recordMetadata(record),null,2);void refreshBlocks()}


function previousSourcePage(){if(selectedPdfPageIndex.value>0)selectedPdfPage.value=recordPdfPages.value[selectedPdfPageIndex.value-1]}
function nextSourcePage(){if(selectedPdfPageIndex.value<recordPdfPages.value.length-1)selectedPdfPage.value=recordPdfPages.value[selectedPdfPageIndex.value+1]}

async function upload(file?:File|null){if(!file)return;busy.value="upload";setMessage("");try{const asset=await pdfCorpusApi.uploadAsset(file,"auto");await refreshAssets();selectedAssetId.value=asset.asset_id;setMessage(i18n.tf("pdf_corpus.source_ingested","Source ingested: {pages} pages · {blocks} source blocks · OCR on {ocr} pages.",{pages:asset.page_count,blocks:asset.block_count,ocr:asset.ocr_pages||0}))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function savePageLabels(labels:Record<number,string|null>){if(!selectedAssetId.value||!Object.keys(labels).length)return;busy.value="page-labels";try{const asset=await pdfCorpusApi.updatePageLabels(selectedAssetId.value,labels);assets.value=assets.value.map(item=>item.asset_id===asset.asset_id?asset:item);setMessage(i18n.t("pdf_corpus.page_mapping_saved","Printed-page overrides saved. New corpus builds will use the corrected labels."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}

async function useCurrentPdf(){const file=(runtime.state as any)?.pdf?.file as File|undefined;if(!file){setMessage(i18n.t("pdf_corpus.open_pdf_first","Open a PDF in Explorer first, or choose a source PDF here."),"error");return}await upload(file)}
async function startBuild(){if(!selectedAssetId.value)return;busy.value="build";setMessage("");try{const payload={asset_id:selectedAssetId.value,profile_id:"derrida-scholarly-v2",...providerPayload.value};const build=await pdfCorpusApi.createBuild(payload);selectedBuildId.value=build.build_id;currentBuild.value=build;await refreshBuilds();startPolling();setMessage(i18n.t("pdf_corpus.build_started","Corpus build started. Progress and completed checkpoints are persisted server-side."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function resumeBuild(){if(!currentBuild.value)return;busy.value="build";try{currentBuild.value=await pdfCorpusApi.resume(currentBuild.value.build_id,providerPayload.value);startPolling();setMessage(i18n.t("pdf_corpus.build_resumed","Build resumed from its last completed checkpoint."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
function startPolling(){stopPolling();pollTimer=window.setInterval(async()=>{if(!selectedBuildId.value)return;await refreshBuild();if(!buildRunning.value){stopPolling();await refreshBuilds();await refreshRecords(true)}},1400)}
function stopPolling(){if(pollTimer!==undefined){clearInterval(pollTimer);pollTimer=undefined}}
async function chooseBuild(build:CorpusBuild){selectedBuildId.value=build.build_id;selectedAssetId.value=build.asset_id;selectedRecordId.value="";selectedRecord.value=null;sourceBlocks.value=[];await refreshBuild();await refreshRecords(true);if(buildRunning.value)startPolling()}
async function toggleAccept(){if(!currentBuild.value||!selectedRecord.value)return;busy.value="record";try{const row=await pdfCorpusApi.accept(currentBuild.value.build_id,selectedRecord.value.record_id,!selectedRecord.value.accepted);selectedRecord.value=row;await refreshBuild();await refreshRecords()}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function saveManifest(changes:Record<string,unknown>){if(!currentBuild.value)return;busy.value="manifest";try{currentBuild.value=await pdfCorpusApi.patchManifest(currentBuild.value.build_id,changes,Number(currentBuild.value.manifest_revision||1));await refreshBuilds();await refreshRecords(true);setMessage(i18n.t("pdf_corpus.manifest_saved","Document manifest saved. Inherited record metadata and citations were regenerated for review."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}

async function saveMetadata(){if(!currentBuild.value||!selectedRecord.value)return;let changes:Record<string,unknown>;try{changes=JSON.parse(metadataDraft.value)}catch{setMessage(i18n.t("pdf_corpus.metadata_invalid","Metadata must be a valid JSON object."),"error");return}busy.value="record";try{const row=await pdfCorpusApi.patchMetadata(currentBuild.value.build_id,selectedRecord.value.record_id,changes,Number(selectedRecord.value.record_revision||1));selectedRecord.value=row;metadataDraft.value=JSON.stringify(recordMetadata(row),null,2);await refreshBuild();await refreshRecords();setMessage(i18n.t("pdf_corpus.metadata_saved","Metadata saved. Source-bound text and provenance were not modified."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function toggleEvidenceBlock(blockId:string){
  if(!currentBuild.value||!selectedRecord.value||!selectedEvidenceField.value)return;
  const field=selectedEvidenceField.value;
  const existing=selectedRecord.value.metadata_evidence?.[field];
  const ids=new Set((existing?.block_ids||[]).map(String));
  if(ids.has(blockId))ids.delete(blockId);else ids.add(blockId);
  busy.value="evidence";
  try{
    const row=await pdfCorpusApi.patchEvidence(currentBuild.value.build_id,selectedRecord.value.record_id,field,Array.from(ids),existing?.confidence??1,existing?.reason||i18n.t("pdf_corpus.human_evidence_reason","Human-reviewed evidence binding."),Number(selectedRecord.value.record_revision||1));
    selectedRecord.value=row;
    metadataDraft.value=JSON.stringify(recordMetadata(row),null,2);
    await refreshBuild();await refreshRecords();
    setMessage(i18n.t("pdf_corpus.evidence_saved","Evidence binding saved. The record remains open for review."));
  }catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}
}
async function merge(direction:"previous"|"next"){if(!currentBuild.value||!selectedRecord.value)return;busy.value="record";try{await pdfCorpusApi.merge(currentBuild.value.build_id,selectedRecord.value.record_id,direction);selectedRecordId.value="";selectedRecord.value=null;await refreshBuild();await refreshRecords(true);setMessage(i18n.tf("pdf_corpus.merged","Merged with {direction} record; the merged boundary now requires review.",{direction:i18n.t(`pdf_corpus.${direction}`,direction)}))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function split(afterBlockId:string){if(!currentBuild.value||!selectedRecord.value)return;busy.value="record";try{await pdfCorpusApi.split(currentBuild.value.build_id,selectedRecord.value.record_id,afterBlockId);selectedRecordId.value="";selectedRecord.value=null;await refreshBuild();await refreshRecords(true);setMessage(i18n.t("pdf_corpus.split_done","Record split at the selected semantic source boundary. Both records require review."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function rerunMetadata(){if(!currentBuild.value||!selectedRecord.value)return;busy.value="record";try{const row=await pdfCorpusApi.rerunMetadata(currentBuild.value.build_id,selectedRecord.value.record_id,providerPayload.value);selectedRecord.value=row;metadataDraft.value=JSON.stringify(recordMetadata(row),null,2);await refreshBuild();await refreshRecords();setMessage(i18n.t("pdf_corpus.metadata_rerun","Interpretive metadata rerun. Primary source text remained unchanged."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function publish(){if(!currentBuild.value)return;busy.value="publish";try{const result=await pdfCorpusApi.publish(currentBuild.value.build_id);await refreshBuild();await refreshBuilds();setMessage(i18n.tf("pdf_corpus.published","Published {count} records · SHA-256 {hash}…",{count:result.record_count,hash:result.sha256.slice(0,12)}));window.location.href=pdfCorpusApi.publicationUrl(result.publication_id)}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function cancelBuild(){if(!currentBuild.value)return;await pdfCorpusApi.cancel(currentBuild.value.build_id);setMessage(i18n.t("pdf_corpus.cancel_requested","Cancellation requested."));startPolling()}
async function previousPage(){if(recordOffset.value<=0)return;recordOffset.value=Math.max(0,recordOffset.value-pageSize);await refreshRecords()}
async function nextPage(){if(recordOffset.value+pageSize>=recordTotal.value)return;recordOffset.value+=pageSize;await refreshRecords()}

watch([reviewOnly,recordQuery],()=>{void refreshRecords(true)});
watch(selectedAssetId,()=>{if(selectedAssetId.value)void refreshBuilds()});
onMounted(()=>{void refreshAll().then(()=>{if(buildRunning.value)startPolling()}).catch(exc=>setMessage(exc instanceof Error?exc.message:String(exc),"error"))});
onBeforeUnmount(stopPolling);
</script>

<template>
  <section class="corpus-builder" :aria-labelledby="'pdf-corpus-builder-title'">
    <header class="builder-header">
      <div>
        <span class="eyebrow">{{i18n.t('pdf_corpus.eyebrow','PDF Explorer · Corpus Builder')}}</span>
        <h1 id="pdf-corpus-builder-title">{{i18n.t('pdf_corpus.title','Build auditable records from source PDFs')}}</h1>
        <p>{{i18n.t('pdf_corpus.subtitle','Semantic boundaries and interpretive metadata are proposed by an LLM; source text, page provenance, IDs, validation, and publication remain deterministic.')}}</p>
      </div>
      <div class="header-actions">
        <button type="button" class="btn" @click="useCurrentPdf" :disabled="busy!==''">{{i18n.t('pdf_corpus.use_current_pdf','Use current Explorer PDF')}}</button>
        <button type="button" class="btn primary" @click="uploadInput?.click()" :disabled="busy!==''">{{busy==='upload'?i18n.t('pdf_corpus.extracting','Extracting…'):i18n.t('pdf_corpus.choose_pdf','Choose source PDF')}}</button>
        <input ref="uploadInput" class="sr-only" type="file" accept="application/pdf,.pdf" :aria-label="i18n.t('pdf_corpus.choose_pdf','Choose source PDF')" @change="upload(($event.target as HTMLInputElement).files?.[0])">
      </div>
    </header>

    <div ref="statusRegion" tabindex="-1" class="status-region" aria-live="polite" aria-atomic="true">
      <div v-if="error" class="builder-message error" role="alert">{{error}}</div>
      <div v-else-if="notice" class="builder-message" role="status">{{notice}}</div>
    </div>

    <section class="builder-setup" :aria-labelledby="'pdf-corpus-config-title'">
      <div class="setup-source">
        <h2 id="pdf-corpus-config-title" class="sr-only">{{i18n.t('pdf_corpus.build_configuration','Build configuration')}}</h2>
        <label for="pdf-corpus-source">{{i18n.t('pdf_corpus.source_asset','Source asset')}}</label>
        <select id="pdf-corpus-source" v-model="selectedAssetId" class="control">
          <option value="">{{i18n.t('pdf_corpus.choose_persisted_pdf','Choose a persisted PDF…')}}</option>
          <option v-for="asset in assets" :key="asset.asset_id" :value="asset.asset_id">{{asset.filename}} · {{asset.page_count}} pp · {{asset.block_count}} {{i18n.t('pdf_corpus.blocks','blocks')}}</option>
        </select>
        <small v-if="selectedAsset">SHA-256 {{selectedAsset.sha256.slice(0,16)}}… · {{selectedAsset.ocr_pages}} {{i18n.t('pdf_corpus.ocr_pages','OCR page(s)')}} · {{i18n.t('pdf_corpus.persisted','persisted')}} {{formatDate(selectedAsset.created_at)}}</small>
      </div>

      <div class="provider-area">
        <ProviderProfileSelect v-model="selectedProviderId" :profiles="providerProfiles" :default-profile-id="runtime.getDefaultProviderProfileId?.() || ''" :label="i18n.t('pdf_corpus.provider_profile','Provider profile')" :help="i18n.t('pdf_corpus.provider_profile_help','Uses the same centrally managed provider profiles as Research and other LLM workflows.')" :empty-title="i18n.t('pdf_corpus.no_provider_profiles','No LLM provider profiles are configured')" :empty-help="i18n.t('pdf_corpus.no_provider_profiles_help','Create a provider profile or use the manual compatibility settings below.')" :manage-label="i18n.t('pdf_corpus.manage_providers','Manage provider profiles')" :model-not-set-label="i18n.t('pdf_corpus.model_not_set','model not set')" :default-label="i18n.t('ui.default','Default')" :concurrent-label="i18n.t('pdf_corpus.concurrent_requests','max concurrent request(s)')" @manage="manageProviders" />
      </div>

      <button type="button" class="btn primary build-button" @click="startBuild" :disabled="!selectedAssetId||busy!==''||buildRunning">{{busy==='build'?i18n.t('pdf_corpus.starting','Starting…'):i18n.t('pdf_corpus.build_records','Build record set')}}</button>

      <details v-if="selectedAsset?.pages?.length" class="advanced-config page-mapping-config">
        <summary>{{i18n.t('pdf_corpus.page_mapping','Printed-page mapping')}}</summary>
        <PdfPageLabelEditor :pages="selectedAsset.pages||[]" :disabled="busy!==''||Boolean(buildRunning&&currentBuild?.asset_id===selectedAssetId)" @save="savePageLabels" />
      </details>

      <details :open="advancedOpen" class="advanced-config" @toggle="advancedOpen=($event.currentTarget as HTMLDetailsElement).open">
        <summary>{{i18n.t('pdf_corpus.manual_provider','Manual provider compatibility settings')}}</summary>
        <p class="help">{{i18n.t('pdf_corpus.manual_provider_help','Used only when no provider profile is selected. Provider profiles are recommended because credentials remain server-owned and resumable builds can reuse the same configuration.')}}</p>
        <label v-if="selectedProviderId&&providerProfiles.length>1" class="review-provider-field" for="pdf-corpus-review-provider"><span>{{i18n.t('pdf_corpus.escalation_provider','Escalation provider')}}</span><select id="pdf-corpus-review-provider" v-model="selectedReviewProviderId" class="control"><option value="">{{i18n.t('pdf_corpus.no_escalation_provider','None — keep failures for human review')}}</option><option v-for="profile in providerProfiles" :key="profile.id" :value="profile.id" :disabled="profile.id===selectedProviderId">{{profile.name||profile.id}} · {{profile.model||i18n.t('pdf_corpus.model_not_set','model not set')}}</option></select><small>{{i18n.t('pdf_corpus.escalation_provider_help','Used only after the primary provider exhausts structured-output retries. It never replaces deterministic validation or human review.')}}</small></label>
        <div class="advanced-grid">
          <label for="pdf-corpus-provider">{{i18n.t('pdf_corpus.provider','Provider')}}</label><select id="pdf-corpus-provider" v-model="manualProvider" class="control" :disabled="!!selectedProviderId"><option value="ollama">Ollama</option><option value="openai">{{i18n.t('pdf_corpus.openai_compatible','OpenAI-compatible')}}</option></select>
          <label for="pdf-corpus-model">{{i18n.t('pdf_corpus.model','Model')}}</label><input id="pdf-corpus-model" v-model="manualModel" class="control" :disabled="!!selectedProviderId" :placeholder="i18n.t('pdf_corpus.provider_default','Provider default')">
          <label for="pdf-corpus-url">{{i18n.t('pdf_corpus.base_url','Base URL')}}</label><input id="pdf-corpus-url" v-model="manualBaseUrl" class="control" :disabled="!!selectedProviderId" :placeholder="i18n.t('pdf_corpus.provider_default','Provider default')">
          <label for="pdf-corpus-key">{{i18n.t('pdf_corpus.api_key','API key')}}</label><input id="pdf-corpus-key" v-model="manualApiKey" class="control" type="password" autocomplete="off" :disabled="!!selectedProviderId" :placeholder="i18n.t('pdf_corpus.not_persisted','Not persisted in build manifest')">
        </div>
      </details>
    </section>

    <div class="builder-workspace">
      <aside class="build-rail" :aria-label="i18n.t('pdf_corpus.builds','Corpus builds')">
        <div class="rail-title"><div><b>{{i18n.t('pdf_corpus.builds','Corpus builds')}}</b><span>{{buildsTotal}} {{i18n.t('pdf_corpus.total','total')}}</span></div><button type="button" class="icon-button" :title="i18n.t('pdf_corpus.refresh_builds','Refresh builds')" :aria-label="i18n.t('pdf_corpus.refresh_builds','Refresh builds')" @click="refreshBuilds">↻</button></div>
        <button v-for="build in builds" :key="build.build_id" type="button" class="build-row" :class="{active:build.build_id===selectedBuildId}" :aria-current="build.build_id===selectedBuildId?'true':undefined" @click="chooseBuild(build)">
          <span class="status-dot" :data-status="build.status" aria-hidden="true"></span>
          <span><b>{{build.source_filename}}</b><small>{{statusLabel(build)}} · {{Math.round((build.progress||0)*100)}}%</small><small>{{build.record_count||0}} {{i18n.t('pdf_corpus.records','records')}} · {{formatDate(build.created_at)}}</small></span>
        </button>
        <div v-if="!builds.length" class="rail-empty">{{i18n.t('pdf_corpus.no_builds','No builds yet.')}}</div>
      </aside>

      <main class="build-main">
        <section v-if="currentBuild" class="build-summary" :aria-labelledby="'pdf-corpus-current-build'">
          <div class="summary-top">
            <div><span class="eyebrow">{{currentBuild.profile_id}}</span><h2 id="pdf-corpus-current-build">{{currentBuild.source_filename}}</h2><p>{{currentBuild.build_id}}</p></div>
            <div class="summary-actions">
              <button v-if="buildRunning" type="button" class="btn" @click="cancelBuild">{{i18n.t('pdf_corpus.cancel','Cancel')}}</button>
              <button v-if="canResume" type="button" class="btn" @click="resumeBuild" :disabled="busy!==''">{{i18n.t('pdf_corpus.resume','Resume from checkpoint')}}</button>
              <button type="button" class="btn primary" @click="publish" :disabled="!canPublish||busy!==''">{{i18n.t('pdf_corpus.publish_jsonl','Publish JSONL')}}</button>
            </div>
          </div>
          <CorpusBuildProgress :status="currentBuild.status" :stage="currentBuild.stage" :progress="currentBuild.progress||0" :record-count="currentBuild.record_count||0" :review-count="currentBuild.needs_review_count||0" :accepted-count="currentBuild.accepted_count||0" :error="currentBuild.error" :warnings="currentBuild.warnings||[]" :validation="currentBuild.validation||null" :llm-metrics="currentBuild.llm_metrics||null" />
          <details v-if="currentBuild.manifest&&Object.keys(currentBuild.manifest).length" class="manifest-details">
            <summary>{{i18n.t('pdf_corpus.document_manifest','Document manifest')}} · {{i18n.t('pdf_corpus.revision','revision')}} {{currentBuild.manifest_revision||1}}</summary>
            <DocumentManifestEditor :manifest="currentBuild.manifest||{}" :disabled="buildRunning||busy!==''" @save="saveManifest" />
          </details>
          <div class="provenance-strip"><span>SHA {{currentBuild.source_sha256?.slice(0,12)}}…</span><span>{{currentBuild.model||i18n.t('pdf_corpus.provider_default','Provider default')}}</span><span>{{currentBuild.schema_version}}</span><span>{{currentBuild.segmentation_prompt_version}}</span></div>
        </section>

        <section v-if="currentBuild" class="review-toolbar" :aria-label="i18n.t('pdf_corpus.review_controls','Record review controls')">
          <label class="check"><input v-model="reviewOnly" type="checkbox"> {{i18n.t('pdf_corpus.review_only','Needs review only')}}</label>
          <label class="sr-only" for="pdf-corpus-record-search">{{i18n.t('pdf_corpus.search_records','Search generated records')}}</label><input id="pdf-corpus-record-search" v-model="recordQuery" class="control" :placeholder="i18n.t('pdf_corpus.search_records','Search generated records')">
          <span>{{recordTotal}} {{i18n.t('pdf_corpus.matches','matches')}}</span>
          <div class="pager"><button type="button" class="btn small" @click="previousPage" :disabled="recordOffset===0">{{i18n.t('ui.previous','Previous')}}</button><span>{{pageNumber}} / {{pageCount}}</span><button type="button" class="btn small" @click="nextPage" :disabled="recordOffset+pageSize>=recordTotal">{{i18n.t('ui.next','Next')}}</button></div>
        </section>

        <section v-if="currentBuild" class="review-grid">
          <section class="source-pane" :aria-labelledby="'pdf-corpus-source-pane'">
            <div class="pane-head"><b id="pdf-corpus-source-pane">{{i18n.t('pdf_corpus.source_pdf','Source PDF')}}</b><span v-if="selectedRecord">PDF {{selectedPdfPage||'—'}} · {{i18n.t('pdf_corpus.printed_pages','printed')}} {{selectedRecord.page_start}}–{{selectedRecord.page_end}}</span></div>
            <div v-if="selectedRecord&&recordPdfPages.length>1" class="source-page-nav" :aria-label="i18n.t('pdf_corpus.source_page_navigation','Source page navigation')"><button type="button" class="btn small" @click="previousSourcePage" :disabled="selectedPdfPageIndex===0">{{i18n.t('ui.previous','Previous')}}</button><span>{{selectedPdfPageIndex+1}} / {{recordPdfPages.length}}</span><button type="button" class="btn small" @click="nextSourcePage" :disabled="selectedPdfPageIndex>=recordPdfPages.length-1">{{i18n.t('ui.next','Next')}}</button></div>
            <PdfEvidenceViewer v-if="sourcePdfUrl&&selectedRecord" :pdf-url="sourcePdfUrl" :page="selectedPdfPage" :page-width="selectedPageMeta?.width||0" :page-height="selectedPageMeta?.height||0" :blocks="selectedPageBlocks" :evidence-block-ids="evidenceIdsArray" />
            <div class="source-blocks">
              <article v-for="(block,index) in visibleBlocks" :key="block.block_id" class="source-block" :class="{'evidence-block':evidenceBlockIds.has(block.block_id)}" :aria-label="`${block.block_id}, ${block.type}`">
                <header><span>{{block.block_id}}</span><span>PDF {{block.page}} · {{block.type}} · {{Math.round(Number(block.confidence||0)*100)}}%</span></header>
                <p>{{block.text}}</p>
                <button v-if="selectedEvidenceField" type="button" class="evidence-toggle" :aria-pressed="evidenceBlockIds.has(block.block_id)" @click="toggleEvidenceBlock(block.block_id)" :disabled="busy!==''">{{evidenceBlockIds.has(block.block_id)?i18n.t('pdf_corpus.remove_evidence','Remove as evidence'):i18n.t('pdf_corpus.add_evidence','Add as evidence')}} · {{selectedEvidenceField}}</button>
                <button v-if="index<visibleBlocks.length-1" type="button" class="split-button" @click="split(block.block_id)" :disabled="busy!==''">{{i18n.t('pdf_corpus.split_after','Split after this block')}}</button>
              </article>
            </div>
          </section>

          <section class="records-pane" :aria-labelledby="'pdf-corpus-records-pane'">
            <div class="pane-head"><b id="pdf-corpus-records-pane">{{i18n.t('pdf_corpus.generated_records','Generated records')}}</b><span>{{recordTotal}}</span></div>
            <button v-for="record in records" :key="record.record_id" type="button" class="record-row" :class="{active:record.record_id===selectedRecordId}" :aria-current="record.record_id===selectedRecordId?'true':undefined" @click="selectRecord(record)">
              <span class="record-state" :data-state="record.needs_review?'review':record.accepted?'accepted':'ready'" aria-hidden="true"></span>
              <span><b>{{record.record_id}}</b><small>{{i18n.t('pdf_corpus.pages','pp.')}} {{record.page_start}}–{{record.page_end}} · {{record.text_length.toLocaleString()}} {{i18n.t('pdf_corpus.characters','chars')}}</small><small>{{record.needs_review?(record.review_reason||i18n.t('pdf_corpus.needs_review','Needs review')):record.accepted?i18n.t('pdf_corpus.accepted_label','Accepted'):i18n.t('pdf_corpus.ready_acceptance','Ready for acceptance')}}</small></span>
            </button>
            <div v-if="!records.length" class="rail-empty">{{i18n.t('pdf_corpus.no_records_filter','No records match this review filter.')}}</div>
          </section>

          <aside class="inspector-pane" :aria-label="i18n.t('pdf_corpus.record_inspector','Record inspector')">
            <template v-if="selectedRecord">
              <div class="pane-head"><b>{{selectedRecord.record_id}}</b><span>{{selectedRecord.needs_review?i18n.t('pdf_corpus.needs_review','Needs review'):selectedRecord.accepted?i18n.t('pdf_corpus.accepted_label','Accepted'):i18n.t('pdf_corpus.ready','Ready')}}</span></div>
              <div class="inspector-actions"><button type="button" class="btn small" @click="merge('previous')" :disabled="busy!==''">{{i18n.t('pdf_corpus.merge_previous','Merge previous')}}</button><button type="button" class="btn small" @click="merge('next')" :disabled="busy!==''">{{i18n.t('pdf_corpus.merge_next','Merge next')}}</button><button type="button" class="btn small" @click="rerunMetadata" :disabled="busy!==''">{{i18n.t('pdf_corpus.rerun_metadata','Rerun metadata')}}</button><button type="button" class="btn small primary" @click="toggleAccept" :disabled="busy!==''">{{selectedRecord.accepted?i18n.t('pdf_corpus.reopen','Reopen'):i18n.t('pdf_corpus.accept','Accept')}}</button></div>
              <details open><summary>{{i18n.t('pdf_corpus.immutable_text','Immutable source text')}}</summary><div class="record-text">{{selectedRecord.text}}</div></details>
              <details open><summary>{{i18n.t('pdf_corpus.interpretive_metadata','Interpretive metadata')}}</summary><p class="help">{{i18n.t('pdf_corpus.metadata_help','Only model/human-owned metadata is editable here. Text, pages, source spans, and record IDs are protected server-side.')}}</p><label class="sr-only" for="pdf-corpus-metadata">{{i18n.t('pdf_corpus.interpretive_metadata','Interpretive metadata')}}</label><textarea id="pdf-corpus-metadata" v-model="metadataDraft" class="metadata-json" spellcheck="false"></textarea><button type="button" class="btn small" @click="saveMetadata" :disabled="busy!==''">{{i18n.t('pdf_corpus.save_metadata','Save metadata')}}</button></details>
              <details open><summary>{{i18n.t('pdf_corpus.field_evidence','Field evidence')}}</summary><p class="help">{{i18n.t('pdf_corpus.evidence_help','Choose a field to highlight only the source blocks bound to that metadata relation.')}}</p><FieldEvidenceList :evidence="selectedRecord.metadata_evidence||{}" :fields="evidenceCandidateFields" :selected-field="selectedEvidenceField" @select="selectedEvidenceField=$event" /></details>
            </template>
            <div v-else class="inspector-empty">{{i18n.t('pdf_corpus.select_record','Select a generated record to inspect its source binding and metadata.')}}</div>
          </aside>
        </section>

        <section v-else class="builder-empty"><h2>{{i18n.t('pdf_corpus.no_selected_build','No corpus build selected')}}</h2><p>{{i18n.t('pdf_corpus.no_selected_build_help','Persist a PDF source and start a semantic corpus build, or choose a historical build from the rail.')}}</p></section>
      </main>
    </div>
  </section>
</template>

<style scoped>
.corpus-builder{padding:20px 22px 32px;display:grid;gap:14px}.builder-header{display:flex;justify-content:space-between;gap:24px;align-items:flex-end}.builder-header h1{font-size:26px;margin:3px 0 6px}.builder-header p{margin:0;max-width:850px;color:var(--muted);line-height:1.5}.eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);font-weight:700}.header-actions,.summary-actions,.inspector-actions,.pager{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.status-region:focus{outline:none}.builder-message{padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--soft);font-size:12px}.builder-message.error,.build-warning{border-color:#c96b6b;background:#fff2f2;color:#7d2222}.builder-setup{display:grid;grid-template-columns:minmax(260px,1.2fr) minmax(320px,1fr) auto;gap:12px;align-items:end;border:1px solid var(--line);background:var(--card);border-radius:14px;padding:14px}.setup-source,.provider-area{display:grid;gap:6px}.builder-setup label{font-size:10px;font-weight:700;color:var(--muted)}.builder-setup small{font-size:9px;color:var(--muted)}.advanced-config{grid-column:1/-1}.advanced-config summary{cursor:pointer;font-size:10px;font-weight:700}.review-provider-field{display:grid;gap:4px;margin:9px 0}.review-provider-field span{font-size:9px;font-weight:750}.review-provider-field small{font-size:8px;color:var(--muted)}.advanced-grid{display:grid;grid-template-columns:max-content 1fr max-content 1fr;gap:8px 10px;margin-top:8px;align-items:center}.build-button{height:36px}.builder-workspace{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:720px;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--card)}.build-rail{border-inline-end:1px solid var(--line);background:var(--soft);padding:10px;overflow:auto}.rail-title,.pane-head{display:flex;justify-content:space-between;align-items:center;gap:8px}.rail-title{padding:6px 4px 10px}.rail-title>div{display:grid}.rail-title b,.pane-head b{font-size:11px}.rail-title span,.pane-head span{font-size:9px;color:var(--muted)}.icon-button{border:0;background:transparent;cursor:pointer;font-size:18px}.build-row{width:100%;border:1px solid transparent;background:transparent;border-radius:10px;padding:9px;display:grid;grid-template-columns:10px 1fr;gap:9px;text-align:start;cursor:pointer}.build-row:hover,.build-row.active{background:var(--card);border-color:var(--line)}.build-row span:last-child{display:grid;gap:2px;min-width:0}.build-row b{font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.build-row small{font-size:8px;color:var(--muted)}.status-dot,.record-state{width:8px;height:8px;border-radius:50%;background:#777;margin-top:3px}.status-dot[data-status="ready"],.status-dot[data-status="published"],.record-state[data-state="accepted"]{background:#287a4c}.status-dot[data-status="running"],.status-dot[data-status="queued"]{background:#8e6815}.status-dot[data-status="failed"],.status-dot[data-status="interrupted"],.record-state[data-state="review"]{background:#a13f3f}.build-main{min-width:0;display:grid;align-content:start}.build-summary{padding:15px 16px;border-bottom:1px solid var(--line);display:grid;gap:10px}.summary-top{display:flex;justify-content:space-between;gap:18px}.summary-top h2{margin:2px 0;font-size:18px}.summary-top p{margin:0;font-size:9px;color:var(--muted)}.build-status-line,.provenance-strip,.validation-strip{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:9px;color:var(--muted)}.pill{border:1px solid var(--line);border-radius:999px;padding:3px 7px;text-transform:uppercase;font-weight:800;letter-spacing:.04em}.progress-track{height:7px;border-radius:999px;background:var(--soft);overflow:hidden}.progress-track span{display:block;height:100%;background:var(--accent);transition:width .25s}.provenance-strip code{font-size:8px}.manifest-details{border:1px solid var(--line);border-radius:9px;padding:8px 10px}.manifest-details>summary{cursor:pointer;font-size:9px;font-weight:800}.build-warning{display:grid;gap:3px;padding:9px;border:1px solid;border-radius:8px;font-size:10px}.warnings{font-size:10px}.warnings summary{cursor:pointer;font-weight:700}.validation-strip{padding:7px 9px;border-radius:8px;background:#edf8f1}.validation-strip.invalid{background:#fff6e5;color:#604300}.review-toolbar{display:grid;grid-template-columns:auto minmax(180px,1fr) auto auto;gap:10px;align-items:center;padding:9px 12px;border-bottom:1px solid var(--line);font-size:9px}.check{display:flex;gap:6px;align-items:center}.review-grid{display:grid;grid-template-columns:minmax(360px,1.2fr) minmax(240px,.65fr) minmax(300px,.85fr);min-height:650px}.source-pane,.records-pane,.inspector-pane{min-width:0;overflow:auto;max-height:76vh}.source-pane,.records-pane{border-inline-end:1px solid var(--line)}.pane-head{position:sticky;top:0;z-index:3;background:var(--card);padding:9px 11px;border-bottom:1px solid var(--line)}.source-page-nav{display:flex;align-items:center;justify-content:center;gap:8px;padding:6px 10px;border-bottom:1px solid var(--line);font-size:9px;color:var(--muted)}.source-blocks{display:grid;gap:8px;padding:10px}.source-block{border:1px solid var(--line);border-radius:9px;padding:9px;position:relative}.source-block.evidence-block{box-shadow:inset 3px 0 0 var(--accent)}[dir="rtl"] .source-block.evidence-block{box-shadow:inset -3px 0 0 var(--accent)}.source-block header{display:flex;justify-content:space-between;gap:8px;font-size:8px;color:var(--muted)}.source-block p{white-space:pre-wrap;font:13px/1.52 Georgia,serif;margin:7px 0}.split-button{display:block;width:100%;border:0;border-top:1px dashed var(--line);background:transparent;color:var(--muted);font-size:8px;padding:5px;cursor:pointer}.evidence-toggle{display:block;width:100%;margin:5px 0;border:1px solid var(--line);border-radius:7px;background:var(--soft);color:var(--text);font-size:8px;padding:6px;text-align:start;cursor:pointer}.evidence-toggle[aria-pressed="true"]{border-color:var(--accent);box-shadow:inset 3px 0 0 var(--accent)}.record-row{width:100%;border:0;border-bottom:1px solid var(--line);background:transparent;padding:10px;display:grid;grid-template-columns:10px 1fr;gap:8px;text-align:start;cursor:pointer}.record-row:hover,.record-row.active{background:var(--soft)}.record-row span:last-child{display:grid;gap:3px}.record-row b{font-size:10px}.record-row small{font-size:8px;color:var(--muted)}.inspector-pane details{border-bottom:1px solid var(--line);padding:10px 12px}.inspector-pane summary{font-size:10px;font-weight:800;cursor:pointer}.inspector-actions{padding:9px 11px;border-bottom:1px solid var(--line)}.record-text{white-space:pre-wrap;font:13px/1.55 Georgia,serif;margin-top:9px}.metadata-json{width:100%;min-height:230px;resize:vertical;font:10px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;border:1px solid var(--line);border-radius:8px;padding:8px;background:var(--bg);color:var(--text);margin:7px 0}.help{font-size:9px;color:var(--muted);line-height:1.45}.evidence-list{display:grid;gap:8px;margin-top:8px}.evidence-list button{display:grid;gap:2px;padding:7px;background:var(--soft);border:1px solid transparent;border-radius:7px;text-align:start;color:inherit;cursor:pointer}.evidence-list button.active{border-color:var(--accent)}.evidence-list b{font-size:9px}.evidence-list span,.evidence-list small{font-size:8px;color:var(--muted)}.rail-empty,.inspector-empty,.builder-empty{padding:26px 14px;color:var(--muted);font-size:10px}.builder-empty{min-height:420px;display:grid;place-content:center;text-align:center}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.btn:focus-visible,.control:focus-visible,.build-row:focus-visible,.record-row:focus-visible,.icon-button:focus-visible,.split-button:focus-visible,.evidence-toggle:focus-visible,.evidence-list button:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
@media(prefers-reduced-motion:reduce){.progress-track span{transition:none}}
@media(max-width:1250px){.review-grid{grid-template-columns:1fr .72fr}.inspector-pane{grid-column:1/-1;border-top:1px solid var(--line);max-height:none}.source-pane,.records-pane{max-height:65vh}}
@media(max-width:900px){.builder-header{align-items:flex-start;flex-direction:column}.builder-setup{grid-template-columns:1fr}.advanced-grid{grid-template-columns:1fr}.advanced-config{grid-column:auto}.builder-workspace{grid-template-columns:1fr}.build-rail{border-inline-end:0;border-bottom:1px solid var(--line);max-height:220px}.review-toolbar{grid-template-columns:1fr 1fr}.review-grid{grid-template-columns:1fr}.source-pane,.records-pane{border-inline-end:0;border-bottom:1px solid var(--line);max-height:none}}
</style>
