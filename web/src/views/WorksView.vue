<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";
import { useShellStore } from "../stores/shell";
import AppIcon from "../components/AppIcon.vue";
import WorksOverviewCard from "../components/works/WorksOverviewCard.vue";
import WorksLibraryCard from "../components/works/WorksLibraryCard.vue";
import WorksWorkspaceHeader from "../components/works/WorksWorkspaceHeader.vue";
import CreateSiteDialog from "../components/works/CreateSiteDialog.vue";
import { useWorksWorkspace } from "../composables/useWorksWorkspace";
import * as runtime from "../runtime/runtime.js";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import UiLoadingState from "../components/ui/UiLoadingState.vue";
import CorpusRecordSemanticMap from "../components/corpus-builder/CorpusRecordSemanticMap.vue";
import CorpusSemanticGraphPanel from "../components/corpus-builder/CorpusSemanticGraphPanel.vue";
import SemanticMapFrame from "../components/semantic/SemanticMapFrame.vue";
import type { SemanticMapSource } from "../domain/semanticMap";
import { corpusBuildsApi } from "../api/corpus";
import { sitesApi, type SiteExportFormat, type SiteExportOptions } from "../api/sites";

const auth = useAuthStore();
const i18n = useI18nStore();
const shell = useShellStore();
const works = useWorksWorkspace();
const { snapshot, error } = works;
const loading = ref(true);
const query = ref("");
const revealed = ref(0);
let queryTimer = 0;
let revealToken = 0;
const page = ref<HTMLElement | null>(null);
const createSiteOpen = ref(false);
const createSiteBusy = ref(false);
const createSiteError = ref("");
const createSiteLanguages = ref<SiteExportOptions["languages"]>([]);
const createSiteProviderProfiles = ref<SiteExportOptions["provider_profiles"]>([]);

async function openCreateSite() {
  createSiteError.value = "";
  try {
    const options = await sitesApi.exportOptions();
    createSiteLanguages.value = options.languages;
    createSiteProviderProfiles.value = options.provider_profiles;
  } catch (cause) {
    createSiteLanguages.value = [...i18n.languages];
    createSiteProviderProfiles.value = [];
    createSiteError.value = cause instanceof Error ? cause.message : String(cause);
  }
  createSiteOpen.value = true;
}

function closeCreateSite() {
  if (createSiteBusy.value) return;
  createSiteOpen.value = false;
  createSiteError.value = "";
}

