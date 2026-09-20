<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import * as runtime from "../runtime/runtime.js";
import { useI18nStore } from "../stores/i18n";
import { useShellStore } from "../stores/shell";
import AppIcon from "../components/AppIcon.vue";
import AccessibleEmptyState from "../components/AccessibleEmptyState.vue";
import CitationMenu from "../components/CitationMenu.vue";
import HighlightedText from "../components/search/HighlightedText.vue";
import SearchSelectionBar from "../components/search/SearchSelectionBar.vue";
import RecordsWorkspaceHeader from "../components/records/RecordsWorkspaceHeader.vue";
import type { RecordsCell, RecordsListSnapshot, RecordsRow } from "../types/records";

const i18n = useI18nStore();
const shell = useShellStore();
const snapshot = ref<RecordsListSnapshot | null>(null);
const query = ref("");
const columnsDialog = ref<HTMLDialogElement | null>(null);
const draftColumns = ref<string[]>([]);
const moreOpen = ref(false);
const liveMessage = ref("");
const density = ref(loadDensity());
let queryTimer = 0;

const fileSig = computed(() => shell.snapshot.files.map(file => `${file.id}:${file.active}:${file.count}:${file.dirty}`).join("|"));
const filterCount = computed(() => Object.values(snapshot.value?.filters || {}).filter(value => String(value || "").trim()).length);
const rangeLabel = computed(() => {
  const snap = snapshot.value;
  if (!snap?.matched) return i18n.t("records.no_matches", "No matching records");
  return i18n.tf("records.range", "{start}–{end} of {matched}", {
    start: (snap.start + 1).toLocaleString(i18n.locale),
    end: snap.end.toLocaleString(i18n.locale),
    matched: snap.matched.toLocaleString(i18n.locale),
  });
});

function loadDensity() {
  try { return localStorage.getItem("derridai.records.density.v1") === "compact" ? "compact" : "comfortable"; }
  catch { return "comfortable"; }
}
function persistDensity() {
  try { localStorage.setItem("derridai.records.density.v1", density.value); }
  catch { /* optional preference */ }
}
function statusLabel(kind: string, fallback: string) {
  const keys: Record<string, [string, string]> = {
    synced: ["records.status.synced", "Synced"],
    changed: ["records.status.pending", "Pending"],
    exists: ["records.status.in_db", "In DB"],
    absent: ["records.status.not_in_db", "Not in DB"],
    unknown: ["records.status.unknown", "Unknown"],
    none: ["records.status.none", "No database"],
  };
  const pair = keys[kind];
  return pair ? i18n.t(pair[0], pair[1]) : fallback;
}
function load() {
  const next = runtime.getRecordsListSnapshot?.() as RecordsListSnapshot | undefined;
  if (!next) return;
  snapshot.value = next;
  query.value = next.query;
}
function applyQuery(value: string) {
  query.value = value;
  window.clearTimeout(queryTimer);
  queryTimer = window.setTimeout(() => {
    runtime.setRecordsListQuery?.(value);
    load();
  }, 80);
}
async function run(name: string) {
  await runtime.recordsListCommand?.(name);
  load();
  shell.sync();
}
function share() {
  const href = runtime.getRecordsListShareHref?.() || location.href;
  void navigator.clipboard.writeText(href).then(() => {
    liveMessage.value = i18n.t("records.link_copied", "Workspace link copied.");
  });
}
function openColumns() {
  draftColumns.value = snapshot.value?.columns.map(column => column.key) || [];
  columnsDialog.value?.showModal();
}
function saveColumns() {
  runtime.setRecordsListColumns?.(draftColumns.value);
  columnsDialog.value?.close();
  load();
}
function addColumn(key: string) {
  if (key && !draftColumns.value.includes(key)) draftColumns.value = [...draftColumns.value, key];
}
function openRow(row: RecordsRow, event?: Event) {
  const target = event?.target as HTMLElement | undefined;
  if (target?.closest("button,input,a,select,label,[role='menu']")) return;
  runtime.openRecordsListRecord?.(row.index);
}
function onRowKey(row: RecordsRow, event: KeyboardEvent) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    openRow(row);
  }
}
function toggleSelected(row: RecordsRow, selected: boolean) {
  runtime.setRecordsListRowSelected?.(row.index, selected);
  load();
}
function togglePage(selected: boolean) {
  runtime.setRecordsListPageSelected?.(selected);
  load();
}
function sortBy(key: string) {
  runtime.setRecordsListSort?.(key);
  load();
}
function filterBy(key: string, value: string) {
  runtime.setRecordsListFilter?.(key, value);
  load();
}
function changeStore(name: string) {
  runtime.setRecordsListStore?.(name);
  load();
}
function changePage(page: number) {
  runtime.setRecordsListPage?.(page);
  load();
}
function changePageSize(size: number) {
  runtime.setRecordsListPageSize?.(size);
  load();
}
function evidence(row: RecordsRow) {
  runtime.toggleRecordsListEvidence?.(row.index);
  load();
}
function cite(row: RecordsRow, kind: "inline" | "full") {
  runtime.copyRecordsListCitation?.(row.index, kind);
}
function searchMeta(cell: RecordsCell) {
  runtime.recordsListMetadataSearch?.(cell.key, cell.meta_value, cell.meta_contains);
}
function cellText(cell: RecordsCell) {
  if (cell.kind === "review") return cell.text === "yes" ? i18n.t("record.needs_review", "Needs review") : "—";
  if (cell.kind === "status") return statusLabel(cell.status_kind || "", cell.text);
  return cell.text;
}

