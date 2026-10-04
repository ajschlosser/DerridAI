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
import { annotationsWorkspace } from "../domain/sharedAnnotations";
import { sharedRecordWorkspace } from "../domain/sharedRecordWorkspace";
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
const modelLoading = ref(false);
const modelError = ref("");
let traceIdentity = "";
// Remount the explorer when the record or requested lens changes.
const explorerKey = computed(() => `${store.value}|${recordId.value}|${mode.value}`);

const latest = createLatestRequest();
const latestModel = createLatestRequest();

/**
 * A stored Record and its graph in one read: the server builds the graph from the stored projection,
 * so the Record is never downloaded only to be uploaded again. Without a store there is nothing
 * stored to read, and the graph is built around the bare identifier.
 */
async function readTrace(signal: AbortSignal) {
  if (!store.value) {
    const bare = { record_id: recordId.value };
    return { record: bare, graph: await sharedRecordWorkspace.getRecordObjectGraph(bare) };
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
  const identity = `${store.value}|${recordId.value}`;
  if (traceIdentity !== identity) {
    record.value = null;
    graph.value = null;
    traceIdentity = identity;
  }
  error.value = "";
  loading.value = false;
  if (!recordId.value) return;
  loading.value = true;
  try {
    const trace = await readTrace(ticket.signal);
    if (!ticket.current()) return;
    record.value = trace.record;
    graph.value = trace.graph as ResearchObjectGraph;
  } catch (exc) {
    if (!ticket.current() || isAbortError(exc)) return;
    if (
      exc &&
      typeof exc === "object" &&
      "status" in exc &&
      [401, 403].includes(Number(exc.status))
    ) {
      record.value = null;
      graph.value = null;
    }
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    if (ticket.current()) loading.value = false;
  }
}
async function loadModel() {
  const ticket = latestModel.start();
  modelLoading.value = true;
  modelError.value = "";
  try {
    const value = await sharedRecordWorkspace.getDerridaiNormativeModel();
    if (ticket.current()) model.value = value as DerridaiNormativeModel;
  } catch (exc) {
    if (!ticket.current() || isAbortError(exc)) return;
    if (
      exc &&
      typeof exc === "object" &&
      "status" in exc &&
      [401, 403].includes(Number(exc.status))
    )
      model.value = null;
    modelError.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    if (ticket.current()) modelLoading.value = false;
  }
}

function submit() {
  const id = idInput.value.trim();
  if (!id) return;
  void router.push({ query: { ...route.query, record: id } });
}
function openRecord() {
  annotationsWorkspace.openAnnotationsWorkspaceRecord({
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
  void loadModel();
  void load();
});
onBeforeUnmount(() => {
  latest.cancel();
  latestModel.cancel();
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
    <div v-if="error" class="relationship-trace-status">
      <UiButton :label="i18n.t('ui.retry')" @click="load" />
    </div>
    <div v-if="modelError" class="relationship-model-status" role="alert">
      <p>{{ i18n.t("traceability.data_model") }}: {{ modelError }}</p>
      <UiButton :label="i18n.t('ui.retry')" @click="loadModel" />
    </div>
    <RecordTraceabilityExplorer
      v-if="recordId || model || modelLoading || modelError"
      :key="explorerKey"
      :graph="graph"
      :model="model"
      :model-loading="modelLoading"
      :model-error="modelError"
      :record="record"
      :loading="loading"
      :error="error"
      :initial-mode="recordId ? mode : 'model'"
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
