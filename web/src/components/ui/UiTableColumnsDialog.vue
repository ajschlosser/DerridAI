<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, useId } from "vue";
import { useI18nStore } from "../../stores/i18n";
import UiDialog from "./UiDialog.vue";
import {
  MIN_COLUMN_PERCENT,
  normalizeColumnWidths,
  setColumnWidth,
  type ColumnWidths,
} from "../../domain/tableColumnWidths";

/**
 * Choose, order and size the columns of any configurable table. The parent owns the draft
 * (v-model for the shown keys, v-model:widths for their widths) and commits it on `apply`.
 * Pass `widths` to offer width controls; leave it out for tables that size their own columns.
 */
const props = withDefaults(
  defineProps<{
    available: { key: string; label: string }[];
    modelValue: string[];
    widths?: ColumnWidths | null;
    title?: string;
    description?: string;
  }>(),
  { widths: null, title: "", description: "" },
);
const emit = defineEmits<{
  "update:modelValue": [keys: string[]];
  "update:widths": [widths: ColumnWidths];
  apply: [];
  reset: [];
  cancel: [];
}>();

const i18n = useI18nStore();
const id = useId();
const isOpen = ref(false);
const find = ref("");
const sizing = computed(() => props.widths !== null);
const selectedSet = computed(() => new Set(props.modelValue));
const labelOf = (key: string) => props.available.find((column) => column.key === key)?.label || key;
const shownWidths = computed(() =>
  sizing.value ? normalizeColumnWidths(props.modelValue, props.widths || {}) : {},
);
const visible = computed(() =>
  props.modelValue.map((key) => ({ key, label: labelOf(key), width: shownWidths.value[key] ?? 0 })),
);
const hidden = computed(() => {
  const needle = find.value.trim().toLocaleLowerCase();
  return props.available.filter(
    (column) =>
      !selectedSet.value.has(column.key) &&
      (!needle ||
        column.label.toLocaleLowerCase().includes(needle) ||
        column.key.toLocaleLowerCase().includes(needle)),
  );
});
const maxWidth = computed(() =>
  Math.max(MIN_COLUMN_PERCENT, 100 - MIN_COLUMN_PERCENT * (props.modelValue.length - 1)),
);

function setKeys(keys: string[]) {
  emit("update:modelValue", keys);
  // Keep the survivors' proportions; a newly shown column takes its default share.
  if (sizing.value) emit("update:widths", normalizeColumnWidths(keys, props.widths || {}));
}
function move(key: string, direction: number) {
  const at = props.modelValue.indexOf(key);
  const to = at + direction;
  if (at < 0 || to < 0 || to >= props.modelValue.length) return;
  const next = [...props.modelValue];
  [next[at], next[to]] = [next[to], next[at]];
  setKeys(next);
}
function hide(key: string) {
  if (props.modelValue.length > 1) setKeys(props.modelValue.filter((item) => item !== key));
}
function show(key: string) {
  if (!props.modelValue.includes(key)) setKeys([...props.modelValue, key]);
}
function resize(key: string, value: string) {
  const percent = Number(value);
  if (!Number.isFinite(percent)) return;
  emit("update:widths", setColumnWidth(props.modelValue, shownWidths.value, key, percent));
}
function evenWidths() {
  const share = 100 / props.modelValue.length;
  emit(
    "update:widths",
    normalizeColumnWidths(
      props.modelValue,
      Object.fromEntries(props.modelValue.map((key) => [key, share])),
    ),
  );
}
function formatPercent(value: number) {
  return (value / 100).toLocaleString(i18n.locale, { style: "percent", maximumFractionDigits: 1 });
}
function open() {
  find.value = "";
  isOpen.value = true;
}
function close() {
  if (!isOpen.value) return;
  isOpen.value = false;
  find.value = "";
  emit("cancel");
}
function apply() {
  if (!props.modelValue.length) return;
  isOpen.value = false;
  emit("apply");
}

defineExpose({ open, close });
</script>

