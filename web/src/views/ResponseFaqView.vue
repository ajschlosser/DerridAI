<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AccessibleEmptyState from "../components/AccessibleEmptyState.vue";
import AppIcon from "../components/AppIcon.vue";
import ResponseFaqArchiveDialog from "../components/research/ResponseFaqArchiveDialog.vue";
import ResponseFaqSelectionBar from "../components/research/ResponseFaqSelectionBar.vue";
import ResearchResultPresentation from "../components/research/ResearchResultPresentation.vue";
import EvaluationReport from "../components/research/EvaluationReport.vue";
import { useI18nStore } from "../stores/i18n";
import type { ResearchResult, ResponseFaqPage, ResponseFaqRecord } from "../types/research";
import * as runtime from "../runtime/runtime.js";

const i18n=useI18nStore();
const router=useRouter();
const route=useRoute();
const loading=ref(false);
const routeText=(value:unknown)=>Array.isArray(value)?String(value[0]??""):String(value??"");
const routePage=(value:unknown)=>Math.max(1,Number.parseInt(routeText(value),10)||1);
const search=ref(routeText(route.query.q));
const page=ref(routePage(route.query.page));
const pageSize=25;
const payload=ref<ResponseFaqPage|null>(null);
const selected=ref<ResponseFaqRecord|null>(null);
const activeEvidenceIndex=ref(0);
const archiveOpen=ref(false);
let searchTimer:number|undefined;
let applyingRoute=false;
let writingRoute=false;

const records=computed(()=>payload.value?.records||[]);
const total=computed(()=>Number(payload.value?.count||0));
const cacheTotal=computed(()=>Number(payload.value?.total||0));
const pages=computed(()=>Math.max(1,Math.ceil(total.value/pageSize)));
const selectedId=computed(()=>recordKey(selected.value));
const evidenceCount=computed(()=>Number(selected.value?.evidence_count??selected.value?.evidence?.length??0));
function gradeScalar(value:unknown):string|number|null{
  return typeof value==="string"||typeof value==="number"?value:null;
}
const primaryGrade=computed<string|number|null>(()=>{
  const grade=selected.value?.grade as Record<string,unknown>|undefined;
  const value=(grade?.result&&typeof grade.result==="object"?grade.result:grade) as Record<string,unknown>|undefined;
  return gradeScalar(value?.overall??value?.score);
});
const result=computed<ResearchResult|null>(()=>{
  const record=selected.value;
  if(!record)return null;
  return {
    prompt:record.question||"",
    answer:record.text||"",
    provider:record.provider||"",
    model:record.model||"",
    elapsed_seconds:record.elapsed_seconds,
    evidence:Array.isArray(record.evidence)?record.evidence:[],
    warnings:Array.isArray(record.warnings)?record.warnings:[],
    query_metadata:record.query_metadata||{},
    retrieval:record.retrieval||{},
    response_cache:{record_id:record.record_id},
    auto_grade:record.grade||null,
    rag_request:record.rag_request||{},
  };
});
const savedGrades=computed<Array<Record<string,unknown>>>(()=>Array.isArray(selected.value?.grades)?selected.value!.grades!:[]);

type MetaEntry={key:string;label:string;value:string};
const retrievalEntries=computed(()=>metadataEntries(selected.value?.retrieval,"retrieval"));
const queryEntries=computed(()=>metadataEntries(selected.value?.query_metadata,"query"));
const runMetrics=computed(()=>{
  const retrieval=selected.value?.retrieval||{};
  const items:Array<{label:string;value:string}>=[];
  const add=(label:string,value:unknown)=>{if(value!==undefined&&value!==null&&String(value)!=="")items.push({label,value:String(value)})};
  if(selected.value?.elapsed_seconds!=null)add(i18n.t("faq.elapsed","Elapsed"),`${Number(selected.value.elapsed_seconds).toFixed(2)} s`);
  add(i18n.t("faq.evidence_bound","Evidence bound"),evidenceCount.value);
  add(i18n.t("faq.retrieved","Retrieved"),retrieval.raw_count);
  add(i18n.t("faq.deduplicated","After deduplication"),retrieval.deduplicated_count);
  add(i18n.t("faq.reranked","After reranking"),retrieval.reranked_count??retrieval.effective_rerank_top_n);
  return items;
});

