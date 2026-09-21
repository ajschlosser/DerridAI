<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import { useShellStore } from "../stores/shell";
import AppIcon from "../components/AppIcon.vue";
import AccessibleEmptyState from "../components/AccessibleEmptyState.vue";
import CitationMenu from "../components/CitationMenu.vue";
import HighlightedText from "../components/search/HighlightedText.vue";
import SearchSelectionBar from "../components/search/SearchSelectionBar.vue";
import RecordsWorkspaceHeader from "../components/records/RecordsWorkspaceHeader.vue";
import RecordsFileRail from "../components/records/RecordsFileRail.vue";
import RecordsColumnsDialog from "../components/records/RecordsColumnsDialog.vue";
import UiStatusBadge from "../components/ui/UiStatusBadge.vue";
import { useRecordsWorkspace } from "../composables/useRecordsWorkspace";
import type { RecordsCell, RecordsRow } from "../types/records";

const i18n = useI18nStore();
const shell = useShellStore();
const records = useRecordsWorkspace();
const { snapshot } = records;
const query = ref("");
const columnsDialog = ref<{ open: () => void; close: () => void } | null>(null);
const draftColumns = ref<string[]>([]);
const moreOpen = ref(false);
const liveMessage = ref("");
const density = ref(loadDensity());
let queryTimer = 0;

const fileSig = computed(() =>
  (snapshot.value?.files || shell.snapshot.files)
    .map(
      (file) =>
        `${file.id}:${file.active}:${file.count}:${file.dirty}:${"origin" in file ? file.origin : ""}`,
    )
    .join("|"),
);
const filterCount = computed(
  () =>
    Object.values(snapshot.value?.filters || {}).filter((value) => String(value || "").trim())
      .length,
);
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
  try {
    return localStorage.getItem("derridai.records.density.v1") === "compact"
      ? "compact"
      : "comfortable";
  } catch {
    return "comfortable";
  }
}
function persistDensity() {
  try {
    localStorage.setItem("derridai.records.density.v1", density.value);
  } catch {
    /* optional preference */
  }
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
function columnLabel(key: string, fallback: string) {
  const labels: Record<string, [string, string]> = {
    __db_status: ["records.column.database_status", "Database status"],
    record_id: ["records.column.record_id", "Record ID"],
    work: ["records.column.work", "Work"],
    text: ["records.column.text", "Text"],
    speaker: ["records.column.speaker", "Speaker"],
    needs_review: ["records.column.needs_review", "Needs review"],
    page_start: ["records.column.page_start", "Start page"],
    page_end: ["records.column.page_end", "End page"],
  };
  const label = labels[key];
  return label ? i18n.t(label[0], label[1]) : fallback;
}
function sortState(key: string) {
  if (snapshot.value?.sort.key !== key) return "none";
  return snapshot.value.sort.dir > 0 ? "ascending" : "descending";
}
function statusTone(kind: string): "neutral" | "info" | "success" | "warning" | "danger" {
  if (kind === "synced") return "success";
  if (kind === "changed") return "warning";
  if (kind === "exists") return "info";
  if (kind === "absent") return "danger";
  return "neutral";
}
function load() {
  records.load();
  if (snapshot.value) query.value = snapshot.value.query;
}
function applyQuery(value: string) {
  query.value = value;
  window.clearTimeout(queryTimer);
  queryTimer = window.setTimeout(() => {
    records.setQuery(value);
  }, 80);
}
async function run(name: string) {
  await records.run(name);
  shell.sync();
}
function selectFile(id: string) {
  records.selectFile(id);
  shell.sync();
}
async function closeFile(id: string) {
  await records.closeFile(id);
  shell.sync();
}
function share() {
  const href = records.shareHref();
  void navigator.clipboard.writeText(href).then(() => {
    liveMessage.value = i18n.t("records.link_copied", "Workspace link copied.");
  });
}
function openColumns() {
  draftColumns.value = snapshot.value?.columns.map((column) => column.key) || [];
  columnsDialog.value?.open();
}
function saveColumns() {
  records.setColumns(draftColumns.value);
}
function resetColumns() {
  records.resetColumns();
  draftColumns.value = snapshot.value?.columns.map((column) => column.key) || [];
}
function openRow(row: RecordsRow, event?: Event) {
  const target = event?.target as HTMLElement | undefined;
  if (target?.closest("button,input,a,select,label,[role='menu']")) return;
  records.openRecord(row);
}
function onRowKey(row: RecordsRow, event: KeyboardEvent) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    openRow(row);
  }
}
function toggleSelected(row: RecordsRow, selected: boolean) {
  records.setRowSelected(row, selected);
}
function togglePage(selected: boolean) {
  records.setPageSelected(selected);
}
function sortBy(key: string) {
  records.sort(key);
}
function filterBy(key: string, value: string) {
  records.setFilter(key, value);
}
function changeStore(name: string) {
  records.setStore(name);
}
function changePage(page: number) {
  records.setPage(page);
}
function changePageSize(size: number) {
  records.setPageSize(size);
}
function evidence(row: RecordsRow) {
  records.toggleEvidence(row);
}
function cite(row: RecordsRow, kind: "inline" | "full") {
  records.copyCitation(row, kind);
}
function searchMeta(cell: RecordsCell) {
  records.searchMetadata(cell);
}
function cellText(cell: RecordsCell) {
  if (cell.kind === "review")
    return cell.text === "yes" ? i18n.t("record.needs_review", "Needs review") : "—";
  if (cell.kind === "status") return statusLabel(cell.status_kind || "", cell.text);
  return cell.text;
}

