<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";
import { useShellStore } from "../stores/shell";
import AppIcon from "../components/AppIcon.vue";
import WorksOverviewCard from "../components/works/WorksOverviewCard.vue";
import WorksLibraryCard from "../components/works/WorksLibraryCard.vue";
import WorksLibraryList from "../components/works/WorksLibraryList.vue";
import WorksCorpusContext from "../components/works/WorksCorpusContext.vue";
import WorksLibraryToolbar from "../components/works/WorksLibraryToolbar.vue";
import WorksWorkspaceHeader from "../components/works/WorksWorkspaceHeader.vue";
import CreateSiteDialog from "../components/works/CreateSiteDialog.vue";
import { useWorksWorkspace } from "../composables/useWorksWorkspace";
import UiDialog from "../components/ui/UiDialog.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiLoadingState from "../components/ui/UiLoadingState.vue";
import CorpusRecordSemanticMap from "../components/corpus-builder/CorpusRecordSemanticMap.vue";
import SemanticMapFrame from "../components/semantic/SemanticMapFrame.vue";
import type { WorksDbStatusKind, WorksFilters, WorksSort, WorksViewMode } from "../types/works";
import type { SemanticMapSource } from "../domain/semanticMap";
import { corpusBuildsApi } from "../api/corpus";
import { semanticMapService } from "../services/semanticMap";
import {
  sitesApi,
  type SiteExportFormat,
  type SiteExportOptions,
  type SiteRecordProfile,
} from "../api/sites";

const auth = useAuthStore();
const i18n = useI18nStore();
const shell = useShellStore();
const works = useWorksWorkspace();
const { snapshot, error } = works;
const loading = ref(true);
const query = ref("");
let queryTimer = 0;
const page = ref<HTMLElement | null>(null);
const createSiteOpen = ref(false);
const createSiteBusy = ref(false);
const createSiteError = ref("");
const createSiteLanguages = ref<SiteExportOptions["languages"]>([]);
const createSiteTransformers = ref<SiteExportOptions["transformers_runtime"] | undefined>();
const createSiteProgress = ref<{ file: string; received: number; total: number } | null>(null);

async function openCreateSite() {
  createSiteError.value = "";
  try {
    const options = await sitesApi.exportOptions();
    createSiteLanguages.value = options.languages;
    createSiteTransformers.value = options.transformers_runtime;
  } catch (cause) {
    createSiteLanguages.value = [...i18n.languages];
    createSiteError.value = cause instanceof Error ? cause.message : String(cause);
  }
  createSiteOpen.value = true;
}

function closeCreateSite() {
  if (createSiteBusy.value) return;
  createSiteOpen.value = false;
  createSiteError.value = "";
}

async function refreshTransformersRuntime() {
  const options = await sitesApi.exportOptions();
  createSiteTransformers.value = options.transformers_runtime;
}

async function runTransformersDownload() {
  createSiteProgress.value = {
    file: "Transformers.js",
    received: 0,
    total: createSiteTransformers.value?.download_bytes || 1,
  };
  try {
    await sitesApi.downloadTransformersRuntime((event) => {
      if (event.status === "error") return;
      createSiteProgress.value = {
        file: event.file || "Transformers.js",
        received: Number(event.received_total || event.received || 0),
        total: Number(event.total || createSiteTransformers.value?.download_bytes || 1),
      };
    });
    await refreshTransformersRuntime();
  } finally {
    createSiteProgress.value = null;
  }
}

async function downloadTransformersRuntime() {
  if (createSiteBusy.value || createSiteTransformers.value?.cached) return;
  createSiteBusy.value = true;
  createSiteError.value = "";
  try {
    await runTransformersDownload();
  } catch (cause) {
    createSiteError.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    createSiteBusy.value = false;
  }
}

async function deleteTransformersRuntime() {
  if (createSiteBusy.value) return;
  createSiteBusy.value = true;
  createSiteError.value = "";
  try {
    const result = await sitesApi.deleteTransformersRuntime();
    createSiteTransformers.value = result.transformers_runtime;
  } catch (cause) {
    createSiteError.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    createSiteBusy.value = false;
  }
}

