<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import * as runtime from "../runtime/runtime.js";
import { useI18nStore } from "../stores/i18n";
import { useShellStore } from "../stores/shell";
import AppIcon from "../components/AppIcon.vue";
import AccessibleEmptyState from "../components/AccessibleEmptyState.vue";
import CitationMenu from "../components/CitationMenu.vue";
import SearchResultLayoutSwitcher from "../components/SearchResultLayoutSwitcher.vue";
import SearchWorkspaceHeader from "../components/search/SearchWorkspaceHeader.vue";
import SearchFacetPanel from "../components/search/SearchFacetPanel.vue";
import SearchSelectionBar from "../components/search/SearchSelectionBar.vue";
import HighlightedText from "../components/search/HighlightedText.vue";
import type { RecentSearchEntry, SavedSearchView, SearchFilter, SearchLayout, SearchMethod, SearchResult, SearchScope, SearchWorkspaceSnapshot } from "../types/search";

const route=useRoute();
const i18n=useI18nStore();
const shell=useShellStore();
const snapshot=ref<SearchWorkspaceSnapshot|null>(null);
const loading=ref(true);
const error=ref("");
const query=ref("");
const facetDrawerOpen=ref(false);
const columnsDialog=ref<HTMLDialogElement|null>(null);
const viewsDialog=ref<HTMLDialogElement|null>(null);
const saveDialog=ref<HTMLDialogElement|null>(null);
const advancedOpen=ref(false);
const newFilterField=ref("work");
const newFilterOp=ref("eq");
const newFilterValue=ref("");
const saveViewName=ref("");
const savedViews=ref<SavedSearchView[]>([]);
const recentSearches=ref<RecentSearchEntry[]>([]);
const draftColumns=ref<string[]>([]);
const expandedText=reactive(new Set<string>());
const columnWidths=reactive<Record<string,number>>(loadColumnWidths());
let localSearchTimer=0;
let recentTimer=0;
let redirectedForDatabase=false;

const scope=computed<SearchScope>(()=>snapshot.value?.scope||"loaded");
const databaseMode=computed(()=>scope.value==="database");
const resultKeys=computed(()=>snapshot.value?.results.filter(result=>result.kind==="workspace").map(result=>result.key)||[]);
const pageAllSelected=computed(()=>Boolean(resultKeys.value.length)&&snapshot.value?.results.filter(result=>result.kind==="workspace").every(result=>result.selected));
const activeFacetChips=computed(()=>snapshot.value?.facets.flatMap(facet=>facet.values.filter(item=>item.selected).map(item=>({field:facet.field,fieldLabel:facet.label,value:item.value,label:item.label})))||[]);
const hasFilters=computed(()=>Boolean(activeFacetChips.value.length||snapshot.value?.filters.length));
const resultSummary=computed(()=>{
  const total=snapshot.value?.total||0;
  return total===1?i18n.tf("search.result_count_one","{count} result",{count:total.toLocaleString(i18n.locale)}):i18n.tf("search.result_count_many","{count} results",{count:total.toLocaleString(i18n.locale)});
});
const searchPlaceholder=computed(()=>databaseMode.value?i18n.t("search.database_placeholder","Search the corpus semantically…"):i18n.t("search.loaded_placeholder","Search extracted text across loaded records…"));
const methodHelp=computed(()=>snapshot.value?.method==="mmr"?i18n.t("search.mmr_help","Balances semantic relevance with diversity across the result set."):snapshot.value?.method==="filter"?i18n.t("search.filter_only_help","Returns records using metadata filters without embedding a text query."):i18n.t("search.similarity_help","Ranks records by semantic similarity to your query."));
const selectedColumnKeys=computed(()=>snapshot.value?.columns.map(column=>column.key)||[]);
const sortOptions=computed(()=>{
  const base=[{key:"work",label:i18n.t("field.work","Work")},{key:"page_start",label:i18n.t("field.page_start","Page Start")},{key:"record_id",label:i18n.t("field.record_id","Record ID")}];
  if(databaseMode.value)base.unshift({key:"similarity",label:i18n.t("search.relevance","Relevance")});
  return base;
});
const activeSortLabel=computed(()=>sortOptions.value.find(item=>item.key===snapshot.value?.sort.key)?.label||i18n.t("search.sort","Sort"));

function loadColumnWidths(){try{return JSON.parse(localStorage.getItem("derridai.search.columnWidths.v1")||"{}")||{}}catch{return {}}}
function persistColumnWidths(){try{localStorage.setItem("derridai.search.columnWidths.v1",JSON.stringify(columnWidths))}catch{}}
function loadSavedState(){
  try{savedViews.value=JSON.parse(localStorage.getItem("derridai.search.savedViews.v1")||"[]")||[]}catch{savedViews.value=[]}
  try{recentSearches.value=JSON.parse(localStorage.getItem("derridai.search.recent.v1")||"[]")||[]}catch{recentSearches.value=[]}
}
function persistSavedViews(){try{localStorage.setItem("derridai.search.savedViews.v1",JSON.stringify(savedViews.value.slice(0,40)))}catch{}}
function persistRecent(){try{localStorage.setItem("derridai.search.recent.v1",JSON.stringify(recentSearches.value.slice(0,12)))}catch{}}