watch(fileSig, load);
watch(density, persistDensity);
onMounted(() => {
  records.activate();
  if (snapshot.value) query.value = snapshot.value.query;
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
      v-if="!(snapshot?.files || []).length"
      icon="upload"
      :title="
        snapshot?.shared
          ? i18n.t('records.open_shared_workspace', 'Open the shared corpus workspace')
          : i18n.t('records.open_workspace', 'Open a corpus workspace')
      "
      :description="
        snapshot?.shared
          ? i18n.t(
              'records.shared_workspace_help',
              'This link preserves the table state and filters, while JSONL contents remain browser-local. Choose the same JSONL file to restore this shared view.',
            )
          : i18n.t(
              'records.open_workspace_help',
              'Drop one or more JSONL files anywhere on this page, or choose files manually. Each file stays in the local corpus list and can be edited, compared, searched, exported, or sent to the corpus database.',
            )
      "
      :action-label="i18n.t('records.choose_jsonl', 'Choose JSONL files')"
      @action="run('import')"
    />

    <div v-else-if="snapshot" class="records-layout">
      <RecordsFileRail
        :files="snapshot.files"
        :can-manage="snapshot.capabilities.can_import"
        @select="selectFile"
        @close="closeFile"
        @open="run('import')"
        @merge="run('merge')"
        @subset="run('subset')"
        @export="run('export')"
      />
      <div class="records-main">
        <template v-if="snapshot.available">
          <section
            class="records-command"
            :aria-label="i18n.t('records.table_controls', 'Records table controls')"
          >
            <label class="records-search">
              <span class="sr-only">{{
                i18n.t("records.search_in_file", "Search text in this file")
              }}</span>
              <AppIcon class="records-search-icon" name="search" />
              <input
                type="search"
                :value="query"
                :placeholder="i18n.t('records.search_in_file', 'Search text in this file')"
                autocomplete="off"
                @input="applyQuery(($event.target as HTMLInputElement).value)"
              />
            </label>
            <p class="records-count">{{ rangeLabel }}</p>
            <label class="records-store">
              <span>{{ i18n.t("search.corpus_database", "Corpus database") }}</span>
              <select
                class="control"
                :value="snapshot.active_store"
                :disabled="!snapshot.stores.length"
                :title="snapshot.stores.length ? '' : snapshot.db_unavailable_reason"
                @change="changeStore(($event.target as HTMLSelectElement).value)"
              >
                <option v-if="!snapshot.stores.length" value="">
                  {{
                    snapshot.db_unavailable_reason ||
                    i18n.t("records.no_collection", "No corpus collection")
                  }}
                </option>
                <option v-for="store in snapshot.stores" :key="store.name" :value="store.name">
                  {{ store.name }} ({{ store.count.toLocaleString(i18n.locale) }})
                </option>
              </select>
            </label>
            <p v-if="!snapshot.stores.length" class="records-database-state" role="status">
              <AppIcon name="database" aria-hidden="true" />
              <span>
                <strong>{{ i18n.t("records.no_collection", "No corpus collection") }}</strong>
                <small v-if="snapshot.db_unavailable_reason">{{
                  snapshot.db_unavailable_reason
                }}</small>
              </span>
            </p>
            <label class="records-page-size">
              <span class="sr-only">{{
                i18n.t("search.results_per_page", "Results per page")
              }}</span>
              <select
                class="control"
                :value="snapshot.page_size"
                @change="changePageSize(Number(($event.target as HTMLSelectElement).value))"
              >
                <option v-for="size in [25, 50, 100, 250]" :key="size" :value="size">
                  {{ size }}
                </option>
              </select>
            </label>
            <div
              class="records-density"
              role="group"
              :aria-label="i18n.t('records.density', 'Row density')"
            >
              <button
                type="button"
                class="btn tiny"
                :aria-pressed="density === 'comfortable'"
                @click="density = 'comfortable'"
              >
                {{ i18n.t("records.density_comfortable", "Comfortable") }}
              </button>
              <button
                type="button"
                class="btn tiny"
                :aria-pressed="density === 'compact'"
                @click="density = 'compact'"
              >
                {{ i18n.t("records.density_compact", "Compact") }}
              </button>
            </div>
            <details
              class="records-more"
              :open="moreOpen"
              @toggle="moreOpen = ($event.currentTarget as HTMLDetailsElement).open"
            >
              <summary class="btn">{{ i18n.t("records.more_actions", "More") }}</summary>
              <div
                class="records-more-menu"
                role="group"
                :aria-label="i18n.t('records.more_actions', 'More')"
              >
                <button
                  type="button"
                  class="btn"
                  :disabled="!snapshot.capabilities.can_upsert"
                  @click="run('upsertFile')"
                >
                  <AppIcon name="database" />{{ i18n.t("records.upsert_file", "Upsert file") }}
                </button>
                <button type="button" class="btn" @click="records.selectMatches()">
                  <AppIcon name="check" />{{
                    filterCount || query
                      ? i18n.t("records.select_matches", "Select matches")
                      : i18n.t("records.select_all", "Select all")
                  }}
                </button>
                <button
                  v-if="filterCount"
                  type="button"
                  class="btn"
                  @click="records.clearFilters()"
                >
                  {{ i18n.t("records.clear_column_filters", "Clear column filters") }}
                </button>
                <button
                  type="button"
                  class="btn"
                  :disabled="!snapshot.capabilities.can_review"
                  @click="run('ocr')"
                >
                  <AppIcon name="broom" />{{ i18n.t("ui.clean_ocr", "Clean OCR Artifacts") }}
                </button>
                <button
                  v-if="snapshot.flagged"
                  type="button"
                  class="btn soft"
                  @click="run('reviewFlagged')"
                >
                  {{
                    i18n.tf("records.review_flagged", "Review needs-review ({count})", {
                      count: snapshot.flagged.toLocaleString(i18n.locale),
                    })
                  }}
                </button>
                <button
                  v-if="snapshot.flagged"
                  type="button"
                  class="btn"
                  @click="run('improveFlagged')"
                >
                  {{ i18n.t("records.auto_improve_flagged", "Auto-improve needs-review") }}
                </button>
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
            @clear="records.clearSelection()"
          />
          <div
            v-if="snapshot.selection_count && snapshot.capabilities.can_upsert"
            class="records-upsert-selected"
          >
            <button type="button" class="btn" @click="run('upsertSelected')">
              <AppIcon name="database" />{{ i18n.t("records.upsert_selected", "Upsert selected") }}
            </button>
          </div>

          <div
            class="records-table-scroll ui-table-scroll"
            tabindex="0"
            role="region"
            :aria-label="
              i18n.t(
                'records.table_scroll_label',
                'Records table. Scroll horizontally to view additional columns.',
              )
            "
          >
            <table class="records-table ui-table" :class="density">
              <caption class="sr-only">
                {{
                  rangeLabel
                }}
              </caption>
              <thead>
                <tr>
                  <th
                    v-if="snapshot.capabilities.can_select"
                    class="select-col ui-table-sticky-start"
                    scope="col"
                  >
                    <input
                      type="checkbox"
                      :checked="snapshot.page_selected"
                      :aria-label="i18n.t('search.select_page', 'Select records on this page')"
                      @change="togglePage(($event.target as HTMLInputElement).checked)"
                    />
                  </th>
                  <th
                    v-for="column in snapshot.columns"
                    :key="column.key"
                    scope="col"
                    :aria-sort="column.key !== '__db_status' ? sortState(column.key) : undefined"
                    :class="{
                      'sticky-status': column.key === '__db_status',
                      'ui-table-sticky-start': column.key === '__db_status',
                      'text-col': column.key === 'text',
                    }"
                  >
                    <button
                      v-if="column.key !== '__db_status'"
                      type="button"
                      class="records-sort"
                      :aria-label="
                        i18n.tf('records.sort_column', 'Sort by {column}', {
                          column: columnLabel(column.key, column.label),
                        })
                      "
                      @click="sortBy(column.key)"
                    >
                      {{ columnLabel(column.key, column.label) }}
                      <span v-if="snapshot.sort.key === column.key" aria-hidden="true">{{
                        snapshot.sort.dir > 0 ? "↑" : "↓"
                      }}</span>
                    </button>
                    <span v-else>{{ columnLabel(column.key, column.label) }}</span>
                  </th>
                  <th class="actions-col" scope="col">
                    {{ i18n.t("research.record_actions", "Record actions") }}
                  </th>
                </tr>
                <tr class="filter-row">
                  <th
                    v-if="snapshot.capabilities.can_select"
                    class="select-col ui-table-sticky-start"
                  ></th>
                  <th
                    v-for="column in snapshot.columns"
                    :key="`filter-${column.key}`"
                    :class="{ 'sticky-status ui-table-sticky-start': column.key === '__db_status' }"
                  >
                    <label class="sr-only" :for="`records-filter-${column.key}`">{{
                      i18n.tf("records.filter_column", "Filter {column}", {
                        column: columnLabel(column.key, column.label),
                      })
                    }}</label>
                    <select
                      v-if="column.key === 'needs_review'"
                      :id="`records-filter-${column.key}`"
                      class="column-filter"
                      :value="snapshot.filters[column.key] || ''"
                      @change="filterBy(column.key, ($event.target as HTMLSelectElement).value)"
                    >
                      <option value="">{{ i18n.t("records.filter_all", "All") }}</option>
                      <option value="yes">
                        {{ i18n.t("record.needs_review", "Needs review") }}
                      </option>
                      <option value="no">
                        {{ i18n.t("records.filter_reviewed", "Reviewed") }}
                      </option>
                    </select>
                    <input
                      v-else
                      :id="`records-filter-${column.key}`"
                      class="column-filter"
                      :value="snapshot.filters[column.key] || ''"
                      :placeholder="i18n.t('records.filter_placeholder', 'Filter…')"
                      @input="filterBy(column.key, ($event.target as HTMLInputElement).value)"
                    />
                  </th>
                  <th class="actions-col ui-table-sticky-end"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!snapshot.rows.length">
                  <td
                    :colspan="snapshot.columns.length + (snapshot.capabilities.can_select ? 2 : 1)"
                  >
                    <AccessibleEmptyState
                      icon="search"
                      icon-tone="neutral"
                      :title="i18n.t('records.no_matches', 'No matching records')"
                      :description="
                        i18n.t(
                          'records.no_matches_help',
                          'Clear the text search or a column filter to see more of this file.',
                        )
                      "
                    />
                  </td>
                </tr>
                <tr
                  v-for="row in snapshot.rows"
                  :key="row.key"
                  :class="{ selected: row.selected }"
                  tabindex="0"
                  :aria-label="
                    i18n.tf('records.open_named', 'Open {record}', { record: row.record_id })
                  "
                  @click="openRow(row, $event)"
                  @keydown="onRowKey(row, $event)"
                >
                  <td v-if="snapshot.capabilities.can_select" class="select-col" @click.stop>
                    <input
                      type="checkbox"
                      :checked="row.selected"
                      :aria-label="
                        i18n.tf('search.select_record_named', 'Select {record}', {
                          record: row.record_id,
                        })
                      "
                      @change="toggleSelected(row, ($event.target as HTMLInputElement).checked)"
                    />
                  </td>
                  <td
                    v-for="cell in row.cells"
                    :key="cell.key"
                    :class="{
                      'text-col': cell.kind === 'text',
                      'sticky-status': cell.kind === 'status',
                    }"
                  >
                    <UiStatusBadge
                      v-if="cell.kind === 'status'"
                      class="db-status"
                      :label="cellText(cell)"
                      :tone="statusTone(cell.status_kind || '')"
                      :help="cell.title"
                    />
                    <span
                      v-else-if="cell.kind === 'review'"
                      :class="{ review: cell.text === 'yes' }"
                      >{{ cellText(cell) }}</span
                    >
                    <HighlightedText
                      v-else-if="cell.kind === 'text'"
                      :text="cell.text"
                      :query="query"
                    />
                    <button
                      v-else-if="cell.kind === 'metadata'"
                      type="button"
                      class="table-metadata-link"
                      @click.stop="searchMeta(cell)"
                    >
                      {{ cell.text }}
                    </button>
                    <span v-else>{{ cell.text }}</span>
                  </td>
                  <td class="actions-col ui-table-sticky-end" @click.stop>
                    <div class="records-row-actions">
                      <CitationMenu
                        compact
                        @inline="cite(row, 'inline')"
                        @full="cite(row, 'full')"
                      />
                      <button
                        v-if="snapshot.capabilities.can_select_evidence"
                        type="button"
                        class="btn tiny"
                        :class="{ soft: row.evidence_selected }"
                        :aria-pressed="row.evidence_selected"
                        @click="evidence(row)"
                      >
                        <AppIcon :name="row.evidence_selected ? 'check' : 'plus'" />
                        {{
                          row.evidence_selected
                            ? i18n.t("ui.selected", "Selected")
                            : i18n.t("ui.add_evidence", "Add evidence")
                        }}
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <nav
            class="records-pagination"
            :aria-label="i18n.t('records.pagination', 'Records pages')"
          >
            <button type="button" class="btn" :disabled="snapshot.page <= 1" @click="changePage(1)">
              {{ i18n.t("records.first_page", "First") }}
            </button>
            <button
              type="button"
              class="btn"
              :disabled="snapshot.page <= 1"
              @click="changePage(snapshot.page - 1)"
            >
              {{ i18n.t("common.previous", "Previous") }}
            </button>
            <span class="records-page-status" aria-live="polite">{{
              i18n.tf("search.page_of", "Page {page} of {pages}", {
                page: snapshot.page,
                pages: snapshot.pages,
              })
            }}</span>
            <button
              type="button"
              class="btn"
              :disabled="snapshot.page >= snapshot.pages"
              @click="changePage(snapshot.page + 1)"
            >
              {{ i18n.t("common.next", "Next") }}
            </button>
            <button
              type="button"
              class="btn"
              :disabled="snapshot.page >= snapshot.pages"
              @click="changePage(snapshot.pages)"
            >
              {{ i18n.t("records.last_page", "Last") }}
            </button>
          </nav>
        </template>
      </div>
    </div>

    <RecordsColumnsDialog
      ref="columnsDialog"
      :available="snapshot?.available_columns || []"
      v-model="draftColumns"
      @apply="saveColumns"
      @reset="resetColumns"
    />
  </main>
