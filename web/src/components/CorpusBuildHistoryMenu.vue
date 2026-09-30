<script setup lang="ts">
import type { CorpusBuild } from "../api/pdfCorpus";
import { corpusStatusTone } from "../features/corpus-builder/domain/workflowPresentation";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";
withDefaults(defineProps<{ builds: CorpusBuild[]; selectedBuildId?: string; total?: number }>(), {
  selectedBuildId: "",
  total: 0,
});
const emit = defineEmits<{ select: [build: CorpusBuild]; refresh: [] }>();
const i18n = useI18nStore();
function statusLabel(build: CorpusBuild) {
  if (build.publication) return i18n.t("pdf_corpus.status.published_snapshot");
  return i18n.t(
    `pdf_corpus.status.${String(build.status || "unknown")}`,
    String(build.status || "unknown").replace(/_/g, " "),
  );
}
function formatDate(value?: string | null) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat(i18n.locale || undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}
</script>
<template>
  <details class="history-menu">
    <summary class="btn">
      {{ i18n.t("pdf_corpus.builds") }} <span class="count">{{ total }}</span>
    </summary>
    <div
      class="history-popover"
      role="region"
      :aria-label="i18n.t('pdf_corpus.build_history_panel')"
      data-surface="overlay"
    >
      <header>
        <div>
          <b>{{ i18n.t("pdf_corpus.builds") }}</b
          ><small>{{ i18n.t("pdf_corpus.build_history_anywhere") }}</small>
        </div>
        <UiButton
          icon="refresh"
          icon-only
          variant="ghost"
          size="small"
          :label="i18n.t('pdf_corpus.refresh_builds')"
          @click="emit('refresh')"
        />
      </header>
      <div class="history-list">
        <button
          v-for="build in builds"
          :key="build.build_id"
          type="button"
          class="history-row"
          :class="{ active: build.build_id === selectedBuildId }"
          :aria-current="build.build_id === selectedBuildId ? 'true' : undefined"
          @click="emit('select', build)"
        >
          <span
            class="dot"
            :data-status="build.status"
            :data-tone="corpusStatusTone(build)"
            aria-hidden="true"
          ></span
          ><span class="history-body"
            ><b
              ><span v-if="build.build_id === selectedBuildId" class="selected-mark"
                >✓ <span class="sr-only">{{ i18n.t("pdf_corpus.build_selected") }}</span></span
              >{{ build.source_filename }}</b
            ><small
              >{{ statusLabel(build) }} · {{ Math.round((build.progress || 0) * 100) }}% ·
              {{ build.record_count || 0 }} {{ i18n.t("pdf_corpus.records") }}</small
            ><small>{{ formatDate(build.created_at) }}</small
            ><small class="build-id">{{ build.build_id }}</small></span
          >
        </button>
        <p v-if="!builds.length" class="empty">{{ i18n.t("pdf_corpus.no_builds") }}</p>
      </div>
    </div>
  </details>
</template>
<style scoped>
.history-menu {
  position: relative;
}
.history-menu > summary {
  list-style: none;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}
.history-menu > summary::-webkit-details-marker {
  display: none;
}
.count {
  display: grid;
  place-items: center;
  min-width: 21px;
  height: 21px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--surface-subtle);
  font-size: var(--fs-xs);
}
.history-popover {
  position: absolute;
  z-index: 40;
  top: calc(100% + var(--space-2));
  inset-inline-end: 0;
  width: min(410px, calc(100vw - 28px));
  max-height: min(560px, 72vh);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-overlay);
  box-shadow: var(--shadow-overlay);
}
.history-popover header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: flex-start;
  padding: var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
}
.history-popover header > div {
  display: grid;
  gap: 2px;
}
.history-popover b {
  font-size: var(--fs-sm);
}
.history-popover small {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  line-height: 1.4;
}
.history-list {
  overflow: auto;
  padding: var(--space-2);
}
.history-row {
  width: 100%;
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  gap: var(--space-2);
  padding: var(--space-2);
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  background: var(--surface-overlay);
  color: inherit;
  text-align: start;
  cursor: pointer;
}
.history-row:hover {
  border-color: var(--border-subtle);
  background: var(--surface-raised);
}
.history-row.active {
  border-color: var(--border-interactive);
  background: var(--surface-raised);
}
.history-body {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.history-row b {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.selected-mark {
  margin-inline-end: var(--space-1);
  color: var(--tone-ok-fg);
}
.build-id {
  font-family: var(--font-mono, ui-monospace, monospace);
  overflow-wrap: anywhere;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-secondary);
  margin-top: 5px;
}
.dot[data-tone="success"] {
  background: var(--tone-ok-fg);
}
.dot[data-tone="warning"] {
  background: var(--tone-warn-fg);
}
.dot[data-tone="danger"] {
  background: var(--tone-danger-fg);
}
.empty {
  margin: 0;
  padding: var(--space-4);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.history-menu :is(summary, button):focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 2px;
}
</style>
