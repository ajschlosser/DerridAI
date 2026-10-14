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
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  corpusSourcesApi,
  type SourceFacetName,
  type SourceListQuery,
  type SourceListResponse,
  type SourceRow,
  type SourceSort,
} from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import { languageList, languageName, sortLanguageCodes } from "../../domain/languages";
import { editionLine, enumLabel, enumTone, type LabelKind } from "../../domain/sourceLabels";
import AppIcon from "../AppIcon.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";
import UiTooltip from "../ui/UiTooltip.vue";
import UiTableColumnsDialog from "../ui/UiTableColumnsDialog.vue";

/**
 * Server-paginated, server-sorted table of registered sources. Rows are compact (identity, language,
 * provenance and status; never text). Used full-width on the Sources page and, with `compact`, as the
 * Corpus Builder source selector, where one row at a time becomes the build's source.
 */
type ColumnKey =
  | "source"
  | "provider"
  | "language"
  | "original_language"
  | "edition"
  | "role"
  | "acquisition"
  | "build"
  | "added"
  | "actions";
type FilterKey = Exclude<SourceFacetName, "media_kind">;

const props = withDefaults(
  defineProps<{
    /** Corpus Builder embed: fewer columns, single-source choice, no bulk selection. */
    compact?: boolean;
    /** Checked rows (bulk actions) in the full table. */
    selected?: string[];
    /** The row chosen as the build's source in the compact table. */
    activeId?: string;
    /** Source ids handed over from the Sources page; shown as a highlighted filter. */
    queuedIds?: string[];
    /** Capture id → display name for the capture filter. */
    captureLabels?: Record<string, string>;
    /** Pre-applied filters (for example a capture chosen on the Sources page). */
    initialFilters?: Partial<Record<FilterKey, string>>;
    pageSize?: number;
    disabled?: boolean;
    /** Why rows cannot be chosen right now (shown once, as status text). */
    lockedReason?: string;
    /** Changing this value reloads the current page. */
    refreshKey?: string | number;
    /** Offer a delete action per row (compact table). */
    deletable?: boolean;
  }>(),
  {
    compact: false,
    selected: () => [],
    activeId: "",
    queuedIds: () => [],
    captureLabels: () => ({}),
    initialFilters: () => ({}),
    pageSize: 25,
    disabled: false,
    lockedReason: "",
    refreshKey: 0,
    deletable: false,
  },
);
const emit = defineEmits<{
  "update:selected": [ids: string[]];
  choose: [id: string];
  inspect: [id: string];
  delete: [id: string];
  loaded: [response: SourceListResponse];
  /** Rows currently represented by the active query identity. */
  displayed: [rows: SourceRow[]];
}>();
const i18n = useI18nStore();
const t = (key: string, fallback?: string) => i18n.t(key, fallback);

const ALL_COLUMNS: ColumnKey[] = [
  "source",
  "provider",
  "language",
  "original_language",
  "edition",
  "role",
  "acquisition",
  "build",
  "added",
  "actions",
];
const COMPACT_COLUMNS: ColumnKey[] = ["source", "language", "provider", "build", "actions"];
const SORTABLE: Partial<Record<ColumnKey, SourceSort>> = {
  source: "title",
  provider: "provider",
  language: "language",
  added: "added",
};
const COLUMN_STORAGE = "derridai.sources.columns.v1";
const FILTERS: FilterKey[] = [
  "provider",
  "document_language",
  "original_language",
  "capture_id",
  "build_status",
  "relationship",
  "role",
];

function storedColumns(): ColumnKey[] {
  try {
    const saved = JSON.parse(localStorage.getItem(COLUMN_STORAGE) || "null");
    if (Array.isArray(saved)) {
      const valid = saved.filter((key): key is ColumnKey => ALL_COLUMNS.includes(key));
      if (valid.includes("source")) return valid;
    }
  } catch {
    /* per-viewer convenience only */
  }
  return [...ALL_COLUMNS];
}