</template>
<style scoped>
.records-page {
  display: grid;
  gap: 16px;
  max-width: 1600px;
  margin: 0 auto;
}
.records-layout {
  display: grid;
  grid-template-columns: minmax(15rem, 18rem) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.records-main {
  display: grid;
  gap: 16px;
  min-width: 0;
}
.records-command {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: end;
}
.records-search {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1 1 16rem;
  min-height: 2.75rem;
  padding: 0 12px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-control);
  background: var(--surface-card);
}
.records-search-icon {
  width: 1.125rem;
  height: 1.125rem;
  flex: 0 0 1.125rem;
  display: block;
}
.records-command :deep(.btn svg) {
  width: 1rem;
  height: 1rem;
  flex: 0 0 1rem;
}
.records-search input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  font-size: 0.875rem;
}
.records-count {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--text-tertiary);
}
.records-database-state {
  display: inline-flex;
  align-items: flex-start;
  gap: 8px;
  max-width: 24rem;
  margin: 0;
  padding: 8px 10px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: var(--radius-control);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: var(--fs-sm);
}
.records-database-state > span {
  display: grid;
  gap: 2px;
}
.records-database-state small {
  color: inherit;
  font-size: var(--fs-xs);
  line-height: var(--lh-normal);
}
.records-store,
.records-page-size {
  display: grid;
  gap: 4px;
  font-size: 0.8125rem;
  font-weight: 700;
}
.records-density {
  display: flex;
  gap: 4px;
}
.records-more {
  position: relative;
}
.records-more-menu {
  position: absolute;
  right: 0;
  z-index: 6;
  display: grid;
  gap: 6px;
  min-width: 16rem;
  padding: 10px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-overlay);
  background: var(--surface-overlay);
  box-shadow: var(--shadow-overlay);
}
.records-upsert-selected {
  display: flex;
  justify-content: flex-end;
}
.records-table-scroll {
  overflow: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-overlay);
  background: var(--surface-card);
}
.records-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.8125rem;
}
.records-table th,
.records-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: top;
  text-align: left;
}
.records-table.compact th,
.records-table.compact td {
  padding: 6px 10px;
}
.records-table tbody tr {
  cursor: pointer;
}
.records-table tbody tr:hover,
.records-table tbody tr:focus-visible {
  background: var(--surface-hover);
}
.records-table tbody tr:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: -2px;
}
.records-table tbody tr.selected {
  background: var(--surface-selected);
}
.records-sort {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: var(--control-height-small);
  background: none;
  border: 0;
  border-radius: var(--radius-control);
  padding: 4px 6px;
  font: inherit;
  color: inherit;
  cursor: pointer;
}
.records-sort:hover {
  background: var(--surface-hover);
}
.records-sort:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.text-col {
  min-width: 18rem;
  max-width: 36rem;
}
.actions-col {
  min-width: 14rem;
  position: sticky;
  right: 0;
  background: var(--surface-card);
  box-shadow: -8px 0 12px color-mix(in srgb, var(--text-primary) 7%, transparent);
}
.select-col,
.sticky-status {
  position: sticky;
  left: 0;
  background: var(--surface-card);
  z-index: 1;
}
.sticky-status {
  left: 2.5rem;
}
.records-row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.records-pagination {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
  font-size: 0.8125rem;
}
.column-filter {
  width: 100%;
  min-height: var(--control-height-small);
  font-size: 0.8125rem;
}
.records-table tbody tr:hover .select-col,
.records-table tbody tr:hover .sticky-status,
.records-table tbody tr:hover .actions-col,
.records-table tbody tr:focus-visible .select-col,
.records-table tbody tr:focus-visible .sticky-status,
.records-table tbody tr:focus-visible .actions-col {
  background: var(--surface-hover);
}
.records-table tbody tr.selected .select-col,
.records-table tbody tr.selected .sticky-status,
.records-table tbody tr.selected .actions-col {
  background: var(--surface-selected);
}
.records-page-status {
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}
@media (max-width: 900px) {
  .records-layout {
    grid-template-columns: 1fr;
  }
}
</style>
