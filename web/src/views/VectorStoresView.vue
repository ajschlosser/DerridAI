<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { toast } from "../composables/notifications";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { state as sharedState } from "../domain/sharedUrlState";
import { pendingUpsertRows, upsertRows } from "../domain/sharedDbPresence";
import { searchWorkspace } from "../domain/sharedSearchWorkspace";
import { openCollectionCreationWizard, triggerUpsertQueue } from "../domain/vectorStoreActions";
import { exportStoreJsonl } from "../domain/storeExport";
import { persistPrefs } from "../domain/sharedWorkspaceStorage";
import { chromaApi } from "../api/chroma";
import { isAbortError } from "../api/graphql/client";
import { createLatestRequest } from "../api/graphql/latestRequest";
import { systemApi, type ProviderProfile } from "../api/system";
import { vectorBrowseReads, type VectorBrowseRow } from "../features/vector-stores/api/browseReads";
import { useAuthStore } from "../stores/auth";
import { useVectorStore } from "../stores/workspace";
import { corpusState } from "../state/workspaceState";
import { useDataQuery } from "../realtime/dataQuery";
import { useI18nStore } from "../stores/i18n";
import { useShellStore } from "../stores/shell";
import AccessibleEmptyState from "../components/AccessibleEmptyState.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiLoadingState from "../components/ui/UiLoadingState.vue";
import UiCard from "../components/ui/UiCard.vue";
import UiDialog from "../components/ui/UiDialog.vue";
import UiField from "../components/ui/UiField.vue";
import UiTabs from "../components/ui/UiTabs.vue";
import VectorBackendPanel from "../components/vector/VectorBackendPanel.vue";
import VectorCollectionHero from "../components/vector/VectorCollectionHero.vue";
import VectorCollectionRail from "../components/vector/VectorCollectionRail.vue";
import VectorWorkspaceHeader from "../components/vector/VectorWorkspaceHeader.vue";
import type {
  ChromaConnectionUpdate,
  ChromaHealth,
  VectorCollection,
  VectorSearchResult,
  VectorWorkStat,
} from "../types/vector";

type VectorTab = "overview" | "data" | "retrieval" | "builds" | "settings";
type BrowseMode = "works" | "records";
// Workspace fields this view shares with the runtime live in the vector store; the rest are read from the shared
// workspace state.
type RuntimeOnlyState = {
  files: Array<{ id: string; records: unknown[] }>;
  activeFileId: string | null;
  llmStatus: { models?: Array<{ name: string }> } | null;
  health: Record<string, unknown> | null;
  appConfig: { embedding_provider?: string; embedding_model?: string };
};
const runtimeState = sharedState as unknown as RuntimeOnlyState;
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
const loading = computed(() => storesQuery.isPending.value);
const hasCollections = ref(false);
const error = ref("");
const health = ref<ChromaHealth | null>(null);
const collections = ref<VectorCollection[]>([]);
const providerProfiles = ref<ProviderProfile[]>([]);
const activeName = ref("");
const filter = ref(String(workspace.vectorCollectionFilter || ""));
const tab = ref<VectorTab>(
  VECTOR_TABS.includes(workspace.vectorTab as VectorTab)
    ? (workspace.vectorTab as VectorTab)
    : "overview",
);
const connectionOpen = ref(false);
const probing = ref(false);
const applying = ref(false);
const probeResult = ref<ChromaHealth | null>(null);
const connectionError = ref("");
const pendingCount = ref(0);
const works = ref<VectorWorkStat[]>([]);
const browseMode = ref<BrowseMode>(workspace.storeBrowseMode === "records" ? "records" : "works");
const records = ref<VectorBrowseRow[]>([]);
const recordCount = ref(0);
const storePage = ref(Number(workspace.storePage) || 1);
const storeWork = ref(String(workspace.storeWork || ""));
const searchQuery = ref(String(workspace.storeQuery || ""));
const searchMode = ref(String(workspace.storeSearchMode || "hybrid"));
const searchResults = ref<VectorSearchResult[]>([]);
type RegionPhase = "idle" | "pending" | "refreshing" | "ready" | "error" | "stale";
type SearchIdentity = { collection: string; query: string; mode: string };
const browseRequests = createLatestRequest();
const searchRequests = createLatestRequest();
const worksPhase = ref<RegionPhase>("idle");
const worksError = ref("");
const recordsPhase = ref<RegionPhase>("idle");
const recordsError = ref("");
const searchPhase = ref<RegionPhase>("idle");
const searchError = ref("");
const shownSearch = ref<SearchIdentity | null>(null);
const inflightSearch = ref<SearchIdentity | null>(null);
let shownWorksCollection = "";
let shownRecordsIdentity = "";
const role = ref("general");
const languageCodes = ref<string[]>([]);
const embeddingProvider = ref("ollama");
const embeddingModel = ref("");
const deriveEn = ref("");
const deriveFr = ref("");
const confirm = ref<{ kind: "delete" | "derive"; title: string; message: string } | null>(null);
let filterTimer = 0;

const current = computed(
  () => collections.value.find((store) => store.name === activeName.value) || null,
);
const visibleCollections = computed(() => {
  const needle = filter.value.trim().toLowerCase();
  return needle
    ? collections.value.filter((store) => store.name.toLowerCase().includes(needle))
    : collections.value;
});
const tabs = computed(() => [
  { id: "overview", label: i18n.t("vector.tab_overview") },
  { id: "data", label: i18n.t("vector.tab_data") },
  { id: "retrieval", label: i18n.t("vector.tab_retrieval") },
  { id: "builds", label: i18n.t("vector.tab_builds") },
  { id: "settings", label: i18n.t("vector.tab_settings") },
]);
const browseTabs = computed(() => [
  { id: "works", label: `${i18n.t("dashboard.works")} ${works.value.length}` },
  {
    id: "records",
    label: `${i18n.t("dashboard.records")} ${Number(current.value?.count || 0).toLocaleString(i18n.locale)}`,
  },
]);
const contractLocked = computed(
  () =>
    Boolean(current.value?.app_version && current.value.app_version !== "legacy") ||
    Boolean(current.value?.count),
);
const maxPage = computed(() =>
  Math.max(1, Math.ceil(recordCount.value / (Number(workspace.storePageSize) || 50))),
);
const providerLabel = computed(() => {
  const provider = current.value?.embedding_provider || "chroma";
  if (provider.startsWith("profile:")) {
    const id = provider.slice("profile:".length);
    const profile = providerProfiles.value.find((item) => item.id === id);
    const name = String(profile?.name || id);
    return current.value?.embedding_model ? `${name} · ${current.value.embedding_model}` : name;
  }
  if (provider === "ollama") return `Ollama · ${current.value?.embedding_model || ""}`.trim();
  if (provider === "precomputed") return i18n.t("vector.provider_precomputed");
  return i18n.t("vector.provider_chroma");
});
const semanticUnavailable = computed(
  () =>
    current.value?.embedding_provider === "precomputed" &&
    ["similarity", "mmr"].includes(searchMode.value),
);

