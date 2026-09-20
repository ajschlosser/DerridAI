<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import AppIcon from "../AppIcon.vue";
import UiButton from "../ui/UiButton.vue";
import { useI18nStore } from "../../stores/i18n";
import type { RecordsFileOrigin, RecordsFileTab } from "../../domain/recordsFiles";

const props = withDefaults(
  defineProps<{
    files: RecordsFileTab[];
    canManage?: boolean;
  }>(),
  {canManage: true},
);
const emit = defineEmits<{
  select: [id: string];
  close: [id: string];
  open: [];
  merge: [];
  subset: [];
  export: [];
}>();
const i18n = useI18nStore();

function originLabel(origin?: RecordsFileOrigin) {
  const keys: Record<RecordsFileOrigin, [string, string]> = {
    imported: ["records.file_origin_imported", "Imported"],
    subset: ["records.file_origin_subset", "Subset"],
    merge: ["records.file_origin_merge", "Merged"],
    work_split: ["records.file_origin_work_split", "Split by work"],
    chroma: ["records.file_origin_chroma", "From collection"],
  };
  const pair = keys[origin || "imported"];
  return i18n.t(pair[0], pair[1]);
}

function originLine(file: RecordsFileTab) {
  const origin = originLabel(file.origin);
  return file.origin_detail ? `${origin} · ${file.origin_detail}` : origin;
}

function closeLabel(file: RecordsFileTab) {
  return i18n.tf("records.close_named", "Close {name}", {name: file.name});
}
</script>
<template>
  <aside class="card records-file-rail" :aria-label="i18n.t('records.files', 'Local JSONL')">
    <div class="records-file-head">
      <div>
        <b>{{ i18n.t("records.files", "Local JSONL") }}</b>
        <span>{{
          i18n.tf("records.file_count", "{count} files", {
            count: props.files.length.toLocaleString(i18n.locale),
          })
        }}</span>
      </div>
    </div>
    <p class="records-file-help">{{
      i18n.t(
        "records.files_help",
        "Browser-local corpus files. The selected file is the one Records, Vector sync, and PDF matching use.",
      )
    }}</p>
    <div
      v-if="props.canManage"
      class="records-file-actions"
      :aria-label="i18n.t('records.file_actions', 'JSONL file actions')"
    >
      <UiButton size="small" icon="upload" :label="i18n.t('ui.open_jsonl', 'Open JSONL')" @click="emit('open')" />
      <UiButton
        size="small"
        icon="plus"
        :label="i18n.t('ui.merge_tabs', 'Merge files')"
        :disabled="props.files.length < 2"
        :disabled-reason="i18n.t('ui.need_two_tabs_merge', 'Load at least two JSONL files to merge them.')"
        @click="emit('merge')"
      />
      <UiButton size="small" icon="filter" :label="i18n.t('ui.create_subset', 'Create subset')" @click="emit('subset')" />
      <UiButton size="small" icon="download" :label="i18n.t('ui.export', 'Export')" @click="emit('export')" />
    </div>
    <div class="records-file-list" role="list">
      <div
        v-for="file in props.files"
        :key="file.id"
        class="records-file-item"
        :class="{active: file.active}"
        role="listitem"
      >
        <button
          type="button"
          class="records-file-select"
          :aria-current="file.active ? 'true' : undefined"
          @click="emit('select', file.id)"
        >
          <span class="records-file-name">{{ file.name }}</span>
          <small>
            <span v-if="file.dirty" class="records-file-edited">{{
              i18n.t("records.file_edited", "Edited since load")
            }}</span>
            <span>{{ originLine(file) }}</span>
            <span>{{ file.count.toLocaleString(i18n.locale) }} {{ i18n.t("dynamic.records", "records") }}</span>
          </small>
        </button>
        <button
          v-if="props.canManage"
          type="button"
          class="records-file-close"
          :aria-label="closeLabel(file)"
          @click="emit('close', file.id)"
        >
          <AppIcon name="close" />
        </button>
      </div>
    </div>
  </aside>
</template>
<style scoped>
.records-file-rail {
  display: grid;
  align-content: start;
  gap: 10px;
  min-width: 0;
  padding: 0 0 10px;
}
.records-file-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 13px 0;
}
.records-file-head > div {
  display: grid;
  gap: 2px;
}
.records-file-head b {
  font-size: 0.8125rem;
}
.records-file-head span,
.records-file-help {
  font-size: 0.8125rem;
  color: var(--muted);
}
.records-file-help {
  margin: 0;
  padding: 0 13px;
  line-height: 1.45;
}
.records-file-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 0 10px;
}
.records-file-actions :deep(.ui-button-wrap) {
  min-width: 0;
}
.records-file-actions :deep(.ui-button) {
  width: 100%;
}
.records-file-list {
  display: grid;
  padding: 0 6px;
}
.records-file-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 2px;
  align-items: start;
  border-radius: 8px;
}
.records-file-item.active {
  background: var(--ui-accent-soft);
}
.records-file-select {
  min-width: 0;
  min-height: 44px;
  display: grid;
  gap: 3px;
  padding: 8px 9px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text);
  text-align: left;
  cursor: pointer;
}
.records-file-item:hover,
.records-file-select:hover {
  background: var(--card);
}
.records-file-item.active .records-file-select {
  color: var(--accent-fg);
  background: transparent;
}
.records-file-name {
  font-size: 0.8125rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.records-file-select small {
  display: grid;
  gap: 1px;
  font-size: 0.8125rem;
  color: var(--muted);
  font-weight: 500;
}
.records-file-edited {
  color: var(--tone-warn-fg);
  font-weight: 700;
}
.records-file-close {
  width: 36px;
  height: 36px;
  margin: 4px 4px 0 0;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}
.records-file-close:hover {
  color: var(--danger);
  background: var(--danger-bg, var(--card));
}
.records-file-close :deep(svg) {
  width: 14px;
  height: 14px;
}
@media (max-width: 900px) {
  .records-file-actions {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .records-file-actions {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
