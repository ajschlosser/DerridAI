<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { esc, icon } from "../domain/html";
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

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}

const markup = computed(() => {
  const rows = records.value
    .map(
      (record, index) =>
        `<tr><td>${esc(runtime.formatTimestamp(record.created_at))}</td><td>${esc(record.question || "")}</td><td>${esc(record.provider || "")} · ${esc(record.model || "")}</td><td>${Number(record.evidence_count || 0)}</td><td>${Array.isArray(record.grades) ? record.grades.length : 0}</td><td><button class="btn tiny" data-cache-faq="${index}">${esc(t("runtime.open_in_response_library", "Open in Response Library"))}</button></td></tr>`,
    )
    .join("");
  return `<div class="response-cache-page">
    <section class="card response-cache-overview">
      <div class="cardhead"><div><b>${esc(t("runtime.help.rag_response_cache", "RAG response cache"))}</b><div class="note">${esc(t("runtime.help.system_cache_only", "System cache only. This collection is intentionally excluded from corpus Vector Stores, corpus DB counts, language mirroring, and RAG source selection."))}</div></div><div class="tools"><button class="btn" id="cacheFaq">${icon("books")}${esc(t("runtime.help.open_response_library", "Open Response Library"))}</button>${exists.value ? `<button class="btn danger" id="clearResponseCache">${esc(t("common.clear", "Clear cache"))}</button>` : ""}</div></div>
      <div class="dashboard-kpis response-cache-kpis"><div class="dash-kpi"><span>${esc(t("runtime.cached_responses", "Cached responses"))}</span><strong>${count.value.toLocaleString()}</strong></div><div class="dash-kpi"><span>${esc(t("runtime.collection", "Collection"))}</span><strong>${exists.value ? "_response_cache" : "Not created"}</strong></div><div class="dash-kpi"><span>${esc(t("runtime.embedding", "Embedding"))}</span><strong>${esc(String(cache.value?.embedding_model || "system-managed"))}</strong></div></div>
      <div class="info">${esc(t("runtime.help.response_cache_record_contents", "Each cache record stores the original RAG query, instructions, run parameters, answer, evidence, retrieval diagnostics, timings, and all saved LLM grading runs."))}</div>
    </section>
    <section class="card"><div class="cardhead"><div><b>${esc(t("runtime.help.recent_cached_responses", "Recent cached responses"))}</b><div class="note">${esc(t("runtime.help.latest_100_response_cache_entries_use_response_faq_for_full_answer_evidence_browsing_and_re_run", "Latest 100 response-cache entries. Use Response Library for full answer/evidence browsing and re-runs."))}</div></div></div>
      <div class="tablewrap"><table><thead><tr><th>${esc(t("runtime.created", "Created"))}</th><th>${esc(t("runtime.question", "Question"))}</th><th>${esc(t("runtime.generation", "Generation"))}</th><th>${esc(t("runtime.evidence", "Evidence"))}</th><th>${esc(t("runtime.grades", "Grades"))}</th><th></th></tr></thead><tbody>${rows || `<tr><td colspan="6" class="note">${esc(t("runtime.help.no_cached_responses_yet", "No cached responses yet."))}</td></tr>`}</tbody></table></div>
    </section>
  </div>`;
});

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
    await nextTick();
    bindActions();
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

function bindActions() {
  document.querySelector("#cacheFaq")?.addEventListener("click", () => openLibrary());
  document.querySelectorAll<HTMLElement>("[data-cache-faq]").forEach((button) => {
    button.addEventListener("click", () =>
      openLibrary(records.value[Number(button.dataset.cacheFaq)]?.question || ""),
    );
  });
  document.querySelector("#clearResponseCache")?.addEventListener("click", () => void clearCache());
}

onMounted(async () => {
  await load();
  await nextTick();
  bindActions();
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
  <main v-else id="main" class="runtime-surface" aria-live="polite" v-html="markup"></main>
</template>
