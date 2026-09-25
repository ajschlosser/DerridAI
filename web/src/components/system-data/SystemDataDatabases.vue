<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import { systemApi, type SystemDataDatabase, type SystemDataTable } from "../../api/system";
import { useI18nStore } from "../../stores/i18n";

type DataRow = Record<string, unknown>;

const i18n = useI18nStore();
const databases = ref<SystemDataDatabase[]>([]);
const selectedDatabase = ref("system");
const selectedTable = ref("");
const search = ref("");
const page = ref<(SystemDataTable & { rows: DataRow[]; offset: number; limit: number }) | null>(null);
const loading = ref(false);
const tableLoading = ref(false);
const error = ref("");
const tableError = ref("");
const detail = ref<DataRow | null>(null);

const database = computed(() => databases.value.find((item) => item.name === selectedDatabase.value));
const filteredTables = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  const rows = database.value?.tables || [];
  return query ? rows.filter((item) => item.name.toLocaleLowerCase().includes(query)) : rows;
});
const table = computed(() => database.value?.tables.find((item) => item.name === selectedTable.value));
const columns = computed(() => page.value?.columns || table.value?.columns || []);
const visibleColumns = computed(() => columns.value.slice(0, 6));
const totalRows = computed(() => table.value?.row_count || 0);

