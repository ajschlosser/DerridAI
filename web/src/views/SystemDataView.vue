<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppIcon from "../components/AppIcon.vue";
import {
  systemApi,
  type SystemDataDatabase,
  type SystemDataTable,
  type SystemVectorStore,
} from "../api/system";
import * as runtime from "../runtime/runtimeBridge";
import { useI18nStore } from "../stores/i18n";

type DataRow = Record<string, unknown>;

const i18n = useI18nStore();
const router = useRouter();
const loading = ref(true);
const error = ref("");
const databases = ref<SystemDataDatabase[]>([]);
const selectedDatabase = ref("");
const selectedTable = ref("");
const tablePayload = ref<(SystemDataTable & { rows: DataRow[] }) | null>(null);
const newRow = ref("{}");
const editRow = ref("{}");
const editKey = ref("{}");
const editingIndex = ref(-1);
const saving = ref(false);
const cachePayload = ref<{
  total?: number;
  exists?: boolean;
  records?: Array<Record<string, unknown>>;
}>({});
const vectorStores = ref<SystemVectorStore[]>([]);

const database = computed(() =>
  databases.value.find((item) => item.name === selectedDatabase.value),
);
const table = computed(() =>
  database.value?.tables.find((item) => item.name === selectedTable.value),
);
const rows = computed(() => tablePayload.value?.rows || []);
const primaryKeys = computed(() =>
  (table.value?.columns || []).filter((column) => column.primary_key),
);

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}

function message(errorValue: unknown) {
  return errorValue instanceof Error ? errorValue.message : String(errorValue);
}

async function loadCache() {
  const response = await fetch("/api/response-cache/records?limit=100&offset=0");
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`.trim());
  cachePayload.value = (await response.json()) as typeof cachePayload.value;
}

async function deleteCacheRecord(record: Record<string, unknown>) {
  const recordId = String(record.record_id || "");
  if (!recordId) return;
  const approved = await runtime.openMessageModal({
    title: t("runtime.system_delete_row", "Delete row"),
    message: String(record.question || recordId),
    tone: "danger",
    confirmLabel: t("runtime.system_delete_row", "Delete row"),
    cancelLabel: t("common.cancel", "Cancel"),
  });
  if (!approved) return;
  try {
    await systemApi.deleteSystemResponseCacheRecord(recordId);
    await loadCache();
    runtime.notifyToast(t("runtime.system_row_deleted", "System data row deleted."));
  } catch (cause) {
    runtime.notifyToast(message(cause), { tone: "danger" });
  }
}

async function clearCache() {
  const approved = await runtime.openMessageModal({
    title: t("runtime.help.clear_rag_response_cache", "Clear RAG response cache?"),
    message: i18n.tf(
      "runtime.help.clear_rag_response_cache_message",
      "Delete all {count} cached RAG responses and saved grades? Corpus vector databases are not affected.",
      { count: Number(cachePayload.value.total || 0).toLocaleString() },
    ),
    tone: "danger",
    confirmLabel: t("runtime.system_clear_response_cache", "Clear response cache"),
    cancelLabel: t("common.cancel", "Cancel"),
  });
  if (!approved) return;
  try {
    const response = await fetch("/api/stores/_response_cache", { method: "DELETE" });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`.trim());
    await loadCache();
    runtime.notifyToast(t("runtime.response_cache_cleared", "Response cache cleared"));
  } catch (cause) {
    runtime.notifyToast(message(cause), { tone: "danger" });
  }
}

async function clearMetadataMemory() {
  const approved = await runtime.openMessageModal({
    title: t("runtime.system_clear_memory", "Clear semantic reviewer memory?"),
    message: t(
      "runtime.system_clear_memory_help",
      "This removes derived similarity/MMR suggestions. It does not change corpus records or confirmed decisions.",
    ),
    tone: "danger",
    confirmLabel: t("common.clear", "Clear"),
    cancelLabel: t("common.cancel", "Cancel"),
  });
  if (!approved) return;
  try {
    await systemApi.clearSystemMetadataMemory();
    await load();
    runtime.notifyToast(t("runtime.system_memory_cleared", "Semantic reviewer memory cleared."));
  } catch (cause) {
    runtime.notifyToast(message(cause), { tone: "danger" });
  }
}

