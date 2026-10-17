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
import { computed, ref } from "vue";
import type { CorpusBuild } from "../api/corpus";
import { useI18nStore } from "../stores/i18n";
import { corpusStatusTone } from "../features/corpus-builder/domain/workflowPresentation";
import UiDialog from "./ui/UiDialog.vue";
const props = withDefaults(
  defineProps<{
    builds: CorpusBuild[];
    selectedBuildId?: string;
    pendingBuildId?: string;
    total?: number;
    loading?: boolean;
    error?: string;
    disabled?: boolean;
  }>(),
  { selectedBuildId: "", pendingBuildId: "", total: 0, loading: false, error: "", disabled: false },
);
const emit = defineEmits<{
  select: [build: CorpusBuild];
  refresh: [];
  loadMore: [];
  openChange: [open: boolean];
}>();
const i18n = useI18nStore();
const open = ref(false),
  query = ref(""),
  activeOnly = ref(false);
const activeCount = computed(
  () => props.builds.filter((build) => ["queued", "running"].includes(build.status)).length,
);
function title(build: CorpusBuild) {
  return typeof build.manifest?.title === "string" && build.manifest.title
    ? build.manifest.title
    : build.source_filename;
}
const visible = computed(() =>
  props.builds.filter(
    (build) =>
      (!activeOnly.value || ["queued", "running"].includes(build.status)) &&
      `${title(build)} ${build.source_filename}`
        .toLocaleLowerCase()
        .includes(query.value.trim().toLocaleLowerCase()),
  ),
);
function setOpen(value: boolean) {
  open.value = value;
  emit("openChange", value);
}
function select(build: CorpusBuild) {
  if (props.disabled) return;
  emit("select", build);
  setOpen(false);
}
function statusLabel(build: CorpusBuild) {
  return build.publication
    ? i18n.t("pdf_corpus.status.published_snapshot", "Published")
    : i18n.t(`pdf_corpus.status.${build.status}`, build.status.replace(/_/g, " "));
}
function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : new Intl.DateTimeFormat(i18n.locale || undefined, {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: i18n.timeZone,
      }).format(date);
}
</script>
<template>
  <button
    type="button"
    class="btn"
    aria-haspopup="dialog"
    :aria-expanded="open"
    @click="setOpen(true)"
  >
    {{ i18n.t("pdf_corpus.builds", "Corpus builds") }} <span>{{ total }}</span>
  </button>
  <UiDialog
    v-if="open"
    placement="side"
    :title="i18n.t('pdf_corpus.builds', 'Corpus builds')"
    :description="
      i18n.t(
        'pdf_corpus.build_history_anywhere',
        'Open or monitor another build without leaving the current task.',
      )
    "
    :close-label="i18n.t('common.close', 'Close')"
    @close="setOpen(false)"
  >
    <div class="history-controls">
      <div role="group" :aria-label="i18n.t('pdf_corpus.history_filter', 'Filter builds')">
        <button type="button" class="btn" :aria-pressed="!activeOnly" @click="activeOnly = false">
          {{ i18n.t("pdf_corpus.queue_all", "All") }}</button
        ><button type="button" class="btn" :aria-pressed="activeOnly" @click="activeOnly = true">
          {{ i18n.tf("pdf_corpus.history_active", { count: activeCount }) }}
        </button>
      </div>
      <label
        >{{ i18n.t("pdf_corpus.history_search", "Search builds")
        }}<input v-model="query" type="search" class="control"
      /></label>
      <button type="button" class="btn" :disabled="loading" @click="emit('refresh')">
        {{ i18n.t("pdf_corpus.refresh_builds", "Refresh builds") }}
      </button>
    </div>
    <p v-if="disabled" role="status">
      {{
        i18n.t(
          "pdf_corpus.history_action_pending",
          "Finish the current action before switching builds.",
        )
      }}
    </p>
    <p v-if="loading" role="status">
      {{ i18n.t("pdf_corpus.history_loading", "Loading builds…") }}
    </p>
    <p v-if="error" role="alert">{{ error }}</p>
    <div class="history-list">
      <button
        v-for="build in visible"
        :key="build.build_id"
        type="button"
        class="history-row"
        :disabled="disabled"
        :aria-busy="build.build_id === pendingBuildId ? true : undefined"
        :data-pending="build.build_id === pendingBuildId ? true : undefined"
        :aria-current="build.build_id === selectedBuildId ? 'true' : undefined"
        @click="select(build)"
      >
        <b
          ><span class="dot" :data-tone="corpusStatusTone(build)" aria-hidden="true">● </span
          ><span v-if="build.build_id === selectedBuildId" class="selected-mark"
            >✓ <span class="sr-only">{{ i18n.t("pdf_corpus.build_selected") }}</span></span
          >{{ title(build) }}</b
        ><span
          >{{ statusLabel(build) }} · {{ Math.round((build.progress || 0) * 100) }}% ·
          {{ build.record_count ?? "—" }} {{ i18n.t("pdf_corpus.records", "records") }}</span
        ><small>{{ formatDate(build.created_at) }}</small
        ><small>{{ build.build_id }}</small>
      </button>
      <p v-if="!visible.length && !loading">
        {{ i18n.t("pdf_corpus.history_empty", "No matching builds in the loaded results.") }}
      </p>
    </div>
    <template #footer
      ><span>{{ i18n.tf("pdf_corpus.history_loaded", { loaded: builds.length, total }) }}</span
      ><button
        v-if="builds.length < total"
        type="button"
        class="btn"
        :disabled="loading"
        @click="emit('loadMore')"
      >
        {{ i18n.t("pdf_corpus.history_more", "Load more builds") }}
      </button></template
    >
  </UiDialog>
</template>
<style scoped>
.history-controls {
  display: grid;
  gap: 12px;
  margin-bottom: 16px;
}
.history-controls > div {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.history-controls label {
  display: grid;
  gap: 6px;
  font-size: 0.875rem;
  font-weight: 700;
}
.control {
  width: 100%;
  min-width: 0;
}
.history-list {
  display: grid;
  gap: 10px;
}
.history-row {
  display: grid;
  gap: 5px;
  width: 100%;
  text-align: start;
  overflow-wrap: anywhere;
  padding: 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 9px;
  background: var(--surface-card);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.875rem;
}
.history-row small,
.history-row span {
  color: var(--text-secondary);
}
.history-row[aria-current="true"] {
  border-color: var(--accent);
}
.btn {
  min-height: 40px;
  white-space: normal;
}
.history-row:focus-visible,
.control:focus-visible,
.btn:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
</style>
