<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { pdfCorpusApi, type CorpusBuild, type CorpusRecord, type PdfAsset, type SourceBlock } from "../api/pdfCorpus";
import { systemApi, type ProviderProfile } from "../api/system";
import { useI18nStore } from "../stores/i18n";
import ProviderProfileSelect from "./ProviderProfileSelect.vue";
import CorpusBuildProgress from "./CorpusBuildProgress.vue";
import FieldEvidenceList from "./FieldEvidenceList.vue";
import PdfEvidenceViewer from "./PdfEvidenceViewer.vue";
import PdfPageLabelEditor from "./PdfPageLabelEditor.vue";
import DocumentManifestEditor from "./DocumentManifestEditor.vue";
import CorpusExecutionSettings from "./CorpusExecutionSettings.vue";
import CorpusWorkflowStepper from "./CorpusWorkflowStepper.vue";
import CorpusQualitySummary from "./CorpusQualitySummary.vue";
import CorpusRecordSizingSettings, { type RecordSizingPolicy } from "./CorpusRecordSizingSettings.vue";
import CorpusRecordFocusReview from "./CorpusRecordFocusReview.vue";
import * as runtime from "../legacy/runtime.js";

const i18n=useI18nStore();
const route=useRoute();
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
const reviewOnly=ref(false);
const recordQuery=ref("");
const focusView=ref(false);
const recordsLoading=ref(false);
const recordListEl=ref<HTMLElement|null>(null);
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
const useProfileDefaults=ref(true);
const generationOverrides=ref<Record<string,unknown>>({});
const maxConcurrentRequests=ref(1);
const stageLimits=ref<Record<string,number>>({
  manifest_num_predict:1800,segmentation_num_predict:1200,reconciliation_num_predict:1000,
  discourse_num_predict:1600,quotation_num_predict:1500,indexing_num_predict:1200,segmentation_window_tokens:5000,
});
const recordSizing=ref<RecordSizingPolicy>({preferred_record_chars:1750,record_length_tolerance:200,long_record_chars:3500,absolute_record_chars:6000});
const metadataDraft=ref("{}");
let pollTimer:number|undefined;
const DRAFT_KEY="derridai.pdf-corpus-builder.draft.v2";
function restoreBuilderDraft(){
  try{
    const raw=localStorage.getItem(DRAFT_KEY);if(!raw)return;
    const draft=JSON.parse(raw) as Record<string,any>;
    if(typeof draft.selectedAssetId==="string")selectedAssetId.value=draft.selectedAssetId;
    if(typeof draft.manualProvider==="string"&&(draft.manualProvider==="ollama"||draft.manualProvider==="openai"))manualProvider.value=draft.manualProvider;
    if(typeof draft.manualModel==="string")manualModel.value=draft.manualModel;
    if(typeof draft.manualBaseUrl==="string")manualBaseUrl.value=draft.manualBaseUrl;
    if(typeof draft.useProfileDefaults==="boolean")useProfileDefaults.value=draft.useProfileDefaults;
    if(draft.generationOverrides&&typeof draft.generationOverrides==="object")generationOverrides.value={...draft.generationOverrides};
    if(draft.stageLimits&&typeof draft.stageLimits==="object")stageLimits.value={...stageLimits.value,...draft.stageLimits};
    if(draft.recordSizing&&typeof draft.recordSizing==="object")recordSizing.value={...recordSizing.value,...draft.recordSizing};
    if(Number.isFinite(Number(draft.maxConcurrentRequests)))maxConcurrentRequests.value=Math.max(1,Math.min(16,Number(draft.maxConcurrentRequests)));
  }catch{/* ignore stale browser drafts */}
}
function persistBuilderDraft(){
  try{localStorage.setItem(DRAFT_KEY,JSON.stringify({selectedAssetId:selectedAssetId.value,manualProvider:manualProvider.value,manualModel:manualModel.value,manualBaseUrl:manualBaseUrl.value,useProfileDefaults:useProfileDefaults.value,generationOverrides:generationOverrides.value,stageLimits:stageLimits.value,recordSizing:recordSizing.value,maxConcurrentRequests:maxConcurrentRequests.value}))}catch{/* storage may be unavailable */}
}
function metadataDraftKey(buildId:string,recordId:string){return `derridai.pdf-corpus.metadata-draft.${buildId}.${recordId}`}


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
const canPublish=computed(()=>Boolean(currentBuild.value && ["ready","awaiting_review"].includes(currentBuild.value.status) && currentBuild.value.needs_review_count===0 && Number(currentBuild.value.rejected_count||0)===0 && currentBuild.value.accepted_count===currentBuild.value.record_count && currentBuild.value.validation?.valid));
const selectedRecordIndex=computed(()=>records.value.findIndex(row=>row.record_id===selectedRecordId.value));
const canMergePrevious=computed(()=>Number(selectedRecord.value?.topology_index??-1)>0);
const canMergeNext=computed(()=>{const index=Number(selectedRecord.value?.topology_index??-1),total=Number(selectedRecord.value?.topology_count??0);return index>=0&&index<total-1});
const reviewRemaining=computed(()=>Math.max(0,Number(currentBuild.value?.record_count||0)-Number(currentBuild.value?.accepted_count||0)-Number(currentBuild.value?.rejected_count||0)));
const buildRunning=computed(()=>Boolean(currentBuild.value && ["queued","running"].includes(currentBuild.value.status)));
const canResume=computed(()=>Boolean(currentBuild.value?.resumable && !buildRunning.value && ["failed","interrupted","cancelled","blocked"].includes(String(currentBuild.value.status))));
const segmentationNeedsReview=computed(()=>Boolean(currentBuild.value?.segmentation_degraded && !buildRunning.value && (currentBuild.value?.segmentation_unresolved_regions?.length||0)>0));
const retryingSegmentation=computed(()=>Boolean(buildRunning.value && currentBuild.value?.retrying_segmentation));
const canRetryMetadata=computed(()=>Boolean(currentBuild.value && !buildRunning.value && Number(currentBuild.value.record_count||0)>0 && Number(currentBuild.value.metadata_completed||0)<Number(currentBuild.value.record_count||0)));
const awaitingManifestReview=computed(()=>currentBuild.value?.status==="awaiting_manifest_review");
const hasRecordTopology=computed(()=>Boolean(currentBuild.value && !awaitingManifestReview.value && (Number(currentBuild.value.record_count||0)>0||Number(currentBuild.value.metadata_total||0)>0||recordTotal.value>0)));
const pageNumber=computed(()=>Math.floor(recordOffset.value/pageSize)+1);
const pageCount=computed(()=>Math.max(1,Math.ceil(recordTotal.value/pageSize)));
const sourcePdfUrl=computed(()=>selectedAssetId.value?pdfCorpusApi.assetContentUrl(selectedAssetId.value):"");
const recordPdfPages=computed(()=>Array.from(new Set((selectedRecord.value?.pdf_pages||[]).map(Number).filter(value=>value>0))).sort((a,b)=>a-b));
const selectedPdfPageIndex=computed(()=>Math.max(0,recordPdfPages.value.indexOf(selectedPdfPage.value)));
const selectedPageMeta=computed(()=>selectedAsset.value?.pages?.find(page=>Number(page.pdf_page)===Number(selectedPdfPage.value))||null);
const selectedPageBlocks=computed(()=>visibleBlocks.value.filter(block=>Number(block.page)===Number(selectedPdfPage.value)));
const evidenceIdsArray=computed(()=>Array.from(evidenceBlockIds.value));
const selectedProfile=computed(()=>providerProfiles.value.find(profile=>profile.id===selectedProviderId.value)||null);
const selectedProfileModel=computed(()=>String(selectedProfile.value?.model||""));
const profileGeneration=computed<Record<string,unknown>>(()=>{
  if(!selectedProviderId.value)return {};
  const payload=directProfilePayload(selectedProviderId.value);
  const generation=payload?.generation;
  return generation&&typeof generation==="object"?{...(generation as Record<string,unknown>)}:{};
});
const effectiveGeneration=computed<Record<string,unknown>>(()=>useProfileDefaults.value?profileGeneration.value:{...profileGeneration.value,...generationOverrides.value});
const effectiveNumCtx=computed(()=>Number(effectiveGeneration.value.num_ctx||0));
const requiredContext=computed(()=>Number(stageLimits.value.segmentation_window_tokens||5000)+Number(stageLimits.value.segmentation_num_predict||1200)+1536);
const contextSafe=computed(()=>!effectiveNumCtx.value||requiredContext.value<=effectiveNumCtx.value);

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
    max_concurrent_requests:Number(config.max_concurrent_requests||1),
    generation:ollama&&typeof ollama==="object"?ollama:undefined,
  };
}
const providerPayload=computed<Record<string,unknown>>(()=>{
  const buildGeneration=useProfileDefaults.value?null:{...effectiveGeneration.value};
  if(selectedProviderId.value){
    const primary=directProfilePayload(selectedProviderId.value)||{provider_profile_id:selectedProviderId.value};
    const payload:Record<string,unknown>={...primary,use_profile_defaults:useProfileDefaults.value};
    if(!useProfileDefaults.value)payload.generation=buildGeneration;
    // Server-owned profiles resolve credentials and their defaults on the API.
    // Per-build generation overrides survive that resolution and are merged there.
    if(serverProviderIds.value.has(selectedProviderId.value)){
      for(const key of ["provider","base_url","api_key"])delete payload[key];
      if(useProfileDefaults.value)delete payload.generation;
    }
    payload.max_concurrent_requests=maxConcurrentRequests.value;
    payload.stage_limits={...stageLimits.value};
    payload.record_sizing={...recordSizing.value};
    if(selectedReviewProviderId.value&&selectedReviewProviderId.value!==selectedProviderId.value){
      payload.review_provider_profile_id=selectedReviewProviderId.value;
      if(!serverProviderIds.value.has(selectedReviewProviderId.value)){
        const review=directProfilePayload(selectedReviewProviderId.value);
        if(review){
          const {provider_profile_id: _profileId,max_concurrent_requests:_max,...reviewConfig}=review;
          payload.review_provider=reviewConfig;
        }
      }
    }
    return payload;
  }
  const payload:Record<string,unknown>={provider:manualProvider.value,use_profile_defaults:false,max_concurrent_requests:maxConcurrentRequests.value,stage_limits:{...stageLimits.value},record_sizing:{...recordSizing.value}};
  if(manualModel.value.trim())payload.model=manualModel.value.trim();
  if(manualBaseUrl.value.trim())payload.base_url=manualBaseUrl.value.trim();
  if(manualApiKey.value)payload.api_key=manualApiKey.value;
  if(Object.keys(generationOverrides.value).length)payload.generation={...generationOverrides.value};
  return payload;
});

