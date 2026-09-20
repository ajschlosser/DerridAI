<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, useId } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type { RecordsColumn } from "../../types/records";

const props = defineProps<{available: RecordsColumn[]; modelValue: string[]}>();
const emit = defineEmits<{
  "update:modelValue": [keys: string[]];
  apply: [];
  reset: [];
  cancel: [];
}>();

const i18n = useI18nStore();
const dialog = ref<HTMLDialogElement | null>(null);
const find = ref("");
const titleId = `records-columns-title-${useId().replaceAll(":", "")}`;
const selectedSet = computed(() => new Set(props.modelValue));
const visible = computed(() => props.modelValue.map(key => props.available.find(column => column.key === key) || {key, label: key}));
const hidden = computed(() => {
  const needle = find.value.trim().toLocaleLowerCase();
  return props.available.filter(column => {
    if (selectedSet.value.has(column.key)) return false;
    return !needle || column.label.toLocaleLowerCase().includes(needle) || column.key.toLocaleLowerCase().includes(needle);
  });
});

function setKeys(keys: string[]) {
  emit("update:modelValue", keys);
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
  if (props.modelValue.length <= 1) return;
  setKeys(props.modelValue.filter(item => item !== key));
}
function show(key: string) {
  if (!props.modelValue.includes(key)) setKeys([...props.modelValue, key]);
}
function onCancel(event: Event) {
  event.preventDefault();
  close();
}
function close() {
  dialog.value?.close();
  find.value = "";
  emit("cancel");
}
function apply() {
  if (!props.modelValue.length) return;
  emit("apply");
  close();
}
async function open() {
  find.value = "";
  dialog.value?.showModal();
  await nextTick();
  dialog.value?.querySelector<HTMLElement>("button,input")?.focus();
}

defineExpose({open, close});
</script>
<template>
  <dialog ref="dialog" class="records-columns-dialog" :aria-labelledby="titleId" @cancel="onCancel">
    <div class="records-columns-head">
      <div>
        <p class="records-columns-kicker">{{ i18n.t("records.table_view", "Table view") }}</p>
        <h2 :id="titleId">{{ i18n.t("records.configure_columns", "Configure columns") }}</h2>
      </div>
      <button type="button" class="btn icon-only" :aria-label="i18n.t('common.close', 'Close')" @click="close">×</button>
    </div>
    <div class="records-columns-body">
      <p>{{ i18n.t("records.configure_columns_help", "Choose the fields shown in the records table. Order is preserved.") }}</p>
      <div class="records-columns-grid">
        <section :aria-label="i18n.t('records.visible_columns', 'Visible columns')">
          <h3>{{ i18n.t("records.visible_columns", "Visible columns") }}</h3>
          <ol>
            <li v-for="(column, index) in visible" :key="column.key">
              <span>{{ column.label }}</span>
              <div class="records-columns-order">
                <button type="button" class="btn tiny" :disabled="index === 0" :aria-label="i18n.tf('search.move_column_up', 'Move {column} up', {column: column.label})" @click="move(column.key, -1)">↑</button>
                <button type="button" class="btn tiny" :disabled="index === visible.length - 1" :aria-label="i18n.tf('search.move_column_down', 'Move {column} down', {column: column.label})" @click="move(column.key, 1)">↓</button>
                <button type="button" class="btn tiny" :disabled="modelValue.length <= 1" :aria-label="i18n.tf('records.hide_column', 'Hide {column}', {column: column.label})" @click="hide(column.key)">{{ i18n.t("ui.remove", "Remove") }}</button>
              </div>
            </li>
          </ol>
        </section>
        <section :aria-label="i18n.t('records.available_fields', 'Available fields')">
          <h3>{{ i18n.t("records.available_fields", "Available fields") }}</h3>
          <label class="records-columns-find">
            <span class="sr-only">{{ i18n.t("records.find_column", "Find a field") }}</span>
            <input class="control" type="search" :value="find" :placeholder="i18n.t('records.find_column', 'Find a field')" @input="find = ($event.target as HTMLInputElement).value">
          </label>
          <ul class="records-columns-available">
            <li v-for="column in hidden" :key="column.key">
              <button type="button" class="records-columns-add" @click="show(column.key)">
                <span aria-hidden="true">+</span>
                {{ column.label }}
              </button>
            </li>
            <li v-if="!hidden.length" class="records-columns-empty">{{ i18n.t("records.no_fields_to_add", "No additional fields match.") }}</li>
          </ul>
        </section>
      </div>
    </div>
    <div class="records-columns-foot">
      <button type="button" class="btn" @click="emit('reset')">{{ i18n.t("records.reset_columns", "Reset defaults") }}</button>
      <button type="button" class="btn" @click="close">{{ i18n.t("common.cancel", "Cancel") }}</button>
      <button type="button" class="btn primary" :disabled="!modelValue.length" @click="apply">{{ i18n.t("records.save_columns", "Save columns") }}</button>
    </div>
  </dialog>
</template>
<style scoped>
.records-columns-dialog{width:min(44rem,calc(100vw - 1.5rem));max-height:min(82vh,40rem);padding:0;border:1px solid var(--line);border-radius:16px;background:var(--panel,#fff);color:var(--text);box-shadow:0 24px 60px rgba(20,30,24,.18)}
.records-columns-dialog::backdrop{background:rgba(21,27,24,.42)}
.records-columns-head,.records-columns-foot{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px}
.records-columns-head{border-bottom:1px solid var(--line)}
.records-columns-kicker{margin:0;font-size:.8125rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--accent-2,var(--accent))}
h2{margin:4px 0 0;font:600 1.125rem/1.3 Georgia,"Times New Roman",serif}
.records-columns-body{display:grid;gap:12px;max-height:calc(82vh - 9rem);overflow:auto;padding:14px 16px}
.records-columns-body>p{margin:0;color:var(--muted);font-size:.875rem;line-height:1.45}
.records-columns-grid{display:grid;gap:16px}
@media (min-width: 720px){.records-columns-grid{grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);align-items:start}}
h3{margin:0 0 8px;font-size:.8125rem;font-weight:800}
ol,ul{margin:0;padding:0;list-style:none;display:grid;gap:6px}
ol li{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px;min-height:2.625rem;padding:6px 8px;border:1px solid var(--line);border-radius:10px;background:var(--panel-2,var(--soft,#f4f7f5))}
.records-columns-order{display:flex;flex-wrap:wrap;gap:4px}
.records-columns-find{display:block;margin-bottom:8px}
.records-columns-add{display:flex;align-items:center;gap:8px;width:100%;min-height:2.5rem;padding:6px 10px;border:1px solid var(--line);border-radius:10px;background:var(--panel,#fff);color:var(--text);font:700 .8125rem/1.3 inherit;text-align:left;cursor:pointer}
.records-columns-add:hover,.records-columns-add:focus-visible{border-color:var(--accent);background:var(--accent-soft,#eef6f1);outline:none}
.records-columns-empty{color:var(--muted);font-size:.8125rem;padding:8px}
.records-columns-foot{border-top:1px solid var(--line);flex-wrap:wrap;justify-content:flex-end}
</style>
