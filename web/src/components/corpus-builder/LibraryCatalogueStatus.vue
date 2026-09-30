<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
/**
 * What the Project Gutenberg search needs locally: the catalogue (required for
 * search) and the optional text collection. Imports download one verified
 * text regardless of the collection.
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
    </div>
    <small v-if="status?.catalogue.error" class="ls-error-text">{{ status.catalogue.error }}</small>
    <small v-if="status?.archive.error" class="ls-error-text">{{ status.archive.error }}</small>
  </section>
</template>

<style scoped>
.ls-error-text {
  color: var(--tone-danger-fg);
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
