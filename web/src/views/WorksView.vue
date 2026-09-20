<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as runtime from "../runtime/runtime.js";
import { useI18nStore } from "../stores/i18n";
import { useShellStore } from "../stores/shell";
import AccessibleEmptyState from "../components/AccessibleEmptyState.vue";
import AppIcon from "../components/AppIcon.vue";
import type { WorksItem, WorksSnapshot } from "../types/works";
import { annotationsService } from "../services/annotations";

const i18n = useI18nStore();
const shell = useShellStore();
const snapshot = ref<WorksSnapshot | null>(null);
const loading = ref(true);
const error = ref("");
let queryTimer = 0;

const fileSignature = computed(() => shell.snapshot.files.map(file => `${file.id}:${file.count}:${file.dirty}`).join("|"));
const selected = computed(() => snapshot.value?.works.find(work => work.work === snapshot.value?.selectedWork) || null);
const activeStoreCount = computed(() => {
  const current = snapshot.value;
  if (!current?.activeStore) return 0;
  return current.stores.find(store => store.name === current.activeStore)?.count || 0;
});
const statusLabels: Record<string, [string, string]> = {
  synced: ["records.status.synced", "Synced"],
  changed: ["records.status.pending", "Pending changes"],
  exists: ["records.status.in_db", "In DB"],
  absent: ["records.status.not_in_db", "Not in DB"],
  unknown: ["records.status.unknown", "Status loading"],
  none: ["records.status.none", "No database"],
};