function recordKey(record:ResponseFaqRecord|null){return String(record?.record_id||record?.question||"")}
function currentFaqQuery(){
  const query:Record<string,string>={};
  if(search.value.trim())query.q=search.value.trim();
  if(page.value>1)query.page=String(page.value);
  if(selectedId.value)query.id=selectedId.value;
  return query;
}
async function syncFaqUrl(){
  if(applyingRoute)return;
  const next=currentFaqQuery();
  const current={q:routeText(route.query.q),page:routeText(route.query.page),id:routeText(route.query.id)};
  const normalized={q:next.q||"",page:next.page||"",id:next.id||""};
  if(current.q===normalized.q&&current.page===normalized.page&&current.id===normalized.id)return;
  writingRoute=true;
  try{await router.replace({path:"/faq",query:next})}finally{writingRoute=false}
}
function choose(record:ResponseFaqRecord){selected.value=record;activeEvidenceIndex.value=0;archiveOpen.value=false;void syncFaqUrl()}
function formatJson(value:unknown){try{return JSON.stringify(value||{},null,2)}catch{return "{}"}}
function formatDate(value?:unknown){if(!value)return "";try{return new Intl.DateTimeFormat(i18n.locale,{dateStyle:"medium",timeStyle:"short"}).format(new Date(String(value)))}catch{return String(value)}}
function gradeOverall(entry:Record<string,unknown>){let grade=(entry.result&&typeof entry.result==="object"?entry.result:entry) as Record<string,unknown>;if(grade.grade&&typeof grade.grade==="object")grade=grade.grade as Record<string,unknown>;if(grade.result&&typeof grade.result==="object"&&!('overall' in grade))grade=grade.result as Record<string,unknown>;const raw=grade.overall??grade.score;if(raw&&typeof raw==="object")return (raw as Record<string,unknown>).score??"—";return raw??"—"}
function formatMetaValue(value:unknown){if(Array.isArray(value))return value.map(item=>String(item)).join(", ");if(typeof value==="boolean")return value?i18n.t("research.on","On"):i18n.t("research.off","Off");if(value&&typeof value==="object")return JSON.stringify(value);return String(value??"")}
function metadataEntries(value:unknown,kind:"retrieval"|"query"):MetaEntry[]{
  if(!value||typeof value!=="object"||Array.isArray(value))return [];
  const preferred=kind==="retrieval"
    ?["search_types","k","fetch_k","lambda_mult","rrf_k","reranker","rerank_top_n","query_decomposition","skip_retrieval","selected_evidence_count","response_language","evidence_record_char_limit","evidence_total_char_limit"]
    :["prompt_query","prompt_query_fr","prompt_instructions","limit_retrieval","limit_reranking","response_language","document_languages"];
  const entries=Object.entries(value as Record<string,unknown>);
  const ordered=[...preferred.map(key=>entries.find(([entryKey])=>entryKey===key)).filter((entry):entry is [string,unknown]=>Boolean(entry)),...entries.filter(([key])=>!preferred.includes(key))];
  return ordered.filter(([,entryValue])=>entryValue!==undefined&&entryValue!==null&&formatMetaValue(entryValue)!=="").slice(0,18).map(([key,entryValue])=>({key,label:i18n.t(`faq.meta_${key}`,key.replaceAll("_"," ").replace(/^./,character=>character.toUpperCase())),value:formatMetaValue(entryValue)}));
}