async function createSite(payload: {
  title: string;
  description: string;
  works: string[];
  export_format: SiteExportFormat;
  record_profile: SiteRecordProfile;
  languages: string[];
  include_transformers: boolean;
  include_vectors: boolean;
}) {
  if (!snapshot.value?.activeStore || createSiteBusy.value) return;
  createSiteBusy.value = true;
  createSiteError.value = "";
  try {
    if (!createSiteTransformers.value?.cached) await runTransformersDownload();
    const download = await sitesApi.exportSite({
      store: snapshot.value.activeStore,
      works: payload.works,
      title: payload.title,
      description: payload.description,
      locale: payload.languages.includes(i18n.locale)
        ? i18n.locale
        : payload.languages[0] || "en-US",
      languages: payload.languages,
      include_transformers: payload.include_transformers,
      include_vectors: payload.include_vectors,
      export_format: payload.export_format,
      record_profile: payload.record_profile,
    });
    const url = URL.createObjectURL(download.blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = download.filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    createSiteOpen.value = false;
  } catch (cause) {
    createSiteError.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    createSiteBusy.value = false;
  }
}

const fileSignature = computed(() =>
  shell.snapshot.files.map((file) => `${file.id}:${file.count}:${file.dirty}`).join("|"),
);
const libraryPage = ref(1);
const libraryPageSize = computed(() => (snapshot.value?.viewMode === "list" ? 100 : 48));
const libraryPageCount = computed(() =>
  Math.max(1, Math.ceil((snapshot.value?.works.length || 0) / libraryPageSize.value)),
);
const visibleWorks = computed(() => {
  const items = snapshot.value?.works || [];
  const start = (libraryPage.value - 1) * libraryPageSize.value;
  return items.slice(start, start + libraryPageSize.value);
});
const showLibraryPagination = computed(() =>
  Boolean(snapshot.value?.works.length && libraryPageCount.value > 1),
);
function setLibraryPage(pageNumber: number) {
  libraryPage.value = Math.min(libraryPageCount.value, Math.max(1, pageNumber));
}
function resetLibraryPage() {
  libraryPage.value = 1;
}
/** Inspector commands, bound to the selected work; the persistent pane and the dialog share them. */
function inspectorHandlers(work: string) {
  return {
    onSearch: () => works.searchOverview(work),
    onReview: () => works.reviewFlagged(work),
    onEdit: () => works.editMetadata(work),
    onPopulate: () => works.populateWork(work),
    onAnnotations: () => works.openAnnotations(work),
    onBrowse: () => works.browseResearcher(work),
    onSemanticMap: () => openWorkSemanticMap(work),
    onSync: () => works.syncWork(work),
    onInspect: (field: string) => works.inspectMixed(work, field),
    onInsight: works.searchInsight,
  };
}
const loadingTitle = computed(() => i18n.t("works.loading"));
const loadingDetail = computed(() =>
  auth.isResearcher ? i18n.t("works.checking_database") : i18n.t("works.checking_database"),
);

async function boot() {
  loading.value = !snapshot.value;
  await works.activate();
  query.value = snapshot.value?.query || "";
  loading.value = false;
}

function reload() {
  works.load();
  query.value = snapshot.value?.query || "";
}

function applyQuery(value: string) {
  query.value = value;
  window.clearTimeout(queryTimer);
  const delay = snapshot.value?.mode === "researcher" ? 150 : 180;
  queryTimer = window.setTimeout(() => {
    works.setQuery(value);
    resetLibraryPage();
  }, delay);
}

function selectWork(work: string) {
  works.setOverview(work);
}

function openWorkRecords(work: string) {
  if (snapshot.value?.mode === "researcher") works.browseResearcher(work);
  else works.searchRecords(work);
}

async function closeInspector() {
  const work = snapshot.value?.selectedWork || "";
  works.setOverview("");
  await nextTick();
  // The persistent inspector has no dialog to restore focus, so return it to the work it described.
  if (wide.value) {
    page.value?.querySelector<HTMLElement>(`[data-select-work="${CSS.escape(work)}"]`)?.focus();
  }
}

function applyView(patch: {
  sort?: WorksSort;
  needsReview?: boolean;
  dbStatus?: WorksDbStatusKind | "";
  author?: string;
  viewMode?: WorksViewMode;
}) {
  works.setView(patch);
  resetLibraryPage();
}
function applyFilters(patch: Partial<WorksFilters>) {
  applyView(patch);
}

// The inspector sits beside the library when there is room, and opens in a dialog otherwise, so
// selecting a work never pushes the library down the page.
const wide = ref(true);
let wideQuery: MediaQueryList | null = null;
function syncWide() {
  wide.value = wideQuery ? wideQuery.matches : true;
}

// --- semantic map dialog ----------------------------------------------------------------------------------------
const semanticMapDialog = ref<HTMLDialogElement | null>(null);
const semanticMapWork = ref("");
const semanticMapLoading = ref(false);
const semanticMapTab = ref<"graph" | "records" | "crossWorks">("graph");
const semanticMapRecords = ref<Array<{ record_id: string; build_id: string }>>([]);
const semanticMapRecordId = ref("");
const semanticMapRecord = computed(
  () =>
    semanticMapRecords.value.find((item) => item.record_id === semanticMapRecordId.value) || null,
);
const semanticMapSources = ref<SemanticMapSource[]>([]);
const semanticMapPersistedWorkSources = ref<SemanticMapSource[]>([]);
const semanticMapGeneration = ref("");
const semanticMapFallbackSources = computed(() =>
  semanticMapPersistedWorkSources.value.length
    ? semanticMapPersistedWorkSources.value
    : semanticMapSources.value.filter((source) => source.work === semanticMapWork.value),
);

async function openWorkSemanticMap(work: string) {
  semanticMapWork.value = work;
  semanticMapLoading.value = true;
  semanticMapTab.value = "graph";
  semanticMapRecords.value = [];
  semanticMapRecordId.value = "";
  semanticMapPersistedWorkSources.value = [];
  semanticMapGeneration.value = "";
  // Cross-Work exploration still uses the active workspace. The selected Work,
  // however, now comes from the persisted canonical semantic projection below.
  const allSources = semanticMapService.listSources();
  semanticMapSources.value = allSources.records;
  semanticMapDialog.value?.showModal();
  try {
    const result = await corpusBuildsApi.workSemanticMap(work);
    if (semanticMapWork.value !== work) return;
    semanticMapPersistedWorkSources.value = result.sources;
    semanticMapGeneration.value = result.generation;
    semanticMapRecords.value = result.records;
    semanticMapRecordId.value = result.records[0]?.record_id || "";
  } catch {
    // Legacy/local workspaces may not yet have publication provenance. Keep the
    // established visual map available from the active workspace in that case.
  } finally {
    semanticMapLoading.value = false;
  }
}
function closeWorkSemanticMap() {
  semanticMapDialog.value?.close();
}

async function changeStore(name: string) {
  loading.value = true;
  await works.setStore(name);
  query.value = snapshot.value?.query || "";
  loading.value = false;
  resetLibraryPage();
}

watch(
  () => [snapshot.value?.works.length, snapshot.value?.viewMode],
  () => setLibraryPage(libraryPage.value),
);
watch(fileSignature, () => {
  if (loading.value || !snapshot.value) return;
  reload();
});
watch(
  () => shell.snapshot.activeStore,
  () => {
    if (loading.value || !snapshot.value) return;
    reload();
  },
);
watch(
  () => i18n.locale,
  () => {
    if (loading.value || !snapshot.value) return;
    reload();
  },
);

onMounted(() => {
  wideQuery = window.matchMedia?.("(min-width: 1100px)") ?? null;
  wideQuery?.addEventListener?.("change", syncWide);
  syncWide();
  void boot();
});
onBeforeUnmount(() => {
  window.clearTimeout(queryTimer);
  wideQuery?.removeEventListener?.("change", syncWide);
});
</script>

<template>
  <main ref="page" class="works-page" :aria-busy="loading">
    <section v-if="loading" class="card view-loading-card">
      <UiLoadingState
        :label="loadingTitle"
        :detail="loadingDetail"
        variant="skeleton"
        :skeleton-count="3"
      />
    </section>

    <div v-else-if="error" class="info error" role="alert">{{ error }}</div>

    <section v-else-if="snapshot?.mode === 'admin' && !snapshot.available" class="empty">
      <div class="drop">
        <div class="drop-icon"><AppIcon name="upload" aria-hidden="true" /></div>
        <h1>
          {{
            snapshot.shared
              ? i18n.t("records.open_shared_workspace")
              : i18n.t("records.open_workspace")
          }}
        </h1>
        <p>
          {{
            snapshot.shared
              ? i18n.t("records.shared_workspace_help")
              : i18n.t("records.open_workspace_help")
          }}
        </p>
        <button id="choose" type="button" class="btn primary" @click="works.chooseJsonl()">
          <AppIcon name="upload" aria-hidden="true" />{{ i18n.t("records.choose_jsonl") }}
        </button>
      </div>
    </section>

    <section v-else-if="snapshot?.mode === 'researcher' && !snapshot.available" class="empty">
      <div class="drop">
        <div class="drop-icon"><AppIcon name="database" aria-hidden="true" /></div>
        <h1>{{ i18n.t("research.no_database") }}</h1>
      </div>
    </section>

    <template v-else-if="snapshot?.available">
      <WorksWorkspaceHeader
        :mode="snapshot.mode"
        :can-manage-corpus="snapshot.capabilities.canManageCorpus"
        :can-populate="snapshot.capabilities.canPopulate"
        :can-create-site="Boolean(snapshot.activeStore && snapshot.totalWorks)"
        :corpus-manage-denied-reason="snapshot.corpusManageDeniedReason"
        :populate-disabled-reason="snapshot.populateDisabledReason"
        :create-site-disabled-reason="
          !snapshot.activeStore
            ? i18n.t('site.create_requires_store')
            : i18n.t('site.create_requires_works')
        "
        @choose-jsonl="works.chooseJsonl()"
        @separate="works.separateWorks()"
        @populate-all="works.populateAll()"
        @create-site="openCreateSite"
      />

      <WorksCorpusContext
        :mode="snapshot.mode"
        :stores="snapshot.stores"
        :active-store="snapshot.activeStore"
        :active-store-count="snapshot.activeStoreCount"
        :source-file-count="snapshot.sourceFileCount"
        :total-records="snapshot.totalRecords"
        :index-freshness="snapshot.indexFreshness"
        :stores-empty-label="snapshot.storesEmptyLabel"
        :db-unavailable-reason="snapshot.dbUnavailableReason"
        :can-sync-all="snapshot.capabilities.canSyncAll"
        :sync-all-disabled-reason="snapshot.syncAllDisabledReason"
        @change-store="changeStore"
        @sync-all="works.syncAll()"
      />

      <WorksLibraryToolbar
        :mode="snapshot.mode"
        :query="query"
        :sort="snapshot.sort"
        :filters="snapshot.filters"
        :view-mode="snapshot.viewMode"
        :authors="snapshot.authors"
        :total-works="snapshot.totalWorks"
        :visible-works="snapshot.visibleWorks"
        :total-review="snapshot.totalReview"
        @query="applyQuery"
        @sort="applyView({ sort: $event })"
        @filters="applyFilters"
        @view-mode="applyView({ viewMode: $event })"
      />

      <div class="works-layout" :class="{ 'has-inspector': wide && snapshot.selected }">
        <section
          id="worksGrid"
          class="works-library"
          :class="{ list: snapshot.viewMode === 'list' }"
          :aria-label="i18n.t('nav.works')"
        >
          <WorksLibraryList
            v-if="snapshot.viewMode === 'list'"
            :works="visibleWorks"
            :mode="snapshot.mode"
            :selected-work="snapshot.selectedWork"
            :can-sync="snapshot.capabilities.canSync"
            :sync-disabled-reason="snapshot.dbUnavailableReason"
            @select="selectWork"
            @sync="works.syncWork"
            @populate="works.populateWork"
            @edit="works.editMetadata"
            @review="works.reviewFlagged"
            @improve="works.autoImprove"
            @remove="works.removeWork"
            @records="openWorkRecords"
            @flagged="(work) => works.searchRecords(work, true)"
            @semantic-map="openWorkSemanticMap"
          />
          <template v-else>
            <WorksLibraryCard
              v-for="work in visibleWorks"
              :key="work.work"
              :work="work"
              :mode="snapshot.mode"
              :selected="snapshot.selectedWork === work.work"
              :can-sync="snapshot.capabilities.canSync"
              :sync-disabled-reason="snapshot.dbUnavailableReason"
              @select="selectWork(work.work)"
              @sync="works.syncWork(work.work)"
              @populate="works.populateWork(work.work)"
              @edit="works.editMetadata(work.work)"
              @review="works.reviewFlagged(work.work)"
              @improve="works.autoImprove(work.work)"
              @remove="works.removeWork(work.work)"
              @records="openWorkRecords(work.work)"
              @flagged="works.searchRecords(work.work, true)"
              @inspect="works.inspectMixed(work.work, $event)"
              @semantic-map="openWorkSemanticMap(work.work)"
            />
          </template>
          <p v-if="!snapshot.works.length" class="works-empty">
            {{
              snapshot.totalWorks
                ? i18n.t("works.no_matches")
                : snapshot.mode === "admin"
                  ? i18n.t("works.add_jsonl_help")
                  : i18n.t("research.no_works")
            }}
          </p>
          <nav
            v-if="showLibraryPagination"
            class="works-library-pagination"
            :aria-label="i18n.t('works.library_pagination')"
          >
            <UiButton
              size="small"
              variant="ghost"
              :label="i18n.t('ui.previous')"
              :disabled="libraryPage <= 1"
              @click="setLibraryPage(libraryPage - 1)"
            />
            <span>
              {{
                i18n.tf("dynamic.page_of_pages", {
                  page: libraryPage,
                  pages: libraryPageCount,
                })
              }}
            </span>
            <UiButton
              size="small"
              variant="ghost"
              :label="i18n.t('ui.next')"
              :disabled="libraryPage >= libraryPageCount"
              @click="setLibraryPage(libraryPage + 1)"
            />
          </nav>
        </section>

        <aside
          v-if="wide && snapshot.selected"
          class="works-inspector-pane"
          :aria-label="i18n.t('works.inspector_label')"
        >
          <WorksOverviewCard
            :key="snapshot.selected.work"
            :work="snapshot.selected"
            :mode="snapshot.mode"
            :citation-label="snapshot.citationLabel"
            :can-sync="snapshot.capabilities.canSync"
            :sync-disabled-reason="snapshot.dbUnavailableReason"
            closable
            v-bind="inspectorHandlers(snapshot.selected.work)"
            @close="closeInspector"
          />
        </aside>
      </div>

      <UiDialog
        v-if="!wide && snapshot.selected"
        :title="snapshot.selected.work"
        :close-label="i18n.t('ui.close')"
        size="large"
        @close="closeInspector"
      >
        <WorksOverviewCard
          :key="snapshot.selected.work"
          :work="snapshot.selected"
          :mode="snapshot.mode"
          :citation-label="snapshot.citationLabel"
          :can-sync="snapshot.capabilities.canSync"
          :sync-disabled-reason="snapshot.dbUnavailableReason"
          embedded
          v-bind="inspectorHandlers(snapshot.selected.work)"
        />
      </UiDialog>
    </template>

    <CreateSiteDialog
      v-if="createSiteOpen && snapshot?.mode === 'admin'"
      :works="snapshot.scopeWorks"
      :store-name="snapshot.activeStore"
      :initial-work="snapshot.selectedWork"
      :languages="createSiteLanguages"
      :transformers-runtime="createSiteTransformers"
      :download-progress="createSiteProgress"
      :busy="createSiteBusy"
      :error="createSiteError"
      @cancel="closeCreateSite"
      @create="createSite"
      @delete-runtime="deleteTransformersRuntime"
      @download-runtime="downloadTransformersRuntime"
    />

    <dialog
      ref="semanticMapDialog"
      class="works-semantic-map-dialog"
      :aria-label="i18n.tf('works.semantic_map_dialog_title', { work: semanticMapWork })"
      @cancel.prevent="closeWorkSemanticMap"
    >
      <header>
        <h2>{{ i18n.tf("works.semantic_map_dialog_title", { work: semanticMapWork }) }}</h2>
        <button type="button" :aria-label="i18n.t('ui.close')" @click="closeWorkSemanticMap">
          ×
        </button>
      </header>
      <UiLoadingState v-if="semanticMapLoading" :label="i18n.t('ui.loading')" />
      <template v-else>
        <div class="works-semantic-tabs" role="tablist" :aria-label="i18n.t('works.semantic_map')">
          <button
            type="button"
            id="works-semantic-tab-graph"
            role="tab"
            aria-controls="works-semantic-panel-graph"
            :aria-selected="semanticMapTab === 'graph'"
            :class="{ on: semanticMapTab === 'graph' }"
            @click="semanticMapTab = 'graph'"
          >
            {{ i18n.t("works.semantic_map_tab_graph") }}
          </button>
          <button
            type="button"
            id="works-semantic-tab-records"
            role="tab"
            aria-controls="works-semantic-panel-records"
            :aria-selected="semanticMapTab === 'records'"
            :class="{ on: semanticMapTab === 'records' }"
            @click="semanticMapTab = 'records'"
          >
            {{ i18n.t("works.semantic_map_tab_records") }}
          </button>
          <button
            type="button"
            id="works-semantic-tab-cross-works"
            role="tab"
            aria-controls="works-semantic-panel-cross-works"
            :aria-selected="semanticMapTab === 'crossWorks'"
            :class="{ on: semanticMapTab === 'crossWorks' }"
            @click="semanticMapTab = 'crossWorks'"
          >
            {{ i18n.t("works.semantic_map_tab_cross_works") }}
          </button>
        </div>
        <div
          v-if="semanticMapTab === 'graph'"
          id="works-semantic-panel-graph"
          role="tabpanel"
          aria-labelledby="works-semantic-tab-graph"
          tabindex="0"
        >
          <SemanticMapFrame
            variant="page"
            :sources="semanticMapFallbackSources"
            :cache-key="semanticMapGeneration"
            :show-close="false"
          />
        </div>
        <SemanticMapFrame
          v-if="semanticMapTab === 'crossWorks'"
          variant="modal"
          :sources="semanticMapSources"
          focus-id=""
          id="works-semantic-panel-cross-works"
          role="tabpanel"
          aria-labelledby="works-semantic-tab-cross-works"
          tabindex="0"
        />
        <div
          v-if="semanticMapTab === 'records'"
          id="works-semantic-panel-records"
          role="tabpanel"
          aria-labelledby="works-semantic-tab-records"
          tabindex="0"
        >
          <p v-if="!semanticMapRecords.length" class="note">
            {{ i18n.t("works.semantic_map_no_records") }}
          </p>
          <template v-else>
            <label class="works-semantic-record-pick">
              <span>{{ i18n.t("works.semantic_map_pick_record") }}</span>
              <select v-model="semanticMapRecordId" class="control">
                <option
                  v-for="item in semanticMapRecords"
                  :key="item.record_id"
                  :value="item.record_id"
                >
                  {{ item.record_id }}
                </option>
              </select>
            </label>
            <CorpusRecordSemanticMap
              v-if="semanticMapRecord"
              :key="semanticMapRecord.record_id"
              id-prefix="works"
              :build-id="semanticMapRecord.build_id"
              :record="{ record_id: semanticMapRecord.record_id }"
              @open-record="semanticMapRecordId = $event"
            />
          </template>
        </div>
      </template>
    </dialog>
  </main>
</template>

<style scoped>
.works-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-4);
  align-items: start;
}
.works-layout.has-inspector {
  grid-template-columns: minmax(0, 1fr) minmax(24rem, 30rem);
}
.works-library {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 22rem), 1fr));
  gap: var(--space-3);
  align-content: start;
  min-width: 0;
}
.works-library.list {
  grid-template-columns: minmax(0, 1fr);
  gap: 0;
}
.works-empty {
  grid-column: 1 / -1;
  margin: 0;
  padding: var(--space-4);
  color: var(--text-secondary);
}
.works-library-pagination {
  grid-column: 1 / -1;
  display: flex;
  gap: var(--space-2);
  align-items: center;
  justify-content: center;
  padding-block: var(--space-3);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.works-inspector-pane {
  position: sticky;
  top: var(--space-4);
  max-height: calc(100vh - var(--space-8));
  overflow-y: auto;
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
</style>
