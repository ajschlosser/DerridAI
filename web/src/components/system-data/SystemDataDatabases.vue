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
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import AppIcon from "../AppIcon.vue";
import { systemApi, type SystemDataDatabase, type SystemDataTable } from "../../api/system";
import { useI18nStore } from "../../stores/i18n";
import UiTooltip from "../ui/UiTooltip.vue";

type DataRow = Record<string, unknown>;

const i18n = useI18nStore();
const route = useRoute();
const router = useRouter();
const databases = ref<SystemDataDatabase[]>([]);
const selectedDatabase = ref(String(route.query.db || "system"));
const selectedTable = ref(String(route.query.table || ""));
const search = ref(String(route.query.q || ""));
const page = ref<(SystemDataTable & { rows: DataRow[]; offset: number; limit: number }) | null>(
  null,
);
const catalogLoaded = ref(false);
const catalogLoading = ref(false);
const tableLoading = ref(false);
const catalogError = ref("");
const tableError = ref("");
const detail = ref<DataRow | null>(null);
const requestedOffset = ref(Math.max(0, Number(route.query.offset) || 0));
const shownTableIdentity = ref("");
let catalogRequest = 0;
let tableRequest = 0;

const database = computed(() =>
  databases.value.find((item) => item.name === selectedDatabase.value),
);
const filteredTables = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  const rows = database.value?.tables || [];
  return query ? rows.filter((item) => item.name.toLocaleLowerCase().includes(query)) : rows;
});
const table = computed(() =>
  database.value?.tables.find((item) => item.name === selectedTable.value),
);
const columns = computed(() => page.value?.columns || table.value?.columns || []);
const visibleColumns = computed(() => columns.value.slice(0, 6));
const totalRows = computed(() => table.value?.row_count || 0);
function tableIdentity(offset = requestedOffset.value) {
  return JSON.stringify([selectedDatabase.value, selectedTable.value, offset]);
}
const displayedTableIsCurrent = computed(
  () => Boolean(page.value) && shownTableIdentity.value === tableIdentity(),
);
const tableInitialPending = computed(() => tableLoading.value && !displayedTableIsCurrent.value);
const tableRefreshing = computed(() => tableLoading.value && displayedTableIsCurrent.value);

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}
function dbTitle(name: string) {
  return name === "auth"
    ? t("runtime.system_identity_access", "Identity and access")
    : t("runtime.system_application_data", "Application data");
}
function dbHelp(name: string) {
  return name === "auth"
    ? t(
        "runtime.system_identity_access_help",
        "Sensitive identity state including users, roles or permissions, sessions, and login security.",
      )
    : t(
        "runtime.system_application_data_help",
        "Durable application information such as provider profiles, annotations, languages, and jobs.",
      );
}
// Explanations live in the locale files as runtime.system_table_help_<table>; unknown tables get none.
function tableHelp(name: string): string {
  const key = `runtime.system_table_help_${name}`;
  const text = i18n.t(key, "");
  return text && text !== key ? text : "";
}
const memoryTables = new Set(["semantic_memory_outbox", "metadata_memory_bindings"]);
function cell(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

async function loadDatabases() {
  const request = ++catalogRequest;
  catalogLoading.value = true;
  catalogError.value = "";
  try {
    const next = (await systemApi.systemData()).databases || [];
    if (request !== catalogRequest) return;
    databases.value = next;
    catalogLoaded.value = true;
    if (!databases.value.some((item) => item.name === selectedDatabase.value))
      selectedDatabase.value = databases.value[0]?.name || "";
    if (!database.value?.tables.some((item) => item.name === selectedTable.value))
      selectedTable.value = database.value?.tables[0]?.name || "";
    applyRequestedTable();
    requestedOffset.value = Math.max(0, Number(route.query.offset) || 0);
    // The database directory is useful as soon as the catalog succeeds. Start
    // row hydration independently so a slow table read cannot hold the whole
    // workspace behind its loading state.
    if (selectedTable.value) void loadTable(requestedOffset.value, false);
  } catch (cause) {
    if (request !== catalogRequest) return;
    catalogError.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    if (request === catalogRequest) catalogLoading.value = false;
  }
}
// A link such as ?table=semantic_memory_outbox opens that table in whichever database holds it.
function applyRequestedTable() {
  const requested = String(route?.query.table || "");
  if (!requested) return;
  const owner = databases.value.find((item) => item.tables.some((tbl) => tbl.name === requested));
  if (!owner) return;
  selectedDatabase.value = owner.name;
  selectedTable.value = requested;
}
function syncRoute(offset = requestedOffset.value) {
  void router.replace({
    name: "system-data-databases",
    query: {
      ...route.query,
      db: selectedDatabase.value || undefined,
      table: selectedTable.value || undefined,
      q: search.value || undefined,
      offset: offset > 0 ? String(offset) : undefined,
    },
  });
}

async function loadTable(offset = 0, updateRoute = true) {
  if (!selectedDatabase.value || !selectedTable.value) return;
  requestedOffset.value = offset;
  if (updateRoute) syncRoute(offset);
  const identity = tableIdentity(offset);
  const request = ++tableRequest;
  const retained = shownTableIdentity.value === identity && Boolean(page.value);
  tableLoading.value = true;
  tableError.value = "";
  if (!retained) detail.value = null;
  try {
    const next = await systemApi.systemDataRows(
      selectedDatabase.value,
      selectedTable.value,
      25,
      offset,
    );
    if (request !== tableRequest || identity !== tableIdentity()) return;
    page.value = next;
    shownTableIdentity.value = identity;
  } catch (cause) {
    if (request !== tableRequest || identity !== tableIdentity()) return;
    tableError.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    if (request === tableRequest) tableLoading.value = false;
  }
}
function chooseDatabase(name: string) {
  selectedDatabase.value = name;
  selectedTable.value = databases.value.find((item) => item.name === name)?.tables[0]?.name || "";
  search.value = "";
  requestedOffset.value = 0;
  void loadTable(0);
}
function chooseTable(name: string) {
  selectedTable.value = name;
  requestedOffset.value = 0;
  void loadTable(0);
}

onMounted(() => void loadDatabases());
watch(search, () => syncRoute(requestedOffset.value));
// Keep URL-addressable database/table/page state authoritative when a cached
// System Data workspace is revisited through breadcrumbs or browser history.
watch(
  () => [route.query.db, route.query.table, route.query.q, route.query.offset],
  ([db, tableName, query, offset]) => {
    if (!databases.value.length) return;
    const nextDb = String(db || selectedDatabase.value || "system");
    const nextTable = String(tableName || "");
    const nextQuery = String(query || "");
    const nextOffset = Math.max(0, Number(offset) || 0);
    if (
      nextDb === selectedDatabase.value &&
      nextTable === selectedTable.value &&
      nextQuery === search.value &&
      nextOffset === requestedOffset.value
    )
      return;
    if (databases.value.some((item) => item.name === nextDb)) selectedDatabase.value = nextDb;
    search.value = nextQuery;
    applyRequestedTable();
    if (nextTable && database.value?.tables.some((item) => item.name === nextTable))
      selectedTable.value = nextTable;
    requestedOffset.value = nextOffset;
    void loadTable(nextOffset, false);
  },
);
</script>

<template>
  <div class="databases-workspace">
    <header class="workspace-heading">
      <div>
        <h2>{{ t("runtime.system_databases", "Databases") }}</h2>
        <p>
          {{
            t(
              "runtime.system_databases_help",
              "Browse durable application and identity data. Generic editing is intentionally disabled; use purpose-built administration pages for supported changes.",
            )
          }}
        </p>
      </div>
      <button class="btn" type="button" :disabled="catalogLoading" @click="loadDatabases">
        <AppIcon name="refresh" /> {{ t("common.refresh", "Refresh") }}
      </button>
    </header>

    <div v-if="catalogError && !catalogLoaded" class="state error" role="alert">
      <strong>{{ t("runtime.system_database_failed", "Could not load system databases.") }}</strong
      ><span>{{ catalogError }}</span>
      <button class="btn tiny" type="button" @click="loadDatabases">
        {{ t("common.retry", "Retry") }}
      </button>
    </div>
    <div v-else-if="catalogLoading && !catalogLoaded" class="state" role="status">
      {{ t("runtime.system_database_loading", "Loading system databases…") }}
    </div>
    <div v-if="catalogLoading && catalogLoaded" class="state state-inline" role="status">
      {{ t("loading.updating", "Updating…") }}
    </div>
    <div v-if="catalogError && catalogLoaded" class="state error state-inline" role="alert">
      <strong>{{ t("loading.stale", "Showing previously loaded data.") }}</strong>
      <span>{{ catalogError }}</span>
      <button class="btn tiny" type="button" @click="loadDatabases">
        {{ t("common.retry", "Retry") }}
      </button>
    </div>
    <div v-if="catalogLoaded" class="browser">
      <aside class="directory">
        <div class="database-switcher">
          <button
            v-for="item in databases"
            :key="item.name"
            type="button"
            :class="{ active: selectedDatabase === item.name }"
            @click="chooseDatabase(item.name)"
          >
            <AppIcon :name="item.name === 'auth' ? 'lock' : 'database'" />
            <span
              ><strong>{{ dbTitle(item.name) }}</strong
              ><small
                >{{ item.name }} · {{ item.tables.length }}
                {{ t("runtime.system_tables", "tables") }}</small
              ></span
            >
          </button>
        </div>
        <div class="database-description">
          <strong>{{ dbTitle(selectedDatabase) }}</strong>
          <p>{{ dbHelp(selectedDatabase) }}</p>
        </div>
        <label class="search-field"
          ><AppIcon name="search" /><input
            v-model="search"
            type="search"
            :placeholder="t('runtime.system_find_table', 'Find a table')"
        /></label>
        <nav class="table-directory" aria-label="Database tables">
          <div
            v-for="item in filteredTables"
            :key="item.name"
            class="table-row"
            :class="{ active: selectedTable === item.name }"
          >
            <button
              type="button"
              :aria-current="selectedTable === item.name ? 'true' : undefined"
              @click="chooseTable(item.name)"
            >
              <span>{{ item.name }}</span
              ><small
                >{{ item.row_count.toLocaleString() }} {{ t("runtime.system_rows", "rows") }}</small
              >
            </button>
            <UiTooltip
              v-if="tableHelp(item.name)"
              :text="tableHelp(item.name)"
              :label="i18n.tf('runtime.system_table_about', { table: item.name })"
              placement="bottom"
            />
          </div>
        </nav>
      </aside>

      <section class="table-space">
        <header v-if="table" class="table-heading">
          <div>
            <h3>
              {{ table.name }}
            </h3>
            <p v-if="tableHelp(table.name)" class="table-about">{{ tableHelp(table.name) }}</p>
            <p>
              {{ totalRows.toLocaleString() }} {{ t("runtime.system_rows", "rows") }} ·
              {{ t("runtime.system_read_only_inspection", "read-only inspection") }}
            </p>
          </div>
          <RouterLink
            v-if="memoryTables.has(table.name)"
            class="related-link"
            to="/metadata-memory"
          >
            {{ t("runtime.system_table_related", "Related: Metadata memory") }}
          </RouterLink>
          <span class="readonly"
            ><AppIcon name="lock" /> {{ t("runtime.system_read_only", "Read only") }}</span
          >
        </header>
        <div class="policy-note">
          <AppIcon name="help" /><span>{{
            t(
              "runtime.system_database_policy",
              "Changes to users, roles, providers, languages, and other managed objects belong in their dedicated administration workspaces so validation and audit rules remain intact.",
            )
          }}</span>
        </div>

        <div v-if="tableError && !displayedTableIsCurrent" class="state error" role="alert">
          <strong>{{ t("runtime.system_table_failed", "Could not load this table.") }}</strong
          ><span>{{ tableError }}</span>
          <button class="btn tiny" type="button" @click="loadTable(requestedOffset)">
            {{ t("common.retry", "Retry") }}
          </button>
        </div>
        <div v-else-if="tableInitialPending" class="state" role="status">
          {{ t("runtime.system_rows_loading", "Loading rows…") }}
        </div>
        <div
          v-if="tableRefreshing && displayedTableIsCurrent"
          class="state state-inline"
          role="status"
        >
          {{ t("loading.updating", "Updating…") }}
        </div>
        <div
          v-if="tableError && displayedTableIsCurrent"
          class="state error state-inline"
          role="alert"
        >
          <strong>{{ t("loading.stale", "Showing previously loaded data.") }}</strong>
          <span>{{ tableError }}</span>
          <button class="btn tiny" type="button" @click="loadTable(requestedOffset)">
            {{ t("common.retry", "Retry") }}
          </button>
        </div>
        <div v-if="displayedTableIsCurrent && !page?.rows.length" class="state">
          {{ t("runtime.system_table_empty", "This table is empty.") }}
        </div>
        <template v-if="displayedTableIsCurrent && page?.rows.length">
          <div class="data-table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="column in visibleColumns" :key="column.name">
                    {{ column.name }}
                    <UiTooltip
                      v-if="column.sensitive"
                      :text="t('runtime.system_sensitive_redacted', 'Sensitive value redacted')"
                      trigger-mode="content"
                      placement="bottom"
                    >
                      <span class="sensitive-mark" aria-hidden="true">●</span>
                    </UiTooltip>
                  </th>
                  <th>
                    <span class="sr-only">{{ t("common.actions", "Actions") }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in page.rows" :key="index">
                  <td
                    v-for="column in visibleColumns"
                    :key="column.name"
                    :class="{ mono: column.primary_key }"
                  >
                    <span class="cell-value">{{ cell(row[column.name]) }}</span>
                  </td>
                  <td>
                    <button class="btn tiny" type="button" @click="detail = row">
                      {{ t("runtime.system_inspect", "Inspect") }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <footer class="pagination">
            <span
              >{{ page.offset + 1 }}–{{ Math.min(page.offset + page.rows.length, totalRows) }} of
              {{ totalRows }}</span
            >
            <div>
              <button
                class="btn tiny"
                type="button"
                :disabled="page.offset <= 0"
                @click="loadTable(Math.max(0, page.offset - page.limit))"
              >
                {{ t("common.previous", "Previous") }}</button
              ><button
                class="btn tiny"
                type="button"
                :disabled="page.offset + page.rows.length >= totalRows"
                @click="loadTable(page.offset + page.limit)"
              >
                {{ t("common.next", "Next") }}
              </button>
            </div>
          </footer>
        </template>
      </section>
    </div>

    <aside v-if="detail && displayedTableIsCurrent" class="detail-panel" aria-label="Row details">
      <header>
        <div>
          <small>{{ selectedDatabase }} / {{ selectedTable }}</small>
          <h3>{{ t("runtime.system_row_details", "Row details") }}</h3>
        </div>
        <button
          class="icon-btn"
          type="button"
          :aria-label="t('runtime.system_close_details', 'Close details')"
          @click="detail = null"
        >
          <AppIcon name="close" />
        </button>
      </header>
      <dl>
        <div v-for="column in columns" :key="column.name">
          <dt>
            {{ column.name
            }}<span v-if="column.sensitive">
              · {{ t("runtime.system_sensitive", "sensitive") }}</span
            >
          </dt>
          <dd :class="{ mono: column.primary_key }">{{ cell(detail[column.name]) }}</dd>
        </div>
      </dl>
    </aside>
  </div>
</template>

<style scoped>
.databases-workspace {
  display: grid;
  gap: 16px;
}
.workspace-heading {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 16px;
}
.workspace-heading h2 {
  margin: 0;
  font-size: 1.25rem;
}
.workspace-heading p {
  margin: 5px 0 0;
  max-width: 760px;
  color: var(--muted);
  line-height: 1.5;
}
.workspace-heading :deep(svg) {
  width: 16px;
  height: 16px;
}
.state {
  display: grid;
  gap: 5px;
  padding: 20px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--soft);
  color: var(--muted);
}
.state.error {
  color: var(--tone-danger-fg);
}
.state-inline {
  padding-block: 10px;
}
.browser {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  gap: 16px;
}
.directory {
  display: grid;
  align-content: start;
  gap: 12px;
}
.database-switcher {
  display: grid;
  gap: 6px;
}
.database-switcher button {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr);
  gap: 9px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  color: inherit;
  text-align: left;
  cursor: pointer;
}
.database-switcher button.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 18%, transparent);
}
.database-switcher :deep(svg) {
  width: 17px;
  height: 17px;
  margin-top: 2px;
}
.database-switcher strong,
.database-switcher small {
  display: block;
}
.database-switcher small {
  margin-top: 2px;
  color: var(--muted);
}
.database-description {
  padding: 11px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.database-description p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.45;
}
.search-field {
  display: flex;
  gap: 7px;
  align-items: center;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
}
.search-field :deep(svg) {
  width: 15px;
  height: 15px;
  color: var(--muted);
}
.search-field input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: inherit;
  font: inherit;
}
.table-directory {
  display: grid;
  gap: 3px;
  max-height: 460px;
  overflow: auto;
}
.table-row {
  display: flex;
  align-items: center;
  border-radius: 8px;
}
.table-row button {
  display: flex;
  flex: 1;
  min-width: 0;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 9px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}