async function load({chooseFirst=false}:{chooseFirst?:boolean}={}){
  loading.value=true;
  try{
    const next=await runtime.getResponseFaqPage({limit:pageSize,offset:(page.value-1)*pageSize,query:search.value}) as ResponseFaqPage;
    payload.value=next;
    const maxPage=Math.max(1,Math.ceil(Number(next.count||0)/pageSize));
    if(page.value>maxPage){page.value=maxPage;await load({chooseFirst});return}
    const requestedId=routeText(route.query.id);
    const requested=requestedId?next.records.find(record=>recordKey(record)===requestedId):null;
    if(requested)selected.value=requested;
    else if(chooseFirst||!selected.value||!next.records.some(record=>recordKey(record)===selectedId.value))selected.value=next.records[0]||null;
    activeEvidenceIndex.value=0;
    await syncFaqUrl();
  }catch(error){runtime.notifyToast(error instanceof Error?error.message:String(error),{tone:"danger"})}
  finally{loading.value=false}
}
function scheduleSearch(){if(applyingRoute)return;window.clearTimeout(searchTimer);page.value=1;searchTimer=window.setTimeout(()=>void load({chooseFirst:true}),250);void syncFaqUrl()}
async function copyAnswer(){try{await navigator.clipboard.writeText(result.value?.answer||"");runtime.notifyToast(i18n.t("research.answer_copied","Answer copied"),{tone:"success"})}catch{runtime.notifyToast(i18n.t("research.clipboard_failed","Could not access the clipboard"),{tone:"danger"})}}
function focusEvidence(index:number){activeEvidenceIndex.value=index}
function grade(){if(selected.value)runtime.gradeResponseFaqRecord(selected.value)}
function rerun(){if(selected.value)runtime.rerunResponseFaqRecord(selected.value)}
function focusDetails(){document.querySelector('#faqRunDetails')?.scrollIntoView({behavior:'smooth',block:'start'})}
function setArchiveSearch(value:string){search.value=value}
function newResearch(){void router.push("/rag")}
async function goPage(delta:number){page.value=Math.min(pages.value,Math.max(1,page.value+delta));await syncFaqUrl();await load({chooseFirst:true})}

watch(search,scheduleSearch);
watch(
  ()=>[route.query.q,route.query.page,route.query.id] as const,
  async()=>{
    if(writingRoute)return;
    const nextSearch=routeText(route.query.q);
    const nextPage=routePage(route.query.page);
    const nextId=routeText(route.query.id);
    if(nextSearch===search.value&&nextPage===page.value&&nextId===selectedId.value)return;
    applyingRoute=true;
    window.clearTimeout(searchTimer);
    try{
      search.value=nextSearch;
      page.value=nextPage;
      selected.value=null;
      await load({chooseFirst:true});
      if(nextId){const match=records.value.find(record=>recordKey(record)===nextId);if(match)selected.value=match}
    }finally{applyingRoute=false}
  }
);
onMounted(()=>void load({chooseFirst:true}));
</script>