async function load(options:{refresh?:boolean;autoRun?:boolean}={}){
  loading.value=!snapshot.value;error.value="";
  try{
    const next=await runtime.getSearchWorkspaceSnapshot({refresh:options.refresh!==false,autoRun:options.autoRun!==false}) as SearchWorkspaceSnapshot;
    snapshot.value=next;query.value=next.query;advancedOpen.value=next.advanced_open;
    if(!newFilterField.value||!next.filter_fields.some(field=>field.key===newFilterField.value))newFilterField.value=next.filter_fields[0]?.key||"work";
    shell.sync();
    const mustCreateDatabase=!next.has_database&&(next.scope==="database"||!next.has_loaded_records);
    if(mustCreateDatabase&&next.capabilities.can_manage_database&&!redirectedForDatabase){redirectedForDatabase=true;runtime.notifyToast(i18n.t("search.redirect_database","Search needs a corpus database. Opening database creation now."),{tone:"info"});runtime.openDatabaseCreationFromResearch();return}
    redirectedForDatabase=false;
  }catch(exc){error.value=exc instanceof Error?exc.message:String(exc)}finally{loading.value=false}
}
function applyQuery(value:string){
  query.value=value;runtime.updateSearchQuery(value,{replace:true});
  if(databaseMode.value)return;
  window.clearTimeout(localSearchTimer);localSearchTimer=window.setTimeout(()=>{void load({refresh:false,autoRun:false});window.clearTimeout(recentTimer);recentTimer=window.setTimeout(()=>recordRecentSearch(),650)},150);
}
async function runSearch(){if(!snapshot.value)return;runtime.updateSearchQuery(query.value,{replace:true});const next=await runtime.runSearchWorkspace() as SearchWorkspaceSnapshot;snapshot.value=next;recordRecentSearch()}

async function clearQuery(){
  query.value="";runtime.updateSearchQuery("",{replace:true});
  if(databaseMode.value){snapshot.value=await runtime.getSearchWorkspaceSnapshot({refresh:false,autoRun:false}) as SearchWorkspaceSnapshot;return}
  await load({refresh:false,autoRun:false});
}
async function updateMmrOption(key:"fetch_k"|"lambda_mult",value:number){
  runtime.setSearchMmrOptions({[key]:value});
  await load({refresh:false,autoRun:false});
}
async function changeScope(next:SearchScope){snapshot.value=await runtime.setSearchScope(next) as SearchWorkspaceSnapshot;if(next==="database"&&!snapshot.value.has_database&&snapshot.value.capabilities.can_manage_database){runtime.openDatabaseCreationFromResearch();return}query.value=snapshot.value.query}
async function changeStore(value:string){runtime.setSearchStore(value);await load({refresh:false,autoRun:false})}
async function changeMethod(value:SearchMethod){runtime.setSearchMethod(value);await load({refresh:false,autoRun:false})}
async function changeLayout(value:SearchLayout){runtime.setSearchLayout(value);await load({refresh:false,autoRun:false})}
async function changePageSize(value:number){runtime.setSearchPageSize(value);await load({refresh:false,autoRun:false})}
async function changePage(page:number){runtime.setSearchPage(page);await load({refresh:false,autoRun:false});document.querySelector(".search-results-panel")?.scrollIntoView({behavior:"smooth",block:"start"})}
async function sortBy(key:string){runtime.setSearchSort(key);await load({refresh:false,autoRun:false})}
async function toggleFacet(field:string,value:string){runtime.toggleSearchFacet(field,value);await load({refresh:false,autoRun:false})}
async function removeFacet(field:string,value:string){await toggleFacet(field,value)}
async function clearFacets(){runtime.clearSearchFacetFilters();await load({refresh:false,autoRun:false})}
async function clearAll(){query.value="";runtime.updateSearchQuery("",{replace:true});runtime.clearSearchAllFilters();await load({refresh:false,autoRun:false})}
async function toggleAdvanced(open:boolean){advancedOpen.value=open;runtime.setSearchAdvancedOpen(open)}
async function addAdvancedFilter(){
  const op=newFilterOp.value;const requiresValue=!['empty','notempty'].includes(op);if(requiresValue&&!newFilterValue.value.trim())return;
  runtime.addSearchAdvancedFilter({field:newFilterField.value,op,value:newFilterValue.value});newFilterValue.value="";await load({refresh:false,autoRun:false})
}
async function removeAdvancedFilter(filter:SearchFilter){runtime.removeSearchAdvancedFilter(filter.id);await load({refresh:false,autoRun:false})}
function filterOps(field:string){
  const numeric=new Set(["page_start","page_end","year","publication_year","text_length","extraction_quality","attribution_confidence","semantic_classification_confidence"]);
  const collection=new Set(["topics","concepts","persons","works_referenced","institutions_referenced","locations_referenced","events_referenced","groups_referenced","languages_referenced","document_language","quoted_speaker","quotation_chain"]);
  const base=numeric.has(field)?[["eq","search.operator_eq","equals"],["neq","search.operator_neq","not equal"],["gte","search.operator_gte","at least"],["lte","search.operator_lte","at most"],["empty","search.operator_empty","is empty"],["notempty","search.operator_notempty","is not empty"]]:collection.has(field)?[["has","search.operator_has","contains"],["nhas","search.operator_nhas","does not contain"],["eq","search.operator_eq","equals"],["neq","search.operator_neq","not equal"],["empty","search.operator_empty","is empty"],["notempty","search.operator_notempty","is not empty"]]:[["eq","search.operator_eq","equals"],["neq","search.operator_neq","not equal"],["has","search.operator_has","contains"],["nhas","search.operator_nhas","does not contain"],["empty","search.operator_empty","is empty"],["notempty","search.operator_notempty","is not empty"]];
  if(databaseMode.value){
    // Chroma metadata queries accept exact equality. Collection-style `contains`
    // is handled by the filters-only endpoint, which expands encoded metadata
    // safely before querying. Never expose an operator here that could produce
    // an invalid semantic/MMR request.
    const allowed=snapshot.value?.method==='filter'?['eq','has']:['eq'];
    return base.filter(([op])=>allowed.includes(op));
  }
  return base;
}
function onFilterFieldChange(){const ops=filterOps(newFilterField.value);if(!ops.some(([value])=>value===newFilterOp.value))newFilterOp.value=ops[0]?.[0]||"eq";newFilterValue.value=""}
function suggestionsFor(field:string){return snapshot.value?.filter_suggestions[field]||[]}