watch(fileSig, load);
watch(density, persistDensity);
onMounted(() => {
  runtime.state.view = "list";
  load();
});
</script>
<template>
  <main class="records-page" aria-labelledby="records-page-title">
    <p class="sr-only" aria-live="polite">{{ liveMessage }}</p>
    <RecordsWorkspaceHeader
      :file-name="snapshot?.file?.name || ''"
      :matched="snapshot?.matched || 0"
      :total="snapshot?.total || 0"
      :flagged="snapshot?.flagged || 0"
      :selected="snapshot?.selection_count || 0"
      @share="share"
      @columns="openColumns"
      @import="run('import')"
    />

    <AccessibleEmptyState
      v-if="!snapshot?.available"
      icon="upload"
      :title="snapshot?.shared ? i18n.t('records.open_shared_workspace', 'Open the shared corpus workspace') : i18n.t('records.open_workspace', 'Open a corpus workspace')"
      :description="snapshot?.shared ? i18n.t('records.shared_workspace_help', 'This link preserves the table state and filters, while JSONL contents remain browser-local. Choose the same JSONL file to restore this shared view.') : i18n.t('records.open_workspace_help', 'Drop one or more JSONL files anywhere on this page, or choose files manually. Each file stays in its own tab and can be edited, compared, searched, exported, or sent to the corpus database.')"
      :action-label="i18n.t('records.choose_jsonl', 'Choose JSONL files')"
      @action="run('import')"
    />

    <template v-else-if="snapshot">
      <section class="records-command" :aria-label="i18n.t('records.table_controls', 'Records table controls')">
        <label class="records-search">
          <span class="sr-only">{{ i18n.t("records.search_in_file", "Search text in this file") }}</span>
          <AppIcon name="search"/>
          <input type="search" :value="query" :placeholder="i18n.t('records.search_in_file', 'Search text in this file')" autocomplete="off" @input="applyQuery(($event.target as HTMLInputElement).value)">
        </label>
        <p class="records-count">{{ rangeLabel }}</p>
        <label class="records-store">
          <span>{{ i18n.t("search.corpus_database", "Corpus database") }}</span>
          <select class="control" :value="snapshot.active_store" :disabled="!snapshot.stores.length" :title="snapshot.stores.length ? '' : snapshot.db_unavailable_reason" @change="changeStore(($event.target as HTMLSelectElement).value)">
            <option v-if="!snapshot.stores.length" value="">{{ snapshot.db_unavailable_reason || i18n.t("records.no_collection", "No corpus collection") }}</option>
            <option v-for="store in snapshot.stores" :key="store.name" :value="store.name">{{ store.name }} ({{ store.count.toLocaleString(i18n.locale) }})</option>
          </select>
        </label>
        <label class="records-page-size">
          <span class="sr-only">{{ i18n.t("search.results_per_page", "Results per page") }}</span>
          <select class="control" :value="snapshot.page_size" @change="changePageSize(Number(($event.target as HTMLSelectElement).value))">
            <option v-for="size in [25, 50, 100, 250]" :key="size" :value="size">{{ size }}</option>
          </select>
        </label>
        <div class="records-density" role="group" :aria-label="i18n.t('records.density', 'Row density')">
          <button type="button" class="btn tiny" :aria-pressed="density === 'comfortable'" @click="density = 'comfortable'">{{ i18n.t("records.density_comfortable", "Comfortable") }}</button>
          <button type="button" class="btn tiny" :aria-pressed="density === 'compact'" @click="density = 'compact'">{{ i18n.t("records.density_compact", "Compact") }}</button>
        </div>
        <details class="records-more" :open="moreOpen" @toggle="moreOpen = ($event.currentTarget as HTMLDetailsElement).open">
          <summary class="btn">{{ i18n.t("records.more_actions", "More") }}</summary>
          <div class="records-more-menu" role="group" :aria-label="i18n.t('records.more_actions', 'More')">
            <button type="button" class="btn" :disabled="!snapshot.capabilities.can_upsert" @click="run('upsertFile')"><AppIcon name="database"/>{{ i18n.t("records.upsert_file", "Upsert file") }}</button>
            <button type="button" class="btn" @click="runtime.selectRecordsListMatches?.(); load()"><AppIcon name="check"/>{{ filterCount || query ? i18n.t("records.select_matches", "Select matches") : i18n.t("records.select_all", "Select all") }}</button>
            <button v-if="filterCount" type="button" class="btn" @click="runtime.clearRecordsListFilters?.(); load()">{{ i18n.t("records.clear_column_filters", "Clear column filters") }}</button>
            <button type="button" class="btn" :disabled="!snapshot.capabilities.can_review" @click="run('ocr')"><AppIcon name="broom"/>{{ i18n.t("ui.clean_ocr", "Clean OCR Artifacts") }}</button>
            <button v-if="snapshot.flagged" type="button" class="btn soft" @click="run('reviewFlagged')">{{ i18n.tf("records.review_flagged", "Review needs-review ({count})", {count: snapshot.flagged.toLocaleString(i18n.locale)}) }}</button>
            <button v-if="snapshot.flagged" type="button" class="btn" @click="run('improveFlagged')">{{ i18n.t("records.auto_improve_flagged", "Auto-improve needs-review") }}</button>
          </div>
        </details>
      </section>

      <SearchSelectionBar
        v-if="snapshot.selection_count"
        :count="snapshot.selection_count"
        :can-review="snapshot.capabilities.can_review"
        :can-bulk-edit="snapshot.capabilities.can_bulk_edit"
        @review="run('reviewSelected')"
        @improve="run('improveSelected')"
        @bulk="run('bulkSelected')"
        @clear="runtime.clearRecordsListSelection?.(); load()"
      />
      <div v-if="snapshot.selection_count && snapshot.capabilities.can_upsert" class="records-upsert-selected">
        <button type="button" class="btn" @click="run('upsertSelected')"><AppIcon name="database"/>{{ i18n.t("records.upsert_selected", "Upsert selected") }}</button>
      </div>

      <div class="records-table-scroll" tabindex="0" :aria-label="i18n.t('records.table_scroll_label', 'Records table. Scroll horizontally to view additional columns.')">
        <table class="records-table" :class="density">
          <caption class="sr-only">{{ rangeLabel }}</caption>
          <thead>
            <tr>
              <th v-if="snapshot.capabilities.can_select" class="select-col">
                <input type="checkbox" :checked="snapshot.page_selected" :aria-label="i18n.t('search.select_page', 'Select records on this page')" @change="togglePage(($event.target as HTMLInputElement).checked)">
              </th>
              <th v-for="column in snapshot.columns" :key="column.key" :class="{'sticky-status': column.key === '__db_status', 'text-col': column.key === 'text'}">
                <button v-if="column.key !== '__db_status'" type="button" class="records-sort" @click="sortBy(column.key)">
                  {{ column.label }}
                  <span v-if="snapshot.sort.key === column.key" aria-hidden="true">{{ snapshot.sort.dir > 0 ? "↑" : "↓" }}</span>
                </button>
                <span v-else>{{ column.label }}</span>
              </th>
              <th class="actions-col">{{ i18n.t("research.record_actions", "Record actions") }}</th>
            </tr>
            <tr class="filter-row">
              <th v-if="snapshot.capabilities.can_select"></th>
              <th v-for="column in snapshot.columns" :key="`filter-${column.key}`">
                <label class="sr-only" :for="`records-filter-${column.key}`">{{ i18n.tf("records.filter_column", "Filter {column}", {column: column.label}) }}</label>
                <select v-if="column.key === 'needs_review'" :id="`records-filter-${column.key}`" class="column-filter" :value="snapshot.filters[column.key] || ''" @change="filterBy(column.key, ($event.target as HTMLSelectElement).value)">
                  <option value="">{{ i18n.t("records.filter_all", "All") }}</option>
                  <option value="yes">{{ i18n.t("record.needs_review", "Needs review") }}</option>
                  <option value="no">{{ i18n.t("records.filter_reviewed", "Reviewed") }}</option>
                </select>
                <input v-else :id="`records-filter-${column.key}`" class="column-filter" :value="snapshot.filters[column.key] || ''" :placeholder="i18n.t('records.filter_placeholder', 'Filter…')" @input="filterBy(column.key, ($event.target as HTMLInputElement).value)">
              </th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!snapshot.rows.length">
              <td :colspan="snapshot.columns.length + (snapshot.capabilities.can_select ? 2 : 1)">
                <AccessibleEmptyState icon="search" icon-tone="neutral" :title="i18n.t('records.no_matches', 'No matching records')" :description="i18n.t('records.no_matches_help', 'Clear the text search or a column filter to see more of this file.')"/>
              </td>
            </tr>
            <tr
              v-for="row in snapshot.rows"
              :key="row.key"
              :class="{selected: row.selected}"
              tabindex="0"
              :aria-label="i18n.tf('records.open_named', 'Open {record}', {record: row.record_id})"
              @click="openRow(row, $event)"
              @keydown="onRowKey(row, $event)"
            >
              <td v-if="snapshot.capabilities.can_select" class="select-col" @click.stop>
                <input type="checkbox" :checked="row.selected" :aria-label="i18n.tf('search.select_record_named', 'Select {record}', {record: row.record_id})" @change="toggleSelected(row, ($event.target as HTMLInputElement).checked)">
              </td>
              <td v-for="cell in row.cells" :key="cell.key" :class="{'text-col': cell.kind === 'text', 'sticky-status': cell.kind === 'status'}">
                <span v-if="cell.kind === 'status'" :class="['db-status', cell.status_kind]" :title="cell.title">{{ cellText(cell) }}</span>
                <span v-else-if="cell.kind === 'review'" :class="{review: cell.text === 'yes'}">{{ cellText(cell) }}</span>
                <HighlightedText v-else-if="cell.kind === 'text'" :text="cell.text" :query="query"/>
                <button v-else-if="cell.kind === 'metadata'" type="button" class="table-metadata-link" @click.stop="searchMeta(cell)">{{ cell.text }}</button>
                <span v-else>{{ cell.text }}</span>
              </td>
              <td class="actions-col" @click.stop>
                <div class="records-row-actions">
                  <CitationMenu compact @inline="cite(row, 'inline')" @full="cite(row, 'full')"/>
                  <button
                    v-if="snapshot.capabilities.can_select_evidence"
                    type="button"
                    class="btn tiny"
                    :class="{soft: row.evidence_selected}"
                    :aria-pressed="row.evidence_selected"
                    @click="evidence(row)"
                  >
                    <AppIcon :name="row.evidence_selected ? 'check' : 'plus'"/>
                    {{ row.evidence_selected ? i18n.t("ui.selected", "Selected") : i18n.t("ui.add_evidence", "Add evidence") }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <nav class="records-pagination" :aria-label="i18n.t('records.pagination', 'Records pages')">
        <button type="button" class="btn" :disabled="snapshot.page <= 1" @click="changePage(1)">{{ i18n.t("records.first_page", "First") }}</button>
        <button type="button" class="btn" :disabled="snapshot.page <= 1" @click="changePage(snapshot.page - 1)">{{ i18n.t("common.previous", "Previous") }}</button>
        <span>{{ i18n.tf("search.page_of", "Page {page} of {pages}", {page: snapshot.page, pages: snapshot.pages}) }}</span>
        <button type="button" class="btn" :disabled="snapshot.page >= snapshot.pages" @click="changePage(snapshot.page + 1)">{{ i18n.t("common.next", "Next") }}</button>
        <button type="button" class="btn" :disabled="snapshot.page >= snapshot.pages" @click="changePage(snapshot.pages)">{{ i18n.t("records.last_page", "Last") }}</button>
      </nav>
    </template>

    <dialog ref="columnsDialog" class="records-columns-dialog" aria-labelledby="records-columns-title">
      <form method="dialog" class="records-columns-form" @submit.prevent="saveColumns">
        <h2 id="records-columns-title">{{ i18n.t("records.configure_columns", "Configure columns") }}</h2>
        <p>{{ i18n.t("records.configure_columns_help", "Choose the fields shown in the records table. Order is preserved.") }}</p>
        <ul>
          <li v-for="(key, index) in draftColumns" :key="key">
            <span>{{ snapshot?.available_columns.find(column => column.key === key)?.label || key }}</span>
            <button type="button" class="btn tiny" :disabled="index === 0" @click="draftColumns.splice(index - 1, 0, draftColumns.splice(index, 1)[0])">↑</button>
            <button type="button" class="btn tiny" :disabled="index === draftColumns.length - 1" @click="draftColumns.splice(index + 1, 0, draftColumns.splice(index, 1)[0])">↓</button>
            <button type="button" class="btn tiny" @click="draftColumns.splice(index, 1)">{{ i18n.t("ui.remove", "Remove") }}</button>
          </li>
        </ul>
        <label>
          <span>{{ i18n.t("records.add_column", "Add column") }}</span>
          <select class="control" @change="addColumn(($event.target as HTMLSelectElement).value); ($event.target as HTMLSelectElement).value = ''">
            <option value="">{{ i18n.t("records.choose_column", "Choose a field") }}</option>
            <option v-for="column in snapshot?.available_columns.filter(item => !draftColumns.includes(item.key))" :key="column.key" :value="column.key">{{ column.label }}</option>
          </select>
        </label>
        <div class="records-columns-actions">
          <button type="button" class="btn" @click="runtime.resetRecordsListColumns?.(); draftColumns = ((runtime.getRecordsListSnapshot?.() as RecordsListSnapshot | undefined)?.columns.map(column => column.key) || [])">{{ i18n.t("records.reset_columns", "Reset defaults") }}</button>
          <button type="button" class="btn" @click="columnsDialog?.close()">{{ i18n.t("common.cancel", "Cancel") }}</button>
          <button type="submit" class="btn primary">{{ i18n.t("records.save_columns", "Save columns") }}</button>
        </div>
      </form>
    </dialog>
  </main>
</template>
<style scoped>
.records-page{display:grid;gap:16px;max-width:1600px;margin:0 auto}
.records-command{display:flex;flex-wrap:wrap;gap:10px;align-items:end}
.records-search{display:flex;align-items:center;gap:8px;flex:1 1 16rem;min-height:2.75rem;padding:0 12px;border:1px solid var(--line);border-radius:12px;background:var(--panel,#fff)}
.records-search input{flex:1;min-width:0;border:0;background:transparent;font-size:.875rem}
.records-count{margin:0;font-size:.8125rem;color:var(--muted)}
.records-store,.records-page-size{display:grid;gap:4px;font-size:.8125rem;font-weight:700}
.records-density{display:flex;gap:4px}
.records-more{position:relative}
.records-more-menu{position:absolute;right:0;z-index:6;display:grid;gap:6px;min-width:16rem;padding:10px;border:1px solid var(--line);border-radius:12px;background:var(--overlay,var(--panel,#fff));box-shadow:0 16px 40px rgba(20,30,24,.16)}
.records-upsert-selected{display:flex;justify-content:flex-end}
.records-table-scroll{overflow:auto;border:1px solid var(--line);border-radius:16px;background:var(--panel,#fff)}
.records-table{width:100%;border-collapse:separate;border-spacing:0;font-size:.8125rem}
.records-table th,.records-table td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}
.records-table.compact th,.records-table.compact td{padding:6px 10px}
.records-table tbody tr{cursor:pointer}
.records-table tbody tr:hover,.records-table tbody tr:focus-visible{background:var(--accent-soft,#eef6f1);outline:none}
.records-table tbody tr.selected{background:#f3f8f5}
.records-sort{background:none;border:0;padding:0;font:inherit;color:inherit;cursor:pointer}
.text-col{min-width:18rem;max-width:36rem}
.actions-col{min-width:14rem;position:sticky;right:0;background:inherit;box-shadow:-8px 0 12px rgba(20,30,24,.04)}
.select-col,.sticky-status{position:sticky;left:0;background:inherit;z-index:1}
.sticky-status{left:2.5rem}
.records-row-actions{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.records-pagination{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:flex-end;font-size:.8125rem}
.records-columns-dialog{border:1px solid var(--line);border-radius:16px;padding:0;max-width:32rem;width:calc(100% - 2rem)}
.records-columns-form{display:grid;gap:12px;padding:18px}
.records-columns-form ul{margin:0;padding:0;list-style:none;display:grid;gap:8px}
.records-columns-form li{display:flex;flex-wrap:wrap;gap:6px;align-items:center;justify-content:space-between}
.records-columns-actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}
.column-filter{width:100%;min-height:2rem;font-size:.8125rem}
</style>
