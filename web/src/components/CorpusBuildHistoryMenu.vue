<script setup lang="ts">
import type { CorpusBuild } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";
// eslint-disable-next-line @typescript-eslint/no-unused-vars -- SA-13: preserve legacy setup binding until its owning workflow is extracted.
const props = withDefaults(
  defineProps<{ builds: CorpusBuild[]; selectedBuildId?: string; total?: number }>(),
  { selectedBuildId: "", total: 0 },
);
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
        <button
          type="button"
          class="icon-button"
          :title="i18n.t('pdf_corpus.refresh_builds')"
          :aria-label="i18n.t('pdf_corpus.refresh_builds')"
          @click="emit('refresh')"
        >
          ↻
        </button>
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
          <span class="dot" :data-status="build.status" aria-hidden="true"></span
          ><span
            ><b>{{ build.source_filename }}</b
            ><small
              >{{ statusLabel(build) }} · {{ Math.round((build.progress || 0) * 100) }}% ·
              {{ build.record_count || 0 }} {{ i18n.t("pdf_corpus.records") }}</small
            ><small>{{ formatDate(build.created_at) }}</small></span
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
  gap: 7px;
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
  background: var(--soft);
  font-size: 0.75rem;
}
.history-popover {
  position: absolute;
  z-index: 40;
  top: calc(100% + 8px);
  inset-inline-end: 0;
  width: min(410px, calc(100vw - 28px));
  max-height: min(560px, 72vh);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface-overlay, #fff);
  box-shadow: 0 18px 48px rgb(15 23 42 / 0.18);
}
.history-popover header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  padding: 12px 13px;
  border-bottom: 1px solid var(--line);
}
.history-popover header > div {
  display: grid;
  gap: 2px;
}
.history-popover b {
  font-size: 0.875rem;
}
.history-popover small {
  font-size: 0.8125rem;
  color: var(--muted);
  line-height: 1.4;
}
.history-list {
  overflow: auto;
  padding: 7px;
}
.history-row {
  width: 100%;
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  gap: 9px;
  padding: 9px;
  border: 1px solid transparent;
  border-radius: 9px;
  background: var(--surface-overlay, #fff);
  color: inherit;
  text-align: start;
  cursor: pointer;
}
.history-row:hover,
.history-row.active {
  border-color: var(--line);
  background: var(--surface-raised, #fff);
}
.history-row > span:last-child {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.history-row b {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #777;
  margin-top: 5px;
}
.dot[data-status="ready"],
.dot[data-status="published"] {
  background: #287a4c;
}
.dot[data-status="running"],
.dot[data-status="queued"] {
  background: #8e6815;
}
.dot[data-status="failed"],
.dot[data-status="interrupted"] {
  background: #a13f3f;
}
.empty {
  margin: 0;
  padding: 18px;
  color: var(--muted);
  font-size: 0.8125rem;
}
.icon-button {
  border: 0;
  background: transparent;
  min-width: 36px;
  min-height: 36px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.125rem;
}
.history-menu :is(summary, button):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
</style>
