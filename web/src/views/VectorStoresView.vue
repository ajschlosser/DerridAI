<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import * as runtime from "../runtime/runtime.js";
import { chromaApi } from "../api/chroma";
import { useAuthStore } from "../stores/auth";
import { useVectorStore } from "../stores/workspace";
import { corpusState } from "../state/workspaceState";
import { useI18nStore } from "../stores/i18n";
import { useShellStore } from "../stores/shell";
import AccessibleEmptyState from "../components/AccessibleEmptyState.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiCard from "../components/ui/UiCard.vue";
import UiDialog from "../components/ui/UiDialog.vue";
import UiField from "../components/ui/UiField.vue";
import UiTabs from "../components/ui/UiTabs.vue";
import VectorBackendPanel from "../components/vector/VectorBackendPanel.vue";
import VectorCollectionHero from "../components/vector/VectorCollectionHero.vue";
import VectorCollectionRail from "../components/vector/VectorCollectionRail.vue";
import VectorWorkspaceHeader from "../components/vector/VectorWorkspaceHeader.vue";
import type { ChromaConnectionUpdate, ChromaHealth, VectorCollection, VectorRecord, VectorSearchResult, VectorWorkStat } from "../types/vector";

type VectorTab = "overview" | "data" | "retrieval" | "builds" | "settings";
type BrowseMode = "works" | "records";
// Workspace fields the runtime shares with this view live in the vector store; the rest are still read from the
// runtime's own state.
type RuntimeOnlyState = {
  files: Array<{id: string; records: unknown[]}>;
  activeFileId: string | null;
  llmStatus: {models?: Array<{name: string}>} | null;
  health: Record<string, unknown> | null;
  appConfig: {embedding_provider?: string; embedding_model?: string};
};
const runtimeState = runtime.state as unknown as RuntimeOnlyState;
const vector = useVectorStore();
// The loaded files change while this view is open (a file imported or closed). The runtime edits them in place, so the
// corpus version and active file tell this view when to count them again; without that the sync buttons stayed disabled
// until you left the view and came back. (A count, not the array: an unchanged array would not re-render anything.)
const loadedFileCount = computed(() => {
  void corpusState.version;
  void corpusState.activeFileId;
  return (runtimeState.files || []).length;
});
// Shape of the shared Vector Stores fields as this view uses them (the store types them loosely).
const workspace = vector as unknown as {
  activeStore: string;
  vectorTab: string;
  vectorCollectionFilter: string;
  vectorAutoCreateRequested: boolean;
  storeBrowseMode: string;
  storePage: number;
  storePageSize: number;
  storeWork: string;
  storeQuery: string;
  storeSearchMode: string;
  stores: VectorCollection[];
};
const VECTOR_TABS: VectorTab[] = ["overview", "data", "retrieval", "builds", "settings"];

const router = useRouter();
const auth = useAuthStore();
const i18n = useI18nStore();
const shell = useShellStore();
const loading = ref(true);
const error = ref("");
const health = ref<ChromaHealth | null>(null);
const collections = ref<VectorCollection[]>([]);
const activeName = ref("");
const filter = ref(String(workspace.vectorCollectionFilter || ""));
const tab = ref<VectorTab>(VECTOR_TABS.includes(workspace.vectorTab as VectorTab) ? workspace.vectorTab as VectorTab : "overview");
const connectionOpen = ref(false);
const probing = ref(false);
const applying = ref(false);
const probeResult = ref<ChromaHealth | null>(null);
const connectionError = ref("");
const pendingCount = ref(0);
const works = ref<VectorWorkStat[]>([]);
const browseMode = ref<BrowseMode>(workspace.storeBrowseMode === "records" ? "records" : "works");
const records = ref<VectorRecord[]>([]);
const recordCount = ref(0);
const storePage = ref(Number(workspace.storePage) || 1);
const storeWork = ref(String(workspace.storeWork || ""));
const searchQuery = ref(String(workspace.storeQuery || ""));
const searchMode = ref(String(workspace.storeSearchMode || "hybrid"));
const searchResults = ref<VectorSearchResult[]>([]);
const searching = ref(false);
const role = ref("general");
const languageCodes = ref<string[]>([]);
const embeddingProvider = ref("ollama");
const embeddingModel = ref("");
const deriveEn = ref("");
const deriveFr = ref("");
const confirm = ref<{kind: "delete" | "derive"; title: string; message: string} | null>(null);
let filterTimer = 0;