async function resultAction(result:SearchResult,action:string){await runtime.searchResultAction(result.key,action);if(action==="evidence"||action==="select")await load({refresh:false,autoRun:false})}
async function toggleResultSelected(result:SearchResult,selected:boolean){runtime.setSearchResultSelected(result.key,selected);await load({refresh:false,autoRun:false})}
async function togglePageSelected(selected:boolean){runtime.setSearchPageSelected(resultKeys.value,selected);await load({refresh:false,autoRun:false})}
async function selectionAction(action:string){runtime.runSearchSelectionAction(action);if(action==='clear')runtime.clearSearchSelection();await load({refresh:false,autoRun:false})}
async function clearSelection(){runtime.clearSearchSelection();await load({refresh:false,autoRun:false})}

function openColumns(){if(!snapshot.value)return;draftColumns.value=[...snapshot.value.columns.map(column=>column.key)];columnsDialog.value?.showModal();void nextTick(()=>columnsDialog.value?.querySelector<HTMLElement>("button,input")?.focus())}
function closeColumns(){columnsDialog.value?.close()}
function toggleDraftColumn(key:string,checked:boolean){if(checked&&!draftColumns.value.includes(key))draftColumns.value.push(key);else if(!checked)draftColumns.value=draftColumns.value.filter(item=>item!==key)}
function moveDraftColumn(key:string,direction:number){const at=draftColumns.value.indexOf(key),to=at+direction;if(at<0||to<0||to>=draftColumns.value.length)return;const next=[...draftColumns.value];[next[at],next[to]]=[next[to],next[at]];draftColumns.value=next}
async function saveColumns(){runtime.setSearchColumns(draftColumns.value);closeColumns();await load({refresh:false,autoRun:false})}
async function resetColumns(){runtime.setSearchColumns([]);closeColumns();await load({refresh:false,autoRun:false})}

function openSavedViews(){loadSavedState();viewsDialog.value?.showModal();void nextTick(()=>viewsDialog.value?.querySelector<HTMLElement>("button")?.focus())}
function closeSavedViews(){viewsDialog.value?.close()}
function openSaveView(){saveViewName.value="";saveDialog.value?.showModal();void nextTick(()=>saveDialog.value?.querySelector<HTMLInputElement>("input")?.focus())}
function closeSaveView(){saveDialog.value?.close()}
function saveCurrentView(){const name=saveViewName.value.trim();if(!name)return;const href=runtime.getSearchShareHref();const now=new Date().toISOString();const existing=savedViews.value.find(item=>item.name.toLocaleLowerCase()===name.toLocaleLowerCase());if(existing){existing.href=href;existing.updated_at=now}else savedViews.value.unshift({id:crypto.randomUUID(),name,href,created_at:now,updated_at:now});persistSavedViews();closeSaveView();runtime.notifyToast(i18n.t("search.view_saved","Search view saved"),{tone:"success"})}
async function openSavedView(view:SavedSearchView|RecentSearchEntry){viewsDialog.value?.close();snapshot.value=await runtime.restoreSearchViewFromHref(view.href) as SearchWorkspaceSnapshot;query.value=snapshot.value.query}
function removeSavedView(id:string){savedViews.value=savedViews.value.filter(item=>item.id!==id);persistSavedViews()}
async function copyLink(){try{await navigator.clipboard.writeText(runtime.getSearchShareHref());runtime.notifyToast(i18n.t("search.link_copied","Shareable search link copied"),{tone:"success"})}catch(exc){runtime.notifyToast(exc instanceof Error?exc.message:String(exc),{tone:"danger"})}}
function recordRecentSearch(){if(!snapshot.value)return;const q=query.value.trim();if(!q&&!hasFilters.value)return;const href=runtime.getSearchShareHref();const entry:RecentSearchEntry={id:crypto.randomUUID(),query:q||i18n.t("search.filtered_view","Filtered view"),scope:snapshot.value.scope,method:snapshot.value.method,href,created_at:new Date().toISOString()};recentSearches.value=[entry,...recentSearches.value.filter(item=>item.href!==href)].slice(0,12);persistRecent()}