<template>
  <main class="vue-native-page response-faq-page" aria-labelledby="response-faq-title">
    <header class="research-page-intro response-faq-intro">
      <div>
        <span class="section-label">{{i18n.t('faq.page_kicker','Research archive')}}</span>
        <h1 id="response-faq-title">{{i18n.t('nav.faq','Response Library')}}</h1>
        <p>{{i18n.t('faq.page_subtitle','Revisit cached answers with the same source-bound evidence experience used in Research.')}}</p>
      </div>
      <div class="response-faq-page-actions">
        <button v-if="payload&&cacheTotal" class="btn" type="button" @click="archiveOpen=true"><AppIcon name="search"/>{{i18n.t('faq.find_question',i18n.t('faq.browse_archive','Browse saved research'))}} <span>{{cacheTotal.toLocaleString(i18n.locale)}}</span></button>
        <button class="btn primary" type="button" @click="newResearch"><AppIcon name="spark"/>{{i18n.t('faq.new_research','New research')}}</button>
      </div>
    </header>

    <div v-if="loading&&!payload" class="research-loading response-faq-loading" role="status"><span class="spinner"></span>{{i18n.t('faq.loading','Loading cached research responses…')}}</div>

    <AccessibleEmptyState
      v-else-if="payload&&!cacheTotal"
      icon="spark"
      icon-tone="neutral"
      :title="i18n.t('faq.empty_title','No cached research responses yet')"
      :description="i18n.t('faq.empty_help','Completed cached Research runs will appear here with their evidence bindings.')"
    />

    <section v-else-if="selected&&result" class="response-faq-workspace" aria-live="polite">
      <ResponseFaqSelectionBar :record="selected" :evidence-count="evidenceCount" :grade="primaryGrade" @browse="archiveOpen=true"/>

      <aside v-if="selected.instructions" class="response-faq-instructions" :aria-label="i18n.t('research.instructions','Instructions')">
        <AppIcon name="edit" aria-hidden="true"/>
        <div><strong>{{i18n.t('research.instructions','Instructions')}}</strong><p>{{selected.instructions}}</p></div>
      </aside>

      <ResearchResultPresentation
        :result="result"
        :active-evidence-index="activeEvidenceIndex"
        :can-grade="true"
        @copy="copyAnswer"
        @grade="grade"
        @rerun="rerun"
        @details="focusDetails"
        @evidence="focusEvidence"
        @select-evidence="activeEvidenceIndex=$event"
      />

      <details id="faqRunDetails" class="response-faq-details">
        <summary>
          <span><AppIcon name="history" aria-hidden="true"/></span>
          <div><strong>{{i18n.t('faq.run_provenance','Run provenance & saved evaluation')}}</strong><small>{{i18n.t('faq.run_provenance_help','Inspect retrieval diagnostics, query metadata, and retained grades without obscuring the answer.')}}</small></div>
          <b aria-hidden="true">⌄</b>
        </summary>
        <div class="response-faq-details-body">
          <section v-if="runMetrics.length" class="response-faq-run-summary">
            <header><h2>{{i18n.t('faq.run_summary','Run summary')}}</h2><p>{{i18n.t('faq.run_summary_help','A compact view of what happened before the answer was generated.')}}</p></header>
            <div class="response-faq-metrics"><article v-for="item in runMetrics" :key="item.label"><span>{{item.label}}</span><strong>{{item.value}}</strong></article></div>
          </section>

          <div class="response-faq-detail-columns">
            <section v-if="retrievalEntries.length" class="response-faq-metadata-section">
              <header><h2>{{i18n.t('research.retrieval_diagnostics','Retrieval diagnostics')}}</h2><p>{{i18n.t('faq.retrieval_help','The retrieval settings and counts retained with this cached answer.')}}</p></header>
              <dl><div v-for="entry in retrievalEntries" :key="entry.key"><dt>{{entry.label}}</dt><dd>{{entry.value}}</dd></div></dl>
            </section>
            <section v-if="queryEntries.length" class="response-faq-metadata-section">
              <header><h2>{{i18n.t('research.query_metadata','Query metadata')}}</h2><p>{{i18n.t('faq.query_help','How the question was interpreted and routed for this run.')}}</p></header>
              <dl><div v-for="entry in queryEntries" :key="entry.key"><dt>{{entry.label}}</dt><dd>{{entry.value}}</dd></div></dl>
            </section>
          </div>

          <section v-if="savedGrades.length" class="response-faq-grades">
            <header><h2>{{i18n.t('faq.saved_grades','Saved LLM grades')}}</h2><p>{{i18n.t('faq.saved_grades_help','Evaluations retained with this cached response.')}}</p></header>
            <div><article v-for="(entry,index) in [...savedGrades].reverse()" :key="index"><span><b>{{entry.provider||i18n.t('research.provider','Provider')}}</b><small>{{entry.model||''}}<template v-if="entry.graded_at"> · {{formatDate(entry.graded_at)}}</template></small></span><strong>{{gradeOverall(entry)}}<small>/10</small></strong><details class="response-faq-grade-output"><summary>{{i18n.t('faq.full_grade_output','Full evaluation report')}}</summary><EvaluationReport :report="entry.result||entry" /></details></article></div>
          </section>

          <details class="response-faq-technical">
            <summary>{{i18n.t('faq.technical_metadata','Technical metadata')}}</summary>
            <div><section><h3>{{i18n.t('research.retrieval_diagnostics','Retrieval diagnostics')}}</h3><pre>{{formatJson(selected.retrieval)}}</pre></section><section><h3>{{i18n.t('research.query_metadata','Query metadata')}}</h3><pre>{{formatJson(selected.query_metadata)}}</pre></section></div>
          </details>
        </div>
      </details>
    </section>

    <ResponseFaqArchiveDialog
      :open="archiveOpen"
      :records="records"
      :selected-id="selectedId"
      :search="search"
      :loading="loading"
      :count="total"
      :total="cacheTotal"
      :page="page"
      :pages="pages"
      @close="archiveOpen=false"
      @select="choose"
      @search="setArchiveSearch"
      @refresh="load()"
      @page="goPage"
    />
  </main>
