<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppIcon from "../components/AppIcon.vue";
import * as runtime from "../runtime/runtimeBridge";
import { useI18nStore } from "../stores/i18n";

type CacheRecord = {
  created_at?: string;
  question?: string;
  provider?: string;
  model?: string;
  evidence_count?: number;
  grades?: unknown[];
};

type CachePayload = {
  total?: number;
  count?: number;
  exists?: boolean;
  records?: CacheRecord[];
};

const router = useRouter();
const i18n = useI18nStore();
const loading = ref(true);
const error = ref("");
const payload = ref<CachePayload>({ records: [] });

const records = computed(() => (Array.isArray(payload.value.records) ? payload.value.records : []));
const count = computed(() => Number(payload.value.total ?? payload.value.count ?? 0));
const cache = computed(() => runtime.responseCacheStore() as Record<string, unknown> | null);
const exists = computed(() => Boolean(payload.value.exists || cache.value));
const embeddingModel = computed(() => String(cache.value?.embedding_model || "system-managed"));

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}

function generationLabel(record: CacheRecord) {
  return `${record.provider || ""} · ${record.model || ""}`;
}

function gradeCount(record: CacheRecord) {
  return Array.isArray(record.grades) ? record.grades.length : 0;
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    await runtime.refreshStores();
    const response = await fetch("/api/response-cache/records?limit=100&offset=0");
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`.trim());
    payload.value = (await response.json()) as CachePayload;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    loading.value = false;
  }
}

function openLibrary(question = "") {
  void router.push(question ? { path: "/faq", query: { q: question } } : "/faq");
}

async function clearCache() {
  const approved = await runtime.openMessageModal({
    title: t("runtime.help.clear_rag_response_cache", "Clear RAG response cache?"),
    message: i18n.tf(
      "runtime.help.clear_rag_response_cache_message",
      "Delete all {count} cached RAG responses and saved grades? Corpus vector databases are not affected.",
      { count: count.value.toLocaleString() },
    ),
    tone: "danger",
    confirmLabel: t("common.clear", "Clear response cache"),
    cancelLabel: t("common.cancel", "Cancel"),
  });
  if (!approved) return;
  try {
    const response = await fetch("/api/stores/_response_cache", { method: "DELETE" });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`.trim());
    await load();
    runtime.notifyToast(t("runtime.response_cache_cleared", "Response cache cleared"));
  } catch (cause) {
    runtime.notifyToast(
      i18n.tf(
        "runtime.help.could_not_clear_response_cache",
        "Could not clear response cache: {error}",
        { error: cause instanceof Error ? cause.message : String(cause) },
      ),
      { tone: "danger" },
    );
  }
}

onMounted(async () => {
  await load();
  await nextTick();
  requestAnimationFrame(() =>
    runtime.enhanceCollapsibles(document.querySelector("#main") ?? undefined),
  );
});
</script>

<template>
  <main v-if="loading" id="main" class="runtime-surface" aria-live="polite">
    <div class="info">{{ t("runtime.loading_response_cache", "Loading response cache") }}</div>
  </main>
  <main v-else-if="error" id="main" class="runtime-surface" aria-live="polite">
    <div class="info error">
      <b>{{ t("runtime.help.could_not_read_response_cache", "Could not read response cache.") }}</b>
      <span>{{ error }}</span>
    </div>
  </main>
  <main v-else id="main" class="runtime-surface" aria-live="polite">
    <div class="response-cache-page">
      <section class="card response-cache-overview">
        <div class="cardhead">
          <div>
            <b>{{ t("runtime.help.rag_response_cache", "RAG response cache") }}</b>
            <div class="note">
              {{
                t(
                  "runtime.help.system_cache_only",
                  "System cache only. This collection is intentionally excluded from corpus Vector Stores, corpus DB counts, language mirroring, and RAG source selection.",
                )
              }}
            </div>
          </div>
          <div class="tools">
            <button class="btn" id="cacheFaq" @click="openLibrary()">
              <AppIcon name="books" />{{
                t("runtime.help.open_response_library", "Open Response Library")
              }}
            </button>
            <button
              v-if="exists"
              class="btn danger"
              id="clearResponseCache"
              @click="clearCache"
            >
              {{ t("common.clear", "Clear cache") }}
            </button>
          </div>
        </div>
        <div class="dashboard-kpis response-cache-kpis">
          <div class="dash-kpi">
            <span>{{ t("runtime.cached_responses", "Cached responses") }}</span>
            <strong>{{ count.toLocaleString() }}</strong>
          </div>
          <div class="dash-kpi">
            <span>{{ t("runtime.collection", "Collection") }}</span>
            <strong>{{ exists ? "_response_cache" : "Not created" }}</strong>
          </div>
          <div class="dash-kpi">
            <span>{{ t("runtime.embedding", "Embedding") }}</span>
            <strong>{{ embeddingModel }}</strong>
          </div>
        </div>
        <div class="info">
          {{
            t(
              "runtime.help.response_cache_record_contents",
              "Each cache record stores the original RAG query, instructions, run parameters, answer, evidence, retrieval diagnostics, timings, and all saved LLM grading runs.",
            )
          }}
        </div>
      </section>
      <section class="card">
        <div class="cardhead">
          <div>
            <b>{{ t("runtime.help.recent_cached_responses", "Recent cached responses") }}</b>
            <div class="note">
              {{
                t(
                  "runtime.help.latest_100_response_cache_entries_use_response_faq_for_full_answer_evidence_browsing_and_re_run",
                  "Latest 100 response-cache entries. Use Response Library for full answer/evidence browsing and re-runs.",
                )
              }}
            </div>
          </div>
        </div>
        <div class="tablewrap">
          <table>
            <thead>
              <tr>
                <th>{{ t("runtime.created", "Created") }}</th>
                <th>{{ t("runtime.question", "Question") }}</th>
                <th>{{ t("runtime.generation", "Generation") }}</th>
                <th>{{ t("runtime.evidence", "Evidence") }}</th>
                <th>{{ t("runtime.grades", "Grades") }}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!records.length">
                <td colspan="6" class="note">
                  {{ t("runtime.help.no_cached_responses_yet", "No cached responses yet.") }}
                </td>
              </tr>
              <tr v-for="(record, index) in records" :key="index">
                <td>{{ runtime.formatTimestamp(record.created_at) }}</td>
                <td>{{ record.question || "" }}</td>
                <td>{{ generationLabel(record) }}</td>
                <td>{{ Number(record.evidence_count || 0) }}</td>
                <td>{{ gradeCount(record) }}</td>
                <td>
                  <button
                    class="btn tiny"
                    :data-cache-faq="index"
                    @click="openLibrary(record.question || '')"
                  >
                    {{ t("runtime.open_in_response_library", "Open in Response Library") }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </main>
</template>
