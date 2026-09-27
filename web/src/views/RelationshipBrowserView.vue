<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import * as runtime from "../runtime/runtime.js";
import { useI18nStore } from "../stores/i18n";
import UiButton from "../components/ui/UiButton.vue";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import RecordTraceabilityExplorer from "../components/record/RecordTraceabilityExplorer.vue";
import type { DerridaiNormativeModel, ResearchObjectGraph } from "../types/researchObjectGraph";

const i18n = useI18nStore();
const route = useRoute();
const router = useRouter();
const recordId = computed(() => String(route.query.record || "").trim());
const store = computed(() => String(route.query.store || "").trim());
const mode = computed<"trace" | "model">(() => (route.query.mode === "model" ? "model" : "trace"));
const idInput = ref(recordId.value);
const record = ref<Record<string, unknown> | null>(null);
const graph = ref<ResearchObjectGraph | null>(null);
const model = ref<DerridaiNormativeModel | null>(null);
const loading = ref(false);
const error = ref("");
// Remount the explorer when the record or requested lens changes.
const explorerKey = computed(() => `${recordId.value}|${mode.value}`);
let request = 0;

async function fetchRecord(): Promise<Record<string, unknown> | null> {
  if (!store.value) return { record_id: recordId.value };
  const found = await runtime.api(
    `/api/stores/${encodeURIComponent(store.value)}/records/${encodeURIComponent(recordId.value)}`,
  );
  return (found as Record<string, unknown>) || null;
}

async function load() {
  const current = ++request;
  record.value = null;
  graph.value = null;
  error.value = "";
  if (!recordId.value) return;
  loading.value = true;
  try {
    const found = await fetchRecord();
    if (!found) throw new Error(i18n.t("relationships.load_failed"));
    const [g, m] = await Promise.all([
      runtime.getRecordObjectGraph({ record_id: recordId.value, ...found }),
      runtime.getDerridaiNormativeModel(),
    ]);
    if (current !== request) return;
    record.value = found;
    graph.value = g as ResearchObjectGraph;
    model.value = m as DerridaiNormativeModel;
  } catch (exc) {
    if (current === request) error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    if (current === request) loading.value = false;
  }
}

function submit() {
  const id = idInput.value.trim();
  if (!id) return;
  void router.push({ query: { ...route.query, record: id } });
}
function openRecord() {
  runtime.openAnnotationsWorkspaceRecord({
    server: true,
    source: store.value,
    record_id: recordId.value,
  });
}

watch([recordId, store], () => {
  idInput.value = recordId.value;
  void load();
});
onMounted(() => {
  // The model alone is browsable without a record.
  if (!recordId.value)
    void runtime
      .getDerridaiNormativeModel()
      .then((m: unknown) => (model.value = m as DerridaiNormativeModel))
      .catch(() => undefined);
  void load();
});
</script>

<template>
  <main class="relationship-browser" aria-labelledby="relationshipBrowserTitle">
    <UiPageHeader
      title-id="relationshipBrowserTitle"
      :title="i18n.t('relationships.title')"
      :description="i18n.t('relationships.help')"
    >
      <UiButton
        v-if="recordId"
        :label="i18n.t('relationships.open_record')"
        icon="record"
        @click="openRecord"
      />
    </UiPageHeader>
    <form class="relationship-browser-picker" @submit.prevent="submit">
      <label for="relationshipRecordId">{{ i18n.t("relationships.record_id") }}</label>
      <input id="relationshipRecordId" v-model="idInput" type="text" autocomplete="off" />
      <UiButton type="submit" :label="i18n.t('relationships.load')" />
    </form>
    <RecordTraceabilityExplorer
      v-if="recordId || model"
      :key="explorerKey"
      :graph="graph"
      :model="model"
      :record="record"
      :loading="loading"
      :error="error"
      :initial-mode="mode"
    />
    <p v-else class="note">{{ i18n.t("relationships.empty") }}</p>
  </main>
</template>

<style scoped>
.relationship-browser {
  display: grid;
  gap: var(--space-4, 1rem);
  padding: var(--space-4, 1rem);
}
.relationship-browser-picker {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2, 0.5rem);
}
.relationship-browser-picker input {
  flex: 1 1 16rem;
  min-width: 0;
}
</style>
