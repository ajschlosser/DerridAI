<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppIcon from "../AppIcon.vue";
import {
  systemApi,
  type SystemResponseCachePage,
} from "../../api/system";
import * as runtime from "../../runtime/runtimeBridge";
import { useI18nStore } from "../../stores/i18n";

type DataRow = Record<string, unknown>;

const router = useRouter();
const i18n = useI18nStore();
const page = ref<SystemResponseCachePage>({
  exists: true,
  records: [],
  total: 0,
  limit: 25,
  offset: 0,
});
const loading = ref(false);
const error = ref("");
const query = ref("");

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}
function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  return typeof value === "string" ? value : JSON.stringify(value);
}
function formatDate(value: unknown) {
  return value ? runtime.formatTimestamp(String(value)) : "—";
}
function provider(record: DataRow) {
  return String(
    record.provider_model ||
      record.model ||
      record.generation_model ||
      record.provider ||
      record.generation_provider ||
      "—",
  );
}
function grade(record: DataRow) {
  const value = record.grade ?? record.grade_status ?? record.grades;
  if (Array.isArray(value)) {
    return value.length
      ? i18n.tf("runtime.system_saved_grades", "{count} saved", { count: value.length })
      : t("runtime.system_not_graded", "Not graded");
  }
  return value ? String(value) : t("runtime.system_not_graded", "Not graded");
}

async function load(offset = 0) {
  loading.value = true;
  error.value = "";
  try {
    page.value = await systemApi.responseCacheRecords(page.value.limit || 25, offset, query.value);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    loading.value = false;
  }
}

async function remove(record: DataRow) {
  const id = String(record.record_id || record.id || "");
  if (!id) return;
  const approved = await runtime.openMessageModal({
    title: t("runtime.system_delete_response", "Delete saved response?"),
    message: String(record.question || id),
    tone: "danger",
    confirmLabel: t("runtime.system_delete_response_confirm", "Delete response"),
    cancelLabel: t("common.cancel", "Cancel"),
  });
  if (!approved) return;
  try {
    await systemApi.deleteSystemResponseCacheRecord(id);
    const offset =
      page.value.records.length === 1 && page.value.offset > 0
        ? Math.max(0, page.value.offset - page.value.limit)
        : page.value.offset;
    await load(offset);
    runtime.notifyToast(t("runtime.system_response_deleted", "Saved response deleted."));
  } catch (cause) {
    runtime.notifyToast(cause instanceof Error ? cause.message : String(cause), { tone: "danger" });
  }
}

async function clearAll() {
  const approved = await runtime.openMessageModal({
    title: t("runtime.help.clear_rag_response_cache", "Clear saved responses?"),
    message: i18n.tf(
      "runtime.help.clear_rag_response_cache_message",
      "Delete all {count} saved research responses and their saved grades? Research corpus data is not affected.",
      { count: Number(page.value.total || 0).toLocaleString() },
    ),
    tone: "danger",
    confirmLabel: t("runtime.system_clear_response_cache", "Clear saved responses"),
    cancelLabel: t("common.cancel", "Cancel"),
  });
  if (!approved) return;
  try {
    await systemApi.clearResponseCache();
    await load(0);
    runtime.notifyToast(t("runtime.response_cache_cleared", "Saved responses cleared."));
  } catch (cause) {
    runtime.notifyToast(cause instanceof Error ? cause.message : String(cause), { tone: "danger" });
  }
}

onMounted(() => void load(0));
</script>