const columns = ref<ColumnKey[]>(props.compact ? COMPACT_COLUMNS : storedColumns());
const columnDraft = ref<string[]>([...columns.value]);
const response = ref<SourceListResponse | null>(null);
const rows = ref<SourceRow[]>([]);
const loading = ref(false);
const error = ref("");
const text = ref("");
const filters = ref<Record<FilterKey, string>>({
  provider: "",
  document_language: "",
  original_language: "",
  capture_id: "",
  build_status: "",
  relationship: "",
  role: "",
  ...props.initialFilters,
});
const queuedOnly = ref(props.queuedIds.length > 0);
const sort = ref<SourceSort>("added");
const order = ref<"asc" | "desc">("desc");
const offset = ref(0);
const limit = ref(props.pageSize);
let requestSerial = 0;
let debounce: ReturnType<typeof setTimeout> | undefined;
const displayedQueryIdentity = ref("");

const selectedSet = computed(() => new Set(props.selected));
const total = computed(() => response.value?.total ?? 0);
const anyFilter = computed(
  () => Boolean(text.value.trim()) || FILTERS.some((key) => filters.value[key]) || queuedOnly.value,
);
const pageIds = computed(() => rows.value.map((row) => row.source_document_id));
const pageSelectedCount = computed(
  () => pageIds.value.filter((id) => selectedSet.value.has(id)).length,
);
const allOnPage = computed(
  () => rows.value.length > 0 && pageSelectedCount.value === rows.value.length,
);
const someOnPage = computed(() => pageSelectedCount.value > 0 && !allOnPage.value);
const rangeText = computed(() =>
  i18n.tf("sources.table.range", {
    from: total.value ? (offset.value + 1).toLocaleString(i18n.locale) : "0",
    to: Math.min(offset.value + limit.value, total.value).toLocaleString(i18n.locale),
    total: total.value.toLocaleString(i18n.locale),
  }),
);