</template>

<style scoped>
.response-faq-page{max-width:1540px!important;display:grid;gap:16px;padding-bottom:38px}.response-faq-intro{align-items:center}.response-faq-page-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end}.response-faq-page-actions .btn{min-height:40px;display:inline-flex;align-items:center;gap:7px}.response-faq-page-actions .btn svg{width:15px;height:15px}.response-faq-page-actions .btn>span{min-width:22px;height:22px;display:grid;place-items:center;border-radius:999px;background:#edf2ef;font-size:.8125rem}.response-faq-loading{min-height:260px;border:1px solid #e2e8ed;border-radius:16px;background:#fff}.response-faq-workspace{display:grid;gap:14px;min-width:0}.response-faq-instructions{display:grid;grid-template-columns:28px minmax(0,1fr);gap:10px;align-items:start;margin:0;padding:10px 12px;border:1px solid #e2e8e4;border-radius:11px;background:#fafcfb;color:#617087}.response-faq-instructions>svg{width:17px;height:17px;margin-top:2px;color:#678173}.response-faq-instructions div{display:grid;gap:2px}.response-faq-instructions strong{color:#405267;font-size:.8125rem;text-transform:uppercase;letter-spacing:.05em}.response-faq-instructions p{margin:0;font-size:12.5px;line-height:1.5}.response-faq-workspace :deep(.research-answer-workspace),.response-faq-workspace :deep(.research-evidence-panel){box-shadow:0 10px 30px rgba(15,23,42,.045)}.response-faq-details{overflow:hidden;border:1px solid #dfe6ec;border-radius:14px;background:#fff}.response-faq-details>summary{min-height:64px;display:grid;grid-template-columns:34px minmax(0,1fr) auto;align-items:center;gap:10px;padding:11px 14px;list-style:none;cursor:pointer;background:#fbfcfd}.response-faq-details>summary::-webkit-details-marker{display:none}.response-faq-details>summary>span{width:32px;height:32px;display:grid;place-items:center;border-radius:9px;background:var(--ui-accent-soft);color:var(--ui-accent-dark)}.response-faq-details>summary svg{width:16px;height:16px}.response-faq-details>summary>div{display:grid;gap:2px}.response-faq-details>summary strong{color:#304158;font-size:13.5px}.response-faq-details>summary small{color:#728095;font-size:.8125rem;line-height:1.4}.response-faq-details>summary>b{color:#7d8999;font-size:17px;transition:transform .16s ease}.response-faq-details[open]>summary{border-bottom:1px solid #e6ebef}.response-faq-details[open]>summary>b{transform:rotate(180deg)}.response-faq-details-body{display:grid;gap:18px;padding:17px}.response-faq-run-summary,.response-faq-metadata-section,.response-faq-grades{display:grid;gap:10px}.response-faq-details-body header{display:grid;gap:3px}.response-faq-details-body h2{margin:0;color:#304158;font-size:14px}.response-faq-details-body header p{margin:0;color:#748296;font-size:.8125rem;line-height:1.45}.response-faq-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:8px}.response-faq-metrics article{display:grid;gap:4px;padding:11px 12px;border:1px solid #e2e8ed;border-radius:10px;background:#fbfcfd}.response-faq-metrics span{color:#748196;font-size:.8125rem;font-weight:750;text-transform:uppercase;letter-spacing:.04em}.response-faq-metrics strong{color:#26384f;font-size:18px;font-variant-numeric:tabular-nums}.response-faq-detail-columns{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.response-faq-metadata-section dl{display:grid;margin:0;border:1px solid #e3e8ed;border-radius:10px;overflow:hidden}.response-faq-metadata-section dl>div{display:grid;grid-template-columns:minmax(120px,.72fr) minmax(0,1fr);gap:9px;padding:8px 10px;border-top:1px solid #edf0f3}.response-faq-metadata-section dl>div:first-child{border-top:0}.response-faq-metadata-section dt{color:#728095;font-size:.8125rem}.response-faq-metadata-section dd{margin:0;color:#34455c;font-size:.8125rem;font-weight:700;overflow-wrap:anywhere}.response-faq-grades>div{display:grid;gap:7px}.response-faq-grades article{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;padding:10px 12px;border:1px solid #e3e8ed;border-radius:10px;background:#fbfcfd}.response-faq-grades article>span{display:grid;gap:2px}.response-faq-grades article>span small{color:#718096;font-size:.8125rem}.response-faq-grades article>strong{color:var(--ui-accent-dark);font-size:18px}.response-faq-grades article>strong small{font-size:.8125rem;color:#758397}.response-faq-grade-output{grid-column:1/-1;border-top:1px solid #e6ebef;padding-top:6px}.response-faq-grade-output>summary{width:max-content;max-width:100%;min-height:32px;display:flex;align-items:center;color:#5f7085;font-size:.8125rem;font-weight:750;cursor:pointer}.response-faq-grade-output :deep(.evaluation-report){margin-top:8px}.response-faq-technical{border-top:1px solid #e8edf1;padding-top:4px}.response-faq-technical>summary{width:max-content;max-width:100%;min-height:34px;display:flex;align-items:center;color:#65758a;font-size:.8125rem;font-weight:750;cursor:pointer}.response-faq-technical>div{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;padding-top:8px}.response-faq-technical section{min-width:0;padding:10px;border:1px solid #e4e9ee;border-radius:9px;background:#f9fbfc}.response-faq-technical h3{margin:0 0 7px;color:#415168;font-size:.8125rem}.response-faq-technical pre{max-height:260px;margin:0;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;color:#4b5c70;font:12px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}.response-faq-page :is(button,input,summary):focus-visible{outline:3px solid var(--ui-accent-focus);outline-offset:2px}@media(max-width:900px){.response-faq-detail-columns,.response-faq-technical>div{grid-template-columns:1fr}}@media(max-width:700px){.response-faq-intro{align-items:flex-start}.response-faq-page-actions{width:100%;justify-content:stretch}.response-faq-page-actions .btn{flex:1;justify-content:center}.response-faq-details>summary small{display:none}.response-faq-details-body{padding:12px}.response-faq-metadata-section dl>div{grid-template-columns:1fr;gap:3px}}@media(max-width:500px){.response-faq-page-actions{display:grid;grid-template-columns:1fr}.response-faq-metrics{grid-template-columns:1fr 1fr}}@media(prefers-reduced-motion:reduce){.response-faq-page *{scroll-behavior:auto!important;transition:none!important}}
</style>
