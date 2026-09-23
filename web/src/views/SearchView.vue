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
import SearchAdvancedFilters from "../components/search/SearchAdvancedFilters.vue";
import SearchSelectionBar from "../components/search/SearchSelectionBar.vue";
import HighlightedText from "../components/search/HighlightedText.vue";
import UiTableColumnsDialog from "../components/ui/UiTableColumnsDialog.vue";
import type { RecentSearchEntry, SavedSearchView, SearchFilter, SearchLayout, SearchMethod, SearchResult, SearchScope, SearchWorkspaceSnapshot } from "../types/search";
import UiMenu from "../components/ui/UiMenu.vue";
import { metadataSchemasApi, type MetadataSchema, type SchemaSummary } from "../api/metadataSchemas";
import {
  chosenFilterSchemaId,
  defaultFilterSchemaId,
  filterOpsForKind,
  resolveSearchFilterFields,
  saveFilterSchemaOverride,
  type SearchFilterFieldOption,
} from "../domain/searchFilterSchema";
import { forwardVerticalWheelToDocument } from "../composables/forwardVerticalWheelToDocument";

const route=useRoute();
const i18n=useI18nStore();
const shell=useShellStore();
const snapshot=ref<SearchWorkspaceSnapshot|null>(null);
const loading=ref(true);
const error=ref("");
const query=ref("");
const facetDrawerOpen=ref(false);
const columnsDialog=ref<{open:()=>void;close:()=>void}|null>(null);
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
const noDatabase=ref(false);

const scope=computed<SearchScope>(()=>snapshot.value?.scope||"loaded");
const databaseMode=computed(()=>scope.value==="database");
const resultKeys=computed(()=>snapshot.value?.results.filter(result=>result.kind==="workspace").map(result=>result.key)||[]);
const pageAllSelected=computed(()=>Boolean(resultKeys.value.length)&&snapshot.value?.results.filter(result=>result.kind==="workspace").every(result=>result.selected));
const activeFacetChips=computed(()=>snapshot.value?.facets.flatMap(facet=>facet.values.filter(item=>item.selected).map(item=>({field:facet.field,fieldLabel:facet.label,value:item.value,label:item.label})))||[]);
const hasFilters=computed(()=>Boolean(activeFacetChips.value.length||snapshot.value?.filters.length));
const resultSummary=computed(()=>{
  const total=snapshot.value?.total||0;
  return total===1?i18n.tf("search.result_count_one", {count:total.toLocaleString(i18n.locale)}):i18n.tf("search.result_count_many", {count:total.toLocaleString(i18n.locale)});
});
const searchPlaceholder=computed(()=>databaseMode.value?i18n.t("search.database_placeholder"):i18n.t("search.loaded_placeholder"));
const methodHelp=computed(()=>snapshot.value?.method==="mmr"?i18n.t("search.mmr_help"):snapshot.value?.method==="filter"?i18n.t("search.filter_only_help"):i18n.t("search.similarity_help"));
// eslint-disable-next-line @typescript-eslint/no-unused-vars -- SA-13: preserve legacy setup binding until its owning workflow is extracted.
const selectedColumnKeys=computed(()=>snapshot.value?.columns.map(column=>column.key)||[]);
const schemaSummaries=ref<SchemaSummary[]>([]);
const schemaCache=ref<Record<string,MetadataSchema>>({});
const filterSchemaId=ref(defaultFilterSchemaId());
const associatedSchemaId=computed(()=>snapshot.value?.stores.find(item=>item.name===snapshot.value?.active_store)?.schema_id||defaultFilterSchemaId());
const schemaFilterFields=computed<SearchFilterFieldOption[]>(()=>{
  const store=snapshot.value?.stores.find(item=>item.name===snapshot.value?.active_store);
  const schema=schemaCache.value[filterSchemaId.value]||null;
  return resolveSearchFilterFields({
    schema,
    collectionFields:store?.filter_fields||[],
    availableFields:snapshot.value?.filter_fields.map(field=>field.key)||[],
    labels:(key)=>snapshot.value?.filter_fields.find(field=>field.key===key)?.label||key,
  });
});
const sortOptions=computed(()=>{
  const base=[{key:"work",label:i18n.t("field.work")},{key:"page_start",label:i18n.t("field.page_start")},{key:"record_id",label:i18n.t("field.record_id")}];
  if(databaseMode.value)base.unshift({key:"similarity",label:i18n.t("search.relevance")});
  return base;
});
const sortMenuItems=computed(()=>sortOptions.value.map(item=>({id:item.key,label:item.label,checked:snapshot.value?.sort.key===item.key})));
const activeSortLabel=computed(()=>sortOptions.value.find(item=>item.key===snapshot.value?.sort.key)?.label||i18n.t("search.sort"));
function sortState(key: string) {
  if (snapshot.value?.sort.key !== key) return "none";
  return snapshot.value.sort.dir > 0 ? "ascending" : "descending";
}

