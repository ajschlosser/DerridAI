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
/**
 * Project Gutenberg installation status. Catalogue search can work before the
 * text database is installed; the full collection enables genuinely local
 * author capture and book acquisition.
 */
import { computed } from "vue";
import type { GutenbergStatus } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{
  status: GutenbergStatus | null;
  catalogueReady: boolean;
  disabled: boolean;
  busy: string;
}>();
const emit = defineEmits<{
  refreshCatalogue: [];
  updateArchive: [action: "start" | "pause" | "resume" | "refetch"];
}>();
const i18n = useI18nStore();

const archiveStatus = computed(() => String(props.status?.archive.status || ""));
const catalogueRefreshing = computed(() =>
  ["refreshing", "indexing"].includes(String(props.status?.catalogue.status || "")),
);
const bytesOnDisk = computed(() => Number(props.status?.archive.bytes_done || 0));
const importedTexts = computed(() => Number(props.status?.archive.imported_texts || 0));
const retryingDownload = computed(
  () => archiveStatus.value === "downloading" && Number(props.status?.archive.retry_count || 0) > 0,
);

function formatNumber(value: number) {
  return new Intl.NumberFormat(i18n.locale || undefined).format(value);
}
function formatBytes(value?: number | null) {
  const bytes = Math.max(0, Number(value || 0));
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let size = bytes;
  let unit = -1;
  do {
    size /= 1024;
    unit += 1;
  } while (size >= 1024 && unit < units.length - 1);
  return `${size.toFixed(size >= 10 ? 1 : 2)} ${units[unit]}`;
}
function archiveAction(): "start" | "pause" | "resume" {
  if (archiveStatus.value === "downloading") return "pause";
  // After a pause or an error, bytes already on disk are kept and the download continues from them.
  if (archiveStatus.value === "paused" || (archiveStatus.value === "error" && bytesOnDisk.value))
    return "resume";
  return "start";
}
function redownload() {
  const size = formatBytes(bytesOnDisk.value);
  if (!window.confirm(i18n.tf("pdf_corpus.gutenberg_redownload_confirm", { size }))) return;
  emit("updateArchive", "refetch");
}
function archiveActionLabel() {
  if (["downloaded", "unpacking"].includes(archiveStatus.value))
    return i18n.t("pdf_corpus.gutenberg_unpacking", "Unpacking collection…");
  if (archiveStatus.value === "downloading") return i18n.t("pdf_corpus.gutenberg_pause_download");
  if (archiveAction() === "resume") return i18n.t("pdf_corpus.gutenberg_resume_download");
  return i18n.t("pdf_corpus.gutenberg_start_download");
}
</script>

<template>
  <section class="ls-collection">
    <p>
      {{
        catalogueReady
          ? i18n.t("pdf_corpus.library.collection_needed")
          : i18n.t("pdf_corpus.library.catalogue_needed")
      }}
    </p>
    <div class="ls-collection-actions">
      <button
        v-if="!catalogueReady"
        type="button"
        class="btn small primary"
        :disabled="disabled || busy === 'gutenberg-catalogue' || catalogueRefreshing"
        @click="emit('refreshCatalogue')"
      >
        {{
          catalogueRefreshing
            ? i18n.t("pdf_corpus.gutenberg_catalogue_refreshing", "Updating catalogue…")
            : i18n.t("pdf_corpus.gutenberg_fetch_catalogue")
        }}
      </button>
      <button
        v-else
        type="button"
        class="btn small"
        :disabled="
          disabled ||
          busy === 'gutenberg-archive' ||
          ['downloaded', 'unpacking'].includes(archiveStatus)
        "
        @click="emit('updateArchive', archiveAction())"
      >
        {{ archiveActionLabel() }}
      </button>
      <button
        v-if="catalogueReady && archiveStatus === 'error' && bytesOnDisk"
        type="button"
        class="btn small quiet"
        :disabled="disabled || busy === 'gutenberg-archive'"
        @click="redownload"
      >
        {{ i18n.t("pdf_corpus.gutenberg_redownload") }}
      </button>
      <template v-if="status?.archive.total_bytes">
        <progress
          class="ls-progress"
          :value="status.archive.bytes_done"
          :max="status.archive.total_bytes"
          :aria-label="i18n.t('pdf_corpus.gutenberg_download_progress')"
        />
        <small
          >{{ formatBytes(status.archive.bytes_done) }} /
          {{ formatBytes(status.archive.total_bytes) }}</small
        >
      </template>
      <small v-if="archiveStatus === 'unpacking' && importedTexts">
        {{
          i18n.tf("pdf_corpus.gutenberg_import_progress", {
            count: formatNumber(importedTexts),
          })
        }}
      </small>
    </div>
    <small v-if="status?.catalogue.error" class="ls-error-text">{{ status.catalogue.error }}</small>
    <small
      v-if="status?.archive.error"
      :class="retryingDownload ? 'ls-retry-text' : 'ls-error-text'"
      aria-live="polite"
    >
      {{ status.archive.error }}
    </small>
  </section>
</template>

<style scoped>
.ls-error-text {
  color: var(--tone-danger-fg);
}
.ls-retry-text {
  color: var(--tone-info-fg);
}
.ls-collection {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid var(--tone-info-edge, var(--line));
  border-radius: var(--radius-control);
  color: var(--tone-info-fg);
  background: var(--tone-info-bg);
  font-size: var(--fs-sm);
}
.ls-collection p {
  margin: 0;
  line-height: 1.45;
}
.ls-collection-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.ls-progress {
  flex: 1 1 8rem;
  min-width: 6rem;
}
.btn.quiet {
  border-color: transparent;
  background: transparent;
}
.btn.quiet:hover:not(:disabled) {
  background: var(--surface-hover);
}
:is(button, select, .ls-chip):focus-visible {
  outline: 3px solid var(--focus-ring, var(--accent));
  outline-offset: 2px;
}
</style>