function statusLabel(kind: string, fallback: string) {
  const pair = statusLabels[kind];
  return pair ? i18n.t(pair[0], pair[1]) : fallback;
}
function fieldLabel(field: string) {
  return i18n.t(`field.${field}`, field.replaceAll("_", " ").replace(/\b\w/g, match => match.toUpperCase()));
}
function load() {
  const next = runtime.getWorksWorkspaceSnapshot?.() as WorksSnapshot | undefined;
  if (!next) return;
  snapshot.value = next;
  shell.sync();
}
function applyQuery(value: string) {
  runtime.setWorksSearch?.(value);
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

watch(fileSignature, load);
onMounted(() => {
  runtime.state.view = "works";
  load();
});
onBeforeUnmount(() => window.clearTimeout(queryTimer));
</script>

<template>
  <main class="works-page" aria-labelledby="works-page-title">
    <header class="page-heading works-page-heading">
      <div>
        <p>{{ i18n.t("section.corpus", "Corpus") }}</p>
        <h1 id="works-page-title">{{ i18n.t("nav.works", "Works") }}</h1>
        <span>{{ i18n.t("research.works_menu_help", "Browse works in the selected corpus database. Select a work for an overview, then browse its summarized records.") }}</span>
      </div>
    </header>

    <p v-if="error" class="info error" role="alert">{{ error }}</p>
    <div v-else-if="loading && !snapshot" class="page-loading" role="status" aria-live="polite">
      <AppIcon name="books" aria-hidden="true" />
      <span>{{ i18n.t("works.loading", "Loading works") }}</span>
    </div>
    <AccessibleEmptyState
      v-else-if="!snapshot?.available"
      icon="upload"
      :title="i18n.t('records.open_workspace', 'Open a corpus workspace')"
      :description="i18n.t('records.open_workspace_help', 'Drop one or more JSONL files anywhere on this page, or choose files manually.')"
      :action-label="i18n.t('records.choose_jsonl', 'Choose JSONL files')"
      @action="runtime.triggerImport?.()"
    />
    <template v-else-if="snapshot">
      <section class="card works-database-context" :aria-label="i18n.t('works.database_context', 'Works synchronization database')">
        <div>
          <span class="section-label">{{ i18n.t("works.database_context", "Works synchronization database") }}</span>
          <b>{{ snapshot.activeStore || i18n.t("research.none_selected", "No database selected") }}</b>
          <small>{{ i18n.t("works.database_context_help", "Sync status and Sync actions on this page refer to the selected corpus database. Changing it does not change your loaded JSONL files.") }}</small>
        </div>
        <label class="field">
          <span>{{ i18n.t("research.corpus_database", "Corpus database") }}</span>
          <select class="control" :value="snapshot.activeStore" :disabled="!snapshot.stores.length" @change="runtime.setWorksStore?.(($event.target as HTMLSelectElement).value); load()">
            <option v-if="!snapshot.stores.length" value="">{{ i18n.t("research.none_selected", "No database selected") }}</option>
            <option v-for="store in snapshot.stores" :key="store.name" :value="store.name">{{ store.name }} · {{ store.count.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records", "records") }}</option>
          </select>
          <small>{{ snapshot.activeStore ? `${activeStoreCount.toLocaleString(i18n.locale)} ${i18n.t("dynamic.records", "records")}` : snapshot.dbUnavailableReason }}</small>
        </label>
      </section>

      <section v-if="selected" class="card work-overview-card" aria-labelledby="selected-work-title">
        <div class="work-overview-cover">
          <img v-if="selected.cover" :src="selected.cover" :alt="i18n.tf('works.cover_alt', 'Cover of {work}', {work: selected.work})" loading="lazy">
          <div v-else class="work-cover-placeholder"><AppIcon name="books" aria-hidden="true" /></div>
        </div>
        <div class="work-overview-content">
          <div class="work-overview-heading">
            <div>
              <span class="section-label">{{ i18n.t("works.overview", "Work overview") }}</span>
              <h2 id="selected-work-title">{{ selected.work }}</h2>
              <p>{{ selected.count.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records", "records") }} · {{ selected.files.length.toLocaleString(i18n.locale) }} {{ i18n.t("works.source_files", "source files") }}</p>
            </div>
            <span class="db-status" :class="selected.status.kind"><i aria-hidden="true"></i>{{ statusLabel(selected.status.kind, selected.status.label) }}</span>
          </div>
          <div class="work-overview-metadata">
            <div v-for="item in selected.metadata" :key="item.field">
              <span>{{ fieldLabel(item.field) }}</span>
              <b>{{ item.mixed ? i18n.t("works.mixed_across_records", "Mixed across records") : item.value }}</b>
            </div>
          </div>
          <div v-if="selected.citation" class="work-overview-citation">
            <span>{{ fieldLabel("full_citation") }}</span>
            <p>{{ selected.citation }}</p>
          </div>
          <div class="work-overview-actions">
            <button type="button" class="btn primary" @click="searchWork(selected.work)"><AppIcon name="search" aria-hidden="true" />{{ i18n.t("works.search_records", "Search records") }}</button>
            <button type="button" class="btn" @click="editMetadata(selected.work)"><AppIcon name="edit" aria-hidden="true" />{{ i18n.t("works.edit_metadata", "Edit metadata") }}</button>
            <button type="button" class="btn soft" @click="populateMetadata(selected.work)"><AppIcon name="spark" aria-hidden="true" />{{ i18n.t("works.populate_metadata_llm", "Populate metadata with LLM") }}</button>
            <button v-if="selected.annotations" type="button" class="btn" @click="openAnnotations(selected.work)"><AppIcon name="record" aria-hidden="true" />{{ i18n.tf("works.view_annotations", "Annotations ({count})", {count: selected.annotations.toLocaleString(i18n.locale)}) }}</button>
          </div>
        </div>
      </section>

      <section class="toolbar works-toolbar aligned-toolbar" :aria-label="i18n.t('works.library_controls', 'Works library controls')">
        <label class="search">
          <span class="sr-only">{{ i18n.t("works.filter_title", "Filter works by title") }}</span>
          <input type="search" :value="snapshot.query" :placeholder="i18n.t('works.filter_title', 'Filter works by title')" @input="applyQuery(($event.target as HTMLInputElement).value)">
        </label>
        <div class="tools">
          <button type="button" class="btn small" :disabled="!snapshot.works.length" @click="runtime.openSeparateWorksModal?.()"><AppIcon name="filter" aria-hidden="true" />{{ i18n.t("works.separate_jsonl", "Separate works") }}</button>
          <button type="button" class="btn small primary" :disabled="!snapshot.capabilities.canSync || !snapshot.works.length" @click="syncAll"><AppIcon name="database" aria-hidden="true" />{{ i18n.t("works.sync_all", "Sync all works") }}</button>
          <span class="note">{{ snapshot.works.length.toLocaleString(i18n.locale) }} {{ i18n.t("works.shown", "shown") }} · {{ snapshot.totalWorks.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.works", "works") }} · {{ snapshot.totalRecords.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records", "records") }}</span>
        </div>
      </section>

      <section class="works works-library-grid" :aria-label="i18n.t('nav.works', 'Works')">
        <article v-for="work in snapshot.works" :key="work.work" class="card work work-library-card" :class="{selected: selected?.work === work.work}" :tabindex="0" :aria-label="i18n.tf('works.open_overview', 'Open overview for {work}', {work: work.work})" @click="selectWork(work.work)" @keydown="onCardKeydown(work.work, $event)">
          <div class="work-card-cover">
            <img v-if="work.cover" :src="work.cover" alt="" loading="lazy">
            <div v-else class="work-cover-placeholder"><AppIcon name="books" aria-hidden="true" /></div>
          </div>
          <div class="work-card-body">
            <div class="work-top">
              <div class="work-main-copy">
                <div class="work-title-line"><h2>{{ work.work }}</h2><span class="db-status" :class="work.status.kind"><i aria-hidden="true"></i>{{ statusLabel(work.status.kind, work.status.label) }}</span></div>
                <div class="note">{{ work.authors.join(", ") || i18n.t("works.unknown_author", "Unknown author") }}<span v-if="work.years.length"> · {{ work.years.join(", ") }}</span></div>
                <div class="work-card-biblio"><span v-if="work.files.length">{{ work.files.length }} {{ i18n.t("works.files", "files") }}</span><span v-if="work.review">{{ work.review }} {{ i18n.t("works.need_review", "need review") }}</span></div>
              </div>
              <div class="work-primary-actions">
                <button type="button" class="btn small" :disabled="!snapshot.capabilities.canSync" @click.stop="syncWork(work)"><AppIcon name="database" aria-hidden="true" />{{ i18n.t("works.sync", "Sync") }}</button>
              </div>
            </div>
            <div class="stats">
              <div class="stat"><strong>{{ work.count.toLocaleString(i18n.locale) }}</strong><span>{{ i18n.t("dynamic.records", "records") }}</span></div>
              <div class="stat"><strong>{{ work.review.toLocaleString(i18n.locale) }}</strong><span>{{ i18n.t("works.need_review", "need review") }}</span></div>
              <div class="stat"><strong>{{ work.files.length.toLocaleString(i18n.locale) }}</strong><span>{{ i18n.t("works.files", "files") }}</span></div>
            </div>
          </div>
        </article>
        <button type="button" class="work-add-jsonl-card" :disabled="!snapshot.capabilities.canManageCorpus" @click="runtime.triggerImport?.()"><span class="work-add-jsonl-icon"><AppIcon name="plus" aria-hidden="true" /></span><span><b>{{ i18n.t("works.add_jsonl", "Add a JSONL file") }}</b><small>{{ i18n.t("works.add_jsonl_help", "Open another corpus source and add its works to this workspace.") }}</small></span></button>
      </section>
    </template>
  </main>
</template>