function displayValue(value:unknown){if(value==null||value==="")return "—";if(Array.isArray(value))return value.join(", ");if(typeof value==="object")return JSON.stringify(value);if(typeof value==="boolean")return value?i18n.t("runtime.yes","Yes"):i18n.t("runtime.no","No");return String(value)}
function columnValue(result:SearchResult,key:string){if(key==="__file")return result.file_name||"—";if(key==="page_start")return result.page_span||"—";if(key==="text")return result.text;if(key==="__db_status")return result.db_status?.label||i18n.t("search.db_in_database","In DB");return result.record[key]}
function columnLabel(key:string){return snapshot.value?.available_columns.find(column=>column.key===key)?.label||key}
function columnStyle(key:string){if(!databaseMode.value)return undefined;const width=columnWidths[key];return width?{width:`${width}px`,minWidth:`${width}px`,maxWidth:key==='text'?`${Math.max(width,260)}px`:undefined}:undefined}
function startResize(event:PointerEvent,key:string){event.preventDefault();event.stopPropagation();const th=(event.currentTarget as HTMLElement).closest("th") as HTMLElement|null;if(!th)return;const startX=event.clientX,startWidth=th.getBoundingClientRect().width;const move=(moveEvent:PointerEvent)=>{columnWidths[key]=Math.max(key==='text'?260:96,Math.min(900,startWidth+(moveEvent.clientX-startX)))};const stop=()=>{window.removeEventListener('pointermove',move);persistColumnWidths()};window.addEventListener('pointermove',move);window.addEventListener('pointerup',stop,{once:true})}
function toggleText(key:string){expandedText.has(key)?expandedText.delete(key):expandedText.add(key)}
function similarityPercent(result:SearchResult){return result.similarity==null?null:Math.round(result.similarity*100)}
function onDialogCancel(event:Event,dialog:HTMLDialogElement|null){event.preventDefault();dialog?.close()}

watch(()=>route.fullPath,(next,prior)=>{if(next===prior)return;void load({refresh:false,autoRun:true})});
watch(()=>i18n.locale,()=>{void load({refresh:false,autoRun:false})});
watch(()=>shell.snapshot.activeStore,()=>{if(snapshot.value?.scope==='database')void load({refresh:false,autoRun:false})});
onMounted(()=>{loadSavedState();void load({refresh:true,autoRun:true})});
onBeforeUnmount(()=>{window.clearTimeout(localSearchTimer);window.clearTimeout(recentTimer)});
</script>