const current = computed(() => collections.value.find(store => store.name === activeName.value) || null);
const visibleCollections = computed(() => {
  const needle = filter.value.trim().toLowerCase();
  return needle ? collections.value.filter(store => store.name.toLowerCase().includes(needle)) : collections.value;
});
const tabs = computed(() => [
  {id: "overview", label: i18n.t("vector.tab_overview", "Overview")},
  {id: "data", label: i18n.t("vector.tab_data", "Data")},
  {id: "retrieval", label: i18n.t("vector.tab_retrieval", "Retrieval")},
  {id: "builds", label: i18n.t("vector.tab_builds", "Builds")},
  {id: "settings", label: i18n.t("vector.tab_settings", "Settings")},
]);
const browseTabs = computed(() => [
  {id: "works", label: `${i18n.t("dashboard.works", "Works")} ${works.value.length}`},
  {id: "records", label: `${i18n.t("dashboard.records", "Records")} ${Number(current.value?.count || 0).toLocaleString(i18n.locale)}`},
]);
const contractLocked = computed(() => Boolean(current.value?.app_version && current.value.app_version !== "legacy") || Boolean(current.value?.count));
const maxPage = computed(() => Math.max(1, Math.ceil(recordCount.value / (Number(workspace.storePageSize) || 50))));
const providerLabel = computed(() => {
  const provider = current.value?.embedding_provider || "chroma";
  if (provider === "ollama") return `Ollama · ${current.value?.embedding_model || ""}`.trim();
  if (provider === "precomputed") return i18n.t("vector.provider_precomputed", "Precomputed");
  return i18n.t("vector.provider_chroma", "Chroma default");
});
const semanticUnavailable = computed(() => current.value?.embedding_provider === "precomputed" && ["similarity", "mmr"].includes(searchMode.value));

function persistWorkspace() {
  workspace.activeStore = activeName.value;
  workspace.vectorTab = tab.value;
  workspace.vectorCollectionFilter = filter.value;
  workspace.storeBrowseMode = browseMode.value;
  workspace.storePage = storePage.value;
  workspace.storeWork = storeWork.value;
  workspace.storeQuery = searchQuery.value;
  workspace.storeSearchMode = searchMode.value;
  runtime.persistPrefs();
  shell.sync();
}

function syncHealthIntoRuntime(next: ChromaHealth) {
  health.value = next;
  runtimeState.health = {...(runtimeState.health || {}), chroma: next, chroma_path: next.path};
}

