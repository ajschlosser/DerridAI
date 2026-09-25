<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import type { CompareLibraryOption } from "../../domain/compare";
import { filterLibraryOptions } from "../../domain/compare";

const props = defineProps<{
  modelValue: string;
  options: CompareLibraryOption[];
  label: string;
  placeholder: string;
  selectedHint: string;
  emptyHint: string;
  noMatches: string;
  clearLabel: string;
}>();
const emit = defineEmits<{ "update:modelValue": [string] }>();
const query = ref("");
const open = ref(false);
const active = ref(-1);
const listId = `compare-picker-${Math.random().toString(36).slice(2, 8)}`;
const selected = computed(
  () => props.options.find((item) => item.value === props.modelValue) || null,
);
const matches = computed(() => filterLibraryOptions(props.options, query.value));
const inputValue = computed(() =>
  open.value || !selected.value ? query.value : selected.value.label,
);

function show() {
  query.value = selected.value?.label || query.value;
  open.value = true;
  active.value = -1;
}
function choose(value: string) {
  emit("update:modelValue", value);
  const option = props.options.find((item) => item.value === value);
  query.value = option?.label || "";
  open.value = false;
}
function clear() {
  emit("update:modelValue", "");
  query.value = "";
  open.value = false;
}
function onInput(event: Event) {
  query.value = (event.target as HTMLInputElement).value;
  open.value = true;
  if (selected.value && query.value !== selected.value.label) emit("update:modelValue", "");
}
function onKey(event: KeyboardEvent) {
  if (event.key === "Escape") {
    open.value = false;
    return;
  }
  if (!matches.value.length) return;
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    open.value = true;
    const last = matches.value.length - 1;
    active.value =
      event.key === "ArrowDown"
        ? (active.value + 1) % matches.value.length
        : active.value <= 0
          ? last
          : active.value - 1;
    void nextTick(() =>
      document.getElementById(`${listId}-${active.value}`)?.scrollIntoView({ block: "nearest" }),
    );
    return;
  }
  if (event.key === "Enter" && open.value) {
    event.preventDefault();
    const item = matches.value[Math.max(0, active.value)];
    if (item) choose(item.value);
  }
}
</script>
<template>
  <div class="compare-picker">
    <label class="compare-picker-label" :for="`${listId}-input`">{{ label }}</label>
    <div class="compare-picker-shell">
      <input
        :id="`${listId}-input`"
        class="control"
        role="combobox"
        :aria-label="label"
        aria-autocomplete="list"
        :aria-expanded="open ? 'true' : 'false'"
        :aria-controls="listId"
        :aria-activedescendant="active >= 0 ? `${listId}-${active}` : undefined"
        :value="inputValue"
        :placeholder="placeholder"
        autocomplete="off"
        @focus="show"
        @input="onInput"
        @keydown="onKey"
        @blur="open = false"
      />
      <button class="btn tiny" type="button" :disabled="!modelValue" @mousedown.prevent="clear">
        {{ clearLabel }}
      </button>
    </div>
    <ul v-if="open" :id="listId" class="compare-picker-list" role="listbox" :aria-label="label">
      <li v-if="!matches.length" class="compare-picker-empty" role="presentation">
        {{ noMatches }}
      </li>
      <li
        v-for="(item, index) in matches"
        :id="`${listId}-${index}`"
        :key="item.value"
        role="option"
        :aria-selected="item.value === modelValue"
        :class="{ active: index === active }"
        @mousedown.prevent="choose(item.value)"
      >
        <b>{{ item.label.split(" · ")[1] || item.label }}</b>
        <small>{{ item.label }}</small>
      </li>
    </ul>
    <p class="compare-picker-hint">
      {{ selected ? selectedHint.replace("{label}", selected.label) : emptyHint }}
    </p>
  </div>
</template>
<style scoped>
.compare-picker {
  display: grid;
  gap: 6px;
  min-width: 0;
}
.compare-picker-label {
  font-size: 0.8125rem;
  font-weight: 700;
}
.compare-picker-shell {
  display: flex;
  gap: 6px;
  align-items: center;
}
.compare-picker-shell .control {
  flex: 1;
  min-width: 0;
  min-height: 40px;
}
.compare-picker-list {
  list-style: none;
  margin: 0;
  padding: 6px;
  max-height: 280px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface-overlay, var(--panel));
  box-shadow: var(--shadow-md, 0 12px 28px rgba(15, 23, 42, 0.16));
}
.compare-picker-list li[role="option"] {
  display: grid;
  gap: 2px;
  min-height: 40px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
}
.compare-picker-list li.active,
.compare-picker-list li[role="option"]:hover {
  background: var(--accent-soft, var(--soft));
}
.compare-picker-list b {
  font-size: 0.875rem;
}
.compare-picker-list small {
  color: var(--muted);
  font-size: 0.8125rem;
}
.compare-picker-empty,
.compare-picker-hint {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
.compare-picker-list li[role="option"]:focus-visible {
  outline: 3px solid var(--focus-ring, var(--accent));
  outline-offset: 2px;
}
@media (prefers-reduced-motion: reduce) {
  .compare-picker-list li {
    transition: none;
  }
}
</style>