function loadColumnWidths(){try{return JSON.parse(localStorage.getItem("derridai.search.columnWidths.v1")||"{}")||{}}catch{return {}}}
// eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
function persistColumnWidths(){try{localStorage.setItem("derridai.search.columnWidths.v1",JSON.stringify(columnWidths))}catch{}}
function loadSavedState(){
  try{savedViews.value=JSON.parse(localStorage.getItem("derridai.search.savedViews.v1")||"[]")||[]}catch{savedViews.value=[]}
  try{recentSearches.value=JSON.parse(localStorage.getItem("derridai.search.recent.v1")||"[]")||[]}catch{recentSearches.value=[]}
}
// eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
function persistSavedViews(){try{localStorage.setItem("derridai.search.savedViews.v1",JSON.stringify(savedViews.value.slice(0,40)))}catch{}}
// eslint-disable-next-line no-empty -- SA-12: legacy best-effort fallback; audit user-visible failure handling separately.
function persistRecent(){try{localStorage.setItem("derridai.search.recent.v1",JSON.stringify(recentSearches.value.slice(0,12)))}catch{}}

async function load(options:{refresh?:boolean;autoRun?:boolean}={}){
  loading.value=!snapshot.value;error.value="";
  try{
    const next=await runtime.getSearchWorkspaceSnapshot({refresh:options.refresh!==false,autoRun:options.autoRun!==false}) as SearchWorkspaceSnapshot;
    snapshot.value=next;query.value=next.query;advancedOpen.value=next.advanced_open;
    shell.sync();
    const mustCreateDatabase=!next.has_database&&(next.scope==="database"||!next.has_loaded_records);
    noDatabase.value=!next.has_database&&!next.has_loaded_records;
    if(noDatabase.value)return;
    if(mustCreateDatabase&&next.capabilities.can_manage_database&&!redirectedForDatabase){redirectedForDatabase=true;runtime.notifyToast(i18n.t("search.redirect_database"),{tone:"info"});runtime.openDatabaseCreationFromResearch();return}
    redirectedForDatabase=false;
    await syncFilterSchema(next);
    if(!newFilterField.value||!schemaFilterFields.value.some(field=>field.key===newFilterField.value))newFilterField.value=schemaFilterFields.value[0]?.key||next.filter_fields[0]?.key||"work";
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
async function changeScope(next:SearchScope){snapshot.value=await runtime.setSearchScope(next) as SearchWorkspaceSnapshot;await syncFilterSchema(snapshot.value);if(next==="database"&&!snapshot.value.has_database&&snapshot.value.capabilities.can_manage_database){runtime.openDatabaseCreationFromResearch();return}query.value=snapshot.value.query}
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
async function loadSchema(id:string){
  if(!id||schemaCache.value[id])return schemaCache.value[id]||null;
  try{
    const schema=await metadataSchemasApi.get(id);
    schemaCache.value={...schemaCache.value,[id]:schema};
    return schema;
  }catch{return null}
}
async function syncFilterSchema(next:SearchWorkspaceSnapshot){
  try{
    if(!schemaSummaries.value.length)schemaSummaries.value=(await metadataSchemasApi.list()).items||[];
  }catch{schemaSummaries.value=[]}
  const store=next.stores.find(item=>item.name===next.active_store);
  filterSchemaId.value=chosenFilterSchemaId({store:next.active_store||"loaded",associatedId:store?.schema_id});
  await loadSchema(filterSchemaId.value);
}
async function changeFilterSchema(id:string){
  filterSchemaId.value=id||defaultFilterSchemaId();
  saveFilterSchemaOverride(snapshot.value?.active_store||"loaded",filterSchemaId.value===defaultFilterSchemaId()?"":filterSchemaId.value);
  await loadSchema(filterSchemaId.value);
  if(!schemaFilterFields.value.some(field=>field.key===newFilterField.value))newFilterField.value=schemaFilterFields.value[0]?.key||"work";
}
function filterOps(field:string){
  const kind=schemaFilterFields.value.find(item=>item.key===field)?.kind||"text";
  return filterOpsForKind(kind,{database:databaseMode.value,method:snapshot.value?.method});
}
function onFilterFieldChange(){const ops=filterOps(newFilterField.value);if(!ops.some(([value])=>value===newFilterOp.value))newFilterOp.value=ops[0]?.[0]||"eq";newFilterValue.value=""}
function suggestionsFor(field:string){return snapshot.value?.filter_suggestions[field]||[]}

async function resultAction(result:SearchResult,action:string){await runtime.searchResultAction(result.key,action);if(action==="evidence"||action==="select")await load({refresh:false,autoRun:false})}
async function toggleResultSelected(result:SearchResult,selected:boolean){runtime.setSearchResultSelected(result.key,selected);await load({refresh:false,autoRun:false})}
async function togglePageSelected(selected:boolean){runtime.setSearchPageSelected(resultKeys.value,selected);await load({refresh:false,autoRun:false})}
async function selectionAction(action:string){runtime.runSearchSelectionAction(action);if(action==='clear')runtime.clearSearchSelection();await load({refresh:false,autoRun:false})}
async function clearSelection(){runtime.clearSearchSelection();await load({refresh:false,autoRun:false})}

function openColumns() {
  if (!snapshot.value) return;
  draftColumns.value = snapshot.value.columns.map((column) => column.key);
  columnsDialog.value?.open();
}
// The columns dialog closes itself when its choice is applied.
async function saveColumns() {
  runtime.setSearchColumns(draftColumns.value);
  await load({ refresh: false, autoRun: false });
}
// Reset restores the default columns (an empty choice) and closes the dialog.
async function resetColumns() {
  runtime.setSearchColumns([]);
  columnsDialog.value?.close();
  await load({ refresh: false, autoRun: false });
}

function openSavedViews(){loadSavedState();viewsDialog.value?.showModal();void nextTick(()=>viewsDialog.value?.querySelector<HTMLElement>("button")?.focus())}
function closeSavedViews(){viewsDialog.value?.close()}
function openSaveView(){saveViewName.value="";saveDialog.value?.showModal();void nextTick(()=>saveDialog.value?.querySelector<HTMLInputElement>("input")?.focus())}
function closeSaveView(){saveDialog.value?.close()}
function saveCurrentView(){const name=saveViewName.value.trim();if(!name)return;const href=runtime.getSearchShareHref();const now=new Date().toISOString();const existing=savedViews.value.find(item=>item.name.toLocaleLowerCase()===name.toLocaleLowerCase());if(existing){existing.href=href;existing.updated_at=now}else savedViews.value.unshift({id:crypto.randomUUID(),name,href,created_at:now,updated_at:now});persistSavedViews();closeSaveView();runtime.notifyToast(i18n.t("search.view_saved"),{tone:"success"})}
async function openSavedView(view:SavedSearchView|RecentSearchEntry){viewsDialog.value?.close();snapshot.value=await runtime.restoreSearchViewFromHref(view.href) as SearchWorkspaceSnapshot;query.value=snapshot.value.query}
function removeSavedView(id:string){savedViews.value=savedViews.value.filter(item=>item.id!==id);persistSavedViews()}
async function copyLink(){try{await navigator.clipboard.writeText(runtime.getSearchShareHref());runtime.notifyToast(i18n.t("search.link_copied"),{tone:"success"})}catch(exc){runtime.notifyToast(exc instanceof Error?exc.message:String(exc),{tone:"danger"})}}
function recordRecentSearch(){if(!snapshot.value)return;const q=query.value.trim();if(!q&&!hasFilters.value)return;const href=runtime.getSearchShareHref();const entry:RecentSearchEntry={id:crypto.randomUUID(),query:q||i18n.t("search.filtered_view"),scope:snapshot.value.scope,method:snapshot.value.method,href,created_at:new Date().toISOString()};recentSearches.value=[entry,...recentSearches.value.filter(item=>item.href!==href)].slice(0,12);persistRecent()}

function displayValue(value:unknown){if(value==null||value==="")return "—";if(Array.isArray(value))return value.join(", ");if(typeof value==="object")return JSON.stringify(value);if(typeof value==="boolean")return value?i18n.t("runtime.yes"):i18n.t("runtime.no");return String(value)}
function columnValue(result:SearchResult,key:string){if(key==="__file")return result.file_name||"—";if(key==="page_start")return result.page_span||"—";if(key==="text")return result.text;if(key==="__db_status")return result.db_status?.label||i18n.t("search.db_in_database");return result.record[key]}
// eslint-disable-next-line @typescript-eslint/no-unused-vars -- SA-13: preserve legacy setup binding until its owning workflow is extracted.
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
  <main class="vue-native-page search-native-page" :aria-busy="loading" aria-labelledby="search-page-title" @wheel="forwardVerticalWheelToDocument">
    <div v-if="loading&&!snapshot" class="search-page-loading" role="status"><span class="spinner"></span>{{i18n.t('search.loading')}}</div>
    <section v-else-if="error" class="search-page-error"><h1>{{i18n.t('search.load_failed')}}</h1><p>{{error}}</p><button type="button" class="btn" @click="load()">{{i18n.t('ui.retry')}}</button></section>
    <AccessibleEmptyState v-else-if="noDatabase" icon="database" :title="i18n.t('search.nothing_to_search_title')" :description="snapshot?.capabilities.can_manage_database?i18n.t('search.nothing_to_search_help'):i18n.t('search.empty_state_denied')" :action-label="snapshot?.capabilities.can_manage_database?i18n.t('search.empty_state_action'):''" @action="runtime.openDatabaseCreationFromResearch()"/>
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

      <section class="search-command-surface" :aria-label="i18n.t('search.search_controls')">
        <div v-if="databaseMode" class="search-database-context">
          <label><span>{{i18n.t('search.corpus_database')}}</span><select class="control" :value="snapshot.active_store" @change="changeStore(($event.target as HTMLSelectElement).value)"><option v-for="store in snapshot.stores" :key="store.name" :value="store.name">{{store.name}} · {{store.count.toLocaleString(i18n.locale)}} {{i18n.t('dynamic.records')}}</option></select></label>
          <span class="search-database-note">{{i18n.t('search.database_context_help')}}</span>
        </div>
        <form class="search-command-row" @submit.prevent="databaseMode?runSearch():recordRecentSearch()">
          <label class="search-command-input">
            <span class="sr-only">{{i18n.t('search.query')}}</span>
            <AppIcon name="search"/>
            <input :value="query" type="search" :disabled="databaseMode&&snapshot.method==='filter'" :placeholder="searchPlaceholder" autocomplete="off" @input="applyQuery(($event.target as HTMLInputElement).value)" />
            <button v-if="query" type="button" class="search-query-clear" :aria-label="i18n.t('search.clear_query')" @click="clearQuery">×</button>
          </label>
          <button v-if="databaseMode" type="submit" class="btn primary search-run-button" :disabled="snapshot.loading||!snapshot.has_database||(snapshot.method!=='filter'&&!query.trim())"><AppIcon name="search"/>{{snapshot.loading?i18n.t('search.searching'):i18n.t('ui.search')}}</button>
        </form>
        <div v-if="activeFacetChips.length||snapshot.filters.length" class="search-active-filters" :aria-label="i18n.t('search.active_filters')">
          <button v-for="chip in activeFacetChips" :key="`facet:${chip.field}:${chip.value}`" type="button" class="search-filter-chip" @click="removeFacet(chip.field,chip.value)"><span>{{chip.fieldLabel}}: {{chip.label}}</span><span aria-hidden="true">×</span><span class="sr-only">{{i18n.t('ui.remove')}}</span></button>
          <button v-for="filter in snapshot.filters" :key="filter.id" type="button" class="search-filter-chip advanced" @click="removeAdvancedFilter(filter)"><span>{{filter.field_label}} {{filter.op_label}} {{filter.value}}</span><span aria-hidden="true">×</span><span class="sr-only">{{i18n.t('ui.remove')}}</span></button>
          <button type="button" class="search-clear-filters" @click="clearAll">{{i18n.t('search.clear_all')}}</button>
        </div>
        <details class="search-options" :open="advancedOpen" @toggle="toggleAdvanced(($event.currentTarget as HTMLDetailsElement).open)">
          <summary><AppIcon name="gear"/>{{i18n.t('search.search_options')}}<span v-if="snapshot.filters.length" class="badge">{{snapshot.filters.length}}</span></summary>
          <div class="search-options-body">
            <div v-if="databaseMode" class="search-method-grid">
              <fieldset class="search-method-picker"><legend>{{i18n.t('search.ranking_method')}}</legend><label v-for="item in ([['similarity','search.method_similarity','Similarity'],['mmr','search.method_mmr','MMR'],['filter','search.method_filter','Filters only']] as const)" :key="item[0]" :class="{selected:snapshot.method===item[0]}"><input type="radio" name="searchMethod" :value="item[0]" :checked="snapshot.method===item[0]" @change="changeMethod(item[0])"><span><b>{{i18n.t(item[1],item[2])}}</b><small>{{item[0]==='similarity'?i18n.t('search.method_similarity_short'):item[0]==='mmr'?i18n.t('search.method_mmr_short'):i18n.t('search.method_filter_short')}}</small></span></label></fieldset>
              <p class="search-method-help">{{methodHelp}}</p>
              <div v-if="snapshot.method==='mmr'" class="search-mmr-controls"><label><span>{{i18n.t('research.fetch_k_label')}}</span><input class="control" type="number" min="1" max="1000" :value="snapshot.fetch_k" @change="updateMmrOption('fetch_k',Number(($event.target as HTMLInputElement).value))"></label><label><span>{{i18n.t('search.mmr_lambda')}}</span><input class="control" type="number" min="0" max="1" step="0.05" :value="snapshot.lambda_mult" @change="updateMmrOption('lambda_mult',Number(($event.target as HTMLInputElement).value))"></label></div>
            </div>
            <SearchAdvancedFilters
              :filters="snapshot.filters"
              :fields="schemaFilterFields"
              :schemas="schemaSummaries"
              :schema-id="filterSchemaId"
              :associated-schema-id="associatedSchemaId"
              :field="newFilterField"
              :op="newFilterOp"
              :value="newFilterValue"
              :ops="filterOps(newFilterField)"
              :suggestions="suggestionsFor(newFilterField)"
              @update:field="newFilterField=$event"
              @update:op="newFilterOp=$event"
              @update:value="newFilterValue=$event"
              @schema="changeFilterSchema"
              @field-change="onFilterFieldChange"
              @add="addAdvancedFilter"
              @remove="removeAdvancedFilter"
            />
          </div>
        </details>
      </section>

      <SearchSelectionBar v-if="snapshot.selection_count" :count="snapshot.selection_count" :can-review="snapshot.capabilities.can_review" :can-bulk-edit="snapshot.capabilities.can_bulk_edit" @review="selectionAction('review')" @improve="selectionAction('improve')" @bulk="selectionAction('bulk')" @clear="clearSelection"/>

      <section class="search-explorer-grid">
        <button type="button" class="btn search-mobile-filter-button" @click="facetDrawerOpen=true"><AppIcon name="filter"/>{{i18n.t('search.filters')}}<span v-if="activeFacetChips.length" class="badge">{{activeFacetChips.length}}</span></button>
        <div v-if="facetDrawerOpen" class="search-facet-scrim" @click="facetDrawerOpen=false"></div>
        <div class="search-facet-shell" :class="{open:facetDrawerOpen}"><button type="button" class="search-facet-close" :aria-label="i18n.t('ui.close')" @click="facetDrawerOpen=false">×</button><SearchFacetPanel :facets="snapshot.facets" @toggle="toggleFacet" @clear="clearFacets"/></div>

        <section class="search-results-panel" aria-labelledby="search-results-title">
          <div class="search-results-toolbar">
            <div class="search-results-count"><span class="section-label">{{i18n.t('search.results')}}</span><h2 id="search-results-title">{{resultSummary}}</h2><p v-if="databaseMode&&snapshot.search_has_run">{{i18n.t('search.database_result_note')}}</p></div>
            <div class="search-results-controls">
              <UiMenu class="search-sort-menu" :label="`${i18n.t('search.sort')}: ${activeSortLabel}`" :items="sortMenuItems" align="end" :menu-label="i18n.t('search.sort')" @select="sortBy"/>
              <SearchResultLayoutSwitcher :model-value="snapshot.layout" @update:model-value="changeLayout"/>
              <button type="button" class="btn" @click="openColumns"><AppIcon name="list"/>{{i18n.t('records.columns')}}</button>
              <label class="search-page-size"><span class="sr-only">{{i18n.t('search.results_per_page')}}</span><select class="control" :value="snapshot.page_size" @change="changePageSize(Number(($event.target as HTMLSelectElement).value))"><option v-for="size in [25,50,100,250]" :key="size" :value="size">{{size}} / {{i18n.t('search.page')}}</option></select></label>
            </div>
          </div>

          <div v-if="snapshot.loading" class="search-results-loading" role="status"><span class="spinner"></span>{{i18n.t('search.searching')}}</div>
          <AccessibleEmptyState v-else-if="databaseMode&&!snapshot.has_database" icon="database" icon-tone="neutral" :title="i18n.t('search.no_database_title')" :description="i18n.t('search.no_database_help')"/><AccessibleEmptyState v-else-if="!snapshot.results.length&&databaseMode&&!snapshot.search_has_run" icon="search" icon-tone="neutral" :title="i18n.t('search.ready_title')" :description="i18n.t('search.ready_help')"/>
          <AccessibleEmptyState v-else-if="!snapshot.results.length" icon="search" icon-tone="neutral" :title="i18n.t('search.no_results')" :description="i18n.t('search.no_results_help')"/>

          <div v-else-if="snapshot.layout==='cards'" class="search-result-cards">
            <article v-for="result in snapshot.results" :key="result.key" class="search-result-card" :class="{selected:result.selected}">
              <header><div><span class="section-label">{{result.record_id}}</span><h3>{{result.work||i18n.t('works.untitled')}}</h3></div><span v-if="databaseMode&&similarityPercent(result)!=null" class="search-relevance-badge" :title="i18n.t('search.similarity_explanation')">{{i18n.t('search.relevance')}} {{similarityPercent(result)}}</span></header>
              <div class="search-result-meta"><span v-if="result.page_span">{{i18n.t('record.page')}} {{result.page_span}}</span><span v-if="result.record.document_author">{{displayValue(result.record.document_author)}}</span><span v-if="result.db_status" :class="['db-status',result.db_status.kind]"><i></i>{{result.db_status.label}}</span></div>
              <p class="search-card-text" :class="{expanded:expandedText.has(result.key)}"><HighlightedText :text="result.text" :query="query"/></p>
              <button v-if="result.text.length>520" type="button" class="search-expand-text" @click="toggleText(result.key)">{{expandedText.has(result.key)?i18n.t('search.show_less'):i18n.t('search.show_more')}}</button>
              <div v-if="result.match_reasons.length" class="search-why-result"><span>{{i18n.t('search.why_result')}}</span><span v-for="reason in result.match_reasons" :key="reason" class="metadata-result-pill">{{reason}}</span></div>
              <footer>
                <label v-if="result.kind==='workspace'&&snapshot.capabilities.can_select" class="search-card-select"><input type="checkbox" :checked="result.selected" @change="toggleResultSelected(result,($event.target as HTMLInputElement).checked)"><span>{{i18n.t('search.select_record')}}</span></label>
                <div class="search-record-actions"><button type="button" class="btn" @click="resultAction(result,'open')">{{result.kind==='database'&&!snapshot.is_researcher?i18n.t('ui.edit'):i18n.t('record.open')}}</button><button v-if="result.evidence_available" type="button" class="btn" :class="{soft:result.evidence_selected}" @click="resultAction(result,'evidence')"><AppIcon :name="result.evidence_selected?'check':'plus'"/>{{result.evidence_selected?i18n.t('ui.selected'):i18n.t('ui.add_evidence')}}</button><CitationMenu @inline="resultAction(result,'citation-inline')" @full="resultAction(result,'citation-full')"/></div>
              </footer>
            </article>
          </div>

          <div v-else class="search-table-scroll ui-table-scroll" tabindex="0" role="region" :aria-label="i18n.t('search.results_table_scroll')">
            <table class="search-results-table ui-table" :class="[snapshot.layout==='roomy'?'roomy':'compact',{'can-select':snapshot.capabilities.can_select,'database-search-table':databaseMode}]">
              <caption class="sr-only">{{resultSummary}}</caption>
              <thead><tr><th v-if="snapshot.capabilities.can_select" class="search-select-column ui-table-sticky-start" scope="col"><input type="checkbox" :checked="pageAllSelected" :aria-label="i18n.t('search.select_page')" @change="togglePageSelected(($event.target as HTMLInputElement).checked)"></th><th v-for="column in snapshot.columns" :key="column.key" scope="col" :aria-sort="column.key!=='__db_status'?sortState(column.key):undefined" :class="[`search-col-${column.key.replaceAll('_','-')}`,{'sticky-status ui-table-sticky-start':column.key==='__db_status'}]" :style="columnStyle(column.key)"><button v-if="column.key!=='__db_status'" type="button" class="search-sort-header" @click="sortBy(column.key)">{{column.label}}<span v-if="snapshot.sort.key===column.key" aria-hidden="true">{{snapshot.sort.dir>0?'↑':'↓'}}</span></button><span v-else>{{column.label}}</span><button v-if="databaseMode" type="button" class="search-column-resizer" :aria-label="i18n.tf('search.resize_column', {column:column.label})" @pointerdown="startResize($event,column.key)"></button></th><th class="search-actions-column ui-table-sticky-end" scope="col">{{i18n.t('ui.actions')}}</th></tr></thead>
              <tbody><tr v-for="result in snapshot.results" :key="result.key" :class="{selected:result.selected}"><td v-if="snapshot.capabilities.can_select" class="search-select-column ui-table-sticky-start"><input type="checkbox" :checked="result.selected" :aria-label="i18n.tf('search.select_record_named', {record:result.record_id})" @change="toggleResultSelected(result,($event.target as HTMLInputElement).checked)"></td><td v-for="column in snapshot.columns" :key="column.key" :class="[`search-col-${column.key.replaceAll('_','-')}`,{'sticky-status ui-table-sticky-start':column.key==='__db_status','search-text-cell':column.key==='text'}]" :style="columnStyle(column.key)"><template v-if="column.key==='__db_status'"><span :class="['db-status',result.db_status?.kind||'exists']" :title="result.db_status?.title"><i></i>{{result.db_status?.label||i18n.t('search.db_in_database')}}</span></template><template v-else-if="column.key==='needs_review'"><span v-if="result.record.needs_review" class="review">{{i18n.t('record.needs_review')}}</span><span v-else>—</span></template><template v-else-if="column.key==='text'"><div class="search-table-text" :class="{expanded:expandedText.has(result.key)}"><HighlightedText :text="result.text" :query="query"/></div><button v-if="result.text.length>320" type="button" class="search-expand-text" @click="toggleText(result.key)">{{expandedText.has(result.key)?i18n.t('search.show_less'):i18n.t('search.show_more')}}</button><div v-if="databaseMode&&(similarityPercent(result)!=null||result.match_reasons.length)" class="search-inline-explanation"><span v-if="similarityPercent(result)!=null" class="search-relevance-mini">{{i18n.t('search.relevance')}} {{similarityPercent(result)}}</span><span v-for="reason in result.match_reasons" :key="reason">{{reason}}</span></div></template><template v-else>{{displayValue(columnValue(result,column.key))}}</template></td><td class="search-actions-column ui-table-sticky-end"><div class="search-record-actions"><button type="button" class="btn tiny" @click="resultAction(result,'open')">{{result.kind==='database'&&!snapshot.is_researcher?i18n.t('ui.edit'):i18n.t('research.open')}}</button><button v-if="result.evidence_available" type="button" class="btn tiny" :class="{soft:result.evidence_selected}" @click="resultAction(result,'evidence')">{{result.evidence_selected?'✓ ':''}}{{i18n.t('ui.add_evidence')}}</button><CitationMenu compact @inline="resultAction(result,'citation-inline')" @full="resultAction(result,'citation-full')"/></div></td></tr></tbody>
            </table>
          </div>

          <nav v-if="snapshot.pages>1" class="search-pagination" :aria-label="i18n.t('search.pagination')"><button type="button" class="btn" :disabled="snapshot.page<=1" @click="changePage(snapshot.page-1)">← {{i18n.t('ui.previous')}}</button><span>{{i18n.tf('search.page_of', {page:snapshot.page,pages:snapshot.pages})}}</span><button type="button" class="btn" :disabled="snapshot.page>=snapshot.pages" @click="changePage(snapshot.page+1)">{{i18n.t('ui.next')}} →</button></nav>
        </section>
      </section>

      <UiTableColumnsDialog
        ref="columnsDialog"
        v-model="draftColumns"
        :available="snapshot.available_columns"
        :title="i18n.t('search.configure_columns')"
        :description="
          i18n.t('search.column_help')
        "
        @apply="saveColumns"
        @reset="resetColumns"
      />

      <dialog ref="saveDialog" class="search-config-dialog search-save-dialog" aria-labelledby="search-save-dialog-title" @cancel="onDialogCancel($event,saveDialog)"><form @submit.prevent="saveCurrentView"><div class="dh"><div><span class="section-label">{{i18n.t('search.saved_views')}}</span><h2 id="search-save-dialog-title">{{i18n.t('search.save_view')}}</h2></div><button type="button" class="btn icon-only" :aria-label="i18n.t('ui.close')" @click="closeSaveView">×</button></div><div class="db"><label class="field"><span>{{i18n.t('search.view_name')}}</span><input v-model="saveViewName" class="control" required maxlength="80" :placeholder="i18n.t('search.view_name_placeholder')"></label><p class="note">{{i18n.t('search.save_view_help')}}</p></div><div class="da"><button type="button" class="btn" @click="closeSaveView">{{i18n.t('ui.cancel')}}</button><button type="submit" class="btn primary" :disabled="!saveViewName.trim()">{{i18n.t('search.save_view')}}</button></div></form></dialog>

      <dialog ref="viewsDialog" class="search-config-dialog search-views-dialog" aria-labelledby="search-views-dialog-title" @cancel="onDialogCancel($event,viewsDialog)"><div class="dh"><div><span class="section-label">{{i18n.t('search.exploration_history')}}</span><h2 id="search-views-dialog-title">{{i18n.t('search.saved_and_recent')}}</h2></div><button type="button" class="btn icon-only" :aria-label="i18n.t('ui.close')" @click="closeSavedViews">×</button></div><div class="db search-views-body"><section><div class="search-options-heading"><div><h3>{{i18n.t('search.saved_views')}}</h3><p>{{i18n.t('search.saved_views_help')}}</p></div><button type="button" class="btn" @click="closeSavedViews();openSaveView()">{{i18n.t('search.save_current')}}</button></div><div v-if="savedViews.length" class="search-view-list"><article v-for="view in savedViews" :key="view.id"><button type="button" class="search-view-open" @click="openSavedView(view)"><b>{{view.name}}</b><small>{{new Date(view.updated_at).toLocaleString(i18n.locale)}}</small></button><button type="button" class="btn tiny danger" :aria-label="i18n.tf('search.delete_saved_view', {name:view.name})" @click="removeSavedView(view.id)">×</button></article></div><p v-else class="note">{{i18n.t('search.no_saved_views')}}</p></section><section><div class="search-options-heading"><div><h3>{{i18n.t('search.recent_searches')}}</h3><p>{{i18n.t('search.recent_searches_help')}}</p></div></div><div v-if="recentSearches.length" class="search-view-list recent"><article v-for="item in recentSearches" :key="item.id"><button type="button" class="search-view-open" @click="openSavedView(item)"><b>{{item.query}}</b><small>{{item.scope==='database'?i18n.t('search.corpus_database'):i18n.t('search.loaded_records')}} · {{new Date(item.created_at).toLocaleString(i18n.locale)}}</small></button></article></div><p v-else class="note">{{i18n.t('search.no_recent_searches')}}</p></section></div><div class="da"><button type="button" class="btn" @click="closeSavedViews">{{i18n.t('ui.close')}}</button></div></dialog>
    </template>
  </main>
</template>

<style scoped>
.search-page-loading,
.search-page-error {
  min-height: 320px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  text-align: center;
}
.search-page-error h1 {
  margin: 0;
  font-family: Georgia,serif;
}
.search-database-note {
  padding-bottom: 8px;
  color: var(--muted);
  font-size: .8125rem;
}
.search-run-button {
  min-width: 118px;
  min-height: 54px;
  justify-content: center;
  border-radius: 12px;
  font-size: 0.8125rem;
  font-weight: 800;
}
.search-method-grid {
  display: grid;
  grid-template-columns: minmax(0,2fr) minmax(220px,1fr);
  gap: 12px 18px;
  padding-top: 16px;
}
.search-method-help {
  margin: 0;
  color: var(--muted);
  font-size: .8125rem;
  line-height: 1.55;
}
.search-results-loading {
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: var(--muted);
  font-size: .8125rem;
}
.search-column-resizer {
  position: absolute;
  right: -12px;
  top: 0;
  width: 24px;
  height: 100%;
  border: 0;
  background: transparent;
  cursor: col-resize;
  touch-action: none;
}
.search-column-resizer::after {
  content: "";
  position: absolute;
  right: 11px;
  top: 9px;
  bottom: 9px;
  width: 2px;
  background: transparent;
}
.search-column-resizer:hover::after,
.search-column-resizer:focus-visible::after {
  background: var(--accent);
}
.search-expand-text {
  min-height: 27px;
  margin-top: 5px;
  border: 0;
  padding: 2px 0;
  background: transparent;
  color: var(--accent-fg);
  font-size: .8125rem;
  font-weight: 760;
}
.search-inline-explanation {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
  margin-top: 7px;
  color: var(--muted);
  font-size: .8125rem;
}
.search-inline-explanation>span {
  padding: 2px 5px;
  border-radius: 999px;
  background: var(--soft);
}
.search-relevance-mini {
  background: var(--blue-soft)!important;
  color: var(--text-2)!important;
  font-weight: 780;
}
.search-results-toolbar {
  position: relative;
  z-index: 80;
  overflow: visible;
}
.search-sort-menu {
  position: relative;
  z-index: 81;
}
.search-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 13px 14px;
  color: var(--muted);
  font-size: .8125rem;
}
.search-relevance-badge {
  flex: 0 0 auto;
  padding: 5px 8px;
  border-radius: 999px;
  background: var(--blue-soft);
  color: var(--text-2);
  font-size: .8125rem;
  font-weight: 820;
}
.search-why-result {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
  padding-top: 8px;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: .8125rem;
}
.search-why-result>span:first-child {
  font-weight: 780;
  color: var(--text-2);
}
@media (max-width:1050px) {
  .search-database-note {
    padding-bottom: 0;
  }
}
@media (max-width:720px) {
  .search-run-button {
    width: 100%;
  }
}
@media (max-width:720px) {
  .search-method-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width:720px) {
  .search-pagination {
    justify-content: space-between;
  }
}
@media (max-width:720px) {
  .search-pagination span {
    font-size: .8125rem;
  }
}
</style>