<template>
  <main class="vue-native-page search-native-page" :aria-busy="loading" aria-labelledby="search-page-title">
    <div v-if="loading&&!snapshot" class="search-page-loading" role="status"><span class="spinner"></span>{{i18n.t('search.loading','Loading Search workspace…')}}</div>
    <section v-else-if="error" class="search-page-error"><h1>{{i18n.t('search.load_failed','Could not load Search')}}</h1><p>{{error}}</p><button type="button" class="btn" @click="load()">{{i18n.t('ui.retry','Retry')}}</button></section>
    <template v-else-if="snapshot">
      <SearchWorkspaceHeader
        :scope="snapshot.scope"
        :researcher="snapshot.is_researcher"
        :total-loaded="snapshot.total_loaded_records"
        :database-count="snapshot.stores.length"
        :selected-evidence="snapshot.selected_evidence_count"
        :can-use-loaded="snapshot.has_loaded_records"
        @update:scope="changeScope"
        @save="openSaveView"
        @share="copyLink"
        @views="openSavedViews"
      />

      <section class="search-command-surface" :aria-label="i18n.t('search.search_controls','Search controls')">
        <div v-if="databaseMode" class="search-database-context">
          <label><span>{{i18n.t('search.corpus_database','Corpus database')}}</span><select class="control" :value="snapshot.active_store" @change="changeStore(($event.target as HTMLSelectElement).value)"><option v-for="store in snapshot.stores" :key="store.name" :value="store.name">{{store.name}} · {{store.count.toLocaleString(i18n.locale)}} {{i18n.t('dynamic.records','records')}}</option></select></label>
          <span class="search-database-note">{{i18n.t('search.database_context_help','Results and evidence stay bound to this corpus database.')}}</span>
        </div>
        <form class="search-command-row" @submit.prevent="databaseMode?runSearch():recordRecentSearch()">
          <label class="search-command-input">
            <span class="sr-only">{{i18n.t('search.query','Search query')}}</span>
            <AppIcon name="search"/>
            <input :value="query" type="search" :disabled="databaseMode&&snapshot.method==='filter'" :placeholder="searchPlaceholder" autocomplete="off" @input="applyQuery(($event.target as HTMLInputElement).value)" />
            <button v-if="query" type="button" class="search-query-clear" :aria-label="i18n.t('search.clear_query','Clear search query')" @click="clearQuery">×</button>
          </label>
          <button v-if="databaseMode" type="submit" class="btn primary search-run-button" :disabled="snapshot.loading||!snapshot.has_database||(snapshot.method!=='filter'&&!query.trim())"><AppIcon name="search"/>{{snapshot.loading?i18n.t('search.searching','Searching…'):i18n.t('ui.search','Search')}}</button>
        </form>
        <div v-if="activeFacetChips.length||snapshot.filters.length" class="search-active-filters" :aria-label="i18n.t('search.active_filters','Active filters')">
          <button v-for="chip in activeFacetChips" :key="`facet:${chip.field}:${chip.value}`" type="button" class="search-filter-chip" @click="removeFacet(chip.field,chip.value)"><span>{{chip.fieldLabel}}: {{chip.label}}</span><span aria-hidden="true">×</span><span class="sr-only">{{i18n.t('ui.remove','Remove')}}</span></button>
          <button v-for="filter in snapshot.filters" :key="filter.id" type="button" class="search-filter-chip advanced" @click="removeAdvancedFilter(filter)"><span>{{filter.field_label}} {{filter.op_label}} {{filter.value}}</span><span aria-hidden="true">×</span><span class="sr-only">{{i18n.t('ui.remove','Remove')}}</span></button>
          <button type="button" class="search-clear-filters" @click="clearAll">{{i18n.t('search.clear_all','Clear all')}}</button>
        </div>
        <details class="search-options" :open="advancedOpen" @toggle="toggleAdvanced(($event.currentTarget as HTMLDetailsElement).open)">
          <summary><AppIcon name="gear"/>{{i18n.t('search.search_options','Search options')}}<span v-if="snapshot.filters.length" class="badge">{{snapshot.filters.length}}</span></summary>
          <div class="search-options-body">
            <div v-if="databaseMode" class="search-method-grid">
              <fieldset class="search-method-picker"><legend>{{i18n.t('search.ranking_method','Ranking method')}}</legend><label v-for="item in ([['similarity','search.method_similarity','Similarity'],['mmr','search.method_mmr','MMR'],['filter','search.method_filter','Filters only']] as const)" :key="item[0]" :class="{selected:snapshot.method===item[0]}"><input type="radio" name="searchMethod" :value="item[0]" :checked="snapshot.method===item[0]" @change="changeMethod(item[0])"><span><b>{{i18n.t(item[1],item[2])}}</b><small>{{item[0]==='similarity'?i18n.t('search.method_similarity_short','Closest semantic matches'):item[0]==='mmr'?i18n.t('search.method_mmr_short','Relevant but less repetitive'):i18n.t('search.method_filter_short','Metadata without embeddings')}}</small></span></label></fieldset>
              <p class="search-method-help">{{methodHelp}}</p>
              <div v-if="snapshot.method==='mmr'" class="search-mmr-controls"><label><span>{{i18n.t('research.fetch_k_label','MMR candidate pool')}}</span><input class="control" type="number" min="1" max="1000" :value="snapshot.fetch_k" @change="updateMmrOption('fetch_k',Number(($event.target as HTMLInputElement).value))"></label><label><span>{{i18n.t('search.mmr_lambda','Relevance weight (λ)')}}</span><input class="control" type="number" min="0" max="1" step="0.05" :value="snapshot.lambda_mult" @change="updateMmrOption('lambda_mult',Number(($event.target as HTMLInputElement).value))"></label></div>
            </div>
            <div class="search-advanced-filter-builder">
              <div class="search-options-heading"><div><span class="section-label">{{i18n.t('search.advanced_filters','Advanced filters')}}</span><h3>{{i18n.t('search.precise_metadata_filter','Precise metadata filter')}}</h3></div><p>{{i18n.t('search.advanced_filter_help','Use field-level conditions when the facet sidebar is not specific enough.')}}</p></div>
              <div class="search-filter-builder-grid">
                <label><span>{{i18n.t('search.field','Field')}}</span><select v-model="newFilterField" class="control" @change="onFilterFieldChange"><option v-for="field in snapshot.filter_fields" :key="field.key" :value="field.key">{{field.label}}</option></select></label>
                <label><span>{{i18n.t('search.condition','Condition')}}</span><select v-model="newFilterOp" class="control"><option v-for="[value,key,fallback] in filterOps(newFilterField)" :key="value" :value="value">{{i18n.t(key,fallback)}}</option></select></label>
                <label><span>{{i18n.t('search.value','Value')}}</span><input v-model="newFilterValue" class="control" :list="`search-suggestions-${newFilterField}`" :disabled="['empty','notempty'].includes(newFilterOp)" :placeholder="i18n.t('search.filter_value_placeholder','Type or choose a value…')" @keydown.enter.prevent="addAdvancedFilter"><datalist :id="`search-suggestions-${newFilterField}`"><option v-for="value in suggestionsFor(newFilterField)" :key="value" :value="value"></option></datalist></label>
                <button type="button" class="btn search-add-filter" :disabled="!['empty','notempty'].includes(newFilterOp)&&!newFilterValue.trim()" @click="addAdvancedFilter"><AppIcon name="plus"/>{{i18n.t('research.add_filter','Add filter')}}</button>
              </div>
            </div>
          </div>
        </details>
      </section>

      <SearchSelectionBar v-if="snapshot.selection_count" :count="snapshot.selection_count" :can-review="snapshot.capabilities.can_review" :can-bulk-edit="snapshot.capabilities.can_bulk_edit" @review="selectionAction('review')" @improve="selectionAction('improve')" @bulk="selectionAction('bulk')" @clear="clearSelection"/>

      <section class="search-explorer-grid">
        <button type="button" class="btn search-mobile-filter-button" @click="facetDrawerOpen=true"><AppIcon name="filter"/>{{i18n.t('search.filters','Filters')}}<span v-if="activeFacetChips.length" class="badge">{{activeFacetChips.length}}</span></button>
        <div v-if="facetDrawerOpen" class="search-facet-scrim" @click="facetDrawerOpen=false"></div>
        <div class="search-facet-shell" :class="{open:facetDrawerOpen}"><button type="button" class="search-facet-close" :aria-label="i18n.t('ui.close','Close')" @click="facetDrawerOpen=false">×</button><SearchFacetPanel :facets="snapshot.facets" @toggle="toggleFacet" @clear="clearFacets"/></div>

        <section class="search-results-panel" aria-labelledby="search-results-title">
          <div class="search-results-toolbar">
            <div class="search-results-count"><span class="section-label">{{i18n.t('search.results','Results')}}</span><h2 id="search-results-title">{{resultSummary}}</h2><p v-if="databaseMode&&snapshot.search_has_run">{{i18n.t('search.database_result_note','Semantic result facets refine the returned candidate set; relevance remains tied to the selected ranking method.')}}</p></div>
            <div class="search-results-controls">
              <details class="search-sort-menu"><summary class="btn">{{i18n.t('search.sort','Sort')}}: {{activeSortLabel}} <span aria-hidden="true">⌄</span></summary><div class="search-sort-popover"><button v-for="item in sortOptions" :key="item.key" type="button" :class="{active:snapshot.sort.key===item.key}" @click="sortBy(item.key)">{{item.label}}<span v-if="snapshot.sort.key===item.key" aria-hidden="true">{{snapshot.sort.dir>0?'↑':'↓'}}</span></button></div></details>
              <SearchResultLayoutSwitcher :model-value="snapshot.layout" @update:model-value="changeLayout"/>
              <button v-if="databaseMode&&snapshot.layout!=='cards'" type="button" class="btn" @click="openColumns"><AppIcon name="list"/>{{i18n.t('records.columns','Columns')}}</button>
              <label class="search-page-size"><span class="sr-only">{{i18n.t('search.results_per_page','Results per page')}}</span><select class="control" :value="snapshot.page_size" @change="changePageSize(Number(($event.target as HTMLSelectElement).value))"><option v-for="size in [25,50,100,250]" :key="size" :value="size">{{size}} / {{i18n.t('search.page','page')}}</option></select></label>
            </div>
          </div>

          <div v-if="snapshot.loading" class="search-results-loading" role="status"><span class="spinner"></span>{{i18n.t('search.searching','Searching…')}}</div>
          <AccessibleEmptyState v-else-if="databaseMode&&!snapshot.has_database" icon="database" icon-tone="neutral" :title="i18n.t('search.no_database_title','No corpus database available')" :description="i18n.t('search.no_database_help','A corpus database must be created before database search can run.')"/><AccessibleEmptyState v-else-if="!snapshot.results.length&&databaseMode&&!snapshot.search_has_run" icon="search" icon-tone="neutral" :title="i18n.t('search.ready_title','Search the corpus database')" :description="i18n.t('search.ready_help','Enter a question, phrase, concept, or passage. Search options control semantic ranking and metadata constraints.')"/>
          <AccessibleEmptyState v-else-if="!snapshot.results.length" icon="search" icon-tone="neutral" :title="i18n.t('search.no_results','No matching records')" :description="i18n.t('search.no_results_help','Try a broader query, remove a filter, or choose another corpus scope.')"/>

          <div v-else-if="snapshot.layout==='cards'" class="search-result-cards">
            <article v-for="result in snapshot.results" :key="result.key" class="search-result-card" :class="{selected:result.selected}">
              <header><div><span class="section-label">{{result.record_id}}</span><h3>{{result.work||i18n.t('works.untitled','Untitled work')}}</h3></div><span v-if="databaseMode&&similarityPercent(result)!=null" class="search-relevance-badge" :title="i18n.t('search.similarity_explanation','Similarity is derived from vector distance; higher values indicate a closer semantic match.')">{{i18n.t('search.relevance','Relevance')}} {{similarityPercent(result)}}</span></header>
              <div class="search-result-meta"><span v-if="result.page_span">{{i18n.t('record.page','Page')}} {{result.page_span}}</span><span v-if="result.record.document_author">{{displayValue(result.record.document_author)}}</span><span v-if="result.db_status" :class="['db-status',result.db_status.kind]"><i></i>{{result.db_status.label}}</span></div>
              <p class="search-card-text" :class="{expanded:expandedText.has(result.key)}"><HighlightedText :text="result.text" :query="query"/></p>
              <button v-if="result.text.length>520" type="button" class="search-expand-text" @click="toggleText(result.key)">{{expandedText.has(result.key)?i18n.t('search.show_less','Show less'):i18n.t('search.show_more','Show more')}}</button>
              <div v-if="result.match_reasons.length" class="search-why-result"><span>{{i18n.t('search.why_result','Why this result')}}</span><span v-for="reason in result.match_reasons" :key="reason" class="metadata-result-pill">{{reason}}</span></div>
              <footer>
                <label v-if="result.kind==='workspace'&&snapshot.capabilities.can_select" class="search-card-select"><input type="checkbox" :checked="result.selected" @change="toggleResultSelected(result,($event.target as HTMLInputElement).checked)"><span>{{i18n.t('search.select_record','Select')}}</span></label>
                <div class="search-record-actions"><button type="button" class="btn" @click="resultAction(result,'open')">{{result.kind==='database'&&!snapshot.is_researcher?i18n.t('ui.edit','Edit'):i18n.t('record.open','Open record')}}</button><button v-if="result.evidence_available" type="button" class="btn" :class="{soft:result.evidence_selected}" @click="resultAction(result,'evidence')"><AppIcon :name="result.evidence_selected?'check':'plus'"/>{{result.evidence_selected?i18n.t('ui.selected','Selected'):i18n.t('ui.add_evidence','Add evidence')}}</button><CitationMenu @inline="resultAction(result,'citation-inline')" @full="resultAction(result,'citation-full')"/></div>
              </footer>
            </article>
          </div>

          <div v-else class="search-table-scroll" tabindex="0" :aria-label="i18n.t('search.results_table_scroll','Search results table. Scroll horizontally to reveal additional columns.')">
            <table class="search-results-table" :class="[snapshot.layout==='roomy'?'roomy':'compact',{'can-select':snapshot.capabilities.can_select,'database-search-table':databaseMode}]">
              <caption class="sr-only">{{resultSummary}}</caption>
              <thead><tr><th v-if="snapshot.capabilities.can_select" class="search-select-column"><input type="checkbox" :checked="pageAllSelected" :aria-label="i18n.t('search.select_page','Select records on this page')" @change="togglePageSelected(($event.target as HTMLInputElement).checked)"></th><th v-for="column in snapshot.columns" :key="column.key" :class="[`search-col-${column.key.replaceAll('_','-')}`,{'sticky-status':column.key==='__db_status'}]" :style="columnStyle(column.key)"><button v-if="column.key!=='__db_status'" type="button" class="search-sort-header" @click="sortBy(column.key)">{{column.label}}<span v-if="snapshot.sort.key===column.key" aria-hidden="true">{{snapshot.sort.dir>0?'↑':'↓'}}</span></button><span v-else>{{column.label}}</span><button v-if="databaseMode" type="button" class="search-column-resizer" :aria-label="i18n.tf('search.resize_column','Resize {column} column',{column:column.label})" @pointerdown="startResize($event,column.key)"></button></th><th class="search-actions-column">{{i18n.t('ui.actions','Actions')}}</th></tr></thead>
              <tbody><tr v-for="result in snapshot.results" :key="result.key" :class="{selected:result.selected}"><td v-if="snapshot.capabilities.can_select" class="search-select-column"><input type="checkbox" :checked="result.selected" :aria-label="i18n.tf('search.select_record_named','Select {record}',{record:result.record_id})" @change="toggleResultSelected(result,($event.target as HTMLInputElement).checked)"></td><td v-for="column in snapshot.columns" :key="column.key" :class="[`search-col-${column.key.replaceAll('_','-')}`,{'sticky-status':column.key==='__db_status','search-text-cell':column.key==='text'}]" :style="columnStyle(column.key)"><template v-if="column.key==='__db_status'"><span :class="['db-status',result.db_status?.kind||'exists']" :title="result.db_status?.title"><i></i>{{result.db_status?.label||i18n.t('search.db_in_database','In DB')}}</span></template><template v-else-if="column.key==='needs_review'"><span v-if="result.record.needs_review" class="review">{{i18n.t('record.needs_review','Needs review')}}</span><span v-else>—</span></template><template v-else-if="column.key==='text'"><div class="search-table-text" :class="{expanded:expandedText.has(result.key)}"><HighlightedText :text="result.text" :query="query"/></div><button v-if="result.text.length>320" type="button" class="search-expand-text" @click="toggleText(result.key)">{{expandedText.has(result.key)?i18n.t('search.show_less','Show less'):i18n.t('search.show_more','Show more')}}</button><div v-if="databaseMode&&(similarityPercent(result)!=null||result.match_reasons.length)" class="search-inline-explanation"><span v-if="similarityPercent(result)!=null" class="search-relevance-mini">{{i18n.t('search.relevance','Relevance')}} {{similarityPercent(result)}}</span><span v-for="reason in result.match_reasons" :key="reason">{{reason}}</span></div></template><template v-else>{{displayValue(columnValue(result,column.key))}}</template></td><td class="search-actions-column"><div class="search-record-actions"><button type="button" class="btn tiny" @click="resultAction(result,'open')">{{result.kind==='database'&&!snapshot.is_researcher?i18n.t('ui.edit','Edit'):i18n.t('research.open','Open')}}</button><button v-if="result.evidence_available" type="button" class="btn tiny" :class="{soft:result.evidence_selected}" @click="resultAction(result,'evidence')">{{result.evidence_selected?'✓ ':''}}{{i18n.t('ui.add_evidence','Evidence')}}</button><CitationMenu compact @inline="resultAction(result,'citation-inline')" @full="resultAction(result,'citation-full')"/></div></td></tr></tbody>
            </table>
          </div>

          <nav v-if="snapshot.pages>1" class="search-pagination" :aria-label="i18n.t('search.pagination','Search results pages')"><button type="button" class="btn" :disabled="snapshot.page<=1" @click="changePage(snapshot.page-1)">← {{i18n.t('ui.previous','Previous')}}</button><span>{{i18n.tf('search.page_of','Page {page} of {pages}',{page:snapshot.page,pages:snapshot.pages})}}</span><button type="button" class="btn" :disabled="snapshot.page>=snapshot.pages" @click="changePage(snapshot.page+1)">{{i18n.t('ui.next','Next')}} →</button></nav>
        </section>
      </section>

      <dialog ref="columnsDialog" class="search-config-dialog" aria-labelledby="search-columns-dialog-title" @cancel="onDialogCancel($event,columnsDialog)"><div class="dh"><div><span class="section-label">{{i18n.t('search.table_view','Table view')}}</span><h2 id="search-columns-dialog-title">{{i18n.t('search.configure_columns','Configure columns')}}</h2></div><button type="button" class="btn icon-only" :aria-label="i18n.t('ui.close','Close')" @click="closeColumns">×</button></div><div class="db search-column-dialog-body"><p>{{i18n.t('search.column_help','Choose the fields shown in the table and order them for this search view.')}}</p><div class="search-column-list"><div v-for="column in snapshot.available_columns" :key="column.key" class="search-column-choice" :class="{active:draftColumns.includes(column.key)}"><label><input type="checkbox" :checked="draftColumns.includes(column.key)" @change="toggleDraftColumn(column.key,($event.target as HTMLInputElement).checked)"><span>{{column.label}}</span></label><div v-if="draftColumns.includes(column.key)" class="search-column-order"><button type="button" class="btn tiny" :disabled="draftColumns.indexOf(column.key)<=0" :aria-label="i18n.tf('search.move_column_up','Move {column} up',{column:column.label})" @click="moveDraftColumn(column.key,-1)">↑</button><button type="button" class="btn tiny" :disabled="draftColumns.indexOf(column.key)>=draftColumns.length-1" :aria-label="i18n.tf('search.move_column_down','Move {column} down',{column:column.label})" @click="moveDraftColumn(column.key,1)">↓</button></div></div></div></div><div class="da"><button type="button" class="btn" @click="resetColumns">{{i18n.t('search.reset_defaults','Reset defaults')}}</button><button type="button" class="btn" @click="closeColumns">{{i18n.t('ui.cancel','Cancel')}}</button><button type="button" class="btn primary" :disabled="!draftColumns.length" @click="saveColumns">{{i18n.t('ui.apply','Apply')}}</button></div></dialog>

      <dialog ref="saveDialog" class="search-config-dialog search-save-dialog" aria-labelledby="search-save-dialog-title" @cancel="onDialogCancel($event,saveDialog)"><form @submit.prevent="saveCurrentView"><div class="dh"><div><span class="section-label">{{i18n.t('search.saved_views','Saved views')}}</span><h2 id="search-save-dialog-title">{{i18n.t('search.save_view','Save view')}}</h2></div><button type="button" class="btn icon-only" :aria-label="i18n.t('ui.close','Close')" @click="closeSaveView">×</button></div><div class="db"><label class="field"><span>{{i18n.t('search.view_name','View name')}}</span><input v-model="saveViewName" class="control" required maxlength="80" :placeholder="i18n.t('search.view_name_placeholder','e.g. Adieu passages needing review')"></label><p class="note">{{i18n.t('search.save_view_help','Saved views preserve the current shareable URL, including scope, query, filters, sort, columns, and layout.')}}</p></div><div class="da"><button type="button" class="btn" @click="closeSaveView">{{i18n.t('ui.cancel','Cancel')}}</button><button type="submit" class="btn primary" :disabled="!saveViewName.trim()">{{i18n.t('search.save_view','Save view')}}</button></div></form></dialog>

      <dialog ref="viewsDialog" class="search-config-dialog search-views-dialog" aria-labelledby="search-views-dialog-title" @cancel="onDialogCancel($event,viewsDialog)"><div class="dh"><div><span class="section-label">{{i18n.t('search.exploration_history','Exploration history')}}</span><h2 id="search-views-dialog-title">{{i18n.t('search.saved_and_recent','Saved & recent searches')}}</h2></div><button type="button" class="btn icon-only" :aria-label="i18n.t('ui.close','Close')" @click="closeSavedViews">×</button></div><div class="db search-views-body"><section><div class="search-options-heading"><div><h3>{{i18n.t('search.saved_views','Saved views')}}</h3><p>{{i18n.t('search.saved_views_help','Reusable search workspaces stored in this browser.')}}</p></div><button type="button" class="btn" @click="closeSavedViews();openSaveView()">{{i18n.t('search.save_current','Save current')}}</button></div><div v-if="savedViews.length" class="search-view-list"><article v-for="view in savedViews" :key="view.id"><button type="button" class="search-view-open" @click="openSavedView(view)"><b>{{view.name}}</b><small>{{new Date(view.updated_at).toLocaleString(i18n.locale)}}</small></button><button type="button" class="btn tiny danger" :aria-label="i18n.tf('search.delete_saved_view','Delete saved view {name}',{name:view.name})" @click="removeSavedView(view.id)">×</button></article></div><p v-else class="note">{{i18n.t('search.no_saved_views','No saved views yet.')}}</p></section><section><div class="search-options-heading"><div><h3>{{i18n.t('search.recent_searches','Recent searches')}}</h3><p>{{i18n.t('search.recent_searches_help','Recent exploration states from this browser.')}}</p></div></div><div v-if="recentSearches.length" class="search-view-list recent"><article v-for="item in recentSearches" :key="item.id"><button type="button" class="search-view-open" @click="openSavedView(item)"><b>{{item.query}}</b><small>{{item.scope==='database'?i18n.t('search.corpus_database','Corpus database'):i18n.t('search.loaded_records','Loaded records')}} · {{new Date(item.created_at).toLocaleString(i18n.locale)}}</small></button></article></div><p v-else class="note">{{i18n.t('search.no_recent_searches','No recent searches yet.')}}</p></section></div><div class="da"><button type="button" class="btn" @click="closeSavedViews">{{i18n.t('ui.close','Close')}}</button></div></dialog>
    </template>
  </main>
</template>
