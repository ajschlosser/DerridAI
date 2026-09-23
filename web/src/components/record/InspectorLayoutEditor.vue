<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import UiDialog from "../ui/UiDialog.vue";
import {
  INSPECTOR_TABS,
  createInspectorField,
  createInspectorHeading,
  defaultInspectorLayout,
  moveInspectorRow,
  unusedInspectorFields,
  type InspectorLayout,
  type InspectorLayoutRow,
  type InspectorTabKey,
} from "../../domain/inspectorLayout";

const props = defineProps<{ layout: InspectorLayout }>();
const emit = defineEmits<{ apply: [layout: InspectorLayout]; reset: [] }>();
const i18n = useI18nStore();
const isOpen = ref(false);
const tab = ref<InspectorTabKey>("overview");
const draft = ref<InspectorLayout>(defaultInspectorLayout());
const dragging = ref<number | null>(null);

const tabLabels: Record<InspectorTabKey, [string, string]> = {
  overview: ["record.tab_overview", "Overview"],
  provenance: ["record.tab_provenance", "Provenance"],
  indexing: ["record.tab_indexing", "Indexing"],
};

const rows = computed(() => draft.value[tab.value]);
const unused = computed(() => unusedInspectorFields(tab.value, rows.value));

function fieldLabel(key: string) {
  if (key === "__pages") return i18n.t("record.page", "Page");
  return i18n.t(`field.${key}`, key.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase()));
}

function open() {
  draft.value = structuredClone(props.layout);
  tab.value = "overview";
  isOpen.value = true;
}
function close() {
  isOpen.value = false;
  dragging.value = null;
}
function apply() {
  emit("apply", structuredClone(draft.value));
  isOpen.value = false;
}
function reset() {
  draft.value = defaultInspectorLayout();
  emit("reset");
}
function setRows(next: InspectorLayoutRow[]) {
  draft.value = { ...draft.value, [tab.value]: next };
}
function addHeading() {
  setRows([...rows.value, createInspectorHeading(i18n.t("record.layout_heading", "Section"))]);
}
function addField(name: string) {
  if (!name) return;
  setRows([...rows.value, createInspectorField(name)]);
}
function removeRow(index: number) {
  setRows(rows.value.filter((_, i) => i !== index));
}
function move(index: number, direction: number) {
  setRows(moveInspectorRow(rows.value, index, index + direction));
}
function onDragStart(index: number) {
  dragging.value = index;
}
function onDrop(index: number) {
  if (dragging.value == null) return;
  setRows(moveInspectorRow(rows.value, dragging.value, index));
  dragging.value = null;
}
function updateHeading(index: number, label: string) {
  setRows(rows.value.map((row, i) => (i === index && row.kind === "heading" ? { ...row, label } : row)));
}

defineExpose({ open, close });
</script>

<template>
  <UiDialog
    :open="isOpen"
    size="medium"
    :title="i18n.t('record.inspector_layout', 'Configure inspector fields')"
    :description="
      i18n.t(
        'record.inspector_layout_help',
        'Choose the fields shown in each inspector tab, their order, and category headings. Drag a row or use the move buttons.',
      )
    "
    :close-label="i18n.t('common.close', 'Close')"
    @close="close"
  >
    <div class="layout-editor">
      <div class="layout-tabs" role="tablist" :aria-label="i18n.t('record.inspector_sections', 'Record inspector sections')">
        <button
          v-for="item in INSPECTOR_TABS"
          :key="item"
          type="button"
          role="tab"
          :aria-selected="tab === item"
          :class="{ active: tab === item }"
          @click="tab = item"
        >
          {{ i18n.t(tabLabels[item][0], tabLabels[item][1]) }}
        </button>
      </div>
      <ol class="layout-rows" :aria-label="i18n.t('record.layout_rows', 'Inspector field order')">
        <li
          v-for="(row, index) in rows"
          :key="row.id"
          class="layout-row"
          :class="row.kind"
          draggable="true"
          @dragstart="onDragStart(index)"
          @dragover.prevent
          @drop.prevent="onDrop(index)"
        >
          <span class="layout-grip" aria-hidden="true"></span>
          <span class="sr-only">{{ i18n.t("record.drag_handle", "Drag to reorder") }}</span>
          <template v-if="row.kind === 'heading'">
            <label class="layout-heading-field">
              <span class="sr-only">{{ i18n.t("record.layout_heading", "Section") }}</span>
              <input class="control" :value="row.label" @input="updateHeading(index, ($event.target as HTMLInputElement).value)" />
            </label>
          </template>
          <span v-else class="layout-field-label">{{ fieldLabel(row.field) }}</span>
          <div class="layout-row-actions">
            <button type="button" class="btn tiny" :disabled="index === 0" :aria-label="i18n.t('record.move_up', 'Move up')" @click="move(index, -1)">↑</button>
            <button type="button" class="btn tiny" :disabled="index === rows.length - 1" :aria-label="i18n.t('record.move_down', 'Move down')" @click="move(index, 1)">↓</button>
            <button type="button" class="btn tiny danger" :aria-label="i18n.t('ui.remove', 'Remove')" @click="removeRow(index)">×</button>
          </div>
        </li>
      </ol>
      <div class="layout-add">
        <button type="button" class="btn" @click="addHeading">{{ i18n.t("record.add_heading", "Add heading") }}</button>
        <label v-if="unused.length">
          <span class="sr-only">{{ i18n.t("record.add_field", "Add field") }}</span>
          <select class="control" @change="addField(($event.target as HTMLSelectElement).value); ($event.target as HTMLSelectElement).value = ''">
            <option value="">{{ i18n.t("record.add_field", "Add field") }}</option>
            <option v-for="name in unused" :key="name" :value="name">{{ fieldLabel(name) }}</option>
          </select>
        </label>
      </div>
      <p class="note">{{ unused.length ? "" : i18n.t("record.layout_all_fields", "Every catalog field for this tab is already in the list.") }}</p>
    </div>
    <template #footer>
      <button type="button" class="btn" @click="reset">{{ i18n.t("record.layout_reset", "Reset layout") }}</button>
      <button type="button" class="btn" @click="close">{{ i18n.t("common.cancel", "Cancel") }}</button>
      <button type="button" class="btn primary" @click="apply">{{ i18n.t("common.apply", "Apply") }}</button>
    </template>
  </UiDialog>
</template>

<style scoped>
.layout-editor {
  display: grid;
  gap: 12px;
}
.layout-tabs {
  display: flex;
  gap: 4px;
}
.layout-tabs button {
  flex: 1;
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  color: var(--muted);
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 750;
  cursor: pointer;
}
.layout-tabs button.active {
  background: var(--surface-raised);
  color: var(--text-2);
  border-color: var(--border-strong);
}
.layout-rows {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
  max-height: min(50vh, 420px);
  overflow: auto;
}
.layout-row {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 6px 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-card);
  cursor: grab;
}
.layout-row.heading {
  background: var(--surface-raised);
}
.layout-grip {
  width: 10px;
  height: 16px;
  border-inline-start: 2px dotted var(--muted);
  border-inline-end: 2px dotted var(--muted);
}
.layout-heading-field {
  min-width: 0;
}
.layout-field-label {
  font-size: 0.8125rem;
  font-weight: 700;
}
.layout-row-actions {
  display: flex;
  gap: 4px;
}
.layout-add {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.layout-add .control {
  min-width: 180px;
}
.note {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
</style>