function t(key: string, fallback: string) { return i18n.t(key, fallback); }
function dbTitle(name: string) { return name === "auth" ? t("runtime.system_identity_access", "Identity and access") : t("runtime.system_application_data", "Application data"); }
function dbHelp(name: string) {
  return name === "auth"
    ? t("runtime.system_identity_access_help", "Sensitive identity state including users, roles or permissions, sessions, and login security.")
    : t("runtime.system_application_data_help", "Durable application information such as provider profiles, annotations, languages, and jobs.");
}
function cell(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

async function loadDatabases() {
  loading.value = true; error.value = "";
  try {
    databases.value = (await systemApi.systemData()).databases || [];
    if (!databases.value.some((item) => item.name === selectedDatabase.value)) selectedDatabase.value = databases.value[0]?.name || "";
    if (!database.value?.tables.some((item) => item.name === selectedTable.value)) selectedTable.value = database.value?.tables[0]?.name || "";
    if (selectedTable.value) await loadTable(0);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally { loading.value = false; }
}
async function loadTable(offset = 0) {
  if (!selectedDatabase.value || !selectedTable.value) return;
  tableLoading.value = true; tableError.value = ""; detail.value = null;
  try {
    page.value = await systemApi.systemDataRows(selectedDatabase.value, selectedTable.value, 25, offset);
  } catch (cause) {
    tableError.value = cause instanceof Error ? cause.message : String(cause);
  } finally { tableLoading.value = false; }
}
function chooseDatabase(name: string) {
  selectedDatabase.value = name;
  selectedTable.value = databases.value.find((item) => item.name === name)?.tables[0]?.name || "";
  search.value = "";
  void loadTable(0);
}
function chooseTable(name: string) { selectedTable.value = name; void loadTable(0); }

onMounted(() => void loadDatabases());
</script>

<template>
  <div class="databases-workspace">
    <header class="workspace-heading">
      <div>
        <h2>{{ t("runtime.system_databases", "Databases") }}</h2>
        <p>{{ t("runtime.system_databases_help", "Browse durable application and identity data. Generic editing is intentionally disabled; use purpose-built administration pages for supported changes.") }}</p>
      </div>
      <button class="btn" type="button" :disabled="loading" @click="loadDatabases"><AppIcon name="refresh" /> {{ t("common.refresh", "Refresh") }}</button>
    </header>

    <div v-if="error" class="state error" role="alert"><strong>Could not load system databases.</strong><span>{{ error }}</span></div>
    <div v-else-if="loading" class="state" role="status">Loading system databases…</div>
    <div v-else class="browser">
      <aside class="directory">
        <div class="database-switcher">
          <button v-for="item in databases" :key="item.name" type="button" :class="{ active: selectedDatabase === item.name }" @click="chooseDatabase(item.name)">
            <AppIcon :name="item.name === 'auth' ? 'lock' : 'database'" />
            <span><strong>{{ dbTitle(item.name) }}</strong><small>{{ item.name }} · {{ item.tables.length }} tables</small></span>
          </button>
        </div>
        <div class="database-description"><strong>{{ dbTitle(selectedDatabase) }}</strong><p>{{ dbHelp(selectedDatabase) }}</p></div>
        <label class="search-field"><AppIcon name="search" /><input v-model="search" type="search" :placeholder="t('runtime.system_find_table', 'Find a table')" /></label>
        <nav class="table-directory" aria-label="Database tables">
          <button v-for="item in filteredTables" :key="item.name" type="button" :class="{ active: selectedTable === item.name }" @click="chooseTable(item.name)">
            <span>{{ item.name }}</span><small>{{ item.row_count.toLocaleString() }} rows</small>
          </button>
        </nav>
      </aside>

      <section class="table-space">
        <header v-if="table" class="table-heading">
          <div><h3>{{ table.name }}</h3><p>{{ totalRows.toLocaleString() }} rows · read-only inspection</p></div>
          <span class="readonly"><AppIcon name="lock" /> Read only</span>
        </header>
        <div class="policy-note"><AppIcon name="help" /><span>Changes to users, roles, providers, languages, and other managed objects belong in their dedicated administration workspaces so validation and audit rules remain intact.</span></div>

        <div v-if="tableError" class="state error"><strong>Could not load this table.</strong><span>{{ tableError }}</span></div>
        <div v-else-if="tableLoading" class="state">Loading rows…</div>
        <div v-else-if="!page?.rows.length" class="state">This table is empty.</div>
        <template v-else>
          <div class="data-table-wrap">
            <table class="data-table">
              <thead><tr><th v-for="column in visibleColumns" :key="column.name">{{ column.name }}<span v-if="column.sensitive" class="sensitive-mark" title="Sensitive value redacted">●</span></th><th><span class="sr-only">Actions</span></th></tr></thead>
              <tbody>
                <tr v-for="(row, index) in page.rows" :key="index">
                  <td v-for="column in visibleColumns" :key="column.name" :class="{ mono: column.primary_key }"><span class="cell-value">{{ cell(row[column.name]) }}</span></td>
                  <td><button class="btn tiny" type="button" @click="detail = row">Inspect</button></td>
                </tr>
              </tbody>
            </table>
          </div>
          <footer class="pagination">
            <span>{{ page.offset + 1 }}–{{ Math.min(page.offset + page.rows.length, totalRows) }} of {{ totalRows }}</span>
            <div><button class="btn tiny" type="button" :disabled="page.offset <= 0" @click="loadTable(Math.max(0, page.offset - page.limit))">Previous</button><button class="btn tiny" type="button" :disabled="page.offset + page.rows.length >= totalRows" @click="loadTable(page.offset + page.limit)">Next</button></div>
          </footer>
        </template>
      </section>
    </div>

    <aside v-if="detail" class="detail-panel" aria-label="Row details">
      <header><div><small>{{ selectedDatabase }} / {{ selectedTable }}</small><h3>Row details</h3></div><button class="icon-btn" type="button" aria-label="Close details" @click="detail = null"><AppIcon name="close" /></button></header>
      <dl>
        <div v-for="column in columns" :key="column.name"><dt>{{ column.name }}<span v-if="column.sensitive"> · sensitive</span></dt><dd :class="{ mono: column.primary_key }">{{ cell(detail[column.name]) }}</dd></div>
      </dl>
    </aside>
  </div>
</template>

<style scoped>
.databases-workspace{display:grid;gap:16px}.workspace-heading{display:flex;justify-content:space-between;align-items:start;gap:16px}.workspace-heading h2{margin:0;font-size:1.25rem}.workspace-heading p{margin:5px 0 0;max-width:760px;color:var(--muted);line-height:1.5}.workspace-heading :deep(svg){width:16px;height:16px}.state{display:grid;gap:5px;padding:20px;border:1px solid var(--line);border-radius:12px;background:var(--soft);color:var(--muted)}.state.error{color:var(--tone-danger-fg)}.browser{display:grid;grid-template-columns:250px minmax(0,1fr);gap:16px}.directory{display:grid;align-content:start;gap:12px}.database-switcher{display:grid;gap:6px}.database-switcher button{display:grid;grid-template-columns:20px minmax(0,1fr);gap:9px;padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:inherit;text-align:left;cursor:pointer}.database-switcher button.active{border-color:var(--accent);box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 18%,transparent)}.database-switcher :deep(svg){width:17px;height:17px;margin-top:2px}.database-switcher strong,.database-switcher small{display:block}.database-switcher small{margin-top:2px;color:var(--muted)}.database-description{padding:11px;border:1px solid var(--line);border-radius:10px;background:var(--soft)}.database-description p{margin:4px 0 0;color:var(--muted);font-size:.78rem;line-height:1.45}.search-field{display:flex;gap:7px;align-items:center;padding:8px 10px;border:1px solid var(--line);border-radius:9px;background:var(--card)}.search-field :deep(svg){width:15px;height:15px;color:var(--muted)}.search-field input{min-width:0;flex:1;border:0;outline:0;background:transparent;color:inherit;font:inherit}.table-directory{display:grid;gap:3px;max-height:460px;overflow:auto}.table-directory button{display:flex;justify-content:space-between;gap:8px;padding:8px 9px;border:0;border-radius:8px;background:transparent;color:inherit;text-align:left;cursor:pointer}.table-directory button:hover,.table-directory button.active{background:var(--soft)}.table-directory small{color:var(--muted);white-space:nowrap}.table-space{min-width:0;display:grid;align-content:start;gap:12px}.table-heading{display:flex;justify-content:space-between;gap:12px;align-items:center}.table-heading h3{margin:0}.table-heading p{margin:3px 0 0;color:var(--muted);font-size:.8rem}.readonly{display:flex;gap:5px;align-items:center;padding:4px 7px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:.75rem}.readonly :deep(svg){width:13px;height:13px}.policy-note{display:flex;gap:8px;padding:10px 12px;border:1px solid var(--line);border-radius:9px;background:var(--soft);color:var(--muted);font-size:.78rem;line-height:1.45}.policy-note :deep(svg){flex:0 0 auto;width:15px;height:15px}.data-table-wrap{max-width:100%;overflow:auto;border:1px solid var(--line);border-radius:11px}.data-table{width:100%;min-width:680px;border-collapse:collapse;background:var(--card)}.data-table th,.data-table td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;font-size:.8rem;vertical-align:top}.data-table th{position:sticky;top:0;background:var(--soft);color:var(--muted);font-size:.72rem}.cell-value{display:block;max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.sensitive-mark{margin-left:5px;color:var(--tone-warn-fg)}.pagination{display:flex;justify-content:space-between;gap:10px;align-items:center;color:var(--muted);font-size:.8rem}.pagination>div{display:flex;gap:6px}.detail-panel{position:fixed;z-index:50;top:0;right:0;width:min(520px,100vw);height:100vh;overflow:auto;padding:22px;border-left:1px solid var(--line);background:var(--card);box-shadow:-16px 0 40px color-mix(in srgb,currentColor 10%,transparent)}.detail-panel header{display:flex;justify-content:space-between;gap:14px}.detail-panel h3{margin:4px 0 0}.detail-panel dl{display:grid;gap:12px}.detail-panel dt{color:var(--muted);font-size:.74rem;font-weight:700}.detail-panel dd{margin:3px 0 0;overflow-wrap:anywhere;white-space:pre-wrap}.icon-btn{display:grid;place-items:center;width:34px;height:34px;border:1px solid var(--line);border-radius:8px;background:transparent;color:inherit;cursor:pointer}.icon-btn :deep(svg){width:15px;height:15px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}@media(max-width:900px){.browser{grid-template-columns:1fr}.table-directory{max-height:220px}}@media(max-width:640px){.workspace-heading{display:grid}.pagination{align-items:start;display:grid}}
</style>
