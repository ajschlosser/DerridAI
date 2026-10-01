<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref, type Ref } from "vue";
import AppIcon from "../AppIcon.vue";
import SystemDataStoreCard from "../SystemDataStoreCard.vue";
import {
  systemApi,
  type SystemChromaCollection,
  type SystemDataDatabase,
  type SystemMetadataExemplarPage,
  type SystemResponseCachePage,
} from "../../api/system";
import { pipelinesApi } from "../../api/pipelines";
import { useDataQuery } from "../../realtime/dataQuery";
import { useI18nStore } from "../../stores/i18n";

type Section = "overview" | "responses" | "metadata" | "pipelines" | "databases" | "advanced";
defineEmits<{ "open-section": [section: Section] }>();

const i18n = useI18nStore();
type LoadState = "loading" | "available" | "unavailable";

// Each count is one server-state read; realtime invalidation of its resource refetches it. The
// database inventory (which files exist) does not change while the app runs: it is read once.
const cacheQuery = useDataQuery("response_library", () => systemApi.responseCacheRecords(1, 0), {
  detail: ["overview"],
});
const exemplarsQuery = useDataQuery(
  "metadata_exemplars",
  () => systemApi.systemMetadataExemplars({ limit: 1, offset: 0 }),
  { detail: ["overview"] },
);
const chromaQuery = useDataQuery("vector_collections", () => systemApi.systemChromaCollections(), {
  detail: ["system-collections"],
});
function stateOf(query: { isPending: Ref<boolean>; isError: Ref<boolean> }): LoadState {
  if (query.isError.value) return "unavailable";
  return query.isPending.value ? "loading" : "available";
}
const databases = ref<SystemDataDatabase[]>([]);
const databaseState = ref<LoadState>("loading");
onMounted(async () => {
  try {
    databases.value = (await systemApi.systemData()).databases || [];
    databaseState.value = "available";
  } catch {
    databaseState.value = "unavailable";
  }
});
const cache = computed<SystemResponseCachePage | null>(() => cacheQuery.data.value ?? null);
const cacheState = computed(() => stateOf(cacheQuery));
const exemplars = computed<SystemMetadataExemplarPage | null>(
  () => exemplarsQuery.data.value ?? null,
);
const exemplarState = computed(() => stateOf(exemplarsQuery));
const collections = computed<SystemChromaCollection[]>(
  () => chromaQuery.data.value?.collections || [],
);
const chromaState = computed(() => stateOf(chromaQuery));
// Pipeline definitions get a `pipelines` resource in the Pipeline Studio change; until it merges,
// the count is read once.
const pipelineCount = ref(0);
const pipelineState = ref<LoadState>("loading");
onMounted(async () => {
  try {
    pipelineCount.value = (await pipelinesApi.catalog()).pipelines.length;
    pipelineState.value = "available";
  } catch {
    pipelineState.value = "unavailable";
  }
});

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
    </header>

    <div class="store-grid">
      <SystemDataStoreCard
        icon="database"
        :title="t('runtime.system_application_data', 'Application data')"
        :detail="
          t(
            'runtime.system_application_data_help',
            'Durable application information such as provider profiles, annotations, languages, and jobs.',
          )
        "
        technical="system · durable SQLite"
        :status="stateLabel(databaseState, database('system')?.tables.length === 0)"
        :count="`${database('system')?.tables.length || 0} ${t('runtime.system_tables', 'tables')}`"
        :action-label="t('runtime.system_open', 'Open')"
        @open="$emit('open-section', 'databases')"
      />
      <SystemDataStoreCard
        icon="lock"
        :title="t('runtime.system_identity_access', 'Identity and access')"
        :detail="
          t(
            'runtime.system_identity_access_help',
            'Sensitive identity state including users, roles or permissions, sessions, and login security.',
          )
        "
        technical="auth · sensitive durable SQLite"
        sensitive
        :status="stateLabel(databaseState, database('auth')?.tables.length === 0)"
        :count="`${database('auth')?.tables.length || 0} ${t('runtime.system_tables', 'tables')}`"
        :action-label="t('runtime.system_open', 'Open')"
        @open="$emit('open-section', 'databases')"
      />
      <SystemDataStoreCard
        icon="record"
        :title="t('runtime.system_saved_responses', 'Saved responses')"
        :detail="
          t(
            'runtime.system_saved_responses_help',
            'Generated research responses and grades. This operational history is not a research source or corpus collection.',
          )
        "
        technical="_response_cache"
        :status="stateLabel(cacheState, cache?.total === 0)"
        :count="`${Number(cache?.total || 0).toLocaleString()} ${t('runtime.system_responses_count', 'responses')}`"
        :action-label="t('runtime.system_open', 'Open')"
        @open="$emit('open-section', 'responses')"
      />
      <SystemDataStoreCard
        icon="spark"
        :title="t('runtime.system_metadata_examples', 'Metadata examples')"
        :detail="
          t(
            'runtime.system_metadata_examples_help',
            'Evidence-bound examples projected from reviewed corpus metadata for progressive enrichment.',
          )
        "
        technical="derived · rebuildable projection"
        :status="
          exemplarState === 'available' && exemplars?.exists === false
            ? t('runtime.system_not_built', 'Not built')
            : stateLabel(exemplarState, exemplars?.count === 0)
        "
        :count="`${Number(exemplars?.count || 0).toLocaleString()} ${t('runtime.system_examples_count', 'examples')}`"
        :action-label="t('runtime.system_open', 'Open')"
        @open="$emit('open-section', 'metadata')"
      />
      <SystemDataStoreCard
        icon="compare"
        :title="t('pipelines.title', 'Pipeline Studio')"
        :detail="
          t(
            'pipelines.overview_help',
            'Versioned retrieval, reranking, validation, model, and fallback chains with inspectable execution traces.',
          )
        "
        technical="system SQLite · operational configuration"
        :status="stateLabel(pipelineState, pipelineCount === 0)"
        :count="`${pipelineCount} ${t('pipelines.definitions_count', 'definitions')}`"
        :action-label="t('runtime.system_open', 'Open')"
        @open="$emit('open-section', 'pipelines')"
      />
      <SystemDataStoreCard
        icon="search"
        :title="t('runtime.system_internal_vectors', 'Internal vector collections')"
        :detail="
          t(
            'runtime.system_internal_vectors_help',
            'Application-owned projections for advanced read-only inspection, distinct from corpus vector collections.',
          )
        "
        technical="system Chroma · derived"
        :status="stateLabel(chromaState, collections.length === 0)"
        :count="`${collections.length} ${t('runtime.system_collections', 'collections')}`"
        :action-label="t('runtime.system_open', 'Open')"
        @open="$emit('open-section', 'advanced')"
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
.overview {
  display: grid;
  gap: 18px;
}
.workspace-heading {
  display: flex;
  gap: 16px;
  align-items: start;
  justify-content: space-between;
}
.workspace-heading h2 {
  margin: 0;
  font-size: 1.25rem;
}
.workspace-heading p {
  margin: 5px 0 0;
  color: var(--muted);
  line-height: 1.5;
}
.workspace-heading :deep(svg) {
  width: 16px;
  height: 16px;
}
.store-grid {
  display: grid;
  gap: 10px;
}
.context-note {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--soft);
}
.context-note > :deep(svg) {
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  margin-top: 1px;
}
.context-note strong {
  font-size: 0.88rem;
}
.context-note p {
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 0.84rem;
  line-height: 1.5;
}
@media (max-width: 640px) {
  .workspace-heading {
    display: grid;
  }
}
</style>