<template>
  <div class="responses-workspace">
    <header class="workspace-heading">
      <div>
        <h2>{{ t("runtime.system_saved_responses", "Saved responses") }}</h2>
        <p>
          {{
            t(
              "runtime.help.system_cache_only",
              "Generated research responses and grades. This operational history is not a corpus or research source.",
            )
          }}
        </p>
      </div>
      <div class="heading-actions">
        <button class="btn" type="button" @click="router.push('/faq')">
          {{ t("runtime.help.open_response_library", "Open Response Library") }}
        </button>
        <details v-if="page.total > 0" class="maintenance-menu">
          <summary class="btn">{{ t("runtime.system_maintenance", "Maintenance") }}</summary>
          <button type="button" @click="clearAll">
            <AppIcon name="trash" /> {{ t("runtime.system_clear_response_cache", "Clear saved responses") }}
          </button>
        </details>
      </div>
    </header>

    <form class="toolbar" role="search" @submit.prevent="load(0)">
      <label class="search-field">
        <span class="sr-only">{{ t("runtime.system_search_responses", "Search saved responses") }}</span>
        <AppIcon name="search" />
        <input
          v-model="query"
          type="search"
          :placeholder="t('runtime.system_search_responses', 'Search questions and responses')"
        />
      </label>
      <button class="btn" type="submit" :disabled="loading">{{ t("common.search", "Search") }}</button>
      <button v-if="query" class="btn" type="button" :disabled="loading" @click="query = ''; load(0)">
        {{ t("common.clear", "Clear") }}
      </button>
    </form>

    <div v-if="error" class="state error" role="alert">
      <strong>{{ t("runtime.system_responses_failed", "Could not load saved responses.") }}</strong>
      <span>{{ error }}</span>
      <button class="btn tiny" type="button" @click="load(page.offset)">{{ t("common.retry", "Retry") }}</button>
    </div>
    <div v-else-if="loading" class="state" role="status">
      {{ t("runtime.system_responses_loading", "Loading saved responses…") }}
    </div>
    <div v-else-if="page.exists === false" class="state">
      {{ t("runtime.system_responses_absent", "The response cache has not been created yet.") }}
    </div>
    <div v-else-if="page.total === 0 && !query" class="state">
      {{ t("runtime.system_responses_empty", "No saved responses yet.") }}
    </div>
    <div v-else-if="page.records.length === 0" class="state">
      {{ t("runtime.system_responses_no_matches", "No saved responses match this search.") }}
    </div>

    <template v-else>
      <div class="result-summary">
        {{
          i18n.tf(
            "runtime.system_response_range",
            "{start}–{end} of {total} saved responses",
            {
              start: page.offset + 1,
              end: Math.min(page.offset + page.records.length, page.total),
              total: page.total.toLocaleString(),
            },
          )
        }}
      </div>
      <div class="data-table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t("runtime.system_question", "Question") }}</th>
              <th>{{ t("runtime.system_created", "Created") }}</th>
              <th>{{ t("runtime.system_provider_model", "Provider / model") }}</th>
              <th>{{ t("runtime.system_grade", "Grade") }}</th>
              <th><span class="sr-only">{{ t("common.actions", "Actions") }}</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in page.records" :key="String(record.record_id || record.id)">
              <td class="question-cell">{{ formatValue(record.question) }}</td>
              <td>{{ formatDate(record.created_at || record.timestamp) }}</td>
              <td>{{ provider(record) }}</td>
              <td><span class="status-pill">{{ grade(record) }}</span></td>
              <td class="row-actions">
                <button class="btn tiny" type="button" @click="router.push('/faq')">
                  {{ t("runtime.system_library", "Library") }}
                </button>
                <button
                  class="icon-btn danger-text"
                  type="button"
                  :aria-label="t('runtime.system_delete_response_confirm', 'Delete response')"
                  @click="remove(record)"
                >
                  <AppIcon name="trash" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <footer class="pagination">
        <button
          class="btn tiny"
          type="button"
          :disabled="loading || page.offset <= 0"
          @click="load(Math.max(0, page.offset - page.limit))"
        >
          {{ t("common.previous", "Previous") }}
        </button>
        <button
          class="btn tiny"
          type="button"
          :disabled="loading || page.offset + page.records.length >= page.total"
          @click="load(page.offset + page.limit)"
        >
          {{ t("common.next", "Next") }}
        </button>
      </footer>
    </template>
  </div>
</template>

<style scoped>
.responses-workspace { display: grid; gap: 16px; }
.workspace-heading { display: flex; justify-content: space-between; align-items: start; gap: 16px; }
.workspace-heading h2 { margin: 0; font-size: 1.25rem; }
.workspace-heading p { margin: 5px 0 0; color: var(--muted); line-height: 1.5; max-width: 720px; }
.heading-actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.maintenance-menu { position: relative; }
.maintenance-menu summary { list-style: none; cursor: pointer; }
.maintenance-menu summary::-webkit-details-marker { display: none; }
.maintenance-menu button {
  position: absolute;
  z-index: 5;
  right: 0;
  top: calc(100% + 6px);
  display: flex;
  gap: 8px;
  align-items: center;
  min-width: 210px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
  color: var(--tone-danger-fg);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 8px 28px color-mix(in srgb, currentColor 12%, transparent);
}
.maintenance-menu :deep(svg) { width: 16px; height: 16px; }
.toolbar { display: flex; gap: 8px; align-items: center; }
.search-field {
  display: flex;
  gap: 8px;
  align-items: center;
  min-width: min(440px, 100%);
  padding: 8px 11px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
}
.search-field :deep(svg) { width: 17px; height: 17px; color: var(--muted); }
.search-field input { min-width: 0; flex: 1; border: 0; outline: 0; background: transparent; color: inherit; font: inherit; }
.state { display: grid; gap: 6px; justify-items: start; padding: 22px; border: 1px solid var(--line); border-radius: 12px; background: var(--soft); color: var(--muted); }
.state.error { color: var(--tone-danger-fg); }
.result-summary { color: var(--muted); font-size: .82rem; }
.data-table-wrap { max-width: 100%; overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; }
.data-table { width: 100%; min-width: 760px; border-collapse: collapse; background: var(--card); }
.data-table th, .data-table td { padding: 11px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: .84rem; }
.data-table th { background: var(--soft); color: var(--muted); font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; }
.data-table tbody tr:last-child td { border-bottom: 0; }
.question-cell { min-width: 260px; font-weight: 650; line-height: 1.4; }
.status-pill { display: inline-flex; padding: 3px 7px; border: 1px solid var(--line); border-radius: 999px; font-size: .75rem; white-space: nowrap; }
.row-actions { display: flex; justify-content: flex-end; gap: 6px; }
.icon-btn { display: grid; place-items: center; width: 32px; height: 32px; border: 1px solid var(--line); border-radius: 8px; background: transparent; color: inherit; cursor: pointer; }
.icon-btn :deep(svg) { width: 15px; height: 15px; }
.danger-text { color: var(--tone-danger-fg); }
.pagination { display: flex; justify-content: flex-end; gap: 6px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
@media (max-width: 700px) {
  .workspace-heading, .toolbar { display: grid; }
  .heading-actions { justify-content: start; }
  .search-field { min-width: 0; }
}
</style>