async function load(options: {details?: boolean} = {}) {
  loading.value = !collections.value.length;
  error.value = "";
  try {
    const [nextHealth, stores] = await Promise.all([chromaApi.health(), chromaApi.collections()]);
    syncHealthIntoRuntime(nextHealth);
    collections.value = stores;
    if (activeName.value && !stores.some(store => store.name === activeName.value)) activeName.value = "";
    if (!activeName.value) activeName.value = String(workspace.activeStore || stores[0]?.name || "");
    if (activeName.value && !stores.some(store => store.name === activeName.value)) activeName.value = stores[0]?.name || "";
    workspace.stores = stores;
    persistWorkspace();
    pendingCount.value = runtime.pendingUpsertRows?.().length || 0;
    if (current.value) {
      role.value = current.value.collection_role || "general";
      languageCodes.value = [...(current.value.language_codes || [])];
      embeddingProvider.value = current.value.embedding_provider || "ollama";
      embeddingModel.value = current.value.embedding_model || "";
      deriveEn.value = `${current.value.name}_en`;
      deriveFr.value = `${current.value.name}_fr`;
      if (!workspace.storeSearchMode) searchMode.value = ({hybrid: "hybrid", lexical: "lexical", semantic: "similarity"} as Record<string, string>)[current.value.retrieval_mode || ""] || "hybrid";
    }
    if (options.details !== false && current.value && tab.value === "data") await loadData();
    if (workspace.vectorAutoCreateRequested && !stores.length) {
      workspace.vectorAutoCreateRequested = false;
      openCreate();
    } else if (stores.length) {
      workspace.vectorAutoCreateRequested = false;
    }
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

async function loadData() {
  if (!activeName.value) { works.value = []; records.value = []; recordCount.value = 0; return; }
  try {
    const payload = await chromaApi.works(activeName.value);
    works.value = payload.stats || (payload.works || []).map(work => ({work, count: 0}));
    if (browseMode.value === "records") {
      const params = new URLSearchParams({limit: String(workspace.storePageSize || 50), offset: String(Math.max(0, (storePage.value - 1) * (workspace.storePageSize || 50)))});
      if (storeWork.value) params.set("work", storeWork.value);
      const page = await chromaApi.records(activeName.value, params);
      records.value = page.records || [];
      recordCount.value = page.count || 0;
    }
  } catch (exc) {
    runtime.notifyToast(exc instanceof Error ? exc.message : String(exc), {tone: "danger"});
  }
}

function openCreate() {
  const models = runtimeState.llmStatus?.models || [];
  runtime.openCollectionCreationWizard({
    defaultProvider: runtimeState.appConfig?.embedding_provider || "ollama",
    defaultModel: runtimeState.appConfig?.embedding_model || "bge-m3:latest",
    installedModels: models,
  } as never);
}

async function probe(body: ChromaConnectionUpdate) {
  probing.value = true; connectionError.value = ""; probeResult.value = null;
  try { probeResult.value = await chromaApi.probe(body); }
  catch (exc) { connectionError.value = i18n.tf("vector.connection_failed", "Could not reach Chroma: {message}", {message: exc instanceof Error ? exc.message : String(exc)}); }
  finally { probing.value = false; }
}

async function applyConnection(body: ChromaConnectionUpdate) {
  applying.value = true; connectionError.value = "";
  try {
    const next = await chromaApi.setConnection(body);
    syncHealthIntoRuntime(next);
    connectionOpen.value = false;
    runtime.notifyToast(i18n.t("vector.connection_changed", "Chroma connection updated. Existing collections were not moved."), {tone: "success"});
    activeName.value = "";
    await load();
  } catch (exc) {
    connectionError.value = i18n.tf("vector.connection_failed", "Could not reach Chroma: {message}", {message: exc instanceof Error ? exc.message : String(exc)});
  } finally { applying.value = false; }
}

function selectCollection(name: string) {
  activeName.value = name;
  tab.value = "overview";
  browseMode.value = "works";
  storePage.value = 1;
  storeWork.value = "";
  searchResults.value = [];
  persistWorkspace();
  void load({details: false});
}

function setTab(next: string) {
  tab.value = (tabs.value.some(item => item.id === next) ? next : "overview") as VectorTab;
  persistWorkspace();
  if (tab.value === "data") void loadData();
}

function setBrowse(next: string) {
  browseMode.value = next === "records" ? "records" : "works";
  if (browseMode.value === "records") { storeWork.value = ""; storePage.value = 1; }
  persistWorkspace();
  void loadData();
}

function openWork(work: string) {
  storeWork.value = work;
  browseMode.value = "records";
  storePage.value = 1;
  tab.value = "data";
  persistWorkspace();
  void loadData();
}

async function runSearch() {
  if (!activeName.value || !searchQuery.value.trim() || semanticUnavailable.value) return;
  searching.value = true;
  persistWorkspace();
  try {
    const payload = await chromaApi.search(activeName.value, {query: searchQuery.value.trim(), mode: searchMode.value, n_results: 30});
    searchResults.value = payload.results || [];
  } catch (exc) {
    runtime.notifyToast(exc instanceof Error ? exc.message : String(exc), {tone: "danger"});
  } finally { searching.value = false; }
}

async function saveLanguages() {
  if (!activeName.value) return;
  try {
    await chromaApi.setLanguages(activeName.value, {language_codes: languageCodes.value, collection_role: role.value});
    runtime.notifyToast(i18n.t("vector.language_tags_saved", "Collection language tags saved"), {tone: "success"});
    await load();
  } catch (exc) { runtime.notifyToast(exc instanceof Error ? exc.message : String(exc), {tone: "danger"}); }
}

async function saveEmbedding() {
  if (!activeName.value || contractLocked.value) return;
  if (embeddingProvider.value === "ollama" && !embeddingModel.value.trim()) return runtime.notifyToast(i18n.t("vector.embedding_model_required", "Choose an Ollama embedding model"), {tone: "warn"});
  try {
    await chromaApi.setEmbedding(activeName.value, {embedding_provider: embeddingProvider.value, embedding_model: embeddingProvider.value === "ollama" ? embeddingModel.value.trim() : null});
    runtime.notifyToast(i18n.t("vector.embedding_saved", "Embedding settings saved"), {tone: "success"});
    await load();
  } catch (exc) { runtime.notifyToast(exc instanceof Error ? exc.message : String(exc), {tone: "danger"}); }
}

async function toggleProtection() {
  if (!current.value) return;
  try {
    await chromaApi.setProtection(current.value.name, !current.value.protected);
    runtime.notifyToast(current.value.protected ? i18n.t("vector.protection_disabled", "Deletion protection disabled") : i18n.t("vector.protection_enabled", "Deletion protection enabled"), {tone: "success"});
    await load();
  } catch (exc) { runtime.notifyToast(exc instanceof Error ? exc.message : String(exc), {tone: "danger"}); }
}

async function confirmAction() {
  const kind = confirm.value?.kind;
  confirm.value = null;
  if (kind === "delete") {
    if (!activeName.value) return;
    try {
      await chromaApi.remove(activeName.value);
      activeName.value = "";
      runtime.notifyToast(i18n.t("vector.collection_deleted", "Collection deleted"), {tone: "success"});
      await load();
    } catch (exc) { runtime.notifyToast(exc instanceof Error ? exc.message : String(exc), {tone: "danger"}); }
  }
  if (kind === "derive") {
    if (!activeName.value || !deriveEn.value.trim() || !deriveFr.value.trim()) return;
    try {
      await chromaApi.deriveLanguages(activeName.value, {en_name: deriveEn.value.trim(), fr_name: deriveFr.value.trim(), overwrite: true});
      runtime.notifyToast(i18n.t("vector.language_collections", "Language databases"), {tone: "success"});
      await load();
    } catch (exc) { runtime.notifyToast(exc instanceof Error ? exc.message : String(exc), {tone: "danger"}); }
  }
}

function syncActive() {
  const file = runtimeState.files?.find(item => item.id === runtimeState.activeFileId);
  if (!file) return runtime.notifyToast(i18n.t("vector.load_jsonl_first", "Load and select a JSONL file first."), {tone: "warn"});
  void runtime.upsertRows(file.records.map((record: unknown, index: number) => ({file, record, index})), "records").then(() => load());
}
function syncAll() {
  const rows = (runtimeState.files || []).flatMap(file => file.records.map((record, index) => ({file, record, index})));
  if (!rows.length) return runtime.notifyToast(i18n.t("vector.load_jsonl_any_first", "Load at least one JSONL file first."), {tone: "warn"});
  void runtime.upsertRows(rows, "records").then(() => load());
}

function snippet(text: unknown) {
  const value = String(text || "").replace(/\s+/g, " ").trim();
  return value.length > 280 ? `${value.slice(0, 277)}…` : value;
}
function toggleLanguage(code: string, checked: boolean) {
  if (checked && !languageCodes.value.includes(code)) languageCodes.value = [...languageCodes.value, code];
  else if (!checked) languageCodes.value = languageCodes.value.filter(item => item !== code);
}

async function redirectResearcher() {
  await runtime.setSearchScope("database");
  await router.replace("/search");
}

function onStoresChanged() { void load(); }
watch(filter, value => {
  window.clearTimeout(filterTimer);
  filterTimer = window.setTimeout(() => persistWorkspace(), 140);
  workspace.vectorCollectionFilter = value;
});
watch(() => i18n.locale, () => { void load({details: false}); });
onMounted(async () => {
  if (auth.isResearcher) { await redirectResearcher(); return; }
  window.addEventListener("derridai:vector-stores-changed", onStoresChanged);
  await load();
});
onBeforeUnmount(() => {
  window.clearTimeout(filterTimer);
  window.removeEventListener("derridai:vector-stores-changed", onStoresChanged);
});
</script>

<template>
  <main class="vue-native-page vector-native-page" :aria-busy="loading" aria-labelledby="vector-page-title">
    <div v-if="auth.isResearcher" class="vector-page-loading" role="status"><span class="spinner"></span>{{ i18n.t("search.redirect_database", "Opening corpus search…") }}</div>
    <div v-else-if="loading && !collections.length && !error" class="vector-page-loading" role="status"><span class="spinner"></span>{{ i18n.t("vector.loading_stores", "Loading Vector Stores…") }}</div>
    <section v-else-if="error" class="vector-page-error">
      <h1 id="vector-page-title">{{ i18n.t("nav.vector", "Vector Stores") }}</h1>
      <p>{{ error }}</p>
      <UiButton :label="i18n.t('ui.retry', 'Retry')" @click="load()" />
    </section>
    <template v-else>
      <VectorWorkspaceHeader :health="health" :collection-count="collections.length" @create="openCreate" @connection="connectionOpen = true; probeResult = null; connectionError = ''" />

      <AccessibleEmptyState
        v-if="!collections.length"
        icon="database"
        :title="i18n.t('vector.empty_title', 'Create your first corpus collection')"
        :description="i18n.t('vector.empty_help', 'A vector collection gives DerridAI a persistent corpus database for semantic search, researcher browsing, and RAG. Configure the collection first, then optionally sync any works already loaded in the browser workspace.')"
        :action-label="i18n.t('vector.create_first_collection', 'Create first collection')"
        @action="openCreate"
      />

      <section v-else class="storegrid vector-store-layout vector-workspace-v0371">
        <VectorCollectionRail
          :collections="visibleCollections"
          :active-name="activeName"
          :filter="filter"
          @update:filter="filter = $event"
          @select="selectCollection"
          @refresh="load()"
          @create="openCreate"
        />
        <article class="vector-store-main">
          <AccessibleEmptyState
            v-if="!current"
            icon="database"
            icon-tone="neutral"
            :title="i18n.t('vector.select_collection', 'Select a collection')"
            :description="i18n.t('vector.select_collection_help', 'Choose a collection from the list to manage settings, sync records, search, or browse its contents.')"
          />
          <template v-else>
            <VectorCollectionHero
              :collection="current"
              :pending-count="pendingCount"
              @sync="runtime.triggerUpsertQueue()"
              @retrieval="setTab('retrieval')"
              @protection="toggleProtection"
              @delete="confirm = {kind: 'delete', title: i18n.t('vector.delete_collection', 'Delete collection'), message: i18n.tf('vector.delete_collection_confirm', 'Delete Chroma collection {name}? This cannot be undone.', {name: current.name})}"
            />
            <UiTabs :tabs="tabs" :model-value="tab" id-prefix="vector-section" :tablist-label="i18n.t('vector.workspace_sections', 'Collection sections')" @update:model-value="setTab" />

            <section v-show="tab === 'overview'" id="vector-section-panel-overview" class="vector-tab-surface" role="tabpanel" aria-labelledby="vector-section-tab-overview">
              <div class="vector-overview-grid">
                <article class="card vector-overview-card"><span>{{ i18n.t("vector.sync_state", "Sync state") }}</span><b>{{ pendingCount ? i18n.tf("vector.changes_pending", "{count} changes pending", {count: pendingCount.toLocaleString(i18n.locale)}) : i18n.t("vector.current", "Current") }}</b><small>{{ current.last_synced_at ? i18n.tf("vector.synced_at", "Last synced {time}", {time: new Date(current.last_synced_at).toLocaleString(i18n.locale)}) : i18n.t("vector.never_synced", "Not yet synced") }}</small></article>
                <article class="card vector-overview-card"><span>{{ i18n.t("vector.retrieval_contract", "Retrieval contract") }}</span><b>{{ current.retrieval_mode || "semantic" }} · {{ current.distance_metric || "l2" }}{{ current.embedding_dimension ? ` · ${Number(current.embedding_dimension).toLocaleString(i18n.locale)}d` : "" }}</b><small>{{ providerLabel }}</small></article>
                <article class="card vector-overview-card"><span>{{ i18n.t("vector.source", "Source") }}</span><b>{{ current.source_label || current.source_kind || i18n.t("vector.source_unrecorded", "Not recorded") }}</b><small>{{ Number(current.source_record_count || current.count || 0).toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records", "records") }}</small></article>
                <article class="card vector-overview-card"><span>{{ i18n.t("vector.current_build", "Current build") }}</span><b>{{ current.build_id ? current.build_id.slice(-12) : i18n.t("vector.no_build", "No build yet") }}</b><small>{{ (current.build_history || []).length.toLocaleString(i18n.locale) }} {{ i18n.t("vector.completed_builds", "completed builds") }}</small></article>
              </div>
              <div v-if="current.last_build_error" class="info warn" role="status"><b>{{ i18n.t("vector.last_build_error", "Last build error") }}</b><span>{{ current.last_build_error }}</span></div>
            </section>

            <section v-show="tab === 'data'" id="vector-section-panel-data" class="card vector-browser-card vector-tab-surface" role="tabpanel" aria-labelledby="vector-section-tab-data">
              <UiTabs :tabs="browseTabs" :model-value="browseMode" id-prefix="vector-browse" :tablist-label="i18n.t('vector.browse_works', 'Browse works')" @update:model-value="setBrowse" />
              <div v-show="browseMode === 'works'" id="vector-browse-panel-works" role="tabpanel" aria-labelledby="vector-browse-tab-works" class="db-work-grid">
                <button v-for="item in works" :key="item.work" type="button" class="db-work-card" @click="openWork(item.work)"><span><b>{{ item.work }}</b><small>{{ i18n.t("vector.open_work_records", "Open records") }}</small></span><strong>{{ item.count == null ? "—" : Number(item.count).toLocaleString(i18n.locale) }}</strong></button>
                <p v-if="!works.length" class="note">{{ i18n.t("research.no_work_metadata", "No work metadata was found in this collection.") }}</p>
              </div>
              <div v-show="browseMode === 'records'" id="vector-browse-panel-records" role="tabpanel" aria-labelledby="vector-browse-tab-records">
                <div class="toolbar store-record-toolbar">
                  <div><b>{{ storeWork || i18n.t("research.all_records", "All records") }}</b><div class="note">{{ recordCount.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records", "records") }} · {{ i18n.t("dynamic.page", "page") }} {{ storePage }} {{ i18n.t("research.of", "of") }} {{ maxPage }}</div></div>
                  <div class="tools">
                    <label class="sr-only" for="vector-store-work">{{ i18n.t("dashboard.works", "Works") }}</label>
                    <select id="vector-store-work" class="control" :value="storeWork" @change="storeWork = ($event.target as HTMLSelectElement).value; storePage = 1; persistWorkspace(); loadData()">
                      <option value="">{{ i18n.t("dashboard.all_works", "All works") }}</option>
                      <option v-for="item in works" :key="item.work" :value="item.work">{{ item.work }}</option>
                    </select>
                    <UiButton :label="i18n.t('ui.previous', 'Previous')" :disabled="storePage <= 1" @click="storePage -= 1; persistWorkspace(); loadData()" />
                    <UiButton :label="i18n.t('ui.next', 'Next')" :disabled="storePage >= maxPage" @click="storePage += 1; persistWorkspace(); loadData()" />
                  </div>
                </div>
                <div
                  class="tablewrap ui-table-scroll"
                  role="region"
                  :aria-label="i18n.t('dashboard.records', 'Records')"
                  tabindex="0"
                >
                  <table class="store-table ui-table">
                    <caption class="sr-only">{{ i18n.t("dashboard.records", "Records") }}</caption>
                    <thead><tr><th scope="col">{{ i18n.t("field.work", "Work") }}</th><th scope="col">{{ i18n.t("field.record_id", "Record ID") }}</th><th scope="col">{{ i18n.t("record.page", "Page") }}</th><th scope="col">{{ i18n.t("record.text", "Text") }}</th></tr></thead>
                    <tbody>
                      <tr v-for="record in records" :key="String(record._chroma_id || record.record_id)">
                        <td>{{ record.work || "—" }}</td>
                        <td>{{ record.record_id || record._chroma_id || "—" }}</td>
                        <td>{{ record.page_start ?? "—" }}{{ record.page_end && record.page_end !== record.page_start ? `–${record.page_end}` : "" }}</td>
                        <td>{{ snippet(record.text) }}</td>
                      </tr>
                      <tr v-if="!records.length"><td colspan="4" class="note">{{ i18n.t("vector.no_matching_records", "No records match the current filters.") }}</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </section>

            <section v-show="tab === 'retrieval'" id="vector-section-panel-retrieval" class="card vector-search-card vector-tab-surface" role="tabpanel" aria-labelledby="vector-section-tab-retrieval">
              <div class="cardhead"><div><b>{{ i18n.t("vector.test_retrieval", "Test retrieval") }}</b><div class="note">{{ i18n.t("vector.test_retrieval_help", "Compare the collection's semantic, lexical, hybrid, and diversity-aware retrieval behavior against the same stored corpus.") }}</div></div></div>
              <form class="vector-search-config" @submit.prevent="runSearch">
                <UiField :label="i18n.t('vector.search_method', 'Search method')">
                  <select class="control" v-model="searchMode">
                    <option value="hybrid">{{ i18n.t("vector.hybrid", "Hybrid") }}</option>
                    <option value="similarity">{{ i18n.t("vector.semantic", "Semantic") }}</option>
                    <option value="lexical">{{ i18n.t("vector.lexical", "Lexical (BM25)") }}</option>
                    <option value="mmr">MMR</option>
                  </select>
                </UiField>
                <div class="vector-search-row">
                  <label class="sr-only" for="vector-store-query">{{ i18n.t("vector.test_retrieval", "Test retrieval") }}</label>
                  <input id="vector-store-query" class="control" v-model="searchQuery" :placeholder="i18n.t('vector.retrieval_search_placeholder', 'Search this collection…')" autocomplete="off">
                  <UiButton type="submit" variant="primary" :label="searching ? i18n.t('search.searching', 'Searching…') : i18n.t('ui.search', 'Search')" :disabled="searching || semanticUnavailable" :disabled-reason="i18n.t('vector.precomputed_search_help', 'Precomputed collections can use lexical or hybrid search, but semantic and MMR query embedding require an embedding function.')" />
                  <UiButton type="button" :label="i18n.t('ui.clear', 'Clear')" @click="searchQuery = ''; searchResults = []; persistWorkspace()" />
                </div>
              </form>
              <div class="vector-search-results">
                <article v-for="result in searchResults" :key="String(result.id || result.record?._chroma_id || result.record?.record_id)" class="result store-result">
                  <div class="result-main">
                    <div class="note">{{ result.hybrid_score != null ? `${i18n.t("vector.hybrid_score", "Hybrid")} ${Number(result.hybrid_score).toFixed(4)}` : (result.distance != null ? Number(result.distance).toFixed(4) : "") }}</div>
                    <b>{{ result.record?.work || result.record?.record_id || result.id }}</b>
                    <div class="textcell">{{ snippet(result.record?.text) }}</div>
                  </div>
                </article>
                <p v-if="!searchResults.length" class="note">{{ i18n.t("vector.search_results_empty", "Search results will appear here.") }}</p>
              </div>
            </section>

            <section v-show="tab === 'builds'" id="vector-section-panel-builds" class="card vector-manifest-card vector-tab-surface" role="tabpanel" aria-labelledby="vector-section-tab-builds">
              <div class="cardhead"><div><b>{{ i18n.t("vector.manifest_builds", "Manifest & builds") }}</b><div class="note">{{ i18n.t("vector.manifest_builds_help", "Inspect the reproducible retrieval contract, source snapshot, and recent completed build history for this collection.") }}</div></div><span class="badge">v{{ current.manifest_version || 1 }}</span></div>
              <dl class="manifest-review vector-manifest-review">
                <div><dt>{{ i18n.t("vector.status", "Status") }}</dt><dd>{{ String(current.status || (current.count ? "ready" : "empty")) }}</dd></div>
                <div><dt>{{ i18n.t("vector.retrieval_mode", "Retrieval") }}</dt><dd>{{ current.retrieval_mode || "semantic" }}</dd></div>
                <div><dt>{{ i18n.t("vector.embedding_dimension", "Dimension") }}</dt><dd>{{ current.embedding_dimension ? Number(current.embedding_dimension).toLocaleString(i18n.locale) : "—" }}</dd></div>
                <div><dt>{{ i18n.t("vector.distance_metric", "Metric") }}</dt><dd>{{ current.distance_metric || "l2" }}</dd></div>
                <div><dt>{{ i18n.t("vector.text_field", "Text field") }}</dt><dd><code>{{ current.text_field || "text" }}</code></dd></div>
                <div><dt>{{ i18n.t("vector.source_records", "Source records") }}</dt><dd>{{ Number(current.source_record_count || 0).toLocaleString(i18n.locale) }}</dd></div>
                <div><dt>{{ i18n.t("vector.created_with", "Created with") }}</dt><dd>{{ current.app_version || "legacy" }}</dd></div>
              </dl>
              <details class="vector-build-history" :open="!(current.build_history || []).length">
                <summary>{{ i18n.tf("vector.build_history", "Build history ({count})", {count: (current.build_history || []).length}) }}</summary>
                <div v-if="current.build_history?.length" class="vector-build-list">
                  <article v-for="build in [...current.build_history].reverse()" :key="String(build.build_id)">
                    <div><b>{{ build.build_id || i18n.t("vector.build", "Build") }}</b></div>
                    <small>{{ build.finished_at || build.created_at || "" }} · {{ Number(build.record_count || 0).toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records", "records") }}</small>
                  </article>
                </div>
                <p v-else class="note">{{ i18n.t("vector.no_build_history", "No completed synchronization build has been recorded yet.") }}</p>
              </details>
            </section>

            <div v-show="tab === 'settings'" id="vector-section-panel-settings" class="vector-tab-surface" role="tabpanel" aria-labelledby="vector-section-tab-settings">
              <div class="vector-settings-grid">
                <UiCard>
                  <div class="cardhead"><div><b>{{ i18n.t("vector.role_language_title", "Role & language") }}</b><div class="note">{{ i18n.t("vector.role_language_help", "Collection role and language tags describe how this database should be used.") }}</div></div></div>
                  <div class="vector-settings-body">
                    <UiField :label="i18n.t('vector.collection_role', 'Collection role')">
                      <select class="control" v-model="role">
                        <option value="primary">{{ i18n.t("vector.role_primary", "Primary") }}</option>
                        <option value="general">{{ i18n.t("vector.role_general", "General") }}</option>
                        <option value="language">{{ i18n.t("vector.role_language", "Language-specific") }}</option>
                      </select>
                    </UiField>
                    <fieldset class="vector-inline-fieldset">
                      <legend>{{ i18n.t("vector.language_tags", "Language tags") }}</legend>
                      <div class="language-checks">
                        <label v-for="code in ['en', 'fr']" :key="code"><input type="checkbox" :checked="languageCodes.includes(code)" @change="toggleLanguage(code, ($event.target as HTMLInputElement).checked)"><span>{{ code }}</span></label>
                      </div>
                    </fieldset>
                    <UiButton :label="i18n.t('ui.save', 'Save')" @click="saveLanguages" />
                  </div>
                </UiCard>
                <UiCard>
                  <div class="cardhead"><div><b>{{ i18n.t("vector.embedding_configuration", "Embedding configuration") }}</b><div class="note">{{ contractLocked ? i18n.t("vector.embedding_locked_help", "Embedding settings are immutable for this collection contract. Create a new collection/build to change them.") : i18n.t("vector.embedding_edit_help", "Choose how DerridAI creates vectors for this collection.") }}</div></div></div>
                  <div class="vector-settings-body">
                    <UiField :label="i18n.t('vector.embedding_provider', 'Provider')">
                      <select class="control" v-model="embeddingProvider" :disabled="contractLocked">
                        <option value="ollama">Ollama</option>
                        <option value="chroma">{{ i18n.t("vector.provider_chroma", "Chroma default") }}</option>
                        <option value="precomputed">{{ i18n.t("vector.provider_precomputed", "Precomputed") }}</option>
                      </select>
                    </UiField>
                    <UiField :label="i18n.t('vector.embedding_model', 'Model')">
                      <input class="control" v-model="embeddingModel" :disabled="contractLocked || embeddingProvider !== 'ollama'" placeholder="bge-m3:latest">
                    </UiField>
                    <UiButton :label="i18n.t('ui.save', 'Save')" :disabled="contractLocked" @click="saveEmbedding" />
                  </div>
                </UiCard>
              </div>
              <UiCard class="vector-transfer-card">
                <div class="cardhead"><div><b>{{ i18n.t("vector.import_export", "Import & export records") }}</b><div class="note">{{ i18n.t("vector.import_export_help", "Sync loaded JSONL records into this collection, or export collection records back to clean JSONL. Exporting does not modify the collection.") }}</div></div></div>
                <div class="vector-transfer-groups">
                  <div>
                    <span class="section-label">{{ i18n.t("vector.sync_into_collection", "Sync into collection") }}</span>
                    <div class="store-actions">
                      <UiButton :label="i18n.t('vector.sync_active_jsonl', 'Sync active JSONL')" icon="database" :disabled="!loadedFileCount" @click="syncActive" />
                      <UiButton :label="i18n.t('vector.sync_all_loaded', 'Sync all loaded JSONL')" icon="database" :disabled="!loadedFileCount" @click="syncAll" />
                    </div>
                  </div>
                  <div>
                    <span class="section-label">{{ i18n.t("vector.export_from_collection", "Export from collection") }}</span>
                    <div class="store-actions">
                      <UiButton :label="i18n.t('vector.open_db_jsonl', 'Open full collection as JSONL')" icon="download" @click="runtime.exportStoreJsonl({loadTab: true})" />
                      <UiButton :label="i18n.t('vector.download_db_jsonl', 'Download full collection JSONL')" icon="download" @click="runtime.exportStoreJsonl({downloadFile: true})" />
                    </div>
                  </div>
                </div>
              </UiCard>
              <UiCard v-if="current.collection_role !== 'language' && current.name !== '_response_cache'">
                <div class="cardhead"><div><b>{{ i18n.t("vector.language_collections", "Language databases") }}</b><div class="note">{{ i18n.t("vector.language_derive_help", "Create separate English and French collections by routing records according to document_language metadata.") }}</div></div></div>
                <div class="language-database-grid">
                  <UiField :label="i18n.t('vector.english_collection', 'English collection')" :hint="i18n.t('vector.english_collection_help', 'Receives records routed as English.')"><input class="control" v-model="deriveEn"></UiField>
                  <UiField :label="i18n.t('vector.french_collection', 'French collection')" :hint="i18n.t('vector.french_collection_help', 'Receives records routed as French.')"><input class="control" v-model="deriveFr"></UiField>
                  <UiButton :label="i18n.t('vector.generate_language_collections', 'Create language databases')" variant="primary" icon="database" @click="confirm = {kind: 'derive', title: i18n.t('vector.generate_language_collections', 'Create language databases'), message: i18n.tf('vector.derive_confirm', 'Generate {en} and {fr} from {source}?', {en: deriveEn, fr: deriveFr, source: current.name})}" />
                </div>
              </UiCard>
            </div>
          </template>
        </article>
      </section>
    </template>

    <UiDialog
      :open="connectionOpen"
      :title="i18n.t('vector.connection', 'Chroma connection')"
      :description="i18n.t('vector.change_storage_location_help', 'Advanced deployment setting. Existing collections are not moved automatically.')"
      :close-label="i18n.t('ui.close', 'Close')"
      size="large"
      @close="connectionOpen = false"
    >
      <VectorBackendPanel :health="health" :probing="probing" :applying="applying" :probe-result="probeResult" :error="connectionError" @probe="probe" @apply="applyConnection" />
    </UiDialog>
    <UiDialog
      :open="Boolean(confirm)"
      :title="confirm?.title || ''"
      :description="confirm?.message || ''"
      :close-label="i18n.t('ui.close', 'Close')"
      size="medium"
      @close="confirm = null"
    >
      <div class="vector-confirm-actions">
        <UiButton :label="i18n.t('ui.cancel', 'Cancel')" @click="confirm = null" />
        <UiButton :label="confirm?.kind === 'delete' ? i18n.t('vector.delete_collection', 'Delete collection') : i18n.t('vector.generate_language_collections', 'Create language databases')" :variant="confirm?.kind === 'delete' ? 'danger' : 'primary'" @click="confirmAction" />
      </div>
    </UiDialog>
  </main>
</template>

<style scoped>
.vector-native-page{display:grid;gap:var(--page-gap)}
.vector-page-loading,.vector-page-error{min-height:240px;display:grid;place-content:center;gap:10px;text-align:center}
.vector-tab-surface{margin-top:12px}
.vector-search-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:8px;align-items:center}
.vector-confirm-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap}
.vector-native-page :deep(.control){min-height:40px}
.vector-native-page :is(button,input,select,textarea,summary):focus-visible{outline:3px solid var(--focus-ring,var(--accent));outline-offset:2px}
@media(max-width:760px){.vector-search-row{grid-template-columns:1fr}}
.store-result {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}
.result-main {
  min-width: 0;
  flex: 1;
}
.vector-store-layout {
  display: grid!important;
  grid-template-columns: minmax(230px,280px) minmax(0,1fr)!important;
  gap: 12px!important;
  align-items: start;
}
.vector-store-main {
  display: grid;
  gap: 10px;
  min-width: 0;
}
.vector-search-results {
  padding: 0 12px 12px;
}
@media (max-width:1050px) {
  .vector-store-layout {
    grid-template-columns: 220px minmax(0,1fr)!important;
  }
}
@media (max-width:760px) {
  .vector-store-layout {
    grid-template-columns: 1fr!important;
  }
}
.vector-manifest-card {
  display: grid;
  gap: 14px;
}
.vector-manifest-review {
  margin-top: 0;
}
.vector-build-history {
  border-top: 1px solid var(--line);
  padding-top: 12px;
}
.vector-build-history>summary {
  cursor: pointer;
  font-weight: 700;
}
.vector-build-list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}
.vector-build-list article {
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--panel-2);
}
.vector-build-list article>div {
  display: flex;
  gap: 8px;
  justify-content: space-between;
  align-items: center;
}
.vector-build-list small {
  display: block;
  margin-top: 4px;
  color: var(--muted);
}
.vector-overview-grid {
  display: grid;
  grid-template-columns: repeat(4,minmax(0,1fr));
  gap: 10px;
  margin-bottom: 10px;
}
.vector-overview-card {
  display: grid;
  gap: 5px;
  padding: 14px;
}
.vector-overview-card>span {
  font-size: .8125rem;
  font-weight: 750;
  letter-spacing: .035em;
  text-transform: uppercase;
  color: var(--muted);
}
.vector-overview-card>b {
  font-size: .98rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.vector-overview-card>small {
  color: var(--muted);
  font-size: .76rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-width:1180px) {
  .vector-overview-grid {
    grid-template-columns: repeat(2,minmax(0,1fr));
  }
}
@media (max-width:760px) {
  .vector-overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