<template>
  <UiDialog
    :open="isOpen"
    size="medium"
    :title="title || i18n.t('records.configure_columns')"
    :description="
      description ||
      (sizing ? i18n.t('table.columns_help_widths') : i18n.t('records.configure_columns_help'))
    "
    :close-label="i18n.t('common.close')"
    @close="close"
  >
    <div class="ui-columns">
      <section class="ui-columns-shown" :aria-labelledby="`${id}-shown`">
        <div class="ui-columns-section-head">
          <h3 :id="`${id}-shown`">{{ i18n.t("records.visible_columns") }}</h3>
          <button
            v-if="sizing && modelValue.length > 1"
            type="button"
            class="btn tiny"
            @click="evenWidths"
          >
            {{ i18n.t("table.even_widths") }}
          </button>
        </div>
        <div v-if="sizing" class="ui-columns-preview" aria-hidden="true">
          <span
            v-for="column in visible"
            :key="column.key"
            :style="{ flexBasis: `${column.width}%` }"
            :title="`${column.label} · ${formatPercent(column.width)}`"
            >{{ column.label }}</span
          >
        </div>
        <ol>
          <li v-for="(column, index) in visible" :key="column.key">
            <span class="ui-columns-name">{{ column.label }}</span>
            <label v-if="sizing" class="ui-columns-width">
              <span class="sr-only">{{
                i18n.tf("table.column_width", {
                  column: column.label,
                })
              }}</span>
              <input
                class="control"
                type="number"
                inputmode="decimal"
                :min="MIN_COLUMN_PERCENT"
                :max="maxWidth"
                step="1"
                :value="column.width"
                :disabled="modelValue.length <= 1"
                @change="resize(column.key, ($event.target as HTMLInputElement).value)"
              />
              <span aria-hidden="true">%</span>
            </label>
            <div class="ui-columns-order">
              <button
                type="button"
                class="btn tiny"
                :disabled="index === 0"
                :aria-label="i18n.tf('search.move_column_up', { column: column.label })"
                @click="move(column.key, -1)"
              >
                ↑
              </button>
              <button
                type="button"
                class="btn tiny"
                :disabled="index === visible.length - 1"
                :aria-label="
                  i18n.tf('search.move_column_down', {
                    column: column.label,
                  })
                "
                @click="move(column.key, 1)"
              >
                ↓
              </button>
              <button
                type="button"
                class="btn tiny"
                :disabled="modelValue.length <= 1"
                :aria-label="i18n.tf('records.hide_column', { column: column.label })"
                @click="hide(column.key)"
              >
                {{ i18n.t("ui.remove") }}
              </button>
            </div>
          </li>
        </ol>
      </section>
      <section class="ui-columns-available" :aria-labelledby="`${id}-available`">
        <h3 :id="`${id}-available`">
          {{ i18n.t("records.available_fields") }}
        </h3>
        <label class="ui-columns-find">
          <span class="sr-only">{{ i18n.t("records.find_column") }}</span>
          <input
            class="control"
            type="search"
            :value="find"
            :placeholder="i18n.t('records.find_column')"
            @input="find = ($event.target as HTMLInputElement).value"
          />
        </label>
        <ul>
          <li v-for="column in hidden" :key="column.key">
            <button type="button" class="ui-columns-add" @click="show(column.key)">
              <span aria-hidden="true">+</span>
              {{ column.label }}
            </button>
          </li>
          <li v-if="!hidden.length" class="ui-columns-empty">
            {{ i18n.t("records.no_fields_to_add") }}
          </li>
        </ul>
      </section>
    </div>
    <template #footer>
      <button type="button" class="btn" @click="emit('reset')">
        {{ i18n.t("records.reset_columns") }}
      </button>
      <div class="ui-columns-commit">
        <button type="button" class="btn" @click="close">
          {{ i18n.t("common.cancel") }}
        </button>
        <button type="button" class="btn primary" :disabled="!modelValue.length" @click="apply">
          {{ i18n.t("records.save_columns") }}
        </button>
      </div>
    </template>
  </UiDialog>
</template>

<style scoped>
.ui-columns {
  display: grid;
  gap: var(--space-4);
}
@media (min-width: 720px) {
  .ui-columns {
    grid-template-columns: minmax(0, 1.3fr) minmax(0, 0.9fr);
    align-items: start;
  }
}
.ui-columns h3 {
  margin: 0;
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
  color: var(--text-primary);
}
.ui-columns-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.ui-columns-available h3 {
  margin-bottom: var(--space-2);
}
.ui-columns-preview {
  display: flex;
  gap: 2px;
  margin-bottom: var(--space-2);
  overflow: hidden;
  border-radius: var(--radius-control);
}
.ui-columns-preview span {
  flex: 0 0 auto;
  min-width: 0;
  overflow: hidden;
  padding: 4px 6px;
  background: var(--surface-selected);
  color: var(--accent-fg);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
  text-overflow: ellipsis;
  white-space: nowrap;
}
ol,
ul {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
ol li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
  padding: 6px 8px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.ui-columns-name {
  flex: 1 1 8rem;
  min-width: 0;
  font-size: var(--fs-base);
  font-weight: var(--fw-semibold);
  overflow-wrap: anywhere;
}
.ui-columns-width {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
}
.ui-columns-width input {
  width: 5rem;
  min-height: var(--control-height-small);
  font-variant-numeric: tabular-nums;
}
.ui-columns-order {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.ui-columns-find {
  display: block;
  margin-bottom: var(--space-2);
}
.ui-columns-find input {
  width: 100%;
}
.ui-columns-add {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  min-height: 2.5rem;
  padding: 6px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  color: var(--text-primary);
  font: inherit;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  text-align: left;
  cursor: pointer;
}
.ui-columns-add:hover,
.ui-columns-add:focus-visible {
  border-color: var(--border-interactive);
  background: var(--surface-hover);
}
.ui-columns-empty {
  padding: var(--space-2);
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
}
.ui-columns-commit {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>