function persistWorkspace() {
  workspace.activeStore = activeName.value;
  workspace.vectorTab = tab.value;
  workspace.vectorCollectionFilter = filter.value;
  workspace.storeBrowseMode = browseMode.value;
  workspace.storePage = storePage.value;
  workspace.storeWork = storeWork.value;
  workspace.storeQuery = searchQuery.value;
  workspace.storeSearchMode = searchMode.value;
  persistPrefs();
  shell.sync();
}

function syncHealthIntoRuntime(next: ChromaHealth) {
  health.value = next;
  runtimeState.health = { ...(runtimeState.health || {}), chroma: next, chroma_path: next.path };
}

let skipDetails = false;
let settingsCollection = "";
// These reads share the existing resource invalidation, but settle independently.
// Detail keys prevent unrelated response shapes from sharing a cache entry.
const readScope = computed(() =>
  JSON.stringify([auth.user?.id, auth.user?.role, auth.user?.capabilities]),
);
const storesQuery = useDataQuery("vector_collections", () => chromaApi.collections(), {
  detail: () => ["workspace", readScope.value, "collections"],
  enabled: () => auth.isAdmin,
});
const healthQuery = useDataQuery("vector_collections", () => chromaApi.health(), {
  detail: () => ["workspace", readScope.value, "health"],
  enabled: () => auth.isAdmin,
});
const providersQuery = useDataQuery("vector_collections", () => systemApi.researcherProviders(), {
  detail: () => ["workspace", readScope.value, "providers"],
  enabled: () => auth.isAdmin,
});
const providersReady = computed(() => providersQuery.isSuccess.value);
const createDisabledReason = computed(() =>
  i18n.t(providersQuery.error.value ? "loading.providers_failed" : "loading.providers"),
);
watch(
  () => storesQuery.dataUpdatedAt.value,
  () => {
    const data = storesQuery.data.value;
    if (data) void applyStores(data);
  },
  { immediate: true },
);
watch(
  () => healthQuery.data.value,
  (data) => {
    if (data) syncHealthIntoRuntime(data);
  },
  { immediate: true },
);
watch(
  () => providersQuery.data.value,
  (data) => {
    if (data) providerProfiles.value = data.profiles || [];
  },
  { immediate: true },
);
watch(
  () => storesQuery.error.value,
  (failure) => {
    if (!failure) {
      error.value = "";
      return;
    }
    error.value = errorText(failure);
    if (
      failure &&
      typeof failure === "object" &&
      "status" in failure &&
      [401, 403].includes(Number(failure.status))
    ) {
      hasCollections.value = false;
      collections.value = [];
      activeName.value = "";
      clearBrowseAndSearch();
    }
  },
  { immediate: true },
);
watch(
  readScope,
  () => {
    hasCollections.value = false;
    collections.value = [];
    activeName.value = "";
    health.value = null;
    providerProfiles.value = [];
    error.value = "";
    clearBrowseAndSearch();
  },
  { flush: "sync" },
);
watch([hasCollections, providersReady], () => {
  if (
    hasCollections.value &&
    providersReady.value &&
    workspace.vectorAutoCreateRequested &&
    !collections.value.length
  ) {
    workspace.vectorAutoCreateRequested = false;
    openCreate();
  }
});
async function load(options: { details?: boolean } = {}) {
  skipDetails = options.details === false;
  await Promise.all([storesQuery.refetch(), healthQuery.refetch(), providersQuery.refetch()]);
}
function errorText(exc: unknown) {
  return exc instanceof Error ? exc.message : String(exc);
}