async function createSite(payload: {
  title: string;
  description: string;
  works: string[];
  export_format: SiteExportFormat;
  languages: string[];
  provider_profile_ids: string[];
}) {
  if (!snapshot.value?.activeStore || createSiteBusy.value) return;
  createSiteBusy.value = true;
  createSiteError.value = "";
  try {
    const download = await sitesApi.exportSite({
      store: snapshot.value.activeStore,
      works: payload.works,
      title: payload.title,
      description: payload.description,
      locale: payload.languages.includes(i18n.locale)
        ? i18n.locale
        : payload.languages[0] || "en-US",
      languages: payload.languages,
      provider_profile_ids: payload.provider_profile_ids,
      export_format: payload.export_format,
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
const visibleWorks = computed(() => (snapshot.value?.works || []).slice(0, revealed.value));
const sourceFileCount = computed(
  () => new Set((snapshot.value?.works || []).flatMap((work) => work.files || [])).size,
);
const showSkeleton = computed(() =>
  Boolean(snapshot.value?.mode === "admin" && snapshot.value.works.length && revealed.value === 0),
);
const showAddCard = computed(() =>
  Boolean(snapshot.value?.mode === "admin" && revealed.value >= (snapshot.value.works.length || 0)),
);
const loadingTitle = computed(() => i18n.t("works.loading"));
const loadingDetail = computed(() =>
  auth.isResearcher ? i18n.t("works.checking_database") : i18n.t("works.checking_database"),
);

function startReveal() {
  const token = ++revealToken;
  const total = snapshot.value?.works.length || 0;
  revealed.value = 0;
  if (!total || snapshot.value?.mode !== "admin") {
    revealed.value = total;
    return;
  }
  const step = () => {
    if (token !== revealToken) return;
    revealed.value = Math.min(total, (revealed.value || 0) + 12);
    if (revealed.value < total) requestAnimationFrame(step);
    else decorate();
  };
  requestAnimationFrame(step);
}

function decorate() {
  void nextTick(() => {
    if (page.value) runtime.decorateDisabledControls?.(page.value);
  });
}

async function boot() {
  loading.value = !snapshot.value;
  await works.activate();
  query.value = snapshot.value?.query || "";
  loading.value = false;
  startReveal();
  decorate();
}

function reload() {
  works.load();
  query.value = snapshot.value?.query || "";
  startReveal();
  decorate();
}

function applyQuery(value: string) {
  query.value = value;
  window.clearTimeout(queryTimer);
  const delay = snapshot.value?.mode === "researcher" ? 150 : 180;
  queryTimer = window.setTimeout(() => {
    works.setQuery(value);
    startReveal();
    decorate();
  }, delay);
}

function selectWork(work: string) {
  const y = window.scrollY;
  works.setOverview(work);
  requestAnimationFrame(() => window.scrollTo(0, y));
  decorate();
}

// --- semantic map dialog ----------------------------------------------------------------------------------------
const semanticMapDialog = ref<HTMLDialogElement | null>(null);
const semanticMapWork = ref("");
const semanticMapBuildId = ref("");
const semanticMapExtraBuilds = ref(0);
const semanticMapLoading = ref(false);
const semanticMapTab = ref<"graph" | "records" | "crossWorks">("graph");
const semanticMapRecords = ref<Array<{ record_id: string; build_id: string }>>([]);
const semanticMapRecordId = ref("");
const semanticMapRecord = computed(
  () =>
    semanticMapRecords.value.find((item) => item.record_id === semanticMapRecordId.value) || null,
);
const semanticMapError = ref(false);
const semanticMapSources = ref<SemanticMapSource[]>([]);

async function openWorkSemanticMap(work: string) {
  semanticMapWork.value = work;
  semanticMapBuildId.value = "";
  semanticMapExtraBuilds.value = 0;
  semanticMapError.value = false;
  semanticMapLoading.value = true;
  semanticMapTab.value = "graph";
  semanticMapRecords.value = [];
  semanticMapRecordId.value = "";
  const allSources = runtime.listSemanticMapSources?.();
  semanticMapSources.value = allSources?.records || [];
  semanticMapDialog.value?.showModal();
  try {
    void corpusBuildsApi
      .workSemanticMapRecords(work)
      .then((result) => {
        if (semanticMapWork.value !== work) return;
        semanticMapRecords.value = result.records;
        semanticMapRecordId.value = result.records[0]?.record_id || "";
      })
      .catch(() => undefined);
    const result = await corpusBuildsApi.workSemanticMapBuilds(work);
    const [first, ...rest] = result.build_ids;
    semanticMapBuildId.value = first || "";
    semanticMapExtraBuilds.value = rest.length;
    semanticMapError.value = !first;
  } catch {
    semanticMapError.value = true;
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
  startReveal();
  decorate();
}

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
watch(visibleWorks, decorate);

onMounted(() => {
  void boot();
});
onBeforeUnmount(() => window.clearTimeout(queryTimer));
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

    <template v-else-if="snapshot?.mode === 'admin' && snapshot.available">
      <WorksWorkspaceHeader
        :stores="snapshot.stores"
        :active-store="snapshot.activeStore"
        :active-store-count="snapshot.activeStoreCount"
        :total-works="snapshot.totalWorks"
        :total-records="snapshot.totalRecords"
        :source-file-count="sourceFileCount"
        :stores-empty-label="snapshot.storesEmptyLabel"
        :db-unavailable-reason="snapshot.dbUnavailableReason"
        :can-manage-corpus="snapshot.capabilities.canManageCorpus"
        :can-populate="snapshot.capabilities.canPopulate"
        :can-sync-all="snapshot.capabilities.canSyncAll"
        :can-create-site="Boolean(snapshot.activeStore && snapshot.works.length)"
        :corpus-manage-denied-reason="snapshot.corpusManageDeniedReason"
        :populate-disabled-reason="snapshot.populateDisabledReason"
        :sync-all-disabled-reason="snapshot.syncAllDisabledReason"
        :create-site-disabled-reason="
          !snapshot.activeStore
            ? i18n.t('site.create_requires_store')
            : i18n.t('site.create_requires_works')
        "
        @change-store="changeStore"
        @choose-jsonl="works.chooseJsonl()"
        @separate="works.separateWorks()"
        @populate-all="works.populateAll()"
        @sync-all="works.syncAll()"
        @create-site="openCreateSite"
      />

      <WorksOverviewCard
        v-if="snapshot.selected"
        :work="snapshot.selected"
        mode="admin"
        :citation-label="snapshot.citationLabel"
        @search="works.searchOverview(snapshot.selected.work)"
        @edit="works.editMetadata(snapshot.selected.work)"
        @populate="works.populateWork(snapshot.selected.work)"
        @annotations="works.openAnnotations(snapshot.selected.work)"
        @inspect="works.inspectMixed(snapshot.selected.work, $event)"
        @insight="works.searchInsight"
      />

      <div class="toolbar works-toolbar aligned-toolbar">
        <div class="search">
          <input
            id="worksSearch"
            :value="query"
            :placeholder="i18n.t('works.filter_title')"
            @input="applyQuery(($event.target as HTMLInputElement).value)"
          />
        </div>
        <div class="tools">
          <span class="note"
            >{{ snapshot.works.length.toLocaleString(i18n.locale) }} {{ i18n.t("works.shown") }} ·
            {{ snapshot.totalWorks.toLocaleString(i18n.locale) }}
            {{ i18n.t("dynamic.works") }} ·
            {{ snapshot.totalRecords.toLocaleString(i18n.locale) }}
            {{ i18n.t("dynamic.records") }}</span
          >
        </div>
      </div>

      <section id="worksGrid" class="works works-library-grid" :aria-label="i18n.t('nav.works')">
        <UiLoadingState
          v-if="showSkeleton"
          :label="
            i18n.tf('works.loading_cards', {
              count: snapshot.works.length.toLocaleString(i18n.locale),
            })
          "
          variant="skeleton"
          :skeleton-count="Math.min(4, snapshot.works.length)"
        />
        <WorksLibraryCard
          v-for="work in visibleWorks"
          :key="work.work"
          :work="work"
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
          @records="works.searchRecords(work.work)"
          @flagged="works.searchRecords(work.work, true)"
          @inspect="works.inspectMixed(work.work, $event)"
          @semantic-map="openWorkSemanticMap(work.work)"
        />
        <button
          v-if="showAddCard"
          id="worksAddJsonl"
          type="button"
          class="work-add-jsonl-card"
          :disabled="!snapshot.capabilities.canManageCorpus"
          :data-disabled-reason="
            snapshot.capabilities.canManageCorpus ? undefined : snapshot.corpusManageDeniedReason
          "
          :title="
            snapshot.capabilities.canManageCorpus ? undefined : snapshot.corpusManageDeniedReason
          "
          @click="works.chooseJsonl()"
        >
          <span class="work-add-jsonl-icon"><AppIcon name="plus" aria-hidden="true" /></span>
          <span>
            <b>{{ i18n.t("works.add_jsonl") }}</b>
            <small>{{ i18n.t("works.add_jsonl_help") }}</small>
          </span>
        </button>
      </section>
    </template>

    <template v-else-if="snapshot?.mode === 'researcher' && snapshot.available">
      <UiPageHeader
        :kicker="i18n.t('section.corpus')"
        :title="i18n.t('nav.works')"
        title-id="works-page-title"
        :description="i18n.t('research.works_menu_help')"
      />

      <WorksOverviewCard
        v-if="snapshot.selected"
        :work="snapshot.selected"
        mode="researcher"
        :citation-label="snapshot.citationLabel"
        @browse="works.browseResearcher(snapshot.selected.work)"
        @annotations="works.openAnnotations(snapshot.selected.work)"
      />

      <div class="toolbar works-toolbar">
        <div class="search">
          <input
            id="worksSearch"
            :value="query"
            :placeholder="i18n.t('research.filter_works')"
            @input="applyQuery(($event.target as HTMLInputElement).value)"
          />
        </div>
        <div class="tools">
          <select
            id="researchWorksStore"
            class="control"
            :value="snapshot.activeStore"
            @change="changeStore(($event.target as HTMLSelectElement).value)"
          >
            <option v-for="store in snapshot.stores" :key="store.name" :value="store.name">
              {{ store.name }}
            </option>
          </select>
          <span class="note"
            >{{ snapshot.works.length.toLocaleString(i18n.locale) }}
            {{ i18n.t("dynamic.works") }}</span
          >
        </div>
      </div>

      <section class="researcher-work-menu">
        <button
          v-for="work in snapshot.works"
          :key="work.work"
          type="button"
          class="researcher-work-menu-card"
          :class="{ active: snapshot.selectedWork === work.work }"
          :data-research-work="work.work"
          @click="selectWork(work.work)"
        >
          <img v-if="work.cover" class="researcher-work-cover" :src="work.cover" alt="" />
          <span v-else class="work-book-icon"><AppIcon name="books" aria-hidden="true" /></span>
          <span>
            <b>{{ work.work }}</b>
            <small>{{ work.subtitle }}</small>
            <small
              >{{ work.count.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records") }}</small
            >
          </span>
          <span class="work-menu-arrow">›</span>
        </button>
        <div v-if="!snapshot.works.length" class="llm-empty">
          {{ i18n.t("research.no_works") }}
        </div>
      </section>
    </template>

    <CreateSiteDialog
      v-if="createSiteOpen && snapshot?.mode === 'admin'"
      :works="snapshot.works"
      :store-name="snapshot.activeStore"
      :initial-work="snapshot.selectedWork"
      :languages="createSiteLanguages"
      :provider-profiles="createSiteProviderProfiles"
      :busy="createSiteBusy"
      :error="createSiteError"
      @cancel="closeCreateSite"
      @create="createSite"
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
      <p v-else-if="semanticMapError">{{ i18n.t("works.semantic_map_unavailable") }}</p>
      <template v-else-if="semanticMapBuildId">
        <p v-if="semanticMapExtraBuilds" class="note">
          {{ i18n.tf("works.semantic_map_multiple_builds", { count: semanticMapExtraBuilds }) }}
        </p>
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
          <CorpusSemanticGraphPanel :build-id="semanticMapBuildId" />
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
