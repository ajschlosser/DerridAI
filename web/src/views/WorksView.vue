<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";
import { useShellStore } from "../stores/shell";
import AppIcon from "../components/AppIcon.vue";
import type { WorksItem, WorksSnapshot } from "../types/works";
import { annotationsService } from "../services/annotations";

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

const fileSignature = computed(() =>
  shell.snapshot.files.map((file) => `${file.id}:${file.count}:${file.dirty}`).join("|"),
);
const visibleWorks = computed(() => (snapshot.value?.works || []).slice(0, revealed.value));
const showSkeleton = computed(() => Boolean(snapshot.value?.mode === "admin" && snapshot.value.works.length && revealed.value === 0));
const showAddCard = computed(() => Boolean(snapshot.value?.mode === "admin" && revealed.value >= (snapshot.value.works.length || 0)));
const loadingTitle = computed(() => i18n.t("works.loading", "Loading works"));
const loadingDetail = computed(() =>
  auth.isResearcher
    ? i18n.t("works.checking_database", "Checking corpus databaseâ€¦")
    : i18n.t("works.checking_database", "Checking vector database stateâ€¦"),
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
  queryTimer = window.setTimeout(load, 80);
}
function selectWork(work: string) {
  runtime.setWorksOverview?.(work);
  load();
}
async function syncWork(work: WorksItem) {
  await runtime.syncWork?.(work.work);
  load();
}
async function syncAll() {
  await runtime.syncAllWorks?.();
  load();
}
function searchWork(work: string) {
  runtime.searchWork?.(work);
}
function editMetadata(work: string) {
  runtime.openWorkMetadataEditor?.(work);
}
function populateMetadata(work: string) {
  runtime.openWorkMetadataLlmDialog?.(work);
}
function openAnnotations(work: string) {
  annotationsService.openWorkAnnotations(work);
}
function onCardKeydown(work: string, event: KeyboardEvent) {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  selectWork(work);
}

