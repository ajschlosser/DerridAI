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
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import * as runtime from "../runtime/runtime.js";
import { useI18nStore } from "../stores/i18n";
import UiButton from "../components/ui/UiButton.vue";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import RecordTraceabilityExplorer from "../components/record/RecordTraceabilityExplorer.vue";
import type { DerridaiNormativeModel, ResearchObjectGraph } from "../types/researchObjectGraph";
import { execute, isAbortError } from "../api/graphql/client";
import { StoredRecordTraceDocument } from "../api/graphql/generated";
import { createLatestRequest } from "../api/graphql/latestRequest";

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

const latest = createLatestRequest();

/**
 * A stored Record and its graph in one read: the server builds the graph from the stored projection,
 * so the Record is never downloaded only to be uploaded again. Without a store there is nothing
 * stored to read, and the graph is built around the bare identifier.
 */
async function readTrace(signal: AbortSignal) {
  if (!store.value) {
    const bare = { record_id: recordId.value };
    return { record: bare, graph: await runtime.getRecordObjectGraph(bare) };
  }
  const { vector_store } = await execute(
    StoredRecordTraceDocument,
    { store: store.value, chroma_id: recordId.value },
    { signal },
  );
  if (!vector_store.record) throw new Error(i18n.t("relationships.load_failed"));
  return {
    record: vector_store.record.document as Record<string, unknown>,
    graph: vector_store.record.graph,
  };
}

async function load() {
  const ticket = latest.start();
  record.value = null;
  graph.value = null;
  error.value = "";
  if (!recordId.value) return;
  loading.value = true;
  try {
    const [trace, m] = await Promise.all([
      readTrace(ticket.signal),
      runtime.getDerridaiNormativeModel(),
    ]);
    if (!ticket.current()) return;
    record.value = trace.record;
    graph.value = trace.graph as ResearchObjectGraph;
    model.value = m as DerridaiNormativeModel;
  } catch (exc) {
    if (ticket.current() && !isAbortError(exc))
      error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    if (ticket.current()) loading.value = false;
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
onBeforeUnmount(() => latest.cancel());
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