.table-row button > span {
  overflow: hidden;
  text-overflow: ellipsis;
}
.table-row:hover,
.table-row.active {
  background: var(--soft);
}
/* The directory scrolls, so anchor the tooltip inside it rather than centring it past the edge. */
.table-row :deep(.ui-tooltip-content) {
  inset-inline: auto 0;
  max-inline-size: 15rem;
  transform: none;
}
.table-about {
  max-width: 60ch;
}
.related-link {
  margin-inline-start: auto;
  margin-inline-end: 10px;
  font-size: 0.8125rem;
  font-weight: 650;
}
.table-directory small {
  color: var(--muted);
  white-space: nowrap;
}
.table-space {
  min-width: 0;
  display: grid;
  align-content: start;
  gap: 12px;
}
.table-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}
.table-heading h3 {
  margin: 0;
}
.table-heading p {
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 0.8rem;
}
.readonly {
  display: flex;
  gap: 5px;
  align-items: center;
  padding: 4px 7px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  font-size: 0.75rem;
}
.readonly :deep(svg) {
  width: 13px;
  height: 13px;
}
.policy-note {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--soft);
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.45;
}
.policy-note :deep(svg) {
  flex: 0 0 auto;
  width: 15px;
  height: 15px;
}
.data-table-wrap {
  max-width: 100%;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 11px;
}
.data-table {
  width: 100%;
  min-width: 680px;
  border-collapse: collapse;
  background: var(--card);
}
.data-table th,
.data-table td {
  padding: 9px 10px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  font-size: 0.8rem;
  vertical-align: top;
}
.data-table th {
  position: sticky;
  top: 0;
  background: var(--soft);
  color: var(--muted);
  font-size: 0.75rem;
}
.cell-value {
  display: block;
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sensitive-mark {
  margin-left: 5px;
  color: var(--tone-warn-fg);
}
.pagination {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  color: var(--muted);
  font-size: 0.8rem;
}
.pagination > div {
  display: flex;
  gap: 6px;
}
.detail-panel {
  position: fixed;
  z-index: 50;
  top: 0;
  right: 0;
  width: min(520px, 100vw);
  height: 100vh;
  overflow: auto;
  padding: 22px;
  border-left: 1px solid var(--line);
  background: var(--card);
  box-shadow: -16px 0 40px color-mix(in srgb, currentColor 10%, transparent);
}
.detail-panel header {
  display: flex;
  justify-content: space-between;
  gap: 14px;
}
.detail-panel h3 {
  margin: 4px 0 0;
}
.detail-panel dl {
  display: grid;
  gap: 12px;
}
.detail-panel dt {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 700;
}
.detail-panel dd {
  margin: 3px 0 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.icon-btn {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: transparent;
  color: inherit;
  cursor: pointer;
}
.icon-btn :deep(svg) {
  width: 15px;
  height: 15px;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
@media (max-width: 900px) {
  .browser {
    grid-template-columns: 1fr;
  }
  .table-directory {
    max-height: 220px;
  }
}
@media (max-width: 640px) {
  .workspace-heading {
    display: grid;
  }
  .pagination {
    align-items: start;
    display: grid;
  }
}
</style>