async function loadTable() {
  if (!selectedDatabase.value || !selectedTable.value) {
    tablePayload.value = null;
    return;
  }
  tablePayload.value = await systemApi.systemDataRows(selectedDatabase.value, selectedTable.value);
  editRow.value = "{}";
  editKey.value = "{}";
  editingIndex.value = -1;
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [data, vectors] = await Promise.all([
      systemApi.systemData(),
      systemApi.systemVectorStores(),
      loadCache(),
    ]);
    databases.value = data.databases;
    vectorStores.value = vectors.stores;
    if (!database.value) selectedDatabase.value = databases.value[0]?.name || "";
    const firstTable = databases.value.find((item) => item.name === selectedDatabase.value)
      ?.tables[0];
    if (
      !selectedTable.value ||
      !database.value?.tables.some((item) => item.name === selectedTable.value)
    )
      selectedTable.value = firstTable?.name || "";
    await loadTable();
  } catch (cause) {
    error.value = message(cause);
  } finally {
    loading.value = false;
  }
}

function parseObject(value: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

async function addRow() {
  const values = parseObject(newRow.value);
  if (!values) {
    runtime.notifyToast(t("runtime.system_invalid_json", "Enter a valid JSON object."), {
      tone: "danger",
    });
    return;
  }
  await persist(() =>
    systemApi.insertSystemDataRow(selectedDatabase.value, selectedTable.value, values),
  );
  newRow.value = "{}";
}

function startEdit(row: DataRow, index: number) {
  editingIndex.value = index;
  const editable = Object.fromEntries(
    Object.entries(row).filter(
      ([name]) => !table.value?.columns.find((column) => column.name === name)?.sensitive,
    ),
  );
  editRow.value = JSON.stringify(editable, null, 2);
  const key = Object.fromEntries(
    primaryKeys.value.map((column) => [column.name, row[column.name]]),
  );
  editKey.value = JSON.stringify(key, null, 2);
}

async function saveRow() {
  const key = parseObject(editKey.value);
  const values = parseObject(editRow.value);
  if (!key || !values) {
    runtime.notifyToast(t("runtime.system_invalid_json", "Enter a valid JSON object."), {
      tone: "danger",
    });
    return;
  }
  await persist(() =>
    systemApi.updateSystemDataRow(selectedDatabase.value, selectedTable.value, key, values),
  );
  editingIndex.value = -1;
}

async function deleteRow(row: DataRow) {
  const key = Object.fromEntries(
    primaryKeys.value.map((column) => [column.name, row[column.name]]),
  );
  if (!Object.keys(key).length) return;
  const approved = await runtime.openMessageModal({
    title: t("runtime.system_delete_row", "Delete row"),
    message: JSON.stringify(key),
    tone: "danger",
    confirmLabel: t("runtime.system_delete_row", "Delete row"),
    cancelLabel: t("common.cancel", "Cancel"),
  });
  if (approved)
    await persist(() =>
      systemApi.deleteSystemDataRow(selectedDatabase.value, selectedTable.value, key),
    );
}

async function persist(action: () => Promise<unknown>) {
  if (!table.value?.writable) {
    runtime.notifyToast(t("runtime.system_read_only", "This table is read-only."), {
      tone: "danger",
    });
    return;
  }
  saving.value = true;
  try {
    await action();
    await Promise.all([loadTable(), loadCache()]);
    runtime.notifyToast(t("runtime.system_row_saved", "System data row saved."));
  } catch (cause) {
    runtime.notifyToast(message(cause), { tone: "danger" });
  } finally {
    saving.value = false;
  }
}

onMounted(() => void load());
</script>

<template>
  <main id="main" class="runtime-surface" aria-live="polite">
    <div v-if="loading" class="info">
      {{ t("runtime.loading_response_cache", "Loading system data") }}
    </div>
    <div v-else-if="error" class="info error">
      <b>{{ t("runtime.help.could_not_read_response_cache", "Could not read system data.") }}</b>
      <span>{{ error }}</span>
    </div>
    <div v-else class="system-data-page">
      <header class="page-header">
        <div>
          <span class="eyebrow">{{ t("runtime.system_data", "System Data") }}</span>
          <h1>{{ t("runtime.system_data", "System Data") }}</h1>
          <p>
            {{
              t(
                "runtime.system_data_help",
                "Manage the response cache and durable application databases through a safe, backend-neutral interface.",
              )
            }}
          </p>
        </div>
        <button class="btn" type="button" @click="load">
          <AppIcon name="refresh" /> {{ t("runtime.system_refresh", "Refresh data") }}
        </button>
      </header>

      <section class="card cache-summary" aria-labelledby="cache-title">
        <div>
          <b id="cache-title">{{ t("runtime.help.rag_response_cache", "RAG response cache") }}</b>
          <p>
            {{
              t(
                "runtime.help.system_cache_only",
                "System cache only. This collection is excluded from corpus stores and source selection.",
              )
            }}
          </p>
        </div>
        <div class="cache-actions">
          <strong>{{ Number(cachePayload.total || 0).toLocaleString() }}</strong>
          <button class="btn" type="button" @click="router.push('/faq')">
            {{ t("runtime.help.open_response_library", "Open Response Library") }}
          </button>
          <button
            v-if="Number(cachePayload.total || 0) > 0"
            class="btn danger"
            type="button"
            @click="clearCache"
          >
            {{ t("runtime.system_clear_response_cache", "Clear response cache") }}
          </button>
        </div>
      </section>
      <section class="card" aria-labelledby="vector-stores-title">
        <div class="table-header">
          <div>
            <h2 id="vector-stores-title">
              {{ t("runtime.system_vector_stores", "Derived vector stores") }}
            </h2>
            <p>
              {{
                t(
                  "runtime.system_vector_stores_help",
                  "Rebuildable system collections used for response caching and semantic reviewer memory.",
                )
              }}
            </p>
          </div>
        </div>
        <div class="tablewrap">
          <table>
            <thead>
              <tr>
                <th>{{ t("runtime.system_store_name", "Store") }}</th>
                <th>{{ t("runtime.system_store_role", "Role") }}</th>
                <th>{{ t("runtime.system_store_count", "Records") }}</th>
                <th>{{ t("runtime.system_store_embedding", "Embedding contract") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in vectorStores" :key="item.name">
                <td>
                  <b>{{ item.name }}</b
                  ><small v-if="item.storage_name"> · {{ item.storage_name }}</small>
                </td>
                <td>
                  {{ item.metadata?.derridai_system_collection || item.collection_role || "" }}
                </td>
                <td>{{ Number(item.count || 0).toLocaleString() }}</td>
                <td>
                  {{ item.embedding_provider || "—" }} · {{ item.embedding_model || "—" }} ·
                  {{ item.embedding_dimension || "?" }}d · {{ item.distance_metric || "—" }}
                  <button
                    v-if="item.metadata?.derridai_system_collection === 'metadata_memory'"
                    class="btn tiny danger"
                    type="button"
                    @click="clearMetadataMemory"
                  >
                    {{ t("runtime.system_clear_memory", "Clear memory") }}
                  </button>
                </td>
              </tr>
              <tr v-if="!vectorStores.length">
                <td colspan="4" class="note">
                  {{ t("runtime.system_no_rows", "No rows are available.") }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
      <section class="card" aria-labelledby="cache-records-title">
        <div class="table-header">
          <div>
            <h2 id="cache-records-title">
              {{ t("runtime.system_cache_records", "Response cache records") }}
            </h2>
            <p>{{ t("runtime.system_cache_records_help", "Latest response-cache entries.") }}</p>
          </div>
        </div>
        <div class="tablewrap">
          <table>
            <thead>
              <tr>
                <th>{{ t("runtime.system_created", "Created") }}</th>
                <th>{{ t("runtime.system_question", "Question") }}</th>
                <th>{{ t("runtime.system_generation", "Generation") }}</th>
                <th>{{ t("runtime.system_actions", "Actions") }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in cachePayload.records || []" :key="String(record.record_id)">
                <td>{{ runtime.formatTimestamp(String(record.created_at || "")) }}</td>
                <td>{{ String(record.question || "") }}</td>
                <td>{{ String(record.provider || "") }} · {{ String(record.model || "") }}</td>
                <td>
                  <button class="btn tiny danger" type="button" @click="deleteCacheRecord(record)">
                    {{ t("runtime.system_delete_row", "Delete row") }}
                  </button>
                </td>
              </tr>
              <tr v-if="!(cachePayload.records || []).length">
                <td colspan="4" class="note">
                  {{ t("runtime.system_no_rows", "No rows are available.") }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="data-grid">
        <aside class="card database-list" aria-labelledby="database-title">
          <h2 id="database-title">{{ t("runtime.system_databases", "System databases") }}</h2>
          <button
            v-for="item in databases"
            :key="item.name"
            class="database-button"
            :class="{ active: item.name === selectedDatabase }"
            type="button"
            @click="
              selectedDatabase = item.name;
              selectedTable = item.tables[0]?.name || '';
              loadTable();
            "
          >
            <b>{{ item.name }}</b>
            <small
              >{{ item.backend }} · {{ item.tables.length }}
              {{ t("runtime.system_table", "table") }}</small
            >
          </button>
        </aside>

        <section class="card table-panel" aria-labelledby="table-title">
          <div v-if="!table">
            <h2 id="table-title">{{ t("runtime.system_table", "Table") }}</h2>
            <p>{{ t("runtime.system_select_table", "Select a table to inspect its rows.") }}</p>
          </div>
          <template v-else>
            <header class="table-header">
              <div>
                <span class="eyebrow">{{ selectedDatabase }}</span>
                <h2 id="table-title">{{ selectedTable }}</h2>
                <p>{{ table.row_count.toLocaleString() }} {{ t("runtime.system_rows", "Rows") }}</p>
              </div>
              <span v-if="!table.writable" class="readonly">{{
                t("runtime.system_read_only", "This table is read-only.")
              }}</span>
            </header>
            <div class="table-tabs" role="tablist" :aria-label="t('runtime.system_table', 'Table')">
              <button
                v-for="item in database?.tables"
                :key="item.name"
                class="btn tiny"
                :class="{ primary: item.name === selectedTable }"
                type="button"
                @click="
                  selectedTable = item.name;
                  loadTable();
                "
              >
                {{ item.name }}
              </button>
            </div>
            <div v-if="table.writable" class="editor-grid">
              <label>
                {{ t("runtime.system_new_row", "New row JSON") }}
                <textarea v-model="newRow" rows="5" spellcheck="false" />
                <button class="btn" type="button" :disabled="saving" @click="addRow">
                  {{ t("runtime.system_add_row", "Add row") }}
                </button>
              </label>
              <label v-if="editingIndex >= 0">
                {{ t("runtime.system_edit_row", "Edit row JSON") }}
                <textarea v-model="editRow" rows="5" spellcheck="false" />
                <small>{{ t("runtime.system_row_key", "Row key JSON") }}: {{ editKey }}</small>
                <button class="btn primary" type="button" :disabled="saving" @click="saveRow">
                  {{ t("runtime.system_save_row", "Save row") }}
                </button>
              </label>
            </div>
            <div class="tablewrap">
              <table>
                <thead>
                  <tr>
                    <th v-for="column in table.columns" :key="column.name">{{ column.name }}</th>
                    <th>{{ t("runtime.system_table", "Actions") }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, index) in rows" :key="index">
                    <td v-for="column in table.columns" :key="column.name">
                      {{
                        column.sensitive
                          ? t("runtime.system_redacted", "[redacted]")
                          : String(row[column.name] ?? "")
                      }}
                    </td>
                    <td class="row-actions">
                      <button
                        v-if="table.writable && primaryKeys.length"
                        class="btn tiny"
                        type="button"
                        @click="startEdit(row, index)"
                      >
                        {{ t("runtime.system_save_row", "Edit") }}
                      </button>
                      <button
                        v-if="table.writable && primaryKeys.length"
                        class="btn tiny danger"
                        type="button"
                        @click="deleteRow(row)"
                      >
                        {{ t("runtime.system_delete_row", "Delete row") }}
                      </button>
                    </td>
                  </tr>
                  <tr v-if="!rows.length">
                    <td :colspan="table.columns.length + 1" class="note">
                      {{ t("runtime.system_no_tables", "No rows are available.") }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </section>
      </section>
    </div>
  </main>
</template>

<style scoped>
.system-data-page {
  display: grid;
  gap: 16px;
}
.page-header,
.cache-summary,
.table-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}
.page-header h1 {
  margin: 4px 0;
  font-size: 1.4rem;
}
.page-header p,
.cache-summary p,
.table-header p {
  margin: 4px 0;
  color: var(--muted);
  line-height: 1.5;
}
.eyebrow {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.cache-summary strong {
  font-size: 1.8rem;
}
.cache-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.data-grid {
  display: grid;
  grid-template-columns: minmax(190px, 0.35fr) minmax(0, 1fr);
  gap: 16px;
}
.database-list {
  display: grid;
  align-content: start;
  gap: 8px;
}
.database-list h2,
.table-panel h2 {
  margin: 0 0 8px;
  font-size: 1rem;
}
.database-button {
  display: grid;
  gap: 3px;
  text-align: start;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--soft);
  color: inherit;
  cursor: pointer;
}
.database-button.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 25%, transparent);
}
.database-button small {
  color: var(--muted);
}
.table-panel {
  min-width: 0;
}
.readonly {
  color: var(--tone-warn-fg);
  font-size: 0.8rem;
  font-weight: 700;
}
.table-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin: 12px 0;
}
.editor-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 12px 0;
}
.editor-grid label {
  display: grid;
  gap: 6px;
  color: var(--muted);
  font-size: 0.8rem;
  font-weight: 700;
}
.editor-grid textarea {
  width: 100%;
  resize: vertical;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  color: inherit;
  font: inherit;
  font-weight: 400;
}
.row-actions {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}
@media (max-width: 800px) {
  .data-grid,
  .editor-grid {
    grid-template-columns: 1fr;
  }
  .page-header,
  .cache-summary,
  .table-header {
    display: grid;
  }
}
</style>
