<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppIcon from "../components/AppIcon.vue";
import {
  systemApi,
  type SystemDataDatabase,
  type SystemDataTable,
  type SystemMetadataExemplarPage,
  type SystemChromaCollection,
  type SystemChromaCommandResult,
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
const exemplarPage = ref<SystemMetadataExemplarPage>({
  exists: false,
  count: 0,
  limit: 25,
  offset: 0,
  rows: [],
  facets: { fields: [], kinds: [], languages: [], scopes: [], schemas: [] },
});
const exemplarLoading = ref(false);
const exemplarField = ref("");
const exemplarKind = ref("");
const exemplarLanguage = ref("");
const exemplarScope = ref("");
const exemplarSchema = ref("");
const exemplarRecord = ref("");
const systemChromaCollections = ref<SystemChromaCollection[]>([]);
const chromaCommand = ref("");
const chromaValidation = ref<SystemChromaCommandResult | null>(null);
const chromaResult = ref<SystemChromaCommandResult | null>(null);
const chromaBusy = ref(false);
const chromaError = ref("");

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
      "Delete all {count} cached RAG responses and saved grades? Research corpus data is not affected.",
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

function exemplarValue(value: unknown) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

async function loadExemplars(offset = 0) {
  exemplarLoading.value = true;
  try {
    exemplarPage.value = await systemApi.systemMetadataExemplars({
      limit: exemplarPage.value.limit || 25,
      offset,
      field: exemplarField.value,
      kind: exemplarKind.value,
      language: exemplarLanguage.value,
      scope_id: exemplarScope.value,
      schema_id: exemplarSchema.value,
      record_id: exemplarRecord.value.trim(),
    });
  } finally {
    exemplarLoading.value = false;
  }
}

function applyExemplarFilters() {
  void loadExemplars(0);
}

function clearExemplarFilters() {
  exemplarField.value = "";
  exemplarKind.value = "";
  exemplarLanguage.value = "";
  exemplarScope.value = "";
  exemplarSchema.value = "";
  exemplarRecord.value = "";
  void loadExemplars(0);
}

async function loadSystemChroma() {
  const payload = await systemApi.systemChromaCollections();
  systemChromaCollections.value = payload.collections || [];
  if (!chromaCommand.value && systemChromaCollections.value[0]) {
    chromaCommand.value = `get ${systemChromaCollections.value[0].name} --limit 10`;
  }
}

async function validateChromaCommand() {
  chromaBusy.value = true;
  chromaError.value = "";
  chromaResult.value = null;
  try {
    chromaValidation.value = await systemApi.validateSystemChroma(chromaCommand.value);
  } catch (cause) {
    chromaValidation.value = null;
    chromaError.value = message(cause);
  } finally {
    chromaBusy.value = false;
  }
}

async function executeChromaCommand() {
  chromaBusy.value = true;
  chromaError.value = "";
  try {
    chromaValidation.value = await systemApi.validateSystemChroma(chromaCommand.value);
    chromaResult.value = await systemApi.querySystemChroma(chromaCommand.value);
  } catch (cause) {
    chromaResult.value = null;
    chromaError.value = message(cause);
  } finally {
    chromaBusy.value = false;
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
    const [data] = await Promise.all([
      systemApi.systemData(),
      loadCache(),
      loadExemplars(0),
      loadSystemChroma(),
    ]);
    databases.value = data.databases;
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
                "Inspect progressive metadata, manage the response cache, and administer durable application databases through a safe, backend-neutral interface.",
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
                "System cache only. It is excluded from research corpora and source selection.",
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
      <section class="card exemplar-panel" aria-labelledby="metadata-exemplars-title">
        <div class="table-header">
          <div>
            <span class="eyebrow">{{ t("runtime.system_progressive_metadata", "Progressive metadata") }}</span>
            <h2 id="metadata-exemplars-title">
              {{ t("runtime.system_metadata_exemplars", "Metadata exemplars") }}
            </h2>
            <p>
              {{
                t(
                  "runtime.system_metadata_exemplars_help",
                  "Read-only, evidence-bound examples learned from reviewed metadata decisions. These are derived from canonical corpus records and can be rebuilt.",
                )
              }}
            </p>
          </div>
          <strong class="exemplar-count">{{ exemplarPage.count.toLocaleString() }}</strong>
        </div>

        <div class="exemplar-filters" role="search" :aria-label="t('runtime.system_exemplar_filters', 'Filter metadata exemplars')">
          <label>
            <span>{{ t("runtime.system_exemplar_field", "Field") }}</span>
            <select v-model="exemplarField" class="control">
              <option value="">{{ t("runtime.system_all_values", "All") }}</option>
              <option v-for="item in exemplarPage.facets.fields" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label>
            <span>{{ t("runtime.system_exemplar_kind", "Kind") }}</span>
            <select v-model="exemplarKind" class="control">
              <option value="">{{ t("runtime.system_all_values", "All") }}</option>
              <option v-for="item in exemplarPage.facets.kinds" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label>
            <span>{{ t("runtime.system_exemplar_language", "Language") }}</span>
            <select v-model="exemplarLanguage" class="control">
              <option value="">{{ t("runtime.system_all_values", "All") }}</option>
              <option v-for="item in exemplarPage.facets.languages" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label>
            <span>{{ t("runtime.system_exemplar_build", "Build") }}</span>
            <select v-model="exemplarScope" class="control">
              <option value="">{{ t("runtime.system_all_values", "All") }}</option>
              <option v-for="item in exemplarPage.facets.scopes" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label>
            <span>{{ t("runtime.system_exemplar_schema", "Schema") }}</span>
            <select v-model="exemplarSchema" class="control">
              <option value="">{{ t("runtime.system_all_values", "All") }}</option>
              <option v-for="item in exemplarPage.facets.schemas" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label class="exemplar-record-filter">
            <span>{{ t("runtime.system_exemplar_record", "Record ID") }}</span>
            <input v-model="exemplarRecord" class="control" type="search" />
          </label>
          <div class="exemplar-filter-actions">
            <button class="btn" type="button" :disabled="exemplarLoading" @click="applyExemplarFilters">
              {{ t("runtime.system_apply_filters", "Apply filters") }}
            </button>
            <button class="btn" type="button" :disabled="exemplarLoading" @click="clearExemplarFilters">
              {{ t("runtime.system_clear_filters", "Clear filters") }}
            </button>
          </div>
        </div>

        <div v-if="!exemplarPage.exists" class="info">
          {{
            t(
              "runtime.system_metadata_exemplars_not_built",
              "No progressive metadata exemplar index exists yet. Review evidence-bound metadata and run enrichment to create it.",
            )
          }}
        </div>
        <div v-else-if="exemplarLoading" class="info">
          {{ t("runtime.system_metadata_exemplars_loading", "Loading metadata exemplars…") }}
        </div>
        <div v-else-if="!exemplarPage.rows.length" class="info">
          {{ t("runtime.system_no_rows", "No rows are available.") }}
        </div>
        <div v-else class="exemplar-list">
          <article v-for="item in exemplarPage.rows" :key="item.exemplar_id" class="exemplar-card">
            <header>
              <div>
                <span class="exemplar-field">{{ item.field_name }}</span>
                <strong>{{ exemplarValue(item.field_value) }}</strong>
              </div>
              <div class="exemplar-badges">
                <span>{{ item.kind }}</span>
                <span v-if="item.assertion_status">{{ item.assertion_status }}</span>
                <span v-if="item.language">{{ item.language }}</span>
              </div>
            </header>
            <dl class="exemplar-provenance">
              <div>
                <dt>{{ t("runtime.system_exemplar_record", "Record") }}</dt>
                <dd>{{ item.record_id }}<template v-if="item.record_revision"> · r{{ item.record_revision }}</template></dd>
              </div>
              <div>
                <dt>{{ t("runtime.system_exemplar_build", "Build") }}</dt>
                <dd>{{ item.scope_id || "—" }}</dd>
              </div>
              <div>
                <dt>{{ t("runtime.system_exemplar_schema", "Schema") }}</dt>
                <dd>{{ item.schema_id || "—" }}<template v-if="item.schema_version"> · {{ item.schema_version }}</template></dd>
              </div>
              <div>
                <dt>{{ t("runtime.system_exemplar_region", "Region") }}</dt>
                <dd>{{ item.region_type || "—" }}</dd>
              </div>
              <div>
                <dt>{{ t("runtime.system_exemplar_evidence_blocks", "Evidence blocks") }}</dt>
                <dd>{{ (item.evidence_block_ids || []).join(", ") || "—" }}</dd>
              </div>
              <div>
                <dt>{{ t("runtime.system_exemplar_evidence_hash", "Evidence hash") }}</dt>
                <dd class="mono">{{ item.evidence_hash || "—" }}</dd>
              </div>
            </dl>
            <details class="exemplar-context">
              <summary>{{ t("runtime.system_exemplar_context", "Evidence context") }}</summary>
              <p>{{ item.context_text || "—" }}</p>
            </details>
          </article>
        </div>

        <footer class="exemplar-pagination">
          <span>
            {{
              i18n.tf(
                "runtime.system_exemplar_range",
                "{start}–{end} of {count}",
                {
                  start: exemplarPage.count ? exemplarPage.offset + 1 : 0,
                  end: Math.min(exemplarPage.offset + exemplarPage.rows.length, exemplarPage.count),
                  count: exemplarPage.count,
                },
              )
            }}
          </span>
          <div>
            <button
              class="btn tiny"
              type="button"
              :disabled="exemplarLoading || exemplarPage.offset <= 0"
              @click="loadExemplars(Math.max(0, exemplarPage.offset - exemplarPage.limit))"
            >
              {{ t("common.previous", "Previous") }}
            </button>
            <button
              class="btn tiny"
              type="button"
              :disabled="exemplarLoading || exemplarPage.offset + exemplarPage.limit >= exemplarPage.count"
              @click="loadExemplars(exemplarPage.offset + exemplarPage.limit)"
            >
              {{ t("common.next", "Next") }}
            </button>
          </div>
        </footer>
      </section>
      <section class="card chroma-console" aria-labelledby="system-chroma-console-title">
        <div class="table-header">
          <div>
            <span class="eyebrow">{{ t("runtime.system_chroma", "System Chroma") }}</span>
            <h2 id="system-chroma-console-title">{{ t("runtime.system_chroma_console", "Read-only query console") }}</h2>
            <p>
              {{
                t(
                  "runtime.system_chroma_console_help",
                  "Inspect internal vector projections with CLI-style get and query commands. Commands are parsed and validated server-side before execution; no mutation commands are accepted.",
                )
              }}
            </p>
          </div>
          <div class="chroma-collection-summary">
            <span v-for="item in systemChromaCollections" :key="item.name">
              <b>{{ item.name }}</b> · {{ item.count.toLocaleString() }}
            </span>
          </div>
        </div>
        <label class="console-command">
          <span>{{ t("runtime.system_chroma_command", "Command") }}</span>
          <textarea
            v-model="chromaCommand"
            class="control mono"
            rows="3"
            spellcheck="false"
            placeholder='query derridai_metadata_exemplars --text "responsibility to the Other" --n-results 8 --where "{"field_name":"position_holder"}"'
            @input="
              chromaValidation = null;
              chromaResult = null;
              chromaError = '';
            "
          />
        </label>
        <div class="console-help">
          <code>get COLLECTION --where '{"field_name":"speaker"}' --limit 20</code>
          <code>query COLLECTION --text "passage" --n-results 8 --where-document '{"$contains":"Levinas"}'</code>
        </div>
        <div class="schema-actions">
          <button class="btn" type="button" :disabled="chromaBusy || !chromaCommand.trim()" @click="validateChromaCommand">
            {{ t("runtime.system_chroma_validate", "Validate & explain") }}
          </button>
          <button class="btn primary" type="button" :disabled="chromaBusy || !chromaCommand.trim()" @click="executeChromaCommand">
            {{ t("runtime.system_chroma_execute", "Execute query") }}
          </button>
        </div>
        <p v-if="chromaError" class="info error" role="alert">{{ chromaError }}</p>
        <div v-if="chromaValidation" class="query-explanation" role="status">
          <b>{{ t("runtime.system_chroma_will_do", "What this will do") }}</b>
          <p>{{ chromaValidation.explanation }}</p>
          <small>
            {{ chromaValidation.embedding_provider || "—" }}
            <template v-if="chromaValidation.embedding_model"> · {{ chromaValidation.embedding_model }}</template>
          </small>
        </div>
        <details v-if="chromaResult?.result" class="query-result" open>
          <summary>{{ t("runtime.system_chroma_result", "Query result") }}</summary>
          <pre>{{ JSON.stringify(chromaResult.result, null, 2) }}</pre>
        </details>
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
.chroma-console {
  display: grid;
  gap: 14px;
}
.chroma-collection-summary {
  display: grid;
  gap: 4px;
  max-width: 42rem;
  font-size: 0.78rem;
  color: var(--muted);
  text-align: end;
}
.console-command {
  display: grid;
  gap: 6px;
  font-size: 0.8rem;
  font-weight: 750;
}
.console-command textarea {
  min-height: 84px;
  resize: vertical;
  font-family: var(--mono, ui-monospace, SFMono-Regular, Menlo, monospace);
}
.console-help {
  display: grid;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
  overflow-x: auto;
}
.console-help code {
  white-space: nowrap;
  font-size: 0.78rem;
}
.query-explanation {
  padding: 12px 14px;
  border-inline-start: 4px solid var(--accent);
  border-radius: 8px;
  background: var(--soft);
}
.query-explanation p {
  margin: 4px 0;
  line-height: 1.5;
}
.query-explanation small {
  color: var(--muted);
}
.query-result pre {
  max-height: 34rem;
  overflow: auto;
  padding: 12px;
  border-radius: 8px;
  background: var(--soft);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 0.76rem;
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
.exemplar-panel {
  display: grid;
  gap: 14px;
}
.exemplar-count {
  font-size: 1.8rem;
}
.exemplar-filters {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 10px;
  align-items: end;
}
.exemplar-filters label {
  display: grid;
  gap: 5px;
  color: var(--muted);
  font-size: 0.8rem;
  font-weight: 700;
}
.exemplar-record-filter {
  grid-column: span 2;
}
.exemplar-filter-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.exemplar-list {
  display: grid;
  gap: 10px;
}
.exemplar-card {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.exemplar-card > header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}
.exemplar-card > header > div:first-child {
  display: grid;
  gap: 4px;
}
.exemplar-field {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.exemplar-badges {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.exemplar-badges span {
  padding: 3px 7px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--card);
  font-size: 0.75rem;
}
.exemplar-provenance {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px 14px;
  margin: 0;
}
.exemplar-provenance div {
  min-width: 0;
}
.exemplar-provenance dt {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 700;
}
.exemplar-provenance dd {
  margin: 2px 0 0;
  overflow-wrap: anywhere;
  font-size: 0.82rem;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.exemplar-context summary {
  cursor: pointer;
  font-weight: 700;
}
.exemplar-context p {
  margin: 8px 0 0;
  white-space: pre-wrap;
  line-height: 1.5;
}
.exemplar-pagination {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}
.exemplar-pagination > div {
  display: flex;
  gap: 6px;
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
  .editor-grid,
  .exemplar-filters,
  .exemplar-provenance {
    grid-template-columns: 1fr;
  }
  .exemplar-record-filter {
    grid-column: auto;
  }
  .page-header,
  .cache-summary,
  .table-header {
    display: grid;
  }
}
</style>
