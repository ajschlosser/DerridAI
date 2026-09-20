/* Copyright 2026 Aaron John Schlosser, PhD. */
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import PdfWorker from "pdfjs-dist/legacy/build/pdf.worker.mjs?worker";
import { diffWordsWithSpace } from "diff";
import {
  dockCollapsedSummary,
  isActiveJobStatus,
  isTerminalJobStatus,
  jobIdsToPruneFromDock,
  jobProgressPercent,
  shouldMountOperationDock,
  statusBadgeTone,
} from "../domain/operationsDock";
import { mountOperationsPanel, unmountOperationsPanel } from "./operationsPanelHost";
import { formatDuration } from "../domain/operationsPanel";
import { cloneAuditValue, compareValues, computeRecordFingerprint, sameValue, sortRows } from "../domain/recordValues";
import { compressUrlState, decompressUrlState } from "../domain/urlState";
import { countOccurrences, flattenValueList, parseJsonl, subsetRuleMatches, subsetValueText, valueMatches } from "../domain/recordQuery";
import { DB_NAME, createWorkspaceDb, deleteAllDerridaiBrowserState as deleteAllDerridaiBrowserStateCompat } from "../services/workspaceDb";
import { fullCitation, inlineCitation, mlaAuthorName, mlaPageSpan, mlaSentence } from "../domain/citations";
import { describeRecordsFile, serializableRecordsFile } from "../domain/recordsFiles";
import {
  applyAppearance as applyAppearanceCompat,
  applyUiTheme as applyUiThemeCompat,
  setTranslationDictionary as setTranslationDictionaryCompat,
  syncColorScheme as syncColorSchemeCompat,
  tr as trCompat,
  trf as trfCompat,
  translateDynamicUiValue as translateDynamicUiValueCompat,
  translateLegacyDom as translateLegacyDomCompat,
} from "./legacyCompat.js";
import { createVectorCollectionBridge } from "./vectorCollectionBridge";

pdfjsLib.GlobalWorkerOptions.workerPort = new PdfWorker();

const state = {
  userContext: null,
  files: [],
  activeFileId: null,
  view: "home",
  selected: {},
  searches: {},
  listFilters: {},
  pages: {},
  pageSize: 100,
  sorts: {},
  globalSearch: "",
  globalFilters: [],
  globalSort: { key: "__file", dir: 1 },
  globalPage: 1,
  globalSearchMode: "traditional",
  dbSearchMethod: "similarity",
  dbSearchWhere: {},
  dbSearchFetchK: 100,
  dbSearchLambda: 0.7,
  globalAdvancedOpen: false,
  searchFacetFilters: {},
  searchDatabaseRan: false,
  worksSearch: "",
  workOverview: "",
  researcherRecordId: "",
  researcherCompareA: "",
  researcherCompareB: "",
  annotationView: "works",
  annotationSearch: "",
  serverAnnotations: [],
  serverAnnotationsStore: "",
  annotationsFetchedAt: 0,
  dashboardMetricIndex: 0,
  lastViewedRecord: null,
  globalSearchAutoRun: false,
  searchResultLayouts: {traditional:"compact",database:"cards"},
  foregroundUpsertCancelRequested: false,
  recordFind: "",
  recordFindKey: "",
  pdf: { doc: null, file: null, url: "", name: "", title: "", author: "", page: 1, rotation: 0, text: "", search: "", relatedSearch: "", extractError: "", extractionSource: "" },
  compareA: "",
  compareB: "",
  compareMode: "workspace",
  comparePasteA: "",
  comparePasteB: "",
  compareSourceA: "library",
  compareSourceB: "library",
  compareFilter: "changed",
  stores: [],
  storesLastFetchedAt: 0,
  vectorAutoCreateRequested: false,
  activeStore: "",
  storeSearchResults: [],
  storeSearchLoading: false,
  storeSearchMessage: "",
  storeSearchSort: {key:"similarity",dir:-1},
  storeRecords: [],
  storeCount: 0,
  storePage: 1,
  storePageSize: 50,
  storeQuery: "",
  storeSearchMode: "",
  storeWork: "",
  storeSort: {key:"",dir:1},
  storeFilters: {},
  storeWorks: [],
  storeWorkStats: [],
  storeWorksStore: "",
  storeBrowseMode: "works",
  vectorTab: "overview",
  vectorCollectionFilter: "",
  health: null,
  llmStatus: null,
  reviewSelection: new Set(),
  selectedEvidence: {},
  researcherProviderProfiles: [],
  translations: {locale:"en-US",dictionary:{},base:{}},
  navHistory: [],
  navForward: [],
  sidebarCollapsed: false,
  collectionsCollapsed: false,
  operationToastsMinimized: false,
  operationStackPosition: null,
  collapsedPanels: {},
  providerStatuses: {},
  providerWarmups: {},
  tableColumns: {},
  upsertState: {},
  upsertIgnored: {},
  storePresence: {},
  storePresenceIds: {},
  storePresenceCheckedAt: {},
  operationProgress: {},
  jobs: [],
  jobsLastFetched: 0,
  jobsPollTimer: null,
  jobApplied: {},
  upsertJobApplied: {},
  foregroundUpsertActive: false,
  warmup: {status:"idle",message:""},
  faqSearch: "",
  faqPage: 1,
  faqExpanded: {},
  ragConfig: {
    source_collection: "",
    locales: ["en","fr"],
    search_types: ["similarity","lexical","mmr"],
    k: 64,
    fetch_k: 500,
    lambda_mult: 0.7,
    rrf_k: 60,
    rerank_top_n: 24,
    reranker: "cross_encoder",
    cross_encoder_model: "cross-encoder/ms-marco-MiniLM-L-6-v2",
    query_decomposition: true,
    query_decomposition_num_predict: 768,
    response_language: "auto",
    evidence_record_char_limit: 12000,
    evidence_total_char_limit: 120000,
    bind_citations: true,
    include_works_cited: true,
    auto_grade: false,
    auto_grade_provider_profile_id: "",
    provider_profile_id: "",
    skip_retrieval: false,
    prompt: "",
    instructions: "",
    history: [],
    run_history: []
  },
  appConfig: {
    chat_provider: "ollama",
    chat_model: "gemma4:e2b",
    embedding_provider: "ollama",
    embedding_model: "bge-m3:latest",
    ollama_base_url: "http://host.docker.internal:11434",
    ollama_rag_concurrency: 1,
    openai_base_url: "http://host.docker.internal:3001/v1",
    openai_model: "auto",
    openai_model_mode: "auto",
    openai_model_kind: "any",
    openai_api_key: "",
    default_review_preset: "text",
    default_llm_run_mode: "foreground",
    desktop_notifications: false,
    ui_color_theme: "green",
    ui_color_scheme: "system",
    ui_contrast: "system",
    default_provider_profile: "",
    // Loading a model takes memory and time, and evicts whichever model is in use, so it is not done until asked for.
    warm_default_provider_on_start: false,
    review_provider_profile: "",
    provider_profiles: [],
    background_llm: true,
    openai_num_predict: 4096,
    openai_temperature: 0,
    openai_top_p: 1,
    openai_seed: "",
    openai_extra_options: "{}",
    metadata_num_predict: 768,
    text_num_predict: 4096
  },
  llmConfig: {
    model: "gemma4:e2b",
    num_ctx: 16384,
    num_predict: "",
    think: "false",
    temperature: 0,
    top_k: 0,
    top_p: 1,
    min_p: "",
    repeat_penalty: 1.1,
    seed: "",
    mirostat: 0,
    mirostat_eta: "",
    mirostat_tau: "",
    keep_alive: "10m",
    extra_options: "{}"
  },
  storageReady: false,
};

function syncColorScheme(){
  return syncColorSchemeCompat(state);
}
function applyUiTheme(theme){
  return applyUiThemeCompat(state, theme);
}
function applyAppearance(patch={}){
  return applyAppearanceCompat(state, patch);
}

function setTranslationDictionary(locale,dictionary={},base={},info={}){
  return setTranslationDictionaryCompat(state, locale, dictionary, base, info);
}
function tr(key,fallback=""){
  return trCompat(state, key, fallback);
}
function trf(key,fallback,values={}){
  return trfCompat(state, key, fallback, values);
}
function translateDynamicUiValue(value){
  return translateDynamicUiValueCompat(state, value);
}
function translateLegacyDom(root=document.querySelector("#main")){
  return translateLegacyDomCompat(state, root);
}

const labels = {
  record_id:"Record ID",work:"Work",document_author:"Document author",edition:"Edition",year:"Year",
  page_start:"Page start",page_end:"Page end",region_type:"Region type",region_author:"Region author",
  primary_text:"Primary text",canonical_work_id:"Canonical work ID",speaker:"Speaker",
  position_holder:"Position holder",target:"Target",discourse_role:"Discourse role",
  proposition_status:"Proposition status",semantic_function:"Semantic function",stance:"Stance",
  claim_scope:"Claim scope",is_direct_quote:"Direct quote",quoted_speaker:"Quoted speaker",
  quoted_author:"Quoted author",quoted_work:"Quoted work",quoted_position_holder:"Quoted position holder",
  quoted_addressee:"Quoted addressee",quoted_referent:"Quoted referent",quotation_chain:"Quotation chain",
  topics:"Topics",concepts:"Concepts",persons:"Persons",works_referenced:"Works referenced",
  attribution_confidence:"Attribution confidence",semantic_classification_confidence:"Semantic classification confidence",
  extraction_quality:"Extraction quality",needs_review:"Needs review",review_reason:"Review reason",
  document_language:"Document language",original_language:"Original language",document_is_translation:"Document is translation",
  translator:"Translator",publisher:"Publisher",publication_year:"Publication year",publication_place:"Publication place",isbn:"ISBN",document_title:"Document title",short_title:"Short title",original_title:"Original title",cover_url:"Cover URL",inline_citation:"Inline citation",full_citation:"Full citation",text:"Extracted text",text_length:"Text length",updates:"Change history",pdf_file:"PDF file",pdf_page:"PDF page",pdf_pages:"PDF pages",pdf_links:"PDF links",__file:"File",__db_status:"DB status",_chroma_id:"Chroma ID"
};


const viewConfig = [
  {id:"home", label:"Home", icon:"dashboard", section:"Overview"},
  {id:"list", label:"Records", icon:"list", section:"Corpus"},
  {id:"record", label:"Record View", icon:"record", section:"Corpus"},
  {id:"works", label:"Works", icon:"books", section:"Corpus"},
  {id:"global", label:"Search", icon:"search", section:"Corpus"},
  {id:"annotations", label:"Annotations", icon:"record", section:"Corpus"},
  {id:"pdf", label:"Corpus Builder", icon:"pdf", section:"Tools"},
  {id:"compare", label:"Compare", icon:"compare", section:"Tools"},
  {id:"vector", label:"Vector Stores", icon:"database", section:"Tools"},
  {id:"rag", label:"Research", icon:"spark", section:"Research"},
  {id:"faq", label:"Response Library", icon:"books", section:"Research"},
  {id:"responsecache", label:"Response Cache", icon:"database", section:"Research"},
  {id:"providers", label:"LLM Providers", icon:"spark", section:"System"},
  {id:"config", label:"Settings", icon:"gear", section:"System"},
];

const TABLE_DEFAULTS={
  // Record actions are rendered as a dedicated trailing column. Keep the default
  // data columns compact enough to scan on a laptop and let users opt into the
  // rest through the column chooser.
  list:["__db_status","work","page_start","needs_review","text"],
  global:["__db_status","work","page_start","needs_review","text"],
  vector:["_chroma_id","record_id","work","page_start","speaker","needs_review"],
};
const SEARCH_LOADED_COLUMNS=["__db_status","work","page_start","needs_review","text"];

function icon(name){
  const paths={
    dashboard:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    list:'<path d="M5 7h14M5 12h14M5 17h14"/><path d="M3 7h.01M3 12h.01M3 17h.01"/>',
    record:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    books:'<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>',
    search:'<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
    pdf:'<path d="M6 2h9l5 5v15H6z"/><path d="M14 2v6h6M8.5 15h7M8.5 18h5"/>',
    compare:'<path d="M8 7h11M16 4l3 3-3 3M16 17H5M8 14l-3 3 3 3"/>',
    database:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    chart:'<path d="M4 20V10M10 20V4M16 20v-7M22 20v-11"/><path d="M2 20h21"/>',
    upload:'<path d="M12 16V4M7 9l5-5 5 5"/><path d="M5 20h14"/>',
    download:'<path d="M12 4v12M7 11l5 5 5-5"/><path d="M5 20h14"/>',
    edit:'<path d="M4 20h4l11-11-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/>',
    copy:'<rect x="8" y="8" width="11" height="11" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
    filter:'<path d="M3 5h18l-7 8v5l-4 2v-7z"/>',
    spark:'<path d="m12 3 1.2 4.1L17 9l-3.8 1.9L12 15l-1.2-4.1L7 9l3.8-1.9L12 3Z"/><path d="m19 15 .7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7L19 15Z"/>',
    broom:'<path d="m15 3 6 6-8 8-6-6z"/><path d="M7 11 3 15l6 6 4-4M5 17l2 2M8 14l4 4"/>',
    plus:'<path d="M12 5v14M5 12h14"/>',
    refresh:'<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    check:'<path d="m5 12 4 4L19 6"/>',
    history:'<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
    arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
    close:'<path d="m6 6 12 12M18 6 6 18"/>',
    gear:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V21h-4v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H3v-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1L7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V3h4v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9A1.7 1.7 0 0 0 21 10h.1v4H21a1.7 1.7 0 0 0-1.6 1Z"/>',
  };
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]||paths.record}</svg>`;
}

function systemCardHtml(){
  const health=state.health;
  if(!health){
    return `<div class="system-row"><span>API</span><span class="system-value"><i class="status-dot warn"></i>Checking</span></div>
      <div class="system-row"><span>Chroma</span><span class="system-value"><i class="status-dot"></i>Unknown</span></div>
      <div class="system-row"><span>Ollama</span><span class="system-value"><i class="status-dot"></i>Unknown</span></div>`;
  }
  const apiOk=health?.ok===true;
  const chromaOk=health?.chroma?.available===true;
  const ollamaOk=(state.llmStatus||health?.ollama)?.available===true;
  return `<div class="system-row"><span>API</span><span class="system-value"><i class="status-dot ${apiOk?"ok":"bad"}"></i>${apiOk?"Online":"Offline"}</span></div>
    <div class="system-row"><span>Chroma</span><span class="system-value"><i class="status-dot ${chromaOk?"ok":apiOk?"warn":"bad"}"></i>${chromaOk?"Ready":apiOk?"Unavailable":"Unknown"}</span></div>
    <div class="system-row"><span>Ollama</span><span class="system-value"><i class="status-dot ${ollamaOk?"ok":apiOk?"warn":"bad"}"></i>${ollamaOk?"Ready":apiOk?"Unavailable":"Unknown"}</span></div>`;
}

function updateSystemCard(){
  const card=document.querySelector(".system-card");
  if(card)card.innerHTML=systemCardHtml();
}

function currentContext(){
  const f=activeFile(),r=selectedRecord();
  if(state.view==="record"&&r) return {kicker:r.record_id||"Record", title:r.work||"Record", meta:f?.name||""};
  const map={
    home:["Overview","Dashboard","Workspace, vector stores, review activity, and corpus statistics"],
    list:["Corpus",f?.name||"Records",f?`${f.records.length.toLocaleString()} ${tr("dynamic.records","records")}`:"Open a JSONL file"],
    works:["Corpus","Works","Cross-file work overview"],
    global:["Corpus","Global Search","Search and filter every loaded record"],
    annotations:["Corpus","Annotations","Review annotations by work or in recent-activity order"],
    pdf:["Tools",state.pdf.title||"Corpus Builder",state.pdf.name?`${state.pdf.name} · page ${state.pdf.page}`:"Build auditable records or inspect source PDFs"],
    compare:["Tools","Record Comparison","Inspect field and text differences"],
    vector:["Storage","Vector Stores","Persistent local ChromaDB collections"],
    rag:["Research","Research","Run the evidence-grounded DerridAI retrieval and synthesis pipeline"],
    faq:["Research","Response Library","Browse saved RAG questions, answers, evidence, reruns, and grades"],
    responsecache:["Research","Response Cache","Manage cached RAG queries, answers, evidence, and LLM grades separately from corpus vector stores"],
    providers:["System","LLM Providers","Create, configure, test, warm, and reuse LLM provider profiles across every LLM workflow"],
    config:["System","Settings","Application behavior, retrieval defaults, storage, backup, and reset controls"],
  };
  const dynamicTitle=state.view==="list"&&f?.name||state.view==="pdf"&&state.pdf.title;
  const dynamicMeta=state.view==="list"&&f||state.view==="pdf"&&state.pdf.name;
  const key=map[state.view]?state.view:"list";
  const [kickerText,titleText,metaText]=map[key];
  // Static labels are translated; data-driven titles (file names, PDF titles) are not.
  return {
    kicker:tr(`context.${key}.kicker`,kickerText),
    title:dynamicTitle?titleText:tr(`context.${key}.title`,titleText),
    meta:dynamicMeta?metaText:tr(`context.${key}.meta`,metaText),
  };
}

const uid = () => crypto.randomUUID();
async function stableJsonlFileIdentity(text){
  // Shareable URLs can only point back to a browser-local JSONL workspace if
  // the same corpus file resolves to the same identifier on every client. Use
  // a content digest rather than a random tab id. The JSONL payload is already
  // resident as text during import, so hashing does not add another file read.
  const bytes=new TextEncoder().encode(String(text||""));
  const digest=await crypto.subtle.digest("SHA-256",bytes);
  const hex=[...new Uint8Array(digest)].map(value=>value.toString(16).padStart(2,"0")).join("");
  return {id:`jsonl-${hex.slice(0,24)}`,content_hash:hex};
}
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
const label = key => tr(`field.${key}`, labels[key] || key.replaceAll("_"," ").replace(/\b\w/g,m=>m.toUpperCase()));
const display = value => {
  if(value === null || value === undefined || value === "") return "—";
  if(Array.isArray(value)) return value.length ? value.map(v => typeof v === "object" ? JSON.stringify(v) : String(v)).join(", ") : "—";
  if(typeof value === "object") return JSON.stringify(value);
  if(typeof value === "boolean") return value ? tr("runtime.yes","Yes") : tr("runtime.no","No");
  return String(value);
};
const activeFile = () => state.files.find(f => f.id === state.activeFileId) || null;
const selectedIndex = f => Math.max(0, Math.min((f?.records.length || 1)-1, state.selected[f?.id] ?? 0));
const selectedRecord = () => {
  const f = activeFile();
  return f?.records[selectedIndex(f)] || null;
};

// Corpus-derived data is read far more often than it changes. Keep one flattened
// index and memoized derived values instead of rebuilding thousands of row
// wrapper objects on every render/chart/filter pass. Any persisted corpus edit
// invalidates the cache synchronously.
const corpusCache={rows:null,fields:null,memo:new Map(),version:0};
let recordFingerprintCache=new WeakMap();
function invalidateCorpusCache(){
  corpusCache.rows=null;
  corpusCache.fields=null;
  corpusCache.memo.clear();
  corpusCache.version++;
  // Fingerprints are cached by record object identity, but records are edited in
  // place. Drop the cache whenever corpus-derived state changes so sync/status
  // checks never reuse a pre-edit hash.
  recordFingerprintCache=new WeakMap();
}
function allRows(){
  if(corpusCache.rows)return corpusCache.rows;
  const rows=[];
  for(const file of state.files){
    for(let index=0;index<file.records.length;index++)rows.push({file,record:file.records[index],index});
  }
  corpusCache.rows=rows;
  return rows;
}
function memoCorpus(key,builder){
  if(corpusCache.memo.has(key))return corpusCache.memo.get(key);
  const value=builder();
  corpusCache.memo.set(key,value);
  return value;
}
function hasChromaService(){return state.health?.chroma?.available===true}
function hasCorpusDb(){return hasChromaService()&&recordStores().length>0}
function dbUnavailableReason(){
  if(!hasChromaService())return "ChromaDB is unavailable. Start/connect ChromaDB before using database features.";
  if(!recordStores().length)return "Create or restore a corpus vector database first.";
  return "";
}
function isResearcher(){return Boolean(state.userContext&&state.userContext.role!=="admin")}
function hasCapability(capability){
  if(!state.userContext)return false;
  if(state.userContext.role==="admin")return true;
  const capabilities=new Set(state.userContext.capabilities||[]);
  return capabilities.has("*")||capabilities.has(capability);
}
function userCapabilities(){
  return {
    viewSharedPages:hasCapability("page.dashboard"),
    annotate:hasCapability("annotations.write"),
    compare:hasCapability("page.compare"),
    research:hasCapability("rag.run"),
    editLocalRecords:hasCapability("records.edit"),
    manageCorpus:hasCapability("corpus.manage"),
    manageUsers:hasCapability("users.manage"),
    configureProviders:hasCapability("providers.manage"),
  };
}
const pageCapabilities={home:"page.dashboard",list:"page.records",record:"page.record",works:"page.works",global:"page.search",annotations:"page.annotations",pdf:"page.pdf",compare:"page.compare",vector:"page.vector",rag:"page.research",faq:"page.faq",responsecache:"page.response_cache",providers:"page.providers",config:"page.settings"};
function canUse(feature){return Boolean(userCapabilities()[feature]);}
function canAccessPage(view){const capability=pageCapabilities[view];return !capability||hasCapability(capability);}
function setUserContext(user){
  const priorId=state.userContext?.id;
  state.userContext=user||null;
  if(priorId!==state.userContext?.id){state.serverAnnotations=[];state.serverAnnotationsStore="";state.annotationsFetchedAt=0}
  if(!canAccessPage(state.view))state.view="home";
  void refreshResearcherContentPolicy();
}
function viewDisabledReason(view){
  if(!canAccessPage(view))return "This workspace is available to administrators only.";
  if(view==="vector"&&isResearcher()&&!hasChromaService())return dbUnavailableReason();
  if(view==="faq"&&!hasChromaService())return "ChromaDB is unavailable, so the Response Library cannot be opened.";
  if(view==="responsecache"&&!hasChromaService())return "ChromaDB is unavailable, so the response cache cannot be opened.";
  return "";
}
/** @param {Document | Element} [root=document] */
function decorateDisabledControls(root=document){
  root.querySelectorAll?.("button:disabled,input:disabled,select:disabled").forEach(control=>{
    if(control.closest?.(".disabled-control-tooltip"))return;
    const explicit=control.dataset.disabledReason;
    const existingTitle=String(control.title||"").trim();
    const id=(control.id||"").toLowerCase();
    const text=String(control.textContent||"").trim().toLowerCase();
    const pageAction=String(control.dataset.page||"").split(":").at(-1);
    let reason=explicit||existingTitle||"This action is unavailable until its required selection or data is available.";
    if(!explicit&&!existingTitle&&(pageAction==="first"||pageAction==="prev"))reason="You are already on the first page.";
    else if(!explicit&&!existingTitle&&(pageAction==="next"||pageAction==="last"))reason="You are already on the last page.";
    else if(!explicit&&!existingTitle&&control.dataset.up!==undefined)reason="This column is already first.";
    else if(!explicit&&!existingTitle&&control.dataset.down!==undefined)reason="This column is already last.";
    else if(id==="breadcrumbback")reason="There is no earlier navigation location.";
    else if(id==="breadcrumbforward")reason="There is no forward navigation location.";
    else if(id==="loadraghistory")reason="Choose a previous RAG question first.";
    else if(id==="applyjobselected"||id==="applyselectedchanges")reason="Select at least one proposed change first.";
    else if(id==="nukeeverything")reason=tr("config.nuke.type_to_enable_help",'Type "NUKE" exactly to enable this destructive action.');
    else if(id==="linkpdf")reason="The current PDF page is already linked to this record.";
    else if(id==="runsearch")reason="Semantic search is unavailable for precomputed-only collections.";
    else if(["ragmodel","toolmodel","touchmodel"].includes(id))reason="The provider is configured to choose the model automatically.";
    else if(id==="columnadd")reason="Every available field is already shown.";
    else if(id==="importactive")reason="Load and select a JSONL tab first.";
    else if(id==="importall")reason="Load at least one JSONL tab first.";
    else if(["extractpage","extractall","pdfllmclean","pdfllmdraft"].includes(id))reason="Load a PDF page with extractable text first.";
    else if(["pdfllmlink","linkcurrentpdf"].includes(id))reason="Load JSONL records before linking a PDF page.";
    else if(["collectionembeddingprovider","collectionembeddingmodel","saveembeddingsettings"].includes(id))reason="Embedding settings are locked after a collection contains records; create a new empty collection to change them.";
    else if(id==="runtouchup")reason="Configure a reachable LLM provider and model before running this operation.";
    else if(text.includes("cancelling"))reason="Cancellation has already been requested for this operation.";
    else if(/upsert|sync|rag/.test(id))reason=dbUnavailableReason()||reason;
    else if(/prev|older/.test(id))reason="There is no previous item or older version.";
    else if(/next|newer/.test(id))reason="There is no next item or newer version.";
    else if(/merge/.test(id))reason="Load at least two JSONL tabs to merge them.";
    else if(/subset|bulk|export/.test(id))reason="Load JSONL records first.";
    else if(/edit/.test(id))reason="Select a record first.";
    if(explicit)reason=explicit;
    control.title=reason;
    if(control.tagName==="BUTTON"&&!control.closest(".disabled-control-tooltip")){
      const wrapper=document.createElement("span");wrapper.className="disabled-control-tooltip";wrapper.dataset.tooltip=reason;control.parentNode?.insertBefore(wrapper,control);wrapper.appendChild(control);
    }
  });
}
function showAppModal(dialog){
  decorateDisabledControls(dialog);
  dialog.showModal();
}

function workspaceDbName(){
  return isResearcher()&&state.userContext?.id?`${DB_NAME}-researcher-${state.userContext.id}`:DB_NAME;
}
let prefsTimer=null;
const fileTimers=new Map();

const workspaceDb=createWorkspaceDb(workspaceDbName);
const idbGetAll=workspaceDb.getAll;
const idbGet=workspaceDb.get;
const idbPut=workspaceDb.put;
const idbDelete=workspaceDb.remove;
async function deleteWorkspaceDatabase(){
  clearTimeout(prefsTimer);
  for(const timer of fileTimers.values())clearTimeout(timer);
  fileTimers.clear();
  await workspaceDb.drop();
}
const deleteAllDerridaiBrowserState=()=>deleteAllDerridaiBrowserStateCompat(deleteWorkspaceDatabase);
async function persistCurrentPdfAsset(){
  if(!state.pdf.file)return;
  try{
    const blob=state.pdf.file instanceof Blob
      ? state.pdf.file
      : new Blob([await state.pdf.file.arrayBuffer()],{type:"application/pdf"});
    await idbPut("assets",{
      key:"current_pdf",
      blob,
      name:state.pdf.name||state.pdf.file.name||"current.pdf",
      title:state.pdf.title||"",
      author:state.pdf.author||"",
      page:state.pdf.page||1,
      rotation:state.pdf.rotation||0,
      text:state.pdf.text||"",
      search:state.pdf.search||"",
      relatedSearch:state.pdf.relatedSearch||"",
      extractionSource:state.pdf.extractionSource||"",
      extractError:state.pdf.extractError||"",
      saved_at:new Date().toISOString(),
    });
  }catch(error){
    console.warn("Could not persist current PDF asset",error);
  }
}
async function restoreCurrentPdfAsset(){
  try{
    const asset=await idbGet("assets","current_pdf");
    if(!asset?.blob)return;
    const file=new File([asset.blob],asset.name||"restored.pdf",{type:asset.blob.type||"application/pdf"});
    const buffer=await file.arrayBuffer();
    if(state.pdf.url)URL.revokeObjectURL(state.pdf.url);
    state.pdf.file=file;
    state.pdf.url=URL.createObjectURL(new Blob([buffer],{type:"application/pdf"}));
    state.pdf.name=file.name;
    state.pdf.title=asset.title||file.name.replace(/\.pdf$/i,"");
    state.pdf.author=asset.author||"";
    state.pdf.page=Math.max(1,Number(asset.page)||1);
    state.pdf.rotation=Number(asset.rotation||0)%360;
    state.pdf.text=String(asset.text||"");
    state.pdf.search=String(asset.search||"");
    state.pdf.relatedSearch=String(asset.relatedSearch||"");
    state.pdf.extractionSource=String(asset.extractionSource||"");
    state.pdf.extractError=String(asset.extractError||"");
    try{
      state.pdf.doc=await pdfjsLib.getDocument({data:new Uint8Array(buffer.slice(0))}).promise;
      const metadata=await loadPdfMetadata(state.pdf.doc,file.name);
      state.pdf.title=asset.title||metadata.title||state.pdf.title;
      state.pdf.author=asset.author||metadata.author||state.pdf.author;
      state.pdf.page=Math.min(state.pdf.page,state.pdf.doc.numPages||state.pdf.page);
    }catch(error){
      state.pdf.doc=null;
      state.pdf.extractError=`Restored PDF.js initialization failed (${error.message}).`;
    }
  }catch(error){
    console.warn("Could not restore current PDF asset",error);
  }
}

function serializableFile(file){
  return serializableRecordsFile(file);
}
async function persistFileNow(file){
  invalidateCorpusCache();
  try{
    await idbPut("files",serializableFile(file));
  }catch(error){
    console.error("IndexedDB file persistence failed",error);
    toast(`Local persistence failed: ${error.message}`);
  }
}
function persistFile(file){
  invalidateCorpusCache();
  clearTimeout(fileTimers.get(file.id));
  const timer=setTimeout(()=>{fileTimers.delete(file.id);persistFileNow(file)},250);
  fileTimers.set(file.id,timer);
}
function workspacePrefs(){
  return {
    key:"workspace",
    activeFileId:state.activeFileId,
    view:state.view,
    selected:state.selected,
    searches:state.searches,
    listFilters:state.listFilters,
    pages:state.pages,
    pageSize:state.pageSize,
    sorts:state.sorts,
    globalSearch:state.globalSearch,
    globalFilters:state.globalFilters,
    globalSort:state.globalSort,
    globalPage:state.globalPage,
    globalSearchMode:state.globalSearchMode,
    dbSearchMethod:state.dbSearchMethod,
    dbSearchWhere:state.dbSearchWhere,
    dbSearchFetchK:state.dbSearchFetchK,
    dbSearchLambda:state.dbSearchLambda,
    globalAdvancedOpen:state.globalAdvancedOpen,
    searchFacetFilters:state.searchFacetFilters,
    worksSearch:state.worksSearch,
    workOverview:state.workOverview,
    researcherRecordId:state.researcherRecordId,
    researcherCompareA:state.researcherCompareA,
    researcherCompareB:state.researcherCompareB,
    dashboardMetricIndex:state.dashboardMetricIndex,
    lastViewedRecord:state.lastViewedRecord,
    compareA:state.compareA,
    compareB:state.compareB,
    compareMode:state.compareMode,
    comparePasteA:state.comparePasteA,
    comparePasteB:state.comparePasteB,
    compareSourceA:state.compareSourceA,
    compareSourceB:state.compareSourceB,
    compareFilter:state.compareFilter,
    activeStore:state.activeStore,
    storePage:state.storePage,
    storePageSize:state.storePageSize,
    storeQuery:state.storeQuery,
    storeSearchMode:state.storeSearchMode,
    storeWork:state.storeWork,
    storeSort:state.storeSort,
    storeFilters:state.storeFilters,
    storeBrowseMode:state.storeBrowseMode,
    vectorTab:state.vectorTab,
    vectorCollectionFilter:state.vectorCollectionFilter,
    llmConfig:state.llmConfig,
    appConfig:state.appConfig,
    ragConfig:state.ragConfig,
    faqSearch:state.faqSearch,
    faqPage:state.faqPage,
    faqExpanded:state.faqExpanded,
    navHistory:state.navHistory,
    navForward:state.navForward,
    sidebarCollapsed:state.sidebarCollapsed,
    collectionsCollapsed:state.collectionsCollapsed,
    operationToastsMinimized:state.operationToastsMinimized,
    operationStackPosition:state.operationStackPosition,
    collapsedPanels:state.collapsedPanels,
    tableColumns:state.tableColumns,
    upsertState:state.upsertState,
    upsertIgnored:state.upsertIgnored,
    jobApplied:state.jobApplied,
    upsertJobApplied:state.upsertJobApplied,
    reviewSelection:[...state.reviewSelection],
    selectedEvidence:state.selectedEvidence,
    storeSearchSort:state.storeSearchSort,
  };
}
function persistPrefs(){
  if(!state.storageReady)return;
  clearTimeout(prefsTimer);
  prefsTimer=setTimeout(()=>idbPut("prefs",workspacePrefs()).catch(error=>console.error("IndexedDB preference persistence failed",error)),400);
}
async function flushWorkspacePrefs(){
  if(!state.storageReady)throw new Error("Workspace storage is not ready yet.");
  clearTimeout(prefsTimer);
  await idbPut("prefs",workspacePrefs());
}
async function restoreWorkspace(){
  try{
    const [savedFiles,prefs]=await Promise.all([idbGetAll("files"),idbGet("prefs","workspace")]);
    state.files=(savedFiles||[]).map(file=>({
      ...file,
      dirty:new Set(file.dirty||[]),
      errors:file.errors||[],
    }));
    // getShellSnapshot/workIndex can be queried before IndexedDB restore finishes.
    // Always drop derived corpus indexes after reattaching persisted files so the
    // Works page and corpus metrics cannot remain stuck on a cached empty corpus.
    invalidateCorpusCache();
    if(prefs){
      const preservedAppDefaults={...state.appConfig};
      const preservedLlmDefaults={...state.llmConfig};
      for(const key of ["selected","searches","listFilters","pages","sorts","globalSearch","globalFilters","globalSort","globalPage","globalSearchMode","globalSearchAutoRun","searchResultLayouts","dbSearchMethod","dbSearchWhere","dbSearchFetchK","dbSearchLambda","globalAdvancedOpen","searchFacetFilters","worksSearch","workOverview","researcherRecordId","researcherCompareA","researcherCompareB","dashboardMetricIndex","lastViewedRecord","compareA","compareB","compareMode","comparePasteA","comparePasteB","compareSourceA","compareSourceB","compareFilter","faqSearch","faqPage","faqExpanded","activeStore","storePage","storePageSize","storeQuery","storeSearchMode","storeWork","storeSort","storeFilters","storeBrowseMode","vectorTab","vectorCollectionFilter","storeSearchSort","selectedEvidence","navHistory","navForward","sidebarCollapsed","collectionsCollapsed","operationToastsMinimized","operationStackPosition","collapsedPanels","tableColumns","upsertState","upsertIgnored","jobApplied","upsertJobApplied"]){
        if(prefs[key]!==undefined)state[key]=prefs[key];
      }
      state.appConfig={...preservedAppDefaults,...(prefs.appConfig||{})};
      applyUiTheme(state.appConfig.ui_color_theme);
      state.llmConfig={...preservedLlmDefaults,...(prefs.llmConfig||{})};
      state.ragConfig={...state.ragConfig,...(prefs.ragConfig||{})};
      if(!state.faqExpanded||typeof state.faqExpanded!=="object"||Array.isArray(state.faqExpanded))state.faqExpanded={};
      state.ragConfig.locales=Array.isArray(state.ragConfig.locales)?state.ragConfig.locales.filter(value=>value==="en"||value==="fr"):["en","fr"];
      if(!state.ragConfig.locales.length)state.ragConfig.locales=["en","fr"];
      state.ragConfig.prompt=String(state.ragConfig.prompt||"");
      state.ragConfig.instructions=String(state.ragConfig.instructions||"");
      if(!Array.isArray(state.ragConfig.history))state.ragConfig.history=[];
      state.ragConfig.history=state.ragConfig.history.slice(0,100);
      if(!Array.isArray(state.ragConfig.run_history))state.ragConfig.run_history=[];
      state.ragConfig.run_history=state.ragConfig.run_history.slice(0,250);
      if(!state.appConfig.default_review_preset)state.appConfig.default_review_preset="text";
      if(!state.appConfig.default_llm_run_mode)state.appConfig.default_llm_run_mode="foreground";
      ensureProviderProfiles();
      if(Number.isFinite(+prefs.pageSize))state.pageSize=+prefs.pageSize;
      if(typeof prefs.view==="string")state.view=prefs.view;
      state.reviewSelection=new Set(prefs.reviewSelection||[]);
      state.activeFileId=state.files.some(f=>f.id===prefs.activeFileId)?prefs.activeFileId:(state.files[0]?.id||null);
    }else{
      // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
      state.activeFileId=state.files[0]?.id||null;ensureProviderProfiles();try{state.appConfig.ui_color_theme=localStorage.getItem("derridai.ui.theme")||state.appConfig.ui_color_theme||"green"}catch{}applyUiTheme(state.appConfig.ui_color_theme);
    }
    const validPrefixes=new Set(state.files.map(f=>f.id));
    state.reviewSelection=new Set([...state.reviewSelection].filter(key=>validPrefixes.has(String(key).split("::")[0])));
    await restoreCurrentPdfAsset();
  }catch(error){
    console.error("Could not restore IndexedDB workspace",error);
    toast(`Could not restore saved workspace: ${error.message}`);
  }finally{
    state.storageReady=true;
  }
}
function reviewKey(file,index){return `${file.id}::${index}`}
function reviewItemFromKey(key){
  const split=String(key).lastIndexOf("::");
  if(split<0)return null;
  const fileId=key.slice(0,split),index=Number(key.slice(split+2));
  const file=state.files.find(f=>f.id===fileId);
  if(!file||!Number.isInteger(index)||!file.records[index])return null;
  return {file,index,record:file.records[index],key};
}
function selectedReviewItems(){return [...state.reviewSelection].map(reviewItemFromKey).filter(Boolean)}

async function copyCitation(record,kind="inline"){
  const text=kind==="full"?fullCitation(record):inlineCitation(record);
  try{await navigator.clipboard.writeText(text);toast(`Copied ${kind} citation`,{tone:"success"})}
  catch(error){toast(`Could not copy citation: ${error.message}`,{tone:"danger"})}
}
function workspaceEvidenceKey(file,index){return `workspace:${file.id}:${index}`}
function dbEvidenceKey(collection,id){return `db:${collection}:${id}`}
function selectedEvidenceEntries(){return Object.values(state.selectedEvidence||{}).filter(Boolean)}
function evidenceIsSelected(key){return Boolean(state.selectedEvidence?.[key])}
function setEvidence(key,item,selected=true){
  if(!state.selectedEvidence||typeof state.selectedEvidence!=="object")state.selectedEvidence={};
  if(selected)state.selectedEvidence[key]=item;else delete state.selectedEvidence[key];
  persistPrefs();
  shellRefreshHook();
}
function workspaceDbEvidenceTarget(file,index,record=file?.records?.[index]){
  if(!record||!state.activeStore)return null;
  const status=recordDbStatus(file,index,record);
  if(!["synced","exists"].includes(status.kind))return null;
  const receipt=storeReceipt(state.activeStore,file,index);
  const key=localRecordKey(file,index);
  const confirmedId=state.storePresenceIds?.[state.activeStore]?.[key];
  const id=String(receipt?.chroma_id||confirmedId||record.record_id||"").trim();
  return id?{collection:state.activeStore,id,key:dbEvidenceKey(state.activeStore,id)}:null;
}
function workspaceEvidenceSelectionKey(file,index){
  const local=workspaceEvidenceKey(file,index);
  if(evidenceIsSelected(local))return local;
  return workspaceDbEvidenceTarget(file,index)?.key||local;
}
function toggleWorkspaceEvidence(file,index){
  if(!hasCapability("evidence.select")){toast(tr("permissions.evidence_denied","Your role cannot change selected evidence."),{tone:"warn"});return}
  const record=file?.records?.[index];if(!record)return;
  const localKey=workspaceEvidenceKey(file,index);
  if(evidenceIsSelected(localKey)){setEvidence(localKey,null,false);return}
  const dbTarget=workspaceDbEvidenceTarget(file,index,record);
  if(dbTarget){toggleDbEvidence(dbTarget.collection,dbTarget.id,record);return}
  setEvidence(localKey,{
    key:localKey,kind:"workspace",file_id:file.id,index,record_id:record.record_id||"",work:record.work||"",
    page_start:record.page_start??record.page??null,page_end:record.page_end??null,
    speaker:record.speaker||null,position_holder:record.position_holder||null,stance:record.stance||null,
    discourse_role:record.discourse_role||null,target:record.target||null,proposition_status:record.proposition_status||null,
    inline_citation:record.inline_citation||null,text_preview:String(record.text||"").replace(/\s+/g," ").trim().slice(0,280),
    label:`${record.record_id||`Record ${index+1}`} · ${record.work||file.name}`
  },true);
}
function toggleDbEvidence(collection,id,record={}){
  if(!hasCapability("evidence.select")){toast(tr("permissions.evidence_denied","Your role cannot change selected evidence."),{tone:"warn"});return}
  if(!collection||!id)return;
  const key=dbEvidenceKey(collection,id);
  setEvidence(key,{
    key,kind:"db",collection,chroma_id:id,record_id:record.record_id||id,work:record.work||"",
    page_start:record.page_start??record.page??null,page_end:record.page_end??null,
    speaker:record.speaker||null,position_holder:record.position_holder||null,stance:record.stance||null,
    discourse_role:record.discourse_role||null,target:record.target||null,proposition_status:record.proposition_status||null,
    inline_citation:record.inline_citation||null,text_preview:String(record.text||"").replace(/\s+/g," ").trim().slice(0,280),
    label:`${record.record_id||id} · ${record.work||collection}`
  },!evidenceIsSelected(key));
}
function clearSelectedEvidence(){
  if(!hasCapability("evidence.select")){toast(tr("permissions.evidence_denied","Your role cannot change selected evidence."),{tone:"warn"});return}
  state.selectedEvidence={};persistPrefs();shellRefreshHook()
}
function selectedEvidencePayload(){
  const payload=[];
  for(const item of selectedEvidenceEntries()){
    if(item.kind==="db")payload.push({collection:item.collection,chroma_id:item.chroma_id});
    else if(item.kind==="workspace"){
      const file=state.files.find(file=>file.id===item.file_id);
      const record=file?.records?.[Number(item.index)];
      if(record)payload.push({record:ragEvidenceRecordPayload(record)});
    }
  }
  return payload;
}
function evidenceButtonHtml(key,labelText="Evidence"){
  const selected=evidenceIsSelected(key),allowed=hasCapability("evidence.select");
  return `<button class="btn tiny evidence-toggle ${selected?"soft":""}" data-evidence-key="${esc(key)}" ${allowed?"":`disabled data-disabled-reason="${esc(tr("permissions.evidence_denied","Your role cannot change selected evidence."))}"`} title="${selected?esc(tr("ui.remove_evidence","Remove from evidence")):esc(tr("ui.add_evidence","Add to evidence"))}">${selected?icon("check"):icon("plus")}${esc(labelText)}</button>`;
}
function setReviewSelected(file,index,selected){
  const key=reviewKey(file,index);
  selected?state.reviewSelection.add(key):state.reviewSelection.delete(key);
  persistPrefs();
}
function clearReviewSelection(){
  state.reviewSelection.clear();
  persistPrefs();
}

// 0.30.11 packet discipline: API boundaries receive only fields required by
// the operation. Audit history is intentionally opt-in because it can dwarf
// the rest of a record after repeated edits.
const TOUCHUP_TRANSPORT_CONTEXT_FIELDS=[
  "record_id","work","document_author","edition","year","page_start","page_end",
  "region_type","region_author","primary_text","speaker","position_holder","target",
  "discourse_role","proposition_status","semantic_function","stance","claim_scope",
  "text","topics","concepts","persons","works_referenced","is_direct_quote",
  "quoted_speaker","quoted_author","quoted_work","quoted_position_holder",
  "quoted_addressee","quoted_referent","quotation_chain","inline_citation",
  "full_citation","needs_review","review_reason"
];
const RAG_EVIDENCE_TRANSPORT_FIELDS=[
  "record_id","canonical_work_id","work","document_author","edition","year",
  "page_start","page_end","translator","speaker","position_holder","target",
  "discourse_role","proposition_status","stance","text","topics","concepts",
  "persons","document_language","document_languages","quoted_speaker",
  "quoted_author","quoted_work","quoted_position_holder"
];
function recordPayload(record,{fields=null,includeUpdates=false,includeChromaId=false}={}){
  const source=record&&typeof record==="object"?record:{};
  const keys=fields?[...new Set(fields)]:Object.keys(source);
  const out={};
  for(const key of keys){
    if(!(key in source))continue;
    if(key==="updates"&&!includeUpdates)continue;
    if(key==="_updates_count"||key==="_researcher_text_policy")continue;
    if(key==="_chroma_id"&&!includeChromaId)continue;
    out[key]=source[key];
  }
  return out;
}
function upsertRecordPayload(record,chromaId=null){
  const out=recordPayload(record,{includeChromaId:false});
  if(chromaId)out._chroma_id=chromaId;
  return out;
}
function touchupRecordPayload(record,fields=[]){
  return recordPayload(record,{fields:[...fields,...TOUCHUP_TRANSPORT_CONTEXT_FIELDS]});
}
function ragEvidenceRecordPayload(record){
  return recordPayload(record,{fields:RAG_EVIDENCE_TRANSPORT_FIELDS});
}
function ragGradeEvidencePayload(evidence=[]){
  return (Array.isArray(evidence)?evidence:[]).slice(0,40).map((item,index)=>({
    evidence_id:item?.evidence_id||`E${index}`,
    inline_citation:item?.inline_citation||"",
    full_citation:item?.full_citation||"",
    collection:item?.collection||null,
    record:recordPayload(item?.record||{},{fields:["record_id","work","text"]}),
  }));
}
function applyRecordChanges(file,index,changes,{source="manual",model=null,batchId=null,rationale=null}={}){
  const current=file.records[index];
  if(!current)return 0;
  const pending={};
  for(const [field,newValue] of Object.entries(changes||{})){
    if(field==="updates")continue;
    if(!sameValue(current[field],newValue))pending[field]=newValue;
  }
  if("text" in pending && "text_length" in current && !("text_length" in pending)){
    const length=String(pending.text??"").length;
    if(!sameValue(current.text_length,length))pending.text_length=length;
  }
  const entries=Object.entries(pending);
  if(!entries.length)return 0;
  const timestamp=new Date().toISOString();
  const operationId=batchId||uid();
  const history=Array.isArray(current.updates)?current.updates.map(cloneAuditValue):[];
  const next={...current};
  for(const [field,newValue] of entries){
    const entry={
      field_name:field,
      old_value:cloneAuditValue(current[field]),
      new_value:cloneAuditValue(newValue),
      timestamp,
      source,
      batch_id:operationId,
      initiated_by:state.userContext?.username||null,
    };
    if(model)entry.model=model;
    if(rationale?.[field])entry.reason=String(rationale[field]);
    history.push(entry);
    next[field]=newValue;
  }
  next.updates=history;
  file.records[index]=next;
  file.dirty.add(index);
  invalidateCorpusCache();
  persistFile(file);
  if(state.view==="record"&&typeof window!=="undefined")window.dispatchEvent(new CustomEvent("derridai:record-updated"));
  return entries.length;
}

async function clearRecordUpdates(file,index,{confirmFirst=true}={}){
  const record=file?.records?.[index];
  const count=Array.isArray(record?.updates)?record.updates.length:0;
  if(!record||!count){
    toast("This record has no updates history");
    return false;
  }
  if(confirmFirst&&!await openMessageModal({title:"Clear record update history?",message:`Clear all ${count} updates entries from ${record.record_id||`record ${index+1}`}? This history cannot be reconstructed automatically.`,tone:"danger",confirmLabel:"Clear history",cancelLabel:"Cancel"}))return false;
  file.records[index]={...record,updates:[]};
  file.dirty.add(index);
  persistFile(file);
  return true;
}
async function clearAllUpdates({confirmed=false}={}){
  const rows=allRows().filter(row=>Array.isArray(row.record.updates)&&row.record.updates.length);
  if(!rows.length)return toast("No loaded records have updates history");
  const entries=rows.reduce((sum,row)=>sum+row.record.updates.length,0);
  if(!confirmed&&!await openMessageModal({title:"Clear all update histories?",message:`Clear ${entries.toLocaleString()} updates entries from ${rows.length.toLocaleString()} loaded records? This permanently removes the local audit histories.`,tone:"danger",confirmLabel:"Clear all histories",cancelLabel:"Cancel"}))return;
  const files=new Set();
  for(const row of rows){
    row.file.records[row.index]={...row.record,updates:[]};
    row.file.dirty.add(row.index);
    files.add(row.file);
  }
  for(const file of files)persistFile(file);
  shell();renderView();
  toast(`Cleared updates history from ${rows.length.toLocaleString()} records`);
}

function historyHtml(record){
  const updates=Array.isArray(record.updates)?record.updates:[];
  if(!updates.length)return "";
  const recent=[...updates].slice(-8).reverse();
  return `<section class="card"><div class="section"><div class="history-title"><h3>Change history</h3><span class="badge">${updates.length}</span></div><div class="history-list">${recent.map(update=>`<div class="history-item"><div><b>${esc(label(update.field_name||"field"))}</b><span>${esc(update.source||"manual")}${update.initiated_by?` · ${esc(update.initiated_by)}`:""}${update.model?` · ${esc(update.model)}`:""}</span></div><time>${esc(formatTimestamp(update.timestamp))}</time></div>`).join("")}</div>${updates.length>recent.length?`<div class="note" style="margin-top:8px">Showing latest ${recent.length} of ${updates.length} changes. Full history is preserved in the record's <code>updates</code> field.</div>`:""}</div></section>`;
}
function formatTimestamp(value){
  if(!value)return "";
  const date=new Date(value);
  return Number.isNaN(date.getTime())?String(value):date.toLocaleString();
}
function recordHistoryVersions(record){
  const updates=Array.isArray(record?.updates)?record.updates:[];
  const cleanSnapshot=value=>{
    const copy=cloneAuditValue(value)||{};
    if(copy&&typeof copy==="object")delete copy.updates;
    return copy;
  };
  const baseline=cleanSnapshot(record);
  for(let index=updates.length-1;index>=0;index--){
    const update=updates[index]||{};
    if(!update.field_name)continue;
    baseline[update.field_name]=cloneAuditValue(update.old_value);
  }
  const versions=[{
    index:0,
    label:"Original",
    timestamp:null,
    source:"original",
    changes:[],
    record:cleanSnapshot(baseline),
  }];
  const groups=[];
  for(let index=0;index<updates.length;index++){
    const update=updates[index]||{};
    const key=update.batch_id||update.timestamp||`change-${index}`;
    const previous=groups.at(-1);
    if(previous?.key===key)previous.items.push(update);
    else groups.push({key,items:[update]});
  }
  let snapshot=cleanSnapshot(baseline);
  for(const group of groups){
    snapshot=cleanSnapshot(snapshot);
    for(const update of group.items){
      if(update?.field_name)snapshot[update.field_name]=cloneAuditValue(update.new_value);
    }
    const last=group.items.at(-1)||{};
    versions.push({
      index:versions.length,
      label:`Version ${versions.length}`,
      timestamp:last.timestamp||null,
      source:last.source||"manual",
      model:last.model||null,
      changes:group.items,
      record:cleanSnapshot(snapshot),
    });
  }
  return versions;
}
function historyVersionChanges(previous,current){
  const keys=new Set([...Object.keys(previous||{}),...Object.keys(current||{})]);
  return [...keys].filter(key=>key!=="updates"&&!key.startsWith("_")&&!sameValue(previous?.[key],current?.[key])).sort((a,b)=>label(a).localeCompare(label(b)));
}
function restoreRecordHistoryVersion(file,index,version){
  const current=file?.records?.[index];
  if(!current||!version?.record)return 0;
  const keys=new Set([...Object.keys(current),...Object.keys(version.record)]);
  const changes={};
  for(const field of keys){
    if(field==="updates"||field.startsWith("_"))continue;
    const value=Object.prototype.hasOwnProperty.call(version.record,field)?cloneAuditValue(version.record[field]):null;
    if(!sameValue(current[field],value))changes[field]=value;
  }
  return applyRecordChanges(file,index,changes,{source:"history_restore",batchId:uid(),rationale:Object.fromEntries(Object.keys(changes).map(field=>[field,`Restored from ${version.label}`]))});
}
function openRecordHistoryBrowser(file,index){
  const record=file?.records?.[index];
  if(!record)return;
  let versions=recordHistoryVersions(record);
  if(versions.length<=1)return toast("This record has no update history");
  let cursor=versions.length-1;
  const dialog=document.createElement("dialog");
  dialog.className="record-history-dialog";
  const close=()=>{dialog.close();dialog.remove()};
  const render=()=>{
    versions=recordHistoryVersions(file.records[index]);
    cursor=Math.max(0,Math.min(cursor,versions.length-1));
    const version=versions[cursor];
    const previous=cursor>0?versions[cursor-1]:null;
    const changed=previous?historyVersionChanges(previous.record,version.record):[];
    const currentIndex=versions.length-1;
    const isCurrent=cursor===currentIndex;
    const text=String(version.record.text||"");
    dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Record history</h2><div class="dialog-subtitle">${esc(file.records[index]?.record_id||`Record ${index+1}`)} · ${versions.length-1} saved change set${versions.length-1===1?"":"s"}</div></div><button class="btn icon-only" data-close title="${esc(tr("ui.close","Close"))}" aria-label="${esc(tr("ui.close","Close"))}">${icon("close")}</button></div>
      <div class="db record-history-body">
        <div class="history-version-nav">
          <button class="btn" id="historyOlder" ${cursor<=0?`disabled data-disabled-reason="Already at the original record."`:""}>← Older</button>
          <div class="history-version-position"><b>${esc(version.label)}${isCurrent?" · Current":""}</b><span>${version.timestamp?esc(formatTimestamp(version.timestamp)):"Before tracked edits"}${version.source?` · ${esc(version.source)}`:""}${version.model?` · ${esc(version.model)}`:""}</span></div>
          <button class="btn" id="historyNewer" ${cursor>=currentIndex?`disabled data-disabled-reason="Already at the newest version."`:""}>Newer →</button>
        </div>
        <div class="history-version-summary"><span><b>${changed.length}</b> field${changed.length===1?"":"s"} changed in this version</span><span><b>${text.trim()?text.trim().split(/\s+/).length:0}</b> words</span><span><b>${text.length.toLocaleString()}</b> characters</span></div>
        ${changed.length?`<div class="history-version-diffs">${changed.map(field=>`<details class="history-version-diff"><summary><b>${esc(label(field))}</b><span>changed</span></summary><div class="history-diff-values"><div><small>Previous</small><pre>${esc(jsonPretty(previous?.record?.[field]))}</pre></div><div><small>This version</small><pre>${esc(jsonPretty(version.record?.[field]))}</pre></div></div></details>`).join("")}</div>`:`<div class="info">This is the reconstructed original state before tracked updates.</div>`}
        <details class="history-record-preview"><summary>Preview this version</summary><div class="history-preview-meta"><b>${esc(version.record.work||"Untitled work")}</b><span>${esc(version.record.document_author||"")} · ${esc(version.record.year||"")}</span></div><div class="history-preview-text">${esc(text.slice(0,5000))}${text.length>5000?"…":""}</div></details>
      </div>
      <div class="da record-history-actions"><button class="btn danger secondary-danger" id="historyClear">Delete audit history…</button><span class="dialog-action-spacer"></span><button class="btn" data-close>Close</button><button class="btn" id="historyUndoAll" ${cursor===0&&isCurrent?"disabled":""}>Restore original</button><button class="btn primary" id="historyRestore" ${isCurrent?`disabled data-disabled-reason="This is already the current version."`:""}>Restore this version</button></div>`;
    dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
    dialog.querySelector("#historyOlder").onclick=()=>{cursor--;render()};
    dialog.querySelector("#historyNewer").onclick=()=>{cursor++;render()};
    dialog.querySelector("#historyRestore").onclick=async()=>{
      if(isCurrent)return;
      const count=restoreRecordHistoryVersion(file,index,version);
      if(!count)return toast("No record fields needed restoring");
      versions=recordHistoryVersions(file.records[index]);cursor=versions.length-1;
      shell();renderView();render();
      toast(`Restored ${count} field${count===1?"":"s"} from ${version.label}`);
    };
    dialog.querySelector("#historyUndoAll").onclick=async()=>{
      const original=versions[0];
      if(!await openMessageModal({title:"Restore original record?",message:"Restore every field to its state before the tracked update history? The restoration itself will be recorded, so you can move forward again later.",confirmLabel:"Restore original",cancelLabel:"Cancel"}))return;
      const count=restoreRecordHistoryVersion(file,index,original);
      if(!count)return toast("The record already matches its original tracked state");
      versions=recordHistoryVersions(file.records[index]);cursor=versions.length-1;
      shell();renderView();render();
      toast(`Restored original record state · ${count} fields changed`);
    };
    dialog.querySelector("#historyClear").onclick=async()=>{
      if(!await clearRecordUpdates(file,index))return;
      close();shell();renderView();toast("Record update history cleared");
    };
    decorateDisabledControls(dialog);
  };
  document.body.appendChild(dialog);showAppModal(dialog);render();
}


function openMessageModal({
  title="Notice",
  message="",
  detail="",
  tone="info",
  confirmLabel="OK",
  cancelLabel=null,
}={}){
  return new Promise(resolve=>{
    const dialog=document.createElement("dialog");
    dialog.className=`message-dialog ${tone}`;
    dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2>${detail?`<div class="dialog-subtitle">${esc(detail)}</div>`:""}</div><button class="btn icon-only" data-cancel>${icon("close")}</button></div><div class="db"><div class="message-modal-body">${esc(message).replace(/\n/g,"<br>")}</div></div><div class="da">${cancelLabel?`<button class="btn" data-cancel>${esc(cancelLabel)}</button>`:""}<button class="btn ${tone==="danger"?"danger":"primary"}" data-confirm>${esc(confirmLabel)}</button></div>`;
    document.body.appendChild(dialog);
    const finish=value=>{dialog.close();dialog.remove();resolve(value)};
    dialog.querySelectorAll("[data-cancel]").forEach(button=>button.onclick=()=>finish(false));
    dialog.querySelector("[data-confirm]").onclick=()=>finish(true);
    dialog.addEventListener("cancel",event=>{event.preventDefault();finish(false)},{once:true});
    showAppModal(dialog);
  });
}
async function copyJsonToClipboard(value,labelText="record"){
  const text=JSON.stringify(value,null,2);
  try{
    await navigator.clipboard.writeText(text);
    toast(`Copied ${labelText} JSON`);
  }catch(error){
    const area=document.createElement("textarea");
    area.value=text;
    area.style.position="fixed";
    area.style.opacity="0";
    document.body.appendChild(area);
    area.select();
    try{document.execCommand("copy");toast(`Copied ${labelText} JSON`)}
    catch{openMessageModal({title:"Could not copy",message:error.message,tone:"danger"})}
    finally{area.remove()}
  }
}
function isResponseCacheStore(store){
  return Boolean(store&&(store.name==="_response_cache"||store.storage_name==="derridai_response_cache"||store.metadata?.derridai_system_collection==="response_cache"));
}
function recordStores(){
  return state.stores.filter(store=>!isResponseCacheStore(store));
}
function responseCacheStore(){
  return state.stores.find(isResponseCacheStore)||null;
}
function corpusStoreExists(name){
  return Boolean(name&&recordStores().some(store=>store.name===name));
}

function toast(message,{tone="auto",duration=null}={}){
  let el=document.querySelector("#toast");
  if(!el){el=document.createElement("div");el.id="toast";el.className="toast";document.body.appendChild(el)}
  // Toast text is operational information: keep it selectable/copyable and
  // pause dismissal while the user is interacting with it.
  el.setAttribute("role","status");
  el.setAttribute("aria-live","polite");
  el.setAttribute("aria-atomic","true");
  el.tabIndex=0;
  const text=translateDynamicUiValue(String(message??""));
  const failed=tone==="danger"||/\bHTTP\s+\d{3}\b/i.test(text)||/\b(failed|could not|error)\b/i.test(text);
  el.classList.toggle("failed",failed);
  el.classList.toggle("success",tone==="success");
  const httpIndex=text.search(/\bHTTP\s+\d{3}\b/i);
  if(failed&&httpIndex>=0){
    el.innerHTML=`${esc(text.slice(0,httpIndex))}<strong>${esc(text.slice(httpIndex))}</strong>`;
  }else{
    el.textContent=text;
  }
  el.classList.add("show");
  const dismissDelay=duration??(failed?8000:4200);
  const pause=()=>clearTimeout(el._timer);
  const resume=()=>{clearTimeout(el._timer);el._timer=setTimeout(()=>el.classList.remove("show"),dismissDelay)};
  el.onpointerenter=pause;
  el.onpointerleave=resume;
  el.onfocusin=pause;
  el.onfocusout=resume;
  resume();
}

function highlight(text, query){
  const s=String(text ?? ""), q=String(query ?? "");
  if(!q) return esc(s);
  const low=s.toLocaleLowerCase(), needle=q.toLocaleLowerCase();
  let out="", pos=0, i;
  while((i=low.indexOf(needle,pos))>=0){
    out += esc(s.slice(pos,i)) + "<mark>" + esc(s.slice(i,i+q.length)) + "</mark>";
    pos=i+Math.max(1,q.length);
  }
  return out + esc(s.slice(pos));
}

function highlightTerms(text, query){
  const source=String(text??"");
  // eslint-disable-next-line no-useless-escape -- SA-14: preserve legacy matching/serialization until dedicated text fixtures cover it.
  const terms=[...new Set(String(query??"").trim().split(/\s+/).map(term=>term.replace(/^["'()\[\]{}]+|["'()\[\]{},.;:!?]+$/g,"")).filter(term=>term.length>1))]
    .sort((a,b)=>b.length-a.length);
  if(!terms.length)return esc(source);
  const pattern=new RegExp(`(${terms.map(term=>term.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")).join("|")})`,"gi");
  let out="",last=0,match;
  while((match=pattern.exec(source))){out+=esc(source.slice(last,match.index))+`<mark>${esc(match[0])}</mark>`;last=match.index+match[0].length;if(!match[0].length)pattern.lastIndex++}
  return out+esc(source.slice(last));
}
function semanticSimilarity(distance){
  const d=Number(distance);
  if(!Number.isFinite(d))return null;
  // Chroma distances are not calibrated probabilities. This monotonic transform
  // provides an intuitive 0..1 display while preserving the result ranking.
  return 1/(1+Math.max(0,d));
}
function similarityHtml(distance){
  const score=semanticSimilarity(distance);
  if(score==null)return `<span class="similarity-score" title="${esc(tr("research.similarity_help","Similarity is derived from vector distance and is not a probability."))}">—</span>`;
  return `<span class="similarity-score" title="${esc(tr("research.similarity_help","A ranking signal derived from vector distance. Higher values indicate closer semantic proximity; it is not a probability or confidence score."))}"><b>${(score*100).toFixed(1)}%</b><small>d=${Number(distance).toFixed(4)}</small></span>`;
}

function snippet(text, query, max=430){
  const s=String(text ?? "").replace(/\s+/g," ").trim();
  if(!s) return "";
  if(!query) return s.length>max?s.slice(0,max)+"…":s;
  const i=s.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());
  if(i<0) return s.length>max?s.slice(0,max)+"…":s;
  const a=Math.max(0,i-Math.floor(max/2)), b=Math.min(s.length,a+max);
  return (a?"…":"")+s.slice(a,b)+(b<s.length?"…":"");
}

let progressiveRenderToken=0;
function nextProgressiveRenderToken(){return ++progressiveRenderToken}
function scheduleUiWork(callback){
  if(typeof requestIdleCallback==="function")return requestIdleCallback(callback,{timeout:120});
  return setTimeout(()=>callback({timeRemaining:()=>8,didTimeout:true}),0);
}
function loadingCardsHtml(label="Loading",count=4){
  return `<div class="progressive-loading" role="status" aria-live="polite"><div class="progressive-loading-head"><span class="spinner small-spinner"></span><b>${esc(label)}</b></div><div class="progressive-skeleton-grid">${Array.from({length:count},()=>'<div class="progressive-skeleton-card"><i></i><i></i><i></i></div>').join("")}</div></div>`;
}
function showViewLoading(main,title="Loading view",detail="Preparing data…"){
  if(!main)return;
  main.innerHTML=`<section class="card view-loading-card"><div class="view-loading-copy"><span class="spinner"></span><div><b>${esc(title)}</b><p>${esc(detail)}</p></div></div>${loadingCardsHtml("Loading cards",3)}</section>`;
}
function progressiveRender(container,items,renderItem,{batchSize=10,label="Loading",token=nextProgressiveRenderToken(),onDone=null}={}){
  if(!container)return token;
  container.innerHTML=items.length?loadingCardsHtml(label,Math.min(4,items.length)):"";
  let index=0;
  const step=()=>{
    if(token!==progressiveRenderToken||!container.isConnected)return;
    if(index===0)container.innerHTML="";
    const end=Math.min(items.length,index+batchSize);
    const fragment=document.createDocumentFragment();
    for(;index<end;index++){
      const template=document.createElement("template");
      try{
        template.innerHTML=String(renderItem(items[index],index)||"").trim();
      }catch(error){
        console.error("Progressive card render failed",error,items[index]);
        template.innerHTML=`<div class="info error progressive-render-error"><b>Could not render this item.</b><span>${esc(error?.message||String(error))}</span></div>`;
      }
      fragment.appendChild(template.content);
    }
    container.appendChild(fragment);
    decorateDisabledControls(container);
    if(index<items.length)scheduleUiWork(step);
    else if(onDone)onDone();
  };
  if(items.length)scheduleUiWork(step);
  else if(onDone)onDone();
  return token;
}

function pages(r){
  if(r.page_start==null && r.page_end==null) return "—";
  return r.page_end!=null && r.page_end!==r.page_start ? `${display(r.page_start)}–${display(r.page_end)}` : display(r.page_start);
}

function toggleSort(sort,key){if(sort.key===key)sort.dir*=-1;else{sort.key=key;sort.dir=1}}
function sortHead(text,key,sort,className=""){const arrow=sort.key===key?(sort.dir===1?"▲":"▼"):"";return `<th${className?` class="${esc(className)}"`:""}><button data-sort="${esc(key)}">${esc(text)} ${arrow}</button></th>`}

function pageInfo(total,page){
  const pages=Math.max(1,Math.ceil(total/state.pageSize));
  page=Math.max(1,Math.min(pages,page||1));
  return {page,pages,start:(page-1)*state.pageSize,end:Math.min(total,page*state.pageSize)};
}
function pager(pg,total,prefix){
  return `<div class="pagebar"><span>${total?`${pg.start+1}–${pg.end} of ${total}`:"0 results"}</span><div class="inline">
  <button class="btn small" data-page="${prefix}:first" ${pg.page<=1?"disabled":""}>First</button>
  <button class="btn small" data-page="${prefix}:prev" ${pg.page<=1?"disabled":""}>Previous</button>
  <span>Page ${pg.page} / ${pg.pages}</span>
  <button class="btn small" data-page="${prefix}:next" ${pg.page>=pg.pages?"disabled":""}>Next</button>
  <button class="btn small" data-page="${prefix}:last" ${pg.page>=pg.pages?"disabled":""}>Last</button></div></div>`;
}
function wirePager(prefix,pg,setPage){
  document.querySelectorAll(`[data-page^="${prefix}:"]`).forEach(b=>b.onclick=()=>{
    const action=b.dataset.page.split(":")[1];
    let p=pg.page;
    if(action==="first")p=1;if(action==="prev")p--;if(action==="next")p++;if(action==="last")p=pg.pages;
    setPage(Math.max(1,Math.min(pg.pages,p)));
  });
}

function recordFingerprint(record){
  if(record&&typeof record==="object"&&recordFingerprintCache.has(record))return recordFingerprintCache.get(record);
  const value=computeRecordFingerprint(record);
  if(record&&typeof record==="object")recordFingerprintCache.set(record,value);
  return value;
}
function localRecordKey(file,index){return `${file.id}::${index}`}
function storeReceipt(store,file,index){return state.upsertState?.[store]?.[localRecordKey(file,index)]||null}
function candidateChromaIds(file,index,record){
  const ids=[];
  const receipt=storeReceipt(state.activeStore,file,index);
  if(receipt?.chroma_id)ids.push(receipt.chroma_id);
  const logical=record?.record_id;
  if(logical!=null&&String(logical)!==""){
    ids.push(String(logical));
    ids.push(`${file.name}::${logical}`);
  }
  return [...new Set(ids)];
}
function recordDbStatus(file,index,record,store=state.activeStore){
  if(!hasCorpusDb())return {kind:"none",label:"No database",title:dbUnavailableReason()};
  if(!store)return {kind:"none",label:"No collection",title:"Select a Chroma collection"};
  if(!corpusStoreExists(store))return {kind:"none",label:"No collection",title:"The selected collection no longer exists"};
  const key=localRecordKey(file,index);
  const receipt=state.upsertState?.[store]?.[key]||null;
  const presence=state.storePresence?.[store]?.[key];
  const fingerprint=recordFingerprint(record);
  if(receipt&&receipt.fingerprint===fingerprint&&presence!==false)return {kind:"synced",label:"Synced",title:`Upserted ${formatTimestamp(receipt.timestamp)}`};
  if(receipt&&receipt.fingerprint!==fingerprint)return {kind:"changed",label:"Pending",title:"Changed since last upsert"};
  if(presence===true)return {kind:"exists",label:"In DB",title:"Record exists in the selected collection; local sync time is unknown"};
  if(presence===false)return {kind:"absent",label:"Not in DB",title:"Record was not found in the selected collection"};
  return {kind:"unknown",label:"Unknown",title:"Database presence has not been checked yet"};
}
function dbStatusBadgeHtml(file,index,record){
  const info=recordDbStatus(file,index,record);
  return `<span class="db-status ${info.kind}" data-db-status-key="${esc(localRecordKey(file,index))}" title="${esc(info.title)}"><i></i>${esc(info.label)}</span>`;
}
function workDbStatus(rows,workName=null){
  if(!hasCorpusDb())return {kind:"none",label:"No database"};
  if(!state.activeStore)return {kind:"none",label:"No collection"};
  if(!corpusStoreExists(state.activeStore))return {kind:"none",label:"No collection"};
  const receipts=rows.map(row=>state.upsertState?.[state.activeStore]?.[localRecordKey(row.file,row.index)]||null);
  if(rows.some((row,index)=>receipts[index]&&receipts[index].fingerprint!==recordFingerprint(row.record)))return {kind:"changed",label:"Pending changes"};
  if(rows.length&&rows.every((row,index)=>receipts[index]?.fingerprint===recordFingerprint(row.record)))return {kind:"synced",label:"Synced"};
  if(state.storeWorksStore===state.activeStore){
    const name=workName??String(rows[0]?.record?.work||"(Untitled work)");
    const stat=(state.storeWorkStats||[]).find(item=>String(item.work||"(Untitled work)")===String(name));
    const dbCount=Number(stat?.count||0);
    if(dbCount>=rows.length&&rows.length)return {kind:"exists",label:"In DB"};
    if(dbCount>0)return {kind:"exists",label:`Partly in DB (${dbCount}/${rows.length})`};
    return {kind:"absent",label:"Not in DB"};
  }
  return {kind:"unknown",label:"DB status loading"};
}
async function refreshPresenceForRows(rows,{force=false}={}){
  const store=state.activeStore;
  if(!hasCorpusDb()||!store||!rows.length)return;
  if(!state.storePresence[store])state.storePresence[store]={};
  if(!state.storePresenceIds[store])state.storePresenceIds[store]={};
  if(!state.storePresenceCheckedAt[store])state.storePresenceCheckedAt[store]={};
  const now=Date.now(),ttl=15000;
  const staleRows=force?rows:rows.filter(row=>now-Number(state.storePresenceCheckedAt[store][localRecordKey(row.file,row.index)]||0)>ttl);
  if(!staleRows.length)return;
  const ids=[...new Set(staleRows.flatMap(row=>candidateChromaIds(row.file,row.index,row.record)))];
  if(!ids.length)return;
  const found=new Set();
  try{
    for(let start=0;start<ids.length;start+=500){
      const data=await api(`/api/stores/${encodeURIComponent(store)}/records/status`,{
        method:"POST",
        body:JSON.stringify({ids:ids.slice(start,start+500)}),
      });
      for(const id of data.existing_ids||[])found.add(id);
    }
    for(const row of staleRows){
      const key=localRecordKey(row.file,row.index);
      const candidates=candidateChromaIds(row.file,row.index,row.record);
      const matchedId=candidates.find(id=>found.has(id))||"";
      state.storePresence[store][key]=Boolean(matchedId);
      state.storePresenceIds[store][key]=matchedId;
      state.storePresenceCheckedAt[store][key]=now;
    }
    pendingUpsertCache.key="";
    updateDbStatusElements();
  }catch(error){
    console.warn("Could not refresh Chroma presence",error);
  }
}
function updateDbStatusElements(){
  document.querySelectorAll("[data-db-status-key]").forEach(el=>{
    const item=reviewItemFromKey(el.dataset.dbStatusKey);
    if(!item)return;
    const info=recordDbStatus(item.file,item.index,item.file.records[item.index]);
    el.className=`db-status ${info.kind}`;
    el.title=info.title;
    el.innerHTML=`<i></i>${esc(info.label)}`;
  });
  document.querySelectorAll("[data-work-status]").forEach(el=>{
    const work=el.dataset.workStatus;
    const rows=workIndex().get(work)?.rows||[];
    const info=workDbStatus(rows,work);
    el.className=`db-status ${info.kind}`;
    el.innerHTML=`<i></i>${esc(info.label)}`;
  });
}
function ignoredFingerprint(store,file,index){
  return state.upsertIgnored?.[store]?.[localRecordKey(file,index)]||null;
}
let pendingUpsertCache={key:"",at:0,rows:[]};
function pendingUpsertRows(){
  if(!hasCorpusDb()||!state.activeStore)return [];
  const dirtyCount=state.files.reduce((sum,file)=>sum+(file.dirty?.size||0),0);
  const key=`${state.activeStore}|${corpusCache.version}|${dirtyCount}|${Number(state.upsertJobApplied?Object.values(state.upsertJobApplied).reduce((a,b)=>a+Number(b||0),0):0)}`;
  const now=performance.now();
  if(pendingUpsertCache.key===key&&now-pendingUpsertCache.at<750)return pendingUpsertCache.rows;
  const rows=allRows().filter(row=>{
    const fingerprint=recordFingerprint(row.record);
    if(ignoredFingerprint(state.activeStore,row.file,row.index)===fingerprint)return false;
    const info=recordDbStatus(row.file,row.index,row.record);
    return info.kind==="changed" || info.kind==="absent" || (row.file.dirty.has(row.index)&&info.kind!=="synced");
  });
  pendingUpsertCache={key,at:now,rows};
  return rows;
}
function pendingChangesForRow(row){
  const store=state.activeStore;
  const receipt=storeReceipt(store,row.file,row.index);
  const since=receipt?.timestamp?new Date(receipt.timestamp).getTime():0;
  const updates=Array.isArray(row.record.updates)?row.record.updates:[];
  const changed=updates.filter(update=>{
    const time=new Date(update.timestamp||0).getTime();
    return !since || Number.isNaN(time) || time>since;
  });
  if(changed.length)return changed;
  if(!receipt)return [{
    field_name:"record",
    old_value:null,
    new_value:"Not previously upserted from this workspace",
    source:"workspace",
    timestamp:null,
  }];
  return [{
    field_name:"record",
    old_value:"Last upserted fingerprint",
    new_value:"Current record differs",
    source:"fingerprint",
    timestamp:null,
  }];
}
function removeFromUpsertQueue(row){
  const store=state.activeStore;
  if(!store)return;
  if(!state.upsertIgnored[store])state.upsertIgnored[store]={};
  state.upsertIgnored[store][localRecordKey(row.file,row.index)]=recordFingerprint(row.record);
  persistPrefs();
}
async function openUpsertQueue(){
  if(!hasCorpusDb())return openMessageModal({title:"Vector database required",message:dbUnavailableReason(),confirmLabel:"OK"});
  if(!state.activeStore)return toast("Select a Chroma collection first");
  if(allRows().length)await refreshPresenceForRows(allRows());
  const rows=pendingUpsertRows();
  const dialog=document.createElement("dialog");
  dialog.className="queue-dialog wide-queue-dialog";

  const render=()=>{
    const currentRows=pendingUpsertRows();
    dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${esc(tr("vector.unsynced_changes","Unsynced local changes"))}</h2><div class="dialog-subtitle">${esc(state.activeStore)} · ${currentRows.length} ${esc(tr("dynamic.records","records"))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db">
      <div class="queue-explainer"><b>${esc(tr("vector.unsynced_changes_what","What is this list?"))}</b><p>${esc(tr("vector.unsynced_changes_help","These are browser-workspace records that changed since their last confirmed sync, plus records DerridAI has confirmed are missing from the selected collection. Removing an item suppresses only its current version; a later change queues it again."))}</p></div><div class="queue-bulk-actions">${currentRows.length?`<button class="btn small" id="queueSelectAll">${esc(tr("ui.select_all","Select all"))}</button><button class="btn small" id="queueSelectNone">${esc(tr("ui.clear_selection","Clear selection"))}</button>`:""}</div>
      <div class="upsert-queue-list">${currentRows.map(row=>{
        const info=recordDbStatus(row.file,row.index,row.record);
        const key=localRecordKey(row.file,row.index);
        const changes=pendingChangesForRow(row);
        return `<section class="upsert-queue-card">
          <div class="upsert-queue-head">
            <label class="upsert-queue-item"><input type="checkbox" data-upsert-key="${esc(key)}" checked><span><b>${esc(row.record.record_id||`Record ${row.index+1}`)}</b><small>${esc(row.record.work||row.file.name)} · ${esc(row.file.name)}</small></span><span class="db-status ${info.kind}"><i></i>${esc(info.label)}</span></label>
            <div class="tools"><button class="btn small" data-review-queue="${esc(key)}">Review ${changes.length} change${changes.length===1?"":"s"}</button><button class="btn small danger" data-remove-queue="${esc(key)}">Remove from queue</button></div>
          </div>
          <div class="queue-change-list hidden" data-queue-changes="${esc(key)}">${changes.map(change=>`<div class="queue-change-row"><b>${esc(label(change.field_name||"field"))}</b><span>${esc(change.source||"manual")}${change.timestamp?` · ${esc(formatTimestamp(change.timestamp))}`:""}</span><details><summary>Values</summary><div class="queue-change-values"><pre>${esc(jsonPretty(change.old_value))}</pre><span>→</span><pre>${esc(jsonPretty(change.new_value))}</pre></div></details></div>`).join("")}</div>
        </section>`;
      }).join("")||`<div class="llm-empty">${esc(tr("vector.no_unsynced_changes","No confirmed unsynced local changes."))}</div>`}</div>
    </div>
    <div class="da"><button class="btn" data-close>Close</button>${currentRows.length?`<button class="btn primary" id="upsertQueued">${icon("database")}${esc(tr("vector.sync_selected","Sync selected"))}</button>`:""}</div>`;

    const close=()=>{dialog.close();dialog.remove()};
    dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
    dialog.querySelector("#queueSelectAll")?.addEventListener("click",()=>dialog.querySelectorAll("[data-upsert-key]").forEach(box=>box.checked=true));
    dialog.querySelector("#queueSelectNone")?.addEventListener("click",()=>dialog.querySelectorAll("[data-upsert-key]").forEach(box=>box.checked=false));
    dialog.querySelectorAll("[data-review-queue]").forEach(button=>button.onclick=()=>{
      const panel=dialog.querySelector(`[data-queue-changes="${CSS.escape(button.dataset.reviewQueue)}"]`);
      panel?.classList.toggle("hidden");
    });
    dialog.querySelectorAll("[data-remove-queue]").forEach(button=>button.onclick=()=>{
      const row=currentRows.find(item=>localRecordKey(item.file,item.index)===button.dataset.removeQueue);
      if(row){removeFromUpsertQueue(row);render();shell()}
    });
    dialog.querySelector("#upsertQueued")?.addEventListener("click",async()=>{
      const selected=new Set([...dialog.querySelectorAll("[data-upsert-key]:checked")].map(x=>x.dataset.upsertKey));
      const chosen=currentRows.filter(row=>selected.has(localRecordKey(row.file,row.index)));
      if(!chosen.length)return toast("Select at least one queued record");
      close();
      await upsertRows(chosen,"queued records");
      shell();renderView();
    });
  };

  document.body.appendChild(dialog);
  showAppModal(dialog);
  render();
}
function tableAvailableFields(rows,extra=[]){
  const cachedRows=allRows();
  if(rows===cachedRows){
    const set=new Set([...extra,...recordFields().filter(key=>key!=="updates")]);
    return [...set].sort((a,b)=>label(a).localeCompare(label(b)));
  }
  const set=new Set(extra);
  for(const row of rows)for(const key of Object.keys(row.record||row||{}))if(key!=="updates")set.add(key);
  return [...set].sort((a,b)=>label(a).localeCompare(label(b)));
}
function getTableColumns(table,available){
  const defaults=TABLE_DEFAULTS[table]||available.slice(0,8);
  let cols=Array.isArray(state.tableColumns[table])?state.tableColumns[table].filter(key=>available.includes(key)):[];
  if(!cols.length)cols=defaults.filter(key=>available.includes(key));
  if(!cols.length)cols=available.slice(0,8);
  state.tableColumns[table]=cols;
  return cols;
}
function openColumnChooser(table,available,rerender){
  let cols=[...getTableColumns(table,available)];
  const dialog=document.createElement("dialog");
  dialog.className="columns-dialog";
  const render=()=>{
    const remaining=available.filter(key=>!cols.includes(key));
    dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Configure columns</h2><div class="dialog-subtitle">${esc(table)} table · drag-free ordering controls</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db"><div class="column-list">${cols.map((key,index)=>`<div class="column-item"><span>${esc(label(key))}</span><div class="tools"><button class="btn small" data-up="${index}" ${index===0?"disabled":""}>↑</button><button class="btn small" data-down="${index}" ${index===cols.length-1?"disabled":""}>↓</button><button class="btn small danger" data-remove="${index}">Remove</button></div></div>`).join("")||'<div class="note">No visible columns.</div>'}</div><div class="column-add"><select class="control" id="columnAddSelect">${remaining.map(key=>`<option value="${esc(key)}">${esc(label(key))}</option>`).join("")}</select><button class="btn" id="columnAdd" ${remaining.length?"":"disabled"}>Add column</button></div></div><div class="da"><button class="btn" id="columnReset">Reset defaults</button><button class="btn" data-close>Cancel</button><button class="btn primary" id="columnSave">Save columns</button></div>`;
    const close=()=>{dialog.close();dialog.remove()};
    dialog.querySelectorAll("[data-close]").forEach(x=>x.onclick=close);
    dialog.querySelectorAll("[data-up]").forEach(x=>x.onclick=()=>{const i=+x.dataset.up;[cols[i-1],cols[i]]=[cols[i],cols[i-1]];render()});
    dialog.querySelectorAll("[data-down]").forEach(x=>x.onclick=()=>{const i=+x.dataset.down;[cols[i+1],cols[i]]=[cols[i],cols[i+1]];render()});
    dialog.querySelectorAll("[data-remove]").forEach(x=>x.onclick=()=>{cols.splice(+x.dataset.remove,1);render()});
    dialog.querySelector("#columnAdd")?.addEventListener("click",()=>{const value=dialog.querySelector("#columnAddSelect").value;if(value){cols.push(value);render()}});
    dialog.querySelector("#columnReset").onclick=()=>{cols=(TABLE_DEFAULTS[table]||[]).filter(key=>available.includes(key));render()};
    dialog.querySelector("#columnSave").onclick=()=>{state.tableColumns[table]=cols;persistPrefs();syncUrl({replace:true});close();rerender()};
  };
  document.body.appendChild(dialog);showAppModal(dialog);render();
}
function dataCellHtml(row,key,query=""){
  const record=row.record;
  if(key==="__file")return `<td>${esc(row.file.name)}</td>`;
  if(key==="__db_status")return `<td>${dbStatusBadgeHtml(row.file,row.index,record)}</td>`;
  if(key==="page_start")return `<td class="page-start-cell">${esc(pages(record))}</td>`;
  if(key==="needs_review")return `<td>${record.needs_review?'<span class="review">Review</span>':"—"}</td>`;
  if(key==="text")return `<td class="textcell extracted-text-cell">${highlightTerms(snippet(record.text,query),query)}</td>`;
  if(key==="inline_citation")return `<td>${esc(inlineCitation(record))}</td>`;
  if(key==="full_citation")return `<td>${esc(fullCitation(record))}</td>`;
  if(key==="record_id"){
    const rowKey=reviewKey(row.file,row.index);
    return `<td class="id"><div class="record-id-copy"><span>${esc(display(record[key]))}</span><button class="copy-record-mini" data-copy-row-key="${esc(rowKey)}" title="Copy entire record JSON">${icon("copy")}</button></div></td>`;
  }
  const value=record[key];if(metadataSearchable(key,value))return `<td><button class="table-metadata-link" type="button" data-meta-search-field="${esc(key)}" data-meta-search-value="${esc(Array.isArray(value)?value[0]:value)}" data-meta-search-contains="${Array.isArray(value)}">${esc(display(value))}</button></td>`;
  return `<td>${esc(display(value))}</td>`;
}
function workspaceRecordActionsHtml(row){
  const rowKey=reviewKey(row.file,row.index);
  const evidenceKey=workspaceEvidenceSelectionKey(row.file,row.index);
  const selected=evidenceIsSelected(evidenceKey);
  return `<td class="record-actions-cell"><div class="record-row-actions"><details class="record-citation-menu"><summary class="btn tiny">${esc(tr("ui.get_citation","Get Citation"))}</summary><div class="record-citation-popover" role="group" aria-label="${esc(tr("ui.get_citation","Get Citation"))}"><button class="btn tiny" data-cite-row-key="${esc(rowKey)}" data-cite-kind="inline" title="${esc(tr("ui.copy_inline","Copy inline citation"))}">${esc(tr("ui.inline","Inline"))}</button><button class="btn tiny" data-cite-row-key="${esc(rowKey)}" data-cite-kind="full" title="${esc(tr("ui.copy_full","Copy full citation"))}">${esc(tr("ui.full","Full"))}</button></div></details><button class="btn tiny ${selected?"soft":""}" data-toggle-workspace-evidence="${esc(rowKey)}" title="${esc(selected?tr("ui.remove_evidence","Remove from evidence"):tr("ui.add_evidence","Add to evidence"))}">${selected?"✓ Evidence":"+ Evidence"}</button></div></td>`;
}
function dataHeadHtml(key,sort){
  const className=key==="page_start"?"page-start-head":key==="text"?"extracted-text-head":"";
  if(["__db_status"].includes(key))return `<th${className?` class="${className}"`:""}>${esc(label(key))}</th>`;
  return sortHead(label(key),key,sort,className);
}

function listFilterValue(fileId,key){
  return state.listFilters?.[fileId]?.[key]??"";
}
function setListFilterValue(fileId,key,value){
  if(!state.listFilters[fileId])state.listFilters[fileId]={};
  if(value===""||value==null)delete state.listFilters[fileId][key];
  else state.listFilters[fileId][key]=value;
  persistPrefs();
}
function rowMatchesListFilters(row,filters){
  for(const [key,raw] of Object.entries(filters||{})){
    const filter=String(raw??"").trim().toLocaleLowerCase();
    if(!filter)continue;
    if(key==="__db_status"){
      const info=recordDbStatus(row.file,row.index,row.record);
      const haystack=`${info.kind} ${info.label}`.toLocaleLowerCase();
      if(!haystack.includes(filter))return false;
      continue;
    }
    if(key==="needs_review"){
      const value=row.record.needs_review===true?"yes":"no";
      if(value!==filter)return false;
      continue;
    }
    const value=key==="page_start"?pages(row.record):display(row.record[key]);
    if(!String(value??"").toLocaleLowerCase().includes(filter))return false;
  }
  return true;
}
function listFilterControl(fileId,key){
  const value=listFilterValue(fileId,key);
  if(key==="needs_review"){
    return `<select class="column-filter" data-list-filter="${esc(key)}"><option value="">All</option><option value="yes" ${value==="yes"?"selected":""}>Needs review</option><option value="no" ${value==="no"?"selected":""}>Reviewed</option></select>`;
  }
  return `<input class="column-filter" data-list-filter="${esc(key)}" value="${esc(value)}" placeholder="Filter…">`;
}

function storeCellHtml(record,key){
  if(key==="_chroma_id")return `<td class="chroma-id-col"><div class="scroll-cell id" title="${esc(record._chroma_id||"")}">${esc(record._chroma_id||"")}</div></td>`;
  if(key==="page_start")return `<td>${esc(pages(record))}</td>`;
  if(key==="needs_review")return `<td>${record.needs_review?'<span class="review">Review</span>':"—"}</td>`;
  if(key==="text")return `<td class="textcell">${esc(snippet(record.text,"",240))}</td>`;
  if(key==="inline_citation")return `<td><div class="scroll-cell">${esc(inlineCitation(record))}</div></td>`;
  if(key==="full_citation")return `<td><div class="scroll-cell" title="${esc(fullCitation(record))}">${esc(fullCitation(record))}</div></td>`;
  const value=record[key];if(metadataSearchable(key,value))return `<td><button class="table-metadata-link scroll-cell" type="button" data-meta-search-field="${esc(key)}" data-meta-search-value="${esc(Array.isArray(value)?value[0]:value)}" data-meta-search-contains="${Array.isArray(value)}" title="${esc(display(value))}">${esc(display(value))}</button></td>`;
  return `<td><div class="scroll-cell ${key==="record_id"?"id":""}" title="${esc(display(value))}">${esc(display(value))}</div></td>`;
}
function pdfLinks(record){
  const file=String(record?.pdf_file||"");
  if(file&&Array.isArray(record?.pdf_pages)){
    return [...new Set(record.pdf_pages.map(Number).filter(page=>Number.isFinite(page)&&page>0))].sort((a,b)=>a-b).map(pdf_page=>({pdf_file:file,pdf_page}));
  }
  const legacyPage=Number(record?.pdf_page);
  if(file&&Number.isFinite(legacyPage)&&legacyPage>0)return [{pdf_file:file,pdf_page:legacyPage}];
  if(Array.isArray(record?.pdf_links)){
    return record.pdf_links.map(link=>({pdf_file:String(link?.pdf_file||""),pdf_page:Number(link?.pdf_page)})).filter(link=>link.pdf_file&&Number.isFinite(link.pdf_page)&&link.pdf_page>0);
  }
  return [];
}

function pdfDisplayTitle(){
  return state.pdf.title||state.pdf.name||"PDF";
}
function matchingLoadedPdfLink(record){
  if(!state.pdf.name)return null;
  return pdfLinks(record).find(link=>link.pdf_file===state.pdf.name)||null;
}
function loadedPdfPagesForRecord(record){
  if(!state.pdf.name)return [];
  return pdfLinks(record)
    .filter(link=>link.pdf_file===state.pdf.name)
    .map(link=>Number(link.pdf_page))
    .filter(page=>Number.isFinite(page)&&page>0)
    .sort((a,b)=>a-b);
}
function allLinkedRowsForLoadedPdf(){
  if(!state.pdf.name)return [];
  const rows=[];
  for(const {file,record,index} of allRows()){
    const pages=loadedPdfPagesForRecord(record);
    if(pages.length)rows.push({file,record,index,pages});
  }
  return rows.sort((a,b)=>
    (a.pages[0]||0)-(b.pages[0]||0)
    ||String(a.record.work||"").localeCompare(String(b.record.work||""))
    ||String(a.record.record_id||"").localeCompare(String(b.record.record_id||""))
  );
}
async function loadPdfMetadata(doc,fileName){
  const fallback=String(fileName||"").replace(/\.pdf$/i,"");
  if(!doc)return {title:fallback,author:""};
  try{
    const metadata=await doc.getMetadata();
    const info=metadata?.info||{};
    const xmp=metadata?.metadata;
    const title=String(
      info.Title
      ||xmp?.get?.("dc:title")
      ||xmp?.get?.("pdf:title")
      ||fallback
      ||""
    ).trim();
    const author=String(
      info.Author
      ||xmp?.get?.("dc:creator")
      ||xmp?.get?.("pdf:author")
      ||""
    ).trim();
    return {title:title||fallback,author};
  }catch(error){
    console.warn("Could not read PDF metadata",error);
    return {title:fallback,author:""};
  }
}
function openPdfExplorerWorkspace(){
  window.dispatchEvent(new CustomEvent("derridai:navigate-native",{detail:{path:"/pdf?mode=explorer",runtimeView:"pdf"}}));
}
function openLoadedPdfPage(page){
  if(!state.pdf.doc&& !state.pdf.file)return toast("Open the linked PDF in PDF Explorer first");
  const max=state.pdf.doc?.numPages||Number(page)||1;
  state.pdf.page=Math.max(1,Math.min(max,Number(page)||1));
  state.pdf.text="";
  state.pdf.extractError="";
  state.pdf.extractionSource="";
  openPdfExplorerWorkspace();
}

function normalizePdfLinkChanges(record,links){
  const files=[...new Set(links.map(link=>link.pdf_file).filter(Boolean))];
  if(files.length>1)throw new Error("A record can link to multiple pages of one PDF source, not multiple PDF files.");
  const file=files[0]||null;
  const pages=[...new Set(links.map(link=>Number(link.pdf_page)).filter(page=>Number.isFinite(page)&&page>0))].sort((a,b)=>a-b);
  const changes={pdf_file:file,pdf_pages:pages};
  if(record.pdf_page!==undefined)changes.pdf_page=null;
  if(record.pdf_links!==undefined)changes.pdf_links=null;
  return changes;
}
function editableChipSection(field,values){
  const list=flattenValueList(values);
  const datalist=[...new Set(allRows().flatMap(row=>flattenValueList(row.record[field])).map(String))].sort((a,b)=>a.localeCompare(b));
  return `<div class="section quick-index" data-chip-field="${esc(field)}"><div class="section-title-row"><h3>${esc(label(field))}</h3><span class="badge">${list.length}</span></div><div class="chips editable-chips" data-annotatable-field="${esc(field)}">${list.map((value,index)=>`<span class="chip editable-chip"><button type="button" class="chip-search-link" data-meta-search-field="${esc(field)}" data-meta-search-value="${esc(value)}" data-meta-search-contains="true">${esc(display(value))}</button><button type="button" data-chip-remove="${index}" title="Remove">×</button></span>`).join("")||'<span class="note">None</span>'}</div><div class="chip-add"><input class="control" data-chip-input list="chip-${esc(field)}" placeholder="Add ${esc(label(field).toLowerCase().replace(/s$/,""))}"><datalist id="chip-${esc(field)}">${datalist.map(value=>`<option value="${esc(value)}"></option>`).join("")}</datalist><button class="btn small" type="button" data-chip-add>${icon("plus")}Add</button></div></div>`;
}
function wireEditableChips(main,file,index){
  main.querySelectorAll("[data-chip-field]").forEach(section=>{
    const field=section.dataset.chipField;
    section.querySelectorAll("[data-chip-remove]").forEach(button=>button.onclick=()=>{
      const current=[...flattenValueList(file.records[index][field])];
      current.splice(+button.dataset.chipRemove,1);
      applyRecordChanges(file,index,{[field]:current},{source:"manual_quick_index"});shell();renderView();
    });
    const input=section.querySelector("[data-chip-input]");
    const add=()=>{
      const value=input.value.trim();if(!value)return;
      const current=[...flattenValueList(file.records[index][field])];
      if(current.some(item=>String(item).localeCompare(value,undefined,{sensitivity:"accent"})===0))return toast(`${value} is already present`);
      current.push(value);
      applyRecordChanges(file,index,{[field]:current},{source:"manual_quick_index"});shell();renderView();
    };
    section.querySelector("[data-chip-add]").onclick=add;
    input.onkeydown=e=>{if(e.key==="Enter"){e.preventDefault();add()}};
  });
  wireMetadataSearch(main);
}
function needsReviewItems(rows=null){
  if(rows===null){
    return memoCorpus("needs-review-items",()=>allRows().filter(row=>row.record.needs_review===true).map(row=>({...row,key:reviewKey(row.file,row.index)})));
  }
  return rows.filter(row=>row.record.needs_review===true).map(row=>({...row,key:reviewKey(row.file,row.index)}));
}
function workIndex(){
  return memoCorpus("work-index",()=>{
    const map=new Map();
    for(const {file,record:r,index} of allRows()){
      const key=String(r.work||"(Untitled work)");
      const item=map.get(key)||{work:key,count:0,review:0,files:new Set(),authors:new Set(),years:new Set(),rows:[]};
      item.count++;
      if(r.needs_review)item.review++;
      item.files.add(file.name);
      if(r.document_author)item.authors.add(r.document_author);
      if(r.year!=null)item.years.add(r.year);
      item.rows.push({file,record:r,index});
      map.set(key,item);
    }
    return map;
  });
}
function openMergeDialog(){
  if(state.files.length<2)return toast("Open at least two JSONL files to merge");
  const dialog=document.createElement("dialog");
  dialog.className="merge-dialog";
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Merge JSONL tabs</h2><div class="dialog-subtitle">Choose any subset. The selected source tabs will be replaced in the workspace by the merged tab.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db"><div class="merge-actions"><button class="btn small" id="mergeSelectAll">Select all</button><button class="btn small" id="mergeSelectNone">Clear</button></div><div class="merge-file-list">${state.files.map(file=>`<label class="merge-file-item"><input type="checkbox" data-merge-file="${file.id}" checked><span><b>${esc(file.name)}</b><small>${file.records.length.toLocaleString()} records</small></span></label>`).join("")}</div><div class="field"><label>Merged file name</label><input class="control" id="mergeName" value="derridai-merged.jsonl"></div><label class="check-item"><input type="checkbox" id="mergeDownload"><span>Download merged JSONL immediately</span></label><div class="info">Unselected tabs remain unchanged. Selected tabs are removed from the workspace after the merge is created; their underlying source files on disk are not deleted.</div></div><div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="mergeCreate">Merge and replace selected tabs</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(x=>x.onclick=close);
  dialog.querySelector("#mergeSelectAll").onclick=()=>dialog.querySelectorAll("[data-merge-file]").forEach(x=>x.checked=true);
  dialog.querySelector("#mergeSelectNone").onclick=()=>dialog.querySelectorAll("[data-merge-file]").forEach(x=>x.checked=false);
  dialog.querySelector("#mergeCreate").onclick=async()=>{
    const ids=[...dialog.querySelectorAll("[data-merge-file]:checked")].map(x=>x.dataset.mergeFile);
    const files=state.files.filter(file=>ids.includes(file.id));
    if(!files.length)return toast("Select at least one file");
    const firstIndex=Math.min(...files.map(file=>state.files.indexOf(file)));
    const name=(dialog.querySelector("#mergeName").value.trim()||"derridai-merged.jsonl").replace(/\s+/g,"-");
    const records=files.flatMap(file=>file.records.map(record=>cloneAuditValue(record)));
    const merged={
      id:uid(),
      name:name.endsWith(".jsonl")?name:`${name}.jsonl`,
      records,
      errors:files.flatMap(file=>file.errors||[]),
      dirty:new Set(records.map((_,index)=>index)),
      imported_at:new Date().toISOString(),
      merged_from:files.map(file=>file.name),
    };

    const removedIds=new Set(files.map(file=>file.id));
    state.files=state.files.filter(file=>!removedIds.has(file.id));
    state.files.splice(firstIndex,0,merged);

    for(const id of removedIds){
      delete state.selected[id];
      delete state.searches[id];
      delete state.pages[id];
      delete state.sorts[id];
      if(fileTimers.has(id)){
        clearTimeout(fileTimers.get(id));
        fileTimers.delete(id);
      }
      await idbDelete("files",id).catch(error=>console.error("Could not remove merged source tab from IndexedDB",error));
    }
    state.reviewSelection=new Set([...state.reviewSelection].filter(key=>!removedIds.has(String(key).split("::")[0])));
    for(const store of Object.keys(state.upsertState||{})){
      for(const key of Object.keys(state.upsertState[store]||{})){
        if(removedIds.has(String(key).split("::")[0]))delete state.upsertState[store][key];
      }
    }
    for(const store of Object.keys(state.upsertIgnored||{})){
      for(const key of Object.keys(state.upsertIgnored[store]||{})){
        if(removedIds.has(String(key).split("::")[0]))delete state.upsertIgnored[store][key];
      }
    }
    for(const bucket of [state.storePresence,state.storePresenceIds]){
      for(const store of Object.keys(bucket||{})){
        for(const key of Object.keys(bucket[store]||{})){
          if(removedIds.has(String(key).split("::")[0]))delete bucket[store][key];
        }
      }
    }

    await persistFileNow(merged);
    state.activeFileId=merged.id;
    if(dialog.querySelector("#mergeDownload").checked)download(merged.name,fileJsonl(merged));
    persistPrefs();
    close();
    navigateTo("list",{fileId:merged.id});
    toast(`Merged and replaced ${files.length} tabs · ${records.length.toLocaleString()} records`);
  };
}

function storeOptions(selected=state.activeStore){
  const stores=recordStores();
  if(!stores.length)return `<option value="">No corpus Chroma collections</option>`;
  return stores.map(store=>`<option value="${esc(store.name)}" ${store.name===selected?"selected":""}>${esc(store.name)} (${store.count})</option>`).join("");
}
function collectionPicker(id){
  const stores=recordStores();
  const reason=stores.length?"":dbUnavailableReason();
  return `<select class="control compact-select" id="${id}" ${stores.length?"":`disabled data-disabled-reason="${esc(reason)}" title="${esc(reason)}"`}>${storeOptions()}</select>`;
}
function setActiveStore(name){
  const next=name||"";
  if(state.activeStore!==next){
    state.storeWorksStore="";
    // Presence maps can become very large for corpus-scale workspaces. Keep
    // only the selected store's map when switching collections.
    state.storePresence=next&&state.storePresence?.[next]?{[next]:state.storePresence[next]}:{};
    state.storePresenceIds=next&&state.storePresenceIds?.[next]?{[next]:state.storePresenceIds[next]}:{};
    state.storePresenceCheckedAt=next&&state.storePresenceCheckedAt?.[next]?{[next]:state.storePresenceCheckedAt[next]}:{};
  }
  state.activeStore=next;
  persistPrefs();
  syncUrl({replace:true});
}
async function ensureStores(){
  try{
    await refreshStores();
    persistPrefs();
  }catch(error){
    console.warn("Could not refresh Chroma collections",error);
  }
}
function upsertAuditDelta(record,receipt,presence){
  const updates=Array.isArray(record?.updates)?record.updates:[];
  const updatesCount=updates.length;
  if(receipt&&receipt.updates_count!==null&&receipt.updates_count!==undefined&&Number.isInteger(Number(receipt.updates_count))){
    const previousCount=Math.max(0,Number(receipt.updates_count));
    if(updatesCount<previousCount){
      return {audit_entries:[],replace_updates:updates.map(cloneAuditValue),updates_count:updatesCount};
    }
    if(updatesCount>previousCount){
      return {audit_entries:updates.slice(previousCount).map(cloneAuditValue),replace_updates:null,updates_count:updatesCount};
    }
    return {audit_entries:[],replace_updates:null,updates_count:updatesCount};
  }
  // Upgrade path for receipts created before 0.30.11: use the receipt timestamp
  // to send only audit entries created after the last successful sync.
  if(receipt?.timestamp){
    const syncedAt=Date.parse(receipt.timestamp);
    if(Number.isFinite(syncedAt)){
      const delta=updates.filter(entry=>{
        const timestamp=Date.parse(entry?.timestamp||"");
        return Number.isFinite(timestamp)&&timestamp>syncedAt;
      });
      return {audit_entries:delta.map(cloneAuditValue),replace_updates:null,updates_count:updatesCount};
    }
  }
  // A genuinely new Chroma row needs its existing local history initialized
  // once. Existing rows with no receipt preserve their server-side history.
  if(presence===false&&updatesCount){
    return {audit_entries:[],replace_updates:updates.map(cloneAuditValue),updates_count:updatesCount};
  }
  return {audit_entries:[],replace_updates:null,updates_count:updatesCount};
}

async function buildUpsertItems(rows,store,{yieldEvery=0}={}){
  const idCounts=new Map();
  for(let i=0;i<rows.length;i++){const row=rows[i],id=String(row.file.records[row.index]?.record_id??"");idCounts.set(id,(idCounts.get(id)||0)+1);if(yieldEvery&&i&&i%yieldEvery===0)await new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)))}
  const items=[];
  for(let i=0;i<rows.length;i++){
    const row=rows[i],current=row.file.records[row.index],logical=String(current?.record_id??""),receipt=storeReceipt(store,row.file,row.index),chromaId=receipt?.chroma_id||((idCounts.get(logical)||0)>1?`${row.file.name}::${logical}`:logical);
    const key=localRecordKey(row.file,row.index);
    const audit=upsertAuditDelta(current,receipt,state.storePresence?.[store]?.[key]);
    items.push({key,record:current,fingerprint:recordFingerprint(current),chroma_id:chromaId,file_name:row.file.name,...audit});
    if(yieldEvery&&i&&i%yieldEvery===0)await new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)));
  }
  return items;
}
async function upsertRows(rows,labelText="records",{largeSyncConfirmed=false}={}){
  if(!hasCorpusDb())return openMessageModal({title:"Vector database required",message:dbUnavailableReason(),confirmLabel:"OK"});
  if(!state.activeStore)return toast("Select a Chroma collection first");
  if(!rows.length)return toast("No records selected for upsert");
  const activeUpsert=state.jobs.find(job=>job.type==="upsert"&&["queued","running","cancelling"].includes(job.status));
  if(activeUpsert)return openMessageModal({title:tr("operations.vector_sync_active_title","A vector sync is already active"),message:trf("operations.vector_sync_active_help","{label} must finish or be cancelled before another collection build starts.",{label:activeUpsert.label||activeUpsert.store_name||"The current sync"}),confirmLabel:"OK"});
  const store=state.activeStore;
  await refreshPresenceForRows(rows,{force:true});
  if(rows.length>500&&!largeSyncConfirmed){
    const approved=await openMessageModal({title:tr("operations.large_sync_background_title","Build collection in the background?"),message:trf("operations.large_sync_background_help","{count} records will be prepared once, then DerridAI will build and validate the collection as a background operation. You may continue working in this tab while the build runs.",{count:rows.length.toLocaleString()}),confirmLabel:tr("operations.start_background_build","Start background build"),cancelLabel:tr("ui.cancel","Cancel")});
    if(!approved)return false;
  }
  const items=await buildUpsertItems(rows,store,{yieldEvery:rows.length>500?80:0});
  try{
    const transportItems=items.map(item=>({
      key:item.key,
      record:upsertRecordPayload(item.record),
      fingerprint:item.fingerprint,
      chroma_id:item.chroma_id,
      file_name:item.file_name,
      audit_entries:item.audit_entries||[],
      replace_updates:item.replace_updates,
      updates_count:item.updates_count,
    }));
    const sourceWorks=[...new Set(rows.map(row=>String(row.record?.work||row.file?.records?.[row.index]?.work||"").trim()).filter(Boolean))];
    const job=await api("/api/jobs/upsert",{method:"POST",body:JSON.stringify({store_name:store,items:transportItems,document_field:"text",embedding_field:"embedding",batch_size:500,mirror_languages:true,label:labelText,source_kind:"browser_workspace",source_label:labelText,source_works:sourceWorks})});
    state.jobs=[job,...state.jobs.filter(existing=>existing.id!==job.id)];
    syncJobProgressToasts();startJobPolling();
    toast(trf("operations.vector_build_queued","Queued {count} records for background build of {store}",{count:rows.length.toLocaleString(),store}),{tone:"success"});
    notifyVectorStoresChanged();
    if(state.view==="home")refreshOperationsPanelOnly();
    return true;
  }catch(error){toast(`Could not start vector build: ${error.message}`);return false}
}

function rowsFromReviewSelection(){
  return selectedReviewItems().map(item=>({file:item.file,record:item.file.records[item.index],index:item.index}));
}
function linkedPdfRows(page=state.pdf.page){
  return allRows().filter(({record})=>pdfLinks(record).some(link=>{
    if(Number(link.pdf_page)!==Number(page))return false;
    return !state.pdf.name||link.pdf_file===state.pdf.name;
  }));
}
async function linkPdfPage(file,index,page){
  if(!state.pdf.name)return toast("Open a PDF first");
  const record=file.records[index];
  let links=pdfLinks(record);
  const target={pdf_file:state.pdf.name,pdf_page:Number(page)};
  if(links.some(link=>link.pdf_file===target.pdf_file&&Number(link.pdf_page)===target.pdf_page))return toast(`Record is already linked to page ${page}`);
  if(links.length&&links.some(link=>link.pdf_file!==target.pdf_file)){
    if(!await openMessageModal({title:"Replace PDF links?",message:`This record is linked to ${links[0].pdf_file}. Replace those PDF links with ${target.pdf_file}?`,tone:"danger",confirmLabel:"Replace links",cancelLabel:"Cancel"}))return;
    links=[];
  }
  const next=[...links,target].sort((a,b)=>a.pdf_page-b.pdf_page);
  const count=applyRecordChanges(file,index,normalizePdfLinkChanges(record,next),{source:"pdf_link"});
  shell();renderView();
  toast(count?`Linked record to PDF page ${page}`:"PDF link unchanged");
}
function unlinkPdfLink(file,index,link,{stayInPdf=false}={}){
  const record=file?.records?.[index];
  if(!record)return;
  const links=pdfLinks(record);
  const next=links.filter(item=>!(item.pdf_file===link.pdf_file&&Number(item.pdf_page)===Number(link.pdf_page)));
  if(next.length===links.length)return toast("That PDF link was not found");
  const count=applyRecordChanges(file,index,normalizePdfLinkChanges(record,next),{source:"pdf_unlink"});
  if(stayInPdf)renderPdf(document.querySelector("#main"));
  else{shell();renderView()}
  toast(count?`Unlinked ${link.pdf_file} page ${link.pdf_page}`:"PDF link unchanged");
}
function unlinkAllPdfLinks(file,index){
  const record=file?.records?.[index];
  if(!record||!pdfLinks(record).length)return toast("This record has no PDF links");
  const count=applyRecordChanges(file,index,normalizePdfLinkChanges(record,[]),{source:"pdf_unlink"});
  shell();renderView();
  toast(count?"All PDF links removed":"No PDF links changed");
}

function viewLabel(view){
  return viewConfig.find(item=>item.id===view)?.label||view;
}
function navSnapshot(){
  const file=activeFile();
  return {
    view:state.view,
    activeFileId:state.activeFileId,
    selectedIndex:file?selectedIndex(file):0,
    activeStore:state.activeStore||"",
    storeWork:state.storeWork||"",
    storePage:state.storePage||1,
    storeBrowseMode:state.storeBrowseMode||"works",
    pdfPage:state.pdf.page||1,
    // Breadcrumb back/forward restores the same state that a copied URL does,
    // rather than only restoring the page shell.
    urlState:cloneAuditValue(currentTableUrlState(state.view)),
  };
}
function sameSnapshot(a,b){
  if(!a||!b)return false;
  return JSON.stringify(a)===JSON.stringify(b);
}
function applyNavSnapshot(target){
  if(!target)return;
  if(target.activeFileId&&state.files.some(file=>file.id===target.activeFileId))state.activeFileId=target.activeFileId;
  state.view=target.view||"home";
  if(state.activeFileId&&Number.isFinite(+target.selectedIndex))state.selected[state.activeFileId]=+target.selectedIndex;
  if(target.activeStore!==undefined)state.activeStore=target.activeStore||"";
  if(target.storeWork!==undefined)state.storeWork=target.storeWork||"";
  if(Number.isFinite(+target.storePage))state.storePage=Math.max(1,+target.storePage);
  if(target.storeBrowseMode)state.storeBrowseMode=target.storeBrowseMode;
  if(Number.isFinite(+target.pdfPage))state.pdf.page=Math.max(1,+target.pdfPage);
  if(target.urlState)applyCompressedTableUrlState(target.urlState,state.view);
}
const viewPathMap={home:"/",list:"/records",record:"/record",works:"/works",global:"/search",annotations:"/annotations",pdf:"/pdf",compare:"/compare",vector:"/databases",rag:"/rag",faq:"/faq",responsecache:"/response-cache",providers:"/providers",config:"/settings"};
const pathViewMap=Object.fromEntries(Object.entries(viewPathMap).map(([view,path])=>[path,view]));
let urlSyncHook=null;
function setUrlSyncHook(hook){urlSyncHook=typeof hook==="function"?hook:null}
function currentTableUrlState(view=state.view){
  // URL state is intentionally view-scoped. It is the public/shareable state
  // contract for a page; IndexedDB remains only a convenience for restoring a
  // user's workspace when no URL overrides are present.
  if(view==="list"){
    const f=activeFile();if(!f)return null;
    return {c:state.tableColumns.list||null,s:state.sorts[f.id]||null,f:state.listFilters[f.id]||null,p:state.pages[f.id]||1,z:state.pageSize,q:state.searches[f.id]||""};
  }
  if(view==="global")return {c:state.tableColumns.global||null,s:state.globalSort,f:state.globalFilters,sf:state.searchFacetFilters||{},p:state.globalPage,z:state.pageSize,q:state.globalSearch,m:state.globalSearchMode,dm:state.dbSearchMethod,dw:state.dbSearchWhere,dk:state.dbSearchFetchK,dl:state.dbSearchLambda,ao:Boolean(state.globalAdvancedOpen),l:state.searchResultLayouts};
  if(view==="vector")return {c:state.tableColumns.vector||null,s:state.storeSort,f:state.storeFilters,p:state.storePage,z:state.storePageSize,w:state.storeWork,b:state.storeBrowseMode,ss:state.storeSearchSort,q:state.storeQuery};
  if(view==="works")return {q:state.worksSearch||"",w:state.workOverview||""};
  if(view==="annotations")return {q:state.annotationSearch||"",m:state.annotationView||"works"};
  if(view==="home")return {m:Number(state.dashboardMetricIndex)||0,sm:state.globalSearchMode||"traditional",q:state.globalSearch||""};
  if(view==="record")return {q:state.recordFind||"",rr:state.researcherRecordId||""};
  if(view==="faq")return {q:state.faqSearch||"",p:state.faqPage||1};
  return null;
}
function applyCompressedTableUrlState(value,view=state.view){
  if(!value||typeof value!=="object")return;
  if(view==="list"){
    const f=activeFile();if(!f)return;
    if(Array.isArray(value.c))state.tableColumns.list=value.c;
    if(value.s)state.sorts[f.id]=value.s;
    if(value.f&&typeof value.f==="object")state.listFilters[f.id]=value.f;
    if(Number.isFinite(+value.p))state.pages[f.id]=Math.max(1,+value.p);
    if(Number.isFinite(+value.z))state.pageSize=Math.max(10,+value.z);
    if(typeof value.q==="string")state.searches[f.id]=value.q;
  }else if(view==="global"){
    if(Array.isArray(value.c))state.tableColumns.global=value.c;
    if(value.s)state.globalSort=value.s;
    if(Array.isArray(value.f))state.globalFilters=value.f;
    if(value.sf&&typeof value.sf==="object"&&!Array.isArray(value.sf))state.searchFacetFilters=Object.fromEntries(Object.entries(value.sf).map(([field,values])=>[field,Array.isArray(values)?values.map(String):[]]).filter(([,values])=>values.length));
    if(Number.isFinite(+value.p))state.globalPage=Math.max(1,+value.p);
    if(Number.isFinite(+value.z))state.pageSize=Math.max(10,+value.z);
    if(typeof value.q==="string")state.globalSearch=value.q;
    if(["traditional","database"].includes(value.m))state.globalSearchMode=value.m;
    if(["similarity","mmr","filter"].includes(value.dm))state.dbSearchMethod=value.dm;
    if(value.dw&&typeof value.dw==="object"&&!Array.isArray(value.dw))state.dbSearchWhere=value.dw;
    if(Number.isFinite(+value.dk))state.dbSearchFetchK=Math.max(1,+value.dk);
    if(Number.isFinite(+value.dl))state.dbSearchLambda=Math.max(0,Math.min(1,+value.dl));
    if(typeof value.ao==="boolean")state.globalAdvancedOpen=value.ao;
    if(value.l&&typeof value.l==="object")state.searchResultLayouts={...state.searchResultLayouts,...value.l};
    if(state.globalSearchMode==="database"&&(state.globalSearch||Object.keys(dbSearchWhere()).length))state.globalSearchAutoRun=true;
  }else if(view==="vector"){
    if(Array.isArray(value.c))state.tableColumns.vector=value.c;
    if(value.s)state.storeSort=value.s;
    if(value.f&&typeof value.f==="object")state.storeFilters=value.f;
    if(Number.isFinite(+value.p))state.storePage=Math.max(1,+value.p);
    if(Number.isFinite(+value.z))state.storePageSize=Math.max(10,+value.z);
    if(typeof value.w==="string")state.storeWork=value.w;
    if(["works","records"].includes(value.b))state.storeBrowseMode=value.b;
    if(value.ss)state.storeSearchSort=value.ss;
    if(typeof value.q==="string")state.storeQuery=value.q;
  }else if(view==="works"){
    if(typeof value.q==="string")state.worksSearch=value.q;
    if(typeof value.w==="string")state.workOverview=value.w;
  }else if(view==="annotations"){
    if(typeof value.q==="string")state.annotationSearch=value.q;
    if(["works","recent"].includes(value.m))state.annotationView=value.m;
  }else if(view==="home"){
    if(Number.isFinite(+value.m))state.dashboardMetricIndex=Math.max(0,+value.m);
    if(["traditional","database"].includes(value.sm))state.globalSearchMode=value.sm;
    if(typeof value.q==="string")state.globalSearch=value.q;
  }else if(view==="record"){
    if(typeof value.q==="string")state.recordFind=value.q;
    if(typeof value.rr==="string")state.researcherRecordId=value.rr;
  }else if(view==="faq"){
    if(typeof value.q==="string")state.faqSearch=value.q;
    if(Number.isFinite(+value.p))state.faqPage=Math.max(1,+value.p);
  }
}

function urlFromState(){
  const url=new URL(location.href);
  const params=url.searchParams;
  for(const key of ["view","file","record","store","work","dbpage","browse","pdfpage","ts"])params.delete(key);
  params.set("view",state.view||"home");
  if(state.activeFileId)params.set("file",state.activeFileId);
  const file=activeFile();
  if(file&&Number.isFinite(selectedIndex(file)))params.set("record",String(selectedIndex(file)));
  if(state.activeStore)params.set("store",state.activeStore);
  if(state.storeWork)params.set("work",state.storeWork);
  if(state.storePage>1)params.set("dbpage",String(state.storePage));
  if(state.storeBrowseMode&&state.storeBrowseMode!=="works")params.set("browse",state.storeBrowseMode);
  if(state.view==="pdf"&&state.pdf.page>1)params.set("pdfpage",String(state.pdf.page));
  const tableState=currentTableUrlState();
  if(tableState){const compressed=compressUrlState(tableState);if(compressed)params.set("ts",compressed)}
  const path=viewPathMap[state.view]||"/";
  const query=params.toString();
  return `${path}${query?`?${query}`:""}${url.hash}`;
}
function syncUrl({replace=false,href=null}={}){
  href=href||urlFromState();
  const current=`${location.pathname}${location.search}${location.hash}`;
  if(href===current)return;
  const snapshot=navSnapshot();
  if(urlSyncHook){urlSyncHook(href,{replace,snapshot});return}
  try{
    history[replace?"replaceState":"pushState"](snapshot,"",href);
  }catch(error){console.warn("Could not update browser URL state",error)}
}
function applyUrlState(){
  const params=new URLSearchParams(location.search);
  const pathView=pathViewMap[location.pathname];
  const view=pathView||params.get("view");
  if(view&&viewConfig.some(item=>item.id===view))state.view=view;
  const file=params.get("file");
  // A file parameter is authoritative. If the referenced browser-local JSONL
  // is not loaded yet, show the corpus-workspace CTA instead of silently
  // substituting another file from IndexedDB. Once the same content is loaded,
  // its stable content-derived id lets the rest of the URL state apply.
  if(file)state.activeFileId=state.files.some(item=>item.id===file)?file:null;
  const record=Number(params.get("record"));
  if(state.activeFileId&&Number.isInteger(record)&&record>=0)state.selected[state.activeFileId]=record;
  const store=params.get("store");
  if(store)state.activeStore=store;
  const work=params.get("work");
  if(work!==null)state.storeWork=work;
  const dbPage=Number(params.get("dbpage"));
  if(Number.isFinite(dbPage)&&dbPage>0)state.storePage=dbPage;
  const browse=params.get("browse");
  if(["works","records"].includes(browse))state.storeBrowseMode=browse;
  const pdfPage=Number(params.get("pdfpage"));
  if(Number.isFinite(pdfPage)&&pdfPage>0)state.pdf.page=pdfPage;
  const compressed=params.get("ts");
  if(compressed)applyCompressedTableUrlState(decompressUrlState(compressed));
}
function navigateTo(view,{fileId=null,index=null,push=true,href=null}={}){
  if(!canAccessPage(view))view="home";
  // Research performs an authoritative store refresh on entry. Do not redirect
  // from this legacy navigation bridge using the cached hasCorpusDb() value; a
  // newly created/restored collection may not have reached shell state yet.
  const before=navSnapshot();
  if(push){
    const last=state.navHistory[state.navHistory.length-1];
    if(!sameSnapshot(last,before)){
      state.navHistory.push(before);
      if(state.navHistory.length>50)state.navHistory.shift();
    }
    state.navForward=[];
  }
  if(fileId&&state.files.some(file=>file.id===fileId))state.activeFileId=fileId;
  if(index!==null&&state.activeFileId)state.selected[state.activeFileId]=Number(index);
  if(state.view==="vector"&&view!=="vector"){
    // Store pages/search results duplicate records already persisted in Chroma.
    // Drop those transient copies when leaving Vector Stores.
    state.storeRecords=[];
    state.storeSearchResults=[];
  }
  state.view=view;
  persistPrefs();
  syncUrl({replace:!push,href});
  shell();
  renderView();
}
function goBack(){
  while(state.navHistory.length){
    const target=state.navHistory.pop();
    if(!target)continue;
    if(target.activeFileId&&!state.files.some(file=>file.id===target.activeFileId))continue;
    state.navForward.push(navSnapshot());
    if(state.navForward.length>50)state.navForward.shift();
    applyNavSnapshot(target);
    persistPrefs();syncUrl({replace:true});shell();renderView();return;
  }
}
function goForward(){
  while(state.navForward.length){
    const target=state.navForward.pop();
    if(!target)continue;
    if(target.activeFileId&&!state.files.some(file=>file.id===target.activeFileId))continue;
    state.navHistory.push(navSnapshot());
    applyNavSnapshot(target);
    persistPrefs();syncUrl({replace:true});shell();renderView();return;
  }
}
function breadcrumbHtml(){
  const previous=state.navHistory[state.navHistory.length-1];
  const next=state.navForward[state.navForward.length-1];
  const current=viewLabel(state.view);
  return `<div class="breadcrumbs"><div class="breadcrumb-nav"><button class="breadcrumb-back" id="breadcrumbBack" type="button" ${previous?"":"disabled"}>← Back</button><button class="breadcrumb-forward" id="breadcrumbForward" type="button" ${next?"":"disabled"}>Forward →</button></div><span class="crumb-path">${previous?`${esc(viewLabel(previous.view))} <span class="crumb-sep">›</span> `:"<span class=\"crumb-home\">DerridAI</span> <span class=\"crumb-sep\">›</span> "}<strong>${esc(current)}</strong>${next?` <span class="crumb-sep">›</span> ${esc(viewLabel(next.view))}`:""}</span></div>`;
}

let operationDockResizeWired=false;

function applyOperationStackPosition(stack){
  if(!stack)return;
  const position=state.operationStackPosition;
  if(!position){
    stack.style.left="";
    stack.style.top="";
    stack.style.right="";
    stack.style.bottom="";
    stack.style.transform="";
    stack.style.translate="";
    stack.style.removeProperty("--operation-stack-max-height");
    stack.classList.remove("user-positioned");
    return;
  }
  const rect=stack.getBoundingClientRect();
  const maxLeft=Math.max(8,window.innerWidth-Math.max(rect.width,280)-8);
  const maxTop=Math.max(8,window.innerHeight-52);
  const left=Math.min(maxLeft,Math.max(8,Number(position.left)||8));
  const top=Math.min(maxTop,Math.max(8,Number(position.top)||8));
  state.operationStackPosition={left,top};
  stack.style.left=`${left}px`;
  stack.style.top=`${top}px`;
  stack.style.right="auto";
  stack.style.bottom="auto";
  stack.style.translate="none";
  stack.style.setProperty("--operation-stack-max-height",`${Math.max(120,window.innerHeight-top-8)}px`);
  stack.classList.add("user-positioned");
}
function setOperationDockMinimized(minimized){
  state.operationToastsMinimized=Boolean(minimized);
  persistPrefs();
  const stack=document.querySelector("#operationProgressStack");
  if(!stack)return;
  stack.classList.toggle("minimized",state.operationToastsMinimized);
  stack.dataset.surface=state.operationToastsMinimized?"glass":"overlay";
  const toggle=stack.querySelector("#operationStackToggle");
  if(toggle){
    toggle.setAttribute("aria-expanded",state.operationToastsMinimized?"false":"true");
    toggle.setAttribute("aria-label",state.operationToastsMinimized
      ?tr("operations.expand","Show operations")
      :tr("operations.collapse","Hide operations"));
  }
  applyOperationStackPosition(stack);
  updateOperationStackCount();
}
function announceOperationDock(message){
  const live=document.querySelector("#operationStackLive");
  if(!live||!message)return;
  live.textContent="";
  live.textContent=message;
}
function operationDockCardStats(stack){
  let active=0,failed=0,finished=0,primaryLabel="",primaryPercent=null;
  stack.querySelectorAll(".operation-progress").forEach(panel=>{
    const job=panel.dataset.jobOperation?state.jobs.find(item=>item.id===panel.dataset.jobOperation):null;
    if(job){
      if(isActiveJobStatus(job.status)){
        active+=1;
        if(!primaryLabel){
          primaryLabel=jobLabel(job);
          primaryPercent=jobProgressPercent(job);
        }
      }else if(job.status==="failed")failed+=1;
      else finished+=1;
      return;
    }
    if(panel.classList.contains("failed")){failed+=1;return;}
    if(panel.classList.contains("operation-complete")){finished+=1;return;}
    active+=1;
    if(!primaryLabel){
      primaryLabel=panel.querySelector("b")?.textContent||"";
      const width=panel.querySelector("[data-progress-bar], .operation-progress-track i")?.style?.width||"";
      const parsed=Number.parseInt(width,10);
      primaryPercent=Number.isNaN(parsed)?null:parsed;
    }
  });
  return {active,failed,finished,primaryLabel,primaryPercent};
}
function wireOperationStackDrag(stack){
  const handle=stack?.querySelector("[data-operation-drag]");
  if(!handle||handle.dataset.dragWired)return;
  handle.dataset.dragWired="1";
  handle.addEventListener("pointerdown",event=>{
    if(event.button!==0||event.target.closest("button"))return;
    event.preventDefault();
    const rect=stack.getBoundingClientRect();
    const startX=event.clientX,startY=event.clientY,startLeft=rect.left,startTop=rect.top,width=rect.width;
    const maxLeft=Math.max(8,window.innerWidth-width-8);
    const maxTop=Math.max(8,window.innerHeight-52);
    let nextLeft=startLeft,nextTop=startTop,frame=0;
    handle.classList.add("dragging");
    stack.classList.add("is-dragging");
    stack.style.translate="none";
    stack.style.left=`${startLeft}px`;
    stack.style.top=`${startTop}px`;
    stack.style.right="auto";
    stack.style.bottom="auto";
    try{handle.setPointerCapture(event.pointerId)}catch{/* pointer capture is optional on this surface */}
    const paint=()=>{
      frame=0;
      stack.style.transform=`translate3d(${Math.round(nextLeft-startLeft)}px,${Math.round(nextTop-startTop)}px,0)`;
    };
    const move=e=>{
      nextLeft=Math.min(maxLeft,Math.max(8,startLeft+(e.clientX-startX)));
      nextTop=Math.min(maxTop,Math.max(8,startTop+(e.clientY-startY)));
      if(!frame)frame=requestAnimationFrame(paint);
    };
    const done=e=>{
      if(frame)cancelAnimationFrame(frame);
      stack.style.transform="";
      state.operationStackPosition={left:Math.round(nextLeft),top:Math.round(nextTop)};
      applyOperationStackPosition(stack);
      handle.classList.remove("dragging");
      stack.classList.remove("is-dragging");
      window.removeEventListener("pointermove",move);
      window.removeEventListener("pointerup",done);
      window.removeEventListener("pointercancel",done);
      try{handle.releasePointerCapture(e?.pointerId)}catch{/* pointer capture is optional on this surface */}
      persistPrefs();
    };
    window.addEventListener("pointermove",move,{passive:true});
    window.addEventListener("pointerup",done,{once:true});
    window.addEventListener("pointercancel",done,{once:true});
  });
  handle.addEventListener("dblclick",event=>{
    if(event.target.closest("button"))return;
    state.operationStackPosition=null;
    persistPrefs();
    applyOperationStackPosition(stack);
  });
  handle.addEventListener("keydown",event=>{
    if(event.key==="Escape"){
      if(!state.operationToastsMinimized){
        event.preventDefault();
        setOperationDockMinimized(true);
      }
      return;
    }
    if(!["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(event.key)||event.target.closest("button"))return;
    event.preventDefault();
    const rect=stack.getBoundingClientRect();
    const step=event.shiftKey?40:12;
    let left=rect.left,top=rect.top;
    if(event.key==="ArrowLeft")left-=step;
    if(event.key==="ArrowRight")left+=step;
    if(event.key==="ArrowUp")top-=step;
    if(event.key==="ArrowDown")top+=step;
    state.operationStackPosition={left:Math.round(Math.max(8,Math.min(window.innerWidth-220,left))),top:Math.round(Math.max(8,Math.min(window.innerHeight-52,top)))};
    persistPrefs();
    applyOperationStackPosition(stack);
  });
  if(!operationDockResizeWired){
    operationDockResizeWired=true;
    window.addEventListener("resize",()=>applyOperationStackPosition(document.querySelector("#operationProgressStack")),{passive:true});
  }
}

function progressStack(){
  let stack=document.querySelector("#operationProgressStack");
  if(!stack){
    const dragHelp=tr("operations.drag_help","Drag anywhere · double-click to recenter");
    const title=tr("operations.title","Operations");
    stack=document.createElement("aside");
    stack.id="operationProgressStack";
    stack.className=`operation-progress-stack${state.operationToastsMinimized?" minimized":""}`;
    stack.dataset.surface=state.operationToastsMinimized?"glass":"overlay";
    stack.setAttribute("role","complementary");
    stack.setAttribute("aria-label",title);
    stack.innerHTML=`<div class="operation-stack-toolbar" data-operation-drag tabindex="0" role="group" aria-label="${esc(dragHelp)}" title="${esc(dragHelp)}"><span class="operation-drag-grip" aria-hidden="true"></span><button type="button" class="operation-dock-toggle" id="operationStackToggle" aria-expanded="${state.operationToastsMinimized?"false":"true"}" aria-controls="operationStackItems" aria-label="${esc(state.operationToastsMinimized?tr("operations.expand","Show operations"):tr("operations.collapse","Hide operations"))}"><span class="operation-dock-dot" aria-hidden="true"></span><span class="operation-dock-copy"><b class="operation-dock-title">${esc(title)}</b><span id="operationStackCount"></span></span><span class="operation-dock-chevron" aria-hidden="true"></span></button><button type="button" class="btn tiny operation-dock-clear" id="operationStackClearFinished" hidden>${esc(tr("operations.clear_finished","Clear finished"))}</button></div><div id="operationStackLive" class="sr-only" aria-live="polite"></div><div id="operationStackItems" class="operation-stack-items"></div>`;
    document.body.appendChild(stack);
    wireOperationStackDrag(stack);
    applyOperationStackPosition(stack);
    stack.querySelector("#operationStackToggle").addEventListener("click",()=>setOperationDockMinimized(!state.operationToastsMinimized));
    stack.querySelector("#operationStackClearFinished").addEventListener("click",()=>clearFinishedOperations());
    stack.addEventListener("keydown",event=>{
      if(event.key==="Escape"&&!state.operationToastsMinimized&&!event.target.closest("input,textarea,select")){
        event.preventDefault();
        setOperationDockMinimized(true);
      }
    });
  }
  return stack.querySelector(".operation-stack-items")||stack;
}
function updateOperationStackCount(){
  const stack=document.querySelector("#operationProgressStack");
  if(!stack)return;
  const count=stack.querySelectorAll(".operation-progress").length;
  if(!shouldMountOperationDock(count)){
    stack.remove();
    return;
  }
  const stats=operationDockCardStats(stack);
  const summary=dockCollapsedSummary(stats);
  const label=stack.querySelector("#operationStackCount");
  if(label){
    label.textContent=trf(summary.key,summary.fallback,summary.values);
    // When there is nothing more specific to say, the summary falls back to the dock's own title; do not say it twice.
    label.hidden=label.textContent===tr("operations.title","Operations");
  }
  stack.dataset.tone=summary.tone;
  if(summary.percent==null)stack.style.removeProperty("--operation-dock-progress");
  else stack.style.setProperty("--operation-dock-progress",`${summary.percent}%`);
  const clear=stack.querySelector("#operationStackClearFinished");
  if(clear){
    const canClear=stats.failed+stats.finished>0;
    clear.hidden=!canClear||state.operationToastsMinimized;
    clear.disabled=!canClear;
  }
  const toggle=stack.querySelector("#operationStackToggle");
  if(toggle){
    toggle.setAttribute("aria-expanded",state.operationToastsMinimized?"false":"true");
    toggle.setAttribute("aria-label",state.operationToastsMinimized
      ?tr("operations.expand","Show operations")
      :tr("operations.collapse","Hide operations"));
  }
}
function showOperationProgress(title,total){
  const id=uid();
  const stack=progressStack();
  const panel=document.createElement("div");
  panel.className="operation-progress show";
  panel.dataset.operationId=id;
  panel.innerHTML=`<div class="operation-progress-head"><div><b>${esc(title)}</b><span data-progress-text>0 of ${total.toLocaleString()}</span></div><div class="spinner small-spinner"></div></div><div class="operation-progress-track"><i data-progress-bar style="width:0%"></i></div><div class="operation-progress-detail" data-progress-detail></div>`;
  stack.appendChild(panel);
  updateOperationStackCount();
  state.operationProgress[id]={title,total,done:0};
  return id;
}
function updateOperationProgress(id,done,total,detail=""){
  const panel=document.querySelector(`[data-operation-id="${CSS.escape(id)}"]`);
  if(!panel)return;
  const pct=Math.round(total?done/total*100:100);
  const text=panel.querySelector("[data-progress-text]");
  const bar=panel.querySelector("[data-progress-bar]");
  const detailEl=panel.querySelector("[data-progress-detail]");
  if(text)text.textContent=`${done.toLocaleString()} of ${total.toLocaleString()} (${pct}%)`;
  if(bar)bar.style.width=`${pct}%`;
  if(detailEl)detailEl.textContent=detail;
  state.operationProgress[id]={...(state.operationProgress[id]||{}),done,total,detail};
}
function hideOperationProgress(id,delay=200){
  // Completed foreground operations remain visible until the user dismisses
  // them. ``delay`` is retained for call-site compatibility but is no longer
  // used to auto-remove operation history.
  const panel=document.querySelector(`[data-operation-id="${CSS.escape(id)}"]`);
  if(!panel)return;
  panel.classList.add("show","operation-complete");
  panel.querySelector(".spinner")?.remove();
  const head=panel.querySelector(".operation-progress-head");
  if(head&&!head.querySelector("[data-dismiss-operation]")){
    const button=document.createElement("button");
    button.className="btn tiny";button.dataset.dismissOperation=id;button.textContent=tr("ui.dismiss","Dismiss");
    button.onclick=()=>{panel.remove();delete state.operationProgress[id];updateOperationStackCount()};
    head.appendChild(button);
  }
  state.operationProgress[id]={...(state.operationProgress[id]||{}),finished:true};
}


const jobCompletionNotified={};
const completedJobToastTimers={};

function pruneClientJobState(jobId,{removeHistory=true}={}){
  state.jobs=state.jobs.filter(job=>job.id!==jobId);
  delete state.jobApplied?.[jobId];
  delete state.upsertJobApplied?.[jobId];
  delete jobCompletionNotified[jobId];
  clearTimeout(completedJobToastTimers[jobId]);
  delete completedJobToastTimers[jobId];
  document.querySelector(`[data-job-operation="${CSS.escape(jobId)}"]`)?.remove();
  if(removeHistory&&Array.isArray(state.ragConfig.run_history)){
    state.ragConfig.run_history=state.ragConfig.run_history.filter(item=>item.job_id!==jobId);
  }
  updateOperationStackCount();
}

async function removeFinishedJob(jobId,{refresh=true}={}){
  try{
    await api(`/api/jobs/${encodeURIComponent(jobId)}`,{method:"DELETE"});
    pruneClientJobState(jobId);
    persistPrefs();
    if(refresh)await refreshJobs({rerender:state.view==="home"});
    else updateOperationStackCount();
  }catch(error){
    toast(trf("operations.remove_failed","Could not remove the operation: {message}",{message:error.message}));
  }
}

async function clearFinishedOperations(){
  try{
    await api("/api/jobs",{method:"DELETE"});
    document.querySelectorAll("#operationProgressStack [data-operation-id].operation-complete").forEach(panel=>{
      delete state.operationProgress[panel.dataset.operationId];
      panel.remove();
    });
    await refreshJobs({rerender:true});
    updateOperationStackCount();
  }catch(error){
    toast(trf("operations.clear_failed","Could not clear jobs: {message}",{message:error.message}));
  }
}

async function syncUpsertJobReceipts(job){
  if(job.type!=="upsert"||Number(job.completed||0)<=0)return;
  const applied=Number(state.upsertJobApplied?.[job.id]||0);
  if(Number(job.completed||0)<=applied)return;
  let detail;
  try{detail=await api(`/api/jobs/${encodeURIComponent(job.id)}`)}catch(error){console.warn("Could not fetch upsert receipts",error);return}
  const results=detail.results||[];
  if(!state.upsertJobApplied)state.upsertJobApplied={};
  for(const result of results.slice(applied)){
    const item=reviewItemFromKey(result.key);
    const stores=[result.store_name,...(result.mirrored_stores||[])].filter(Boolean);
    for(const store of stores){
      if(!state.upsertState[store])state.upsertState[store]={};
      if(!state.storePresence[store])state.storePresence[store]={};
      if(!state.storePresenceIds[store])state.storePresenceIds[store]={};
      state.upsertState[store][result.key]={
        fingerprint:result.fingerprint,
        timestamp:result.completed_at||new Date().toISOString(),
        chroma_id:result.chroma_id,
        job_id:job.id,
        updates_count:result.updates_count,
      };
      state.storePresence[store][result.key]=true;
      state.storePresenceIds[store][result.key]=result.chroma_id||"";
      if(state.upsertIgnored?.[store])delete state.upsertIgnored[store][result.key];
    }
    // If the local record changed while the background upsert was running, the
    // stored fingerprint intentionally remains the older one, so status becomes Pending.
    if(item&&result.fingerprint!==recordFingerprint(item.file.records[item.index])){
      // no-op: fingerprint mismatch is the pending-state signal
    }
  }
  state.upsertJobApplied[job.id]=results.length;
  persistPrefs();
  updateDbStatusElements();
  if(!["queued","running","cancelling"].includes(detail.status)){
    // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
    try{await refreshStores()}catch{}
  }
}

async function refreshJobs({rerender=false}={}){
  try{
    const payload=await api("/api/jobs");
    const previousJobs=[...state.jobs];
    const previous=new Map(previousJobs.map(job=>[job.id,job.status]));
    state.jobs=payload.jobs||[];
    state.jobsLastFetched=Date.now();
    const knownJobIds=new Set(state.jobs.map(job=>job.id));
    const disappearedRagIds=previousJobs.filter(job=>job.type==="rag"&&!knownJobIds.has(job.id)).map(job=>job.id);
    if(disappearedRagIds.length&&Array.isArray(state.ragConfig.run_history)){
      const removed=new Set(disappearedRagIds);
      state.ragConfig.run_history=state.ragConfig.run_history.filter(item=>!removed.has(item.job_id));
      for(const id of disappearedRagIds)pruneClientJobState(id,{removeHistory:false});
      persistPrefs();
    }
    for(const id of Object.keys(state.jobApplied||{}))if(!knownJobIds.has(id))delete state.jobApplied[id];
    for(const id of Object.keys(state.upsertJobApplied||{}))if(!knownJobIds.has(id))delete state.upsertJobApplied[id];
    for(const job of state.jobs)await syncUpsertJobReceipts(job);
    syncJobProgressToasts(previous);
    const operationsButton=document.querySelector("#operationsBtn");
    if(operationsButton){
      const active=state.jobs.filter(job=>["queued","running","cancelling"].includes(job.status)).length;
      operationsButton.classList.toggle("soft",active>0);
      operationsButton.innerHTML=`${icon("history")}Operations <span class="button-count">${active}</span>`;
    }
    notifyOperationsChanged();
    if(rerender&&state.view==="home")refreshCorpusBuildsHomeCardOnly();
    if(state.view==="rag")refreshRagProgressPanel();
    return state.jobs;
  }catch(error){
    console.warn("Could not refresh background jobs",error);
    return state.jobs;
  }
}
function jobLabel(job){
  if(job.type==="rag")return tr("operations.job.rag","RAG pipeline");
  if(job.type==="upsert")return tr("operations.job.upsert","Chroma upsert");
  if(job.type==="pdf_corpus")return tr("pdf_corpus.operation_label","PDF corpus build");
  if(job.type==="llm_tool"){
    const known={
      pdf_clean_text:tr("operations.job.pdf_clean_text","PDF · clean text"),
      pdf_draft_record:tr("operations.job.pdf_draft_record","PDF · draft record"),
      pdf_link_record:tr("operations.job.pdf_link_record","PDF · link record"),
      rag_grade:tr("operations.job.rag_grade","RAG · grade response"),
      rag_grade_batch:tr("operations.job.rag_grade_batch","RAG · grade response cache"),
      work_metadata:tr("works.populate_metadata_llm","Populate metadata with LLM"),
    };
    return job.label||known[job.tool||job.mode]||tr("operations.job.llm_tool","LLM operation");
  }
  return job.mode==="auto"?tr("operations.job.auto","Auto-improve"):tr("operations.job.review","LLM review");
}
function jobProviderSummary(job){
  if(job.type==="upsert")return [job.label,job.store_name||"collection"].filter(Boolean).join(" · ");
  const profile=job.provider_profile_id?providerProfiles().find(item=>item.id===job.provider_profile_id):null;
  const providerName=profile?providerDisplayName(profile):(job.provider||"");
  const model=job.model||"";
  return [providerName,model].filter(Boolean).join(" · ");
}
function jobElapsedSeconds(job){
  const start=job.started_at?new Date(job.started_at).getTime():null;
  if(!Number.isFinite(start))return 0;
  const end=job.finished_at?new Date(job.finished_at).getTime():Date.now();
  return Math.max(0,(end-start)/1000);
}
function humanDuration(seconds){
  return formatDuration(seconds,state.translations?.locale||"en-US");
}
// Names of the facts shown for an operation (panel rows and the details dialog), translated at render time.
const OPERATION_FACT_NAMES={
  started_by:["operations.fact.started_by","Started by"],
  model:["operations.fact.model","Model"],
  fields:["operations.fact.fields","Fields"],
  current_record:["operations.fact.current_record","Current record"],
  pending_results:["operations.fact.pending_results","Pending results"],
  pending_changes:["operations.fact.pending_changes","Pending changes"],
  unprocessed_records:["operations.fact.unprocessed_records","Unprocessed records"],
  accepted:["operations.fact.accepted","Accepted"],
  rejected:["operations.fact.rejected","Rejected"],
  decision:["operations.fact.decision","Decision"],
  generation:["operations.fact.generation","Generation"],
  embedding:["operations.fact.embedding","Embedding"],
  reranker:["operations.fact.reranker","Reranker"],
  collection:["operations.fact.collection","Collection"],
  stage:["operations.fact.stage","Stage"],
  languages:["operations.fact.languages","Languages"],
  retrieval:["operations.fact.retrieval","Retrieval"],
  auto_grade:["operations.fact.auto_grade","Auto-grade"],
  operation:["operations.fact.operation","Operation"],
  provider:["operations.fact.provider","Provider"],
  max_concurrent:["operations.fact.max_concurrent","Max concurrent"],
  top_n:["operations.fact.top_n","Top N"],
  pdf:["operations.fact.pdf","PDF"],
  page:["operations.fact.page","Page"],
  cached_response:["operations.fact.cached_response","Cached response"],
  scope:["operations.fact.scope","Scope"],
  records:["operations.fact.records","Records"],
  committed:["operations.fact.committed","Committed"],
  language_mirrors:["operations.fact.language_mirrors","Language mirrors"],
  total_time:["operations.fact.total_time","Total time"],
  elapsed:["operations.fact.elapsed","Elapsed"],
};
function fact(id){const [key,fallback]=OPERATION_FACT_NAMES[id];return tr(key,fallback)}
function decisionLabel(state){
  const id=String(state||"pending");
  return tr(`operations.decision.${id}`,id.replaceAll("_"," "));
}
function operationDetailPairs(job){
  const request=job.request||{};
  const pairs=[];
  if(job.owner)pairs.push([fact("started_by"),job.owner]);
  if(job.type==="llm"){
    pairs.push(
      [fact("model"),job.model||job.provider||"—"],
      [fact("fields"),(job.fields||[]).join(", ")||"—"],
      [fact("current_record"),job.current_record_id||"—"],
      [fact("pending_results"),job.pending_result_count??0],
      [fact("pending_changes"),job.pending_change_count??0],
      [fact("unprocessed_records"),job.remaining_record_count??Math.max(0,(job.total||0)-(job.completed||0))],
      [fact("accepted"),trf("operations.fact.result_field_counts","{results} result(s) · {fields} field(s)",{results:job.accepted_results||0,fields:job.accepted_fields||0})],
      [fact("rejected"),trf("operations.fact.result_field_counts","{results} result(s) · {fields} field(s)",{results:job.rejected_results||0,fields:job.rejected_fields||0})],
      [fact("decision"),decisionLabel(job.resolution_state||"pending")]
    );
    if(request.generation&&Object.keys(request.generation).length)pairs.push([fact("generation"),JSON.stringify(request.generation)]);
  }else if(job.type==="rag"){
    const sourceStore=state.stores.find(store=>store.name===job.source_collection);
    pairs.push(
      [fact("generation"),job.model||job.provider||"—"],
      [fact("embedding"),sourceStore?.embedding_model||sourceStore?.embedding_provider||"—"],
      [fact("reranker"),request.cross_encoder_model||request.reranker||"—"],
      [fact("collection"),job.source_collection||"—"],
      [fact("stage"),job.stage||"—"],
      [fact("languages"),(request.locales||[]).join(", ")||"—"],
      [fact("retrieval"),(request.search_types||[]).join(" + ")||"—"],
      ["k / fetch_k",`${request.k??"—"} / ${request.fetch_k??"—"}`],
      ["RRF k",request.rrf_k??"—"],
      [fact("top_n"),request.rerank_top_n??"—"]
    );
    if(request.auto_grade){
      const gradeProfile=request.auto_grade_provider_profile_id?providerProfiles().find(item=>item.id===request.auto_grade_provider_profile_id):null;
      pairs.push([fact("auto_grade"),`${gradeProfile?providerDisplayName(gradeProfile):(request.auto_grade_provider||job.provider||"grader")} · ${request.auto_grade_model||job.model||"model"}`]);
    }
  }else if(job.type==="pdf_corpus"){
    pairs.push(
      [tr("pdf_corpus.source_pdf","Source PDF"),job.source_filename||"—"],
      [tr("pdf_corpus.stage","Stage"),job.stage||"—"],
      [tr("pdf_corpus.records","records"),job.record_count??0],
      [tr("pdf_corpus.need_review","need review"),job.review_count??0],
      [tr("pdf_corpus.unresolved_regions","Unresolved regions"),job.unresolved_regions??0],
      [tr("pdf_corpus.concurrent_requests","max concurrent request(s)"),job.max_concurrent_requests??1]
    );
  }else if(job.type==="llm_tool"){
    pairs.push([fact("operation"),job.label||job.tool||job.mode||"LLM tool"],[fact("provider"),job.provider||"—"],[fact("model"),job.model||"—"],[fact("stage"),job.stage||"—"],[fact("max_concurrent"),job.max_concurrent_requests??"—"]);
    if(request.pdf_file)pairs.push([fact("pdf"),request.pdf_file],[fact("page"),request.pdf_page??"—"]);
    if(request.response_record_id)pairs.push([fact("cached_response"),request.response_record_id]);
  }else if(job.type==="upsert"){
    pairs.push([fact("collection"),job.store_name||"—"],[fact("scope"),job.label||request.label||tr("operations.sub.records","records")],[fact("records"),job.total??0],[fact("committed"),job.completed??0],[fact("current_record"),job.current_record_id||"—"]);
    const mirrors=Object.entries(job.mirrored||{}).map(([name,count])=>`${name}: ${count}`).join(" · ");
    if(mirrors)pairs.push([fact("language_mirrors"),mirrors]);
  }
  pairs.push([fact(job.finished_at?"total_time":"elapsed"),humanDuration(jobElapsedSeconds(job))]);
  return pairs;
}
async function cancelBackgroundJob(jobId,{refresh=true}={}){
  const job=state.jobs.find(item=>item.id===jobId);
  if(job?.cancel_requested)return;
  try{
    const updated=await api(`/api/jobs/${encodeURIComponent(jobId)}/cancel`,{
      method:"POST",
      body:"{}",
    });
    state.jobs=state.jobs.map(item=>item.id===jobId?updated:item);
    syncJobProgressToasts();
    if(refresh){
      if(state.view==="home")refreshOperationsPanelOnly();
      if(state.view==="rag")refreshRagProgressPanel();
    }
    const cancellationMessage=updated.type==="llm"||updated.type==="llm_tool"
      ? "interrupting the active model stream"
      : updated.type==="rag"
        ? "interrupting model streaming or stopping at the next vector/rerank checkpoint"
        : updated.type==="upsert"
          ? "finishing the current Chroma batch, then stopping"
          : "stopping at the next safe checkpoint";
    toast(updated.status==="cancelled"
      ? `${jobLabel(updated)} cancelled`
      : `Cancellation requested for ${jobLabel(updated)} · ${cancellationMessage}.`);
    return updated;
  }catch(error){
    toast(`Cancel failed: ${error.message}`);
    return null;
  }
}

function ensureJobProgressCard(job){
  const stack=progressStack();
  let panel=stack.querySelector(`[data-job-operation="${CSS.escape(job.id)}"]`);
  if(!panel){
    panel=document.createElement("article");
    panel.className="operation-progress show";
    panel.dataset.jobOperation=job.id;
    stack.appendChild(panel);
  }
  const pct=jobProgressPercent(job);
  const active=isActiveJobStatus(job.status);
  const tone=statusBadgeTone(job.status);
  panel.classList.toggle("failed",job.status==="failed");
  panel.classList.toggle("operation-complete",isTerminalJobStatus(job.status));
  panel.dataset.tone=tone;
  const cancellationDetail=job.type==="llm"||job.type==="llm_tool"
    ?"Cancellation requested · interrupting the active model stream."
    : job.type==="rag"
      ?"Cancellation requested · interrupting model streaming or waiting for the current vector/rerank checkpoint."
      : job.type==="upsert"
        ?"Cancellation requested · the current Chroma batch will finish, then the job stops."
        : "Cancellation requested.";
  const detail=job.status==="cancelling"||job.cancel_requested
    ?cancellationDetail
    : job.status==="failed"
      ? trf("operations.failed_help","Failed · {detail}",{detail:String(job.fatal_error||job.stage_detail||"Operation failed")})
    : job.status==="completed"
      ? tr("operations.completed_help","Completed · open the result or dismiss")
    : job.status==="cancelled"
      ? tr("operations.cancelled_help","Cancelled · partial results may still be available")
    : job.type==="rag"
      ? `${job.stage_detail||job.stage||"Running RAG pipeline"}`
      : job.type==="upsert"
        ? `${job.store_name||"collection"} · ${job.completed}/${job.total} records committed`
        : job.type==="llm_tool"
          ? `${job.stage_detail||jobLabel(job)}`
          : `${job.failed?`${job.failed} failed · `:""}${job.current_record_id?`Reviewing ${job.current_record_id}`:"Background operation"}`;
  const httpIndex=String(detail).search(/\bHTTP\s+\d{3}\b/i);
  const detailHtml=httpIndex>=0
    ? `${esc(String(detail).slice(0,httpIndex))}<strong>${esc(String(detail).slice(httpIndex))}</strong>`
    : esc(detail);
  const canOpenResult=(job.type==="llm"&&Number(job.pending_result_count||0)>0)||(["rag","llm_tool"].includes(job.type)&&job.status==="completed")||(job.type==="pdf_corpus"&&["completed","blocked"].includes(job.status));
  const resultActionLabel=job.type==="pdf_corpus"
    ?tr("pdf_corpus.open_build","Open corpus build")
    :job.type==="llm_tool"&&(job.tool==="rag_grade"||job.mode==="rag_grade")
      ?tr("operations.view_grade","View grade")
      :tr("operations.open_result","Open result");
  const statusLabel=tr(`operations.status.${job.status}`,job.status);
  const provider=jobProviderSummary(job);
  const pending=Number(job.pending_result_count||0);
  const actions=[];
  if(active){
    if(job.cancel_requested||job.status==="cancelling")actions.push(`<span class="cancel-pending">${esc(tr("operations.cancelling","Cancelling…"))}</span>`);
    else actions.push(`<button type="button" class="btn tiny danger" data-toast-cancel-job="${job.id}">${esc(tr("ui.cancel","Cancel"))}</button>`);
  }else{
    if(canOpenResult)actions.push(`<button type="button" class="btn tiny primary" data-toast-open-result="${job.id}">${esc(resultActionLabel)}</button>`);
    if(job.type==="llm"&&pending>0)actions.push(`<button type="button" class="btn tiny primary" data-toast-review-results="${job.id}">${esc(trf("operations.review_available","Review {count} available",{count:pending}))}</button>`);
    actions.push(`<button type="button" class="btn tiny" data-toast-dismiss-job="${job.id}">${esc(tr("ui.dismiss","Dismiss"))}</button>`);
  }
  actions.push(`<button type="button" class="btn tiny" data-toast-open-details="${job.id}">${esc(tr("operations.open_details","Full details"))}</button>`);
  panel.innerHTML=`<div class="operation-progress-head"><div><b>${esc(jobLabel(job))}</b>${provider?`<small class="operation-progress-provider">${esc(provider)}</small>`:""}</div><span class="operation-status-badge" data-tone="${esc(tone)}"><span class="operation-status-dot" aria-hidden="true"></span>${esc(statusLabel)}</span></div><div class="operation-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="${esc(jobProgressText(job,"of"))}"><i style="width:${pct}%"></i></div><div class="operation-progress-detail">${detailHtml}</div><div class="operation-toast-actions">${actions.join("")}${active?'<div class="spinner small-spinner"></div>':""}</div>`;
  panel.querySelector("[data-toast-cancel-job]")?.addEventListener("click",()=>cancelBackgroundJob(job.id));
  panel.querySelector("[data-toast-review-results]")?.addEventListener("click",()=>openJobResults(job.id));
  panel.querySelectorAll("[data-toast-open-result]").forEach(button=>button.addEventListener("click",()=>openJobResults(job.id)));
  panel.querySelector("[data-toast-open-details]")?.addEventListener("click",()=>openJobDetails(job.id));
  panel.querySelector("[data-toast-dismiss-job]")?.addEventListener("click",()=>removeFinishedJob(job.id));
  updateOperationStackCount();
}
function jobProgressText(job,style){
  const total=Number(job.total||0),done=Number(job.completed||0),pct=Math.round(total?done/total*100:0);
  // A PDF corpus build reports a synthetic count (source blocks x weighted
  // stage progress), not a real tally, so show only the honest percentage.
  if(job.type==="pdf_corpus"){
    if(job.status==="completed")return tr("operations.progress_build_complete","Build complete · ready for review");
    return trf("operations.progress_overall","{percent}% overall",{percent:pct});
  }
  return style==="of"?trf("operations.progress_of","{done} of {total} ({percent}%)",{done:done.toLocaleString(),total:total.toLocaleString(),percent:pct}):`${done}/${total} (${pct}%)`;
}
function maybeDesktopNotify(job){
  if(!state.appConfig.desktop_notifications)return;
  if(typeof Notification==="undefined"||Notification.permission!=="granted")return;
  try{
    const notification=new Notification(`${jobLabel(job)} ${job.status}`,{
      body:job.type==="rag"
        ? `${job.prompt||"RAG pipeline"} · ${job.stage_detail||job.status}`
        : job.type==="llm"
          ? `${job.completed}/${job.total} records processed · ${job.pending_result_count||0} pending results`
          : job.type==="llm_tool"
            ? `${job.label||"LLM operation"} · ${job.status}`
            : `${job.label||job.store_name||"Chroma sync"} · ${job.completed}/${job.total} records committed`,
      tag:`derridai-job-${job.id}`,
    });
    notification.onclick=()=>{
      window.focus();
      navigateTo("home");
      notification.close();
    };
  }catch(error){console.warn("Desktop notification failed",error)}
}
function syncJobProgressToasts(previous=new Map()){
  for(const job of state.jobs){
    if(isActiveJobStatus(job.status)){
      if(previous.size&&!previous.has(job.id)){
        announceOperationDock(trf("operations.live_started","{label} started",{label:jobLabel(job)}));
      }
      ensureJobProgressCard(job);
      continue;
    }
    const transitioned=previous.get(job.id)&&previous.get(job.id)!==job.status&&["completed","cancelled","failed"].includes(job.status);
    const panel=document.querySelector(`[data-job-operation="${CSS.escape(job.id)}"]`);
    if(panel||transitioned)ensureJobProgressCard(job);
    if(transitioned&&!jobCompletionNotified[job.id]){
      jobCompletionNotified[job.id]=true;
      if(job.status==="completed"&&job.type==="llm_tool"&&(job.tool||job.mode)==="language_dictionary"){
        window.dispatchEvent(new CustomEvent("derridai:languages-changed",{detail:{source:"translation-job",jobId:job.id}}));
      }
      {
        const providerSummary=jobProviderSummary(job);
        const unit=job.type==="rag"?" stages":job.type==="llm_tool"&&(job.tool||job.mode)==="work_metadata"?" works":" records";
        toast(`${jobLabel(job)}${providerSummary?` · ${providerSummary}`:""} ${job.status}: ${job.completed}/${job.total}${unit}`);
      }
      const liveKey=job.status==="failed"?"operations.live_failed":job.status==="cancelled"?"operations.live_cancelled":"operations.live_completed";
      const liveFallback=job.status==="failed"?"{label} failed":job.status==="cancelled"?"{label} cancelled":"{label} completed";
      announceOperationDock(trf(liveKey,liveFallback,{label:jobLabel(job)}));
      maybeDesktopNotify(job);
    }
  }
  const liveIds=state.jobs.map(job=>job.id);
  const visibleIds=[...document.querySelectorAll("[data-job-operation]")].map(panel=>panel.dataset.jobOperation);
  for(const id of jobIdsToPruneFromDock(visibleIds,liveIds)){
    document.querySelector(`[data-job-operation="${CSS.escape(id)}"]`)?.remove();
  }
  updateOperationStackCount();
}
function startJobPolling(){
  if(state.jobsPollTimer)return;
  // Never create an idle polling loop. A one-time bootstrap refresh discovers
  // restored server jobs; thereafter only known active jobs schedule polling.
  if(!state.jobs.some(job=>["queued","running","cancelling"].includes(job.status)))return;
  const poll=async()=>{
    state.jobsPollTimer=null;
    if(!state.jobs.some(job=>["queued","running","cancelling"].includes(job.status)))return;
    await refreshJobs({rerender:state.view==="home"});
    const active=state.jobs.some(job=>["queued","running","cancelling"].includes(job.status));
    if(active)state.jobsPollTimer=setTimeout(poll,4000);
  };
  state.jobsPollTimer=setTimeout(poll,4000);
}
function pauseRuntime(){
  if(state.jobsPollTimer){clearTimeout(state.jobsPollTimer);state.jobsPollTimer=null}
}

async function warmupProviderProfile(profileId=null){
  const profile=providerProfile(profileId||state.appConfig.default_provider_profile);
  if(!profile)return;
  const current=state.providerWarmups?.[profile.id]||{};
  if(current.status==="running")return;
  const cfg=providerRequestConfig(profile,{textReview:false});
  const started=performance.now();
  const startedAt=new Date().toISOString();
  const running={
    status:"running",message:`Warming ${cfg.model}…`,profile_id:profile.id,
    provider:profile.type,model:cfg.model,base_url:cfg.base_url,
    started_at:startedAt,completed_at:null,elapsed_seconds:null,error:null,
  };
  state.providerWarmups[profile.id]=running;
  if(profile.id===state.appConfig.default_provider_profile)state.warmup=running;
  if(state.view==="home")renderDashboard(document.querySelector("#main"));
  try{
    const result=await api("/api/llm/warmup",{method:"POST",body:JSON.stringify({
      provider:profile.type,model:cfg.model,base_url:cfg.base_url,api_key:cfg.api_key,
      // Load with the context real calls use, so the model is not loaded twice.
      num_ctx:Number(cfg.ollama?.num_ctx)>0?Number(cfg.ollama.num_ctx):undefined,
    })});
    const ready={
      status:"ready",message:`${providerDisplayName(profile)} · ${result.model||cfg.model} warmed`,
      profile_id:profile.id,provider:profile.type,model:result.model||cfg.model,
      base_url:result.base_url||cfg.base_url,started_at:startedAt,completed_at:new Date().toISOString(),
      elapsed_seconds:(performance.now()-started)/1000,error:null,
    };
    state.providerWarmups[profile.id]=ready;
    if(profile.id===state.appConfig.default_provider_profile)state.warmup=ready;
  }catch(error){
    const failed={
      status:"failed",message:error.message,profile_id:profile.id,provider:profile.type,model:cfg.model,
      base_url:cfg.base_url,started_at:startedAt,completed_at:new Date().toISOString(),
      elapsed_seconds:(performance.now()-started)/1000,error:error.message,
    };
    state.providerWarmups[profile.id]=failed;
    if(profile.id===state.appConfig.default_provider_profile)state.warmup=failed;
  }
  if(state.view==="home")renderDashboard(document.querySelector("#main"));
}

async function warmupConfiguredLlm(){
  return warmupProviderProfile(state.appConfig.default_provider_profile);
}
async function submitBackgroundLlmJob(items,config,fields,instructions,mode){
  const payload={
    items:items.map(item=>({
      key:item.key||reviewKey(item.file,item.index),
      record:touchupRecordPayload(item.file.records[item.index],fields),
      fingerprint:recordFingerprint(item.file.records[item.index]),
    })),
    fields:[...fields],
    instructions:instructions||"",
    model:config.model,
    provider:config.provider,
    base_url:config.base_url,
    api_key:config.api_key,
    provider_profile_id:config.provider_profile_id,
    max_concurrent_requests:config.max_concurrent_requests,
    ollama:config.ollama,
    mode:mode==="auto"?"auto":"review",
  };
  const job=await api("/api/jobs/llm",{
    method:"POST",
    body:JSON.stringify(payload),
  });
  state.jobs=[job,...state.jobs.filter(existing=>existing.id!==job.id)];
  syncJobProgressToasts();
  startJobPolling();
  toast(`${mode==="auto"?"Auto-improve":"LLM review"} started in background · ${items.length} records`);
  return job;
}
function topFieldValues(field,limit=5){
  return memoCorpus(`top:${field}:${limit}`,()=>{
    const counts=new Map();
    for(const {record} of allRows()){
      for(const value of flattenValueList(record[field])){
        const key=value.trim();
        if(!key)continue;
        counts.set(key,(counts.get(key)||0)+1);
      }
    }
    return [...counts.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,limit);
  });
}
function averageRecordLengthForTopWorks(limit=5){
  return memoCorpus(`avg-record-length-by-work:${limit}`,()=>{
    const groups=new Map();
    for(const {record} of allRows()){
      const work=String(record.work||"(Untitled work)").trim()||"(Untitled work)";
      const stats=groups.get(work)||{count:0,total:0};
      stats.count++;
      stats.total+=String(record.text||"").length;
      groups.set(work,stats);
    }
    return [...groups.entries()]
      .sort((a,b)=>b[1].count-a[1].count||a[0].localeCompare(b[0]))
      .slice(0,limit)
      .map(([work,stats])=>({key:work,value:Math.round(stats.total/Math.max(1,stats.count)),count:stats.count}));
  });
}
function recentAuditChanges(limit=10){
  return memoCorpus(`recent-audit:${limit}`,()=>{
  const changes=[];
  for(const {file,record,index} of allRows()){
    for(const update of Array.isArray(record.updates)?record.updates:[]){
      changes.push({file,record,index,update});
    }
  }
  return changes.sort((a,b)=>new Date(b.update.timestamp||0)-new Date(a.update.timestamp||0)).slice(0,limit);
  });
}

function serverAnnotationItems(){
  return (state.serverAnnotations||[]).map(annotation=>({
    file:null,
    record:{record_id:annotation.record_id,work:annotation.work||"",page_start:annotation.page_start,page_end:annotation.page_end,_chroma_id:annotation.record_id},
    index:null,
    annotation,
    annotationIndex:null,
    work:String(annotation.work||"(Untitled work)"),
    server:true,
    store:annotation.store||"",
  }));
}
async function refreshServerAnnotations(force=false){
  if(isResearcher()&&!hasCapability("annotations.read")){state.serverAnnotations=[];state.serverAnnotationsStore="";return []}
  const storeName=isResearcher()?String(state.activeStore||""):"";
  if(!force&&Date.now()-Number(state.annotationsFetchedAt||0)<15000&&(!isResearcher()||state.serverAnnotationsStore===storeName))return state.serverAnnotations||[];
  try{
    const suffix=storeName?`?store=${encodeURIComponent(storeName)}`:"";
    const data=await api(`/api/annotations${suffix}`);
    state.serverAnnotations=data.annotations||[];
    state.serverAnnotationsStore=storeName;
    state.annotationsFetchedAt=Date.now();
  }catch(error){console.warn("Could not load shared annotations",error)}
  return state.serverAnnotations||[];
}
function allAnnotations(){
  const local=isResearcher()?[]:memoCorpus("annotations-all",()=>{
    const items=[];
    for(const {file,record,index} of allRows()){
      const annotations=Array.isArray(record.annotations)?record.annotations:[];
      annotations.forEach((annotation,annotationIndex)=>items.push({file,record,index,annotation,annotationIndex,work:String(record.work||"(Untitled work)"),server:false}));
    }
    return items;
  });
  // Administrator annotations are mirrored to the shared annotation store so
  // researcher accounts can see them. Avoid showing the local + shared copy
  // twice in an administrator workspace.
  const mirroredIds=new Set(local.map(item=>String(item.annotation?.shared_annotation_id||"")).filter(Boolean));
  const shared=serverAnnotationItems().filter(item=>!mirroredIds.has(String(item.annotation?.id||"")));
  return [...local,...shared].sort((a,b)=>new Date(b.annotation.created_at||0)-new Date(a.annotation.created_at||0));
}
function recentAnnotations(limit=10){return allAnnotations().slice(0,limit)}
function annotationTimeline(days=14){
  const keys=dateKeys(days),counts=new Map(keys.map(key=>[key,0]));
  for(const item of allAnnotations()){
    const key=String(item.annotation?.created_at||"").slice(0,10);
    if(counts.has(key))counts.set(key,(counts.get(key)||0)+1);
  }
  return keys.map(key=>({key,value:counts.get(key)||0}));
}
function annotationMatches(item,query){
  const q=String(query||"").trim().toLocaleLowerCase();if(!q)return true;
  const annotation=item.annotation||{};
  return [item.work,item.record?.record_id,item.file?.name,item.store,annotation.note,annotation.quote,annotation.author,annotation.initiated_by,...(annotation.tags||[])].some(value=>String(value||"").toLocaleLowerCase().includes(q));
}
function annotationItemHtml(item){
  const annotation=item.annotation||{};
  const tags=(annotation.tags||[]).map(tag=>`<span class="chip">${esc(tag)}</span>`).join("");
  const open=item.server?`<button class="annotation-open-record" data-server-annotation-record="${esc(annotation.record_id||"")}" data-server-annotation-store="${esc(annotation.store||"")}" title="${esc(tr("annotations.open_record","Open record"))}">${icon("record")}</button>`:`<button class="annotation-open-record" data-annotation-file="${esc(item.file.id)}" data-annotation-index="${item.index}" title="${esc(tr("annotations.open_record","Open record"))}">${icon("record")}</button>`;
  const source=item.server?(annotation.store||tr("annotations.shared","Shared annotation")):(item.file?.name||"");
  const canDeleteServer=item.server&&(state.userContext?.role==="admin"||Number(annotation.user_id||0)===Number(state.userContext?.id||-1));
  const canDeleteLocal=!item.server&&canUse("editLocalRecords");
  const removeButton=canDeleteServer
    ?`<button class="btn tiny danger" data-delete-server-annotation="${esc(annotation.id)}">${esc(tr("ui.remove","Remove"))}</button>`
    :canDeleteLocal
      ?`<button class="btn tiny danger" data-delete-local-annotation="${esc(reviewKey(item.file,item.index))}" data-local-annotation-index="${item.annotationIndex}">${esc(tr("ui.remove","Remove"))}</button>`
      :"";
  return `<article class="annotation-feed-item">${open}<div class="annotation-feed-copy"><div class="annotation-feed-meta"><b>${esc(item.record?.record_id||tr("nav.record","Record"))}</b><span>${esc(annotation.field?label(annotation.field):tr("annotations.record_note","Record note"))}</span><time>${esc(formatTimestamp(annotation.created_at))}</time></div>${annotation.quote?`<blockquote>${esc(annotation.quote)}</blockquote>`:""}${annotation.note?`<p>${esc(annotation.note)}</p>`:""}${tags?`<div class="annotation-tags">${tags}</div>`:""}<small>${esc(annotation.initiated_by||annotation.author||tr("annotations.unknown_author","Unknown author"))} · ${esc(source)}</small></div>${removeButton}</article>`;
}
async function renderAnnotations(main){
  // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  if(isResearcher()&&!state.activeStore){try{await refreshStores();state.activeStore=recordStores()[0]?.name||""}catch{}}
  await refreshServerAnnotations(isResearcher()&&state.serverAnnotationsStore!==String(state.activeStore||""));
  const all=allAnnotations();
  const filtered=all.filter(item=>annotationMatches(item,state.annotationSearch));
  const byWork=new Map();for(const item of filtered){if(!byWork.has(item.work))byWork.set(item.work,[]);byWork.get(item.work).push(item)}
  const groups=[...byWork.entries()].sort((a,b)=>a[0].localeCompare(b[0]));
  main.innerHTML=`<section class="page-heading legacy-page-heading"><div><p>${esc(tr("section.corpus","Corpus"))}</p><h1>${esc(tr("nav.annotations","Annotations"))}</h1><span>${esc(tr("annotations.page_help","Review annotations across the corpus. The default view groups discussion by work; switch to Recent for a chronological stream."))}</span></div></section><section class="card annotations-index-card"><div class="annotations-toolbar"><div class="search"><input id="annotationSearch" value="${esc(state.annotationSearch)}" placeholder="${esc(tr("annotations.search_placeholder","Search annotations, tags, quotes, records, or works…"))}"></div><div class="view-tabs"><button class="view-tab ${state.annotationView==="works"?"active":""}" data-annotation-view="works">${esc(tr("annotations.by_work","By work"))}</button><button class="view-tab ${state.annotationView==="recent"?"active":""}" data-annotation-view="recent">${esc(tr("annotations.recent","Recent"))}</button></div><span class="note">${filtered.length.toLocaleString()} ${esc(tr("annotations.annotation_count","annotations"))} · ${groups.length.toLocaleString()} ${esc(tr("dynamic.works","works"))}</span></div></section>${state.annotationView==="recent"?`<section class="card annotations-recent-card"><div class="cardhead"><div><b>${esc(tr("annotations.recent_annotations","Recent annotations"))}</b><div class="note">${esc(tr("annotations.recent_help","Newest annotations across all loaded works."))}</div></div></div><div class="annotation-feed">${filtered.map(annotationItemHtml).join("")||`<div class="llm-empty">${esc(tr("annotations.empty","No annotations match the current search."))}</div>`}</div></section>`:`<section class="annotation-work-groups">${groups.map(([work,items])=>`<details class="card annotation-work-group" open><summary><span><b>${esc(work)}</b><small>${items.length.toLocaleString()} ${esc(tr("annotations.annotation_count","annotations"))} · ${new Set(items.map(item=>item.record.record_id||item.index)).size.toLocaleString()} ${esc(tr("dynamic.records","records"))}</small></span><button type="button" class="btn tiny" data-annotation-work="${esc(work)}">${esc(tr("works.open_overview","Open work overview"))}</button></summary><div class="annotation-feed">${items.map(annotationItemHtml).join("")}</div></details>`).join("")||`<div class="card llm-empty">${esc(tr("annotations.empty","No annotations match the current search."))}</div>`}</section>`}`;
  const input=main.querySelector("#annotationSearch");let timer=null;input?.addEventListener("input",event=>{const value=event.target.value,pos=event.target.selectionStart;state.annotationSearch=value;persistPrefs();syncUrl({replace:true});clearTimeout(timer);timer=setTimeout(()=>{if(state.view!=="annotations")return;renderAnnotations(main);requestAnimationFrame(()=>{const next=main.querySelector("#annotationSearch");if(next){next.focus();next.setSelectionRange(pos,pos)}})},150)});
  main.querySelectorAll("[data-annotation-view]").forEach(button=>button.onclick=()=>{state.annotationView=button.dataset.annotationView;persistPrefs();syncUrl({replace:true});renderAnnotations(main)});
  main.querySelectorAll("[data-annotation-file]").forEach(button=>button.onclick=()=>navigateTo("record",{fileId:button.dataset.annotationFile,index:Number(button.dataset.annotationIndex)}));
  // eslint-disable-next-line no-undef -- SA-11: existing missing runtime handler or stale variable; repair with workflow regression coverage.
  main.querySelectorAll("[data-server-annotation-record]").forEach(button=>button.onclick=()=>openSharedAnnotationRecord(button.dataset.serverAnnotationStore,button.dataset.serverAnnotationRecord));
  main.querySelectorAll("[data-delete-server-annotation]").forEach(button=>button.onclick=async()=>{if(!await openMessageModal({title:tr("annotations.remove_title","Remove annotation?"),message:tr("annotations.remove_help","This removes the shared annotation. This action cannot be undone."),tone:"danger",confirmLabel:tr("ui.remove","Remove"),cancelLabel:tr("ui.cancel","Cancel")}))return;try{await api(`/api/annotations/${encodeURIComponent(button.dataset.deleteServerAnnotation)}`,{method:"DELETE"});state.annotationsFetchedAt=0;await refreshServerAnnotations(true);toast(tr("annotations.removed","Annotation removed."));renderAnnotations(main)}catch(error){toast(error.message,{tone:"danger"})}});
  main.querySelectorAll("[data-delete-local-annotation]").forEach(button=>button.onclick=async()=>{
    if(!canUse("editLocalRecords"))return;
    const item=reviewItemFromKey(button.dataset.deleteLocalAnnotation||"");
    const annotationIndex=Number(button.dataset.localAnnotationIndex);
    const annotations=Array.isArray(item?.record?.annotations)?item.record.annotations:[];
    const annotation=Number.isInteger(annotationIndex)?annotations[annotationIndex]:null;
    if(!item||!annotation)return;
    if(!await openMessageModal({title:tr("annotations.remove_title","Remove annotation?"),message:tr("annotations.remove_local_help","This removes the annotation from the local JSONL record and records the change in its audit history."),tone:"danger",confirmLabel:tr("ui.remove","Remove"),cancelLabel:tr("ui.cancel","Cancel")}))return;
    try{
      const sharedId=String(annotation.shared_annotation_id||"").trim();
      if(sharedId){
        try{await api(`/api/annotations/${encodeURIComponent(sharedId)}`,{method:"DELETE"})}
        catch(error){if(Number(error?.status||0)!==404)throw error}
      }
      const next=annotations.filter((_,index)=>index!==annotationIndex);
      applyRecordChanges(item.file,item.index,{annotations:next},{source:"annotation-delete"});
      await persistFileNow(item.file);
      state.annotationsFetchedAt=0;
      await refreshServerAnnotations(true);
      toast(tr("annotations.removed","Annotation removed."));
      renderAnnotations(main);
    }catch(error){toast(error.message,{tone:"danger"})}
  });
  main.querySelectorAll("[data-annotation-work]").forEach(button=>button.addEventListener("click",event=>{event.preventDefault();event.stopPropagation();state.workOverview=button.dataset.annotationWork||"";persistPrefs();navigateTo("works")}));
  decorateDisabledControls(main);
}

function timelineCounts(kind,days=30){
  const dayKey=new Date().toISOString().slice(0,10);
  return memoCorpus(`timeline:${kind}:${days}:${dayKey}`,()=>{
  const today=new Date();
  const keys=[];
  const counts=new Map();
  for(let offset=days-1;offset>=0;offset--){
    const d=new Date(today);
    d.setHours(0,0,0,0);
    d.setDate(d.getDate()-offset);
    const key=d.toISOString().slice(0,10);
    keys.push(key);counts.set(key,0);
  }
  if(kind==="records"){
    for(const file of state.files){
      const key=String(file.imported_at||"").slice(0,10);
      if(counts.has(key))counts.set(key,(counts.get(key)||0)+file.records.length);
    }
  }else{
    const reviewSeen=new Set();
    for(const {record} of allRows()){
      for(const update of Array.isArray(record.updates)?record.updates:[]){
        const key=String(update.timestamp||"").slice(0,10);
        if(!counts.has(key))continue;
        if(kind==="reviews"){
          const reviewed=update.field_name==="needs_review"&&update.new_value===false;
          const llmSource=String(update.source||"").startsWith("llm");
          if(!(reviewed||llmSource))continue;
          const reviewKey=`${key}::${record.record_id||""}::${update.batch_id||update.timestamp||""}`;
          if(reviewSeen.has(reviewKey))continue;
          reviewSeen.add(reviewKey);
        }
        counts.set(key,(counts.get(key)||0)+1);
      }
    }
  }
  return keys.map(key=>({key,value:counts.get(key)||0}));
  });
}
function dateKeys(days=30){
  const today=new Date();
  const keys=[];
  for(let offset=days-1;offset>=0;offset--){
    const d=new Date(today);
    d.setHours(0,0,0,0);
    d.setDate(d.getDate()-offset);
    keys.push(d.toISOString().slice(0,10));
  }
  return keys;
}
function ragRunTimeline(days=30){
  const keys=dateKeys(days);
  const rows=new Map(keys.map(key=>[key,{key,ollama:0,freellm:0}]));
  const seen=new Set();
  const runs=[];
  for(const item of state.ragConfig.run_history||[]){
    if(item?.job_id)seen.add(item.job_id);
    runs.push(item);
  }
  for(const job of state.jobs){
    if(job.type!=="rag"||seen.has(job.id))continue;
    runs.push({
      job_id:job.id,
      timestamp:job.created_at,
      provider:job.provider,
      model:job.model,
    });
  }
  for(const run of runs){
    const key=String(run?.timestamp||"").slice(0,10);
    if(!rows.has(key))continue;
    const row=rows.get(key);
    if(run.provider==="openai")row.freellm++;
    else row.ollama++;
  }
  return [...rows.values()];
}
function topNeedsReviewWorkSeries(days=30,limit=5){
  const dayKey=new Date().toISOString().slice(0,10);
  return memoCorpus(`review-work-series:${days}:${limit}:${dayKey}`,()=>{
  const counts=new Map();
  for(const {record} of allRows()){
    if(!record.needs_review)continue;
    const work=String(record.work||"(Untitled work)");
    counts.set(work,(counts.get(work)||0)+1);
  }
  const top=[...counts.entries()]
    .sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]))
    .slice(0,limit)
    .map(([work])=>work);
  if(!top.length)return {rows:[],series:[]};

  const recordsByWork=new Map(top.map(work=>[work,[]]));
  for(const {record} of allRows()){
    const work=String(record.work||"(Untitled work)");
    if(!recordsByWork.has(work))continue;
    const events=(Array.isArray(record.updates)?record.updates:[])
      .filter(update=>update.field_name==="needs_review"&&update.timestamp)
      .map(update=>({
        time:new Date(update.timestamp).getTime(),
        old:Boolean(update.old_value),
      }))
      .filter(event=>Number.isFinite(event.time))
      .sort((a,b)=>b.time-a.time);
    recordsByWork.get(work).push({
      current:Boolean(record.needs_review),
      events,
    });
  }

  const keys=dateKeys(days);
  const series=top.map((work,index)=>({
    key:`work_${index}`,
    label:work,
    short_label:`${index+1}. ${work.length>18?`${work.slice(0,16)}…`:work}`,
  }));
  const rows=keys.map(key=>{
    const end=new Date(`${key}T23:59:59.999Z`).getTime();
    const row={key};
    top.forEach((work,index)=>{
      let count=0;
      for(const history of recordsByWork.get(work)||[]){
        let value=history.current;
        for(const event of history.events){
          if(event.time<=end)break;
          value=event.old;
        }
        if(value)count++;
      }
      row[`work_${index}`]=count;
    });
    return row;
  });
  return {rows,series};
  });
}
function multiLineChart(rows,title,seriesDefs,{note=""}={}){
  if(!rows.length||!seriesDefs.length)return `<div class="dash-chart-empty">${esc(title)} · no data yet</div>`;
  const width=540,height=185,left=46,right=14,top=18,bottom=28;
  const values=rows.flatMap(row=>seriesDefs.map(series=>Number(row[series.key])||0));
  const maxValue=Math.max(0,...values);
  const scaleMax=Math.max(1,maxValue);
  const plotWidth=width-left-right,plotHeight=height-top-bottom;
  const xFor=index=>rows.length===1?left+plotWidth/2:left+(index/(rows.length-1))*plotWidth;
  const yFor=value=>top+plotHeight-(Number(value||0)/scaleMax)*plotHeight;
  const grades=[0,.25,.5,.75,1].map(fraction=>{
    const value=Math.round(scaleMax*fraction);
    const y=top+plotHeight-fraction*plotHeight;
    return `<g class="chart-grade"><line x1="${left}" x2="${width-right}" y1="${y}" y2="${y}"/><text x="${left-7}" y="${y+3}" text-anchor="end">${value}</text></g>`;
  }).join("");
  const paths=seriesDefs.map((series,seriesIndex)=>{
    const points=rows.map((row,index)=>({
      x:xFor(index),
      y:yFor(row[series.key]),
      value:Number(row[series.key])||0,
      key:row.key,
    }));
    const d=points.map((point,index)=>`${index?"L":"M"}${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
    return `<path class="chart-line chart-series-${seriesIndex}" d="${d}"/>${points.map(point=>`<circle class="chart-dot chart-series-${seriesIndex}" data-chart-tip="${esc(`${series.label} · ${point.key}: ${point.value.toLocaleString()}`)}" cx="${point.x}" cy="${point.y}" r="3"><title>${esc(series.label)} · ${esc(point.key)}: ${point.value.toLocaleString()}</title></circle>`).join("")}`;
  }).join("");
  const mid=rows[Math.floor((rows.length-1)/2)]?.key||"";
  return `<div class="dash-chart multi-line-chart">
    <div class="dash-chart-head"><div><div class="dash-chart-title">${esc(title)}</div>${note?`<div class="dash-chart-note">${esc(note)}</div>`:""}</div><div class="chart-legend multi-chart-legend">${seriesDefs.map((series,index)=>`<span title="${esc(series.label)}"><i class="chart-series-${index}"></i>${esc(series.short_label||series.label)}</span>`).join("")}</div></div>
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(title)}">
      ${grades}
      <path class="chart-axis" d="M${left},${top+plotHeight} H${width-right}"/>
      ${paths}
    </svg>
    <div class="dash-chart-foot"><span>${esc(rows[0]?.key||"")}</span><span>${esc(mid)}</span><span>${esc(rows[rows.length-1]?.key||"")}</span></div>
  </div>`;
}

function workRecordShares(limit=9){
  return memoCorpus(`work-shares:${limit}`,()=>{
  const counts=new Map();
  for(const {record} of allRows()){
    const work=String(record.work||"(Untitled work)");
    counts.set(work,(counts.get(work)||0)+1);
  }
  const sorted=[...counts.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
  const top=sorted.slice(0,limit);
  const other=sorted.slice(limit).reduce((sum,[,count])=>sum+count,0);
  if(other)top.push(["Other works",other]);
  return top;
  });
}
function pieChart(title,entries){
  const total=entries.reduce((sum,[,value])=>sum+Number(value||0),0);
  if(!total)return `<div class="dash-chart-empty">${esc(title)} · no records loaded</div>`;
  const cx=90,cy=90,r=64,circ=2*Math.PI*r;
  let offset=0;
  const slices=entries.map(([name,value],index)=>{
    const fraction=Number(value||0)/total;
    const dash=fraction*circ;
    const gap=Math.max(0,circ-dash);
    const current=offset;
    offset+=dash;
    return `<circle class="pie-slice pie-series-${index%10}" data-chart-tip="${esc(`${name} · ${Number(value).toLocaleString()} records · ${(fraction*100).toFixed(1)}%`)}" cx="${cx}" cy="${cy}" r="${r}" pathLength="${circ}" stroke-dasharray="${dash} ${gap}" stroke-dashoffset="${-current}" transform="rotate(-90 ${cx} ${cy})"><title>${esc(name)}: ${Number(value).toLocaleString()} (${(fraction*100).toFixed(1)}%)</title></circle>`;
  }).join("");
  return `<div class="dash-chart pie-chart"><div class="dash-chart-head"><div class="dash-chart-title">${esc(title)}</div></div><div class="pie-layout"><svg viewBox="0 0 180 180" role="img" aria-label="${esc(title)}"><circle class="pie-track" cx="${cx}" cy="${cy}" r="${r}"/>${slices}<text class="pie-total" x="${cx}" y="${cy-2}" text-anchor="middle">${total.toLocaleString()}</text><text class="pie-total-label" x="${cx}" y="${cy+15}" text-anchor="middle">records</text></svg><div class="pie-legend">${entries.map(([name,value],index)=>`<div title="${esc(name)}"><i class="pie-series-${index%10}"></i><span>${esc(name)}</span><b>${(Number(value)/total*100).toFixed(1)}%</b><small>${Number(value).toLocaleString()}</small></div>`).join("")}</div></div></div>`;
}
function recentRagRuns(limit=5){
  const jobMap=new Map(state.jobs.filter(job=>job.type==="rag").map(job=>[job.id,job]));
  const merged=[];
  const seen=new Set();
  for(const run of state.ragConfig.run_history||[]){
    const job=jobMap.get(run.job_id);
    merged.push({...run,...(job||{})});
    seen.add(run.job_id);
  }
  for(const job of jobMap.values()){
    if(!seen.has(job.id))merged.push(job);
  }
  return merged.sort((a,b)=>new Date(b.created_at||b.timestamp||0)-new Date(a.created_at||a.timestamp||0)).slice(0,limit);
}
function recentRagRunsHtml(){
  const runs=recentRagRuns(5);
  return `<section class="card recent-rag-card"><div class="cardhead"><div><b>Recent RAG pipelines</b><div class="note">Five most recent runs</div></div><button class="btn small" id="dashboardRag">${icon("spark")}Research</button></div>
    <div class="recent-rag-table-wrap"><table class="recent-rag-table"><thead><tr><th>Started</th><th>Question</th><th>Provider / model</th><th>Collection</th><th>Status</th><th></th></tr></thead><tbody>${runs.map(run=>`<tr><td>${esc(formatTimestamp(run.created_at||run.timestamp))}</td><td class="recent-rag-question" title="${esc(run.prompt||"RAG query")}">${esc(String(run.prompt||"RAG query").replace(/\s+/g," ").slice(0,130))}${String(run.prompt||"").length>130?"…":""}</td><td><b>${esc(run.provider==="openai"?"FreeLLM":"Ollama")}</b><span>${esc(run.model||"model")}</span></td><td>${esc(run.source_collection||"—")}</td><td>${run.status?`<span class="job-status ${esc(run.status)}">${esc(run.status)}</span>`:"—"}</td><td>${run.id&&run.status==="completed"?`<button class="btn tiny" data-recent-rag-result="${esc(run.id)}">Open</button>`:""}</td></tr>`).join("")||'<tr><td colspan="6" class="note">No RAG pipeline runs recorded yet.</td></tr>'}</tbody></table></div>
  </section>`;
}

function publicationYearSeries(){
  return memoCorpus("publication-year-series",()=>{
  const counts=new Map();
  for(const {record} of allRows()){
    const year=Number(record.year);
    if(!Number.isFinite(year)||year<1000||year>3000)continue;
    counts.set(year,(counts.get(year)||0)+1);
  }
  return [...counts.entries()].sort((a,b)=>a[0]-b[0]).map(([key,value])=>({key:String(key),value}));
  });
}
function needsReviewTimeline(days=30){
  const dayKey=new Date().toISOString().slice(0,10);
  return memoCorpus(`needs-review-timeline:${days}:${dayKey}`,()=>{
  const today=new Date();
  today.setHours(23,59,59,999);
  const dates=[];
  for(let offset=days-1;offset>=0;offset--){
    const d=new Date(today);
    d.setDate(d.getDate()-offset);
    dates.push(d);
  }

  const recordHistories=allRows().map(({record})=>{
    const events=(Array.isArray(record.updates)?record.updates:[])
      .filter(update=>update.field_name==="needs_review"&&update.timestamp)
      .map(update=>({
        time:new Date(update.timestamp).getTime(),
        old:Boolean(update.old_value),
        next:Boolean(update.new_value),
      }))
      .filter(event=>Number.isFinite(event.time))
      .sort((a,b)=>b.time-a.time);
    return {current:Boolean(record.needs_review),events};
  });

  return dates.map(date=>{
    const end=date.getTime();
    let count=0;
    for(const history of recordHistories){
      let value=history.current;
      for(const event of history.events){
        if(event.time<=end)break;
        value=event.old;
      }
      if(value)count++;
    }
    return {key:date.toISOString().slice(0,10),value:count};
  });
  });
}
function lineChart(series,title,legendLabel=title){
  if(!series.length)return `<div class="dash-chart-empty">${esc(title)} · no data yet</div>`;
  const width=540,height=185,left=46,right=14,top=18,bottom=28;
  const maxValue=Math.max(0,...series.map(item=>Number(item.value)||0));
  const scaleMax=Math.max(1,maxValue);
  const plotWidth=width-left-right,plotHeight=height-top-bottom;
  const points=series.map((item,index)=>{
    const x=series.length===1?left+plotWidth/2:left+(index/(series.length-1))*plotWidth;
    const y=top+plotHeight-(Number(item.value||0)/scaleMax)*plotHeight;
    return {x,y,...item};
  });
  const path=points.map((point,index)=>`${index?"L":"M"}${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
  const grades=[0,.25,.5,.75,1].map(fraction=>{
    const value=Math.round(scaleMax*fraction);
    const y=top+plotHeight-fraction*plotHeight;
    return `<g class="chart-grade"><line x1="${left}" x2="${width-right}" y1="${y}" y2="${y}"/><text x="${left-7}" y="${y+3}" text-anchor="end">${value}</text></g>`;
  }).join("");
  const mid=series[Math.floor((series.length-1)/2)]?.key||"";
  return `<div class="dash-chart">
    <div class="dash-chart-head"><div class="dash-chart-title">${esc(title)}</div><div class="chart-legend"><i></i><span>${esc(legendLabel)}</span></div></div>
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(title)}">
      ${grades}
      <path class="chart-axis" d="M${left},${top+plotHeight} H${width-right}"/>
      <path class="chart-line" d="${path}"/>
      ${points.map(point=>`<circle class="chart-dot" data-chart-tip="${esc(`${legendLabel} · ${point.key}: ${Number(point.value||0).toLocaleString()}`)}" cx="${point.x}" cy="${point.y}" r="3"><title>${esc(point.key)}: ${Number(point.value||0).toLocaleString()}</title></circle>`).join("")}
    </svg>
    <div class="dash-chart-foot"><span>${esc(series[0]?.key||"")}</span><span>${esc(mid)}</span><span>${esc(series[series.length-1]?.key||"")}</span></div>
  </div>`;
}

function pieShareSeries(items,valueField,limit=7){
  const sorted=[...items].map(item=>({key:item.work,value:Number(item[valueField]||0)})).filter(item=>item.value>0).sort((a,b)=>b.value-a.value);
  const top=sorted.slice(0,limit),other=sorted.slice(limit).reduce((sum,item)=>sum+item.value,0);
  if(other)top.push({key:tr("dashboard.other_works","Other works"),value:other});
  return top;
}
function dashboardPieChart(series,title,{valueLabel="records",searchField=""}={}){
  const total=series.reduce((sum,item)=>sum+Number(item.value||0),0);
  if(!total)return `<div class="dash-chart-empty">${esc(title)} · no data yet</div>`;
  let cursor=0;const colors=["var(--chart-1)","var(--chart-2)","var(--chart-3)","var(--chart-4)","var(--chart-5)","var(--chart-6)","var(--chart-7)","var(--chart-8)"];
  const stops=series.map((item,index)=>{const start=cursor;cursor+=Number(item.value||0)/total*100;return `${colors[index%colors.length]} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`}).join(",");
  return `<div class="dashboard-pie-layout"><div class="dashboard-pie" style="background:conic-gradient(${stops})" role="img" aria-label="${esc(title)}"></div><div class="dashboard-pie-legend">${series.map((item,index)=>{const pct=Number(item.value||0)/total*100;const other=Boolean(item.other)||item.key===tr("dashboard.other_works","Other works");const action=searchField?`data-dashboard-search-field="${esc(searchField)}" data-dashboard-search-value="${esc(item.key)}"`:`data-dashboard-work="${esc(item.key)}"`;return `<button type="button" ${other?"disabled":action}><i style="background:${colors[index%colors.length]}"></i><span title="${esc(item.key)}">${esc(item.key)}</span><b>${pct.toFixed(pct>=10?0:1)}%</b><small>${Number(item.value||0).toLocaleString()} ${esc(valueLabel)}</small></button>`}).join("")}</div></div>`;
}
function flattenedMetricValues(value){
  if(Array.isArray(value))return value.flatMap(flattenedMetricValues);
  if(value===undefined||value===null||value==="")return [];
  if(typeof value==="object")return Object.values(value).flatMap(flattenedMetricValues);
  return [String(value).trim()].filter(Boolean);
}
function topRecordFieldValues(rows,field,limit=5){
  const counts=new Map();
  for(const row of rows||[])for(const value of flattenedMetricValues(row.record?.[field]))counts.set(value,(counts.get(value)||0)+1);
  return [...counts.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,limit).map(([key,value])=>({key,value}));
}
function topRecordFieldShare(rows,field,limit=5){
  const counts=new Map();
  for(const row of rows||[])for(const value of flattenedMetricValues(row.record?.[field]))counts.set(value,(counts.get(value)||0)+1);
  const sorted=[...counts.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
  const top=sorted.slice(0,limit).map(([key,value])=>({key,value}));
  const other=sorted.slice(limit).reduce((sum,[,value])=>sum+Number(value||0),0);
  if(other)top.push({key:tr("works.other_values","Other"),value:other,other:true});
  return top;
}
function workInsightMetrics(rows,work){
  return [
    {id:"persons",field:"persons",title:tr("dashboard.top_persons_work","Top 5 persons mentioned in the work"),type:"bars",values:topRecordFieldValues(rows,"persons")},
    {id:"concepts",field:"concepts",title:tr("dashboard.top_concepts_work","Top 5 concepts mentioned in the work"),type:"bars",values:topRecordFieldValues(rows,"concepts")},
    {id:"topics",field:"topics",title:tr("dashboard.top_topics_work","Top 5 topics in the work"),type:"bars",values:topRecordFieldValues(rows,"topics")},
    {id:"targets",field:"target",title:tr("dashboard.top_discourse_targets_work","Top 5 discourse targets in the work"),type:"bars",values:topRecordFieldValues(rows,"target")},
    {id:"roles",field:"discourse_role",title:tr("dashboard.discourse_roles_share_work","Top discourse roles as percentage of recorded roles"),type:"pie",values:topRecordFieldShare(rows,"discourse_role"),valueLabel:tr("works.role_occurrences","role occurrences")},
  ].map(metric=>({...metric,work,format:value=>Number(value).toLocaleString()}));
}
function workInsightPieHtml(metric){
  const total=metric.values.reduce((sum,item)=>sum+Number(item.value||0),0);
  if(!total)return `<p class="note">${esc(tr("works.no_indexed_values","No indexed values in the loaded records."))}</p>`;
  const colors=["var(--chart-1)","var(--chart-2)","var(--chart-3)","var(--chart-4)","var(--chart-5)","var(--chart-6)"];
  let cursor=0;
  const stops=metric.values.map((item,index)=>{const start=cursor;cursor+=Number(item.value||0)/total*100;return `${colors[index%colors.length]} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`}).join(",");
  const legend=metric.values.map((item,index)=>{const pct=Number(item.value||0)/total*100;return `<li>${item.other?`<span class="work-insight-pie-label" aria-label="${esc(item.key)}"><i style="background:${colors[index%colors.length]}"></i><span>${esc(item.key)}</span></span>`:`<button type="button" data-work-insight-field="${esc(metric.field)}" data-work-insight-value="${esc(item.key)}"><i style="background:${colors[index%colors.length]}"></i><span>${esc(item.key)}</span></button>`}<b>${pct.toFixed(pct>=10?0:1)}%</b></li>`}).join("");
  return `<div class="work-insight-pie-layout"><div class="work-insight-pie" style="background:conic-gradient(${stops})" role="img" aria-label="${esc(metric.title)}"></div><ol class="work-insight-pie-legend">${legend}</ol></div>`;
}
function workInsightsPanelHtml(rows,work){
  const metrics=workInsightMetrics(rows,work);
  return `<section class="work-insights-panel" aria-label="${esc(tr("works.work_insights","Work insights"))}"><div class="work-insights-heading"><div><span class="section-label">${esc(tr("works.work_insights","Work insights"))}</span><h2>${esc(tr("works.indexed_patterns","Indexed patterns in this work"))}</h2></div><p>${esc(tr("works.work_insights_help","Counts are derived from the currently loaded records and use the corpus metadata fields directly."))}</p></div><div class="work-insights-grid">${metrics.map(metric=>`<article class="work-insight-card ${metric.type==="pie"?"work-insight-card-pie":""}"><h3>${esc(metric.title.replace(" in the work","").replace(" mentioned in the work",""))}</h3>${metric.type==="pie"?workInsightPieHtml(metric):`<ol>${metric.values.map(item=>`<li><button type="button" data-work-insight-field="${esc(metric.field)}" data-work-insight-value="${esc(item.key)}"><span>${esc(item.key)}</span><b>${Number(item.value).toLocaleString()}</b></button></li>`).join("")||`<li class="note">${esc(tr("works.no_indexed_values","No indexed values in the loaded records."))}</li>`}</ol>`}</article>`).join("")}</div></section>`;
}

function dashboardMetricBody(metric){
  if(metric.type==="pie")return dashboardPieChart(metric.values,metric.title,{valueLabel:metric.valueLabel,searchField:metric.field||""});
  if(metric.type==="line")return lineChart(metric.values,metric.title,metric.valueLabel||metric.title);
  const ranking=metric.values,maxRank=Math.max(1,...ranking.map(item=>Number(item.value)||0));
  return `<div class="dashboard-average-list">${ranking.map(item=>`<button class="dashboard-average-row" ${metric.field?`data-dashboard-search-field="${esc(metric.field)}" data-dashboard-search-value="${esc(item.key)}"`:`data-dashboard-work="${esc(item.key)}"`}><span>${esc(item.key)}</span><i><em style="width:${Math.max(4,Math.round(Number(item.value)/maxRank*100))}%"></em></i><b>${esc(metric.format(item.value))}</b></button>`).join("")||`<div class="note">${esc(metric.field?tr("works.no_indexed_values","No indexed values in the loaded records."):tr("research.no_works","No works loaded yet."))}</div>`}</div>`;
}

function barChart(series,title,{valueLabel="Average characters"}={}){
  if(!series.length)return `<div class="dash-chart-empty">${esc(title)} · no data yet</div>`;
  const max=Math.max(1,...series.map(item=>Number(item.value)||0));
  return `<section class="dash-chart dash-bar-chart"><div class="dash-chart-head"><div class="dash-chart-title">${esc(title)}</div><div class="chart-legend"><i></i><span>${esc(valueLabel)}</span></div></div><div class="dash-bars">${series.map(item=>{
    const pct=Math.max(2,Math.round((Number(item.value||0)/max)*100));
    return `<div class="dash-bar-row" data-chart-tip="${esc(`${item.key} · ${Number(item.value||0).toLocaleString()} ${valueLabel.toLowerCase()} · ${Number(item.count||0).toLocaleString()} records`)}"><div class="dash-bar-label" title="${esc(item.key)}"><b>${esc(item.key)}</b><span>${Number(item.count||0).toLocaleString()} records</span></div><div class="dash-bar-track"><i style="width:${pct}%"></i></div><strong>${Number(item.value||0).toLocaleString()}</strong></div>`;
  }).join("")}</div></section>`;
}

function statList(title,items){
  return `<section class="card dash-ranking"><div class="cardhead"><b>${esc(title)}</b></div><div>${items.map(([value,count],index)=>`<button class="rank-row" type="button" data-dashboard-search="${esc(value)}" title="Search the corpus for ${esc(value)}"><span>${index+1}</span><b>${esc(value)}</b><strong>${count.toLocaleString()}</strong></button>`).join("")||'<div class="note" style="padding:12px">No data</div>'}</div></section>`;
}
// ---- Operations panel bridge -------------------------------------------------------------
// The panel itself is a Vue component (components/OperationsPanel.vue). The runtime still owns
// job state, the dock, toasts, and the details/results dialogs, so the panel reads a plain view
// model from here and calls back into the existing functions.
const operationsListeners=new Set();
function notifyOperationsChanged(){
  for(const listener of [...operationsListeners]){
    try{listener()}catch(error){console.warn("Operations panel listener failed",error)}
  }
}
function operationIcon(job){
  if(job.type==="pdf_corpus")return "pdf";
  if(job.type==="upsert")return "database";
  if(job.type==="rag")return "spark";
  if(job.type==="llm_tool"){
    const kind=String(job.tool||job.mode||job.label||"").toLowerCase();
    if(kind.includes("policy"))return "lock";
    if(kind.includes("language"))return "language";
    if(kind.includes("pdf"))return "pdf";
    return "gear";
  }
  return "edit";
}
function operationSubtitle(job){
  if(job.status==="cancelling"||job.cancel_requested)return tr("operations.sub.cancelling","Cancellation requested · current call/batch is reaching a safe stopping point");
  if(job.type==="rag")return String(job.stage_detail||job.stage||tr("operations.sub.queued","queued"));
  if(job.type==="upsert")return `${job.store_name||tr("operations.sub.collection","collection")} · ${job.completed}/${job.total} ${tr("operations.sub.committed","committed")}${Object.keys(job.mirrored||{}).length?` · ${tr("operations.sub.mirrors_active","language mirrors active")}`:""}`;
  if(job.type==="pdf_corpus")return `${job.source_filename||tr("pdf_corpus.source_pdf","Source PDF")} · ${job.stage_detail||job.stage||job.raw_status||tr("operations.sub.queued","queued")}${job.unresolved_regions?` · ${Number(job.unresolved_regions).toLocaleString()} ${tr("pdf_corpus.unresolved_regions","unresolved segmentation region(s)")}`:""}`;
  // Provider and model appear in the facts, and the label is the row title: say only what is new.
  if(job.type==="llm_tool"){const detail=String(job.stage_detail||"");return detail&&detail!==jobLabel(job)?detail:""}
  return `${job.completed}/${job.total} ${tr("operations.sub.records","records")}${job.current_record_id?` · ${tr("operations.sub.current","current:")} ${job.current_record_id}`:""}${job.failed?` · ${job.failed} ${tr("operations.sub.failed","failed")}`:""}`;
}
function operationResultKind(job){
  const active=isActiveJobStatus(job.status);
  if(job.type==="llm"&&Number(job.pending_result_count||0)>0)return active?"review-partial":"review";
  if(["rag","llm_tool"].includes(job.type)&&job.status==="completed")return "result";
  if(job.type==="pdf_corpus"&&["completed","blocked"].includes(job.status))return "build";
  return null;
}
function operationViewModel(job){
  // Facts already shown elsewhere in the row (owner, operation name, stage) are left out.
  const skip=new Set([fact("started_by"),fact("operation"),fact("stage"),fact("total_time"),tr("pdf_corpus.stage","Stage")]);
  const facts=operationDetailPairs(job)
    .filter(([name,value])=>!skip.has(String(name))&&String(value??"").trim()!==""&&String(value).trim()!=="—")
    .slice(0,4)
    .map(([name,value])=>({name:String(name),value:String(value)}));
  const failure=job.status==="failed"?String(job.fatal_error||job.error_message||job.error?.message||job.stage_detail||""):job.status==="blocked"?String(job.stage_detail||""):"";
  const kind=operationResultKind(job);
  return {
    id:String(job.id),type:String(job.type||"llm"),status:String(job.status||""),
    label:jobLabel(job),icon:operationIcon(job),subtitle:operationSubtitle(job),facts,
    owner:String(job.owner||""),createdAt:job.created_at||null,startedAt:job.started_at||null,finishedAt:job.finished_at||null,
    total:Number(job.total||0),completed:Number(job.completed||0),progressLabel:jobProgressText(job,"of"),
    cancelRequested:Boolean(job.cancel_requested),error:failure,result:kind?{kind}:null,
  };
}
function operationsBridge(){
  return {
    snapshot:()=>(state.jobs||[]).map(operationViewModel),
    subscribe:listener=>{operationsListeners.add(listener);return()=>operationsListeners.delete(listener)},
    refresh:async()=>{await refreshJobs({rerender:true})},
    openDetails:id=>{void openJobDetails(id)},
    openResult:id=>{void openJobResults(id)},
    cancel:async id=>{await cancelBackgroundJob(id)},
    remove:async id=>{
      await api(`/api/jobs/${encodeURIComponent(id)}`,{method:"DELETE"});
      pruneClientJobState(id);
      persistPrefs();
      await refreshJobs({rerender:true});
    },
    clearFinished:async()=>{
      await api("/api/jobs",{method:"DELETE"});
      await refreshJobs({rerender:true});
    },
  };
}
function renderOperationsPanel(){
  // A placeholder only: the Vue panel is mounted into it by mountOperationsPanelHost().
  return `<div id="operationsPanelHost"></div>`;
}
function mountOperationsPanelHost(){
  mountOperationsPanel(document.querySelector("#operationsPanelHost"),operationsBridge());
}
function refreshOperationsPanelOnly(){
  notifyOperationsChanged();
  if(state.view==="rag")refreshRagProgressPanel();
}
function wireCorpusBuildsHomeCard(root=document){
  root.querySelector("#dashCorpusBuilder")?.addEventListener("click",()=>window.dispatchEvent(new CustomEvent("derridai:navigate-native",{detail:{path:"/pdf?mode=builder",runtimeView:"pdf"}})));
  root.querySelectorAll("[data-dashboard-corpus-build]").forEach(button=>button.addEventListener("click",()=>openJobResults(button.dataset.dashboardCorpusBuild)));
}
function refreshCorpusBuildsHomeCardOnly(){
  const current=document.querySelector(".dashboard-corpus-builds");
  if(!current)return;
  const holder=document.createElement("div");
  holder.innerHTML=renderCorpusBuildsHomeCard();
  const replacement=holder.firstElementChild;
  if(replacement)current.replaceWith(replacement);
  wireCorpusBuildsHomeCard();
}

async function openJobDetails(jobId){
  let job;
  try{
    job=await api(`/api/jobs/${encodeURIComponent(jobId)}`);
  }catch(error){
    if(String(error?.message||"").includes("404")){
      pruneClientJobState(jobId);
      persistPrefs();
      if(state.view==="rag")refreshRagProgressPanel();
      return toast("This operation was removed and has been cleared from the activity view");
    }
    return toast(`Could not load operation details: ${error.message}`);
  }
  const dialog=document.createElement("dialog");
  dialog.className="job-details-dialog";
  const events=job.events||[];
  const request=job.request||{};
  const safeRequest=cloneAuditValue(request);
  if(safeRequest&&typeof safeRequest==="object")delete safeRequest.api_key;

  const resultSummary=job.type==="llm"
    ? {
        pending_result_count:job.pending_result_count??(job.results||[]).length,
        pending_proposed_changes:job.pending_change_count??(job.results||[]).reduce((sum,result)=>sum+Object.keys(result.proposal?.changes||{}).length,0),
        accepted_results:job.accepted_results||0,
        accepted_fields:job.accepted_fields||0,
        rejected_results:job.rejected_results||0,
        rejected_fields:job.rejected_fields||0,
        resolution_state:job.resolution_state||"pending",
        unprocessed_records:job.remaining_record_count??Math.max(0,(job.total||0)-(job.completed||0)),
        failures:(job.results||[]).filter(result=>result.error).length,
      }
    : job.type==="upsert"
      ? {
          committed:job.completed||0,
          requested:job.total||0,
          target_collection:job.store_name,
          language_mirrors:job.mirrored||{},
          receipt_count:(job.results||[]).length,
        }
      : job.type==="pdf_corpus"
        ? {
            source_pdf:job.source_filename||null,
            build_id:job.build_id||job.id,
            raw_status:job.raw_status||job.status,
            stage:job.stage||null,
            record_count:job.record_count||0,
            review_count:job.review_count||0,
            unresolved_regions:job.unresolved_regions||0,
          }
      : job.type==="llm_tool"
        ? {
            operation:job.label||job.tool||job.mode,
            provider_profile_id:job.provider_profile_id||null,
            max_concurrent_requests:job.max_concurrent_requests||null,
            has_result:Boolean(job.result),
            result_keys:job.result&&typeof job.result==="object"?Object.keys(job.result):[],
          }
        : {
            has_result:Boolean(job.result),
            evidence_count:job.result?.evidence?.length||0,
            elapsed_seconds:job.result?.elapsed_seconds??null,
            collections:job.result?.collections||[],
            response_cache:job.result?.response_cache||job.response_cache||null,
          };

  dialog.innerHTML=`<div class="dh">
    <div><h2 class="dialog-title">${esc(jobLabel(job))} details</h2><div class="dialog-subtitle">${esc(job.id)} · ${esc(job.status)} · created ${esc(formatTimestamp(job.created_at))}</div></div>
    <button class="btn icon-only" data-close>${icon("close")}</button>
  </div>
  <div class="db job-details-body">
    <section class="job-detail-summary">
      ${[
        ["Type",job.type],
        ["Started by",job.owner||"—"],
        ["Status",job.status],
        ["Provider",job.provider],
        ["Model",job.model],
        ["Progress",`${job.completed}/${job.total}`],
        ["Failed",job.failed||0],
        ["Started",job.started_at?formatTimestamp(job.started_at):"—"],
        ["Finished",job.finished_at?formatTimestamp(job.finished_at):"—"],
        ["Cancel requested",job.cancel_requested_at?formatTimestamp(job.cancel_requested_at):"—"],
      ].map(([name,value])=>`<div><span>${esc(name)}</span><b>${esc(value??"—")}</b></div>`).join("")}
    </section>
    ${job.fatal_error?`<div class="info error">${esc(job.fatal_error)}</div>`:""}
    <section class="card-inset">
      <div class="rag-result-section-head"><div><b>Request configuration</b><div class="note">API keys are intentionally omitted.</div></div></div>
      <pre class="job-detail-json">${esc(JSON.stringify(safeRequest,null,2))}</pre>
    </section>
    <section class="card-inset">
      <div class="rag-result-section-head"><div><b>Operation timeline</b><div class="note">${events.length} recorded events</div></div></div>
      <div class="job-event-list">${events.map((event,index)=>`<div class="job-event ${index===events.length-1?"latest":""}"><time>${esc(formatTimestamp(event.timestamp))}</time><b>${esc(label(event.stage||"event"))}</b><span>${event.current!=null&&event.total!=null?`${event.current}/${event.total} · `:""}${esc(event.detail||"")}</span></div>`).join("")||'<div class="note">No events recorded.</div>'}</div>
    </section>
    <section class="card-inset">
      <div class="rag-result-section-head"><b>Result summary</b></div>
      <pre class="job-detail-json">${esc(JSON.stringify(resultSummary,null,2))}</pre>
    </section>
  </div>
  <div class="da">
    <button class="btn" data-close>Close</button>
    ${["queued","running","cancelling"].includes(job.status)?(job.cancel_requested||job.status==="cancelling"?'<button class="btn" disabled>Cancelling…</button>':`<button class="btn danger" id="detailsCancelJob">Cancel operation</button>`):""}
    ${job.type==="llm"&&(job.pending_result_count??(job.results||[]).length)>0?`<button class="btn primary" id="detailsOpenResult">${["queued","running","cancelling"].includes(job.status)?"Review available results":"Review results"}</button>`:""}
    ${((["rag","llm_tool"].includes(job.type)&&job.status==="completed")||(job.type==="pdf_corpus"&&["completed","blocked"].includes(job.status)))?`<button class="btn primary" id="detailsOpenResult">${job.type==="pdf_corpus"?esc(tr("pdf_corpus.open_build","Open corpus build")):"Open result"}</button>`:""}
  </div>`;
  document.body.appendChild(dialog);
  showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelector("#detailsCancelJob")?.addEventListener("click",async()=>{
    const updated=await cancelBackgroundJob(job.id);
    if(updated){close();openJobDetails(job.id)}
  });
  dialog.querySelector("#detailsOpenResult")?.addEventListener("click",()=>{close();openJobResults(job.id)});
}

function openReviewRecordPreview(local,result){
  const record=local?.file?.records?.[local.index];
  if(!record)return toast("The source record is no longer loaded in this workspace");

  const proposal=result?.proposal||{};
  const proposedFields=Object.keys(proposal.changes||{});
  const important=[
    "work","document_author","edition","year","page_start","page_end",
    "region_type","region_author","speaker","position_holder","target",
    "discourse_role","proposition_status","semantic_function","stance",
    "claim_scope","is_direct_quote","quoted_speaker","quoted_author",
    "quoted_work","quoted_position_holder","quoted_addressee",
    "quoted_referent","quotation_chain","topics","concepts","persons",
    "works_referenced","document_language","original_language",
    "inline_citation","full_citation","needs_review","review_reason"
  ].filter(field=>record[field]!==undefined);

  const dialog=document.createElement("dialog");
  dialog.className="record-preview-dialog";
  const stale=Boolean(result?.fingerprint&&recordFingerprint(record)!==result.fingerprint);
  const updates=Array.isArray(record.updates)?record.updates.slice(-8).reverse():[];

  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Record preview</h2><div class="dialog-subtitle">${esc(record.record_id||`Record ${local.index+1}`)} · ${esc(record.work||local.file.name)} · ${esc(local.file.name)}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db record-preview-body">
    ${stale?'<div class="info warn">This local record changed after the LLM job started. Current values below may differ from the values originally reviewed.</div>':""}
    <section class="record-preview-summary">
      <div><span>Record ID</span><b>${esc(record.record_id||"—")}</b></div>
      <div><span>Work</span><b>${esc(record.work||"—")}</b></div>
      <div><span>Pages</span><b>${esc(pages(record))}</b></div>
      <div><span>Citation</span><b>${esc(fullCitation(record)||"—")}</b></div>
      <div><span>LLM proposals</span><b>${proposedFields.length}</b></div>
      <div><span>Needs review</span><b>${record.needs_review?"Yes":"No"}</b></div>
    </section>

    <section class="record-preview-section">
      <div class="record-preview-heading"><b>Metadata</b><span>${important.length} populated fields</span></div>
      <div class="record-preview-metadata">${important.map(field=>`<div class="record-preview-field ${proposedFields.includes(field)?"proposed-field":""}"><span>${esc(label(field))}${proposedFields.includes(field)?'<i>proposed change</i>':""}</span><pre>${esc(jsonPretty(record[field]))}</pre></div>`).join("")}</div>
    </section>

    <section class="record-preview-section">
      <div class="record-preview-heading"><b>Text</b><span>${String(record.text||"").length.toLocaleString()} characters</span></div>
      <pre class="record-preview-text">${esc(record.text||"")}</pre>
    </section>

    ${proposedFields.length?`<section class="record-preview-section"><div class="record-preview-heading"><b>Proposed changes for this record</b><span>${proposedFields.length}</span></div><div class="record-preview-proposals">${proposedFields.map(field=>`<div><b>${esc(label(field))}</b><div class="record-preview-proposal-grid"><pre>${esc(jsonPretty(record[field]))}</pre><span>→</span><pre>${esc(jsonPretty(proposal.changes[field]))}</pre></div>${proposal.rationale?.[field]?`<small>${esc(proposal.rationale[field])}</small>`:""}</div>`).join("")}</div></section>`:""}

    <section class="record-preview-section">
      <div class="record-preview-heading"><b>Recent audit history</b><span>${updates.length} shown</span></div>
      <div class="record-preview-history">${updates.map(update=>`<div><time>${esc(formatTimestamp(update.timestamp))}</time><b>${esc(label(update.field_name||"field"))}</b><span>${esc(update.source||"manual")}${update.initiated_by?` · ${esc(update.initiated_by)}`:""}</span></div>`).join("")||'<div class="note">No audit history recorded.</div>'}</div>
    </section>
  </div>
  <div class="da"><button class="btn" data-close>Close preview</button><button class="btn" data-copy-row-key="${esc(reviewKey(local.file,local.index))}">${icon("copy")}Copy entire record</button><button class="btn primary" id="previewOpenRecord">${icon("arrow")}Open full Record view</button></div>`;

  document.body.appendChild(dialog);
  showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelector("#previewOpenRecord").onclick=()=>{
    close();
    navigateTo("record",{fileId:local.file.id,index:local.index});
  };
}

function reviewDiffSides(current,proposed){
  const leftText=jsonPretty(current);
  const rightText=jsonPretty(proposed);
  const parts=diffWordsWithSpace(leftText,rightText);
  const left=parts.filter(part=>!part.added).map(part=>part.removed?`<span class="del">${esc(part.value)}</span>`:esc(part.value)).join("");
  const right=parts.filter(part=>!part.removed).map(part=>part.added?`<span class="ins">${esc(part.value)}</span>`:esc(part.value)).join("");
  return {left,right};
}

async function openJobResults(jobId){
  let job;
  try{job=await api(`/api/jobs/${encodeURIComponent(jobId)}`)}catch(error){
    if(String(error?.message||"").includes("404")){pruneClientJobState(jobId);persistPrefs();if(state.view==="rag")refreshRagProgressPanel();return toast("This operation was removed and has been cleared from the activity view")}
    await openMessageModal({title:"Could not open operation result",message:error.message||String(error),tone:"danger"});
    return;
  }
  try{
    if(job.type==="rag")return openRagResult(job);
    if(job.type==="llm_tool")return openLlmToolResult(job);
    if(job.type==="upsert")return openJobDetails(job.id);
    if(job.type==="pdf_corpus"){
      window.dispatchEvent(new CustomEvent("derridai:navigate-native",{detail:{path:`/pdf?mode=builder&build=${encodeURIComponent(job.build_id||job.id)}`,runtimeView:"pdf"}}));
      return;
    }
  }catch(error){
    console.error("Could not render operation result",error,job);
    await openMessageModal({title:"Could not render operation result",message:error.message||String(error),detail:jobLabel(job),tone:"danger"});
    return;
  }

  const dialog=document.createElement("dialog");
  dialog.className="job-results-dialog";
  document.body.appendChild(dialog);
  showAppModal(dialog);
  let liveTimer=null;

  async function refreshJob(){
    try{
      job=await api(`/api/jobs/${encodeURIComponent(jobId)}`);
      const idx=state.jobs.findIndex(item=>item.id===job.id);
      if(idx>=0)state.jobs[idx]={...state.jobs[idx],...job};
      return true;
    }catch(error){
      toast(`Could not refresh review results: ${error.message}`);
      return false;
    }
  }

  function buildData(){
    const successful=(job.results||[]).filter(result=>!result.error&&result.proposal);
    const failures=(job.results||[]).filter(result=>result.error);
    const unchanged=[];
    const flattened=[];
    for(const result of successful){
      const local=reviewItemFromKey(result.key);
      const currentRecord=local?.file.records[local.index];
      const stale=Boolean(local&&result.fingerprint&&recordFingerprint(currentRecord)!==result.fingerprint);
      const changes=Object.entries(result.proposal?.changes||{});
      if(!changes.length){
        unchanged.push({result,local,stale});
        continue;
      }
      for(const [field,proposed] of changes){
        flattened.push({
          result,local,field,
          current:currentRecord?.[field],
          proposed,
          rationale:result.proposal?.rationale?.[field]||"",
          stale,
        });
      }
    }
    return {successful,failures,unchanged,flattened};
  }

  let selections=new Set();

  function initializeSelections(flattened){
    const valid=[...selections].filter(index=>index<flattened.length);
    selections=new Set(valid);
    if(!selections.size){
      flattened.forEach((item,index)=>{if(item.field!=="text")selections.add(index)});
    }
  }

  async function resolveOnServer(action,items,{dismissJob=false}={}){
    return api(`/api/jobs/${encodeURIComponent(job.id)}/llm-results/resolve`,{
      method:"POST",
      body:JSON.stringify({action,items,dismiss_job:dismissJob}),
    });
  }

  async function rejectAndDismiss(){
    if(!await openMessageModal({title:"Discard pending LLM review?",message:"Discard all currently pending proposed changes, stop the review if it is still running, and remove this operation from the queue?",tone:"danger",confirmLabel:"Discard pending & remove",cancelLabel:"Keep review"}))return;
    try{
      await api(`/api/jobs/${encodeURIComponent(job.id)}/llm-results/reject`,{
        method:"POST",
        body:JSON.stringify({dismiss:true}),
      });
      dialog.close();dialog.remove();
      await refreshJobs({rerender:state.view==="home"});
      toast("LLM review rejected and removed from the operations queue");
    }catch(error){
      toast(`Could not reject LLM review: ${error.message}`);
    }
  }

  async function apply(mode){
    const {successful,unchanged,flattened}=buildData();
    const batchId=uid();
    let fieldsApplied=0;
    let fullyReviewed=0;
    const resolveItems=[];
    const byKey=new Map();

    for(const result of successful){
      const local=reviewItemFromKey(result.key);
      if(local){
        byKey.set(result.key,{
          item:local,
          result,
          fields:[],
          allFields:Object.keys(result.proposal?.changes||{}),
          rationale:result.proposal?.rationale||{},
          resolveRecord:false,
        });
      }
    }

    if(mode==="review"){
      for(const entry of byKey.values())entry.resolveRecord=true;
    }else if(mode==="all"){
      for(const entry of byKey.values()){
        entry.fields=[...entry.allFields];
        entry.resolveRecord=true;
      }
    }else{
      flattened.forEach((entry,index)=>{
        if(!selections.has(index)||!entry.local)return;
        const target=byKey.get(entry.result.key);
        if(target)target.fields.push(entry.field);
      });
      for(const target of byKey.values()){
        if(target.fields.length&&target.fields.length===target.allFields.length){
          target.resolveRecord=true;
        }
      }
    }

    for(const [key,target] of byKey.entries()){
      if(mode==="selected"&&!target.fields.length)continue;
      const record=target.item.file.records[target.item.index];
      const changes={};
      if(mode!=="review"){
        const sourceChanges=target.result.proposal?.changes||{};
        for(const field of target.fields){
          if(field in sourceChanges)changes[field]=sourceChanges[field];
        }
      }

      // Clear needs_review only when the full pending proposal for this record
      // is being resolved, or the user explicitly chose "mark reviewed only".
      if(target.resolveRecord){
        if(record.needs_review!==false)changes.needs_review=false;
        if(record.review_reason!=null&&record.review_reason!=="")changes.review_reason=null;
      }
      fieldsApplied+=applyRecordChanges(
        target.item.file,
        target.item.index,
        changes,
        {
          source:"llm_review",
          model:job.model,
          batchId,
          rationale:target.rationale,
        }
      );
      if(target.resolveRecord)fullyReviewed++;

      resolveItems.push({
        key,
        fields:target.resolveRecord?null:target.fields,
        resolve_record:target.resolveRecord,
      });
    }

    if(mode==="review"){
      for(const entry of unchanged){
        if(!entry.local)continue;
        const record=entry.local.file.records[entry.local.index];
        const changes={};
        if(record.needs_review!==false)changes.needs_review=false;
        if(record.review_reason!=null&&record.review_reason!=="")changes.review_reason=null;
        fieldsApplied+=applyRecordChanges(
          entry.local.file,
          entry.local.index,
          changes,
          {source:"llm_review",model:job.model,batchId,rationale:{}}
        );
        fullyReviewed++;
        resolveItems.push({key:entry.result.key,fields:null,resolve_record:true});
      }
    }else if(mode==="all"){
      for(const entry of unchanged){
        if(!entry.local)continue;
        const record=entry.local.file.records[entry.local.index];
        const changes={};
        if(record.needs_review!==false)changes.needs_review=false;
        if(record.review_reason!=null&&record.review_reason!=="")changes.review_reason=null;
        fieldsApplied+=applyRecordChanges(
          entry.local.file,
          entry.local.index,
          changes,
          {source:"llm_review",model:job.model,batchId,rationale:{}}
        );
        fullyReviewed++;
        resolveItems.push({key:entry.result.key,fields:null,resolve_record:true});
      }
    }

    if(!resolveItems.length)return toast("No LLM results selected");

    try{
      job=await resolveOnServer("accept",resolveItems);
      state.jobApplied[job.id]=new Date().toISOString();
      persistPrefs();
      shell();renderView();
      await refreshJobs({rerender:state.view==="home"});
      selections.clear();
      render({preserveScroll:true});
      toast(`Accepted ${resolveItems.length} pending result${resolveItems.length===1?"":"s"} · ${fieldsApplied} tracked field changes · ${job.pending_result_count||0} pending`);
    }catch(error){
      toast(`Local changes were applied, but the operation queue could not be updated: ${error.message}`);
    }
  }

  async function rejectSelected(){
    const {flattened}=buildData();
    const grouped=new Map();
    flattened.forEach((entry,index)=>{
      if(!selections.has(index))return;
      if(!grouped.has(entry.result.key))grouped.set(entry.result.key,[]);
      grouped.get(entry.result.key).push(entry.field);
    });
    const items=[...grouped.entries()].map(([key,fields])=>({key,fields,resolve_record:false}));
    if(!items.length)return toast("Select proposed changes to reject");
    try{
      job=await resolveOnServer("reject",items);
      selections.clear();
      await refreshJobs({rerender:state.view==="home"});
      render({preserveScroll:true});
      toast(`Rejected selected proposed changes · ${job.pending_change_count||0} pending changes remain`);
    }catch(error){
      toast(`Could not reject selected changes: ${error.message}`);
    }
  }

  function render({preserveScroll=false}={}){
    const tableBefore=dialog.querySelector(".job-change-table-wrap");
    const scrollState=preserveScroll?{dialog:dialog.scrollTop,tableTop:tableBefore?.scrollTop||0,tableLeft:tableBefore?.scrollLeft||0}:null;
    const {successful,failures,unchanged,flattened}=buildData();
    initializeSelections(flattened);
    const selected=selections.size;
    const changedRecords=new Set(flattened.map(item=>item.result.key)).size;
    const noChangeCount=unchanged.length;
    const active=["queued","running","cancelling"].includes(job.status);
    const statusText=job.status==="cancelled"?"cancelled with partial results":job.status;
    const pendingResults=job.pending_result_count??successful.length;
    const pendingChanges=job.pending_change_count??flattened.length;
    const remaining=job.remaining_record_count??Math.max(0,(job.total||0)-(job.completed||0));

    const changeTable=flattened.length?`<div class="job-change-table-wrap"><table class="job-change-table"><thead><tr><th></th><th>Record</th><th>Field</th><th>Current</th><th>Proposed</th><th>Rationale</th></tr></thead><tbody>${flattened.map((item,index)=>{
      const rid=item.local?.record?.record_id||item.result.record_id||item.result.key;
      const diff=reviewDiffSides(item.current,item.proposed);
      return `<tr class="${item.stale?"stale-change":""}"><td><input type="checkbox" data-job-change="${index}" ${selections.has(index)?"checked":""}></td><td><div class="job-record-cell"><b>${esc(rid)}</b>${item.local?`<button class="btn tiny" data-copy-row-key="${esc(reviewKey(item.local.file,item.local.index))}">${icon("copy")}Copy</button>`:""}<button class="btn tiny" data-preview-result="${index}">Preview record</button>${item.stale?'<span class="stale-badge">local record changed since job started</span>':""}</div></td><td><b>${esc(label(item.field))}</b></td><td><pre class="change-diff current-diff">${diff.left}</pre></td><td><pre class="change-diff proposed-diff">${diff.right}</pre></td><td>${esc(item.rationale||"No rationale supplied.")}</td></tr>`;
    }).join("")}</tbody></table></div>`:`<section class="review-no-changes-empty"><div class="review-no-changes-icon">✓</div><div><h3>${active?"No pending changes yet":"No changes proposed"}</h3><p>${active?`The review is still running. ${job.completed.toLocaleString()} records have completed and ${remaining.toLocaleString()} remain unprocessed.`:`The model reviewed ${noChangeCount.toLocaleString()} record${noChangeCount===1?"":"s"} and did not propose metadata/text edits.`}</p></div></section>`;

    const unchangedSection=noChangeCount?`<details class="unchanged-review-list" ${flattened.length?"":"open"}><summary><span><b>${noChangeCount.toLocaleString()} record${noChangeCount===1?"":"s"} with no proposed changes</b><small>Expand to inspect or preview these records</small></span></summary><div class="unchanged-review-grid">${unchanged.map((item,index)=>{const rid=item.local?.record?.record_id||item.result.record_id||item.result.key;return `<div class="unchanged-review-row"><div><b>${esc(rid)}</b><span>${esc(item.local?.record?.work||"")}${item.stale?" · local record changed since review":""}</span></div><button class="btn tiny" data-preview-unchanged="${index}">Preview record</button></div>`}).join("")}</div></details>`:"";

    dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${job.mode==="auto"?"Auto-improve changes":"LLM review changes"}</h2><div class="dialog-subtitle">${job.completed}/${job.total} processed · ${pendingResults} pending result${pendingResults===1?"":"s"} · ${pendingChanges} pending change${pendingChanges===1?"":"s"} · ${remaining} unprocessed · ${failures.length} failures · ${esc(statusText)}</div></div><div class="tools">${active?'<span class="job-status running">live</span>':""}<button class="btn icon-only" data-close>${icon("close")}</button></div></div>
    <div class="db job-change-review">
      <div class="job-resolution-summary">
        <span><b>${job.accepted_results||0}</b> accepted results</span>
        <span><b>${job.accepted_fields||0}</b> accepted fields</span>
        <span><b>${job.rejected_results||0}</b> rejected results</span>
        <span><b>${job.rejected_fields||0}</b> rejected fields</span>
        <span><b>${esc((job.resolution_state||"pending").replaceAll("_"," "))}</b> decision state</span>
      </div>
      ${flattened.length?`<div class="job-change-toolbar"><button class="btn small" id="jobSelectAll">Select all changes</button><button class="btn small" id="jobSelectNone">Select none</button><button class="btn small danger" id="jobRejectSelected">Reject selected</button><span class="note"><b id="jobSelectedCount">${selected}</b> selected · accepted changes are removed from this pending queue immediately</span></div>`:""}
      ${failures.length?`<div class="info warn">${failures.map(result=>`${esc(result.record_id||result.key)}: ${esc(result.error?.message||"failed")}`).join("<br>")}</div>`:""}
      ${changeTable}
      ${unchangedSection}
    </div>
    <div class="da">
      <button class="btn" data-close>Close</button>
      ${active&&remaining>0?`<button class="btn danger subtle-danger" id="rejectJob">${icon("close")}Stop review & discard pending</button>`:pendingResults>0?`<button class="btn danger subtle-danger" id="rejectJob">${icon("close")}Discard pending & remove operation</button>`:""}
      ${active?`<button class="btn" id="refreshLiveResults">${icon("refresh")}Refresh available results</button>`:""}
      ${successful.length?`<button class="btn" id="markJobReviewed">${icon("check")}Mark all available reviewed</button>${flattened.length?`<button class="btn primary" id="applyJobSelected" ${selected?"":"disabled"}>${icon("check")}Apply selected</button><button class="btn soft" id="applyJobAll">${icon("check")}Accept all available</button>`:""}`:""}
    </div>`;

    const close=()=>{if(liveTimer)clearInterval(liveTimer);dialog.close();dialog.remove()};
    dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
    const syncSelectionUi=()=>{
      dialog.querySelectorAll("[data-job-change]").forEach(box=>{box.checked=selections.has(+box.dataset.jobChange)});
      const count=dialog.querySelector("#jobSelectedCount");if(count)count.textContent=String(selections.size);
      const applyButton=dialog.querySelector("#applyJobSelected");if(applyButton)applyButton.disabled=!selections.size;
    };
    dialog.querySelector("#jobSelectAll")?.addEventListener("click",()=>{flattened.forEach((_,index)=>selections.add(index));syncSelectionUi()});
    dialog.querySelector("#jobSelectNone")?.addEventListener("click",()=>{selections.clear();syncSelectionUi()});
    dialog.querySelector("#jobRejectSelected")?.addEventListener("click",rejectSelected);
    dialog.querySelector("#rejectJob")?.addEventListener("click",rejectAndDismiss);
    dialog.querySelector("#refreshLiveResults")?.addEventListener("click",async()=>{if(await refreshJob())render({preserveScroll:true})});
    dialog.querySelectorAll("[data-job-change]").forEach(box=>box.onchange=()=>{const index=+box.dataset.jobChange;box.checked?selections.add(index):selections.delete(index);syncSelectionUi()});
    dialog.querySelectorAll("[data-preview-result]").forEach(button=>button.onclick=()=>{const entry=flattened[+button.dataset.previewResult];if(entry?.local)openReviewRecordPreview(entry.local,entry.result);else toast("The source record is no longer loaded")});
    dialog.querySelectorAll("[data-preview-unchanged]").forEach(button=>button.onclick=()=>{const entry=unchanged[+button.dataset.previewUnchanged];if(entry?.local)openReviewRecordPreview(entry.local,entry.result);else toast("The source record is no longer loaded")});
    dialog.querySelector("#markJobReviewed")?.addEventListener("click",()=>apply("review"));
    dialog.querySelector("#applyJobSelected")?.addEventListener("click",()=>apply("selected"));
    dialog.querySelector("#applyJobAll")?.addEventListener("click",()=>apply("all"));
    if(scrollState)requestAnimationFrame(()=>{dialog.scrollTop=scrollState.dialog;const table=dialog.querySelector(".job-change-table-wrap");if(table){table.scrollTop=scrollState.tableTop;table.scrollLeft=scrollState.tableLeft}});
  }

  render();
  if(["queued","running","cancelling"].includes(job.status)){
    liveTimer=setInterval(async()=>{
      if(!dialog.isConnected){clearInterval(liveTimer);return}
      const before=job.completed;
      const pendingBefore=job.pending_result_count;
      if(await refreshJob()){
        if(job.completed!==before||job.pending_result_count!==pendingBefore||!["queued","running","cancelling"].includes(job.status)){
          render({preserveScroll:true});
        }
        if(!["queued","running","cancelling"].includes(job.status)){
          clearInterval(liveTimer);liveTimer=null;
        }
      }
    },4000);
  }
}
function prepareRagRerun(request={}){
  const cfg=state.ragConfig;
  const source=request.source_collection;
  if(source)cfg.source_collection=source;
  if(Array.isArray(request.locales)&&request.locales.length)cfg.locales=[...request.locales];
  if(Array.isArray(request.search_types)&&request.search_types.length)cfg.search_types=[...request.search_types];
  for(const key of [
    "k","fetch_k","lambda_mult","rrf_k","rerank_top_n","reranker",
    "cross_encoder_model","query_decomposition","query_decomposition_num_predict",
    "response_language","evidence_record_char_limit","evidence_total_char_limit",
    "bind_citations","include_works_cited","auto_grade"
  ]){
    if(request[key]!==undefined)cfg[key]=cloneAuditValue(request[key]);
  }
  cfg.prompt=String(request.prompt||cfg.prompt||"");
  cfg.instructions=String(request.instructions||cfg.instructions||"");

  const providerType=request.provider;
  const baseUrl=request.base_url;
  const model=request.model;
  let profile=providerProfiles().find(item=>
    (!providerType||item.type===providerType)
    &&(!baseUrl||item.base_url===baseUrl)
    &&(!model||item.model===model||model==="auto"&&item.model_mode==="auto")
  );
  if(!profile&&providerType){
    profile={
      id:`rerun-${providerType}-${uid()}`,
      name:`Rerun · ${providerType==="ollama"?"Ollama":"OpenAI-compatible"}`,
      type:providerType,
      base_url:baseUrl||(providerType==="ollama"?"http://host.docker.internal:11434":"http://host.docker.internal:3001/v1"),
      model:model||(providerType==="ollama"?"gemma4:e2b":"auto"),
      model_mode:providerType==="openai"&&model==="auto"?"auto":"manual",
      model_kind:"any",
      api_key:"",
      max_concurrent_requests:Math.max(1,Math.min(64,Number(request.max_concurrent_requests??(providerType==="ollama"?1:32))||1)),
      num_predict:request.generation?.num_predict??4096,
      num_ctx:request.generation?.num_ctx??16384,
      think:String(request.generation?.think??"false"),
      temperature:request.generation?.temperature??0,
      top_k:request.generation?.top_k??0,
      top_p:request.generation?.top_p??1,
      min_p:request.generation?.min_p??"",
      repeat_penalty:request.generation?.repeat_penalty??1.1,
      seed:request.generation?.seed??"",
      keep_alive:request.generation?.keep_alive||"10m",
      extra_options:JSON.stringify(request.generation?.extra_options||{}),
    };
    state.appConfig.provider_profiles.push(profile);
  }
  if(profile){
    cfg.provider_profile_id=profile.id;
    if(request.generation){
      const generation=request.generation;
      for(const key of ["num_ctx","num_predict","temperature","top_k","top_p","min_p","repeat_penalty","seed","mirostat","mirostat_eta","mirostat_tau","keep_alive"]){
        if(generation[key]!==undefined&&generation[key]!==null)profile[key]=generation[key];
      }
      if(generation.think!==undefined&&generation.think!==null)profile.think=String(generation.think);
      if(generation.extra_options)profile.extra_options=JSON.stringify(generation.extra_options);
    }
  }
  if(request.auto_grade_provider_profile_id&&providerProfiles().some(item=>item.id===request.auto_grade_provider_profile_id)){
    cfg.auto_grade_provider_profile_id=request.auto_grade_provider_profile_id;
  }else if(request.auto_grade_provider){
    const gradeProfile=providerProfiles().find(item=>
      item.type===request.auto_grade_provider
      &&(!request.auto_grade_model||item.model===request.auto_grade_model||request.auto_grade_model==="auto"&&item.model_mode==="auto")
    );
    if(gradeProfile)cfg.auto_grade_provider_profile_id=gradeProfile.id;
  }
  persistPrefs();
  navigateTo("rag");
}
async function gradeRagResponse({
  question,
  answer,
  evidence=[],
  responseRecordId=null,
  generationProvider=null,
  generationModel=null,
}){
  openLlmTaskLauncher({
    task:"rag_grade",
    title:"Analyze & grade RAG response",
    description:"Grade relevance, source binding, attribution, fidelity, precision, coverage, and interpretive usefulness.",
    contextText:question,
    generationProvider,
    generationModel,
    payload:{
      question,answer,evidence:ragGradeEvidencePayload(evidence),response_record_id:responseRecordId,
      generation_provider:generationProvider,
      generation_model:generationModel,
    },
    onForegroundResult:async result=>{
      const dialog=document.createElement("dialog");dialog.className="rag-grade-dialog";
      dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">RAG response grade</h2><div class="dialog-subtitle">Saved with the cached RAG query when a response-cache record is available.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db">${ragGradeHtml(result.grade||{})}</div><div class="da"><button class="btn" data-close>Close</button></div>`;
      document.body.appendChild(dialog);showAppModal(dialog);const close=()=>{dialog.close();dialog.remove()};dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
    },
  });
}
function faqExpansionKey(record){
  return String(record?.record_id||record?.cache_key||`${record?.question||"question"}::${record?.created_at||"unknown"}`);
}
function gradeEveryFaqResponse(){
  openLlmTaskLauncher({
    task:"rag_grade_batch",
    title:"Grade every Response Library entry",
    description:"Grade or re-grade every cached RAG response sequentially with the selected provider/model/config. Existing grades are retained in grade history.",
    contextText:"All cached RAG responses in the logical response cache",
  });
}
async function renderFaq(main){
  const token=nextProgressiveRenderToken();
  showViewLoading(main,"Loading Response Library","Reading saved RAG responses and grades…");
  const pageSize=50;
  const requestedPage=Math.max(1,state.faqPage||1);
  const fetchPage=async page=>{
    const offset=(page-1)*pageSize;
    const params=new URLSearchParams({limit:String(pageSize),offset:String(offset)});
    if(state.faqSearch)params.set("query",state.faqSearch);
    return api(`/api/response-cache/records?${params}`);
  };
  let payload;
  try{
    payload=await fetchPage(requestedPage);
  }catch(error){
    main.innerHTML=`<div class="info error"><b>Could not load Response Library.</b><span>${esc(error.message||String(error))}</span></div>`;
    return;
  }
  let matchedTotal=Number(payload.count||0);
  const cacheTotal=Number(payload.total??matchedTotal??0);
  let pagesTotal=Math.max(1,Math.ceil(matchedTotal/pageSize));
  if(requestedPage>pagesTotal){
    state.faqPage=pagesTotal;persistPrefs();
    try{
      payload=await fetchPage(pagesTotal);
      matchedTotal=Number(payload.count||0);
    }catch(error){
      main.innerHTML=`<div class="info error">${esc(error.message||String(error))}</div>`;
      return;
    }
  }else state.faqPage=requestedPage;
  const records=Array.isArray(payload.records)?payload.records:[];
  pagesTotal=Math.max(1,Math.ceil(matchedTotal/pageSize));
  const noMatches=records.length===0&&matchedTotal===0&&cacheTotal>0&&Boolean(state.faqSearch);
  const noCache=cacheTotal===0&&!payload.exists;
  if(noCache){
    main.innerHTML=`<section class="empty"><div class="drop"><div class="drop-icon">${icon("spark")}</div><h1>Response Library</h1><p>Completed RAG runs will be cached automatically and appear here.</p><button class="btn primary" id="faqGoRag">${icon("spark")}Run a RAG query</button></div></section>`;
    main.querySelector("#faqGoRag")?.addEventListener("click",e=>{if(!e.currentTarget.disabled)navigateTo("rag")});
    decorateDisabledControls(main);
    return;
  }
  main.innerHTML=`<div class="toolbar faq-toolbar"><div class="search"><input id="faqSearch" value="${esc(state.faqSearch||"")}" placeholder="Search cached questions"></div><div class="tools"><span class="note">${cacheTotal.toLocaleString()} cached response${cacheTotal===1?"":"s"}${state.faqSearch?` · ${matchedTotal.toLocaleString()} match${matchedTotal===1?"":"es"}`:""}</span>${state.faqSearch?'<button class="btn small" id="faqClearSearch">Clear search</button>':""}<button class="btn small" id="faqExpandAll">Expand all</button><button class="btn small" id="faqCollapseAll">Collapse all</button>${isResearcher()?"":`<button class="btn small soft" id="faqGradeAll">${icon("spark")}Grade every response</button>`}<button class="btn" id="faqGoRag">${icon("spark")}New RAG query</button></div></div>
  ${noMatches?`<div class="info">The response cache contains ${cacheTotal.toLocaleString()} response${cacheTotal===1?"":"s"}, but none match the current Response Library search. Clear the search to show all cached responses.</div>`:""}
  <section class="faq-list" id="faqList"></section>
  <div class="pagebar"><span>Page ${state.faqPage||1} of ${pagesTotal}</span><div class="tools"><button class="btn small" id="faqPrev" ${(state.faqPage||1)<=1?"disabled":""}>← Previous</button><button class="btn small" id="faqNext" ${(state.faqPage||1)>=pagesTotal?"disabled":""}>Next →</button></div></div>`;
  const cardHtml=(record,index)=>{
    const grade=normalizeRagGrade(record.grade||{});
    const overall=grade.score("overall");
    const grades=Array.isArray(record.grades)?record.grades:[];
    const evidence=Array.isArray(record.evidence)?record.evidence:[];
    const expansionKey=faqExpansionKey(record);
    return `<article class="card faq-card" data-faq-index="${index}"><details class="faq-response-shell" data-faq-expand-key="${esc(expansionKey)}" ${state.faqExpanded[expansionKey]?"open":""}>
      <summary class="faq-response-summary"><div class="faq-summary-copy"><b>${esc(record.question||"Untitled question")}</b><span>${esc(record.provider||"")} · ${esc(record.model||"")} · ${esc(formatTimestamp(record.created_at))} · ${Number(record.evidence_count||evidence.length||0)} evidence records</span></div><div class="faq-summary-status">${overall!=="—"?`<span class="faq-grade">${esc(overall)}/10</span>`:""}<span class="faq-summary-chevron">⌄</span></div></summary>
      <div class="faq-response-body"><div class="faq-card-actions"><button class="btn small" data-faq-rerun="${index}">${icon("refresh")}Re-run</button><button class="btn small" data-faq-grade="${index}">${icon("spark")}Grade</button></div>
        ${record.instructions?`<div class="faq-instructions"><b>Instructions</b><span>${esc(record.instructions)}</span></div>`:""}
        <div class="rag-answer-prose faq-answer">${ragAnswerHtml(record.text||"")}</div>
        ${grades.length?`<details class="faq-grade-details"><summary>Saved LLM grades (${grades.length})</summary><div class="faq-grade-history">${[...grades].reverse().map(entry=>`<section class="faq-grade-entry"><div class="faq-grade-source"><b>${esc(entry?.provider||"")}</b><span>${esc(entry?.model||"")} · ${esc(formatTimestamp(entry?.graded_at))}${entry?.same_model_as_generation?" · same model as generation":""}</span></div>${entry?.same_model_as_generation?'<div class="info warn">This grade used the same model as answer generation; interpret it as self-evaluation rather than an independent grade.</div>':""}${ragGradeHtml(entry?.result||entry||{})}</section>`).join("")}</div></details>`:""}
        <details class="faq-details"><summary>Evidence, retrieval, and pipeline details</summary><div class="rag-result-grid"><pre class="rag-json">${esc(JSON.stringify(record.retrieval||{},null,2))}</pre><pre class="rag-json">${esc(JSON.stringify(record.query_metadata||{},null,2))}</pre></div><div class="rag-evidence-list">${evidence.map(ragEvidencePreview).join("")||'<div class="note">No full evidence retained.</div>'}</div></details>
      </div></details></article>`;
  };
  const list=main.querySelector("#faqList");
  if(records.length)progressiveRender(list,records,cardHtml,{batchSize:6,label:`Loading ${records.length.toLocaleString()} cached responses`,token});
  else list.innerHTML='<div class="llm-empty">No cached RAG responses match this search.</div>';

  let timer=null;
  main.querySelector("#faqSearch").oninput=e=>{state.faqSearch=e.target.value;state.faqPage=1;persistPrefs();syncUrl({replace:true});clearTimeout(timer);timer=setTimeout(()=>{if(state.view==="faq")renderFaq(main)},280)};
  main.querySelector("#faqClearSearch")?.addEventListener("click",()=>{state.faqSearch="";state.faqPage=1;persistPrefs();syncUrl({replace:true});renderFaq(main)});
  main.querySelector("#faqGoRag").onclick=e=>{if(!e.currentTarget.disabled)navigateTo("rag")};
  main.querySelector("#faqGradeAll")?.addEventListener("click",gradeEveryFaqResponse);
  main.querySelector("#faqExpandAll")?.addEventListener("click",()=>{
    for(const record of records)state.faqExpanded[faqExpansionKey(record)]=true;
    list.querySelectorAll("details[data-faq-expand-key]").forEach(details=>details.open=true);
    persistPrefs();
  });
  main.querySelector("#faqCollapseAll")?.addEventListener("click",()=>{
    for(const record of records)delete state.faqExpanded[faqExpansionKey(record)];
    list.querySelectorAll("details[data-faq-expand-key]").forEach(details=>details.open=false);
    persistPrefs();
  });
  main.querySelector("#faqPrev").onclick=()=>{state.faqPage=Math.max(1,(state.faqPage||1)-1);persistPrefs();syncUrl({replace:true});renderFaq(main)};
  main.querySelector("#faqNext").onclick=()=>{state.faqPage=Math.min(pagesTotal,(state.faqPage||1)+1);persistPrefs();syncUrl({replace:true});renderFaq(main)};
  list.addEventListener("click",e=>{
    const rerun=e.target.closest("[data-faq-rerun]");
    if(rerun)return prepareRagRerun(records[+rerun.dataset.faqRerun]?.rag_request||{});
    const grade=e.target.closest("[data-faq-grade]");
    if(grade){const record=records[+grade.dataset.faqGrade];if(record)return gradeRagResponse({question:record.question||"",answer:record.text||"",evidence:Array.isArray(record.evidence)?record.evidence:[],responseRecordId:record.record_id||null,generationProvider:record.provider||null,generationModel:record.model||null})}
    const copy=e.target.closest("[data-copy-rag-record]");
    if(copy){const card=copy.closest("[data-faq-index]");const record=records[+card?.dataset.faqIndex];const evidence=Array.isArray(record?.evidence)?record.evidence[+copy.dataset.copyRagRecord]?.record:null;if(evidence)copyJsonToClipboard(evidence,evidence.record_id||"evidence record")}
  });
  list.addEventListener("toggle",e=>{
    const details=e.target.closest?.("details[data-faq-expand-key]");
    if(!details)return;
    if(details.open)state.faqExpanded[details.dataset.faqExpandKey]=true;
    else delete state.faqExpanded[details.dataset.faqExpandKey];
    persistPrefs();
  },true);
  decorateDisabledControls(main);
}

function ragAnswerHtml(text){
  const value=String(text||"").trim();
  if(!value)return '<div class="llm-empty">No answer returned.</div>';
  return value.split(/\n{2,}/).map(block=>{
    const trimmed=block.trim();
    if(!trimmed)return "";
    if(/^\*\*Works Cited\*\*/i.test(trimmed))return `<h3>Works Cited</h3>`;
    if(/^\d+\.\s/.test(trimmed))return `<div class="rag-bibliography">${trimmed.split(/\n/).map(line=>`<div>${esc(line)}</div>`).join("")}</div>`;
    return `<p>${esc(trimmed).replace(/\n/g,"<br>")}</p>`;
  }).join("");
}
function ragEvidencePreview(item,index){
  const record=item.record||{};
  const metadata=[
    ["Record ID",record.record_id],
    ["Work",record.work],
    ["Pages",pages(record)],
    ["Document author",record.document_author],
    ["Speaker",record.speaker],
    ["Position holder",record.position_holder],
    ["Stance",record.stance],
    ["Target",record.target],
    ["Role",record.discourse_role],
    ["Proposition status",record.proposition_status],
    ["Quoted speaker",record.quoted_speaker],
    ["Quoted author",record.quoted_author],
    ["Quoted work",record.quoted_work],
    ["Topics",record.topics],
    ["Concepts",record.concepts],
    ["Persons",record.persons],
  ].filter(([,value])=>value!==undefined&&value!==null&&display(value)!=="—");
  return `<details class="rag-evidence-card" ${index<3?"open":""}>
    <summary><span class="rag-evidence-id">[[${esc(item.evidence_id||`E${index}`)}]]</span><span class="rag-evidence-title"><b>${esc(record.record_id||`Record ${index+1}`)}</b><small>${esc(record.work||item.collection||"")} · ${esc(item.inline_citation||pages(record))}</small></span><span class="rag-evidence-score">${item.rerank_score==null?"":Number(item.rerank_score).toFixed(3)}</span></summary>
    <div class="rag-evidence-body">
      <div class="rag-evidence-meta">${metadata.map(([name,value])=>`<div><span>${esc(name)}</span><b>${esc(display(value))}</b></div>`).join("")}</div>
      <div class="rag-evidence-source"><span>Collection</span><b>${esc(item.collection||"")}</b><span>Full citation</span><b>${esc(item.full_citation||"")}</b></div>
      ${record._researcher_text_policy?`<div class="info researcher-evidence-policy">Researcher view · Edmundson extractive summary · ${Number(record._researcher_text_policy.source_chars||0).toLocaleString()} source characters · topics, concepts, and persons used as bonus terms.</div>`:""}
      <div class="tools"><button class="btn tiny" data-copy-rag-record="${index}">${icon("copy")}Copy ${record._researcher_text_policy?"summarized ":""}record</button></div>
      <pre>${esc(record.text||"")}</pre>
    </div>
  </details>`;
}
async function openRagResult(job){
  if(!job?.id)return toast(tr("research.result_unavailable","This Research run has no result identifier."),{tone:"warn"});
  if(!canAccessPage("rag"))return toast(tr("permissions.research_result_denied","Your role cannot open Research results."),{tone:"warn"});
  // v0.35.5: a RAG result is a research object, not a legacy modal. Open it in
  // the same native result workspace used by Research so typography, source
  // binding, evidence inspection, accessibility, and i18n stay identical no
  // matter where the result was launched (Operations, job history, etc.).
  state.view="rag";
  persistPrefs();
  shellRefreshHook?.();
  const href=`/rag?job=${encodeURIComponent(job.id)}`;
  if(urlSyncHook){urlSyncHook(href,{replace:false,snapshot:navSnapshot()});return}
  location.assign(href);
}
async function getResponseFaqPage({limit=50,offset=0,query=""}={}){
  if(!canAccessPage("faq"))throw new Error(tr("permissions.faq_denied","Your role cannot open Response Library."));
  const params=new URLSearchParams({limit:String(Math.max(1,Math.min(1000,Number(limit)||50))),offset:String(Math.max(0,Number(offset)||0))});
  const search=String(query||"").trim();
  if(search)params.set("query",search);
  return api(`/api/response-cache/records?${params}`);
}
function gradeResponseFaqRecord(record={}){
  return gradeRagResponse({
    question:record.question||"",
    answer:record.text||"",
    evidence:Array.isArray(record.evidence)?record.evidence:[],
    responseRecordId:record.record_id||null,
    generationProvider:record.provider||null,
    generationModel:record.model||null,
  });
}
function rerunResponseFaqRecord(record={}){
  return prepareRagRerun(record.rag_request||{});
}

function rememberRagPrompt(prompt,instructions,extra={}){
  const question=String(prompt||"").trim();
  const guidance=String(instructions||"").trim();
  if(!question&&!guidance)return;
  const history=Array.isArray(state.ragConfig.history)?state.ragConfig.history:[];
  const existing=history.findIndex(item=>
    String(item.prompt||"").trim()===question
    &&String(item.instructions||"").trim()===guidance
  );
  if(existing>=0)history.splice(existing,1);
  history.unshift({
    id:uid(),
    prompt:question,
    instructions:guidance,
    timestamp:new Date().toISOString(),
    source_collection:extra.source_collection||state.ragConfig.source_collection||"",
    provider:extra.provider||state.appConfig.chat_provider||"ollama",
    model:extra.model||"",
  });
  state.ragConfig.history=history.slice(0,100);
}
function rememberRagRun(job){
  if(!job?.id)return;
  const history=Array.isArray(state.ragConfig.run_history)?state.ragConfig.run_history:[];
  const existing=history.findIndex(item=>item.job_id===job.id);
  if(existing>=0)history.splice(existing,1);
  history.unshift({
    job_id:job.id,
    timestamp:job.created_at||new Date().toISOString(),
    provider:job.provider==="openai"?"openai":"ollama",
    model:job.model||"",
    source_collection:job.source_collection||state.ragConfig.source_collection||"",
    prompt:job.prompt||state.ragConfig.prompt||"",
  });
  state.ragConfig.run_history=history.slice(0,250);
}
function ragHistoryLabel(item){
  const prompt=String(item?.prompt||"").replace(/\s+/g," ").trim();
  return prompt.length>96?`${prompt.slice(0,93)}…`:(prompt||"(instructions only)");
}
async function removeRagJob(jobId){
  const job=state.jobs.find(item=>item.id===jobId);
  if(!job)return pruneClientJobState(jobId);
  if(["queued","running","cancelling"].includes(job.status))return toast("Cancel the RAG pipeline before removing it");
  const approved=await openMessageModal({
    title:"Remove RAG pipeline result?",
    message:`Remove this ${job.status} RAG pipeline and its retained result from activity history?`,
    tone:"danger",confirmLabel:"Remove pipeline",cancelLabel:"Cancel",
  });
  if(!approved)return;
  try{
    await api(`/api/jobs/${encodeURIComponent(jobId)}`,{method:"DELETE"});
    pruneClientJobState(jobId);persistPrefs();
    refreshRagProgressPanel();
    if(state.view==="home")refreshOperationsPanelOnly();
    toast("RAG pipeline removed");
  }catch(error){
    if(String(error?.message||"").includes("404")){pruneClientJobState(jobId);persistPrefs();refreshRagProgressPanel();return toast("RAG pipeline was already removed")}
    openMessageModal({title:"Could not remove RAG pipeline",message:error.message,tone:"danger"});
  }
}

async function clearFinishedRagJobs(){
  const finished=state.jobs.filter(job=>job.type==="rag"&&!["queued","running","cancelling"].includes(job.status));
  if(!finished.length)return toast("There are no past RAG results to clear");
  if(!await openMessageModal({title:"Clear past RAG results?",message:`Clear ${finished.length} finished RAG operation${finished.length===1?"":"s"} and their retained results?`,tone:"danger",confirmLabel:"Clear results",cancelLabel:"Cancel"}))return;
  let removed=0,failed=0;
  for(const job of finished){
    try{
      await api(`/api/jobs/${encodeURIComponent(job.id)}`,{method:"DELETE"});
      pruneClientJobState(job.id);
      removed++;
    }catch(error){
      failed++;
      console.warn("Could not remove RAG job",job.id,error);
    }
  }
  await refreshJobs();
  refreshRagProgressPanel();
  toast(`Cleared ${removed} past RAG result${removed===1?"":"s"}${failed?` · ${failed} could not be removed`:""}`);
}

const RAG_STAGE_ORDER=[
  ["query_metadata","Query decomposition"],
  ["retrieval","Vector retrieval"],
  ["deduplicate","Deduplication / rank fusion"],
  ["rerank","Reranking"],
  ["context","Evidence packaging"],
  ["generation","Answer generation"],
  ["bind_sources","Citation/source binding"],
  ["response_cache","Response cache"],
  ["auto_grade","Automatic grade"],
];
function ragProgressPanelHtml(){
  const allRagJobs=state.jobs.filter(job=>job.type==="rag");
  const jobs=allRagJobs.slice(0,12);
  const activeCount=allRagJobs.filter(job=>["queued","running","cancelling"].includes(job.status)).length;
  const finishedCount=allRagJobs.length-activeCount;
  return `<section class="card rag-live-panel" id="ragProgressPanel">
    <div class="cardhead"><div><b>RAG pipeline activity</b><div class="note">${activeCount} active · ${finishedCount} past result${finishedCount===1?"":"s"} · stage, model, parameters, and timing refresh automatically</div></div><div class="tools"><button class="btn small" id="ragRefreshJobs">${icon("refresh")}Refresh</button>${finishedCount?'<button class="btn small danger" id="ragClearFinished">Clear past results</button>':""}</div></div>
    <div class="rag-live-jobs">${jobs.map(job=>{
      const active=["queued","running","cancelling"].includes(job.status);
      const request=job.request||{};
      const stageOrder=RAG_STAGE_ORDER.filter(([stage])=>stage!=="auto_grade"||request.auto_grade);
      const stageIndex=stageOrder.findIndex(([stage])=>stage===job.stage);
      const generation=request.generation||{};
      const elapsed=humanDuration(jobElapsedSeconds(job));
      const totalLabel=job.finished_at?`Total ${elapsed}`:`Elapsed ${elapsed}`;
      const sourceStore=state.stores.find(store=>store.name===job.source_collection);
      const stageEvents=(job.events||[]).filter(event=>event.stage===job.stage&&event.timestamp);
      const stageStart=stageEvents.length?new Date(stageEvents[0].timestamp).getTime():null;
      const stageElapsed=Number.isFinite(stageStart)?humanDuration(Math.max(0,(Date.now()-stageStart)/1000)):"—";
      const params=[
        `started by ${job.owner||"—"}`,
        `provider ${job.provider||"—"}`,
        `generation ${job.model||"—"}`,
        `embedding ${sourceStore?.embedding_model||sourceStore?.embedding_provider||"—"}`,
        `reranker model ${request.cross_encoder_model||request.reranker||"—"}`,
        `languages ${(request.locales||[]).join("+")||"—"}`,
        `retrieval ${(request.search_types||[]).join("+")||"—"}`,
        `k ${request.k??"—"}`,
        `fetch ${request.fetch_k??"—"}`,
        `λ ${request.lambda_mult??"—"}`,
        `RRF ${request.rrf_k??"—"}`,
        `topN ${request.rerank_top_n??"—"}`,
        `auto-grade ${request.auto_grade?"on":"off"}`,
        `num_ctx ${generation.num_ctx??"—"}`,
        `num_predict ${generation.num_predict??"—"}`,
        job.provider==="openai"
          ?"scheduler uncapped"
          :`scheduler ${job.scheduling?.active_when_started??state.health?.rag_concurrency?.ollama_active??"—"}/${job.scheduling?.limit??state.appConfig.ollama_rag_concurrency??1}`,
        `stage time ${stageElapsed}`,
      ];
      return `<article class="rag-live-job">
        <div class="rag-live-job-head"><div><b>${esc(job.prompt||"RAG query")}</b><span>${esc(job.source_collection||"")} · ${esc(job.model||job.provider||"")} · ${esc(totalLabel)}</span></div><span class="job-status ${esc(job.status)}">${esc(job.status)}</span></div>
        <div class="rag-live-params">${params.map(value=>`<span>${esc(value)}</span>`).join("")}</div>
        <div class="rag-stage-rail">${stageOrder.map(([stage,name],index)=>{
          const done=job.status==="completed"||index<stageIndex;
          const current=active&&index===stageIndex;
          return `<div class="rag-stage-node ${done?"done":""} ${current?"current":""}"><i>${done?"✓":index+1}</i><div><b>${esc(name)}</b><span>${current?esc(job.stage_detail||"Running…"):done?"Complete":"Pending"}</span></div></div>`;
        }).join("")}</div>
        <div class="rag-live-detail">${job.status==="cancelling"||job.cancel_requested?"Cancellation requested · waiting for the current pipeline call to reach a safe checkpoint.":esc(job.stage_detail||job.fatal_error||"Queued")}</div>
        <div class="rag-live-footer"><div class="rag-live-timing"><span>${esc(totalLabel)}</span><span>${job.started_at?`Started ${esc(formatTimestamp(job.started_at))}`:"Not started"}</span>${job.finished_at?`<span>Finished ${esc(formatTimestamp(job.finished_at))}</span>`:""}</div><div class="tools"><button class="btn small" data-rag-job-details="${job.id}">Details / timeline</button>${job.status==="completed"?`<button class="btn small primary" data-rag-job-result="${job.id}">Open result</button>`:""}${active?(job.cancel_requested||job.status==="cancelling"?'<button class="btn small" disabled>Cancelling…</button>':`<button class="btn small danger" data-rag-job-cancel="${job.id}">Cancel</button>`):`<button class="btn small danger" data-rag-job-remove="${job.id}">Remove</button>`}</div></div>
      </article>`;
    }).join("")||'<div class="llm-empty">No RAG jobs yet. Start one below.</div>'}</div>
  </section>`;
}

function wireRagProgressPanel(){
  const panel=document.querySelector("#ragProgressPanel");
  if(!panel)return;
  panel.querySelector("#ragRefreshJobs")?.addEventListener("click",()=>refreshJobs());
  panel.querySelector("#ragClearFinished")?.addEventListener("click",clearFinishedRagJobs);
  panel.querySelectorAll("[data-rag-job-details]").forEach(button=>button.onclick=()=>openJobDetails(button.dataset.ragJobDetails));
  panel.querySelectorAll("[data-rag-job-result]").forEach(button=>button.onclick=()=>openJobResults(button.dataset.ragJobResult));
  panel.querySelectorAll("[data-rag-job-cancel]").forEach(button=>button.onclick=()=>cancelBackgroundJob(button.dataset.ragJobCancel));
  panel.querySelectorAll("[data-rag-job-remove]").forEach(button=>button.onclick=()=>removeRagJob(button.dataset.ragJobRemove));
}
function refreshRagProgressPanel(){
  const current=document.querySelector("#ragProgressPanel");
  if(!current)return;
  const holder=document.createElement("div");
  holder.innerHTML=ragProgressPanelHtml();
  const replacement=holder.firstElementChild;
  if(replacement)current.replaceWith(replacement);
  wireRagProgressPanel();
}
async function renderRag(main){
  try{await refreshStores()}catch(error){
    main.innerHTML=`<div class="info warn">Could not load Chroma collections: ${esc(error.message)}</div>`;
    return;
  }
  const cfg=state.ragConfig;
  const corpusStores=recordStores();
  const selectedEvidenceCount=selectedEvidenceEntries().length;
  const hasRetrievalDb=hasCorpusDb();
  if(!hasRetrievalDb&&!selectedEvidenceCount){
    const reason=dbUnavailableReason();
    main.innerHTML=`<section class="empty db-required-empty"><div class="drop"><div class="drop-icon">${icon("database")}</div><h1>Vector database or selected evidence required</h1><p>${esc(reason)} Retrieval-based RAG needs a corpus collection. An administrator can also select loaded records as evidence and run an evidence-only pipeline without Chroma retrieval.</p>${isResearcher()?'<div class="info">Ask an administrator to create or populate a corpus vector database.</div>':`<button class="btn primary" id="ragOpenVector">${icon("database")}Open Vector Stores</button>`}</div></section>`;
    document.querySelector("#ragOpenVector")?.addEventListener("click",()=>navigateTo("vector"));
    return;
  }
  if(!selectedEvidenceCount)cfg.skip_retrieval=false;
  else if(!hasRetrievalDb)cfg.skip_retrieval=true;
  const usable=corpusStores.filter(store=>Number(store.count||0)>0);
  if(!cfg.source_collection||!corpusStores.some(store=>store.name===cfg.source_collection)){
    cfg.source_collection=(usable.find(store=>store.collection_role==="primary")||usable[0]||corpusStores[0]||{}).name||"";
  }

  const profiles=providerProfiles();
  const preferredProfileId=cfg.provider_profile_id||state.appConfig.default_provider_profile||defaultProviderProfile()?.id||"";
  if(profiles.length&&!profiles.some(item=>item.id===preferredProfileId)){
    // A researcher can inherit an admin-only profile id from old browser prefs.
    // Normalize it before rendering so the visible selection and submitted id
    // always refer to the same administrator-approved static profile.
    cfg.provider_profile_id=profiles[0].id;
  }
  const profileId=cfg.provider_profile_id||preferredProfileId||profiles[0]?.id||"";
  const profile=providerProfile(profileId);
  const provider=profile?.type||"ollama";
  const alternativeGradeProfile=profiles.find(item=>item.id!==profileId)||profile;
  if(!cfg.auto_grade_provider_profile_id||!profiles.some(item=>item.id===cfg.auto_grade_provider_profile_id)){
    cfg.auto_grade_provider_profile_id=alternativeGradeProfile?.id||profileId;
  }
  // Prefer an independent grader whenever another configured provider exists.
  if(cfg.auto_grade_provider_profile_id===profileId&&profiles.some(item=>item.id!==profileId)){
    cfg.auto_grade_provider_profile_id=profiles.find(item=>item.id!==profileId)?.id||profileId;
  }
  const autoGradeProfile=providerProfile(cfg.auto_grade_provider_profile_id);
  let providerStatus=state.providerStatuses?.[profileId]||null;
  if(isResearcher()){
    // Researcher profiles are static, administrator-approved profiles. Do not
    // probe arbitrary provider endpoints from the browser; the server resolves
    // secrets and queues local-model work against each profile's concurrency.
    providerStatus={provider,available:Boolean(profile),models:profile?.model?[{name:profile.model}]:[],error:profile?null:"No researcher LLM profile is configured."};
  }else if(!providerStatus){
    try{
      providerStatus=await api("/api/llm/status",{
        method:"POST",
        body:JSON.stringify({
          provider,
          base_url:profile?.base_url||null,
          api_key:provider==="openai"?(profile?.api_key||""):null,
        }),
      });
      state.providerStatuses[profileId]=providerStatus;
    }catch(error){providerStatus={provider,available:false,models:[],error:error.message}}
  }
  const defaultModel=provider==="openai"&&profile?.model_mode==="auto"
    ?"auto"
    :(profile?.model||(provider==="ollama"?"gemma4:e2b":"auto"));
  const discoveredModels=(providerStatus?.models||[]).map(item=>item.name).filter(Boolean);
  const filteredDiscovered=provider==="openai"
    ? discoveredModels.filter(name=>openAiModelMatchesKind(name,profile?.model_kind||"any"))
    : discoveredModels;

  const gen=provider==="openai"
    ? {
        num_predict:profile?.num_predict??4096,
        temperature:profile?.temperature??0,
        top_p:profile?.top_p??1,
        seed:profile?.seed??"",
        extra_options:profile?.extra_options||"{}",
      }
    : {
        num_ctx:profile?.num_ctx??16384,
        num_predict:profile?.num_predict??4096,
        think:profile?.think??"false",
        temperature:profile?.temperature??0,
        top_k:profile?.top_k??0,
        top_p:profile?.top_p??1,
        min_p:profile?.min_p??"",
        repeat_penalty:profile?.repeat_penalty??1.1,
        seed:profile?.seed??"",
        mirostat:profile?.mirostat??0,
        mirostat_eta:profile?.mirostat_eta??"",
        mirostat_tau:profile?.mirostat_tau??"",
        keep_alive:profile?.keep_alive||"10m",
        extra_options:profile?.extra_options||"{}",
      };

  main.innerHTML=`<div class="rag-page research-page-0309">
    <section class="research-hero"><div><span class="section-label">${esc(tr("nav.rag","Research"))}</span><h1>${esc(tr("research.workspace_title","Evidence-grounded research workspace"))}</h1><p>${esc(tr("research.workspace_help","Build a question, choose retrieval and generation settings, pin evidence, then run the full provenance-aware pipeline."))}</p></div><div class="research-hero-status"><span>${selectedEvidenceEntries().length.toLocaleString()} ${esc(tr("rag.selected_evidence","selected evidence"))}</span><span>${corpusStores.length.toLocaleString()} ${esc(tr("dashboard.databases","databases"))}</span></div></section><div class="rag-runner-page">
      <section class="card rag-runner-main">
        <div class="cardhead research-pipeline-head"><div><b>${esc(tr("research.pipeline_title","Research pipeline"))}</b><div class="note">${esc(tr("research.pipeline_help","Configure the corpus, retrieval, evidence, and generation stages. Advanced controls stay available without competing with the primary question workflow."))}</div></div></div>

        <div class="research-context-bar" aria-label="Research run context">
          <span><b>${esc(tr("research.database","Database"))}</b>${esc(cfg.source_collection||tr("research.selected_evidence_only","Selected evidence only"))}</span>
          <span><b>${esc(tr("research.generation","Generation"))}</b>${esc(providerDisplayName(profile))} · ${esc(defaultModel)}</span>
          <span><b>${esc(tr("rag.selected_evidence","Selected evidence"))}</b>${selectedEvidenceEntries().length.toLocaleString()}</span>
          <span><b>${esc(tr("research.retrieval","Retrieval"))}</b>${cfg.skip_retrieval?esc(tr("rag.skip_retrieval_short","Evidence only")):esc(cfg.search_types.join(" + "))}</span>
        </div>

        <section class="rag-memory research-composer card-inset">
          <div class="rag-result-section-head"><div><b>Question & instructions</b><div class="note">Drafts persist across navigation and browser refresh. The 40 most recent submitted question/instruction pairs are retained locally.</div></div><div class="tools">${cfg.history?.length?'<button class="btn small" id="clearRagHistory">Clear remembered questions</button>':""}</div></div>
          ${cfg.history?.length?`<div class="rag-history-recall"><select class="control" id="ragHistorySelect"><option value="">Recall a previous question…</option>${cfg.history.map(item=>`<option value="${esc(item.id)}">${esc(ragHistoryLabel(item))}</option>`).join("")}</select><button class="btn" id="loadRagHistory" disabled>Load</button></div>`:""}
          <div class="field"><label>Research question / prompt</label><textarea id="ragPrompt" class="rag-prompt" placeholder="Ask a research question about Derrida…">${esc(cfg.prompt||"")}</textarea></div>
          <div class="field"><div class="field-label-row"><label>Additional instructions</label>${cfg.instructions?'<button class="btn tiny" id="clearRagInstructions" type="button">Clear instructions</button>':""}</div><textarea id="ragInstructions" placeholder="Optional constraints on the answer; kept separate from the research question.">${esc(cfg.instructions||"")}</textarea></div>
        </section>

        <section class="rag-selected-evidence card-inset">
          <div class="rag-result-section-head"><div><b>${esc(tr("rag.selected_evidence","Selected evidence"))}</b><div class="note">Records selected across corpus tables are pinned into this run. You can also bypass retrieval entirely and answer only from this evidence packet.</div></div><div class="tools"><span class="badge">${selectedEvidenceEntries().length}</span>${selectedEvidenceEntries().length&&hasCapability("evidence.select")?'<button class="btn tiny" id="ragClearEvidence">Clear</button>':""}</div></div>
          ${selectedEvidenceEntries().length?`<div class="rag-selected-evidence-list">${selectedEvidenceEntries().map(item=>`<span class="selected-evidence-chip" data-selected-evidence-key="${esc(item.key)}"><b>${esc(item.record_id||"Record")}</b><small>${esc(item.work||item.collection||"")}</small>${hasCapability("evidence.select")?`<button class="chip-remove" data-remove-evidence="${esc(item.key)}" title="Remove evidence">×</button>`:""}</span>`).join("")}</div>`:'<div class="note">No evidence selected yet. Use “Add to evidence” on record/search rows.</div>'}
          <label class="check-item selected-evidence-only"><input type="checkbox" id="ragSkipRetrieval" ${cfg.skip_retrieval?"checked":""} ${selectedEvidenceEntries().length?"":"disabled"}><span>${esc(tr("rag.skip_retrieval","Use selected evidence only (skip retrieval)"))}</span></label>
        </section>

        <details class="research-settings-drawer">
          <summary><span><b>${esc(tr("research.retrieval_settings","Retrieval & evidence settings"))}</b><small>${esc(cfg.source_collection||tr("research.no_database","No database"))} · k ${cfg.k} · ${esc(cfg.reranker)}</small></span><span aria-hidden="true">⌄</span></summary>
        <section class="rag-options card-inset research-settings-body">
          <div class="rag-result-section-head"><div><b>${esc(tr("research.corpus_retrieval","Corpus and retrieval"))}</b><div class="note">${esc(tr("research.corpus_retrieval_help","Language routing, retrieval depth, reranking, citation binding, and grading."))}</div></div></div>
          <div class="rag-config-grid">
            <div class="field"><label>Source collection</label><select class="control" id="ragSource" ${hasRetrievalDb?"":"disabled"}>${hasRetrievalDb?recordStores().map(store=>`<option value="${esc(store.name)}" ${store.name===cfg.source_collection?"selected":""}>${esc(store.name)} · ${Number(store.count||0).toLocaleString()} records · ${esc(store.collection_role||"general")}</option>`).join(""):'<option value="">Selected evidence only · retrieval disabled</option>'}</select></div>
            <div class="field"><label>Reranker</label><select class="control" id="ragReranker"><option value="cross_encoder" ${cfg.reranker==="cross_encoder"?"selected":""}>Cross-encoder</option><option value="lexical" ${cfg.reranker==="lexical"?"selected":""}>Lexical/vector fallback</option><option value="none" ${cfg.reranker==="none"?"selected":""}>No reranking</option></select></div>
            <div class="field"><label>Response language</label><select class="control" id="ragResponseLanguage"><option value="auto" ${cfg.response_language==="auto"?"selected":""}>Auto</option><option value="en" ${cfg.response_language==="en"?"selected":""}>English</option><option value="fr" ${cfg.response_language==="fr"?"selected":""}>French</option></select></div>
            <div class="field"><label>Cross-encoder model</label><input class="control" id="ragCrossEncoder" value="${esc(cfg.cross_encoder_model)}"></div>
          </div>
          <div class="rag-option-section"><b>Document languages</b><div class="language-checks">${["en","fr"].map(code=>`<label><input type="checkbox" data-rag-locale="${code}" ${cfg.locales.includes(code)?"checked":""}><span>${code}</span></label>`).join("")}</div></div>
          <div class="rag-option-section"><b>Retrieval routes</b><div class="language-checks">${[["similarity","Similarity"],["lexical","Lexical (BM25)"],["mmr","MMR"]].map(([value,name])=>`<label><input type="checkbox" data-rag-search="${value}" ${cfg.search_types.includes(value)?"checked":""}><span>${name}</span></label>`).join("")}</div></div>
          <div class="rag-number-grid rag-number-grid-wide">
            <div class="field"><label>k</label><input class="control" id="ragK" type="number" min="1" max="500" value="${cfg.k}"></div>
            <div class="field"><label>fetch_k</label><input class="control" id="ragFetchK" type="number" min="1" max="5000" value="${cfg.fetch_k}"></div>
            <div class="field"><label>MMR λ</label><input class="control" id="ragLambda" type="number" min="0" max="1" step="0.05" value="${cfg.lambda_mult}"></div>
            <div class="field"><label>RRF k</label><input class="control" id="ragRrfK" type="number" min="1" value="${cfg.rrf_k??60}"></div>
            <div class="field"><label>Rerank top N</label><input class="control" id="ragRerankTop" type="number" min="1" max="500" value="${cfg.rerank_top_n}"></div>
            <div class="field"><label>Decomposition max tokens</label><input class="control" id="ragDecomposePredict" type="number" min="64" value="${cfg.query_decomposition_num_predict??768}"></div>
            <div class="field"><label>Chars / evidence record</label><input class="control" id="ragRecordChars" type="number" min="500" value="${cfg.evidence_record_char_limit??12000}"></div>
            <div class="field"><label>Total evidence chars</label><input class="control" id="ragTotalChars" type="number" min="5000" value="${cfg.evidence_total_char_limit??120000}"></div>
          </div>
          <div class="rag-toggle-grid">
            <label class="check-item"><input type="checkbox" id="ragDecompose" ${cfg.query_decomposition?"checked":""}><span>LLM query decomposition + French query formulation</span></label>
            <label class="check-item"><input type="checkbox" id="ragBind" ${cfg.bind_citations?"checked":""}><span>Bind evidence tags to citations <small>Default: [[E0]]; also accepts (), [], {}, and doubled wrappers.</small></span></label>
            <label class="check-item"><input type="checkbox" id="ragWorksCited" ${cfg.include_works_cited?"checked":""}><span>Append Works Cited</span></label>
            <label class="check-item"><input type="checkbox" id="ragAutoGrade" ${cfg.auto_grade?"checked":""}><span>Auto-grade final response as the last pipeline step <small>Saved to Response Library when caching succeeds.</small></span></label>
          </div>
          <div class="rag-auto-grade-config ${cfg.auto_grade?"":"disabled-section"}">
            <div class="field"><label>Auto-grade provider profile</label><select class="control" id="ragAutoGradeProvider" ${cfg.auto_grade?"":"disabled"}>${profiles.map(p=>`<option value="${esc(p.id)}" ${p.id===cfg.auto_grade_provider_profile_id?"selected":""}>${esc(providerDisplayName(p))} · ${esc(p.model||"auto")}${p.id===profileId?" · generation provider":""}</option>`).join("")}</select></div>
            <div class="note">When more than one provider profile is configured, DerridAI defaults grading to a profile different from answer generation.</div>
          </div>
        </section></details>

        <section class="rag-options card-inset research-generation-card">
          <div class="rag-result-section-head"><div><b>${esc(tr("research.generation_provider","Generation provider"))}</b><div class="note">${esc(tr("research.generation_provider_help","Choose the approved provider and model for this run. Fine tuning stays out of the way until needed."))}</div></div></div>
          <div class="rag-config-grid">
            <div class="field"><label>Provider profile</label><select class="control" id="ragProvider">${profiles.map(p=>`<option value="${esc(p.id)}" ${p.id===profileId?"selected":""}>${esc(providerDisplayName(p))} · ${p.type==="ollama"?"Ollama":"OpenAI-compatible"}</option>`).join("")}</select></div>
            ${provider==="openai"?`<div class="field"><label>Model selection mode</label><select class="control" id="ragOpenaiMode"><option value="auto" ${profile?.model_mode==="auto"?"selected":""}>Auto router</option><option value="discovered" ${profile?.model_mode==="discovered"?"selected":""}>Discovered model</option><option value="manual" ${profile?.model_mode==="manual"?"selected":""}>Manual model ID</option></select></div><div class="field"><label>Model kind</label><select class="control" id="ragOpenaiKind"><option value="any" ${profile?.model_kind==="any"?"selected":""}>Any</option><option value="general" ${profile?.model_kind==="general"?"selected":""}>General/chat</option><option value="reasoning" ${profile?.model_kind==="reasoning"?"selected":""}>Reasoning</option><option value="coding" ${profile?.model_kind==="coding"?"selected":""}>Coding</option><option value="fast" ${profile?.model_kind==="fast"?"selected":""}>Fast/small</option></select></div>`:""}
            <div class="field"><label>Generation model</label>${provider==="openai"&&profile?.model_mode==="discovered"
              ? `<select class="control" id="ragModel">${filteredDiscovered.map(name=>`<option value="${esc(name)}" ${name===defaultModel?"selected":""}>${esc(name)}</option>`).join("")||`<option value="${esc(defaultModel)}">${esc(defaultModel)}</option>`}</select>`
              : `<input class="control" id="ragModel" list="rag-model-options" autocomplete="off" value="${esc(defaultModel)}" ${provider==="openai"&&profile?.model_mode==="auto"?"disabled":""}><datalist id="rag-model-options">${filteredDiscovered.map(name=>`<option value="${esc(name)}"></option>`).join("")}</datalist>`
            }</div>
          </div>

          <details class="research-generation-advanced"><summary><span><b>${esc(tr("research.advanced_generation","Advanced generation parameters"))}</b><small>${esc(tr("research.advanced_generation_help","Context, sampling, token limits, and provider-specific options"))}</small></span><span aria-hidden="true">⌄</span></summary>
          ${provider==="ollama"?`<div class="rag-generation-grid">
            <div class="field"><label>num_ctx</label><input class="control" id="ragNumCtx" type="number" min="512" value="${esc(gen.num_ctx)}"></div>
            <div class="field"><label>num_predict</label><input class="control" id="ragNumPredict" type="number" min="16" value="${esc(gen.num_predict)}"></div>
            <div class="field"><label>Think</label><select class="control" id="ragThink">${[["false","Off"],["true","On"],["low","Low"],["medium","Medium"],["high","High"]].map(([value,name])=>`<option value="${value}" ${String(gen.think)===value?"selected":""}>${name}</option>`).join("")}</select></div>
            <div class="field"><label>Temperature</label><input class="control" id="ragTemperature" type="number" step="0.01" min="0" max="2" value="${esc(gen.temperature)}"></div>
            <div class="field"><label>top_k</label><input class="control" id="ragTopK" type="number" min="0" value="${esc(gen.top_k)}"></div>
            <div class="field"><label>top_p</label><input class="control" id="ragTopP" type="number" step="0.01" min="0" max="1" value="${esc(gen.top_p)}"></div>
            <div class="field"><label>min_p</label><input class="control" id="ragMinP" type="number" step="0.01" min="0" max="1" value="${esc(gen.min_p)}"></div>
            <div class="field"><label>repeat_penalty</label><input class="control" id="ragRepeatPenalty" type="number" step="0.01" value="${esc(gen.repeat_penalty)}"></div>
            <div class="field"><label>seed</label><input class="control" id="ragSeed" type="number" value="${esc(gen.seed)}"></div>
            <div class="field"><label>mirostat</label><select class="control" id="ragMirostat">${[0,1,2].map(v=>`<option value="${v}" ${Number(gen.mirostat||0)===v?"selected":""}>${v}</option>`).join("")}</select></div>
            <div class="field"><label>mirostat_eta</label><input class="control" id="ragMirostatEta" type="number" step="0.01" value="${esc(gen.mirostat_eta)}"></div>
            <div class="field"><label>mirostat_tau</label><input class="control" id="ragMirostatTau" type="number" step="0.01" value="${esc(gen.mirostat_tau)}"></div>
            <div class="field"><label>keep_alive</label><input class="control" id="ragKeepAlive" value="${esc(gen.keep_alive)}"></div>
            <div class="field field-full"><label>Advanced Ollama options JSON</label><textarea id="ragExtraOptions" spellcheck="false">${esc(gen.extra_options)}</textarea></div>
          </div>`:`<div class="rag-generation-grid">
            <div class="field"><label>Max output tokens</label><input class="control" id="ragNumPredict" type="number" min="16" value="${esc(gen.num_predict)}"></div>
            <div class="field"><label>Temperature</label><input class="control" id="ragTemperature" type="number" step="0.01" min="0" max="2" value="${esc(gen.temperature)}"></div>
            <div class="field"><label>top_p</label><input class="control" id="ragTopP" type="number" step="0.01" min="0" max="1" value="${esc(gen.top_p)}"></div>
            <div class="field"><label>seed</label><input class="control" id="ragSeed" type="number" value="${esc(gen.seed)}"></div>
            <div class="field field-full"><label>Advanced OpenAI-compatible options JSON</label><textarea id="ragExtraOptions" spellcheck="false">${esc(gen.extra_options)}</textarea></div>
          </div>`}
          </details>
        </section>

        ${provider==="openai"?`<div class="info">${providerStatus?.available?`${filteredDiscovered.length} discovered model${filteredDiscovered.length===1?"":"s"} match the current model-kind filter.`:`Model discovery unavailable: ${esc(providerStatus?.error||"unknown error")}. Auto/manual model IDs can still be used if the endpoint supports them.`}</div>`:""}
        <div class="info">When <code>${esc(cfg.source_collection||"a primary collection")}_en</code> or <code>_fr</code> exists, RAG uses the matching language collection. Missing requested languages fall back to the source collection and are filtered by <code>document_language(s)</code>.</div>
        <div class="config-actions research-run-bar"><div class="research-run-summary"><b>${esc(tr("research.ready_to_run","Ready to research"))}</b><small>${selectedEvidenceCount.toLocaleString()} ${esc(tr("rag.selected_evidence","selected evidence"))} · ${esc(providerDisplayName(profile))}</small></div><button class="btn primary" id="runRag" ${hasCapability("rag.run")&&((usable.length||selectedEvidenceCount)&&profiles.length)?"":`disabled data-disabled-reason="${esc(!hasCapability("rag.run")?tr("permissions.rag_denied","Your role cannot run Research pipelines."):(!(usable.length||selectedEvidenceCount)?"Create/populate a corpus vector database or select evidence before running RAG.":"An administrator must configure at least one researcher LLM profile."))}"`}>${icon("spark")}Run RAG pipeline in background</button>${isResearcher()?"":`<button class="btn" id="ragDashboard">${icon("dashboard")}Operations dashboard</button>`}</div>
      </section>
    </div>

    ${ragProgressPanelHtml()}
  </div>`;

  wireRagProgressPanel();

  const ragPromptInput=document.querySelector("#ragPrompt");
  const ragInstructionsInput=document.querySelector("#ragInstructions");
  let ragDraftTimer=null;
  const persistRagDraft=()=>{
    cfg.prompt=ragPromptInput?.value||"";
    cfg.instructions=ragInstructionsInput?.value||"";
    clearTimeout(ragDraftTimer);
    ragDraftTimer=setTimeout(()=>persistPrefs(),250);
  };
  ragPromptInput?.addEventListener("input",persistRagDraft);
  ragInstructionsInput?.addEventListener("input",persistRagDraft);

  const historySelect=document.querySelector("#ragHistorySelect");
  const historyLoad=document.querySelector("#loadRagHistory");
  historySelect?.addEventListener("change",()=>{if(historyLoad)historyLoad.disabled=!historySelect.value});
  historyLoad?.addEventListener("click",()=>{
    const item=(cfg.history||[]).find(entry=>entry.id===historySelect.value);
    if(!item)return;
    cfg.prompt=String(item.prompt||"");
    cfg.instructions=String(item.instructions||"");
    if(ragPromptInput)ragPromptInput.value=cfg.prompt;
    if(ragInstructionsInput)ragInstructionsInput.value=cfg.instructions;
    persistPrefs();
    toast("Restored remembered RAG question and instructions");
  });
  document.querySelector("#clearRagHistory")?.addEventListener("click",async()=>{
    if(!await openMessageModal({title:"Clear remembered RAG prompts?",message:"Clear remembered RAG questions and instructions? Running/completed RAG operations are unaffected.",tone:"danger",confirmLabel:"Clear prompts",cancelLabel:"Cancel"}))return;
    cfg.history=[];
    persistPrefs();
    renderRag(main);
  });
  document.querySelector("#clearRagInstructions")?.addEventListener("click",()=>{
    cfg.instructions="";
    if(ragInstructionsInput)ragInstructionsInput.value="";
    persistPrefs();
    toast("RAG instructions cleared");
  });

  const n=(id,fallback=null)=>{
    const value=document.querySelector(`#${id}`)?.value?.trim();
    if(value===""||value==null)return fallback;
    const parsed=Number(value);
    return Number.isFinite(parsed)?parsed:fallback;
  };
  const persistRag=()=>{
    cfg.prompt=ragPromptInput?.value||cfg.prompt||"";
    cfg.instructions=ragInstructionsInput?.value||cfg.instructions||"";
    cfg.source_collection=document.querySelector("#ragSource")?.value||"";
    cfg.locales=[...document.querySelectorAll("[data-rag-locale]:checked")].map(box=>box.dataset.ragLocale);
    cfg.search_types=[...document.querySelectorAll("[data-rag-search]:checked")].map(box=>box.dataset.ragSearch);
    cfg.k=Math.max(1,n("ragK",64));
    cfg.fetch_k=Math.max(cfg.k,n("ragFetchK",500));
    cfg.lambda_mult=Math.max(0,Math.min(1,n("ragLambda",0.7)));
    cfg.rrf_k=Math.max(1,n("ragRrfK",60));
    cfg.rerank_top_n=Math.max(1,n("ragRerankTop",24));
    cfg.reranker=document.querySelector("#ragReranker").value;
    cfg.cross_encoder_model=document.querySelector("#ragCrossEncoder").value.trim()||"cross-encoder/ms-marco-MiniLM-L-6-v2";
    cfg.query_decomposition=document.querySelector("#ragDecompose").checked;
    cfg.query_decomposition_num_predict=Math.max(64,n("ragDecomposePredict",768));
    cfg.response_language=document.querySelector("#ragResponseLanguage").value;
    cfg.evidence_record_char_limit=Math.max(500,n("ragRecordChars",12000));
    cfg.evidence_total_char_limit=Math.max(5000,n("ragTotalChars",120000));
    cfg.bind_citations=document.querySelector("#ragBind").checked;
    cfg.include_works_cited=document.querySelector("#ragWorksCited").checked;
    cfg.auto_grade=document.querySelector("#ragAutoGrade").checked;
    cfg.skip_retrieval=Boolean(document.querySelector("#ragSkipRetrieval")?.checked);
    cfg.auto_grade_provider_profile_id=document.querySelector("#ragAutoGradeProvider")?.value||cfg.auto_grade_provider_profile_id||"";
    persistPrefs();
  };

  document.querySelectorAll("#ragSource,#ragReranker,#ragK,#ragFetchK,#ragLambda,#ragRrfK,#ragRerankTop,#ragCrossEncoder,#ragDecompose,#ragDecomposePredict,#ragResponseLanguage,#ragRecordChars,#ragTotalChars,#ragBind,#ragWorksCited,#ragAutoGrade,#ragAutoGradeProvider,#ragSkipRetrieval,[data-rag-locale],[data-rag-search]").forEach(control=>control.addEventListener("change",persistRag));
  document.querySelector("#ragAutoGrade")?.addEventListener("change",()=>renderRag(main));
  document.querySelector("#ragClearEvidence")?.addEventListener("click",()=>{clearSelectedEvidence();renderRag(main)});
  document.querySelectorAll("[data-remove-evidence]").forEach(button=>button.addEventListener("click",()=>{setEvidence(button.dataset.removeEvidence,null,false);renderRag(main)}));

  // Static researcher profiles define model and generation settings. Researchers
  // may choose among profiles, but cannot mutate the administrator-owned config.
  if(isResearcher()){
    const lockedIds=["ragModel","ragOpenaiMode","ragOpenaiKind","ragNumCtx","ragNumPredict","ragThink","ragTemperature","ragTopK","ragTopP","ragMinP","ragRepeatPenalty","ragSeed","ragMirostat","ragMirostatEta","ragMirostatTau","ragKeepAlive","ragExtraOptions"];
    lockedIds.forEach(id=>{const control=document.querySelector(`#${id}`);if(control){control.disabled=true;control.title="This setting is fixed by the administrator-approved researcher profile."}});
  }

  document.querySelector("#ragProvider").onchange=e=>{
    persistRagDraft();
    cfg.provider_profile_id=e.target.value;
    if(cfg.auto_grade_provider_profile_id===cfg.provider_profile_id){
      cfg.auto_grade_provider_profile_id=profiles.find(item=>item.id!==cfg.provider_profile_id)?.id||cfg.provider_profile_id;
    }
    persistPrefs();renderRag(main);
  };
  document.querySelector("#ragOpenaiMode")?.addEventListener("change",e=>{
    persistRagDraft();
    if(profile){
      profile.model_mode=e.target.value;
      if(e.target.value==="auto")profile.model="auto";
    }
    persistPrefs();renderRag(main);
  });
  document.querySelector("#ragOpenaiKind")?.addEventListener("change",e=>{
    persistRagDraft();
    if(profile)profile.model_kind=e.target.value;
    persistPrefs();renderRag(main);
  });
  document.querySelector("#ragDashboard")?.addEventListener("click",()=>navigateTo("home"));

  document.querySelector("#runRag").onclick=async()=>{
    persistRag();
    const prompt=document.querySelector("#ragPrompt").value.trim();
    const instructions=document.querySelector("#ragInstructions").value.trim();
    cfg.prompt=prompt;
    cfg.instructions=instructions;
    if(!prompt)return toast("Enter a research question");
    if(!cfg.skip_retrieval&&!cfg.source_collection)return toast("Select a source collection");
    if(cfg.skip_retrieval&&!selectedEvidenceEntries().length)return toast("Select at least one evidence record before skipping retrieval");
    if(!cfg.skip_retrieval&&!cfg.locales.length)return toast("Select English and/or French");
    if(!cfg.skip_retrieval&&!cfg.search_types.length)return toast("Select at least one retrieval route");

    const selectedProfileId=document.querySelector("#ragProvider").value;
    const selectedProfile=providerProfile(selectedProfileId);
    const provider=selectedProfile?.type||"ollama";
    const model=provider==="openai"&&selectedProfile?.model_mode==="auto"
      ?"auto"
      : document.querySelector("#ragModel").value.trim();
    if(!model)return toast("Select a generation model");

    let extra={};
    try{
      extra=JSON.parse(document.querySelector("#ragExtraOptions").value||"{}");
      if(!extra||Array.isArray(extra)||typeof extra!=="object")throw new Error();
    }catch{return toast("Advanced generation options must be a JSON object")}

    let think=false;
    if(provider==="ollama"){
      const raw=document.querySelector("#ragThink").value;
      think=raw==="true"?true:["low","medium","high"].includes(raw)?raw:false;
    }
    const generation={
      num_ctx:provider==="ollama"?n("ragNumCtx",null):null,
      num_predict:n("ragNumPredict",4096),
      temperature:n("ragTemperature",0),
      top_k:provider==="ollama"?n("ragTopK",0):null,
      top_p:n("ragTopP",1),
      min_p:provider==="ollama"?n("ragMinP",null):null,
      repeat_penalty:provider==="ollama"?n("ragRepeatPenalty",null):null,
      seed:n("ragSeed",null),
      mirostat:provider==="ollama"?n("ragMirostat",0):null,
      mirostat_eta:provider==="ollama"?n("ragMirostatEta",null):null,
      mirostat_tau:provider==="ollama"?n("ragMirostatTau",null):null,
      think,
      keep_alive:provider==="ollama"?(document.querySelector("#ragKeepAlive").value.trim()||null):null,
      extra_options:extra,
    };

    if(selectedProfile){
      Object.assign(selectedProfile,{
        model,
        num_ctx:generation.num_ctx??selectedProfile.num_ctx,
        num_predict:generation.num_predict,
        think:String(generation.think??selectedProfile.think??"false"),
        temperature:generation.temperature,
        top_k:generation.top_k??selectedProfile.top_k,
        top_p:generation.top_p,
        min_p:generation.min_p??selectedProfile.min_p,
        repeat_penalty:generation.repeat_penalty??selectedProfile.repeat_penalty,
        seed:generation.seed??"",
        mirostat:generation.mirostat??selectedProfile.mirostat,
        mirostat_eta:generation.mirostat_eta??selectedProfile.mirostat_eta,
        mirostat_tau:generation.mirostat_tau??selectedProfile.mirostat_tau,
        keep_alive:generation.keep_alive??selectedProfile.keep_alive,
        extra_options:JSON.stringify(extra),
      });
      cfg.provider_profile_id=selectedProfile.id;
    }
    persistPrefs();

    const base_url=selectedProfile?.base_url||null;
    const api_key=provider==="openai"?(selectedProfile?.api_key||""):null;
    const gradeProfile=cfg.auto_grade?providerProfile(cfg.auto_grade_provider_profile_id):null;
    const gradeConfig=gradeProfile?providerRequestConfig(gradeProfile,{textReview:true}):null;
    const button=document.querySelector("#runRag");
    button.disabled=true;button.textContent="Starting RAG job…";
    try{
      rememberRagPrompt(prompt,instructions,{source_collection:cfg.source_collection,provider,model});
      persistPrefs();
      const job=await api("/api/jobs/rag",{
        method:"POST",
        body:JSON.stringify({
          prompt,
          instructions:instructions||null,
          source_collection:cfg.source_collection,
          // eslint-disable-next-line no-undef -- SA-11: existing missing runtime handler or stale variable; repair with workflow regression coverage.
          selected_evidence:selectedPayload,
          skip_retrieval:Boolean(cfg.skip_retrieval),
          locales:cfg.locales,
          search_types:cfg.search_types,
          k:cfg.k,
          fetch_k:cfg.fetch_k,
          lambda_mult:cfg.lambda_mult,
          rrf_k:cfg.rrf_k,
          rerank_top_n:cfg.rerank_top_n,
          reranker:cfg.reranker,
          cross_encoder_model:cfg.cross_encoder_model,
          query_decomposition:cfg.query_decomposition,
          query_decomposition_num_predict:cfg.query_decomposition_num_predict,
          response_language:cfg.response_language,
          evidence_record_char_limit:cfg.evidence_record_char_limit,
          evidence_total_char_limit:cfg.evidence_total_char_limit,
          provider,
          model,
          base_url,
          api_key,
          provider_profile_id:selectedProfile?.id||profile?.id||null,
          max_concurrent_requests:Math.max(1,Math.min(64,Number(selectedProfile?.max_concurrent_requests??profile?.max_concurrent_requests??(provider==="ollama"?1:32))||1)),
          generation,
          ollama_concurrency_limit:provider==="ollama"
            ?Math.max(1,Math.min(32,Number(selectedProfile?.max_concurrent_requests??profile?.max_concurrent_requests??state.appConfig.ollama_rag_concurrency??1)))
            :null,
          bind_citations:cfg.bind_citations,
          include_works_cited:cfg.include_works_cited,
          auto_grade:cfg.auto_grade,
          auto_grade_provider:gradeConfig?.provider||null,
          auto_grade_model:gradeConfig?.model||null,
          auto_grade_base_url:gradeConfig?.base_url||null,
          auto_grade_api_key:gradeConfig?.api_key||null,
          auto_grade_provider_profile_id:gradeConfig?.provider_profile_id||null,
          auto_grade_generation:gradeConfig?.ollama?sanitizeResearchGeneration(gradeConfig.ollama):null,
        }),
      });
      state.jobs=[job,...state.jobs.filter(existing=>existing.id!==job.id)];
      rememberRagRun(job);
      persistPrefs();
      syncJobProgressToasts();
      startJobPolling();
      refreshRagProgressPanel();
      toast(`RAG pipeline started · ${providerDisplayName(selectedProfile)} · ${model}`);
    }catch(error){
      toast(`Could not start RAG pipeline: ${error.message}`);
    }finally{
      button.disabled=false;button.innerHTML=`${icon("spark")}Run RAG pipeline in background`;
    }
  };
}

function dashboardTotals(){
  if(isResearcher()){const stores=recordStores();const active=stores.find(store=>store.name===state.activeStore)||stores[0];return {records:Number(active?.count||0),works:state.storeWorkStats.length,flagged:0,files:0,changes:0,dbs:stores.length,dbRecords:stores.reduce((sum,store)=>sum+(Number(store.count)||0),0),cacheResponses:0}}
  const corpus=memoCorpus("dashboard-totals",()=>{
    let flagged=0,changes=0;
    const works=new Set();
    for(const {record} of allRows()){
      const work=String(record.work||"").trim();
      if(work)works.add(work);
      if(record.needs_review)flagged++;
      changes+=Array.isArray(record.updates)?record.updates.length:0;
    }
    return {records:allRows().length,works:works.size,flagged,files:state.files.length,changes};
  });
  const stores=recordStores();
  return {
    ...corpus,
    dbs:stores.length,
    dbRecords:stores.reduce((sum,store)=>sum+(Number(store.count)||0),0),
    cacheResponses:Number(responseCacheStore()?.count||0),
  };
}
function compactNumber(value){const n=Number(value)||0;if(n>=1000000)return `${(n/1000000).toFixed(n>=10000000?0:1)}M`;if(n>=1000)return `${(n/1000).toFixed(n>=100000?0:1)}K`;return n.toLocaleString()}
function relativeTime(value){const date=new Date(value||0);if(!Number.isFinite(date.getTime()))return tr("time.recently","Recently");const seconds=Math.max(0,Math.round((Date.now()-date.getTime())/1000));if(seconds<60)return tr("time.just_now","just now");const minutes=Math.round(seconds/60);if(minutes<60)return trf("time.minutes_ago","{count} min ago",{count:minutes});const hours=Math.round(minutes/60);if(hours<24)return trf("time.hours_ago","{count} hr ago",{count:hours});return trf("time.days_ago","{count} d ago",{count:Math.round(hours/24)})}

function llmReadinessHtml(){
  const profiles=providerProfiles();
  const concurrency=state.health?.rag_concurrency;
  return `<div class="llm-readiness-all">
    ${profiles.map(profile=>{
      const warm=state.providerWarmups?.[profile.id]||{status:"idle"};
      const status=state.providerStatuses?.[profile.id]||{};
      const models=status.models||[];
      const model=profile.type==="openai"&&profile.model_mode==="auto"?"auto":(profile.model||"");
      const exact=models.some(item=>String(item.name||"")===model);
      const family=models.some(item=>String(item.name||"").split(":")[0]===String(model).split(":")[0]);
      const modelReady=profile.type==="openai"&&model==="auto"?Boolean(status.available):Boolean(exact||family);
      const selectedModelMeta=models.find(item=>String(item.name||"")===model)
        ||models.find(item=>String(item.name||"").split(":")[0]===String(model).split(":")[0])
        ||null;
      const warmLabel=warm.status==="ready"?"Warm":warm.status==="running"?"Warming":warm.status==="failed"?"Warmup failed":"Not warmed this session";
      const warmDetail=warm.completed_at
        ? `${formatTimestamp(warm.completed_at)}${Number.isFinite(Number(warm.elapsed_seconds))?` · ${Number(warm.elapsed_seconds).toFixed(2)}s`:""}`
        : warm.started_at?`Started ${formatTimestamp(warm.started_at)}`:"—";
      return `<article class="provider-readiness ${profile.id===state.appConfig.default_provider_profile?"default-provider":""}">
        <div class="provider-readiness-head">
          <div><b>${esc(providerDisplayName(profile))}</b><span>${profile.type==="ollama"?"Ollama":"OpenAI-compatible"}${profile.id===state.appConfig.default_provider_profile?" · default":""}</span></div>
          <span class="llm-endpoint-status"><i class="status-dot ${status.available?"ok":"bad"}"></i>${status.available?"Reachable":"Unavailable"}</span>
        </div>
        <div class="llm-readiness-grid">
          <div><span>Endpoint</span><b title="${esc(profile.base_url||"")}">${esc(profile.base_url||"—")}</b></div>
          <div><span>Configured model</span><b>${esc(model||"—")}</b></div>
          <div><span>Model readiness</span><b>${modelReady?"Available":"Not confirmed"}</b></div>
          <div><span>Discovered models</span><b>${models.length.toLocaleString()}</b></div>
          <div><span>Warmup</span><b>${esc(warmLabel)}${warmDetail!=="—"?` · ${esc(warmDetail)}`:""}</b></div>
          <div><span>Max concurrent requests</span><b>${Number(profile.max_concurrent_requests??(profile.type==="ollama"?1:32))}</b></div>
          ${profile.type==="ollama"?`<div><span>Active Ollama RAG</span><b>${Number(concurrency?.ollama_active||0)}</b></div>`:""}
          ${selectedModelMeta?.parameter_size?`<div><span>Model size</span><b>${esc(selectedModelMeta.parameter_size)}</b></div>`:""}
          ${selectedModelMeta?.quantization_level?`<div><span>Quantization</span><b>${esc(selectedModelMeta.quantization_level)}</b></div>`:""}
          ${status.error?`<div class="llm-readiness-error"><span>Status error</span><b>${esc(status.error)}</b></div>`:""}
        </div>
        <div class="tools provider-readiness-actions"><button class="btn tiny" data-warm-provider="${esc(profile.id)}">${icon("spark")}Warm</button>${profile.id!==state.appConfig.default_provider_profile?`<button class="btn tiny" data-default-provider="${esc(profile.id)}">Make default</button>`:""}</div>
      </article>`;
    }).join("")||'<div class="note">No LLM provider profiles configured.</div>'}
  </div>`;
}
function dashboardWorkspaceRecordTarget(pointer){
  if(!pointer||pointer.kind!=="workspace")return null;
  const file=state.files.find(item=>item.id===pointer.fileId);
  const index=Number(pointer.index);
  if(!file||!Number.isInteger(index)||index<0||index>=file.records.length)return null;
  return {record:file.records[index],target:{kind:"workspace",fileId:file.id,index}};
}
async function dashboardRecordPreview(){
  const pointer=state.lastViewedRecord;
  if(pointer?.kind==="workspace"){const found=dashboardWorkspaceRecordTarget(pointer);if(found)return {...found,lastViewed:true}}
  if(pointer?.kind==="database"&&pointer.store&&pointer.id){
    let record=(state.activeStore===pointer.store?researcherDbRecords():[]).find(item=>String(item._chroma_id||item.record_id||"")===String(pointer.id));
    if(!record){try{record=await api(`/api/stores/${encodeURIComponent(pointer.store)}/records/${encodeURIComponent(pointer.id)}`)}catch{record=null}}
    if(record)return {record,target:{kind:"database",store:pointer.store,id:String(pointer.id)},lastViewed:true};
  }
  if(isResearcher()){
    const current=recordStores().find(store=>store.name===state.activeStore)||recordStores()[0];
    if(!current?.name||!Number(current.count||0))return {record:null,target:null,lastViewed:false};
    try{
      const offset=Math.floor(Math.random()*Math.max(1,Number(current.count||0)));
      const data=await api(`/api/stores/${encodeURIComponent(current.name)}/records?limit=1&offset=${offset}`);
      const record=(data.records||[])[0]||null;
      if(record){const id=String(record._chroma_id||record.record_id||"");return {record,target:{kind:"database",store:current.name,id},lastViewed:false}}
    }catch(error){console.warn("Could not choose a random dashboard record",error)}
    return {record:null,target:null,lastViewed:false};
  }
  const choices=allRows();if(!choices.length)return {record:null,target:null,lastViewed:false};
  const item=choices[Math.floor(Math.random()*choices.length)];
  return {record:item.record,target:{kind:"workspace",fileId:item.file.id,index:item.index},lastViewed:false};
}

function renderCorpusBuildsHomeCard(){
  if(isResearcher())return "";
  const builds=(state.jobs||[]).filter(job=>job.type==="pdf_corpus").slice(0,4);
  const active=builds.filter(job=>["queued","running","cancelling"].includes(job.status)).length;
  return `<section class="card dashboard-corpus-builds" aria-label="${esc(tr("pdf_corpus.home_title","Corpus builds"))}">
    <div class="dashboard-section-heading"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("pdf")}</span><b>${esc(tr("pdf_corpus.home_title","Corpus builds"))}</b>${active?`<span class="dashboard-corpus-active">${active} ${esc(tr("operations.active","active"))}</span>`:""}</div><button class="dashboard-text-link" id="dashCorpusBuilder">${esc(tr("pdf_corpus.open_builder","Open Corpus Builder"))} →</button></div>
    <p class="dashboard-corpus-help">${esc(tr("pdf_corpus.home_help","Recent PDF-to-corpus pipelines stay visible here even after you leave Corpus Builder."))}</p>
    <div class="dashboard-corpus-list">${builds.length?builds.map(job=>{const pct=Math.max(0,Math.min(100,Math.round(Number(job.progress||0)*100)));const status=job.raw_status||job.status||"unknown";return `<button type="button" class="dashboard-corpus-row" data-dashboard-corpus-build="${esc(job.id)}"><span class="dashboard-corpus-state ${esc(job.status||"")}" aria-hidden="true"></span><span class="dashboard-corpus-copy"><b>${esc(job.source_filename||tr("pdf_corpus.source_pdf","Source PDF"))}</b><small>${esc(String(status).replaceAll("_"," "))} · ${esc(String(job.stage_detail||job.stage||""))}</small></span><span class="dashboard-corpus-progress"><b>${pct}%</b><i><span style="width:${pct}%"></span></i></span></button>`}).join(""):`<div class="dashboard-corpus-empty">${esc(tr("pdf_corpus.home_empty","No corpus builds yet. Start with a source PDF in Corpus Builder."))}</div>`}</div>
  </section>`;
}

async function renderDashboard(main){
  if(isResearcher()){
    try{await refreshStores();if(!state.activeStore)state.activeStore=recordStores()[0]?.name||"";if(state.activeStore)await refreshStoreWorks(true)}catch(error){console.warn("Could not refresh researcher dashboard data",error)}
  }
  try{await refreshServerAnnotations(isResearcher()&&state.serverAnnotationsStore!==String(state.activeStore||""))}catch(error){console.warn("Could not refresh annotations for dashboard",error)}
  const rows=allRows(),totals=dashboardTotals(),workMap=isResearcher()?null:workIndex();
  const workItems=isResearcher()?(state.storeWorkStats||[]).map(item=>({work:item.work,count:Number(item.count||0),totalWords:Number(item.total_words||0),averageRecordLength:Number(item.average_record_length||0),year:item.publication_year||item.year||"",cover:item.cover_url||"",author:item.document_author||"",publisher:item.publisher||""})): [...workMap.values()].map(item=>{const year=commonWorkValue(item.rows,"publication_year"),totalWords=item.rows.reduce((sum,row)=>sum+String(row.record?.text||"").trim().split(/\s+/).filter(Boolean).length,0);return {work:item.work,count:item.count,totalWords,averageRecordLength:item.count?Math.round(totalWords/item.count):0,year:year.value||[...item.years].sort()[0]||"",cover:workCoverUrl(item.rows),author:[...item.authors].join(", "),publisher:commonWorkValue(item.rows,"publisher").value||""}}).sort((a,b)=>a.work.localeCompare(b.work));
  const words=workItems.reduce((sum,item)=>sum+Number(item.totalWords||0),0);
  const singleLoadedWork=!isResearcher()&&workItems.length===1&&workMap?.has(workItems[0].work)?workMap.get(workItems[0].work):null;
  const metricSets=singleLoadedWork?workInsightMetrics(singleLoadedWork.rows,singleLoadedWork.work):[
    {id:"average",type:"bars",title:tr("dashboard.top_avg_record_length","Top 5 Works by Average Record Length"),values:[...workItems].sort((a,b)=>b.averageRecordLength-a.averageRecordLength).slice(0,5).map(item=>({key:item.work,value:item.averageRecordLength})),format:value=>Number(value).toLocaleString()},
    {id:"words",type:"bars",title:tr("dashboard.top_total_words","Top 5 Works by Total Words"),values:[...workItems].sort((a,b)=>b.totalWords-a.totalWords).slice(0,5).map(item=>({key:item.work,value:item.totalWords})),format:value=>compactNumber(value)},
    {id:"records",type:"bars",title:tr("dashboard.top_works_records","Top 5 Works by Number of Records"),values:[...workItems].sort((a,b)=>b.count-a.count).slice(0,5).map(item=>({key:item.work,value:item.count})),format:value=>Number(value).toLocaleString()},
    {id:"record-share",type:"pie",title:tr("dashboard.work_record_share","Works as percentage of total records"),values:pieShareSeries(workItems,"count"),valueLabel:tr("dynamic.records","records")},
    {id:"word-share",type:"pie",title:tr("dashboard.work_word_share","Works as percentage of total words"),values:pieShareSeries(workItems,"totalWords"),valueLabel:tr("dashboard.words","words")},
  ];
  state.dashboardMetricIndex=Math.max(0,Math.min(metricSets.length-1,Number(state.dashboardMetricIndex)||0));
  const activeMetric=metricSets[state.dashboardMetricIndex];
  const recent=isResearcher()
    ? (hasCapability("activity.read")?[...(hasCapability("annotations.read")?(state.serverAnnotations||[]).map(annotation=>({kind:"annotation",timestamp:annotation.created_at||"",annotation})):[]),...(hasCapability("rag.jobs.own")?(state.jobs||[]).filter(job=>job.type==="rag").map(job=>({kind:"rag",timestamp:job.updated_at||job.finished_at||job.created_at||"",job})):[])].sort((a,b)=>new Date(b.timestamp||0)-new Date(a.timestamp||0)).slice(0,4):[])
    : recentAuditChanges(4).map(({file,record,index,update})=>({kind:"record",timestamp:update.timestamp||"",file,record,index,update}));
  const works=workItems.sort((a,b)=>a.work.localeCompare(b.work));
  const currentProvider=defaultProviderProfile();
  const currentLanguage=state.translations?.info?.name||state.translations?.locale||"";
  const currentLanguageFlag=state.translations?.info?.flag||"🌐";
  const latestAnnotation=(!isResearcher()||hasCapability("annotations.read"))?(recentAnnotations(1)[0]||null):null;
  const preview=await dashboardRecordPreview(),previewRecord=preview.record,previewTarget=preview.target;
  main.innerHTML=`<div class="dashboard-page">
    <section class="dashboard-page-top"><article class="card dashboard-hero"><img src="/brand/derridai-mark.png" alt="" class="dashboard-hero-mark"><div class="dashboard-hero-copy"><h1>${esc(tr("dashboard.welcome","Welcome to DerridAI"))}</h1><p class="dashboard-hero-tagline">${esc(tr("dashboard.tagline","Search. Compare. Annotate. Always already."))}</p><blockquote>${esc(tr("dashboard.quote","“Il n’y a pas de hors-texte.”"))}</blockquote><small>— Jacques Derrida</small><div class="dashboard-hero-actions"><button class="btn dark" id="dashStartSearch">${icon("search")}${esc(tr("dashboard.start_searching","Start searching"))}</button><button class="btn" id="dashBrowseWorks">${icon("books")}${esc(tr("dashboard.browse_works","Browse works"))}</button></div></div></article>
    <article class="card dashboard-search-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("search")}</span><b>${esc(tr("dashboard.global_search","Global Search"))}</b></div><div class="dashboard-search-tabs"><button class="${state.globalSearchMode==="traditional"?"active":""}" data-dash-search-mode="traditional">${esc(tr("research.traditional_search",isResearcher()?"Record search":"Traditional search"))}</button><button class="${state.globalSearchMode!=="traditional"?"active":""}" data-dash-search-mode="database">${esc(tr("research.semantic_db_search","Semantic DB Search"))}</button></div><div class="dashboard-search-line"><div class="dashboard-search-input">${icon("search")}<input id="dashSearchQuery" value="${esc(state.globalSearch||"")}" placeholder="${esc(tr("dashboard.search_corpus_placeholder","Search the corpus…"))}"></div><select id="dashSearchWork" class="control" aria-label="${esc(tr("field.work","Work"))}"><option value="">${esc(tr("dashboard.all_works","All works"))}</option>${works.map(item=>`<option value="${esc(item.work)}">${esc(item.work)}</option>`).join("")}</select><button class="btn dark" id="dashRunSearch">${icon("search")}${esc(tr("ui.search","Search"))}</button></div><div class="dashboard-search-footer"><button class="dashboard-advanced-link" id="dashAdvancedSearch">${esc(tr("dashboard.advanced_filters","Advanced filters"))} →</button><p class="dashboard-search-help">${esc(tr("dashboard.search_help","Search across works, metadata, annotations, and—when available—the semantic database."))}</p></div></article></section>
    <section class="dashboard-page-middle"><article class="card dashboard-overview-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("books")}</span><b>${esc(tr("dashboard.corpus_overview","Corpus Overview"))}</b></div><div class="dashboard-overview-grid"><button data-dashboard-nav="works"><span class="dashboard-overview-icon">${icon("books")}</span><strong>${works.length.toLocaleString()}</strong><small>${esc(tr("dashboard.works","Works"))}</small></button><button data-dashboard-nav="${isResearcher()?"vector":"list"}"><span class="dashboard-overview-icon">${icon("record")}</span><strong>${totals.records.toLocaleString()}</strong><small>${esc(tr("dashboard.records","Records"))}</small></button><button ${isResearcher()?"disabled data-disabled-reason=\"Word totals are not exposed to researcher accounts.\"":""}><span class="dashboard-overview-icon">${icon("list")}</span><strong>${isResearcher()?"—":compactNumber(words)}</strong><small>${esc(tr("dashboard.total_words","Total words"))}</small></button><button data-dashboard-nav="vector"><span class="dashboard-overview-icon">${icon("database")}</span><strong>${totals.dbs.toLocaleString()}</strong><small>${esc(tr("dashboard.databases","Databases"))}</small></button></div></article>
    <article class="card dashboard-average-card dashboard-metric-carousel" aria-roledescription="carousel"><div class="dashboard-metric-head"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("chart")}</span><b>${esc(activeMetric.title)}</b></div><div class="dashboard-metric-controls"><button class="dashboard-metric-arrow" id="dashMetricPrev" type="button" aria-label="${esc(tr("dashboard.previous_chart","Previous chart"))}">←</button><span>${state.dashboardMetricIndex+1} / ${metricSets.length}</span><button class="dashboard-metric-arrow" id="dashMetricNext" type="button" aria-label="${esc(tr("dashboard.next_chart","Next chart"))}">→</button></div></div><div class="dashboard-metric-body">${dashboardMetricBody(activeMetric)}</div><div class="dashboard-metric-dots" role="tablist" aria-label="${esc(tr("dashboard.work_charts","Work charts"))}">${metricSets.map((metric,index)=>`<button type="button" role="tab" data-dashboard-metric="${index}" class="${index===state.dashboardMetricIndex?"active":""}" aria-label="${esc(metric.title)}" aria-selected="${index===state.dashboardMetricIndex}" tabindex="${index===state.dashboardMetricIndex?0:-1}"></button>`).join("")}</div></article>
    <article class="card dashboard-activity-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("history")}</span><b>${esc(tr("dashboard.recent_activity","Recent Activity"))}</b></div><div class="dashboard-activity-list">${recent.map(item=>item.kind==="annotation"?`<button class="dashboard-activity-row" data-recent-server-annotation-record="${esc(item.annotation.record_id||"")}" data-recent-server-annotation-store="${esc(item.annotation.store||"")}"><span class="dashboard-activity-clock">${icon("record")}</span><time>${esc(relativeTime(item.timestamp))}</time><span>${esc(tr("annotations.record_note","Annotation"))} · ${esc(item.annotation.work||item.annotation.record_id||tr("nav.record","Record"))}</span></button>`:item.kind==="rag"?`<button class="dashboard-activity-row" ${item.job.status==="completed"?`data-recent-rag-result="${esc(item.job.id)}"`:""}><span class="dashboard-activity-clock">${icon("spark")}</span><time>${esc(relativeTime(item.timestamp))}</time><span>${esc(tr("nav.rag","Research"))} · ${esc(String(item.job.prompt||item.job.label||"RAG").slice(0,90))}</span></button>`:`<button class="dashboard-activity-row" data-recent-file="${item.file.id}" data-recent-index="${item.index}"><span class="dashboard-activity-clock">${icon("history")}</span><time>${esc(relativeTime(item.update.timestamp))}</time><span>${esc(label(item.update.field_name||tr("dashboard.updated_record","Updated record")))} · ${esc(item.record.work||item.record.record_id||item.file.name)}</span></button>`).join("")||`<div class="dashboard-activity-empty">${esc(tr("dashboard.no_recent_activity","No recent activity in areas available to this account."))}</div>`}</div></article></section>
    <section class="card dashboard-works-card"><div class="dashboard-section-heading"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("books")}</span><b>${esc(tr("dashboard.works","Works"))}</b></div><button class="dashboard-text-link" id="dashViewAllWorks">${esc(tr("dashboard.view_all_works","View all works"))} →</button></div><div class="dashboard-work-carousel-shell"><button class="carousel-arrow" id="dashWorksPrev" type="button" title="${esc(tr("ui.previous","Previous"))}" aria-label="${esc(tr("ui.previous","Previous"))}">‹</button><div class="dashboard-work-strip" id="dashWorksCarousel">${works.map((item,index)=>`<button class="dashboard-work-card" data-dashboard-work="${esc(item.work)}">${item.cover?`<img class="dashboard-book-cover image" src="${esc(item.cover)}" alt="${esc(trf("works.cover_alt","Cover of {work}",{work:item.work}))}" loading="lazy">`:`<span class="dashboard-book-cover placeholder">${String(index+1).padStart(2,"0")}</span>`}<span><b>${esc(item.work)}</b><small>${esc(item.year||tr("dashboard.year_not_recorded","Year not recorded"))}</small><small>${item.count.toLocaleString()} ${esc(tr("dynamic.records","records"))}</small></span></button>`).join("")||`<div class="note">${esc(tr("research.no_works","No works loaded yet."))}</div>`}</div><button class="carousel-arrow" id="dashWorksNext" type="button" title="${esc(tr("ui.next","Next"))}" aria-label="${esc(tr("ui.next","Next"))}">›</button></div></section>
    <section class="dashboard-page-lower">${isResearcher()?(hasCapability("appearance.manage")?`<article class="card dashboard-quick-card dashboard-appearance-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("gear")}</span><b>${esc(tr("dashboard.appearance","Appearance"))}</b></div><p>${esc(tr("dashboard.appearance_help","Choose the interface accent that is easiest for you to read."))}</p><fieldset class="dashboard-theme-options"><legend>${esc(tr("dashboard.interface_theme","Interface theme"))}</legend>${[["green",tr("theme.green","Green")],["blue",tr("theme.blue","Blue")],["slate",tr("theme.slate","Slate")]].map(([value,name])=>`<label><input type="radio" name="dashboard-theme" data-dashboard-theme="${value}" ${state.appConfig.ui_color_theme===value?"checked":""}><span class="theme-swatch ${value}" aria-hidden="true"></span><b>${esc(name)}</b></label>`).join("")}</fieldset><button class="btn" id="dashAppearanceSettings">${esc(tr("dashboard.more_appearance_settings","More appearance settings"))}</button></article>`:`<article class="card dashboard-quick-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("gear")}</span><b>${esc(tr("dashboard.appearance","Appearance"))}</b></div><p>${esc(tr("permissions.appearance_denied","Appearance controls are disabled for this role."))}</p></article>`):`<article class="card dashboard-quick-card dashboard-language-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("gear")}</span><b>${esc(tr("dashboard.language_settings","Language Settings"))}</b></div><p>${esc(tr("dashboard.language_settings_help","Choose the interface language and manage translation dictionaries."))}</p><div class="dashboard-quick-field dashboard-locale-field"><span>${esc(tr("dashboard.interface_language","Interface language"))}</span><b><i class="dashboard-locale-symbol">${currentLanguageFlag}</i>${esc(currentLanguage)}</b></div><button class="btn primary" id="dashLanguages">${esc(tr("dashboard.manage_languages","Manage languages"))}</button></article>`}
    <article class="card dashboard-quick-card dashboard-provider-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("spark")}</span><b>${esc(tr("dashboard.llm_provider_settings","LLM Provider Settings"))}</b></div><p>${esc(tr("dashboard.llm_provider_help","Configure the provider used for LLM-assisted workflows."))}</p><div class="dashboard-provider-fields"><div class="dashboard-quick-field"><span>${esc(tr("dashboard.default_provider","Default provider"))}</span><b>${currentProvider?esc(providerDisplayName(currentProvider)):esc(tr("dashboard.not_configured","Not configured"))}</b></div><div class="dashboard-quick-field"><span>${esc(tr("dashboard.model","Model"))}</span><b>${currentProvider?esc(currentProvider.model||"auto"):"—"}</b></div></div><button class="btn" id="dashProviders">${esc(isResearcher()?tr("nav.rag","Research"):tr("dashboard.manage_provider","Manage provider"))}</button></article>
    <article class="card dashboard-quick-card dashboard-record-preview"><div class="dashboard-section-heading"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("record")}</span><b>${esc(tr("dashboard.record_view","Record View"))}</b></div><button class="dashboard-text-link" id="dashRecordView" ${previewTarget?"":`disabled data-disabled-reason="${esc(tr("dashboard.no_record_available","No record is available to open."))}"`}>${esc(tr("research.open","Open"))} →</button></div>${previewRecord?`<div class="dashboard-record-state">${esc(preview.lastViewed?tr("dashboard.last_viewed_record","Last viewed record"):tr("dashboard.random_record","A record from the corpus"))}</div><div class="dashboard-record-meta"><b>${esc(previewRecord.work||previewRecord.record_id||tr("dashboard.record","Record"))}</b><span class="dashboard-record-pages">${esc(mlaPageSpan(previewRecord)||"")}</span></div><div class="dashboard-record-text">${esc(String(previewRecord.text||"").replace(/\s+/g," ").slice(0,220))}${String(previewRecord.text||"").length>220?"…":""}</div>`:`<div class="dashboard-record-empty">${esc(tr("dashboard.no_record_selected","No corpus record is currently available."))}</div>`}</article>
    ${latestAnnotation?`<article class="card dashboard-quick-card dashboard-annotations-card"><div class="dashboard-section-heading"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("record")}</span><b>${esc(tr("dashboard.latest_annotation","Latest annotation"))}</b></div><button class="dashboard-text-link" id="dashAnnotations">${esc(tr("annotations.view_all","View all"))} →</button></div><button class="dashboard-annotation-preview" ${latestAnnotation.server?`data-recent-server-annotation-record="${esc(latestAnnotation.annotation.record_id||"")}" data-recent-server-annotation-store="${esc(latestAnnotation.annotation.store||"")}"`:`data-recent-annotation-file="${esc(latestAnnotation.file.id)}" data-recent-annotation-index="${latestAnnotation.index}"`}><div class="dashboard-annotation-meta"><span class="dashboard-annotation-work">${esc(latestAnnotation.work)}</span><span class="dashboard-annotation-pages">${esc(mlaPageSpan(latestAnnotation.record)||tr("record.page_not_recorded","Page not recorded"))}</span><span class="dashboard-annotation-author">${esc(latestAnnotation.annotation.initiated_by||latestAnnotation.annotation.author||tr("annotations.unknown_author","Unknown author"))}</span><time>${esc(formatTimestamp(latestAnnotation.annotation.created_at))}</time><small>${esc(latestAnnotation.record.record_id||tr("nav.record","Record"))}</small></div>${latestAnnotation.annotation.note?`<p>${esc(latestAnnotation.annotation.note)}</p>`:latestAnnotation.annotation.quote?`<blockquote>${esc(latestAnnotation.annotation.quote)}</blockquote>`:`<p>${esc(tr("annotations.record_note","Record annotation"))}</p>`}</button></article>`:`<article class="card dashboard-quick-card dashboard-annotations-card"><div class="dashboard-section-heading"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("record")}</span><b>${esc(tr("dashboard.annotations","Annotations"))}</b></div><button class="dashboard-text-link" id="dashAnnotations">${esc(tr("research.open","Open"))} →</button></div><p>${esc(isResearcher()?tr("annotations.researcher_help","Annotations are organized by work when available in the current workspace."):tr("dashboard.annotations_help","Collect notes, tags, and discussion threads attached to corpus evidence."))}</p></article>`}
    </section>${renderCorpusBuildsHomeCard()}${renderOperationsPanel()}</div>`;
  mountOperationsPanelHost();
  // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  const goSearch=async()=>{state.globalSearch=main.querySelector("#dashSearchQuery")?.value?.trim()||"";const work=main.querySelector("#dashSearchWork")?.value||"",semantic=state.globalSearchMode==="database";state.globalPage=1;state.storeSearchResults=[];if(semantic){if(!state.activeStore){try{await refreshStores()}catch{};state.activeStore=recordStores()[0]?.name||""}state.globalSearchMode="database";if(!state.activeStore){persistPrefs();if(canAccessPage("vector")){toast(tr("search.redirect_database","Search needs a corpus database. Opening database creation now."),{tone:"info"});openDatabaseCreationFromResearch()}else{navigateTo("global");toast(tr("research.no_database","No corpus database available"),{tone:"warn"})}return;}state.dbSearchWhere=work?{work}:{};state.storeQuery=state.globalSearch;if(state.globalSearch&&state.dbSearchMethod==="filter")state.dbSearchMethod="similarity";if(!state.globalSearch&&work)state.dbSearchMethod="filter";state.globalSearchAutoRun=false;state.storeSearchLoading=true;persistPrefs();navigateTo("global");try{const mode=state.dbSearchMethod||"similarity";const data=await api(`/api/stores/${encodeURIComponent(state.activeStore)}/search`,{method:"POST",body:JSON.stringify({query:state.globalSearch,mode,n_results:100,where:Object.keys(dbSearchWhere()).length?dbSearchWhere():null,fetch_k:Number(state.dbSearchFetchK||100),lambda_mult:Number(state.dbSearchLambda??0.7)})});state.storeSearchResults=data.results||[]}catch(error){toast(`${tr("research.search_failed","Search failed")}: ${error.message}`,{tone:"danger"})}finally{state.storeSearchLoading=false;persistPrefs();if(state.view==="global")renderGlobal(document.querySelector("#main"))}}else{state.globalSearchMode="traditional";state.globalSearchAutoRun=false;if(isResearcher())state.dbSearchWhere=work?{work}:{};else state.globalFilters=work?[{id:uid(),field:"work",op:"eq",value:work}]:[];persistPrefs();navigateTo("global")}};
  // eslint-disable-next-line no-undef -- SA-11: existing missing runtime handler or stale variable; repair with workflow regression coverage.
  main.querySelector("#dashStartSearch")?.addEventListener("click",()=>navigateTo("global"));main.querySelector("#dashBrowseWorks")?.addEventListener("click",()=>navigateTo("works"));main.querySelector("#dashViewAllWorks")?.addEventListener("click",()=>navigateTo("works"));main.querySelector("#dashRunSearch")?.addEventListener("click",goSearch);main.querySelector("#dashSearchQuery")?.addEventListener("keydown",event=>{if(event.key==="Enter"){event.preventDefault();goSearch()}});main.querySelector("#dashAdvancedSearch")?.addEventListener("click",()=>{state.globalSearch=main.querySelector("#dashSearchQuery")?.value?.trim()||"";const work=main.querySelector("#dashSearchWork")?.value||"";state.globalAdvancedOpen=true;if(state.globalSearchMode==="database")state.dbSearchWhere=work?{work}:{};else if(!isResearcher())state.globalFilters=work?[{id:uid(),field:"work",op:"eq",value:work}]:[];persistPrefs();navigateTo("global")});main.querySelectorAll("[data-dash-search-mode]").forEach(button=>button.addEventListener("click",()=>{state.globalSearchMode=button.dataset.dashSearchMode;persistPrefs();syncUrl({replace:true});renderDashboard(main)}));main.querySelectorAll("[data-dashboard-nav]").forEach(button=>button.addEventListener("click",()=>navigateTo(button.dataset.dashboardNav)));main.querySelectorAll("[data-dashboard-work]").forEach(button=>button.addEventListener("click",()=>{state.workOverview=button.dataset.dashboardWork||"";persistPrefs();navigateTo("works")}));main.querySelectorAll("[data-dashboard-search-field]").forEach(button=>button.addEventListener("click",()=>searchByMetadata(button.dataset.dashboardSearchField,button.dataset.dashboardSearchValue,{contains:["persons","concepts","topics"].includes(button.dataset.dashboardSearchField)})));const carousel=main.querySelector("#dashWorksCarousel");const scrollWorks=direction=>carousel?.scrollBy({left:direction*Math.max(280,carousel.clientWidth*.78),behavior:"smooth"});main.querySelector("#dashWorksPrev")?.addEventListener("click",()=>scrollWorks(-1));main.querySelector("#dashWorksNext")?.addEventListener("click",()=>scrollWorks(1));main.querySelectorAll("[data-recent-file]").forEach(button=>button.addEventListener("click",()=>navigateTo("record",{fileId:button.dataset.recentFile,index:+button.dataset.recentIndex})));main.querySelectorAll("[data-dashboard-theme]").forEach(input=>input.addEventListener("change",()=>{applyUiTheme(input.dataset.dashboardTheme);persistPrefs();toast(tr("dashboard.appearance_saved","Appearance updated"),{tone:"success"})}));main.querySelector("#dashAppearanceSettings")?.addEventListener("click",()=>navigateTo("config"));main.querySelector("#dashLanguages")?.addEventListener("click",()=>{if(isResearcher())navigateTo("config");else window.dispatchEvent(new CustomEvent("derridai:navigate-native",{detail:{path:"/languages"}}))});main.querySelector("#dashProviders")?.addEventListener("click",()=>navigateTo(isResearcher()?"rag":"providers"));main.querySelector("#dashRecordView")?.addEventListener("click",()=>{if(!previewTarget)return;if(previewTarget.kind==="workspace")navigateTo("record",{fileId:previewTarget.fileId,index:previewTarget.index});else{state.activeStore=previewTarget.store;state.researcherRecordId=previewTarget.id;persistPrefs();navigateTo("record")}});main.querySelector("#dashMetricPrev")?.addEventListener("click",()=>{state.dashboardMetricIndex=(state.dashboardMetricIndex+metricSets.length-1)%metricSets.length;persistPrefs();syncUrl({replace:true});renderDashboard(main)});main.querySelector("#dashMetricNext")?.addEventListener("click",()=>{state.dashboardMetricIndex=(state.dashboardMetricIndex+1)%metricSets.length;persistPrefs();syncUrl({replace:true});renderDashboard(main)});main.querySelectorAll("[data-dashboard-metric]").forEach(button=>{button.addEventListener("click",()=>{state.dashboardMetricIndex=Number(button.dataset.dashboardMetric)||0;persistPrefs();syncUrl({replace:true});renderDashboard(main)});button.addEventListener("keydown",event=>{if(!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;event.preventDefault();if(event.key==="Home")state.dashboardMetricIndex=0;else if(event.key==="End")state.dashboardMetricIndex=metricSets.length-1;else state.dashboardMetricIndex=(state.dashboardMetricIndex+(event.key==="ArrowRight"?1:-1)+metricSets.length)%metricSets.length;persistPrefs();syncUrl({replace:true});renderDashboard(main);queueMicrotask(()=>main.querySelector(`[data-dashboard-metric="${state.dashboardMetricIndex}"]`)?.focus())})});main.querySelector("#dashAnnotations")?.addEventListener("click",()=>navigateTo("annotations"));main.querySelector("[data-recent-annotation-file]")?.addEventListener("click",event=>navigateTo("record",{fileId:event.currentTarget.dataset.recentAnnotationFile,index:+event.currentTarget.dataset.recentAnnotationIndex}));main.querySelector("[data-recent-server-annotation-record]")?.addEventListener("click",event=>openSharedAnnotationRecord(event.currentTarget.dataset.recentServerAnnotationStore,event.currentTarget.dataset.recentServerAnnotationRecord));wireCorpusBuildsHomeCard(main);wireOperationsPanel();decorateDisabledControls(main);
}


let shellRefreshHook=()=>{};
function setShellRefreshHook(hook){
  shellRefreshHook=typeof hook==="function"?hook:()=>{};
}
function shell(){
  persistPrefs();
  shellRefreshHook();
}
function collapseKeyFor(element,index){
  const heading=element.querySelector(".cardhead b,.cardhead h2,.section-title-row h3,.dash-chart-title")?.textContent?.trim()
    ||element.getAttribute("aria-label")
    ||element.className
    ||element.tagName;
  return `${state.view}::${heading}::${index}`;
}
function enhanceCollapsibles(root=document.querySelector("#main")){
  if(!root)return;
  const targets=[...root.querySelectorAll(".card:not(.work):not(.faq-card),.card-inset,.dash-chart,.provider-profile-card,.rag-live-job")];
  targets.forEach((element,index)=>{
    if(element.dataset.collapsibleReady==="1"||element.closest("dialog")||element.matches("[data-no-collapse=true]")||element.closest("[data-no-collapse=true]"))return;
    let host=element.querySelector(":scope > .cardhead")
      ||element.querySelector(":scope > .dash-chart-head")
      ||element.querySelector(":scope > .provider-profile-card-head")
      ||element.querySelector(":scope > .rag-live-job-head")
      ||element.querySelector(":scope > .section-title-row");
    if(!host)return;
    const fullHeight=Math.max(element.scrollHeight,element.getBoundingClientRect().height);
    const headerHeight=Math.max(30,host.getBoundingClientRect().height||30);
    if(fullHeight<=headerHeight*2){
      element.dataset.collapsibleReady="skip";
      return;
    }
    element.dataset.collapsibleReady="1";
    const key=collapseKeyFor(element,index);
    element.dataset.collapseKey=key;
    const collapsed=Boolean(state.collapsedPanels?.[key]);
    element.classList.toggle("ui-collapsed",collapsed);
    const compactTitle=document.createElement("span");
    compactTitle.className="ui-collapse-title";
    compactTitle.textContent=
      element.querySelector(":scope > .cardhead b,:scope > .dash-chart-head .dash-chart-title,:scope > .section-title-row h3,:scope > .rag-live-job-head b")?.textContent?.trim()
      ||element.querySelector(":scope > .provider-profile-card-head [data-profile-field='name']")?.value
      ||element.querySelector("h1,h2,h3,h4,b")?.textContent?.trim()
      ||"Section";
    host.appendChild(compactTitle);
    const button=document.createElement("button");
    button.type="button";button.className="ui-collapse-toggle";button.title=collapsed?"Expand":"Collapse";button.setAttribute("aria-label",button.title);button.textContent=collapsed?"＋":"−";
    button.onclick=e=>{e.stopPropagation();const next=!element.classList.contains("ui-collapsed");element.classList.toggle("ui-collapsed",next);button.textContent=next?"＋":"−";button.title=next?"Expand":"Collapse";state.collapsedPanels[key]=next;persistPrefs()};
    host.appendChild(button);
  });
}
let collapsibleObserver=null;
function installCollapsibleObserver(){
  const main=document.querySelector("#main");
  if(!main)return;
  if(collapsibleObserver)collapsibleObserver.disconnect();
  let scheduled=false;
  collapsibleObserver=new MutationObserver(()=>{
    if(scheduled)return;
    scheduled=true;
    scheduleUiWork(()=>{scheduled=false;enhanceCollapsibles(main);translateLegacyDom(main)});
  });
  collapsibleObserver.observe(main,{childList:true,subtree:true});
  enhanceCollapsibles(main);
}
function renderView(){
  const main=document.querySelector("#main");
  // Native Vue routes (for example Users & roles) intentionally do not mount
  // the legacy surface. Do not let compatibility rendering or URL syncing
  // overwrite those routes while they are active.
  if(!main){
    unmountOperationsPanel();
    shellRefreshHook?.();
    return null;
  }
  if(state.view!=="home")unmountOperationsPanel();
  if(!canAccessPage(state.view))state.view="home";
  syncUrl({replace:true});
  let result;
  if(state.view==="home") result=renderDashboard(main);
  else if(state.view==="pdf") result=renderPdf(main);
  else if(state.view==="compare") result=renderCompare(main);
  // The Vector Stores route is Vue-native. Keep this guard only for callers
  // that invoke the legacy renderer while a native route is mounting.
  else if(state.view==="vector") result=null;
  else if(state.view==="rag") result=renderRag(main);
  else if(state.view==="faq") result=renderFaq(main);
  else if(state.view==="responsecache") result=renderResponseCache(main);
  else if(isResearcher()&&state.view==="record") result=renderRecord(main);
  else if(isResearcher()&&state.view==="works") result=renderWorks(main);
  else if(isResearcher()&&state.view==="annotations") result=renderAnnotations(main);
  else if(isResearcher()&&state.view==="global") result=renderGlobal(main);
  else if(!state.files.length) result=renderEmpty(main);
  else if(state.view==="list") result=renderList(main);
  else if(state.view==="record") result=renderRecord(main);
  else if(state.view==="works") result=renderWorks(main);
  else if(state.view==="annotations") result=renderAnnotations(main);
  else result=renderGlobal(main);
  Promise.resolve(result).finally(()=>requestAnimationFrame(()=>{enhanceCollapsibles(main);decorateDisabledControls(main);translateLegacyDom(main)}));
  return result;
}

function renderEmpty(main){
  const requestedFileId=new URLSearchParams(location.search).get("file");
  const shared=Boolean(requestedFileId);
  main.innerHTML=`<section class="empty"><div class="drop"><div class="drop-icon">${icon("upload")}</div><h1>${esc(shared?tr("records.open_shared_workspace","Open the shared corpus workspace"):tr("records.open_workspace","Open a corpus workspace"))}</h1><p>${esc(shared?tr("records.shared_workspace_help","This link preserves the table state and filters, while JSONL contents remain browser-local. Choose the same JSONL file to restore this shared view."):tr("records.open_workspace_help","Drop one or more JSONL files anywhere on this page, or choose files manually. Each file stays in its own tab and can be edited, compared, searched, exported, or sent to the corpus database."))}</p><button class="btn primary" id="choose">${icon("upload")}${esc(tr("records.choose_jsonl","Choose JSONL files"))}</button></div></section>`;
  document.querySelector("#choose").onclick=()=>document.querySelector("#fileInput")?.click();
}

async function importFiles(fileList){
  if(isResearcher())return toast("Researcher accounts cannot load or edit corpus files.");
  const shareParams=new URLSearchParams(location.search);
  const requestedFileId=shareParams.get("file");
  const requestedUrlState=shareParams.get("ts");
  let first=null, total=0, errors=0;
  for(const file of [...fileList]){
    const text=await file.text();
    const parsed=parseJsonl(text);
    if(!parsed.records.length){errors+=parsed.errors.length||1;continue}
    const identity=await stableJsonlFileIdentity(text);
    const existing=state.files.find(item=>item.id===identity.id);
    if(existing){
      first ||= existing.id;
      total+=existing.records.length;
      errors+=existing.errors?.length||0;
      continue;
    }
    const item={...identity,name:file.name,records:parsed.records,errors:parsed.errors,dirty:new Set(),imported_at:new Date().toISOString()};
    state.files.push(item);persistFileNow(item);first ||= item.id;total+=item.records.length;errors+=item.errors.length;
  }
  if(requestedFileId&&state.files.some(item=>item.id===requestedFileId)){
    state.activeFileId=requestedFileId;
    if(requestedUrlState)applyCompressedTableUrlState(decompressUrlState(requestedUrlState),state.view);
  }else if(first)state.activeFileId=first;
  persistPrefs();shell();renderView();syncUrl({replace:true});toast(`Loaded ${total} records${errors?` · ${errors} parse issues`:""}`);
}
async function closeFile(id){
  const f=state.files.find(x=>x.id===id);if(!f)return;
  if(f.dirty.size && !await openMessageModal({title:"Close modified JSONL?",message:`${f.name} has modified records. Close anyway?`,tone:"danger",confirmLabel:"Close file",cancelLabel:"Keep open"}))return;
  const i=state.files.indexOf(f);state.files.splice(i,1);delete state.searches[id];delete state.listFilters[id];delete state.pages[id];delete state.sorts[id];
  clearFileDerivedState(id);
  invalidateCorpusCache();
  idbDelete("files",id).catch(error=>console.error("Could not remove saved file",error));
  if(state.activeFileId===id)state.activeFileId=state.files[Math.min(i,state.files.length-1)]?.id||null;
  persistPrefs();shell();renderView();
}

function renderList(main){
  const f=activeFile(),q=state.searches[f.id]||"",sort=state.sorts[f.id]||(state.sorts[f.id]={key:"page_start",dir:1}),filters=state.listFilters[f.id]||{};
  let rows=f.records.map((record,index)=>({file:f,record,index}))
    .filter(x=>!q||String(x.record.text||"").toLocaleLowerCase().includes(q.toLocaleLowerCase()))
    .filter(x=>rowMatchesListFilters(x,filters));
  rows=sortRows(rows,sort);
  const pg=pageInfo(rows.length,state.pages[f.id]||1);state.pages[f.id]=pg.page;
  const slice=rows.slice(pg.start,pg.end);
  const reviewCount=state.reviewSelection.size;
  const flagged=needsReviewItems(f.records.map((record,index)=>({file:f,record,index}))).length;
  const pageSelected=slice.length>0&&slice.every(x=>state.reviewSelection.has(reviewKey(f,x.index)));
  const available=tableAvailableFields(f.records.map((record,index)=>({file:f,record,index})),["__db_status","work","page_start","needs_review","text"]);
  const columns=getTableColumns("list",available);
  main.innerHTML=`<div class="toolbar"><div class="tools"><div class="search"><input id="listSearch" value="${esc(q)}" placeholder="Search text in this file"></div><span class="note">${rows.length} of ${f.records.length} records</span></div><div class="tools">${reviewCount?`<span class="selection-count">${reviewCount} selected</span><button class="btn soft" id="reviewSelected">${icon("spark")}LLM review</button><button class="btn small" id="autoImproveSelected">${icon("spark")}Auto-improve</button><button class="btn small" id="upsertSelected" ${hasCorpusDb()?"":`disabled data-disabled-reason="${esc(dbUnavailableReason())}"`}>${icon("database")}Upsert selected</button><button class="btn small" id="bulkEditSelected">${icon("edit")}Bulk edit</button><button class="btn small" id="clearSelected">Clear</button>`:""}${flagged?`<button class="btn small soft" id="reviewNeedsReview">${icon("spark")}Review needs-review (${flagged})</button><button class="btn small" id="autoImproveNeedsReview">${icon("spark")}Auto-improve needs-review</button>`:""}${collectionPicker("listStore")}<button class="btn small" id="upsertFile" ${hasCorpusDb()?"":`disabled data-disabled-reason="${esc(dbUnavailableReason())}"`}>${icon("database")}Upsert file</button><button class="btn small" id="selectMatches">Select ${q||Object.keys(filters).length?"matches":"all"}</button><button class="btn small" id="listColumns">Columns</button>${Object.keys(filters).length?'<button class="btn small" id="clearListFilters">Clear column filters</button>':""}<button class="btn small" id="cleanFile">Clean OCR Artifacts</button><select class="control" id="size">${[25,50,100,250].map(n=>`<option ${state.pageSize===n?"selected":""}>${n}</option>`).join("")}</select></div></div>
  <section class="card tablewrap records-table-wrap" tabindex="0" aria-label="${esc(tr("records.table_scroll_label","Records table. Scroll horizontally to view additional columns."))}"><table class="configurable-table"><thead><tr><th class="select-col"><input id="selectPage" type="checkbox" title="Select visible records" ${pageSelected?"checked":""}></th>${columns.map(key=>dataHeadHtml(key,sort)).join("")}<th class="record-actions-head">${esc(tr("research.record_actions","Record actions"))}</th></tr><tr class="column-filter-row"><th></th>${columns.map(key=>`<th>${listFilterControl(f.id,key)}</th>`).join("")}<th></th></tr></thead><tbody>${slice.map(x=>`<tr class="clickable ${state.reviewSelection.has(reviewKey(f,x.index))?"row-selected":""}" data-index="${x.index}"><td class="select-col"><input class="row-select" type="checkbox" data-select-index="${x.index}" ${state.reviewSelection.has(reviewKey(f,x.index))?"checked":""}></td>${columns.map(key=>dataCellHtml(x,key,q)).join("")}${workspaceRecordActionsHtml(x)}</tr>`).join("")||`<tr><td colspan="${columns.length+2}" style="padding:30px;text-align:center;color:#777">No matches</td></tr>`}</tbody></table></section>${pager(pg,rows.length,"list")}`;
  const search=document.querySelector("#listSearch");
  search.oninput=e=>{const pos=e.target.selectionStart;state.searches[f.id]=e.target.value;state.pages[f.id]=1;persistPrefs();syncUrl({replace:true});renderList(main);requestAnimationFrame(()=>{const x=document.querySelector("#listSearch");x.focus();x.setSelectionRange(pos,pos)})};
  document.querySelector("#size").onchange=e=>{state.pageSize=+e.target.value;state.pages[f.id]=1;persistPrefs();syncUrl({replace:true});renderList(main)};
  document.querySelector("#cleanFile").onclick=()=>cleanFile(f);
  document.querySelector("#listStore").onchange=e=>{setActiveStore(e.target.value);renderList(main)};
  document.querySelector("#upsertFile").onclick=()=>upsertRows(f.records.map((record,index)=>({file:f,record,index})),"records").then(()=>renderList(main));
  document.querySelector("#upsertSelected")?.addEventListener("click",()=>upsertRows(rowsFromReviewSelection(),"selected records").then(()=>renderList(main)));
  document.querySelector("#bulkEditSelected")?.addEventListener("click",()=>openBulkFieldEditor({rows:selectedReviewItems(),title:"Bulk edit selected records"}));
  document.querySelector("#selectMatches").onclick=()=>{for(const x of rows)state.reviewSelection.add(reviewKey(f,x.index));persistPrefs();syncUrl({replace:true});renderList(main)};
  document.querySelector("#reviewSelected")?.addEventListener("click",()=>openTouchup(selectedReviewItems()));
  document.querySelector("#autoImproveSelected")?.addEventListener("click",()=>openTouchup(selectedReviewItems(),"auto"));
  document.querySelector("#reviewNeedsReview")?.addEventListener("click",()=>openTouchup(needsReviewItems(f.records.map((record,index)=>({file:f,record,index})))));
  document.querySelector("#autoImproveNeedsReview")?.addEventListener("click",()=>openTouchup(needsReviewItems(f.records.map((record,index)=>({file:f,record,index}))),"auto"));
  document.querySelector("#clearSelected")?.addEventListener("click",()=>{clearReviewSelection();renderList(main)});
  document.querySelector("#listColumns").onclick=()=>openColumnChooser("list",available,()=>renderList(main));
  document.querySelector("#clearListFilters")?.addEventListener("click",()=>{state.listFilters[f.id]={};state.pages[f.id]=1;persistPrefs();syncUrl({replace:true});renderList(main)});
  document.querySelectorAll("[data-list-filter]").forEach(control=>{
    const handler=e=>{
      const key=e.target.dataset.listFilter;
      const value=e.target.value;
      const pos=e.target.selectionStart;
      setListFilterValue(f.id,key,value);
      state.pages[f.id]=1;
      syncUrl({replace:true});
      renderList(main);
      if(e.target.tagName==="INPUT"){
        requestAnimationFrame(()=>{
          const next=document.querySelector(`[data-list-filter="${CSS.escape(key)}"]`);
          if(next){next.focus();const p=Math.min(pos??next.value.length,next.value.length);next.setSelectionRange(p,p)}
        });
      }
    };
    control.addEventListener(control.tagName==="SELECT"?"change":"input",handler);
  });
  document.querySelector("#selectPage").onchange=e=>{for(const x of slice)setReviewSelected(f,x.index,e.target.checked);renderList(main)};
  document.querySelectorAll("[data-select-index]").forEach(box=>box.onchange=e=>{e.stopPropagation();setReviewSelected(f,+box.dataset.selectIndex,box.checked);renderList(main)});
  document.querySelectorAll("[data-sort]").forEach(b=>b.onclick=()=>{toggleSort(sort,b.dataset.sort);state.pages[f.id]=1;persistPrefs();syncUrl({replace:true});renderList(main)});
  document.querySelectorAll("tr[data-index]").forEach(row=>row.onclick=e=>{if(e.target.closest("input,button,summary,details"))return;navigateTo("record",{fileId:f.id,index:+row.dataset.index})});
  wirePager("list",pg,p=>{state.pages[f.id]=p;persistPrefs();syncUrl({replace:true});renderList(main)});
  wireMetadataSearch(main);
  refreshPresenceForRows(slice);
}
function recordAnnotationsHtml(record){
  const annotations=Array.isArray(record?.annotations)?record.annotations:[];
  if(!annotations.length)return `<div class="annotation-empty-state"><span class="annotation-empty-icon">${icon("record")}</span><div><b>${esc(tr("annotations.none_record","No annotations on this record yet"))}</b><p>${esc(tr("annotations.none_record_help","Select text or a displayed value above to attach a note or tags."))}</p></div></div>`;
  return `<div class="record-annotations">${annotations.map((item,index)=>`<article class="record-annotation"><div class="record-annotation-context"><span class="annotation-field-label">${esc(label(item.field||"text"))}</span>${item.quote?`<blockquote>${esc(item.quote)}</blockquote>`:""}</div><div class="record-annotation-body">${item.note?`<p>${esc(item.note)}</p>`:""}${(item.tags||[]).length?`<div class="annotation-tags">${(item.tags||[]).map(tag=>`<span class="chip">${esc(tag)}</span>`).join("")}</div>`:""}<div class="record-annotation-meta"><span>${esc(item.initiated_by||item.author||tr("annotations.unknown_author","Unknown author"))}</span><time>${esc(formatTimestamp(item.created_at))}</time></div></div><button class="btn tiny danger record-annotation-remove" data-remove-annotation="${index}" aria-label="${esc(tr("annotations.remove_title","Remove annotation?"))}">${icon("close")}<span>${esc(tr("ui.remove","Remove"))}</span></button></article>`).join("")}</div>`;
}
function selectionInsideRecordView(){
  const selection=window.getSelection();
  if(!selection||selection.isCollapsed||!selection.rangeCount)return null;
  const quote=String(selection.toString()||"").replace(/\s+/g," ").trim();
  if(!quote)return null;
  const range=selection.getRangeAt(0);
  const node=range.commonAncestorContainer.nodeType===Node.ELEMENT_NODE?range.commonAncestorContainer:range.commonAncestorContainer.parentElement;
  const host=node?.closest?.("[data-annotatable-field]");
  const recordView=document.querySelector(".recordgrid");
  if(!host||!recordView?.contains(host))return null;
  const rect=range.getBoundingClientRect();
  return {quote,field:host.dataset.annotatableField||"text",rect:{left:rect.left,top:rect.top,right:rect.right,bottom:rect.bottom,width:rect.width,height:rect.height}};
}
function positionSelectionToolbar(toolbar,selection){
  if(!toolbar||!selection?.rect)return;
  const rect=selection.rect;
  toolbar.style.position="fixed";
  toolbar.style.left=`${Math.max(12,Math.min(window.innerWidth-260,(rect.left+rect.right)/2-130))}px`;
  toolbar.style.top=`${Math.max(12,rect.top-54)}px`;
  toolbar.style.bottom="auto";
  toolbar.style.margin="0";
}
function openAnnotationPopover(selection,{recordLabel="",onSave}={}){
  if(!selection?.quote||typeof onSave!=="function")return;
  document.querySelector(".selection-annotation-popover")?.remove();
  const {quote,field="text",rect}=selection;
  const popover=document.createElement("section");popover.className="selection-annotation-popover";popover.setAttribute("role","dialog");popover.setAttribute("aria-label",tr("annotations.annotate_selection","Annotate selection"));
  popover.innerHTML=`<div class="selection-annotation-head"><span><b>${esc(tr("annotations.annotate_selection","Annotate selection"))}</b><small>${esc(label(field))}${recordLabel?` · ${esc(recordLabel)}`:""}</small></span><button class="icon-btn" data-close aria-label="${esc(tr("ui.close","Close"))}">×</button></div><blockquote>${esc(quote)}</blockquote><label class="field"><span>${esc(tr("annotations.note","Note"))}</span><textarea id="annotationNote" rows="3" placeholder="${esc(tr("annotations.note_placeholder","Add a note about this selection…"))}"></textarea></label><label class="field"><span>${esc(tr("annotations.tags","Tags"))}</span><input id="annotationTags" class="control" placeholder="${esc(tr("annotations.tags_placeholder","Comma-separated tags"))}"></label><div class="selection-annotation-actions"><button class="btn" data-close>${esc(tr("ui.cancel","Cancel"))}</button><button class="btn primary" id="saveAnnotation">${esc(tr("annotations.save","Save annotation"))}</button></div>`;
  const close=()=>{document.removeEventListener("keydown",onKey);popover.remove()};const onKey=event=>{if(event.key==="Escape"){event.preventDefault();close()}};document.addEventListener("keydown",onKey);popover.querySelectorAll("[data-close]").forEach(button=>button.addEventListener("click",close));
  popover.querySelector("#saveAnnotation")?.addEventListener("click",async()=>{const note=popover.querySelector("#annotationNote")?.value?.trim()||"";const tags=String(popover.querySelector("#annotationTags")?.value||"").split(",").map(value=>value.trim()).filter(Boolean);const button=popover.querySelector("#saveAnnotation");button.disabled=true;try{await onSave({field,quote,note,tags});close()}catch(error){button.disabled=false;toast(error.message||String(error),{tone:"danger"})}});
  document.body.appendChild(popover);
  requestAnimationFrame(()=>{const box=popover.getBoundingClientRect();let left=(rect.left+rect.right)/2-box.width/2;let top=rect.bottom+9;if(top+box.height>window.innerHeight-12)top=Math.max(12,rect.top-box.height-9);left=Math.max(12,Math.min(window.innerWidth-box.width-12,left));popover.style.left=`${Math.round(left)}px`;popover.style.top=`${Math.round(top)}px`;popover.querySelector("#annotationNote")?.focus()});
}
function openTextAnnotationDialog(file,index,selection){
  if(!selection?.quote)return;
  openAnnotationPopover(selection,{recordLabel:String(file.records[index]?.record_id||index+1),onSave:async({field,quote,note,tags})=>{
    const record=file.records[index];
    // Keep the JSONL annotation for provenance while also publishing the same
    // annotation to the shared store. This makes administrator annotations
    // visible to researcher accounts instead of trapping them in one browser.
    const shared=await api("/api/annotations",{method:"POST",body:JSON.stringify({
      store:state.activeStore||null,
      record_id:String(record._chroma_id||record.record_id||index+1),
      work:String(record.work||""),page_start:record.page_start??null,page_end:record.page_end??null,
      field,quote,note,tags,
    })});
    const annotations=Array.isArray(record.annotations)?record.annotations.map(cloneAuditValue):[];
    annotations.push({id:uid(),shared_annotation_id:shared?.id||null,field,quote,note,tags,created_at:shared?.created_at||new Date().toISOString(),initiated_by:state.userContext?.username||null});
    applyRecordChanges(file,index,{annotations},{source:"annotation"});state.annotationsFetchedAt=0;await refreshServerAnnotations(true);shell();renderView();toast(tr("annotations.saved","Record annotation saved"),{tone:"success"});
  }});
}

function renderRecord(main){
  if(isResearcher())return renderResearcherRecord(main);
  const f=activeFile(),r=selectedRecord();
  if(!r){main.innerHTML='<div class="card panel">No record selected.</div>';return}
  const i=selectedIndex(f),key=`${f.id}:${i}`;
  const viewedPointer={kind:"workspace",fileId:f.id,index:i};
  if(JSON.stringify(state.lastViewedRecord)!==JSON.stringify(viewedPointer)){state.lastViewedRecord=viewedPointer;persistPrefs()}
  // Keep the find query while moving between records. The record key is only
  // retained for compatibility with older saved workspaces; clearing is an
  // explicit user action now.
  state.recordFindKey=key;
  const q=state.recordFind;
  const text=String(r.text||"");
  const words=text.trim()?text.trim().split(/\s+/).length:0;
  const quoteFields=["quoted_speaker","quoted_author","quoted_work","quoted_position_holder","quoted_addressee","quoted_referent"];
  const hasQuoteMeta=quoteFields.some(k=>r[k]!=null&&display(r[k])!=="—");
  const links=pdfLinks(r);
  const pdfLoaded=Boolean(state.pdf.file&&state.pdf.name);
  const loadedPdfPages=loadedPdfPagesForRecord(r);
  const loadedPdfRelated=pdfLoaded&&loadedPdfPages.length>0;
  const currentPdfLinked=loadedPdfRelated&&loadedPdfPages.includes(Number(state.pdf.page));
  const linkedPdfName=links[0]?.pdf_file||"";

  main.innerHTML=`
  <div class="toolbar record-toolbar">
    <div class="inline">
      <button class="btn small" id="prev" ${i<=0?"disabled":""}>← Previous</button>
      <span class="note">${(i+1).toLocaleString()} of ${f.records.length.toLocaleString()}</span>
      <button class="btn small" id="next" ${i>=f.records.length-1?"disabled":""}>Next →</button>
      ${dbStatusBadgeHtml(f,i,r)}
    </div>
    <div class="tools">
      ${collectionPicker("recordStore")}
      <button class="btn" id="upsertRecord" ${hasCorpusDb()?"":`disabled data-disabled-reason="${esc(dbUnavailableReason())}"`}>${icon("database")}Upsert record</button>
      <button class="btn soft" id="llmBtn">${icon("spark")}Review with LLM</button>
      <button class="btn" data-copy-row-key="${esc(reviewKey(f,i))}">${icon("copy")}Copy record</button>
      <button class="btn" data-cite-row-key="${esc(reviewKey(f,i))}" data-cite-kind="inline">${icon("copy")}Inline citation</button>
      <button class="btn" data-cite-row-key="${esc(reviewKey(f,i))}" data-cite-kind="full">${icon("copy")}Full citation</button>
      <button class="btn ${evidenceIsSelected(workspaceEvidenceSelectionKey(f,i))?"soft":""}" data-toggle-workspace-evidence="${esc(reviewKey(f,i))}" title="${esc(tr("record.add_evidence_help","Add this record to the selected evidence set used by Research and evidence-only RAG runs."))}">${evidenceIsSelected(workspaceEvidenceSelectionKey(f,i))?icon("check"):icon("plus")}${evidenceIsSelected(workspaceEvidenceSelectionKey(f,i))?"Evidence selected":"Add evidence"}</button>
      <button class="btn ${state.reviewSelection.has(reviewKey(f,i))?"soft":""}" id="queueRecord" title="${esc(tr("record.select_help","Select this record for bulk review, editing, or synchronization actions."))}">${state.reviewSelection.has(reviewKey(f,i))?icon("check"):icon("plus")}${state.reviewSelection.has(reviewKey(f,i))?"Selected":"Select"}</button>
      ${loadedPdfRelated?`<button class="btn primary" id="returnToPdf">${icon("pdf")}PDF: ${esc(pdfDisplayTitle())} · p. ${state.pdf.page}</button>`:""}
      ${!loadedPdfRelated&&links.length?`<button class="btn" id="openPdfExplorer">${icon("pdf")}PDF Explorer</button>`:""}
      ${pdfLoaded?`<button class="btn" id="linkPdf" ${currentPdfLinked?"disabled":""}>${icon("pdf")}${currentPdfLinked?`Linked to p. ${state.pdf.page}`:`Link current PDF p. ${state.pdf.page}`}</button>`:""}
      <button class="btn" id="cleanRecord">${icon("broom")}Clean OCR artifacts</button>
      ${Array.isArray(r.updates)&&r.updates.length?`<button class="btn" id="recordHistoryBtn">${icon("history")}History & undo (${r.updates.length})</button>`:""}
      <div class="search record-find-control"><input id="recordSearch" value="${esc(q)}" placeholder="${esc(tr("record.find_text","Find in record text"))}"><button class="record-find-clear" id="clearRecordFind" type="button" ${q?"":"disabled"} data-disabled-reason="${esc(tr("record.clear_find_empty","Enter a find query before clearing it."))}" title="${esc(tr("record.clear_find","Clear find query"))}"><span>${esc(tr("record.clear_search","Clear search"))}</span></button></div>
    </div>
  </div>
  ${links.length?`<section class="pdf-record-bridge ${loadedPdfRelated?"active":""}">
    <div class="pdf-record-bridge-title">${icon("pdf")}<div><b>${loadedPdfRelated?esc(pdfDisplayTitle()):esc(linkedPdfName||"Linked PDF")}</b><span>${loadedPdfRelated&&state.pdf.author?`${esc(state.pdf.author)} · `:""}${loadedPdfRelated?esc(state.pdf.name):"Open this PDF in Explorer to jump directly between source pages and this record."}</span></div></div>
    <div class="pdf-record-page-links">${links.map((link,linkIndex)=>{
      const canOpen=pdfLoaded&&link.pdf_file===state.pdf.name;
      return `<button class="pdf-page-chip ${canOpen&&Number(link.pdf_page)===Number(state.pdf.page)?"active":""}" data-bridge-pdf-link="${linkIndex}" ${canOpen?"":'title="Load this PDF in PDF Explorer first"'}>p. ${link.pdf_page}</button>`;
    }).join("")}${loadedPdfRelated?`<button class="btn small" id="bridgeBackCurrent">Back to PDF p. ${state.pdf.page}</button>`:`<button class="btn small" id="bridgeOpenExplorer">Open PDF Explorer</button>`}</div>
  </section>`:""}
  <section class="recordgrid">
    <article class="card record-main">
      <div class="headline">
        <div class="eyebrow" data-annotatable-field="record_id">${esc(display(r.record_id))}</div>
        <h1 data-annotatable-field="work">${metadataLinkHtml("work",r.work,{className:"metadata-heading-link"})}</h1>
        <div class="meta">${metadataLinkHtml("document_author",r.document_author)} · ${metadataLinkHtml("year",r.year)} · <span data-annotatable-field="page_start">page ${esc(pages(r))}</span></div>
        <div class="pills">
          <span class="pill">${esc(display(r.region_type))}</span>
          <span class="pill">${r.primary_text===false?"Secondary text":"Primary text"}</span>
          ${r.document_is_translation?'<span class="pill">Translation</span>':""}
          ${r.needs_review?'<span class="pill warn">Needs review</span>':""}
          ${links.length?`<span class="pill">${links.length} PDF link${links.length===1?"":"s"}</span>`:""}
        </div>
      </div>
      <div class="cardhead"><div><b>Extracted text</b><div class="note">${words.toLocaleString()} words · ${text.length.toLocaleString()} characters${q?` · ${countOccurrences(text,q)} matches`:""}</div></div></div>
      <div class="recordtext" data-annotatable-text data-annotatable-field="text">${highlight(text,q)}</div>
      <div class="record-selection-toolbar" id="recordSelectionToolbar" hidden><span id="recordSelectionLabel">Selected value</span><button class="btn tiny primary" id="annotateSelection">Add note / tags</button></div>
      <section class="record-annotation-section"><div class="record-annotation-heading"><div><span class="section-label">${esc(tr("annotations.record_notes","Annotations"))}</span><h3>${esc(tr("annotations.record_annotations","Record annotations"))}</h3><p>${esc(tr("annotations.record_annotations_help","Notes and tags attached to specific evidence in this record."))}</p></div><span class="badge">${Array.isArray(r.annotations)?r.annotations.length:0}</span></div>${recordAnnotationsHtml(r)}</section>
    </article>
    <aside class="side">
      <section class="card">
        <div class="section"><h3>Source</h3><div class="mg">${["document_author","edition","page_start","page_end","region_author","translator","document_language","original_language"].map(k=>metaRow(k,r[k])).join("")}</div></div>
        <div class="section"><h3>Discourse</h3><div class="mg">${["speaker","position_holder","target","discourse_role","proposition_status","stance","claim_scope","is_direct_quote"].map(k=>metaRow(k,r[k])).join("")}</div></div>
        ${hasQuoteMeta?`<div class="section"><h3>Quotation provenance</h3><div class="mg">${quoteFields.map(k=>metaRow(k,r[k])).join("")}</div></div>`:""}
      </section>
      <section class="card record-index-card">
        ${editableChipSection("topics",r.topics)}
        ${editableChipSection("concepts",r.concepts)}
        ${editableChipSection("persons",r.persons)}
      </section>
      <section class="card"><div class="section"><div class="section-title-row"><h3>PDF links</h3><span class="badge">${links.length}</span></div>${links.length?`<div class="record-pdf-links">${links.map((link,linkIndex)=>`<div class="record-pdf-link"><div><b>${esc(pdfLoaded&&link.pdf_file===state.pdf.name?pdfDisplayTitle():link.pdf_file)}</b><span>${esc(link.pdf_file)} · page ${link.pdf_page}</span></div><div class="tools">${pdfLoaded&&link.pdf_file===state.pdf.name?`<button class="btn small" data-open-pdf-link="${linkIndex}">${icon("pdf")}Open page</button>`:`<button class="btn small" data-pdf-explorer-link="${linkIndex}">${icon("pdf")}Explorer</button>`}<button class="btn small danger" data-remove-pdf-link="${linkIndex}">Remove</button></div></div>`).join("")}</div>${links.length>1?'<button class="btn small danger" id="unlinkAllPdf">Remove all PDF links</button>':""}`:'<div class="note">No PDF pages linked to this record.</div>'}</div></section>
      ${r.needs_review?`<section class="card"><div class="section"><h3>Review status</h3><div class="rb">${esc(r.review_reason||"Flagged for review.")}</div></div></section>`:""}
      ${historyHtml(r)}
    </aside>
  </section>`;

  document.querySelector("#prev").onclick=()=>{state.selected[f.id]=i-1;persistPrefs();syncUrl({replace:true});shell();renderView()};
  document.querySelector("#next").onclick=()=>{state.selected[f.id]=i+1;persistPrefs();syncUrl({replace:true});shell();renderView()};
  document.querySelector("#recordStore").onchange=e=>{setActiveStore(e.target.value);renderRecord(main)};
  document.querySelector("#upsertRecord").onclick=()=>upsertRows([{file:f,record:f.records[i],index:i}],"record").then(()=>renderRecord(main));
  document.querySelector("#cleanRecord").onclick=()=>cleanRecord(f,i);
  document.querySelector("#recordHistoryBtn")?.addEventListener("click",()=>openRecordHistoryBrowser(f,i));
  document.querySelector("#llmBtn").onclick=()=>openTouchup([{file:f,index:i,record:f.records[i],key:reviewKey(f,i)}]);
  document.querySelector("#queueRecord").onclick=()=>{const selected=state.reviewSelection.has(reviewKey(f,i));setReviewSelected(f,i,!selected);shell();renderView()};
  document.querySelector("#linkPdf")?.addEventListener("click",()=>linkPdfPage(f,i,state.pdf.page));
  document.querySelector("#returnToPdf")?.addEventListener("click",()=>openLoadedPdfPage(state.pdf.page));
  document.querySelector("#openPdfExplorer")?.addEventListener("click",openPdfExplorerWorkspace);
  document.querySelector("#bridgeBackCurrent")?.addEventListener("click",()=>openLoadedPdfPage(state.pdf.page));
  document.querySelector("#bridgeOpenExplorer")?.addEventListener("click",()=>{
    openPdfExplorerWorkspace();
    toast(`Open ${linkedPdfName||"the linked PDF"} to activate page jumps`);
  });
  document.querySelectorAll("[data-bridge-pdf-link]").forEach(button=>button.onclick=()=>{
    const link=links[+button.dataset.bridgePdfLink];
    if(!link)return;
    if(pdfLoaded&&link.pdf_file===state.pdf.name)openLoadedPdfPage(link.pdf_page);
    else{
      openPdfExplorerWorkspace();
      toast(`Open ${link.pdf_file} to jump to page ${link.pdf_page}`);
    }
  });
  document.querySelectorAll("[data-pdf-explorer-link]").forEach(button=>button.onclick=()=>{
    const link=links[+button.dataset.pdfExplorerLink];
    openPdfExplorerWorkspace();
    if(link)toast(`Open ${link.pdf_file} to jump to page ${link.pdf_page}`);
  });
  document.querySelectorAll("[data-open-pdf-link]").forEach(button=>button.onclick=()=>{
    const link=links[+button.dataset.openPdfLink];
    if(!link)return;
    openLoadedPdfPage(link.pdf_page);
  });
  document.querySelectorAll("[data-remove-pdf-link]").forEach(button=>button.onclick=()=>{
    const link=links[+button.dataset.removePdfLink];
    if(link)unlinkPdfLink(f,i,link);
  });
  document.querySelector("#unlinkAllPdf")?.addEventListener("click",()=>unlinkAllPdfLinks(f,i));
  let selectedAnnotation=null;
  const updateSelectedAnnotation=()=>{
    selectedAnnotation=selectionInsideRecordView();
    const toolbar=document.querySelector("#recordSelectionToolbar");
    if(toolbar){toolbar.hidden=!selectedAnnotation;if(selectedAnnotation)positionSelectionToolbar(toolbar,selectedAnnotation)}
    const labelEl=document.querySelector("#recordSelectionLabel");
    if(labelEl&&selectedAnnotation)labelEl.textContent=`${tr("annotations.selected","Selected")} ${label(selectedAnnotation.field).toLowerCase()}`;
  };
  const annotationGrid=document.querySelector(".recordgrid");annotationGrid?.addEventListener("mouseup",updateSelectedAnnotation);annotationGrid?.addEventListener("keyup",updateSelectedAnnotation);
  document.querySelector("#annotateSelection")?.addEventListener("click",()=>openTextAnnotationDialog(f,i,selectedAnnotation));
  document.querySelectorAll("[data-remove-annotation]").forEach(button=>button.addEventListener("click",async()=>{
    const annotations=Array.isArray(f.records[i].annotations)?f.records[i].annotations.map(cloneAuditValue):[];
    const index=Number(button.dataset.removeAnnotation);if(!Number.isInteger(index)||!annotations[index])return;
    if(!await openMessageModal({title:"Remove record annotation?",message:"Remove this note/tag annotation? The record audit history will retain the change.",tone:"danger",confirmLabel:"Remove",cancelLabel:"Cancel"}))return;
    const sharedId=annotations[index]?.shared_annotation_id;
    if(sharedId){await api(`/api/annotations/${encodeURIComponent(sharedId)}`,{method:"DELETE"});state.annotationsFetchedAt=0;await refreshServerAnnotations(true)}
    annotations.splice(index,1);applyRecordChanges(f,i,{annotations},{source:"annotation"});shell();renderView();toast(tr("annotations.removed","Record annotation removed"),{tone:"success"});
  }));
  wireEditableChips(main,f,i);
  const search=document.querySelector("#recordSearch");
  search.oninput=e=>{
    const pos=e.target.selectionStart;state.recordFind=e.target.value;persistPrefs();renderRecord(main);
    requestAnimationFrame(()=>{const x=document.querySelector("#recordSearch");if(x){x.focus();x.setSelectionRange(pos,pos)}});
  };
  document.querySelector("#clearRecordFind")?.addEventListener("click",()=>{state.recordFind="";persistPrefs();renderRecord(main);requestAnimationFrame(()=>document.querySelector("#recordSearch")?.focus())});
  decorateDisabledControls(main);
  refreshPresenceForRows([{file:f,record:r,index:i}]);
}

function metadataSearchable(field,value){return value!==undefined&&value!==null&&String(value).trim()!==""&&!['text','record_id','inline_citation','full_citation','page_start','page_end'].includes(field)}
function searchByMetadata(field,value,{contains=false}={}){
  const raw=String(value??"").trim();if(!field||!raw)return;state.globalPage=1;state.storeSearchResults=[];
  if(isResearcher()){state.globalSearchMode="database";state.dbSearchMethod="filter";state.dbSearchWhere={[field]:contains?{$contains:raw}:raw};state.globalSearch="";state.globalSearchAutoRun=true}else{state.globalSearchMode="traditional";state.globalSearch="";state.globalFilters=[{id:uid(),field,op:contains?"has":"eq",value:raw}]}
  persistPrefs();navigateTo("global");
}
function wireMetadataSearch(){wireMetadataSearchDelegation()}
function metaRow(k,v){const searchable=metadataSearchable(k,v);return `<div class="mr"><span>${esc(label(k))}</span>${searchable?`<button class="metadata-search-link" type="button" data-meta-search-field="${esc(k)}" data-meta-search-value="${esc(v)}">${esc(display(v))}</button>`:`<b data-annotatable-field="${esc(k)}">${esc(display(v))}</b>`}</div>`}
function metadataLinkHtml(field,value,{className="metadata-inline-link",contains=false,fallback="—"}={}){if(!metadataSearchable(field,value))return esc(value??fallback);return `<button class="${esc(className)}" type="button" data-meta-search-field="${esc(field)}" data-meta-search-value="${esc(value)}" data-meta-search-contains="${contains}">${esc(display(value))}</button>`}
function chips(values){return Array.isArray(values)&&values.length?values.map(v=>`<span class="chip">${esc(display(v))}</span>`).join(""):'<span class="note">None</span>'}

const WORK_METADATA_FIELDS=[
  "work","source_type","document_type","document_title","short_title","original_title","document_author",
  "container_title","journal_title","editor","edition","volume","issue","pages","year","publication_year",
  "publisher","publication_place","translator","document_language","original_language","document_is_translation",
  "canonical_work_id","isbn","doi","url","full_citation","cover_url"
];
function commonWorkValue(rows,field){
  const values=rows.map(row=>row.record[field]);
  if(!values.length)return {mixed:false,value:null};
  const first=JSON.stringify(values[0]??null);
  const mixed=values.some(value=>JSON.stringify(value??null)!==first);
  return {mixed,value:mixed?null:values[0]};
}
function uniqueWorkValues(rows,field){
  const values=new Map();
  for(const row of rows||[]){
    const value=row.record?.[field]??null;
    let token;try{token=JSON.stringify(value)}catch{token=String(value)}
    if(!values.has(token))values.set(token,{value,count:0,files:new Set(),records:[]});
    const entry=values.get(token);entry.count++;entry.files.add(row.file?.name||tr("works.unknown_source","Unknown source"));
    if(entry.records.length<3)entry.records.push(String(row.record?.record_id||row.index+1));
  }
  return [...values.values()].sort((a,b)=>b.count-a.count||String(display(a.value)).localeCompare(String(display(b.value))));
}
function mixedWorkValueButton(rows,field,{compact=false}={}){
  const count=uniqueWorkValues(rows,field).length;
  return `<button type="button" class="mixed-value-inspect ${compact?"compact":""}" data-inspect-mixed-field="${esc(field)}" aria-label="${esc(trf("works.inspect_mixed_aria","Inspect {count} unique values for {field}",{count,field:label(field)}))}"><span>${esc(tr("works.mixed","Mixed"))}</span><b>${count}</b><small>${esc(tr("works.unique_values","values"))}</small></button>`;
}
function openMixedWorkValuesDialog(work,field,rows){
  const values=uniqueWorkValues(rows,field);
  const dialog=document.createElement("dialog");
  dialog.className="mixed-values-dialog";
  dialog.setAttribute("aria-labelledby","mixedValuesTitle");
  dialog.innerHTML=`<div class="dh"><div><span class="section-label">${esc(tr("works.metadata_variants","Metadata variants"))}</span><h2 class="dialog-title" id="mixedValuesTitle">${esc(label(field))}</h2><div class="dialog-subtitle">${esc(work)} · ${values.length.toLocaleString()} ${esc(tr("works.unique_values","unique values"))} · ${rows.length.toLocaleString()} ${esc(tr("dynamic.records","records"))}</div></div><button class="btn icon-only" type="button" data-close aria-label="${esc(tr("ui.close","Close"))}">${icon("close")}</button></div><div class="db mixed-values-body"><p class="note">${esc(tr("works.mixed_values_help","These are the distinct values currently present across records for this work. Counts help distinguish a dominant value from an isolated inconsistency before you bulk-edit metadata."))}</p><div class="mixed-values-list">${values.map((entry,index)=>`<article class="mixed-value-row"><span class="mixed-value-rank">${index+1}</span><div class="mixed-value-copy"><b>${esc(entry.value==null||entry.value===""?tr("ui.unset","Unset"):display(entry.value))}</b><small>${esc([...entry.files].slice(0,3).join(" · "))}${entry.files.size>3?` · +${entry.files.size-3}`:""}</small></div><span class="mixed-value-count">${entry.count.toLocaleString()} <small>${esc(entry.count===1?tr("dynamic.record_one","record"):tr("dynamic.records","records"))}</small></span></article>`).join("")}</div></div><div class="da"><button class="btn primary" type="button" data-close>${esc(tr("ui.done","Done"))}</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
}
function workMetadataControl(field,rows){
  const {mixed,value}=commonWorkValue(rows,field);
  const exemplar=rows.map(row=>row.record[field]).find(value=>value!==undefined&&value!==null);
  const current=mixed?"":value;
  let control;
  if(typeof exemplar==="boolean"||field==="document_is_translation"){
    control=`<select class="control work-meta-value" data-work-meta-value="${esc(field)}"><option value="" ${mixed||current==null?"selected":""}>${mixed?"Mixed / leave unchanged":"Unset"}</option><option value="true" ${current===true?"selected":""}>true</option><option value="false" ${current===false?"selected":""}>false</option></select>`;
  }else if(Array.isArray(exemplar)||exemplar&&typeof exemplar==="object"){
    control=`<textarea class="work-meta-value work-meta-json" data-work-meta-value="${esc(field)}" placeholder='${mixed?"Mixed values — enter JSON to replace":"JSON value"}'>${mixed?"":esc(JSON.stringify(current??[],null,2))}</textarea>`;
  }else if(typeof exemplar==="number"||["year","publication_year"].includes(field)){
    control=`<input class="control work-meta-value" data-work-meta-value="${esc(field)}" type="number" value="${mixed?"":esc(current??"")}" placeholder="${mixed?"Mixed values":""}">`;
  }else if(field==="full_citation"||field==="edition"){
    control=`<textarea class="work-meta-value" data-work-meta-value="${esc(field)}" placeholder="${mixed?"Mixed values":""}">${mixed?"":esc(current??"")}</textarea>`;
  }else{
    control=`<input class="control work-meta-value" data-work-meta-value="${esc(field)}" value="${mixed?"":esc(current??"")}" placeholder="${mixed?"Mixed values":""}">`;
  }
  return `<div class="work-meta-row"><label class="work-meta-apply"><input type="checkbox" data-work-meta-apply="${esc(field)}"><span>${esc(tr("ui.apply","Apply"))}</span></label><div class="work-meta-field"><b>${esc(label(field))}</b>${mixed?mixedWorkValueButton(rows,field,{compact:true}):""}</div>${control}</div>`;
}
function parseWorkMetadataValue(field,control,rows){
  const exemplar=rows.map(row=>row.record[field]).find(value=>value!==undefined&&value!==null);
  const raw=control.value;
  if(typeof exemplar==="boolean"||field==="document_is_translation"){
    if(raw==="")return null;
    return raw==="true";
  }
  if(Array.isArray(exemplar)||exemplar&&typeof exemplar==="object"){
    const parsed=JSON.parse(raw||"null");
    if(exemplar&&Array.isArray(exemplar)&&!Array.isArray(parsed))throw new Error(`${label(field)} must be a JSON array.`);
    return parsed;
  }
  if(typeof exemplar==="number"||["year","publication_year"].includes(field)){
    if(raw.trim()==="")return null;
    const value=Number(raw);
    if(!Number.isFinite(value))throw new Error(`${label(field)} must be numeric.`);
    return value;
  }
  return raw;
}
function openWorkMetadataEditor(work,rows){
  if(!rows?.length)return toast("No records found for this work");
  const available=[...new Set([...WORK_METADATA_FIELDS,...rows.flatMap(row=>Object.keys(row.record).filter(field=>/^(document_|publication_|canonical_|publisher$|translator$|isbn$|full_citation$)/.test(field)))])].filter(field=>field!=="updates");
  const dialog=document.createElement("dialog");
  dialog.className="work-metadata-dialog";
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Edit work metadata</h2><div class="dialog-subtitle">${esc(work)} · ${rows.length.toLocaleString()} associated records across ${new Set(rows.map(row=>row.file.name)).size} files</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db work-metadata-body"><div class="info">Check <b>Apply</b> only for fields that should be changed across every associated record. Changing <code>work</code> renames the work for all loaded records. Every modified field is written to each record's <code>updates</code> history.</div><div class="work-meta-table">${available.map(field=>workMetadataControl(field,rows)).join("")}</div></div>
  <div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="applyWorkMetadata">Apply selected metadata to ${rows.length.toLocaleString()} records</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelectorAll("[data-inspect-mixed-field]").forEach(button=>button.onclick=()=>openMixedWorkValuesDialog(work,button.dataset.inspectMixedField,rows));
  dialog.querySelector("#applyWorkMetadata").onclick=async()=>{
    const selected=[...dialog.querySelectorAll("[data-work-meta-apply]:checked")].map(box=>box.dataset.workMetaApply);
    if(!selected.length)return toast("Select at least one work metadata field to apply");
    const changes={};
    try{
      for(const field of selected){
        const control=dialog.querySelector(`[data-work-meta-value="${CSS.escape(field)}"]`);
        changes[field]=parseWorkMetadataValue(field,control,rows);
      }
    }catch(error){return toast(error.message)}
    if(!await openMessageModal({title:"Apply work metadata?",message:`Apply ${selected.length} metadata field${selected.length===1?"":"s"} to all ${rows.length} records associated with ${work}?`,confirmLabel:"Apply metadata",cancelLabel:"Cancel"}))return;
    const applyButton=dialog.querySelector("#applyWorkMetadata");if(applyButton){applyButton.disabled=true;applyButton.textContent=tr("works.applying_metadata","Applying metadata…")}
    const batchId=uid();let changedRecords=0,fieldChanges=0;const touchedFiles=new Set();
    for(const row of rows){
      const count=applyRecordChanges(row.file,row.index,changes,{source:"work_metadata",batchId,reason:`Bulk work metadata update for ${work}`});
      if(count){changedRecords++;fieldChanges+=count;touchedFiles.add(row.file)}
    }
    for(const file of touchedFiles)await persistFileNow(file);
    close();shell();renderView();
    toast(trf("works.metadata_applied","Updated {records} records · {fields} tracked field changes",{records:changedRecords.toLocaleString(),fields:fieldChanges.toLocaleString()}),{tone:"success"});
  };
}


const WORK_METADATA_LLM_FIELDS=[
  "source_type","document_type","document_title","short_title","document_author","container_title","journal_title",
  "editor","edition","volume","issue","pages","year","publication_year","publisher","publication_place",
  "translator","document_language","document_is_translation","isbn","doi","url","full_citation","cover_url"
];
function representativeWorkMetadata(rows){
  const metadata={};
  for(const field of WORK_METADATA_LLM_FIELDS){
    const values=rows.map(row=>row.record?.[field]).filter(value=>value!==undefined&&value!==null&&value!=="");
    if(!values.length)continue;
    const counts=new Map();
    for(const value of values){const key=JSON.stringify(value);counts.set(key,(counts.get(key)||0)+1)}
    const [winner]=[...counts.entries()].sort((a,b)=>b[1]-a[1])[0]||[];
    if(winner!==undefined){try{metadata[field]=JSON.parse(winner)}catch{metadata[field]=values[0]}}
  }
  const work=rows[0]?.record?.work;
  if(work)metadata.work=work;
  return metadata;
}
function workCoverUrl(rows){
  return String(rows.map(row=>row.record?.cover_url).find(Boolean)||"").trim();
}
function workOverviewMetadataRows(rows){
  const fields=["document_title","document_author","edition","year","publication_year","publisher","publication_place","translator","isbn","document_language","original_language","canonical_work_id","full_citation"];
  return fields.map(field=>({field,...commonWorkValue(rows,field)})).filter(item=>item.mixed||item.value!==undefined&&item.value!==null&&item.value!=="");
}
function workflowProviderSelectHtml(selectedId){
  const profiles=providerProfiles();
  const selected=providerProfile(selectedId)||profiles[0]||null;
  if(!profiles.length)return `<div class="workflow-provider-empty"><b>${esc(tr("language.no_provider_profiles","No LLM provider profiles are configured"))}</b><p>${esc(tr("language.no_provider_profiles_help","Create a provider profile first, then return here."))}</p></div>`;
  return `<label class="workflow-field workflow-provider-select-field"><span>${esc(tr("works.provider_profile","Provider profile"))}</span><select class="control workflow-provider-select" id="workMetadataProvider">${profiles.map(profile=>`<option value="${esc(profile.id)}" ${profile.id===selected?.id?"selected":""}>${esc(providerDisplayName(profile))} · ${profile.type==="ollama"?"Ollama":"OpenAI-compatible"} · ${esc(profile.model||tr("language.model_not_set","model not set"))}${profile.id===state.appConfig.default_provider_profile?` · ${esc(tr("ui.default","Default"))}`:""}</option>`).join("")}</select><small>${esc(tr("works.provider_profile_help","Uses the same configured provider profiles as Research, PDF tools, and LLM review."))}</small></label><div class="workflow-provider-summary" id="workMetadataProviderSummary">${workflowProviderSummaryHtml(selected)}</div>`;
}
function workflowProviderSummaryHtml(profile){
  if(!profile)return "";
  return `<span class="workflow-provider-mark">${profile.type==="ollama"?"O":"AI"}</span><span><b>${esc(providerDisplayName(profile))}</b><small>${profile.type==="ollama"?"Ollama":"OpenAI-compatible"} · ${esc(profile.model||tr("language.model_not_set","model not set"))}</small><small>${Number(profile.max_concurrent_requests??1)} ${esc(tr("works.concurrent_requests","max concurrent request(s)"))}</small></span>${profile.id===state.appConfig.default_provider_profile?`<span class="provider-default-chip">${esc(tr("ui.default","Default"))}</span>`:""}`;
}

function openWorkMetadataLlmDialog(items){
  const works=(items||[]).filter(item=>item?.work&&item?.rows?.length);
  if(!works.length)return toast(tr("works.no_work_metadata_rows","No work records are available for metadata lookup."));
  const profiles=providerProfiles();
  const selectedId=state.appConfig.default_provider_profile||profiles[0]?.id||"";
  const dialog=document.createElement("dialog");
  dialog.className="workflow-dialog work-metadata-llm-dialog";
  const sample=works.slice(0,6).map(item=>`<span>${esc(item.work)}</span>`).join("");
  dialog.innerHTML=`<div class="workflow-dialog-header"><div class="workflow-heading"><span class="workflow-icon">${icon("spark")}</span><div><p>${esc(tr("works.metadata_workflow_kicker","Bibliographic enrichment"))}</p><h2>${esc(tr("works.populate_metadata_llm","Populate metadata with LLM"))}</h2><span>${esc(tr("works.populate_metadata_help","DerridAI searches format-appropriate public bibliographic sources (Open Library, Google Books, and Crossref), asks the selected LLM to identify the best match, then returns proposed metadata changes for review. Nothing is applied automatically."))}</span></div></div><button class="icon-btn workflow-close" data-close title="${esc(tr("ui.close","Close"))}">×</button></div>
    <ol class="workflow-steps"><li class="active"><span>1</span><b>${esc(tr("works.step_scope","Works"))}</b></li><li class="active"><span>2</span><b>${esc(tr("works.step_provider","Provider profile"))}</b></li><li><span>3</span><b>${esc(tr("works.step_review","Review proposals"))}</b></li></ol>
    <div class="workflow-form"><section class="workflow-section"><div class="workflow-section-copy"><b>${esc(tr("works.lookup_scope","Lookup scope"))}</b><span>${esc(trf("works.lookup_scope_help","Retrieve bibliographic metadata for {count} work(s).",{count:works.length.toLocaleString()}))}</span></div><div class="work-metadata-scope"><strong>${works.length.toLocaleString()} ${esc(tr("dynamic.works","works"))}</strong><div class="work-metadata-sample">${sample}${works.length>6?`<span>+${works.length-6}</span>`:""}</div><small>${esc(tr("works.metadata_fields_help","Proposals can include source type, container/journal, volume/issue/pages, publisher, year, edition, translator/editor, ISBN/DOI, language, MLA citation, and cover image."))}</small></div></section>
    <section class="workflow-section"><div class="workflow-section-copy"><b>${esc(tr("works.provider_profile","Provider profile"))}</b><span>${esc(tr("works.provider_profile_help","Uses the same configured provider profiles as RAG, PDF tools, and LLM review."))}</span></div><div class="workflow-provider-area">${workflowProviderSelectHtml(selectedId)}<button type="button" class="btn small" id="manageWorkProviders">${esc(tr("language.manage_providers","Manage provider profiles"))}</button></div></section>
    <section class="workflow-review-strip"><span class="workflow-summary-icon">${icon("history")}</span><span><b>${esc(tr("works.background_operation","Background operation"))}</b><small>${esc(tr("works.background_operation_help","You can leave the Works page. Open the completed operation to review and apply proposed changes."))}</small></span><span><b>${esc(tr("works.catalog_source","Catalogue source"))}</b><small>Open Library · Google Books · Crossref</small></span></section></div>
    <div class="workflow-actions"><button class="btn" data-close>${esc(tr("ui.cancel","Cancel"))}</button><button class="btn primary" id="startWorkMetadata" ${profiles.length?"":`disabled data-disabled-reason="${esc(tr("works.no_provider_profiles_help","Create an LLM provider profile before populating work metadata."))}"`}>${icon("spark")}${esc(tr("works.start_metadata_lookup","Start background lookup"))}</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);decorateDisabledControls(dialog);
  const close=()=>{dialog.close();dialog.remove()};dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelector("#workMetadataProvider")?.addEventListener("change",event=>{const profile=providerProfile(event.target.value);const summary=dialog.querySelector("#workMetadataProviderSummary");if(summary)summary.innerHTML=workflowProviderSummaryHtml(profile)});
  dialog.querySelector("#manageWorkProviders")?.addEventListener("click",async()=>{const ok=await openMessageModal({title:tr("works.leave_metadata_title","Open provider profiles?"),message:tr("works.leave_metadata_help","This will close the metadata workflow and navigate to LLM Providers. Your lookup has not started yet."),confirmLabel:tr("works.open_providers","Open providers"),cancelLabel:tr("ui.cancel","Cancel")});if(!ok)return;close();navigateTo("providers")});
  dialog.querySelector("#startWorkMetadata")?.addEventListener("click",async()=>{
    const profileId=dialog.querySelector("#workMetadataProvider")?.value||selectedId;
    const profile=providerProfile(profileId);
    if(!profile)return toast(tr("works.provider_required","Select an LLM provider profile."));
    const config=providerRequestConfig(profile,{textReview:false});
    if(!config?.model)return toast(tr("works.provider_model_required","The selected provider profile does not have a model configured."));
    const payload=works.map(item=>({work:item.work,current_metadata:representativeWorkMetadata(item.rows)}));
    const button=dialog.querySelector("#startWorkMetadata");button.disabled=true;button.textContent=tr("works.starting_metadata_lookup","Starting…");
    try{
      const job=await api("/api/jobs/llm-tool",{method:"POST",body:JSON.stringify({task:"work_metadata",label:works.length===1?`${tr("works.populate_metadata_llm","Populate metadata with LLM")} · ${works[0].work}`:trf("works.populate_all_metadata_label","Populate metadata · {count} works",{count:works.length}),provider_profile_id:profile.id,max_concurrent_requests:config.max_concurrent_requests,work_metadata:{works:payload,provider:config.provider,model:config.model,base_url:config.base_url,api_key:config.api_key,generation:config.ollama,provider_profile_id:profile.id}})});
      state.jobs=[job,...state.jobs.filter(existing=>existing.id!==job.id)];syncJobProgressToasts();startJobPolling();close();toast(trf("works.metadata_lookup_started","Metadata lookup started for {count} work(s).",{count:works.length}));if(state.view==="home")renderDashboard(document.querySelector("#main"));
    }catch(error){button.disabled=false;button.innerHTML=`${icon("spark")}${esc(tr("works.start_metadata_lookup","Start background lookup"))}`;openMessageModal({title:tr("works.metadata_lookup_failed","Could not start metadata lookup"),message:error.message||String(error),tone:"danger"})}
  });
}
function parseProposedMetadataValue(raw,original){
  if(typeof original==="number"){const value=Number(raw);if(!Number.isFinite(value))throw new Error("Expected a number.");return value}
  if(typeof original==="boolean")return String(raw).toLowerCase()==="true";
  return raw;
}
function openWorkMetadataProposalResult(job){
  const proposals=Array.isArray(job.result?.proposals)?job.result.proposals:[];
  const map=workIndex();
  const flattened=[];
  for(const proposal of proposals){
    const item=map.get(String(proposal.work||""));
    if(!item)continue;
    const current=representativeWorkMetadata(item.rows);
    for(const [field,proposed] of Object.entries(proposal.changes||{}))flattened.push({proposal,item,field,current:current[field],proposed,rationale:proposal.rationale?.[field]||proposal.match_reason||""});
  }
  const dialog=document.createElement("dialog");dialog.className="work-metadata-proposal-dialog";
  const errors=proposals.filter(item=>item.error||item.message&&!Object.keys(item.changes||{}).length);
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${esc(tr("works.review_metadata_proposals","Review work metadata proposals"))}</h2><div class="dialog-subtitle">${esc(jobLabel(job))} · ${flattened.length.toLocaleString()} ${esc(tr("works.proposed_field_changes","proposed field changes"))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db work-proposal-body">${errors.length?`<div class="info warn">${esc(trf("works.metadata_no_match_count","{count} work(s) had no usable catalogue match or returned an error.",{count:errors.length}))}</div>`:""}<div class="work-proposal-toolbar"><button class="btn small" id="selectAllWorkProposals">${esc(tr("ui.select_all","Select all"))}</button><button class="btn small" id="clearWorkProposals">${esc(tr("ui.clear","Clear"))}</button><span class="note">${esc(tr("works.proposal_edit_help","Edit proposed values if needed, then apply selected fields across every loaded record belonging to that work."))}</span></div>${flattened.length?`<div class="work-proposal-table-wrap"><table class="work-proposal-table"><thead><tr><th></th><th>${esc(tr("nav.works","Work"))}</th><th>${esc(tr("works.field","Field"))}</th><th>${esc(tr("works.current_value","Current"))}</th><th>${esc(tr("works.proposed_value","Proposed"))}</th><th>${esc(tr("works.source_reason","Source / reason"))}</th></tr></thead><tbody>${flattened.map((entry,index)=>`<tr><td><input type="checkbox" data-work-proposal-select="${index}" checked></td><td><b>${esc(entry.item.work)}</b><small>${entry.item.count.toLocaleString()} ${esc(tr("dynamic.records","records"))}</small></td><td>${esc(label(entry.field))}</td><td><div class="proposal-current">${esc(display(entry.current))}</div></td><td><textarea class="control proposal-value" data-work-proposal-value="${index}" rows="2">${esc(entry.proposed==null?"":typeof entry.proposed==="object"?JSON.stringify(entry.proposed):String(entry.proposed))}</textarea></td><td><small>${esc(entry.rationale||tr("works.catalogue_selected","Public bibliographic catalogue match selected by the LLM."))}</small>${entry.proposal.confidence!=null?`<span class="proposal-confidence">${Math.round(Number(entry.proposal.confidence||0)*100)}%</span>`:""}</td></tr>`).join("")}</tbody></table></div>`:`<div class="llm-empty">${esc(tr("works.no_metadata_changes","No metadata changes were proposed."))}</div>`}${errors.length?`<details class="work-proposal-errors"><summary>${esc(tr("works.unmatched_works","Unmatched / failed works"))}</summary>${errors.map(item=>`<div><b>${esc(item.work)}</b><span>${esc(item.error||item.message||tr("works.no_catalogue_match","No catalogue match"))}</span></div>`).join("")}</details>`:""}</div><div class="da"><button class="btn" data-close>${esc(tr("ui.close","Close"))}</button><button class="btn primary" id="applyWorkProposals" ${flattened.length?"":"disabled"}>${icon("check")}${esc(tr("works.apply_selected_metadata","Apply selected metadata"))}</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);decorateDisabledControls(dialog);
  const close=()=>{dialog.close();dialog.remove()};dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelector("#selectAllWorkProposals")?.addEventListener("click",()=>dialog.querySelectorAll("[data-work-proposal-select]").forEach(box=>box.checked=true));
  dialog.querySelector("#clearWorkProposals")?.addEventListener("click",()=>dialog.querySelectorAll("[data-work-proposal-select]").forEach(box=>box.checked=false));
  dialog.querySelector("#applyWorkProposals")?.addEventListener("click",async()=>{
    const selected=[...dialog.querySelectorAll("[data-work-proposal-select]:checked")].map(box=>Number(box.dataset.workProposalSelect)).filter(index=>flattened[index]);
    if(!selected.length)return toast(tr("works.select_metadata_changes","Select at least one proposed metadata change."));
    const grouped=new Map();
    try{
      for(const index of selected){const entry=flattened[index];const control=dialog.querySelector(`[data-work-proposal-value="${index}"]`);const value=parseProposedMetadataValue(control.value,entry.proposed);if(!grouped.has(entry.item.work))grouped.set(entry.item.work,{item:entry.item,changes:{},rationale:{}});const group=grouped.get(entry.item.work);group.changes[entry.field]=value;group.rationale[entry.field]=entry.rationale}
    }catch(error){return toast(error.message)}
    const recordCount=[...grouped.values()].reduce((sum,group)=>sum+group.item.rows.length,0);
    const applyButton=dialog.querySelector("#applyWorkProposals");if(applyButton){applyButton.disabled=true;applyButton.textContent=tr("works.applying_metadata","Applying metadata…")}
    const batchId=uid();let changedRecords=0,fieldChanges=0;const touchedFiles=new Set();
    try{
      for(const group of grouped.values())for(const row of group.item.rows){const count=applyRecordChanges(row.file,row.index,group.changes,{source:"work_metadata_llm",model:job.model,batchId,reason:`LLM-assisted bibliographic metadata update for ${group.item.work}`,rationale:group.rationale});if(count){changedRecords++;fieldChanges+=count;touchedFiles.add(row.file)}}
      for(const file of touchedFiles)await persistFileNow(file);
      state.jobApplied[job.id]=new Date().toISOString();persistPrefs();close();shell();renderView();toast(trf("works.metadata_applied","Updated {records} records · {fields} tracked field changes",{records:changedRecords.toLocaleString(),fields:fieldChanges.toLocaleString()}),{tone:"success"});
    }catch(error){if(applyButton){applyButton.disabled=false;applyButton.textContent=tr("works.apply_selected_metadata","Apply selected metadata")}toast(error.message||String(error),{tone:"danger"})}
  });
}

function parseBulkFieldValue(field,raw,rows){
  const sample=rows.map(row=>row.record?.[field]).find(value=>value!==undefined&&value!==null);
  const text=String(raw??"");
  if(text.trim()==="__NULL__")return null;
  if(typeof sample==="boolean"){
    const token=text.trim().toLowerCase();
    if(["true","1","yes","on"].includes(token))return true;
    if(["false","0","no","off"].includes(token))return false;
    throw new Error(`Enter true or false for ${label(field)}.`);
  }
  if(typeof sample==="number"){
    const value=Number(text);
    if(!Number.isFinite(value))throw new Error(`${label(field)} requires a number.`);
    return value;
  }
  if(Array.isArray(sample)||sample&&typeof sample==="object"){
    try{
      const value=JSON.parse(text);
      if(Array.isArray(sample)&&!Array.isArray(value))throw new Error("Expected JSON array.");
      if(!Array.isArray(sample)&&(Array.isArray(value)||!value||typeof value!=="object"))throw new Error("Expected JSON object.");
      return value;
    }catch(error){
      throw new Error(`${label(field)} requires valid JSON: ${error.message}`);
    }
  }
  return text;
}
function bulkEditRowsForScope(scope){
  if(scope==="selected")return selectedReviewItems();
  if(scope==="active"){
    const file=activeFile();
    return file?file.records.map((record,index)=>({file,record,index,key:reviewKey(file,index)})):[];
  }
  if(scope==="work"){
    const selected=selectedRecord();
    const work=selected?.work;
    return work?allRows().filter(row=>row.record.work===work):[];
  }
  return allRows();
}
const SUBSET_PROFILE_STORAGE_KEY="derridai.subset-filter-profiles.v1";
function loadSubsetProfiles(){
  try{const value=JSON.parse(localStorage.getItem(SUBSET_PROFILE_STORAGE_KEY)||"[]");return Array.isArray(value)?value:[]}catch{return []}
}
function saveSubsetProfiles(profiles){
  localStorage.setItem(SUBSET_PROFILE_STORAGE_KEY,JSON.stringify((profiles||[]).slice(0,50)));
}

function openSubsetBuilder(){
  if(!state.files.length)return toast("Load one or more JSONL files first");
  const dialog=document.createElement("dialog");
  dialog.className="subset-dialog";
  const fields=recordFields().filter(field=>!field.startsWith("_"));
  const sourceOptions=[
    `<option value="active">Active JSONL · ${esc(activeFile()?.name||"")}</option>`,
    `<option value="all">All loaded JSONL files</option>`,
    ...state.files.map(file=>`<option value="${esc(file.id)}">Only ${esc(file.name)} · ${file.records.length.toLocaleString()} records</option>`),
  ].join("");
  const fieldOptions=fields.map(field=>`<option value="${esc(field)}">${esc(label(field))} · ${esc(field)}</option>`).join("");
  const operatorOptions=[["equals","Equals"],["not_equals","Does not equal"],["contains","Contains"],["not_contains","Does not contain"],["array_contains","Array contains exact value"],["exists","Exists / non-empty"],["missing","Missing / empty"],["truthy","Truthy"],["falsy","Falsy"],["regex","Regular expression"]].map(([value,name])=>`<option value="${value}">${name}</option>`).join("");
  const profiles=loadSubsetProfiles();
  dialog.innerHTML=`<div class="dh subset-dialog-head"><div><span class="section-label">Corpus utility</span><h2 class="dialog-title">Create JSONL subset</h2><div class="dialog-subtitle">Build reusable record filters without editing the source JSONL.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db subset-body subset-body-v3">
    <section class="subset-config-card"><div class="subset-config-copy"><b>Source & output</b><span>Choose the loaded records to filter and the name of the derived JSONL tab.</span></div><div class="subset-head-grid"><div class="field"><label>Source</label><select class="control" id="subsetSource">${sourceOptions}</select></div><div class="field"><label>New JSONL tab name</label><input class="control" id="subsetName" value="${esc((activeFile()?.name||"subset.jsonl").replace(/\.jsonl$/i,""))}-subset.jsonl"></div><label class="check-item subset-case"><input type="checkbox" id="subsetCase"><span>Case-sensitive matching</span></label></div></section>
    <section class="subset-config-card"><div class="subset-config-copy"><b>Saved filter profile</b><span>Reuse common corpus slices such as primary Derrida text, one language, or records needing review.</span></div><div class="subset-profile-row"><select class="control" id="subsetProfile"><option value="">No saved profile</option>${profiles.map(profile=>`<option value="${esc(profile.id)}">${esc(profile.name)}</option>`).join("")}</select><button class="btn small" id="saveSubsetProfile">${icon("plus")}Save current</button><button class="btn small danger" id="deleteSubsetProfile" disabled>Delete</button></div></section>
    <section class="subset-config-card subset-filter-card"><div class="subset-config-copy"><b>Filter expression</b><span>Conditions are readable, grouped explicitly, and previewed against the selected source as you edit.</span></div><div class="subset-expression" id="subsetExpression"></div><div class="subset-builder-actions"><button class="btn small" id="addSubsetRule">${icon("plus")}Condition</button><button class="btn small" id="addSubsetGroup">${icon("plus")}Group</button><span class="subset-match-count" id="subsetPreview">Add at least one condition.</span></div><div class="subset-expression-preview" id="subsetExpressionPreview"></div></section>
  </div>
  <div class="da"><button class="btn" data-close>Cancel</button><button class="btn" id="createSubsetDownload">Create & download</button><button class="btn primary" id="createSubset">Create subset tab</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  const expression=dialog.querySelector("#subsetExpression");
  let previewTimer=null;
  const schedulePreview=()=>{clearTimeout(previewTimer);previewTimer=setTimeout(updatePreview,120)};

  const subsetAutocompleteExcluded=new Set(["text","extracted_text","extractedText","raw_text","ocr_text"]);
  function ruleHtml({field="work",operator="equals",value=""}={}){
    return `<div class="subset-rule-core"><select class="control subset-field">${fieldOptions}</select><select class="control subset-operator">${operatorOptions}</select><input class="control subset-value" placeholder="${esc(tr("subset.value","Value"))}" autocomplete="off"><datalist class="subset-value-options"></datalist><button class="btn icon-only danger subset-remove" type="button" title="${esc(tr("subset.remove_condition","Remove condition"))}" aria-label="${esc(tr("subset.remove_condition","Remove condition"))}">${icon("close")}</button></div>`;
  }
  function initializeRule(row,{field="work",operator="equals",value=""}={}){
    row.querySelector(".subset-field").value=fields.includes(field)?field:fields[0]||"";
    row.querySelector(".subset-operator").value=operator;
    row.querySelector(".subset-value").value=value;
    const input=row.querySelector(".subset-value"),datalist=row.querySelector(".subset-value-options");
    const listId=`subset-values-${uid()}`;datalist.id=listId;
    const syncSuggestions=()=>{
      const fieldName=row.querySelector(".subset-field").value;
      if(subsetAutocompleteExcluded.has(fieldName)){input.removeAttribute("list");datalist.innerHTML="";input.title=tr("subset.autocomplete_large_field","Autocomplete is disabled for large text fields.");return}
      const values=new Set();
      for(const {record} of selectedRows()){
        const raw=record?.[fieldName];
        const items=Array.isArray(raw)?raw:[raw];
        for(const item of items){if(item===null||item===undefined||typeof item==="object")continue;const text=String(item).trim();if(text)values.add(text)}
      }
      const ordered=[...values].sort((a,b)=>a.localeCompare(b,undefined,{numeric:true,sensitivity:"base"}));
      datalist.innerHTML=ordered.map(option=>`<option value="${esc(option)}"></option>`).join("");
      if(ordered.length){input.setAttribute("list",listId);input.title=trf("subset.autocomplete_count","{count} unique values from the selected JSONL source.",{count:ordered.length.toLocaleString()})}
      else{input.removeAttribute("list");input.title=""}
    };
    const syncValue=()=>{
      const noValue=["exists","missing","truthy","falsy"].includes(row.querySelector(".subset-operator").value);
      input.disabled=noValue;
      input.placeholder=noValue?tr("subset.no_value","No value required"):tr("subset.value","Value");
      if(noValue)input.value="";
      if(noValue)input.removeAttribute("list");else syncSuggestions();
    };
    row.querySelectorAll("select,input").forEach(control=>control.addEventListener("input",()=>{syncValue();schedulePreview()}));
    row.querySelector(".subset-remove").onclick=()=>{
      const group=row.closest(".subset-group");
      row.remove();
      if(group&&!group.querySelector(".subset-group-rules .subset-rule-row"))group.remove();
      normalizeTopJoins();updatePreview();
    };
    syncValue();
  }
  function topJoinHtml(){return `<select class="control subset-join"><option value="AND">AND</option><option value="OR">OR</option></select>`}
  function addTopRule(config={}){
    const item=document.createElement("div");
    item.className="subset-expression-item subset-top-rule";
    item.dataset.kind="rule";
    item.innerHTML=`${topJoinHtml()}<div class="subset-rule-row">${ruleHtml(config)}</div>`;
    expression.appendChild(item);
    initializeRule(item.querySelector(".subset-rule-row"),config);
    item.querySelector(".subset-join").addEventListener("change",schedulePreview);
    normalizeTopJoins();updatePreview();
  }
  function addGroup({mode="OR",rules=null}={}){
    const item=document.createElement("div");
    item.className="subset-expression-item subset-group";
    item.dataset.kind="group";
    item.innerHTML=`${topJoinHtml()}<div class="subset-group-box"><div class="subset-group-head"><div><b>Grouped conditions</b><span>Parentheses: evaluate this block as one boolean value</span></div><div class="tools"><select class="control subset-group-mode"><option value="OR">Match ANY (OR)</option><option value="AND">Match ALL (AND)</option></select><button class="btn tiny" type="button" data-add-group-rule>${icon("plus")}Condition</button><button class="btn tiny danger" type="button" data-remove-group>Remove group</button></div></div><div class="subset-group-rules"></div></div>`;
    expression.appendChild(item);
    item.querySelector(".subset-group-mode").value=mode;
    const list=item.querySelector(".subset-group-rules");
    const addInner=(config={})=>{
      const row=document.createElement("div");row.className="subset-rule-row";row.innerHTML=ruleHtml(config);list.appendChild(row);initializeRule(row,config);updatePreview();
    };
    (rules?.length?rules:[{field:"topics",operator:"array_contains",value:""},{field:"concepts",operator:"array_contains",value:""}]).forEach(addInner);
    item.querySelector("[data-add-group-rule]").onclick=()=>addInner({field:fields.includes("topics")?"topics":fields[0],operator:"contains",value:""});
    item.querySelector("[data-remove-group]").onclick=()=>{item.remove();normalizeTopJoins();updatePreview()};
    item.querySelector(".subset-group-mode").addEventListener("change",schedulePreview);
    item.querySelector(".subset-join").addEventListener("change",schedulePreview);
    normalizeTopJoins();updatePreview();
  }
  function normalizeTopJoins(){
    [...expression.querySelectorAll(":scope > .subset-expression-item")].forEach((item,index)=>{
      const join=item.querySelector(":scope > .subset-join");
      join.disabled=index===0;
      if(index===0)join.value="AND";
    });
  }
  function selectedRows(){
    const source=dialog.querySelector("#subsetSource").value;
    if(source==="all")return allRows();
    if(source==="active"){const file=activeFile();return file?file.records.map((record,index)=>({file,record,index})):[]}
    const file=state.files.find(item=>item.id===source);return file?file.records.map((record,index)=>({file,record,index})):[];
  }
  function readRule(row){return {field:row.querySelector(".subset-field").value,operator:row.querySelector(".subset-operator").value,value:row.querySelector(".subset-value").value}}
  function readExpression(){
    return [...expression.querySelectorAll(":scope > .subset-expression-item")].map((item,index)=>{
      const base={join:index===0?"AND":item.querySelector(":scope > .subset-join").value,type:item.dataset.kind};
      if(item.dataset.kind==="group")return {...base,mode:item.querySelector(".subset-group-mode").value,rules:[...item.querySelectorAll(".subset-group-rules .subset-rule-row")].map(readRule)};
      return {...base,rule:readRule(item.querySelector(".subset-rule-row"))};
    });
  }
  function itemMatches(record,item,caseSensitive){
    if(item.type==="group"){
      const values=item.rules.map(rule=>subsetRuleMatches(record,rule,caseSensitive));
      return item.mode==="AND"?values.every(Boolean):values.some(Boolean);
    }
    return subsetRuleMatches(record,item.rule,caseSensitive);
  }
  function recordMatchesExpression(record,items,caseSensitive){
    if(!items.length)return false;
    const groups=[];let group=[];
    for(const item of items){if(item.join==="OR"&&group.length){groups.push(group);group=[]}group.push(item)}
    if(group.length)groups.push(group);
    return groups.some(itemsInAndGroup=>itemsInAndGroup.every(item=>itemMatches(record,item,caseSensitive)));
  }
  function expressionText(items){
    const oneRule=rule=>`${label(rule.field)} ${dialog.querySelector(`.subset-operator option[value="${CSS.escape(rule.operator)}"]`)?.textContent||rule.operator}${["exists","missing","truthy","falsy"].includes(rule.operator)?"":` “${rule.value}”`}`;
    return items.map((item,index)=>{
      const prefix=index?` ${item.join} `:"";
      if(item.type==="group")return `${prefix}(${item.rules.map(oneRule).join(` ${item.mode} `)})`;
      return `${prefix}${oneRule(item.rule)}`;
    }).join("");
  }
  function matchedRows(){const items=readExpression();if(!items.length)return [];const caseSensitive=dialog.querySelector("#subsetCase").checked;return selectedRows().filter(({record})=>recordMatchesExpression(record,items,caseSensitive))}
  function updatePreview(){
    const items=readExpression(),sourceCount=selectedRows().length,matched=items.length?matchedRows().length:0;
    dialog.querySelector("#subsetPreview").textContent=items.length?`${matched.toLocaleString()} of ${sourceCount.toLocaleString()} source records match`:"Add at least one condition.";
    dialog.querySelector("#subsetExpressionPreview").innerHTML=items.length?`<b>Expression</b><code>${esc(expressionText(items))}</code>`:"";
    decorateDisabledControls(dialog);
  }
  const refreshSubsetSuggestions=()=>expression.querySelectorAll(".subset-rule-row").forEach(row=>row.querySelector(".subset-field")?.dispatchEvent(new Event("input",{bubbles:false})));
  const applyProfile=profile=>{
    expression.innerHTML="";
    for(const item of profile?.expression||[]){
      if(item?.type==="group"){addGroup({mode:item.mode||"OR",rules:item.rules||[]});const added=expression.lastElementChild;if(added&&item.join)added.querySelector(":scope > .subset-join").value=item.join}
      else if(item?.rule){addTopRule(item.rule);const added=expression.lastElementChild;if(added&&item.join)added.querySelector(":scope > .subset-join").value=item.join}
    }
    dialog.querySelector("#subsetCase").checked=Boolean(profile?.caseSensitive);
    normalizeTopJoins();refreshSubsetSuggestions();updatePreview();
  };
  const profileSelect=dialog.querySelector("#subsetProfile");
  profileSelect?.addEventListener("change",()=>{
    const profile=loadSubsetProfiles().find(item=>item.id===profileSelect.value);
    dialog.querySelector("#deleteSubsetProfile").disabled=!profile;
    if(profile)applyProfile(profile);
  });
  dialog.querySelector("#saveSubsetProfile")?.addEventListener("click",async()=>{
    const items=readExpression();if(!items.length)return toast("Add at least one condition before saving a profile");
    const name=prompt("Filter profile name");if(!name?.trim())return;
    const profiles=loadSubsetProfiles();const profile={id:uid(),name:name.trim(),expression:items,caseSensitive:dialog.querySelector("#subsetCase").checked,created_at:new Date().toISOString()};
    profiles.push(profile);saveSubsetProfiles(profiles);
    profileSelect.insertAdjacentHTML("beforeend",`<option value="${esc(profile.id)}">${esc(profile.name)}</option>`);profileSelect.value=profile.id;dialog.querySelector("#deleteSubsetProfile").disabled=false;toast(`Saved filter profile “${profile.name}”`,{tone:"success"});
  });
  dialog.querySelector("#deleteSubsetProfile")?.addEventListener("click",()=>{
    const id=profileSelect.value;if(!id)return;const profiles=loadSubsetProfiles();const profile=profiles.find(item=>item.id===id);saveSubsetProfiles(profiles.filter(item=>item.id!==id));profileSelect.querySelector(`option[value="${CSS.escape(id)}"]`)?.remove();profileSelect.value="";dialog.querySelector("#deleteSubsetProfile").disabled=true;if(profile)toast(`Deleted filter profile “${profile.name}”`);
  });
  dialog.querySelector("#addSubsetRule").onclick=()=>addTopRule({field:fields.includes("work")?"work":fields[0],operator:"equals",value:""});
  dialog.querySelector("#addSubsetGroup").onclick=()=>addGroup();
  dialog.querySelector("#subsetSource")?.addEventListener("change",()=>{refreshSubsetSuggestions();schedulePreview()});
  dialog.querySelector("#subsetCase")?.addEventListener("change",schedulePreview);
  const createSubset=async downloadFile=>{
    const items=readExpression();const rows=matchedRows();if(!items.length)return toast("Add at least one subset condition");if(!rows.length)return toast("No records match the subset expression");
    let name=dialog.querySelector("#subsetName").value.trim()||"subset.jsonl";if(!name.toLowerCase().endsWith(".jsonl"))name+=".jsonl";
    const file={id:uid(),name,records:rows.map(({record})=>cloneAuditValue(record)),errors:[],dirty:new Set(),imported_at:new Date().toISOString(),subset:{created_at:new Date().toISOString(),source:dialog.querySelector("#subsetSource").value,logic:"grouped_boolean_v2",expression:items}};
    state.files.push(file);state.activeFileId=file.id;await persistFileNow(file);
    if(downloadFile){const blob=new Blob([file.records.map(record=>JSON.stringify(record)).join("\n")+"\n"],{type:"application/x-ndjson"});downloadBlob(blob,name)}
    close();navigateTo("list",{fileId:file.id});toast(`Created ${name} with ${file.records.length.toLocaleString()} records`);
  };
  dialog.querySelector("#createSubset").onclick=()=>createSubset(false);
  dialog.querySelector("#createSubsetDownload").onclick=()=>createSubset(true);
  addTopRule({field:fields.includes("document_author")?"document_author":fields[0],operator:"equals",value:"Jacques Derrida"});
}

function openBulkFieldEditor({rows=null,title="Bulk edit one field"}={}){
  if(!state.files.length)return toast("Load JSONL records first");
  const dialog=document.createElement("dialog");
  dialog.className="bulk-field-dialog";
  const fields=recordFields().filter(field=>field!=="updates"&&!field.startsWith("_"));
  const selectedCount=selectedReviewItems().length;
  const activeCount=activeFile()?.records.length||0;
  const currentWork=selectedRecord()?.work||"";
  const fixedRows=Array.isArray(rows)?rows:null;
  const defaultScope=fixedRows?"fixed":selectedCount?"selected":"active";
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">Apply one field value consistently across a selected record set. Every actual change is audited.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db bulk-field-body">
    ${fixedRows?`<div class="info">${fixedRows.length.toLocaleString()} records are in this operation.</div>`:`<div class="field"><label>Target records</label><select class="control" id="bulkFieldScope"><option value="selected" ${defaultScope==="selected"?"selected":""} ${selectedCount?"":"disabled"}>Selected records (${selectedCount.toLocaleString()})</option><option value="active" ${defaultScope==="active"?"selected":""}>Active JSONL (${activeCount.toLocaleString()})</option>${currentWork?`<option value="work">Current work: ${esc(currentWork)}</option>`:""}<option value="all">All loaded records (${allRows().length.toLocaleString()})</option></select></div>`}
    <div class="field"><label>Field</label><select class="control" id="bulkFieldName">${fields.map(field=>`<option value="${esc(field)}">${esc(label(field))} · ${esc(field)}</option>`).join("")}</select></div>
    <div class="field"><label>New value</label><textarea id="bulkFieldValue" spellcheck="false" placeholder="Enter the new value. Arrays/objects use JSON. Enter __NULL__ for null."></textarea><div class="note" id="bulkFieldHint"></div></div>
    <label class="check-item"><input type="checkbox" id="bulkFieldOnlyDifferent" checked><span>Only modify records whose value actually differs</span></label>
  </div>
  <div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="applyBulkField">${icon("check")}Apply field update</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);

  const currentRows=()=>fixedRows||bulkEditRowsForScope(dialog.querySelector("#bulkFieldScope")?.value||"active");
  let lastHintField="";
  const updateHint=()=>{
    const field=dialog.querySelector("#bulkFieldName").value;
    const target=currentRows();
    const rawValues=target.slice(0,300).map(row=>row.record?.[field]);
    const values=[...new Set(rawValues.map(value=>JSON.stringify(value)))];
    dialog.querySelector("#bulkFieldHint").textContent=`${target.length.toLocaleString()} target records · ${values.length} distinct current value${values.length===1?"":"s"}${values.length>8?" (sampled)":""}`;
    const input=dialog.querySelector("#bulkFieldValue");
    if(values.length===1&&(lastHintField!==field||!input.value.trim())){
      const only=rawValues[0];
      input.value=only===null?"__NULL__":Array.isArray(only)||only&&typeof only==="object"?JSON.stringify(only,null,2):String(only??"");
    }else if(lastHintField!==field&&values.length!==1)input.value="";
    lastHintField=field;
  };
  dialog.querySelector("#bulkFieldScope")?.addEventListener("change",updateHint);
  dialog.querySelector("#bulkFieldName").addEventListener("change",updateHint);
  updateHint();

  dialog.querySelector("#applyBulkField").onclick=async()=>{
    const target=currentRows();
    if(!target.length)return toast("No records are in the selected scope");
    const field=dialog.querySelector("#bulkFieldName").value;
    let value;
    try{value=parseBulkFieldValue(field,dialog.querySelector("#bulkFieldValue").value,target)}
    catch(error){return toast(error.message)}
    const changing=target.filter(row=>!sameValue(row.record?.[field],value));
    if(!changing.length)return toast("Every target record already has that value");
    if(!await openMessageModal({title:"Apply bulk field update?",message:`Set ${field} on ${changing.length.toLocaleString()} record${changing.length===1?"":"s"}?`,confirmLabel:"Apply update",cancelLabel:"Cancel"}))return;
    const batchId=uid();let fieldChanges=0;
    for(const row of changing){
      fieldChanges+=applyRecordChanges(row.file,row.index,{[field]:cloneAuditValue(value)},{
        source:"bulk_field_edit",
        batchId,
        reason:`Bulk edit ${field}`,
      });
    }
    close();shell();renderView();
    toast(`Updated ${field} on ${changing.length.toLocaleString()} records · ${fieldChanges.toLocaleString()} audited changes`);
  };
}

function clearFileDerivedState(fileId){
  state.reviewSelection=new Set([...state.reviewSelection].filter(key=>!String(key).startsWith(fileId+"::")));
  delete state.selected[fileId];
  for(const bucket of [state.upsertState,state.upsertIgnored,state.storePresence,state.storePresenceIds,state.storePresenceCheckedAt]){
    for(const store of Object.keys(bucket||{})){
      for(const key of Object.keys(bucket[store]||{}))if(key.startsWith(fileId+"::"))delete bucket[store][key];
    }
  }
}

async function openRemoveWorkModal(work,rows){
  const fileCounts=new Map();
  for(const row of rows)fileCounts.set(row.file,(fileCounts.get(row.file)||0)+1);
  const dialog=document.createElement("dialog");
  dialog.className="message-dialog danger remove-work-dialog";
  const dbStore=state.activeStore&&recordStores().some(store=>store.name===state.activeStore)?state.activeStore:"";
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Remove entire work</h2><div class="dialog-subtitle">${esc(work)} · destructive operation</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db remove-work-body"><div class="info warn">Remove every record for this work from selected loaded JSONL files and, optionally, from the selected Chroma collection. Primary collection deletion also removes matching records from its language collections.</div>
    <div class="remove-work-files">${[...fileCounts].map(([file,count])=>`<label class="check-item"><input type="checkbox" data-remove-work-file="${esc(file.id)}" checked><span><b>${esc(file.name)}</b><small>${count.toLocaleString()} matching record${count===1?"":"s"}</small></span></label>`).join("")}</div>
    <label class="check-item"><input type="checkbox" id="removeWorkDb" ${dbStore?"":`disabled data-disabled-reason="Select or create a corpus vector database first." title="Select or create a corpus vector database first."`}><span><b>Also remove from Chroma</b><small>${dbStore?esc(dbStore):"Select a corpus collection first"}</small></span></label></div>
    <div class="da"><button class="btn" data-close>Cancel</button><button class="btn danger" id="confirmRemoveWork">Remove work</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelector("#confirmRemoveWork").onclick=async()=>{
    const fileIds=[...dialog.querySelectorAll("[data-remove-work-file]:checked")].map(input=>input.dataset.removeWorkFile);
    const removeDb=Boolean(dialog.querySelector("#removeWorkDb")?.checked&&dbStore);
    if(!fileIds.length&&!removeDb)return toast("Select at least one JSONL file or the Chroma collection");
    const button=dialog.querySelector("#confirmRemoveWork");button.disabled=true;button.textContent="Removing…";
    let localDeleted=0,dbDeleted=0,mirrored=0;
    try{
      for(const fileId of fileIds){
        const file=state.files.find(item=>item.id===fileId);if(!file)continue;
        const before=file.records.length;
        file.records=file.records.filter(record=>String(record.work||"(Untitled work)")!==work);
        const removed=before-file.records.length;
        if(removed){
          localDeleted+=removed;
          clearFileDerivedState(file.id);
          file.dirty=new Set([file.records.length?0:-1]);
          await persistFileNow(file);
        }
      }
      if(removeDb){
        const result=await api(`/api/stores/${encodeURIComponent(dbStore)}/works/${encodeURIComponent(work)}`,{method:"DELETE"});
        dbDeleted=Number(result.deleted||0);
        mirrored=Object.values(result.mirrored_deletes||{}).reduce((sum,value)=>sum+Number(value||0),0);
        state.storeWorksStore="";
        if(state.storePresence[dbStore])state.storePresence[dbStore]={};
        if(state.storePresenceIds[dbStore])state.storePresenceIds[dbStore]={};
        await refreshStores();
      }
      close();persistPrefs();shell();renderView();
      toast(`Removed “${work}” · ${localDeleted.toLocaleString()} local record${localDeleted===1?"":"s"}${removeDb?` · ${dbDeleted.toLocaleString()} DB${mirrored?` · ${mirrored.toLocaleString()} language mirror`:""}`:""}`);
    }catch(error){button.disabled=false;button.textContent="Remove work";openMessageModal({title:"Could not remove work",message:error.message,tone:"danger"})}
  };
}

async function openSeparateWorksModal(){
  const eligible=state.files.filter(file=>{const works=new Set(file.records.map(record=>String(record?.work||record?.document_title||"").trim()).filter(Boolean));return works.size>1});
  if(!eligible.length)return toast("No loaded JSONL file contains multiple named works");
  const dialog=document.createElement("dialog");dialog.className="work-separate-dialog";
  const options=eligible.map(file=>`<option value="${esc(file.id)}">${esc(file.name)} · ${file.records.length.toLocaleString()} records</option>`).join("");
  dialog.innerHTML=`<div class="dh"><div><span class="section-label">JSONL organization</span><h2 class="dialog-title">Separate works from a JSONL file</h2><div class="dialog-subtitle">Create one derived JSONL tab per selected work while preserving record metadata and audit history.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db separate-works-body"><div class="field"><label>Source JSONL</label><select class="control" id="separateWorksSource">${options}</select></div><div id="separateWorksList" class="separate-works-list"></div><label class="check-item"><input type="checkbox" id="separateWorksRemove"><span>Remove separated records from the source tab after creating the new tabs</span></label><div class="info">By default this is non-destructive: new tabs are created as copies. Enable removal only when you want to partition the original loaded JSONL.</div></div><div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="separateWorksCreate">Separate selected works</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);const close=()=>{dialog.close();dialog.remove()};dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  const source=()=>state.files.find(file=>file.id===dialog.querySelector("#separateWorksSource").value);
  const renderList=()=>{const file=source();const groups=new Map();for(const record of file?.records||[]){const work=String(record?.work||record?.document_title||"").trim()||"(Untitled work)";if(!groups.has(work))groups.set(work,[]);groups.get(work).push(record)}dialog.querySelector("#separateWorksList").innerHTML=[...groups.entries()].map(([work,records])=>`<label class="separate-work-row"><input type="checkbox" data-separate-work="${esc(work)}" ${work==="(Untitled work)"?"":"checked"}><span><b>${esc(work)}</b><small>${records.length.toLocaleString()} records</small></span></label>`).join("")};
  dialog.querySelector("#separateWorksSource").addEventListener("change",renderList);renderList();
  dialog.querySelector("#separateWorksCreate").onclick=async()=>{const file=source();const selected=[...dialog.querySelectorAll("[data-separate-work]:checked")].map(box=>box.dataset.separateWork);if(!selected.length)return toast("Select at least one work");const selectedSet=new Set(selected);const created=[];for(const work of selected){const records=file.records.filter(record=>(String(record?.work||record?.document_title||"").trim()||"(Untitled work)")===work).map(cloneAuditValue);if(!records.length)continue;const stem=work.replace(/[^a-z0-9]+/gi,"-").replace(/^-|-$/g,"").slice(0,80)||"untitled-work";const derived={id:uid(),name:`${stem}.jsonl`,records,errors:[],dirty:new Set(),imported_at:new Date().toISOString(),derived_from:{type:"work_separation",source_file:file.name,work}};state.files.push(derived);await persistFileNow(derived);created.push(derived)}if(dialog.querySelector("#separateWorksRemove").checked){file.records=file.records.filter(record=>!selectedSet.has(String(record?.work||record?.document_title||"").trim()||"(Untitled work)"));file.dirty=new Set(file.records.map((_,index)=>index));await persistFileNow(file)}if(created.length)state.activeFileId=created[0].id;close();corpusCache.fields=null;persistPrefs();shell();renderView();toast(`Created ${created.length} work JSONL tab${created.length===1?"":"s"}`,{tone:"success"})};
}

async function renderWorks(main){
  if(isResearcher())return renderResearcherWorks(main);
  // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  try{await refreshServerAnnotations()}catch{}
  if(Date.now()-Number(state.storesLastFetchedAt||0)>5000){
    showViewLoading(main,tr("works.loading","Loading works"),tr("works.checking_database","Checking vector database state…"));
    try{await refreshStores()}catch(error){console.warn("Could not refresh vector stores for Works",error)}
    if(state.view!=="works")return;
  }
  const token=nextProgressiveRenderToken();
  const map=workIndex();
  const works=[...map.values()].filter(x=>!state.worksSearch||x.work.toLocaleLowerCase().includes(state.worksSearch.toLocaleLowerCase())).sort((a,b)=>a.work.localeCompare(b.work));
  const totalRecords=[...map.values()].reduce((sum,item)=>sum+item.count,0);
  const noDbReason=dbUnavailableReason();
  const profiles=providerProfiles();
  if(state.workOverview&&!map.has(state.workOverview))state.workOverview="";
  const selected=state.workOverview?map.get(state.workOverview):null;

  const metadataValue=(rows,field)=>{const value=commonWorkValue(rows,field);return value.mixed?mixedWorkValueButton(rows,field):esc(display(value.value))};
  const overviewHtml=selected?(()=>{
    const cover=workCoverUrl(selected.rows);
    const coreFields=["source_type","document_author","container_title","journal_title","volume","issue","pages","publisher","publication_year","edition","translator","editor","publication_place","isbn","doi","document_language","original_language"];
    const citationText=fullCitation(selected.rows[0]?.record||{work:selected.work},{includePages:false});
    const annotationCount=allAnnotations().filter(item=>String(item.work||"")===String(selected.work)).length;
    return `<section class="card work-overview-card"><div class="work-overview-cover">${cover?`<img src="${esc(cover)}" alt="${esc(trf("works.cover_alt","Cover of {work}",{work:selected.work}))}" loading="lazy">`:`<div class="work-cover-placeholder">${icon("books")}</div>`}</div><div class="work-overview-content"><div class="work-overview-heading"><div><span class="section-label">${esc(tr("works.overview","Work overview"))}</span><h1>${esc(selected.work)}</h1><p>${selected.count.toLocaleString()} ${esc(tr("dynamic.records","records"))} · ${selected.files.size.toLocaleString()} ${esc(tr("works.source_files","source files"))}</p></div><span class="db-status ${workDbStatus(selected.rows,selected.work).kind}"><i></i>${esc(workDbStatus(selected.rows,selected.work).label)}</span></div><div class="work-overview-metadata">${coreFields.map(field=>`<div><span>${esc(label(field))}</span><b>${metadataValue(selected.rows,field)}</b></div>`).join("")}</div><div class="work-overview-citation"><span>${esc(label("full_citation"))}</span><p>${esc(citationText)}</p></div>${workInsightsPanelHtml(selected.rows,selected.work)}<div class="work-overview-actions"><button class="btn primary" id="overviewSearchWork">${icon("search")}${esc(tr("works.search_records","Search records"))}</button><button class="btn" id="overviewEditWork">${icon("edit")}${esc(tr("works.edit_metadata","Edit work metadata"))}</button><button class="btn soft" id="overviewPopulateWork">${icon("spark")}${esc(tr("works.populate_metadata_llm","Populate metadata with LLM"))}</button>${annotationCount?`<button class="btn" id="overviewAnnotations">${icon("record")}${esc(trf("works.view_annotations","Annotations ({count})",{count:annotationCount.toLocaleString()}))}</button>`:""}</div></div></section>`;
  })():"";

  const addJsonlCard=()=>`<button type="button" class="work-add-jsonl-card" id="worksAddJsonl" ${canUse("manageCorpus")?"":`disabled data-disabled-reason="${esc(tr("permissions.corpus_manage_denied","Your role cannot load corpus files."))}"`}><span class="work-add-jsonl-icon">${icon("plus")}</span><span><b>${esc(tr("works.add_jsonl","Add a JSONL file"))}</b><small>${esc(tr("works.add_jsonl_help","Open another corpus source and add its works to this workspace."))}</small></span></button>`;

  const workCard=x=>{
    const status=workDbStatus(x.rows,x.work),cover=workCoverUrl(x.rows);
    const publisher=commonWorkValue(x.rows,"publisher"),translator=commonWorkValue(x.rows,"translator"),year=commonWorkValue(x.rows,"publication_year");
    return `<article class="card work work-library-card ${state.workOverview===x.work?"selected":""}" data-work="${esc(x.work)}"><div class="work-card-cover">${cover?`<img src="${esc(cover)}" alt="" loading="lazy">`:`<div class="work-cover-placeholder">${icon("books")}</div>`}</div><div class="work-card-body"><div class="work-top"><div class="work-main-copy"><div class="work-title-line"><h2>${esc(x.work)}</h2><span class="db-status ${status.kind}" data-work-status="${esc(x.work)}"><i></i>${esc(status.label)}</span></div><div class="note">${esc([...x.authors].join(", ")||tr("works.unknown_author","Unknown author"))}${year.value?` · ${esc(year.value)}`:x.years.size?` · ${esc([...x.years].sort().join(", "))}`:""}</div><div class="work-card-biblio">${publisher.mixed?`<span>${esc(label("publisher"))} ${mixedWorkValueButton(x.rows,"publisher",{compact:true})}</span>`:publisher.value?`<span>${esc(publisher.value)}</span>`:""}${translator.mixed?`<span>${esc(tr("works.translated_by","Translated by"))} ${mixedWorkValueButton(x.rows,"translator",{compact:true})}</span>`:translator.value?`<span>${esc(tr("works.translated_by","Translated by"))} ${esc(translator.value)}</span>`:""}</div></div><div class="work-primary-actions"><button class="btn small" data-upsert-work="${esc(x.work)}" ${hasCorpusDb()?"":`disabled data-disabled-reason="${esc(noDbReason)}"`}>${icon("database")}${esc(tr("works.sync","Sync"))}</button><details class="work-action-menu"><summary class="btn small" title="${esc(tr("ui.more_actions","More actions"))}">${esc(tr("ui.actions","Actions"))}</summary><div class="work-action-popover"><button class="btn small" data-populate-work="${esc(x.work)}">${icon("spark")}${esc(tr("works.populate_metadata_llm","Populate metadata with LLM"))}</button><button class="btn small" data-edit-work-meta="${esc(x.work)}">${icon("edit")}${esc(tr("works.edit_metadata","Edit metadata"))}</button>${x.review?`<button class="btn small soft" data-review-work="${esc(x.work)}">${icon("spark")}${esc(trf("works.review_flagged","Review flagged ({count})",{count:x.review}))}</button><button class="btn small" data-auto-work="${esc(x.work)}">${icon("spark")}${esc(tr("works.auto_improve","Auto-improve flagged"))}</button>`:""}<button class="btn small danger" data-remove-work="${esc(x.work)}">${icon("close")}${esc(tr("works.remove_entire","Remove entire work"))}</button></div></details></div></div><div class="stats"><button type="button" class="stat work-stat-link" data-work-records="${esc(x.work)}" aria-label="${esc(trf("works.open_records_for_work","Open {count} records for {work}",{count:x.count,work:x.work}))}"><strong>${x.count}</strong><span>${esc(tr("dynamic.records","records"))}</span></button><button type="button" class="stat work-stat-link" data-work-review="${esc(x.work)}" ${x.review?"":"disabled"} aria-label="${esc(trf("works.open_review_records_for_work","Open {count} records needing review for {work}",{count:x.review,work:x.work}))}"><strong>${x.review}</strong><span>${esc(tr("works.need_review","need review"))}</span></button><div class="stat"><strong>${x.files.size}</strong><span>${esc(tr("works.files","files"))}</span></div></div></div></article>`;
  };

  const activeStoreInfo=recordStores().find(store=>store.name===state.activeStore)||null;
  const dbContext=`<section class="card works-database-context"><div><span class="section-label">${esc(tr("works.database_context","Works synchronization database"))}</span><b>${esc(state.activeStore||tr("research.none_selected","No database selected"))}</b><small>${esc(tr("works.database_context_help","Sync status and Sync actions on this page refer to the selected corpus database. Changing it does not change your loaded JSONL files."))}</small></div><label class="field"><span>${esc(tr("research.corpus_database","Corpus database"))}</span>${collectionPicker("worksStore")}<small>${activeStoreInfo?`${Number(activeStoreInfo.count||0).toLocaleString()} ${esc(tr("dynamic.records","records"))}`:esc(noDbReason)}</small></label></section>`;
  main.innerHTML=`${dbContext}${overviewHtml}<div class="toolbar works-toolbar aligned-toolbar"><div class="search"><input id="worksSearch" value="${esc(state.worksSearch)}" placeholder="${esc(tr("works.filter_title","Filter works by title"))}"></div><div class="tools"><button class="btn small" id="separateWorks">${icon("filter")}${esc(tr("works.separate_jsonl","Separate works"))}</button><button class="btn small soft" id="populateAllWorks" ${profiles.length&&map.size?"":`disabled data-disabled-reason="${esc(profiles.length?tr("works.no_works_to_populate","No works are available to populate."):tr("works.no_provider_profiles_help","Create an LLM provider profile before populating work metadata."))}"`}>${icon("spark")}${esc(tr("works.populate_all_metadata","Populate all metadata with LLM"))}</button><button class="btn small primary" id="syncAllWorks" ${state.activeStore&&totalRecords&&hasCorpusDb()?"":`disabled data-disabled-reason="${esc(noDbReason||tr("works.select_collection","Select a corpus collection first."))}"`}>${icon("database")}${esc(tr("works.sync_all","Sync all works"))}</button><span class="note">${works.length.toLocaleString()} ${esc(tr("works.shown","shown"))} · ${map.size.toLocaleString()} ${esc(tr("dynamic.works","works"))} · ${totalRecords.toLocaleString()} ${esc(tr("dynamic.records","records"))}</span></div></div><section class="works works-library-grid" id="worksGrid"></section>`;
  const grid=main.querySelector("#worksGrid");
  progressiveRender(grid,works,workCard,{batchSize:12,label:trf("works.loading_cards","Loading {count} work cards",{count:works.length.toLocaleString()}),token,onDone:()=>{
    if(state.view!=="works"||token!==progressiveRenderToken)return;
    grid.insertAdjacentHTML("beforeend",addJsonlCard());
    grid.querySelector("#worksAddJsonl")?.addEventListener("click",()=>document.querySelector("#fileInput")?.click());
    decorateDisabledControls(grid);
    refreshPresenceForRows(works.slice(0,24).flatMap(item=>item.rows.slice(0,2)));
  }});

  let searchTimer=null;
  const search=main.querySelector("#worksSearch");
  search.oninput=e=>{
    const value=e.target.value,pos=e.target.selectionStart;state.worksSearch=value;persistPrefs();clearTimeout(searchTimer);
    searchTimer=setTimeout(()=>{if(state.view!=="works")return;syncUrl({replace:true});renderWorks(main);requestAnimationFrame(()=>{const x=main.querySelector("#worksSearch");if(x){x.focus();x.setSelectionRange(pos,pos)}})},180);
  };
  main.querySelector("#worksStore").onchange=e=>{setActiveStore(e.target.value);renderWorks(main)};
  main.querySelector("#separateWorks")?.addEventListener("click",()=>openSeparateWorksModal());
  main.querySelector("#syncAllWorks")?.addEventListener("click",async()=>{const rows=[...map.values()].flatMap(item=>item.rows);const ok=await upsertRows(rows,tr("works.all_records_label","records across all works"));if(ok)renderWorks(main)});
  main.querySelector("#populateAllWorks")?.addEventListener("click",()=>openWorkMetadataLlmDialog([...map.values()].sort((a,b)=>a.work.localeCompare(b.work))));
  main.querySelector("#overviewSearchWork")?.addEventListener("click",()=>{state.globalSearch="";state.globalFilters=[{id:uid(),field:"work",op:"eq",value:selected.work}];state.globalPage=1;persistPrefs();navigateTo("global")});
  main.querySelector("#overviewEditWork")?.addEventListener("click",()=>openWorkMetadataEditor(selected.work,selected.rows));
  main.querySelector("#overviewPopulateWork")?.addEventListener("click",()=>openWorkMetadataLlmDialog([selected]));
  main.querySelector("#overviewAnnotations")?.addEventListener("click",()=>{state.annotationSearch=selected.work;state.annotationView="works";persistPrefs();navigateTo("annotations")});
  main.querySelectorAll("[data-inspect-mixed-field]").forEach(button=>button.addEventListener("click",()=>openMixedWorkValuesDialog(selected.work,button.dataset.inspectMixedField,selected.rows)));
  main.querySelectorAll("[data-work-insight-field]").forEach(button=>button.addEventListener("click",()=>searchByMetadata(button.dataset.workInsightField,button.dataset.workInsightValue,{contains:["persons","concepts","topics"].includes(button.dataset.workInsightField)})));
  const openWorkSearch=(work,{needsReview=false}={})=>{state.globalSearchMode="traditional";state.globalSearch="";state.globalFilters=[{id:uid(),field:"work",op:"eq",value:work},...(needsReview?[{id:uid(),field:"needs_review",op:"eq",value:"true"}]:[])];state.globalPage=1;persistPrefs();navigateTo("global")};
  grid.addEventListener("click",e=>{
    const target=e.target;
    const action=target.closest("button");
    if(action){
      e.stopPropagation();
      if(action.dataset.workRecords!==undefined)return openWorkSearch(action.dataset.workRecords);
      if(action.dataset.workReview!==undefined)return openWorkSearch(action.dataset.workReview,{needsReview:true});
      if(action.dataset.inspectMixedField!==undefined){const card=action.closest("[data-work]"),work=card?.dataset.work||"";return openMixedWorkValuesDialog(work,action.dataset.inspectMixedField,map.get(work)?.rows||[])}
      if(action.dataset.populateWork!==undefined){const work=action.dataset.populateWork;return openWorkMetadataLlmDialog([map.get(work)])}
      if(action.dataset.editWorkMeta!==undefined){const work=action.dataset.editWorkMeta;return openWorkMetadataEditor(work,map.get(work)?.rows||[])}
      if(action.dataset.upsertWork!==undefined){const work=action.dataset.upsertWork;return upsertRows(map.get(work)?.rows||[],`work “${work}”`).then(()=>renderWorks(main))}
      if(action.dataset.removeWork!==undefined){const work=action.dataset.removeWork;return openRemoveWorkModal(work,map.get(work)?.rows||[])}
      if(action.dataset.reviewWork!==undefined){const work=action.dataset.reviewWork;return openTouchup(needsReviewItems(map.get(work)?.rows||[]))}
      if(action.dataset.autoWork!==undefined){const work=action.dataset.autoWork;return openTouchup(needsReviewItems(map.get(work)?.rows||[]),"auto")}
    }
    if(target.closest("details,summary"))return;
    const card=target.closest("[data-work]");
    if(card){const y=window.scrollY;state.workOverview=card.dataset.work||"";persistPrefs();syncUrl({replace:true});renderWorks(main);requestAnimationFrame(()=>window.scrollTo(0,y))}
  });
  const needsWorkStats=hasCorpusDb()&&state.storeWorksStore!==state.activeStore;
  if(needsWorkStats)refreshStoreWorks().then(()=>{if(state.view==="works"&&token===progressiveRenderToken)renderWorks(document.querySelector("#main"))}).catch(error=>console.warn("Could not load work DB counts",error));
  decorateDisabledControls(main);
}

function recordFields(){
  if(corpusCache.fields)return corpusCache.fields;
  const set=new Set();
  allRows().forEach(x=>Object.keys(x.record).forEach(k=>set.add(k)));
  corpusCache.fields=[...set].sort();
  return corpusCache.fields;
}

function dbFilterDisplayValue(value){return value&&typeof value==="object"&&"$contains" in value?`${tr("research.contains","contains")} ${value.$contains}`:String(value??"")}
function dbSearchWhere(){return Object.fromEntries(Object.entries(state.dbSearchWhere||{}).filter(([,value])=>String(value??"").trim()!==""))}
function safeDbSearchWhere(method=state.dbSearchMethod){
  const safe={};
  for(const [rawField,rawValue] of Object.entries(dbSearchWhere())){
    const field=String(rawField||"").trim();
    if(!field||field.startsWith("$"))continue;
    if(method==="filter"&&rawValue&&typeof rawValue==="object"&&!Array.isArray(rawValue)&&Object.prototype.hasOwnProperty.call(rawValue,"$contains")){
      const value=String(rawValue.$contains??"").trim();if(value)safe[field]={$contains:value};continue;
    }
    if(["string","number","boolean"].includes(typeof rawValue)&&String(rawValue).trim()!=="")safe[field]=rawValue;
  }
  return safe;
}
function researcherDbRecords(){
  const map=new Map();
  for(const item of state.storeSearchResults||[]){const record=item.record||{};const id=String(item.id||record._chroma_id||record.record_id||"");if(id)map.set(id,{...record,_chroma_id:id})}
  for(const record of state.storeRecords||[]){const id=String(record._chroma_id||record.record_id||"");if(id&&!map.has(id))map.set(id,record)}
  return [...map.values()];
}
function searchResultLayout(mode=state.globalSearchMode){
  const key=mode==="database"?"database":"traditional",value=state.searchResultLayouts?.[key]|| (key==="database"?"cards":"compact");return ["compact","roomy","cards"].includes(value)?value:(key==="database"?"cards":"compact");
}
function searchLayoutControls(mode=state.globalSearchMode){
  const active=searchResultLayout(mode);return `<div class="search-layout-switcher" role="group" aria-label="${esc(tr("research.result_layout","Result layout"))}">${[["compact",tr("research.layout_compact","Compact table")],["roomy",tr("research.layout_roomy","Comfortable table")],["cards",tr("research.layout_cards","Cards")]].map(([value,text])=>`<button type="button" class="btn tiny ${active===value?"active":""}" data-search-layout="${value}" data-search-layout-mode="${mode==="database"?"database":"traditional"}" aria-pressed="${active===value}">${esc(text)}</button>`).join("")}</div>`;
}
function wireSearchLayoutControls(main,rerender){main.querySelectorAll("[data-search-layout]").forEach(button=>button.addEventListener("click",()=>{const y=window.scrollY,mode=button.dataset.searchLayoutMode||"traditional";state.searchResultLayouts={...(state.searchResultLayouts||{}),[mode]:button.dataset.searchLayout};persistPrefs();syncUrl({replace:true});rerender();requestAnimationFrame(()=>window.scrollTo({top:y,behavior:"auto"}))}))}
function databaseResultsHtml({admin=false,query="",layoutMode="database"}={}){
  const layout=searchResultLayout(layoutMode),results=state.storeSearchResults||[];if(layout==="cards")return `<div class="researcher-result-grid">${admin?adminDatabaseResultCards(query):researcherResultCards(query)}</div>`;
  const roomy=layout==="roomy"?"roomy-results":"compact-results";return `<div class="tablewrap search-result-table ${roomy}"><table><thead><tr><th>${esc(tr("record.id","Record"))}</th><th>${esc(label("work"))}</th><th>${esc(label("document_author"))}</th><th>${esc(tr("research.similarity","Similarity"))}</th><th>${esc(tr("record.text","Text"))}</th><th>${esc(tr("ui.actions","Actions"))}</th></tr></thead><tbody>${results.map(result=>{const record=result.record||{},id=String(result.id||record._chroma_id||record.record_id||""),eKey=dbEvidenceKey(state.activeStore,id);return `<tr ${admin?"":`data-open-research-record="${esc(id)}" class="clickable"`}><td>${esc(record.record_id||id)}</td><td>${metadataLinkHtml("work",record.work)}</td><td>${metadataLinkHtml("document_author",record.document_author)}</td><td>${result.distance!=null?similarityHtml(result.distance):"—"}</td><td class="textcell">${highlightTerms(snippet(record.text||"",query,layout==="roomy"?420:180),query)}</td><td><div class="tools">${evidenceButtonHtml(eKey,evidenceIsSelected(eKey)?tr("ui.selected","Selected"):tr("ui.add_evidence","Evidence"))}${admin?`<button class="btn tiny" data-admin-db-edit="${esc(id)}">${esc(tr("ui.edit","Edit"))}</button><button class="btn tiny" data-admin-db-cite="inline" data-admin-db-id="${esc(id)}">${esc(tr("ui.copy_inline","Inline citation"))}</button><button class="btn tiny" data-admin-db-cite="full" data-admin-db-id="${esc(id)}">${esc(tr("ui.copy_full","Full citation"))}</button>`:`<button class="btn tiny" data-r-cite="inline" data-r-id="${esc(id)}">${esc(tr("ui.copy_inline","Inline citation"))}</button><button class="btn tiny" data-r-cite="full" data-r-id="${esc(id)}">${esc(tr("ui.copy_full","Full citation"))}</button>`}</div></td></tr>`}).join("")||`<tr><td colspan="6" class="note search-empty-cell">${esc(tr("research.no_matches","No matching records."))}</td></tr>`}</tbody></table></div>`;
}
function workspaceResultsHtml(slice,columns,query,pageSelected){
  const layout=searchResultLayout("traditional");if(layout!=="cards")return `<section class="card tablewrap search-result-table ${layout==="roomy"?"roomy-results":"compact-results"}"><table class="configurable-table"><thead><tr><th class="select-col"><input id="selectGlobalPage" type="checkbox" ${pageSelected?"checked":""}></th>${columns.map(key=>dataHeadHtml(key,state.globalSort)).join("")}<th class="record-actions-head">${esc(tr("research.record_actions","Record actions"))}</th></tr></thead><tbody>${slice.map(x=>`<tr class="clickable ${state.reviewSelection.has(reviewKey(x.file,x.index))?"row-selected":""}" data-f="${x.file.id}" data-i="${x.index}"><td class="select-col"><input class="row-select" type="checkbox" data-select-key="${esc(reviewKey(x.file,x.index))}" ${state.reviewSelection.has(reviewKey(x.file,x.index))?"checked":""}></td>${columns.map(key=>dataCellHtml(x,key,query)).join("")}${workspaceRecordActionsHtml(x)}</tr>`).join("")||`<tr><td colspan="${columns.length+2}" class="note search-empty-cell">${esc(tr("research.no_matches","No matching records."))}</td></tr>`}</tbody></table></section>`;
  return `<section class="workspace-search-card-grid">${slice.map(x=>{const r=x.record,key=reviewKey(x.file,x.index);return `<article class="card workspace-search-card ${state.reviewSelection.has(key)?"selected":""}" data-f="${x.file.id}" data-i="${x.index}"><header><label><input class="row-select" type="checkbox" data-select-key="${esc(key)}" ${state.reviewSelection.has(key)?"checked":""}><span>${esc(r.record_id||tr("nav.record","Record"))}</span></label><span>${dbStatusBadgeHtml(x.file,x.index,r)}</span></header><h3>${esc(r.work||tr("works.untitled","Untitled work"))}</h3><div class="researcher-result-meta">${[["document_author",r.document_author],["year",r.year],["speaker",r.speaker],["position_holder",r.position_holder]].filter(([,v])=>v).map(([field,v])=>metadataLinkHtml(field,v,{className:"metadata-result-pill"})).join("")}</div><p>${highlightTerms(snippet(r.text||"",query,460),query)}</p><footer><button class="btn tiny" data-card-open-record>${esc(tr("record.open","Open record"))}</button><button class="btn tiny" data-card-cite-kind="inline">${esc(tr("ui.copy_inline","Inline citation"))}</button><button class="btn tiny" data-card-cite-kind="full">${esc(tr("ui.copy_full","Full citation"))}</button></footer></article>`}).join("")||`<div class="llm-empty">${esc(tr("research.no_matches","No matching records."))}</div>`}</section>`;
}

function researcherResultCards(query=""){
  return (state.storeSearchResults||[]).map(result=>{const record=result.record||{};const id=String(result.id||record._chroma_id||record.record_id||"");const eKey=dbEvidenceKey(state.activeStore,id);return `<article class="card researcher-search-result" data-open-research-record="${esc(id)}"><div class="researcher-result-head"><div><span class="section-label">${esc(record.record_id||id||tr("nav.record","Record"))}</span><h3>${esc(record.work||tr("works.untitled","Untitled work"))}</h3></div>${result.distance!=null?similarityHtml(result.distance):""}</div><div class="researcher-result-meta">${[["document_author",record.document_author],["year",record.year],["speaker",record.speaker],["position_holder",record.position_holder]].filter(([,v])=>v).map(([field,v])=>metadataLinkHtml(field,v,{className:"metadata-result-pill"})).join("")}</div><p class="researcher-summary-text">${highlightTerms(record.text||"",query)}</p><div class="record-inline-actions">${evidenceButtonHtml(eKey,evidenceIsSelected(eKey)?tr("ui.selected","Selected"):tr("ui.add_evidence","Add evidence"))}<button class="btn tiny" data-r-cite="inline" data-r-id="${esc(id)}">${icon("copy")}${esc(tr("ui.copy_inline","Inline citation"))}</button><button class="btn tiny" data-r-cite="full" data-r-id="${esc(id)}">${icon("copy")}${esc(tr("ui.copy_full","Full citation"))}</button></div></article>`}).join("")||`<div class="llm-empty">${esc(tr("research.no_matches","No matching records. Try a broader query or another corpus database."))}</div>`;
}
async function renderResearcherGlobal(main){
  showViewLoading(main,tr("context.global_search","Global Search"),tr("research.loading_databases","Loading corpus databases…"));
  try{await refreshStores()}catch(error){main.innerHTML=`<div class="info error">${esc(error.message)}</div>`;return}
  const stores=recordStores();if(!state.activeStore&&stores.length)state.activeStore=stores[0].name;
  if(!stores.length){
    if(canAccessPage("vector")){toast(tr("search.redirect_database","Search needs a corpus database. Opening database creation now."),{tone:"info"});openDatabaseCreationFromResearch();return}
    main.innerHTML=`<section class="empty"><div class="drop"><div class="drop-icon">${icon("database")}</div><h1>${esc(tr("research.no_database","No corpus database available"))}</h1><p>${esc(tr("research.no_database_help","An administrator must create or restore a corpus database before researcher search and Research can be used."))}</p></div></section>`;return
  }
  const semantic=state.globalSearchMode==="database";const method=semantic?(state.dbSearchMethod||"similarity"):"keyword";
  const filterFields=["work","document_author","year","document_language","original_language","speaker","position_holder","discourse_role","proposition_status","stance"];
  const chips=Object.entries(dbSearchWhere()).map(([field,value])=>`<span class="filter-chip">${esc(label(field))}: ${esc(dbFilterDisplayValue(value))} <button data-remove-r-filter="${esc(field)}" aria-label="${esc(tr("ui.remove","Remove"))}">×</button></span>`).join("");
  main.innerHTML=`<div class="global-search-v25 unified-search"><section class="card search-mode-card"><div class="cardhead"><div><b>${esc(tr("context.global_search","Global Search"))}</b><div class="note">${esc(tr("research.global_search_help","Search summarized records by text or switch to semantic ranking in the selected corpus database."))}</div></div></div><div class="view-tabs"><button class="view-tab ${!semantic?"active":""}" data-r-global-mode="traditional">${esc(tr("research.traditional_search","Record search"))}</button><button class="view-tab ${semantic?"active":""}" data-r-global-mode="database">${esc(tr("research.semantic_db_search","Semantic DB search"))}</button></div><div class="db-search-toolbar"><label class="field"><span>${esc(tr("research.corpus_database","Corpus database"))}</span><select class="control" id="rGlobalStore">${stores.map(store=>`<option value="${esc(store.name)}" ${store.name===state.activeStore?"selected":""}>${esc(store.name)} · ${Number(store.count||0).toLocaleString()} ${esc(tr("dynamic.records","records"))}</option>`).join("")}</select></label>${semantic?`<label class="field"><span>${esc(tr("research.search_method","Search method"))}</span><select class="control" id="rSearchMethod"><option value="similarity" ${method==="similarity"?"selected":""}>${esc(tr("research.similarity","Similarity"))}</option><option value="mmr" ${method==="mmr"?"selected":""}>MMR</option><option value="filter" ${method==="filter"?"selected":""}>${esc(tr("research.filters_only","Filters only"))}</option></select></label>`:""}</div><div class="search-query-row"><input id="rGlobalQuery" class="control" value="${esc(state.globalSearch)}" placeholder="${esc(semantic?tr("research.search_placeholder","Search the corpus semantically"):tr("research.record_search_placeholder","Search record text…"))}" ${semantic&&method==="filter"?"disabled":""}><button class="btn primary" id="runRGlobalSearch">${icon("search")}${esc(tr("ui.search","Search"))}</button><button class="btn" id="clearRGlobalSearch">${esc(tr("ui.clear","Clear"))}</button></div>${semantic&&method==="mmr"?`<div class="advanced-search-config"><label class="field"><span>fetch_k</span><input id="rFetchK" class="control" type="number" min="1" max="1000" value="${esc(state.dbSearchFetchK||100)}"></label><label class="field"><span>λ</span><input id="rLambda" class="control" type="number" min="0" max="1" step="0.05" value="${esc(state.dbSearchLambda??0.7)}"></label></div>`:""}<details class="advanced-search-filters" ${state.globalAdvancedOpen?"open":""}><summary>${esc(tr("research.metadata_filters","Metadata filters"))}</summary><div class="db-filter-builder"><select id="rFilterField" class="control">${filterFields.map(field=>`<option value="${field}">${esc(label(field))}</option>`).join("")}</select><input id="rFilterValue" class="control" placeholder="${esc(tr("research.filter_value","Exact filter value"))}"><button class="btn small" id="addRFilter">${esc(tr("research.add_filter","Add filter"))}</button></div><div class="filter-chip-row">${chips||`<span class="note">${esc(tr("research.no_filters","No database filters applied."))}</span>`}</div></details></section><section class="card db-global-results"><div class="cardhead"><div><b>${esc(tr("research.search_results","Search results"))}</b><div class="note">${state.storeSearchLoading?esc(tr("research.search_loading","Searching the corpus…")):state.storeSearchResults.length?`${state.storeSearchResults.length.toLocaleString()} ${esc(tr("research.results","results"))}`:esc(tr("research.record_search_empty","Run a search to find summarized records."))}</div></div>${searchLayoutControls(semantic?"database":"traditional")}</div>${state.storeSearchLoading?loadingCardsHtml(tr("research.search_loading","Searching the corpus…"),3):databaseResultsHtml({admin:false,query:state.globalSearch,layoutMode:semantic?"database":"traditional"})}</section></div>`;
  const run=async()=>{const query=String(main.querySelector("#rGlobalQuery")?.value||"").trim();if(method!=="filter"&&!query)return;state.globalSearch=query;state.storeSearchLoading=true;state.storeSearchResults=[];persistPrefs();syncUrl({replace:true});renderResearcherGlobal(main);try{const body={query,mode:method,n_results:100,where:Object.keys(dbSearchWhere()).length?dbSearchWhere():null,fetch_k:Number(state.dbSearchFetchK||100),lambda_mult:Number(state.dbSearchLambda??0.7)};const data=await api(`/api/stores/${encodeURIComponent(state.activeStore)}/search`,{method:"POST",body:JSON.stringify(body)});state.storeSearchResults=data.results||[]}catch(error){toast(`${tr("research.search_failed","Search failed")}: ${error.message}`,{tone:"danger"})}finally{state.storeSearchLoading=false;persistPrefs();renderResearcherGlobal(main)}};
  main.querySelectorAll("[data-r-global-mode]").forEach(button=>button.onclick=()=>{state.globalSearchMode=button.dataset.rGlobalMode;state.storeSearchResults=[];persistPrefs();syncUrl({replace:true});renderResearcherGlobal(main)});
  wireSearchLayoutControls(main,()=>renderResearcherGlobal(main));
  main.querySelector("#rGlobalStore")?.addEventListener("change",event=>{state.activeStore=event.target.value;state.storeSearchResults=[];persistPrefs();syncUrl({replace:true});renderResearcherGlobal(main)});
  main.querySelector("#rSearchMethod")?.addEventListener("change",event=>{state.dbSearchMethod=event.target.value;state.storeSearchResults=[];persistPrefs();syncUrl({replace:true});renderResearcherGlobal(main)});
  main.querySelector("#rFetchK")?.addEventListener("change",event=>{state.dbSearchFetchK=Math.max(1,Number(event.target.value)||100);persistPrefs();syncUrl({replace:true})});main.querySelector("#rLambda")?.addEventListener("change",event=>{state.dbSearchLambda=Math.max(0,Math.min(1,Number(event.target.value)||0.7));persistPrefs();syncUrl({replace:true})});
  main.querySelector("#runRGlobalSearch")?.addEventListener("click",run);main.querySelector("#rGlobalQuery")?.addEventListener("keydown",event=>{if(event.key==="Enter"){event.preventDefault();void run()}});main.querySelector("#clearRGlobalSearch")?.addEventListener("click",()=>{state.globalSearch="";state.storeSearchResults=[];state.dbSearchWhere={};persistPrefs();syncUrl({replace:true});renderResearcherGlobal(main)});
  main.querySelector("#addRFilter")?.addEventListener("click",()=>{const field=main.querySelector("#rFilterField")?.value;const value=main.querySelector("#rFilterValue")?.value?.trim();if(field&&value){state.dbSearchWhere={...(state.dbSearchWhere||{}),[field]:value};persistPrefs();syncUrl({replace:true});renderResearcherGlobal(main)}});main.querySelectorAll("[data-remove-r-filter]").forEach(button=>button.onclick=()=>{const next={...(state.dbSearchWhere||{})};delete next[button.dataset.removeRFilter];state.dbSearchWhere=next;persistPrefs();syncUrl({replace:true});renderResearcherGlobal(main)});
  main.querySelectorAll("[data-open-research-record]").forEach(card=>card.addEventListener("click",event=>{if(event.target.closest("button"))return;state.researcherRecordId=card.dataset.openResearchRecord||"";persistPrefs();navigateTo("record")}));main.querySelectorAll("[data-evidence-key]").forEach(button=>button.onclick=event=>{event.stopPropagation();const key=button.dataset.evidenceKey;if(!key?.startsWith("db:"))return;const id=key.split(":").slice(2).join(":");const result=state.storeSearchResults.find(item=>String(item.id||item.record?._chroma_id||item.record?.record_id||"")===id);toggleDbEvidence(state.activeStore,id,result?.record||{});renderResearcherGlobal(main)});decorateDisabledControls(main);if(state.globalSearchAutoRun){state.globalSearchAutoRun=false;persistPrefs();queueMicrotask(()=>void run())}
}
async function renderResearcherWorks(main){
  showViewLoading(main,tr("works.loading","Loading works"),tr("works.checking_database","Checking corpus database…"));try{await refreshStores();if(state.activeStore)await refreshStoreWorks(true)}catch(error){main.innerHTML=`<div class="info error">${esc(error.message)}</div>`;return}
  // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  const stores=recordStores();if(!state.activeStore&&stores.length){state.activeStore=stores[0].name;await refreshStoreWorks(true)};try{await refreshServerAnnotations(true)}catch{};if(!stores.length){main.innerHTML=`<section class="empty"><div class="drop"><div class="drop-icon">${icon("database")}</div><h1>${esc(tr("research.no_database","No corpus database available"))}</h1></div></section>`;return}
  const works=(state.storeWorkStats||[]).filter(item=>!state.worksSearch||String(item.work).toLocaleLowerCase().includes(state.worksSearch.toLocaleLowerCase()));const selected=works.find(item=>item.work===state.workOverview)||null;
  const selectedAnnotationCount=selected?allAnnotations().filter(item=>String(item.work||"")===String(selected.work)).length:0;
  const cover=item=>String(item?.cover_url||"");const overview=selected?`<section class="card work-overview-card"><div class="work-overview-cover">${cover(selected)?`<img src="${esc(cover(selected))}" alt="${esc(trf("works.cover_alt","Cover of {work}",{work:selected.work}))}">`:icon("books")}</div><div class="work-overview-content"><div class="work-overview-heading"><div><span class="section-label">${esc(tr("works.overview","Work overview"))}</span><h1>${esc(selected.work)}</h1><p>${Number(selected.count||0).toLocaleString()} ${esc(tr("dynamic.records","records"))}</p></div></div><div class="work-overview-metadata">${["document_author","publisher","publication_year","edition","translator","publication_place","isbn","document_language","original_language"].map(field=>selected[field]?`<div><span>${esc(label(field))}</span><b>${esc(display(selected[field]))}</b></div>`:"").join("")}</div>${selected.full_citation?`<div class="work-overview-citation"><span>${esc(label("full_citation"))}</span><p>${esc(selected.full_citation)}</p></div>`:""}<div class="work-overview-actions"><button class="btn primary" id="browseResearchWork">${icon("search")}${esc(tr("works.browse_records","Browse records"))}</button>${selectedAnnotationCount?`<button class="btn" id="researchWorkAnnotations">${icon("record")}${esc(trf("works.view_annotations","Annotations ({count})",{count:selectedAnnotationCount.toLocaleString()}))}</button>`:""}</div></div></section>`:"";
  main.innerHTML=`<section class="page-heading legacy-page-heading"><div><p>${esc(tr("section.corpus","Corpus"))}</p><h1>${esc(tr("nav.works","Works"))}</h1><span>${esc(tr("research.works_menu_help","Browse works in the selected corpus database. Select a work for an overview, then browse its summarized records."))}</span></div></section>${overview}<div class="toolbar works-toolbar"><div class="search"><input id="worksSearch" value="${esc(state.worksSearch)}" placeholder="${esc(tr("research.filter_works","Filter works by title"))}"></div><div class="tools"><select class="control" id="researchWorksStore">${stores.map(store=>`<option value="${esc(store.name)}" ${store.name===state.activeStore?"selected":""}>${esc(store.name)}</option>`).join("")}</select><span class="note">${works.length.toLocaleString()} ${esc(tr("dynamic.works","works"))}</span></div></div><section class="researcher-work-menu">${works.map(item=>`<button class="researcher-work-menu-card ${state.workOverview===item.work?"active":""}" data-research-work="${esc(item.work)}">${cover(item)?`<img class="researcher-work-cover" src="${esc(cover(item))}" alt="">`:`<span class="work-book-icon">${icon("books")}</span>`}<span><b>${esc(item.work)}</b><small>${[item.document_author,item.publication_year||item.year,item.publisher].filter(Boolean).map(esc).join(" · ")}</small><small>${Number(item.count||0).toLocaleString()} ${esc(tr("dynamic.records","records"))}</small></span><span class="work-menu-arrow">›</span></button>`).join("")||`<div class="llm-empty">${esc(tr("research.no_works","No works are available."))}</div>`}</section>`;
  let timer=null;main.querySelector("#worksSearch")?.addEventListener("input",event=>{state.worksSearch=event.target.value;persistPrefs();syncUrl({replace:true});clearTimeout(timer);timer=setTimeout(()=>renderResearcherWorks(main),150)});main.querySelector("#researchWorksStore")?.addEventListener("change",async event=>{state.activeStore=event.target.value;state.storeWorksStore="";state.workOverview="";await refreshStoreWorks(true);persistPrefs();syncUrl({replace:true});renderResearcherWorks(main)});main.querySelectorAll("[data-research-work]").forEach(button=>button.onclick=()=>{const y=window.scrollY;state.workOverview=button.dataset.researchWork||"";persistPrefs();syncUrl({replace:true});renderResearcherWorks(main);requestAnimationFrame(()=>window.scrollTo(0,y))});main.querySelector("#browseResearchWork")?.addEventListener("click",()=>{state.storeWork=state.workOverview;state.storeBrowseMode="records";state.storePage=1;persistPrefs();navigateTo("vector")});main.querySelector("#researchWorkAnnotations")?.addEventListener("click",()=>{state.annotationSearch=state.workOverview;state.annotationView="works";persistPrefs();navigateTo("annotations")});
}
async function renderResearcherRecord(main){
  // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  try{await refreshServerAnnotations()}catch{}
  // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  if(!state.activeStore){try{await refreshStores()}catch{};if(!state.activeStore){main.innerHTML=`<div class="info warn">${esc(tr("research.no_database","No corpus database available"))}</div>`;return}}
  let id=state.researcherRecordId;let record=researcherDbRecords().find(item=>String(item._chroma_id||item.record_id||"")===String(id));
  if(!record&&id){try{record=await api(`/api/stores/${encodeURIComponent(state.activeStore)}/records/${encodeURIComponent(id)}`)}catch{record=null}}
  // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  if(!record){if(!state.storeRecords.length){try{await loadStorePage()}catch{}}record=state.storeRecords[0];id=String(record?._chroma_id||record?.record_id||"");state.researcherRecordId=id}
  if(!record){main.innerHTML=`<section class="empty"><div class="drop"><h1>${esc(tr("research.no_records","No records available"))}</h1><button class="btn primary" id="recordBrowseWorks">${esc(tr("works.browse_records","Browse records"))}</button></div></section>`;main.querySelector("#recordBrowseWorks")?.addEventListener("click",()=>navigateTo("works"));return}
  const viewedPointer={kind:"database",store:state.activeStore,id:String(record._chroma_id||record.record_id||id)};
  if(JSON.stringify(state.lastViewedRecord)!==JSON.stringify(viewedPointer)){state.lastViewedRecord=viewedPointer;persistPrefs()}
  const q=state.recordFind||"";const text=String(record.text||"");const eKey=dbEvidenceKey(state.activeStore,String(record._chroma_id||record.record_id||id));const groups=[["topics",record.topics],["concepts",record.concepts],["persons",record.persons],["works_referenced",record.works_referenced]];const sharedAnnotations=(state.serverAnnotations||[]).filter(item=>String(item.store||"")===String(state.activeStore)&&String(item.record_id||"")===String(record._chroma_id||record.record_id||id));const sharedAnnotationsHtml=sharedAnnotations.length?`<div class="record-annotations shared-record-annotations">${sharedAnnotations.map(item=>`<article class="record-annotation"><div class="record-annotation-context"><span class="annotation-field-label">${esc(label(item.field||"text"))}</span>${item.quote?`<blockquote>${esc(item.quote)}</blockquote>`:""}</div><div class="record-annotation-body">${item.note?`<p>${esc(item.note)}</p>`:""}${(item.tags||[]).length?`<div class="annotation-tags">${(item.tags||[]).map(tag=>`<span class="chip">${esc(tag)}</span>`).join("")}</div>`:""}<div class="record-annotation-meta"><span>${esc(item.initiated_by||item.author||tr("annotations.unknown_author","Unknown author"))}</span><time>${esc(formatTimestamp(item.created_at))}</time></div></div></article>`).join("")}</div>`:`<div class="annotation-empty-state"><span class="annotation-empty-icon">${icon("record")}</span><div><b>${esc(tr("annotations.none_record","No annotations on this record yet"))}</b><p>${esc(tr("annotations.none_record_help","Select text above to attach a note or tags."))}</p></div></div>`;
  main.innerHTML=`<section class="record-toolbar"><div class="record-nav"><button class="btn" id="researchRecordBack">${icon("search")}${esc(tr("nav.search","Search"))}</button><button class="btn" id="researchRecordWorks">${icon("books")}${esc(tr("nav.works","Works"))}</button></div><div class="search"><input id="recordSearch" value="${esc(q)}" placeholder="${esc(tr("record.find_text","Find in record text"))}"><button class="record-find-clear" id="clearRecordFind" ${q?"":`disabled data-disabled-reason="${esc(tr("record.clear_find_empty","Enter a find query before clearing it."))}"`}>${esc(tr("record.clear_search","Clear search"))}</button></div></section><section class="recordgrid"><article class="card record-main"><div class="headline"><div class="eyebrow">${esc(record.record_id||id)}</div><h1>${metadataLinkHtml("work",record.work||tr("nav.record","Record"),{className:"metadata-heading-link"})}</h1><div class="meta">${metadataLinkHtml("document_author",record.document_author)} · ${metadataLinkHtml("year",record.year)}${mlaPageSpan(record)?` · <span>${esc(`p. ${mlaPageSpan(record)}`)}</span>`:""}</div></div><div class="cardhead"><div><b>${esc(tr("record.summary","Researcher summary"))}</b><div class="note">${esc(tr("research.summary_policy","Edmundson summary · 2–3 sentences"))}${q?` · ${countOccurrences(text,q)} ${esc(tr("record.matches","matches"))}`:""}</div></div><div class="tools">${evidenceButtonHtml(eKey,evidenceIsSelected(eKey)?tr("ui.selected","Selected"):tr("ui.add_evidence","Add evidence"))}<button class="btn tiny" id="researchInlineCite">${icon("copy")}${esc(tr("ui.copy_inline","Inline citation"))}</button><button class="btn tiny" id="researchFullCite">${icon("copy")}${esc(tr("ui.copy_full","Full citation"))}</button></div></div><div class="recordtext" data-annotatable-text data-annotatable-field="text">${highlight(text,q)}</div><div class="record-selection-toolbar" id="researchRecordSelectionToolbar" hidden><span id="researchRecordSelectionLabel">${esc(tr("annotations.selected_text","Selected text"))}</span>${hasCapability("annotations.write")?`<button class="btn tiny primary" id="researchAnnotateSelection">${esc(tr("annotations.add_note_tags","Add note / tags"))}</button>`:""}</div><section class="record-annotation-section"><div class="record-annotation-heading"><div><span class="section-label">${esc(tr("annotations.record_notes","Annotations"))}</span><h3>${esc(tr("annotations.record_annotations","Record annotations"))}</h3><p>${esc(tr("annotations.record_annotations_help","Notes and tags attached to specific evidence in this record."))}</p></div><span class="badge">${sharedAnnotations.length}</span></div>${sharedAnnotationsHtml}</section></article><aside class="side"><section class="card"><div class="section"><h3>${esc(tr("record.metadata","Metadata"))}</h3><div class="mg">${["document_author","edition","year","page_start","page_end","speaker","position_holder","target","discourse_role","proposition_status","stance"].map(key=>metaRow(key,record[key])).join("")}</div></div></section><section class="card record-index-card researcher-index-card">${groups.map(([key,values])=>`<div class="quick-index metadata-badge-section"><div class="section-title-row"><h3>${esc(label(key))}</h3><span class="badge">${Array.isArray(values)?values.length:values?1:0}</span></div><div class="editable-chips researcher-badge-wrap">${flattenValueList(values).map(value=>`<span class="editable-chip researcher-index-chip"><button class="chip-search-link" data-meta-search-field="${esc(key)}" data-meta-search-value="${esc(value)}" data-meta-search-contains="true">${esc(value)}</button></span>`).join("")||`<span class="note">${esc(tr("ui.none","None"))}</span>`}</div></div>`).join("")}</section></aside></section>`;
  main.querySelector("#researchRecordBack")?.addEventListener("click",()=>navigateTo("global"));main.querySelector("#researchRecordWorks")?.addEventListener("click",()=>navigateTo("works"));main.querySelector("#recordSearch")?.addEventListener("input",event=>{const pos=event.target.selectionStart;state.recordFind=event.target.value;persistPrefs();syncUrl({replace:true});renderResearcherRecord(main);requestAnimationFrame(()=>{const input=main.querySelector("#recordSearch");input?.focus();input?.setSelectionRange(pos,pos)})});main.querySelector("#clearRecordFind")?.addEventListener("click",()=>{state.recordFind="";persistPrefs();syncUrl({replace:true});renderResearcherRecord(main);requestAnimationFrame(()=>main.querySelector("#recordSearch")?.focus())});main.querySelector("#researchInlineCite")?.addEventListener("click",()=>copyCitation(record,"inline"));main.querySelector("#researchFullCite")?.addEventListener("click",()=>copyCitation(record,"full"));main.querySelectorAll("[data-evidence-key]").forEach(button=>button.onclick=()=>{toggleDbEvidence(state.activeStore,String(record._chroma_id||record.record_id||id),record);renderResearcherRecord(main)});wireMetadataSearch(main);
  let researcherSelection=null;const updateResearcherSelection=()=>{researcherSelection=selectionInsideRecordView();const toolbar=main.querySelector("#researchRecordSelectionToolbar");if(toolbar){toolbar.hidden=!researcherSelection;if(researcherSelection)positionSelectionToolbar(toolbar,researcherSelection)}};const researcherGrid=main.querySelector(".recordgrid");researcherGrid?.addEventListener("mouseup",updateResearcherSelection);researcherGrid?.addEventListener("keyup",updateResearcherSelection);main.querySelector("#researchAnnotateSelection")?.addEventListener("click",()=>{if(!researcherSelection)return;openAnnotationPopover(researcherSelection,{recordLabel:String(record.record_id||id),onSave:async({field,quote,note,tags})=>{await api("/api/annotations",{method:"POST",body:JSON.stringify({store:state.activeStore,record_id:String(record._chroma_id||record.record_id||id),work:String(record.work||""),page_start:record.page_start??null,page_end:record.page_end??null,field,quote,note,tags})});state.annotationsFetchedAt=0;await refreshServerAnnotations(true);toast(tr("annotations.saved","Record annotation saved"),{tone:"success"});renderResearcherRecord(main)}})});
}
async function renderResearcherCompare(main){
  // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  if(!state.activeStore){try{await refreshStores()}catch{}};if(!state.storeRecords.length&&state.activeStore){state.storePageSize=100;try{await loadStorePage()}catch{}}
  const records=researcherDbRecords();const byId=new Map(records.map(record=>[String(record._chroma_id||record.record_id||""),record]));if(!state.researcherCompareA&&records[0])state.researcherCompareA=String(records[0]._chroma_id||records[0].record_id||"");if(!state.researcherCompareB&&records[1])state.researcherCompareB=String(records[1]._chroma_id||records[1].record_id||"");const a=byId.get(state.researcherCompareA),b=byId.get(state.researcherCompareB);
  const options=records.map(record=>{const id=String(record._chroma_id||record.record_id||"");return `<option value="${esc(id)}">${esc(record.record_id||id)} · ${esc(record.work||"")}</option>`}).join("");
  main.innerHTML=`<div class="compare-page"><section class="card compare-intro-card"><div><span class="section-label">${esc(tr("section.tools","Tools"))}</span><h1>${esc(tr("nav.compare","Compare"))}</h1><p>${esc(tr("research.compare_help","Compare researcher-visible summarized records side by side."))}</p></div></section><section class="card compare-picker-card"><div class="compare-selectors"><label class="field"><span>${esc(tr("compare.record_a","Record A"))}</span><select class="control" id="rCompareA">${options}</select></label><label class="field"><span>${esc(tr("compare.record_b","Record B"))}</span><select class="control" id="rCompareB">${options}</select></label></div><div class="compare-picker-note"><span>${icon("info")}</span><p>${esc(tr("compare.researcher_source_help","Records are drawn from the selected corpus database and use the same Compare workspace as administrator accounts. Editing controls appear only where your role permits them."))}</p></div></section>${a&&b?compareRecordTable(a,b,{titleA:a.record_id||"A",titleB:b.record_id||"B"}):`<div class="compare-empty-state"><b>${esc(tr("compare.need_two","Two records are needed"))}</b><span>${esc(tr("compare.need_two_help","Browse records or run a search first, then return to Compare."))}</span></div>`}</div>`;
  const sa=main.querySelector("#rCompareA"),sb=main.querySelector("#rCompareB");if(sa)sa.value=state.researcherCompareA;if(sb)sb.value=state.researcherCompareB;sa?.addEventListener("change",event=>{state.researcherCompareA=event.target.value;persistPrefs();renderResearcherCompare(main)});sb?.addEventListener("change",event=>{state.researcherCompareB=event.target.value;persistPrefs();renderResearcherCompare(main)});decorateDisabledControls(main);
}

function adminDatabaseResultCards(query=""){
  return (state.storeSearchResults||[]).map(result=>{const record=result.record||{};const id=String(result.id||record._chroma_id||record.record_id||"");const eKey=dbEvidenceKey(state.activeStore,id);return `<article class="card researcher-search-result admin-db-search-result"><div class="researcher-result-head"><div><span class="section-label">${esc(record.record_id||id||tr("nav.record","Record"))}</span><h3>${esc(record.work||tr("works.untitled","Untitled work"))}</h3></div>${result.distance!=null?similarityHtml(result.distance):""}</div><div class="researcher-result-meta">${[["document_author",record.document_author],["year",record.year],["speaker",record.speaker],["position_holder",record.position_holder]].filter(([,v])=>v).map(([field,v])=>metadataLinkHtml(field,v,{className:"metadata-result-pill"})).join("")}</div><p class="researcher-summary-text">${highlightTerms(record.text||"",query)}</p><div class="record-inline-actions">${evidenceButtonHtml(eKey,evidenceIsSelected(eKey)?tr("ui.selected","Selected"):tr("ui.add_evidence","Add evidence"))}<button class="btn tiny" data-admin-db-cite="inline" data-admin-db-id="${esc(id)}">${icon("copy")}${esc(tr("ui.copy_inline","Inline citation"))}</button><button class="btn tiny" data-admin-db-cite="full" data-admin-db-id="${esc(id)}">${icon("copy")}${esc(tr("ui.copy_full","Full citation"))}</button><button class="btn tiny" data-admin-db-edit="${esc(id)}">${icon("edit")}${esc(tr("ui.edit","Edit"))}</button></div></article>`}).join("")||`<div class="llm-empty">${esc(tr("research.no_matches","No matching records. Try a broader query or another corpus database."))}</div>`;
}

async function renderAdminDatabaseGlobal(main){
  showViewLoading(main,tr("context.global_search","Global Search"),tr("research.loading_databases","Loading corpus databases…"));
  try{await refreshStores()}catch(error){main.innerHTML=`<div class="info error">${esc(error.message)}</div>`;return}
  const stores=recordStores();if(!state.activeStore&&stores.length)state.activeStore=stores[0].name;
  if(!stores.length){toast(tr("search.redirect_database","Search needs a corpus database. Opening database creation now."),{tone:"info"});openDatabaseCreationFromResearch();return}
  const method=state.dbSearchMethod||"similarity";const filterFields=["work","document_author","year","document_language","original_language","speaker","position_holder","discourse_role","proposition_status","stance"];
  const chips=Object.entries(dbSearchWhere()).map(([field,value])=>`<span class="filter-chip">${esc(label(field))}: ${esc(dbFilterDisplayValue(value))} <button data-remove-admin-filter="${esc(field)}" aria-label="${esc(tr("ui.remove","Remove"))}">×</button></span>`).join("");
  main.innerHTML=`<div class="global-search-v25 unified-search"><section class="card search-mode-card"><div class="cardhead"><div><b>${esc(tr("context.global_search","Global Search"))}</b><div class="note">${esc(tr("research.global_search_admin_help","Search loaded records or switch to semantic search in the selected corpus database."))}</div></div></div><div class="view-tabs"><button class="view-tab" data-global-mode="traditional">${esc(tr("research.traditional_search","Record search"))}</button><button class="view-tab active" data-global-mode="database">${esc(tr("research.semantic_db_search","Semantic DB search"))}</button></div><div class="db-search-toolbar"><label class="field"><span>${esc(tr("research.corpus_database","Corpus database"))}</span><select class="control" id="adminGlobalStore">${stores.map(store=>`<option value="${esc(store.name)}" ${store.name===state.activeStore?"selected":""}>${esc(store.name)} · ${Number(store.count||0).toLocaleString()} ${esc(tr("dynamic.records","records"))}</option>`).join("")}</select><small>${esc(tr("research.selected_database_help","Searches run against this selected database only."))}</small></label><label class="field"><span>${esc(tr("research.search_method","Search method"))}</span><select class="control" id="adminSearchMethod"><option value="similarity" ${method==="similarity"?"selected":""}>${esc(tr("research.similarity","Similarity"))}</option><option value="mmr" ${method==="mmr"?"selected":""}>MMR</option><option value="filter" ${method==="filter"?"selected":""}>${esc(tr("research.filters_only","Filters only"))}</option></select></label></div><div class="search-query-row"><input id="adminGlobalQuery" class="control" value="${esc(state.globalSearch)}" placeholder="${esc(tr("research.search_placeholder","Search the corpus semantically"))}" ${method==="filter"?"disabled data-disabled-reason=\"Filters-only mode does not require query text.\"":""}><button class="btn primary" id="runAdminGlobalSearch">${icon("search")}${esc(tr("ui.search","Search"))}</button><button class="btn" id="clearAdminGlobalSearch">${esc(tr("ui.clear","Clear"))}</button></div>${method==="mmr"?`<div class="advanced-search-config"><label class="field"><span>fetch_k</span><input id="adminFetchK" class="control" type="number" min="1" max="1000" value="${esc(state.dbSearchFetchK||100)}"></label><label class="field"><span>λ</span><input id="adminLambda" class="control" type="number" min="0" max="1" step="0.05" value="${esc(state.dbSearchLambda??0.7)}"></label></div>`:""}<details class="advanced-search-filters" ${state.globalAdvancedOpen?"open":""}><summary>${esc(tr("research.metadata_filters","Metadata filters"))}</summary><div class="db-filter-builder"><select id="adminFilterField" class="control">${filterFields.map(field=>`<option value="${field}">${esc(label(field))}</option>`).join("")}</select><input id="adminFilterValue" class="control" placeholder="${esc(tr("research.filter_value","Exact filter value"))}"><button class="btn small" id="addAdminFilter">${esc(tr("research.add_filter","Add filter"))}</button></div><div class="filter-chip-row">${chips||`<span class="note">${esc(tr("research.no_filters","No database filters applied."))}</span>`}</div></details></section><section class="card db-global-results"><div class="cardhead"><div><b>${esc(tr("research.search_results","Search results"))}</b><div class="note">${state.storeSearchLoading?esc(tr("research.search_loading","Searching the corpus…")):state.storeSearchResults.length?`${state.storeSearchResults.length.toLocaleString()} ${esc(tr("research.results","results"))}`:esc(tr("research.record_search_empty","Run a search to find records."))}</div></div>${searchLayoutControls("database")}</div>${state.storeSearchLoading?loadingCardsHtml(tr("research.search_loading","Searching the corpus…"),3):databaseResultsHtml({admin:true,query:state.globalSearch})}</section></div>`;
  const run=async()=>{const query=String(main.querySelector("#adminGlobalQuery")?.value||"").trim();if(method!=="filter"&&!query)return;state.globalSearch=query;state.storeSearchLoading=true;state.storeSearchResults=[];persistPrefs();syncUrl({replace:true});renderAdminDatabaseGlobal(main);try{const body={query,mode:method,n_results:100,where:Object.keys(dbSearchWhere()).length?dbSearchWhere():null,fetch_k:Number(state.dbSearchFetchK||100),lambda_mult:Number(state.dbSearchLambda??0.7)};const data=await api(`/api/stores/${encodeURIComponent(state.activeStore)}/search`,{method:"POST",body:JSON.stringify(body)});state.storeSearchResults=data.results||[]}catch(error){toast(`${tr("research.search_failed","Search failed")}: ${error.message}`,{tone:"danger"})}finally{state.storeSearchLoading=false;persistPrefs();renderAdminDatabaseGlobal(main)}};
  main.querySelectorAll("[data-global-mode]").forEach(button=>button.onclick=()=>{state.globalSearchMode=button.dataset.globalMode;state.storeSearchResults=[];persistPrefs();syncUrl({replace:true});renderGlobal(main)});
  wireSearchLayoutControls(main,()=>renderAdminDatabaseGlobal(main));
  main.querySelector("#adminGlobalStore")?.addEventListener("change",event=>{state.activeStore=event.target.value;state.storeSearchResults=[];persistPrefs();syncUrl({replace:true});renderAdminDatabaseGlobal(main)});
  main.querySelector("#adminSearchMethod")?.addEventListener("change",event=>{state.dbSearchMethod=event.target.value;state.storeSearchResults=[];persistPrefs();syncUrl({replace:true});renderAdminDatabaseGlobal(main)});
  main.querySelector("#adminFetchK")?.addEventListener("change",event=>{state.dbSearchFetchK=Math.max(1,Number(event.target.value)||100);persistPrefs();syncUrl({replace:true})});main.querySelector("#adminLambda")?.addEventListener("change",event=>{state.dbSearchLambda=Math.max(0,Math.min(1,Number(event.target.value)||0.7));persistPrefs();syncUrl({replace:true})});
  main.querySelector("#runAdminGlobalSearch")?.addEventListener("click",run);main.querySelector("#adminGlobalQuery")?.addEventListener("keydown",event=>{if(event.key==="Enter"){event.preventDefault();void run()}});main.querySelector("#clearAdminGlobalSearch")?.addEventListener("click",()=>{state.globalSearch="";state.storeSearchResults=[];state.dbSearchWhere={};persistPrefs();syncUrl({replace:true});renderAdminDatabaseGlobal(main)});
  main.querySelector("#addAdminFilter")?.addEventListener("click",()=>{const field=main.querySelector("#adminFilterField")?.value;const value=main.querySelector("#adminFilterValue")?.value?.trim();if(field&&value){state.dbSearchWhere={...(state.dbSearchWhere||{}),[field]:value};persistPrefs();syncUrl({replace:true});renderAdminDatabaseGlobal(main)}});main.querySelectorAll("[data-remove-admin-filter]").forEach(button=>button.onclick=()=>{const next={...(state.dbSearchWhere||{})};delete next[button.dataset.removeAdminFilter];state.dbSearchWhere=next;persistPrefs();syncUrl({replace:true});renderAdminDatabaseGlobal(main)});
  main.querySelectorAll("[data-admin-db-edit]").forEach(button=>button.onclick=()=>{const result=state.storeSearchResults.find(item=>String(item.id||item.record?._chroma_id||item.record?.record_id||"")===String(button.dataset.adminDbEdit));if(result)openStoreRecordEditor({...result.record,_chroma_id:result.id})});
  // eslint-disable-next-line no-undef -- SA-11: existing missing runtime handler or stale variable; repair with workflow regression coverage.
  wireEvidenceButtons(main);decorateDisabledControls(main);
  if(state.globalSearchAutoRun){state.globalSearchAutoRun=false;persistPrefs();queueMicrotask(()=>void run())}
}

function renderGlobal(main){
  if(isResearcher())return renderResearcherGlobal(main);
  if(state.globalSearchMode==="database")return renderAdminDatabaseGlobal(main);
  return renderTraditionalGlobal(main);
}

function renderTraditionalGlobal(main){
  const fields=recordFields(),sort=state.globalSort;
  let rows=allRows().filter(x=>(!state.globalSearch||String(x.record.text||"").toLocaleLowerCase().includes(state.globalSearch.toLocaleLowerCase()))&&state.globalFilters.every(f=>valueMatches(x.record[f.field],f.op,f.value)));
  rows=sortRows(rows,sort);const pg=pageInfo(rows.length,state.globalPage);state.globalPage=pg.page;const slice=rows.slice(pg.start,pg.end);
  const reviewCount=state.reviewSelection.size;
  const flagged=needsReviewItems(rows).length;
  const pageSelected=slice.length>0&&slice.every(x=>state.reviewSelection.has(reviewKey(x.file,x.index)));
  const available=tableAvailableFields(allRows(),["__file","__db_status"]);
  // eslint-disable-next-line no-undef -- SA-11: existing missing runtime handler or stale variable; repair with workflow regression coverage.
  const columns=scope==="loaded"
    ? SEARCH_LOADED_COLUMNS.filter(key=>available.includes(key))
    : getTableColumns("global",available);
  main.innerHTML=`<div class="global-search-v25 unified-search"><section class="card search-mode-card"><div class="cardhead"><div><b>${esc(tr("context.global_search","Global Search"))}</b><div class="note">${esc(tr("research.global_search_admin_help","Search loaded records or switch to semantic search in the selected corpus database."))}</div></div></div><div class="view-tabs"><button class="view-tab active" data-global-mode="traditional">${esc(tr("research.traditional_search","Record search"))}</button><button class="view-tab" data-global-mode="database">${esc(tr("research.semantic_db_search","Semantic DB search"))}</button></div></section><section class="card filterpanel"><div class="filtertop"><div class="search"><input id="globalSearch" value="${esc(state.globalSearch)}" placeholder="${esc(tr("research.loaded_record_search_placeholder","Search record text across all loaded files"))}"></div><div class="tools"><button class="btn small" id="addFilter">+ ${esc(tr("research.add_metadata_filter","Add metadata filter"))}</button><button class="btn small" id="clearFilters">${esc(tr("research.clear_filters","Clear filters"))}</button></div></div><div class="filters">${state.globalFilters.map(f=>filterHtml(f,fields)).join("")}</div></section>
  <div class="toolbar search-results-toolbar"><div class="tools"><span class="note">${rows.length} matching records</span>${reviewCount?`<span class="selection-count">${reviewCount} selected</span>`:""}${searchLayoutControls("traditional")}</div><div class="tools">${reviewCount?`<button class="btn soft" id="reviewSelected">${icon("spark")}Review selected with LLM</button><button class="btn small" id="autoImproveSelected">${icon("spark")}Auto-improve selected</button><button class="btn small" id="bulkEditGlobalSelected">${icon("edit")}Bulk edit selected</button><button class="btn small" id="clearSelected">Clear selection</button>`:""}${flagged?`<button class="btn small soft" id="reviewNeedsReview">${icon("spark")}Review needs-review (${flagged})</button><button class="btn small" id="autoImproveNeedsReview">${icon("spark")}Auto-improve needs-review</button>`:""}<button class="btn small" id="selectResults">Select all results</button>${searchResultLayout("traditional")!=="cards"?`<button class="btn small" id="globalColumns">${esc(tr("records.columns","Columns"))}</button>`:""}<select class="control" id="globalSize">${[25,50,100,250].map(n=>`<option ${state.pageSize===n?"selected":""}>${n}</option>`).join("")}</select></div></div>
  ${workspaceResultsHtml(slice,columns,state.globalSearch,pageSelected)}${pager(pg,rows.length,"global")}</div>`;
  main.querySelectorAll("[data-global-mode]").forEach(button=>button.onclick=()=>{state.globalSearchMode=button.dataset.globalMode;state.storeSearchResults=[];persistPrefs();syncUrl({replace:true});renderGlobal(main)});
  wireSearchLayoutControls(main,()=>renderGlobal(main));
  const search=document.querySelector("#globalSearch");let globalSearchTimer=null;search.oninput=e=>{const pos=e.target.selectionStart;state.globalSearch=e.target.value;state.globalPage=1;persistPrefs();clearTimeout(globalSearchTimer);globalSearchTimer=setTimeout(()=>{if(state.view!=="global")return;syncUrl({replace:true});renderGlobal(main);requestAnimationFrame(()=>{const x=document.querySelector("#globalSearch");if(x){x.focus();x.setSelectionRange(pos,pos)}})},180)};
  document.querySelector("#globalSize").onchange=e=>{state.pageSize=+e.target.value;state.globalPage=1;persistPrefs();syncUrl({replace:true});renderGlobal(main)};
  document.querySelector("#addFilter").onclick=()=>{state.globalFilters.push({id:uid(),field:fields.includes("work")?"work":fields[0],op:"eq",value:""});persistPrefs();syncUrl({replace:true});renderGlobal(main)};
  document.querySelector("#clearFilters").onclick=()=>{state.globalSearch="";state.globalFilters=[];state.globalPage=1;persistPrefs();syncUrl({replace:true});renderGlobal(main)};
  document.querySelector("#selectResults").onclick=()=>{for(const x of rows)state.reviewSelection.add(reviewKey(x.file,x.index));persistPrefs();syncUrl({replace:true});renderGlobal(main)};
  document.querySelector("#reviewSelected")?.addEventListener("click",()=>openTouchup(selectedReviewItems()));
  document.querySelector("#autoImproveSelected")?.addEventListener("click",()=>openTouchup(selectedReviewItems(),"auto"));
  document.querySelector("#bulkEditGlobalSelected")?.addEventListener("click",()=>openBulkFieldEditor({rows:selectedReviewItems(),title:"Bulk edit selected records"}));
  document.querySelector("#reviewNeedsReview")?.addEventListener("click",()=>openTouchup(needsReviewItems(rows)));
  document.querySelector("#autoImproveNeedsReview")?.addEventListener("click",()=>openTouchup(needsReviewItems(rows),"auto"));
  document.querySelector("#clearSelected")?.addEventListener("click",()=>{clearReviewSelection();renderGlobal(main)});
  document.querySelector("#globalColumns")?.addEventListener("click",()=>openColumnChooser("global",available,()=>renderGlobal(main)));
  document.querySelector("#selectGlobalPage")?.addEventListener("change",e=>{for(const x of slice)setReviewSelected(x.file,x.index,e.target.checked);renderGlobal(main)});
  document.querySelectorAll("[data-select-key]").forEach(box=>box.onchange=e=>{e.stopPropagation();const item=reviewItemFromKey(box.dataset.selectKey);if(item)setReviewSelected(item.file,item.index,box.checked);renderGlobal(main)});
  document.querySelectorAll("[data-sort]").forEach(b=>b.onclick=()=>{toggleSort(sort,b.dataset.sort);state.globalPage=1;persistPrefs();syncUrl({replace:true});renderGlobal(main)});
  document.querySelectorAll("[data-card-open-record]").forEach(button=>button.addEventListener("click",event=>{event.stopPropagation();const card=button.closest("[data-f][data-i]");if(card)navigateTo("record",{fileId:card.dataset.f,index:+card.dataset.i})}));
  document.querySelectorAll("[data-card-cite-kind]").forEach(button=>button.addEventListener("click",event=>{event.stopPropagation();const card=button.closest("[data-f][data-i]"),file=state.files.find(f=>f.id===card?.dataset.f),record=file?.records?.[+card?.dataset.i];if(record)copyCitation(record,button.dataset.cardCiteKind)}));
  document.querySelectorAll("tr[data-f]").forEach(row=>row.onclick=e=>{if(e.target.closest("input,button,summary,details"))return;navigateTo("record",{fileId:row.dataset.f,index:+row.dataset.i})});
  document.querySelectorAll(".filterrow").forEach(row=>wireFilterRow(row,main));
  wirePager("global",pg,p=>{state.globalPage=p;persistPrefs();syncUrl({replace:true});renderGlobal(main)});
  refreshPresenceForRows(slice);
}
const numericFilterFields=new Set(["page_start","page_end","year","publication_year","text_length","extraction_quality","attribution_confidence","semantic_classification_confidence"]);
const collectionFilterFields=new Set(["topics","concepts","persons","works_referenced","institutions_referenced","locations_referenced","events_referenced","groups_referenced","languages_referenced","document_language","quoted_speaker","quotation_chain"]);
function filterOpsForField(field){
  if(numericFilterFields.has(field))return [["eq","equals"],["neq","not equal"],["gte","greater than or equal"],["lte","less than or equal"],["empty","is empty"],["notempty","is not empty"]];
  if(collectionFilterFields.has(field))return [["has","contains"],["nhas","does not contain"],["eq","equals exactly"],["neq","does not equal"],["empty","is empty"],["notempty","is not empty"]];
  return [["eq","equals"],["neq","not equal"],["has","contains"],["nhas","does not contain"],["empty","is empty"],["notempty","is not empty"]];
}
function filterHtml(f,fields){const ops=filterOpsForField(f.field);if(!ops.some(([value])=>value===f.op))f.op=ops[0][0];return `<div class="filterrow" data-filter="${f.id}"><label class="filter-cell"><span>Field</span><select class="control field">${fields.map(k=>`<option value="${esc(k)}" ${f.field===k?"selected":""}>${esc(label(k))}</option>`).join("")}</select></label><label class="filter-cell"><span>Condition</span><select class="control op">${ops.map(([v,l])=>`<option value="${v}" ${f.op===v?"selected":""}>${esc(l)}</option>`).join("")}</select></label><label class="filter-cell"><span>Value</span><input class="control value" value="${esc(f.value||"")}" placeholder="Filter value" ${["empty","notempty"].includes(f.op)?"disabled":""}></label><button class="btn small remove filter-remove" title="Remove filter" aria-label="Remove filter">×</button></div>`}
function wireFilterRow(row,main){
  const f=state.globalFilters.find(x=>x.id===row.dataset.filter);
  row.querySelector(".field").onchange=e=>{f.field=e.target.value;const allowed=filterOpsForField(f.field);if(!allowed.some(([value])=>value===f.op))f.op=allowed[0][0];state.globalPage=1;persistPrefs();syncUrl({replace:true});renderGlobal(main)};
  row.querySelector(".op").onchange=e=>{f.op=e.target.value;state.globalPage=1;persistPrefs();syncUrl({replace:true});renderGlobal(main)};
  row.querySelector(".value").onchange=e=>{f.value=e.target.value;state.globalPage=1;persistPrefs();syncUrl({replace:true});renderGlobal(main)};
  row.querySelector(".remove").onclick=()=>{state.globalFilters=state.globalFilters.filter(x=>x!==f);persistPrefs();syncUrl({replace:true});renderGlobal(main)};
}


// 0.36.10 native Search bridge. SearchView owns presentation while the runtime
// continues to own browser-local corpus state, Chroma transport, evidence
// selection, URL serialization, and the existing LLM review workflows.
const SEARCH_FACET_FIELDS=["work","needs_review","__db_status","document_author","quoted_speaker","speaker","position_holder","discourse_role","document_language","topics","concepts"];
const SEARCH_FILTER_FIELDS=["work","document_author","year","document_language","original_language","speaker","quoted_speaker","position_holder","target","discourse_role","proposition_status","stance","topics","concepts","persons","needs_review"];
const SEARCH_AUTOCOMPLETE_EXCLUDED=new Set(["text","extracted_text","extractedText","raw_text","ocr_text","updates"]);

function searchScope(){return state.globalSearchMode==="database"||isResearcher()?"database":"loaded"}
function searchLayout(scope=searchScope()){
  const key=scope==="database"?"database":"traditional";
  const value=state.searchResultLayouts?.[key]|| (key==="database"?"cards":"compact");
  return ["compact","roomy","cards"].includes(value)?value:(key==="database"?"cards":"compact");
}
function searchFacetRawValues(record,field,row=null){
  if(field==="needs_review")return [record?.needs_review?"true":"false"];
  if(field==="__db_status"){
    if(row?.file)return [recordDbStatus(row.file,row.index,record).kind];
    return ["exists"];
  }
  const value=record?.[field];
  if(value==null||value==="")return [];
  if(Array.isArray(value))return value.flatMap(item=>item==null?[]:[String(item).trim()]).filter(Boolean);
  if(typeof value==="object")return Object.values(value).flatMap(item=>item==null?[]:[String(item).trim()]).filter(Boolean);
  return [String(value).trim()].filter(Boolean);
}
function searchFacetDisplay(field,value){
  if(field==="needs_review")return value==="true"?tr("search.needs_review","Needs review"):tr("search.reviewed","Reviewed");
  if(field==="__db_status"){
    const labelsByKind={synced:tr("search.db_synced","Synced"),changed:tr("search.db_pending","Pending"),exists:tr("search.db_in_database","In DB"),absent:tr("search.db_not_in_database","Not in DB"),unknown:tr("search.db_unknown","Unknown"),none:tr("search.db_none","No database")};
    return labelsByKind[value]||value;
  }
  return value||tr("ui.none","None");
}
function searchFacetMatches(record,field,selected,row=null){
  if(!selected?.length)return true;
  const values=searchFacetRawValues(record,field,row).map(value=>String(value).toLocaleLowerCase());
  return selected.some(value=>values.includes(String(value).toLocaleLowerCase()));
}
function searchRowMatchesFacets(row,excludeField=""){
  for(const [field,values] of Object.entries(state.searchFacetFilters||{})){
    if(field===excludeField||!Array.isArray(values)||!values.length)continue;
    if(!searchFacetMatches(row.record,field,values,row))return false;
  }
  return true;
}
function searchRecordMatchesFacets(record,excludeField=""){
  for(const [field,values] of Object.entries(state.searchFacetFilters||{})){
    if(field===excludeField||!Array.isArray(values)||!values.length)continue;
    if(!searchFacetMatches(record,field,values,null))return false;
  }
  return true;
}
function localSearchBaseRows(){
  const q=String(state.globalSearch||"").trim().toLocaleLowerCase();
  return allRows().filter(row=>(!q||String(row.record.text||"").toLocaleLowerCase().includes(q))&&state.globalFilters.every(filter=>valueMatches(row.record[filter.field],filter.op,filter.value)));
}
function searchFacetCountsFromRows(baseRows,field){
  const counts=new Map();
  for(const row of baseRows){
    if(!searchRowMatchesFacets(row,field))continue;
    for(const value of searchFacetRawValues(row.record,field,row))counts.set(value,(counts.get(value)||0)+1);
  }
  return counts;
}
function searchFacetCountsFromRecords(records,field){
  const counts=new Map();
  for(const record of records){
    if(!searchRecordMatchesFacets(record,field))continue;
    for(const value of searchFacetRawValues(record,field,null))counts.set(value,(counts.get(value)||0)+1);
  }
  return counts;
}
function buildSearchFacets(source,{database=false}={}){
  const rows=database?null:source;
  const records=database?source:null;
  return SEARCH_FACET_FIELDS.filter(field=>!(database&&field==="__db_status")).map(field=>{
    const counts=database?searchFacetCountsFromRecords(records,field):searchFacetCountsFromRows(rows,field);
    const selected=new Set((state.searchFacetFilters?.[field]||[]).map(String));
    const values=[...counts.entries()].sort((a,b)=>b[1]-a[1]||String(a[0]).localeCompare(String(b[0]))).slice(0,20).map(([value,count])=>({value:String(value),label:searchFacetDisplay(field,String(value)),count,selected:selected.has(String(value))}));
    for(const value of selected){if(!values.some(item=>item.value===value))values.push({value,label:searchFacetDisplay(field,value),count:0,selected:true})}
    return {field,label:label(field),values};
  }).filter(facet=>facet.values.length);
}
function searchSuggestions(recordsOrRows,{database=false}={}){
  const out={};
  const rows=database?recordsOrRows.map(record=>({record})):recordsOrRows;
  const fields=[...new Set([...SEARCH_FILTER_FIELDS,...recordFields().filter(field=>!SEARCH_AUTOCOMPLETE_EXCLUDED.has(field))])];
  for(const field of fields){
    if(SEARCH_AUTOCOMPLETE_EXCLUDED.has(field))continue;
    const values=new Set();
    for(const row of rows){
      for(const value of searchFacetRawValues(row.record,field,row.file?row:null)){
        const text=String(value).trim();if(text&&text.length<=180)values.add(text);
        if(values.size>=120)break;
      }
      if(values.size>=120)break;
    }
    if(values.size)out[field]=[...values].sort((a,b)=>a.localeCompare(b,undefined,{numeric:true,sensitivity:"base"}));
  }
  return out;
}
function searchFilterDescriptor(filter){
  const ops=filterOpsForField(filter.field);const op=ops.find(([value])=>value===filter.op);
  return {id:String(filter.id||uid()),field:String(filter.field||""),field_label:label(filter.field||""),op:String(filter.op||"eq"),op_label:tr(`search.operator_${filter.op}`,op?.[1]||filter.op||"equals"),value:String(filter.value??"")};
}
function dbSearchFilterDescriptors(){
  return Object.entries(dbSearchWhere()).map(([field,value])=>{
    const contains=value&&typeof value==="object"&&"$contains" in value;
    return {id:`db:${field}`,field,field_label:label(field),op:contains?"has":"eq",op_label:contains?tr("search.operator_has","contains"):tr("search.operator_eq","equals"),value:String(contains?value.$contains:value??"")};
  });
}
function searchColumnOptions(available){return available.map(key=>({key,label:label(key)}))}
function searchSimilarity(distance){
  if(distance==null||!Number.isFinite(Number(distance)))return null;
  return Math.max(0,Math.min(1,1/(1+Math.max(0,Number(distance)))));
}
function searchMatchReasons(record,query,{database=false,method="similarity"}={}){
  const reasons=[];const terms=String(query||"").toLocaleLowerCase().split(/\s+/).filter(term=>term.length>2);
  for(const field of ["work","document_author","speaker","quoted_speaker","position_holder","target","discourse_role","topics","concepts","persons"]){
    if(!terms.length)break;
    const text=display(record?.[field]).toLocaleLowerCase();
    if(terms.some(term=>text.includes(term)))reasons.push(label(field));
    if(reasons.length>=3)break;
  }
  if(database&&method==="similarity")reasons.unshift(tr("search.semantic_match","Semantic similarity"));
  if(database&&method==="mmr")reasons.unshift(tr("search.mmr_match","Semantic relevance + diversity"));
  if(database&&method==="filter")reasons.unshift(tr("search.filter_match","Metadata filter match"));
  if(!database&&terms.length&&String(record?.text||"").toLocaleLowerCase().includes(terms[0]))reasons.unshift(tr("search.text_match","Text match"));
  return [...new Set(reasons)].slice(0,4);
}
function buildWorkspaceSearchResult(row){
  const record=row.record;const selectionKey=reviewKey(row.file,row.index);const evidenceKey=workspaceEvidenceSelectionKey(row.file,row.index);
  return {key:`workspace:${selectionKey}`,kind:"workspace",file_id:row.file.id,file_name:row.file.name,index:row.index,record_id:String(record.record_id||row.index+1),work:String(record.work||""),page_span:mlaPageSpan(record,{prefix:false}),text:String(record.text||""),record:cloneAuditValue(record),db_status:recordDbStatus(row.file,row.index,record),selected:state.reviewSelection.has(selectionKey),evidence_selected:evidenceIsSelected(evidenceKey),evidence_available:hasCapability("evidence.select"),distance:null,similarity:null,mmr_score:null,match_reasons:searchMatchReasons(record,state.globalSearch,{database:false})};
}
function buildDatabaseSearchResult(item){
  const record=item.record||{};const id=String(item.id||record._chroma_id||record.record_id||"");const evidenceKey=dbEvidenceKey(state.activeStore,id);
  return {key:`database:${state.activeStore}:${id}`,kind:"database",collection:state.activeStore,chroma_id:id,record_id:String(record.record_id||id),work:String(record.work||""),page_span:mlaPageSpan(record,{prefix:false}),text:String(record.text||""),record:cloneAuditValue(record),db_status:{kind:"exists",label:tr("search.db_in_database","In DB"),title:state.activeStore},selected:false,evidence_selected:evidenceIsSelected(evidenceKey),evidence_available:hasCapability("evidence.select"),distance:item.distance??null,similarity:searchSimilarity(item.distance),mmr_score:item.mmr_score??null,match_reasons:searchMatchReasons(record,state.globalSearch,{database:true,method:state.dbSearchMethod})};
}
function sortDatabaseSearchResults(results){
  const sort=state.storeSearchSort||{key:"similarity",dir:-1};const dir=Number(sort.dir)||1;const key=sort.key||"similarity";
  return [...results].sort((a,b)=>{
    let av,bv;
    if(key==="similarity"){av=a.similarity??-1;bv=b.similarity??-1}
    else if(key==="page_start"){av=Number(a.record?.page_start??0);bv=Number(b.record?.page_start??0)}
    else {av=String(a.record?.[key]??"");bv=String(b.record?.[key]??"")}
    if(typeof av==="number"&&typeof bv==="number")return (av-bv)*dir;
    return String(av).localeCompare(String(bv),undefined,{numeric:true,sensitivity:"base"})*dir;
  });
}
async function getSearchWorkspaceSnapshot({refresh=true,autoRun=true}={}){
  // Native Search may be re-entered through Vue breadcrumb/history navigation.
  // Keep the legacy state owner aligned without rewriting the URL that brought
  // the user here; popstate/app bootstrap already restore encoded URL state.
  state.view="global";
  if(refresh){try{await refreshStores()}catch(error){console.warn("Search store refresh failed",error)}}
  const stores=recordStores();
  if(!state.activeStore&&stores.length)state.activeStore=stores[0].name;
  if(state.activeStore&&!stores.some(store=>store.name===state.activeStore))state.activeStore=stores[0]?.name||"";
  if(isResearcher())state.globalSearchMode="database";
  if(autoRun&&state.globalSearchAutoRun&&searchScope()==="database"&&stores.length){state.globalSearchAutoRun=false;persistPrefs();await runSearchWorkspace({silent:true})}
  const scope=searchScope();const layout=searchLayout(scope);const pageSize=Math.max(10,Number(state.pageSize)||100);
  let results=[],total=0,facets=[],suggestions={},available=[],filters=[];
  if(scope==="loaded"){
    const base=localSearchBaseRows();let rows=base.filter(row=>searchRowMatchesFacets(row));rows=sortRows(rows,state.globalSort);
    total=rows.length;const pages=Math.max(1,Math.ceil(total/pageSize));state.globalPage=Math.max(1,Math.min(pages,Number(state.globalPage)||1));const start=(state.globalPage-1)*pageSize;const slice=rows.slice(start,start+pageSize);
    await refreshPresenceForRows(slice).catch(()=>undefined);
    results=slice.map(buildWorkspaceSearchResult);facets=buildSearchFacets(base);suggestions=searchSuggestions(allRows());available=tableAvailableFields(allRows(),["__file",...SEARCH_LOADED_COLUMNS]);filters=state.globalFilters.map(searchFilterDescriptor);
  }else{
    let dbItems=(state.storeSearchResults||[]).map(buildDatabaseSearchResult).filter(result=>searchRecordMatchesFacets(result.record));dbItems=sortDatabaseSearchResults(dbItems);total=dbItems.length;const pages=Math.max(1,Math.ceil(total/pageSize));state.globalPage=Math.max(1,Math.min(pages,Number(state.globalPage)||1));const start=(state.globalPage-1)*pageSize;results=dbItems.slice(start,start+pageSize);const records=(state.storeSearchResults||[]).map(item=>item.record||{});facets=buildSearchFacets(records,{database:true});suggestions=searchSuggestions(records,{database:true});available=tableAvailableFields(records.map(record=>({record})),["__db_status"]);filters=dbSearchFilterDescriptors();
  }
  if(!available.includes("__db_status"))available.unshift("__db_status");
  const columns=getTableColumns("global",available);
  const pages=Math.max(1,Math.ceil(total/pageSize));
  const filterFields=[...new Set([...SEARCH_FILTER_FIELDS,...available.filter(field=>!field.startsWith("__")&&!SEARCH_AUTOCOMPLETE_EXCLUDED.has(field))])].filter(Boolean).sort((a,b)=>label(a).localeCompare(label(b)));
  return {ready:true,is_researcher:isResearcher(),scope,query:String(state.globalSearch||""),method:["similarity","mmr","filter"].includes(state.dbSearchMethod)?state.dbSearchMethod:"similarity",fetch_k:Math.max(1,Number(state.dbSearchFetchK)||100),lambda_mult:Math.max(0,Math.min(1,Number(state.dbSearchLambda??0.7))),advanced_open:Boolean(state.globalAdvancedOpen),stores:stores.map(store=>({name:store.name,count:Number(store.count||0)})),active_store:state.activeStore||"",has_database:stores.length>0,has_loaded_records:allRows().length>0,total_loaded_records:allRows().length,results,total,page:state.globalPage,page_size:pageSize,pages,layout,sort:scope==="database"?(state.storeSearchSort||{key:"similarity",dir:-1}):(state.globalSort||{key:"__file",dir:1}),columns:searchColumnOptions(columns),available_columns:searchColumnOptions(available),facets,filters,filter_fields:searchColumnOptions(filterFields),filter_suggestions:suggestions,selection_count:state.reviewSelection.size,selected_evidence_count:selectedEvidenceEntries().length,loading:Boolean(state.storeSearchLoading),search_has_run:scope==="loaded"||Boolean(state.searchDatabaseRan||state.storeSearchResults.length),capabilities:{can_select:scope==="loaded"&&canUse("editLocalRecords"),can_review:scope==="loaded"&&canUse("editLocalRecords"),can_bulk_edit:scope==="loaded"&&canUse("editLocalRecords"),can_manage_database:canUse("manageCorpus"),can_select_evidence:hasCapability("evidence.select")}};
}
async function setSearchScope(scope){
  const next=scope==="database"||isResearcher()?"database":"traditional";state.globalSearchMode=next;state.globalPage=1;state.storeSearchResults=[];state.searchDatabaseRan=false;persistPrefs();syncUrl({replace:false});shell();return getSearchWorkspaceSnapshot({refresh:true,autoRun:false});
}
function updateSearchQuery(value,{replace=true}={}){state.globalSearch=String(value||"");state.globalPage=1;persistPrefs();syncUrl({replace});return state.globalSearch}
function setSearchAdvancedOpen(value){state.globalAdvancedOpen=Boolean(value);persistPrefs();syncUrl({replace:true})}
function setSearchMethod(method){
  if(!["similarity","mmr","filter"].includes(method))return;
  if(method!=="filter"){
    const previous=state.dbSearchWhere||{};
    const safe=Object.fromEntries(Object.entries(previous).filter(([,value])=>!(value&&typeof value==="object"&&Object.prototype.hasOwnProperty.call(value,"$contains"))));
    if(Object.keys(safe).length!==Object.keys(previous).length){
      state.dbSearchWhere=safe;
      toast(tr("search.contains_filter_removed","Contains metadata filters are available only in Filters only mode and were removed."),{tone:"info"});
    }
  }
  state.dbSearchMethod=method;state.storeSearchResults=[];state.searchDatabaseRan=false;state.globalPage=1;persistPrefs();syncUrl({replace:true});
}
function setSearchStore(name){state.activeStore=recordStores().some(store=>store.name===name)?name:(recordStores()[0]?.name||"");state.storeSearchResults=[];state.searchDatabaseRan=false;state.globalPage=1;persistPrefs();syncUrl({replace:true});shell()}
function setSearchMmrOptions({fetch_k,lambda_mult}={}){if(fetch_k!=null)state.dbSearchFetchK=Math.max(1,Math.min(1000,Number(fetch_k)||100));if(lambda_mult!=null)state.dbSearchLambda=Math.max(0,Math.min(1,Number(lambda_mult)||0));persistPrefs();syncUrl({replace:true})}
function setSearchLayout(layout){if(!["compact","roomy","cards"].includes(layout))return;const key=searchScope()==="database"?"database":"traditional";state.searchResultLayouts={...(state.searchResultLayouts||{}),[key]:layout};persistPrefs();syncUrl({replace:true})}
function setSearchPage(page){state.globalPage=Math.max(1,Number(page)||1);persistPrefs();syncUrl({replace:true})}
function setSearchPageSize(size){state.pageSize=Math.max(10,Math.min(500,Number(size)||100));state.globalPage=1;persistPrefs();syncUrl({replace:true})}
function setSearchColumns(columns){
  const scope=searchScope();
  const available=scope==="loaded"?tableAvailableFields(allRows(),["__file",...SEARCH_LOADED_COLUMNS]):tableAvailableFields((state.storeSearchResults||[]).map(item=>({record:item.record||{}})),["__db_status"]);
  if(scope==="loaded"){
    // Loaded-record Search has one stable table contract: DB status, Work,
    // Page Start, Needs Review, Extracted Text, followed by Actions.
    state.tableColumns.global=SEARCH_LOADED_COLUMNS.filter(key=>available.includes(key));
  }else{
    state.tableColumns.global=[...new Set((columns||[]).map(String))].filter(key=>available.includes(key));
    if(!state.tableColumns.global.length)state.tableColumns.global=TABLE_DEFAULTS.global.filter(key=>available.includes(key));
  }
  persistPrefs();syncUrl({replace:true});
}
function setSearchSort(key){
  if(searchScope()==="database"){
    const sort=state.storeSearchSort||{key:"similarity",dir:-1};state.storeSearchSort={key,dir:sort.key===key?-Number(sort.dir||1):(key==="similarity"?-1:1)};
  }else toggleSort(state.globalSort,key);
  state.globalPage=1;persistPrefs();syncUrl({replace:true});
}
function toggleSearchFacet(field,value){
  const next={...(state.searchFacetFilters||{})};const values=new Set(Array.isArray(next[field])?next[field].map(String):[]);const token=String(value);values.has(token)?values.delete(token):values.add(token);if(values.size)next[field]=[...values];else delete next[field];state.searchFacetFilters=next;state.globalPage=1;persistPrefs();syncUrl({replace:true});
}
function clearSearchFacetFilters(){state.searchFacetFilters={};state.globalPage=1;persistPrefs();syncUrl({replace:true})}
function clearSearchAllFilters(){state.searchFacetFilters={};state.globalFilters=[];state.dbSearchWhere={};state.globalPage=1;state.storeSearchResults=[];state.searchDatabaseRan=false;persistPrefs();syncUrl({replace:true})}
/** @param {{field?: string, op?: string, value?: string}} [options] */
function addSearchAdvancedFilter({field="",op="eq",value=""}={}){
  field=String(field||"");value=String(value??"").trim();if(!field)return;
  if(searchScope()==="database"){
    if(!value)return;const next={...(state.dbSearchWhere||{})};next[field]=op==="has"?{$contains:value}:value;state.dbSearchWhere=next;state.storeSearchResults=[];state.searchDatabaseRan=false;
  }else{
    const nextOp=filterOpsForField(field).some(([candidate])=>candidate===op)?op:"eq";if(!["empty","notempty"].includes(nextOp)&&!value)return;state.globalFilters=[...(state.globalFilters||[]),{id:uid(),field,op:nextOp,value}];
  }
  state.globalPage=1;persistPrefs();syncUrl({replace:true});
}
function removeSearchAdvancedFilter(id){
  if(String(id).startsWith("db:")){const field=String(id).slice(3);const next={...(state.dbSearchWhere||{})};delete next[field];state.dbSearchWhere=next;state.storeSearchResults=[];state.searchDatabaseRan=false}else state.globalFilters=(state.globalFilters||[]).filter(filter=>String(filter.id)!==String(id));
  state.globalPage=1;persistPrefs();syncUrl({replace:true});
}
async function runSearchWorkspace({silent=false}={}){
  if(searchScope()!=="database")return getSearchWorkspaceSnapshot({refresh:false,autoRun:false});
  await refreshStores().catch(()=>undefined);const stores=recordStores();if(!stores.length){if(canAccessPage("vector"))openDatabaseCreationFromResearch();return getSearchWorkspaceSnapshot({refresh:false,autoRun:false})}
  if(!state.activeStore||!stores.some(store=>store.name===state.activeStore))state.activeStore=stores[0].name;
  const method=["similarity","mmr","filter"].includes(state.dbSearchMethod)?state.dbSearchMethod:"similarity";const query=String(state.globalSearch||"").trim();if(method!=="filter"&&!query){if(!silent)toast(tr("search.enter_query","Enter a search query first."),{tone:"warn"});return getSearchWorkspaceSnapshot({refresh:false,autoRun:false})}
  state.dbSearchFetchK=Math.max(1,Math.min(1000,Number(state.dbSearchFetchK)||100));state.dbSearchLambda=Math.max(0,Math.min(1,Number(state.dbSearchLambda??0.7)));state.storeSearchLoading=true;state.searchDatabaseRan=true;state.globalPage=1;persistPrefs();syncUrl({replace:true});
  try{
    const safeWhere=safeDbSearchWhere(method);state.dbSearchWhere=safeWhere;
    const body={query,mode:method,n_results:100,where:Object.keys(safeWhere).length?safeWhere:null,fetch_k:state.dbSearchFetchK,lambda_mult:state.dbSearchLambda};
    const data=await api(`/api/stores/${encodeURIComponent(state.activeStore)}/search`,{method:"POST",body:JSON.stringify(body)});state.storeSearchResults=Array.isArray(data?.results)?data.results:[];
  }catch(error){state.storeSearchResults=[];if(!silent)toast(`${tr("research.search_failed","Search failed")}: ${error.message}`,{tone:"danger"})}
  finally{state.storeSearchLoading=false;persistPrefs();syncUrl({replace:true})}
  return getSearchWorkspaceSnapshot({refresh:false,autoRun:false});
}
function searchResultFromKey(key){
  const token=String(key||"");if(token.startsWith("workspace:"))return reviewItemFromKey(token.slice("workspace:".length));
  if(token.startsWith("database:")){
    const rest=token.slice("database:".length);const split=rest.indexOf(":");const collection=split>=0?rest.slice(0,split):state.activeStore;const id=split>=0?rest.slice(split+1):rest;const item=(state.storeSearchResults||[]).find(result=>String(result.id||result.record?._chroma_id||result.record?.record_id||"")===id);return item?{collection,id,record:item.record||{},item}:null;
  }
  return null;
}
async function searchResultAction(key,action){
  const result=searchResultFromKey(key);if(!result)return false;
  if(String(key).startsWith("workspace:")){
    if(action==="open"){navigateTo("record",{fileId:result.file.id,index:result.index});return true}
    if(action==="citation-inline"){await copyCitation(result.record,"inline");return true}
    if(action==="citation-full"){await copyCitation(result.record,"full");return true}
    if(action==="evidence"){toggleWorkspaceEvidence(result.file,result.index);return true}
    if(action==="select"){setReviewSelected(result.file,result.index,!state.reviewSelection.has(reviewKey(result.file,result.index)));return true}
  }else{
    if(action==="open"||action==="edit"){
      if(isResearcher()){state.activeStore=result.collection;state.researcherRecordId=result.id;persistPrefs();navigateTo("record")}else openStoreRecordEditor({...result.record,_chroma_id:result.id});return true;
    }
    if(action==="citation-inline"){await copyCitation(result.record,"inline");return true}
    if(action==="citation-full"){await copyCitation(result.record,"full");return true}
    if(action==="evidence"){toggleDbEvidence(result.collection,result.id,result.record);return true}
  }
  return false;
}
function setSearchResultSelected(key,selected){const item=searchResultFromKey(key);if(item?.file)setReviewSelected(item.file,item.index,Boolean(selected));}
function setSearchPageSelected(keys,selected){for(const key of keys||[])setSearchResultSelected(key,selected);persistPrefs()}
function clearSearchSelection(){clearReviewSelection()}
function runSearchSelectionAction(action){
  const items=selectedReviewItems();if(!items.length)return;
  if(action==="review")return openTouchup(items);
  if(action==="improve")return openTouchup(items,"auto");
  if(action==="bulk")return openBulkFieldEditor({rows:items,title:tr("search.bulk_edit_selected","Bulk edit selected records")});
}
function getSearchShareHref(){const path=urlFromState();return new URL(path,location.origin).href}
function restoreSearchViewFromHref(href){
  const url=new URL(String(href||""),location.origin);const token=url.searchParams.get("ts");state.view="global";if(token)applyCompressedTableUrlState(decompressUrlState(token),"global");const store=url.searchParams.get("store");if(store)state.activeStore=store;state.storeSearchResults=[];state.searchDatabaseRan=false;if(searchScope()==="database"&&(state.globalSearch||Object.keys(dbSearchWhere()).length))state.globalSearchAutoRun=true;persistPrefs();syncUrl({replace:false});shell();return getSearchWorkspaceSnapshot({refresh:true,autoRun:true});
}

function recordsListCell(row,key,query){
  const record=row.record;
  if(key==="__db_status"){
    const info=recordDbStatus(row.file,row.index,record);
    return {key,kind:"status",text:info.label,title:info.title||"",status_kind:info.kind};
  }
  if(key==="page_start")return {key,kind:"pages",text:pages(record),title:""};
  if(key==="needs_review")return {key,kind:"review",text:record.needs_review?"yes":"no",title:""};
  if(key==="text")return {key,kind:"text",text:snippet(record.text,query),title:""};
  if(key==="inline_citation")return {key,kind:"plain",text:inlineCitation(record),title:""};
  if(key==="full_citation")return {key,kind:"plain",text:fullCitation(record),title:""};
  if(key==="record_id")return {key,kind:"id",text:display(record[key]),title:""};
  const value=record[key];
  return {key,kind:metadataSearchable(key,value)?"metadata":"plain",text:display(value),title:"",meta_value:Array.isArray(value)?String(value[0]??""):String(value??""),meta_contains:Array.isArray(value)};
}

function getRecordsListSnapshot(){
  const files=state.files.map(file=>describeRecordsFile(file,state.activeFileId));
  const stores=recordStores();
  const shared=Boolean(new URLSearchParams(location.search).get("file"));
  const capabilities={
    can_select:canUse("editLocalRecords"),
    can_review:canUse("editLocalRecords"),
    can_bulk_edit:canUse("editLocalRecords"),
    can_upsert:canUse("manageCorpus")&&hasCorpusDb(),
    can_import:canUse("manageCorpus"),
    can_select_evidence:hasCapability("evidence.select"),
  };
  const f=activeFile();
  if(!f){
    return {
      available:false,shared,files,file:null,query:"",rows:[],columns:[],available_columns:[],
      sort:{key:"page_start",dir:1},filters:{},page:1,pages:1,page_size:state.pageSize,start:0,end:0,
      matched:0,total:0,flagged:0,selection_count:state.reviewSelection.size,page_selected:false,
      stores:stores.map(store=>({name:store.name,count:Number(store.count||0)})),
      active_store:state.activeStore||"",has_database:stores.length>0,
      db_unavailable_reason:dbUnavailableReason(),capabilities,
    };
  }
  const query=state.searches[f.id]||"";
  const sort=state.sorts[f.id]||(state.sorts[f.id]={key:"page_start",dir:1});
  const filters=state.listFilters[f.id]||{};
  let rows=f.records.map((record,index)=>({file:f,record,index}))
    .filter(x=>!query||String(x.record.text||"").toLocaleLowerCase().includes(query.toLocaleLowerCase()))
    .filter(x=>rowMatchesListFilters(x,filters));
  rows=sortRows(rows,sort);
  const pg=pageInfo(rows.length,state.pages[f.id]||1);state.pages[f.id]=pg.page;
  const slice=rows.slice(pg.start,pg.end);
  try{refreshPresenceForRows(slice)}catch{/* presence is best-effort */}
  const flagged=needsReviewItems(f.records.map((record,index)=>({file:f,record,index}))).length;
  const pageSelected=slice.length>0&&slice.every(x=>state.reviewSelection.has(reviewKey(f,x.index)));
  const available=tableAvailableFields(f.records.map((record,index)=>({file:f,record,index})),["__db_status","work","page_start","needs_review","text"]);
  const columnKeys=getTableColumns("list",available);
  return {
    available:true,shared,files,
    file:describeRecordsFile(f,state.activeFileId),
    query,rows:slice.map(x=>{
      const key=reviewKey(f,x.index);
      const evidenceKey=workspaceEvidenceSelectionKey(f,x.index);
      const status=recordDbStatus(f,x.index,x.record);
      return {
        index:x.index,key,record_id:String(x.record.record_id||`#${x.index+1}`),
        work:String(x.record.work||""),selected:state.reviewSelection.has(key),
        evidence_selected:evidenceIsSelected(evidenceKey),
        db_status:{kind:status.kind,label:status.label,title:status.title||""},
        cells:columnKeys.map(column=>recordsListCell(x,column,query)),
      };
    }),
    columns:columnKeys.map(key=>({key,label:label(key)})),
    available_columns:available.map(key=>({key,label:label(key)})),
    sort:{key:sort.key,dir:sort.dir},filters:{...filters},
    page:pg.page,pages:pg.pages,page_size:state.pageSize,start:pg.start,end:pg.end,
    matched:rows.length,total:f.records.length,flagged,selection_count:state.reviewSelection.size,
    page_selected:pageSelected,
    stores:stores.map(store=>({name:store.name,count:Number(store.count||0)})),
    active_store:state.activeStore||"",has_database:stores.length>0,
    db_unavailable_reason:dbUnavailableReason(),capabilities,
  };
}
function setRecordsListQuery(value){
  const f=activeFile();if(!f)return;
  state.searches[f.id]=String(value||"");state.pages[f.id]=1;persistPrefs();syncUrl({replace:true});
}
function setRecordsListStore(name){setActiveStore(name);shell()}
function setRecordsListPage(page){
  const f=activeFile();if(!f)return;
  state.pages[f.id]=Math.max(1,Number(page)||1);persistPrefs();syncUrl({replace:true});
}
function setRecordsListPageSize(size){
  const f=activeFile();if(!f)return;
  state.pageSize=Number(size)||state.pageSize;state.pages[f.id]=1;persistPrefs();syncUrl({replace:true});
}
function setRecordsListSort(key){
  const f=activeFile();if(!f)return;
  const sort=state.sorts[f.id]||(state.sorts[f.id]={key:"page_start",dir:1});
  toggleSort(sort,key);state.pages[f.id]=1;persistPrefs();syncUrl({replace:true});
}
function setRecordsListFilter(key,value){
  const f=activeFile();if(!f)return;
  setListFilterValue(f.id,key,value);state.pages[f.id]=1;syncUrl({replace:true});
}
function clearRecordsListFilters(){
  const f=activeFile();if(!f)return;
  state.listFilters[f.id]={};state.pages[f.id]=1;persistPrefs();syncUrl({replace:true});
}
function setRecordsListRowSelected(index,selected){
  const f=activeFile();if(!f)return;
  setReviewSelected(f,index,selected);syncUrl({replace:true});
}
function setRecordsListPageSelected(selected){
  const snapshot=getRecordsListSnapshot();
  const f=activeFile();if(!f)return;
  for(const row of snapshot.rows)setReviewSelected(f,row.index,selected);
  syncUrl({replace:true});
}
function selectRecordsListMatches(){
  const f=activeFile();if(!f)return;
  const query=state.searches[f.id]||"";
  const filters=state.listFilters[f.id]||{};
  const rows=f.records.map((record,index)=>({file:f,record,index}))
    .filter(x=>!query||String(x.record.text||"").toLocaleLowerCase().includes(query.toLocaleLowerCase()))
    .filter(x=>rowMatchesListFilters(x,filters));
  for(const x of rows)state.reviewSelection.add(reviewKey(f,x.index));
  persistPrefs();syncUrl({replace:true});
}
function clearRecordsListSelection(){clearReviewSelection();syncUrl({replace:true})}
function openRecordsListRecord(index){
  const f=activeFile();if(!f)return;
  navigateTo("record",{fileId:f.id,index});
}
function copyRecordsListJson(index){
  const f=activeFile();const record=f?.records?.[index];
  if(record)copyJsonToClipboard(record,record.record_id||"record");
}
function copyRecordsListCitation(index,kind){
  const f=activeFile();const record=f?.records?.[index];
  if(record)copyCitation(record,kind||"inline");
}
function toggleRecordsListEvidence(index){
  const f=activeFile();if(!f)return;
  toggleWorkspaceEvidence(f,index);shell();
}
function recordsListMetadataSearch(field,value,contains){
  return searchByMetadata(field,value,{contains:Boolean(contains)});
}
function setRecordsListColumns(keys){
  const list=Array.isArray(keys)?keys.filter(Boolean):[];
  if(list.length)state.tableColumns.list=list;
  persistPrefs();syncUrl({replace:true});
}
function resetRecordsListColumns(){
  state.tableColumns.list=[...TABLE_DEFAULTS.list];
  persistPrefs();syncUrl({replace:true});
}
function getRecordsListShareHref(){const path=urlFromState();return new URL(path,location.origin).href}
function recordsListCommand(name){
  const f=activeFile();
  if(name==="import"){document.querySelector("#fileInput")?.click();return Promise.resolve()}
  if(name==="ocr")return Promise.resolve(canUse("editLocalRecords")?openOcrCleanupDialog():toast("Your role does not have permission to edit records."));
  if(!f)return Promise.resolve();
  if(name==="reviewSelected")return Promise.resolve(openTouchup(selectedReviewItems()));
  if(name==="improveSelected")return Promise.resolve(openTouchup(selectedReviewItems(),"auto"));
  if(name==="bulkSelected")return Promise.resolve(openBulkFieldEditor({rows:selectedReviewItems(),title:tr("search.bulk_edit_selected","Bulk edit selected records")}));
  if(name==="upsertSelected")return upsertRows(rowsFromReviewSelection(),"selected records");
  if(name==="reviewFlagged")return Promise.resolve(openTouchup(needsReviewItems(f.records.map((record,index)=>({file:f,record,index})))));
  if(name==="improveFlagged")return Promise.resolve(openTouchup(needsReviewItems(f.records.map((record,index)=>({file:f,record,index}))),"auto"));
  if(name==="upsertFile")return upsertRows(f.records.map((record,index)=>({file:f,record,index})),"records");
  return Promise.resolve();
}

const ligatures={"ﬀ":"ff","ﬁ":"fi","ﬂ":"fl","ﬃ":"ffi","ﬄ":"ffl","ﬅ":"ft","ﬆ":"st"};
function cleanText(text){
  let s=String(text??""),before=s;
  s=s.replace(/[ﬀﬁﬂﬃﬄﬅﬆ]/g,c=>ligatures[c]||c)
    .replace(/\u00ad/g,"")
    // eslint-disable-next-line no-misleading-character-class -- SA-15: OCR Unicode matching needs corpus fixtures before changing character semantics.
    .replace(/[\u200b\u200c\u200d\u2060\ufeff\ufffe\uffff]/g,"")
    .replace(/([A-Za-zÀ-ÖØ-öø-ÿ])-[ \t]*\r?\n[ \t]*([a-zà-öø-ÿ])/g,"$1$2")
    .replace(/\r\n/g,"\n");
  return {text:s,changed:s!==before};
}
function cleanRecord(f,i){
  const c=cleanText(f.records[i].text);if(!c.changed)return toast("No supported ligatures or artifacts found");
  const changed=applyRecordChanges(f,i,{text:c.text},{source:"ocr_cleanup"});
  shell();renderView();toast(`${changed} tracked change${changed===1?"":"s"} applied`);
}
async function cleanFile(f){
  if(!await openMessageModal({title:"Clean entire JSONL file?",message:`Apply conservative cleanup to all ${f.records.length} records in ${f.name}?`,confirmLabel:"Run cleanup",cancelLabel:"Cancel"}))return;
  const batchId=uid();let recordsChanged=0,fieldsChanged=0;
  f.records.forEach((r,i)=>{const c=cleanText(r.text);if(!c.changed)return;const n=applyRecordChanges(f,i,{text:c.text},{source:"ocr_cleanup",batchId});if(n){recordsChanged++;fieldsChanged+=n}});
  persistFile(f);shell();renderView();toast(`${recordsChanged} records cleaned · ${fieldsChanged} tracked changes`);
}

function cleanRows(rows){
  const batchId=uid();let recordsChanged=0,fieldsChanged=0;
  for(const row of rows){
    const current=row.file.records[row.index];
    const cleaned=cleanText(current?.text);
    if(!cleaned.changed)continue;
    const n=applyRecordChanges(row.file,row.index,{text:cleaned.text},{source:"ocr_cleanup",batchId});
    if(n){recordsChanged++;fieldsChanged+=n}
  }
  shell();renderView();
  toast(`${recordsChanged} records cleaned · ${fieldsChanged} tracked changes`);
}
function openOcrCleanupDialog(){
  if(!state.files.length)return toast("Load JSONL records first");
  const dialog=document.createElement("dialog");
  const selected=selectedReviewItems();
  const active=activeFile();
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Clean OCR Artifacts</h2><div class="dialog-subtitle">Conservative ligature, zero-width character, and broken line-hyphen cleanup. No paraphrasing.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db ocr-clean-options"><button class="scope-card" data-scope="active" ${active?"":"disabled"}><b>Active JSONL tab</b><span>${active?`${active.records.length.toLocaleString()} records · ${esc(active.name)}`:"No active tab"}</span></button><button class="scope-card" data-scope="selected" ${selected.length?"":"disabled"}><b>Selected records</b><span>${selected.length.toLocaleString()} currently selected</span></button><button class="scope-card" data-scope="review"><b>Needs-review records</b><span>${needsReviewItems().length.toLocaleString()} flagged records</span></button><button class="scope-card" data-scope="all"><b>All loaded records</b><span>${allRows().length.toLocaleString()} records across ${state.files.length} tabs</span></button></div><div class="da"><button class="btn" data-close>Cancel</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelectorAll("[data-scope]").forEach(button=>button.onclick=async()=>{
    let rows=[];
    if(button.dataset.scope==="active"&&active)rows=active.records.map((record,index)=>({file:active,record,index}));
    else if(button.dataset.scope==="selected")rows=selected.map(item=>({file:item.file,record:item.record,index:item.index}));
    else if(button.dataset.scope==="review")rows=needsReviewItems().map(item=>({file:item.file,record:item.record,index:item.index}));
    else rows=allRows();
    if(!rows.length)return toast("No records in that scope");
    close();
    if(await openMessageModal({title:"Run OCR cleanup?",message:`Run conservative OCR cleanup on ${rows.length.toLocaleString()} records?`,confirmLabel:"Run cleanup",cancelLabel:"Cancel"}))cleanRows(rows);
  });
}


const EDITOR_GROUPS = [
  {name:"Source", fields:["record_id","work","document_author","edition","year","page_start","page_end","region_type","region_author","primary_text","canonical_work_id","pdf_file","pdf_pages"]},
  {name:"Discourse", fields:["speaker","position_holder","target","discourse_role","proposition_status","semantic_function","stance","claim_scope"]},
  {name:"Quotation provenance", fields:["is_direct_quote","quoted_speaker","quoted_author","quoted_work","quoted_position_holder","quoted_addressee","quoted_referent","quotation_chain"]},
  {name:"Indexing", fields:["topics","concepts","persons","works_referenced"]},
  {name:"Quality / review", fields:["attribution_confidence","semantic_classification_confidence","extraction_quality","needs_review","review_reason"]},
  {name:"Language / translation", fields:["document_language","original_language","document_is_translation","translator"]},
  {name:"Citation", fields:["inline_citation","full_citation"]},
  {name:"Text", fields:["text","text_length"]},
];

function openEditor(){
  const f=activeFile(),i=selectedIndex(f),r=selectedRecord();if(!r)return;
  const dialog=document.createElement("dialog");
  const used=new Set();
  const groups=[];
  for(const group of EDITOR_GROUPS){
    const fields=group.fields.filter(k=>k in r);
    if(!fields.length)continue;
    fields.forEach(k=>used.add(k));
    groups.push(`<section class="editor-section"><h3>${esc(group.name)}</h3><div class="editor-grid">${fields.map(k=>fieldEditor(k,r[k])).join("")}</div></section>`);
  }
  const other=Object.keys(r).filter(k=>!used.has(k) && k!=="updates");
  if(other.length)groups.push(`<section class="editor-section"><h3>Other fields</h3><div class="editor-grid">${other.map(k=>fieldEditor(k,r[k])).join("")}</div></section>`);
  dialog.innerHTML=`<form><div class="dh"><div><h2 class="dialog-title">Edit record</h2><div class="dialog-subtitle">${esc(r.record_id||"")} · ${esc(r.work||f.name)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body">${groups.join("")}</div><div class="da"><div class="llm-footer-note">Changes stay local until you export or upsert them.</div><button class="btn" type="button" data-close>Cancel</button><button class="btn primary">${icon("check")}Save changes</button></div></form>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  dialog.querySelectorAll("[data-close]").forEach(b=>b.onclick=()=>{dialog.close();dialog.remove()});
  dialog.querySelector("form").onsubmit=e=>{
    e.preventDefault();
    const next={...r};
    try{
      dialog.querySelectorAll("[data-key]").forEach(el=>next[el.dataset.key]=parseEditor(el));
    }catch(error){
      openMessageModal({title:"Could not save record",message:error.message,tone:"danger"});return;
    }
    if("text_length" in next)next.text_length=String(next.text||"").length;
    const changes={};
    for(const [field,value] of Object.entries(next))if(field!=="updates"&&!sameValue(r[field],value))changes[field]=value;
    const count=applyRecordChanges(f,i,changes,{source:"manual"});
    dialog.close();dialog.remove();shell();renderView();count?toast(`Saved ${count} tracked change${count===1?"":"s"}`,{tone:"success"}):toast("No changes to save");
  };
}

function fieldEditor(k,v){
  const t=Array.isArray(v)?"array":v===null?"null":typeof v;
  const full=["text","edition","review_reason","full_citation","quotation_chain"].includes(k);
  const cls=`field ${full?"field-full":""}`;
  if(t==="boolean")return `<div class="${cls}"><label>${esc(label(k))}</label><label class="boolean-control"><input data-key="${esc(k)}" data-type="boolean" type="checkbox" ${v?"checked":""}><span>${v?"Enabled":"Disabled"}</span></label></div>`;
  if(k==="text")return `<div class="${cls}"><label>${esc(label(k))}</label><textarea class="long" data-key="${esc(k)}" data-type="string">${esc(v||"")}</textarea></div>`;
  if(t==="array"||t==="object")return `<div class="${cls}"><label>${esc(label(k))} · JSON</label><textarea data-key="${esc(k)}" data-type="json">${esc(JSON.stringify(v,null,2))}</textarea></div>`;
  return `<div class="${cls}"><label>${esc(label(k))}</label><input data-key="${esc(k)}" data-type="${t}" ${t==="number"?'type="number" step="any"':""} value="${esc(v??"")}"></div>`;
}

function parseEditor(el){if(el.dataset.type==="boolean")return el.checked;if(el.dataset.type==="number")return el.value===""?null:+el.value;if(el.dataset.type==="null")return el.value===""?null:el.value;if(el.dataset.type==="json")return JSON.parse(el.value);return el.value}

function exportMenu(){
  const dialog=document.createElement("dialog");
  dialog.innerHTML=`<div class="dh"><h2 style="margin:0;font-size:16px">${esc(tr("export.title","Export JSONL"))}</h2><button class="btn" data-close>${esc(tr("ui.close","Close"))}</button></div><div class="db"><div class="tools"><button class="btn" data-export="current">${esc(tr("export.current","Current file"))}</button><button class="btn" data-export="changed">${esc(tr("export.changed","Changed files"))}</button><button class="btn" data-export="all">${esc(tr("export.all","All files separately"))}</button><button class="btn" data-export="aggregate">${esc(tr("export.aggregate","Aggregate JSONL"))}</button><button class="btn" data-export="both">${esc(tr("export.changed_aggregate","Changed + aggregate"))}</button></div></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);dialog.querySelector("[data-close]").onclick=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-export]").forEach(button=>button.onclick=()=>{doExport(button.dataset.export);dialog.close();dialog.remove()});
}
function downloadBlob(blob,name){const u=URL.createObjectURL(blob);const a=document.createElement("a");a.href=u;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),500)}
function download(name,text){downloadBlob(new Blob([text],{type:"application/x-ndjson"}),name)}
function fileJsonl(f){return f.records.map(r=>JSON.stringify(r)).join("\n")+"\n"}
function doExport(kind){
  const current=activeFile(),changed=state.files.filter(f=>f.dirty.size);
  if(kind==="current"&&current)download(current.name,fileJsonl(current));
  if(kind==="changed")changed.forEach((f,i)=>setTimeout(()=>download(f.name,fileJsonl(f)),i*160));
  if(kind==="all")state.files.forEach((f,i)=>setTimeout(()=>download(f.name,fileJsonl(f)),i*160));
  if(kind==="aggregate"||kind==="both")download("derridai-aggregate.jsonl",state.files.flatMap(f=>f.records).map(r=>JSON.stringify(r)).join("\n")+"\n");
  if(kind==="both")changed.forEach((f,i)=>setTimeout(()=>download(f.name,fileJsonl(f)),250+i*160));
}

async function currentPdfPageText(){
  const result=await extractPdfPageSmart(state.pdf.page);
  state.pdf.text=result.text;
  state.pdf.extractionSource=result.source;
  state.pdf.extractError=result.warning||"";
  return result.text||"";
}
function openLlmTaskLauncher({
  task,
  title,
  description="",
  contextText="",
  payload={},
  generationProvider=null,
  generationModel=null,
  onForegroundResult=null,
}={}){
  const profiles=providerProfiles();
  if(!profiles.length)return toast("Configure an LLM provider first");
  let profileId=state.appConfig.default_provider_profile||profiles[0].id;
  if(task==="rag_grade"&&generationModel){
    const independent=profiles.find(item=>!(item.type===generationProvider&&String(item.model||"")===String(generationModel)));
    if(independent)profileId=independent.id;
  }
  let runMode=task==="rag_grade_batch"?"background":(isResearcher()?"foreground":"background");
  const dialog=document.createElement("dialog");
  dialog.className="llm-tool-launcher";

  const render=()=>{
    const profile=providerProfile(profileId);
    const status=state.providerStatuses?.[profile.id]||{};
    const sameModel=Boolean(
      generationModel
      && String(profile.model||"")===String(generationModel)
      && (!generationProvider||profile.type===generationProvider)
    );
    dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">${esc(description)}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db llm-tool-body">
      ${contextText?`<section class="llm-tool-context"><span>Question / prompt</span><p>${esc(contextText)}</p></section>`:""}
      ${sameModel?`<div class="info warn"><b>Same-model grading warning.</b> This provider/model was also used to generate the RAG answer. Self-grading can be systematically biased; use a different model for a more independent evaluation.</div>`:""}
      <div class="llm-tool-grid">
        <div class="field field-wide"><label>Provider profile</label><select class="control" id="toolProvider">${profiles.map(item=>`<option value="${esc(item.id)}" ${item.id===profile.id?"selected":""}>${esc(providerDisplayName(item))} · ${item.type==="ollama"?"Ollama":"OpenAI-compatible"}</option>`).join("")}</select></div>
        <div class="field"><label>Run mode</label><select class="control" id="toolRunMode" ${isResearcher()||task==="rag_grade_batch"?"disabled":""}>${task==="rag_grade_batch"?'<option value="background" selected>Background operation</option>':isResearcher()?'<option value="foreground" selected>Interactive foreground</option>':`<option value="background" ${runMode==="background"?"selected":""}>Background operation</option><option value="foreground" ${runMode==="foreground"?"selected":""}>Interactive foreground</option>`}</select></div>
        <div class="field field-wide"><label>Model</label><input class="control" id="toolModel" value="${esc(profile.type==="openai"&&profile.model_mode==="auto"?"auto":profile.model||"")}" ${profile.type==="openai"&&profile.model_mode==="auto"?"disabled":""}></div>
        <div class="field"><label>Max concurrent requests</label><input class="control" value="${esc(profile.max_concurrent_requests??1)}" disabled></div>
        ${profile.type==="ollama"?`<div class="field"><label>Context</label><input class="control" id="toolCtx" type="number" value="${esc(profile.num_ctx??16384)}"></div><div class="field"><label>Think</label><select class="control" id="toolThink">${[["false","Off"],["true","On"],["low","Low"],["medium","Medium"],["high","High"]].map(([v,l])=>`<option value="${v}" ${String(profile.think??"false")===v?"selected":""}>${l}</option>`).join("")}</select></div>`:""}
        <div class="field"><label>Max output tokens</label><input class="control" id="toolPredict" type="number" value="${esc(profile.num_predict??4096)}"></div>
        <div class="field"><label>Temperature</label><input class="control" id="toolTemp" type="number" step="0.01" value="${esc(profile.temperature??0)}"></div>
        <div class="field"><label>top_p</label><input class="control" id="toolTopP" type="number" step="0.01" value="${esc(profile.top_p??1)}"></div>
        <div class="field"><label>Seed</label><input class="control" id="toolSeed" type="number" value="${esc(profile.seed??"")}"></div>
        <div class="field field-wide"><label>Advanced options JSON</label><textarea id="toolExtra" spellcheck="false">${esc(profile.extra_options||"{}")}</textarea></div>
      </div>
      <div class="tools llm-tool-profile-actions"><button class="btn small" id="toolWarm">${icon("spark")}Warm this provider</button>${isResearcher()?"":`<button class="btn small" id="toolProviders">${icon("gear")}Manage providers</button>`}<span class="note" id="toolStatus">${status.available?"Endpoint ready":status.error||"Not verified"}</span></div>
    </div>
    <div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="runLlmTask">${icon("spark")}${runMode==="background"?"Start background operation":"Run now"}</button></div>`;
    const close=()=>{dialog.close();dialog.remove()};
    dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
    dialog.querySelector("#toolProvider").onchange=e=>{profileId=e.target.value;render()};
    dialog.querySelector("#toolRunMode").onchange=e=>{runMode=e.target.value;render()};
    dialog.querySelector("#toolProviders")?.addEventListener("click",()=>{close();navigateTo("providers")});
    dialog.querySelector("#toolWarm").onclick=async()=>{const el=dialog.querySelector("#toolStatus");el.textContent="Warming…";await warmupProviderProfile(profileId);el.textContent=state.providerWarmups?.[profileId]?.message||"Warmup requested"};
    dialog.querySelector("#runLlmTask").onclick=async()=>{
      const active=providerProfile(profileId);
      if(!active)return toast("Choose an available provider profile before continuing.");
      if(!["ollama","openai"].includes(String(active.type||"")))return toast("The selected provider profile is not supported by this operation.");
      const config=providerRequestConfig(active,{textReview:true});
      let extra={};
      try{extra=JSON.parse(dialog.querySelector("#toolExtra").value||"{}");if(!extra||Array.isArray(extra)||typeof extra!=="object")throw new Error("Advanced options must be an object")}
      catch(error){return toast(error.message)}
      const n=id=>{const raw=dialog.querySelector(`#${id}`)?.value;if(raw===""||raw==null)return null;const value=Number(raw);return Number.isFinite(value)?value:null};
      let think=false;
      if(active.type==="ollama"){const raw=dialog.querySelector("#toolThink")?.value||"false";think=raw==="true"?true:["low","medium","high"].includes(raw)?raw:false}
      const generation=sanitizeResearchGeneration({...config.ollama,num_ctx:active.type==="ollama"?n("toolCtx"):null,num_predict:n("toolPredict")??4096,think,temperature:n("toolTemp")??0,top_p:n("toolTopP")??1,seed:n("toolSeed"),extra_options:extra});
      const model=active.type==="openai"&&active.model_mode==="auto"?"auto":String(dialog.querySelector("#toolModel")?.value||"").trim();
      if(!model)return toast("Select a model before continuing.");
      if(task==="rag_grade"&&(!String(payload.question||"").trim()||!String(payload.answer||"").trim()))return toast("A completed Research question and answer are required before grading.");
      const direct={...payload,provider:active.type,model,base_url:active.base_url||null,api_key:active.type==="openai"?active.api_key||"":null,generation};
      const button=dialog.querySelector("#runLlmTask");button.disabled=true;button.textContent=runMode==="background"?"Starting…":"Running…";
      try{
        if(runMode==="background"){
          const body={task,label:title,provider_profile_id:active.id,max_concurrent_requests:Math.max(1,Math.min(64,Number(active.max_concurrent_requests)||1)),pdf:task.startsWith("pdf_")?direct:null,grade:task==="rag_grade"?direct:null,grade_batch:task==="rag_grade_batch"?{provider:direct.provider,model:direct.model,base_url:direct.base_url,api_key:direct.api_key,generation:direct.generation,provider_profile_id:active.id,max_concurrent_requests:Math.max(1,Math.min(64,Number(active.max_concurrent_requests)||1))}:null};
          const job=await api("/api/jobs/llm-tool",{method:"POST",body:JSON.stringify(body)});
          state.jobs=[job,...state.jobs.filter(item=>item.id!==job.id)];syncJobProgressToasts();startJobPolling();close();toast(`${title} started in background`);
        }else{
          if(task==="rag_grade_batch")throw new Error("Cache-wide grading runs as a background operation.");
          const endpoint=task==="rag_grade"?"/api/rag/grade":"/api/pdf/llm";
          const result=await api(endpoint,{method:"POST",body:JSON.stringify(direct)});
          close();if(onForegroundResult)await onForegroundResult(result);
        }
      }catch(error){button.disabled=false;button.innerHTML=`${icon("spark")}${runMode==="background"?"Start background operation":"Run now"}`;toast(`${title} failed: ${error.message}`)}
    };
  };
  document.body.appendChild(dialog);showAppModal(dialog);render();
}
async function applyPdfLinkMatch(match){
  if(!match?.key)return openMessageModal({title:"No supported record match",message:match?.reason||"The model did not identify a sufficiently supported record."});
  const item=reviewItemFromKey(match.key);
  if(!item)return openMessageModal({title:"Matched record unavailable",message:"The matched record is no longer loaded.",tone:"danger"});
  const confidence=Number(match.confidence);
  const approved=await openMessageModal({
    title:"Link PDF page to record?",
    message:`PDF page ${state.pdf.page} → ${item.record.record_id||"matched record"}\n\n${Number.isFinite(confidence)?`${Math.round(confidence*100)}% confidence`:"Confidence not reported"}${match.reason?`\n${match.reason}`:""}`,
    confirmLabel:"Link page",cancelLabel:"Cancel",
  });
  if(!approved)return;
  linkPdfPage(item.file,item.index,state.pdf.page);
  toast(`Linked page ${state.pdf.page} to ${item.record.record_id||"record"}`);
}
function openLlmToolResult(job){
  const result=job.result;
  if(!result)return openMessageModal({title:"Result unavailable",message:"This completed LLM operation does not contain a retained result. Open full details to inspect the operation.",tone:"danger"});
  const dialog=document.createElement("dialog");
  dialog.className="llm-tool-result-dialog";
  const task=job.tool||job.mode;
  if(task==="work_metadata"){dialog.remove();return openWorkMetadataProposalResult(job)}
  let body="",actions="";
  if(task==="pdf_clean_text"){body=`<section class="card-inset"><div class="cardhead"><b>Cleaned page text</b></div><pre class="llm-tool-text">${esc(result.text||"")}</pre></section>`;actions='<button class="btn primary" id="useToolText">Use as current page text</button>'}
  else if(task==="pdf_draft_record"){body=`<pre class="rag-json">${esc(JSON.stringify(result.record||{},null,2))}</pre>`;actions='<button class="btn primary" id="openToolDraft">Review / add draft</button>'}
  else if(task==="pdf_link_record"){body=`<div class="llm-tool-match"><b>${esc(result.match?.record_id||"No supported match")}</b><p>${esc(result.match?.reason||"")}</p></div>`;actions=result.match?.key?'<button class="btn primary" id="applyToolLink">Review & link page</button>':""}
  else if(task==="rag_grade"){
    const question=job.request?.question||"";
    body=`${question?`<section class="llm-tool-context"><span>Question / prompt</span><p>${esc(question)}</p></section>`:""}${result.response_cache_error?`<div class="info warn">The grade completed, but saving it to the response cache failed: ${esc(result.response_cache_error)}</div>`:""}${ragGradeHtml(result.grade||{})}`;
  }
  else if(task==="rag_grade_batch"){
    body=`<section class="bulk-grade-result"><div class="compare-result-summary"><div><strong>${Number(result.graded||0).toLocaleString()}</strong><span>graded</span></div><div><strong>${Number(result.failed||0).toLocaleString()}</strong><span>failed</span></div><div><strong>${Number(result.total||0).toLocaleString()}</strong><span>responses</span></div></div>${Array.isArray(result.errors)&&result.errors.length?`<details><summary>Errors (${result.errors.length})</summary><pre class="rag-json">${esc(JSON.stringify(result.errors,null,2))}</pre></details>`:'<div class="info">All cached responses were processed.</div>'}</section>`;
  }
  else body=`<pre class="rag-json">${esc(JSON.stringify(result,null,2))}</pre>`;
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">${esc(jobLabel(job))}</h2><div class="dialog-subtitle">${esc(job.provider||"")} · ${esc(job.model||result.model||"")}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db">${body}</div><div class="da"><button class="btn" data-close>Close</button>${actions}</div>`;
  document.body.appendChild(dialog);const close=()=>{dialog.close();dialog.remove()};dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);showAppModal(dialog);
  dialog.querySelector("#useToolText")?.addEventListener("click",()=>{state.pdf.text=result.text||"";state.pdf.extractionSource=`LLM cleanup · ${job.model||result.model||"model"}`;close();if(state.view==="pdf")renderPdf(document.querySelector("#main"))});
  dialog.querySelector("#openToolDraft")?.addEventListener("click",()=>{close();openPdfDraftRecord(result.record||{})});
  dialog.querySelector("#applyToolLink")?.addEventListener("click",async()=>{await applyPdfLinkMatch(result.match||{});close()});
}
function normalizeRagGrade(value){
  let grade=value;
  if(grade&&typeof grade==="object"&&!Array.isArray(grade)){
    if(grade.grade&&typeof grade.grade==="object"&&!Array.isArray(grade.grade))grade=grade.grade;
    else if(grade.result&&typeof grade.result==="object"&&!Array.isArray(grade.result))grade=grade.result;
  }
  if(!grade||typeof grade!=="object"||Array.isArray(grade))grade={summary:grade==null?"":String(grade)};
  const scores=grade.scores&&typeof grade.scores==="object"&&!Array.isArray(grade.scores)?grade.scores:{};
  const list=value=>{
    if(value==null||value==="")return [];
    if(Array.isArray(value))return value.flatMap(item=>list(item));
    if(typeof value==="object")return Object.entries(value).map(([key,item])=>`${label(key)}: ${display(item)}`);
    return [String(value)];
  };
  const score=key=>{
    const raw=grade[key]??scores[key];
    if(raw==null||raw==="")return "—";
    if(typeof raw==="object"){
      const nested=raw.score??raw.value??raw.rating;
      return nested==null?display(raw):nested;
    }
    return raw;
  };
  return {
    raw:grade,score,
    summary:String(grade.summary??grade.overall_summary??grade.assessment??""),
    strengths:list(grade.strengths??grade.strength),
    weaknesses:list(grade.weaknesses??grade.weakness),
    unsupported_or_risky_claims:list(grade.unsupported_or_risky_claims??grade.risky_claims??grade.unsupported_claims),
  };
}
function ragGradeHtml(grade={}){
  const normalized=normalizeRagGrade(grade);
  const scoreKeys=[["query_relevance","Query relevance"],["source_binding","Source binding"],["claim_traceability","Claim traceability"],["attribution_source_discrimination","Attribution/source discrimination"],["claim_evidence_fidelity","Claim/evidence fidelity"],["conceptual_precision","Conceptual precision"],["coverage","Coverage"],["interpretive_usefulness","Interpretive usefulness"],["overall","Overall"]];
  const sections=[["Strengths",normalized.strengths],["Weaknesses",normalized.weaknesses],["Unsupported or risky claims",normalized.unsupported_or_risky_claims]];
  return `<div class="rag-grade-content"><div class="rag-grade-scores">${scoreKeys.map(([key,name])=>`<div><span>${esc(name)}</span><strong>${esc(normalized.score(key))}</strong><small>/10</small></div>`).join("")}</div><section><b>Summary</b><p>${esc(normalized.summary||"No summary returned.")}</p></section>${sections.map(([name,items])=>`<section><b>${esc(name)}</b><ul>${items.map(item=>`<li>${esc(item)}</li>`).join("")||"<li>None reported.</li>"}</ul></section>`).join("")}</div>`;
}

function currentPdfLlmConfig(){
  const profile=defaultProviderProfile();
  if(!profile)throw new Error("Configure an LLM provider first.");
  const config=providerRequestConfig(profile,{textReview:true});
  return {profile,config};
}
async function callPdfLlm(mode,{candidates=[],rawText=null}={}){
  const raw_text=rawText===null?await currentPdfPageText():String(rawText||"");
  if(!raw_text.trim()&&mode!=="link_record"){
    throw new Error("No extractable text was found on the current page. Raster-only pages still require OCR/vision extraction.");
  }
  const {profile,config}=currentPdfLlmConfig();
  return api("/api/pdf/llm",{
    method:"POST",
    body:JSON.stringify({
      mode,
      raw_text,
      pdf_file:state.pdf.name||null,
      pdf_title:state.pdf.title||null,
      pdf_author:state.pdf.author||null,
      pdf_page:state.pdf.page,
      candidates,
      provider:config.provider,
      model:config.model,
      base_url:config.base_url,
      api_key:config.api_key,
      generation:config.ollama,
    }),
  });
}
function openPdfDraftRecord(record){
  const dialog=document.createElement("dialog");
  dialog.className="pdf-draft-dialog";
  const files=state.files;
  const stores=recordStores();
  dialog.innerHTML=`<div class="dh"><div><h2 class="dialog-title">Draft record from PDF page</h2><div class="dialog-subtitle">${esc(state.pdf.title||state.pdf.name)} · page ${state.pdf.page} · unsaved draft</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db pdf-draft-body">
    <div class="info warn">This is a draft generated by an LLM. Review attribution, page metadata, quotation provenance, and text before saving.</div>
    <textarea class="pdf-draft-json" id="pdfDraftJson" spellcheck="false">${esc(JSON.stringify(record,null,2))}</textarea>
    <div class="pdf-draft-targets">
      <div class="field"><label>JSONL destination</label><select class="control" id="pdfDraftFile"><option value="">Do not add to JSONL</option>${files.map(file=>`<option value="${esc(file.id)}">${esc(file.name)} · ${file.records.length} records</option>`).join("")}</select></div>
      <div class="field"><label>Chroma destination</label><select class="control" id="pdfDraftStore" ${stores.length?"":`disabled data-disabled-reason="Create or restore a corpus vector database before upserting PDF drafts." title="Create or restore a corpus vector database before upserting PDF drafts."`}><option value="">${stores.length?"Do not upsert to Chroma":"No corpus database available"}</option>${stores.map(store=>`<option value="${esc(store.name)}">${esc(store.name)} · ${Number(store.count||0).toLocaleString()} records</option>`).join("")}</select></div>
    </div>
  </div>
  <div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="savePdfDraft">${icon("check")}Add draft</button></div>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(button=>button.onclick=close);
  dialog.querySelector("#savePdfDraft").onclick=async()=>{
    let draft;
    try{
      draft=JSON.parse(dialog.querySelector("#pdfDraftJson").value);
      if(!draft||typeof draft!=="object"||Array.isArray(draft))throw new Error("Draft must be one JSON object.");
    }catch(error){return toast(`Invalid draft JSON: ${error.message}`)}
    if(!draft.record_id)draft.record_id=`pdf-draft-${Date.now()}`;
    draft.needs_review=true;
    draft.updates=Array.isArray(draft.updates)?draft.updates:[];
    draft.pdf_file=state.pdf.name||draft.pdf_file||null;
    draft.pdf_pages=[...new Set([...(Array.isArray(draft.pdf_pages)?draft.pdf_pages:[]),state.pdf.page])].sort((a,b)=>a-b);
    draft.text_length=String(draft.text||"").length;

    const fileId=dialog.querySelector("#pdfDraftFile").value;
    const storeName=dialog.querySelector("#pdfDraftStore").value;
    if(!fileId&&!storeName)return toast("Choose a JSONL file, a Chroma collection, or both.");

    if(fileId){
      const file=state.files.find(item=>item.id===fileId);
      if(!file)return toast("Selected JSONL file is no longer loaded");
      file.records.push(cloneAuditValue(draft));
      file.dirty.add(file.records.length-1);
      await persistFileNow(file);
    }
    if(storeName){
      try{
        await api(`/api/stores/${encodeURIComponent(storeName)}/records`,{
          method:"POST",
          body:JSON.stringify({record:upsertRecordPayload(draft)}),
        });
        await refreshStores();
      }catch(error){
        return toast(`Draft was added to JSONL where selected, but Chroma upsert failed: ${error.message}`);
      }
    }
    close();shell();renderView();
    toast(`Draft ${draft.record_id} added${fileId&&storeName?" to JSONL and Chroma":fileId?" to JSONL":" to Chroma"}`,{tone:"success"});
  };
}
function rankPdfLinkCandidates(rawText){
  const titleTokens=new Set(String(state.pdf.title||state.pdf.name||"").toLocaleLowerCase().split(/\W+/).filter(token=>token.length>3));
  const page=Number(state.pdf.page);
  const pageTokens=new Set(String(rawText||"").toLocaleLowerCase().split(/\W+/).filter(token=>token.length>5).slice(0,140));
  return allRows().map(({file,record,index})=>{
    let score=0;
    const work=String(record.work||record.document_title||"").toLocaleLowerCase();
    score+=work.split(/\W+/).filter(token=>token.length>3&&titleTokens.has(token)).length*6;
    const start=Number(record.page_start),end=Number(record.page_end??record.page_start);
    if(Number.isFinite(start)&&Number.isFinite(end)&&page>=Math.min(start,end)&&page<=Math.max(start,end))score+=10;
    if(pdfLinks(record).some(link=>link.pdf_file===state.pdf.name))score+=12;
    score+=Math.min(12,String(record.text||"").toLocaleLowerCase().split(/\W+/).filter(token=>token.length>5&&pageTokens.has(token)).slice(0,140).length);
    return {score,candidate:{key:reviewKey(file,index),record_id:record.record_id||"",work:record.work||"",pages:pages(record),citation:record.inline_citation||record.full_citation||"",text:String(record.text||"").slice(0,600)}};
  }).sort((a,b)=>b.score-a.score).slice(0,32).map(item=>item.candidate);
}
async function cleanPdfPageWithLlm(){
  try{
    const raw_text=await currentPdfPageText();if(!raw_text.trim())return toast("No extractable text was found on this page");
    openLlmTaskLauncher({task:"pdf_clean_text",title:"Clean PDF page text",description:`${state.pdf.title||state.pdf.name} · page ${state.pdf.page}`,payload:{mode:"clean_text",raw_text,pdf_file:state.pdf.name||null,pdf_title:state.pdf.title||null,pdf_author:state.pdf.author||null,pdf_page:state.pdf.page,candidates:[]},onForegroundResult:async result=>{state.pdf.text=result.text||"";state.pdf.extractionSource=`LLM cleanup · ${result.model||"model"} · page ${state.pdf.page}`;state.pdf.extractError="";renderPdf(document.querySelector("#main"))}});
  }catch(error){toast(`Could not prepare LLM cleanup: ${error.message}`)}
}
async function draftPdfPageWithLlm(){
  try{
    const raw_text=await currentPdfPageText();if(!raw_text.trim())return toast("No extractable text was found on this page");
    openLlmTaskLauncher({task:"pdf_draft_record",title:"Create draft record from PDF page",description:`${state.pdf.title||state.pdf.name} · page ${state.pdf.page}`,payload:{mode:"draft_record",raw_text,pdf_file:state.pdf.name||null,pdf_title:state.pdf.title||null,pdf_author:state.pdf.author||null,pdf_page:state.pdf.page,candidates:[]},onForegroundResult:async result=>openPdfDraftRecord(result.record||{})});
  }catch(error){toast(`Could not prepare draft generation: ${error.message}`)}
}
async function linkPdfPageWithLlm(){
  if(!state.files.length)return toast("Load JSONL records before asking the LLM to match this PDF page.");
  try{
    const raw_text=await currentPdfPageText(),candidates=rankPdfLinkCandidates(raw_text);
    if(!candidates.length)return toast("No candidate records are loaded");
    openLlmTaskLauncher({task:"pdf_link_record",title:"Link PDF page to record",description:`${state.pdf.title||state.pdf.name} · page ${state.pdf.page} · ${candidates.length} pre-ranked candidates`,payload:{mode:"link_record",raw_text,pdf_file:state.pdf.name||null,pdf_title:state.pdf.title||null,pdf_author:state.pdf.author||null,pdf_page:state.pdf.page,candidates},onForegroundResult:async result=>applyPdfLinkMatch(result.match||{})});
  }catch(error){toast(`Could not prepare LLM record matching: ${error.message}`)}
}

function renderPdf(main){
  if(state.view==="pdf")syncUrl({replace:true});
  const loaded=Boolean(state.pdf.file);
  const canRender=Boolean(state.pdf.doc);
  const extractReady=Boolean(state.pdf.doc||state.pdf.file);
  const linked=loaded?linkedPdfRows(state.pdf.page):[];
  const allRelated=loaded?allLinkedRowsForLoadedPdf():[];
  const relatedQuery=String(state.pdf.relatedSearch||"").trim().toLocaleLowerCase();
  const related=allRelated.filter(({file,record,pages})=>
    !relatedQuery
    ||[
      file.name,
      record.record_id,
      record.work,
      record.document_author,
      record.inline_citation,
      record.full_citation,
      pages.join(" "),
    ].some(value=>String(value||"").toLocaleLowerCase().includes(relatedQuery))
  );
  const selectedFile=activeFile();
  const selected=selectedRecord();
  const hasRecordOptions=state.files.some(file=>file.records.length>0);
  const currentRecordKey=selectedFile&&selected?`${selectedFile.id}::${selectedIndex(selectedFile)}`:"";
  const currentOption=selectedFile&&selected?{value:currentRecordKey,label:recordOptionLabel(selectedFile,selected,selectedIndex(selectedFile))}:null;
  const selectedPdfPages=selected?loadedPdfPagesForRecord(selected):[];
  const selectedRelated=Boolean(selectedFile&&selected&&selectedPdfPages.length);
  const pdfTitle=pdfDisplayTitle();
  const relatedWorks=[...new Set(allRelated.map(item=>String(item.record.work||"")).filter(Boolean))].sort((a,b)=>a.localeCompare(b));

  const pdfProvider=defaultProviderProfile();
  main.innerHTML=`<section class="card pdf-document-header">
    <input id="pdfInput" type="file" accept="application/pdf" hidden>
    <div class="pdf-document-primary">
      <button class="btn primary" id="openPdf">${icon("pdf")}${loaded?"Open another":"Open PDF"}</button>
      <div class="pdf-document-title">${loaded?`<span>PDF document</span><h2>${esc(pdfTitle)}</h2><p>${esc(state.pdf.name)}${state.pdf.author?` · ${esc(state.pdf.author)}`:""}${state.pdf.doc?` · ${state.pdf.doc.numPages} pages`:""}</p>`:`<span>PDF Explorer</span><h2>Open a source PDF</h2><p>Render pages, extract text, connect pages to records, and run LLM-assisted source workflows.</p>`}</div>
      ${loaded?`<div class="pdf-document-status"><span><b>${relatedWorks.length}</b> linked works</span><span><b>${allRelated.length}</b> linked records</span><span><b>${linked.length}</b> on this page</span></div>`:""}
    </div>
    ${loaded?`<div class="pdf-command-row">
      <div class="pdf-page-nav"><button class="btn small icon-only" id="pdfPrev" ${state.pdf.page<=1?"disabled":""}>←</button><label><span>Page</span><input class="control pdf-page-input" id="pdfPageInput" type="number" min="1" max="${state.pdf.doc?.numPages||999999}" value="${state.pdf.page}"></label><span class="pdf-page-total">/ ${state.pdf.doc?.numPages||"?"}</span><button class="btn small" id="pdfGo">Go</button><button class="btn small icon-only" id="pdfNext" ${state.pdf.doc&&state.pdf.page>=state.pdf.doc.numPages?"disabled":""}>→</button></div>
      <div class="pdf-command-divider"></div>
      <div class="pdf-view-actions"><button class="btn small icon-only" id="pdfRotateLeft" title="Rotate left 90°">↶</button><button class="btn small icon-only" id="pdfRotateRight" title="Rotate right 90°">↷</button><span class="note">${state.pdf.rotation?`${state.pdf.rotation}°`:"upright"}</span></div>
      <div class="pdf-command-divider"></div>
      <button class="btn small" id="extractPage" ${extractReady?"":"disabled"}>Extract page text</button>
      <details class="pdf-toolbar-menu"><summary class="btn small">More text tools</summary><div class="pdf-toolbar-menu-popover"><button class="btn small" id="extractAll" ${extractReady?"":"disabled"}>Extract all text</button></div></details>
      <details class="pdf-toolbar-menu llm-menu"><summary class="btn small soft">${icon("spark")}LLM tools</summary><div class="pdf-toolbar-menu-popover"><div class="pdf-menu-context"><b>${esc(providerDisplayName(pdfProvider))}</b><span>Each action lets you choose provider, model, parameters, and run mode.</span></div><button class="btn small" id="pdfLlmClean" ${extractReady?"":"disabled"}>Clean current page text</button><button class="btn small" id="pdfLlmDraft" ${extractReady?"":"disabled"}>Create draft record</button><button class="btn small" id="pdfLlmLink" ${state.files.length?"":"disabled"}>Match & link page to record</button><button class="btn small" id="pdfProviders">${icon("gear")}Manage LLM providers</button></div></details><button class="btn small primary" id="pdfCorpusBuilder">${icon("spark")}Build record set</button>
    </div>
    <div class="pdf-context-row"><div class="pdf-context-pill"><span>Source</span><b>p. ${state.pdf.page}</b></div><div class="pdf-context-pill"><span>Works</span><b>${esc(relatedWorks.slice(0,2).join(" · ")||"None linked")}${relatedWorks.length>2?` +${relatedWorks.length-2}`:""}</b></div><div class="pdf-context-pill"><span>Current-page records</span><b>${linked.length}</b></div>${selectedRelated?`<button class="btn soft" id="returnToSelectedRecord">${icon("record")}Back to ${esc(selected.record_id||"record")}</button>`:""}</div>`:""}
  </section>
  ${loaded?`<section class="pdfgrid pdfgrid-v2">
    <article class="card pdf-viewer-card">
      <div class="cardhead pdf-viewer-head"><div><b>Page ${state.pdf.page}</b><div class="note">${canRender?"PDF.js renderer":"Browser fallback"} · ${linked.length} linked record${linked.length===1?"":"s"} on this page</div></div><span class="pdf-view-badge">${state.pdf.rotation?`${state.pdf.rotation}° rotation`:"Fit width"}</span></div>
      ${canRender?`<div class="pdf-canvas-wrap"><canvas id="pdfCanvas"></canvas><div class="pdf-render-status" id="pdfRenderStatus"></div></div>`:`<iframe class="pdf-frame" id="pdfFrame" title="${esc(pdfTitle)}" src="${esc(state.pdf.url)}#page=${state.pdf.page}"></iframe>`}
    </article>

    <aside class="pdf-side-stack">
      <article class="card pdf-text-card">
        <div class="cardhead"><div><b>Page text</b><div class="note">${state.pdf.extractionSource?`Source: ${esc(state.pdf.extractionSource)}`:"Extract the current page, then optionally clean it with an LLM."}</div></div><div class="search"><input id="pdfSearch" value="${esc(state.pdf.search||"")}" placeholder="Search page text"></div></div>
        ${state.pdf.extractError?`<div class="info warn" style="margin:14px">${esc(state.pdf.extractError)}</div>`:""}
        <div class="pdftext">${highlight(state.pdf.text||"",state.pdf.search||"")||'<span class="note">Use “Extract current page” or “Extract all text.” If both PDF.js and PyMuPDF find no text, the page likely requires OCR.</span>'}</div>
      </article>

      <article class="card panel pdf-current-links">
        <div class="toolbar compact-toolbar"><div><b>Records on page ${state.pdf.page}</b><div class="note">${linked.length} linked record${linked.length===1?"":"s"}</div></div></div>
        <div class="pdf-link-controls">
          <div class="autocomplete"><input class="control" id="pdfRecordSearch" autocomplete="off" placeholder="Search record ID, work, or source file" value="${esc(currentOption?.label||"")}"><input type="hidden" id="pdfRecordKey" value="${esc(currentOption?.value||"")}"><div class="autocomplete-list hidden" id="pdfRecordSuggestions"></div></div>
          <button class="btn" id="linkCurrentPdf" ${hasRecordOptions?"":"disabled"}>${icon("plus")}Link page ${state.pdf.page}</button>
        </div>
        <div class="pdf-linked-list">${linked.map(({file,record,index})=>`<div class="linked-record-row">
          <button class="linked-record" data-linked-file="${file.id}" data-linked-index="${index}"><b>${esc(record.record_id||`Record ${index+1}`)}</b><span>${esc(record.work||file.name)} · ${esc(record.inline_citation||pages(record))}</span></button>
          <div class="tools"><button class="btn small" data-copy-row-key="${esc(reviewKey(file,index))}">${icon("copy")}Copy</button><button class="btn small" data-cite-row-key="${esc(reviewKey(file,index))}" data-cite-kind="inline" title="${esc(tr("ui.copy_inline","Copy inline citation"))}">Inline</button><button class="btn small" data-cite-row-key="${esc(reviewKey(file,index))}" data-cite-kind="full" title="${esc(tr("ui.copy_full","Copy full citation"))}">Full</button><button class="btn small ${evidenceIsSelected(workspaceEvidenceSelectionKey(file,index))?"soft":""}" data-toggle-workspace-evidence="${esc(reviewKey(file,index))}" title="${esc(evidenceIsSelected(workspaceEvidenceSelectionKey(file,index))?tr("ui.remove_evidence","Remove from evidence"):tr("ui.add_evidence","Add to evidence"))}">${evidenceIsSelected(workspaceEvidenceSelectionKey(file,index))?icon("check"):icon("plus")}Evidence</button><button class="btn small" data-linked-open-file="${file.id}" data-linked-open-index="${index}">${icon("record")}Open record</button><button class="btn small danger unlink-pdf-link" data-unlink-file="${file.id}" data-unlink-index="${index}" title="Unlink record from PDF">${icon("close")}Unlink</button></div>
        </div>`).join("")||'<div class="note">No records linked to this page yet.</div>'}</div>
      </article>

      <article class="card panel pdf-related-records">
        <div class="toolbar compact-toolbar"><div><b>Records linked anywhere in this PDF</b><div class="note">${allRelated.length} record${allRelated.length===1?"":"s"} · jump directly between source pages and records</div></div></div>
        <div class="search pdf-related-search"><input id="pdfRelatedSearch" value="${esc(state.pdf.relatedSearch||"")}" placeholder="Filter linked records"></div>
        <div class="pdf-related-list">${related.slice(0,80).map(({file,record,index,pages:recordPages})=>`<div class="pdf-related-row">
          <button class="pdf-related-record" data-related-record-file="${file.id}" data-related-record-index="${index}"><b>${esc(record.record_id||`Record ${index+1}`)}</b><span>${esc(record.work||file.name)}</span><small>${esc(fullCitation(record)||file.name)}</small></button>
          <div class="pdf-related-pages"><button class="copy-record-mini" data-copy-row-key="${esc(reviewKey(file,index))}" title="Copy entire record">${icon("copy")}</button><button class="copy-record-mini" data-cite-row-key="${esc(reviewKey(file,index))}" data-cite-kind="inline" title="${esc(tr("ui.copy_inline","Copy inline citation"))}">I</button><button class="copy-record-mini" data-cite-row-key="${esc(reviewKey(file,index))}" data-cite-kind="full" title="${esc(tr("ui.copy_full","Copy full citation"))}">F</button><button class="copy-record-mini ${evidenceIsSelected(workspaceEvidenceSelectionKey(file,index))?"selected":""}" data-toggle-workspace-evidence="${esc(reviewKey(file,index))}" title="${esc(evidenceIsSelected(workspaceEvidenceSelectionKey(file,index))?tr("ui.remove_evidence","Remove from evidence"):tr("ui.add_evidence","Add to evidence"))}">${evidenceIsSelected(workspaceEvidenceSelectionKey(file,index))?"✓":"+"}</button>${recordPages.map(page=>`<button class="pdf-page-chip ${Number(page)===Number(state.pdf.page)?"active":""}" data-related-page="${page}" title="Open PDF page ${page}">p. ${page}</button>`).join("")}</div>
        </div>`).join("")||'<div class="note">No linked records match this filter.</div>'}</div>
        ${related.length>80?`<div class="note" style="padding-top:8px">Showing first 80 of ${related.length} matches. Narrow the filter to see a specific record.</div>`:""}
      </article>
    </aside>
  </section>`:`<section class="empty"><div class="drop"><div class="drop-icon">${icon("pdf")}</div><h1>PDF Explorer</h1><p>Open a PDF to render pages, read its embedded title metadata, extract text, and move directly between linked PDF pages and corpus records.</p><button class="btn primary" id="openPdf2">${icon("pdf")}Choose PDF</button></div></section>`}`;

  document.querySelector("#openPdf").onclick=()=>document.querySelector("#pdfInput").click();
  document.querySelector("#openPdf2")?.addEventListener("click",()=>document.querySelector("#pdfInput").click());
  document.querySelector("#pdfInput").onchange=async e=>{
    const file=e.target.files[0];if(!file)return;
    const openButtons=[document.querySelector("#openPdf"),document.querySelector("#openPdf2")].filter(Boolean);
    const buttonState=openButtons.map(button=>({button,html:button.innerHTML}));
    for(const {button} of buttonState){button.disabled=true;button.innerHTML=`<span class="spinner small-spinner"></span>Opening PDF…`}
    try{
      if(state.pdf.url)URL.revokeObjectURL(state.pdf.url);
      const buffer=await file.arrayBuffer();
      state.pdf.file=file;
    state.pdf.url=URL.createObjectURL(new Blob([buffer],{type:"application/pdf"}));
    state.pdf.name=file.name;
    state.pdf.title=file.name.replace(/\.pdf$/i,"");
    state.pdf.author="";
    state.pdf.page=1;
    state.pdf.rotation=0;
    state.pdf.text="";
    state.pdf.search="";
    state.pdf.relatedSearch="";
    state.pdf.extractError="";
    state.pdf.extractionSource="";
    try{
      state.pdf.doc=await pdfjsLib.getDocument({data:new Uint8Array(buffer.slice(0))}).promise;
      const metadata=await loadPdfMetadata(state.pdf.doc,file.name);
      state.pdf.title=metadata.title||state.pdf.title;
      state.pdf.author=metadata.author||"";
    }catch(error){
      console.error("PDF.js initialization failed",error);
      state.pdf.doc=null;
      state.pdf.extractError=`PDF.js could not initialize (${error.message}). Rendering and extraction will use fallbacks where possible.`;
    }
      await persistCurrentPdfAsset();
      shell();
      renderView();
    }catch(error){
      console.error("Could not open PDF",error);
      await openMessageModal({title:"Could not open PDF",message:error.message||String(error),tone:"danger"});
      for(const {button,html} of buttonState){if(button.isConnected){button.disabled=false;button.innerHTML=html}}
    }
  };

  if(!loaded)return;

  if(canRender)renderPdfCanvas(state.pdf.page);

  const setPage=page=>{
    const max=state.pdf.doc?.numPages||Math.max(1,page);
    state.pdf.page=Math.max(1,Math.min(max,Number(page)||1));
    state.pdf.text="";
    state.pdf.extractError="";
    state.pdf.extractionSource="";
    persistCurrentPdfAsset();
    syncUrl({replace:true});
    renderPdf(main);
  };

  document.querySelector("#pdfRotateLeft")?.addEventListener("click",()=>{state.pdf.rotation=(Number(state.pdf.rotation||0)+270)%360;persistCurrentPdfAsset();renderPdf(main)});
  document.querySelector("#pdfRotateRight")?.addEventListener("click",()=>{state.pdf.rotation=(Number(state.pdf.rotation||0)+90)%360;persistCurrentPdfAsset();renderPdf(main)});
  document.querySelector("#pdfLlmClean")?.addEventListener("click",cleanPdfPageWithLlm);
  document.querySelector("#pdfLlmDraft")?.addEventListener("click",draftPdfPageWithLlm);
  document.querySelector("#pdfLlmLink")?.addEventListener("click",linkPdfPageWithLlm);
  document.querySelector("#pdfProviders")?.addEventListener("click",()=>navigateTo("providers"));
  document.querySelector("#pdfCorpusBuilder")?.addEventListener("click",()=>window.dispatchEvent(new CustomEvent("derridai:pdf-builder")));
  document.querySelector("#pdfPrev")?.addEventListener("click",()=>setPage(state.pdf.page-1));
  document.querySelector("#pdfNext")?.addEventListener("click",()=>setPage(state.pdf.page+1));
  document.querySelector("#pdfGo")?.addEventListener("click",()=>setPage(document.querySelector("#pdfPageInput").value));
  document.querySelector("#pdfPageInput")?.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();setPage(e.target.value)}});
  document.querySelector("#returnToSelectedRecord")?.addEventListener("click",()=>navigateTo("record",{fileId:selectedFile.id,index:selectedIndex(selectedFile)}));

  document.querySelector("#extractPage")?.addEventListener("click",async()=>{
    const pageToExtract=Number(document.querySelector("#pdfPageInput")?.value||state.pdf.page);
    state.pdf.page=Math.max(1,Math.min(state.pdf.doc?.numPages||pageToExtract,pageToExtract));
    const button=document.querySelector("#extractPage");button.disabled=true;button.textContent=`Extracting page ${state.pdf.page}…`;
    try{
      const result=await extractPdfPageSmart(state.pdf.page);
      state.pdf.text=result.text;state.pdf.extractionSource=result.source;state.pdf.extractError=result.warning||"";
    }catch(error){state.pdf.extractError=error.message}
    renderPdf(main);
  });
  document.querySelector("#extractAll")?.addEventListener("click",async()=>{
    const button=document.querySelector("#extractAll");button.disabled=true;button.textContent="Extracting…";
    try{
      const result=await extractPdfAllSmart();
      state.pdf.text=result.text;state.pdf.extractionSource=result.source;state.pdf.extractError=result.warning||"";
    }catch(error){state.pdf.extractError=error.message}
    renderPdf(main);
  });

  const s=document.querySelector("#pdfSearch");
  if(s)s.oninput=e=>{const pos=e.target.selectionStart;state.pdf.search=e.target.value;renderPdf(main);requestAnimationFrame(()=>{const x=document.querySelector("#pdfSearch");if(x){x.focus();x.setSelectionRange(pos,pos)}})};

  const relatedSearch=document.querySelector("#pdfRelatedSearch");
  if(relatedSearch)relatedSearch.oninput=e=>{
    const pos=e.target.selectionStart;
    state.pdf.relatedSearch=e.target.value;
    renderPdf(main);
    requestAnimationFrame(()=>{
      const next=document.querySelector("#pdfRelatedSearch");
      if(next){next.focus();next.setSelectionRange(pos,pos)}
    });
  };

  const search=document.querySelector("#pdfRecordSearch");
  const hidden=document.querySelector("#pdfRecordKey");
  const suggestions=document.querySelector("#pdfRecordSuggestions");
  const renderSuggestions=()=>{
    const q=search.value.trim();
    const matches=searchRecordOptions(q,12);
    suggestions.innerHTML=matches.map(option=>`<button type="button" class="autocomplete-option" data-record-key="${esc(option.value)}"><b>${esc(option.label.split(" · ")[1]||option.label)}</b><span>${esc(option.label)}</span></button>`).join("")||'<div class="autocomplete-empty">No matching records</div>';
    suggestions.classList.remove("hidden");
    suggestions.querySelectorAll("[data-record-key]").forEach(button=>button.onclick=()=>{
      const option=recordOptionForKey(button.dataset.recordKey);
      if(option){hidden.value=option.value;search.value=option.label}
      suggestions.classList.add("hidden");
    });
  };
  search?.addEventListener("focus",renderSuggestions);
  search?.addEventListener("input",()=>{hidden.value="";renderSuggestions()});
  search?.addEventListener("keydown",e=>{if(e.key==="Escape")suggestions.classList.add("hidden")});
  document.addEventListener("click",e=>{if(!e.target.closest(".autocomplete"))suggestions?.classList.add("hidden")},{once:true});

  document.querySelector("#linkCurrentPdf")?.addEventListener("click",()=>{
    let key=hidden.value;
    if(!key){
      const exact=searchRecordOptions(search.value,24).find(option=>option.label===search.value);
      key=exact?.value||"";
    }
    const item=lookupRecord(key);
    if(item)linkPdfPage(item.file,item.index,state.pdf.page);
    else toast("Choose a record from the autocomplete list");
  });

  document.querySelectorAll("[data-linked-file],[data-linked-open-file]").forEach(button=>button.onclick=()=>{
    const fileId=button.dataset.linkedFile||button.dataset.linkedOpenFile;
    const index=+(button.dataset.linkedIndex??button.dataset.linkedOpenIndex);
    navigateTo("record",{fileId,index});
  });
  document.querySelectorAll("[data-unlink-file]").forEach(button=>button.onclick=()=>{
    const file=state.files.find(item=>item.id===button.dataset.unlinkFile);
    if(file)unlinkPdfLink(file,+button.dataset.unlinkIndex,{pdf_file:state.pdf.name,pdf_page:state.pdf.page},{stayInPdf:true});
  });
  document.querySelectorAll("[data-related-record-file]").forEach(button=>button.onclick=()=>{
    navigateTo("record",{fileId:button.dataset.relatedRecordFile,index:+button.dataset.relatedRecordIndex});
  });
  document.querySelectorAll("[data-related-page]").forEach(button=>button.onclick=()=>setPage(+button.dataset.relatedPage));
}

async function renderPdfCanvas(pageNumber){
  const canvas=document.querySelector("#pdfCanvas");
  if(!canvas||!state.pdf.doc)return;
  const status=document.querySelector("#pdfRenderStatus");
  try{
    if(status)status.textContent=`Rendering page ${pageNumber}…`;
    const page=await state.pdf.doc.getPage(pageNumber);
    const rotation=Number(state.pdf.rotation||0)%360;
    const base=page.getViewport({scale:1,rotation});
    const container=canvas.parentElement;
    const maxWidth=Math.max(420,(container?.clientWidth||900)-32);
    // PDF tools now live below the viewer, so the document can use its natural
    // fit-width scale without reserving horizontal room for a side column.
    const scale=Math.min(2.1,Math.max(.5,maxWidth/base.width));
    const viewport=page.getViewport({scale,rotation});
    const dpr=Math.min(window.devicePixelRatio||1,2);
    canvas.width=Math.floor(viewport.width*dpr);
    canvas.height=Math.floor(viewport.height*dpr);
    canvas.style.width=`${viewport.width}px`;
    canvas.style.height=`${viewport.height}px`;
    const context=canvas.getContext("2d");
    context.setTransform(dpr,0,0,dpr,0,0);
    await page.render({canvasContext:context,viewport}).promise;
    if(status)status.textContent="";
  }catch(error){
    console.error("PDF render failed",error);
    if(status)status.textContent=`Could not render page ${pageNumber}: ${error.message}`;
  }
}
async function extractPdfPageBrowser(p){
  if(!state.pdf.doc)throw new Error("PDF.js is unavailable for this document.");
  const page=await state.pdf.doc.getPage(p);
  const content=await page.getTextContent({includeMarkedContent:true});
  let text="";
  for(const item of content.items){
    if(!item||typeof item.str!=="string")continue;
    text+=item.str;
    text+=item.hasEOL?"\n":" ";
  }
  return text.replace(/[ \t]+\n/g,"\n").replace(/ {2,}/g," ").trim();
}
async function extractPdfApi(page=null){
  if(!state.pdf.file)throw new Error("The PDF file is no longer available in this browser session.");
  const form=new FormData();
  form.append("file",state.pdf.file,state.pdf.name||"document.pdf");
  const url=page?`/api/pdf/extract?page=${page}`:"/api/pdf/extract";
  let response;
  try{response=await fetch(url,{method:"POST",body:form})}catch(error){throw new Error(`PDF extraction API is unreachable: ${error.message}`)}
  const payload=await response.json().catch(()=>({detail:`HTTP ${response.status}`}));
  if(!response.ok)throw new Error(typeof payload.detail==="string"?payload.detail:`PDF extraction failed with HTTP ${response.status}`);
  return payload;
}
async function extractPdfPageSmart(p){
  let browserError="";
  if(state.pdf.doc){
    try{
      const text=await extractPdfPageBrowser(p);
      if(text.trim())return {text,source:`PDF.js (browser), page ${p}`,warning:""};
    }catch(error){browserError=error.message}
  }
  const payload=await extractPdfApi(p);
  const text=payload.pages?.[0]?.text||"";
  if(text.trim())return {text,source:`PyMuPDF (API fallback), page ${p}`,warning:browserError?`PDF.js failed: ${browserError}`:""};
  return {text:"",source:"No extractable text layer",warning:`Neither PDF.js nor PyMuPDF found extractable text on page ${p}. It likely requires OCR.`};
}
async function extractPdfAllSmart(){
  let browserError="";
  if(state.pdf.doc){
    try{
      const parts=[];let nonempty=0;
      for(let p=1;p<=state.pdf.doc.numPages;p++){
        const text=await extractPdfPageBrowser(p);
        if(text.trim())nonempty++;
        parts.push(`--- Page ${p} ---\n${text}`);
      }
      if(nonempty)return {text:parts.join("\n\n"),source:"PDF.js (browser), all pages",warning:""};
    }catch(error){browserError=error.message}
  }
  const payload=await extractPdfApi();
  const parts=(payload.pages||[]).map(item=>`--- Page ${item.page} ---\n${item.text||""}`);
  if(payload.has_text)return {text:parts.join("\n\n"),source:"PyMuPDF (API fallback), all pages",warning:browserError?`PDF.js failed: ${browserError}`:""};
  return {text:parts.join("\n\n"),source:"No extractable text layer",warning:"Neither PDF.js nor PyMuPDF found extractable text. Image-only pages require OCR."};
}
function recordOptionLabel(file,record,index){
  return `${file.name} · ${record.record_id||index+1} · ${record.work||""}`;
}
function recordOptionForKey(key){
  const item=lookupRecord(key);
  if(!item)return null;
  return {value:key,label:recordOptionLabel(item.file,item.record,item.index)};
}
function compareSearchIndex(){
  return memoCorpus("compare-search-index",()=>allRows().map(({file,record,index})=>{
    const labelText=recordOptionLabel(file,record,index);
    return {
      value:`${file.id}::${index}`,
      label:labelText,
      search:`${labelText} ${record.document_author||""}`.toLocaleLowerCase(),
    };
  }));
}
function searchRecordOptions(query,limit=18){
  const terms=String(query||"").trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const matches=[];
  for(const option of compareSearchIndex()){
    if(terms.length&&!terms.every(term=>option.search.includes(term)))continue;
    matches.push({value:option.value,label:option.label});
    if(matches.length>=limit)break;
  }
  return matches;
}
function lookupRecord(key){
  if(!key)return null;const [fid,i]=key.split("::");const f=state.files.find(x=>x.id===fid);return f?{file:f,index:+i,record:f.records[+i]}:null;
}
function getCompareLibrary(){
  if(isResearcher()){
    return researcherDbRecords().map(record=>{
      const id=String(record._chroma_id||record.record_id||"");
      const label=`${record.record_id||id} · ${record.work||""}`;
      return {value:id,label,search:`${label} ${record.document_author||""}`.toLocaleLowerCase()};
    });
  }
  return compareSearchIndex();
}
function getCompareRecord(key){
  if(!key)return null;
  if(isResearcher()){
    const record=researcherDbRecords().find(item=>String(item._chroma_id||item.record_id||"")===String(key));
    if(!record)return null;
    const copy={...record};
    delete copy._chroma_id;
    delete copy._researcher_text_policy;
    return {record:copy,label:`${record.record_id||key} · ${record.work||""}`};
  }
  const item=lookupRecord(key);
  if(!item?.record)return null;
  return {record:item.record,label:recordOptionLabel(item.file,item.record,item.index)};
}
async function ensureCompareLibrary(){
  if(!isResearcher())return getCompareLibrary();
  if(!state.activeStore){
    try{await refreshStores()}catch{ /* stores may be unavailable */ }
  }
  if(!state.storeRecords.length&&state.activeStore){
    state.storePageSize=Math.max(Number(state.storePageSize||50),100);
    try{await loadStorePage()}catch{ /* page load is best-effort for Compare */ }
  }
  return getCompareLibrary();
}
function parsePastedRecord(value){
  let text=String(value||"").trim();
  if(!text)return null;
  text=text.replace(/^```(?:json|jsonl)?\s*/i,"").replace(/\s*```$/,"").trim();
  try{
    const parsed=JSON.parse(text);
    if(Array.isArray(parsed)){
      if(parsed.length!==1||!parsed[0]||typeof parsed[0]!=="object"||Array.isArray(parsed[0])){
        throw new Error("Paste exactly one JSON record, not an array of multiple records.");
      }
      return parsed[0];
    }
    if(!parsed||typeof parsed!=="object")throw new Error("Pasted value is not a JSON object.");
    return parsed;
  }catch(error){
    const lines=text.split(/\r?\n/).map(line=>line.trim()).filter(Boolean);
    const parsedLines=[];
    for(const line of lines){
      try{parsedLines.push(JSON.parse(line))}catch{throw error}
    }
    if(parsedLines.length!==1||!parsedLines[0]||typeof parsedLines[0]!=="object"||Array.isArray(parsedLines[0])){
      throw new Error("Paste exactly one JSON/JSONL record on each side.");
    }
    return parsedLines[0];
  }
}
function compareRecordTable(a,b,{titleA="Record A",titleB="Record B",rowKeyA="",rowKeyB=""}={}){
  if(!a||!b)return '<div class="empty mini"><p>Select or paste two records to compare them.</p></div>';
  const keys=[...new Set([...Object.keys(a),...Object.keys(b)])].filter(key=>key!=="updates").sort((x,y)=>{
    const priority=["record_id","work","document_author","edition","year","page_start","page_end","speaker","position_holder","stance","target","discourse_role","proposition_status","text"];
    const ax=priority.indexOf(x),ay=priority.indexOf(y);
    if(ax>=0||ay>=0)return (ax<0?999:ax)-(ay<0?999:ay);
    return x.localeCompare(y);
  });
  const changed=keys.filter(key=>!sameValue(a[key],b[key]));
  const unchanged=keys.filter(key=>sameValue(a[key],b[key]));
  const summary=(record,title,side,rowKey)=>{const evidenceItem=rowKey?reviewItemFromKey(rowKey):null;const evidenceKey=evidenceItem?workspaceEvidenceKey(evidenceItem.file,evidenceItem.index):"";const selected=evidenceKey&&evidenceIsSelected(evidenceKey);return `<article class="compare-record-summary compare-${side.toLowerCase()}"><span>${esc(title)}</span><b>${esc(record.work||record.record_id||"Untitled record")}</b><small>${esc(record.document_author||"Unknown author")} · ${esc(pages(record))}</small><div class="record-row-actions"><button class="btn tiny" data-copy-compare="${side.toLowerCase()}">${icon("copy")}Copy JSON</button><button class="btn tiny" data-cite-compare="${side.toLowerCase()}" data-cite-kind="inline">Inline</button><button class="btn tiny" data-cite-compare="${side.toLowerCase()}" data-cite-kind="full">Full</button>${rowKey?`<button class="btn tiny ${selected?"soft":""}" data-toggle-workspace-evidence="${esc(rowKey)}" title="${esc(selected?tr("ui.remove_evidence","Remove from evidence"):tr("ui.add_evidence","Add to evidence"))}">${selected?"✓ Evidence":"+ Evidence"}</button>`:""}</div></article>`};
  const changedHtml=changed.map(key=>{
    const diff=reviewDiffSides(a[key],b[key]);
    return `<article class="compare-diff-card ${key==="text"?"compare-text-diff":""}"><div class="compare-diff-head"><div><b>${esc(label(key))}</b><code>${esc(key)}</code></div><span>Changed</span></div><div class="compare-diff-sides"><section><div class="compare-side-label">A · ${esc(titleA)}</div><pre class="change-diff current-diff">${diff.left}</pre></section><section><div class="compare-side-label">B · ${esc(titleB)}</div><pre class="change-diff proposed-diff">${diff.right}</pre></section></div></article>`;
  }).join("");
  const unchangedHtml=unchanged.map(key=>`<div class="compare-unchanged-row"><b>${esc(label(key))}</b><code>${esc(key)}</code><span>${esc(display(a[key]))}</span></div>`).join("");
  return `<section class="compare-modern-results">
    <div class="compare-record-pair">${summary(a,titleA,"A",rowKeyA)}${summary(b,titleB,"B",rowKeyB)}</div>
    <div class="compare-result-summary"><div><strong>${changed.length}</strong><span>fields changed</span></div><div><strong>${unchanged.length}</strong><span>identical fields</span></div><div><strong>${keys.length}</strong><span>fields compared</span></div></div>
    <section class="compare-changes-section"><div class="compare-section-title"><div><b>Differences</b><span>Only changed fields are expanded by default.</span></div></div>${changedHtml||'<div class="card panel">These records are identical across all compared fields.</div>'}</section>
    ${unchanged.length?`<details class="card compare-unchanged"><summary>${unchanged.length} identical fields</summary><div class="compare-unchanged-list">${unchangedHtml}</div></details>`:""}
  </section>`;
}
function comparePickerHtml(side,selectedKey){
  const selected=recordOptionForKey(selectedKey);
  return `<div class="compare-picker" data-compare-picker="${side}"><div class="field"><label>Record ${side}</label><div class="compare-autocomplete-shell"><input class="control compare-autocomplete" id="compare${side}Search" value="${esc(selected?.label||"")}" placeholder="Type record ID, work, author, or file…" autocomplete="off" aria-autocomplete="list" aria-controls="compare${side}Results"><button class="btn tiny compare-picker-clear" type="button" data-clear-compare="${side}" ${selected?"":`disabled data-disabled-reason="No record is selected."`}>Clear</button><div class="compare-autocomplete-results" id="compare${side}Results" role="listbox" hidden></div></div>${selected?`<div class="compare-selected-hint">Selected · ${esc(selected.label)}</div>`:'<div class="compare-selected-hint">Start typing to search loaded records.</div>'}</div></div>`;
}
function wireComparePicker(side,main){
  const input=main.querySelector(`#compare${side}Search`),results=main.querySelector(`#compare${side}Results`);
  if(!input||!results)return;
  const stateKey=side==="A"?"compareA":"compareB";
  let timer=null,activeIndex=-1,lastMatches=[];
  const selectOption=value=>{
    if(!value)return;
    state[stateKey]=value;
    persistPrefs();
    renderCompare(main);
  };
  const markActive=()=>{
    const buttons=[...results.querySelectorAll("[data-compare-option]")];
    buttons.forEach((button,index)=>button.classList.toggle("active",index===activeIndex));
    buttons[activeIndex]?.scrollIntoView({block:"nearest"});
  };
  const show=()=>{
    const current=recordOptionForKey(state[stateKey]);
    lastMatches=searchRecordOptions(input.value,18);
    activeIndex=-1;
    results.innerHTML=lastMatches.map(option=>`<button type="button" role="option" data-compare-option="${esc(option.value)}"><b>${esc(option.label.split(" · ")[1]||option.label)}</b><span>${esc(option.label)}</span></button>`).join("")||'<div class="compare-no-results">No matching records.</div>';
    results.hidden=false;
    if(current&&input.value===current.label&&lastMatches.length===1&&lastMatches[0].value===current.value)results.hidden=true;
  };
  results.addEventListener("pointerdown",event=>{
    const button=event.target.closest("[data-compare-option]");
    if(!button)return;
    event.preventDefault();
    selectOption(button.dataset.compareOption);
  });
  input.addEventListener("focus",show);
  input.addEventListener("input",()=>{
    const current=recordOptionForKey(state[stateKey]);
    if(current&&input.value!==current.label)state[stateKey]="";
    clearTimeout(timer);timer=setTimeout(show,70);
  });
  input.addEventListener("keydown",event=>{
    if(event.key==="Escape"){results.hidden=true;return}
    if(event.key==="ArrowDown"||event.key==="ArrowUp"){
      if(results.hidden)show();
      const count=lastMatches.length;if(!count)return;
      event.preventDefault();
      activeIndex=event.key==="ArrowDown"?(activeIndex+1)%count:(activeIndex<=0?count-1:activeIndex-1);
      markActive();
      return;
    }
    if(event.key==="Enter"&&!results.hidden&&lastMatches.length){
      event.preventDefault();
      selectOption(lastMatches[Math.max(0,activeIndex)]?.value);
    }
  });
  input.addEventListener("blur",()=>setTimeout(()=>{results.hidden=true},150));
  main.querySelector(`[data-clear-compare="${side}"]`)?.addEventListener("click",()=>{state[stateKey]="";persistPrefs();renderCompare(main)});
}
function renderCompare(main){
  if(isResearcher())return renderResearcherCompare(main);
  const mode=state.compareMode||"workspace";
  if(mode==="workspace"){
    if(state.compareA&&!lookupRecord(state.compareA))state.compareA="";
    if(state.compareB&&!lookupRecord(state.compareB))state.compareB="";
  }
  const a=mode==="workspace"?lookupRecord(state.compareA):null;
  const b=mode==="workspace"?lookupRecord(state.compareB):null;
  let parsedA=null,parsedB=null,errorA="",errorB="";
  if(mode==="paste"){
    try{parsedA=parsePastedRecord(state.comparePasteA)}catch(error){errorA=error.message}
    try{parsedB=parsePastedRecord(state.comparePasteB)}catch(error){errorB=error.message}
  }

  main.innerHTML=`<div class="compare-page"><section class="card compare-intro-card"><div><span class="section-label">${esc(tr("section.tools","Tools"))}</span><h1>${esc(tr("nav.compare","Compare"))}</h1><p>${esc(tr("compare.page_help","Compare record metadata and text with focused, side-by-side field differences."))}</p></div><div class="compare-intro-actions"><div class="view-tabs"><button class="view-tab ${mode==="workspace"?"active":""}" data-compare-mode="workspace">${esc(tr("compare.workspace_records","Workspace records"))}</button><button class="view-tab ${mode==="paste"?"active":""}" data-compare-mode="paste">${esc(tr("compare.paste_records","Paste records"))}</button></div>${mode==="paste"?`<button class="btn small" id="clearPastedCompare">${esc(tr("compare.clear_pasted","Clear pasted records"))}</button>`:""}</div></section>
  ${mode==="workspace"?`<section class="card compare-picker-card"><div class="compare-selectors">${comparePickerHtml("A",state.compareA)}${comparePickerHtml("B",state.compareB)}</div></section>
  ${a&&b?compareRecordTable(a.record,b.record,{titleA:a.record.record_id||"Record A",titleB:b.record.record_id||"Record B",rowKeyA:reviewKey(a.file,a.index),rowKeyB:reviewKey(b.file,b.index)}):'<div class="compare-empty-state"><b>Select two records</b><span>Autocomplete searches record IDs, works, authors, and source files without rendering an enormous select menu.</span></div>'}`
  :`<section class="compare-paste-grid">
      <div class="field"><label>Record A JSON / JSONL</label><textarea id="comparePasteA" class="compare-paste-input" spellcheck="false" placeholder='{"record_id":"...","work":"...", ...}'>${esc(state.comparePasteA||"")}</textarea>${errorA?`<div class="info error">${esc(errorA)}</div>`:""}</div>
      <div class="field"><label>Record B JSON / JSONL</label><textarea id="comparePasteB" class="compare-paste-input" spellcheck="false" placeholder='{"record_id":"...","work":"...", ...}'>${esc(state.comparePasteB||"")}</textarea>${errorB?`<div class="info error">${esc(errorB)}</div>`:""}</div>
    </section>
    <div class="compare-format-note"><span>${icon("info")}</span><div><b>${esc(tr("compare.paste_guidance_title","Paste one record on each side"))}</b><span>${esc(tr("compare.paste_guidance_help","JSON objects and one-line JSONL records are supported. DerridAI compares parsed fields after both sides are valid."))}</span></div></div>${parsedA&&parsedB?compareRecordTable(parsedA,parsedB,{titleA:parsedA.record_id||"Pasted A",titleB:parsedB.record_id||"Pasted B"}):''}`}</div>`;

  document.querySelectorAll("[data-compare-mode]").forEach(button=>button.onclick=()=>{state.compareMode=button.dataset.compareMode;persistPrefs();renderCompare(main)});
  if(mode==="workspace"){wireComparePicker("A",main);wireComparePicker("B",main)}
  let pasteTimer=null;
  const updatePaste=()=>{
    state.comparePasteA=document.querySelector("#comparePasteA")?.value||"";
    state.comparePasteB=document.querySelector("#comparePasteB")?.value||"";
    persistPrefs();clearTimeout(pasteTimer);pasteTimer=setTimeout(()=>renderCompare(main),280);
  };
  document.querySelector("#comparePasteA")?.addEventListener("input",updatePaste);
  document.querySelector("#comparePasteB")?.addEventListener("input",updatePaste);
  document.querySelector("#clearPastedCompare")?.addEventListener("click",()=>{state.comparePasteA="";state.comparePasteB="";persistPrefs();renderCompare(main)});
  const comparedA=mode==="workspace"?a?.record:parsedA,comparedB=mode==="workspace"?b?.record:parsedB;
  document.querySelectorAll("[data-copy-compare]").forEach(button=>button.onclick=()=>{const record=button.dataset.copyCompare==="a"?comparedA:comparedB;if(record)copyJsonToClipboard(record,record.record_id||`Record ${button.dataset.copyCompare.toUpperCase()}`)});
  document.querySelectorAll("[data-cite-compare]").forEach(button=>button.onclick=()=>{const record=button.dataset.citeCompare==="a"?comparedA:comparedB;if(record)copyCitation(record,button.dataset.citeKind||"inline")});
  decorateDisabledControls(main);
}

const HTTP_ERROR_STORAGE_KEY="derridai.httpErrors.v1";
function fullHttpErrorDetail(payload,text,statusText=""){
  const detail=payload?.detail;
  if(typeof detail==="string"&&detail.trim())return detail.trim();
  if(Array.isArray(detail)){
    const value=detail.map(item=>{
      if(item&&typeof item==="object"){
        const location=Array.isArray(item.loc)?item.loc.join("."):"";
        const message=item.msg||item.message||JSON.stringify(item);
        return location?`${location}: ${message}`:String(message);
      }
      return String(item);
    }).filter(Boolean).join("; ");
    if(value)return value;
  }
  if(detail&&typeof detail==="object"){
    const message=detail.message||detail.error||detail.detail;
    if(message)return String(message);
    // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
    try{return JSON.stringify(detail)}catch{}
  }
  if(text&&String(text).trim())return String(text).trim();
  return String(statusText||"Request failed");
}
function storeHttpError(entry){
  try{
    const current=JSON.parse(localStorage.getItem(HTTP_ERROR_STORAGE_KEY)||"[]");
    const rows=Array.isArray(current)?current:[];
    rows.unshift(entry);
    localStorage.setItem(HTTP_ERROR_STORAGE_KEY,JSON.stringify(rows.slice(0,50)));
  // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  }catch{}
}
async function api(path,options={}){
  const method=String(options.method||"GET").toUpperCase();
  let response;
  try{
    response=await fetch(path,{headers:{"Content-Type":"application/json",...(options.headers||{})},...options});
  }catch(error){
    const diagnostic=String(error?.message||error);
    const wrapped=new Error(`Network error · ${diagnostic}`);
    wrapped.diagnostic=diagnostic;
    wrapped.status=0;
    wrapped.fullMessage=wrapped.message;
    wrapped.requestPath=String(path);
    storeHttpError({timestamp:new Date().toISOString(),method,path:String(path),status:0,statusText:"Network error",message:wrapped.message,diagnostic,responseBody:""});
    throw wrapped;
  }
  if(response.status===401&&!String(path).startsWith("/api/auth/"))window.dispatchEvent(new CustomEvent("derridai-auth-expired"));
  const text=await response.text();
  let payload={};
  try{payload=text?JSON.parse(text):{}}catch{payload={detail:text}}
  if(!response.ok){
    const detail=fullHttpErrorDetail(payload,text,response.statusText);
    const diagnostic=typeof payload?.detail==="object"&&!Array.isArray(payload.detail)?String(payload.detail?.diagnostic||""):"";
    const message=`HTTP ${response.status}${response.statusText?` ${response.statusText}`:""} · ${detail}`;
    const error=new Error(message);
    error.status=response.status;
    error.statusText=response.statusText;
    error.diagnostic=diagnostic;
    error.payload=payload;
    error.responseBody=text;
    error.requestPath=String(path);
    error.requestMethod=method;
    error.fullMessage=message;
    storeHttpError({timestamp:new Date().toISOString(),method,path:String(path),status:response.status,statusText:response.statusText||"",message,diagnostic,responseBody:text});
    throw error;
  }
  return payload;
}
async function refreshStores(){
  const data=await api("/api/stores");
  state.stores=data.stores||[];
  state.storesLastFetchedAt=Date.now();
  const corpus=recordStores();
  if(state.activeStore&&!corpus.some(store=>store.name===state.activeStore))state.activeStore="";
  if(!state.activeStore&&corpus.length)state.activeStore=corpus[0].name;
  return state.stores;
}
async function refreshStoreWorks(force=false){
  if(!state.activeStore){
    state.storeWorks=[];
    state.storeWorkStats=[];
    state.storeWorksStore="";
    state.storeWork="";
    return;
  }
  if(!force&&state.storeWorksStore===state.activeStore)return;
  const data=await api(`/api/stores/${encodeURIComponent(state.activeStore)}/works`);
  state.storeWorks=data.works||[];
  state.storeWorkStats=data.stats||state.storeWorks.map(work=>({work,count:null}));
  state.storeWorksStore=state.activeStore;
  if(state.storeWork&&!state.storeWorks.includes(state.storeWork))state.storeWork="";
}
async function loadStorePage(){
  if(!state.activeStore){state.storeRecords=[];state.storeCount=0;return}
  const offset=Math.max(0,(state.storePage-1)*state.storePageSize);
  const params=new URLSearchParams({limit:String(state.storePageSize),offset:String(offset)});
  if(state.storeWork)params.set("work",state.storeWork);
  if(state.storeSort?.key){
    params.set("sort_field",state.storeSort.key);
    params.set("sort_dir",state.storeSort.dir===-1?"desc":"asc");
  }
  const activeFilters=Object.fromEntries(Object.entries(state.storeFilters||{}).filter(([,value])=>String(value||"").trim()));
  if(Object.keys(activeFilters).length)params.set("filters",JSON.stringify(activeFilters));
  const data=await api(`/api/stores/${encodeURIComponent(state.activeStore)}/records?${params}`);
  state.storeRecords=data.records||[];
  state.storeCount=data.count||0;
  const maxPage=Math.max(1,Math.ceil(state.storeCount/state.storePageSize));
  if(state.storePage>maxPage){state.storePage=maxPage;return loadStorePage()}
}
function deriveNames(source){
  const base=source||"chroma_primary";
  return {
    en:`${base}_en`,
    fr:`${base}_fr`,
  };
}
function languageTagHtml(codes=[]){
  const order=["en","fr"];
  return order.filter(code=>codes.includes(code)).map(code=>`<span class="lang-tag">${code}</span>`).join("")||'<span class="lang-tag muted">untagged</span>';
}
async function exportStoreJsonl({store=state.activeStore,work=null,downloadFile=false,loadTab=false}={}){
  if(!store)return toast("Select a Chroma collection first");
  const params=new URLSearchParams();
  if(work)params.set("work",work);
  const op=showOperationProgress(`Exporting ${store}`,1);
  try{
    updateOperationProgress(op,0,1,work?`Reading work: ${work}`:"Reading complete collection…");
    const payload=await api(`/api/stores/${encodeURIComponent(store)}/export${params.toString()?`?${params}`:""}`);
    const records=payload.records||[];
    const suffix=work?`-${String(work).replace(/[^a-z0-9]+/gi,"-").replace(/^-|-$/g,"")}`:"";
    const name=`${store}${suffix}.jsonl`;
    const jsonl=records.map(record=>JSON.stringify(record)).join("\n")+(records.length?"\n":"");
    if(downloadFile)download(name,jsonl);
    if(loadTab){
      const file={
        id:uid(),
        name,
        records:records.map(record=>cloneAuditValue(record)),
        errors:[],
        dirty:new Set(),
        imported_at:new Date().toISOString(),
        imported_from_chroma:store,
      };
      state.files.push(file);
      await persistFileNow(file);
      state.activeFileId=file.id;
      persistPrefs();
      navigateTo("list",{fileId:file.id});
    }
    updateOperationProgress(op,1,1,`${records.length.toLocaleString()} records exported`);
    setTimeout(()=>hideOperationProgress(op),600);
    if(!loadTab)toast(`Exported ${records.length.toLocaleString()} records from ${store}`);
    return records;
  }catch(error){
    updateOperationProgress(op,0,1,`Failed: ${error.message}`);
    setTimeout(()=>hideOperationProgress(op),1800);
    toast(`Chroma export failed: ${error.message}`);
    return null;
  }
}
function persistVectorLocation(){
  persistPrefs();
  syncUrl({replace:true});
}
function openStoreRecordEditor(record){
  const chromaId=record._chroma_id;
  if(!chromaId)return toast(tr("record.no_storage_id","This Chroma record has no storage ID"));
  const dialog=document.createElement("dialog");
  const editable=Object.keys(record).filter(k=>k!=="_chroma_id"&&k!=="updates"&&k!=="_updates_count"&&!k.startsWith("_researcher_"));
  dialog.innerHTML=`<form><div class="dh"><div><h2 class="dialog-title">Edit Chroma record</h2><div class="dialog-subtitle">${esc(chromaId)} · ${esc(state.activeStore)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body"><div class="info">Saving updates this record in place under the same Chroma ID and regenerates its embedding when the configured embedding provider allows it.</div><section class="editor-section"><h3>Record</h3><div class="editor-grid">${editable.map(k=>fieldEditor(k,record[k])).join("")}</div></section></div><div class="da"><button class="btn" type="button" data-close>Cancel</button><button class="btn primary">${icon("check")}Save to Chroma</button></div></form>`;
  document.body.appendChild(dialog);showAppModal(dialog);
  const close=()=>{dialog.close();dialog.remove()};
  dialog.querySelectorAll("[data-close]").forEach(b=>b.onclick=close);
  dialog.querySelector("form").onsubmit=async e=>{
    e.preventDefault();
    const raw={...record};delete raw._chroma_id;
    const changes={};
    try{
      dialog.querySelectorAll("[data-key]").forEach(el=>{
        const value=parseEditor(el);
        if(!sameValue(raw[el.dataset.key],value))changes[el.dataset.key]=value;
      });
    }catch(error){openMessageModal({title:"Could not parse edited record",message:error.message,tone:"danger"});return}
    if(!Object.keys(changes).length)return close();
    const timestamp=new Date().toISOString(),batchId=uid();
    const auditEntries=Object.entries(changes).map(([field,newValue])=>({
      field_name:field,old_value:cloneAuditValue(raw[field]),new_value:cloneAuditValue(newValue),timestamp,
      source:"chroma_manual",batch_id:batchId,initiated_by:state.userContext?.username||null,
    }));
    try{
      await api(`/api/stores/${encodeURIComponent(state.activeStore)}/records/${encodeURIComponent(chromaId)}`,{
        method:"PATCH",body:JSON.stringify({changes,audit_entries:auditEntries,document_field:"text",embedding_field:"embedding"}),
      });
      state.storeWorksStore="";
      close();toast("Chroma record updated",{tone:"success"});renderView();
    }catch(error){toast(`Chroma update failed: ${error.message}`,{tone:"danger"})}
  };
}
const vectorCollectionBridge=createVectorCollectionBridge({
  state,workIndex,recordStores,tr,trf,esc,icon,api,refreshStores,persistPrefs,
  upsertRows,toast,openMessageModal,decorateDisabledControls,showAppModal,
});
function notifyVectorStoresChanged(){return vectorCollectionBridge.notifyVectorStoresChanged()}
function openDatabaseCreationFromResearch(){return vectorCollectionBridge.openDatabaseCreationFromResearch()}
function openCollectionCreationWizard(options={}){return vectorCollectionBridge.openCollectionCreationWizard(options)}
const TOUCHUP_GROUPS = [
  {name:"Text quality", fields:["text"]},
  {name:"Attribution", fields:["speaker","position_holder","target"]},
  {name:"Quotation provenance", fields:["is_direct_quote","quoted_speaker","quoted_author","quoted_work","quoted_position_holder","quoted_addressee","quoted_referent","quotation_chain"]},
  {name:"Discourse semantics", fields:["discourse_role","proposition_status","semantic_function","stance","claim_scope"]},
  {name:"Indexing", fields:["topics","concepts","persons","works_referenced"]},
  {name:"Review / quality", fields:["attribution_confidence","semantic_classification_confidence","extraction_quality","needs_review","review_reason"]},
  {name:"Source / edition", fields:["work","document_author","edition","year","page_start","page_end","region_type","region_author","primary_text","document_language","original_language","document_is_translation","translator","inline_citation","full_citation","canonical_work_id"]},
];

const HIGH_RISK_TOUCHUP_FIELDS = new Set(["text","record_id","canonical_work_id","inline_citation","full_citation","edition","year","page_start","page_end"]);
const TOUCHUP_CREATABLE_FIELDS = new Set([
  "speaker","position_holder","target","discourse_role","proposition_status","semantic_function","stance","claim_scope",
  "is_direct_quote","quoted_speaker","quoted_author","quoted_work","quoted_position_holder","quoted_addressee","quoted_referent","quotation_chain",
  "topics","concepts","persons","works_referenced","attribution_confidence","semantic_classification_confidence","extraction_quality","needs_review","review_reason"
]);

function touchupFieldsForRecord(record){
  const known=[];
  for(const group of TOUCHUP_GROUPS){
    for(const field of group.fields){
      if(field in record || TOUCHUP_CREATABLE_FIELDS.has(field)){
        if(!known.includes(field))known.push(field);
      }
    }
  }
  for(const field of Object.keys(record)){
    if(!known.includes(field) && field!=="text_length" && !field.startsWith("_"))known.push(field);
  }
  return known;
}

function modelOptionLabel(model){
  const bits=[];
  if(model.parameter_size)bits.push(model.parameter_size);
  if(model.quantization_level)bits.push(model.quantization_level);
  return bits.length?`${model.name} · ${bits.join(" · ")}`:model.name;
}

function jsonPretty(value){
  if(typeof value==="string")return value;
  try{return JSON.stringify(value,null,2)}catch{return String(value)}
}

function llmDiffSides(field,current,proposed){
  if(field!=="text")return null;
  const parts=diffWordsWithSpace(String(current??""),String(proposed??""));
  const left=parts.filter(part=>!part.added).map(part=>part.removed?`<span class="del">${esc(part.value)}</span>`:esc(part.value)).join("");
  const right=parts.filter(part=>!part.removed).map(part=>part.added?`<span class="ins">${esc(part.value)}</span>`:esc(part.value)).join("");
  return {left,right};
}


function ensureProviderProfiles(){
  let profiles=Array.isArray(state.appConfig.provider_profiles)?state.appConfig.provider_profiles:[];
  profiles=profiles.filter(profile=>profile&&profile.id&&["ollama","openai"].includes(profile.type));
  if(!profiles.length){
    profiles=[
      {
        id:"ollama-default",
        name:"Local Ollama",
        type:"ollama",
        base_url:state.appConfig.ollama_base_url||"http://host.docker.internal:11434",
        model:state.appConfig.chat_model||"gemma4:e2b",
        model_mode:"manual",
        model_kind:"any",
        api_key:"",
        num_ctx:state.llmConfig.num_ctx??16384,
        num_predict:state.appConfig.text_num_predict??4096,
        metadata_num_predict:state.appConfig.metadata_num_predict??768,
        think:String(state.llmConfig.think??"false"),
        temperature:state.llmConfig.temperature??0,
        top_k:state.llmConfig.top_k??0,
        top_p:state.llmConfig.top_p??1,
        min_p:state.llmConfig.min_p??"",
        repeat_penalty:state.llmConfig.repeat_penalty??1.1,
        seed:state.llmConfig.seed??"",
        mirostat:state.llmConfig.mirostat??0,
        mirostat_eta:state.llmConfig.mirostat_eta??"",
        mirostat_tau:state.llmConfig.mirostat_tau??"",
        keep_alive:state.llmConfig.keep_alive||"10m",
        extra_options:state.llmConfig.extra_options||"{}",
        max_concurrent_requests:1,
      },
      {
        id:"openai-default",
        name:"FreeLLM / OpenAI-compatible",
        type:"openai",
        base_url:state.appConfig.openai_base_url||"http://host.docker.internal:3001/v1",
        model:state.appConfig.openai_model||"auto",
        model_mode:state.appConfig.openai_model_mode||"auto",
        model_kind:state.appConfig.openai_model_kind||"any",
        api_key:state.appConfig.openai_api_key||"",
        num_predict:state.appConfig.openai_num_predict??4096,
        temperature:state.appConfig.openai_temperature??0,
        top_p:state.appConfig.openai_top_p??1,
        seed:state.appConfig.openai_seed??"",
        extra_options:state.appConfig.openai_extra_options||"{}",
        max_concurrent_requests:32,
      },
    ];
  }
  profiles=profiles.map(profile=>({
    ...profile,
    max_concurrent_requests:Math.max(1,Math.min(64,Number(profile.max_concurrent_requests??(profile.type==="ollama"?1:32))||1)),
  }));
  // Ollama concurrency belongs to the endpoint, not the profile. Multiple
  // profiles can point at the same server/model host, so the safest configured
  // limit governs every profile sharing that endpoint. Normalize on read as
  // well as save so older browser preferences cannot bypass the shared cap.
  const ollamaEndpointLimits=new Map();
  for(const profile of profiles){
    if(profile.type!=="ollama")continue;
    const endpoint=String(profile.base_url||"").replace(/\/+$/g,"").toLocaleLowerCase();
    const limit=Number(profile.max_concurrent_requests||1);
    ollamaEndpointLimits.set(endpoint,Math.min(ollamaEndpointLimits.get(endpoint)??limit,limit));
  }
  profiles=profiles.map(profile=>profile.type==="ollama"?{...profile,max_concurrent_requests:ollamaEndpointLimits.get(String(profile.base_url||"").replace(/\/+$/g,"").toLocaleLowerCase())??profile.max_concurrent_requests}:profile);
  state.appConfig.provider_profiles=profiles;
  if(!profiles.some(profile=>profile.id===state.appConfig.default_provider_profile)){
    const preferred=profiles.find(profile=>profile.type===(state.appConfig.chat_provider||"ollama"))||profiles[0];
    state.appConfig.default_provider_profile=preferred?.id||"";
  }
  return profiles;
}
function providerProfiles(){
  if(isResearcher())return Array.isArray(state.researcherProviderProfiles)?state.researcherProviderProfiles:[];
  return ensureProviderProfiles();
}
function providerProfile(id){
  const profiles=providerProfiles();
  return profiles.find(profile=>profile.id===id)||profiles[0]||null;
}
function defaultProviderProfile(){
  return providerProfile(state.appConfig.default_provider_profile);
}
function providerDisplayName(profile){
  if(!profile)return "LLM provider";
  return profile.name||`${profile.type==="ollama"?"Ollama":"OpenAI-compatible"} · ${profile.model||"model"}`;
}
function providerRequestConfig(profile,{textReview=false}={}){
  if(!profile)return null;
  let extra={};
  // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  try{extra=JSON.parse(profile.extra_options||"{}")}catch{}
  if(!extra||Array.isArray(extra)||typeof extra!=="object")extra={};
  let think=null;
  if(profile.type==="ollama"){
    const raw=String(profile.think??"false");
    think=raw==="true"?true:["low","medium","high"].includes(raw)?raw:false;
  }
  return {
    provider_profile_id:profile.id,
    max_concurrent_requests:Math.max(1,Math.min(64,Number(profile.max_concurrent_requests??(profile.type==="ollama"?1:32))||1)),
    provider:profile.type,
    model:profile.type==="openai"&&profile.model_mode==="auto"?"auto":(profile.model||""),
    base_url:profile.base_url||null,
    api_key:profile.type==="openai"?(profile.api_key||""):null,
    ollama:{
      num_ctx:profile.type==="ollama"&&profile.num_ctx!==""?Number(profile.num_ctx):null,
      num_predict:Number(textReview?(profile.num_predict??4096):(profile.metadata_num_predict??profile.num_predict??768)),
      think,
      temperature:profile.temperature===""?null:Number(profile.temperature??0),
      top_k:profile.type==="ollama"&&profile.top_k!==""?Number(profile.top_k):null,
      top_p:profile.top_p===""?null:Number(profile.top_p??1),
      min_p:profile.type==="ollama"&&profile.min_p!==""?Number(profile.min_p):null,
      repeat_penalty:profile.type==="ollama"&&profile.repeat_penalty!==""?Number(profile.repeat_penalty):null,
      seed:profile.seed===""?null:Number(profile.seed),
      mirostat:profile.type==="ollama"&&profile.mirostat!==""?Number(profile.mirostat):null,
      mirostat_eta:profile.type==="ollama"&&profile.mirostat_eta!==""?Number(profile.mirostat_eta):null,
      mirostat_tau:profile.type==="ollama"&&profile.mirostat_tau!==""?Number(profile.mirostat_tau):null,
      keep_alive:profile.type==="ollama"?(profile.keep_alive||null):null,
      extra_options:extra,
    },
  };
}
async function refreshProviderStatuses(){
  const statuses={};
  await Promise.all(providerProfiles().map(async profile=>{
    try{
      statuses[profile.id]=await api("/api/llm/status",{
        method:"POST",
        body:JSON.stringify({
          provider:profile.type,
          base_url:profile.base_url||null,
          api_key:profile.type==="openai"?(profile.api_key||""):null,
        }),
      });
    }catch(error){
      statuses[profile.id]={
        provider:profile.type,
        available:false,
        base_url:profile.base_url,
        configured_model:profile.model,
        models:[],
        error:error.message,
      };
    }
  }));
  state.providerStatuses=statuses;
  const current=defaultProviderProfile();
  state.llmStatus=current?statuses[current.id]||null:null;
  return statuses;
}

function openAiModelMatchesKind(name,kind){
  if(!kind||kind==="any")return true;
  const value=String(name||"").toLocaleLowerCase();
  const patterns={
    reasoning:["reason","deepseek","r1","qwq","o1","o3","thinking"],
    coding:["code","coder","codex","devstral","starcoder"],
    fast:["mini","small","flash","haiku","fast","3b","4b","7b","8b"],
    general:["gpt","gemma","llama","qwen","mistral","claude","general","chat"],
  };
  return (patterns[kind]||[]).some(token=>value.includes(token));
}

async function legacyOpenTouchup(inputItems=null,initialMode="foreground"){
  const fallback=(()=>{
    const file=activeFile(),record=selectedRecord();
    if(!file||!record)return [];
    const index=selectedIndex(file);
    return [{file,index,record,key:reviewKey(file,index)}];
  })();
  const items=(inputItems?.length?inputItems:fallback).map(item=>({
    ...item,
    record:item.file.records[item.index],
    key:item.key||reviewKey(item.file,item.index),
  })).filter(item=>item.record);
  if(!items.length)return;

  const dialog=document.createElement("dialog");
  dialog.className="llm-dialog batch-llm-dialog";
  document.body.appendChild(dialog);

  let profileId=state.appConfig.review_provider_profile||state.appConfig.default_provider_profile||defaultProviderProfile()?.id||"";
  let profile=providerProfile(profileId);
  let provider=profile?.type||state.appConfig.chat_provider||"ollama";
  let reviewMode=initialMode==="auto"
    ?"auto"
    :(state.appConfig.default_llm_run_mode==="foreground"?"foreground":"background");
  let status=null;
  let running=false;
  let stopped=false;
  let instructionsValue="";
  let selection=new Set();
  const results=new Map();
  const approvals=new Map();
  const expanded=new Set([items[0].key]);

  const fieldSet=new Set();
  for(const item of items){
    for(const field of touchupFieldsForRecord(item.record)){
      if(field!=="updates")fieldSet.add(field);
    }
  }
  const availableFields=[...fieldSet];
  const attributionPreset=["speaker","position_holder","target","is_direct_quote","quoted_speaker","quoted_author","quoted_work","quoted_position_holder","quoted_addressee","quoted_referent","quotation_chain"].filter(x=>availableFields.includes(x));
  const semanticPreset=["discourse_role","proposition_status","semantic_function","stance","claim_scope","topics","concepts","persons","works_referenced"].filter(x=>availableFields.includes(x));
  selection=new Set(
    state.appConfig.default_review_preset==="text"&&availableFields.includes("text")
      ? ["text"]
      : state.appConfig.default_review_preset==="semantic"
        ? semanticPreset
        : attributionPreset
  );

  function close(){
    stopped=true;
    dialog.close();
    dialog.remove();
  }
  function providerName(){
    return profile?providerDisplayName(profile):(provider==="openai"?"OpenAI-compatible":"Ollama");
  }
  function modelStatusHtml(){
    if(!status)return `<span class="llm-status"><i class="status-dot warn"></i>Checking ${providerName()}…</span>`;
    if(status.available)return `<span class="llm-status"><i class="status-dot ok"></i><strong>${providerName()} ready</strong><span>${status.models?.length||0} models</span></span>`;
    return `<span class="llm-status"><i class="status-dot bad"></i><strong>${providerName()} unavailable</strong></span>`;
  }
  function fieldGroupsHtml(){
    const used=new Set(),groups=[];
    for(const group of TOUCHUP_GROUPS){
      const fields=group.fields.filter(field=>availableFields.includes(field)&&field!=="updates");
      if(!fields.length)continue;
      fields.forEach(field=>used.add(field));
      groups.push(`<div class="field-group"><h4>${esc(group.name)}</h4><div class="check-list">${fields.map(field=>`<label class="check-item"><input type="checkbox" data-field="${esc(field)}" ${selection.has(field)?"checked":""}><span>${esc(label(field))}</span>${HIGH_RISK_TOUCHUP_FIELDS.has(field)?'<span class="field-risk">verify</span>':""}</label>`).join("")}</div></div>`);
    }
    const other=availableFields.filter(field=>!used.has(field)&&field!=="updates");
    if(other.length)groups.push(`<div class="field-group"><h4>Other fields</h4><div class="check-list">${other.map(field=>`<label class="check-item"><input type="checkbox" data-field="${esc(field)}" ${selection.has(field)?"checked":""}><span>${esc(label(field))}</span></label>`).join("")}</div></div>`);
    return groups.join("");
  }
  function nullableNumber(id,integer=false){
    const value=dialog.querySelector(`#${id}`)?.value?.trim();
    if(!value)return null;
    const n=integer?parseInt(value,10):parseFloat(value);
    if(!Number.isFinite(n))throw new Error(`${id} must be numeric`);
    return n;
  }
  function configValue(key){
    if(profile&&profile[key]!==undefined&&profile[key]!==null)return String(profile[key]);
    const value=state.llmConfig?.[key];
    return value===null||value===undefined?"":String(value);
  }
  function chosenModel(){
    const mode=dialog.querySelector("#openaiModelMode")?.value||profile?.model_mode||"auto";
    if(provider==="openai"&&mode==="auto")return "auto";
    return dialog.querySelector("#touchModel")?.value?.trim()
      ||profile?.model
      ||state.llmConfig.model
      ||status?.configured_model
      ||"";
  }
  function captureConfig(){
    const thinkRaw=dialog.querySelector("#ollamaThink")?.value??state.llmConfig.think;
    let think=null;
    if(thinkRaw==="false")think=false;
    else if(thinkRaw==="true")think=true;
    else if(["low","medium","high"].includes(thinkRaw))think=thinkRaw;

    let extra={};
    const extraText=dialog.querySelector("#ollamaExtra")?.value?.trim()
      ||profile?.extra_options
      ||state.llmConfig.extra_options
      ||"{}";
    try{extra=JSON.parse(extraText)}catch{throw new Error("Advanced LLM options must be valid JSON")}
    if(!extra||Array.isArray(extra)||typeof extra!=="object")throw new Error("Advanced LLM options must be a JSON object");

    profileId=dialog.querySelector("#llmProvider")?.value||profileId;
    profile=providerProfile(profileId);
    provider=profile?.type||provider;
    reviewMode=dialog.querySelector("#reviewMode")?.value||reviewMode;
    if(reviewMode!=="auto")state.appConfig.default_llm_run_mode=reviewMode;
    const modelMode=provider==="openai"?(dialog.querySelector("#openaiModelMode")?.value||profile?.model_mode||"auto"):"manual";
    const modelKind=provider==="openai"?(dialog.querySelector("#openaiModelKind")?.value||profile?.model_kind||"any"):"any";
    const model=chosenModel();
    // Connection details belong to the provider profile. The review workspace
    // consumes them but never duplicates credentials or endpoint editing UI.
    const base_url=profile?.base_url||"";
    const api_key=provider==="openai"?(profile?.api_key||""):null;

    const config={
      model,
      num_ctx:nullableNumber("ollamaNumCtx",true),
      num_predict:nullableNumber("ollamaNumPredict",true) ?? (selection.has("text")?Number(state.appConfig.text_num_predict||4096):Number(state.appConfig.metadata_num_predict||768)),
      think:thinkRaw,
      temperature:nullableNumber("ollamaTemperature"),
      top_k:nullableNumber("ollamaTopK",true),
      top_p:nullableNumber("ollamaTopP"),
      min_p:nullableNumber("ollamaMinP"),
      repeat_penalty:nullableNumber("ollamaRepeatPenalty"),
      seed:nullableNumber("ollamaSeed",true),
      mirostat:nullableNumber("ollamaMirostat",true),
      mirostat_eta:nullableNumber("ollamaMirostatEta"),
      mirostat_tau:nullableNumber("ollamaMirostatTau"),
      keep_alive:dialog.querySelector("#ollamaKeepAlive")?.value?.trim()||null,
      extra_options:extraText,
    };
    state.llmConfig={...state.llmConfig,...config};
    state.appConfig.chat_provider=provider;
    state.appConfig.review_provider_profile=profileId;
    if(profile){
      Object.assign(profile,{
        model,
        model_mode:modelMode,
        model_kind:modelKind,
        num_ctx:config.num_ctx??profile.num_ctx,
        num_predict:selection.has("text")?config.num_predict:(profile.num_predict??config.num_predict),
        metadata_num_predict:selection.has("text")?(profile.metadata_num_predict??768):config.num_predict,
        think:String(config.think??profile.think??"false"),
        temperature:config.temperature??profile.temperature,
        top_k:config.top_k??profile.top_k,
        top_p:config.top_p??profile.top_p,
        min_p:config.min_p??profile.min_p,
        repeat_penalty:config.repeat_penalty??profile.repeat_penalty,
        seed:config.seed??"",
        mirostat:config.mirostat??profile.mirostat,
        mirostat_eta:config.mirostat_eta??profile.mirostat_eta,
        mirostat_tau:config.mirostat_tau??profile.mirostat_tau,
        keep_alive:config.keep_alive??profile.keep_alive,
        extra_options:extraText,
      });
    }
    persistPrefs();
    return {
      provider_profile_id:profileId,
      max_concurrent_requests:Math.max(1,Math.min(64,Number(profile?.max_concurrent_requests??(provider==="ollama"?1:32))||1)),
      provider,
      model,
      base_url,
      api_key,
      ollama:{
        num_ctx:config.num_ctx,
        num_predict:config.num_predict,
        think,
        temperature:config.temperature,
        top_k:config.top_k,
        top_p:config.top_p,
        min_p:config.min_p,
        repeat_penalty:config.repeat_penalty,
        seed:config.seed,
        mirostat:config.mirostat,
        mirostat_eta:config.mirostat_eta,
        mirostat_tau:config.mirostat_tau,
        keep_alive:config.keep_alive,
        extra_options:extra,
      },
    };
  }
  async function fetchLlmStatus(){
    const base_url=profile?.base_url||"";
    const api_key=provider==="openai"?(profile?.api_key||""):"";
    try{
      const next=await api("/api/llm/status",{
        method:"POST",
        body:JSON.stringify({provider,base_url,api_key}),
      });
      state.providerStatuses[profileId]=next;
      if(profileId===state.appConfig.default_provider_profile)state.llmStatus=next;
      updateSystemCard();
      return next;
    }catch(error){
      return {provider,available:false,models:[],configured_model:"",base_url,error:error.message};
    }
  }
  async function switchProvider(nextProfileId){
    profileId=nextProfileId;
    profile=providerProfile(profileId);
    provider=profile?.type||"ollama";
    state.appConfig.review_provider_profile=profileId;
    state.appConfig.chat_provider=provider;
    state.llmConfig.model=profile?.model||"";
    status=state.providerStatuses?.[profileId]||null;
    renderSetup();
    if(!status){
      status=await fetchLlmStatus();
      renderSetup();
    }
  }
  function renderSetup(){
    const models=status?.models||[];
    const configured=profile?.model||status?.configured_model||(provider==="ollama"?"gemma4:e2b":"auto");
    if(!state.llmConfig.model || provider!==state.appConfig.chat_provider){
      state.llmConfig.model=configured;
    }else if(provider==="ollama"&&models.length&&!models.some(m=>m.name===state.llmConfig.model)){
      state.llmConfig.model=models.some(m=>m.name===configured)?configured:(models[0]?.name||configured);
    }
    const canRun=Boolean(selection.size&&chosenModel()&&(status?.available||provider==="openai"));
    const selectedKind=profile?.model_kind||"any";
    const filteredModels=provider==="openai"?models.filter(model=>openAiModelMatchesKind(model.name,selectedKind)):models;
    const providerModels=filteredModels.map(m=>`<option value="${esc(m.name)}"></option>`).join("");

    dialog.innerHTML=`<div class="dh llm-head"><div><h2 class="dialog-title">${reviewMode==="auto"?"Auto-improve":"LLM Review Workspace"}</h2><div class="dialog-subtitle">${items.length} record${items.length===1?"":"s"} · ${reviewMode==="foreground"?"interactive review stays in this dialog and exposes proposals as each record completes":"background review can continue while you use the rest of the application"}</div></div><div class="inline">${modelStatusHtml()}<button class="btn icon-only" type="button" data-close>${icon("close")}</button></div></div>
    <div class="db llm-body"><div class="llm-layout">
      <aside class="llm-config">
        <div class="llm-section"><div class="llm-section-title">Run mode</div><select class="control" id="reviewMode"><option value="foreground" ${reviewMode==="foreground"?"selected":""}>Interactive foreground</option><option value="background" ${reviewMode==="background"?"selected":""}>Background review</option><option value="auto" ${reviewMode==="auto"?"selected":""}>Background Auto-improve</option></select><div class="note" style="margin-top:6px">Switch freely between interactive review, background review, and aggregate Auto-improve before starting the run.</div></div>
        <div class="llm-section llm-provider-section"><div class="llm-section-title">${esc(tr("llm.provider_profile","Provider profile"))}</div><select class="control llm-provider-select" id="llmProvider" aria-label="${esc(tr("llm.provider_profile","Provider profile"))}">${providerProfiles().map(p=>`<option value="${esc(p.id)}" ${p.id===profileId?"selected":""} title="${esc(providerDisplayName(p))}">${esc(providerDisplayName(p))}</option>`).join("")}</select>
          <div class="llm-provider-summary"><span class="llm-provider-kind">${esc(provider==="ollama"?"Ollama":tr("llm.openai_compatible","OpenAI-compatible"))}</span><span class="llm-provider-model" title="${esc(profile?.model||state.llmConfig.model||"")}">${esc(profile?.model||state.llmConfig.model||tr("llm.model_not_set","Model not set"))}</span></div>
          <p class="note llm-provider-profile-note">${esc(tr("llm.connection_from_profile","Endpoint and credentials come from the provider profile and are managed centrally."))}</p>
          <button class="btn small" id="llmManageProvider" type="button">${esc(tr("llm.manage_provider_profiles","Manage provider profiles"))}</button>
        </div>
        ${provider==="openai"?`<div class="llm-section"><div class="llm-section-title">FreeLLM / OpenAI model selection</div><div class="llm-param-grid"><div class="field"><label>Selection mode</label><select class="control" id="openaiModelMode"><option value="auto" ${profile?.model_mode==="auto"?"selected":""}>Auto router</option><option value="discovered" ${profile?.model_mode==="discovered"?"selected":""}>Choose discovered model</option><option value="manual" ${profile?.model_mode==="manual"?"selected":""}>Manual model ID</option></select></div><div class="field"><label>Model kind filter</label><select class="control" id="openaiModelKind"><option value="any" ${profile?.model_kind==="any"?"selected":""}>Any</option><option value="general" ${profile?.model_kind==="general"?"selected":""}>General/chat</option><option value="reasoning" ${profile?.model_kind==="reasoning"?"selected":""}>Reasoning</option><option value="coding" ${profile?.model_kind==="coding"?"selected":""}>Coding</option><option value="fast" ${profile?.model_kind==="fast"?"selected":""}>Fast/small</option></select></div></div><div class="note">The kind filter narrows the endpoint's discovered model IDs by name. Auto router sends model <code>auto</code>; Manual accepts any compatible model ID.</div></div>`:""}
        <div class="llm-section"><div class="llm-section-title">Review preset</div><div class="preset-row"><button class="preset" data-preset="attribution" type="button">Attribution</button><button class="preset" data-preset="semantic" type="button">Semantics</button><button class="preset" data-preset="text" type="button">OCR / text</button></div><div class="note" style="margin-top:8px">Text review runs separately so output stays bounded.</div></div>
        <div class="llm-section"><div class="llm-section-title">Allowed fields</div><div class="inline" style="margin-bottom:7px"><button class="btn small" id="selectAllFields" type="button">Select metadata</button><button class="btn small" id="clearAllFields" type="button">Clear</button><span class="note" id="fieldCount"></span></div><div class="field-groups">${fieldGroupsHtml()}</div></div>
        <div class="llm-section"><div class="llm-section-title">Model</div><div class="llm-model-row"><input class="control" id="touchModel" list="llmModels" value="${esc(provider==="openai"&&profile?.model_mode==="auto"?"auto":(state.llmConfig.model||configured))}" placeholder="Model name" ${provider==="openai"&&profile?.model_mode==="auto"?"disabled":""}><datalist id="llmModels">${providerModels}</datalist><button class="btn icon-only" id="refreshModels" type="button">${icon("refresh")}</button></div>${status&&!status.available?`<div class="info warn" style="margin-top:8px">${esc(status.error||`${providerName()} model discovery unavailable. You may still enter a model manually.`)}</div>`:""}</div>
        <div class="llm-section"><div class="llm-section-title">${provider==="ollama"?"Ollama":"Generation"} parameters</div><div class="llm-param-grid">
          ${provider==="ollama"?`<div class="field"><label>Context (num_ctx)</label><input class="control" id="ollamaNumCtx" type="number" min="512" value="${esc(configValue("num_ctx"))}" placeholder="model default"></div>`:""}
          <div class="field"><label>Max output</label><input class="control" id="ollamaNumPredict" type="number" min="16" value="${esc(configValue("num_predict"))}" placeholder="${selection.has("text")?status?.limits?.text_num_predict||4096:status?.limits?.metadata_num_predict||768}"></div>
          ${provider==="ollama"?`<div class="field"><label>Think</label><select class="control" id="ollamaThink">${[["false","Off"],["true","On"],["low","Low"],["medium","Medium"],["high","High"]].map(([v,l])=>`<option value="${v}" ${String(state.llmConfig.think)===v?"selected":""}>${l}</option>`).join("")}</select></div>`:""}
          <div class="field"><label>Temperature</label><input class="control" id="ollamaTemperature" type="number" step="0.01" min="0" max="2" value="${esc(configValue("temperature"))}"></div>
          ${provider==="ollama"?`<div class="field"><label>top_k</label><input class="control" id="ollamaTopK" type="number" min="0" value="${esc(configValue("top_k"))}"></div>`:""}
          <div class="field"><label>top_p</label><input class="control" id="ollamaTopP" type="number" step="0.01" min="0" max="1" value="${esc(configValue("top_p"))}"></div>
          ${provider==="ollama"?`<div class="field"><label>min_p</label><input class="control" id="ollamaMinP" type="number" step="0.01" min="0" max="1" value="${esc(configValue("min_p"))}"></div><div class="field"><label>repeat_penalty</label><input class="control" id="ollamaRepeatPenalty" type="number" step="0.01" min="0" value="${esc(configValue("repeat_penalty"))}"></div>`:""}
          <div class="field"><label>seed</label><input class="control" id="ollamaSeed" type="number" value="${esc(configValue("seed"))}" placeholder="random"></div>
          ${provider==="ollama"?`<div class="field"><label>mirostat</label><select class="control" id="ollamaMirostat">${[0,1,2].map(v=>`<option value="${v}" ${Number(state.llmConfig.mirostat||0)===v?"selected":""}>${v}</option>`).join("")}</select></div><div class="field"><label>mirostat_eta</label><input class="control" id="ollamaMirostatEta" type="number" step="0.01" value="${esc(configValue("mirostat_eta"))}"></div><div class="field"><label>mirostat_tau</label><input class="control" id="ollamaMirostatTau" type="number" step="0.01" value="${esc(configValue("mirostat_tau"))}"></div><div class="field field-full"><label>keep_alive</label><input class="control" id="ollamaKeepAlive" value="${esc(configValue("keep_alive"))}" placeholder="10m"></div>`:""}
        </div><details class="advanced-options"><summary>Advanced provider options</summary><div class="field"><label>Additional options JSON</label><textarea id="ollamaExtra" spellcheck="false">${esc(profile?.extra_options||"{}")}</textarea></div></details></div>
        <div class="llm-section field"><label>Additional instructions</label><textarea id="touchInstructions" placeholder="Optional instructions applied to every record in this batch.">${esc(instructionsValue)}</textarea></div>
      </aside>
      <section class="llm-review" id="proposalArea"></section>
    </div></div>
    <div class="da" id="llmFooter"><div class="llm-footer-note">${reviewMode==="foreground"?"Interactive mode keeps this dialog open and reveals completed proposals immediately.":"The job continues in the background; results are available from Dashboard → Background operations."}</div><button class="btn" type="button" data-close>Cancel</button><button class="btn primary" id="runTouchup" type="button" ${canRun?"":"disabled"}>${icon("spark")}${reviewMode==="auto"?"Auto-improve":reviewMode==="foreground"?"Run interactive review":"Start background review"} · ${items.length}</button></div>`;

    dialog.querySelectorAll("[data-close]").forEach(b=>b.onclick=close);
    dialog.querySelector("#llmProvider").onchange=e=>switchProvider(e.target.value);
    dialog.querySelector("#llmManageProvider")?.addEventListener("click",()=>{close();navigateTo("providers")});
    dialog.querySelector("#reviewMode").onchange=e=>{
      reviewMode=e.target.value;
      if(reviewMode!=="auto")state.appConfig.default_llm_run_mode=reviewMode;
      persistPrefs();
      renderSetup();
    };
    dialog.querySelector("#openaiModelMode")?.addEventListener("change",e=>{if(profile)profile.model_mode=e.target.value;if(e.target.value==="auto")state.llmConfig.model="auto";persistPrefs();renderSetup()});
    dialog.querySelector("#openaiModelKind")?.addEventListener("change",e=>{if(profile)profile.model_kind=e.target.value;persistPrefs();renderSetup()});
    const updateSelection=()=>{
      const n=selection.size;
      dialog.querySelector("#fieldCount").textContent=`${n} selected`;
      dialog.querySelector("#runTouchup").disabled=!(n&&chosenModel());
    };
    dialog.querySelectorAll("[data-field]").forEach(box=>box.onchange=()=>{
      const field=box.dataset.field;
      if(box.checked&&field==="text")selection=new Set(["text"]);
      else if(box.checked){selection.delete("text");selection.add(field)}
      else selection.delete(field);
      dialog.querySelectorAll("[data-field]").forEach(x=>x.checked=selection.has(x.dataset.field));
      updateSelection();
    });
    dialog.querySelector("#selectAllFields").onclick=()=>{selection=new Set(availableFields.filter(field=>field!=="text"&&field!=="updates").slice(0,12));dialog.querySelectorAll("[data-field]").forEach(x=>x.checked=selection.has(x.dataset.field));updateSelection()};
    dialog.querySelector("#clearAllFields").onclick=()=>{selection.clear();dialog.querySelectorAll("[data-field]").forEach(x=>x.checked=false);updateSelection()};
    dialog.querySelectorAll("[data-preset]").forEach(button=>button.onclick=()=>{
      selection=new Set(button.dataset.preset==="text"?(availableFields.includes("text")?["text"]:[]):button.dataset.preset==="semantic"?semanticPreset:attributionPreset);
      dialog.querySelectorAll("[data-field]").forEach(x=>x.checked=selection.has(x.dataset.field));
      updateSelection();
    });
    dialog.querySelector("#touchModel")?.addEventListener("input",e=>{state.llmConfig.model=e.target.value;persistPrefs();updateSelection()});
    dialog.querySelector("#touchInstructions")?.addEventListener("input",e=>instructionsValue=e.target.value);
    dialog.querySelector("#refreshModels").onclick=async()=>{
      // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
      try{captureConfig()}catch{}
      status=await fetchLlmStatus();
      renderSetup();
    };
    dialog.querySelector("#runTouchup").onclick=run;
    renderQueue(-1);
    updateSelection();
  }
  function changeHtml(item,result,field,value){
    const current=item.file.records[item.index]?.[field];
    const diff=llmDiffSides(field,current,value);
    const checked=approvals.get(item.key)?.has(field)||false;
    return `<article class="proposal compact-proposal"><div class="proposalhead"><input type="checkbox" data-change-key="${esc(item.key)}" data-change-field="${esc(field)}" ${checked?"checked":""}><b>${esc(label(field))}</b>${HIGH_RISK_TOUCHUP_FIELDS.has(field)?'<span class="field-risk">verify carefully</span>':""}</div><div class="proposalbody"><div class="proposal-col"><div class="proposal-label">Current</div><div class="box ${field==="text"?"text-diff":""}">${diff?diff.left:esc(jsonPretty(current))}</div></div><div class="proposal-col"><div class="proposal-label">Proposed</div><div class="box ${field==="text"?"text-diff":""}">${diff?diff.right:esc(jsonPretty(value))}</div></div></div><div class="reason">${esc(result.proposal.rationale?.[field]||"No rationale supplied.")}</div></article>`;
  }
  function renderAutoProgress(activeIndex){
    const area=dialog.querySelector("#proposalArea");if(!area)return;
    const completed=results.size;
    area.innerHTML=`<div class="auto-improve-running"><div class="spinner"></div><h3>Auto-improve pass in progress</h3><p>${completed} of ${items.length} records reviewed.</p><div class="batch-progress-bar"><i style="width:${Math.round(items.length?completed/items.length*100:0)}%"></i></div><div class="note">Proposals are intentionally hidden until every queued record has been processed.</div>${activeIndex>=0?`<div class="auto-current">Currently reviewing ${esc(items[activeIndex]?.record?.record_id||`record ${activeIndex+1}`)}</div>`:""}</div>`;
  }
  function renderQueue(activeIndex=-1){
    if(reviewMode==="auto"&&running){
      renderAutoProgress(activeIndex);
      updateFooter();
      return;
    }
    const area=dialog.querySelector("#proposalArea");if(!area)return;
    const completed=results.size;
    const proposed=[...results.values()].reduce((n,r)=>n+Object.keys(r.proposal?.changes||{}).length,0);
    area.innerHTML=`<div class="queue-header"><div><b>${running?"Review in progress":reviewMode==="auto"?"Auto-improve results":"Review queue"}</b><div class="note">${completed} of ${items.length} completed${proposed?` · ${proposed} proposed changes`:""} · expand cards to inspect proposals</div></div><div class="tools"><button class="btn small" id="expandAllCards" type="button">Expand all</button><button class="btn small" id="collapseAllCards" type="button">Collapse all</button>${proposed?`<button class="btn small" id="selectAllChanges" type="button">Select all changes</button><button class="btn small" id="selectNoChanges" type="button">Select none</button>`:""}${running?'<button class="btn small" id="stopBatch" type="button">Stop after current</button>':""}</div></div>${running?`<div class="batch-progress"><div class="batch-progress-bar"><i style="width:${Math.round((completed/items.length)*100)}%"></i></div></div>`:""}
    <div class="live-queue">${items.map((item,index)=>{
      const result=results.get(item.key);
      const active=running&&index===activeIndex&&!result;
      const isExpanded=expanded.has(item.key)||active;
      const changes=Object.entries(result?.proposal?.changes||{});
      const statusHtml=result?`<span class="llm-status"><i class="status-dot ${result.error?"bad":"ok"}"></i>${result.error?"Failed":`${changes.length} change${changes.length===1?"":"s"}`}</span>`:active?'<span class="llm-status"><div class="spinner small-spinner"></div>Reviewing</span>':'<span class="llm-status"><i class="status-dot"></i>Queued</span>';
      let body="";
      if(isExpanded){
        if(active)body='<div class="queue-card-wait"><div class="spinner"></div><span>Waiting for model…</span></div>';
        else if(!result)body='<div class="llm-empty compact-empty">Waiting in queue.</div>';
        else if(result.error)body=`<div class="llm-error"><h3>Review failed</h3><p>${esc(result.error.message||String(result.error))}</p>${result.error.diagnostic?`<pre>${esc(result.error.diagnostic)}</pre>`:""}</div>`;
        else body=`${changes.length?`<div class="record-proposal-actions"><button class="btn small" data-select-record="${esc(item.key)}">Select record changes</button><button class="btn small" data-clear-record="${esc(item.key)}">Clear record</button></div>${changes.map(([field,value])=>changeHtml(item,result,field,value)).join("")}`:'<div class="llm-empty compact-empty">No changes proposed.</div>'}${result.proposal?.warnings?.length?`<div class="info warn llm-warnings">${result.proposal.warnings.map(w=>esc(w)).join("<br>")}</div>`:""}${result.proposal?.effective_options?`<details class="effective-options"><summary>Effective ${esc(result.proposal.provider||providerName())} parameters</summary><pre>${esc(JSON.stringify(result.proposal.effective_options,null,2))}</pre></details>`:""}`;
      }
      return `<section class="llm-queue-card ${active?"active":""} ${result?.error?"error-card":""}"><button class="llm-queue-summary" data-expand="${esc(item.key)}"><span class="queue-index">${index+1}</span><span class="queue-title"><b>${esc(item.record.record_id||`Record ${index+1}`)}</b><small>${esc(item.record.work||item.file.name)} · page ${esc(pages(item.record))}</small></span>${statusHtml}<span class="queue-chevron">${isExpanded?"▾":"▸"}</span></button>${isExpanded?`<div class="llm-queue-body">${body}</div>`:""}</section>`;
    }).join("")}</div>`;
    area.querySelector("#expandAllCards")?.addEventListener("click",()=>{for(const item of items)expanded.add(item.key);renderQueue(activeIndex)});
    area.querySelector("#collapseAllCards")?.addEventListener("click",()=>{expanded.clear();renderQueue(activeIndex)});
    area.querySelectorAll("[data-expand]").forEach(button=>button.onclick=()=>{
      const key=button.dataset.expand;
      expanded.has(key)?expanded.delete(key):expanded.add(key);
      renderQueue(activeIndex);
    });
    area.querySelector("#stopBatch")?.addEventListener("click",e=>{stopped=true;e.target.disabled=true;e.target.textContent="Stopping after current"});
    area.querySelector("#selectAllChanges")?.addEventListener("click",()=>{for(const item of items){const result=results.get(item.key);if(result?.proposal)approvals.set(item.key,new Set(Object.keys(result.proposal.changes||{})))}renderQueue(activeIndex);updateFooter()});
    area.querySelector("#selectNoChanges")?.addEventListener("click",()=>{for(const item of items)approvals.set(item.key,new Set());renderQueue(activeIndex);updateFooter()});
    area.querySelectorAll("[data-select-record]").forEach(button=>button.onclick=()=>{const result=results.get(button.dataset.selectRecord);if(result?.proposal)approvals.set(button.dataset.selectRecord,new Set(Object.keys(result.proposal.changes||{})));renderQueue(activeIndex);updateFooter()});
    area.querySelectorAll("[data-clear-record]").forEach(button=>button.onclick=()=>{approvals.set(button.dataset.clearRecord,new Set());renderQueue(activeIndex);updateFooter()});
    area.querySelectorAll("[data-change-key]").forEach(box=>box.onchange=()=>{
      const key=box.dataset.changeKey,field=box.dataset.changeField;
      if(!approvals.has(key))approvals.set(key,new Set());
      box.checked?approvals.get(key).add(field):approvals.get(key).delete(field);
      updateFooter();
    });
    updateFooter();
  }
  function approvedCount(){
    let n=0;for(const fields of approvals.values())n+=fields.size;return n;
  }
  function updateFooter(){
    const footer=dialog.querySelector("#llmFooter");if(!footer)return;
    if(running){
      footer.innerHTML=`<div class="llm-footer-note">${reviewMode==="foreground"?"Interactive review is running. Completed cards remain inspectable while later records continue.":"Starting background operation…"}</div><button class="btn" type="button" id="closeWhileRunning">${reviewMode==="foreground"?"Stop and close":"Close"}</button>`;
      footer.querySelector("#closeWhileRunning").onclick=close;
      return;
    }
    const successful=[...results.values()].filter(result=>result.proposal);
    const total=successful.reduce((n,result)=>n+Object.keys(result.proposal?.changes||{}).length,0);
    const selected=approvedCount();
    footer.innerHTML=`<div class="llm-footer-note">${results.size?`${successful.length} records reviewed · ${selected} of ${total} proposed changes selected.`:"Ready to review."}</div><button class="btn" data-close type="button">Close</button>${results.size?`<button class="btn" id="reviewAgain" type="button">${icon("refresh")}Review again</button><button class="btn" id="markForegroundReviewed" type="button">${icon("check")}Mark reviewed only</button>`:""}${total?`<button class="btn soft" id="acceptAllChanges" type="button">${icon("check")}Accept all changes</button><button class="btn primary" id="applySelectedChanges" type="button" ${selected?"":"disabled"}>${icon("check")}Apply ${selected} selected</button>`:`${results.size?"":`<button class="btn primary" id="runTouchup" type="button">${icon("spark")}Run review</button>`}`}`;
    footer.querySelector("[data-close]").onclick=close;
    footer.querySelector("#reviewAgain")?.addEventListener("click",()=>{results.clear();approvals.clear();stopped=false;renderSetup()});
    footer.querySelector("#markForegroundReviewed")?.addEventListener("click",()=>applyResults(false,true));
    footer.querySelector("#acceptAllChanges")?.addEventListener("click",()=>applyResults(true,false));
    footer.querySelector("#applySelectedChanges")?.addEventListener("click",()=>applyResults(false,false));
    footer.querySelector("#runTouchup")?.addEventListener("click",run);
  }
  async function run(){
    if(running)return;
    if(!selection.size)return toast("Select at least one field");
    if(selection.has("text")&&selection.size>1)return toast("Text review must run separately from metadata");
    let requestConfig;
    try{requestConfig=captureConfig()}catch(error){return toast(error.message)}
    if(!requestConfig.model)return toast("No model selected");
    instructionsValue=dialog.querySelector("#touchInstructions")?.value||instructionsValue;

    if(reviewMode!=="foreground"){
      running=true;
      const runButton=dialog.querySelector("#runTouchup");
      if(runButton){runButton.disabled=true;runButton.textContent="Starting background job…"}
      try{
        await submitBackgroundLlmJob(
          items,
          requestConfig,
          selection,
          instructionsValue,
          reviewMode==="auto"?"auto":"review",
        );
        close();
      }catch(error){
        running=false;
        if(runButton){
          runButton.disabled=false;
          runButton.innerHTML=`${icon("spark")}${reviewMode==="auto"?"Auto-improve":"Start background review"} · ${items.length}`;
        }
        toast(`Could not start LLM job: ${error.message}`);
      }
      return;
    }

    // Original interactive workflow: one request at a time, proposals visible live.
    results.clear();approvals.clear();running=true;stopped=false;updateFooter();
    for(let index=0;index<items.length;index++){
      if(stopped)break;
      renderQueue(index);
      const item=items[index];
      try{
        const proposal=await api("/api/llm/touchup",{
          method:"POST",
          body:JSON.stringify({
            record:touchupRecordPayload(item.file.records[item.index],[...selection]),
            fields:[...selection],
            instructions:instructionsValue,
            model:requestConfig.model,
            provider:requestConfig.provider,
            base_url:requestConfig.base_url,
            api_key:requestConfig.api_key,
            ollama:requestConfig.ollama,
          }),
        });
        results.set(item.key,{item,proposal,error:null});
        approvals.set(item.key,new Set(Object.keys(proposal.changes||{}).filter(field=>field!=="text")));
      }catch(error){
        results.set(item.key,{item,proposal:null,error});
        approvals.set(item.key,new Set());
      }
      expanded.add(item.key);
      renderQueue(index+1);
    }
    running=false;
    renderQueue(-1);
    updateFooter();
  }
  async function applyResults(all,reviewOnly=false){
    const batchId=uid();let appliedFields=0,reviewedRecords=0;
    for(const item of items){
      const result=results.get(item.key);if(!result?.proposal)continue;
      const fields=reviewOnly?[]:(all?Object.keys(result.proposal.changes||{}):[...(approvals.get(item.key)||[])]);
      const changes={};
      for(const field of fields){
        if(field in result.proposal.changes)changes[field]=result.proposal.changes[field];
      }
      const record=item.file.records[item.index];
      if(record.needs_review===true)changes.needs_review=false;
      if(record.review_reason!==undefined&&record.review_reason!==null&&record.review_reason!=="")changes.review_reason=null;
      const count=applyRecordChanges(item.file,item.index,changes,{source:"llm_review",model:result.proposal.model,batchId,rationale:result.proposal.rationale});
      appliedFields+=count;
      reviewedRecords++;
    }
    clearReviewSelection();close();shell();renderView();
    toast(`Marked ${reviewedRecords} record${reviewedRecords===1?"":"s"} reviewed · ${appliedFields} tracked field change${appliedFields===1?"":"s"}`);
  }

  showAppModal(dialog);
  dialog.innerHTML=`<div class="dh llm-head"><div><h2 class="dialog-title">LLM Review Workspace</h2><div class="dialog-subtitle">${items.length} record${items.length===1?"":"s"}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="llm-loading"><div><div class="spinner"></div><div class="note">Checking configured LLM provider…</div></div></div>`;
  dialog.querySelector("[data-close]").onclick=close;
  status=await fetchLlmStatus();
  renderSetup();
}

function normalizeTouchupItems(inputItems=null){
  const fallback=(()=>{
    const file=activeFile(),record=selectedRecord();
    if(!file||!record)return [];
    const index=selectedIndex(file);
    return [{file,index,record,key:reviewKey(file,index)}];
  })();
  return (inputItems?.length?inputItems:fallback).map(item=>({
    ...item,
    record:item.file.records[item.index],
    key:item.key||reviewKey(item.file,item.index),
  })).filter(item=>item.record);
}
function openTouchup(inputItems=null,initialMode="foreground"){
  const items=normalizeTouchupItems(inputItems);
  if(!items.length)return;
  window.dispatchEvent(new CustomEvent("derridai:open-touchup",{detail:{items,initialMode}}));
}
function touchupWorkspaceInfo(inputItems=null,initialMode="foreground"){
  const items=normalizeTouchupItems(inputItems);
  const availableFields=[];
  for(const item of items){
    for(const field of touchupFieldsForRecord(item.record))if(!availableFields.includes(field)&&field!=="updates")availableFields.push(field);
  }
  const attributionPreset=["speaker","position_holder","target","is_direct_quote","quoted_speaker","quoted_author","quoted_work","quoted_position_holder","quoted_addressee","quoted_referent","quotation_chain"].filter(field=>availableFields.includes(field));
  const semanticPreset=["discourse_role","proposition_status","semantic_function","stance","claim_scope","topics","concepts","persons","works_referenced"].filter(field=>availableFields.includes(field));
  const preset=state.appConfig.default_review_preset;
  return {
    items,
    initialMode,
    availableFields,
    attributionPreset,
    semanticPreset,
    defaultSelection:preset==="text"&&availableFields.includes("text")?["text"]:preset==="semantic"?semanticPreset:attributionPreset,
    groups:TOUCHUP_GROUPS,
    highRiskFields:[...HIGH_RISK_TOUCHUP_FIELDS],
    fieldLabels:Object.fromEntries(availableFields.map(field=>[field,label(field)])),
    profiles:providerProfiles().map(profile=>({...profile,api_key:undefined})),
    providerProfileId:state.appConfig.review_provider_profile||state.appConfig.default_provider_profile||defaultProviderProfile()?.id||"",
    defaultMode:initialMode==="auto"?"auto":state.appConfig.default_llm_run_mode==="foreground"?"foreground":"background",
  };
}
async function touchupProviderStatus(profileId){
  const profile=providerProfile(profileId);
  if(!profile)return {provider:"ollama",available:false,models:[],configured_model:"",error:"No provider profile configured"};
  try{
    const status=await api("/api/llm/status",{method:"POST",body:JSON.stringify({provider:profile.type,base_url:profile.base_url||null,api_key:profile.type==="openai"?(profile.api_key||""):null})});
    state.providerStatuses[profile.id]=status;
    return status;
  }catch(error){return {provider:profile.type,available:false,models:[],configured_model:profile.model||"",error:error.message};}
}
function touchupRequestConfig(profileId,model,fields=[]){
  const profile=providerProfile(profileId);
  const config=providerRequestConfig(profile,{textReview:fields.includes("text")});
  if(config&&model)config.model=model;
  return config;
}
async function touchupRequest(item,fields,config,instructions=""){
  return api("/api/llm/touchup",{method:"POST",body:JSON.stringify({
    record:touchupRecordPayload(item.file.records[item.index],fields),fields,instructions,
    model:config.model,provider:config.provider,base_url:config.base_url,api_key:config.api_key,ollama:config.ollama,
  })});
}
async function touchupSubmitBackground(items,config,fields,instructions,mode){
  return submitBackgroundLlmJob(items,config,fields,instructions,mode);
}
function touchupApplyResults(items,results,approvals,all=false,reviewOnly=false){
  const batchId=uid();let appliedFields=0,reviewedRecords=0;
  for(const item of items){
    const result=results[item.key];if(!result?.proposal)continue;
    const fields=reviewOnly?[]:(all?Object.keys(result.proposal.changes||{}):[...(approvals[item.key]||[])]);
    const changes={};
    for(const field of fields)if(field in result.proposal.changes)changes[field]=result.proposal.changes[field];
    const record=item.file.records[item.index];
    if(record.needs_review===true)changes.needs_review=false;
    if(record.review_reason!==undefined&&record.review_reason!==null&&record.review_reason!=="")changes.review_reason=null;
    appliedFields+=applyRecordChanges(item.file,item.index,changes,{source:"llm_review",model:result.proposal.model,batchId,rationale:result.proposal.rationale});
    reviewedRecords++;
  }
  clearReviewSelection();shell();renderView();
  toast(`Marked ${reviewedRecords} record${reviewedRecords===1?"":"s"} reviewed · ${appliedFields} tracked field change${appliedFields===1?"":"s"}`);
  return {appliedFields,reviewedRecords};
}

function backupContainsCredentials(){
  return providerProfiles().some(profile=>Boolean(profile.api_key));
}
async function downloadFullBackup({confirmed=false}={}){
  const activeJobs=state.jobs.filter(job=>["queued","running","cancelling"].includes(job.status));
  if(activeJobs.length){
    return toast(`Wait for or cancel ${activeJobs.length} active background operation${activeJobs.length===1?"":"s"} before backing up.`);
  }
  const hasCredentials=backupContainsCredentials();
  const warning=hasCredentials
    ? "This full backup contains provider API keys/credentials configured in DerridAI. Treat the ZIP as sensitive. Continue?"
    : "Create a full DerridAI backup containing all loaded JSONL records, configuration, audit history, UI workspace state, the current PDF, and every Chroma collection with its stored embeddings?";
  if(!confirmed&&!await openMessageModal({title:"Create full backup?",message:warning,tone:hasCredentials?"danger":"info",confirmLabel:"Create backup",cancelLabel:"Cancel"}))return;
  const button=document.querySelector("#downloadFullBackup");
  if(button){button.disabled=true;button.textContent="Creating backup…"}
  try{
    for(const file of state.files)await persistFileNow(file);
    const workspace={
      backup_client_version:"0.40.10",
      created_at:new Date().toISOString(),
      files:state.files.map(serializableFile),
      prefs:workspacePrefs(),
    };
    const form=new FormData();
    form.append("workspace",new Blob([JSON.stringify(workspace)],{type:"application/json"}),"workspace.json");
    form.append("pdf_metadata",JSON.stringify({
      name:state.pdf.name||"",
      title:state.pdf.title||"",
      author:state.pdf.author||"",
      page:state.pdf.page||1,
      rotation:state.pdf.rotation||0,
      text:state.pdf.text||"",
      search:state.pdf.search||"",
      relatedSearch:state.pdf.relatedSearch||"",
      extractionSource:state.pdf.extractionSource||"",
      extractError:state.pdf.extractError||"",
    }));
    if(state.pdf.file)form.append("current_pdf",state.pdf.file,state.pdf.name||state.pdf.file.name||"current.pdf");
    const response=await fetch("/api/admin/backup",{method:"POST",body:form});
    if(!response.ok){
      let detail=`HTTP ${response.status}`;
      // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
      try{const payload=await response.json();detail=payload.detail||detail}catch{}
      throw new Error(detail);
    }
    const blob=await response.blob();
    const disposition=response.headers.get("content-disposition")||"";
    // eslint-disable-next-line no-useless-escape -- SA-14: preserve legacy matching/serialization until dedicated text fixtures cover it.
    const match=disposition.match(/filename\*?=(?:UTF-8''|\")?([^\";]+)/i);
    // eslint-disable-next-line no-useless-escape -- SA-14: preserve legacy matching/serialization until dedicated text fixtures cover it.
    const filename=decodeURIComponent((match?.[1]||`derridai-full-backup-${new Date().toISOString().slice(0,10)}.zip`).replace(/^\"|\"$/g,""));
    const url=URL.createObjectURL(blob);
    const anchor=document.createElement("a");
    anchor.href=url;anchor.download=filename;document.body.appendChild(anchor);anchor.click();anchor.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    toast(`Full backup created · ${(blob.size/1024/1024).toFixed(1)} MB`);
  }catch(error){
    toast(`Backup failed: ${error.message}`);
  }finally{
    const current=document.querySelector("#downloadFullBackup");
    if(current){current.disabled=false;current.textContent="Download full backup"}
  }
}
async function restoreFullBackup(file,{confirmed=false}={}){
  if(!file)return;
  const activeJobs=state.jobs.filter(job=>["queued","running","cancelling"].includes(job.status));
  if(activeJobs.length)return toast("Cancel or wait for all background operations before restoring a backup.");
  if(!confirmed&&!await openMessageModal({title:"Restore full DerridAI backup?",message:"This replaces the current browser workspace and every collection in the active Chroma database. The restore is validated first and Chroma uses a rollback snapshot if restoration fails.",tone:"danger",confirmLabel:"Restore backup",cancelLabel:"Cancel"}))return;
  const button=document.querySelector("#restoreFullBackup");
  if(button){button.disabled=true;button.textContent="Restoring…"}
  try{
    const form=new FormData();form.append("backup",file,file.name);
    const response=await fetch("/api/admin/restore",{method:"POST",body:form});
    let payload;
    try{payload=await response.json()}catch{payload=null}
    if(!response.ok)throw new Error(payload?.detail||`HTTP ${response.status}`);
    const workspace=payload?.workspace;
    if(!workspace||!Array.isArray(workspace.files)||!workspace.prefs||typeof workspace.prefs!=="object")throw new Error("Backup restore returned an invalid workspace.");

    await deleteWorkspaceDatabase();
    state.storageReady=false;
    for(const saved of workspace.files){
      if(!saved?.id||!Array.isArray(saved.records))continue;
      await idbPut("files",{
        ...saved,
        dirty:Array.isArray(saved.dirty)?saved.dirty:[],
        errors:Array.isArray(saved.errors)?saved.errors:[],
      });
    }
    await idbPut("prefs",{...workspace.prefs,key:"workspace"});

    if(payload.pdf_available){
      const pdfResponse=await fetch("/api/admin/restore/current-pdf");
      if(pdfResponse.ok){
        const blob=await pdfResponse.blob();
        const meta=payload.pdf?.metadata||{};
        await idbPut("assets",{
          key:"current_pdf",
          blob,
          name:payload.pdf?.filename||meta.name||"restored.pdf",
          title:meta.title||"",
          author:meta.author||"",
          page:Math.max(1,Number(meta.page)||1),
          rotation:Number(meta.rotation||0)%360,
          text:String(meta.text||""),
          search:String(meta.search||""),
          relatedSearch:String(meta.relatedSearch||""),
          extractionSource:String(meta.extractionSource||""),
          extractError:String(meta.extractError||""),
          saved_at:new Date().toISOString(),
        });
      }
    }
    toast(`Restore complete · ${payload.chroma?.count||0} Chroma collections restored`);
    setTimeout(()=>location.reload(),500);
  }catch(error){
    toast(`Restore failed: ${error.message}`);
    const current=document.querySelector("#restoreFullBackup");
    if(current){current.disabled=false;current.textContent="Load from backup"}
  }
}

async function syncResearcherProviderProfiles(){
  const approved=providerProfiles().filter(profile=>profile.researcher_enabled).map(profile=>({...profile}));
  const result=await api("/api/system/researcher-providers",{method:"PUT",body:JSON.stringify({profiles:approved})});
  state.researcherProviderProfiles=result.profiles||[];
}
async function renderResponseCache(main){
  showViewLoading(main,"Loading response cache","Reading cached RAG responses…");
  try{await refreshStores()}catch(error){console.warn("Could not refresh store metadata",error)}
  let payload;
  try{
    payload=await api("/api/response-cache/records?limit=100&offset=0");
  }catch(error){
    main.innerHTML=`<div class="info error"><b>Could not read response cache.</b><span>${esc(error.message||String(error))}</span></div>`;
    return;
  }
  const cache=responseCacheStore();
  const count=Number(payload.total??payload.count??0);
  const records=Array.isArray(payload.records)?payload.records:[];
  const exists=Boolean(payload.exists||cache);
  main.innerHTML=`<div class="response-cache-page">
    <section class="card response-cache-overview">
      <div class="cardhead"><div><b>RAG response cache</b><div class="note">System cache only. This collection is intentionally excluded from corpus Vector Stores, corpus DB counts, language mirroring, and RAG source selection.</div></div><div class="tools"><button class="btn" id="cacheFaq">${icon("books")}Open Response Library</button>${exists?'<button class="btn danger" id="clearResponseCache">Clear cache</button>':""}</div></div>
      <div class="dashboard-kpis response-cache-kpis"><div class="dash-kpi"><span>Cached responses</span><strong>${count.toLocaleString()}</strong></div><div class="dash-kpi"><span>Collection</span><strong>${exists?"_response_cache":"Not created"}</strong></div><div class="dash-kpi"><span>Embedding</span><strong>${esc(cache?.embedding_model||"system-managed")}</strong></div></div>
      <div class="info">Each cache record stores the original RAG query, instructions, run parameters, answer, evidence, retrieval diagnostics, timings, and all saved LLM grading runs.</div>
    </section>
    <section class="card"><div class="cardhead"><div><b>Recent cached responses</b><div class="note">Latest 100 response-cache entries. Use Response Library for full answer/evidence browsing and re-runs.</div></div></div>
      <div class="tablewrap"><table><thead><tr><th>Created</th><th>Question</th><th>Generation</th><th>Evidence</th><th>Grades</th><th></th></tr></thead><tbody>${records.map((record,index)=>`<tr><td>${esc(formatTimestamp(record.created_at))}</td><td>${esc(record.question||"")}</td><td>${esc(record.provider||"")} · ${esc(record.model||"")}</td><td>${Number(record.evidence_count||0)}</td><td>${Array.isArray(record.grades)?record.grades.length:0}</td><td><button class="btn tiny" data-cache-faq="${index}">Open in Response Library</button></td></tr>`).join("")||'<tr><td colspan="6" class="note">No cached responses yet.</td></tr>'}</tbody></table></div>
    </section>
  </div>`;
  main.querySelector("#cacheFaq")?.addEventListener("click",()=>navigateTo("faq"));
  main.querySelectorAll("[data-cache-faq]").forEach(button=>button.onclick=()=>{
    state.faqSearch=records[+button.dataset.cacheFaq]?.question||"";
    state.faqPage=1;persistPrefs();navigateTo("faq");
  });
  main.querySelector("#clearResponseCache")?.addEventListener("click",async()=>{
    const approved=await openMessageModal({title:"Clear RAG response cache?",message:`Delete all ${count.toLocaleString()} cached RAG responses and saved grades? Corpus vector databases are not affected.`,tone:"danger",confirmLabel:"Clear response cache",cancelLabel:"Cancel"});
    if(!approved)return;
    try{
      await api("/api/stores/_response_cache",{method:"DELETE"});
      await refreshStores();renderResponseCache(main);toast("Response cache cleared");
    }catch(error){toast(`Could not clear response cache: ${error.message}`)}
  });
}

async function checkHealth(){
  try{
    state.health=await api("/api/health");
    ensureProviderProfiles();
    await refreshProviderStatuses();
  }catch(error){
    state.health={ok:false,error:error.message};
    state.providerStatuses={};
    state.llmStatus={
      provider:defaultProviderProfile()?.type||"ollama",
      available:false,
      models:[],
      error:error.message,
    };
  }
  updateSystemCard();
  if(state.health?.chroma?.available){
    try{
      await refreshStores();
      if(isResearcher()&&state.activeStore)await refreshStoreWorks(true);
      persistPrefs();
      const active=document.activeElement;
      const userIsEditing=active&&active!==document.body&&["INPUT","TEXTAREA","SELECT"].includes(active.tagName);
      if(!userIsEditing){shell();renderView()}
    }catch(error){console.warn("Initial Chroma collection refresh failed",error)}
  }
}




function translatedNavLabel(item){
  const keys={home:"nav.dashboard",list:"nav.records",record:"nav.record",works:"nav.works",global:"nav.search",annotations:"nav.annotations",pdf:"nav.pdf",compare:"nav.compare",vector:"nav.vector",rag:"nav.rag",faq:"nav.faq",responsecache:"nav.cache",providers:"nav.providers",config:"nav.config"};
  return keys[item.id]?tr(keys[item.id],item.label):item.label;
}
function translatedSectionLabel(section){
  const keys={Overview:"section.overview",Corpus:"section.corpus",Research:"section.research",Tools:"section.tools",System:"section.system"};
  return keys[section]?tr(keys[section],section):section;
}
function getShellSnapshot(){
  const ctx=currentContext();
  const totalLoaded=allRows().length;
  const flagged=needsReviewItems().length;
  const pending=state.activeStore?pendingUpsertRows().length:0;
  const corpusStores=recordStores();
  const dbRecords=corpusStores.reduce((sum,store)=>sum+(Number(store.count)||0),0);
  const cacheCount=Number(responseCacheStore()?.count||0);
  const activeJobs=state.jobs.filter(job=>["queued","running","cancelling"].includes(job.status)).length;
  return {
    view:state.view,
    sidebarCollapsed:state.sidebarCollapsed,
    files:state.files.map(file=>describeRecordsFile(file,state.activeFileId)),
    context:ctx,
    totalLoaded,
    flagged,
    pending,
    activeJobs,
    corpusStoreCount:corpusStores.length,
    dbRecords,
    cacheCount,
    hasCorpusDb:hasCorpusDb(),
    dbUnavailableReason:dbUnavailableReason(),
    activeStore:state.activeStore,
    canEdit:canUse("editLocalRecords")&&state.view==="record"&&Boolean(selectedRecord()),
    canGoBack:state.navHistory.length>0,
    canGoForward:state.navForward.length>0,
    backLabel:state.navHistory.length?viewLabel(state.navHistory[state.navHistory.length-1].view):"",
    forwardLabel:state.navForward.length?viewLabel(state.navForward[state.navForward.length-1].view):"",
    selectedEvidenceCount:selectedEvidenceEntries().length,
    systemHtml:systemCardHtml(),
    nav:getNavItems(),
  };
}
// Navigation membership depends only on the signed-in user, the static view list,
// and translations, never on workspace/bootstrap state. The Vue shell calls this as
// soon as a user exists so the menu is complete before the slow runtime bootstrap.
function getNavItems(){
  return viewConfig.filter(item=>canAccessPage(item.id)).map(item=>({
    ...item,
    label:item.id==="home"?tr("nav.home","Home"):(isResearcher()&&item.id==="vector"?tr("research.corpus_search","Corpus search"):translatedNavLabel(item)),
    section:translatedSectionLabel(item.section),
    disabledReason:viewDisabledReason(item.id),
  }));
}

function toggleSidebar(){
  state.sidebarCollapsed=!state.sidebarCollapsed;
  persistPrefs();
  shell();
}
function activateFile(fileId){
  if(["list","record"].includes(state.view)){
    state.activeFileId=fileId;
    persistPrefs();
    syncUrl({replace:true});
    shell();
    renderView();
  }else navigateTo("list",{fileId});
}
function triggerImport(fileList){return canUse("manageCorpus")?importFiles(fileList):toast("Your role does not have permission to load corpus files.")}
function triggerMerge(){return canUse("manageCorpus")?openMergeDialog():toast("Your role does not have permission to merge corpus files.")}
function triggerSubset(){return canUse("manageCorpus")?openSubsetBuilder():toast("Your role does not have permission to create subsets.")}
function triggerBulkEdit(){return canUse("editLocalRecords")?openBulkFieldEditor():toast("Your role does not have permission to edit records.")}
function triggerOcrClean(){return canUse("editLocalRecords")?openOcrCleanupDialog():toast("Your role does not have permission to edit records.")}
function triggerReviewFlagged(){return canUse("editLocalRecords")?openTouchup(needsReviewItems()):toast("Your role does not have permission to review records.")}
function triggerAutoImproveFlagged(){return canUse("editLocalRecords")?openTouchup(needsReviewItems(),"auto"):toast("Your role does not have permission to modify records.")}
function triggerUpsertQueue(){return canUse("manageCorpus")?openUpsertQueue():toast("Your role does not have permission to manage corpus databases.")}
function triggerOperations(){return navigateTo("home")}
function triggerExport(){return canUse("manageCorpus")?exportMenu():toast("Your role does not have permission to export corpus data.")}
function triggerEdit(){return canUse("editLocalRecords")?openEditor():toast("Your role does not have permission to edit records.")}
function triggerBack(){return goBack()}
function triggerForward(){return goForward()}
/**
 * Navigate the runtime and, when supplied, preserve an explicit native URL.
 * @param {string} view
 * @param {string} [href=""]
 */
function navigateView(view,href=""){return navigateTo(view,{href})}
function getProviderProfilesForUi(){return cloneAuditValue(providerProfiles())}
function getProviderRequestConfigForUi(profileId,{textReview=false}={}){
  const profile=providerProfile(profileId);
  return profile?cloneAuditValue(providerRequestConfig(profile,{textReview})):null;
}
function getWarmOnStartForUi(){return state.appConfig.warm_default_provider_on_start===true}
function setWarmOnStartForUi(value){state.appConfig.warm_default_provider_on_start=Boolean(value);persistPrefs();return getWarmOnStartForUi()}
function getDefaultProviderProfileId(){return state.appConfig.default_provider_profile||defaultProviderProfile()?.id||""}
function getProviderStatusesForUi(){return cloneAuditValue(state.providerStatuses||{})}
function getProviderWarmupsForUi(){return cloneAuditValue(state.providerWarmups||{})}
function saveProviderProfilesForUi(profiles=[]){
  if(!Array.isArray(profiles)||!profiles.length)throw new Error("At least one provider profile is required.");
  state.appConfig.provider_profiles=cloneAuditValue(profiles);
  if(!state.appConfig.provider_profiles.some(profile=>profile.id===state.appConfig.default_provider_profile))state.appConfig.default_provider_profile=state.appConfig.provider_profiles[0].id;
  const defaultProfile=defaultProviderProfile();
  if(defaultProfile)state.appConfig.chat_provider=defaultProfile.type;
  persistPrefs();
  return getProviderProfilesForUi();
}
function addProviderProfileForUi(type){
  ensureProviderProfiles();
  const profile=type==="openai"
    ? {id:`openai-${uid()}`,name:"New OpenAI-compatible / FreeLLM",type:"openai",base_url:"http://host.docker.internal:3001/v1",model:"auto",model_mode:"auto",model_kind:"any",api_key:"",max_concurrent_requests:32,num_predict:4096,temperature:0,top_p:1,seed:"",extra_options:"{}"}
    : {id:`ollama-${uid()}`,name:"New Ollama",type:"ollama",base_url:"http://host.docker.internal:11434",model:"gemma4:e2b",model_mode:"manual",model_kind:"any",api_key:"",max_concurrent_requests:1,num_ctx:16384,metadata_num_predict:768,num_predict:4096,think:"false",temperature:0,top_k:0,top_p:1,min_p:"",repeat_penalty:1.1,seed:"",mirostat:0,mirostat_eta:"",mirostat_tau:"",keep_alive:"10m",extra_options:"{}"};
  state.appConfig.provider_profiles=[...providerProfiles(),profile];
  persistPrefs();
  return cloneAuditValue(profile);
}
function removeProviderProfileForUi(profileId){
  if(providerProfiles().length<=1)throw new Error("At least one LLM provider profile is required.");
  state.appConfig.provider_profiles=providerProfiles().filter(profile=>profile.id!==profileId);
  if(state.appConfig.default_provider_profile===profileId)state.appConfig.default_provider_profile=state.appConfig.provider_profiles[0]?.id||"";
  persistPrefs();
  return getProviderProfilesForUi();
}
function setDefaultProviderProfileForUi(profileId){
  if(!providerProfiles().some(profile=>profile.id===profileId))throw new Error("The selected provider profile is no longer available.");
  state.appConfig.default_provider_profile=profileId;
  const profile=providerProfile(profileId);if(profile)state.appConfig.chat_provider=profile.type;
  persistPrefs();
}
async function testProviderProfileForUi(profileId){
  const profile=providerProfile(profileId);if(!profile)throw new Error("The selected provider profile is no longer available.");
  const result=await api("/api/llm/status",{method:"POST",body:JSON.stringify({provider:profile.type,base_url:profile.base_url,api_key:profile.type==="openai"?profile.api_key:null})});
  state.providerStatuses[profile.id]=result;
  return cloneAuditValue(result);
}
async function warmProviderProfileForUi(profileId){
  const profile=providerProfile(profileId);if(!profile)throw new Error("The selected provider profile is no longer available.");
  await warmupProviderProfile(profile.id);
  return cloneAuditValue(state.providerWarmups?.[profile.id]||{});
}
function closeWorkspaceFile(fileId){return closeFile(fileId)}
function notifyToast(message,options={}){return toast(message,options)}
function registerExternalJob(job){
  if(!job?.id)return;
  state.jobs=[job,...state.jobs.filter(existing=>existing.id!==job.id)];
  syncJobProgressToasts();startJobPolling();shell();
}

let chartTooltip=null;
function ensureChartTooltip(){
  if(chartTooltip?.isConnected)return chartTooltip;
  chartTooltip=document.createElement("div");chartTooltip.className="chart-hover-tooltip";document.body.appendChild(chartTooltip);return chartTooltip;
}
document.addEventListener("pointermove",event=>{
  const target=event.target.closest?.("[data-chart-tip]");
  if(!target){if(chartTooltip)chartTooltip.classList.remove("show");return}
  const tip=ensureChartTooltip();tip.textContent=target.dataset.chartTip||"";tip.style.left=`${Math.min(window.innerWidth-280,event.clientX+14)}px`;tip.style.top=`${Math.max(8,event.clientY+14)}px`;tip.classList.add("show");
});

window.addEventListener("dragover",e=>e.preventDefault());
window.addEventListener("drop",e=>{if(e.dataTransfer?.files?.length){e.preventDefault();if(!isResearcher())importFiles([...e.dataTransfer.files].filter(f=>/\.(jsonl|ndjson|json)$/i.test(f.name)));}});
document.addEventListener("click",event=>{
  const resultButton=event.target.closest?.("[data-toast-open-result],[data-job-result],[data-rag-job-result],[data-recent-rag-result]");
  if(!resultButton)return;
  const jobId=resultButton.dataset.toastOpenResult||resultButton.dataset.jobResult||resultButton.dataset.ragJobResult||resultButton.dataset.recentRagResult;
  if(!jobId)return;
  event.preventDefault();
  event.stopImmediatePropagation();
  resultButton.disabled=true;
  const original=resultButton.innerHTML;
  resultButton.textContent="Opening…";
  void openJobResults(jobId).catch(error=>openMessageModal({title:"Could not open operation result",message:error.message||String(error),tone:"danger"})).finally(()=>{if(resultButton.isConnected){resultButton.disabled=false;resultButton.innerHTML=original}});
},{capture:true});

document.addEventListener("click",event=>{
  const loadedButton=event.target.closest("[data-copy-row-key]");
  if(loadedButton){
    event.stopPropagation();
    const item=reviewItemFromKey(loadedButton.dataset.copyRowKey);
    if(item)copyJsonToClipboard(item.file.records[item.index],item.record.record_id||"record");
    else toast("The source record is no longer loaded");
    return;
  }
  const citeButton=event.target.closest("[data-cite-row-key]");
  if(citeButton){
    event.stopPropagation();
    const item=reviewItemFromKey(citeButton.dataset.citeRowKey);
    if(item)copyCitation(item.record,citeButton.dataset.citeKind||"inline");
    return;
  }
  const dbCite=event.target.closest("[data-admin-db-cite],[data-r-cite]");
  if(dbCite){
    event.preventDefault();event.stopPropagation();
    const id=String(dbCite.dataset.adminDbId||dbCite.dataset.rId||"");
    const result=(state.storeSearchResults||[]).find(item=>String(item.id||item.record?._chroma_id||item.record?.record_id||"")===id);
    const record=result?.record||(state.storeRecords||[]).find(item=>String(item._chroma_id||item.record_id||"")===id);
    if(record)copyCitation(record,dbCite.dataset.adminDbCite||dbCite.dataset.rCite||"inline");
    else toast("Citation source is no longer available",{tone:"warn"});
    return;
  }
  const evidenceButton=event.target.closest("[data-toggle-workspace-evidence]");
  if(evidenceButton){
    event.stopPropagation();
    const item=reviewItemFromKey(evidenceButton.dataset.toggleWorkspaceEvidence);
    if(item){toggleWorkspaceEvidence(item.file,item.index);renderView()}
    return;
  }
  const storeButton=event.target.closest("[data-copy-store-record]");
  if(storeButton){
    event.stopPropagation();
    const record=state.storeRecords.find(item=>String(item._chroma_id||"")===String(storeButton.dataset.copyStoreRecord||""));
    if(record){const copy={...record};delete copy._chroma_id;copyJsonToClipboard(copy,copy.record_id||"Chroma record")}
  }
});
let researcherPolicy={ready:false,blocked:new Set(),contextual:[]};
let researcherPolicyToastAt=0;
const researcherLeet={"0":"o","1":"i","3":"e","4":"a","5":"s","7":"t","@":"a","$":"s"};
function normalizeResearcherToken(value){
  const text=String(value||"").normalize("NFKC").replace(/[013457@$]/g,ch=>researcherLeet[ch]||ch).toLocaleLowerCase();
  return text.replace(/(?<=\w)[._*~-]+(?=\w)/g,"");
}
async function researcherTokenDigest(value){
  if(!globalThis.crypto?.subtle)return "";
  const buf=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(normalizeResearcherToken(value)));
  return Array.from(new Uint8Array(buf),b=>b.toString(16).padStart(2,"0")).join("");
}
async function refreshResearcherContentPolicy(){
  if(!state.userContext){researcherPolicy={ready:false,blocked:new Set(),contextual:[]};return}
  try{
    const data=await api("/api/i18n/content-policy");
    researcherPolicy={
      ready:Boolean(data?.ready),
      blocked:new Set(Array.isArray(data?.blocked_term_hashes)?data.blocked_term_hashes:[]),
      contextual:Array.isArray(data?.contextual)?data.contextual:[],
    };
  }catch{
    researcherPolicy={ready:false,blocked:new Set(),contextual:[]};
  }
}
async function filterResearcherInputElement(target){
  if(!isResearcher()||!(target instanceof HTMLElement)||!researcherPolicy.ready)return;
  const acceptsText=target instanceof HTMLTextAreaElement||(target instanceof HTMLInputElement&&["text","search","url","email","tel"].includes(target.type))||target.isContentEditable;
  if(!acceptsText)return;
  const original=target.isContentEditable?target.textContent||"":target.value||"";
  const words=[...original.matchAll(/[\w'’]+/g)];
  const remove=[];
  for(const match of words){
    const raw=match[0];
    const digest=await researcherTokenDigest(raw);
    if(!digest)continue;
    if(researcherPolicy.blocked.has(digest)){remove.push(raw);continue}
    const rule=researcherPolicy.contextual.find(item=>item.term_hash===digest);
    if(!rule)continue;
    if(rule.allow_title_case&&raw===raw.charAt(0).toUpperCase()+raw.slice(1).toLowerCase()&&raw!==raw.toLowerCase())continue;
    const index=words.indexOf(match);
    const surrounding=words.slice(Math.max(0,index-3),index+4).map(item=>normalizeResearcherToken(item[0])).join(" ");
    if((rule.allow_if_surrounding||[]).some(marker=>surrounding.includes(normalizeResearcherToken(marker))))continue;
    const before=normalizeResearcherToken(original.slice(Math.max(0,match.index-20),match.index));
    if((rule.allow_if_before_markers||[]).some(marker=>before.includes(normalizeResearcherToken(marker))))continue;
    remove.push(raw);
  }
  if(!remove.length)return;
  let filtered=original;
  for(const token of remove)filtered=filtered.replace(new RegExp(`\\b${token.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")}\\b`),"");
  filtered=filtered.replace(/ {2,}/g," ");
  if(target.isContentEditable)target.textContent=filtered;else target.value=filtered;
  target.dispatchEvent(new Event("change",{bubbles:true}));
  const now=Date.now();if(now-researcherPolicyToastAt>1200){researcherPolicyToastAt=now;toast(tr("content_filter.warning","That language is not permitted for researcher accounts. The flagged term was removed."),{tone:"warn"})}
}
document.addEventListener("input",event=>{void filterResearcherInputElement(event.target)},true);

window.addEventListener("popstate",()=>{
  applyUrlState();
  persistPrefs();
  shell();
  renderView();
});

let metadataSearchDelegationWired=false;
function wireMetadataSearchDelegation(){if(metadataSearchDelegationWired)return;metadataSearchDelegationWired=true;document.addEventListener("click",event=>{const button=event.target instanceof Element?event.target.closest("[data-meta-search-field][data-meta-search-value]"):null;if(!button)return;if(button.closest("#main")){event.preventDefault();event.stopPropagation();searchByMetadata(button.dataset.metaSearchField,button.dataset.metaSearchValue,{contains:button.dataset.metaSearchContains==="true"})}},true)}
let tabScrollPreservationWired=false;
function wireTabScrollPreservation(){
  if(tabScrollPreservationWired)return;
  tabScrollPreservationWired=true;
  const selector=['[role="tab"]','.view-tab','.db-browser-tab','.search-mode-tabs button','.dashboard-search-tabs button','.annotation-tabs button','.annotations-tabs button','.record-view-tabs button','.compare-tabs button','.config-tabs button'].join(',');
  const arm=target=>{
    if(!target)return;
    const top=window.scrollY,left=window.scrollX,main=document.querySelector('#main');
    let cancelled=false,quietTimer=null,stopTimer=null,observer=null;
    const restore=()=>{if(cancelled)return;if(Math.abs(window.scrollY-top)>1||Math.abs(window.scrollX-left)>1)window.scrollTo({top,left,behavior:'auto'})};
    const stop=()=>{observer?.disconnect();if(quietTimer)clearTimeout(quietTimer);if(stopTimer)clearTimeout(stopTimer);window.removeEventListener('wheel',cancel);window.removeEventListener('touchmove',cancel)};
    const cancel=()=>{cancelled=true;stop()};
    observer=main?new MutationObserver(()=>{restore();if(quietTimer)clearTimeout(quietTimer);quietTimer=setTimeout(stop,140)}):null;
    observer?.observe(main,{childList:true,subtree:true});
    window.addEventListener('wheel',cancel,{passive:true,once:true});window.addEventListener('touchmove',cancel,{passive:true,once:true});
    requestAnimationFrame(restore);stopTimer=setTimeout(stop,1200);
  };
  document.addEventListener('pointerdown',event=>{const target=event.target instanceof Element?event.target.closest(selector):null;if(target)arm(target)},true);
  document.addEventListener('keydown',event=>{if(!['Enter',' '].includes(event.key))return;const target=event.target instanceof Element?event.target.closest(selector):null;if(target)arm(target)},true);
}

async function bootstrapRuntime(){
  wireTabScrollPreservation();wireMetadataSearchDelegation();
  await restoreWorkspace();
  try{
    if(!state.appConfig.ui_color_scheme)state.appConfig.ui_color_scheme=localStorage.getItem("derridai.ui.scheme")||"system";
    if(!state.appConfig.ui_contrast)state.appConfig.ui_contrast=localStorage.getItem("derridai.ui.contrast")||"system";
  }catch{ /* localStorage can be blocked */ }
  applyAppearance({
    ui_color_theme:state.appConfig.ui_color_theme,
    ui_color_scheme:state.appConfig.ui_color_scheme||"system",
    ui_contrast:state.appConfig.ui_contrast||"system",
  });
  try{
    const providerData=await api("/api/system/researcher-providers");
    state.researcherProviderProfiles=Array.isArray(providerData.profiles)?providerData.profiles:[];
  }catch(error){
    console.warn("Could not load researcher provider profiles",error);
    state.researcherProviderProfiles=[];
  }
  if(isResearcher()){
    state.files=[];
    state.activeFileId=null;
    state.selected={};
    state.reviewSelection=new Set();
    if(!["home","rag","vector","works","global","record","compare","annotations","config"].includes(state.view))state.view="home";
  }
  applyUrlState();
  if(!canAccessPage(state.view))state.view="home";
  shell();
  // A native Vue route may be active without #main. In that case bootstrap
  // background health/job state only; RuntimeSurface will render when mounted.
  if(document.querySelector("#main"))renderView();
  await checkHealth();
  // One discovery request on startup is not a polling loop. Polling begins only
  // if this request finds an active job and then runs every four seconds.
  await refreshJobs({rerender:false});
  if(state.view==="home"&&document.querySelector("#main"))renderDashboard(document.querySelector("#main"));
  startJobPolling();
  if(!isResearcher()&&state.appConfig.warm_default_provider_on_start===true)warmupConfiguredLlm();
}



// 0.31.0 native Research bridge. The Vue Research workspace owns presentation,
// while this compatibility layer continues to own corpus/provider/job state and
// the sparse API contracts introduced in 0.30.11. Keep the bridge intentionally
// operation-specific so native components never need to receive credentials,
// full corpus records, or unrelated runtime state.
function researchProfileForUi(profile){
  if(!profile)return null;
  const keys=[
    "id","name","type","model","model_mode","model_kind","max_concurrent_requests",
    "num_ctx","num_predict","think","temperature","top_k","top_p","min_p",
    "repeat_penalty","seed","mirostat","mirostat_eta","mirostat_tau","keep_alive",
    "extra_options",
  ];
  return Object.fromEntries(keys.filter(key=>profile[key]!==undefined).map(key=>[key,cloneAuditValue(profile[key])]));
}
function researchEvidenceForUi(item){
  if(!item)return null;
  return {
    key:item.key,
    kind:item.kind,
    collection:item.collection||null,
    chroma_id:item.chroma_id||null,
    record_id:item.record_id||"",
    work:item.work||"",
    page_start:item.page_start??null,
    page_end:item.page_end??null,
    speaker:item.speaker||null,
    position_holder:item.position_holder||null,
    stance:item.stance||null,
    discourse_role:item.discourse_role||null,
    target:item.target||null,
    proposition_status:item.proposition_status||null,
    inline_citation:item.inline_citation||null,
    text_preview:item.text_preview||"",
    label:item.label||"",
  };
}
function researchJobForUi(job){
  if(!job)return null;
  const result=job.result&&typeof job.result==="object"?job.result:null;
  return {
    id:job.id,
    type:job.type,
    status:job.status,
    stage:job.stage||"",
    stage_detail:job.stage_detail||"",
    prompt:job.prompt||result?.prompt||"",
    provider:job.provider||result?.provider||"",
    provider_profile_id:job.provider_profile_id||null,
    model:job.model||result?.model||"",
    source_collection:job.source_collection||"",
    owner:job.owner||"",
    created_at:job.created_at||null,
    started_at:job.started_at||null,
    finished_at:job.finished_at||null,
    updated_at:job.updated_at||null,
    completed:Number(job.completed||0),
    total:Number(job.total||0),
    cancel_requested:Boolean(job.cancel_requested),
    fatal_error:job.fatal_error||null,
    request:job.request?cloneAuditValue(job.request):null,
    result:result?cloneAuditValue(result):null,
    events:Array.isArray(job.events)?cloneAuditValue(job.events):[],
  };
}
function researchConfigForUi(){
  return cloneAuditValue(state.ragConfig||{});
}
async function getResearchWorkspaceSnapshot({refresh=false}={}){
  if(refresh){
    try{await refreshStores()}catch(error){console.warn("Could not refresh Research collections",error)}
    if(hasCapability("rag.jobs.own")||!isResearcher())await refreshJobs({rerender:false});
  }
  const corpus=recordStores();
  const usable=corpus.filter(store=>Number(store.count||0)>0);
  const evidence=selectedEvidenceEntries().map(researchEvidenceForUi).filter(item=>item!==null);
  if(!evidence.length)state.ragConfig.skip_retrieval=false;
  if(evidence.length&&!hasCorpusDb())state.ragConfig.skip_retrieval=true;
  if(!state.ragConfig.source_collection||!corpus.some(store=>store.name===state.ragConfig.source_collection)){
    state.ragConfig.source_collection=(usable.find(store=>store.collection_role==="primary")||usable[0]||corpus[0]||{}).name||"";
  }
  const profiles=providerProfiles();
  if(profiles.length&&!profiles.some(profile=>profile.id===state.ragConfig.provider_profile_id)){
    state.ragConfig.provider_profile_id=(profiles.find(profile=>profile.id===state.appConfig.default_provider_profile)||profiles[0])?.id||"";
  }
  if(profiles.length&&!profiles.some(profile=>profile.id===state.ragConfig.auto_grade_provider_profile_id)){
    state.ragConfig.auto_grade_provider_profile_id=(profiles.find(profile=>profile.id!==state.ragConfig.provider_profile_id)||profiles[0])?.id||"";
  }
  persistPrefs();
  return {
    config:researchConfigForUi(),
    stores:corpus.map(store=>({
      name:store.name,
      count:Number(store.count||0),
      collection_role:store.collection_role||"general",
      embedding_model:store.embedding_model||store.metadata?.embedding_model||"",
    })),
    profiles:profiles.map(researchProfileForUi).filter(Boolean),
    selected_evidence:evidence,
    jobs:(!isResearcher()||hasCapability("rag.jobs.own"))?(state.jobs||[]).filter(job=>job.type==="rag").map(researchJobForUi).filter(Boolean):[],
    history:cloneAuditValue(state.ragConfig.history||[]),
    can_run:hasCapability("rag.run"),
    can_select_evidence:hasCapability("evidence.select"),
    can_manage_jobs:!isResearcher()||hasCapability("rag.jobs.own"),
    is_researcher:isResearcher(),
  };
}
function updateResearchConfig(patch={}){
  const allowed=new Set([
    "source_collection","locales","search_types","k","fetch_k","lambda_mult","rrf_k",
    "rerank_top_n","reranker","cross_encoder_model","query_decomposition",
    "query_decomposition_num_predict","response_language","evidence_record_char_limit",
    "evidence_total_char_limit","bind_citations","include_works_cited","auto_grade",
    "auto_grade_provider_profile_id","provider_profile_id","skip_retrieval","prompt","instructions",
  ]);
  for(const [key,value] of Object.entries(patch||{}))if(allowed.has(key))state.ragConfig[key]=cloneAuditValue(value);
  if(!selectedEvidenceEntries().length)state.ragConfig.skip_retrieval=false;
  persistPrefs();shellRefreshHook?.();
  return researchConfigForUi();
}
function removeResearchEvidence(key){
  if(!hasCapability("evidence.select"))throw new Error(tr("permissions.evidence_denied","Your role cannot change selected evidence."));
  setEvidence(String(key||""),null,false);
  if(!selectedEvidenceEntries().length)state.ragConfig.skip_retrieval=false;
  persistPrefs();
  return selectedEvidenceEntries().map(researchEvidenceForUi).filter(item=>item!==null);
}
function clearResearchEvidence(){
  if(!hasCapability("evidence.select"))throw new Error(tr("permissions.evidence_denied","Your role cannot change selected evidence."));
  clearSelectedEvidence();
  state.ragConfig.skip_retrieval=false;
  persistPrefs();
  return [];
}
async function discoverResearchModels(profileId){
  const profile=providerProfile(profileId);
  if(!profile)return [];
  if(isResearcher())return profile.model?[String(profile.model)]:[];
  try{
    const status=await api("/api/llm/status",{
      method:"POST",
      body:JSON.stringify({provider:profile.type||"ollama",base_url:profile.base_url||null,api_key:profile.type==="openai"?(profile.api_key||""):null}),
    });
    state.providerStatuses[profile.id]=status;
    return (status.models||[]).map(item=>String(item.name||"")).filter(Boolean);
  }catch(error){
    console.warn("Research model discovery failed",error);
    return profile.model?[String(profile.model)]:[];
  }
}
async function refreshResearchJobs(){
  if(isResearcher()&&!hasCapability("rag.jobs.own"))return [];
  await refreshJobs({rerender:false});
  return (state.jobs||[]).filter(job=>job.type==="rag").map(researchJobForUi).filter(Boolean);
}
async function getResearchJob(jobId){
  const job=await api(`/api/jobs/${encodeURIComponent(jobId)}`);
  const index=state.jobs.findIndex(item=>item.id===job.id);
  if(index>=0)state.jobs[index]={...state.jobs[index],...job};else state.jobs.unshift(job);
  return researchJobForUi(job);
}
async function cancelResearchJob(jobId){
  if(isResearcher()&&!hasCapability("rag.jobs.own"))throw new Error("Your role cannot manage Research jobs.");
  const job=await cancelBackgroundJob(jobId,{refresh:false});
  return researchJobForUi(job);
}
async function deleteResearchJob(jobId){
  if(isResearcher()&&!hasCapability("rag.jobs.own"))throw new Error("Your role cannot manage Research jobs.");
  await api(`/api/jobs/${encodeURIComponent(jobId)}`,{method:"DELETE"});
  pruneClientJobState(jobId);persistPrefs();shellRefreshHook?.();
  return true;
}
function generationFromProfile(profile){
  const cfg=providerRequestConfig(profile,{textReview:true});
  return cloneAuditValue(cfg?.ollama||{});
}
function finiteResearchNumber(value,fallback,{integer=false,min=-Infinity,max=Infinity}={}){
  if(value===null||value===undefined||value==="")return fallback;
  const parsed=integer?Number.parseInt(String(value),10):Number(value);
  if(!Number.isFinite(parsed))return fallback;
  return Math.min(max,Math.max(min,parsed));
}
function sanitizeResearchGeneration(input={}){
  const source=input&&typeof input==="object"&&!Array.isArray(input)?input:{};
  const out={};
  const specs={
    num_ctx:{integer:true,min:512,max:262144},num_predict:{integer:true,min:16,max:32768},
    temperature:{min:0,max:2},top_k:{integer:true,min:0,max:1000},top_p:{min:0,max:1},min_p:{min:0,max:1},
    repeat_penalty:{min:0,max:5},seed:{integer:true},mirostat:{integer:true,min:0,max:2},mirostat_eta:{min:0},mirostat_tau:{min:0},
  };
  for(const [key,spec] of Object.entries(specs)){
    const raw=source[key];
    if(raw===null||raw===undefined||raw==="")continue;
    const value=finiteResearchNumber(raw,null,spec);
    if(value!==null&&Number.isFinite(value))out[key]=value;
  }
  const think=source.think;
  if(typeof think==="boolean")out.think=think;
  else if(["low","medium","high"].includes(String(think||"").toLowerCase()))out.think=String(think).toLowerCase();
  else if(String(think||"").toLowerCase()==="true")out.think=true;
  else if(String(think||"").toLowerCase()==="false")out.think=false;
  if(source.keep_alive!==null&&source.keep_alive!==undefined&&String(source.keep_alive).trim())out.keep_alive=String(source.keep_alive).trim();
  if(Array.isArray(source.stop))out.stop=source.stop.map(item=>String(item)).filter(Boolean);
  let extra=source.extra_options;
  if(typeof extra==="string"){try{extra=JSON.parse(extra||"{}")}catch{extra={}}}
  out.extra_options=extra&&typeof extra==="object"&&!Array.isArray(extra)?extra:{};
  return out;
}
function normalizedResearchConfig(cfg={}){
  const locales=Array.isArray(cfg.locales)?[...new Set(cfg.locales.map(String).filter(value=>["en","fr"].includes(value)))]:["en","fr"];
  const searchTypes=Array.isArray(cfg.search_types)?[...new Set(cfg.search_types.map(String).filter(value=>["mmr","similarity","lexical"].includes(value)))]:["similarity","lexical","mmr"];
  const reranker=["cross_encoder","lexical","none"].includes(String(cfg.reranker||""))?String(cfg.reranker):"cross_encoder";
  const responseLanguage=["auto","en","fr"].includes(String(cfg.response_language||""))?String(cfg.response_language):"auto";
  return {
    ...cfg,
    k:finiteResearchNumber(cfg.k,64,{integer:true,min:1,max:500}),
    fetch_k:finiteResearchNumber(cfg.fetch_k,500,{integer:true,min:1,max:5000}),
    lambda_mult:finiteResearchNumber(cfg.lambda_mult,.7,{min:0,max:1}),
    rrf_k:finiteResearchNumber(cfg.rrf_k,60,{integer:true,min:1,max:10000}),
    rerank_top_n:finiteResearchNumber(cfg.rerank_top_n,24,{integer:true,min:1,max:500}),
    reranker,
    cross_encoder_model:String(cfg.cross_encoder_model||"cross-encoder/ms-marco-MiniLM-L-6-v2").trim()||"cross-encoder/ms-marco-MiniLM-L-6-v2",
    query_decomposition:Boolean(cfg.query_decomposition),
    query_decomposition_num_predict:finiteResearchNumber(cfg.query_decomposition_num_predict,768,{integer:true,min:64,max:8192}),
    response_language:responseLanguage,
    evidence_record_char_limit:finiteResearchNumber(cfg.evidence_record_char_limit,12000,{integer:true,min:500,max:100000}),
    evidence_total_char_limit:finiteResearchNumber(cfg.evidence_total_char_limit,120000,{integer:true,min:5000,max:1000000}),
    locales,
    search_types:searchTypes,
    bind_citations:cfg.bind_citations!==false,
    include_works_cited:cfg.include_works_cited!==false,
    auto_grade:Boolean(cfg.auto_grade),
    skip_retrieval:Boolean(cfg.skip_retrieval),
  };
}
async function startResearchRun(input={}){
  if(!hasCapability("rag.run"))throw new Error(tr("permissions.rag_denied","Your role cannot run Research pipelines."));
  const cfg=normalizedResearchConfig(updateResearchConfig(input.config||{}));
  updateResearchConfig({
    k:cfg.k,fetch_k:cfg.fetch_k,lambda_mult:cfg.lambda_mult,rrf_k:cfg.rrf_k,rerank_top_n:cfg.rerank_top_n,
    query_decomposition_num_predict:cfg.query_decomposition_num_predict,evidence_record_char_limit:cfg.evidence_record_char_limit,
    evidence_total_char_limit:cfg.evidence_total_char_limit,locales:cfg.locales,search_types:cfg.search_types,
  });
  const prompt=String(input.prompt??cfg.prompt??"").trim();
  const instructions=String(input.instructions??cfg.instructions??"").trim();
  if(!prompt)throw new Error("Enter a research question.");
  const selected=selectedEvidenceEntries();
  const skipRetrieval=Boolean(input.skip_retrieval??cfg.skip_retrieval);
  if(skipRetrieval&&!selected.length)throw new Error("Select at least one evidence record before using evidence-only mode.");
  if(!skipRetrieval&&!cfg.source_collection)throw new Error("Select a corpus database.");
  if(!skipRetrieval&&!(cfg.locales||[]).length)throw new Error("Select at least one document language.");
  if(!skipRetrieval&&!(cfg.search_types||[]).length)throw new Error("Select at least one retrieval route.");
  if(!skipRetrieval){
    const store=recordStores().find(item=>item.name===cfg.source_collection);
    if(!store)throw new Error("The selected corpus database is no longer available. Choose an existing database before running Research.");
    if(Number(store.count||0)<=0)throw new Error("The selected corpus database is empty. Add records before running Research.");
  }
  if(selected.length>500)throw new Error("Research supports at most 500 selected evidence records in one run.");
  const selectedPayload=selectedEvidencePayload();
  if(skipRetrieval&&selectedPayload.length!==selected.length)throw new Error("One or more selected evidence records are no longer available. Remove the stale selection and try again.");

  const profileId=String(input.provider_profile_id||cfg.provider_profile_id||state.appConfig.default_provider_profile||"");
  const profile=providerProfile(profileId);
  if(!profile)throw new Error("No LLM profile is available for Research.");
  const provider=["ollama","openai"].includes(String(profile.type||""))?String(profile.type):"";
  if(!provider)throw new Error("The selected LLM profile uses an unsupported provider. Update the profile before running Research.");
  const defaultModel=provider==="openai"&&profile.model_mode==="auto"?"auto":String(profile.model||"");
  const model=String(input.model||defaultModel).trim();
  if(!model)throw new Error("Select a generation model.");

  const baseGeneration=generationFromProfile(profile);
  const generation=sanitizeResearchGeneration({...baseGeneration,...(input.generation||{})});

  const gradeProfile=cfg.auto_grade?providerProfile(cfg.auto_grade_provider_profile_id||profile.id):null;
  if(cfg.auto_grade&&!gradeProfile)throw new Error("The selected auto-grade LLM profile is no longer available. Choose another grader or turn off auto-grading.");
  if(gradeProfile&&!["ollama","openai"].includes(String(gradeProfile.type||"")))throw new Error("The selected auto-grade profile uses an unsupported provider.");
  const gradeConfig=gradeProfile?providerRequestConfig(gradeProfile,{textReview:true}):null;
  state.ragConfig.prompt=prompt;
  state.ragConfig.instructions=instructions;
  state.ragConfig.provider_profile_id=profile.id;
  state.ragConfig.skip_retrieval=skipRetrieval;
  rememberRagPrompt(prompt,instructions,{source_collection:cfg.source_collection,provider,model});
  persistPrefs();

  const job=await api("/api/jobs/rag",{
    method:"POST",
    body:JSON.stringify({
      prompt,
      instructions:instructions||null,
      source_collection:cfg.source_collection||"",
      selected_evidence:selectedPayload,
      skip_retrieval:skipRetrieval,
      locales:cfg.locales,
      search_types:cfg.search_types,
      k:cfg.k,
      fetch_k:cfg.fetch_k,
      lambda_mult:cfg.lambda_mult,
      rrf_k:cfg.rrf_k,
      rerank_top_n:cfg.rerank_top_n,
      reranker:cfg.reranker,
      cross_encoder_model:cfg.cross_encoder_model,
      query_decomposition:cfg.query_decomposition,
      query_decomposition_num_predict:cfg.query_decomposition_num_predict,
      response_language:cfg.response_language,
      evidence_record_char_limit:cfg.evidence_record_char_limit,
      evidence_total_char_limit:cfg.evidence_total_char_limit,
      provider,
      model,
      base_url:isResearcher()?null:(profile.base_url||null),
      api_key:isResearcher()?null:(provider==="openai"?(profile.api_key||""):null),
      provider_profile_id:profile.id,
      max_concurrent_requests:Math.max(1,Math.min(64,Number(profile.max_concurrent_requests??(provider==="ollama"?1:32))||1)),
      generation,
      ollama_concurrency_limit:provider==="ollama"?Math.max(1,Math.min(32,Number(profile.max_concurrent_requests??state.appConfig.ollama_rag_concurrency??1)||1)):null,
      bind_citations:Boolean(cfg.bind_citations),
      include_works_cited:Boolean(cfg.include_works_cited),
      auto_grade:Boolean(cfg.auto_grade),
      auto_grade_provider:gradeConfig?.provider||null,
      auto_grade_model:gradeConfig?.model||null,
      auto_grade_base_url:isResearcher()?null:(gradeConfig?.base_url||null),
      auto_grade_api_key:isResearcher()?null:(gradeConfig?.api_key||null),
      auto_grade_provider_profile_id:gradeConfig?.provider_profile_id||null,
      auto_grade_generation:gradeConfig?.ollama?sanitizeResearchGeneration(gradeConfig.ollama):null,
    }),
  });
  state.jobs=[job,...state.jobs.filter(existing=>existing.id!==job.id)];
  rememberRagRun(job);persistPrefs();syncJobProgressToasts();startJobPolling();shellRefreshHook?.();
  toast(`Research started · ${providerDisplayName(profile)} · ${model}`,{tone:"success"});
  return researchJobForUi(job);
}
async function gradeResearchJob(jobId){
  const job=await api(`/api/jobs/${encodeURIComponent(jobId)}`);
  const result=job?.result;
  if(!result?.answer)throw new Error("This Research run has no completed answer to grade.");
  return gradeRagResponse({
    question:result.prompt||job.prompt||"",
    answer:result.answer||"",
    evidence:Array.isArray(result.evidence)?result.evidence:[],
    responseRecordId:result.response_cache?.record_id||null,
    generationProvider:result.provider||job.provider||null,
    generationModel:result.model||job.model||null,
  });
}
function prepareResearchRerun(job){
  const request=job?.request||job?.result?.rag_request||{};
  if(!request||typeof request!=="object")return researchConfigForUi();
  const keys=["source_collection","locales","search_types","k","fetch_k","lambda_mult","rrf_k","rerank_top_n","reranker","cross_encoder_model","query_decomposition","query_decomposition_num_predict","response_language","evidence_record_char_limit","evidence_total_char_limit","bind_citations","include_works_cited","auto_grade","auto_grade_provider_profile_id","provider_profile_id","skip_retrieval"];
  const patch=Object.fromEntries(keys.filter(key=>request[key]!==undefined).map(key=>[key,request[key]]));
  patch.prompt=request.prompt||job?.prompt||"";
  patch.instructions=request.instructions||"";
  return updateResearchConfig(patch);
}


// 0.35.10 — Record Player. The Record page is Vue-native; this bridge exposes
// only the current record data and actions needed by that workspace. Audit
// history is summarized separately so the heavyweight `updates` payload never
// becomes ordinary component state.
function compactRecordHistory(record,limit=80){
  const updates=Array.isArray(record?.updates)?record.updates:[];
  return updates.slice(-Math.max(1,limit)).reverse().map((update,index)=>({
    id:`history-${updates.length-index-1}`,
    field_name:String(update?.field_name||""),
    timestamp:update?.timestamp||null,
    source:String(update?.source||"manual"),
    initiated_by:update?.initiated_by||null,
    model:update?.model||null,
    reason:update?.reason||null,
  }));
}
function recordWorkspaceRecord(record){
  const out=recordPayload(record,{includeChromaId:true});
  delete out.updates;
  delete out.annotations;
  return cloneAuditValue(out);
}
function normalizedRecordAnnotation(item,index=0,{removable=false}={}){
  return {
    id:item?.id||item?.shared_annotation_id||`annotation-${index}`,
    field:String(item?.field||"text"),
    quote:String(item?.quote||""),
    note:String(item?.note||""),
    tags:Array.isArray(item?.tags)?item.tags.map(String):[],
    author:String(item?.initiated_by||item?.author||tr("annotations.unknown_author","Unknown author")),
    created_at:item?.created_at||null,
    removable:Boolean(removable),
    shared_annotation_id:item?.shared_annotation_id||null,
  };
}
async function researcherCurrentRecord(){
  // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
  try{await refreshServerAnnotations()}catch{}
  if(!state.activeStore){
    // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
    try{await refreshStores()}catch{}
    if(!state.activeStore)return null;
  }
  let id=state.researcherRecordId;
  let record=researcherDbRecords().find(item=>String(item._chroma_id||item.record_id||"")===String(id));
  if(!record&&id){try{record=await api(`/api/stores/${encodeURIComponent(state.activeStore)}/records/${encodeURIComponent(id)}`)}catch{record=null}}
  if(!record){
    // eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
    if(!state.storeRecords.length){try{await loadStorePage()}catch{}}
    record=state.storeRecords[0]||null;
    id=String(record?._chroma_id||record?.record_id||"");
    state.researcherRecordId=id;
  }
  return record;
}
async function getRecordWorkspaceSnapshot(){
  if(isResearcher()){
    const record=await researcherCurrentRecord();
    if(!record)return {available:false,mode:"database",reason:tr("research.no_records","No records available")};
    const id=String(record._chroma_id||record.record_id||state.researcherRecordId||"");
    const list=researcherDbRecords();
    const currentIndex=list.findIndex(item=>String(item._chroma_id||item.record_id||"")===id);
    const annotations=(state.serverAnnotations||[])
      .filter(item=>String(item.store||"")===String(state.activeStore)&&String(item.record_id||"")===id)
      .map((item,index)=>normalizedRecordAnnotation(item,index,{removable:false}));
    const text=String(record.text||"");
    const q=String(state.recordFind||"");
    const key=dbEvidenceKey(state.activeStore,id);
    return {
      available:true,mode:"database",record:recordWorkspaceRecord(record),record_id:id,
      file_name:null,collection:state.activeStore||"",current_index:currentIndex,total:list.length,
      has_previous:currentIndex>0,has_next:currentIndex>=0&&currentIndex<list.length-1,
      find_query:q,find_matches:countOccurrences(text,q),word_count:text.trim()?text.trim().split(/\s+/).length:0,character_count:text.length,
      evidence_selected:evidenceIsSelected(key),review_selected:false,
      annotations,pdf_links:[],history:[],history_count:0,
      inline_citation:inlineCitation(record),full_citation:fullCitation(record),page_span:mlaPageSpan(record),
      capabilities:{
        edit:false,annotate:hasCapability("annotations.write"),evidence:hasCapability("evidence.select"),
        review:false,upsert:false,llm_review:false,pdf:false,history:false,copy:true,
      },
      pdf:{loaded:false,related:false,current_page:null,title:"",name:""},
    };
  }
  const file=activeFile(),index=file?selectedIndex(file):0,record=file?.records?.[index];
  if(!file||!record)return {available:false,mode:"workspace",reason:tr("record.no_record_selected","No record selected.")};
  const pointer={kind:"workspace",fileId:file.id,index};
  if(JSON.stringify(state.lastViewedRecord)!==JSON.stringify(pointer)){state.lastViewedRecord=pointer;persistPrefs()}
  const text=String(record.text||"");
  const q=String(state.recordFind||"");
  const links=pdfLinks(record);
  const loadedPages=loadedPdfPagesForRecord(record);
  const related=Boolean(state.pdf.file&&state.pdf.name&&loadedPages.length);
  const annotations=(Array.isArray(record.annotations)?record.annotations:[]).map((item,annotationIndex)=>normalizedRecordAnnotation(item,annotationIndex,{removable:true}));
  const key=workspaceEvidenceKey(file,index);
  return {
    available:true,mode:"workspace",record:recordWorkspaceRecord(record),record_id:String(record.record_id||index+1),
    file_id:file.id,file_name:file.name,collection:state.activeStore||"",current_index:index,total:file.records.length,
    has_previous:index>0,has_next:index<file.records.length-1,
    find_query:q,find_matches:countOccurrences(text,q),word_count:text.trim()?text.trim().split(/\s+/).length:0,character_count:text.length,
    evidence_selected:evidenceIsSelected(key),review_selected:state.reviewSelection.has(reviewKey(file,index)),
    annotations,pdf_links:cloneAuditValue(links),history:compactRecordHistory(record),history_count:Array.isArray(record.updates)?record.updates.length:0,
    inline_citation:inlineCitation(record),full_citation:fullCitation(record),page_span:mlaPageSpan(record),
    capabilities:{
      edit:canUse("editLocalRecords"),annotate:hasCapability("annotations.write"),evidence:hasCapability("evidence.select"),
      review:canUse("editLocalRecords"),upsert:canUse("manageCorpus")&&hasCorpusDb(),llm_review:canUse("editLocalRecords"),
      pdf:canAccessPage("pdf"),history:canUse("editLocalRecords"),copy:true,
    },
    pdf:{
      loaded:Boolean(state.pdf.file&&state.pdf.name),related,current_page:state.pdf.page||null,
      current_linked:related&&loadedPages.includes(Number(state.pdf.page)),title:pdfDisplayTitle(),name:state.pdf.name||"",
      loaded_pages:loadedPages,
    },
  };
}
async function recordWorkspaceNavigate(delta){
  const step=Number(delta)||0;if(!step)return getRecordWorkspaceSnapshot();
  if(isResearcher()){
    const current=await researcherCurrentRecord();if(!current)return getRecordWorkspaceSnapshot();
    const id=String(current._chroma_id||current.record_id||"");
    const list=researcherDbRecords();const index=list.findIndex(item=>String(item._chroma_id||item.record_id||"")===id);
    const next=list[index+step];if(next){state.researcherRecordId=String(next._chroma_id||next.record_id||"");persistPrefs();syncUrl({replace:true});shell()}
    return getRecordWorkspaceSnapshot();
  }
  const file=activeFile();if(!file)return getRecordWorkspaceSnapshot();
  const index=selectedIndex(file),next=Math.max(0,Math.min(file.records.length-1,index+step));
  state.selected[file.id]=next;persistPrefs();syncUrl({replace:true});shell();
  return getRecordWorkspaceSnapshot();
}
function setRecordWorkspaceFind(value){state.recordFind=String(value||"");persistPrefs();syncUrl({replace:true});return state.recordFind}
async function toggleCurrentRecordEvidence(){
  if(isResearcher()){
    const record=await researcherCurrentRecord();if(!record)return getRecordWorkspaceSnapshot();
    toggleDbEvidence(state.activeStore,String(record._chroma_id||record.record_id||""),record);
  }else{const file=activeFile();if(file)toggleWorkspaceEvidence(file,selectedIndex(file))}
  return getRecordWorkspaceSnapshot();
}
async function toggleCurrentRecordReviewSelection(){
  if(isResearcher())return getRecordWorkspaceSnapshot();
  const file=activeFile();if(!file)return getRecordWorkspaceSnapshot();const index=selectedIndex(file);const selected=state.reviewSelection.has(reviewKey(file,index));setReviewSelected(file,index,!selected);shell();return getRecordWorkspaceSnapshot();
}
async function copyCurrentRecordCitation(kind="inline"){
  const snapshot=await getRecordWorkspaceSnapshot();if(!snapshot?.available)return false;
  const text=kind==="full"?snapshot.full_citation:snapshot.inline_citation;
  try{await navigator.clipboard.writeText(String(text||""));toast(tr(kind==="full"?"record.full_citation_copied":"record.inline_citation_copied",kind==="full"?"Full citation copied":"Inline citation copied"),{tone:"success"});return true}
  catch(error){toast(`${tr("record.copy_failed","Could not copy citation")}: ${error.message}`,{tone:"danger"});return false}
}
async function copyCurrentRecordJson(){
  if(isResearcher()){
    const record=await researcherCurrentRecord();if(!record)return false;await copyJsonToClipboard(recordWorkspaceRecord(record),tr("record.record_json","record"));return true;
  }
  const record=selectedRecord();if(!record)return false;await copyJsonToClipboard(recordWorkspaceRecord(record),tr("record.record_json","record"));return true;
}
async function saveCurrentRecordChanges(changes={}){
  if(isResearcher()||!canUse("editLocalRecords"))throw new Error(tr("permissions.record_edit_denied","Your role cannot edit local records."));
  const file=activeFile();if(!file)throw new Error(tr("record.no_record_selected","No record selected."));
  const index=selectedIndex(file);const safe={};
  for(const [field,value] of Object.entries(changes||{})){if(field!=="updates"&&!String(field).startsWith("_"))safe[field]=value}
  const count=applyRecordChanges(file,index,safe,{source:"record_workspace"});shell();
  if(count)toast(tr("record.saved","Record changes saved"),{tone:"success"});
  else toast(tr("record.no_changes","No record fields changed"),{tone:"info"});
  return getRecordWorkspaceSnapshot();
}
async function addCurrentRecordAnnotation(payload={}){
  if(!hasCapability("annotations.write"))throw new Error(tr("permissions.annotations_denied","Your role cannot create annotations."));
  const field=String(payload.field||"text"),quote=String(payload.quote||"").trim(),note=String(payload.note||"").trim(),tags=Array.isArray(payload.tags)?payload.tags.map(String).filter(Boolean):[];
  if(!quote&&!note&&!tags.length)throw new Error(tr("annotations.empty","Add a quotation, note, or tag first."));
  if(isResearcher()){
    const record=await researcherCurrentRecord();if(!record)throw new Error(tr("record.no_record_selected","No record selected."));
    await api("/api/annotations",{method:"POST",body:JSON.stringify({store:state.activeStore,record_id:String(record._chroma_id||record.record_id||""),work:String(record.work||""),page_start:record.page_start??null,page_end:record.page_end??null,field,quote,note,tags})});
    state.annotationsFetchedAt=0;await refreshServerAnnotations(true);toast(tr("annotations.saved","Record annotation saved"),{tone:"success"});return getRecordWorkspaceSnapshot();
  }
  const file=activeFile();if(!file)throw new Error(tr("record.no_record_selected","No record selected."));const index=selectedIndex(file),record=file.records[index];
  const shared=await api("/api/annotations",{method:"POST",body:JSON.stringify({store:state.activeStore||null,record_id:String(record._chroma_id||record.record_id||index+1),work:String(record.work||""),page_start:record.page_start??null,page_end:record.page_end??null,field,quote,note,tags})});
  const annotations=Array.isArray(record.annotations)?record.annotations.map(cloneAuditValue):[];
  annotations.push({id:uid(),shared_annotation_id:shared?.id||null,field,quote,note,tags,created_at:shared?.created_at||new Date().toISOString(),initiated_by:state.userContext?.username||null});
  applyRecordChanges(file,index,{annotations},{source:"annotation"});state.annotationsFetchedAt=0;await refreshServerAnnotations(true);shell();toast(tr("annotations.saved","Record annotation saved"),{tone:"success"});return getRecordWorkspaceSnapshot();
}
async function removeCurrentRecordAnnotation(annotationId){
  if(isResearcher()||!canUse("editLocalRecords"))throw new Error(tr("permissions.record_edit_denied","Your role cannot edit local records."));
  const file=activeFile();if(!file)throw new Error(tr("record.no_record_selected","No record selected."));const index=selectedIndex(file),record=file.records[index];
  const annotations=Array.isArray(record.annotations)?record.annotations.map(cloneAuditValue):[];
  const at=annotations.findIndex((item,i)=>String(item.id||item.shared_annotation_id||`annotation-${i}`)===String(annotationId));if(at<0)return getRecordWorkspaceSnapshot();
  const sharedId=annotations[at]?.shared_annotation_id;if(sharedId){await api(`/api/annotations/${encodeURIComponent(sharedId)}`,{method:"DELETE"});state.annotationsFetchedAt=0;await refreshServerAnnotations(true)}
  annotations.splice(at,1);applyRecordChanges(file,index,{annotations},{source:"annotation"});shell();toast(tr("annotations.removed","Record annotation removed"),{tone:"success"});return getRecordWorkspaceSnapshot();
}
async function currentRecordPrimaryAction(action,payload={}){
  if(action==="upsert"){
    if(isResearcher()||!canUse("manageCorpus"))throw new Error(tr("permissions.corpus_denied","Your role cannot manage corpus databases."));const file=activeFile();if(!file)return false;await upsertRows([{file,record:file.records[selectedIndex(file)],index:selectedIndex(file)}],"record");return true;
  }
  if(action==="llm"){
    if(isResearcher()||!canUse("editLocalRecords"))throw new Error(tr("permissions.record_edit_denied","Your role cannot edit local records."));const file=activeFile();if(!file)return false;const index=selectedIndex(file);openTouchup([{file,index,record:file.records[index],key:reviewKey(file,index)}]);return true;
  }
  if(action==="ocr"){
    if(isResearcher()||!canUse("editLocalRecords"))throw new Error(tr("permissions.record_edit_denied","Your role cannot edit local records."));const file=activeFile();if(!file)return false;cleanRecord(file,selectedIndex(file));return true;
  }
  if(action==="history"){
    if(isResearcher()||!canUse("editLocalRecords"))throw new Error(tr("permissions.record_edit_denied","Your role cannot edit local records."));const file=activeFile();if(!file)return false;openRecordHistoryBrowser(file,selectedIndex(file));return true;
  }
  if(action==="open_pdf"){
    if(!canAccessPage("pdf"))throw new Error(tr("permissions.pdf_denied","Your role cannot open PDF Explorer."));
    const snapshot=await getRecordWorkspaceSnapshot();const link=snapshot?.pdf_links?.[Number(payload.index)||0];if(!link)return false;
    if(state.pdf.file&&link.pdf_file===state.pdf.name)openLoadedPdfPage(link.pdf_page);else{openPdfExplorerWorkspace();toast(tr("record.open_pdf_first",`Open ${link.pdf_file} in PDF Explorer to jump to the linked page.`).replace("{file}",link.pdf_file),{tone:"info"})}return true;
  }
  if(action==="pdf_explorer"){if(!canAccessPage("pdf"))throw new Error(tr("permissions.pdf_denied","Your role cannot open PDF Explorer."));openPdfExplorerWorkspace();return true}
  if(action==="link_pdf"){
    if(isResearcher())return false;const file=activeFile();if(!file)return false;await linkPdfPage(file,selectedIndex(file),state.pdf.page);return true;
  }
  if(action==="remove_pdf"){
    if(isResearcher())return false;const file=activeFile();if(!file)return false;const record=file.records[selectedIndex(file)],links=pdfLinks(record),link=links[Number(payload.index)||0];if(link)unlinkPdfLink(file,selectedIndex(file),link);return true;
  }
  if(action==="remove_all_pdf"){
    if(isResearcher())return false;const file=activeFile();if(!file)return false;unlinkAllPdfLinks(file,selectedIndex(file));return true;
  }
  return false;
}
function searchCurrentRecordMetadata(field,value,{contains=false}={}){return searchByMetadata(field,value,{contains})}
function navigateRecordWorkspace(destination){if(["global","works","pdf"].includes(destination))navigateTo(destination)}

function getWorksWorkspaceSnapshot(){
  const map=workIndex();
  const query=String(state.worksSearch||"");
  const metadataFields=["source_type","document_author","container_title","journal_title","volume","issue","pages","publisher","publication_year","edition","translator","editor","publication_place","isbn","doi","document_language","original_language"];
  const items=[...map.values()].filter(item=>!query||item.work.toLocaleLowerCase().includes(query.toLocaleLowerCase())).sort((a,b)=>a.work.localeCompare(b.work)).map(item=>({
    work:item.work,count:item.count,review:item.review,annotations:allAnnotations().filter(annotation=>String(annotation.work||"")===String(item.work)).length,files:[...item.files],authors:[...item.authors],years:[...item.years].map(String),cover:workCoverUrl(item.rows),citation:fullCitation(item.rows[0]?.record||{work:item.work},{includePages:false}),
    metadata:metadataFields.map(field=>{const value=commonWorkValue(item.rows,field);return {field,mixed:value.mixed,value:value.mixed?"":String(display(value.value))}}).filter(value=>value.mixed||value.value!=="—"),
    status:workDbStatus(item.rows,item.work),insights:workInsightMetrics(item.rows,item.work).map(metric=>({id:metric.id,title:metric.title,values:metric.values.map(value=>({key:String(value.key),value:Number(value.value||0)}))})),
  }));
  const stores=recordStores().map(store=>({name:store.name,count:Number(store.count||0)}));
  return {available:state.files.length>0,works:items,query,selectedWork:String(state.workOverview||""),stores,activeStore:String(state.activeStore||""),totalWorks:map.size,totalRecords:[...map.values()].reduce((sum,item)=>sum+item.count,0),dbUnavailableReason:dbUnavailableReason(),capabilities:{canManageCorpus:canUse("manageCorpus"),canSync:canUse("manageCorpus")&&hasCorpusDb()}};
}
function setWorksSearch(value){state.worksSearch=String(value||"");persistPrefs();syncUrl({replace:true})}
function setWorksOverview(work){state.workOverview=String(work||"");persistPrefs();syncUrl({replace:true})}
function setWorksStore(name){setActiveStore(name)}
async function syncWork(work){const item=workIndex().get(String(work||""));if(!item)return false;return upsertRows(item.rows,trf("works.work_records_label","records for {work}",{work:item.work}))}
async function syncAllWorks(){const rows=[...workIndex().values()].flatMap(item=>item.rows);return upsertRows(rows,tr("works.all_records_label","records across all works"))}
function searchWork(work){state.globalSearchMode="traditional";state.globalSearch="";state.globalFilters=[{id:uid(),field:"work",op:"eq",value:String(work||"")}];state.globalPage=1;persistPrefs();navigateTo("global")}
function openWorkMetadataEditorForVue(work){const item=workIndex().get(String(work||""));if(item)openWorkMetadataEditor(item.work,item.rows)}
function openWorkMetadataLlmDialogForVue(work){const item=workIndex().get(String(work||""));if(item)openWorkMetadataLlmDialog([item])}
function openWorkAnnotations(work){state.annotationSearch=String(work||"");state.annotationView="works";persistPrefs();navigateTo("annotations")}

export {
  getNavItems,
  operationViewModel,
  operationDetailPairs,
  jobProgressText,
  state,
  viewConfig,
  setUserContext,
  setTranslationDictionary,
  getShellSnapshot,
  setShellRefreshHook,
  setUrlSyncHook,
  pauseRuntime,
  viewPathMap,
  pathViewMap,
  bootstrapRuntime,
  renderView,
  navigateView,
  toggleSidebar,
  activateFile,
  closeWorkspaceFile,
  triggerImport,
  triggerMerge,
  triggerSubset,
  triggerBulkEdit,
  triggerOcrClean,
  triggerReviewFlagged,
  triggerAutoImproveFlagged,
  openTouchup,
  touchupWorkspaceInfo,
  touchupProviderStatus,
  touchupRequestConfig,
  touchupRequest,
  touchupSubmitBackground,
  touchupApplyResults,
  triggerUpsertQueue,
  triggerOperations,
  triggerExport,
  triggerEdit,
  triggerBack,
  triggerForward,
  getProviderProfilesForUi,
  getProviderRequestConfigForUi,
  getDefaultProviderProfileId,
  getProviderStatusesForUi,
  getProviderWarmupsForUi,
  saveProviderProfilesForUi,
  addProviderProfileForUi,
  removeProviderProfileForUi,
  setDefaultProviderProfileForUi,
  testProviderProfileForUi,
  warmProviderProfileForUi,
  getWarmOnStartForUi,
  setWarmOnStartForUi,
  syncResearcherProviderProfiles,
  notifyToast,
  registerExternalJob,
  dbUnavailableReason,
  hasCorpusDb,
  openDatabaseCreationFromResearch,
  notifyVectorStoresChanged,
  openCollectionCreationWizard,
  upsertRows,
  exportStoreJsonl,
  persistPrefs,
  lookupRecord,
  getCompareLibrary,
  getCompareRecord,
  ensureCompareLibrary,
  copyJsonToClipboard,
  copyCitation,
  flushWorkspacePrefs,
  applyUiTheme,
  applyAppearance,
  downloadFullBackup,
  restoreFullBackup,
  clearAllUpdates,
  deleteAllDerridaiBrowserState,
  backupContainsCredentials,
  pendingUpsertRows,
  decorateDisabledControls,
  getResearchWorkspaceSnapshot,
  updateResearchConfig,
  removeResearchEvidence,
  clearResearchEvidence,
  discoverResearchModels,
  refreshResearchJobs,
  getResearchJob,
  cancelResearchJob,
  deleteResearchJob,
  startResearchRun,
  gradeResearchJob,
  prepareResearchRerun,
  getResponseFaqPage,
  gradeResponseFaqRecord,
  rerunResponseFaqRecord,
  getRecordWorkspaceSnapshot,
  recordWorkspaceNavigate,
  setRecordWorkspaceFind,
  toggleCurrentRecordEvidence,
  toggleCurrentRecordReviewSelection,
  copyCurrentRecordCitation,
  copyCurrentRecordJson,
  saveCurrentRecordChanges,
  addCurrentRecordAnnotation,
  removeCurrentRecordAnnotation,
  currentRecordPrimaryAction,
  searchCurrentRecordMetadata,
  navigateRecordWorkspace,
  getWorksWorkspaceSnapshot,
  setWorksSearch,
  setWorksOverview,
  setWorksStore,
  syncWork,
  syncAllWorks,
  searchWork,
  openWorkMetadataEditorForVue as openWorkMetadataEditor,
  openWorkMetadataLlmDialogForVue as openWorkMetadataLlmDialog,
  openWorkAnnotations,
  openSeparateWorksModal,
  getSearchWorkspaceSnapshot,
  setSearchScope,
  updateSearchQuery,
  setSearchAdvancedOpen,
  setSearchMethod,
  setSearchStore,
  setSearchMmrOptions,
  setSearchLayout,
  setSearchPage,
  setSearchPageSize,
  setSearchColumns,
  setSearchSort,
  toggleSearchFacet,
  clearSearchFacetFilters,
  clearSearchAllFilters,
  addSearchAdvancedFilter,
  removeSearchAdvancedFilter,
  runSearchWorkspace,
  searchResultAction,
  setSearchResultSelected,
  setSearchPageSelected,
  clearSearchSelection,
  runSearchSelectionAction,
  getSearchShareHref,
  restoreSearchViewFromHref,
  getRecordsListSnapshot,
  setRecordsListQuery,
  setRecordsListStore,
  setRecordsListPage,
  setRecordsListPageSize,
  setRecordsListSort,
  setRecordsListFilter,
  clearRecordsListFilters,
  setRecordsListRowSelected,
  setRecordsListPageSelected,
  selectRecordsListMatches,
  clearRecordsListSelection,
  openRecordsListRecord,
  copyRecordsListJson,
  copyRecordsListCitation,
  toggleRecordsListEvidence,
  recordsListMetadataSearch,
  setRecordsListColumns,
  resetRecordsListColumns,
  getRecordsListShareHref,
  recordsListCommand,
};