function selectWork(work: string) {
  const y = window.scrollY;
  works.setOverview(work);
  requestAnimationFrame(() => window.scrollTo(0, y));
  decorate();
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
watch(() => shell.snapshot.activeStore, () => {
  if (loading.value || !snapshot.value) return;
  reload();
});
watch(() => i18n.locale, () => {
  if (loading.value || !snapshot.value) return;
  reload();
});
watch(visibleWorks, decorate);

onMounted(() => {
  void boot();
});
onBeforeUnmount(() => window.clearTimeout(queryTimer));
</script>

<template>
  <main ref="page" class="works-page" :aria-busy="loading">
    <section v-if="loading" class="card view-loading-card">
      <div class="view-loading-copy">
        <span class="spinner"></span>
        <div>
          <b>{{ loadingTitle }}</b>
          <p>{{ loadingDetail }}</p>
        </div>
      </div>
      <div class="progressive-loading" role="status" aria-live="polite">
        <div class="progressive-loading-head"><span class="spinner small-spinner"></span><b>Loading cards</b></div>
        <div class="progressive-skeleton-grid">
          <div class="progressive-skeleton-card"><i></i><i></i><i></i></div>
          <div class="progressive-skeleton-card"><i></i><i></i><i></i></div>
          <div class="progressive-skeleton-card"><i></i><i></i><i></i></div>
        </div>
      </div>
    </section>

    <div v-else-if="error" class="info error" role="alert">{{ error }}</div>

    <section v-else-if="snapshot?.mode === 'admin' && !snapshot.available" class="empty">
      <div class="drop">
        <div class="drop-icon"><AppIcon name="upload" aria-hidden="true" /></div>
        <h1>{{ snapshot.shared ? i18n.t("records.open_shared_workspace", "Open the shared corpus workspace") : i18n.t("records.open_workspace", "Open a corpus workspace") }}</h1>
        <p>{{ snapshot.shared ? i18n.t("records.shared_workspace_help", "This link preserves the table state and filters, while JSONL contents remain browser-local. Choose the same JSONL file to restore this shared view.") : i18n.t("records.open_workspace_help", "Drop one or more JSONL files anywhere on this page, or choose files manually. Each file stays in its own tab and can be edited, compared, searched, exported, or sent to the corpus database.") }}</p>
        <button id="choose" type="button" class="btn primary" @click="works.chooseJsonl()"><AppIcon name="upload" aria-hidden="true" />{{ i18n.t("records.choose_jsonl", "Choose JSONL files") }}</button>
      </div>
    </section>

    <section v-else-if="snapshot?.mode === 'researcher' && !snapshot.available" class="empty">
      <div class="drop">
        <div class="drop-icon"><AppIcon name="database" aria-hidden="true" /></div>
        <h1>{{ i18n.t("research.no_database", "No corpus database available") }}</h1>
      </div>
    </section>

    <template v-else-if="snapshot?.mode === 'admin' && snapshot.available">
      <section class="card works-database-context">
        <div>
          <span class="section-label">{{ i18n.t("works.database_context", "Works synchronization database") }}</span>
          <b>{{ snapshot.activeStore || i18n.t("research.none_selected", "No database selected") }}</b>
          <small>{{ i18n.t("works.database_context_help", "Sync status and Sync actions on this page refer to the selected corpus database. Changing it does not change your loaded JSONL files.") }}</small>
        </div>
        <label class="field">
          <span>{{ i18n.t("research.corpus_database", "Corpus database") }}</span>
          <select
            id="worksStore"
            class="control compact-select"
            :value="snapshot.activeStore"
            :disabled="!snapshot.stores.length"
            :data-disabled-reason="snapshot.stores.length ? undefined : snapshot.dbUnavailableReason"
            :title="snapshot.stores.length ? undefined : snapshot.dbUnavailableReason"
            @change="changeStore(($event.target as HTMLSelectElement).value)"
          >
            <option v-if="!snapshot.stores.length" value="">{{ snapshot.storesEmptyLabel }}</option>
            <option v-for="store in snapshot.stores" :key="store.name" :value="store.name">{{ store.name }} ({{ store.count }})</option>
          </select>
          <small>{{ snapshot.activeStore ? `${snapshot.activeStoreCount.toLocaleString(i18n.locale)} ${i18n.t("dynamic.records", "records")}` : snapshot.dbUnavailableReason }}</small>
        </label>
      </section>

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
          <input id="worksSearch" :value="query" :placeholder="i18n.t('works.filter_title', 'Filter works by title')" @input="applyQuery(($event.target as HTMLInputElement).value)">
        </div>
        <div class="tools">
          <button id="separateWorks" type="button" class="btn small" @click="works.separateWorks()"><AppIcon name="filter" aria-hidden="true" />{{ i18n.t("works.separate_jsonl", "Separate works") }}</button>
          <button
            id="populateAllWorks"
            type="button"
            class="btn small soft"
            :disabled="!snapshot.capabilities.canPopulate"
            :data-disabled-reason="snapshot.capabilities.canPopulate ? undefined : snapshot.populateDisabledReason"
            :title="snapshot.capabilities.canPopulate ? undefined : snapshot.populateDisabledReason"
            @click="works.populateAll()"
          ><AppIcon name="spark" aria-hidden="true" />{{ i18n.t("works.populate_all_metadata", "Populate all metadata with LLM") }}</button>
          <button
            id="syncAllWorks"
            type="button"
            class="btn small primary"
            :disabled="!snapshot.capabilities.canSyncAll"
            :data-disabled-reason="snapshot.capabilities.canSyncAll ? undefined : snapshot.syncAllDisabledReason"
            :title="snapshot.capabilities.canSyncAll ? undefined : snapshot.syncAllDisabledReason"
            @click="works.syncAll()"
          ><AppIcon name="database" aria-hidden="true" />{{ i18n.t("works.sync_all", "Sync all works") }}</button>
          <span class="note">{{ snapshot.works.length.toLocaleString(i18n.locale) }} {{ i18n.t("works.shown", "shown") }} Â· {{ snapshot.totalWorks.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.works", "works") }} Â· {{ snapshot.totalRecords.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records", "records") }}</span>
        </div>
      </div>

      <section id="worksGrid" class="works works-library-grid" :aria-label="i18n.t('nav.works', 'Works')">
        <div v-if="showSkeleton" class="progressive-loading" role="status" aria-live="polite">
          <div class="progressive-loading-head"><span class="spinner small-spinner"></span><b>{{ i18n.tf("works.loading_cards", "Loading {count} work cards", {count: snapshot.works.length.toLocaleString(i18n.locale)}) }}</b></div>
          <div class="progressive-skeleton-grid">
            <div v-for="index in Math.min(4, snapshot.works.length)" :key="index" class="progressive-skeleton-card"><i></i><i></i><i></i></div>
          </div>
        </div>
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
        />
        <button
          v-if="showAddCard"
          id="worksAddJsonl"
          type="button"
          class="work-add-jsonl-card"
          :disabled="!snapshot.capabilities.canManageCorpus"
          :data-disabled-reason="snapshot.capabilities.canManageCorpus ? undefined : snapshot.corpusManageDeniedReason"
          :title="snapshot.capabilities.canManageCorpus ? undefined : snapshot.corpusManageDeniedReason"
          @click="works.chooseJsonl()"
        >
          <span class="work-add-jsonl-icon"><AppIcon name="plus" aria-hidden="true" /></span>
          <span>
            <b>{{ i18n.t("works.add_jsonl", "Add a JSONL file") }}</b>
            <small>{{ i18n.t("works.add_jsonl_help", "Open another corpus source and add its works to this workspace.") }}</small>
          </span>
        </button>
      </section>
    </template>

    <template v-else-if="snapshot?.mode === 'researcher' && snapshot.available">
      <section class="page-heading legacy-page-heading">
        <div>
          <p>{{ i18n.t("section.corpus", "Corpus") }}</p>
          <h1>{{ i18n.t("nav.works", "Works") }}</h1>
          <span>{{ i18n.t("research.works_menu_help", "Browse works in the selected corpus database. Select a work for an overview, then browse its summarized records.") }}</span>
        </div>
      </section>

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
          <input id="worksSearch" :value="query" :placeholder="i18n.t('research.filter_works', 'Filter works by title')" @input="applyQuery(($event.target as HTMLInputElement).value)">
        </div>
        <div class="tools">
          <select id="researchWorksStore" class="control" :value="snapshot.activeStore" @change="changeStore(($event.target as HTMLSelectElement).value)">
            <option v-for="store in snapshot.stores" :key="store.name" :value="store.name">{{ store.name }}</option>
          </select>
          <span class="note">{{ snapshot.works.length.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.works", "works") }}</span>
        </div>
      </div>

      <section class="researcher-work-menu">
        <button
          v-for="work in snapshot.works"
          :key="work.work"
          type="button"
          class="researcher-work-menu-card"
          :class="{active: snapshot.selectedWork === work.work}"
          :data-research-work="work.work"
          @click="selectWork(work.work)"
        >
          <img v-if="work.cover" class="researcher-work-cover" :src="work.cover" alt="">
          <span v-else class="work-book-icon"><AppIcon name="books" aria-hidden="true" /></span>
          <span>
            <b>{{ work.work }}</b>
            <small>{{ work.subtitle }}</small>
            <small>{{ work.count.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records", "records") }}</small>
          </span>
          <span class="work-menu-arrow">â€º</span>
        </button>
        <div v-if="!snapshot.works.length" class="llm-empty">{{ i18n.t("research.no_works", "No works are available.") }}</div>
      </section>
    </template>
  </main>
</template>