function label(kind: LabelKind, value: string | null | undefined) {
  return enumLabel(t, kind, value);
}
function columnLabel(key: ColumnKey) {
  return i18n.t(`sources.column.${key}`);
}
function lang(codes: string[] | null | undefined) {
  return languageList(codes, i18n.locale) || i18n.t("sources.language_unknown");
}
function formatDate(value: string | null) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat(i18n.locale || undefined, {
      timeZone: i18n.timeZone,
      dateStyle: "medium",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function facetOptions(key: FilterKey): Array<{ value: string; label: string; count: number }> {
  const counts = response.value?.facets?.[key] || {};
  const values = Object.keys(counts);
  const ordered =
    key === "document_language" || key === "original_language"
      ? sortLanguageCodes(values, i18n.locale)
      : values;
  const current = filters.value[key];
  if (current && !ordered.includes(current)) ordered.push(current);
  return ordered.map((value) => ({
    value,
    count: counts[value] ?? 0,
    label: filterValueLabel(key, value),
  }));
}
function filterValueLabel(key: FilterKey, value: string) {
  if (key === "document_language" || key === "original_language")
    return value === "und" ? i18n.t("sources.language_unknown") : languageName(value, i18n.locale);
  if (key === "capture_id")
    return props.captureLabels[value] || i18n.t("sources.filter.capture_unnamed");
  const kind: Record<string, LabelKind> = {
    provider: "provider",
    build_status: "build_status",
    relationship: "relationship",
    role: "role",
  };
  return label(kind[key], value);
}

function query(): SourceListQuery {
  const params: SourceListQuery = {
    q: text.value.trim() || undefined,
    sort: sort.value,
    order: order.value,
    offset: offset.value,
    limit: limit.value,
  };
  for (const key of FILTERS) if (filters.value[key]) params[key] = [filters.value[key]];
  if (queuedOnly.value && props.queuedIds.length) params.ids = props.queuedIds;
  return params;
}

function queryIdentity(value: SourceListQuery) {
  return JSON.stringify(
    Object.entries(value)
      .filter(([, entry]) => entry !== undefined)
      .sort(([left], [right]) => left.localeCompare(right)),
  );
}

async function reload() {
  const serial = ++requestSerial;
  const nextQuery = query();
  const nextIdentity = queryIdentity(nextQuery);
  const changesDisplayedIdentity =
    Boolean(displayedQueryIdentity.value) && displayedQueryIdentity.value !== nextIdentity;

  loading.value = true;
  error.value = "";
  if (changesDisplayedIdentity) {
    response.value = null;
    rows.value = [];
    emit("displayed", []);
    if (props.selected.length) emit("update:selected", []);
  }
  try {
    const next = await corpusSourcesApi.listSources(nextQuery);
    if (serial !== requestSerial) return;
    response.value = next;
    rows.value = next.items;
    displayedQueryIdentity.value = nextIdentity;
    emit("displayed", next.items);
    emit("loaded", next);
  } catch (cause) {
    if (serial !== requestSerial) return;
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    if (serial === requestSerial) loading.value = false;
  }
}

/** Re-read only the given rows (for example after one build finished) and patch them in place. */
async function refreshRows(ids: string[]) {
  const wanted = ids.filter((id) => pageIds.value.includes(id));
  if (!wanted.length) return;
  try {
    const fresh = await corpusSourcesApi.listSources({ ids: wanted, limit: wanted.length });
    const byId = new Map(fresh.items.map((row) => [row.source_document_id, row]));
    rows.value = rows.value
      .filter((row) => !wanted.includes(row.source_document_id) || byId.has(row.source_document_id))
      .map((row) => byId.get(row.source_document_id) || row);
    emit("displayed", rows.value);
  } catch {
    /* the next full reload reports errors */
  }
}
defineExpose({ reload, refreshRows });

function applyFilters() {
  offset.value = 0;
  void reload();
}
function onText() {
  if (debounce !== undefined) clearTimeout(debounce);
  debounce = setTimeout(applyFilters, 250);
}
function clearFilters() {
  text.value = "";
  for (const key of FILTERS) filters.value[key] = "";
  queuedOnly.value = false;
  applyFilters();
}
function sortBy(key: ColumnKey) {
  const target = SORTABLE[key];
  if (!target) return;
  if (sort.value === target) order.value = order.value === "asc" ? "desc" : "asc";
  else {
    sort.value = target;
    order.value = target === "added" ? "desc" : "asc";
  }
  offset.value = 0;
  void reload();
}
function ariaSort(key: ColumnKey) {
  const target = SORTABLE[key];
  if (!target) return undefined;
  if (sort.value !== target) return "none";
  return order.value === "asc" ? "ascending" : "descending";
}
function page(delta: number) {
  const next = offset.value + delta * limit.value;
  if (next < 0 || next >= total.value) return;
  offset.value = next;
  void reload();
}
function setLimit(value: number) {
  limit.value = value;
  offset.value = 0;
  void reload();
}

function toggleRow(id: string) {
  const next = new Set(props.selected);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  emit("update:selected", [...next]);
}
function togglePage() {
  const next = new Set(props.selected);
  if (allOnPage.value) for (const id of pageIds.value) next.delete(id);
  else for (const id of pageIds.value) next.add(id);
  emit("update:selected", [...next]);
}
function choose(id: string) {
  if (props.disabled) return;
  emit("choose", id === props.activeId ? "" : id);
}

function applyColumns() {
  columns.value = columnDraft.value.filter((key): key is ColumnKey =>
    ALL_COLUMNS.includes(key as ColumnKey),
  );
  if (!columns.value.includes("source")) columns.value.unshift("source");
  try {
    localStorage.setItem(COLUMN_STORAGE, JSON.stringify(columns.value));
  } catch {
    /* ignore */
  }
}
function resetColumns() {
  columnDraft.value = [...ALL_COLUMNS];
}

const selectAll = ref<HTMLInputElement | null>(null);
const columnsDialog = ref<InstanceType<typeof UiTableColumnsDialog> | null>(null);
watch([someOnPage, selectAll], () => {
  if (selectAll.value) selectAll.value.indeterminate = someOnPage.value;
});
watch(
  () => props.refreshKey,
  () => void reload(),
);
watch(
  () => props.queuedIds.join(","),
  (value) => {
    queuedOnly.value = Boolean(value);
    applyFilters();
  },
);
onMounted(() => void reload());
onBeforeUnmount(() => {
  if (debounce !== undefined) clearTimeout(debounce);
});
</script>

<template>
  <section class="source-table" :class="{ 'is-compact': compact }" :aria-busy="loading">
    <div class="st-filters" role="search" :aria-label="i18n.t('sources.filter.label')">
      <label class="st-search">
        <span class="sr-only">{{ i18n.t("sources.filter.search") }}</span>
        <AppIcon name="search" />
        <input
          v-model="text"
          class="control"
          type="search"
          :placeholder="i18n.t('sources.filter.search_placeholder')"
          @input="onText"
        />
      </label>
      <label
        v-for="key in compact ? (['provider', 'document_language'] as FilterKey[]) : FILTERS"
        :key="key"
        class="st-filter"
      >
        <span class="st-filter-label">{{ i18n.t(`sources.filter.${key}`) }}</span>
        <select v-model="filters[key]" class="control" :data-filter="key" @change="applyFilters">
          <option value="">{{ i18n.t("sources.filter.any") }}</option>
          <option v-for="option in facetOptions(key)" :key="option.value" :value="option.value">
            {{ option.label }} ({{ option.count.toLocaleString(i18n.locale) }})
          </option>
        </select>
      </label>
      <button v-if="anyFilter" type="button" class="btn small quiet st-clear" @click="clearFilters">
        {{ i18n.t("sources.filter.clear") }}
      </button>
      <button
        v-if="!compact"
        type="button"
        class="btn small st-columns"
        @click="
          columnDraft = [...columns];
          columnsDialog?.open();
        "
      >
        {{ i18n.t("sources.table.columns") }}
      </button>
      <UiTableColumnsDialog
        v-if="!compact"
        ref="columnsDialog"
        v-model="columnDraft"
        :available="ALL_COLUMNS.map((key) => ({ key, label: columnLabel(key) }))"
        :title="i18n.t('sources.table.columns')"
        @apply="applyColumns"
        @reset="resetColumns"
        @cancel="columnDraft = [...columns]"
      />
    </div>

    <p v-if="queuedIds.length" class="st-queued" role="status">
      <label>
        <input v-model="queuedOnly" type="checkbox" data-queued-filter @change="applyFilters" />
        <AppIcon name="filter" />
        {{ i18n.tf("sources.queued_filter", { count: queuedIds.length }) }}
      </label>
    </p>
    <p v-if="lockedReason" class="st-locked" role="status">
      <AppIcon name="lock" />{{ lockedReason }}
    </p>

    <p v-if="error" class="st-error" role="alert">
      <AppIcon name="warning" /><span>{{ i18n.tf("sources.load_failed", { error }) }}</span>
      <button type="button" class="btn small" @click="reload">
        {{ i18n.t("sources.retry_load") }}
      </button>
    </p>

    <div class="st-scroll" tabindex="0" :aria-label="i18n.t('sources.table.caption')" role="region">
      <table class="st-table">
        <caption class="sr-only">
          {{
            i18n.t("sources.table.caption")
          }}
          ·
          {{
            rangeText
          }}
        </caption>
        <thead>
          <tr>
            <th v-if="!compact" scope="col" class="st-check">
              <input
                ref="selectAll"
                type="checkbox"
                :checked="allOnPage"
                :disabled="!rows.length"
                :aria-label="i18n.t('sources.table.select_page')"
                data-select-page
                @change="togglePage"
              />
            </th>
            <th v-else scope="col" class="st-check">
              <span class="sr-only">{{ i18n.t("sources.table.use_column") }}</span>
            </th>
            <th
              v-for="key in columns"
              :key="key"
              scope="col"
              :aria-sort="ariaSort(key)"
              :data-column="key"
            >
              <button
                v-if="SORTABLE[key]"
                type="button"
                class="st-sort"
                :data-sort="SORTABLE[key]"
                @click="sortBy(key)"
              >
                {{ columnLabel(key) }}
                <span aria-hidden="true" class="st-sort-mark">{{
                  ariaSort(key) === "ascending" ? "▲" : ariaSort(key) === "descending" ? "▼" : "↕"
                }}</span>
              </button>
              <span v-else>{{ columnLabel(key) }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && !rows.length">
            <td :colspan="columns.length + 1" class="st-state" role="status">
              {{ i18n.t("sources.loading") }}
            </td>
          </tr>
          <tr v-else-if="!rows.length && !error">
            <td :colspan="columns.length + 1" class="st-state">
              <strong>{{
                anyFilter ? i18n.t("sources.empty_filtered") : i18n.t("sources.empty")
              }}</strong>
              <button v-if="anyFilter" type="button" class="btn small" @click="clearFilters">
                {{ i18n.t("sources.filter.clear") }}
              </button>
            </td>
          </tr>
          <tr
            v-for="row in rows"
            :key="row.source_document_id"
            :data-source-id="row.source_document_id"
            :class="{
              'is-active': compact && row.source_document_id === activeId,
              'is-checked': !compact && selectedSet.has(row.source_document_id),
              'is-queued': queuedIds.includes(row.source_document_id),
            }"
          >
            <td class="st-check">
              <input
                v-if="!compact"
                type="checkbox"
                :checked="selectedSet.has(row.source_document_id)"
                :aria-label="i18n.tf('sources.table.select_row', { title: row.title })"
                @change="toggleRow(row.source_document_id)"
              />
              <input
                v-else
                type="radio"
                name="corpus-builder-source"
                :checked="row.source_document_id === activeId"
                :disabled="disabled"
                :aria-label="i18n.tf('sources.table.use_row', { title: row.title })"
                @click="choose(row.source_document_id)"
                @keydown.space.prevent="choose(row.source_document_id)"
              />
            </td>
            <template v-for="key in columns" :key="key">
              <th v-if="key === 'source'" scope="row" class="st-source">
                <strong>{{ row.title || row.filename }}</strong>
                <small v-if="row.title && row.filename && row.title !== row.filename">{{
                  row.filename
                }}</small>
                <small v-if="row.document_author">{{ row.document_author }}</small>
              </th>
              <td v-else-if="key === 'provider'">
                {{ label("provider", row.provider) }}
                <small v-if="row.source_project_language" class="st-sub">{{
                  i18n.tf("sources.project", {
                    project: languageName(row.source_project_language, i18n.locale),
                  })
                }}</small>
              </td>
              <td v-else-if="key === 'language'" :lang="undefined">
                {{ lang(row.document_languages) }}
              </td>
              <td v-else-if="key === 'original_language'">
                {{ row.original_language ? languageName(row.original_language, i18n.locale) : "—" }}
              </td>
              <td v-else-if="key === 'edition'">{{ editionLine(t, row) || "—" }}</td>
              <td v-else-if="key === 'role'">
                {{ row.contribution_role ? label("role", row.contribution_role) : "—" }}
              </td>
              <td v-else-if="key === 'acquisition'">
                <UiStatusBadge
                  :label="label('acquisition', row.acquisition_status)"
                  :tone="enumTone('acquisition', row.acquisition_status)"
                />
              </td>
              <td v-else-if="key === 'build'">
                <UiStatusBadge
                  :label="label('build_status', row.build_status)"
                  :tone="enumTone('build_status', row.build_status)"
                />
                <small v-if="row.build_count > 1" class="st-sub">{{
                  i18n.tf("sources.build_count", { count: row.build_count })
                }}</small>
              </td>
              <td v-else-if="key === 'added'">{{ formatDate(row.created_at) }}</td>
              <td v-else-if="key === 'actions'" class="st-actions">
                <button
                  type="button"
                  class="btn small"
                  :aria-label="i18n.tf('sources.details_named', { title: row.title })"
                  @click="emit('inspect', row.source_document_id)"
                >
                  {{ i18n.t("sources.details") }}
                </button>
                <UiTooltip
                  v-if="compact && deletable"
                  :text="i18n.t('pdf_corpus.source_delete')"
                  trigger-mode="content"
                  :content-focusable="disabled"
                  placement="bottom"
                >
                  <button
                    type="button"
                    class="btn small icon-only"
                    :disabled="disabled"
                    :aria-label="i18n.tf('pdf_corpus.source_delete_named', { name: row.title })"
                    @click="emit('delete', row.source_document_id)"
                  >
                    <AppIcon name="trash" />
                  </button>
                </UiTooltip>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>

    <nav class="st-pager" :aria-label="i18n.t('sources.table.pagination')">
      <span role="status">{{ rangeText }}</span>
      <label v-if="!compact" class="st-page-size">
        <span>{{ i18n.t("sources.table.page_size") }}</span>
        <select
          class="control"
          :value="limit"
          @change="setLimit(Number(($event.target as HTMLSelectElement).value))"
        >
          <option v-for="size in [25, 50, 100, 200]" :key="size" :value="size">{{ size }}</option>
        </select>
      </label>
      <button
        type="button"
        class="btn small"
        data-page="previous"
        :disabled="offset === 0 || loading"
        @click="page(-1)"
      >
        <AppIcon name="chevron-left" />{{ i18n.t("ui.previous") }}
      </button>
      <button
        type="button"
        class="btn small"
        data-page="next"
        :disabled="offset + limit >= total || loading"
        @click="page(1)"
      >
        {{ i18n.t("ui.next") }}<AppIcon name="chevron-right" />
      </button>
    </nav>
  </section>
</template>

<style scoped>
.source-table {
  display: grid;
  gap: 10px;
  min-width: 0;
}
.st-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 8px 10px;
}
.st-search {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 1 1 220px;
  min-width: 0;
}
.st-search input {
  width: 100%;
}
.st-search :deep(svg) {
  inline-size: 1rem;
  block-size: 1rem;
  width: 1rem;
  height: 1rem;
  max-inline-size: 1rem;
  max-block-size: 1rem;
  flex: 0 0 1rem;
  display: block;
}
.st-filter {
  display: grid;
  gap: 2px;
  min-width: 0;
  max-width: 220px;
}
.st-filter-label {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.st-filter select {
  max-width: 100%;
}
.st-queued,
.st-locked,
.st-error {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 8px 10px;
  border-radius: var(--radius-control);
  font-size: var(--fs-sm);
}
.st-queued {
  border: 1px solid var(--tone-info-border);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
}
.st-queued label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: var(--fw-semibold);
}
.st-locked {
  border: 1px solid var(--border-subtle);
  background: var(--surface-inset);
  color: var(--text-secondary);
}
.st-error {
  border: 1px solid var(--tone-danger-border);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.st-scroll {
  max-height: min(70vh, 720px);
  overflow: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.is-compact .st-scroll {
  max-height: 360px;
}
.st-scroll:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: 2px;
}
.st-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: var(--fs-sm);
}
.st-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-strong);
  background: var(--surface-raised);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  text-align: start;
  white-space: nowrap;
}
.st-table td,
.st-table tbody th {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
  text-align: start;
  vertical-align: top;
  font-weight: var(--fw-regular);
}
.st-table tbody tr:hover {
  background: var(--surface-hover);
}
.st-table tbody tr.is-active,
.st-table tbody tr.is-checked {
  background: var(--surface-selected);
}
.st-table tbody tr.is-queued .st-source {
  box-shadow: inset 3px 0 0 var(--tone-info-edge);
}
.st-check {
  width: 36px;
}
.st-source strong {
  display: block;
  overflow-wrap: anywhere;
}
.st-source small,
.st-sub {
  display: block;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  overflow-wrap: anywhere;
}
.st-sort {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
.st-sort:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: 2px;
}
.st-sort-mark {
  font-size: var(--fs-xs);
}
.st-state {
  padding: 24px 10px;
  color: var(--text-secondary);
  text-align: center;
}
.st-state .btn {
  margin-inline-start: 8px;
}
.st-actions {
  display: flex;
  gap: 6px;
  white-space: nowrap;
}
.st-pager {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.st-pager > span {
  margin-inline-end: auto;
}
.st-page-size {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>
