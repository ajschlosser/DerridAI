<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { onMounted, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import SystemDataStoreCard from "../SystemDataStoreCard.vue";
import {
  systemApi,
  type SystemChromaCollection,
  type SystemDataDatabase,
  type SystemMetadataExemplarPage,
  type SystemResponseCachePage,
} from "../../api/system";
import { useI18nStore } from "../../stores/i18n";

type Section = "overview" | "responses" | "metadata" | "databases" | "advanced";
defineEmits<{ "open-section": [section: Section] }>();

const i18n = useI18nStore();
const databases = ref<SystemDataDatabase[]>([]);
const databaseState = ref<"loading" | "available" | "unavailable">("loading");
const cache = ref<SystemResponseCachePage | null>(null);
const cacheState = ref<"loading" | "available" | "unavailable">("loading");
const exemplars = ref<SystemMetadataExemplarPage | null>(null);
const exemplarState = ref<"loading" | "available" | "unavailable">("loading");
const collections = ref<SystemChromaCollection[]>([]);
const chromaState = ref<"loading" | "available" | "unavailable">("loading");

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}
function stateLabel(state: "loading" | "available" | "unavailable", empty = false) {
  if (state === "loading") return t("common.loading", "Checking");
  if (state === "unavailable") return t("common.unavailable", "Unavailable");
  if (empty) return t("common.empty", "Empty");
  return t("common.available", "Available");
}
function database(name: string) {
  return databases.value.find((item) => item.name === name);
}

async function loadDatabases() {
  databaseState.value = "loading";
  try {
    databases.value = (await systemApi.systemData()).databases || [];
    databaseState.value = "available";
  } catch {
    databases.value = [];
    databaseState.value = "unavailable";
  }
}
async function loadCache() {
  cacheState.value = "loading";
  try {
    cache.value = await systemApi.responseCacheRecords(1, 0);
    cacheState.value = "available";
  } catch {
    cache.value = null;
    cacheState.value = "unavailable";
  }
}
async function loadExemplars() {
  exemplarState.value = "loading";
  try {
    exemplars.value = await systemApi.systemMetadataExemplars({ limit: 1, offset: 0 });
    exemplarState.value = "available";
  } catch {
    exemplars.value = null;
    exemplarState.value = "unavailable";
  }
}
async function loadChroma() {
  chromaState.value = "loading";
  try {
    collections.value = (await systemApi.systemChromaCollections()).collections || [];
    chromaState.value = "available";
  } catch {
    collections.value = [];
    chromaState.value = "unavailable";
  }
}
function refresh() {
  void Promise.allSettled([loadDatabases(), loadCache(), loadExemplars(), loadChroma()]);
}

onMounted(refresh);
</script>

<template>
  <div class="overview">
    <header class="workspace-heading">
      <div>
        <h2>{{ t("runtime.system_storage_overview", "Storage overview") }}</h2>
        <p>
          {{
            t(
              "runtime.system_storage_overview_help",
              "Understand what DerridAI stores, why it exists, and where to inspect it.",
            )
          }}
        </p>
      </div>
      <button class="btn" type="button" @click="refresh">
        <AppIcon name="refresh" /> {{ t("common.refresh", "Refresh") }}
      </button>
    </header>

    <div class="store-grid">
      <SystemDataStoreCard
        icon="database"
        :title="t('runtime.system_application_data', 'Application data')"
        :detail="t('runtime.system_application_data_help', 'Durable application information such as provider profiles, annotations, languages, and jobs.')"
        technical="system · durable SQLite"
        :status="stateLabel(databaseState, database('system')?.tables.length === 0)"
        :count="`${database('system')?.tables.length || 0} ${t('runtime.system_tables', 'tables')}`"
         :action-label="t('runtime.system_open', 'Open')" @open="$emit('open-section', 'databases')"
      />
      <SystemDataStoreCard
        icon="lock"
        :title="t('runtime.system_identity_access', 'Identity and access')"
        :detail="t('runtime.system_identity_access_help', 'Sensitive identity state including users, roles or permissions, sessions, and login security.')"
        technical="auth · sensitive durable SQLite"
        sensitive
        :status="stateLabel(databaseState, database('auth')?.tables.length === 0)"
        :count="`${database('auth')?.tables.length || 0} ${t('runtime.system_tables', 'tables')}`"
         :action-label="t('runtime.system_open', 'Open')" @open="$emit('open-section', 'databases')"
      />
      <SystemDataStoreCard
        icon="record"
        :title="t('runtime.system_saved_responses', 'Saved responses')"
        :detail="t('runtime.system_saved_responses_help', 'Generated research responses and grades. This operational history is not a research source or corpus collection.')"
        technical="_response_cache"
        :status="stateLabel(cacheState, cache?.total === 0)"
        :count="`${Number(cache?.total || 0).toLocaleString()} ${t('runtime.system_responses_count', 'responses')}`"
         :action-label="t('runtime.system_open', 'Open')" @open="$emit('open-section', 'responses')"
      />
      <SystemDataStoreCard
        icon="spark"
        :title="t('runtime.system_metadata_examples', 'Metadata examples')"
        :detail="t('runtime.system_metadata_examples_help', 'Evidence-bound examples projected from reviewed corpus metadata for progressive enrichment.')"
        technical="derived · rebuildable projection"
        :status="exemplarState === 'available' && exemplars?.exists === false ? t('runtime.system_not_built', 'Not built') : stateLabel(exemplarState, exemplars?.count === 0)"
        :count="`${Number(exemplars?.count || 0).toLocaleString()} ${t('runtime.system_examples_count', 'examples')}`"
         :action-label="t('runtime.system_open', 'Open')" @open="$emit('open-section', 'metadata')"
      />
      <SystemDataStoreCard
        icon="search"
        :title="t('runtime.system_internal_vectors', 'Internal vector collections')"
        :detail="t('runtime.system_internal_vectors_help', 'Application-owned projections for advanced read-only inspection, distinct from corpus vector collections.')"
        technical="system Chroma · derived"
        :status="stateLabel(chromaState, collections.length === 0)"
        :count="`${collections.length} ${t('runtime.system_collections', 'collections')}`"
         :action-label="t('runtime.system_open', 'Open')" @open="$emit('open-section', 'advanced')"
      />
    </div>

    <aside class="context-note">
      <AppIcon name="help" />
      <div>
        <strong>{{ t("runtime.system_corpus_separate", "Corpus data remains separate") }}</strong>
        <p>
          {{
            t(
              "runtime.system_corpus_separate_help",
              "These stores support DerridAI itself. Corpus records and their scholarly provenance remain the authoritative research layer.",
            )
          }}
        </p>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.overview { display: grid; gap: 18px; }
.workspace-heading {
  display: flex;
  gap: 16px;
  align-items: start;
  justify-content: space-between;
}
.workspace-heading h2 { margin: 0; font-size: 1.25rem; }
.workspace-heading p { margin: 5px 0 0; color: var(--muted); line-height: 1.5; }
.workspace-heading :deep(svg) { width: 16px; height: 16px; }
.store-grid { display: grid; gap: 10px; }
.context-note {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--soft);
}
.context-note > :deep(svg) { flex: 0 0 auto; width: 18px; height: 18px; margin-top: 1px; }
.context-note strong { font-size: .88rem; }
.context-note p { margin: 3px 0 0; color: var(--muted); font-size: .84rem; line-height: 1.5; }
@media (max-width: 640px) {
  .workspace-heading { display: grid; }
}
</style>