function formatDate(value?:string|null){if(!value)return "—";try{return new Intl.DateTimeFormat(i18n.locale||undefined,{dateStyle:"medium",timeStyle:"short"}).format(new Date(value))}catch{return value}}
function statusLabel(build:CorpusBuild){return i18n.t(`pdf_corpus.status.${String(build.status||"unknown")}`,String(build.status||"unknown").replace(/_/g," "))}
function registerBuildOperation(build:CorpusBuild){
  const asset=assets.value.find(item=>item.asset_id===build.asset_id);
  const total=Math.max(1,Number(asset?.block_count||1));
  const progress=Math.max(0,Math.min(1,Number(build.progress||0)));
  (runtime as any).registerExternalJob?.({
    id:build.build_id,build_id:build.build_id,type:"pdf_corpus",kind:"pdf_corpus",label:`PDF corpus · ${build.source_filename||"source"}`,
    status:["queued","running"].includes(build.status)?build.status:build.status==="blocked"?"blocked":"completed",raw_status:build.status,stage:build.stage,stage_detail:build.stage,
    source_filename:build.source_filename,progress,total,completed:Math.min(total,Math.round(total*progress)),record_count:Number(build.record_count||0),review_count:Number(build.needs_review_count||0),
    unresolved_regions:Number(build.segmentation_unresolved_regions?.length||0),created_at:build.created_at,started_at:build.started_at,finished_at:build.finished_at,
  });
}
function setMessage(message:string,tone:"error"|"notice"="notice"){if(tone==="error"){error.value=message;notice.value=""}else{notice.value=message;error.value=""};void nextTick(()=>statusRegion.value?.focus({preventScroll:true}))}
function recordMetadata(record:CorpusRecord){
  const protectedFields=new Set([
    "record_id","record_revision","text","text_length","page_start","page_end","pdf_file","pdf_pages","source_asset_id","source_block_ids","source_spans","boundary_evidence","metadata_evidence","accepted","rejected","review_disposition","updates","metadata_complete",
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
  const activeBuildProfile=String((currentBuild.value?.request as Record<string,unknown>|undefined)?.provider_profile_id||"");
  if(activeBuildProfile&&providerProfiles.value.some(profile=>profile.id===activeBuildProfile)){
    selectedProviderId.value=activeBuildProfile;
  }else if(!currentBuild.value||!selectedProviderId.value||!providerProfiles.value.some(profile=>profile.id===selectedProviderId.value)){
    selectedProviderId.value=providerProfiles.value.find(profile=>profile.id===defaultId)?.id||providerProfiles.value[0]?.id||"";
  }
}
async function refreshAssets(){const result=await pdfCorpusApi.listAssets();assets.value=result.items;if(!selectedAssetId.value&&assets.value[0])selectedAssetId.value=assets.value[0].asset_id}
async function refreshBuilds(){const result=await pdfCorpusApi.listBuilds(0,100);builds.value=result.items;buildsTotal.value=result.total;const requested=String(route.query.build||"");if(requested&&builds.value.some(build=>build.build_id===requested))selectedBuildId.value=requested;else if(!selectedBuildId.value&&builds.value[0])selectedBuildId.value=builds.value[0].build_id}
function syncBuildInRail(build:CorpusBuild){const index=builds.value.findIndex(item=>item.build_id===build.build_id);if(index>=0)builds.value.splice(index,1,{...builds.value[index],...build});else builds.value.unshift(build)}
async function refreshBuild(){if(!selectedBuildId.value){currentBuild.value=null;return}try{currentBuild.value=await pdfCorpusApi.build(selectedBuildId.value);syncBuildInRail(currentBuild.value)}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error");return}if(currentBuild.value?.asset_id)selectedAssetId.value=currentBuild.value.asset_id;const request=currentBuild.value?.request||{};if(typeof request.provider_profile_id==="string"&&providerProfiles.value.some(profile=>profile.id===request.provider_profile_id))selectedProviderId.value=request.provider_profile_id;if(typeof request.review_provider_profile_id==="string"&&providerProfiles.value.some(profile=>profile.id===request.review_provider_profile_id))selectedReviewProviderId.value=request.review_provider_profile_id;const requestGeneration=request.generation;if(requestGeneration&&typeof requestGeneration==="object")generationOverrides.value={...(requestGeneration as Record<string,unknown>)};useProfileDefaults.value=request.use_profile_defaults!==false;if(request.stage_limits&&typeof request.stage_limits==="object")stageLimits.value={...stageLimits.value,...(request.stage_limits as Record<string,number>)};if(request.record_sizing&&typeof request.record_sizing==="object")recordSizing.value={...recordSizing.value,...(request.record_sizing as RecordSizingPolicy)};if(request.max_concurrent_requests)maxConcurrentRequests.value=Math.max(1,Math.min(16,Number(request.max_concurrent_requests)||1))}
async function refreshRecords(reset=false, preferredId=""){
  if(reset)recordOffset.value=0;
  if(!selectedBuildId.value){records.value=[];recordTotal.value=0;selectedRecord.value=null;return}
  recordsLoading.value=true;
  try{
    let result=await pdfCorpusApi.records(selectedBuildId.value,recordOffset.value,pageSize,reviewOnly.value,recordQuery.value);
    // A refreshed review page can race the final records.jsonl rename/checkpoint.
    // When the build advertises records but the first unfiltered read is empty,
    // retry once instead of requiring a checkbox toggle to trigger another fetch.
    if(!reviewOnly.value&&!recordQuery.value&&result.total===0&&Number(currentBuild.value?.record_count||currentBuild.value?.metadata_total||0)>0){
      await new Promise(resolve=>window.setTimeout(resolve,120));
      result=await pdfCorpusApi.records(selectedBuildId.value,0,pageSize,false,"");
      recordOffset.value=0;
    }
    records.value=result.items;recordTotal.value=result.total;
    const wanted=preferredId||selectedRecordId.value;const match=wanted?records.value.find(row=>row.record_id===wanted):undefined;
    if(match){selectRecord(match);return}
    if(records.value[0]){selectRecord(records.value[0]);return}
    selectedRecordId.value="";selectedRecord.value=null;sourceBlocks.value=[];
  }finally{recordsLoading.value=false}
}
async function refreshBlocks(){if(!selectedAssetId.value||!selectedRecord.value?.source_block_ids?.length){sourceBlocks.value=[];return}const result=await pdfCorpusApi.blocks(selectedAssetId.value,0,Math.min(1000,selectedRecord.value.source_block_ids.length),selectedRecord.value.source_block_ids);sourceBlocks.value=result.items}
async function refreshAll(){await Promise.all([refreshProviders(),refreshAssets(),refreshBuilds()]);await refreshBuild();await refreshRecords(true);if(currentBuild.value?.status==="ready"&&!currentBuild.value.publication)await finalizeIfReady()}
function selectRecord(record:CorpusRecord){selectedRecordId.value=record.record_id;selectedRecord.value=record;selectedEvidenceField.value="";selectedPdfPage.value=Number(record.pdf_pages?.[0]||1);const fallback=JSON.stringify(recordMetadata(record),null,2);try{metadataDraft.value=localStorage.getItem(metadataDraftKey(selectedBuildId.value,record.record_id))||fallback}catch{metadataDraft.value=fallback}void refreshBlocks()}


function previousSourcePage(){if(selectedPdfPageIndex.value>0)selectedPdfPage.value=recordPdfPages.value[selectedPdfPageIndex.value-1]}
function nextSourcePage(){if(selectedPdfPageIndex.value<recordPdfPages.value.length-1)selectedPdfPage.value=recordPdfPages.value[selectedPdfPageIndex.value+1]}

async function upload(file?:File|null){if(!file)return;busy.value="upload";setMessage("");try{const asset=await pdfCorpusApi.uploadAsset(file,"auto");await refreshAssets();selectedAssetId.value=asset.asset_id;setMessage(i18n.tf("pdf_corpus.source_ingested","Source ingested: {pages} pages · {blocks} source blocks · OCR on {ocr} pages.",{pages:asset.page_count,blocks:asset.block_count,ocr:asset.ocr_pages||0}))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function savePageLabels(labels:Record<number,string|null>){if(!selectedAssetId.value||!Object.keys(labels).length)return;busy.value="page-labels";try{const asset=await pdfCorpusApi.updatePageLabels(selectedAssetId.value,labels);assets.value=assets.value.map(item=>item.asset_id===asset.asset_id?asset:item);setMessage(i18n.t("pdf_corpus.page_mapping_saved","Printed-page overrides saved. New corpus builds will use the corrected labels."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}

async function useCurrentPdf(){const file=(runtime.state as any)?.pdf?.file as File|undefined;if(!file){setMessage(i18n.t("pdf_corpus.open_pdf_first","Open a PDF in Explorer first, or choose a source PDF here."),"error");return}await upload(file)}
async function startBuild(){if(!selectedAssetId.value)return;busy.value="build";setMessage("");try{const payload={asset_id:selectedAssetId.value,review_manifest_before_segmentation:false,auto_enrich_work_metadata:true,...providerPayload.value};const build=await pdfCorpusApi.createBuild(payload);selectedBuildId.value=build.build_id;currentBuild.value=build;registerBuildOperation(build);await refreshBuilds();startPolling();setMessage(i18n.t("pdf_corpus.build_started","Corpus build started. Progress and completed checkpoints are persisted server-side."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function resumeBuild(){if(!currentBuild.value)return;if(buildRunning.value){setMessage(i18n.t("pdf_corpus.already_running","This build is already running. Its live status is shown below."));return}busy.value="build";try{currentBuild.value=await pdfCorpusApi.resume(currentBuild.value.build_id,providerPayload.value);syncBuildInRail(currentBuild.value);registerBuildOperation(currentBuild.value);startPolling();setMessage(i18n.t("pdf_corpus.build_resumed","Build resumed from its last completed checkpoint."))}catch(exc){const message=exc instanceof Error?exc.message:String(exc);if(message.includes("already running")){await refreshBuild();if(currentBuild.value)registerBuildOperation(currentBuild.value);setMessage(i18n.t("pdf_corpus.already_running","This build is already running. Its live status is shown below."))}else setMessage(message,"error")}finally{busy.value=""}}
async function confirmManifest(){if(!currentBuild.value)return;busy.value="manifest";try{currentBuild.value=await pdfCorpusApi.confirmManifest(currentBuild.value.build_id,providerPayload.value);syncBuildInRail(currentBuild.value);registerBuildOperation(currentBuild.value);startPolling();setMessage(i18n.t("pdf_corpus.manifest_confirmed","Document manifest confirmed. Semantic segmentation has started."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
function startPolling(){stopPolling();pollTimer=window.setInterval(async()=>{if(!selectedBuildId.value)return;await refreshBuild();if(!buildRunning.value){stopPolling();await refreshBuilds();await refreshRecords(true)}},1400)}
function stopPolling(){if(pollTimer!==undefined){clearInterval(pollTimer);pollTimer=undefined}}
async function chooseBuild(build:CorpusBuild){selectedBuildId.value=build.build_id;selectedAssetId.value=build.asset_id;selectedRecordId.value="";selectedRecord.value=null;sourceBlocks.value=[];await refreshBuild();await refreshRecords(true);if(buildRunning.value)startPolling();else if(currentBuild.value?.status==="ready"&&!currentBuild.value.publication)await finalizeIfReady()}
async function advanceFrom(recordId:string){const index=records.value.findIndex(row=>row.record_id===recordId);const next=records.value[index+1]||records.value[index-1];if(next){selectRecord(next);return}if(recordOffset.value+pageSize<recordTotal.value){recordOffset.value+=pageSize;await refreshRecords();return}await refreshRecords()}
async function setDisposition(disposition:"pending"|"accepted"|"rejected"){
  if(!currentBuild.value||!selectedRecord.value)return;const id=selectedRecord.value.record_id;busy.value="record";
  try{
    await pdfCorpusApi.disposition(currentBuild.value.build_id,id,disposition,"",Number(selectedRecord.value.record_revision||1));
    await refreshBuild();await refreshRecords(false);if(disposition!=="pending")await advanceFrom(id);
    if(disposition==="accepted"&&currentBuild.value?.status==="ready"){busy.value="";await finalizeIfReady();return}
    setMessage(disposition==="accepted"?i18n.t("pdf_corpus.accepted_notice","Record accepted. Advanced to the next record."):disposition==="rejected"?i18n.t("pdf_corpus.rejected_notice","Record rejected. Advanced to the next record."):i18n.t("pdf_corpus.reopened_notice","Record reopened for review."));
  }catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}
}
async function toggleAccept(){await setDisposition(selectedRecord.value?.accepted?"pending":"accepted")}
async function rejectRecord(){await setDisposition("rejected")}
async function skipRecord(){if(!selectedRecord.value)return;await advanceFrom(selectedRecord.value.record_id)}
async function bulkDisposition(disposition:"accepted"|"rejected"){
  if(!currentBuild.value)return;const count=recordTotal.value;if(!count)return;const verb=disposition==="accepted"?i18n.t("pdf_corpus.accept_all","Accept all"):i18n.t("pdf_corpus.reject_all","Reject all");
  if(!window.confirm(i18n.tf("pdf_corpus.bulk_confirm","{action} {count} record(s) matching the current filter?",{action:verb,count})))return;busy.value="bulk";
  try{
    const result=await pdfCorpusApi.bulkDisposition(currentBuild.value.build_id,disposition,reviewOnly.value?true:null,recordQuery.value);await refreshBuild();await refreshRecords(true);
    if(disposition==="accepted"&&currentBuild.value?.status==="ready"){busy.value="";await finalizeIfReady();return}
    setMessage(i18n.tf("pdf_corpus.bulk_done","Updated {count} record(s).",{count:result.changed}));
  }catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}
}
async function undoReview(){if(!currentBuild.value)return;busy.value="record";try{const result=await pdfCorpusApi.undoReview(currentBuild.value.build_id);await refreshBuild();await refreshRecords(true,result.selected_record_id||"");setMessage(i18n.t("pdf_corpus.undo_done","The last merge or split was undone."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function saveManifest(changes:Record<string,unknown>){if(!currentBuild.value)return;busy.value="manifest";try{currentBuild.value=await pdfCorpusApi.patchManifest(currentBuild.value.build_id,changes,Number(currentBuild.value.manifest_revision||1));await refreshBuilds();await refreshRecords(true);setMessage(i18n.t("pdf_corpus.manifest_saved","Document manifest saved. Inherited record metadata and citations were regenerated for review."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}

async function saveMetadata(){if(!currentBuild.value||!selectedRecord.value)return;let changes:Record<string,unknown>;try{changes=JSON.parse(metadataDraft.value)}catch{setMessage(i18n.t("pdf_corpus.metadata_invalid","Metadata must be a valid JSON object."),"error");return}busy.value="record";try{const row=await pdfCorpusApi.patchMetadata(currentBuild.value.build_id,selectedRecord.value.record_id,changes,Number(selectedRecord.value.record_revision||1));selectedRecord.value=row;metadataDraft.value=JSON.stringify(recordMetadata(row),null,2);try{localStorage.removeItem(metadataDraftKey(currentBuild.value.build_id,row.record_id))}catch{}await refreshBuild();await refreshRecords();setMessage(i18n.t("pdf_corpus.metadata_saved","Metadata saved. Source-bound text and provenance were not modified."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
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
async function merge(direction:"previous"|"next"){if(!currentBuild.value||!selectedRecord.value)return;const id=selectedRecord.value.record_id;const scrollY=window.scrollY;busy.value="record";try{const row=await pdfCorpusApi.merge(currentBuild.value.build_id,id,direction,Number(selectedRecord.value.record_revision||1));await refreshBuild();await refreshRecords(false,row.record_id);await nextTick();window.scrollTo({top:scrollY});setMessage(i18n.tf("pdf_corpus.merged","Merged with {direction} record; the merged boundary now requires review.",{direction:i18n.t(`pdf_corpus.${direction}`,direction)}))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function split(afterBlockId:string){if(!currentBuild.value||!selectedRecord.value)return;const id=selectedRecord.value.record_id;const scrollY=window.scrollY;busy.value="record";try{const result=await pdfCorpusApi.split(currentBuild.value.build_id,id,afterBlockId,Number(selectedRecord.value.record_revision||1));await refreshBuild();await refreshRecords(false,result.records[0]?.record_id||id);await nextTick();window.scrollTo({top:scrollY});setMessage(i18n.t("pdf_corpus.split_done","Record split at the selected semantic source boundary. Both records require review."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function rerunMetadata(){if(!currentBuild.value||!selectedRecord.value)return;busy.value="record";try{const row=await pdfCorpusApi.rerunMetadata(currentBuild.value.build_id,selectedRecord.value.record_id,providerPayload.value);selectedRecord.value=row;metadataDraft.value=JSON.stringify(recordMetadata(row),null,2);await refreshBuild();await refreshRecords();setMessage(i18n.t("pdf_corpus.metadata_rerun","Interpretive metadata rerun. Primary source text remained unchanged."))}catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error")}finally{busy.value=""}}
async function publish(options:{download?:boolean;automatic?:boolean}={}){
  if(!currentBuild.value)return null;busy.value="publish";
  try{
    const result=await pdfCorpusApi.publish(currentBuild.value.build_id);await refreshBuild();await refreshBuilds();
    setMessage(options.automatic?i18n.tf("pdf_corpus.auto_published","Review complete. Published {count} records automatically.",{count:result.record_count}):i18n.tf("pdf_corpus.published","Published {count} records · SHA-256 {hash}…",{count:result.record_count,hash:result.sha256.slice(0,12)}));
    if(options.download)window.location.href=pdfCorpusApi.publicationUrl(result.publication_id);
    return result;
  }catch(exc){setMessage(exc instanceof Error?exc.message:String(exc),"error");return null}finally{busy.value=""}
}
async function finalizeIfReady(){
  await refreshBuild();
  if(currentBuild.value?.status==="ready"&&!currentBuild.value.publication&&currentBuild.value.validation?.valid){await publish({automatic:true})}
}
async function cancelBuild(){if(!currentBuild.value)return;await pdfCorpusApi.cancel(currentBuild.value.build_id);setMessage(i18n.t("pdf_corpus.cancel_requested","Cancellation requested."));startPolling()}
async function previousPage(){if(recordOffset.value<=0)return;recordOffset.value=Math.max(0,recordOffset.value-pageSize);await refreshRecords()}
async function nextPage(){if(recordOffset.value+pageSize>=recordTotal.value)return;recordOffset.value+=pageSize;await refreshRecords()}

function reviewShortcut(event:KeyboardEvent){if(!selectedRecord.value||busy.value)return;const target=event.target as HTMLElement|null;if(target&&["INPUT","TEXTAREA","SELECT"].includes(target.tagName))return;if(event.key.toLowerCase()==="a"){event.preventDefault();void setDisposition("accepted")}else if(event.key.toLowerCase()==="r"){event.preventDefault();void setDisposition("rejected")}else if(event.key.toLowerCase()==="z"){event.preventDefault();void undoReview()}else if(event.key.toLowerCase()==="j"||event.key==="ArrowDown"){event.preventDefault();void skipRecord()}else if(event.key.toLowerCase()==="f"){event.preventDefault();focusView.value=!focusView.value}}
watch(selectedProviderId,(profileId)=>{if(!profileId)return;const payload=directProfilePayload(profileId);if(payload?.generation&&typeof payload.generation==="object")generationOverrides.value={...(payload.generation as Record<string,unknown>)};const profile=providerProfiles.value.find(item=>item.id===profileId);maxConcurrentRequests.value=Math.max(1,Math.min(16,Number(profile?.max_concurrent_requests||payload?.max_concurrent_requests||1)))});
watch([reviewOnly,recordQuery],()=>{void refreshRecords(true)});
watch(selectedAssetId,()=>{if(selectedAssetId.value)void refreshBuilds()});
watch(()=>route.query.build,async value=>{
  const buildId=String(value||"");
  if(!buildId||buildId===selectedBuildId.value)return;
  selectedBuildId.value=buildId;selectedRecordId.value="";selectedRecord.value=null;sourceBlocks.value=[];
  await refreshBuild();await refreshRecords(true);if(buildRunning.value)startPolling();
});
watch([selectedProviderId,selectedReviewProviderId,selectedAssetId,manualProvider,manualModel,manualBaseUrl,useProfileDefaults,generationOverrides,stageLimits,recordSizing,maxConcurrentRequests],persistBuilderDraft,{deep:true});
watch(metadataDraft,(value)=>{if(!selectedBuildId.value||!selectedRecordId.value)return;try{localStorage.setItem(metadataDraftKey(selectedBuildId.value,selectedRecordId.value),value)}catch{}},{flush:"post"});
onMounted(()=>{window.addEventListener("keydown",reviewShortcut);restoreBuilderDraft();void refreshAll().then(()=>{if(buildRunning.value)startPolling()}).catch(exc=>setMessage(exc instanceof Error?exc.message:String(exc),"error"))});
onBeforeUnmount(()=>{window.removeEventListener("keydown",reviewShortcut);stopPolling()});
</script>

<template>
  <section class="corpus-builder" :aria-labelledby="'pdf-corpus-builder-title'">
    <header class="builder-header">
      <div>
        <span class="eyebrow">{{i18n.t('pdf_corpus.eyebrow','Corpus Builder')}}</span>
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

    <CorpusWorkflowStepper :stage="currentBuild?.stage||''" :status="currentBuild?.status||''" :has-asset="Boolean(selectedAssetId)" :has-manifest="Boolean(currentBuild?.manifest&&Object.keys(currentBuild.manifest).length)" :accepted-count="currentBuild?.accepted_count||0" :record-count="currentBuild?.record_count||0" />

    <section class="builder-setup" :aria-labelledby="'pdf-corpus-config-title'">
      <div class="setup-card setup-source">
        <h2 id="pdf-corpus-config-title" class="sr-only">{{i18n.t('pdf_corpus.build_configuration','Build configuration')}}</h2>
        <div class="setup-card-heading"><b>{{i18n.t('pdf_corpus.source_setup_title','Source PDF')}}</b><small>{{i18n.t('pdf_corpus.source_setup_help','Choose an extracted PDF, or add the PDF currently open in Explorer.')}}</small></div>
        <label for="pdf-corpus-source">{{i18n.t('pdf_corpus.source_asset','Source asset')}}</label>
        <select id="pdf-corpus-source" v-model="selectedAssetId" class="control">
          <option value="">{{i18n.t('pdf_corpus.choose_persisted_pdf','Choose a persisted PDF…')}}</option>
          <option v-for="asset in assets" :key="asset.asset_id" :value="asset.asset_id">{{asset.filename}} · {{asset.page_count}} pp · {{asset.block_count}} {{i18n.t('pdf_corpus.blocks','blocks')}}</option>
        </select>
        <small v-if="selectedAsset">SHA-256 {{selectedAsset.sha256.slice(0,16)}}… · {{selectedAsset.ocr_pages}} {{i18n.t('pdf_corpus.ocr_pages','OCR page(s)')}} · {{i18n.t('pdf_corpus.persisted','persisted')}} {{formatDate(selectedAsset.created_at)}}</small>
      </div>

      <div class="provider-area">
        <ProviderProfileSelect v-model="selectedProviderId" :profiles="providerProfiles" :default-profile-id="runtime.getDefaultProviderProfileId?.() || ''" :label="i18n.t('pdf_corpus.provider_profile','Primary LLM provider')" :help="i18n.t('pdf_corpus.provider_profile_help','Use a centrally managed provider profile. Its model and generation defaults remain reusable across DerridAI workflows.')" :empty-title="i18n.t('pdf_corpus.no_provider_profiles','No LLM provider profiles are configured')" :empty-help="i18n.t('pdf_corpus.no_provider_profiles_help','Create a provider profile or use the manual compatibility settings below.')" :manage-label="i18n.t('pdf_corpus.manage_providers','Manage provider profiles')" :model-not-set-label="i18n.t('pdf_corpus.model_not_set','model not set')" :default-label="i18n.t('ui.default','Default')" :concurrent-label="i18n.t('pdf_corpus.concurrent_requests','max concurrent request(s)')" :context-label="i18n.t('providers.context_tokens','context tokens')" @manage="manageProviders" />
        <p v-if="selectedProviderId&&selectedProfileModel" class="provider-model-summary"><b>{{i18n.t('pdf_corpus.profile_model','Profile model')}}:</b> <code>{{selectedProfileModel}}</code> · {{i18n.t('pdf_corpus.profile_model_help','New corpus builds use this provider profile model by default.')}}</p>
        <label v-if="selectedProviderId&&providerProfiles.length>1" class="escalation-field" for="pdf-corpus-review-provider"><span><b>{{i18n.t('pdf_corpus.escalation_provider','Escalation provider')}}</b><small>{{i18n.t('pdf_corpus.escalation_provider_help','Optional fallback used only after the primary provider exhausts structured-output retries.')}}</small></span><select id="pdf-corpus-review-provider" v-model="selectedReviewProviderId" class="control"><option value="">{{i18n.t('pdf_corpus.no_escalation_provider','None — keep failures for human review')}}</option><option v-for="profile in providerProfiles" :key="profile.id" :value="profile.id" :disabled="profile.id===selectedProviderId">{{profile.name||profile.id}} · {{profile.model||i18n.t('pdf_corpus.model_not_set','model not set')}}</option></select></label>
      </div>

      <CorpusRecordSizingSettings v-model="recordSizing" :disabled="buildRunning||busy!==''" />

      <CorpusExecutionSettings class="execution-config" :generation="effectiveGeneration" :stage-limits="stageLimits" :max-concurrent-requests="maxConcurrentRequests" :use-profile-defaults="useProfileDefaults" :disabled="buildRunning||busy!==''" @update:generation="generationOverrides=$event" @update:stage-limits="stageLimits=$event" @update:max-concurrent-requests="maxConcurrentRequests=$event" @update:use-profile-defaults="useProfileDefaults=$event" />

      <div class="build-launch-row">
        <div class="launch-copy"><b>{{i18n.t('pdf_corpus.ready_to_build','Ready to build')}}</b><span>{{selectedAsset?selectedAsset.filename:i18n.t('pdf_corpus.choose_source_prompt','Choose a source PDF to continue.')}}</span></div>
        <div v-if="!contextSafe" class="context-blocker" role="alert">{{i18n.tf('pdf_corpus.context_start_blocked','Increase the context window or reduce the segmentation window/output budget before starting. Approximate minimum: {count} tokens.',{count:requiredContext.toLocaleString()})}}</div>
        <button type="button" class="btn primary build-button" @click="startBuild" :disabled="!selectedAssetId||busy!==''||buildRunning||!contextSafe">{{busy==='build'?i18n.t('pdf_corpus.starting','Starting…'):i18n.t('pdf_corpus.build_records','Build record set')}}</button>
      </div>

      <details v-if="selectedAsset?.pages?.length" class="advanced-config page-mapping-config">
        <summary>{{i18n.t('pdf_corpus.page_mapping','Printed-page mapping')}}</summary>
        <PdfPageLabelEditor :pages="selectedAsset.pages||[]" :disabled="busy!==''||Boolean(buildRunning&&currentBuild?.asset_id===selectedAssetId)" @save="savePageLabels" />
      </details>

      <details v-if="!selectedProviderId" :open="advancedOpen" class="advanced-config" @toggle="advancedOpen=($event.currentTarget as HTMLDetailsElement).open">
        <summary>{{i18n.t('pdf_corpus.manual_provider','Manual provider compatibility settings')}}</summary>
        <p class="help">{{i18n.t('pdf_corpus.manual_provider_help','Used only when no provider profile is selected. Provider profiles are recommended because credentials remain server-owned and resumable builds can reuse the same configuration.')}}</p>
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
              <button v-if="canRetryMetadata" type="button" class="btn" @click="resumeBuild" :disabled="busy!==''">{{i18n.t('pdf_corpus.retry_metadata_failures','Retry incomplete metadata')}}</button>
              <a v-if="currentBuild.publication" class="btn primary" :href="pdfCorpusApi.publicationUrl(currentBuild.publication.publication_id)">{{i18n.t('pdf_corpus.download_jsonl','Download JSONL')}}</a><button v-else-if="canPublish" type="button" class="btn primary" @click="publish({download:false})" :disabled="busy!==''">{{i18n.t('pdf_corpus.finalize_publish','Finalize & publish')}}</button>
            </div>
          </div>
          <CorpusBuildProgress :status="currentBuild.status" :stage="currentBuild.stage" :progress="currentBuild.progress||0" :record-count="currentBuild.record_count||0" :review-count="currentBuild.needs_review_count||0" :accepted-count="currentBuild.accepted_count||0" :error="currentBuild.error" :warnings="currentBuild.warnings||[]" :validation="currentBuild.validation||null" :llm-metrics="currentBuild.llm_metrics||null" :unresolved-count="currentBuild.boundary_review_count||currentBuild.segmentation_unresolved_regions?.length||0" :segmentation-telemetry="{candidateCount:currentBuild.boundary_candidate_count||0,deterministicSplits:currentBuild.boundary_deterministic_split_count||0,deterministicKeeps:currentBuild.boundary_deterministic_keep_count||0,llmAdjudications:currentBuild.boundary_llm_adjudication_count||0,llmBatchCalls:currentBuild.boundary_llm_batch_call_count||0,llmSplits:currentBuild.boundary_llm_split_count||0,llmKeeps:currentBuild.boundary_llm_keep_count||0,provisionalSplits:currentBuild.provisional_boundary_count||0,sizeOptimizedSplits:currentBuild.size_optimized_boundary_count||0,absoluteSafetySplits:currentBuild.absolute_safety_boundary_count||0,budgetSkipped:currentBuild.boundary_budget_skipped_count||0,classifierFailures:currentBuild.boundary_classifier_failure_count||0,reviewCount:currentBuild.boundary_review_count||0}" />
          <CorpusQualitySummary v-if="!awaitingManifestReview" :build="currentBuild" />
          <section v-if="awaitingManifestReview" class="manifest-gate" aria-labelledby="manifest-review-title">
            <div><h3 id="manifest-review-title">{{i18n.t('pdf_corpus.manifest_review_required','Review document structure')}}</h3><p>{{i18n.t('pdf_corpus.manifest_review_required_help','Confirm the detected work-level metadata and printed-page mapping before DerridAI lets those values propagate into semantic segmentation and generated records.')}}</p></div>
            <button type="button" class="btn primary" @click="confirmManifest" :disabled="busy!==''||!contextSafe">{{i18n.t('pdf_corpus.confirm_manifest_continue','Confirm document & continue')}}</button>
          </section>
          <section v-if="retryingSegmentation" class="build-guidance running-guidance" role="status" aria-live="polite">
            <span class="guidance-icon" aria-hidden="true">↻</span>
            <div><h3>{{i18n.t('pdf_corpus.retry_in_progress','Retrying unresolved segmentation')}}</h3><p>{{i18n.t('pdf_corpus.retry_in_progress_help','DerridAI has resumed from the last safe checkpoint. The retry action is locked while this run is active; watch the stage and progress here or on Home.')}}</p></div>
          </section>
          <section v-else-if="currentBuild.status==='failed'||currentBuild.status==='interrupted'||currentBuild.status==='cancelled'" class="build-guidance failure-guidance" role="alert">
            <span class="guidance-icon" aria-hidden="true">!</span>
            <div><h3>{{i18n.t('pdf_corpus.build_stopped_title','Build stopped before completion')}}</h3><p>{{currentBuild.error||i18n.t('pdf_corpus.build_stopped_help','Completed checkpoints were preserved. Review the provider and execution settings above, then resume from the last safe checkpoint.')}}</p><small>{{i18n.t('pdf_corpus.build_stopped_checkpoint','Resuming does not restart completed stages or discard validated records.')}}</small></div>
          </section>
          <section v-if="segmentationNeedsReview" class="segmentation-blocked segmentation-review-localized" role="status" aria-labelledby="segmentation-review-title">
            <div><h3 id="segmentation-review-title">{{i18n.t('pdf_corpus.segmentation_review_title','Localized segmentation review')}}</h3><p>{{i18n.t('pdf_corpus.segmentation_review_help','The corpus was constructed successfully. A small number of boundary decisions may still need review; these are boundary-level questions and do not mark the neighboring records as failed. Metadata enrichment continues normally.')}}</p></div>
            <details v-if="currentBuild.segmentation_unresolved_regions?.length"><summary>{{i18n.tf('pdf_corpus.unresolved_count','{count} boundary decision(s) to review',{count:currentBuild.segmentation_unresolved_regions.length})}}</summary><ul><li v-for="(region,index) in currentBuild.segmentation_unresolved_regions.slice(0,20)" :key="index"><code>{{region.after_block_id||region.left_block_id||region.start_block_id||'?'}}</code> → <code>{{region.next_block_id||region.right_block_id||region.end_block_id||'?'}}</code><span v-if="region.reason"> · {{region.reason}}</span></li></ul></details>
          </section>
          <details v-if="currentBuild.manifest&&Object.keys(currentBuild.manifest).length" class="manifest-details" :open="awaitingManifestReview">
            <summary>{{i18n.t('pdf_corpus.document_manifest','Document manifest')}} · {{i18n.t('pdf_corpus.revision','revision')}} {{currentBuild.manifest_revision||1}}</summary>
            <DocumentManifestEditor :manifest="currentBuild.manifest||{}" :disabled="buildRunning||busy!==''" @save="saveManifest" />
          </details>
          <div class="provenance-strip"><span>SHA {{currentBuild.source_sha256?.slice(0,12)}}…</span><span>{{currentBuild.model||selectedProfileModel||i18n.t('pdf_corpus.provider_default','Provider default')}}</span><span>{{currentBuild.schema_version}}</span><span>{{currentBuild.segmentation_prompt_version}}</span></div>
        </section>

        <section v-if="hasRecordTopology&&currentBuild" class="review-handoff" :data-state="currentBuild.status" role="status">
          <div><b>{{currentBuild.status==='published'?i18n.t('pdf_corpus.flow_published_title','Corpus published'):currentBuild.status==='ready'?i18n.t('pdf_corpus.flow_ready_title','Review complete'):i18n.t('pdf_corpus.flow_review_title','Review generated records')}}</b><span>{{currentBuild.status==='published'?i18n.t('pdf_corpus.flow_published_help','The reviewed JSONL is finalized and ready to download.'):currentBuild.status==='ready'?i18n.t('pdf_corpus.flow_ready_help','All records are accepted. DerridAI will finalize the publication automatically.'):i18n.t('pdf_corpus.flow_review_help','Accept, reject, merge, or split records. Accepting the final pending record automatically finalizes the JSONL; there is no separate publish step.')}}</span></div>
          <strong>{{currentBuild.accepted_count||0}} / {{currentBuild.record_count||0}} {{i18n.t('pdf_corpus.accepted_label','accepted')}}</strong>
        </section>

        <section v-if="hasRecordTopology" class="review-toolbar" :aria-label="i18n.t('pdf_corpus.review_controls','Record review controls')">
          <label class="check"><input v-model="reviewOnly" type="checkbox"> {{i18n.t('pdf_corpus.review_only','Needs review only')}}</label>
          <label class="sr-only" for="pdf-corpus-record-search">{{i18n.t('pdf_corpus.search_records','Search generated records')}}</label><input id="pdf-corpus-record-search" v-model="recordQuery" class="control" :placeholder="i18n.t('pdf_corpus.search_records','Search generated records')">
          <span>{{recordTotal}} {{i18n.t('pdf_corpus.matches','matches')}} · {{currentBuild?.accepted_count||0}} {{i18n.t('pdf_corpus.accepted_label','Accepted')}} · {{currentBuild?.rejected_count||0}} {{i18n.t('pdf_corpus.rejected','Rejected')}} · {{reviewRemaining}} {{i18n.t('pdf_corpus.remaining','remaining')}}</span><div class="review-bulk"><button type="button" class="btn small" @click="bulkDisposition('accepted')" :disabled="busy!==''||recordTotal===0">{{i18n.t('pdf_corpus.accept_all','Accept all')}}</button><button type="button" class="btn small" @click="bulkDisposition('rejected')" :disabled="busy!==''||recordTotal===0">{{i18n.t('pdf_corpus.reject_all','Reject all')}}</button><button type="button" class="btn small" @click="focusView=true" :disabled="!selectedRecord">{{i18n.t('pdf_corpus.focus_view','Focus view')}}</button></div>
          <div class="pager"><button type="button" class="btn small" @click="previousPage" :disabled="recordOffset===0">{{i18n.t('ui.previous','Previous')}}</button><span>{{pageNumber}} / {{pageCount}}</span><button type="button" class="btn small" @click="nextPage" :disabled="recordOffset+pageSize>=recordTotal">{{i18n.t('ui.next','Next')}}</button></div>
        </section>

        <section v-if="hasRecordTopology" class="review-grid">
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

          <section ref="recordListEl" class="records-pane" :aria-labelledby="'pdf-corpus-records-pane'">
            <div class="pane-head"><b id="pdf-corpus-records-pane">{{i18n.t('pdf_corpus.generated_records','Generated records')}}</b><span>{{recordTotal}}</span></div>
            <button v-for="record in records" :key="record.record_id" type="button" class="record-row" :class="{active:record.record_id===selectedRecordId}" :aria-current="record.record_id===selectedRecordId?'true':undefined" @click="selectRecord(record)">
              <span class="record-state" :data-state="record.rejected?'rejected':record.needs_review?'review':record.accepted?'accepted':'ready'" aria-hidden="true"></span>
              <span><b>{{record.record_id}}</b><small>{{i18n.t('pdf_corpus.pages','pp.')}} {{record.page_start}}–{{record.page_end}} · {{record.text_length.toLocaleString()}} {{i18n.t('pdf_corpus.characters','chars')}}</small><small>{{record.rejected?i18n.t('pdf_corpus.rejected','Rejected'):record.needs_review?(record.review_reason||i18n.t('pdf_corpus.needs_review','Needs review')):record.accepted?i18n.t('pdf_corpus.accepted_label','Accepted'):i18n.t('pdf_corpus.ready_acceptance','Ready for acceptance')}}</small></span>
            </button>
            <div v-if="recordsLoading" class="rail-empty" role="status">{{i18n.t('pdf_corpus.loading_records','Loading generated records…')}}</div><div v-else-if="!records.length" class="rail-empty">{{i18n.t('pdf_corpus.no_records_filter','No records match this review filter.')}} <button type="button" class="btn small" @click="reviewOnly=false;recordQuery=''">{{i18n.t('pdf_corpus.show_all_records','Show all records')}}</button></div>
          </section>

          <aside class="inspector-pane" :aria-label="i18n.t('pdf_corpus.record_inspector','Record inspector')">
            <template v-if="selectedRecord">
              <div class="pane-head"><b>{{selectedRecord.record_id}}</b><span>{{selectedRecord.rejected?i18n.t('pdf_corpus.rejected','Rejected'):selectedRecord.needs_review?i18n.t('pdf_corpus.needs_review','Needs review'):selectedRecord.accepted?i18n.t('pdf_corpus.accepted_label','Accepted'):i18n.t('pdf_corpus.ready','Ready')}}</span></div>
              <div class="inspector-actions"><button type="button" class="btn small" @click="merge('previous')" :disabled="busy!==''||!canMergePrevious">{{i18n.t('pdf_corpus.merge_previous','Merge previous')}}</button><button type="button" class="btn small" @click="merge('next')" :disabled="busy!==''||!canMergeNext">{{i18n.t('pdf_corpus.merge_next','Merge next')}}</button><button type="button" class="btn small" @click="undoReview" :disabled="busy!==''">{{i18n.t('pdf_corpus.undo','Undo')}}</button><button type="button" class="btn small" @click="rerunMetadata" :disabled="busy!==''">{{i18n.t('pdf_corpus.rerun_metadata','Rerun metadata')}}</button><button type="button" class="btn small" @click="focusView=true">{{i18n.t('pdf_corpus.focus_view','Focus view')}}</button><button type="button" class="btn small danger" @click="rejectRecord" :disabled="busy!==''">{{i18n.t('pdf_corpus.reject','Reject')}}</button><button type="button" class="btn small primary" @click="toggleAccept" :disabled="busy!==''">{{selectedRecord.accepted?i18n.t('pdf_corpus.reopen','Reopen'):i18n.t('pdf_corpus.accept','Accept')}}</button></div>
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

    <CorpusRecordFocusReview v-if="focusView&&selectedRecord" :record="selectedRecord" :busy="busy!==''" :can-merge-previous="canMergePrevious" :can-merge-next="canMergeNext" @close="focusView=false" @accept="setDisposition('accepted')" @reject="setDisposition('rejected')" @skip="skipRecord" @undo="undoReview" @merge="merge" />
  </section>
</template>

<style scoped>
.corpus-builder{padding:20px 22px 32px;display:grid;gap:14px}.builder-header{display:flex;justify-content:space-between;gap:24px;align-items:flex-end}.builder-header h1{font-size:26px;margin:3px 0 6px}.builder-header p{margin:0;max-width:850px;color:var(--muted);line-height:1.5}.eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);font-weight:700}.header-actions,.summary-actions,.inspector-actions,.pager{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.status-region:focus{outline:none}.builder-message{padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--soft);font-size:12px}.builder-message.error,.build-warning{border-color:#c96b6b;background:#fff2f2;color:#7d2222}.builder-setup{display:grid;grid-template-columns:minmax(280px,.9fr) minmax(420px,1.35fr);gap:12px;align-items:start;border:1px solid var(--line);background:var(--card);border-radius:14px;padding:14px}.setup-card{min-width:0;height:100%;display:grid;align-content:start;gap:8px;padding:13px;border:1px solid var(--line);border-radius:12px;background:linear-gradient(180deg,#fff,#fbfcfd)}.setup-source,.provider-area{display:grid;gap:8px}.setup-card-heading{display:grid;gap:3px}.setup-card-heading b{font-size:12px}.setup-card-heading small{font-size:10px!important;line-height:1.45}.builder-setup label{font-size:10px;font-weight:700;color:var(--muted)}.builder-setup small{font-size:9px;color:var(--muted)}.execution-config,.advanced-config,.build-launch-row{grid-column:1/-1}.advanced-config{grid-column:1/-1}.advanced-config summary{cursor:pointer;font-size:10px;font-weight:700}.escalation-field{display:grid;grid-template-columns:minmax(150px,.7fr) minmax(220px,1fr);gap:12px;align-items:center;padding:10px 11px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}.escalation-field>span{display:grid;gap:2px}.escalation-field b{font-size:10px}.escalation-field small{font-size:9px;line-height:1.4;color:var(--muted)}.advanced-grid{display:grid;grid-template-columns:max-content 1fr max-content 1fr;gap:8px 10px;margin-top:8px;align-items:center}.build-launch-row{display:grid;grid-template-columns:minmax(180px,1fr) minmax(280px,1.2fr) auto;gap:12px;align-items:center;padding:11px 12px;border:1px solid var(--line);border-radius:11px;background:var(--soft)}.launch-copy{display:grid;gap:2px;min-width:0}.launch-copy b{font-size:10px}.launch-copy span{font-size:9px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.build-button{min-height:38px;padding-inline:17px}.context-blocker{padding:8px 10px;border-radius:8px;background:#fff2f2;color:#7d2222;font-size:9px}.builder-workspace{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:720px;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--card)}.build-rail{border-inline-end:1px solid var(--line);background:var(--soft);padding:10px;overflow:auto}.rail-title,.pane-head{display:flex;justify-content:space-between;align-items:center;gap:8px}.rail-title{padding:6px 4px 10px}.rail-title>div{display:grid}.rail-title b,.pane-head b{font-size:11px}.rail-title span,.pane-head span{font-size:9px;color:var(--muted)}.icon-button{border:0;background:transparent;cursor:pointer;font-size:18px}.build-row{width:100%;border:1px solid transparent;background:transparent;border-radius:10px;padding:9px;display:grid;grid-template-columns:10px 1fr;gap:9px;text-align:start;cursor:pointer}.build-row:hover,.build-row.active{background:var(--card);border-color:var(--line)}.build-row span:last-child{display:grid;gap:2px;min-width:0}.build-row b{font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.build-row small{font-size:8px;color:var(--muted)}.status-dot,.record-state{width:8px;height:8px;border-radius:50%;background:#777;margin-top:3px}.status-dot[data-status="ready"],.status-dot[data-status="published"],.record-state[data-state="accepted"]{background:#287a4c}.status-dot[data-status="running"],.status-dot[data-status="queued"]{background:#8e6815}.status-dot[data-status="failed"],.status-dot[data-status="interrupted"],.record-state[data-state="review"],.record-state[data-state="rejected"]{background:#a13f3f}.build-main{min-width:0;display:grid;align-content:start}.build-summary{padding:15px 16px;border-bottom:1px solid var(--line);display:grid;gap:10px}.summary-top{display:flex;justify-content:space-between;gap:18px}.summary-top h2{margin:2px 0;font-size:18px}.summary-top p{margin:0;font-size:9px;color:var(--muted)}.build-status-line,.provenance-strip,.validation-strip{display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:9px;color:var(--muted)}.pill{border:1px solid var(--line);border-radius:999px;padding:3px 7px;text-transform:uppercase;font-weight:800;letter-spacing:.04em}.progress-track{height:7px;border-radius:999px;background:var(--soft);overflow:hidden}.progress-track span{display:block;height:100%;background:var(--accent);transition:width .25s}.provenance-strip code{font-size:8px}.manifest-details{border:1px solid var(--line);border-radius:9px;padding:8px 10px}.manifest-details>summary{cursor:pointer;font-size:9px;font-weight:800}.build-warning{display:grid;gap:3px;padding:9px;border:1px solid;border-radius:8px;font-size:10px}.warnings{font-size:10px}.warnings summary{cursor:pointer;font-weight:700}.validation-strip{padding:7px 9px;border-radius:8px;background:#edf8f1}.validation-strip.invalid{background:#fff6e5;color:#604300}.provider-model-summary{margin:6px 0 0;font-size:9px;color:var(--muted)}.provider-model-summary code{font-size:9px;color:var(--text)}.review-handoff{display:flex;justify-content:space-between;gap:18px;align-items:center;padding:11px 13px;border-bottom:1px solid var(--line);background:var(--soft)}.review-handoff>div{display:grid;gap:2px}.review-handoff b{font-size:11px}.review-handoff span{font-size:9px;color:var(--muted);line-height:1.4}.review-handoff>strong{white-space:nowrap;font-size:10px}.review-handoff[data-state="published"]{background:#edf8f1}.review-toolbar{display:grid;grid-template-columns:auto minmax(180px,1fr) auto auto auto;gap:10px;align-items:center;padding:9px 12px;border-bottom:1px solid var(--line);font-size:9px}.check{display:flex;gap:6px;align-items:center}.review-bulk{display:flex;gap:6px;flex-wrap:wrap}.danger{border-color:#a13f3f!important;color:#7d2222!important}.review-grid{display:grid;grid-template-columns:minmax(360px,1.2fr) minmax(240px,.65fr) minmax(300px,.85fr);min-height:650px}.source-pane,.records-pane,.inspector-pane{min-width:0;overflow:auto;max-height:76vh}.source-pane,.records-pane{border-inline-end:1px solid var(--line)}.pane-head{position:sticky;top:0;z-index:3;background:var(--card);padding:9px 11px;border-bottom:1px solid var(--line)}.source-page-nav{display:flex;align-items:center;justify-content:center;gap:8px;padding:6px 10px;border-bottom:1px solid var(--line);font-size:9px;color:var(--muted)}.source-blocks{display:grid;gap:8px;padding:10px}.source-block{border:1px solid var(--line);border-radius:9px;padding:9px;position:relative}.source-block.evidence-block{box-shadow:inset 3px 0 0 var(--accent)}[dir="rtl"] .source-block.evidence-block{box-shadow:inset -3px 0 0 var(--accent)}.source-block header{display:flex;justify-content:space-between;gap:8px;font-size:8px;color:var(--muted)}.source-block p{white-space:pre-wrap;font:13px/1.52 Georgia,serif;margin:7px 0}.split-button{display:block;width:100%;border:0;border-top:1px dashed var(--line);background:transparent;color:var(--muted);font-size:8px;padding:5px;cursor:pointer}.evidence-toggle{display:block;width:100%;margin:5px 0;border:1px solid var(--line);border-radius:7px;background:var(--soft);color:var(--text);font-size:8px;padding:6px;text-align:start;cursor:pointer}.evidence-toggle[aria-pressed="true"]{border-color:var(--accent);box-shadow:inset 3px 0 0 var(--accent)}.record-row{width:100%;border:0;border-bottom:1px solid var(--line);background:transparent;padding:10px;display:grid;grid-template-columns:10px 1fr;gap:8px;text-align:start;cursor:pointer}.record-row:hover,.record-row.active{background:var(--soft)}.record-row span:last-child{display:grid;gap:3px}.record-row b{font-size:10px}.record-row small{font-size:8px;color:var(--muted)}.inspector-pane details{border-bottom:1px solid var(--line);padding:10px 12px}.inspector-pane summary{font-size:10px;font-weight:800;cursor:pointer}.inspector-actions{padding:9px 11px;border-bottom:1px solid var(--line)}.record-text{white-space:pre-wrap;font:13px/1.55 Georgia,serif;margin-top:9px}.metadata-json{width:100%;min-height:230px;resize:vertical;font:10px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;border:1px solid var(--line);border-radius:8px;padding:8px;background:var(--bg);color:var(--text);margin:7px 0}.help{font-size:9px;color:var(--muted);line-height:1.45}.evidence-list{display:grid;gap:8px;margin-top:8px}.evidence-list button{display:grid;gap:2px;padding:7px;background:var(--soft);border:1px solid transparent;border-radius:7px;text-align:start;color:inherit;cursor:pointer}.evidence-list button.active{border-color:var(--accent)}.evidence-list b{font-size:9px}.evidence-list span,.evidence-list small{font-size:8px;color:var(--muted)}.rail-empty,.inspector-empty,.builder-empty{padding:26px 14px;color:var(--muted);font-size:10px}.builder-empty{min-height:420px;display:grid;place-content:center;text-align:center}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.btn:focus-visible,.control:focus-visible,.build-row:focus-visible,.record-row:focus-visible,.icon-button:focus-visible,.split-button:focus-visible,.evidence-toggle:focus-visible,.evidence-list button:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.build-guidance{display:grid;grid-template-columns:34px minmax(0,1fr);gap:10px;align-items:start;padding:11px 12px;border:1px solid var(--line);border-radius:10px}.build-guidance .guidance-icon{width:30px;height:30px;display:grid;place-items:center;border-radius:8px;font-weight:850}.build-guidance h3{margin:0 0 3px;font-size:12px}.build-guidance p{margin:0;font-size:10px;line-height:1.45}.build-guidance small{display:block;margin-top:4px;font-size:9px;color:inherit;opacity:.8}.running-guidance{background:var(--accent-soft,#eef6f2);border-color:var(--accent-soft-2,#dce9e3)}.running-guidance .guidance-icon{background:#fff;color:var(--accent-2,var(--accent))}.failure-guidance{background:#fff7f7;border-color:#e7b4b4;color:#7d2222}.failure-guidance .guidance-icon{background:#fff;color:#9a3636}.manifest-gate{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:start;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}.manifest-gate h3{margin:0 0 4px;font-size:13px}.manifest-gate p{margin:0;max-width:800px;font-size:10px;line-height:1.45}.segmentation-blocked{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:start;padding:12px;border:1px solid #c96b6b;border-radius:10px;background:#fff7f7}.segmentation-blocked h3{margin:0 0 4px;font-size:13px}.segmentation-blocked p{margin:0;max-width:800px;font-size:10px;line-height:1.45}.segmentation-blocked details{grid-column:1/-1;font-size:9px}.segmentation-blocked ul{margin:6px 0 0;padding-inline-start:20px}.segmentation-blocked code{font-size:8px}.segmentation-review-localized{border-color:#c6a85b;background:#fffaf0;color:#5e4a12}@media(prefers-reduced-motion:reduce){.progress-track span{transition:none}}
@media(max-width:1250px){.review-grid{grid-template-columns:1fr .72fr}.inspector-pane{grid-column:1/-1;border-top:1px solid var(--line);max-height:none}.source-pane,.records-pane{max-height:65vh}}
@media(max-width:900px){.manifest-gate,.segmentation-blocked{grid-template-columns:1fr}.builder-header{align-items:flex-start;flex-direction:column}.builder-setup{grid-template-columns:1fr}.build-launch-row{grid-template-columns:1fr}.escalation-field{grid-template-columns:1fr}.advanced-grid{grid-template-columns:1fr}.advanced-config{grid-column:auto}.builder-workspace{grid-template-columns:1fr}.build-rail{border-inline-end:0;border-bottom:1px solid var(--line);max-height:220px}.review-toolbar{grid-template-columns:1fr 1fr}.review-grid{grid-template-columns:1fr}.source-pane,.records-pane{border-inline-end:0;border-bottom:1px solid var(--line);max-height:none}}
</style>