async function applyStores(stores: VectorCollection[]) {
  const details = !skipDetails;
  skipDetails = false;
  error.value = "";
  try {
    const previousName = activeName.value;
    const previous = current.value;
    const preserveSettings =
      previous &&
      settingsCollection === previous.name &&
      (role.value !== (previous.collection_role || "general") ||
        JSON.stringify(languageCodes.value) !== JSON.stringify(previous.language_codes || []) ||
        embeddingProvider.value !== (previous.embedding_provider || "ollama") ||
        embeddingModel.value !== (previous.embedding_model || ""));
    hasCollections.value = true;
    const corpusStores = stores.filter((store) => !store.metadata?.derridai_system_collection);
    collections.value = corpusStores;
    if (activeName.value && !corpusStores.some((store) => store.name === activeName.value))
      activeName.value = "";
    if (!activeName.value)
      activeName.value = String(workspace.activeStore || corpusStores[0]?.name || "");
    if (activeName.value && !corpusStores.some((store) => store.name === activeName.value))
      activeName.value = corpusStores[0]?.name || "";
    if (activeName.value !== previousName) clearBrowseAndSearch();
    workspace.stores = corpusStores;
    persistWorkspace();
    pendingCount.value = pendingUpsertRows().length || 0;
    if (current.value && (settingsCollection !== current.value.name || !preserveSettings)) {
      settingsCollection = current.value.name;
      role.value = current.value.collection_role || "general";
      languageCodes.value = [...(current.value.language_codes || [])];
      embeddingProvider.value = current.value.embedding_provider || "ollama";
      embeddingModel.value = current.value.embedding_model || "";
      deriveEn.value = `${current.value.name}_en`;
      deriveFr.value = `${current.value.name}_fr`;
      if (!workspace.storeSearchMode)
        searchMode.value =
          (
            { hybrid: "hybrid", lexical: "lexical", semantic: "similarity" } as Record<
              string,
              string
            >
          )[current.value.retrieval_mode || ""] || "hybrid";
    }
    if (details && current.value && tab.value === "data") await loadData();
    if (corpusStores.length) {
      workspace.vectorAutoCreateRequested = false;
    }
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}

function recordsIdentity() {
  return JSON.stringify([activeName.value, storeWork.value, storePage.value]);
}
function recordScope(identity: string) {
  if (!identity) return "";
  const [collection, work] = JSON.parse(identity) as [string, string, number];
  return `${collection}\0${work}`;
}
function searchKey(identity: SearchIdentity) {
  return JSON.stringify([identity.collection, identity.query, identity.mode]);
}
const searchResultsArePrevious = computed(
  () =>
    Boolean(shownSearch.value) &&
    Boolean(inflightSearch.value) &&
    searchKey(shownSearch.value as SearchIdentity) !==
      searchKey(inflightSearch.value as SearchIdentity),
);
function clearBrowseAndSearch() {
  browseRequests.cancel();
  searchRequests.cancel();
  works.value = [];
  records.value = [];
  recordCount.value = 0;
  shownWorksCollection = "";
  shownRecordsIdentity = "";
  worksPhase.value = "idle";
  recordsPhase.value = "idle";
  worksError.value = "";
  recordsError.value = "";
  searchResults.value = [];
  shownSearch.value = null;
  inflightSearch.value = null;
  searchPhase.value = "idle";
  searchError.value = "";
}
async function loadData() {
  if (!activeName.value) {
    clearBrowseAndSearch();
    return;
  }
  const collection = activeName.value;
  const includeRecords = browseMode.value === "records";
  const nextRecordsIdentity = recordsIdentity();
  const retainedWorks =
    shownWorksCollection === collection &&
    (worksPhase.value === "ready" || worksPhase.value === "stale");
  const retainedRecords =
    includeRecords &&
    shownRecordsIdentity === nextRecordsIdentity &&
    (recordsPhase.value === "ready" || recordsPhase.value === "stale");
  if (shownWorksCollection !== collection) {
    works.value = [];
    records.value = [];
    recordCount.value = 0;
    shownRecordsIdentity = "";
    recordsPhase.value = "idle";
    recordsError.value = "";
    worksPhase.value = "pending";
  } else worksPhase.value = retainedWorks ? "refreshing" : "pending";
  worksError.value = "";
  if (includeRecords) {
    if (shownRecordsIdentity !== nextRecordsIdentity) {
      records.value = [];
      if (recordScope(shownRecordsIdentity) !== recordScope(nextRecordsIdentity))
        recordCount.value = 0;
      recordsPhase.value = "pending";
    } else recordsPhase.value = retainedRecords ? "refreshing" : "pending";
    recordsError.value = "";
  }
  const ticket = browseRequests.start();
  try {
    const limit = Number(workspace.storePageSize) || 50;
    const result = await vectorBrowseReads.browse(collection, {
      includeRecords,
      offset: Math.max(0, (storePage.value - 1) * limit),
      limit,
      work: storeWork.value || undefined,
      signal: ticket.signal,
    });
    if (!ticket.current()) return;
    works.value = result.works;
    shownWorksCollection = collection;
    worksPhase.value = "ready";
    worksError.value = "";
    if (includeRecords) {
      records.value = result.page?.rows || [];
      recordCount.value = result.page?.total || 0;
      shownRecordsIdentity = nextRecordsIdentity;
      recordsPhase.value = "ready";
      recordsError.value = "";
    }
  } catch (exc) {
    if (!ticket.current() || isAbortError(exc)) return;
    const message = exc instanceof Error ? exc.message : String(exc);
    if (retainedWorks) worksPhase.value = "stale";
    else {
      works.value = [];
      worksPhase.value = "error";
    }
    worksError.value = message;
    if (includeRecords) {
      if (retainedRecords) recordsPhase.value = "stale";
      else {
        records.value = [];
        recordsPhase.value = "error";
      }
      recordsError.value = message;
    }
  }
}

function openCreate() {
  if (!providersReady.value) return;
  const models = runtimeState.llmStatus?.models || [];
  openCollectionCreationWizard({
    defaultProvider: runtimeState.appConfig?.embedding_provider || "ollama",
    defaultModel: runtimeState.appConfig?.embedding_model || "bge-m3:latest",
    installedModels: models,
    providerProfiles: providerProfiles.value,
  } as never);
}

async function probe(body: ChromaConnectionUpdate) {
  probing.value = true;
  connectionError.value = "";
  probeResult.value = null;
  try {
    probeResult.value = await chromaApi.probe(body);
  } catch (exc) {
    connectionError.value = i18n.tf("vector.connection_failed", {
      message: exc instanceof Error ? exc.message : String(exc),
    });
  } finally {
    probing.value = false;
  }
}

async function applyConnection(body: ChromaConnectionUpdate) {
  applying.value = true;
  connectionError.value = "";
  try {
    const next = await chromaApi.setConnection(body);
    syncHealthIntoRuntime(next);
    connectionOpen.value = false;
    toast(i18n.t("vector.connection_changed"), { tone: "success" });
    activeName.value = "";
    await load();
  } catch (exc) {
    connectionError.value = i18n.tf("vector.connection_failed", {
      message: exc instanceof Error ? exc.message : String(exc),
    });
  } finally {
    applying.value = false;
  }
}

function selectCollection(name: string) {
  if (name !== activeName.value) clearBrowseAndSearch();
  activeName.value = name;
  tab.value = "overview";
  browseMode.value = "works";
  storePage.value = 1;
  storeWork.value = "";
  persistWorkspace();
  void load({ details: false });
}

function setTab(next: string) {
  tab.value = (tabs.value.some((item) => item.id === next) ? next : "overview") as VectorTab;
  persistWorkspace();
  if (tab.value === "data") void loadData();
}

function setBrowse(next: string) {
  browseMode.value = next === "records" ? "records" : "works";
  if (browseMode.value === "records") {
    storeWork.value = "";
    storePage.value = 1;
  }
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
  const query = searchQuery.value.trim();
  if (!activeName.value || !query || semanticUnavailable.value) return;
  const identity: SearchIdentity = {
    collection: activeName.value,
    query,
    mode: searchMode.value,
  };
  const same =
    Boolean(shownSearch.value) &&
    searchKey(shownSearch.value as SearchIdentity) === searchKey(identity) &&
    (searchPhase.value === "ready" || searchPhase.value === "stale");
  if (shownSearch.value && shownSearch.value.collection !== identity.collection) {
    searchResults.value = [];
    shownSearch.value = null;
  }
  inflightSearch.value = identity;
  searchPhase.value = same ? "refreshing" : "pending";
  searchError.value = "";
  persistWorkspace();
  const ticket = searchRequests.start();
  try {
    const payload = await chromaApi.search(
      identity.collection,
      { query: identity.query, mode: identity.mode, n_results: 30 },
      ticket.signal,
    );
    if (!ticket.current()) return;
    searchResults.value = payload.results || [];
    shownSearch.value = identity;
    inflightSearch.value = null;
    searchPhase.value = "ready";
    searchError.value = "";
  } catch (exc) {
    if (!ticket.current() || isAbortError(exc)) return;
    searchError.value = exc instanceof Error ? exc.message : String(exc);
    if (same) searchPhase.value = "stale";
    else if (shownSearch.value?.collection === identity.collection) searchPhase.value = "error";
    else {
      searchResults.value = [];
      shownSearch.value = null;
      searchPhase.value = "error";
    }
  }
}
function clearSearch() {
  searchRequests.cancel();
  searchQuery.value = "";
  searchResults.value = [];
  shownSearch.value = null;
  inflightSearch.value = null;
  searchPhase.value = "idle";
  searchError.value = "";
  persistWorkspace();
}

async function saveLanguages() {
  if (!activeName.value) return;
  try {
    await chromaApi.setLanguages(activeName.value, {
      language_codes: languageCodes.value,
      collection_role: role.value,
    });
    toast(i18n.t("vector.language_tags_saved"), { tone: "success" });
    await load();
  } catch (exc) {
    toast(exc instanceof Error ? exc.message : String(exc), { tone: "danger" });
  }
}

async function saveEmbedding() {
  if (!activeName.value || contractLocked.value) return;
  if (embeddingProvider.value.startsWith("profile:") && !embeddingModel.value.trim())
    return toast(i18n.t("vector.embedding_model_required"), { tone: "warning" });
  try {
    await chromaApi.setEmbedding(activeName.value, {
      embedding_provider: embeddingProvider.value,
      embedding_model: embeddingProvider.value.startsWith("profile:")
        ? embeddingModel.value.trim()
        : null,
    });
    toast(i18n.t("vector.embedding_saved"), { tone: "success" });
    await load();
  } catch (exc) {
    toast(exc instanceof Error ? exc.message : String(exc), { tone: "danger" });
  }
}

async function toggleProtection() {
  if (!current.value) return;
  try {
    await chromaApi.setProtection(current.value.name, !current.value.protected);
    toast(
      current.value.protected
        ? i18n.t("vector.protection_disabled")
        : i18n.t("vector.protection_enabled"),
      { tone: "success" },
    );
    await load();
  } catch (exc) {
    toast(exc instanceof Error ? exc.message : String(exc), { tone: "danger" });
  }
}

async function confirmAction() {
  const kind = confirm.value?.kind;
  confirm.value = null;
  if (kind === "delete") {
    if (!activeName.value) return;
    try {
      await chromaApi.remove(activeName.value);
      activeName.value = "";
      toast(i18n.t("vector.collection_deleted"), { tone: "success" });
      await load();
    } catch (exc) {
      toast(exc instanceof Error ? exc.message : String(exc), { tone: "danger" });
    }
  }
  if (kind === "derive") {
    if (!activeName.value || !deriveEn.value.trim() || !deriveFr.value.trim()) return;
    try {
      await chromaApi.deriveLanguages(activeName.value, {
        en_name: deriveEn.value.trim(),
        fr_name: deriveFr.value.trim(),
        overwrite: true,
      });
      toast(i18n.t("vector.language_collections"), { tone: "success" });
      await load();
    } catch (exc) {
      toast(exc instanceof Error ? exc.message : String(exc), { tone: "danger" });
    }
  }
}

function syncActive() {
  const file = runtimeState.files?.find((item) => item.id === runtimeState.activeFileId);
  if (!file) return toast(i18n.t("vector.load_jsonl_first"), { tone: "warning" });
  void upsertRows(
    file.records.map((record: unknown, index: number) => ({ file, record, index })),
    "records",
  ).then(() => load());
}
function syncAll() {
  const rows = (runtimeState.files || []).flatMap((file) =>
    file.records.map((record, index) => ({ file, record, index })),
  );
  if (!rows.length) return toast(i18n.t("vector.load_jsonl_any_first"), { tone: "warning" });
  void upsertRows(rows, "records").then(() => load());
}

function snippet(text: unknown) {
  const value = String(text || "")
    .replace(/\s+/g, " ")
    .trim();
  return value.length > 280 ? `${value.slice(0, 277)}…` : value;
}
function toggleLanguage(code: string, checked: boolean) {
  if (checked && !languageCodes.value.includes(code))
    languageCodes.value = [...languageCodes.value, code];
  else if (!checked) languageCodes.value = languageCodes.value.filter((item) => item !== code);
}

async function redirectResearcher() {
  await searchWorkspace.setSearchScope("database");
  await router.replace("/search");
}

function onStoresChanged() {
  void load();
}
watch(filter, (value) => {
  window.clearTimeout(filterTimer);
  filterTimer = window.setTimeout(() => persistWorkspace(), 140);
  workspace.vectorCollectionFilter = value;
});
watch(
  () => i18n.locale,
  () => {
    void load({ details: false });
  },
);
onMounted(async () => {
  if (auth.isResearcher) {
    await redirectResearcher();
    return;
  }
  window.addEventListener("derridai:vector-stores-changed", onStoresChanged);
});
onBeforeUnmount(() => {
  window.clearTimeout(filterTimer);
  window.removeEventListener("derridai:vector-stores-changed", onStoresChanged);
  browseRequests.cancel();
  searchRequests.cancel();
});
</script>

<template>
  <main class="vue-native-page vector-native-page" aria-labelledby="vector-page-title">
    <VectorWorkspaceHeader
      v-if="!auth.isResearcher"
      :health-loading="healthQuery.isPending.value"
      :can-create="providersReady"
      :create-disabled-reason="createDisabledReason"
      :health="health"
      :collection-count="collections.length"
      @create="openCreate"
      @connection="
        connectionOpen = true;
        probeResult = null;
        connectionError = '';
      "
    />
    <template v-if="!auth.isResearcher">
      <div v-if="healthQuery.error.value" class="info error" role="alert">
        {{ i18n.t("loading.health_failed") }} {{ errorText(healthQuery.error.value) }}
        <UiButton :label="i18n.t('ui.retry')" @click="healthQuery.refetch()" />
      </div>
      <UiLoadingState
        v-if="providersQuery.isPending.value"
        variant="inline"
        :label="i18n.t('loading.providers')"
      />
      <div v-if="providersQuery.error.value" class="info error" role="alert">
        {{ i18n.t("loading.providers_failed") }} {{ errorText(providersQuery.error.value) }}
        <UiButton :label="i18n.t('ui.retry')" @click="providersQuery.refetch()" />
      </div>
    </template>
    <div v-if="auth.isResearcher" class="vector-page-loading">
      <UiLoadingState :label="i18n.t('search.redirect_database')" />
    </div>
    <div v-if="!auth.isResearcher && loading && !hasCollections" class="vector-page-loading">
      <UiLoadingState :label="i18n.t('vector.loading_stores')" variant="skeleton" />
    </div>
    <section v-if="error && !auth.isResearcher" class="vector-page-error" role="alert">
      <p v-if="hasCollections">{{ i18n.t("loading.stale") }}</p>
      <p>{{ error }}</p>
      <UiButton :label="i18n.t('ui.retry')" @click="load()" />
    </section>
    <template v-if="hasCollections && !auth.isResearcher">
      <UiLoadingState
        v-if="storesQuery.isFetching.value"
        variant="inline"
        :label="i18n.t('loading.updating')"
      />
      <AccessibleEmptyState
        v-if="!collections.length"
        icon="database"
        :title="i18n.t('vector.empty_title')"
        :description="i18n.t('vector.empty_help')"
        :action-label="providersReady ? i18n.t('vector.create_first_collection') : ''"
        @action="openCreate"
      />

      <section v-else class="storegrid vector-store-layout vector-workspace-v0371">
        <VectorCollectionRail
          :can-create="providersReady"
          :create-disabled-reason="createDisabledReason"
          :collections="visibleCollections"
          :active-name="activeName"
          :filter="filter"
          @update:filter="filter = $event"
          @select="selectCollection"
          @create="openCreate"
        />
        <article class="vector-store-main">
          <AccessibleEmptyState
            v-if="!current"
            icon="database"
            icon-tone="neutral"
            :title="i18n.t('vector.select_collection')"
            :description="i18n.t('vector.select_collection_help')"
          />
          <template v-else>
            <VectorCollectionHero
              :collection="current"
              :pending-count="pendingCount"
              @sync="triggerUpsertQueue()"
              @retrieval="setTab('retrieval')"
              @protection="toggleProtection"
              @delete="
                confirm = {
                  kind: 'delete',
                  title: i18n.t('vector.delete_collection'),
                  message: i18n.tf('vector.delete_collection_confirm', { name: current.name }),
                }
              "
            />
            <UiTabs
              :tabs="tabs"
              :model-value="tab"
              id-prefix="vector-section"
              :tablist-label="i18n.t('vector.workspace_sections')"
              @update:model-value="setTab"
            />

            <section
              v-show="tab === 'overview'"
              id="vector-section-panel-overview"
              class="vector-tab-surface"
              role="tabpanel"
              aria-labelledby="vector-section-tab-overview"
            >
              <div class="vector-overview-grid">
                <article class="card vector-overview-card">
                  <span>{{ i18n.t("vector.sync_state") }}</span
                  ><b>{{
                    pendingCount
                      ? i18n.tf("vector.changes_pending", {
                          count: pendingCount.toLocaleString(i18n.locale),
                        })
                      : i18n.t("vector.current")
                  }}</b
                  ><small>{{
                    current.last_synced_at
                      ? i18n.tf("vector.synced_at", {
                          time: new Date(current.last_synced_at).toLocaleString(i18n.locale, {
                            timeZone: i18n.timeZone,
                          }),
                        })
                      : i18n.t("vector.never_synced")
                  }}</small>
                </article>
                <article class="card vector-overview-card">
                  <span>{{ i18n.t("vector.retrieval_contract") }}</span
                  ><b
                    >{{ current.retrieval_mode || "semantic" }} ·
                    {{ current.distance_metric || "l2"
                    }}{{
                      current.embedding_dimension
                        ? ` · ${Number(current.embedding_dimension).toLocaleString(i18n.locale)}d`
                        : ""
                    }}</b
                  ><small>{{ providerLabel }}</small>
                </article>
                <article class="card vector-overview-card">
                  <span>{{ i18n.t("vector.source") }}</span
                  ><b>{{
                    current.source_label ||
                    current.source_kind ||
                    i18n.t("vector.source_unrecorded")
                  }}</b
                  ><small
                    >{{
                      Number(current.source_record_count || current.count || 0).toLocaleString(
                        i18n.locale,
                      )
                    }}
                    {{ i18n.t("dynamic.records") }}</small
                  >
                </article>
                <article class="card vector-overview-card">
                  <span>{{ i18n.t("vector.current_build") }}</span
                  ><b>{{
                    current.build_id ? current.build_id.slice(-12) : i18n.t("vector.no_build")
                  }}</b
                  ><small
                    >{{ (current.build_history || []).length.toLocaleString(i18n.locale) }}
                    {{ i18n.t("vector.completed_builds") }}</small
                  >
                </article>
              </div>
              <div v-if="current.last_build_error" class="info warn" role="status">
                <b>{{ i18n.t("vector.last_build_error") }}</b
                ><span>{{ current.last_build_error }}</span>
              </div>
            </section>

            <section
              v-show="tab === 'data'"
              id="vector-section-panel-data"
              class="card vector-browser-card vector-tab-surface"
              role="tabpanel"
              aria-labelledby="vector-section-tab-data"
            >
              <UiTabs
                :tabs="browseTabs"
                :model-value="browseMode"
                id-prefix="vector-browse"
                :tablist-label="i18n.t('vector.browse_works')"
                @update:model-value="setBrowse"
              />
              <div
                v-show="browseMode === 'works'"
                id="vector-browse-panel-works"
                role="tabpanel"
                aria-labelledby="vector-browse-tab-works"
                class="db-work-grid"
                :aria-busy="worksPhase === 'pending' || worksPhase === 'refreshing'"
              >
                <UiLoadingState
                  v-if="worksPhase === 'pending'"
                  :label="i18n.t('vector.browse_loading')"
                  variant="skeleton"
                />
                <div
                  v-else-if="worksPhase === 'error'"
                  id="vector-works-status"
                  class="info error"
                  role="alert"
                >
                  <p>{{ i18n.tf("vector.browse_failed", { message: worksError }) }}</p>
                  <UiButton :label="i18n.t('ui.retry')" @click="loadData()" />
                </div>
                <template v-else>
                  <UiLoadingState
                    v-if="worksPhase === 'refreshing'"
                    variant="inline"
                    :label="i18n.t('loading.updating')"
                  />
                  <div
                    v-if="worksPhase === 'stale'"
                    id="vector-works-status"
                    class="info error"
                    role="alert"
                  >
                    <p>{{ i18n.t("loading.stale") }} {{ worksError }}</p>
                    <UiButton :label="i18n.t('ui.retry')" @click="loadData()" />
                  </div>
                  <button
                    v-for="item in works"
                    :key="item.work"
                    type="button"
                    class="db-work-card"
                    @click="openWork(item.work)"
                  >
                    <span
                      ><b>{{ item.work }}</b
                      ><small>{{ i18n.t("vector.open_work_records") }}</small></span
                    ><strong>{{
                      item.count == null ? "—" : Number(item.count).toLocaleString(i18n.locale)
                    }}</strong>
                  </button>
                  <p
                    v-if="(worksPhase === 'ready' || worksPhase === 'stale') && !works.length"
                    class="note"
                  >
                    {{ i18n.t("research.no_work_metadata") }}
                  </p>
                </template>
              </div>
              <div
                v-show="browseMode === 'records'"
                id="vector-browse-panel-records"
                role="tabpanel"
                aria-labelledby="vector-browse-tab-records"
                :aria-busy="recordsPhase === 'pending' || recordsPhase === 'refreshing'"
              >
                <div class="toolbar store-record-toolbar">
                  <div>
                    <b>{{ storeWork || i18n.t("research.all_records") }}</b>
                    <div class="note">
                      {{
                        recordsPhase === "pending"
                          ? i18n.t("vector.records_loading")
                          : `${recordCount.toLocaleString(i18n.locale)} ${i18n.t("dynamic.records")}`
                      }}
                      · {{ i18n.t("dynamic.page") }} {{ storePage }} {{ i18n.t("research.of") }}
                      {{ maxPage }}
                    </div>
                  </div>
                  <div class="tools">
                    <label class="sr-only" for="vector-store-work">{{
                      i18n.t("dashboard.works")
                    }}</label>
                    <select
                      id="vector-store-work"
                      class="control"
                      :value="storeWork"
                      @change="
                        storeWork = ($event.target as HTMLSelectElement).value;
                        storePage = 1;
                        persistWorkspace();
                        loadData();
                      "
                    >
                      <option value="">{{ i18n.t("dashboard.all_works") }}</option>
                      <option v-for="item in works" :key="item.work" :value="item.work">
                        {{ item.work }}
                      </option>
                    </select>
                    <UiButton
                      :label="i18n.t('ui.previous')"
                      :disabled="storePage <= 1"
                      @click="
                        storePage -= 1;
                        persistWorkspace();
                        loadData();
                      "
                    />
                    <UiButton
                      :label="i18n.t('ui.next')"
                      :disabled="storePage >= maxPage"
                      @click="
                        storePage += 1;
                        persistWorkspace();
                        loadData();
                      "
                    />
                  </div>
                </div>
                <UiLoadingState
                  v-if="recordsPhase === 'pending'"
                  id="vector-records-status"
                  :label="i18n.t('vector.records_loading')"
                  variant="skeleton"
                />
                <div
                  v-else-if="recordsPhase === 'error'"
                  id="vector-records-status"
                  class="info error"
                  role="alert"
                >
                  <p>{{ i18n.tf("vector.records_failed", { message: recordsError }) }}</p>
                  <UiButton :label="i18n.t('ui.retry')" @click="loadData()" />
                </div>
                <div
                  v-else
                  class="tablewrap ui-table-scroll"
                  role="region"
                  :aria-label="i18n.t('dashboard.records')"
                  tabindex="0"
                >
                  <UiLoadingState
                    v-if="recordsPhase === 'refreshing'"
                    variant="inline"
                    :label="i18n.t('loading.updating')"
                  />
                  <div
                    v-if="recordsPhase === 'stale'"
                    id="vector-records-status"
                    class="info error"
                    role="alert"
                  >
                    <p>{{ i18n.t("loading.stale") }} {{ recordsError }}</p>
                    <UiButton :label="i18n.t('ui.retry')" @click="loadData()" />
                  </div>
                  <table class="store-table ui-table">
                    <caption class="sr-only">
                      {{
                        i18n.t("dashboard.records")
                      }}
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">{{ i18n.t("field.work") }}</th>
                        <th scope="col">{{ i18n.t("field.record_id") }}</th>
                        <th scope="col">{{ i18n.t("record.page") }}</th>
                        <th scope="col">{{ i18n.t("record.text") }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="record in records" :key="record.chroma_id">
                        <td>{{ record.work || "—" }}</td>
                        <td>{{ record.record_id || record.chroma_id || "—" }}</td>
                        <td>
                          {{ record.page_start ?? "—"
                          }}{{
                            record.page_end && record.page_end !== record.page_start
                              ? `–${record.page_end}`
                              : ""
                          }}
                        </td>
                        <td>{{ record.text_preview }}</td>
                      </tr>
                      <tr
                        v-if="
                          (recordsPhase === 'ready' || recordsPhase === 'stale') && !records.length
                        "
                      >
                        <td colspan="4" class="note">{{ i18n.t("vector.no_matching_records") }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </section>

            <section
              v-show="tab === 'retrieval'"
              id="vector-section-panel-retrieval"
              class="card vector-search-card vector-tab-surface"
              role="tabpanel"
              aria-labelledby="vector-section-tab-retrieval"
            >
              <div class="cardhead">
                <div>
                  <b>{{ i18n.t("vector.test_retrieval") }}</b>
                  <div class="note">{{ i18n.t("vector.test_retrieval_help") }}</div>
                </div>
              </div>
              <form class="vector-search-config" @submit.prevent="runSearch">
                <UiField :label="i18n.t('vector.search_method')">
                  <select class="control" v-model="searchMode">
                    <option value="hybrid">{{ i18n.t("vector.hybrid") }}</option>
                    <option value="similarity">{{ i18n.t("vector.semantic") }}</option>
                    <option value="lexical">{{ i18n.t("vector.lexical") }}</option>
                    <option value="mmr">MMR</option>
                  </select>
                </UiField>
                <div class="vector-search-row">
                  <label class="sr-only" for="vector-store-query">{{
                    i18n.t("vector.test_retrieval")
                  }}</label>
                  <input
                    id="vector-store-query"
                    class="control"
                    v-model="searchQuery"
                    :placeholder="i18n.t('vector.retrieval_search_placeholder')"
                    autocomplete="off"
                  />
                  <UiButton
                    type="submit"
                    variant="primary"
                    :label="i18n.t('ui.search')"
                    :disabled="semanticUnavailable"
                    :disabled-reason="i18n.t('vector.precomputed_search_help')"
                  />
                  <UiButton type="button" :label="i18n.t('ui.clear')" @click="clearSearch" />
                </div>
              </form>
              <div
                class="vector-search-results"
                :aria-busy="searchPhase === 'pending' || searchPhase === 'refreshing'"
              >
                <UiLoadingState
                  v-if="searchPhase === 'pending' || searchPhase === 'refreshing'"
                  id="vector-search-status"
                  variant="inline"
                  :label="i18n.t('search.searching')"
                />
                <div
                  v-if="searchPhase === 'error' || searchPhase === 'stale'"
                  id="vector-search-status"
                  class="info error"
                  role="alert"
                >
                  <p>{{ i18n.tf("vector.search_failed", { message: searchError }) }}</p>
                  <p v-if="searchPhase === 'stale'">{{ i18n.t("loading.stale") }}</p>
                  <UiButton :label="i18n.t('ui.retry')" @click="runSearch()" />
                </div>
                <p v-if="searchResultsArePrevious && shownSearch" class="note">
                  {{ i18n.tf("vector.search_previous", { query: shownSearch.query }) }}
                </p>
                <article
                  v-for="result in searchResults"
                  :key="String(result.id || result.record?._chroma_id || result.record?.record_id)"
                  class="result store-result"
                >
                  <div class="result-main">
                    <div class="note">
                      {{
                        result.hybrid_score != null
                          ? `${i18n.t("vector.hybrid_score")} ${Number(result.hybrid_score).toFixed(4)}`
                          : result.distance != null
                            ? Number(result.distance).toFixed(4)
                            : ""
                      }}
                    </div>
                    <b>{{ result.record?.work || result.record?.record_id || result.id }}</b>
                    <div class="textcell">{{ snippet(result.record?.text) }}</div>
                  </div>
                </article>
                <p v-if="searchPhase === 'idle'" class="note">
                  {{ i18n.t("vector.search_results_empty") }}
                </p>
                <p v-else-if="searchPhase === 'ready' && !searchResults.length" class="note">
                  {{ i18n.t("vector.search_no_results") }}
                </p>
              </div>
            </section>

            <section
              v-show="tab === 'builds'"
              id="vector-section-panel-builds"
              class="card vector-manifest-card vector-tab-surface"
              role="tabpanel"
              aria-labelledby="vector-section-tab-builds"
            >
              <div class="cardhead">
                <div>
                  <b>{{ i18n.t("vector.manifest_builds") }}</b>
                  <div class="note">{{ i18n.t("vector.manifest_builds_help") }}</div>
                </div>
                <span class="badge">v{{ current.manifest_version || 1 }}</span>
              </div>
              <dl class="manifest-review vector-manifest-review">
                <div>
                  <dt>{{ i18n.t("vector.status") }}</dt>
                  <dd>{{ String(current.status || (current.count ? "ready" : "empty")) }}</dd>
                </div>
                <div>
                  <dt>{{ i18n.t("vector.retrieval_mode") }}</dt>
                  <dd>{{ current.retrieval_mode || "semantic" }}</dd>
                </div>
                <div>
                  <dt>{{ i18n.t("vector.embedding_dimension") }}</dt>
                  <dd>
                    {{
                      current.embedding_dimension
                        ? Number(current.embedding_dimension).toLocaleString(i18n.locale)
                        : "—"
                    }}
                  </dd>
                </div>
                <div>
                  <dt>{{ i18n.t("vector.distance_metric") }}</dt>
                  <dd>{{ current.distance_metric || "l2" }}</dd>
                </div>
                <div>
                  <dt>{{ i18n.t("vector.text_field") }}</dt>
                  <dd>
                    <code>{{ current.text_field || "text" }}</code>
                  </dd>
                </div>
                <div>
                  <dt>{{ i18n.t("vector.source_records") }}</dt>
                  <dd>
                    {{ Number(current.source_record_count || 0).toLocaleString(i18n.locale) }}
                  </dd>
                </div>
                <div>
                  <dt>{{ i18n.t("vector.created_with") }}</dt>
                  <dd>{{ current.app_version || "legacy" }}</dd>
                </div>
              </dl>
              <details class="vector-build-history" :open="!(current.build_history || []).length">
                <summary>
                  {{
                    i18n.tf("vector.build_history", { count: (current.build_history || []).length })
                  }}
                </summary>
                <div v-if="current.build_history?.length" class="vector-build-list">
                  <article
                    v-for="build in [...current.build_history].reverse()"
                    :key="String(build.build_id)"
                  >
                    <div>
                      <b>{{ build.build_id || i18n.t("vector.build") }}</b>
                    </div>
                    <small
                      >{{ build.finished_at || build.created_at || "" }} ·
                      {{ Number(build.record_count || 0).toLocaleString(i18n.locale) }}
                      {{ i18n.t("dynamic.records") }}</small
                    >
                  </article>
                </div>
                <p v-else class="note">{{ i18n.t("vector.no_build_history") }}</p>
              </details>
            </section>

            <div
              v-show="tab === 'settings'"
              id="vector-section-panel-settings"
              class="vector-tab-surface"
              role="tabpanel"
              aria-labelledby="vector-section-tab-settings"
            >
              <div class="vector-settings-grid">
                <UiCard>
                  <div class="cardhead">
                    <div>
                      <b>{{ i18n.t("vector.role_language_title") }}</b>
                      <div class="note">{{ i18n.t("vector.role_language_help") }}</div>
                    </div>
                  </div>
                  <div class="vector-settings-body">
                    <UiField :label="i18n.t('vector.collection_role')">
                      <select class="control" v-model="role">
                        <option value="primary">{{ i18n.t("vector.role_primary") }}</option>
                        <option value="general">{{ i18n.t("vector.role_general") }}</option>
                        <option value="language">{{ i18n.t("vector.role_language") }}</option>
                      </select>
                    </UiField>
                    <fieldset class="vector-inline-fieldset">
                      <legend>{{ i18n.t("vector.language_tags") }}</legend>
                      <div class="language-checks">
                        <label v-for="code in ['en', 'fr']" :key="code"
                          ><input
                            type="checkbox"
                            :checked="languageCodes.includes(code)"
                            @change="
                              toggleLanguage(code, ($event.target as HTMLInputElement).checked)
                            "
                          /><span>{{ code }}</span></label
                        >
                      </div>
                    </fieldset>
                    <UiButton :label="i18n.t('ui.save')" @click="saveLanguages" />
                  </div>
                </UiCard>
                <UiCard>
                  <div class="cardhead">
                    <div>
                      <b>{{ i18n.t("vector.embedding_configuration") }}</b>
                      <div class="note">
                        {{
                          contractLocked
                            ? i18n.t("vector.embedding_locked_help")
                            : i18n.t("vector.embedding_edit_help")
                        }}
                      </div>
                    </div>
                  </div>
                  <div class="vector-settings-body">
                    <UiField :label="i18n.t('vector.embedding_provider')">
                      <select
                        class="control"
                        v-model="embeddingProvider"
                        :disabled="contractLocked || !providersReady"
                      >
                        <option value="chroma">{{ i18n.t("vector.provider_chroma") }}</option>
                        <option value="precomputed">
                          {{ i18n.t("vector.provider_precomputed") }}
                        </option>
                        <option
                          v-for="profile in providerProfiles"
                          :key="profile.id"
                          :value="`profile:${profile.id}`"
                        >
                          {{ profile.name || profile.id }}
                        </option>
                        <option v-if="embeddingProvider === 'ollama'" value="ollama">
                          Ollama (legacy)
                        </option>
                      </select>
                    </UiField>
                    <UiField :label="i18n.t('vector.embedding_model')">
                      <input
                        class="control"
                        v-model="embeddingModel"
                        :disabled="contractLocked || !embeddingProvider.startsWith('profile:')"
                        placeholder="bge-m3:latest"
                      />
                    </UiField>
                    <UiButton
                      :label="i18n.t('ui.save')"
                      :disabled="contractLocked"
                      @click="saveEmbedding"
                    />
                  </div>
                </UiCard>
              </div>
              <UiCard class="vector-transfer-card">
                <div class="cardhead">
                  <div>
                    <b>{{ i18n.t("vector.import_export") }}</b>
                    <div class="note">{{ i18n.t("vector.import_export_help") }}</div>
                  </div>
                </div>
                <div class="vector-transfer-groups">
                  <div>
                    <span class="section-label">{{ i18n.t("vector.sync_into_collection") }}</span>
                    <div class="store-actions">
                      <UiButton
                        :label="i18n.t('vector.sync_active_jsonl')"
                        icon="database"
                        :disabled="!loadedFileCount"
                        @click="syncActive"
                      />
                      <UiButton
                        :label="i18n.t('vector.sync_all_loaded')"
                        icon="database"
                        :disabled="!loadedFileCount"
                        @click="syncAll"
                      />
                    </div>
                  </div>
                  <div>
                    <span class="section-label">{{ i18n.t("vector.export_from_collection") }}</span>
                    <div class="store-actions">
                      <UiButton
                        :label="i18n.t('vector.open_db_jsonl')"
                        icon="download"
                        @click="exportStoreJsonl({ loadTab: true })"
                      />
                      <UiButton
                        :label="i18n.t('vector.download_db_jsonl')"
                        icon="download"
                        @click="exportStoreJsonl({ downloadFile: true })"
                      />
                    </div>
                  </div>
                </div>
              </UiCard>
              <UiCard
                v-if="current.collection_role !== 'language' && current.name !== '_response_cache'"
              >
                <div class="cardhead">
                  <div>
                    <b>{{ i18n.t("vector.language_collections") }}</b>
                    <div class="note">{{ i18n.t("vector.language_derive_help") }}</div>
                  </div>
                </div>
                <div class="language-database-grid">
                  <UiField
                    :label="i18n.t('vector.english_collection')"
                    :hint="i18n.t('vector.english_collection_help')"
                    ><input class="control" v-model="deriveEn"
                  /></UiField>
                  <UiField
                    :label="i18n.t('vector.french_collection')"
                    :hint="i18n.t('vector.french_collection_help')"
                    ><input class="control" v-model="deriveFr"
                  /></UiField>
                  <UiButton
                    :label="i18n.t('vector.generate_language_collections')"
                    variant="primary"
                    icon="database"
                    @click="
                      confirm = {
                        kind: 'derive',
                        title: i18n.t('vector.generate_language_collections'),
                        message: i18n.tf('vector.derive_confirm', {
                          en: deriveEn,
                          fr: deriveFr,
                          source: current.name,
                        }),
                      }
                    "
                  />
                </div>
              </UiCard>
            </div>
          </template>
        </article>
      </section>
    </template>

    <UiDialog
      :open="connectionOpen"
      :title="i18n.t('vector.connection')"
      :description="i18n.t('vector.change_storage_location_help')"
      :close-label="i18n.t('ui.close')"
      size="large"
      @close="connectionOpen = false"
    >
      <VectorBackendPanel
        :health="health"
        :probing="probing"
        :applying="applying"
        :probe-result="probeResult"
        :error="connectionError"
        @probe="probe"
        @apply="applyConnection"
      />
    </UiDialog>
    <UiDialog
      :open="Boolean(confirm)"
      :title="confirm?.title || ''"
      :description="confirm?.message || ''"
      :close-label="i18n.t('ui.close')"
      size="medium"
      @close="confirm = null"
    >
      <div class="vector-confirm-actions">
        <UiButton :label="i18n.t('ui.cancel')" @click="confirm = null" />
        <UiButton
          :label="
            confirm?.kind === 'delete'
              ? i18n.t('vector.delete_collection')
              : i18n.t('vector.generate_language_collections')
          "
          :variant="confirm?.kind === 'delete' ? 'danger' : 'primary'"
          @click="confirmAction"
        />
      </div>
    </UiDialog>
  </main>
</template>

<style scoped>
.vector-native-page {
  display: grid;
  gap: var(--page-gap);
}
.vector-page-loading,
.vector-page-error {
  min-height: 240px;
  display: grid;
  place-content: center;
  gap: 10px;
  text-align: center;
}
.vector-tab-surface {
  margin-top: 12px;
}
.vector-search-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 8px;
  align-items: center;
}
.vector-confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
.vector-native-page :deep(.control) {
  min-height: 40px;
}
.vector-native-page :is(button, input, select, textarea, summary):focus-visible {
  outline: 3px solid var(--focus-ring, var(--accent));
  outline-offset: 2px;
}
@media (max-width: 760px) {
  .vector-search-row {
    grid-template-columns: 1fr;
  }
}
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
  display: grid !important;
  grid-template-columns: minmax(230px, 280px) minmax(0, 1fr) !important;
  gap: 12px !important;
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
@media (max-width: 1050px) {
  .vector-store-layout {
    grid-template-columns: 220px minmax(0, 1fr) !important;
  }
}
@media (max-width: 760px) {
  .vector-store-layout {
    grid-template-columns: 1fr !important;
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
.vector-build-history > summary {
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
.vector-build-list article > div {
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
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 10px;
}
.vector-overview-card {
  display: grid;
  gap: 5px;
  padding: 14px;
}
.vector-overview-card > span {
  font-size: 0.8125rem;
  font-weight: 750;
  letter-spacing: 0.035em;
  text-transform: uppercase;
  color: var(--muted);
}
.vector-overview-card > b {
  font-size: 0.98rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.vector-overview-card > small {
  color: var(--muted);
  font-size: 0.76rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-width: 1180px) {
  .vector-overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 760px) {
  .vector-overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
